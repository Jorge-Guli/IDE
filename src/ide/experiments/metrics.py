"""Métricas poblacionales M1 a M7, telemetría evolutiva M8 a M13 y telemetría de evolución
abierta de la Fase II-B (`experimental-suite`, D53.2, D53.3 y D63.2-D63.4).

Sólo cuentan las creencias de `BoundedMemory`. Una creencia es válida si su signo coincide con
el del mundo y su confianza alcanza `decision_conf_threshold`; es falsa si el signo es opuesto
con la misma confianza.
"""

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from typing import Literal, NamedTuple

from ide.agent.dna import (
    BEHAVIORS,
    canonical_codon,
    evaluate_behavior,
    expressible_codons,
    founder_dna,
    functional_codon_values,
    learning_codons,
    trait_or_behavior_codons,
)
from ide.agent.holon import AgentNode, CompositeAgent, composite_nodes, is_effectively_locked
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.types import (
    ActionType,
    AgentAction,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    Pattern,
    SensorySignals,
    counts_as_knowledge,
)


@dataclass(frozen=True)
class TickMetrics:
    tick: int
    active_agents: int
    individual_coverage_mean: float  # M1
    collective_coverage: float  # M1
    accessible_coverage_mean: float  # M1 (1 salto)
    decision_opportunities: int  # M2
    correct_decisions: int  # M2
    decision_accuracy: float  # M2 (0.0 si no hubo oportunidades)
    cumulative_decision_accuracy: float  # M2
    pattern_prevalence: dict[Pattern, float]  # M3/M4
    pattern_false_prevalence: dict[Pattern, float]  # M6
    false_belief_prevalence: float  # M6 (agentes con >= 1 creencia falsa)
    messages_sent: int  # M7
    messages_per_agent: float  # M7 (0.0 si no hay agentes)


@dataclass(frozen=True)
class KnowledgeSnapshot:
    """Estado epistémico de la población, sin decisiones ni mensajes."""

    active_agents: int
    individual_coverage_mean: float
    collective_coverage: float
    accessible_coverage_mean: float
    pattern_prevalence: dict[Pattern, float]
    pattern_false_prevalence: dict[Pattern, float]
    false_belief_prevalence: float


def _sign(value: float) -> int:
    return (value > 0) - (value < 0)


def has_truthful_query_channel(config: SimulationConfig) -> bool:
    """Existe una consulta en vivo que transmite el contenido real (Decisión 9)."""
    return config.comm_enabled and config.max_queries_per_tick > 0 and not config.comm_content_null


def knowledge_snapshot(
    agents: Mapping[int, MicroAgent],
    world_patterns: Mapping[Pattern, float],
    neighbors: Mapping[int, list[int]],
    config: SimulationConfig,
) -> KnowledgeSnapshot:
    """Función pura: coberturas y prevalencias del estado actual.

    Sin un canal de consulta veraz, los vecinos se ignoran y la cobertura accesible es la
    individual.
    """
    patterns = sorted(world_patterns)
    if not agents:
        zeros = dict.fromkeys(patterns, 0.0)
        return KnowledgeSnapshot(0, 0.0, 0.0, 0.0, zeros, dict(zeros), 0.0)

    threshold = config.decision_conf_threshold
    valid: dict[int, frozenset[Pattern]] = {}
    false: dict[int, frozenset[Pattern]] = {}
    for aid, agent in agents.items():
        good: list[Pattern] = []
        bad: list[Pattern] = []
        for unit in agent.memory.all_units():
            truth = world_patterns.get(unit.pattern)
            if truth is None or unit.confidence < threshold:
                continue
            sign = _sign(unit.predicted_value)
            if sign == _sign(truth):
                good.append(unit.pattern)
            elif sign == -_sign(truth):
                bad.append(unit.pattern)
        valid[aid] = frozenset(good)
        false[aid] = frozenset(bad)

    total = len(patterns)
    count = len(agents)
    truthful = has_truthful_query_channel(config)
    accessible = 0.0
    for aid in agents:
        reach = set(valid[aid])
        if truthful:
            for other in neighbors.get(aid, []):
                reach.update(valid.get(other, frozenset()))
        accessible += len(reach) / total
    known: frozenset[Pattern] = frozenset[Pattern]().union(*valid.values())
    return KnowledgeSnapshot(
        active_agents=count,
        individual_coverage_mean=sum(len(v) for v in valid.values()) / total / count,
        collective_coverage=len(known) / total,
        accessible_coverage_mean=accessible / count,
        pattern_prevalence={p: sum(p in v for v in valid.values()) / count for p in patterns},
        pattern_false_prevalence={p: sum(p in f for f in false.values()) / count for p in patterns},
        false_belief_prevalence=sum(1 for f in false.values() if f) / count,
    )


