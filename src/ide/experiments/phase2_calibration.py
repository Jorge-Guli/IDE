"""Calibración de viabilidad del perfil de la Fase II (enmienda de design D29, 2026-10-19).

La prueba de humo de D29 mostró que, con las configuraciones congeladas, la población no llega a
varias generaciones. Este procedimiento, declarado **antes** de ejecutarlo, elige la abundancia de
recursos con un criterio puramente demográfico: nunca calcula ni mira las métricas de C5 a C8.

- Parámetro: `resources_per_pattern` (abundancia del entorno; no toca ninguna regla R12-R23).
- Grilla cerrada, en orden ascendente: 10, 20, 40, 80. Se elige el menor valor viable y la
  evaluación se detiene ahí; si ninguno lo es, no se elige nada y se consulta.
- Semillas de calibración 0 a 9, distintas de las de medición (`PHASE2_SEEDS`, 42 a 51).
- Una corrida es viable si al final del perfil `phase2` (2000 ticks) la población sigue viva y
  llegó al menos a la generación 5. Un valor es viable si en cada protocolo de
  `PHASE2_PROTOCOL_CONFIGS` al menos 8 de las 10 semillas son viables.

Uso: `python -m ide.experiments.phase2_calibration [--jobs N] [--out results/] [--ticks T]`.
"""

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from ide.config import SimulationConfig
from ide.experiments import attribution
from ide.experiments.exp001_runner import (
    PROFILES,
    map_in_order,
    positive_int,
    report_to_dict,
    write_json,
)
from ide.simulation.engine import SimulationEngine

CALIBRATION_PARAMETER = "resources_per_pattern"
CALIBRATION_GRID: tuple[int, ...] = (10, 20, 40, 80)
CALIBRATION_SEEDS: tuple[int, ...] = tuple(range(10))
MIN_VIABLE_SEEDS = 8
MIN_GENERATION = 5


@dataclass(frozen=True)
class ViabilityRun:
    """Sólo demografía: población final y generación máxima de la corrida."""

    protocol: str
    value: int
    seed: int
    final_agents: int
    max_generation: int

    @property
    def viable(self) -> bool:
        return self.final_agents > 0 and self.max_generation >= MIN_GENERATION


@dataclass(frozen=True)
class CalibrationReport:
    parameter: str
    total_ticks: int
    chosen: int | None  # menor valor viable de la grilla; None si ninguno lo es
    runs: tuple[ViabilityRun, ...]


def is_viable_value(runs: Sequence[ViabilityRun]) -> bool:
    """En cada protocolo, al menos `MIN_VIABLE_SEEDS` semillas viables."""
    return all(
        sum(r.viable for r in runs if r.protocol == protocol) >= MIN_VIABLE_SEEDS
        for protocol in sorted(attribution.PHASE2_PROTOCOL_CONFIGS)
    )


def _demography(task: tuple[SimulationConfig, int]) -> tuple[int, int]:
    config, total_ticks = task
    engine = SimulationEngine(config)
    engine.run(total_ticks)
    return len(engine.agents), max(m.max_generation for m in engine.evolutionary_history)


def run_calibration(total_ticks: int | None = None, jobs: int = 1) -> CalibrationReport:
    """Evalúa la grilla en orden ascendente y se detiene en el primer valor viable."""
    ticks = PROFILES[attribution.PHASE2_ATTRIBUTION_PROFILE].total_ticks
    ticks = ticks if total_ticks is None else total_ticks
    protocols = sorted(attribution.PHASE2_PROTOCOL_CONFIGS)
    runs: list[ViabilityRun] = []
    for value in CALIBRATION_GRID:
        planned = {
            (protocol, seed): replace(
                attribution.PHASE2_PROTOCOL_CONFIGS[protocol],
                seed=seed,
                **{CALIBRATION_PARAMETER: value},
            )
            for protocol in protocols
            for seed in CALIBRATION_SEEDS
        }
        # Configuraciones idénticas (003-A y 003-B) corren una sola vez.
        tasks = list(dict.fromkeys((config, ticks) for config in planned.values()))
        results = dict(zip(tasks, map_in_order(_demography, tasks, jobs), strict=True))
        batch = [
            ViabilityRun(protocol, value, seed, *results[(config, ticks)])
            for (protocol, seed), config in planned.items()
        ]
        runs += batch
        if is_viable_value(batch):
            return CalibrationReport(CALIBRATION_PARAMETER, ticks, value, tuple(runs))
    return CalibrationReport(CALIBRATION_PARAMETER, ticks, None, tuple(runs))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibración de viabilidad de la Fase II")
    parser.add_argument("--jobs", type=positive_int, default=1)
    parser.add_argument("--out", type=Path, default=Path("results/"))
    parser.add_argument("--ticks", type=positive_int, default=None, help="sólo para pruebas")
    args = parser.parse_args(argv)
    out: Path = args.out
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        parser.error(f"--out no es un directorio utilizable ({out}): {error}")
    report = run_calibration(args.ticks, args.jobs)
    write_json(out / "phase2_calibration.json", report_to_dict(report))
    for value in sorted({r.value for r in report.runs}):
        for protocol in sorted({r.protocol for r in report.runs}):
            batch = [r for r in report.runs if r.value == value and r.protocol == protocol]
            generations = " ".join(str(r.max_generation) for r in batch)
            alive = sum(r.final_agents > 0 for r in batch)
            print(
                f"{CALIBRATION_PARAMETER}={value} {protocol}: viables "
                f"{sum(r.viable for r in batch)}/{len(batch)}, vivas {alive}/{len(batch)}, "
                f"generación máxima por semilla: {generations}"
            )
    if report.chosen is None:
        print("Resultado: ningún valor de la grilla es viable; no se elige nada.")
    else:
        print(f"Resultado: {CALIBRATION_PARAMETER} = {report.chosen}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
