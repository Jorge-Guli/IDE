"""Motor de simulación: pipeline determinista de 5 fases sin coordinador cognitivo."""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import cast

import numpy as np

from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.extensions import TrustStrategyPort
from ide.domain.ports import EnvironmentPort
from ide.domain.types import AgentAction, KnowledgeUnit, Message, Observation, Pattern
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.metrics import (
    KnowledgeSnapshot,
    MetricsCollector,
    TickMetrics,
    has_truthful_query_channel,
    judge_decision,
    knowledge_snapshot,
)
from ide.simulation.controls import nullify_belief


class SimulationEngine:
    """Orquesta el tiempo discreto. Un único generador, compartido con la grilla por defecto."""

    def __init__(
        self,
        config: SimulationConfig,
        env: EnvironmentPort | None = None,
        trust_strategy: TrustStrategyPort | None = None,
    ) -> None:
        if config.enable_specialization:
            raise NotImplementedError("Especialización (Exp 003) fuera de alcance del Exp 001")
        if config.epsilon_recheck > 0 or config.tau_policy != "validation":
            raise NotImplementedError(
                "Mecanismos anti-trampa de evitación (Exp 004) fuera de alcance del Exp 001"
            )
        if config.update_scheme != "synchronous":
            raise NotImplementedError(
                "Esquema asíncrono (Decisión 15) previsto para el barrido de densidad"
            )
        self.config = config
        self.rng = np.random.Generator(np.random.PCG64(config.seed))
        # Generador propio del control nulo: no desplaza la secuencia principal.
        self.null_rng = np.random.Generator(
            np.random.PCG64(np.random.SeedSequence(config.seed, spawn_key=(1,)))
        )
        self.env: EnvironmentPort = env if env is not None else ToroidalGrid2D(config, self.rng)
        self.agents: dict[int, MicroAgent] = {
            aid: MicroAgent(aid, config, trust_strategy) for aid in self.env.get_active_agent_ids()
        }
        self.direct_discoverers: dict[Pattern, set[int]] = defaultdict(set)
        self.collector = MetricsCollector(config)
        self.history: list[TickMetrics] = []
        self.next_tick: int = 0

    # --- Tick ----------------------------------------------------------------------------------

    def step(self) -> TickMetrics:
        """Ejecuta el tick `next_tick` y lo incrementa."""
        tick = self.next_tick
        env = self.env
        order = cast(
            list[int],
            self.rng.permutation(np.array(sorted(self.agents), dtype=np.int64)).tolist(),  # pyright: ignore[reportUnknownMemberType]
        )

        # 1. Percepción y emisión, sobre la misma instantánea para todos.
        observations: dict[int, Observation] = {}
        emitted: list[Message] = []
        for aid in order:
            observations[aid] = env.get_observation(aid, tick)
            emitted += self.agents[aid].perceive_and_emit_messages(observations[aid], tick)

        # 2. Intercambio social en dos pasadas.
        messages_sent = 0
        if self.config.comm_enabled:
            # Nadie se mueve entre las fases 1 y 2: los vecinos de la observación son los del
            # ruteo, sin volver a recorrer la vecindad (Decisión 18).
            neighbors = {aid: observations[aid].neighbor_ids for aid in order}
            responses: list[Message] = []
            for aid, inbox in self._route(emitted, neighbors, order).items():
                responses += self.agents[aid].process_incoming_messages(inbox, tick)
            for aid, inbox in self._route(responses, neighbors, order).items():
                if self.agents[aid].process_incoming_messages(inbox, tick):
                    raise RuntimeError("la segunda pasada no debe generar respuestas")
            messages_sent = len(emitted) + len(responses)

        # 3. Decisión sobre la observación de la fase 1; M2 juzga la intención.
        actions: dict[int, AgentAction] = {}
        opportunities = correct = 0
        for aid in order:
            truth = env.get_reachable_true_values(aid)
            actions[aid] = self.agents[aid].decide_action(observations[aid], tick, self.rng)
            if truth:
                opportunities += 1
                correct += judge_decision(actions[aid], truth)

        # 4. Ejecución y aprendizaje directo; los conflictos se resuelven por `order`.
        for aid in order:
            result = env.execute_action(aid, actions[aid], tick)
            if result.experienced_value is not None and result.interacted_pattern is not None:
                self.agents[aid].learn_from_experience(
                    result.interacted_pattern, result.experienced_value, tick
                )
                self.direct_discoverers[result.interacted_pattern].add(aid)

        # 5. Mantenimiento y telemetría, con los vecinos posteriores al movimiento.
        for aid in order:
            self.agents[aid].decay_memory(tick)
        env.step_dynamics(tick)
        metrics = self.collector.record_tick(
            tick,
            self.agents,
            env.get_world_patterns(),
            self._neighbor_map(),
            opportunities,
            correct,
            messages_sent,
        )
        self.history.append(metrics)
        self.next_tick += 1
        return metrics

    def run(self, ticks: int) -> list[TickMetrics]:
        """Ejecuta `ticks` ticks y devuelve sus métricas."""
        return [self.step() for _ in range(ticks)]

    def _route(
        self, messages: list[Message], neighbors: Mapping[int, Sequence[int]], order: list[int]
    ) -> dict[int, list[Message]]:
        """Bandejas por agente, en `order`; cada entrega del control nulo es una extracción."""
        inboxes: dict[int, list[Message]] = {aid: [] for aid in order}
        null = self.config.comm_content_null
        for msg in messages:
            reach: Sequence[int] = neighbors[msg.sender_id]
            if msg.recipient_id is not None:
                reach = [msg.recipient_id] if msg.recipient_id in reach else []
            for receiver in reach:
                delivered = msg
                if null and msg.belief is not None:
                    delivered = replace(msg, belief=nullify_belief(msg.belief, self.null_rng))
                inboxes[receiver].append(delivered)
        return inboxes

    def _neighbor_map(self) -> dict[int, list[int]]:
        """Vecinos para la cobertura accesible: vacíos sin un canal de consulta veraz.

        `knowledge_snapshot` ya ignora los vecinos en ese caso; vaciarlos aquí cumple el
        contrato de `record_tick` y evita recorrer la vecindad de cada agente sin necesidad.
        """
        if not has_truthful_query_channel(self.config):
            return {aid: [] for aid in self.agents}
        return {aid: self.env.get_communication_neighbors(aid) for aid in self.agents}

    # --- Perturbaciones (entre ticks; el tick efectivo es `next_tick`) --------------------------

    def _choose(self, fraction: float) -> list[int]:
        if not 0.0 <= fraction <= 1.0:  # también rechaza NaN
            raise ValueError(f"fraction debe estar en [0, 1], recibido {fraction}")
        active = np.array(sorted(self.agents), dtype=np.int64)
        k = round(fraction * len(active))
        chosen = cast(
            list[int],
            self.rng.choice(active, size=k, replace=False).tolist(),  # pyright: ignore[reportUnknownMemberType]
        )
        return sorted(chosen)

    def _remove(self, victims: list[int]) -> None:
        for aid in victims:
            del self.agents[aid]
        self.env.remove_agents(victims)

    def inject_false_belief(
        self, pattern: Pattern, false_value: float, confidence: float, fraction: float
    ) -> list[int]:
        """Planta un rumor (Decisión 7): no es experiencia directa del portador."""
        targets = self._choose(fraction)
        rumor = KnowledgeUnit(pattern, false_value, confidence, 1, self.next_tick, False)
        for aid in targets:
            self.agents[aid].memory.upsert(rumor, self.next_tick, force=True)
        return targets

    def ablate_population(self, fraction: float) -> list[int]:
        victims = self._choose(fraction)
        self._remove(victims)
        return victims

    def ablate_discoverers(self, pattern: Pattern, retire_stimulus: bool = True) -> list[int]:
        """Elimina a quienes experimentaron `pattern` y, opcionalmente, su estímulo físico."""
        victims = sorted(self.direct_discoverers.get(pattern, set()) & self.agents.keys())
        self._remove(victims)
        if retire_stimulus:
            self.env.retire_pattern_resources(pattern)
        return victims

    def snapshot(self) -> KnowledgeSnapshot:
        """Estado epistémico actual, sin ejecutar ticks ni tocar el acumulado de M2."""
        return knowledge_snapshot(
            self.agents, self.env.get_world_patterns(), self._neighbor_map(), self.config
        )
