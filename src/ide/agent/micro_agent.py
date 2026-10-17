"""Micro-agente autónomo: percepción local, comunicación delegada y decisión."""

import numpy as np

from ide.agent.epistemology import (
    is_known,
    merge_social_belief,
    update_from_direct_experience,
)
from ide.agent.memory import BoundedMemory
from ide.agent.protocol import BeliefExchangeProtocol
from ide.config import SimulationConfig
from ide.domain.extensions import AgentCapabilities, TrustStrategyPort, UniformTrustStrategy
from ide.domain.types import (
    ActionType,
    AgentAction,
    KnowledgeUnit,
    Message,
    Observation,
    Pattern,
    VisibleResource,
)


class MicroAgent:
    """Agente con memoria acotada que no conoce coordenadas ni valores verdaderos."""

    def __init__(
        self,
        agent_id: int,
        config: SimulationConfig,
        trust_strategy: TrustStrategyPort | None = None,
        protocol: BeliefExchangeProtocol | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._config = config
        self._trust = UniformTrustStrategy() if trust_strategy is None else trust_strategy
        self._protocol = BeliefExchangeProtocol() if protocol is None else protocol
        self._memory = BoundedMemory(config.memory_capacity, config.lambda_decay)
        self._capabilities = AgentCapabilities()
        # Creencias asimiladas en el tick actual, aunque la memoria las haya rechazado.
        self._ephemeral_tick_beliefs: dict[Pattern, KnowledgeUnit] = {}

    @property
    def agent_id(self) -> int:
        return self._agent_id

    @property
    def config(self) -> SimulationConfig:
        return self._config

    @property
    def memory(self) -> BoundedMemory:
        return self._memory

    @property
    def capabilities(self) -> AgentCapabilities:
        return self._capabilities

    def get_effective_belief(self, pattern: Pattern) -> KnowledgeUnit | None:
        """Creencia de memoria si existe; si no, la del caché efímero del tick."""
        unit = self._memory.get(pattern)
        return unit if unit is not None else self._ephemeral_tick_beliefs.get(pattern)

    def assimilate_testimony(
        self, belief: KnowledgeUnit, sender_id: int, tick: int
    ) -> KnowledgeUnit:
        """Única puerta de entrada del conocimiento social."""
        trust = self._trust.compute_sender_trust(
            self._agent_id, sender_id, self._config.gamma_social_discount
        )
        merged = merge_social_belief(
            self.get_effective_belief(belief.pattern), belief, tick, self._config, trust
        )
        self._ephemeral_tick_beliefs[merged.pattern] = merged
        self._memory.upsert(merged, tick)
        return merged

    def perceive_and_emit_messages(self, obs: Observation, tick: int) -> list[Message]:
        self._ephemeral_tick_beliefs.clear()
        return self._protocol.emit(self, obs, tick)

    def process_incoming_messages(self, messages: list[Message], tick: int) -> list[Message]:
        return self._protocol.receive(self, messages, tick)

    def decide_action(self, obs: Observation, tick: int, rng: np.random.Generator) -> AgentAction:
        """Consumir, explorar, navegar o caminar al azar; desempates por menor `resource_id`."""
        reachable = [r for r in obs.visible_resources if r.is_reachable_now]
        beneficial = self._known_beneficial(reachable)
        if beneficial:
            best = min(beneficial, key=lambda item: (-item[1], item[0].resource_id))
            return AgentAction(ActionType.INTERACT, best[0].resource_id)

        unknown = [r for r in reachable if not self._is_known(r.pattern)]
        if unknown and rng.random() < self._config.epsilon_explore:
            target = min(unknown, key=lambda r: r.resource_id)
            return AgentAction(ActionType.INTERACT, target.resource_id)

        if self._config.enable_navigation:
            distant = [r for r in obs.visible_resources if not r.is_reachable_now]
            goals = self._known_beneficial(distant)
            if goals:
                goal = min(goals, key=lambda item: (item[0].distance, item[0].resource_id))
                return AgentAction(ActionType.MOVE, goal[0].recommended_move)

        if not obs.available_moves:
            return AgentAction(ActionType.IDLE)
        return AgentAction(
            ActionType.MOVE, obs.available_moves[int(rng.integers(len(obs.available_moves)))]
        )

    def learn_from_experience(self, pattern: Pattern, real_value: float, tick: int) -> None:
        """La experiencia directa siempre se retiene (prioridad empírica)."""
        updated = update_from_direct_experience(
            self.get_effective_belief(pattern), pattern, real_value, tick, self._config
        )
        self._memory.upsert(updated, tick, force=True)

    def decay_memory(self, tick: int) -> None:
        self._memory.decay_step(tick, self._config.passive_conf_decay, self._config.min_confidence)

    def _is_known(self, pattern: Pattern) -> bool:
        return is_known(self.get_effective_belief(pattern), self._config)

    def _known_beneficial(
        self, resources: list[VisibleResource]
    ) -> list[tuple[VisibleResource, float]]:
        """Recursos de patrón conocido con `v̂ > 0`, con su valor esperado `v̂·c`."""
        result: list[tuple[VisibleResource, float]] = []
        for res in resources:
            belief = self.get_effective_belief(res.pattern)
            if is_known(belief, self._config) and belief.predicted_value > 0:
                result.append((res, belief.predicted_value * belief.confidence))
        return result
