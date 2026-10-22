"""Motor de simulación: pipeline determinista de sistemas sin coordinador cognitivo (D44)."""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import cast

import numpy as np

from ide.agent.dna import plasticity_active
from ide.agent.epistemology import is_known
from ide.agent.evolution import (
    compute_dna_cost,
    compute_metabolic_cost,
    compute_senescence_cost,
    compute_sos_scale,
    transfer_cultural_heritage,
)
from ide.agent.holon import (
    AgentNode,
    CompositeAgent,
    apply_downward_causation,
    assign_epigenetic_roles,
    best_beliefs,
    composite_nodes,
    evaluate_bond_candidates,
    is_effectively_locked,
    prune_dead_leaves,
    reproduce_holon,
    should_lock_holon,
    should_split_holon,
)
from ide.agent.micro_agent import MicroAgent
from ide.agent.policy import GeneticPolicy
from ide.config import (
    SimulationConfig,
    epigenetic_roles_active,
    genetic_policy_active,
    sporulation_active,
    stress_energy_limit,
    symbiotic_ratchet_active,
)
from ide.domain.extensions import CompositeRule, TrustStrategyPort
from ide.domain.ports import (
    EcologicalEnvironmentPort,
    EnvironmentPort,
    EvolutionaryEnvironmentPort,
)
from ide.domain.types import (
    EpigeneticContext,
    EpigeneticRole,
    KnowledgeUnit,
    Message,
    Pattern,
    counts_as_knowledge,
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
from ide.simulation.pipeline import (
    CompositeContext,
    EngineSystem,
    TickFrame,
    TickObserver,
    build_systems,
    carcasses_active,
    energy_transfer_active,
    predation_active,
)

# Emisor sintético de los testimonios estigmérgicos (D27); los holones usan IDs <= -2 (D23).
STIGMERGY_SENDER_ID = -1


def _needs_evolutionary_env(config: SimulationConfig) -> bool:
    return (
        config.enable_evolution
        or config.enable_holonic_hierarchy
        or config.enable_stigmergy
        or config.num_composite_patterns > 0
    )


def _needs_ecological_env(config: SimulationConfig) -> bool:
    """Ecología del entorno (D48, precisiones 79 y 82): R33 y R34 siempre; R35 sólo con evolución;
    y la percepción social de R32 (`get_visible_agents`, D47.3) con la política genética
    efectivamente activa.

    Sin evolución no hay muertes y R35 es inerte (D52.3): no exige el puerto ecológico.
    """
    return (
        config.enable_resource_depletion
        or config.enable_heterogeneity
        or carcasses_active(config)
        or genetic_policy_active(config)
    )


class TickMetricsObserver:
    """Produce `TickMetrics` (M1 a M7) en `frame.tick_metrics` y `engine.history` (D44.2).

    Juzga M2 en `on_decisions`, antes de ejecutar las acciones, con el oráculo
    `get_reachable_true_values` y sólo sobre recursos elementales (D25.3): un agente con un
    compuesto alcanzable (`frame.composite_reachable`) no cuenta esos recursos, y si decide
    consumir uno, no cuenta el tick. El oráculo es exclusivo del motor; por eso este observador
    vive en `engine.py` (precisión 72). No guarda estado propio: todo queda en el `TickFrame`.
    """

    def on_decisions(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        env = engine.env
        reachable, intents = frame.composite_reachable, frame.composite_intents
        opportunities = correct = 0
        for aid in frame.active_order:  # R28 (D38): una dormida no decide, no hay oportunidad
            truth = env.get_reachable_true_values(aid)
            composite = reachable.get(aid)
            if composite:
                if aid in intents:
                    truth = {}
                else:
                    truth = {rid: v for rid, v in truth.items() if rid not in composite}
            if truth:
                opportunities += 1
                correct += judge_decision(frame.actions[aid], truth)
        frame.decision_opportunities, frame.correct_decisions = opportunities, correct

    def on_tick_end(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        frame.tick_metrics = engine.collector.record_tick(
            frame.tick,
            engine.agents,
            frame.world_patterns,
            engine._neighbor_map(),  # pyright: ignore[reportPrivateUsage]
            frame.decision_opportunities,
            frame.correct_decisions,
            frame.messages_sent,
        )
        engine.history.append(frame.tick_metrics)


class EvolutionaryMetricsObserver:
    """Produce `EvolutionaryTickMetrics` (M8 a M14) en `engine.evolutionary_history` (D44.2)."""

    def on_decisions(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        """Las métricas evolutivas sólo miran el final del tick."""

    def on_tick_end(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        evo_env = engine._evo_env  # pyright: ignore[reportPrivateUsage]
        engine.evolutionary_history.append(
            engine.evo_collector.record_tick(
                frame.tick,
                engine.agents,
                engine.root_nodes,
                frame.world_patterns,
                frame.births,
                frame.deaths,
                engine.composite_completions,
                evo_env.get_active_stigmergy_cells() if evo_env is not None else 0,
            )
        )


class SimulationEngine:
    """Orquesta el tiempo discreto. Un único generador, compartido con la grilla por defecto.

    Los mecanismos de la Fase II usan sus generadores derivados (D19) y sólo actúan con sus
    banderas activas: con los valores por defecto, `step()` reproduce bit a bit la Fase I.
    Con `enable_compact_dna` (R24, design D34), cada tick empieza por la Fase 0 de expresión
    del fenotipo; sin la bandera, no corre y la Fase II no cambia en un bit.

    El tick lo ejecutan los sistemas de `build_systems(config)` (`systems`, design D44) y la
    telemetría la producen los observadores: `metrics_observer`, obligatorio porque produce el
    `TickMetrics` que devuelve `step()`, y después los de `observers`. Los métodos auxiliares de
    este módulo son las piezas que comparten los sistemas y las perturbaciones.
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
        if _needs_ecological_env(config) and not isinstance(self.env, EcologicalEnvironmentPort):
            raise TypeError(
                "la ecología del entorno (R33-R35) y la percepción social (R32) exigen un "
                "EcologicalEnvironmentPort"
            )
        # R35 efectivamente activa (precisión 78): la leen el paso de muerte y la ejecución.
        self.carcasses_active = carcasses_active(config)
        # R32 efectivamente activa (precisión 31): los fundadores deciden con `GeneticPolicy`
        # (D45.4) y la Fase 1 construye su percepción social (D47.3); si no, `HandwrittenPolicy`.
        self.genetic_policy_active = genetic_policy_active(config)
        # R36 y R37 efectivamente activas (D52.3, precisión 83): la Fase 4 ejecuta `SHARE` y
        # `ATTACK`; sin ellas, la grilla los ejecuta como `IDLE`.
        self.energy_transfer_active = energy_transfer_active(config)
        self.predation_active = predation_active(config)
        # R28 efectivamente activa (precisión 30): germinación, física y costo de la endospora.
        self.sporulation_active = sporulation_active(config)
        # R40 efectivamente activa (D59): la Fase 4 aplica la regla de aprendizaje tras cada acción.
        self.plasticity_active = plasticity_active(config)
        # R41 (D60.4): por receptor, el OR de los símbolos emitidos en la Fase 3 del tick anterior
        # por los emisores de los que era vecino de comunicación; lo consume la Fase 1.
        self.pending_signals: dict[int, int] = {}
        # R41: los agentes con máscara percibida no nula, ascendentes; la Fase 1 siguiente los
        # pone en 0 antes de asignar las máscaras nuevas, sin recorrer a toda la población.
        self.signal_receivers: tuple[int, ...] = ()
        # `GeneticPolicy` no guarda estado: una sola instancia sirve a todos los fundadores.
        policy = GeneticPolicy() if self.genetic_policy_active else None
        self.agents: dict[int, MicroAgent] = {
            aid: MicroAgent(aid, config, trust_strategy, policy=policy)
            for aid in self.env.get_active_agent_ids()
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
        # R25 y R31 efectivamente activas (D36, D50.3): la asignación de roles de la Fase 5 y la
        # impronta; el sello, la protección contra SPLIT y el descuento de coordinación.
        self.epigenetic_roles_active = epigenetic_roles_active(config)
        self.symbiotic_ratchet_active = symbiotic_ratchet_active(config)
        # R25 (D36): de cada raíz, el conjunto de hojas que tenía en su última asignación.
        self._role_leaf_sets: dict[int, frozenset[int]] = {}
        self.evo_collector = EvolutionaryMetricsCollector(config)
        self.evolutionary_history: list[EvolutionaryTickMetrics] = []
        self._composite_rules: dict[Pattern, CompositeRule] = (
            self._evo_env.get_composite_rules() if self._evo_env is not None else {}
        )
        # Motor por sistemas (D44): la lista de sistemas es fija para la configuración.
        self.systems: tuple[EngineSystem, ...] = build_systems(config)
        self.metrics_observer = TickMetricsObserver()
        self.observers: list[TickObserver] = [EvolutionaryMetricsObserver()]

    @property
    def _evo(self) -> EvolutionaryEnvironmentPort:
        if self._evo_env is None:  # pragma: no cover - lo impide la validación de __init__
            raise TypeError("este entorno no implementa EvolutionaryEnvironmentPort")
        return self._evo_env

    # --- Tick ----------------------------------------------------------------------------------

    def step(self) -> TickMetrics:
        """Ejecuta el tick `next_tick` con los sistemas de `build_systems` y lo incrementa (D44).

        Los observadores (`metrics_observer` primero y después los de `observers`) reciben
        `on_decisions` inmediatamente después del sistema marcado con `notifies_decisions`, antes
        de ejecutar ninguna acción, y `on_tick_end` al final del tick, con `frame.world_patterns`
        ya calculado. Si `metrics_observer` no produce el `TickMetrics`, el tick falla antes de
        notificar a los demás observadores y de incrementar `next_tick`, para que ningún
        historial quede desalineado.
        """
        frame = TickFrame(self.next_tick)
        metrics_observer, observers = self.metrics_observer, self.observers
        for system in self.systems:
            system.run(self, frame)
            if system.notifies_decisions:
                metrics_observer.on_decisions(self, frame)
                for observer in observers:
                    observer.on_decisions(self, frame)
        frame.world_patterns = self.env.get_world_patterns()
        metrics_observer.on_tick_end(self, frame)
        metrics = frame.tick_metrics
        if metrics is None:
            raise RuntimeError("metrics_observer no produjo el TickMetrics del tick")
        for observer in observers:
            observer.on_tick_end(self, frame)
        self.next_tick += 1
        return metrics

    def run(self, ticks: int) -> list[TickMetrics]:
        """Ejecuta `ticks` ticks y devuelve sus métricas."""
        return [self.step() for _ in range(ticks)]

    def _route(
        self,
        messages: list[Message],
        neighbors: Mapping[int, Sequence[int]],
        order: list[int],
        dormant: frozenset[int] = frozenset(),
    ) -> dict[int, list[Message]]:
        """Bandejas por agente, en `order`; cada entrega del control nulo es una extracción.

        Las endosporas dormidas del tick (`frame.dormant`, R28, D38) no tienen bandeja: no reciben
        en ninguna pasada ni consumen extracciones del control nulo.
        """
        inboxes: dict[int, list[Message]] = {aid: [] for aid in order if aid not in dormant}
        null = self.config.comm_content_null
        for msg in messages:
            reach: Sequence[int] = neighbors[msg.sender_id]
            if msg.recipient_id is not None:
                reach = [msg.recipient_id] if msg.recipient_id in reach else []
            for receiver in reach:
                if receiver in dormant:
                    continue
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

    # --- Fase II-B: expresión del fenotipo (R24) ----------------------------------------------

    def _express_phenotypes(self, tick: int) -> None:
        """Fase 0 (design D34.4): expresa el ADN de cada agente en su contexto del tick.

        El contexto se arma con el estado de fin del tick anterior: el nivel del holón raíz que
        contiene a la hoja (0 si es su propia raíz), su rol epigenético y su energía relativa al
        umbral de reproducción. La expresión de un agente no altera el contexto de otro, así que
        el recorrido por `agent_id` no introduce efectos de orden, y no consume generadores. El
        entorno sólo se actualiza cuando cambian los radios expresados.
        """
        env = self._evo
        threshold = self.config.reproduction_threshold
        # Un nivel por raíz: `holon_level` recorre el árbol, y todas sus hojas lo comparten.
        levels = {nid: node.holon_level for nid, node in self.root_nodes.items()}
        for aid in sorted(self.agents):
            agent = self.agents[aid]
            context = EpigeneticContext(
                levels[self.agent_to_root[aid]],
                agent.epigenetic_role,
                agent.energy / threshold,
            )
            if agent.express(context, tick):
                genome = agent.genome
                env.set_agent_radii(aid, genome.perception_radius, genome.comm_radius)

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

    def _sync_holon_view(
        self,
        reach: Mapping[int, list[int]],
        from_memory: bool,
        inactive: frozenset[int] = frozenset(),
    ) -> None:
        """Vista del holón (R22, D25.2): primero calcula todas las vistas, después inyecta.

        Las hojas de `inactive` (endosporas inactivas, R28, D38) no aportan creencias ni reciben
        vista, así que tampoco consumen `null_rng` por ella; su vista anterior se borra igual.
        """
        beliefs = {
            aid: (
                self.agents[aid].collective_memory()
                if from_memory
                else self.agents[aid].own_beliefs()
            )
            for aid in reach
            if aid not in inactive
        }
        views = {
            aid: best_beliefs({other: beliefs[other] for other in others if other not in inactive})
            for aid, others in reach.items()
            if aid not in inactive
        }
        null = self.config.comm_content_null
        for aid in sorted(self.agents):
            agent = self.agents[aid]
            agent.clear_holon_beliefs()
            for unit in views.get(aid, {}).values():
                agent.inject_ephemeral_belief(nullify_belief(unit, self.null_rng) if null else unit)

    def _assimilate_stigmergy(self, tick: int, dormant: frozenset[int] = frozenset()) -> None:
        """Rastros de la celda como testimonios del emisor sintético (R19, D27.3)."""
        env = self._evo
        null = self.config.comm_content_null
        for aid in sorted(self.agents):
            if aid in dormant:
                continue  # R28 (D38): una endospora dormida no asimila estigmergia
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
        self,
        aid: int,
        rule: CompositeRule,
        reach: Mapping[int, list[int]],
        dormant: frozenset[int] = frozenset(),
    ) -> CompositeContext:
        """Éxito, hojas que reciben la ganancia y holón raíz de una resolución compuesta (D27).

        Las endosporas dormidas del tick (`dormant`, R28, D38) no cuentan: ni su conocimiento
        resuelve el compuesto ni reciben parte de la ganancia.
        """
        root = self.root_nodes[self.agent_to_root[aid]]
        holon = root if isinstance(root, CompositeAgent) else None
        local = (
            sorted(leaf for leaf in (aid, *reach[aid]) if leaf not in dormant)
            if holon is not None
            else [aid]
        )
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
        context: CompositeContext,
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
        """Costo de coordinación, superávit y SPLIT de cada holón raíz, por `node_id` (D24.2).

        Con $R_{31}$ (D50.3, precisiones 8 y 19), antes del costo y de `SPLIT` la raíz no
        soldada se suelda si sus hojas se comprometen (`should_lock_holon`); el costo de una raíz
        soldada se multiplica por `lock_coord_discount`, y `should_split_holon` no la parte.
        """
        config = self.config
        reach = self._local_reach()
        for nid in sorted(self.root_nodes):
            node = self.root_nodes[nid]
            if not isinstance(node, CompositeAgent):
                continue
            leaves = node.leaf_agents
            if should_lock_holon(node, config, leaves):
                node.is_locked = True
            if config.enable_evolution:
                share = config.holon_coord_cost * node.holon_level  # c_coord(U) / |U|
                if is_effectively_locked(node, config):  # sólo la raíz da descuento (prec. 8)
                    share *= config.lock_coord_discount
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
        """La mayor componente conexa de alcance local sabe más que la mejor hoja (D24.2).

        Sólo cuentan los patrones que `counts_as_knowledge`: comer carroña no sostiene un holón
        (D48.3, precisión 80).
        """
        threshold = self.config.decision_conf_threshold
        known = {
            leaf.agent_id: frozenset(
                u.pattern
                for u in leaf.memory.all_units()
                if u.confidence >= threshold and counts_as_knowledge(u.pattern)
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

    def _bond(self, tick: int, dormant: frozenset[int] = frozenset()) -> None:
        """BOND (R15, D24.3) entre nodos raíz con hojas activas a distancia <= 1.

        Una endospora dormida del tick (`dormant`, R28, D38) no forma holones nuevos: no cuenta
        como hoja adyacente. Sigue en su holón, que puede unirse por la adyacencia de otras hojas.
        """
        roots = [self.root_nodes[nid] for nid in sorted(self.root_nodes)]
        pairs = self._adjacent_root_pairs(dormant)
        for a, b in evaluate_bond_candidates(roots, pairs, self.config):
            children = (self.root_nodes.pop(a), self.root_nodes.pop(b))
            holon = CompositeAgent(self._take_holon_id(), children, tick, True)
            holon.formation_knowledge = self._formation_knowledge(holon)
            self._set_root(holon)

    def _adjacent_root_pairs(self, dormant: frozenset[int] = frozenset()) -> list[tuple[int, int]]:
        env = self._evo
        pairs: set[tuple[int, int]] = set()
        everyone = [aid for aid in sorted(self.agents) if aid not in dormant]
        for a in everyone:
            root_a = self.agent_to_root[a]
            # Con radio de comunicación >= 1, los vecinos incluyen a todos los de distancia 1.
            radius = self.agents[a].genome.comm_radius
            candidates = env.get_communication_neighbors(a) if radius >= 1 else everyone
            for b in candidates:
                if b in dormant:
                    continue
                root_b = self.agent_to_root[b]
                pair = (min(root_a, root_b), max(root_a, root_b))
                if root_a != root_b and pair not in pairs and env.get_agent_distance(a, b) <= 1:
                    pairs.add(pair)
        return sorted(pairs)

    def _apply_downward_causation(self) -> dict[int, list[int]]:
        """R18 sobre el bosque actual; los nodos raíz de nivel 0 quedan sin penalización.

        Devuelve el alcance local que usó, para que la asignación de roles de $R_{25}$ del mismo
        paso no lo recalcule (precisión 110).
        """
        reach = self._local_reach()
        for nid in sorted(self.root_nodes):
            node = self.root_nodes[nid]
            if isinstance(node, CompositeAgent):
                local = {leaf.agent_id: reach[leaf.agent_id] for leaf in node.leaf_agents}
                apply_downward_causation(node, local, self.config)
            else:
                cast(MicroAgent, node).memory.set_redundant_patterns(frozenset(), 1.0)
        return reach

    def _assign_epigenetic_roles(self, reach: Mapping[int, list[int]] | None = None) -> None:
        """R25 (D36): roles de las raíces cuya composición cambió, tras R18 en la Fase 5.

        Recorre las raíces por `node_id`: un holón sin entrada en `_role_leaf_sets` o con otro
        conjunto de hojas recibe roles nuevos (`assign_epigenetic_roles`, con el alcance local
        de D25.1: `reach` si quien llama ya lo calculó, el de R18 del mismo paso); las hojas que
        dejaron de estar en una raíz compuesta vuelven a `NONE`; las entradas de raíces que ya
        no existen se descartan. Los roles se escriben después de calcularlos todos. No consume
        generadores. Sólo escribe `NONE` en las hojas de las entradas que cambiaron o
        desaparecieron: un rol distinto de `NONE` siempre pertenece a una entrada registrada, o
        a una réplica sin registrar que este mismo paso recalcula (precisiones 110 y 111).
        """
        previous = self._role_leaf_sets
        roles: dict[int, EpigeneticRole] = {}
        leaf_sets: dict[int, frozenset[int]] = {}
        for nid in sorted(self.root_nodes):
            node = self.root_nodes[nid]
            if not isinstance(node, CompositeAgent):
                continue
            leaves = node.leaf_agents
            current = frozenset(leaf.agent_id for leaf in leaves)
            leaf_sets[nid] = current
            if previous.get(nid) == current:
                continue
            if reach is None:  # sólo si alguna raíz cambió
                reach = self._local_reach()
            local = {leaf.agent_id: reach[leaf.agent_id] for leaf in leaves}
            roles.update(assign_epigenetic_roles(node, local, self.config))
        released: set[int] = set()
        for nid, old in previous.items():
            if leaf_sets.get(nid) != old:
                released.update(old)
        for aid in sorted(released):  # hojas que quedaron como su propia raíz
            if aid not in roles and aid in self.agents and self.agent_to_root[aid] == aid:
                roles[aid] = EpigeneticRole.NONE
        self._role_leaf_sets = leaf_sets
        for aid in sorted(roles):
            self.agents[aid].set_epigenetic_role(roles[aid])

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

    def _metabolize(
        self,
        moved: set[int],
        sent: Mapping[int, int],
        attacks: Mapping[int, int],
        signals: Mapping[int, int],
        dormant: frozenset[int] = frozenset(),
    ) -> None:
        """Cobra el costo basal, de movimiento y de mensajes a cada agente, por `agent_id`.

        Con $R_{28}$ (D38, precisión 103), una endospora dormida todo el tick (`dormant`) paga sólo
        `spore_cost_fraction * metabolic_base_cost`, en lugar del basal, del ADN, del movimiento y
        de los mensajes. Quien esporuló en la Fase 4 o germinó en la Fase 1 actuó en el tick y paga
        el costo completo.

        Con ADN (design D34.5), el costo basal se calcula sobre el genoma expresado en la Fase 0
        del tick y se le suma el costo del ADN; sin la bandera, la suma no se hace. Con $R_{37}$
        (D49.2), suma `attack_cost` por cada intento de ataque del tick en `attacks`, con éxito o
        sin él; sin intentos, la suma no se hace. Con $R_{41}$ (D60.3), suma siempre
        `signal_cost` por cada símbolo emitido en el tick (`signals`: emisor -> máscara); sin
        emisión suma 0.0, que no cambia el costo en un bit.
        """
        config = self.config
        dna = config.enable_compact_dna
        for aid in sorted(self.agents):
            agent = self.agents[aid]
            if aid in dormant:
                agent.apply_energy_delta(-(config.spore_cost_fraction * config.metabolic_base_cost))
                continue
            cost = compute_metabolic_cost(agent.genome, config)
            if dna:
                cost += compute_dna_cost(agent.dna, config)
            cost += config.move_cost * (aid in moved) + config.message_cost * sent.get(aid, 0)
            if aid in attacks:
                cost += config.attack_cost * attacks[aid]
            # Sin símbolos suma 0.0, que no cambia el costo en un bit.
            cost += config.signal_cost * signals.get(aid, 0).bit_count()
            agent.apply_energy_delta(-cost)

    def _charge_senescence(self, tick: int) -> None:
        """Cobra la senescencia (R29, D39) a cada agente, endosporas incluidas, por `agent_id`.

        La edad es `tick - birth_tick` y la longevidad, la expresada en la Fase 0 del tick (con
        ADN, por el destino `0x07`; sin ADN, `telomere_base_lifespan`). Quien no superó su
        longevidad no paga nada: su energía no cambia en un bit.
        """
        config = self.config
        for aid in sorted(self.agents):
            agent = self.agents[aid]
            cost = compute_senescence_cost(
                tick - agent.birth_tick, agent.phenotype.lifespan, config
            )
            if cost:
                agent.apply_energy_delta(-cost)

    def _record_stress(self, tick: int) -> None:
        """Registra `last_stress_tick = tick` en cada sobreviviente con energía bajo el umbral.

        Hay estrés si `energy < stress_energy_limit(config)`, el umbral con tolerancia compartido
        con el promotor `0x18` (D39, precisión 93), que se calcula una vez por tick. Lo llama
        `StressSystem`, después de la muerte y sólo con $R_{30}$ efectivamente activa (precisión
        7 y 91); no consume generadores.
        """
        limit = stress_energy_limit(self.config)
        for aid in sorted(self.agents):
            agent = self.agents[aid]
            if agent.energy < limit:
                agent.record_stress(tick)

    def _remove_dead(self, tick: int) -> list[int]:
        """Elimina, por `agent_id`, a quien quedó con E <= 0 tras el metabolismo (R13).

        Con R35 (D48.3, precisiones 17 y 78), antes de quitarlos deposita el cadáver de cada
        muerto en su celda, en el mismo orden de `agent_id`. Las perturbaciones no pasan por
        aquí, así que no dejan cadáver. Devuelve los muertos, en orden.
        """
        dead = [aid for aid in sorted(self.agents) if self.agents[aid].energy <= 0]
        if dead:
            if self.carcasses_active:
                env = cast(EcologicalEnvironmentPort, self.env)
                value = self.config.carcass_value
                for aid in dead:
                    env.deposit_carcass(aid, value, tick)
            self._remove(dead, tick)
        return dead

    def _reproduce(self, tick: int) -> int:
        """R17 y luego R12 (o su ablación neutral), a lo sumo un evento por agente (D26)."""
        config = self.config
        reproduced: set[int] = set()
        neutral = config.reproduction_mode == "neutral"
        spores = self.sporulation_active
        # Donantes: los vivos que no están en endospora al empezar la fase (D38, precisión 14).
        donors = (
            [
                self.agents[aid]
                for aid in sorted(self.agents)
                if not (spores and self.agents[aid].is_endospore)
            ]
            if neutral
            else []
        )
        births = 0
        if config.enable_holonic_hierarchy and config.enable_holon_reproduction:
            for nid in sorted(self.root_nodes):
                node = self.root_nodes[nid]
                if not isinstance(node, CompositeAgent):
                    continue
                leaves = node.leaf_agents
                if any(leaf.agent_id in reproduced for leaf in leaves):
                    continue
                if spores and any(leaf.is_endospore for leaf in leaves):
                    continue  # R28 (D38, precisión 14): un holón con una endospora no se reproduce
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
                if self.epigenetic_roles_active:  # impronta de R25 (D36, precisiones 11 y 111)
                    for leaf in leaves:
                        offspring[leaf.agent_id].set_epigenetic_role(leaf.epigenetic_role)
                    # Si la composición del progenitor cambió en este tick, sus roles no son de
                    # ella: la réplica no queda registrada y el paso (vii) le asigna roles.
                    if self._role_leaf_sets.get(nid) == frozenset(leaf.agent_id for leaf in leaves):
                        self._role_leaf_sets[child.node_id] = frozenset(
                            c.agent_id for c in offspring.values()
                        )
                reproduced.update(offspring)
                reproduced.update(c.agent_id for c in offspring.values())
                births += len(offspring)
        for aid in sorted(self.agents):
            agent = self.agents[aid]
            if aid in reproduced or agent.energy < config.reproduction_threshold:
                continue
            if spores and agent.is_endospore:
                continue  # R28 (D38): una endospora no se reproduce
            if len(self.agents) >= config.max_population:
                break
            donor = donors[int(self.donor_rng.integers(len(donors)))] if neutral else None
            child = self._give_birth(agent, tick, donor)
            self._set_root(child)
            reproduced.update((aid, child.agent_id))
            births += 1
        return births

    def _give_birth(
        self, parent: MicroAgent, tick: int, donor: MicroAgent | None = None
    ) -> MicroAgent:
        """Hijo con ID nuevo, ubicado junto al progenitor y con su herencia cultural (D22, D26).

        `donor` es el donante de la reproducción neutral: aporta su genoma o, si el progenitor
        tiene ADN, su ADN (design D34.7). El hijo nace expresado en su contexto de nacimiento
        (`create_offspring`) y `spawn_agent_near` recibe los radios de ese fenotipo (D34.6).
        Con $R_{30}$ (D39), la escala de mutación se decide con el estado del progenitor antes
        de partir la energía; en la reproducción holónica, con el de cada hoja. Sin la regla, la
        escala es 1.0 y la Fase II no cambia en un bit.
        """
        rng = self.evo_rng
        scale = compute_sos_scale(parent.energy, parent.last_stress_tick, tick, self.config)
        if donor is None:
            child = parent.create_offspring(self.next_agent_id, tick, rng, mutation_scale=scale)
        elif (parent.dna is None) != (donor.dna is None):
            # Una población mixta no la produce el motor: heredar en silencio el ADN propio o el
            # genoma expresado del donante falsearía la deriva neutral.
            raise ValueError(
                f"población mixta en la reproducción neutral: el progenitor {parent.agent_id} "
                f"y el donante {donor.agent_id} deben tener ADN los dos o ninguno"
            )
        elif parent.dna is None:  # la misma fuente de verdad que valida `create_offspring`
            child = parent.create_offspring(
                self.next_agent_id, tick, rng, donor.genome, mutation_scale=scale
            )
        else:
            child = parent.create_offspring(
                self.next_agent_id, tick, rng, dna_source=donor.dna, mutation_scale=scale
            )
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
            # Entre pasos: las hojas liberadas pierden la penalización de R18 antes del tick y,
            # con R25, los holones podados se reasignan como en la Fase 5 (precisión 123).
            reach = self._apply_downward_causation()
            if self.epigenetic_roles_active:
                self._assign_epigenetic_roles(reach)

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
