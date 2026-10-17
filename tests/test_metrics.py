"""Tests de las métricas M1 a M7 (`experimental-suite`)."""

from dataclasses import replace
from typing import Any

import pytest

from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.types import ActionType, AgentAction, KnowledgeUnit, Pattern
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.metrics import (
    MetricsCollector,
    TickMetrics,
    judge_decision,
    knowledge_snapshot,
    propagation_time,
    windowed_accuracy,
)
from ide.simulation.engine import SimulationEngine

CFG = SimulationConfig()
WORLD = {Pattern((("id", f"p_{i}"),)): (1.0 if i < 6 else -1.0) for i in range(12)}


def pat(i: int) -> Pattern:
    return Pattern((("id", f"p_{i}"),))


def agent_with(
    aid: int, *beliefs: tuple[int, float, float], config: SimulationConfig = CFG
) -> MicroAgent:
    agent = MicroAgent(aid, config)
    for i, value, conf in beliefs:
        agent.memory.upsert(KnowledgeUnit(pat(i), value, conf, 1, 0, True), 0, force=True)
    return agent


def tick_metrics(
    tick: int, prevalence: dict[Pattern, float] | None = None, **fields: Any
) -> TickMetrics:
    base = TickMetrics(
        tick=tick,
        active_agents=1,
        individual_coverage_mean=0.0,
        collective_coverage=0.0,
        accessible_coverage_mean=0.0,
        decision_opportunities=0,
        correct_decisions=0,
        decision_accuracy=0.0,
        cumulative_decision_accuracy=0.0,
        pattern_prevalence=prevalence or {},
        pattern_false_prevalence={},
        false_belief_prevalence=0.0,
        messages_sent=0,
        messages_per_agent=0.0,
    )
    return replace(base, **fields)


# --- Instantánea epistémica --------------------------------------------------------------------


def test_poblacion_extinguida() -> None:
    snap = knowledge_snapshot({}, WORLD, {}, CFG)
    assert snap.active_agents == 0
    assert snap.individual_coverage_mean == 0.0
    assert snap.collective_coverage == 0.0
    assert snap.accessible_coverage_mean == 0.0
    assert snap.false_belief_prevalence == 0.0
    assert snap.pattern_prevalence == dict.fromkeys(sorted(WORLD), 0.0)
    assert snap.pattern_false_prevalence == dict.fromkeys(sorted(WORLD), 0.0)


def test_creencia_correcta_pero_debil_no_cuenta() -> None:
    agents = {0: agent_with(0, (0, 1.0, 0.30))}
    snap = knowledge_snapshot(agents, WORLD, {0: []}, CFG)
    assert snap.pattern_prevalence[pat(0)] == 0.0
    assert snap.pattern_false_prevalence[pat(0)] == 0.0
    assert snap.individual_coverage_mean == 0.0


def test_validez_y_falsedad_en_el_umbral() -> None:
    agents = {0: agent_with(0, (0, 0.4, 0.35), (7, 0.9, 0.35), (2, -0.2, 0.9))}
    snap = knowledge_snapshot(agents, WORLD, {0: []}, CFG)
    assert snap.pattern_prevalence[pat(0)] == 1.0  # signo correcto, c == umbral
    assert snap.pattern_false_prevalence[pat(7)] == 1.0  # p_7 es dañino
    assert snap.pattern_false_prevalence[pat(2)] == 1.0  # p_2 es benéfico
    assert snap.individual_coverage_mean == pytest.approx(1 / 12, abs=1e-9)
    assert snap.false_belief_prevalence == 1.0


def test_valor_cero_no_es_valido_ni_falso() -> None:
    agents = {0: agent_with(0, (0, 0.0, 0.9))}
    snap = knowledge_snapshot(agents, WORLD, {0: []}, CFG)
    assert snap.pattern_prevalence[pat(0)] == 0.0
    assert snap.pattern_false_prevalence[pat(0)] == 0.0


