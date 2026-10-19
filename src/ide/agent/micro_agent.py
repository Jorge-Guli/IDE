"""Micro-agente autónomo: percepción local, comunicación delegada y decisión."""

from dataclasses import replace

import numpy as np

from ide.agent.epistemology import (
    is_known,
    merge_social_belief,
    update_from_direct_experience,
)
from ide.agent.evolution import genome_from_config
from ide.agent.memory import BoundedMemory
from ide.agent.protocol import BeliefExchangeProtocol
from ide.config import SimulationConfig
from ide.domain.extensions import (
    AgentCapabilities,
    TrustStrategyPort,
    UniformTrustStrategy,
    mutate_genome,
)
from ide.domain.types import (
    ActionType,
    AgentAction,
    AgentGenome,
    KnowledgeUnit,
    Message,
    Observation,
    Pattern,
    VisibleResource,
)


class MicroAgent:
    """Agente con memoria acotada que no conoce coordenadas ni valores verdaderos.

    Es también el nodo holónico de nivel cero (`AgentNode`, design D23) y lleva su estado
    energético y de linaje (Exp 002 v2), inerte mientras el motor no active la evolución.
    """

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
        # Vista compartida del holón (R22): efímera, nunca se escribe en la memoria.
        self._holon_tick_beliefs: dict[Pattern, KnowledgeUnit] = {}
        self._genome = genome_from_config(config)
        self._energy = config.initial_energy
        self._generation = 0
        self._parent_id: int | None = None

    @classmethod
    def from_lineage(
        cls,
        agent_id: int,
        config: SimulationConfig,
        genome: AgentGenome,
        energy: float,
        generation: int,
        parent_id: int | None,
        trust_strategy: TrustStrategyPort | None = None,
        protocol: BeliefExchangeProtocol | None = None,
    ) -> "MicroAgent":
        """Descendiente cuyo fenotipo (configuración) expresa su genoma.

        `initial_bond_affinity` conserva el valor fundador (D22): la afinidad de un descendiente
        se lee siempre de su genoma, nunca de su configuración.
        """
        agent_config = replace(
            config,
            alpha_learning=genome.alpha_learning,
            gamma_social_discount=genome.gamma_social_discount,
            epsilon_explore=genome.epsilon_explore,
            memory_capacity=genome.memory_capacity,
            perception_radius=genome.perception_radius,
            comm_radius=genome.comm_radius,
        )
        agent = cls(agent_id, agent_config, trust_strategy, protocol)
        agent._genome = genome
        agent._energy = energy
        agent._generation = generation
        agent._parent_id = parent_id
        return agent

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

    @property
    def energy(self) -> float:
        return self._energy

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def parent_id(self) -> int | None:
        return self._parent_id

    @property
    def genome(self) -> AgentGenome:
        return self._genome

    @property
    def node_id(self) -> int:
        return self._agent_id

    @property
    def holon_level(self) -> int:
        return 0

    @property
    def leaf_agents(self) -> tuple["MicroAgent", ...]:
        return (self,)

    @property
    def effective_capacity(self) -> int:
        return self._memory.capacity

    def collective_memory(self) -> dict[Pattern, KnowledgeUnit]:
        """La memoria propia, ordenada por `pattern`: una hoja es su propio colectivo."""
        return {unit.pattern: unit for unit in self._memory.all_units()}

    def apply_energy_delta(self, delta: float) -> None:
        """Suma `delta` a la energía (negativo para los costos)."""
        self._energy += delta

    def create_offspring(
        self,
        child_id: int,
        tick: int,
        rng: np.random.Generator,
        genome_source: AgentGenome | None = None,
    ) -> "MicroAgent":
        """Hijo con energía particionada y genoma mutado (R12, R13), sin creencias.

        `genome_source` sólo lo pasa la reproducción neutral. La herencia cultural (R14) la
        entrega el motor después, por `assimilate_testimony`.
        """
        source = self._genome if genome_source is None else genome_source
        genome = mutate_genome(source, self._config, rng)
        child_energy = self._config.offspring_energy_share * self._energy
        self._energy -= child_energy
        return MicroAgent.from_lineage(
            child_id,
            self._config,
            genome,
            child_energy,
            self._generation + 1,
            self._agent_id,
            self._trust,
            self._protocol,
        )

    def own_belief(self, pattern: Pattern) -> KnowledgeUnit | None:
        """Creencia de memoria si existe; si no, la del caché efímero propio del tick."""
        unit = self._memory.get(pattern)
        return unit if unit is not None else self._ephemeral_tick_beliefs.get(pattern)

    def get_effective_belief(self, pattern: Pattern) -> KnowledgeUnit | None:
        """Creencia propia si existe; si no, la de la vista del holón del tick (R22)."""
        unit = self.own_belief(pattern)
        return unit if unit is not None else self._holon_tick_beliefs.get(pattern)

    def clear_holon_beliefs(self) -> None:
        self._holon_tick_beliefs.clear()

    def inject_ephemeral_belief(self, unit: KnowledgeUnit) -> None:
        """Vista del holón (R22): sólo guía la decisión del tick; no entra en la memoria."""
        self._holon_tick_beliefs[unit.pattern] = unit

    def assimilate_testimony(
        self, belief: KnowledgeUnit, sender_id: int, tick: int
    ) -> KnowledgeUnit:
        """Única puerta de entrada del conocimiento social."""
        trust = self._trust.compute_sender_trust(
            self._agent_id, sender_id, self._config.gamma_social_discount
        )
        merged = merge_social_belief(
            self.own_belief(belief.pattern), belief, tick, self._config, trust
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
        navigate = self._config.enable_navigation
        beneficial: list[tuple[float, int]] = []  # (-v̂·c, resource_id): `min` elige el mejor
        unknown: list[VisibleResource] = []
        goals: list[VisibleResource] = []
        for res in obs.visible_resources:
            if not (res.is_reachable_now or navigate):
                continue
            belief = self.get_effective_belief(res.pattern)
            if not is_known(belief, self._config):
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
        if unknown and rng.random() < self._config.epsilon_explore:
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

    def learn_from_experience(self, pattern: Pattern, real_value: float, tick: int) -> None:
        """La experiencia directa siempre se retiene (prioridad empírica)."""
        updated = update_from_direct_experience(
            self.own_belief(pattern), pattern, real_value, tick, self._config
        )
        self._memory.upsert(updated, tick, force=True)

    def decay_memory(self, tick: int) -> None:
        self._memory.decay_step(tick, self._config.passive_conf_decay, self._config.min_confidence)
