"""Protocolos del Experimento 001 (001-A, 001-B, 001-C) y su CLI reproducible.

Uso: `python -m ide.experiments.exp001_runner [--profile {quick,full}] [--seeds 42 43 ...]
[--out results/] [--jobs N] [--attribution]`. Con `--attribution` ejecuta sólo 001-D.
"""

import argparse
import csv
import dataclasses
import json
import math
import sys
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, cast

from ide.config import SimulationConfig
from ide.domain.types import Pattern
from ide.experiments.metrics import TickMetrics, propagation_time, windowed_accuracy
from ide.simulation.engine import SimulationEngine

TARGET_PATTERN = Pattern((("id", "p_0"),))
RECOVERY_WINDOW = 20
ABLATION_LEVELS = (0.10, 0.30, 0.50, 0.70)
_INJECTED_VALUE = -1.0
_INJECTED_CONFIDENCE = 0.95
_RECOVERY_FRACTION = 0.9


@dataclass(frozen=True)
class SurplusReport:
    collective_accuracy: float  # cumulative_decision_accuracy final, comm on
    isolated_accuracy: float  # ídem, comm off
    collective_surplus: float  # collective_accuracy - isolated_accuracy
    collective_accessible_coverage: float  # accessible_coverage_mean final, comm on
    isolated_accessible_coverage: float  # accessible_coverage_mean final, comm off
    collective_coverage: float
    isolated_coverage: float
    collective_individual_coverage_mean: float
    mean_messages_per_agent: float  # media de messages_per_agent sobre todos los ticks, comm on
    accuracy_gain_per_message: float | None  # collective_surplus / mean_messages_per_agent
    propagation_t50: dict[str, int | None]  # por pattern.label, corrida colectiva
    propagation_t90: dict[str, int | None]


@dataclass(frozen=True)
class FalsificationReport:
    target_pattern: str  # TARGET_PATTERN.label == "id=p_0"
    injected_agents: int
    initial_injected_prevalence: float  # snapshot inmediatamente tras inyectar
    peak_false_prevalence: float  # máximo entre la inicial y la de cada tick posterior
    final_false_prevalence: float  # pattern_false_prevalence[p_0] del último tick
    ticks_to_extinction: int | None  # menor k >= 1 con prevalencia falsa 0
    extinguished_or_contained: bool  # final < initial


@dataclass(frozen=True)
class AblationPointResult:
    ablation_fraction: float
    remaining_agents: int
    pre_ablation_coverage: float  # collective_coverage del último tick de warmup
    immediate_post_ablation_coverage: float  # snapshot inmediatamente tras la ablación
    final_recovered_coverage: float  # collective_coverage del último tick
    retention_ratio: float  # immediate_post / pre (0.0 si pre == 0)
    pre_ablation_accuracy: float  # windowed_accuracy de los últimos RECOVERY_WINDOW de warmup
    recovery_ticks: int | None


@dataclass(frozen=True)
class ResilienceReport:
    ablation_results: tuple[AblationPointResult, ...]
    discoverers_ablated_count: int
    remaining_agents_after_discoverer_ablation: int
    post_discoverer_ablation_prevalence: float  # pattern_prevalence[p_0] tras la ablación
    final_social_persistence_prevalence: float  # pattern_prevalence[p_0] del último tick
    social_persistence_ticks: int | None  # menor k >= 1 con prevalencia 0; None si sobrevive


@dataclass(frozen=True)
class Profile:
    total_ticks: int
    injection_tick: int
    warmup_ticks: int
    post_ablation_ticks: int


