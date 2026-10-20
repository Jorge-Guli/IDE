"""Motor de simulación: pipeline determinista de 5 fases sin coordinador cognitivo."""

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import cast

import numpy as np

from ide.agent.epistemology import is_known
from ide.agent.evolution import compute_metabolic_cost, transfer_cultural_heritage
from ide.agent.holon import (
    AgentNode,
    CompositeAgent,
    apply_downward_causation,
    best_beliefs,
    composite_nodes,
    evaluate_bond_candidates,
    prune_dead_leaves,
    reproduce_holon,
    should_split_holon,
)
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.extensions import CompositeRule, TrustStrategyPort
from ide.domain.ports import EnvironmentPort, EvolutionaryEnvironmentPort
from ide.domain.types import (
    ActionType,
    AgentAction,
    AgentGenome,
    KnowledgeUnit,
    Message,
    Observation,
    Pattern,
)
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.metrics import (
    EvolutionaryMetricsCollector,
    EvolutionaryTickMetrics,
    KnowledgeSnapshot,
    MetricsCollector,
    TickMetrics,
    correct_known_patterns,
    has_truthful_query_channel,
    judge_decision,
    knowledge_snapshot,
)
from ide.simulation.controls import nullify_belief

# Emisor sintético de los testimonios estigmérgicos (D27); los holones usan IDs <= -2 (D23).
STIGMERGY_SENDER_ID = -1

# Contexto de una resolución compuesta, fijado al empezar la Fase 4 (D27):
# (éxito, hojas que reciben la ganancia, holón raíz o None).
_CompositeContext = tuple[bool, list[int], CompositeAgent | None]


def _needs_evolutionary_env(config: SimulationConfig) -> bool:
    return (
        config.enable_evolution
        or config.enable_holonic_hierarchy
        or config.enable_stigmergy
        or config.num_composite_patterns > 0
    )


