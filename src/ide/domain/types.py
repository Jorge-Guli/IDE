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


class EpigeneticRole(Enum):
    """Casta epigenética de una hoja dentro de su holón (R25, D36)."""

    NONE = "NONE"
    EXPLORER = "EXPLORER"  # casta periférica (menor grado interno en el holón)
    LIBRARIAN = "LIBRARIAN"  # casta de conocimiento propio único
    NERVE = "NERVE"  # casta de enlace (mayor grado interno)


_CODON_MAX = 2**32 - 1


@dataclass(frozen=True)
class CompactDNA:
    """ADN compacto de codones de 32 bits (R24, D31).

    La longitud no se valida aquí: las cotas `dna_min_length`, `dna_max_length` y `max_plasmids`
    son de la configuración y las aplica la mutación (D35).
    """

    chromosome: tuple[int, ...]  # herencia vertical
    plasmids: tuple[int, ...] = ()  # herencia vertical y horizontal (R26)
    crispr_memory: tuple[int, ...] = ()  # firmas de plásmidos rechazados, FIFO (R27)

    def __post_init__(self) -> None:
        for name in ("chromosome", "plasmids", "crispr_memory"):
            if type(getattr(self, name)) is not tuple:
                raise TypeError(f"{name} debe ser una tupla de int")
            for codon in getattr(self, name):
                if type(codon) is not int:  # rechaza bool, float y numpy (D32)
                    raise TypeError(f"{name}: el codón {codon!r} debe ser un int de Python")
                if not 0 <= codon <= _CODON_MAX:
                    raise ValueError(f"{name}: codón {codon} fuera de [0, 2**32 - 1]")
        if not self.chromosome:
            raise ValueError("chromosome no puede estar vacío")
        if len(set(self.plasmids)) != len(self.plasmids):
            raise ValueError("plasmids no admite codones repetidos")
        if len(set(self.crispr_memory)) != len(self.crispr_memory):
            raise ValueError("crispr_memory no admite codones repetidos")


@dataclass(frozen=True)
class EpigeneticContext:
    """Contexto de expresión de una hoja (D31): sin capa Z ni estado de endospora."""

    holon_level: int = 0  # nivel del nodo raíz que contiene a la hoja; 0 si está sola
    role: EpigeneticRole = EpigeneticRole.NONE
    energy_ratio: float = 1.0  # E_i / reproduction_threshold


@dataclass(frozen=True)
class ExpressedPhenotype:
    """Fenotipo expresado por la transcripción del ADN (D33)."""

    genome: AgentGenome  # los 7 rasgos expresados
    lifespan: int  # T_max expresada (R29)
    spore_threshold: float  # E_espora expresada (R28)
    expressed_codons: int  # codones que modulan un rasgo en este contexto (telemetría)
