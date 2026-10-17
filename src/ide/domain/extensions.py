"""Contratos de extensión para los Experimentos 002 a 006 (sólo contratos, sin su lógica)."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from ide.domain.types import KnowledgeUnit, Pattern


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
