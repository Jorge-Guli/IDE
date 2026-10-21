"""Micro-agente autónomo: percepción local, comunicación delegada y decisión."""

import math
from dataclasses import replace

import numpy as np

from ide.agent.dna import (
    evaluate_drives,
    founder_dna,
    mutate_dna,
    phenotype_from_genome,
    transcribe_phenotype,
)
from ide.agent.epistemology import (
    merge_social_belief,
    update_from_direct_experience,
)
from ide.agent.evolution import genome_from_config
from ide.agent.memory import BoundedMemory
from ide.agent.policy import HandwrittenPolicy, PolicyPort
from ide.agent.protocol import BeliefExchangeProtocol
from ide.config import SimulationConfig
from ide.domain.extensions import (
    AgentCapabilities,
    TrustStrategyPort,
    UniformTrustStrategy,
    mutate_genome,
)
from ide.domain.types import (
    AgentAction,
    AgentGenome,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    ExpressedPhenotype,
    KnowledgeUnit,
    Message,
    Observation,
    Pattern,
    SensorySignals,
    SocialPerception,
)

# Clave del caché de expresión (design D34.2): nivel acotado a 9, rol y banda de energía.
_ExpressionKey = tuple[int, EpigeneticRole, int]
# Clave del caché de impulsos (D46.8): la del caché de expresión más las señales del tick.
_DrivesKey = tuple[_ExpressionKey, SensorySignals]
# Tope del caché de impulsos, por agente: al alcanzarlo se vacía. Las claves posibles son muchas
# (10 niveles, 4 roles, 3 bandas y 2^12 señales), así que sin tope el caché crecería sin medida
# en una vida larga. Medido en el bloque 10 (002a y 003a con ADN, política genética, mutación
# 0.2, R36 y R37, 500 ticks), un agente usa a lo sumo 117 claves (media de 21 a 32), así que 512
# casi nunca se alcanza y acota la memoria a unos cientos de tuplas por agente. Vaciarlo no
# cambia ningún resultado: sólo obliga a recalcular.
DRIVES_CACHE_LIMIT = 512
_BAND_STRESS, _BAND_NORMAL, _BAND_SURPLUS = 0, 1, 2
# Los promotores de nivel distinguen hasta `IN_HOLON_L9` (0x0A, design D32).
_MAX_DISTINCT_LEVEL = 9


def _phenotype_config(base: SimulationConfig, genome: AgentGenome) -> SimulationConfig:
    """Configuración fenotípica: la base con los 6 rasgos del genoma (design D22 y D34.2).

    `initial_bond_affinity` conserva el valor fundador: la afinidad se lee siempre del genoma.
    """
    return replace(
        base,
        alpha_learning=genome.alpha_learning,
        gamma_social_discount=genome.gamma_social_discount,
        epsilon_explore=genome.epsilon_explore,
        memory_capacity=genome.memory_capacity,
        perception_radius=genome.perception_radius,
        comm_radius=genome.comm_radius,
    )


def _birth_context(energy: float, base: SimulationConfig) -> EpigeneticContext:
    """Contexto de expresión al nacer o al fundar: solo, sin rol (design D34.6, precisión 1)."""
    return EpigeneticContext(0, EpigeneticRole.NONE, energy / base.reproduction_threshold)


