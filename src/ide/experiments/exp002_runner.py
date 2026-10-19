"""Protocolos del Experimento 002 (002-A selección, 002-B herencia cultural) y su CLI.

Uso: `python -m ide.experiments.exp002_runner [--profile {full,phase2,quick}]
[--seeds 42 43 ...] [--out results/] [--jobs N] [--attribution]`. Cada protocolo parte de su
configuración congelada en `PHASE2_PROTOCOL_CONFIGS` (design D29); del perfil sólo se usa
`total_ticks`. Con `--attribution` ejecuta sólo la atribución de C5 y C6.
"""

import argparse
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ide.config import SimulationConfig
from ide.experiments.attribution import EXP002_CLAIMS, ablate
from ide.experiments.metrics import TickMetrics
from ide.experiments.phase2_cli import (
    ProtocolSpec,
    condition_demography,
    require_positive_ticks,
    run_protocol,
)
from ide.experiments.phase2_cli import build_arg_parser as phase2_parser
from ide.experiments.phase2_cli import main as phase2_main
from ide.simulation.engine import SimulationEngine

CONVERGENCE_ACCURACY = 0.70


@dataclass(frozen=True)
class AdaptationReport:
    seed: int
    total_ticks: int
    evolved_accuracy: float
    frozen_genome_accuracy: float
    drift_accuracy: float  # reproduction_mode="neutral" con mutación (control de deriva)
    adaptation_gain: float  # evolved_accuracy - frozen_genome_accuracy
    selection_gain: float  # evolved_accuracy - drift_accuracy
    final_mean_memory_capacity: float  # exploratorio: qué rasgos evolucionan
    final_mean_bond_affinity: float  # exploratorio
    evolved_max_generation: int
    evolved_mean_energy: float
    total_births: int
    total_deaths: int
    condition_demography: tuple[tuple[str, int, int], ...]  # (condición, población, generación)


@dataclass(frozen=True)
class CulturalInheritanceReport:
    seed: int
    total_ticks: int
    cultural_accuracy: float
    tabula_rasa_accuracy: float
    cultural_accuracy_surplus: float  # cultural_accuracy - tabula_rasa_accuracy
    final_offspring_social_ratio: float
    final_offspring_social_ratio_tabula_rasa: float
    social_ratio_gain: float  # final_offspring_social_ratio - ..._tabula_rasa
    cultural_convergence_tick: int | None
    tabula_rasa_convergence_tick: int | None
    condition_demography: tuple[tuple[str, int, int], ...]  # (condición, población, generación)


@dataclass(frozen=True)
class EvolutionSummary:
    """Resumen de una condición evolutiva: lo que usan los reportes de 002-A y 002-B."""

    final_accuracy: float  # M2 acumulada del último tick (sólo recursos elementales)
    final_agents: int  # población viva al final
    convergence_tick: int | None
    final_offspring_social_ratio: float  # M9 del último tick
    final_mean_memory_capacity: float  # media sobre los vivos al final (0.0 si no hay)
    final_mean_bond_affinity: float
    max_generation: int  # máximo de la corrida
    final_mean_energy: float  # M8 del último tick
    total_births: int
    total_deaths: int


def convergence_tick(history: Sequence[TickMetrics]) -> int | None:
    """Menor tick con oportunidades de decisión y precisión acumulada `>= 0.70` (D28)."""
    return next(
        (
            m.tick
            for m in history
            if m.decision_opportunities > 0
            and m.cumulative_decision_accuracy >= CONVERGENCE_ACCURACY
        ),
        None,
    )


def run_evolution_condition(config: SimulationConfig, total_ticks: int) -> EvolutionSummary:
    """Corre una condición de 002 durante `total_ticks` y la resume."""
    require_positive_ticks(total_ticks)
    engine = SimulationEngine(config)
    history = engine.run(total_ticks)
    evolution = engine.evolutionary_history
    alive = [engine.agents[aid] for aid in sorted(engine.agents)]
    count = len(alive)
    return EvolutionSummary(
        final_accuracy=history[-1].cumulative_decision_accuracy,
        final_agents=count,
        convergence_tick=convergence_tick(history),
        final_offspring_social_ratio=evolution[-1].offspring_social_ratio,
        final_mean_memory_capacity=(
            sum(a.genome.memory_capacity for a in alive) / count if count else 0.0
        ),
        final_mean_bond_affinity=(
            sum(a.genome.bond_affinity for a in alive) / count if count else 0.0
        ),
        max_generation=max(m.max_generation for m in evolution),
        final_mean_energy=evolution[-1].mean_energy,
        total_births=sum(m.births_this_tick for m in evolution),
        total_deaths=sum(m.deaths_this_tick for m in evolution),
    )