def three_neighbors() -> tuple[dict[int, MicroAgent], dict[int, list[int]]]:
    agents = {
        a: agent_with(a, *((3 * a + k, WORLD[pat(3 * a + k)], 0.9) for k in range(3)))
        for a in range(3)
    }
    neighbors = {a: [b for b in range(3) if b != a] for a in range(3)}
    return agents, neighbors


def test_meta_agente_de_tres_vecinos() -> None:
    agents, neighbors = three_neighbors()
    snap = knowledge_snapshot(agents, WORLD, neighbors, CFG)
    assert snap.accessible_coverage_mean == pytest.approx(0.75, abs=1e-9)
    assert snap.individual_coverage_mean == pytest.approx(0.25, abs=1e-9)
    assert snap.collective_coverage == pytest.approx(0.75, abs=1e-9)


@pytest.mark.parametrize(
    "overrides",
    [{"max_queries_per_tick": 0}, {"comm_enabled": False}, {"comm_content_null": True}],
)
def test_sin_consulta_no_hay_acceso(overrides: dict[str, Any]) -> None:
    agents, neighbors = three_neighbors()
    snap = knowledge_snapshot(agents, WORLD, neighbors, replace(CFG, **overrides))
    assert snap.accessible_coverage_mean == pytest.approx(0.25, abs=1e-9)
    assert snap.individual_coverage_mean == pytest.approx(0.25, abs=1e-9)


def test_prevalencias_por_patron() -> None:
    agents = {
        0: agent_with(0, (0, 1.0, 0.9), (6, 1.0, 0.9)),
        1: agent_with(1, (0, 1.0, 0.9)),
        2: agent_with(2),
        3: agent_with(3, (6, -1.0, 0.9)),
    }
    snap = knowledge_snapshot(agents, WORLD, {a: [] for a in agents}, CFG)
    assert snap.pattern_prevalence[pat(0)] == pytest.approx(0.5, abs=1e-9)
    assert snap.pattern_prevalence[pat(6)] == pytest.approx(0.25, abs=1e-9)
    assert snap.pattern_false_prevalence[pat(6)] == pytest.approx(0.25, abs=1e-9)
    assert snap.false_belief_prevalence == pytest.approx(0.25, abs=1e-9)
    assert snap.collective_coverage == pytest.approx(2 / 12, abs=1e-9)
    assert list(snap.pattern_prevalence) == sorted(WORLD)


def test_poblacion_sin_falsedades() -> None:
    engine = SimulationEngine(SimulationConfig(seed=3))
    for metrics in engine.run(30):
        assert metrics.false_belief_prevalence == 0.0
        assert all(v == 0.0 for v in metrics.pattern_false_prevalence.values())


# --- M1: cota de la cobertura individual -------------------------------------------------------


def test_cota_superior_de_la_cobertura_individual() -> None:
    engine = SimulationEngine(SimulationConfig())
    for metrics in engine.run(80):
        assert metrics.individual_coverage_mean <= 0.25 + 1e-12
        assert metrics.individual_coverage_mean <= metrics.accessible_coverage_mean + 1e-12


# --- M2 ----------------------------------------------------------------------------------------

MOVE = AgentAction(ActionType.MOVE, (0, 1))


def test_evitacion_correcta_de_un_recurso_toxico() -> None:
    assert judge_decision(MOVE, {4: -1.0}) is True


def test_omision_de_un_recurso_benefico() -> None:
    assert judge_decision(MOVE, {4: 1.0}) is False
    assert judge_decision(AgentAction(ActionType.IDLE), {4: -1.0, 5: 1.0}) is False


def test_consumo_de_un_benefico_y_de_un_toxico() -> None:
    assert judge_decision(AgentAction(ActionType.INTERACT, 5), {4: -1.0, 5: 1.0}) is True
    assert judge_decision(AgentAction(ActionType.INTERACT, 4), {4: -1.0, 5: 1.0}) is False


def test_interact_sobre_un_objetivo_inexistente_es_incorrecto() -> None:
    assert judge_decision(AgentAction(ActionType.INTERACT, 99), {4: 1.0}) is False


