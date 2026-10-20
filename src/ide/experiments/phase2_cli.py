"""Ejecución común de los protocolos 002 y 003 (design D28) y su CLI reproducible.

Cada protocolo se describe con un `ProtocolSpec`: sus condiciones (todas con la misma semilla),
la función que corre una condición y la que arma el reporte. Las condiciones son corridas
independientes, así que la CLI las reparte en `--jobs` procesos sin cambiar la salida.
"""

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ide.config import SimulationConfig
from ide.experiments import attribution
from ide.experiments.attribution import MIN_SEEDS, EmergenceClaim, run_phase2_attribution
from ide.experiments.exp001_runner import (
    PROFILES,
    aggregate_reports,
    aggregate_values,
    map_in_order,
    non_negative_int,
    positive_int,
    report_to_dict,
    validate_seeds,
    write_json,
)


@dataclass(frozen=True)
class ProtocolSpec:
    key: str  # "002a" | "002b" | "003a" | "003b"
    conditions: Callable[[SimulationConfig], dict[str, SimulationConfig]]  # en orden fijo
    run_condition: Callable[[SimulationConfig, int], Any]
    assemble: Callable[[int, int, Mapping[str, Any]], Any]  # (semilla, ticks, resúmenes)
    headline: Callable[[Any], str]  # resumen de una línea del reporte, para la consola
    validate: Callable[[SimulationConfig], None] = lambda _: None  # ValueError si no admite config


def condition_demography(runs: Mapping[str, Any]) -> tuple[tuple[str, int, int], ...]:
    """(condición, población final, generación máxima) de cada condición, en su orden."""
    return tuple((name, s.final_agents, s.max_generation) for name, s in runs.items())


def require_positive_ticks(total_ticks: int) -> None:
    if total_ticks < 1:
        raise ValueError(f"total_ticks debe ser >= 1, recibido {total_ticks}")


def run_protocol(spec: ProtocolSpec, config: SimulationConfig, total_ticks: int) -> Any:
    """Corre todas las condiciones del protocolo con la semilla de `config` y arma el reporte."""
    require_positive_ticks(total_ticks)
    spec.validate(config)
    summaries = {
        name: spec.run_condition(condition, total_ticks)
        for name, condition in spec.conditions(config).items()
    }
    return spec.assemble(config.seed, total_ticks, summaries)


_Task = tuple[Callable[[SimulationConfig, int], Any], SimulationConfig, int]


def _run_task(task: _Task) -> Any:
    run_condition, config, total_ticks = task
    return run_condition(config, total_ticks)


def build_arg_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default=attribution.PHASE2_ATTRIBUTION_PROFILE,
        help="sólo se usa `total_ticks` del perfil",
    )
    parser.add_argument(
        "--seeds",
        type=non_negative_int,
        nargs="+",
        default=None,
        help="por defecto, 42; con --attribution, las semillas pre-registradas (PHASE2_SEEDS)",
    )
    parser.add_argument("--out", type=Path, default=Path("results/"))
    parser.add_argument("--jobs", type=positive_int, default=1)
    parser.add_argument(
        "--attribution",
        action="store_true",
        help="ejecuta sólo la atribución de las afirmaciones, con el perfil pre-registrado",
    )
    parser.add_argument(
        "--reference",
        action="store_true",
        help="usa PHASE2_PROTOCOL_CONFIGS_ORIGINAL (referencia de la Enmienda 1 de D29)",
    )
    return parser


def _aggregate(reports: Sequence[Any]) -> dict[str, Any]:
    """`aggregate_reports`, salvo `level_counts_peak`, que se agrega por nivel.

    Un nivel que una semilla no alcanzó cuenta como 0 holones, y el número de nivel no se
    promedia: es la clave.
    """
    result = aggregate_reports(reports)
    peaks = [dict(r.level_counts_peak) for r in reports if hasattr(r, "level_counts_peak")]
    if peaks:  # pares [L, estadísticos] ordenados por L, como en cada reporte
        levels = sorted({level for peak in peaks for level in peak})
        result["level_counts_peak"] = [
            [level, aggregate_values([peak.get(level, 0) for peak in peaks])] for level in levels
        ]
    return result