def judge_decision(action: AgentAction, reachable_truth: Mapping[int, float]) -> bool:
    """M2: juzga la intención contra la verdad alcanzable al decidir (no vacía)."""
    if action.action_type is ActionType.INTERACT:
        return reachable_truth.get(action.target, 0.0) > 0
    return all(value < 0 for value in reachable_truth.values())


class MetricsCollector:
    """Acumula M2 desde el inicio de la corrida y arma un `TickMetrics` por tick."""

    def __init__(self, config: SimulationConfig) -> None:
        self._config = config
        self._opportunities = 0
        self._correct = 0

    def record_tick(
        self,
        tick: int,
        agents: Mapping[int, MicroAgent],
        world_patterns: Mapping[Pattern, float],
        neighbors: Mapping[int, list[int]],
        decision_opportunities: int,
        correct_decisions: int,
        messages_sent: int,
    ) -> TickMetrics:
        self._opportunities += decision_opportunities
        self._correct += correct_decisions
        snap = knowledge_snapshot(agents, world_patterns, neighbors, self._config)
        active = snap.active_agents
        return TickMetrics(
            tick=tick,
            active_agents=active,
            individual_coverage_mean=snap.individual_coverage_mean,
            collective_coverage=snap.collective_coverage,
            accessible_coverage_mean=snap.accessible_coverage_mean,
            decision_opportunities=decision_opportunities,
            correct_decisions=correct_decisions,
            decision_accuracy=(
                correct_decisions / decision_opportunities if decision_opportunities else 0.0
            ),
            cumulative_decision_accuracy=(
                self._correct / self._opportunities if self._opportunities else 0.0
            ),
            pattern_prevalence=snap.pattern_prevalence,
            pattern_false_prevalence=snap.pattern_false_prevalence,
            false_belief_prevalence=snap.false_belief_prevalence,
            messages_sent=messages_sent,
            messages_per_agent=messages_sent / active if active else 0.0,
        )


def windowed_accuracy(history_slice: Sequence[TickMetrics]) -> float:
    """Precisión ponderada: `Σ correctas / Σ oportunidades` (0.0 sin oportunidades).

    Promediar `decision_accuracy` tick a tick sesgaría el resultado con los ticks vacíos.
    """
    opportunities = sum(m.decision_opportunities for m in history_slice)
    correct = sum(m.correct_decisions for m in history_slice)
    return correct / opportunities if opportunities else 0.0


def propagation_time(history: Sequence[TickMetrics], pattern: Pattern, theta: float) -> int | None:
    """M3: tiempo de subida normalizado desde el primer tick con prevalencia positiva.

    Devuelve el menor `t - t_0` con prevalencia `>= theta · P_max`, o `None` si `P_max == 0`.
    """
    if not 0.0 <= theta <= 1.0:
        raise ValueError(f"theta debe estar en [0, 1], recibido {theta}")
    series = [(m.tick, m.pattern_prevalence.get(pattern, 0.0)) for m in history]
    peak = max((value for _, value in series), default=0.0)
    if peak <= 0:
        return None
    start = next(tick for tick, value in series if value > 0)
    return next(tick - start for tick, value in series if tick >= start and value >= theta * peak)


# --- Fase II: telemetría evolutiva y holónica (design D28) ------------------------------------


