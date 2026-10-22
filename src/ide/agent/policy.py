"""Puerto de política de acción, política escrita a mano y política genética (D45, D46).

`GeneticPolicy` (R32) decide con los impulsos que el ADN del agente asigna a cada `Behavior`
(D46.4): construye las `SensorySignals` del tick desde la observación, las creencias efectivas, la
percepción social (D47.4) y los eventos del tick anterior (D58.5), y prueba las conductas con
impulso positivo en orden de $(-d_B, \text{posición})$, con la factibilidad de D46.1 evaluada de
forma perezosa (precisión 25).
"""

from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, NamedTuple, Protocol

import numpy as np

from ide.agent.dna import BEHAVIORS
from ide.agent.epistemology import is_known
from ide.config import sporulation_active
from ide.domain.types import (
    ActionType,
    AgentAction,
    Behavior,
    EventSignals,
    Observation,
    SensorySignals,
    SocialPerception,
    VisibleResource,
)

if TYPE_CHECKING:
    from ide.agent.micro_agent import MicroAgent


class PolicyPort(Protocol):
    """Componente intercambiable que decide la acción de un agente (design D45.1).

    `social` es la `SocialPerception` del tick o `None` (design D47.1).

    `gates_communication` declara la puerta de comunicación de D46.6: si vale `True`, el agente
    comunica sólo con `comm_propensity >= 0.5`; si vale `False`, comunica siempre.
    """

    gates_communication: bool

    def decide(
        self,
        agent: "MicroAgent",
        obs: Observation,
        social: SocialPerception | None,
        tick: int,
        rng: np.random.Generator,
    ) -> AgentAction: ...


class HandwrittenPolicy:
    """Lógica de decisión de la Fase I, sin cambios (design D45.2).

    Consume el recurso alcanzable de mayor $\\hat{v} \\cdot c$, explora con probabilidad
    $\\epsilon$, navega hacia un objetivo conocido o camina al azar; desempates por menor
    `resource_id`. Ignora `social`. Comparte con `GeneticPolicy` la clasificación de los recursos
    visibles (`_survey`), que no consume generadores: las extracciones de `rng` no cambian.
    """

    gates_communication = False

    def decide(
        self,
        agent: "MicroAgent",
        obs: Observation,
        social: SocialPerception | None,
        tick: int,
        rng: np.random.Generator,
    ) -> AgentAction:
        config = agent.config
        # Sin navegación no consulta las creencias de los recursos lejanos, como en la Fase I.
        beneficial, unknown, goals, _, _ = _survey(agent, obs, config.enable_navigation)
        if beneficial:
            return AgentAction(ActionType.INTERACT, min(beneficial)[1])
        if unknown and rng.random() < config.epsilon_explore:
            target = min(unknown, key=lambda r: r.resource_id)
            return AgentAction(ActionType.INTERACT, target.resource_id)
        if goals:
            goal = min(goals, key=lambda r: (r.distance, r.resource_id))
            return AgentAction(ActionType.MOVE, goal.recommended_move)
        if not obs.available_moves:
            return AgentAction(ActionType.IDLE)
        return AgentAction(
            ActionType.MOVE, obs.available_moves[int(rng.integers(len(obs.available_moves)))]
        )


# --- Política genética (R32, D46) ----------------------------------------------------------------

_NO_SOCIAL = SocialPerception()  # sin percepción social, las señales sociales son falsas (prec. 24)
_IDLE = AgentAction(ActionType.IDLE)


class _Survey(NamedTuple):
    """Clasificación de los recursos visibles con las creencias efectivas del agente.

    "Conocido", "benéfico" y "alcanzable" son los de `HandwrittenPolicy` (D46.1).
    """

    beneficial: list[tuple[float, int]]  # alcanzables conocidos benéficos: (-v̂·c, resource_id)
    unknown: list[VisibleResource]  # alcanzables desconocidos
    goals: list[VisibleResource]  # conocidos benéficos no alcanzables
    known_good: bool  # algún recurso visible es conocido y benéfico
    any_unknown: bool  # algún recurso visible es desconocido


def _survey(agent: "MicroAgent", obs: Observation, far: bool = True) -> _Survey:
    """Clasifica los recursos visibles; con `far=False` ignora los no alcanzables.

    `HandwrittenPolicy` pasa `far = enable_navigation` y no consulta las creencias de lo que no
    usará; `GeneticPolicy` los mira todos, porque las señales hablan de todo lo visible.
    """
    config = agent.config
    beneficial: list[tuple[float, int]] = []
    unknown: list[VisibleResource] = []
    goals: list[VisibleResource] = []
    known_good = any_unknown = False
    for res in obs.visible_resources:
        if not (far or res.is_reachable_now):
            continue
        belief = agent.get_effective_belief(res.pattern)
        if not is_known(belief, config):
            any_unknown = True
            if res.is_reachable_now:
                unknown.append(res)
        elif belief.predicted_value > 0:
            known_good = True
            if res.is_reachable_now:
                beneficial.append((-belief.predicted_value * belief.confidence, res.resource_id))
            else:
                goals.append(res)
    return _Survey(beneficial, unknown, goals, known_good, any_unknown)