# --- 002-A -------------------------------------------------------------------------------------


def _conditions_002a(config: SimulationConfig) -> dict[str, SimulationConfig]:
    return {
        "evolved": config,
        "frozen_genome": ablate(config, ["R13"]),
        "drift": ablate(config, ["R12"]),
    }


def _assemble_002a(
    seed: int, total_ticks: int, runs: Mapping[str, EvolutionSummary]
) -> AdaptationReport:
    evolved, frozen, drift = runs["evolved"], runs["frozen_genome"], runs["drift"]
    return AdaptationReport(
        seed=seed,
        total_ticks=total_ticks,
        evolved_accuracy=evolved.final_accuracy,
        frozen_genome_accuracy=frozen.final_accuracy,
        drift_accuracy=drift.final_accuracy,
        adaptation_gain=evolved.final_accuracy - frozen.final_accuracy,
        selection_gain=evolved.final_accuracy - drift.final_accuracy,
        final_mean_memory_capacity=evolved.final_mean_memory_capacity,
        final_mean_bond_affinity=evolved.final_mean_bond_affinity,
        evolved_max_generation=evolved.max_generation,
        evolved_mean_energy=evolved.final_mean_energy,
        total_births=evolved.total_births,
        total_deaths=evolved.total_deaths,
        condition_demography=condition_demography(runs),
    )


SPEC_002A = ProtocolSpec(
    "002a",
    _conditions_002a,
    run_evolution_condition,
    _assemble_002a,
    lambda r: (
        f"002-A selección {r.selection_gain:+.4f} (adaptación {r.adaptation_gain:+.4f}, "
        f"generación máxima {r.evolved_max_generation})"
    ),
)


def run_protocol_002a_adaptation(config: SimulationConfig, total_ticks: int) -> AdaptationReport:
    """002-A: evolución frente a genoma congelado (sin R13) y frente a deriva (sin R12)."""
    return run_protocol(SPEC_002A, config, total_ticks)


# --- 002-B -------------------------------------------------------------------------------------


def _conditions_002b(config: SimulationConfig) -> dict[str, SimulationConfig]:
    return {"cultural": config, "tabula_rasa": ablate(config, ["R14"])}


def _assemble_002b(
    seed: int, total_ticks: int, runs: Mapping[str, EvolutionSummary]
) -> CulturalInheritanceReport:
    cultural, tabula = runs["cultural"], runs["tabula_rasa"]
    return CulturalInheritanceReport(
        seed=seed,
        total_ticks=total_ticks,
        cultural_accuracy=cultural.final_accuracy,
        tabula_rasa_accuracy=tabula.final_accuracy,
        cultural_accuracy_surplus=cultural.final_accuracy - tabula.final_accuracy,
        final_offspring_social_ratio=cultural.final_offspring_social_ratio,
        final_offspring_social_ratio_tabula_rasa=tabula.final_offspring_social_ratio,
        social_ratio_gain=cultural.final_offspring_social_ratio
        - tabula.final_offspring_social_ratio,
        cultural_convergence_tick=cultural.convergence_tick,
        tabula_rasa_convergence_tick=tabula.convergence_tick,
        condition_demography=condition_demography(runs),
    )


SPEC_002B = ProtocolSpec(
    "002b",
    _conditions_002b,
    run_evolution_condition,
    _assemble_002b,
    lambda r: f"002-B superávit cultural {r.cultural_accuracy_surplus:+.4f}",
)


def run_protocol_002b_cultural_inheritance(
    config: SimulationConfig, total_ticks: int
) -> CulturalInheritanceReport:
    """002-B: herencia cultural frente a tabula rasa (sin R14), con la misma semilla."""
    return run_protocol(SPEC_002B, config, total_ticks)


_DESCRIPTION = "Experimento 002: protocolos 002-A (selección) y 002-B (herencia cultural)"


def build_arg_parser() -> argparse.ArgumentParser:
    return phase2_parser(_DESCRIPTION)


def main(argv: list[str] | None = None) -> int:
    return phase2_main("exp002", _DESCRIPTION, (SPEC_002A, SPEC_002B), EXP002_CLAIMS, argv)


if __name__ == "__main__":
    sys.exit(main())
