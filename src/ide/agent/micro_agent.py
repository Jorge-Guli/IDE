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
        beneficial: list[tuple[float, int]] = []  # (-v̂·c, resource_id)
        unknown: list[int] = []
        goals: list[tuple[int, int, object]] = []  # (distance, resource_id, recommended_move)
        for res in obs.visible_resources:
            belief = self.get_effective_belief(res.pattern)
            known = is_known(belief, self._config)
            if res.is_reachable_now:
                if known and belief.predicted_value > 0:
                    beneficial.append(
                        (-belief.predicted_value * belief.confidence, res.resource_id)
                    )
                elif not known:
                    unknown.append(res.resource_id)
            elif self._config.enable_navigation and known and belief.predicted_value > 0:
                goals.append((res.distance, res.resource_id, res.recommended_move))

        if beneficial:
            return AgentAction(ActionType.INTERACT, min(beneficial)[1])
        if unknown and rng.random() < self._config.epsilon_explore:
            return AgentAction(ActionType.INTERACT, min(unknown))
        if goals:
            nearest = min(goals, key=lambda g: (g[0], g[1]))
            return AgentAction(ActionType.MOVE, nearest[2])
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
