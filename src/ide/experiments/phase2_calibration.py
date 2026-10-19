"""Calibración de viabilidad del perfil de la Fase II (enmienda de design D29, 2026-10-19).

La prueba de humo de D29 mostró que, con las configuraciones congeladas, la población no llega a
varias generaciones. Este procedimiento, declarado **antes** de ejecutarlo, elige la abundancia de
recursos con un criterio puramente demográfico: nunca calcula ni mira las métricas de C5 a C8.

- Parámetro: `resources_per_pattern` (abundancia del entorno; no toca ninguna regla R12-R23).
- Grilla cerrada, en orden ascendente: 10, 20, 40, 80. Se elige el menor valor viable y la
  evaluación se detiene ahí; si ninguno lo es, no se elige nada (para esta grilla, la Enmienda
  1b de abajo fija qué sigue).
- Semillas de calibración 0 a 9, distintas de las de medición (`PHASE2_SEEDS`, 42 a 51).
- Una corrida es viable si al final del perfil `phase2` (2000 ticks) la población sigue viva y
  llegó al menos a la generación 5. Un valor es viable si al menos 8 de las 10 semillas son
  viables en cada condición de comparación (`calibration_conditions`): las de cada runner, tal
  como las declaran sus `ProtocolSpec`, y el control nulo de cada protocolo (E4). Exigirlo sólo a
  la base la dejaría en el borde de la supervivencia, y una variante más débil podría perder por
  pura demografía.
- Parte de `PHASE2_PROTOCOL_CONFIGS_ORIGINAL`, así que es reproducible después de incorporar el
  valor elegido a `PHASE2_PROTOCOL_CONFIGS`.
- Enmienda 1b: con la grilla original ningún valor fue viable (`RESULTADOS.md`). Se evalúa,
  con el mismo criterio y las mismas semillas, la grilla refinada 25, 30, 35 (`--refined`). Si
  tampoco hay un valor viable, se usa `CALIBRATION_FALLBACK = 20` y la comparación E4 de C5 a C8
  se declara no interpretable (con 20 se extingue el control nulo), regla fijada antes de esta
  corrida; el reporte la registra en `fallback`.
- La grilla refinada tampoco dio un valor viable (`RESULTADOS.md`), así que
  `PHASE2_PROTOCOL_CONFIGS` usa la salida de respaldo, 20 (`PHASE2_RESOURCES_PER_PATTERN`).

Uso: `python -m ide.experiments.phase2_calibration [--refined] [--jobs N] [--out results/]
[--ticks T]`.
"""

import argparse
import sys
from collections.abc import Mapping, Sequence
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
from ide.experiments.exp002_runner import SPEC_002A, SPEC_002B
from ide.experiments.exp003_runner import SPEC_003A, SPEC_003B
from ide.simulation.engine import SimulationEngine

CALIBRATION_PARAMETER = "resources_per_pattern"
CALIBRATION_GRID: tuple[int, ...] = (10, 20, 40, 80)
CALIBRATION_REFINED_GRID: tuple[int, ...] = (25, 30, 35)  # Enmienda 1b
# Enmienda 1b, fijado antes de correr la grilla refinada: si no da un valor viable. Es el valor
# que tomó el perfil (`PHASE2_RESOURCES_PER_PATTERN`); un test exige que coincidan.
CALIBRATION_FALLBACK = 20
CALIBRATION_SEEDS: tuple[int, ...] = tuple(range(10))
MIN_VIABLE_SEEDS = 8
MIN_GENERATION = 5


def calibration_conditions(
    configs: Mapping[str, SimulationConfig],
) -> list[tuple[str, str, SimulationConfig]]:
    """(protocolo, condición, configuración): las de cada runner y su control nulo, en orden.

    Exige un `ProtocolSpec` por protocolo de `configs` y valida cada base como el runner.
    """
    specs = (SPEC_002A, SPEC_002B, SPEC_003A, SPEC_003B)
    if sorted(spec.key for spec in specs) != sorted(configs):
        raise ValueError(f"protocolos sin condiciones de calibración: {sorted(configs)}")
    found: list[tuple[str, str, SimulationConfig]] = []
    for spec in specs:
        base = configs[spec.key]
        spec.validate(base)
        found += [(spec.key, name, config) for name, config in spec.conditions(base).items()]
        found.append((spec.key, attribution.NULL_CONTENT, attribution.null_content_variant(base)))
    return found


@dataclass(frozen=True)
class ViabilityRun:
    """Sólo demografía: población final y generación máxima de la corrida."""

    protocol: str
    condition: str  # nombre de la condición del runner, o `NULL_CONTENT`
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
    grid: tuple[int, ...]  # grilla evaluada, en orden
    chosen: int | None  # menor valor viable de la grilla; None si ninguno lo es
    runs: tuple[ViabilityRun, ...]
    # Enmienda 1b: `CALIBRATION_FALLBACK` si la grilla refinada no dio un valor viable
    fallback: int | None = None


