"""Genoma fundador, costo metabólico y herencia cultural vertical (Exp 002 v2, design D21 y D22).

En la Fase II-B suma el costo del ADN compacto (R24, design D34.5), la senescencia telomérica
(R29) y la escala de mutación SOS (R30) (design D39).

No importa `micro_agent.py`: opera sobre `BoundedMemory`, `AgentGenome` y `SimulationConfig`.
"""

from dataclasses import replace

from ide.agent.memory import BoundedMemory
from ide.config import ENERGY_THRESHOLD_TOLERANCE, SimulationConfig
from ide.domain.types import AgentGenome, CompactDNA, KnowledgeUnit


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


def compute_dna_cost(dna: CompactDNA | None, config: SimulationConfig) -> float:
    """Costo del ADN por tick (R24, design D34.5): `dna_codon_cost` por codón; 0 sin ADN.

    Cuenta los codones del cromosoma, de los plásmidos y de la memoria CRISPR.
    """
    if dna is None:
        return 0.0
    codons = len(dna.chromosome) + len(dna.plasmids) + len(dna.crispr_memory)
    return config.dna_codon_cost * codons


def compute_senescence_cost(age: int, lifespan: int, config: SimulationConfig) -> float:
    """Costo de senescencia telomérica por tick (R29, design D39).

    Devuelve `senescence_cost_rate * (age - lifespan) ** 2` si `enable_telomere_senescence` y
    `age > lifespan`, y `0.0` en otro caso. `age` es `tick - birth_tick` y `lifespan` la
    longevidad expresada (`phenotype.lifespan`).
    """
    if not config.enable_telomere_senescence or age <= lifespan:
        return 0.0
    return config.senescence_cost_rate * (age - lifespan) ** 2


def sos_mutation_active(config: SimulationConfig) -> bool:
    """R30 efectivamente activa: `enable_sos_mutation` con evolución (D30.3, D39).

    Es la única definición de la condición: con ella `compute_sos_scale` deja de devolver 1.0 y
    `build_systems` agrega `StressSystem`, el único que registra `last_stress_tick`. Sin
    evolución la bandera es inerte.
    """
    return config.enable_evolution and config.enable_sos_mutation


def compute_sos_scale(
    energy: float, last_stress_tick: int | None, tick: int, config: SimulationConfig
) -> float:
    """Escala de mutación SOS del progenitor (R30, design D39); 1.0 sin `sos_mutation_active`.

    Se decide con el estado del progenitor antes de partir la energía: `sos_hypermutation_factor`
    si registró estrés en los últimos `sos_window` ticks; si no, `sos_high_fidelity_factor` si
    `energy >= sos_high_fidelity_energy_ratio * reproduction_threshold` (con tolerancia
    `ENERGY_THRESHOLD_TOLERANCE`, precisión 93); y si no, 1.0.
    """
    if not sos_mutation_active(config):
        return 1.0
    if last_stress_tick is not None and tick - last_stress_tick <= config.sos_window:
        return config.sos_hypermutation_factor
    high_fidelity = config.sos_high_fidelity_energy_ratio * config.reproduction_threshold
    if energy >= high_fidelity - ENERGY_THRESHOLD_TOLERANCE:
        return config.sos_high_fidelity_factor
    return 1.0


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
