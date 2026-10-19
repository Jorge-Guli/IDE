"""Genoma fundador, costo metabólico y herencia cultural vertical (Exp 002 v2, design D21 y D22).

No importa `micro_agent.py`: opera sobre `BoundedMemory`, `AgentGenome` y `SimulationConfig`.
"""

from dataclasses import replace

from ide.agent.memory import BoundedMemory
from ide.config import SimulationConfig
from ide.domain.types import AgentGenome, KnowledgeUnit


def genome_from_config(config: SimulationConfig) -> AgentGenome:
    """Genoma de un fundador (g = 0), tomado de la configuración."""
    return AgentGenome(
        alpha_learning=config.alpha_learning,
        gamma_social_discount=config.gamma_social_discount,
        epsilon_explore=config.epsilon_explore,
        bond_affinity=config.initial_bond_affinity,
        memory_capacity=config.memory_capacity,
        perception_radius=config.perception_radius,
        comm_radius=config.comm_radius,
    )


def compute_metabolic_cost(genome: AgentGenome, config: SimulationConfig) -> float:
    """Costo basal por tick: c_fijo + c_mem · C_max² + c_sens · (r_perc² + r_com²) (R20, R21)."""
    return (
        config.metabolic_base_cost
        + config.memory_capacity_cost * genome.memory_capacity**2
        + config.sensory_radius_cost * (genome.perception_radius**2 + genome.comm_radius**2)
    )


def transfer_cultural_heritage(
    parent_memory: BoundedMemory, child_capacity: int, tick: int, config: SimulationConfig
) -> tuple[KnowledgeUnit, ...]:
    """Testimonios parentales para el hijo (R14), con la confianza descontada por γ_gen.

    Función pura: no escribe en ninguna memoria. El motor entrega cada testimonio por
    `assimilate_testimony`, que aplica además el descuento social γ.
    """
    if child_capacity < 0:
        raise ValueError(f"child_capacity no puede ser negativo, recibido {child_capacity}")
    discount = config.inheritance_discount
    if not config.enable_cultural_inheritance or discount == 0.0:
        return ()
    ranked = sorted(
        parent_memory.all_units(),
        key=lambda u: (-parent_memory.compute_utility(u, tick), u.pattern),
    )
    return tuple(
        replace(unit, confidence=discount * unit.confidence)
        for unit in ranked[:child_capacity]
        if config.gamma_social_discount * discount * unit.confidence >= config.min_confidence
    )
