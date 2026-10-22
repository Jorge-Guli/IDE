"""Compuerta de viabilidad de la Fase II-B (design D55), antes de cualquier afirmación.

Procedimiento declarado de antemano, puramente demográfico: nunca calcula ni mira las métricas
de C13 a C20.

- Parámetros: `(resources_per_pattern, resource_regen_delay)`, la abundancia del entorno; no se
  toca ningún otro campo de los protocolos de D56 (`attribution.phase25_protocol_configs`).
- Grilla cerrada `VIABILITY_GRID`, de menos a más abundancia. Se elige la primera configuración
  viable y la evaluación se detiene ahí; si ninguna lo es, no se elige nada y decide el
  responsable del proyecto (D55.5): no se prueba nada fuera de la grilla.
- Semillas `PHASE25_VIABILITY_SEEDS` (0 a 9), disjuntas de `PHASE25_SEEDS`; la define
  `attribution.py` y este módulo la reexporta (precisión 118).
- Una corrida dura el perfil `phase25` (5000 ticks) y es viable si termina con al menos una hoja
  viva que no está en endospora y `max_generation >= 20`. Una configuración es viable si cada
  condición de `DECIDING_CONDITIONS` de cada protocolo tiene al menos 9 de 10 semillas viables.
  `null_content` se corre y se registra, pero no decide: sólo informa si E4 es interpretable.
- `--jobs` usa por defecto los núcleos detectados (D62.3 y precisión 55); la salida es idéntica
  para cualquier `--jobs`.
- `--ticks` es sólo para pruebas: con otra duración que la del perfil la corrida no es la
  compuerta pre-registrada, lo dice en consola y en el JSON, no anuncia una configuración elegida
  y exige un `--out` explícito, distinto del predeterminado.

Enmienda 2 de D55 (2026-10-22, decisión del responsable del proyecto, antes de correrla): con la
grilla original ninguna configuración fue viable. `--amendment2` recorre, con el mismo criterio,
las mismas semillas y el mismo perfil, la grilla extendida `AMENDMENT2_GRID`, de menos a más
abundancia, y se detiene en la primera viable. Si tampoco la hay, la salida de respaldo fijada de
antemano elige, entre las diez configuraciones (la grilla original, leída de su JSON con
`--original`, y la extendida), la de más semillas viables sumadas sobre las condiciones que deciden;
el empate lo gana la de menos abundancia, en el orden de las dos grillas. Sigue siendo sólo
demografía.

Uso: `python -m ide.experiments.phase25_viability [--jobs N] [--ticks T] [--out archivo.json]`
y `python -m ide.experiments.phase25_viability --amendment2 [--original archivo.json] [...]`.
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ide.config import SimulationConfig
from ide.experiments import attribution
from ide.experiments.attribution import (
    NULL_CONTENT,
    PHASE25_ATTRIBUTION_PROFILE,
    PHASE25_VIABILITY_SEEDS,
    final_demography,
    phase25_conditions,
)
from ide.experiments.exp001_runner import (
    PROFILES,
    default_jobs,
    map_in_order,
    positive_int,
    validate_seeds,
    write_json,
)
from ide.simulation.engine import SimulationEngine

__all__ = [
    "AMENDMENT2_DEFAULT_OUT",
    "AMENDMENT2_GRID",
    "DECIDING_CONDITIONS",
    "DEFAULT_OUT",
    "MIN_GENERATION",
    "MIN_VIABLE_SEEDS",
    "NOT_PREREGISTERED",
    "ORIGINAL_RECORD",
    "PHASE25_VIABILITY_SEEDS",
    "PREREGISTERED_TICKS",
    "VIABILITY_GRID",
    "Amendment2Report",
    "ConfigurationResult",
    "ViabilityReport",
    "ViabilityRun",
    "amendment2_to_json",
    "build_arg_parser",
    "check_original",
    "deciding_viable_seeds",
    "default_jobs",
    "demography",
    "fallback_configuration",
    "is_viable_configuration",
    "main",
    "report_from_json",
    "report_to_json",
    "run_amendment2",
    "run_viability",
    "viability_conditions",
]

# `(resources_per_pattern, resource_regen_delay)`, en el orden de preferencia de D55.4.
VIABILITY_GRID: tuple[tuple[int, int], ...] = (
    (20, 20),
    (20, 10),
    (30, 20),
    (30, 10),
    (40, 40),
    (40, 20),
)
# Enmienda 2 de D55: grilla extendida, de menos a más abundancia; se recorre después de la original.
AMENDMENT2_GRID: tuple[tuple[int, int], ...] = (
    (60, 20),
    (60, 10),
    (80, 20),
    (80, 10),
)
MIN_VIABLE_SEEDS = 9  # de las 10 semillas, por condición (D55.3)
MIN_GENERATION = 20
# Condiciones que deciden la viabilidad; `null_content` no está (D55.3).
DECIDING_CONDITIONS: tuple[str, ...] = (
    "full",
    "drift",
    "no_predation",
    "no_predation_drift",
    "stable",
    "stable_drift",
    "no_learning",
)
PREREGISTERED_TICKS = PROFILES[PHASE25_ATTRIBUTION_PROFILE].total_ticks  # 5000 (D55.3)
DEFAULT_OUT = Path("results/phase25_viability.json")
ORIGINAL_RECORD = Path("registros/phase25_viability.json")  # la compuerta original corrida (D55)
AMENDMENT2_DEFAULT_OUT = Path("results/phase25_viability_enmienda2.json")
NOT_PREREGISTERED = "no es la compuerta pre-registrada"
_PROTOCOLS = ("25a", "25b", "25c", "25d")


def viability_conditions(
    configs: Mapping[str, SimulationConfig],
) -> list[tuple[str, str, SimulationConfig]]:
    """(protocolo, condición, configuración) de los cuatro protocolos de D56, en orden fijo."""
    if sorted(configs) != list(_PROTOCOLS):
        raise ValueError(f"se esperaban los protocolos {_PROTOCOLS}: {sorted(configs)}")
    return [
        (protocol, name, config)
        for protocol in _PROTOCOLS
        for name, config in phase25_conditions(protocol, configs[protocol]).items()
    ]


# Las (protocolo, condición) de la compuerta, en orden; no dependen de la abundancia.
_LABELS: tuple[tuple[str, str], ...] = tuple(
    (protocol, name)
    for protocol, name, _ in viability_conditions(attribution.PHASE25_PROTOCOL_CONFIGS)
)


@dataclass(frozen=True)
class ViabilityRun:
    """Sólo demografía de una corrida: población final, hojas activas y generación máxima."""

    protocol: str
    condition: str
    seed: int
    final_agents: int
    final_active_agents: int  # hojas vivas que no están en endospora
    max_generation: int

    @property
    def termination(self) -> str:
        return "alive" if self.final_agents > 0 else "extinct"

    @property
    def viable(self) -> bool:
        return self.final_active_agents > 0 and self.max_generation >= MIN_GENERATION


def _viable_counts(runs: Sequence[ViabilityRun]) -> Counter[tuple[str, str]]:
    """Semillas viables por (protocolo, condición)."""
    return Counter((r.protocol, r.condition) for r in runs if r.viable)


def deciding_viable_seeds(runs: Sequence[ViabilityRun]) -> int:
    """Semillas viables sumadas sobre las (protocolo, condición) que deciden (Enmienda 2)."""
    counts = _viable_counts(runs)
    return sum(counts[label] for label in _LABELS if label[1] in DECIDING_CONDITIONS)


def is_viable_configuration(runs: Sequence[ViabilityRun]) -> bool:
    """Cada condición que decide, de cada protocolo, con al menos `MIN_VIABLE_SEEDS` viables."""
    counts = _viable_counts(runs)
    return all(
        counts[label] >= MIN_VIABLE_SEEDS for label in _LABELS if label[1] in DECIDING_CONDITIONS
    )


@dataclass(frozen=True)
class ConfigurationResult:
    abundance: tuple[int, int]  # (resources_per_pattern, resource_regen_delay)
    viable: bool
    runs: tuple[ViabilityRun, ...]  # en el orden de (protocolo, condición, semilla)


@dataclass(frozen=True)
class ViabilityReport:
    total_ticks: int
    seeds: tuple[int, ...]
    configurations: tuple[ConfigurationResult, ...]  # las evaluadas, en el orden de la grilla
    chosen: tuple[int, int] | None  # primera configuración viable; None si ninguna lo es
    # Semillas viables de `null_content` por protocolo en la elegida (para E4); None sin elegida.
    null_content_viable_seeds: dict[str, int] | None
    grid: tuple[tuple[int, int], ...] = VIABILITY_GRID  # la grilla recorrida, en su orden

    @property
    def preregistered(self) -> bool:
        """Perfil `phase25` y semillas `PHASE25_VIABILITY_SEEDS`: la compuerta de D55."""
        return (
            self.total_ticks == PREREGISTERED_TICKS
            and self.seeds == attribution.PHASE25_VIABILITY_SEEDS
        )


def demography(task: tuple[SimulationConfig, int]) -> tuple[int, int, int]:
    """(hojas vivas, hojas activas, generación máxima) al final de la corrida."""
    config, total_ticks = task
    engine = SimulationEngine(config)
    engine.run(total_ticks)
    return final_demography(engine)


def run_viability(
    total_ticks: int | None = None,
    jobs: int = 1,
    seeds: Sequence[int] | None = None,
    grid: Sequence[tuple[int, int]] = VIABILITY_GRID,
) -> ViabilityReport:
    """Evalúa `grid` (por defecto, `VIABILITY_GRID`) en orden y se detiene en la primera viable."""
    ticks = PREREGISTERED_TICKS if total_ticks is None else total_ticks
    seeds = tuple(PHASE25_VIABILITY_SEEDS if seeds is None else seeds)
    validate_seeds(seeds)  # una semilla repetida es la misma corrida e infla el conteo
    grid = tuple(grid)
    if not grid or len(set(grid)) != len(grid):
        raise ValueError(f"la grilla debe ser no vacía y sin repetidos: {list(grid)}")
    evaluated: list[ConfigurationResult] = []
    for abundance in grid:
        configs = attribution.phase25_protocol_configs(*abundance)
        planned = {
            (protocol, name, seed): replace(config, seed=seed)
            for protocol, name, config in viability_conditions(configs)
            for seed in seeds
        }
        # Configuraciones idénticas (p. ej., `stable` de 25d y `full` de 25a) corren una vez.
        tasks = list(dict.fromkeys((config, ticks) for config in planned.values()))
        results = dict(zip(tasks, map_in_order(demography, tasks, jobs), strict=True))
        runs = tuple(
            ViabilityRun(protocol, name, seed, *results[(config, ticks)])
            for (protocol, name, seed), config in planned.items()
        )
        viable = is_viable_configuration(runs)
        evaluated.append(ConfigurationResult(abundance, viable, runs))
        if viable:
            nulls = _null_seeds(runs)
            return ViabilityReport(ticks, seeds, tuple(evaluated), abundance, nulls, grid)
    return ViabilityReport(ticks, seeds, tuple(evaluated), None, None, grid)


def _null_seeds(runs: Sequence[ViabilityRun]) -> dict[str, int]:
    """Semillas viables de `null_content` por protocolo (para E4)."""
    counts = _viable_counts(runs)
    return {p: counts[(p, NULL_CONTENT)] for p in _PROTOCOLS}


def fallback_configuration(results: Sequence[ConfigurationResult]) -> tuple[int, int]:
    """Salida de respaldo de la Enmienda 2: la de más semillas viables en las condiciones que
    deciden; ante un empate, la primera de `results` (el orden de las grillas: menos abundancia)."""
    return _best_total({r.abundance: deciding_viable_seeds(r.runs) for r in results})


def _best_total(totals: Mapping[tuple[int, int], int]) -> tuple[int, int]:
    """La de mayor total; ante un empate, la primera en el orden de `totals`."""
    if not totals:
        raise ValueError("la salida de respaldo necesita al menos una configuración evaluada")
    best = max(totals.values())
    return next(abundance for abundance, total in totals.items() if total == best)


@dataclass(frozen=True)
class Amendment2Report:
    """Enmienda 2 de D55: la grilla extendida y, si no hay viable, la salida de respaldo."""

    original: ViabilityReport  # la compuerta original (D55.4), sin configuración viable
    extended: ViabilityReport  # `AMENDMENT2_GRID`, detenida en la primera viable
    chosen: tuple[int, int]  # la primera viable de la extendida o, si no hay, la de respaldo
    fallback: bool  # True si `chosen` es la salida de respaldo
    # Semillas viables en las condiciones que deciden, por configuración evaluada, en el orden de
    # las grillas (original y después extendida).
    deciding_viable_seeds: dict[tuple[int, int], int]
    null_content_viable_seeds: dict[str, int]  # de `chosen` (para E4)

    @property
    def preregistered(self) -> bool:
        return self.original.preregistered and self.extended.preregistered


def check_original(original: ViabilityReport, total_ticks: int, seeds: Sequence[int]) -> None:
    """La enmienda sólo aplica sobre la compuerta original completa, sin viables y comparable."""
    if original.total_ticks != total_ticks:
        raise ValueError(
            f"la compuerta original corrió {original.total_ticks} ticks, no {total_ticks}"
        )
    if original.seeds != tuple(seeds):
        raise ValueError(f"las semillas de la original {list(original.seeds)} no son {seeds}")
    if original.chosen is not None or any(c.viable for c in original.configurations):
        raise ValueError("la compuerta original tiene una configuración viable: no hay enmienda")
    if tuple(c.abundance for c in original.configurations) != VIABILITY_GRID:
        raise ValueError("la compuerta original no recorrió completa la grilla de D55.4")


def run_amendment2(
    original: ViabilityReport,
    total_ticks: int | None = None,
    jobs: int = 1,
    seeds: Sequence[int] | None = None,
) -> Amendment2Report:
    """Recorre `AMENDMENT2_GRID` y, si ninguna es viable, aplica la salida de respaldo."""
    ticks = PREREGISTERED_TICKS if total_ticks is None else total_ticks
    seeds = tuple(PHASE25_VIABILITY_SEEDS if seeds is None else seeds)
    check_original(original, ticks, seeds)
    return _extend(original, ticks, jobs, seeds)


def _extend(
    original: ViabilityReport, ticks: int, jobs: int, seeds: tuple[int, ...]
) -> Amendment2Report:
    """`run_amendment2` sobre una original ya validada con `check_original`."""
    extended = run_viability(ticks, jobs, seeds, AMENDMENT2_GRID)
    results = (*original.configurations, *extended.configurations)
    totals = {r.abundance: deciding_viable_seeds(r.runs) for r in results}  # una sola vez
    if extended.chosen is not None:
        chosen, fallback = extended.chosen, False
    else:
        chosen, fallback = _best_total(totals), True
    runs = next(r.runs for r in results if r.abundance == chosen)
    return Amendment2Report(original, extended, chosen, fallback, totals, _null_seeds(runs))


def _abundance_dict(abundance: tuple[int, int]) -> dict[str, int]:
    return {"resources_per_pattern": abundance[0], "resource_regen_delay": abundance[1]}


def _configuration_to_json(result: ConfigurationResult) -> dict[str, Any]:
    """Sólo demografía de una configuración, por protocolo, condición y semilla."""
    counts = _viable_counts(result.runs)
    conditions = [
        {
            "protocol": protocol,
            "condition": condition,
            "decides": condition in DECIDING_CONDITIONS,
            "viable_seeds": counts[(protocol, condition)],
            "runs": [
                {
                    "seed": r.seed,
                    "termination": r.termination,
                    "final_agents": r.final_agents,
                    "final_active_agents": r.final_active_agents,
                    "max_generation": r.max_generation,
                    "viable": r.viable,
                }
                for r in result.runs
                if (r.protocol, r.condition) == (protocol, condition)
            ],
        }
        for protocol, condition in _LABELS
    ]
    return {
        **_abundance_dict(result.abundance),
        "viable": result.viable,
        "conditions": conditions,
    }


def report_to_json(report: ViabilityReport) -> dict[str, Any]:
    """JSON de la compuerta: sólo demografía por configuración, protocolo, condición y semilla."""
    configurations = [_configuration_to_json(result) for result in report.configurations]
    return {
        "preregistered": report.preregistered,
        "note": None if report.preregistered else NOT_PREREGISTERED,
        "total_ticks": report.total_ticks,
        "seeds": list(report.seeds),
        "grid": [list(point) for point in report.grid],
        "min_viable_seeds": MIN_VIABLE_SEEDS,
        "min_generation": MIN_GENERATION,
        "configurations": configurations,
        "chosen": None if report.chosen is None else _abundance_dict(report.chosen),
        "null_content_viable_seeds": report.null_content_viable_seeds,
    }


def _int(value: Any, what: str) -> int:
    """Entero estricto del JSON: ni `bool`, ni `float`, ni texto."""
    if type(value) is not int:
        raise ValueError(f"{what} debe ser un entero, no {value!r}")
    return value


def _bool(value: Any, what: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{what} debe ser booleano, no {value!r}")
    return value


def _abundance(data: Mapping[str, Any]) -> tuple[int, int]:
    return (
        _int(data["resources_per_pattern"], "resources_per_pattern"),
        _int(data["resource_regen_delay"], "resource_regen_delay"),
    )


def report_from_json(data: Mapping[str, Any]) -> ViabilityReport:
    """Reconstruye un reporte de la grilla de D55.4 escrito por `report_to_json` y verifica que
    sea coherente con el criterio: conteos, veredictos, terminación y elegida se recalculan desde
    las corridas, no se copian del JSON, y los números deben ser enteros estrictos."""
    grid = tuple((_int(a, "grid"), _int(b, "grid")) for a, b in data["grid"])
    if grid != VIABILITY_GRID:
        raise ValueError(f"la grilla del JSON no es la de D55.4: {data['grid']}")
    if (data["min_viable_seeds"], data["min_generation"]) != (MIN_VIABLE_SEEDS, MIN_GENERATION):
        raise ValueError("el JSON no usa el criterio de D55.3")
    total_ticks = _int(data["total_ticks"], "total_ticks")
    seeds = tuple(_int(seed, "seed") for seed in data["seeds"])
    validate_seeds(seeds)  # no vacías y sin repetidas
    configurations: list[ConfigurationResult] = []
    for configuration in data["configurations"]:
        labels = [(c["protocol"], c["condition"]) for c in configuration["conditions"]]
        if labels != list(_LABELS):
            raise ValueError(f"condiciones inesperadas en el JSON: {labels}")
        runs: list[ViabilityRun] = []
        for condition in configuration["conditions"]:
            label = (condition["protocol"], condition["condition"])
            for record in condition["runs"]:
                run = ViabilityRun(
                    *label,
                    _int(record["seed"], "seed"),
                    _int(record["final_agents"], "final_agents"),
                    _int(record["final_active_agents"], "final_active_agents"),
                    _int(record["max_generation"], "max_generation"),
                )
                if _bool(record["viable"], "viable") is not run.viable:
                    raise ValueError(f"el veredicto de una corrida de {label} no sigue el criterio")
                if record["termination"] != run.termination:
                    raise ValueError(f"la terminación de una corrida de {label} no es coherente")
                runs.append(run)
            batch = runs[len(runs) - len(condition["runs"]) :]
            if tuple(r.seed for r in batch) != seeds:
                raise ValueError(f"semillas inesperadas en {label}")
            if sum(r.viable for r in batch) != _int(condition["viable_seeds"], "viable_seeds"):
                raise ValueError(f"las semillas viables de {label} no coinciden con sus corridas")
        viable = is_viable_configuration(runs)
        if _bool(configuration["viable"], "viable") is not viable:
            raise ValueError("el veredicto de una configuración del JSON no sigue el criterio")
        configurations.append(ConfigurationResult(_abundance(configuration), viable, tuple(runs)))
    evaluated = tuple(c.abundance for c in configurations)
    first = next((i for i, c in enumerate(configurations) if c.viable), None)
    expected = grid if first is None else grid[: first + 1]  # en orden y hasta la primera viable
    if evaluated != expected:
        raise ValueError(f"configuraciones fuera del orden o del alcance de la grilla: {evaluated}")
    chosen = None if data["chosen"] is None else _abundance(data["chosen"])
    if chosen != (None if first is None else evaluated[first]):
        raise ValueError("la configuración elegida del JSON no es la primera viable")
    nulls = None if first is None else _null_seeds(configurations[first].runs)
    if data["null_content_viable_seeds"] != nulls:
        raise ValueError("la viabilidad de `null_content` del JSON no coincide con sus corridas")
    report = ViabilityReport(total_ticks, seeds, tuple(configurations), chosen, nulls, grid)
    if _bool(data["preregistered"], "preregistered") is not report.preregistered:
        raise ValueError("`preregistered` del JSON no es coherente con sus ticks y semillas")
    if data["note"] != (None if report.preregistered else NOT_PREREGISTERED):
        raise ValueError("la nota del JSON no es coherente con `preregistered`")
    return report


def amendment2_to_json(
    report: Amendment2Report, original_path: str, original_sha256: str
) -> dict[str, Any]:
    """JSON de la Enmienda 2: la grilla extendida evaluada (sólo demografía), la elegida, el
    archivo de la original usada (ruta y sha256 de su contenido) y, si la elegida es de la grilla
    original, su bloque de corridas por semilla."""
    extended = report.extended
    from_original = [r for r in report.original.configurations if r.abundance == report.chosen]
    return {
        "amendment": 2,
        "original": {"path": original_path, "sha256": original_sha256},
        "preregistered": report.preregistered,
        "note": None if report.preregistered else NOT_PREREGISTERED,
        "total_ticks": extended.total_ticks,
        "seeds": list(extended.seeds),
        "original_grid": [list(point) for point in VIABILITY_GRID],
        "grid": [list(point) for point in AMENDMENT2_GRID],
        "min_viable_seeds": MIN_VIABLE_SEEDS,
        "min_generation": MIN_GENERATION,
        "configurations": [_configuration_to_json(r) for r in extended.configurations],
        "deciding_viable_seeds": [
            {**_abundance_dict(abundance), "viable_seeds": total}
            for abundance, total in report.deciding_viable_seeds.items()
        ],
        "chosen": _abundance_dict(report.chosen),
        "chosen_configuration": (
            _configuration_to_json(from_original[0]) if from_original else None
        ),
        "fallback": report.fallback,
        "null_content_viable_seeds": report.null_content_viable_seeds,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compuerta de viabilidad de la Fase II-B (D55)")
    parser.add_argument(
        "--jobs", type=positive_int, default=default_jobs(), help="por defecto, los núcleos"
    )
    parser.add_argument(
        "--ticks",
        type=positive_int,
        default=None,
        help=f"sólo para pruebas: con otro valor que {PREREGISTERED_TICKS}, {NOT_PREREGISTERED}",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=f"por defecto, {DEFAULT_OUT} ({AMENDMENT2_DEFAULT_OUT} con --amendment2)",
    )
    parser.add_argument(
        "--amendment2",
        action="store_true",
        help=f"Enmienda 2 de D55: grilla extendida {list(AMENDMENT2_GRID)} y salida de respaldo",
    )
    parser.add_argument(
        "--original",
        type=Path,
        default=None,
        help=f"sólo con --amendment2: JSON de la compuerta original (por defecto, "
        f"{ORIGINAL_RECORD})",
    )
    return parser


def _print_configurations(configurations: Sequence[ConfigurationResult]) -> None:
    for result in configurations:
        counts = _viable_counts(result.runs)
        print(f"(resources_per_pattern, resource_regen_delay) = {result.abundance}:")
        for protocol, condition in _LABELS:
            batch = [r for r in result.runs if (r.protocol, r.condition) == (protocol, condition)]
            generations = " ".join(str(r.max_generation) for r in batch)
            active = sum(r.final_active_agents > 0 for r in batch)
            note = "" if condition in DECIDING_CONDITIONS else " (no decide)"
            print(
                f"  {protocol} {condition}{note}: viables {counts[(protocol, condition)]}/"
                f"{len(batch)}, con hojas activas {active}/{len(batch)}, generación máxima por "
                f"semilla: {generations}"
            )


def _print_amendment2(report: Amendment2Report) -> None:
    _print_configurations(report.extended.configurations)
    if report.fallback:
        print("Semillas viables sumadas sobre las condiciones que deciden, por configuración:")
        for abundance, total in report.deciding_viable_seeds.items():
            print(f"  {abundance}: {total}")
    if not report.preregistered:
        kind = "de respaldo" if report.fallback else "primera viable"
        print(f"Resultado de prueba ({NOT_PREREGISTERED}): configuración {kind}: {report.chosen}.")
    elif report.fallback:
        print(
            "Resultado: ninguna configuración de la grilla extendida es viable; configuración de "
            f"respaldo (Enmienda 2 de D55) (resources_per_pattern, resource_regen_delay) = "
            f"{report.chosen}"
        )
    else:
        print(
            f"Resultado: configuración elegida (resources_per_pattern, resource_regen_delay) = "
            f"{report.chosen} (Enmienda 2 de D55)"
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    ticks: int = PREREGISTERED_TICKS if args.ticks is None else args.ticks
    seeds = tuple(PHASE25_VIABILITY_SEEDS)
    if seeds != attribution.PHASE25_VIABILITY_SEEDS:  # el umbral de 9 es sobre esas 10
        parser.error(f"las semillas deben ser PHASE25_VIABILITY_SEEDS, no {list(seeds)}")
    if args.original is not None and not args.amendment2:
        parser.error("--original sólo tiene sentido con --amendment2")
    default_out = AMENDMENT2_DEFAULT_OUT if args.amendment2 else DEFAULT_OUT
    preregistered = ticks == PREREGISTERED_TICKS
    if not preregistered and (args.out is None or args.out == default_out):
        parser.error(
            f"--ticks {ticks} {NOT_PREREGISTERED}: exige un --out distinto de {default_out}"
        )
    out: Path = default_out if args.out is None else args.out
    original: ViabilityReport | None = None
    source: Path = ORIGINAL_RECORD if args.original is None else args.original
    digest = ""
    if args.amendment2:
        if out.resolve() in {source.resolve(), ORIGINAL_RECORD.resolve()}:
            parser.error(f"--out ({out}) no puede pisar la compuerta original")
        try:  # antes de calcular: una compuerta original ilegible o incomparable falla ya
            content = source.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            original = report_from_json(json.loads(content.decode("utf-8")))
            check_original(original, ticks, seeds)
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(f"--original no sirve para la Enmienda 2 ({source}): {error}")
    try:  # antes de calcular: un --out inválido falla ya
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        parser.error(f"--out no es una ruta utilizable ({out}): {error}")
    if not preregistered:
        print(f"Aviso: --ticks {ticks}; {NOT_PREREGISTERED} ({PREREGISTERED_TICKS} ticks).")
    if original is not None:
        amendment = _extend(original, ticks, args.jobs, seeds)  # ya pasó `check_original`
        write_json(out, amendment2_to_json(amendment, str(source), digest))
        _print_amendment2(amendment)
        return 0
    report = run_viability(ticks, args.jobs, seeds)
    write_json(out, report_to_json(report))
    _print_configurations(report.configurations)
    if not report.preregistered:
        found = "ninguna" if report.chosen is None else str(report.chosen)
        print(f"Resultado de prueba ({NOT_PREREGISTERED}): primera viable: {found}.")
    elif report.chosen is None:
        print("Resultado: ninguna configuración de la grilla es viable; decide el responsable.")
    else:
        print(
            f"Resultado: configuración elegida (resources_per_pattern, resource_regen_delay) = "
            f"{report.chosen}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
