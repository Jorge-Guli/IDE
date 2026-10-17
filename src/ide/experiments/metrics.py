"""Métricas poblacionales M1 a M7 (`experimental-suite`).

Sólo cuentan las creencias de `BoundedMemory`. Una creencia es válida si su signo coincide con
el del mundo y su confianza alcanza `decision_conf_threshold`; es falsa si el signo es opuesto
con la misma confianza.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.types import ActionType, AgentAction, Pattern


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