@dataclass(frozen=True)
class EvolutionaryTickMetrics:
    tick: int
    active_agents: int
    mean_generation: float  # M8
    max_generation: int  # M8
    births_this_tick: int  # M8
    deaths_this_tick: int  # M8
    mean_energy: float  # M8
    offspring_social_ratio: float  # M9 (descriptiva: incluye testimonios horizontales)
    holon_count_by_level: tuple[tuple[int, int], ...]  # M10: pares (L, conteo), L >= 1
    max_holon_level: int  # M10
    mean_holon_size: float  # M10 (0.0 si no hay holones L >= 1)
    holonic_coverage_gain: float  # M11 (1.0 si no hay holones L >= 1)
    composite_completions: int  # M12 (acumulado)
    acquired_coverage: float | None  # M13, métrica de C8 (None sin holones elegibles)
    redundancy_reduction: float | None  # M13, descriptiva
    eligible_holons: int  # M13
    stigmergy_active_cells: int


def correct_known_patterns(
    agent: MicroAgent, world_patterns: Mapping[Pattern, float], config: SimulationConfig
) -> frozenset[Pattern]:
    """K de M13 (por hoja): patrones elementales de la memoria, válidos y con el signo del mundo."""
    threshold = config.decision_conf_threshold
    return frozenset(
        unit.pattern
        for unit in agent.memory.all_units()
        if unit.confidence >= threshold
        and (truth := world_patterns.get(unit.pattern)) is not None
        and _sign(unit.predicted_value) == _sign(truth)
    )


def _coverage_and_redundancy(knowledge: Sequence[frozenset[Pattern]]) -> tuple[int, float]:
    coverage = len(frozenset[Pattern]().union(*knowledge))
    total = sum(len(k) for k in knowledge)
    return coverage, (total - coverage) / total if total else 0.0


