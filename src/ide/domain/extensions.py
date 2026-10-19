"""Contratos de extensión para los Experimentos 002 a 006.

Fuera de `mutate_genome` y `compute_epistemic_synergy` (Fase II, design D22), son sólo contratos.
"""

from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

import numpy as np

from ide.config import SimulationConfig
from ide.domain.types import AgentGenome, KnowledgeUnit, Pattern


@runtime_checkable
class TrustStrategyPort(Protocol):
    """Confianza que un receptor deposita en un emisor (Exp 002)."""

    def compute_sender_trust(
        self, receiver_id: int, sender_id: int, base_gamma: float
    ) -> float: ...


@dataclass(frozen=True)
class UniformTrustStrategy:
    """Todos los emisores merecen el mismo descuento γ."""

    def compute_sender_trust(self, receiver_id: int, sender_id: int, base_gamma: float) -> float:
        return base_gamma


@dataclass(frozen=True)
class AgentCapabilities:
    """Perfil de capacidades plásticas (Exp 003); permanece en sus valores base en el Exp 001."""

    perception_multiplier: float = 1.0
    memory_bonus: int = 0
    comm_multiplier: float = 1.0


@dataclass(frozen=True)
class CompositeRule:
    """Regla que sólo se reconstruye con todos los fragmentos requeridos (Exp 005)."""

    required_patterns: tuple[Pattern, ...]
    composite_value: float

    def __post_init__(self) -> None:
        if len(self.required_patterns) < 2:
            raise ValueError("required_patterns debe contener al menos dos patrones")
        if len(set(self.required_patterns)) != len(self.required_patterns):
            raise ValueError("required_patterns no admite patrones repetidos")

    def evaluate(self, known_patterns: set[Pattern] | dict[Pattern, KnowledgeUnit]) -> float | None:
        """`composite_value` si se conocen todos los fragmentos; `None` si falta alguno."""
        keys = set(known_patterns.keys()) if isinstance(known_patterns, dict) else known_patterns
        if all(p in keys for p in self.required_patterns):
            return self.composite_value
        return None


@dataclass(frozen=True)
class AgentHyperParams:
    alpha_learning: float = 0.40
    gamma_social_discount: float = 0.75
    epsilon_explore: float = 0.15


@runtime_checkable
class EvolutionaryPort(Protocol):
    """Operador de reproducción con mutación (Exp 006)."""

    def reproduce_and_mutate(
        self, parent_params: AgentHyperParams, rng: np.random.Generator
    ) -> AgentHyperParams: ...


@dataclass(frozen=True)
class DefaultEvolutionaryOperator:
    """Suma ruido gaussiano a α, γ y ε y recorta a [0, 1]."""

    mutation_std: float = 0.05

    def reproduce_and_mutate(
        self, parent_params: AgentHyperParams, rng: np.random.Generator
    ) -> AgentHyperParams:
        def mutate(val: float) -> float:
            noisy = val + float(rng.normal(0.0, self.mutation_std))
            return min(1.0, max(0.0, noisy))

        return AgentHyperParams(
            alpha_learning=mutate(parent_params.alpha_learning),
            gamma_social_discount=mutate(parent_params.gamma_social_discount),
            epsilon_explore=mutate(parent_params.epsilon_explore),
        )


def _mutate_integer(value: int, lo: int, hi: int, rng: np.random.Generator) -> int:
    """Salto de ±1 recortado a [lo, hi]; si hi < lo conserva el valor parental.

    Siempre consume su extracción del signo, para que la secuencia del generador no dependa de
    los valores del genoma.
    """
    step = 1 if int(rng.integers(0, 2)) == 1 else -1
    if hi < lo:
        return value
    return min(hi, max(lo, value + step))


def mutate_genome(
    genome: AgentGenome, config: SimulationConfig, rng: np.random.Generator
) -> AgentGenome:
    """Mutación gaussiana acotada de los rasgos continuos y de ±1 de los enteros (Exp 002 v2).

    Sin mutación configurada devuelve el genoma sin consumir `rng`. El número de extracciones
    no depende de los valores del genoma, para que la secuencia del generador sea estable.
    """
    if config.mutation_rate == 0.0 and config.discrete_mutation_prob == 0.0:
        return genome
    alpha, gamma = genome.alpha_learning, genome.gamma_social_discount
    epsilon, bond = genome.epsilon_explore, genome.bond_affinity
    if config.mutation_rate > 0.0:
        noise = rng.normal(0.0, config.mutation_rate, size=4)
        alpha = min(1.0, max(0.01, alpha + float(noise[0])))
        gamma = min(1.0, max(0.0, gamma + float(noise[1])))
        epsilon = min(1.0, max(0.0, epsilon + float(noise[2])))
        bond = min(1.0, max(0.0, bond + float(noise[3])))
    capacity, perception, comm = (
        genome.memory_capacity,
        genome.perception_radius,
        genome.comm_radius,
    )
    if config.discrete_mutation_prob > 0.0:
        capacity_hi = config.max_genome_memory_capacity
        if config.enforce_memory_constraint:
            capacity_hi = min(capacity_hi, config.num_world_patterns - 1)
        radius_hi = (min(config.grid_width, config.grid_height) - 1) // 2
        bounds = ((capacity, capacity_hi), (perception, radius_hi), (comm, radius_hi))
        mutated: list[int] = []
        for value, hi in bounds:
            if float(rng.random()) < config.discrete_mutation_prob:
                value = _mutate_integer(value, 1, hi, rng)
            mutated.append(value)
        capacity, perception, comm = mutated
    return replace(
        genome,
        alpha_learning=alpha,
        gamma_social_discount=gamma,
        epsilon_explore=epsilon,
        bond_affinity=bond,
        memory_capacity=capacity,
        perception_radius=perception,
        comm_radius=comm,
    )


def compute_epistemic_synergy(
    patterns_a: frozenset[Pattern], patterns_b: frozenset[Pattern], mean_bond_affinity: float
) -> float:
    """Distancia de Jaccard entre los conocimientos, ponderada por la afinidad media (R15)."""
    union = patterns_a | patterns_b
    if not union:
        return 0.0
    return len(patterns_a ^ patterns_b) / len(union) * mean_bond_affinity
