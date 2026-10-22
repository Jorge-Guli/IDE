"""Protocolos de la Fase II-B (`25a`, `25b`, `25c` y `25d`, design D56) y su CLI reproducible.

Cada protocolo parte de su configuración en `PHASE25_PROTOCOL_CONFIGS` (condición `full`) y
compara las condiciones de `phase25_conditions`, todas con la misma semilla. Usa la
infraestructura de `phase2_cli.py` (`ProtocolSpec` y `run_protocol`). Tres modos:

- **Protocolos** (por defecto): corre cada protocolo con sus condiciones y semillas (por defecto
  `PHASE25_SEEDS` y el perfil `phase25`, del que sólo se usa `total_ticks`) y escribe un JSON por
  condición con el resumen de cada semilla (`Phase25ConditionSummary`). Con `--histories` escribe
  además los historiales genético y ecológico completos de cada corrida, en archivos aparte. La
  consola sólo muestra demografía.
- **Prueba de humo** (`--smoke`, D56): registra, por protocolo, condición y semilla, sólo la
  terminación, la generación máxima y la población final. No arma resúmenes ni calcula ninguna
  métrica de afirmación.
- **Atribución** (`--attribution`): `run_phase25_attribution` con las semillas (por defecto
  `PHASE25_SEEDS`) y los `rule_effects` exploratorios (por defecto `PHASE25_RULE_EFFECT_SEEDS`);
  escribe el `Phase25Report` en JSON y una tabla en consola. Usa siempre el perfil pre-registrado.

Las corridas son independientes: se reparten en `--jobs` procesos (por defecto, los núcleos
detectados; D62.3 y precisión 55) y la salida es idéntica para cualquier `--jobs`. Las
configuraciones idénticas (p. ej., `stable` de `25d` y `full` de `25a`) corren una sola vez.

Uso: `python -m ide.experiments.exp25_runner [--profile P] [--seeds 42 43 ...] [--jobs N]
[--out results/] [--histories | --smoke | --attribution [--rule-effect-seeds 42 ...]]`.
"""

import argparse
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import median
from typing import Any

from ide.config import SimulationConfig
from ide.experiments import attribution
from ide.experiments.attribution import (
    PHASE25_ATTRIBUTION_PROFILE,
    PHASE25_CLAIMS,
    PHASE25_MIN_VALID_PAIRS,
    PHASE25_RULE_EFFECT_SEEDS,
    PHASE25_SEEDS,
    Phase25ClaimEvaluation,
    Phase25Report,
    effect_threshold,
    final_demography,
    phase25_conditions,
    run_phase25_attribution,
)
from ide.experiments.exp001_runner import (
    PROFILES,
    default_jobs,
    map_in_order,
    non_negative_int,
    positive_int,
    report_to_dict,
    validate_seeds,
    write_json,
)
from ide.experiments.metrics import EcologyTickMetrics, GeneticTickMetrics
from ide.experiments.phase2_cli import ProtocolSpec, require_positive_ticks, run_protocol
from ide.simulation.engine import SimulationEngine

__all__ = [
    "PHASE25_SPECS",
    "Phase25ConditionHistories",
    "Phase25ConditionSummary",
    "Phase25ProtocolReport",
    "build_arg_parser",
    "main",
    "run_phase25_condition",
    "run_phase25_condition_histories",
    "run_phase25_protocol",
]

_PROTOCOLS = ("25a", "25b", "25c", "25d")
_NAME = "exp25"


@dataclass(frozen=True)
class Phase25ConditionSummary:
    """Resumen de una condición (spec "Resumen por Condición de los Protocolos 25a a 25d")."""

    final_accuracy: float  # M2 acumulada del último tick
    final_agents: int  # hojas vivas al final
    final_active_agents: int  # hojas vivas que no están en endospora
    max_generation: int  # máximo de la corrida
    last_genetic: GeneticTickMetrics | None  # último registro de `genetic_history`
    last_ecology: EcologyTickMetrics | None  # último registro de `ecology_history`


@dataclass(frozen=True)
class Phase25ConditionHistories:
    """Historiales genético y ecológico completos de una corrida, un registro por tick."""

    genetic_history: tuple[GeneticTickMetrics, ...]
    ecology_history: tuple[EcologyTickMetrics, ...]


@dataclass(frozen=True)
class Phase25ProtocolReport:
    protocol: str  # "25a" | "25b" | "25c" | "25d"
    seed: int
    total_ticks: int
    conditions: dict[str, Phase25ConditionSummary]  # en el orden de `phase25_conditions`


