"""Puerto de política de acción, política escrita a mano y política genética (D45, D46).

`GeneticPolicy` (R32) decide con los impulsos que el ADN del agente asigna a cada `Behavior`
(D46.4): construye las `SensorySignals` del tick desde la observación, las creencias efectivas, la
percepción social (D47.4) y los eventos del tick anterior (D58.5), y prueba las conductas con
impulso positivo en orden de $(-d_B, \text{posición})$, con la factibilidad de D46.1 evaluada de
forma perezosa (precisión 25).
"""

from typing import TYPE_CHECKING, NamedTuple, Protocol

import numpy as np

from ide.agent.epistemology import is_known
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

_BEHAVIORS = tuple(Behavior)  # orden de la tabla de D46.1: orden de desempate
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


class GeneticPolicy:
    """Política codificada en el ADN del agente (R32, design D46.4).

    Calcula las señales y la evaluación de conducta (`agent.evaluate_for_decision`, D60.1, que
    la registra para el motor; con el
    caché del agente, D46.8, sobre su `last_context`, precisión 23, y su estado interno, D58.3),
    recorre las conductas con $d_B > 0$ en orden de $(-d_B, \text{posición})$ y
    devuelve la acción de la primera factible, o `IDLE` si ninguna lo es. La factibilidad se
    evalúa en ese orden y se detiene en la primera factible, así que `rng` sólo se consume en
    `EXPLORE` (si hay un recurso alcanzable desconocido) y en `WANDER`, como en
    `HandwrittenPolicy` (precisión 25). No guarda estado, así que una sola instancia sirve a
    toda la población. Declara la puerta de comunicación de D46.6.
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
        social = _NO_SOCIAL if social is None else social
        survey = _survey(agent, obs)
        signals = _signals(survey, obs, social, agent.last_events)
        drives = agent.evaluate_for_decision(signals, tick).drives
        for _, slot in sorted((-drive, slot) for slot, drive in enumerate(drives) if drive > 0):
            action = _feasible_action(_BEHAVIORS[slot], agent, obs, social, survey, rng)
            if action is not None:
                agent.record_behavior(slot, tick)  # conducta elegida, para R40 (D59.4)
                return action
        return _IDLE


def _feasible_action(
    behavior: Behavior,
    agent: "MicroAgent",
    obs: Observation,
    social: SocialPerception,
    survey: _Survey,
    rng: np.random.Generator,
) -> AgentAction | None:
    """Acción de `behavior` si es factible (D46.1, precisiones 11, 24 y 30); si no, `None`.

    `SHARE` y `ATTACK` exigen además un objetivo (`social.weakest_adjacent is not None`): con
    una percepción incoherente no devuelven una acción sin destinatario.
    """
    config = agent.config
    match behavior:
        case Behavior.CONSUME:
            if survey.beneficial:
                return AgentAction(ActionType.INTERACT, min(survey.beneficial)[1])
        case Behavior.EXPLORE:
            # La extracción ocurre sólo si existe algún candidato (D46.1).
            if survey.unknown and rng.random() < config.epsilon_explore:
                target = min(survey.unknown, key=lambda r: r.resource_id)
                return AgentAction(ActionType.INTERACT, target.resource_id)
        case Behavior.NAVIGATE:
            if config.enable_navigation and survey.goals:
                goal = min(survey.goals, key=lambda r: (r.distance, r.resource_id))
                return AgentAction(ActionType.MOVE, goal.recommended_move)
        case Behavior.WANDER:
            moves = obs.available_moves
            if moves:
                return AgentAction(ActionType.MOVE, moves[int(rng.integers(len(moves)))])
        case Behavior.SHARE:
            target = social.weakest_adjacent
            if config.enable_energy_transfer and target is not None and agent.energy > 0:
                return AgentAction(ActionType.SHARE, target)
        case Behavior.ATTACK:
            target = social.weakest_adjacent
            if config.enable_predation and social.weaker_adjacent and target is not None:
                return AgentAction(ActionType.ATTACK, target)
        case Behavior.FLEE:
            if social.flee_move is not None:
                return AgentAction(ActionType.MOVE, social.flee_move)
        case Behavior.SPORULATE:
            if (
                config.enable_evolution
                and config.enable_sporulation
                and agent.energy <= agent.phenotype.spore_threshold
            ):
                return AgentAction(ActionType.SPORULATE)
    return None
