"""Entidades de dominio inmutables compartidas por agentes, entornos y motor."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


@dataclass(frozen=True, order=True)
class Pattern:
    """Rasgo observable de un recurso. Es la clave canónica de orden (Decisión 6)."""

    attributes: tuple[tuple[str, str], ...]

    @property
    def label(self) -> str:
        """Etiqueta legible: `id=p_0`; varios atributos se unen con `&`."""
        return "&".join(f"{key}={value}" for key, value in self.attributes)


@dataclass(frozen=True)
class KnowledgeUnit:
    """Creencia de un agente sobre un patrón. Los rangos los garantiza `epistemology.py`."""

    pattern: Pattern
    predicted_value: float  # en [-1.0, 1.0]
    confidence: float  # en [0.0, 1.0]
    evidence_count: int  # >= 1
    last_updated_tick: int  # tau
    from_direct_experience: bool


@dataclass(frozen=True)
class Resource:
    """Recurso del entorno. `true_value` nunca llega a un agente."""

    resource_id: int
    pattern: Pattern
    true_value: float


@dataclass(frozen=True)
class VisibleResource:
    """Proyección de un `Resource` que percibe el agente, sin `true_value`."""

    resource_id: int
    pattern: Pattern
    recommended_move: Any  # None si distance == 0
    distance: int
    is_reachable_now: bool  # True sii distance == 0


@dataclass(frozen=True)
class Observation:
    agent_id: int
    tick: int
    visible_resources: tuple[VisibleResource, ...]  # ordenados por (distance, resource_id)
    available_moves: tuple[Any, ...]  # orden fijo definido por el entorno
    neighbor_ids: tuple[int, ...]  # ascendentes, sin el propio agente


class MessageType(Enum):
    QUERY_PATTERN = "QUERY_PATTERN"
    QUERY_RESPONSE = "QUERY_RESPONSE"
    BROADCAST_BELIEF = "BROADCAST_BELIEF"


@dataclass(frozen=True)
class Message:
    msg_type: MessageType
    sender_id: int
    recipient_id: int | None  # None = todos los vecinos de comunicación del emisor
    pattern: Pattern
    belief: KnowledgeUnit | None = None  # obligatorio en QUERY_RESPONSE y BROADCAST_BELIEF

    def __post_init__(self) -> None:
        if self.msg_type is MessageType.QUERY_PATTERN:
            if self.belief is not None:
                raise ValueError("QUERY_PATTERN no puede transportar una creencia (belief)")
            return
        if self.belief is None:
            raise ValueError(f"{self.msg_type.value} exige una creencia (belief)")
        if self.belief.pattern != self.pattern:
            raise ValueError("belief.pattern debe coincidir con pattern")


class ActionType(Enum):
    MOVE = "MOVE"
    INTERACT = "INTERACT"
    IDLE = "IDLE"


@dataclass(frozen=True)
class AgentAction:
    action_type: ActionType
    target: Any = None  # movimiento si MOVE, resource_id si INTERACT


@dataclass(frozen=True)
class ActionResult:
    action_type: ActionType
    interacted_pattern: Pattern | None = None
    experienced_value: float | None = None


@dataclass(frozen=True)
class AgentGenome:
    """Genoma heredable (Exp 002 v2). Los valores por defecto coinciden con `SimulationConfig`.

    El genoma fundador real se construye siempre con `genome_from_config`.
    """

    alpha_learning: float = 0.40
    gamma_social_discount: float = 0.75
    epsilon_explore: float = 0.15
    bond_affinity: float = 0.60
    memory_capacity: int = 3
    perception_radius: int = 2
    comm_radius: int = 2


@dataclass(frozen=True)
class StigmergicTrace:
    """Rastro depositado en una celda (R19): signo de la experiencia e intensidad decreciente."""

    pattern: Pattern
    sign_value: float  # -1.0, 0.0 o 1.0
    intensity: float
    last_updated_tick: int


@dataclass(frozen=True)
class HolonSnapshot:
    """Vista inmutable de un nodo holónico para la telemetría (Exp 003 v2)."""

    node_id: int
    holon_level: int
    child_node_ids: tuple[int, ...]
    leaf_agent_ids: tuple[int, ...]
    effective_capacity: int
    collective_known_patterns: int