def _labels() -> list[tuple[str, str]]:
    configs = attribution.PHASE2_PROTOCOL_CONFIGS_ORIGINAL
    return [(protocol, name) for protocol, name, _ in calibration_conditions(configs)]


def is_viable_value(runs: Sequence[ViabilityRun]) -> bool:
    """En cada condición de comparación, al menos `MIN_VIABLE_SEEDS` semillas viables."""
    return all(
        sum(r.viable for r in runs if (r.protocol, r.condition) == key) >= MIN_VIABLE_SEEDS
        for key in _labels()
    )


def _demography(task: tuple[SimulationConfig, int]) -> tuple[int, int]:
    config, total_ticks = task
    engine = SimulationEngine(config)
    engine.run(total_ticks)
    return len(engine.agents), max(m.max_generation for m in engine.evolutionary_history)


def run_calibration(
    total_ticks: int | None = None, jobs: int = 1, grid: Sequence[int] = CALIBRATION_GRID
) -> CalibrationReport:
    """Evalúa `grid` en orden ascendente y se detiene en el primer valor viable."""
    grid = tuple(grid)
    if not grid or list(grid) != sorted(set(grid)):
        raise ValueError(f"la grilla debe ser ascendente y sin repetidos: {grid}")
    ticks = PROFILES[attribution.PHASE2_ATTRIBUTION_PROFILE].total_ticks
    ticks = ticks if total_ticks is None else total_ticks
    runs: list[ViabilityRun] = []
    for value in grid:
        # Parte de las configuraciones originales: reproducible tras incorporar el valor.
        bases = {
            key: replace(config, **{CALIBRATION_PARAMETER: value})
            for key, config in attribution.PHASE2_PROTOCOL_CONFIGS_ORIGINAL.items()
        }
        planned = {
            (protocol, label, seed): replace(config, seed=seed)
            for protocol, label, config in calibration_conditions(bases)
            for seed in CALIBRATION_SEEDS
        }
        # Configuraciones idénticas (p. ej., las bases de 003-A y 003-B) corren una sola vez.
        tasks = list(dict.fromkeys((config, ticks) for config in planned.values()))
        results = dict(zip(tasks, map_in_order(_demography, tasks, jobs), strict=True))
        batch = [
            ViabilityRun(protocol, label, value, seed, *results[(config, ticks)])
            for (protocol, label, seed), config in planned.items()
        ]
        runs += batch
        if is_viable_value(batch):
            return CalibrationReport(CALIBRATION_PARAMETER, ticks, grid, value, tuple(runs))
    fallback = CALIBRATION_FALLBACK if grid == CALIBRATION_REFINED_GRID else None
    return CalibrationReport(CALIBRATION_PARAMETER, ticks, grid, None, tuple(runs), fallback)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibración de viabilidad de la Fase II")
    parser.add_argument("--jobs", type=positive_int, default=1)
    parser.add_argument("--out", type=Path, default=Path("results/"))
    parser.add_argument("--ticks", type=positive_int, default=None, help="sólo para pruebas")
    parser.add_argument(
        "--refined", action="store_true", help="grilla refinada 25, 30, 35 (Enmienda 1b)"
    )
    args = parser.parse_args(argv)
    out: Path = args.out
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        parser.error(f"--out no es un directorio utilizable ({out}): {error}")
    grid = CALIBRATION_REFINED_GRID if args.refined else CALIBRATION_GRID
    report = run_calibration(args.ticks, args.jobs, grid)
    name = "phase2_calibration_refinada.json" if args.refined else "phase2_calibration.json"
    write_json(out / name, report_to_dict(report))
    for value in sorted({r.value for r in report.runs}):
        for protocol, label in _labels():
            batch = [
                r
                for r in report.runs
                if (r.value, r.protocol, r.condition) == (value, protocol, label)
            ]
            if not batch:
                continue
            generations = " ".join(str(r.max_generation) for r in batch)
            alive = sum(r.final_agents > 0 for r in batch)
            print(
                f"{CALIBRATION_PARAMETER}={value} {protocol} {label}: viables "
                f"{sum(r.viable for r in batch)}/{len(batch)}, vivas {alive}/{len(batch)}, "
                f"generación máxima por semilla: {generations}"
            )
    if report.fallback is not None:
        print(
            f"Resultado: ningún valor de la grilla es viable; por la Enmienda 1b se usa "
            f"{CALIBRATION_PARAMETER} = {report.fallback} y E4 se declara no interpretable."
        )
    elif report.chosen is None:
        print("Resultado: ningún valor de la grilla es viable; no se elige nada.")
    else:
        print(f"Resultado: {CALIBRATION_PARAMETER} = {report.chosen}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
