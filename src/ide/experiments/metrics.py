"""Métricas poblacionales M1 a M7 y telemetría evolutiva M8 a M13 (`experimental-suite`).

Sólo cuentan las creencias de `BoundedMemory`. Una creencia es válida si su signo coincide con
el del mundo y su confianza alcanza `decision_conf_threshold`; es falsa si el signo es opuesto
con la misma confianza.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from ide.agent.holon import AgentNode, CompositeAgent, composite_nodes
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.types import CARCASS_PATTERN, ActionType, AgentAction, Pattern


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

        No cuenta las creencias sobre `CARCASS_PATTERN`: las métricas de la Fase II no ven el
        cadáver de R35 (D48.3, precisión 80). Sin R35 no hay cadáveres y nada cambia.
        """
        threshold = self._config.decision_conf_threshold
        return [
            unit.from_direct_experience
            for unit in agent.memory.all_units()
            if unit.confidence >= threshold and unit.pattern != CARCASS_PATTERN
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
                u.confidence >= config.decision_conf_threshold and u.pattern != CARCASS_PATTERN
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