def test_tick_sin_oportunidades() -> None:
    collector = MetricsCollector(CFG)
    agents = {0: agent_with(0)}
    first = collector.record_tick(0, agents, WORLD, {0: []}, 4, 3, 0)
    assert first.decision_accuracy == pytest.approx(0.75, abs=1e-9)
    second = collector.record_tick(1, agents, WORLD, {0: []}, 0, 0, 0)
    assert second.decision_accuracy == 0.0
    assert second.cumulative_decision_accuracy == pytest.approx(0.75, abs=1e-9)
    third = collector.record_tick(2, agents, WORLD, {0: []}, 4, 1, 0)
    assert third.cumulative_decision_accuracy == pytest.approx(0.5, abs=1e-9)


def test_sin_oportunidades_desde_el_inicio() -> None:
    metrics = MetricsCollector(CFG).record_tick(0, {}, WORLD, {}, 0, 0, 0)
    assert metrics.decision_accuracy == 0.0
    assert metrics.cumulative_decision_accuracy == 0.0
    assert metrics.messages_per_agent == 0.0


def test_windowed_accuracy_ponderada() -> None:
    history = [
        tick_metrics(0, decision_opportunities=1, correct_decisions=1, decision_accuracy=1.0),
        tick_metrics(1, decision_opportunities=9, correct_decisions=0, decision_accuracy=0.0),
        tick_metrics(2),
    ]
    assert windowed_accuracy(history) == pytest.approx(0.1, abs=1e-9)
    assert windowed_accuracy(history[2:]) == pytest.approx(0.0, abs=1e-9)
    assert windowed_accuracy([]) == pytest.approx(0.0, abs=1e-9)


# --- M3 ----------------------------------------------------------------------------------------


def test_propagation_time() -> None:
    p = pat(3)
    series = [0.0, 0.0, 0.1, 0.3, 0.5, 0.4, 0.6]
    history = [tick_metrics(10 + t, {p: v}) for t, v in enumerate(series)]
    # t_0 = 12, P_max = 0.6: 50 % -> 0.3 en el tick 13; 90 % -> 0.54 en el tick 16.
    assert propagation_time(history, p, 0.5) == 1
    assert propagation_time(history, p, 0.9) == 4
    assert propagation_time(history, p, 0.0) == 0


def test_patron_nunca_descubierto() -> None:
    p = pat(3)
    history = [tick_metrics(t, {p: 0.0}) for t in range(5)]
    assert propagation_time(history, p, 0.5) is None
    assert propagation_time([], p, 0.5) is None


# --- M7 ----------------------------------------------------------------------------------------


def test_un_broadcast_con_tres_receptores() -> None:
    config = replace(
        SimulationConfig(grid_width=10, grid_height=10, num_agents=4, resources_per_pattern=1),
        max_queries_per_tick=0,
    )
    engine = SimulationEngine(config)
    grid = engine.env
    assert isinstance(grid, ToroidalGrid2D)
    # Los cuatro agentes en una misma celda vacía; sólo el agente 0 sabe algo.
    target = next(cell for cell in sorted(grid.cell_resources) if not grid.cell_resources[cell])
    for aid in range(4):
        while grid.get_agent_position(aid) != target:
            x, y = grid.get_agent_position(aid)
            dx = ((target[0] - x + 5) % 10) - 5
            dy = ((target[1] - y + 5) % 10) - 5
            grid.execute_action(
                aid, AgentAction(ActionType.MOVE, ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))), 0
            )
    engine.agents[0].memory.upsert(KnowledgeUnit(pat(0), 1.0, 0.9, 1, 0, True), 0, force=True)
    metrics = engine.step()
    assert metrics.messages_sent == 1
    assert metrics.messages_per_agent == pytest.approx(0.25, abs=1e-9)


@pytest.mark.parametrize("theta", [-0.1, 1.1, float("nan")])
def test_theta_fuera_de_rango(theta: float) -> None:
    history = [tick_metrics(0, {pat(3): 0.5})]
    with pytest.raises(ValueError, match="theta"):
        propagation_time(history, pat(3), theta)
