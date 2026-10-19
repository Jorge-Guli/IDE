"""Protocolos del Experimento 003 (003-A cooperación compuesta, 003-B cobertura) y su CLI.

Uso: `python -m ide.experiments.exp003_runner [--profile {full,phase2,quick}]
[--seeds 42 43 ...] [--out results/] [--jobs N] [--attribution]`. Cada protocolo parte de su
configuración congelada en `PHASE2_PROTOCOL_CONFIGS` (design D29); del perfil sólo se usa
`total_ticks`. Con `--attribution` ejecuta sólo la atribución de C7 y C8.
"""

import argparse
import sys
from collections.abc import Mapping
from dataclasses import dataclass

from ide.config import SimulationConfig
from ide.experiments.attribution import EXP003_CLAIMS, ablate, require_r18_off
from ide.experiments.metrics import holon_tick_mean, holon_ticks
from ide.experiments.phase2_cli import ProtocolSpec, require_positive_ticks, run_protocol
from ide.experiments.phase2_cli import build_arg_parser as phase2_parser
from ide.experiments.phase2_cli import main as phase2_main
from ide.simulation.engine import SimulationEngine


@dataclass(frozen=True)
class HolonicTransitionReport:
    seed: int
    total_ticks: int
    holonic_composite_completions: int
    individual_composite_completions: int
    composite_completion_surplus: float  # float(holonic - individual)
    holonic_accuracy: float
    individual_accuracy: float
    holonic_surplus: float  # holonic_accuracy - individual_accuracy
    max_holon_level: int
    peak_holonic_coverage_gain: float


@dataclass(frozen=True)
class OrthogonalizationReport:
    seed: int
    total_ticks: int
    mean_acquired_coverage: float | None  # M13 por par (tick, holón elegible); R22 activa
    mean_acquired_coverage_without_view: float | None  # misma media con R22 apagada
    coverage_advantage: float | None  # con vista - sin vista; None si alguna media es None
    mean_redundancy_reduction: float | None  # descriptiva, condición con vista
    mean_redundancy_reduction_without_view: float | None  # descriptiva, sin vista
    holon_ticks: int  # pares (tick, holón elegible) de la condición con vista
    holon_ticks_without_view: int  # lo mismo sin vista
    max_holon_level: int
    level_counts_peak: tuple[tuple[int, int], ...]  # pares (L, conteo) ordenados por L


@dataclass(frozen=True)
class HolonicSummary:
    """Resumen de una condición holónica: lo que usan los reportes de 003-A y 003-B."""

    final_accuracy: float  # M2 acumulada del último tick (sólo recursos elementales)
    composite_completions: int  # M12 acumulada al final
    max_holon_level: int  # máximo de la corrida
    peak_holonic_coverage_gain: float  # máximo de M11 en la corrida
    mean_acquired_coverage: float | None  # M13 por par (tick, holón elegible)
    mean_redundancy_reduction: float | None
    holon_ticks: int
    level_counts_peak: tuple[tuple[int, int], ...]  # por nivel, el máximo conteo de la corrida


def run_holonic_condition(config: SimulationConfig, total_ticks: int) -> HolonicSummary:
    """Corre una condición de 003 durante `total_ticks` y la resume."""
    require_positive_ticks(total_ticks)
    engine = SimulationEngine(config)
    history = engine.run(total_ticks)
    evolution = engine.evolutionary_history
    peak: dict[int, int] = {}
    for m in evolution:
        for level, count in m.holon_count_by_level:
            peak[level] = max(peak.get(level, 0), count)
    return HolonicSummary(
        final_accuracy=history[-1].cumulative_decision_accuracy,
        composite_completions=evolution[-1].composite_completions,
        max_holon_level=max(m.max_holon_level for m in evolution),
        peak_holonic_coverage_gain=max(m.holonic_coverage_gain for m in evolution),
        mean_acquired_coverage=holon_tick_mean(evolution, "acquired_coverage"),
        mean_redundancy_reduction=holon_tick_mean(evolution, "redundancy_reduction"),
        holon_ticks=holon_ticks(evolution),
        level_counts_peak=tuple(sorted(peak.items())),
    )