# Decisión 11: las funciones usan `quick` por defecto; la CLI, `full`.
PROFILES: dict[str, Profile] = {
    "quick": Profile(total_ticks=300, injection_tick=80, warmup_ticks=150, post_ablation_ticks=100),
    "full": Profile(
        total_ticks=1000, injection_tick=200, warmup_ticks=500, post_ablation_ticks=200
    ),
    # Pre-registro de la Fase II (design D29): los protocolos 002 y 003 sólo usan `total_ticks`.
    "phase2": Profile(
        total_ticks=2000, injection_tick=80, warmup_ticks=150, post_ablation_ticks=100
    ),
    # Pre-registro de la Fase II-B (design D56): los protocolos 25a a 25d sólo usan `total_ticks`.
    "phase25": Profile(
        total_ticks=5000, injection_tick=80, warmup_ticks=150, post_ablation_ticks=100
    ),
}


# --- Protocolos --------------------------------------------------------------------------------


def _first_k(series: Sequence[float], condition: Callable[[float], bool]) -> int | None:
    """Menor `k >= 1` (k-ésimo tick tras la perturbación) que cumple `condition`."""
    return next((k for k, value in enumerate(series, start=1) if condition(value)), None)


def _require_fraction(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:  # también rechaza NaN
        raise ValueError(f"{name} debe estar en [0, 1], recibido {value}")


def _require_positive(**durations: int) -> None:
    for name, value in durations.items():
        if value < 1:
            raise ValueError(f"{name} debe ser >= 1, recibido {value}")


def _run_001a(
    config: SimulationConfig, total_ticks: int
) -> tuple[SurplusReport, list[TickMetrics], list[TickMetrics]]:
    _require_positive(total_ticks=total_ticks)
    collective = SimulationEngine(replace(config, comm_enabled=True)).run(total_ticks)
    isolated = SimulationEngine(replace(config, comm_enabled=False)).run(total_ticks)
    last_c, last_i = collective[-1], isolated[-1]
    surplus = last_c.cumulative_decision_accuracy - last_i.cumulative_decision_accuracy
    messages = sum(m.messages_per_agent for m in collective) / len(collective)
    patterns = sorted(last_c.pattern_prevalence)
    report = SurplusReport(
        collective_accuracy=last_c.cumulative_decision_accuracy,
        isolated_accuracy=last_i.cumulative_decision_accuracy,
        collective_surplus=surplus,
        collective_accessible_coverage=last_c.accessible_coverage_mean,
        isolated_accessible_coverage=last_i.accessible_coverage_mean,
        collective_coverage=last_c.collective_coverage,
        isolated_coverage=last_i.collective_coverage,
        collective_individual_coverage_mean=last_c.individual_coverage_mean,
        mean_messages_per_agent=messages,
        accuracy_gain_per_message=surplus / messages if messages else None,
        propagation_t50={p.label: propagation_time(collective, p, 0.5) for p in patterns},
        propagation_t90={p.label: propagation_time(collective, p, 0.9) for p in patterns},
    )
    return report, collective, isolated


def run_protocol_001a_surplus(config: SimulationConfig, total_ticks: int = 300) -> SurplusReport:
    """001-A: misma semilla con y sin comunicación."""
    return _run_001a(config, total_ticks)[0]


def run_protocol_001b_falsification(
    config: SimulationConfig,
    total_ticks: int = 300,
    injection_tick: int = 80,
    injection_fraction: float = 0.25,
) -> FalsificationReport:
    """001-B: rumor `(p_0, -1.0, 0.95)` plantado en `injection_tick`."""
    if not 0 <= injection_tick < total_ticks:
        raise ValueError(
            f"injection_tick debe estar en [0, total_ticks), recibido {injection_tick} "
            f"con total_ticks={total_ticks}"
        )
    _require_fraction("injection_fraction", injection_fraction)
    engine = SimulationEngine(config)
    engine.run(injection_tick)
    injected = engine.inject_false_belief(
        TARGET_PATTERN, _INJECTED_VALUE, _INJECTED_CONFIDENCE, injection_fraction
    )
    initial = engine.snapshot().pattern_false_prevalence[TARGET_PATTERN]
    after = [
        m.pattern_false_prevalence[TARGET_PATTERN] for m in engine.run(total_ticks - injection_tick)
    ]
    final = after[-1]
    return FalsificationReport(
        target_pattern=TARGET_PATTERN.label,
        injected_agents=len(injected),
        initial_injected_prevalence=initial,
        peak_false_prevalence=max([initial, *after]),
        final_false_prevalence=final,
        ticks_to_extinction=_first_k(after, lambda v: v == 0.0),
        extinguished_or_contained=final < initial,
    )


def recovery_ticks(post_history: Sequence[TickMetrics], pre_ablation_accuracy: float) -> int | None:
    """M5: menor `k` cuya ventana post-ablación `max(1, k-19)..k` alcanza el 90 % previo.

    La ventana nunca incluye ticks anteriores a la ablación. Con `pre_ablation_accuracy == 0`
    no hay referencia: el umbral 0 se alcanzaría en `k = 1` y se leería como una recuperación
    instantánea, así que devuelve `None` (no medible).
    """
    if pre_ablation_accuracy == 0:
        return None
    target = _RECOVERY_FRACTION * pre_ablation_accuracy
    for k in range(1, len(post_history) + 1):
        window = post_history[max(0, k - RECOVERY_WINDOW) : k]
        if windowed_accuracy(window) >= target:
            return k
    return None


def _ablation_point(
    config: SimulationConfig, fraction: float, warmup_ticks: int, post_ablation_ticks: int
) -> AblationPointResult:
    _require_positive(warmup_ticks=warmup_ticks, post_ablation_ticks=post_ablation_ticks)
    _require_fraction("ablation_fraction", fraction)
    engine = SimulationEngine(config)
    warmup = engine.run(warmup_ticks)
    pre_coverage = warmup[-1].collective_coverage
    pre_accuracy = windowed_accuracy(warmup[-RECOVERY_WINDOW:])
    engine.ablate_population(fraction)
    immediate = engine.snapshot().collective_coverage
    post = engine.run(post_ablation_ticks)
    return AblationPointResult(
        ablation_fraction=fraction,
        remaining_agents=len(engine.agents),
        pre_ablation_coverage=pre_coverage,
        immediate_post_ablation_coverage=immediate,
        final_recovered_coverage=post[-1].collective_coverage,
        retention_ratio=immediate / pre_coverage if pre_coverage else 0.0,
        pre_ablation_accuracy=pre_accuracy,
        recovery_ticks=recovery_ticks(post, pre_accuracy),
    )


@dataclass(frozen=True)
class _DiscovererResult:
    ablated_count: int
    remaining_agents: int
    post_ablation_prevalence: float
    final_prevalence: float
    persistence_ticks: int | None


def _discoverer_ablation(
    config: SimulationConfig, warmup_ticks: int, post_ablation_ticks: int
) -> _DiscovererResult:
    _require_positive(warmup_ticks=warmup_ticks, post_ablation_ticks=post_ablation_ticks)
    engine = SimulationEngine(config)
    engine.run(warmup_ticks)
    removed = engine.ablate_discoverers(TARGET_PATTERN, retire_stimulus=True)
    prevalence = engine.snapshot().pattern_prevalence[TARGET_PATTERN]
    after = [m.pattern_prevalence[TARGET_PATTERN] for m in engine.run(post_ablation_ticks)]
    return _DiscovererResult(
        ablated_count=len(removed),
        remaining_agents=len(engine.agents),
        post_ablation_prevalence=prevalence,
        final_prevalence=after[-1],
        persistence_ticks=_first_k(after, lambda v: v == 0.0),
    )


def _assemble_001c(
    points: Sequence[AblationPointResult], discoverers: _DiscovererResult
) -> ResilienceReport:
    return ResilienceReport(
        ablation_results=tuple(points),
        discoverers_ablated_count=discoverers.ablated_count,
        remaining_agents_after_discoverer_ablation=discoverers.remaining_agents,
        post_discoverer_ablation_prevalence=discoverers.post_ablation_prevalence,
        final_social_persistence_prevalence=discoverers.final_prevalence,
        social_persistence_ticks=discoverers.persistence_ticks,
    )


def run_protocol_001c_resilience(
    config: SimulationConfig,
    warmup_ticks: int = 150,
    post_ablation_ticks: int = 100,
    ablation_levels: tuple[float, ...] = ABLATION_LEVELS,
) -> ResilienceReport:
    """001-C: una corrida nueva por nivel de ablación, más la ablación de descubridores."""
    for level in ablation_levels:
        _require_fraction("ablation_levels", level)
    points = [
        _ablation_point(config, level, warmup_ticks, post_ablation_ticks)
        for level in ablation_levels
    ]
    return _assemble_001c(points, _discoverer_ablation(config, warmup_ticks, post_ablation_ticks))


# --- Serialización y agregación ----------------------------------------------------------------


def report_to_dict(report: Any) -> Any:
    """Convierte reportes a estructuras JSON: `Pattern` -> etiqueta, tuplas -> listas."""
    if dataclasses.is_dataclass(report) and not isinstance(report, type):
        return {f.name: report_to_dict(getattr(report, f.name)) for f in dataclasses.fields(report)}
    if isinstance(report, Pattern):
        return report.label
    if isinstance(report, Enum):
        return report.value
    if isinstance(report, dict):
        items = cast(dict[Any, Any], report).items()
        return {report_to_dict(k): report_to_dict(v) for k, v in items}
    if isinstance(report, tuple | list):
        return [report_to_dict(v) for v in cast(Sequence[Any], report)]
    return report


def aggregate_values(values: list[Any]) -> Any:
    present = [v for v in values if v is not None]
    if present and all(isinstance(v, bool) for v in present):
        return sum(present) / len(present)
    if present and all(isinstance(v, dict) for v in present):
        dicts = cast(list[dict[str, Any]], present)
        keys = sorted({k for d in dicts for k in d})
        return {k: aggregate_values([d.get(k) for d in dicts]) for k in keys}
    if present and all(isinstance(v, list) for v in present):
        lists = cast(list[list[Any]], present)
        width = max(len(v) for v in lists)
        return [
            aggregate_values([v[i] if i < len(v) else None for v in lists]) for i in range(width)
        ]
    if present and all(isinstance(v, str) for v in present):
        return present[0] if len(set(present)) == 1 else sorted(set(present))
    numbers = [float(v) for v in present]
    if not numbers:
        return {"mean": None, "std": None, "n": 0}
    mean = sum(numbers) / len(numbers)
    std = math.sqrt(sum((x - mean) ** 2 for x in numbers) / len(numbers))
    return {"mean": mean, "std": std, "n": len(numbers)}


def aggregate_reports(reports: Sequence[Any]) -> dict[str, Any]:
    """Media, desvío (`ddof=0`) y `n` por campo numérico; fracción de `True` por campo `bool`.

    Los diccionarios y las secuencias de resultados se agregan por clave o posición; `None`
    se excluye. Para 001-A agrega `surplus_sign_test_p`.
    """
    dicts = [cast(dict[str, Any], report_to_dict(r)) for r in reports]
    fields = list(dicts[0]) if dicts else []
    result = {name: aggregate_values([d[name] for d in dicts]) for name in fields}
    if reports and all(isinstance(r, SurplusReport) for r in reports):
        surplus = cast(Sequence[SurplusReport], reports)
        result["surplus_sign_test_p"] = sign_test_p_value([r.collective_surplus for r in surplus])
    return result


def sign_test_p_value(differences: Sequence[float]) -> float:
    """Prueba de signo unilateral (H1: diferencia > 0), descartando ceros."""
    nonzero = [d for d in differences if d != 0]
    n = len(nonzero)
    if n == 0:
        return 1.0
    positives = sum(1 for d in nonzero if d > 0)
    return sum(math.comb(n, i) for i in range(positives, n + 1)) / 2**n


# --- Ejecución multi-semilla -------------------------------------------------------------------

Task = tuple[int, str, float | None]  # (semilla, unidad de trabajo, nivel de ablación)


def _execute(config: SimulationConfig, profile: Profile, task: Task) -> Any:
    """Unidad independiente de trabajo: función pura de su configuración."""
    _, kind, level = task
    if kind == "001a":
        return _run_001a(config, profile.total_ticks)
    if kind == "001b":
        return run_protocol_001b_falsification(config, profile.total_ticks, profile.injection_tick)
    if kind == "001c":
        if level is None:
            raise ValueError(f"la unidad 001c exige un nivel de ablación: {task}")
        return _ablation_point(config, level, profile.warmup_ticks, profile.post_ablation_ticks)
    if kind == "discoverers":
        return _discoverer_ablation(config, profile.warmup_ticks, profile.post_ablation_ticks)
    raise ValueError(f"unidad de trabajo desconocida: {task}")


def _execute_task(args: tuple[SimulationConfig, Profile, Task]) -> Any:
    return _execute(*args)


def validate_seeds(seeds: Sequence[int]) -> None:
    """Al menos una y sin repetir: una repetida es la misma corrida e infla `n`.

    La regla de dominio `seed >= 0` vive en `SimulationConfig`; la CLI la repite en el tipo de
    `--seeds` sólo para responder con un error de argumento (código 2).
    """
    if not seeds:
        raise ValueError("se necesita al menos una semilla")
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"semillas repetidas: {list(seeds)}")