class SimulationEngine:
    """Orquesta el tiempo discreto. Un único generador, compartido con la grilla por defecto.

    Los mecanismos de la Fase II usan sus generadores derivados (D19) y sólo actúan con sus
    banderas activas: con los valores por defecto, `step()` reproduce bit a bit la Fase I.
    """

    def __init__(
        self,
        config: SimulationConfig,
        env: EnvironmentPort | None = None,
        trust_strategy: TrustStrategyPort | None = None,
    ) -> None:
        if config.enable_specialization:
            raise NotImplementedError("Especialización (Exp 004) fuera de alcance del Exp 001")
        if config.epsilon_recheck > 0 or config.tau_policy != "validation":
            raise NotImplementedError(
                "Mecanismos anti-trampa de evitación (Exp 005) fuera de alcance del Exp 001"
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
        # Dinámica evolutiva (mutación y ubicación de nacimientos) y donante neutral (D19).
        self.evo_rng = np.random.Generator(
            np.random.PCG64(np.random.SeedSequence(config.seed, spawn_key=(2,)))
        )
        self.donor_rng = np.random.Generator(
            np.random.PCG64(np.random.SeedSequence(config.seed, spawn_key=(4,)))
        )
        self.env: EnvironmentPort = env if env is not None else ToroidalGrid2D(config, self.rng)
        self._evo_env: EvolutionaryEnvironmentPort | None = (
            self.env if isinstance(self.env, EvolutionaryEnvironmentPort) else None
        )
        if self._evo_env is None and _needs_evolutionary_env(config):
            raise TypeError("los mecanismos de la Fase II exigen un EvolutionaryEnvironmentPort")
        self.agents: dict[int, MicroAgent] = {
            aid: MicroAgent(aid, config, trust_strategy) for aid in self.env.get_active_agent_ids()
        }
        self.direct_discoverers: dict[Pattern, set[int]] = defaultdict(set)
        self.collector = MetricsCollector(config)
        self.history: list[TickMetrics] = []
        self.next_tick: int = 0

        # Bosque holónico (D23, D24): al empezar, cada agente es su propio nodo raíz.
        self.root_nodes: dict[int, AgentNode] = dict(self.agents)
        self.agent_to_root: dict[int, int] = {aid: aid for aid in self.agents}
        self.next_holon_id: int = -2
        self.next_agent_id: int = max(self.agents) + 1 if self.agents else 0
        self.composite_completions: int = 0
        self.evo_collector = EvolutionaryMetricsCollector(config)
        self.evolutionary_history: list[EvolutionaryTickMetrics] = []
        self._composite_rules: dict[Pattern, CompositeRule] = (
            self._evo_env.get_composite_rules() if self._evo_env is not None else {}
        )

    @property
    def _evo(self) -> EvolutionaryEnvironmentPort:
        if self._evo_env is None:  # pragma: no cover - lo impide la validación de __init__
            raise TypeError("este entorno no implementa EvolutionaryEnvironmentPort")
        return self._evo_env

    # --- Tick ----------------------------------------------------------------------------------

    def step(self) -> TickMetrics:
        """Ejecuta el tick `next_tick` y lo incrementa."""
        tick = self.next_tick
        env = self.env
        config = self.config
        holonic = config.enable_holonic_hierarchy
        view = holonic and config.enable_holon_view
        rules = self._composite_rules
        order = cast(
            list[int],
            self.rng.permutation(np.array(sorted(self.agents), dtype=np.int64)).tolist(),  # pyright: ignore[reportUnknownMemberType]
        )
        # Nadie se mueve antes de la Fase 4: el alcance local vale para las fases 1 a 3.
        reach = self._local_reach() if holonic else {}

        # 1. Percepción y emisión, sobre la misma instantánea para todos.
        if view:
            self._sync_holon_view(reach, from_memory=True)
        observations: dict[int, Observation] = {}
        emitted: list[Message] = []
        for aid in order:
            observations[aid] = env.get_observation(aid, tick)
            emitted += self.agents[aid].perceive_and_emit_messages(observations[aid], tick)
        if config.enable_stigmergy:
            self._assimilate_stigmergy(tick)

        # 2. Intercambio social en dos pasadas.
        messages_sent = 0
        responses: list[Message] = []
        if config.comm_enabled:
            # Nadie se mueve entre las fases 1 y 2: los vecinos de la observación son los del
            # ruteo, sin volver a recorrer la vecindad (Decisión 18).
            neighbors = {aid: observations[aid].neighbor_ids for aid in order}
            for aid, inbox in self._route(emitted, neighbors, order).items():
                responses += self.agents[aid].process_incoming_messages(inbox, tick)
            for aid, inbox in self._route(responses, neighbors, order).items():
                if self.agents[aid].process_incoming_messages(inbox, tick):
                    raise RuntimeError("la segunda pasada no debe generar respuestas")
            messages_sent = len(emitted) + len(responses)
        if view:
            self._sync_holon_view(reach, from_memory=False)

        # 3. Decisión sobre la observación de la fase 1; M2 juzga la intención, sólo sobre
        # recursos elementales (D25.3).
        actions: dict[int, AgentAction] = {}
        composite_intents: dict[int, Pattern] = {}
        opportunities = correct = 0
        for aid in order:
            truth = env.get_reachable_true_values(aid)
            action = actions[aid] = self.agents[aid].decide_action(
                observations[aid], tick, self.rng
            )
            if rules:
                composite = {
                    res.resource_id: res.pattern
                    for res in observations[aid].visible_resources
                    if res.is_reachable_now and res.pattern in rules
                }
                if composite:
                    truth = {rid: value for rid, value in truth.items() if rid not in composite}
                    target = action.target
                    if action.action_type is ActionType.INTERACT and target in composite:
                        composite_intents[aid] = composite[cast(int, target)]
                        truth = {}
            if truth:
                opportunities += 1
                correct += judge_decision(action, truth)
        # Estado al empezar la Fase 4: la permutación no altera la resolución compuesta (D27).
        contexts = {
            aid: self._composite_context(aid, rules[pattern], reach)
            for aid, pattern in composite_intents.items()
        }

        # 4. Ejecución y aprendizaje directo; los conflictos se resuelven por `order`.
        moved: set[int] = set()
        surplus: set[int] = set()
        for aid in order:
            result = env.execute_action(aid, actions[aid], tick)
            if result.action_type is ActionType.MOVE:
                moved.add(aid)
            pattern, value = result.interacted_pattern, result.experienced_value
            if value is None or pattern is None:
                continue
            if pattern in rules:
                self._resolve_composite(aid, pattern, rules[pattern], contexts[aid], tick, surplus)
                continue
            agent = self.agents[aid]
            agent.learn_from_experience(pattern, value, tick)
            self.direct_discoverers[pattern].add(aid)
            if config.enable_evolution:
                agent.apply_energy_delta(config.energy_gain_scale * value)
            if config.enable_stigmergy and config.stigmergy_deposit_rate > 0:
                learned = agent.memory.get(pattern)
                if learned is not None:  # siempre presente: la experiencia se fuerza en memoria
                    self._evo.deposit_stigmergy(aid, pattern, value, learned.confidence, tick)

        # 5. Mantenimiento y telemetría, con los vecinos posteriores al movimiento.
        for aid in order:
            self.agents[aid].decay_memory(tick)
        births = deaths = 0
        if holonic:
            self._coordinate_and_split(tick, surplus)
            self._bond(tick)
        if config.enable_evolution:
            # Sin comunicación ningún mensaje se envía: no hay costo de mensajes (D21).
            sent = Counter(msg.sender_id for msg in (*emitted, *responses))
            if not config.comm_enabled:
                sent.clear()
            deaths = self._metabolize(tick, moved, sent)
            births = self._reproduce(tick)
        if holonic:
            self._apply_downward_causation()
        env.step_dynamics(tick)
        world = env.get_world_patterns()
        metrics = self.collector.record_tick(
            tick,
            self.agents,
            world,
            self._neighbor_map(),
            opportunities,
            correct,
            messages_sent,
        )
        self.history.append(metrics)
        self.evolutionary_history.append(
            self.evo_collector.record_tick(
                tick,
                self.agents,
                self.root_nodes,
                world,
                births,
                deaths,
                self.composite_completions,
                self._evo_env.get_active_stigmergy_cells() if self._evo_env is not None else 0,
            )
        )
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

    # --- Fase II: canales de conocimiento (R19, R22) -------------------------------------------

    def _local_reach(self) -> dict[int, list[int]]:
        """Para cada hoja de un holón raíz, las otras hojas en alcance local (D24.1), ordenadas."""
        env = self._evo
        reach: dict[int, list[int]] = {}
        for nid in sorted(self.root_nodes):
            node = self.root_nodes[nid]
            if not isinstance(node, CompositeAgent):
                continue
            leaves = node.leaf_agents
            for leaf in leaves:
                reach[leaf.agent_id] = []
            for i, a in enumerate(leaves):
                for b in leaves[i + 1 :]:
                    limit = max(a.genome.comm_radius, b.genome.comm_radius) + 1
                    if env.get_agent_distance(a.agent_id, b.agent_id) <= limit:
                        reach[a.agent_id].append(b.agent_id)
                        reach[b.agent_id].append(a.agent_id)
        return reach

    def _sync_holon_view(self, reach: Mapping[int, list[int]], from_memory: bool) -> None:
        """Vista del holón (R22, D25.2): primero calcula todas las vistas, después inyecta."""
        beliefs = {
            aid: (
                self.agents[aid].collective_memory()
                if from_memory
                else self.agents[aid].own_beliefs()
            )
            for aid in reach
        }
        views = {
            aid: best_beliefs({other: beliefs[other] for other in others})
            for aid, others in reach.items()
        }
        null = self.config.comm_content_null
        for aid in sorted(self.agents):
            agent = self.agents[aid]
            agent.clear_holon_beliefs()
            for unit in views.get(aid, {}).values():
                agent.inject_ephemeral_belief(nullify_belief(unit, self.null_rng) if null else unit)

    def _assimilate_stigmergy(self, tick: int) -> None:
        """Rastros de la celda como testimonios del emisor sintético (R19, D27.3)."""
        env = self._evo
        null = self.config.comm_content_null
        for aid in sorted(self.agents):
            for trace in env.get_cell_stigmergy(aid):
                unit = KnowledgeUnit(
                    trace.pattern,
                    trace.sign_value,
                    trace.intensity,
                    1,
                    trace.last_updated_tick,
                    False,
                )
                if null:
                    unit = nullify_belief(unit, self.null_rng)
                self.agents[aid].assimilate_testimony(unit, STIGMERGY_SENDER_ID, tick)

    # --- Fase II: recursos compuestos (D25.3, D27.2) -------------------------------------------

    def _composite_context(
        self, aid: int, rule: CompositeRule, reach: Mapping[int, list[int]]
    ) -> _CompositeContext:
        root = self.root_nodes[self.agent_to_root[aid]]
        holon = root if isinstance(root, CompositeAgent) else None
        local = sorted([aid, *reach[aid]]) if holon is not None else [aid]
        config = self.config
        known = {
            pattern
            for pattern in rule.required_patterns
            for leaf in local
            if is_known(belief := self.agents[leaf].own_belief(pattern), config)
            and belief.predicted_value > 0
        }
        return rule.evaluate(known) is not None, local, holon

    def _resolve_composite(
        self,
        aid: int,
        pattern: Pattern,
        rule: CompositeRule,
        context: _CompositeContext,
        tick: int,
        surplus: set[int],
    ) -> None:
        config = self.config
        agent = self.agents[aid]
        success, local, holon = context
        if not success:
            agent.learn_from_experience(pattern, -config.composite_failure_penalty, tick)
            if config.enable_evolution:
                agent.apply_energy_delta(
                    -config.energy_gain_scale * config.composite_failure_penalty
                )
            return
        agent.learn_from_experience(pattern, 1.0, tick)
        self.composite_completions += 1
        if holon is not None:
            holon.cooperative_completions += 1
            holon.ticks_without_surplus = 0
            surplus.add(holon.node_id)
        if config.enable_evolution:
            sharers = local if holon is not None and config.holon_energy_sharing else [aid]
            gain = config.energy_gain_scale * rule.composite_value / len(sharers)
            for leaf in sharers:
                self.agents[leaf].apply_energy_delta(gain)

    # --- Fase II: Fase 5 holónica (R15, R16, R18, R23) -----------------------------------------

    def _coordinate_and_split(self, tick: int, surplus: set[int]) -> None:
        """Costo de coordinación, superávit y SPLIT de cada holón raíz, por `node_id` (D24.2)."""
        config = self.config
        reach = self._local_reach()
        for nid in sorted(self.root_nodes):
            node = self.root_nodes[nid]
            if not isinstance(node, CompositeAgent):
                continue
            leaves = node.leaf_agents
            if config.enable_evolution:
                share = config.holon_coord_cost * node.holon_level  # c_coord(U) / |U|
                for leaf in leaves:
                    leaf.apply_energy_delta(-share)
            if nid in surplus or self._has_knowledge_surplus(node, reach):
                node.ticks_without_surplus = 0
            else:
                node.ticks_without_surplus += 1
            if should_split_holon(node, config):
                del self.root_nodes[nid]
                for child in node.children:
                    if isinstance(child, CompositeAgent):
                        # Su contador no corrió mientras estuvo anidado (D24.2).
                        child.ticks_without_surplus = 0
                    self._set_root(child)

    def _has_knowledge_surplus(self, holon: CompositeAgent, reach: Mapping[int, list[int]]) -> bool:
        """La mayor componente conexa de alcance local sabe más que la mejor hoja (D24.2)."""
        threshold = self.config.decision_conf_threshold
        known = {
            leaf.agent_id: frozenset(
                u.pattern for u in leaf.memory.all_units() if u.confidence >= threshold
            )
            for leaf in holon.leaf_agents
        }
        components: list[list[int]] = []
        seen: set[int] = set()
        for start in sorted(known):
            if start in seen:
                continue
            component: list[int] = []
            stack = [start]
            seen.add(start)
            while stack:
                current = stack.pop()
                component.append(current)
                for other in reach[current]:
                    if other not in seen:
                        seen.add(other)
                        stack.append(other)
            components.append(sorted(component))
        largest = max(components, key=lambda c: (len(c), -c[0]))
        collective = frozenset[Pattern]().union(*(known[aid] for aid in largest))
        return len(collective) > max(len(k) for k in known.values())

    def _bond(self, tick: int) -> None:
        """BOND (R15, D24.3) entre nodos raíz con hojas a distancia <= 1."""
        roots = [self.root_nodes[nid] for nid in sorted(self.root_nodes)]
        for a, b in evaluate_bond_candidates(roots, self._adjacent_root_pairs(), self.config):
            children = (self.root_nodes.pop(a), self.root_nodes.pop(b))
            holon = CompositeAgent(self._take_holon_id(), children, tick, True)
            holon.formation_knowledge = self._formation_knowledge(holon)
            self._set_root(holon)

    def _adjacent_root_pairs(self) -> list[tuple[int, int]]:
        env = self._evo
        pairs: set[tuple[int, int]] = set()
        everyone = sorted(self.agents)
        for a in everyone:
            root_a = self.agent_to_root[a]
            # Con radio de comunicación >= 1, los vecinos incluyen a todos los de distancia 1.
            radius = self.agents[a].genome.comm_radius
            candidates = env.get_communication_neighbors(a) if radius >= 1 else everyone
            for b in candidates:
                root_b = self.agent_to_root[b]
                pair = (min(root_a, root_b), max(root_a, root_b))
                if root_a != root_b and pair not in pairs and env.get_agent_distance(a, b) <= 1:
                    pairs.add(pair)
        return sorted(pairs)

    def _apply_downward_causation(self) -> None:
        """R18 sobre el bosque actual; los nodos raíz de nivel 0 quedan sin penalización."""
        reach = self._local_reach()
        for nid in sorted(self.root_nodes):
            node = self.root_nodes[nid]
            if isinstance(node, CompositeAgent):
                local = {leaf.agent_id: reach[leaf.agent_id] for leaf in node.leaf_agents}
                apply_downward_causation(node, local, self.config)
            else:
                cast(MicroAgent, node).memory.set_redundant_patterns(frozenset(), 1.0)

    def _set_root(self, node: AgentNode) -> None:
        self.root_nodes[node.node_id] = node
        for leaf in node.leaf_agents:
            self.agent_to_root[leaf.agent_id] = node.node_id

    def _take_holon_id(self) -> int:
        node_id = self.next_holon_id
        self.next_holon_id -= 1
        return node_id

    def _formation_knowledge(
        self, holon: CompositeAgent, world: Mapping[Pattern, float] | None = None
    ) -> tuple[tuple[int, frozenset[Pattern]], ...]:
        """K de M13 de cada hoja al formarse o reiniciarse el holón (M13, D28)."""
        world = self.env.get_world_patterns() if world is None else world
        return tuple(
            (leaf.agent_id, correct_known_patterns(leaf, world, self.config))
            for leaf in holon.leaf_agents
        )

    # --- Fase II: metabolismo, muerte y reproducción (R12-R14, R17, R20, R21) -----------------

    def _metabolize(self, tick: int, moved: set[int], sent: Mapping[int, int]) -> int:
        """Cobra el costo basal, de movimiento y de mensajes; elimina a quien queda en E <= 0."""
        config = self.config
        for aid in sorted(self.agents):
            agent = self.agents[aid]
            cost = compute_metabolic_cost(agent.genome, config)
            cost += config.move_cost * (aid in moved) + config.message_cost * sent.get(aid, 0)
            agent.apply_energy_delta(-cost)
        dead = [aid for aid in sorted(self.agents) if self.agents[aid].energy <= 0]
        if dead:
            self._remove(dead, tick)
        return len(dead)

    def _reproduce(self, tick: int) -> int:
        """R17 y luego R12 (o su ablación neutral), a lo sumo un evento por agente (D26)."""
        config = self.config
        reproduced: set[int] = set()
        neutral = config.reproduction_mode == "neutral"
        donors = [self.agents[aid] for aid in sorted(self.agents)] if neutral else []
        births = 0
        if config.enable_holonic_hierarchy and config.enable_holon_reproduction:
            for nid in sorted(self.root_nodes):
                node = self.root_nodes[nid]
                if not isinstance(node, CompositeAgent):
                    continue
                leaves = node.leaf_agents
                if any(leaf.agent_id in reproduced for leaf in leaves):
                    continue
                if node.total_energy < len(leaves) * config.reproduction_threshold:
                    continue
                if len(self.agents) + len(leaves) > config.max_population:
                    continue
                offspring = {leaf.agent_id: self._give_birth(leaf, tick) for leaf in leaves}
                child = reproduce_holon(node, offspring, self._take_holon_id, tick)
                world = self.env.get_world_patterns()
                for replica in composite_nodes(child):
                    replica.formation_knowledge = self._formation_knowledge(replica, world)
                self._set_root(child)
                reproduced.update(offspring)
                reproduced.update(c.agent_id for c in offspring.values())
                births += len(offspring)
        for aid in sorted(self.agents):
            agent = self.agents[aid]
            if aid in reproduced or agent.energy < config.reproduction_threshold:
                continue
            if len(self.agents) >= config.max_population:
                break
            source = donors[int(self.donor_rng.integers(len(donors)))].genome if neutral else None
            child = self._give_birth(agent, tick, source)
            self._set_root(child)
            reproduced.update((aid, child.agent_id))
            births += 1
        return births

    def _give_birth(
        self, parent: MicroAgent, tick: int, genome_source: AgentGenome | None = None
    ) -> MicroAgent:
        """Hijo con ID nuevo, ubicado junto al progenitor y con su herencia cultural (D22, D26)."""
        child = parent.create_offspring(self.next_agent_id, tick, self.evo_rng, genome_source)
        self.next_agent_id += 1
        genome = child.genome
        self._evo.spawn_agent_near(
            child.agent_id,
            parent.agent_id,
            self.evo_rng,
            genome.perception_radius,
            genome.comm_radius,
        )
        null = self.config.comm_content_null
        heritage = transfer_cultural_heritage(
            parent.memory, child.memory.capacity, tick, child.config
        )
        for belief in heritage:
            if null:
                belief = nullify_belief(belief, self.null_rng)
            child.assimilate_testimony(belief, parent.agent_id, tick)
        self.agents[child.agent_id] = child
        return child

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

    def _remove(self, victims: list[int], tick: int | None = None) -> None:
        """Elimina agentes y poda el bosque holónico (D21).

        Un holón que sobrevive con menos hojas reinicia su estado de formación (M13, D28) en
        `tick`, o en `next_tick` si la poda la pide una perturbación entre pasos.
        """
        affected = sorted({self.agent_to_root[aid] for aid in victims})
        before = [
            (node, len(node.leaf_agents))
            for nid in affected
            for node in composite_nodes(self.root_nodes[nid])
        ]
        for aid in victims:
            del self.agents[aid]
            del self.agent_to_root[aid]
        self.env.remove_agents(victims)
        alive = set(self.agents)
        survivors: set[int] = set()
        for nid in affected:
            pruned = prune_dead_leaves(self.root_nodes.pop(nid), alive)
            if pruned is not None:
                self._set_root(pruned)
                survivors.update(id(node) for node in composite_nodes(pruned))
        formation_tick = self.next_tick if tick is None else tick
        for node, size in before:
            if id(node) in survivors and len(node.leaf_agents) < size:
                node.formation_knowledge = self._formation_knowledge(node)
                node.formation_tick = formation_tick
        if tick is None and self.config.enable_holonic_hierarchy:
            # Entre pasos: las hojas liberadas pierden la penalización de R18 antes del tick.
            self._apply_downward_causation()

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