# --- 003-A -------------------------------------------------------------------------------------


def _conditions_003a(config: SimulationConfig) -> dict[str, SimulationConfig]:
    return {"holonic": config, "individual": ablate(config, ["R15"])}


def _assemble_003a(
    seed: int, total_ticks: int, runs: Mapping[str, HolonicSummary]
) -> HolonicTransitionReport:
    holonic, individual = runs["holonic"], runs["individual"]
    return HolonicTransitionReport(
        seed=seed,
        total_ticks=total_ticks,
        holonic_composite_completions=holonic.composite_completions,
        individual_composite_completions=individual.composite_completions,
        composite_completion_surplus=float(
            holonic.composite_completions - individual.composite_completions
        ),
        holonic_accuracy=holonic.final_accuracy,
        individual_accuracy=individual.final_accuracy,
        holonic_surplus=holonic.final_accuracy - individual.final_accuracy,
        max_holon_level=holonic.max_holon_level,
        peak_holonic_coverage_gain=holonic.peak_holonic_coverage_gain,
    )


SPEC_003A = ProtocolSpec(
    "003a",
    _conditions_003a,
    run_holonic_condition,
    _assemble_003a,
    lambda r: (
        f"003-A compuestos {r.holonic_composite_completions} frente a "
        f"{r.individual_composite_completions} (nivel máximo {r.max_holon_level})"
    ),
)


def run_protocol_003a_holonic_transition(
    config: SimulationConfig, total_ticks: int
) -> HolonicTransitionReport:
    """003-A: holones frente a individuos (sin R15) ante recursos compuestos de orden m."""
    return run_protocol(SPEC_003A, config, total_ticks)


# --- 003-B -------------------------------------------------------------------------------------


def _conditions_003b(config: SimulationConfig) -> dict[str, SimulationConfig]:
    return {"with_view": config, "without_view": ablate(config, ["R22"])}


def _assemble_003b(
    seed: int, total_ticks: int, runs: Mapping[str, HolonicSummary]
) -> OrthogonalizationReport:
    view, blind = runs["with_view"], runs["without_view"]
    with_coverage, without_coverage = view.mean_acquired_coverage, blind.mean_acquired_coverage
    return OrthogonalizationReport(
        seed=seed,
        total_ticks=total_ticks,
        mean_acquired_coverage=with_coverage,
        mean_acquired_coverage_without_view=without_coverage,
        coverage_advantage=(
            None
            if with_coverage is None or without_coverage is None
            else with_coverage - without_coverage
        ),
        mean_redundancy_reduction=view.mean_redundancy_reduction,
        mean_redundancy_reduction_without_view=blind.mean_redundancy_reduction,
        holon_ticks=view.holon_ticks,
        holon_ticks_without_view=blind.holon_ticks,
        max_holon_level=view.max_holon_level,
        level_counts_peak=view.level_counts_peak,
    )


def _format_advantage(value: float | None) -> str:
    return "sin medición" if value is None else f"{value:+.4f}"


SPEC_003B = ProtocolSpec(
    "003b",
    _conditions_003b,
    run_holonic_condition,
    _assemble_003b,
    lambda r: (
        f"003-B ventaja de cobertura {_format_advantage(r.coverage_advantage)} "
        f"({r.holon_ticks} y {r.holon_ticks_without_view} pares tick-holón)"
    ),
    validate=require_r18_off,
)


def run_protocol_003b_orthogonalization(
    config: SimulationConfig, total_ticks: int
) -> OrthogonalizationReport:
    """003-B: cobertura adquirida con y sin la vista del holón (sin R22), con R18 apagada."""
    return run_protocol(SPEC_003B, config, total_ticks)


_DESCRIPTION = "Experimento 003: protocolos 003-A (cooperación compuesta) y 003-B (cobertura)"


def build_arg_parser() -> argparse.ArgumentParser:
    return phase2_parser(_DESCRIPTION)


def main(argv: list[str] | None = None) -> int:
    return phase2_main("exp003", _DESCRIPTION, (SPEC_003A, SPEC_003B), EXP003_CLAIMS, argv)


if __name__ == "__main__":
    sys.exit(main())