def _signals(
    survey: _Survey, obs: Observation, social: SocialPerception, events: EventSignals
) -> SensorySignals:
    """Señales del tick (D46.2, D47.4) y eventos del tick anterior (`agent.last_events`, D58.5)."""
    return SensorySignals(
        known_good=survey.known_good,
        unknown=survey.any_unknown,
        no_resource=not obs.visible_resources,
        neighbor_adjacent=bool(social.adjacent),
        weaker_adjacent=social.weaker_adjacent,
        stronger_near=social.flee_move is not None,
        crowded=social.crowded,
        carcass=social.carcass_visible,
        attacked=events.attacked,
        ate=events.ate,
        lost_energy=events.lost_energy,
        received_energy=events.received_energy,
    )


def sensory_signals(
    agent: "MicroAgent", obs: Observation, social: SocialPerception | None
) -> SensorySignals:
    """`SensorySignals` del tick desde la observación, las creencias efectivas, `social` (D47.4)
    y los eventos del tick anterior (`agent.last_events`, D58.5).

    Con `social=None` usa `SocialPerception()` (precisión 24). No consume generadores.
    """
    social = _NO_SOCIAL if social is None else social
    return _signals(_survey(agent, obs), obs, social, agent.last_events)


def behavior_order(drives: Sequence[float]) -> list[int]:
    """Orden de prueba de `GeneticPolicy` (D46.4): las posiciones con impulso positivo en orden
    de $(-d_B, \\text{posición})$. Es la única definición; la usa también la telemetría."""
    return [
        slot for _, slot in sorted((-drive, slot) for slot, drive in enumerate(drives) if drive > 0)
    ]


def first_feasible(order: Iterable[int], feasible: Callable[[int], bool]) -> int | None:
    """La primera posición de `order` con `feasible(posición)`, o `None` si ninguna lo es."""
    for slot in order:
        if feasible(slot):
            return slot
    return None


class DecisionTrace:
    """Lo que `GeneticPolicy` calcula al decidir, registrado en la decisión del tick (D53.2).

    Guarda las `SensorySignals` del tick y los insumos de la factibilidad de D46.1 (la
    clasificación de los recursos, la observación, la percepción social y lo que la factibilidad
    lee del agente: su configuración efectiva, su energía y su umbral de esporulación), y evalúa
    la factibilidad de cada posición de `BEHAVIORS` de forma perezosa, una vez, sin generador.
    La telemetría lo lee en `on_decisions` (precisión 126), antes de la Fase 4, así que ve lo
    mismo que vio la política. No guarda una referencia al agente.
    """

    __slots__ = (
        "_config",
        "_energy",
        "_known",
        "_obs",
        "_social",
        "_spore_threshold",
        "_values",
        "signals",
        "survey",
    )

    def __init__(
        self, agent: "MicroAgent", obs: Observation, social: SocialPerception | None
    ) -> None:
        social = _NO_SOCIAL if social is None else social
        self.survey = _survey(agent, obs)
        self.signals = _signals(self.survey, obs, social, agent.last_events)
        self._obs, self._social = obs, social
        self._config = agent.config
        self._energy = agent.energy
        self._spore_threshold = agent.phenotype.spore_threshold
        self._known = self._values = 0  # máscaras de las posiciones evaluadas y factibles

    def feasible(self, slot: int) -> bool:
        """Factibilidad de `BEHAVIORS[slot]` (`_feasible`), evaluada la primera vez que se pide."""
        bit = 1 << slot
        if self._known & bit:
            return bool(self._values & bit)
        value = self._check(BEHAVIORS[slot])
        self._known |= bit
        if value:
            self._values |= bit
        return value

    def first_feasible(self, order: Iterable[int]) -> int | None:
        """La primera posición factible de `order` (`behavior_order`), o `None` (`IDLE`)."""
        return first_feasible(order, self.feasible)

    def _check(self, behavior: Behavior) -> bool:
        """Factibilidad de `behavior` sin generador (D46.1, precisiones 11, 24 y 30).

        `EXPLORE` es factible si hay algún recurso alcanzable desconocido y `WANDER` si hay algún
        movimiento: la extracción de `rng` que decide si EXPLORE explora y adónde camina WANDER
        es aparte (`_action`). `SHARE` y `ATTACK` exigen además un objetivo
        (`social.weakest_adjacent is not None`): con una percepción incoherente no son
        factibles.
        """
        config, survey, social = self._config, self.survey, self._social
        match behavior:
            case Behavior.CONSUME:
                return bool(survey.beneficial)
            case Behavior.EXPLORE:
                return bool(survey.unknown)
            case Behavior.NAVIGATE:
                return config.enable_navigation and bool(survey.goals)
            case Behavior.WANDER:
                return bool(self._obs.available_moves)
            case Behavior.SHARE:
                return (
                    config.enable_energy_transfer
                    and social.weakest_adjacent is not None
                    and self._energy > 0
                )
            case Behavior.ATTACK:
                return (
                    config.enable_predation
                    and social.weaker_adjacent
                    and social.weakest_adjacent is not None
                )
            case Behavior.FLEE:
                return social.flee_move is not None
            case Behavior.SPORULATE:
                return sporulation_active(config) and self._energy <= self._spore_threshold

    def action(self, behavior: Behavior, rng: np.random.Generator) -> AgentAction | None:
        """Acción de `behavior`, ya factible; `None` si `EXPLORE` no explora.

        `EXPLORE` extrae de `rng` sólo si existe algún candidato (D46.1), y explora con
        probabilidad `epsilon_explore`; `WANDER` extrae el movimiento sólo si hay alguno: las
        extracciones son las de antes de separar la factibilidad (bloque 21).
        """
        survey, social = self.survey, self._social
        match behavior:
            case Behavior.CONSUME:
                return AgentAction(ActionType.INTERACT, min(survey.beneficial)[1])
            case Behavior.EXPLORE:
                if rng.random() < self._config.epsilon_explore:
                    target = min(survey.unknown, key=lambda r: r.resource_id)
                    return AgentAction(ActionType.INTERACT, target.resource_id)
                return None
            case Behavior.NAVIGATE:
                goal = min(survey.goals, key=lambda r: (r.distance, r.resource_id))
                return AgentAction(ActionType.MOVE, goal.recommended_move)
            case Behavior.WANDER:
                moves = self._obs.available_moves
                return AgentAction(ActionType.MOVE, moves[int(rng.integers(len(moves)))])
            case Behavior.SHARE:
                return AgentAction(ActionType.SHARE, social.weakest_adjacent)
            case Behavior.ATTACK:
                return AgentAction(ActionType.ATTACK, social.weakest_adjacent)
            case Behavior.FLEE:
                return AgentAction(ActionType.MOVE, social.flee_move)
            case Behavior.SPORULATE:
                return AgentAction(ActionType.SPORULATE)