def run_phase25_condition_histories(
    config: SimulationConfig, total_ticks: int
) -> tuple[Phase25ConditionSummary, Phase25ConditionHistories]:
    """Corre una condición durante `total_ticks`: su resumen y sus historiales."""
    require_positive_ticks(total_ticks)
    engine = SimulationEngine(config)
    history = engine.run(total_ticks)
    final_agents, final_active_agents, max_generation = final_demography(engine)
    genetic, ecology = engine.genetic_history, engine.ecology_history
    summary = Phase25ConditionSummary(
        final_accuracy=history[-1].cumulative_decision_accuracy,
        final_agents=final_agents,
        final_active_agents=final_active_agents,
        max_generation=max_generation,
        last_genetic=genetic[-1] if genetic else None,
        last_ecology=ecology[-1] if ecology else None,
    )
    return summary, Phase25ConditionHistories(tuple(genetic), tuple(ecology))


def run_phase25_condition(config: SimulationConfig, total_ticks: int) -> Phase25ConditionSummary:
    """Corre una condición durante `total_ticks` y la resume."""
    return run_phase25_condition_histories(config, total_ticks)[0]


def _spec(key: str) -> ProtocolSpec:
    def conditions(config: SimulationConfig) -> dict[str, SimulationConfig]:
        return phase25_conditions(key, config)

    def assemble(
        seed: int, total_ticks: int, runs: Mapping[str, Phase25ConditionSummary]
    ) -> Phase25ProtocolReport:
        return Phase25ProtocolReport(key, seed, total_ticks, dict(runs))

    def headline(report: Phase25ProtocolReport) -> str:
        """Sólo demografía: nunca las métricas de las afirmaciones."""
        return "; ".join(
            f"{key} {name}: población {s.final_agents} (hojas activas {s.final_active_agents}), "
            f"generación máxima {s.max_generation}"
            for name, s in report.conditions.items()
        )

    return ProtocolSpec(key, conditions, run_phase25_condition, assemble, headline)


PHASE25_SPECS: tuple[ProtocolSpec, ...] = tuple(_spec(key) for key in _PROTOCOLS)
_SPECS_BY_KEY = {spec.key: spec for spec in PHASE25_SPECS}


def run_phase25_protocol(
    key: str, config: SimulationConfig, total_ticks: int
) -> Phase25ProtocolReport:
    """Corre todas las condiciones del protocolo `key` con la semilla de `config`."""
    spec = _SPECS_BY_KEY.get(key)
    if spec is None:
        raise ValueError(f"protocolo desconocido de la Fase II-B: {key}")
    return run_protocol(spec, config, total_ticks)


# --- Unidades de trabajo -----------------------------------------------------------------------

_Task = tuple[SimulationConfig, int, bool]  # (configuración, ticks, con historiales)


def _run_task(
    task: _Task,
) -> tuple[Phase25ConditionSummary, Phase25ConditionHistories | None]:
    config, total_ticks, keep_histories = task
    summary, histories = run_phase25_condition_histories(config, total_ticks)
    return summary, (histories if keep_histories else None)  # no viajan si no se piden


def _smoke_task(task: tuple[SimulationConfig, int]) -> tuple[int, int]:
    """(población final, generación máxima): sólo demografía, sin resúmenes ni métricas."""
    config, total_ticks = task
    engine = SimulationEngine(config)
    engine.run(total_ticks)
    final_agents, _, max_generation = final_demography(engine)
    return final_agents, max_generation