def main(
    name: str,
    description: str,
    specs: Sequence[ProtocolSpec],
    claims: Sequence[EmergenceClaim],
    argv: list[str] | None = None,
) -> int:
    """CLI de un experimento de Fase II: un JSON por semilla y, con varias, uno agregado."""
    parser = build_arg_parser(description)
    args = parser.parse_args(argv)
    profile_name: str = args.profile
    out: Path = args.out
    jobs: int = args.jobs
    default_seeds = list(attribution.PHASE2_SEEDS) if args.attribution else [42]
    seeds: list[int] = args.seeds if args.seeds is not None else default_seeds
    try:
        validate_seeds(seeds)
    except ValueError as error:
        parser.error(f"--seeds: {error}")
    # Con --reference, las configuraciones previas a la Enmienda 1 y archivos con otro nombre.
    configs = (
        attribution.PHASE2_PROTOCOL_CONFIGS_ORIGINAL
        if args.reference
        else attribution.PHASE2_PROTOCOL_CONFIGS
    )
    prefix = f"{name}_reference" if args.reference else name
    bases = {
        (seed, spec.key): replace(configs[spec.key], seed=seed) for seed in seeds for spec in specs
    }
    try:  # antes de crear --out, también con --attribution: p. ej., R18 encendida en 003-B
        for spec in specs:
            spec.validate(configs[spec.key])
    except ValueError as error:
        parser.error(f"configuración inválida: {error}")
    conditions = {
        (seed, spec.key): spec.conditions(bases[(seed, spec.key)])
        for seed in seeds
        for spec in specs
    }
    try:  # antes de calcular: un --out inválido falla ya
        out.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        parser.error(f"--out no es un directorio utilizable ({out}): {error}")
    if args.attribution:  # ignora --profile: usa siempre el perfil pre-registrado
        return _main_attribution(prefix, claims, seeds, out, jobs, configs)

    total_ticks = PROFILES[profile_name].total_ticks
    tasks: dict[_Task, None] = {}  # conjunto ordenado: una condición idéntica corre una vez
    for seed in seeds:
        for spec in specs:
            for config in conditions[(seed, spec.key)].values():
                tasks[(spec.run_condition, config, total_ticks)] = None
    keys = list(tasks)
    results = dict(zip(keys, map_in_order(_run_task, keys, jobs), strict=True))

    per_protocol: dict[str, list[Any]] = {spec.key: [] for spec in specs}
    for seed in seeds:
        data: dict[str, Any] = {"profile": profile_name, "seed": seed}
        lines: list[str] = []
        for spec in specs:
            summaries = {
                condition: results[(spec.run_condition, config, total_ticks)]
                for condition, config in conditions[(seed, spec.key)].items()
            }
            report = spec.assemble(seed, total_ticks, summaries)
            per_protocol[spec.key].append(report)
            data[f"protocol_{spec.key}"] = {
                "config": bases[(seed, spec.key)].to_dict(),
                "report": report_to_dict(report),
            }
            lines.append(spec.headline(report))
        write_json(out / f"{prefix}_seed{seed}.json", data)
        print(f"semilla {seed}: " + " | ".join(lines))
    if len(seeds) > 1:
        aggregate: dict[str, Any] = {"seeds": seeds, "profile": profile_name}
        for key, reports in per_protocol.items():
            aggregate[f"protocol_{key}"] = _aggregate(reports)
        write_json(out / f"{prefix}_aggregate.json", aggregate)
    return 0


def _main_attribution(
    name: str,
    claims: Sequence[EmergenceClaim],
    seeds: list[int],
    out: Path,
    jobs: int,
    configs: Mapping[str, SimulationConfig],
) -> int:
    """Atribución de las afirmaciones del experimento: JSON y tabla de estados en consola."""
    profile = attribution.PHASE2_ATTRIBUTION_PROFILE
    print(f"Atribución de {name} con el perfil {profile} (pre-registrado; ignora --profile)")
    if len(seeds) < MIN_SEEDS:
        print(
            f"Aviso: con menos de {MIN_SEEDS} semillas la prueba de signo no tiene potencia; "
            "todos los estados serán INSUFFICIENT_EVIDENCE."
        )
    report = run_phase2_attribution(seeds, claims, jobs, configs)
    data = report_to_dict(report)
    # Las configuraciones base van en el archivo: distingue la referencia por su contenido.
    data["configs"] = {key: configs[key].to_dict() for key in sorted(configs)}
    write_json(out / f"{name}_attribution.json", data)

    def fmt(p: float | None) -> str:
        return "—" if p is None else f"{p:.5f}"

    if any(not e.e4_interpretable for e in report.evaluations):
        print(
            "Nota: E4 no interpretable (Enmienda 1b de D29): con la abundancia del perfil el "
            "control nulo se extingue; revisar la demografía de cada variante antes de leer "
            "rule_effects."
        )
    print(f"{'Afirmación':<11}{'Estado':<30}{'Por construcción':<18}{'p E2':>9}{'p E4':>9}")
    for e in report.evaluations:
        # Sólo las comparaciones de la tabla (E2 y E4): una ablación sin medición no las afecta.
        unmeasured = sorted(
            {
                s
                for variant in ("isolated", attribution.NULL_CONTENT)
                for s in e.unmeasured_seeds.get(variant, ())
            }
        )
        note = f"  sin medición: {unmeasured}" if unmeasured else ""
        print(
            f"{e.claim_id:<11}{e.status.value:<30}{('sí' if e.by_construction else 'no'):<18}"
            f"{fmt(e.p_vs_isolated):>9}{fmt(e.p_vs_null_content):>9}{note}"
        )
    return 0