class MicroAgent:
    """Agente con memoria acotada que no conoce coordenadas ni valores verdaderos.

    Es también el nodo holónico de nivel cero (`AgentNode`, design D23) y lleva su estado
    energético y de linaje (Exp 002 v2), inerte mientras el motor no active la evolución.
    En la Fase II-B lleva además su ADN compacto, su fenotipo expresado, su configuración base,
    su rol epigenético y su estado de vida (design D34.1), inertes sin `enable_compact_dna` y
    sin las reglas que los usan.
    """

    def __init__(
        self,
        agent_id: int,
        config: SimulationConfig,
        trust_strategy: TrustStrategyPort | None = None,
        protocol: BeliefExchangeProtocol | None = None,
        policy: PolicyPort | None = None,
    ) -> None:
        self._setup(agent_id, config, trust_strategy, protocol, policy)
        self._last_context = _birth_context(config.initial_energy, config)
        if config.enable_compact_dna:
            # El ADN fundador expresa exactamente la base (design D32): `_genome` no cambia.
            self._dna = founder_dna(config)
            self._phenotype = self._transcribe(self._last_context)
        else:
            self._phenotype = phenotype_from_genome(self._genome, config)

    def _setup(
        self,
        agent_id: int,
        config: SimulationConfig,
        trust_strategy: TrustStrategyPort | None,
        protocol: BeliefExchangeProtocol | None,
        policy: PolicyPort | None,
    ) -> None:
        """Estado común a fundadores y descendientes, sin ADN ni fenotipo todavía."""
        self._agent_id = agent_id
        self._config = config
        self._trust = UniformTrustStrategy() if trust_strategy is None else trust_strategy
        self._protocol = BeliefExchangeProtocol() if protocol is None else protocol
        self._policy: PolicyPort = HandwrittenPolicy() if policy is None else policy
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
        # --- Fase II-B (design D34.1 y precisiones 1 y 4) ---
        self._base_config = config
        self._epigenetic_role = EpigeneticRole.NONE
        self._birth_tick = 0
        self._is_endospore = False
        self._last_stress_tick: int | None = None
        # Ensayos CRISPR abiertos: codón -> (tick de apertura, energía de ingreso, cedida).
        self._plasmid_trials: dict[int, tuple[int, float, float]] = {}
        self._expression_cache: dict[_ExpressionKey, ExpressedPhenotype] = {}
        self._drives_cache: dict[_DrivesKey, tuple[float, ...]] = {}
        self._dna: CompactDNA | None = None
        self._phenotype: ExpressedPhenotype
        self._last_context: EpigeneticContext

    @classmethod
    def from_lineage(
        cls,
        agent_id: int,
        config: SimulationConfig,
        genome: AgentGenome | None,
        energy: float,
        generation: int,
        parent_id: int | None,
        trust_strategy: TrustStrategyPort | None = None,
        protocol: BeliefExchangeProtocol | None = None,
        dna: CompactDNA | None = None,
        base_config: SimulationConfig | None = None,
        policy: PolicyPort | None = None,
    ) -> "MicroAgent":
        """Descendiente cuyo fenotipo (configuración) expresa su genoma.

        `initial_bond_affinity` conserva el valor fundador (D22): la afinidad de un descendiente
        se lee siempre de su genoma, nunca de su configuración.

        `base_config` es la configuración de la población (por defecto, `config`).
        - Sin `dna`, el agente no tiene ADN: `genome` es obligatorio, la configuración es la de
          `config` con los rasgos del genoma y el fenotipo es `phenotype_from_genome`.
        - Con `dna`, que exige `base_config.enable_compact_dna`, el fenotipo es la única
          transcripción en el contexto de nacimiento (design D34.6) y la configuración sale de
          `base_config`. Con `genome=None`, el genoma es el expresado; si no, debe coincidir.
        """
        base = config if base_config is None else base_config
        if dna is None:
            if genome is None:
                raise ValueError("genome es obligatorio sin dna")
            return cls._assemble(
                agent_id=agent_id,
                config=config,
                energy=energy,
                generation=generation,
                parent_id=parent_id,
                trust_strategy=trust_strategy,
                protocol=protocol,
                policy=policy,
                base=base,
                phenotype=phenotype_from_genome(genome, base),
                dna=None,
                context=None,
            )
        if not base.enable_compact_dna:
            raise ValueError("dna exige base_config.enable_compact_dna=True")
        context = _birth_context(energy, base)
        phenotype = transcribe_phenotype(dna, context, base)
        if genome is not None and phenotype.genome != genome:
            raise ValueError("genome debe ser el genoma que expresa dna al nacer")
        return cls._assemble(
            agent_id=agent_id,
            config=base,
            energy=energy,
            generation=generation,
            parent_id=parent_id,
            trust_strategy=trust_strategy,
            protocol=protocol,
            policy=policy,
            base=base,
            phenotype=phenotype,
            dna=dna,
            context=context,
        )

    @classmethod
    def _assemble(
        cls,
        *,
        agent_id: int,
        config: SimulationConfig,
        energy: float,
        generation: int,
        parent_id: int | None,
        trust_strategy: TrustStrategyPort | None,
        protocol: BeliefExchangeProtocol | None,
        policy: PolicyPort | None,
        base: SimulationConfig,
        phenotype: ExpressedPhenotype,
        dna: CompactDNA | None,
        context: EpigeneticContext | None,
    ) -> "MicroAgent":
        """Descendiente con su fenotipo ya calculado, sin transcribir ni crear un fundador.

        La configuración es `config` con los rasgos de `phenotype.genome`. Con `dna`,
        `phenotype` es la transcripción en `context`, y queda en el caché bajo su clave.
        """
        genome = phenotype.genome
        agent = cls.__new__(cls)
        agent._setup(agent_id, _phenotype_config(config, genome), trust_strategy, protocol, policy)
        agent._genome = genome
        agent._energy = energy
        agent._generation = generation
        agent._parent_id = parent_id
        agent._base_config = base
        agent._dna = dna
        agent._phenotype = phenotype
        agent._last_context = _birth_context(energy, base) if context is None else context
        if dna is not None:
            assert context is not None, "el fenotipo con ADN se cachea con su contexto"
            agent._expression_cache[agent._expression_key(context)] = phenotype
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
    def policy(self) -> PolicyPort:
        return self._policy

    @property
    def dna(self) -> CompactDNA | None:
        return self._dna

    @property
    def phenotype(self) -> ExpressedPhenotype:
        return self._phenotype

    @property
    def base_config(self) -> SimulationConfig:
        return self._base_config

    @property
    def last_context(self) -> EpigeneticContext:
        """Contexto de la última expresión: el de la Fase 0 o el del nacimiento (precisión 23)."""
        return self._last_context

    @property
    def communicates(self) -> bool:
        """Puerta de comunicación (D46.6): `comm_propensity >= 0.5` si la política la declara.

        La declara una política con `gates_communication = True` (`GeneticPolicy`); con
        `False` (`HandwrittenPolicy`) vale siempre `True`. La lee `protocol.py`.
        """
        if self._policy.gates_communication:
            return self._phenotype.comm_propensity >= 0.5
        return True

    @property
    def epigenetic_role(self) -> EpigeneticRole:
        return self._epigenetic_role

    @property
    def birth_tick(self) -> int:
        return self._birth_tick

    @property
    def is_endospore(self) -> bool:
        return self._is_endospore

    @property
    def last_stress_tick(self) -> int | None:
        return self._last_stress_tick

    @property
    def plasmid_trials(self) -> dict[int, tuple[int, float, float]]:
        """Copia de los ensayos CRISPR abiertos, ordenada por codón (precisión 4)."""
        return {codon: self._plasmid_trials[codon] for codon in sorted(self._plasmid_trials)}

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

    def set_epigenetic_role(self, role: EpigeneticRole) -> None:
        """Rol epigenético asignado por el motor (R25, design D36)."""
        self._epigenetic_role = role

    def set_dna(self, dna: CompactDNA) -> None:
        """Reemplaza el ADN e invalida el caché; el fenotipo cambia en el próximo `express`.

        Exige `base_config.enable_compact_dna`: sin la bandera, el agente no lleva ADN.
        """
        if not self._base_config.enable_compact_dna:
            raise ValueError("set_dna exige base_config.enable_compact_dna=True")
        self._dna = dna
        self._expression_cache.clear()
        self._drives_cache.clear()

    def set_endospore(self, flag: bool) -> None:
        """Entrada en endospora o germinación (R28, design D38)."""
        self._is_endospore = flag

    def open_plasmid_trial(self, codon: int, tick: int) -> None:
        """Abre un ensayo CRISPR con la energía actual; no reabre uno abierto (precisión 4)."""
        if codon not in self._plasmid_trials:
            self._plasmid_trials[codon] = (tick, self._energy, 0.0)

    def close_plasmid_trial(self, codon: int) -> None:
        """Cierra el ensayo CRISPR del codón, si está abierto (precisión 4)."""
        self._plasmid_trials.pop(codon, None)

    def _expression_key(self, context: EpigeneticContext) -> _ExpressionKey:
        """Clave del caché: el fenotipo sólo depende del nivel acotado, el rol y la banda."""
        base = self._base_config
        ratio = context.energy_ratio
        if ratio < base.stress_energy_ratio:
            band = _BAND_STRESS
        elif ratio >= base.surplus_energy_ratio:
            band = _BAND_SURPLUS
        else:
            band = _BAND_NORMAL  # también NaN: no activa ni el estrés ni el superávit
        return (min(context.holon_level, _MAX_DISTINCT_LEVEL), context.role, band)

    def _transcribe(self, context: EpigeneticContext) -> ExpressedPhenotype:
        """`transcribe_phenotype` del ADN propio sobre la configuración base, memoizada.

        Lee siempre `self._dna`, y `set_dna` invalida el caché: nunca sirve el fenotipo de
        otro ADN.
        """
        dna = self._dna
        assert dna is not None, "sólo un agente con ADN se transcribe"
        key = self._expression_key(context)
        phenotype = self._expression_cache.get(key)
        if phenotype is None:
            phenotype = transcribe_phenotype(dna, context, self._base_config)
            self._expression_cache[key] = phenotype
        return phenotype

    def behavior_drives(self, signals: SensorySignals) -> tuple[float, ...]:
        """Impulsos de `evaluate_drives` del ADN propio en `last_context`, memoizados (D46.8).

        La clave es la del caché de expresión (D34.2) más `signals`: los promotores de contexto
        sólo distinguen el nivel acotado, el rol y la banda de energía. `set_dna` invalida el
        caché, así que nunca sirve los impulsos de otro ADN, y se vacía al superar
        `DRIVES_CACHE_LIMIT` entradas.
        """
        dna = self._dna
        if dna is None:
            raise ValueError("los impulsos exigen un agente con ADN")
        context = self._last_context
        key = (self._expression_key(context), signals)
        drives = self._drives_cache.get(key)
        if drives is None:
            drives = evaluate_drives(dna, context, signals, self._base_config)
            if len(self._drives_cache) >= DRIVES_CACHE_LIMIT:
                self._drives_cache.clear()
            self._drives_cache[key] = drives
        return drives

    def express(self, context: EpigeneticContext, tick: int) -> bool:
        """Expresa el ADN en el contexto del tick (R24, design D34.2 y precisión 2).

        Sin ADN no hace nada. Con ADN, reemplaza siempre el fenotipo; si cambió el genoma,
        reemplaza también la configuración fenotípica y ajusta la memoria con `resize`, lo que
        puede forzar el olvido. Devuelve `True` si y sólo si cambió algún radio, para que el
        motor actualice el entorno.
        """
        if self._dna is None:
            return False
        self._last_context = context
        self._phenotype = self._transcribe(context)
        genome, previous = self._phenotype.genome, self._genome
        if genome == previous:
            return False
        self._genome = genome
        self._config = _phenotype_config(self._base_config, genome)
        self._memory.resize(genome.memory_capacity, tick)
        return (genome.perception_radius, genome.comm_radius) != (
            previous.perception_radius,
            previous.comm_radius,
        )

    def create_offspring(
        self,
        child_id: int,
        tick: int,
        rng: np.random.Generator,
        genome_source: AgentGenome | None = None,
        dna_source: CompactDNA | None = None,
        mutation_scale: float = 1.0,
    ) -> "MicroAgent":
        """Hijo con energía particionada y genoma mutado (R12, R13), sin creencias.

        `genome_source` y `dna_source` sólo los pasa la reproducción neutral, según el agente
        tenga o no ADN. `mutation_scale` es la escala de R30 (design D35). Con ADN, el hijo
        muta el ADN con la configuración base y se expresa al nacer (design D34.6). El hijo
        nace con `birth_tick = tick`, sin rol, sin endospora, sin estrés registrado y sin
        ensayos CRISPR; su energía se suma a la cedida de los ensayos abiertos del progenitor.
        La herencia cultural (R14) la entrega el motor después, por `assimilate_testimony`.
        """
        if not (mutation_scale >= 0.0 and math.isfinite(mutation_scale)):
            raise ValueError(f"mutation_scale debe ser finito y no negativo: {mutation_scale}")
        if self._dna is None:
            if dna_source is not None:
                raise ValueError("dna_source exige un progenitor con ADN")
            child, child_energy = self._offspring_from_genome(
                child_id, rng, genome_source, mutation_scale
            )
        else:
            if genome_source is not None:
                raise ValueError("genome_source no se usa con ADN: corresponde dna_source")
            source = self._dna if dna_source is None else dna_source
            dna = mutate_dna(source, self._base_config, rng, mutation_scale)
            child_energy = self._base_config.offspring_energy_share * self._energy
            self._energy -= child_energy
            # `from_lineage` hace la única transcripción del nacimiento (design D34.6).
            child = MicroAgent.from_lineage(
                child_id,
                self._base_config,
                None,
                child_energy,
                self._generation + 1,
                self._agent_id,
                self._trust,
                self._protocol,
                dna=dna,
                base_config=self._base_config,
                policy=self._policy,
            )
        child._birth_tick = tick
        for codon in sorted(self._plasmid_trials):
            opened, entry_energy, ceded = self._plasmid_trials[codon]
            self._plasmid_trials[codon] = (opened, entry_energy, ceded + child_energy)
        return child

    def _offspring_from_genome(
        self,
        child_id: int,
        rng: np.random.Generator,
        genome_source: AgentGenome | None,
        mutation_scale: float,
    ) -> tuple["MicroAgent", float]:
        """Hijo de la Fase II; con `mutation_scale == 1.0` usa la configuración intacta."""
        config = self._config
        if mutation_scale != 1.0:
            config = replace(
                config,
                mutation_rate=mutation_scale * config.mutation_rate,
                discrete_mutation_prob=min(1.0, mutation_scale * config.discrete_mutation_prob),
            )
        source = self._genome if genome_source is None else genome_source
        genome = mutate_genome(source, config, rng)
        child_energy = self._config.offspring_energy_share * self._energy
        self._energy -= child_energy
        child = MicroAgent.from_lineage(
            child_id,
            self._config,
            genome,
            child_energy,
            self._generation + 1,
            self._agent_id,
            self._trust,
            self._protocol,
            base_config=self._base_config,
            policy=self._policy,
        )
        return child, child_energy

    def own_belief(self, pattern: Pattern) -> KnowledgeUnit | None:
        """Creencia de memoria si existe; si no, la del caché efímero propio del tick."""
        unit = self._memory.get(pattern)
        return unit if unit is not None else self._ephemeral_tick_beliefs.get(pattern)

    def own_beliefs(self) -> dict[Pattern, KnowledgeUnit]:
        """`own_belief` de cada patrón de la memoria o del caché propio, ordenado por patrón.

        No incluye la vista del holón: es lo que el motor lee en el tiempo 2 de R22.
        """
        memory = {unit.pattern: unit for unit in self._memory.all_units()}
        cache = self._ephemeral_tick_beliefs
        return {p: memory[p] if p in memory else cache[p] for p in sorted({*cache, *memory})}

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

    def decide_action(
        self,
        obs: Observation,
        tick: int,
        rng: np.random.Generator,
        social: SocialPerception | None = None,
    ) -> AgentAction:
        """Delega en la política del agente (design D45.3); `social` es opcional."""
        return self._policy.decide(self, obs, social, tick, rng)

    def learn_from_experience(self, pattern: Pattern, real_value: float, tick: int) -> None:
        """La experiencia directa siempre se retiene (prioridad empírica)."""
        updated = update_from_direct_experience(
            self.own_belief(pattern), pattern, real_value, tick, self._config
        )
        self._memory.upsert(updated, tick, force=True)

    def decay_memory(self, tick: int) -> None:
        self._memory.decay_step(tick, self._config.passive_conf_decay, self._config.min_confidence)