# --- CLI ---------------------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fase II-B: protocolos 25a, 25b, 25c y 25d (design D56)"
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default=PHASE25_ATTRIBUTION_PROFILE,
        help="sólo se usa `total_ticks` del perfil; --attribution lo ignora",
    )
    parser.add_argument("--seeds", type=non_negative_int, nargs="+", default=list(PHASE25_SEEDS))
    parser.add_argument(
        "--rule-effect-seeds",
        type=non_negative_int,
        nargs="*",
        default=list(PHASE25_RULE_EFFECT_SEEDS),
        help="semillas de los rule_effects exploratorios (sólo con --attribution)",
    )
    parser.add_argument("--out", type=Path, default=Path("results/"))
    parser.add_argument(
        "--jobs", type=positive_int, default=default_jobs(), help="por defecto, los núcleos"
    )
    parser.add_argument(
        "--histories",
        action="store_true",
        help="escribe también los historiales genético y ecológico de cada corrida",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--smoke",
        action="store_true",
        help="prueba de humo (D56): sólo terminación, generación máxima y población final",
    )
    mode.add_argument(
        "--attribution",
        action="store_true",
        help="atribución de C13-C20 con el perfil pre-registrado",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    seeds: list[int] = args.seeds
    rule_effect_seeds: list[int] = args.rule_effect_seeds
    out: Path = args.out
    jobs: int = args.jobs
    try:
        validate_seeds(seeds)
    except ValueError as error:
        parser.error(f"--seeds: {error}")
    if args.attribution and rule_effect_seeds:
        try:
            validate_seeds(rule_effect_seeds)
        except ValueError as error:
            parser.error(f"--rule-effect-seeds: {error}")
    if args.histories and (args.smoke or args.attribution):
        parser.error("--histories sólo se usa en el modo protocolos")
    configs = attribution.PHASE25_PROTOCOL_CONFIGS  # se lee aquí: los tests lo reemplazan
    try:  # antes de crear --out: un --out inválido falla ya
        out.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        parser.error(f"--out no es un directorio utilizable ({out}): {error}")
    if args.attribution:
        return _main_attribution(seeds, rule_effect_seeds, out, jobs, configs)
    profile: str = args.profile
    total_ticks = PROFILES[profile].total_ticks
    # (protocolo, condición, semilla) -> configuración, en orden fijo.
    planned: dict[tuple[str, str, int], SimulationConfig] = {
        (protocol, name, seed): config
        for protocol in _PROTOCOLS
        for seed in seeds
        for name, config in phase25_conditions(
            protocol, replace(configs[protocol], seed=seed)
        ).items()
    }
    if args.smoke:
        return _main_smoke(planned, profile, total_ticks, seeds, out, jobs)
    return _main_protocols(planned, profile, total_ticks, seeds, out, jobs, args.histories)


def _labels(planned: Mapping[tuple[str, str, int], SimulationConfig]) -> list[tuple[str, str]]:
    """(protocolo, condición) en el orden de los protocolos y de `phase25_conditions`."""
    return list(dict.fromkeys((protocol, name) for protocol, name, _ in planned))


def _main_protocols(
    planned: Mapping[tuple[str, str, int], SimulationConfig],
    profile: str,
    total_ticks: int,
    seeds: list[int],
    out: Path,
    jobs: int,
    histories: bool,
) -> int:
    tasks: list[_Task] = list(
        dict.fromkeys((config, total_ticks, histories) for config in planned.values())
    )
    results = dict(zip(tasks, map_in_order(_run_task, tasks, jobs), strict=True))

    def result(key: tuple[str, str, int]) -> Any:
        return results[(planned[key], total_ticks, histories)]

    for protocol, name in _labels(planned):
        runs: list[dict[str, Any]] = []
        for seed in seeds:
            summary, history = result((protocol, name, seed))
            runs.append(
                {
                    "seed": seed,
                    "config": planned[(protocol, name, seed)].to_dict(),
                    "summary": report_to_dict(summary),
                }
            )
            if history is not None:
                write_json(
                    out / f"{_NAME}_{protocol}_{name}_seed{seed}_histories.json",
                    {
                        "protocol": protocol,
                        "condition": name,
                        "seed": seed,
                        "total_ticks": total_ticks,
                        **report_to_dict(history),
                    },
                )
        write_json(
            out / f"{_NAME}_{protocol}_{name}.json",
            {
                "protocol": protocol,
                "condition": name,
                "profile": profile,
                "total_ticks": total_ticks,
                "seeds": seeds,
                "runs": runs,
            },
        )
    for seed in seeds:
        lines: list[str] = []
        for spec in PHASE25_SPECS:
            summaries = {
                name: result((protocol, name, s))[0]
                for (protocol, name, s) in planned
                if protocol == spec.key and s == seed
            }
            lines.append(spec.headline(spec.assemble(seed, total_ticks, summaries)))
        print(f"semilla {seed}: " + " | ".join(lines))
    return 0


def _main_smoke(
    planned: Mapping[tuple[str, str, int], SimulationConfig],
    profile: str,
    total_ticks: int,
    seeds: list[int],
    out: Path,
    jobs: int,
) -> int:
    """Prueba de humo de D56: sólo terminación, generación máxima y población final."""
    tasks = list(dict.fromkeys((config, total_ticks) for config in planned.values()))
    results = dict(zip(tasks, map_in_order(_smoke_task, tasks, jobs), strict=True))
    runs: list[dict[str, Any]] = []
    print(f"Prueba de humo de la Fase II-B: perfil {profile} ({total_ticks} ticks)")
    for protocol, name in _labels(planned):
        parts: list[str] = []
        for seed in seeds:
            final_agents, max_generation = results[(planned[(protocol, name, seed)], total_ticks)]
            termination = "alive" if final_agents > 0 else "extinct"
            runs.append(
                {
                    "protocol": protocol,
                    "condition": name,
                    "seed": seed,
                    "termination": termination,
                    "final_agents": final_agents,
                    "max_generation": max_generation,
                }
            )
            parts.append(
                f"semilla {seed} {termination}, población {final_agents}, "
                f"generación {max_generation}"
            )
        print(f"  {protocol} {name}: " + "; ".join(parts))
    write_json(
        out / f"{_NAME}_smoke.json",
        {"profile": profile, "total_ticks": total_ticks, "seeds": seeds, "runs": runs},
    )
    return 0


# --- Atribución --------------------------------------------------------------------------------


def _valid_seeds(evaluation: Phase25ClaimEvaluation, seeds: Sequence[int]) -> list[int]:
    excluded = evaluation.excluded_seeds
    return [s for s in seeds if s not in excluded]


def _threshold(evaluation: Phase25ClaimEvaluation, seeds: Sequence[int]) -> float:
    """Umbral de efecto de D56 con `M` sobre los pares válidos (precisiones 116 y 119)."""
    claim = next(c for c in PHASE25_CLAIMS if c.claim_id == evaluation.claim_id)
    valid = _valid_seeds(evaluation, seeds)
    comparison = median([evaluation.comparison_values[s] for s in valid]) if valid else 0.0
    return effect_threshold(claim, comparison)


def _demography_line(condition: str, records: Mapping[int, Mapping[str, float]]) -> str:
    seeds = sorted(records)
    active = sum(records[s]["final_active_agents"] >= 1 for s in seeds)
    generation = median([records[s]["max_generation"] for s in seeds]) if seeds else 0.0
    parents = median([records[s]["effective_parents"] for s in seeds]) if seeds else 0.0
    return (
        f"    {condition}: con hojas activas {active}/{len(seeds)}, generación máxima mediana "
        f"{generation:g}, progenitores efectivos medianos {parents:.2f}"
    )


def _main_attribution(
    seeds: list[int],
    rule_effect_seeds: list[int],
    out: Path,
    jobs: int,
    configs: Mapping[str, SimulationConfig],
) -> int:
    """Atribución de C13-C20 (D56): JSON del `Phase25Report` y tabla en consola."""
    print(
        f"Atribución de la Fase II-B con el perfil {PHASE25_ATTRIBUTION_PROFILE} "
        "(pre-registrado; ignora --profile)"
    )
    if len(seeds) < PHASE25_MIN_VALID_PAIRS:
        print(
            f"Aviso: con menos de {PHASE25_MIN_VALID_PAIRS} semillas ninguna afirmación es "
            "evaluable; todos los estados serán NOT_OBSERVED."
        )
    report: Phase25Report = run_phase25_attribution(
        seeds=seeds,
        claims=PHASE25_CLAIMS,
        jobs=jobs,
        configs=configs,
        rule_effect_seeds=rule_effect_seeds,
    )
    thresholds = {e.claim_id: _threshold(e, seeds) for e in report.evaluations}
    valid_pairs = {e.claim_id: len(_valid_seeds(e, seeds)) for e in report.evaluations}
    data = report_to_dict(report)
    data["seeds"] = seeds
    data["rule_effect_seeds"] = rule_effect_seeds
    data["thresholds"] = thresholds
    data["valid_pairs"] = valid_pairs
    data["configs"] = {key: configs[key].to_dict() for key in sorted(configs)}
    write_json(out / f"{_NAME}_attribution.json", data)

    def fmt(value: float | None) -> str:
        return "—" if value is None else f"{value:.5f}"

    print(
        f"{'Afirmación':<11}{'Estado':<14}{'p crudo':>9}{'p ajustado':>12}{'Mediana':>11}"
        f"{'Umbral':>11}{'Pares válidos':>15}{'Evaluable':>11}{'E4 interpretable':>18}"
        f"{'p E4':>9}"
    )
    for e in report.evaluations:
        print(
            f"{e.claim_id:<11}{e.status.value:<14}{fmt(e.p_value):>9}{fmt(e.p_adjusted):>12}"
            f"{e.median_difference:>11.5f}{thresholds[e.claim_id]:>11.5f}"
            f"{valid_pairs[e.claim_id]:>15}{('sí' if e.evaluable else 'no'):>11}"
            f"{('sí' if e.e4_interpretable else 'no'):>18}{fmt(e.e4_p_value):>9}"
        )
        for condition, records in e.demography.items():
            print(_demography_line(condition, records))
    print(
        "Los rule_effects son exploratorios (semillas "
        f"{rule_effect_seeds if rule_effect_seeds else 'ninguna'}) y están en el JSON."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
