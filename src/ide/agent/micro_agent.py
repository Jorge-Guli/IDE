"""Micro-agente autónomo: percepción local, comunicación delegada y decisión."""

import math
from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType

import numpy as np

from ide.agent.dna import (
    BEHAVIORS,
    SYMBOL_MASK,
    BehaviorTerms,
    apply_plastic_weights,
    behavior_terms,
    founder_dna,
    heard_symbols,
    mutate_dna,
    phenotype_from_genome,
    signals_active,
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
from ide.config import SimulationConfig, is_stress_energy_ratio
from ide.domain.extensions import (
    AgentCapabilities,
    TrustStrategyPort,
    UniformTrustStrategy,
    mutate_genome,
)
from ide.domain.types import (
    AgentAction,
    AgentGenome,
    Behavior,
    BehaviorEvaluation,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    EventSignals,
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
# Clave del caché de la evaluación de conducta (D46.8, precisión 57): la de expresión más las
# señales del tick, el estado interno y la máscara percibida (0 hasta el bloque 15). Los pesos
# aprendidos no forman parte de la clave: el caché guarda la evaluación sin ellos (D59.5).
_EvaluationKey = tuple[_ExpressionKey, SensorySignals, int, int]
_STATE_MASK = 0xFF  # `internal_state` tiene 8 bits (D58.1)
# Tope del caché de la evaluación, por agente: al alcanzarlo se vacía. Las claves posibles son
# muchas (10 niveles, 4 roles, 3 bandas, 2^12 señales y 256 estados), así que sin tope el caché
# crecería sin medida en una vida larga. Medido en el bloque 13 (002a y 003a con ADN, política
# genética, mutación 0.2, R36, R37 y R39, 500 ticks, semillas 42 y 43, fundadores con nueve
# codones de estado y de eventos), un agente usa a lo sumo 94 claves (media de 11 a 13; en el
# bloque 10, sin estado, a lo sumo 117), así que 512 casi nunca se alcanza y acota la memoria a
# unos cientos de evaluaciones por agente. Vaciarlo no cambia ningún resultado: sólo obliga a
# recalcular.
EVALUATION_CACHE_LIMIT = 512
_BAND_STRESS, _BAND_NORMAL, _BAND_SURPLUS = 0, 1, 2
# Los promotores de nivel distinguen hasta `IN_HOLON_L9` (0x0A, design D32).
_MAX_DISTINCT_LEVEL = 9

# R38 (D51.1, precisión 127): propensión expresada mínima para buscar pareja y para ser candidata.
MATE_PROPENSITY_THRESHOLD = 0.5


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
        # Ensayos CRISPR abiertos: codón -> (tick de apertura, energía de ingreso, neto
        # transferido a otros agentes, precisión 125).
        self._plasmid_trials: dict[int, tuple[int, float, float]] = {}
        self._expression_cache: dict[_ExpressionKey, ExpressedPhenotype] = {}
        self._evaluation_cache: dict[_EvaluationKey, BehaviorTerms] = {}
        # --- Ampliación de la Fase II-B (R39, design D58) ---
        # Estado interno de 8 bits: 0 al nacer, no se hereda y se conserva en endospora (D58.1).
        self._internal_state = 0
        # Eventos del tick anterior, que escribe el motor al final de cada tick (D58.5).
        self._last_events = EventSignals()
        # Registro único de la decisión: (tick, evaluación, posición en `Behavior` de la conducta
        # elegida o `None` si cayó en `IDLE`). Lo escribe la política genética al decidir y lo
        # leen los sistemas del motor de ese tick (D58.3, D59.4); `None` sin decisión registrada.
        self._decision: tuple[int, BehaviorEvaluation, int | None] | None = None
        # --- R40 (design D59) ---
        # Pesos aprendidos por posición en `chromosome + plasmids`, en orden ascendente de
        # posición: vacíos al nacer (todos en 0), no se heredan y se vacían en `set_dna` (D59.2).
        self._plastic_weights: dict[int, float] = {}
        # --- R41 (design D60, precisión 65) ---
        # Máscara de símbolos percibidos: 0 al nacer, no se hereda y la recalcula el motor en cada
        # Fase 1. Es un canal sensorial: nunca se escribe en la memoria (D60.6).
        self._perceived_symbols = 0
        # Símbolos que oye el ADN vigente (`heard_symbols`), calculados de forma perezosa y
        # guardados junto a esa instancia de ADN: acotan la máscara percibida en la clave del
        # caché de la evaluación (precisión 105).
        self._heard: tuple[CompactDNA, int] | None = None
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

    def seeks_mate(self) -> bool:
        """R38 (D51.1): `recombination_propensity` expresada `>= 0.5`, sin tolerancia.

        Es la única definición de la condición de propensión: la usan el progenitor que busca
        pareja y el filtro de las candidatas. Lee el fenotipo de la última expresión.
        """
        return self._phenotype.recombination_propensity >= MATE_PROPENSITY_THRESHOLD

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
    def internal_state(self) -> int:
        """Estado interno de 8 bits ($R_{39}$, D58.1): 0 al nacer y sin $R_{39}$."""
        return self._internal_state

    @property
    def last_events(self) -> EventSignals:
        """Eventos del tick anterior (D58.5); `EventSignals()` en un recién nacido."""
        return self._last_events

    @property
    def perceived_symbols(self) -> int:
        """Máscara de símbolos percibidos en la Fase 1 del tick ($R_{41}$, precisión 65)."""
        return self._perceived_symbols

    def decision_evaluation(self, tick: int) -> BehaviorEvaluation | None:
        """La evaluación con que el agente decidió en `tick`, o `None` si no decidió con ella."""
        decision = self._decision
        if decision is None or decision[0] != tick:
            return None
        return decision[1]

    def decision_behavior(self, tick: int) -> Behavior | None:
        """La conducta elegida en la decisión registrada de `tick`, o `None` (D59.4)."""
        decision = self._decision
        if decision is None or decision[0] != tick or decision[2] is None:
            return None
        return BEHAVIORS[decision[2]]

    @property
    def plastic_weights(self) -> Mapping[int, float]:
        """Vista viva de sólo lectura de los pesos aprendidos ($R_{40}$, D59.2).

        No copia: el agente conserva siempre el mismo diccionario, en orden ascendente de
        posición, y la vista refleja cada cambio, también el vaciado de `set_dna`. Quien quiera
        una instantánea hace `dict(agent.plastic_weights)`.
        """
        return MappingProxyType(self._plastic_weights)

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
        self._evaluation_cache.clear()
        self._decision = None  # la decisión registrada era la de otro ADN
        self._plastic_weights.clear()  # las posiciones cambian (D59.2); la vista sigue viva

    def set_endospore(self, flag: bool) -> None:
        """Entrada en endospora o germinación (R28, design D38).

        Conserva `internal_state` (D58.1) y `plastic_weights` (sólo `set_dna` los vacía, D59.2).
        """
        self._is_endospore = flag

    def set_last_events(self, events: EventSignals) -> None:
        """Eventos del tick, que el motor escribe al final de cada tick (D58.5)."""
        self._last_events = events

    def set_perceived_symbols(self, mask: int) -> None:
        """Máscara percibida del tick, que el motor recalcula en cada Fase 1 (D60.4, D60.5).

        Sólo la leen los promotores `HEARD_k` de la evaluación de conducta: no es un `Message`
        ni una creencia y no pasa por el protocolo ni por la memoria (D60.6).

        Raises:
            ValueError: si `mask` no está en $[0, 255]$.
        """
        if not 0 <= mask <= SYMBOL_MASK:
            raise ValueError(f"perceived_symbols debe estar en [0, 255]; recibió {mask}")
        self._perceived_symbols = mask

    def record_stress(self, tick: int) -> None:
        """Registra `last_stress_tick = tick`: el motor lo llama tras la muerte (D39)."""
        self._last_stress_tick = tick

    def open_plasmid_trial(self, codon: int, tick: int) -> None:
        """Abre un ensayo CRISPR con la energía actual; no reabre uno abierto (precisión 4)."""
        if codon not in self._plasmid_trials:
            self._plasmid_trials[codon] = (tick, self._energy, 0.0)

    def close_plasmid_trial(self, codon: int) -> None:
        """Cierra el ensayo CRISPR del codón, si está abierto (precisión 4)."""
        self._plasmid_trials.pop(codon, None)

    @property
    def has_plasmid_trials(self) -> bool:
        """Si hay algún ensayo CRISPR abierto, sin copiar ni ordenar los ensayos."""
        return bool(self._plasmid_trials)

    def credit_plasmid_trials(self, amount: float) -> None:
        """Suma `amount` al neto transferido de los ensayos CRISPR abiertos (precisión 125).

        El tercer valor del ensayo es el neto de las transferencias de energía entre agentes
        durante la ventana, que el balance excluye porque no son un efecto metabólico del
        plásmido. Suma lo que el agente da: la energía de cada hijo (`create_offspring`), la que
        cede con un `SHARE` propio y la que le roban en un ataque sufrido. Lo que recibe lo
        resta `debit_plasmid_trials`. Sin ensayos abiertos no hace nada; el orden no importa.
        """
        trials = self._plasmid_trials
        if not trials:
            return
        for codon, (opened, entry_energy, net) in trials.items():
            trials[codon] = (opened, entry_energy, net + amount)

    def debit_plasmid_trials(self, amount: float) -> None:
        """Resta `amount` del neto transferido de los ensayos CRISPR abiertos (precisión 125).

        Registra lo que el agente recibe de otro: la energía de un `SHARE` ajeno y la que gana
        con un ataque propio con éxito (`predation_efficiency * stolen`).
        """
        self.credit_plasmid_trials(-amount)

    def _expression_key(self, context: EpigeneticContext) -> _ExpressionKey:
        """Clave del caché: el fenotipo sólo depende del nivel acotado, el rol y la banda."""
        base = self._base_config
        ratio = context.energy_ratio
        if is_stress_energy_ratio(ratio, base):  # la misma definición que `0x18` (precisión 93)
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

    def evaluate_behavior(self, signals: SensorySignals) -> BehaviorEvaluation:
        """Evaluación de conducta (D60.1) del ADN propio en `last_context`, memoizada; sin efectos.

        Evalúa con el `internal_state`, la máscara percibida (`perceived_symbols`) y los
        `plastic_weights` vigentes. La clave del caché es la de expresión (D34.2) más `signals`, el
        estado y la máscara percibida restringida a los símbolos que el ADN oye (precisiones 57 y
        105): los promotores de contexto sólo distinguen el
        nivel acotado, el rol y la banda de energía. El caché guarda la evaluación sin los pesos
        (`behavior_terms`) y los suma después (`apply_plastic_weights`, D59.5), así que es igual a
        `evaluate_behavior` con los pesos vigentes. `set_dna` invalida el caché, así que nunca
        sirve la evaluación de otro ADN, y se vacía al alcanzar `EVALUATION_CACHE_LIMIT` entradas.
        No consume generadores ni cambia el agente, salvo el caché.
        """
        dna = self._dna
        if dna is None:
            raise ValueError("la evaluación de conducta exige un agente con ADN")
        # Sólo con R41 y sólo los bits que algún `HEARD_k` del ADN lee cambian la evaluación
        # (precisión 105); sin R41 la máscara es inerte y la clave usa 0.
        context, state = self._last_context, self._internal_state
        perceived = self._perceived_symbols
        if perceived and signals_active(self._base_config):
            perceived &= self._heard_mask(dna)
        else:
            perceived = 0
        key = (self._expression_key(context), signals, state, perceived)
        terms = self._evaluation_cache.get(key)
        if terms is None:
            terms = behavior_terms(dna, context, signals, self._base_config, state, perceived)
            if len(self._evaluation_cache) >= EVALUATION_CACHE_LIMIT:
                self._evaluation_cache.clear()
            self._evaluation_cache[key] = terms
        return apply_plastic_weights(terms, self._plastic_weights)

    def _heard_mask(self, dna: CompactDNA) -> int:
        """`heard_symbols(dna)`, calculada una vez por instancia de ADN (precisión 105)."""
        heard = self._heard
        if heard is None or heard[0] is not dna:
            heard = (dna, heard_symbols(dna))
            self._heard = heard
        return heard[1]

    def evaluate_for_decision(self, signals: SensorySignals, tick: int) -> BehaviorEvaluation:
        """`evaluate_behavior` de la decisión de `tick`, registrada para el motor (D58.3).

        La invoca la política genética al decidir. La decisión usa el estado anterior; el motor
        aplica el estado siguiente al terminar la Fase 3 con `apply_internal_state`. Una
        endospora no registra nada: conserva su estado (D58.1). Con $R_{28}$ el motor no la hace
        decidir (D38); el caso de una endospora puesta a mano, que sí decide, es el de los tests.

        Raises:
            RuntimeError: si ya hay una decisión registrada en `tick`: se decide una vez por tick.
        """
        if self._decision is not None and self._decision[0] == tick:
            raise RuntimeError(f"el agente {self._agent_id} ya decidió en el tick {tick}")
        evaluation = self.evaluate_behavior(signals)
        if not self._is_endospore:
            self._decision = (tick, evaluation, None)
        return evaluation

    def record_behavior(self, slot: int, tick: int) -> None:
        """Registra la conducta elegida, por su posición en `Behavior`, en la decisión de `tick`.

        La invoca la política genética al elegir una conducta factible (D59.4). Sin una decisión
        registrada en `tick` (por ejemplo, en endospora) no hace nada.
        """
        decision = self._decision
        if decision is not None and decision[0] == tick:
            self._decision = (tick, decision[1], slot)

    def reinforce(self, tick: int, reward: float) -> int:
        """Regla de aprendizaje de $R_{40}$ (D59.4) con la recompensa `reward` de la Fase 4.

        La invoca el motor inmediatamente después de ejecutar la acción del agente, sólo con
        $R_{40}$ efectivamente activa. Los codones elegibles son los de modo 3 activos en la
        evaluación registrada de `tick` (`decision_evaluation(tick).plastic`) con destino igual a
        la conducta elegida (`decision_behavior(tick)`); cada uno se actualiza con
        $w_i \\leftarrow \\min(1, \\max(-1, w_i + \\eta \\cdot r))$, con
        $\\eta$ = `phenotype.plasticity_rate`. Con $\\eta \\cdot r = 0$ ningún peso cambia ni se
        agregan pesos en 0. Si se agrega una posición nueva, el diccionario se reordena en el
        lugar por posición. No consume generadores.

        Returns:
            Los pesos cuyo valor cambió, para `plastic_updates` (D63.3, precisiones 62 y 96): no
            cuentan los ya saturados en $\\pm 1$ que la cota deja igual; 0 sin decisión o
            conducta registradas o con $\\eta \\cdot r = 0$.
        """
        decision = self._decision
        if decision is None or decision[0] != tick or decision[2] is None or reward == 0.0:
            return 0
        eligible = decision[1].plastic[decision[2]]
        step = self._phenotype.plasticity_rate * reward
        if step == 0.0:
            return 0
        weights = self._plastic_weights
        changed = 0
        inserted = False
        for index in eligible:
            old = weights.get(index)
            new = min(1.0, max(-1.0, (0.0 if old is None else old) + step))
            if new != (0.0 if old is None else old):
                changed += 1
            if old is None:
                inserted = True
            weights[index] = new
        if inserted:  # orden ascendente de posición, en el mismo diccionario (vista viva)
            items = sorted(weights.items())
            weights.clear()
            weights.update(items)
        return changed

    def apply_internal_state(self, tick: int) -> None:
        """Aplica `(internal_state | set_mask) & ~clear_mask` de la decisión de `tick` (D58.3).

        Lo invoca el motor al terminar la Fase 3, sólo con $R_{39}$ efectivamente activa. Sin una
        evaluación registrada en `tick` (el agente no decidió con la política genética) no hace
        nada y el agente conserva su estado. Aplicarlo dos veces da lo mismo que una.
        """
        evaluation = self.decision_evaluation(tick)
        if evaluation is not None:
            state = self._internal_state | evaluation.set_mask
            self._internal_state = state & ~evaluation.clear_mask & _STATE_MASK

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
        ensayos CRISPR; su energía se suma al neto transferido de los ensayos abiertos del
        progenitor.
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
        self.credit_plasmid_trials(child_energy)
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