def map_in_order(function: Callable[[Any], Any], items: Sequence[Any], jobs: int) -> list[Any]:
    """`map` reproducible (Decisión 18): sin procesos con `jobs <= 1`; si no, en un pool.

    `pool.map` conserva el orden de `items`, así que la salida no depende de `jobs`.
    """
    jobs = min(jobs, len(items))
    if jobs <= 1:
        return [function(item) for item in items]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(function, items))


def run_tasks(
    jobs_args: list[tuple[SimulationConfig, Profile, Task]], jobs: int
) -> dict[Task, Any]:
    """Ejecuta las unidades independientes y reúne los resultados por clave, en orden fijo."""
    results = map_in_order(_execute_task, jobs_args, jobs)
    return {args[2]: result for args, result in zip(jobs_args, results, strict=True)}


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_timeseries(
    path: Path, collective: list[TickMetrics], isolated: list[TickMetrics]
) -> None:
    scalars = [
        f.name
        for f in dataclasses.fields(TickMetrics)
        if f.name not in ("pattern_prevalence", "pattern_false_prevalence")
    ]
    patterns = sorted(collective[0].pattern_prevalence) if collective else []
    header = (
        ["mode", *scalars]
        + [f"prevalence[{p.label}]" for p in patterns]
        + [f"false_prevalence[{p.label}]" for p in patterns]
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        for mode, history in (("collective", collective), ("isolated", isolated)):
            for m in history:
                writer.writerow(
                    [mode, *(getattr(m, name) for name in scalars)]
                    + [m.pattern_prevalence[p] for p in patterns]
                    + [m.pattern_false_prevalence[p] for p in patterns]
                )


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"se esperaba un entero, recibido {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"debe ser >= 1, recibido {value}")
    return value


def non_negative_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"se esperaba un entero, recibido {text!r}") from None
    if value < 0:
        raise argparse.ArgumentTypeError(f"debe ser >= 0, recibido {value}")
    return value


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Experimento 001: protocolos 001-A, 001-B y 001-C")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="full")
    parser.add_argument("--seeds", type=non_negative_int, nargs="+", default=[42])
    parser.add_argument("--out", type=Path, default=Path("results/"))
    parser.add_argument("--jobs", type=positive_int, default=1)
    parser.add_argument(
        "--attribution",
        action="store_true",
        help="ejecuta sólo 001-D, siempre con el perfil pre-registrado",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    profile_name: str = args.profile
    seeds: list[int] = args.seeds
    out: Path = args.out
    jobs: int = args.jobs
    try:
        validate_seeds(seeds)
    except ValueError as error:
        parser.error(f"--seeds: {error}")
    try:  # antes de calcular: un --out inválido falla ya
        out.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        parser.error(f"--out no es un directorio utilizable ({out}): {error}")
    if args.attribution:  # 001-D ignora --profile: usa siempre el perfil pre-registrado
        return _main_attribution(seeds, out, jobs)

    profile = PROFILES[profile_name]
    configs = {seed: SimulationConfig(seed=seed) for seed in seeds}

    tasks: list[Task] = []
    for seed in seeds:
        tasks += [(seed, "001a", None), (seed, "001b", None)]
        tasks += [(seed, "001c", level) for level in ABLATION_LEVELS]
        tasks.append((seed, "discoverers", None))
    results = run_tasks([(configs[t[0]], profile, t) for t in tasks], jobs)

    per_protocol: dict[str, list[Any]] = {"001a": [], "001b": [], "001c": []}
    for seed in seeds:
        surplus, collective, isolated = results[(seed, "001a", None)]
        falsification = results[(seed, "001b", None)]
        resilience = _assemble_001c(
            [results[(seed, "001c", level)] for level in ABLATION_LEVELS],
            results[(seed, "discoverers", None)],
        )
        reports = {"001a": surplus, "001b": falsification, "001c": resilience}
        for key, report in reports.items():
            per_protocol[key].append(report)
        write_json(
            out / f"exp001_seed{seed}.json",
            {
                "config": configs[seed].to_dict(),
                "profile": profile_name,
                **{f"protocol_{key}": report_to_dict(r) for key, r in reports.items()},
            },
        )
        _write_timeseries(out / f"exp001a_seed{seed}_timeseries.csv", collective, isolated)
        print(
            f"semilla {seed}: superávit {surplus.collective_surplus:+.4f} | "
            f"rumor final {falsification.final_false_prevalence:.3f} "
            f"(inicial {falsification.initial_injected_prevalence:.3f}) | "
            f"persistencia social {resilience.final_social_persistence_prevalence:.3f}"
        )
    if len(seeds) > 1:
        aggregate: dict[str, Any] = {"seeds": seeds, "profile": profile_name}
        for key, reports_list in per_protocol.items():
            aggregate[f"protocol_{key}"] = aggregate_reports(reports_list)
        write_json(out / "exp001_aggregate.json", aggregate)
        p_value = aggregate["protocol_001a"]["surplus_sign_test_p"]
        print(f"prueba de signo del superávit ({len(seeds)} semillas): p = {p_value:.5f}")
    return 0


def _main_attribution(seeds: list[int], out: Path, jobs: int) -> int:
    """001-D desde la CLI: perfil pre-registrado, JSON y tabla de estados en consola."""
    # Importación diferida: `attribution` depende de este módulo.
    from ide.experiments.attribution import (
        ATTRIBUTION_PROFILE,
        MIN_SEEDS,
        run_protocol_001d_attribution,
    )

    print(
        f"Atribución 001-D con el perfil {ATTRIBUTION_PROFILE} (pre-registrado; ignora --profile)"
    )
    if len(seeds) < MIN_SEEDS:
        print(
            f"Aviso: con menos de {MIN_SEEDS} semillas la prueba de signo no tiene potencia; "
            "todos los estados serán INSUFFICIENT_EVIDENCE."
        )
    report = run_protocol_001d_attribution(SimulationConfig(), seeds, jobs=jobs)
    write_json(out / "exp001_attribution.json", report_to_dict(report))

    def fmt(p: float | None) -> str:
        return "—" if p is None else f"{p:.5f}"

    print(
        f"{'Afirmación':<11}{'Estado':<30}{'Por construcción':<18}{'p E2':>9}{'p E3':>9}{'p E4':>9}"
    )
    for e in report.evaluations:
        print(
            f"{e.claim_id:<11}{e.status.value:<30}{('sí' if e.by_construction else 'no'):<18}"
            f"{fmt(e.p_vs_isolated):>9}{fmt(e.p_purpose_ablated_vs_isolated):>9}"
            f"{fmt(e.p_vs_null_content):>9}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