class GeneticPolicy:
    """Política codificada en el ADN del agente (R32, design D46.4).

    Calcula las señales y la evaluación de conducta (`agent.evaluate_for_decision`, D60.1, que
    la registra para el motor; con el
    caché del agente, D46.8, sobre su `last_context`, precisión 23, y su estado interno, D58.3),
    recorre las conductas con $d_B > 0$ en el orden de `behavior_order` y
    devuelve la acción de la primera factible, o `IDLE` si ninguna lo es. La factibilidad se
    evalúa en ese orden y se detiene en la primera factible, así que `rng` sólo se consume en
    `EXPLORE` (si hay un recurso alcanzable desconocido) y en `WANDER`, como en
    `HandwrittenPolicy` (precisión 25). Registra en la decisión del agente lo que calculó
    (`DecisionTrace`), que lee la telemetría. No guarda estado, así que una sola instancia sirve
    a toda la población. Declara la puerta de comunicación de D46.6.
    """

    gates_communication = True

    def decide(
        self,
        agent: "MicroAgent",
        obs: Observation,
        social: SocialPerception | None,
        tick: int,
        rng: np.random.Generator,
    ) -> AgentAction:
        if agent.dna is None:
            raise ValueError("GeneticPolicy exige un agente con ADN (enable_compact_dna)")
        trace = DecisionTrace(agent, obs, social)
        drives = agent.evaluate_for_decision(trace.signals, tick).drives
        agent.record_decision_trace(trace, tick)
        for slot in behavior_order(drives):
            if not trace.feasible(slot):
                continue
            action = trace.action(BEHAVIORS[slot], rng)
            if action is not None:
                agent.record_behavior(slot, tick)  # conducta elegida, para R40 (D59.4)
                return action
        return _IDLE


def behavior_feasibility(
    agent: "MicroAgent", obs: Observation, social: SocialPerception | None
) -> tuple[SensorySignals, tuple[bool, ...]]:
    """Señales del tick y factibilidad de cada `Behavior`, en el orden de `BEHAVIORS`, sin `rng`.

    Son las mismas señales y factibilidades con que decide `GeneticPolicy` (`DecisionTrace`),
    con `EXPLORE` factible si hay recursos alcanzables desconocidos. Con `social=None` usa
    `SocialPerception()` (precisión 24). No consume generadores ni cambia el agente.
    """
    trace = DecisionTrace(agent, obs, social)
    return trace.signals, tuple(trace.feasible(slot) for slot in range(len(BEHAVIORS)))
