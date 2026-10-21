"""Entidades de dominio inmutables compartidas por agentes, entornos y motor."""

from dataclasses import dataclass
from enum import Enum
from itertools import pairwise
from numbers import Integral
from typing import Any


@dataclass(frozen=True, order=True)
class Pattern:
    """Rasgo observable de un recurso. Es la clave canónica de orden (Decisión 6)."""

    attributes: tuple[tuple[str, str], ...]

    @property
    def label(self) -> str:
        """Etiqueta legible: `id=p_0`; varios atributos se unen con `&`."""
        return "&".join(f"{key}={value}" for key, value in self.attributes)


# Patrón de los cadáveres de R35 (design D48.3 y precisión 77): no forma parte de los patrones del
# mundo. Vive en el dominio para que lo compartan el entorno, el motor, las métricas y el agente.
CARCASS_PATTERN = Pattern((("id", "carcass"),))


def counts_as_knowledge(pattern: Pattern) -> bool:
    """Si una creencia sobre `pattern` cuenta como conocimiento para el motor y las métricas.

    El cadáver de R35 no cuenta (D48.3, precisión 80): ni para M9 y M11 ni para el superávit de
    conocimiento de los holones. El agente lo aprende y lo usa como cualquier patrón.
    """
    return pattern != CARCASS_PATTERN


def integer_id(value: object) -> int | None:
    """`value` como identificador entero (`resource_id` o `agent_id`); `None` si no lo es.

    Acepta los enteros de Python y de NumPy (`numbers.Integral`) y rechaza `bool`. Es la única
    validación de los objetivos de `AgentAction`: la usan la grilla (`INTERACT`) y el motor
    (`SHARE` y `ATTACK`).
    """
    if isinstance(value, bool) or not isinstance(value, Integral):
        return None
    return int(value)


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
    SHARE = "SHARE"  # Fase II-B (R36, D47.1)
    ATTACK = "ATTACK"  # Fase II-B (R37, D47.1)
    SPORULATE = "SPORULATE"  # Fase II-B (R28, D47.1)


@dataclass(frozen=True)
class AgentAction:
    action_type: ActionType
    target: Any = None  # movimiento si MOVE, resource_id si INTERACT, agent_id si SHARE o ATTACK


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
    # Rasgos de la reformulación y de la ampliación (D46.7, D59.3): los valores por defecto son las
    # bases por defecto de `SimulationConfig`. Se transcriben de los destinos 0x0A-0x0C y 0x0F.
    symbiotic_commitment: float = 0.0  # R31
    recombination_propensity: float = 0.0  # R38
    comm_propensity: float = 1.0  # R32
    plasticity_rate: float = 0.0  # R40


class Behavior(Enum):
    """Conducta que el ADN puede activar (R32, D46.1). El orden es el de desempate."""

    CONSUME = "CONSUME"
    EXPLORE = "EXPLORE"
    NAVIGATE = "NAVIGATE"
    WANDER = "WANDER"
    SHARE = "SHARE"
    ATTACK = "ATTACK"
    FLEE = "FLEE"
    SPORULATE = "SPORULATE"


@dataclass(frozen=True)
class VisibleAgent:
    """Proyección de un agente que percibe el observador, sin coordenadas (D47.1)."""

    agent_id: int
    distance: int  # Chebyshev toroidal
    recommended_move: Any  # hacia el agente; None si distance == 0
    flee_move: Any  # movimiento de Moore que maximiza la distancia (desempate por MOORE_MOVES)


@dataclass(frozen=True)
class SocialPerception:
    """Percepción social de un agente en un tick (D47.1 y D47.3)."""

    adjacent: tuple[int, ...] = ()  # agentes activos a distancia <= 1, ascendentes
    weakest_adjacent: int | None = None  # de `adjacent`, el de menor (energía, agent_id)
    weaker_adjacent: bool = False  # su energía es menor que la propia
    flee_move: Any = None  # huida del más cercano con más energía que la propia
    crowded: bool = False  # agentes activos visibles >= crowding_threshold
    carcass_visible: bool = False  # algún recurso visible es un cadáver (R35)

    def __post_init__(self) -> None:
        """Exige la coherencia que fijan D47.1 y D47.3 entre los campos sobre los adyacentes.

        `adjacent` es estrictamente ascendente; `weakest_adjacent` es uno de ellos, y es `None`
        si y sólo si `adjacent` está vacío; `weaker_adjacent` exige un `weakest_adjacent`.

        Raises:
            ValueError: si la percepción es incoherente.
        """
        adjacent = self.adjacent
        if any(a >= b for a, b in pairwise(adjacent)):
            raise ValueError(f"adjacent debe ser estrictamente ascendente: {adjacent}")
        weakest = self.weakest_adjacent
        if (weakest is None) != (not adjacent) or (weakest is not None and weakest not in adjacent):
            raise ValueError(
                f"weakest_adjacent debe estar en adjacent, o ser None sin adyacentes: "
                f"{weakest} con {adjacent}"
            )
        if self.weaker_adjacent and weakest is None:
            raise ValueError("weaker_adjacent exige un weakest_adjacent")


@dataclass(frozen=True)
class SensorySignals:
    """Señales que leen los promotores `0x20`-`0x2B` de la evaluación de conducta (D46.2, D60.1).

    Los cuatro últimos campos son los eventos del tick anterior (`EventSignals`, D58.5).
    """

    known_good: bool
    unknown: bool
    no_resource: bool
    neighbor_adjacent: bool
    weaker_adjacent: bool
    stronger_near: bool
    crowded: bool
    carcass: bool
    attacked: bool
    ate: bool
    lost_energy: bool
    received_energy: bool


@dataclass(frozen=True)
class EventSignals:
    """Eventos del tick anterior de un agente, que leen los promotores `0x28`-`0x2B` (D58.5)."""

    attacked: bool = False  # fue objetivo de un ataque con éxito y `stolen > 0`
    ate: bool = False  # consumió un recurso con valor experimentado positivo
    lost_energy: bool = False  # su energía al final del tick fue menor que al principio
    received_energy: bool = False  # fue objetivo de un `SHARE` que lo alcanzó


@dataclass(frozen=True)
class BehaviorEvaluation:
    """Resultado de `evaluate_behavior` (D60.1): impulsos, estado interno, señales y plasticidad."""

    drives: tuple[float, ...]  # uno por `Behavior`, en el orden del enumerado
    set_mask: int  # bits de `internal_state` a encender (D58.3)
    clear_mask: int  # bits de `internal_state` a apagar (D58.3)
    emitted: int  # máscara de símbolos emitidos (D60.3)
    plastic: tuple[tuple[int, ...], ...]  # codones plásticos activos por conducta (D59.4)
