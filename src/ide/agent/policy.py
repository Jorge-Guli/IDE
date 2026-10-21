"""Puerto de política de acción y política escrita a mano (design D45)."""

from typing import TYPE_CHECKING, Protocol

import numpy as np

from ide.agent.epistemology import is_known
from ide.domain.types import (
    ActionType,
    AgentAction,
    Observation,
    VisibleResource,
)

if TYPE_CHECKING:
    from ide.agent.micro_agent import MicroAgent


class PolicyPort(Protocol):
    """Componente intercambiable que decide la acción de un agente (design D45.1).

    `social` es la percepción social del tick o `None`. Su tipo concreto
    (`SocialPerception`) lo introduce el bloque 8; hasta entonces el puerto la trata como
    opaca.
    """

    def decide(
        self,
        agent: "MicroAgent",
        obs: Observation,
        social: object | None,
        tick: int,
        rng: np.random.Generator,
    ) -> AgentAction: ...


class HandwrittenPolicy:
    """Lógica de decisión de la Fase I, sin cambios (design D45.2).

    Consume el recurso alcanzable de mayor $\\hat{v} \\cdot c$, explora con probabilidad
    $\\epsilon$, navega hacia un objetivo conocido o camina al azar; desempates por menor
    `resource_id`. Ignora `social`.
    """

    def decide(
        self,
        agent: "MicroAgent",
        obs: Observation,
        social: object | None,
        tick: int,
        rng: np.random.Generator,
    ) -> AgentAction:
        config = agent.config
        navigate = config.enable_navigation
        beneficial: list[tuple[float, int]] = []  # (-v̂·c, resource_id): `min` elige el mejor
        unknown: list[VisibleResource] = []
        goals: list[VisibleResource] = []
        for res in obs.visible_resources:
            if not (res.is_reachable_now or navigate):
                continue
            belief = agent.get_effective_belief(res.pattern)
            if not is_known(belief, config):
                if res.is_reachable_now:
                    unknown.append(res)
            elif belief.predicted_value > 0:
                if res.is_reachable_now:
                    beneficial.append(
                        (-belief.predicted_value * belief.confidence, res.resource_id)
                    )
                else:
                    goals.append(res)

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