def _mean_or_none(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


class EvolutionaryMetricsCollector:
    """Arma un `EvolutionaryTickMetrics` por tick; el motor le pasa los contadores del tick."""

    def __init__(self, config: SimulationConfig) -> None:
        self._config = config

    def _valid(self, agent: MicroAgent) -> list[bool]:
        """Origen (`from_direct_experience`) de cada creencia válida de la memoria.

        Sólo cuenta las que `counts_as_knowledge`: las métricas de la Fase II no ven el cadáver de
        R35 (D48.3, precisión 80). Sin R35 no hay cadáveres y nada cambia.
        """
        threshold = self._config.decision_conf_threshold
        return [
            unit.from_direct_experience
            for unit in agent.memory.all_units()
            if unit.confidence >= threshold and counts_as_knowledge(unit.pattern)
        ]

    def record_tick(
        self,
        tick: int,
        agents: Mapping[int, MicroAgent],
        root_nodes: Mapping[int, AgentNode],
        world_patterns: Mapping[Pattern, float],
        births: int,
        deaths: int,
        composite_completions: int,
        stigmergy_active_cells: int,
    ) -> EvolutionaryTickMetrics:
        config = self._config
        count = len(agents)
        population = list(agents.values())

        offspring = [self._valid(a) for a in population if a.generation >= 1]
        valid_total = sum(len(origins) for origins in offspring)
        social = sum(not direct for origins in offspring for direct in origins)

        roots = [root_nodes[nid] for nid in sorted(root_nodes)]
        holons = [n for root in roots for n in composite_nodes(root)]
        levels: dict[int, int] = {}
        for holon in holons:
            levels[holon.holon_level] = levels.get(holon.holon_level, 0) + 1
        root_holons = [root for root in roots if isinstance(root, CompositeAgent)]

        gains: list[float] = []
        for holon in root_holons:
            collective = sum(
                u.confidence >= config.decision_conf_threshold and counts_as_knowledge(u.pattern)
                for u in holon.collective_memory().values()
            )
            leaves = holon.leaf_agents
            mean_leaf = sum(len(self._valid(leaf)) for leaf in leaves) / len(leaves)
            gains.append(collective / mean_leaf if mean_leaf > 0 else 1.0)

        acquired: list[float] = []
        reductions: list[float] = []
        for holon in root_holons:
            if not holon.formed_by_bond or tick - holon.formation_tick < 1:
                continue
            leaves = holon.leaf_agents
            now = [correct_known_patterns(leaf, world_patterns, config) for leaf in leaves]
            cov, red = _coverage_and_redundancy(now)
            cov0, red0 = _coverage_and_redundancy([k for _, k in holon.formation_knowledge])
            acquired.append((cov - cov0) / len(leaves))
            reductions.append(red0 - red)

        return EvolutionaryTickMetrics(
            tick=tick,
            active_agents=count,
            mean_generation=sum(a.generation for a in population) / count if count else 0.0,
            max_generation=max((a.generation for a in population), default=0),
            births_this_tick=births,
            deaths_this_tick=deaths,
            mean_energy=sum(a.energy for a in population) / count if count else 0.0,
            offspring_social_ratio=social / valid_total if valid_total else 0.0,
            holon_count_by_level=tuple(sorted(levels.items())),
            max_holon_level=max(levels, default=0),
            mean_holon_size=(
                sum(len(h.leaf_agents) for h in root_holons) / len(root_holons)
                if root_holons
                else 0.0
            ),
            holonic_coverage_gain=sum(gains) / len(gains) if gains else 1.0,
            composite_completions=composite_completions,
            acquired_coverage=_mean_or_none(acquired),
            redundancy_reduction=_mean_or_none(reductions),
            eligible_holons=len(acquired),
            stigmergy_active_cells=stigmergy_active_cells,
        )


def holon_ticks(history: Sequence[EvolutionaryTickMetrics]) -> int:
    """Exposición de una corrida a M13: cantidad de pares (tick, holón elegible)."""
    return sum(m.eligible_holons for m in history)


def holon_tick_mean(
    history: Sequence[EvolutionaryTickMetrics],
    field: Literal["acquired_coverage", "redundancy_reduction"],
) -> float | None:
    """Media de M13 de una corrida sobre los pares (tick, holón elegible); `None` sin pares.

    Cada tick pesa por sus holones elegibles, así que una condición con menos holones no se
    acerca a 0 por tener menos exposición (D28).
    """
    pairs = holon_ticks(history)
    if pairs == 0:
        return None
    total = 0.0
    for m in history:
        value = getattr(m, field)
        if value is not None:
            total += value * m.eligible_holons
    return total / pairs


# --- Fase II-B: telemetría de evolución abierta (D53.2, D53.3, D63.2-D63.4) --------------------


@dataclass(frozen=True)
class GeneticTickMetrics:
    """Telemetría genética de un tick (D41, D53.2, precisiones 42, 43, 49 y 68, D63.2).

    Los promedios son sobre las hojas vivas al final del tick (precisión 10); los de codones, sobre
    las que tienen ADN. Con la población vacía los promedios valen 0.0 y los conteos 0.
    """

    # D41 y precisión 10.
    tick: int
    mean_chromosome_length: float
    mean_expressed_codons: float
    mean_plasmids: float
    endospores: int
    senescent_agents: int  # `tick - birth_tick > phenotype.lifespan`
    mean_age: float
    max_age: int
    explorers: int
    librarians: int
    nerves: int
    locked_holons: int
    hgt_transfers: int  # eventos del tick (precisión 5)
    crispr_rejections: int
    crispr_purges: int
    # D53.2.
    distinct_genotypes: int
    mean_functional_codons: float  # descriptiva
    regulated_expression_fraction: float  # descriptiva (precisión 42)
    policy_divergence: float  # métrica de C14
    communicating_fraction: float  # métrica de C15
    new_activity: int  # Bedau-Packard por nacimientos portadores (precisión 43)
    cumulative_new_activity: int
    # Precisiones 42, 43 y 49.
    mean_expressible_codons: float  # descriptiva
    cumulative_births: int
    new_activity_per_birth: float  # métrica de C16
    mean_age_at_death: float  # covariable (precisión 49)
    mean_conditional_codons: float  # métrica de C13
    mean_expressible_nonattack_codons: float  # métrica de C17
    # D63.2.
    mean_internal_state_bits: float
    mean_plasticity_rate: float
    mean_abs_plastic_weight: float
    mean_learning_codons: float  # métrica de C19 (precisión 52)
    signaling_rate: float
    symbol_diversity: int
    max_signal_information: float  # descriptiva
    birth_source_ids: tuple[int, ...]  # precisión 68


@dataclass(frozen=True)
class EcologyTickMetrics:
    """Telemetría ecológica de un tick (D53.3, D63.3, D63.4).

    Los contadores son los eventos del tick (`frame.events`, precisión 20); `share_rate` es
    `shares` sobre las decisiones del tick (precisiones 5 y 85).
    """

    tick: int
    resources_available: int
    shares: int
    attacks: int
    successful_attacks: int
    predation_deaths: int
    starvation_deaths: int
    carcasses_deposited: int
    carcasses_eaten: int
    sporulations: int
    recombinations: int
    share_rate: float  # métrica de C18
    behavior_counts: tuple[int, ...]  # decisiones por `Behavior`, en el orden de D46.1
    signals_emitted: int
    plastic_updates: int
    decision_opportunities: int  # M2 del tick (D63.4), métrica de C20
    correct_decisions: int


# Contadores de `EcologyTickMetrics` que se copian de `frame.events` (precisión 20).
_ECOLOGY_EVENTS = (
    "shares",
    "attacks",
    "successful_attacks",
    "predation_deaths",
    "starvation_deaths",
    "carcasses_deposited",
    "carcasses_eaten",
    "sporulations",
    "recombinations",
)


class Birth(NamedTuple):
    """Un nacimiento del tick: su fuente genética (precisión 68) y el ADN con que nació.

    La fuente es el `agent_id` cuyo ADN hereda el hijo antes de mutar: el progenitor con
    selección; el donante en la reproducción neutral (también en $R_{17}$, precisión 41); con
    $R_{38}$, el que inicia el cruce, sin la pareja. `dna` es el del hijo al nacer (`None` sin
    ADN): la actividad cuenta los individuos que nacieron portando un codón (precisión 43).
    """

    source_id: int
    dna: CompactDNA | None


class DecisionRecord(NamedTuple):
    """Una decisión del tick (precisión 5) para la telemetría genética de la Fase 3.

    `signals` es `None` si la decisión no se tomó con la política genética; `divergent` dice si
    la primera conducta factible según el ADN del agente difiere de la del ADN fundador.
    """

    emitted: int  # máscara de símbolos emitidos (R41); 0 sin emisión
    signals: SensorySignals | None
    divergent: bool


class DecisionGenetics(NamedTuple):
    """Lo que la telemetría genética lee de las decisiones del tick, en `on_decisions`."""

    policy_divergence: float
    signaling_rate: float
    symbol_diversity: int
    max_signal_information: float


NO_DECISIONS = DecisionGenetics(0.0, 0.0, 0, 0.0)


class DecisionEcology(NamedTuple):
    """Las decisiones del tick (precisión 5) y su conteo por `Behavior` (D53.3)."""

    decisions: int
    behavior_counts: tuple[int, ...]


def first_feasible_slot(drives: Sequence[float], feasible: Sequence[bool]) -> int | None:
    """La posición de la primera conducta factible en el orden de `GeneticPolicy` (D46.4).

    Se prueban las conductas con impulso positivo en orden de `(-d_B, posición)`; `None` si
    ninguna es factible (la decisión es `IDLE`).
    """
    for _, slot in sorted((-drive, slot) for slot, drive in enumerate(drives) if drive > 0):
        if feasible[slot]:
            return slot
    return None


def _binary_information(n11: int, n10: int, n01: int, n00: int) -> float:
    """Información mutua, en bits, entre dos variables binarias con esa tabla de conteos."""
    total = n11 + n10 + n01 + n00
    x1, y1 = n11 + n10, n11 + n01
    marginal = {(1, 1): x1 * y1, (1, 0): x1 * (total - y1)}
    marginal |= {(0, 1): (total - x1) * y1, (0, 0): (total - x1) * (total - y1)}
    joint = {(1, 1): n11, (1, 0): n10, (0, 1): n01, (0, 0): n00}
    info = 0.0
    for cell in ((1, 1), (1, 0), (0, 1), (0, 0)):
        count = joint[cell]
        if count:
            info += count / total * math.log2(count * total / marginal[cell])
    return info


_SIGNAL_FIELDS = tuple(f.name for f in fields(SensorySignals))
_SYMBOLS = 8  # símbolos de señal, `channel & 0x07` (D60.2)


def signal_information(samples: Sequence[tuple[int, SensorySignals]]) -> float:
    """`max_signal_information` (D63.2): el máximo, sobre los pares (símbolo $k$, campo $j$ de
    las `SensorySignals` del emisor), de la información mutua en bits entre "emitió $k$" y "$j$
    es verdadero" en las decisiones dadas; 0.0 sin decisiones o sin emisiones."""
    total = len(samples)
    emitted = 0
    for mask, _ in samples:
        emitted |= mask
    if not total or not emitted:
        return 0.0
    columns = [[bool(getattr(signals, name)) for _, signals in samples] for name in _SIGNAL_FIELDS]
    best = 0.0
    for k in range(_SYMBOLS):
        if not emitted >> k & 1:
            continue  # un símbolo que nadie emitió no informa nada
        sent = [bool(mask >> k & 1) for mask, _ in samples]
        for column in columns:
            n11 = sum(1 for s, v in zip(sent, column, strict=True) if s and v)
            n10 = sum(sent) - n11
            n01 = sum(column) - n11
            best = max(best, _binary_information(n11, n10, n01, total - n11 - n10 - n01))
    return best


def summarize_decisions(records: Sequence[DecisionRecord]) -> DecisionGenetics:
    """Telemetría genética de las decisiones del tick (D53.2, D63.2, precisión 5).

    `policy_divergence` es la fracción de las decisiones genéticas que divergen del fundador
    (0.0 sin ellas); `signaling_rate`, la de decisiones cuyo agente emitió algún símbolo;
    `symbol_diversity`, los símbolos distintos emitidos; y `max_signal_information`, la de
    `signal_information` sobre las decisiones genéticas, las únicas con señales.
    """
    if not records:
        return NO_DECISIONS
    genetic = [r for r in records if r.signals is not None]
    union = 0
    for record in records:
        union |= record.emitted
    return DecisionGenetics(
        policy_divergence=(
            sum(1 for r in genetic if r.divergent) / len(genetic) if genetic else 0.0
        ),
        signaling_rate=sum(1 for r in records if r.emitted) / len(records),
        symbol_diversity=union.bit_count(),
        max_signal_information=signal_information(
            [(r.emitted, r.signals) for r in genetic if r.signals is not None]
        ),
    )


def ecology_tick_metrics(
    tick: int,
    resources_available: int,
    events: Mapping[str, int],
    decisions: DecisionEcology,
    decision_opportunities: int,
    correct_decisions: int,
) -> EcologyTickMetrics:
    """Arma el `EcologyTickMetrics` del tick a partir de los eventos y de las decisiones."""
    counts = {name: events.get(name, 0) for name in _ECOLOGY_EVENTS}
    return EcologyTickMetrics(
        tick=tick,
        resources_available=resources_available,
        **counts,
        share_rate=counts["shares"] / decisions.decisions if decisions.decisions else 0.0,
        behavior_counts=decisions.behavior_counts,
        signals_emitted=events.get("signals_emitted", 0),
        plastic_updates=events.get("plastic_updates", 0),
        decision_opportunities=decision_opportunities,
        correct_decisions=correct_decisions,
    )


class _Genotype(NamedTuple):
    """Consultas por genotipo de una hoja, que dependen sólo de su ADN y del protocolo."""

    expressible: int
    nonattack: int
    conditional: int
    functional: int
    learning: int  # sin la condición del modo 3
    learning_plastic: int  # con ella (hoja con `plasticity_rate > 0`)


_ATTACK_TARGET = 0x45  # destino de `ATTACK` (D46.1): inerte en `no_predation` (precisión 42)
_ROLE_FIELDS = (EpigeneticRole.EXPLORER, EpigeneticRole.LIBRARIAN, EpigeneticRole.NERVE)


class GeneticMetricsCollector:
    """Arma un `GeneticTickMetrics` por tick y acumula lo que cruza ticks (precisiones 43 y 49).

    Guarda la actividad $a_c$ de cada valor canónico funcional ausente del cromosoma fundador,
    la actividad nueva acumulada, los nacimientos y las edades de las muertes. Las consultas por
    genotipo se guardan por instancia de ADN mientras alguna hoja viva la porte, así que el
    resultado no depende del caché. No consume generadores.
    """

    def __init__(self, config: SimulationConfig) -> None:
        self._config = config
        founder = founder_dna(config)
        self._founder_values = functional_codon_values(founder)
        # Los codones del fundador tienen el promotor constitutivo 0x00 (D32, D46.5): sus
        # impulsos no dependen de las señales, del contexto ni del estado del tick.
        if any((codon >> 24) & 0xFF for codon in founder.chromosome):  # pragma: no cover
            raise ValueError("el ADN fundador debe tener sólo el promotor constitutivo 0x00")
        signals = SensorySignals(**dict.fromkeys(_SIGNAL_FIELDS, False))
        self.founder_drives: tuple[float, ...] = evaluate_behavior(
            founder, EpigeneticContext(), signals, config
        ).drives
        self._activity: dict[int, int] = {}
        self._cumulative_new_activity = 0
        self._cumulative_births = 0
        self._death_age_sum = 0
        self._deaths = 0
        self._genotypes: dict[int, tuple[CompactDNA, _Genotype]] = {}

    def _genotype(
        self, dna: CompactDNA, cache: dict[int, tuple[CompactDNA, _Genotype]]
    ) -> _Genotype:
        key = id(dna)
        entry = cache.get(key) or self._genotypes.get(key)
        if entry is None or entry[0] is not dna:
            config = self._config
            holonic, roles = config.enable_holonic_hierarchy, config.enable_epigenetic_roles
            values = expressible_codons(dna, holonic, roles)
            fixed = learning_codons(dna, holonic, roles, False)
            entry = (
                dna,
                _Genotype(
                    expressible=len(values),
                    nonattack=sum(1 for v, _ in values if (v >> 16) & 0xFF != _ATTACK_TARGET),
                    conditional=sum(1 for _, conditional in values if conditional),
                    functional=trait_or_behavior_codons(dna),
                    learning=len(fixed),
                    learning_plastic=len(learning_codons(dna, holonic, roles, True)),
                ),
            )
        cache[key] = entry
        return entry[1]

    def _activity_step(
        self, births: Sequence[Birth], receptions: Sequence[tuple[CompactDNA, int]]
    ) -> int:
        """Suma los nacimientos portadores y las recepciones del tick a $a_c$ (precisión 43) y
        devuelve los valores que cruzaron `activity_threshold` en el tick."""
        founder = self._founder_values
        increments: Counter[int] = Counter()
        for birth in births:
            if birth.dna is not None:
                increments.update(functional_codon_values(birth.dna) - founder)
        for before, codon in receptions:
            # Cuenta si el codón recibido es funcional, no es fundador y el receptor no lo portaba.
            value = canonical_codon(codon)
            functional = value in functional_codon_values(CompactDNA((codon,)))
            if functional and value not in founder and value not in functional_codon_values(before):
                increments[value] += 1
        threshold = self._config.activity_threshold
        crossed = 0
        for value in sorted(increments):
            old = self._activity.get(value, 0)
            new = old + increments[value]
            self._activity[value] = new
            if old < threshold <= new:
                crossed += 1
        return crossed

    def record_tick(
        self,
        tick: int,
        agents: Mapping[int, MicroAgent],
        root_nodes: Mapping[int, AgentNode],
        events: Mapping[str, int],
        births: Sequence[Birth],
        death_ages: Sequence[int],
        receptions: Sequence[tuple[CompactDNA, int]],
        decisions: DecisionGenetics,
    ) -> GeneticTickMetrics:
        """El registro del tick, con el estado de las hojas vivas al final del tick.

        `births` son los nacimientos del tick, `death_ages` las edades de sus muertes (paso de
        muerte, sin las perturbaciones), `receptions` las conjugaciones que cambiaron el ADN del
        receptor (con su ADN anterior y el codón recibido) y `decisions` lo leído en
        `on_decisions` (precisión 126).
        """
        config = self._config
        new_activity = self._activity_step(births, receptions)
        self._cumulative_new_activity += new_activity
        self._cumulative_births += len(births)
        self._deaths += len(death_ages)
        self._death_age_sum += sum(death_ages)

        population = [agents[aid] for aid in sorted(agents)]
        count = len(population)
        ages = [tick - agent.birth_tick for agent in population]
        roles = Counter(agent.epigenetic_role for agent in population)
        awake = [agent for agent in population if not agent.is_endospore]
        weights = [abs(w) for agent in population for w in agent.plastic_weights.values()]

        cache: dict[int, tuple[CompactDNA, _Genotype]] = {}
        chromosomes: set[tuple[int, ...]] = set()
        dna_count = lengths = plasmids = expressed = 0
        expressible = nonattack = conditional = functional = learning = 0
        regulated = 0.0
        for agent in population:
            dna = agent.dna
            if dna is None:  # sin ADN, las medias genéticas valen 0.0 (precisión 10)
                continue
            dna_count += 1
            expressed += agent.phenotype.expressed_codons
            genotype = self._genotype(dna, cache)
            chromosomes.add(dna.chromosome)
            lengths += len(dna.chromosome)
            plasmids += len(dna.plasmids)
            expressible += genotype.expressible
            nonattack += genotype.nonattack
            conditional += genotype.conditional
            functional += genotype.functional
            if genotype.expressible:
                regulated += genotype.conditional / genotype.expressible
            plastic = agent.phenotype.plasticity_rate > 0
            learning += genotype.learning_plastic if plastic else genotype.learning
        self._genotypes = cache  # sólo los ADN de las hojas vivas

        def mean(total: float, n: int) -> float:
            return total / n if n else 0.0

        births_total = self._cumulative_births
        return GeneticTickMetrics(
            tick=tick,
            mean_chromosome_length=mean(lengths, count),
            mean_expressed_codons=mean(expressed, count),
            mean_plasmids=mean(plasmids, count),
            endospores=count - len(awake),
            senescent_agents=sum(
                1
                for agent, age in zip(population, ages, strict=True)
                if age > agent.phenotype.lifespan
            ),
            mean_age=mean(sum(ages), count),
            max_age=max(ages, default=0),
            explorers=roles[_ROLE_FIELDS[0]],
            librarians=roles[_ROLE_FIELDS[1]],
            nerves=roles[_ROLE_FIELDS[2]],
            locked_holons=sum(
                1
                for nid in sorted(root_nodes)
                for holon in composite_nodes(root_nodes[nid])
                if is_effectively_locked(holon, config)
            ),
            hgt_transfers=events.get("hgt_transfers", 0),
            crispr_rejections=events.get("crispr_rejections", 0),
            crispr_purges=events.get("crispr_purges", 0),
            distinct_genotypes=len(chromosomes),
            mean_functional_codons=mean(functional, dna_count),
            regulated_expression_fraction=mean(regulated, dna_count),
            policy_divergence=decisions.policy_divergence,
            communicating_fraction=mean(
                sum(1 for agent in awake if agent.phenotype.comm_propensity >= 0.5), len(awake)
            ),
            new_activity=new_activity,
            cumulative_new_activity=self._cumulative_new_activity,
            mean_expressible_codons=mean(expressible, dna_count),
            cumulative_births=births_total,
            new_activity_per_birth=mean(self._cumulative_new_activity, births_total),
            mean_age_at_death=mean(self._death_age_sum, self._deaths),
            mean_conditional_codons=mean(conditional, dna_count),
            mean_expressible_nonattack_codons=mean(nonattack, dna_count),
            mean_internal_state_bits=mean(
                sum(agent.internal_state.bit_count() for agent in population), count
            ),
            mean_plasticity_rate=mean(
                sum(agent.phenotype.plasticity_rate for agent in population), count
            ),
            mean_abs_plastic_weight=mean(sum(weights), len(weights)),
            mean_learning_codons=mean(learning, dna_count),
            signaling_rate=decisions.signaling_rate,
            symbol_diversity=decisions.symbol_diversity,
            max_signal_information=decisions.max_signal_information,
            birth_source_ids=tuple(sorted(birth.source_id for birth in births)),
        )


# Posición de cada `Behavior` en `behavior_counts` (el orden de la tabla de D46.1).
BEHAVIOR_SLOTS = {behavior: slot for slot, behavior in enumerate(BEHAVIORS)}
