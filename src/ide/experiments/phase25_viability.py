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

Uso: `python -m ide.experiments.phase25_viability [--jobs N] [--ticks T] [--out archivo.json]`.
"""

import argparse
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
    "DECIDING_CONDITIONS",
    "DEFAULT_OUT",
    "MIN_GENERATION",
    "MIN_VIABLE_SEEDS",
    "NOT_PREREGISTERED",
    "PHASE25_VIABILITY_SEEDS",
    "PREREGISTERED_TICKS",
    "VIABILITY_GRID",
    "ConfigurationResult",
    "ViabilityReport",
    "ViabilityRun",
    "build_arg_parser",
    "default_jobs",
    "demography",
    "is_viable_configuration",
    "main",
    "report_to_json",
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
    total_ticks: int | None = None, jobs: int = 1, seeds: Sequence[int] | None = None
) -> ViabilityReport:
    """Evalúa `VIABILITY_GRID` en orden y se detiene en la primera configuración viable."""
    ticks = PREREGISTERED_TICKS if total_ticks is None else total_ticks
    seeds = tuple(PHASE25_VIABILITY_SEEDS if seeds is None else seeds)
    validate_seeds(seeds)  # una semilla repetida es la misma corrida e infla el conteo
    evaluated: list[ConfigurationResult] = []
    for abundance in VIABILITY_GRID:
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
            counts = _viable_counts(runs)
            nulls = {p: counts[(p, NULL_CONTENT)] for p in _PROTOCOLS}
            return ViabilityReport(ticks, seeds, tuple(evaluated), abundance, nulls)
    return ViabilityReport(ticks, seeds, tuple(evaluated), None, None)


def _abundance_dict(abundance: tuple[int, int]) -> dict[str, int]:
    return {"resources_per_pattern": abundance[0], "resource_regen_delay": abundance[1]}


def report_to_json(report: ViabilityReport) -> dict[str, Any]:
    """JSON de la compuerta: sólo demografía por configuración, protocolo, condición y semilla."""
    configurations: list[dict[str, Any]] = []
    for result in report.configurations:
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
        configurations.append(
            {**_abundance_dict(result.abundance), "viable": result.viable, "conditions": conditions}
        )
    return {
        "preregistered": report.preregistered,
        "note": None if report.preregistered else NOT_PREREGISTERED,
        "total_ticks": report.total_ticks,
        "seeds": list(report.seeds),
        "grid": [list(point) for point in VIABILITY_GRID],
        "min_viable_seeds": MIN_VIABLE_SEEDS,
        "min_generation": MIN_GENERATION,
        "configurations": configurations,
        "chosen": None if report.chosen is None else _abundance_dict(report.chosen),
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
    parser.add_argument("--out", type=Path, default=None, help=f"por defecto, {DEFAULT_OUT}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    ticks: int = PREREGISTERED_TICKS if args.ticks is None else args.ticks
    seeds = tuple(PHASE25_VIABILITY_SEEDS)
    if seeds != attribution.PHASE25_VIABILITY_SEEDS:  # el umbral de 9 es sobre esas 10
        parser.error(f"las semillas deben ser PHASE25_VIABILITY_SEEDS, no {list(seeds)}")
    preregistered = ticks == PREREGISTERED_TICKS
    if not preregistered and (args.out is None or args.out == DEFAULT_OUT):
        parser.error(
            f"--ticks {ticks} {NOT_PREREGISTERED}: exige un --out distinto de {DEFAULT_OUT}"
        )
    out: Path = DEFAULT_OUT if args.out is None else args.out
    try:  # antes de calcular: un --out inválido falla ya
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        parser.error(f"--out no es una ruta utilizable ({out}): {error}")
    if not preregistered:
        print(f"Aviso: --ticks {ticks}; {NOT_PREREGISTERED} ({PREREGISTERED_TICKS} ticks).")
    report = run_viability(ticks, args.jobs, seeds)
    write_json(out, report_to_json(report))
    for result in report.configurations:
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
