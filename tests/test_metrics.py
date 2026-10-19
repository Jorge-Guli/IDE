"""Tests de las métricas M1 a M7 y de la telemetría evolutiva M8 a M13 (`experimental-suite`)."""

import dataclasses
from dataclasses import replace
from typing import Any

import pytest

from ide.agent.holon import AgentNode, CompositeAgent
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.types import ActionType, AgentAction, KnowledgeUnit, Pattern
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.metrics import (
    EvolutionaryMetricsCollector,
    EvolutionaryTickMetrics,
    MetricsCollector,
    TickMetrics,
    correct_known_patterns,
    holon_tick_mean,
    holon_ticks,
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


# --- Fase II: telemetría evolutiva y holónica M8 a M13 (design D28) ----------------------------

TICK_METRICS_FIELDS = [
    "tick", "active_agents", "individual_coverage_mean", "collective_coverage",
    "accessible_coverage_mean", "decision_opportunities", "correct_decisions",
    "decision_accuracy", "cumulative_decision_accuracy", "pattern_prevalence",
    "pattern_false_prevalence", "false_belief_prevalence", "messages_sent", "messages_per_agent",
]  # fmt: skip
EVOLUTIONARY_FIELDS = [
    "tick", "active_agents", "mean_generation", "max_generation", "births_this_tick",
    "deaths_this_tick", "mean_energy", "offspring_social_ratio", "holon_count_by_level",
    "max_holon_level", "mean_holon_size", "holonic_coverage_gain", "composite_completions",
    "acquired_coverage", "redundancy_reduction", "eligible_holons", "stigmergy_active_cells",
]  # fmt: skip


def record(
    tick: int,
    agents: list[MicroAgent],
    roots: list[AgentNode] | None = None,
    **counters: int,
) -> EvolutionaryTickMetrics:
    """Un tick del colector; sin `roots`, cada agente es su propio nodo raíz."""
    nodes = roots if roots is not None else list(agents)
    base = {"births": 0, "deaths": 0, "composite_completions": 0, "stigmergy_active_cells": 0}
    return EvolutionaryMetricsCollector(CFG).record_tick(
        tick,
        {a.agent_id: a for a in agents},
        {n.node_id: n for n in nodes},
        WORLD,
        **{**base, **counters},
    )


def bonded(node_id: int, *children: AgentNode, tick: int = 0) -> CompositeAgent:
    """Holón formado por BOND en `tick`, con el estado de formación que completa el motor."""
    holon = CompositeAgent(node_id, tuple(children), tick, True)
    holon.formation_knowledge = tuple(
        (leaf.agent_id, correct_known_patterns(leaf, WORLD, CFG)) for leaf in holon.leaf_agents
    )
    return holon


def forget(agent: MicroAgent, i: int) -> None:
    assert agent.memory.remove(pat(i))


def learn(agent: MicroAgent, i: int, value: float = 1.0) -> None:
    agent.memory.upsert(KnowledgeUnit(pat(i), value, 0.9, 1, 0, True), 0, force=True)


def test_campos_de_tick_metrics_y_de_la_telemetria_evolutiva() -> None:
    assert [f.name for f in dataclasses.fields(TickMetrics)] == TICK_METRICS_FIELDS
    assert [f.name for f in dataclasses.fields(EvolutionaryTickMetrics)] == EVOLUTIONARY_FIELDS


def test_holon_de_nivel_uno_con_dos_especialistas() -> None:
    """Escenario de la spec: estructura holónica (M10) y ganancia holónica (M11)."""
    a = agent_with(0, (0, 1.0, 0.9), (1, 1.0, 0.9))
    b = agent_with(1, (2, 1.0, 0.9), (3, 1.0, 0.9))
    loner = agent_with(2, (4, 1.0, 0.9))
    m = record(5, [a, b, loner], [bonded(-2, a, b), loner], births=1, deaths=2)
    assert m.holon_count_by_level == ((1, 1),)
    assert m.max_holon_level == 1
    assert m.mean_holon_size == pytest.approx(2.0, abs=1e-9)
    assert m.holonic_coverage_gain == pytest.approx(2.0, abs=1e-9)  # 4 patrones / 2 por hoja
    assert (m.tick, m.active_agents, m.births_this_tick, m.deaths_this_tick) == (5, 3, 1, 2)


def test_holones_anidados_por_nivel() -> None:
    a, b, c, d = (agent_with(i, (i, 1.0, 0.9)) for i in range(4))
    inner = bonded(-2, a, b)
    outer = bonded(-3, inner, c)
    m = record(1, [a, b, c, d], [outer, d])
    assert m.holon_count_by_level == ((1, 1), (2, 1))
    assert m.max_holon_level == 2
    assert m.mean_holon_size == pytest.approx(3.0, abs=1e-9)  # sólo los holones raíz


def test_poblacion_extinguida_en_la_telemetria_evolutiva() -> None:
    m = record(9, [], deaths=4, composite_completions=7, stigmergy_active_cells=2)
    assert (m.mean_generation, m.max_generation, m.mean_energy) == (0.0, 0, 0.0)
    assert m.offspring_social_ratio == 0.0
    assert (m.holon_count_by_level, m.max_holon_level, m.mean_holon_size) == ((), 0, 0.0)
    assert m.holonic_coverage_gain == 1.0
    assert (m.acquired_coverage, m.redundancy_reduction, m.eligible_holons) == (None, None, 0)
    assert (m.composite_completions, m.stigmergy_active_cells, m.deaths_this_tick) == (7, 2, 4)


def test_generaciones_energia_y_proporcion_social() -> None:
    """M8 y M9: la proporción social sólo mira descendientes y creencias válidas."""
    founder = agent_with(0, (0, 1.0, 0.9))
    child = MicroAgent.from_lineage(1, CFG, founder.genome, 0.5, 2, 0)
    child.memory.upsert(KnowledgeUnit(pat(1), 1.0, 0.9, 1, 0, True), 0, force=True)
    child.memory.upsert(KnowledgeUnit(pat(2), 1.0, 0.6, 1, 0, False), 0, force=True)
    child.memory.upsert(KnowledgeUnit(pat(3), 1.0, 0.1, 1, 0, False), 0, force=True)  # débil
    m = record(3, [founder, child])
    assert m.mean_generation == pytest.approx(1.0, abs=1e-9)
    assert m.max_generation == 2
    assert m.mean_energy == pytest.approx((CFG.initial_energy + 0.5) / 2, abs=1e-9)
    assert m.offspring_social_ratio == pytest.approx(0.5, abs=1e-9)


def test_holon_que_gana_cobertura_despues_de_formarse() -> None:
    """Escenario de la spec (M13): de 2 a 3 patrones distintos, entre 2 hojas."""
    a = agent_with(0, (0, 1.0, 0.9), (1, 1.0, 0.9))
    b = agent_with(1, (0, 1.0, 0.9))
    holon = bonded(-2, a, b, tick=0)
    assert record(0, [a, b], [holon]).acquired_coverage is None  # recién formado
    forget(b, 0)
    learn(b, 2)
    learn(b, 7)  # signo incorrecto: no cuenta
    m = record(2, [a, b], [holon])
    assert m.acquired_coverage == pytest.approx(0.5, abs=1e-9)
    assert m.redundancy_reduction == pytest.approx(1 / 3, abs=1e-9)
    assert m.eligible_holons == 1
    plain = record(2, [a, b])
    assert (plain.acquired_coverage, plain.redundancy_reduction) == (None, None)
    assert plain.eligible_holons == 0


def test_olvidar_un_duplicado_no_suma() -> None:
    a = agent_with(0, (0, 1.0, 0.9))
    b = agent_with(1, (0, 1.0, 0.9))
    holon = bonded(-2, a, b, tick=0)
    forget(b, 0)
    m = record(1, [a, b], [holon])
    assert m.acquired_coverage == pytest.approx(0.0, abs=1e-9)
    assert m.redundancy_reduction == pytest.approx(0.5, abs=1e-9)


def test_los_holones_nacidos_por_r17_no_entran() -> None:
    a = agent_with(0, (0, 1.0, 0.9))
    b = agent_with(1, (1, 1.0, 0.9))
    holon = CompositeAgent(-2, (a, b), 0, formed_by_bond=False)
    m = record(5, [a, b], [holon])
    assert m.acquired_coverage is None
    assert m.eligible_holons == 0
    assert m.holon_count_by_level == ((1, 1),)


def test_la_muerte_de_una_hoja_no_cuenta_como_ganancia(monkeypatch: pytest.MonkeyPatch) -> None:
    """Escenario de la spec: B muere en el tick 1 y el holón reinicia su estado de formación."""
    config = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=3,
        resources_per_pattern=4,
        comm_enabled=False,
        enable_evolution=True,
        enable_holonic_hierarchy=True,
        holon_bond_threshold=1.0,
        metabolic_base_cost=0.0,
        memory_capacity_cost=0.0,
        sensory_radius_cost=0.0,
        holon_coord_cost=0.0,
        reproduction_threshold=100.0,
    )
    engine = SimulationEngine(config)
    a, b, c = (engine.agents[i] for i in range(3))
    for agent in (a, b, c):
        idle = AgentAction(ActionType.IDLE)
        monkeypatch.setattr(agent, "decide_action", lambda *_args, x=idle: x)
    learn(a, 0)
    learn(b, 1)
    learn(c, 2)
    holon = bonded(engine.next_holon_id, a, b, c, tick=0)
    engine.next_holon_id -= 1
    engine.root_nodes = {holon.node_id: holon}
    engine.agent_to_root = dict.fromkeys(range(3), holon.node_id)
    engine.step()  # tick 0: recién formado, no es elegible
    learn(a, 1)  # A duplica lo que sabe B
    b.apply_energy_delta(-b.energy)
    engine.step()  # tick 1: B muere en la Fase 5
    assert sorted(engine.agents) == [0, 2]
    assert holon.formation_tick == 1
    assert holon.formation_knowledge == ((0, frozenset({pat(0), pat(1)})), (2, frozenset({pat(2)})))
    assert engine.evolutionary_history[-1].acquired_coverage is None
    assert engine.evolutionary_history[-1].eligible_holons == 0
    engine.step()  # tick 2: sin otros cambios
    assert engine.evolutionary_history[-1].acquired_coverage == pytest.approx(0.0, abs=1e-9)
    assert engine.evolutionary_history[-1].eligible_holons == 1


def evo_tick(
    tick: int, acquired: float | None, reduction: float | None, eligible: int
) -> EvolutionaryTickMetrics:
    return EvolutionaryTickMetrics(
        tick, 2, 0.0, 0, 0, 0, 1.0, 0.0, (), 0, 0.0, 1.0, 0, acquired, reduction, eligible, 0
    )


def test_media_por_par_tick_holon() -> None:
    """La media de una corrida pondera cada tick por sus holones elegibles (D28)."""
    history = [evo_tick(0, 0.5, 0.2, 2), evo_tick(1, None, None, 0), evo_tick(2, -0.1, 0.5, 1)]
    assert holon_ticks(history) == 3
    assert holon_tick_mean(history, "acquired_coverage") == pytest.approx(0.3, abs=1e-9)
    assert holon_tick_mean(history, "redundancy_reduction") == pytest.approx(0.3, abs=1e-9)
    empty = [evo_tick(0, None, None, 0)]
    assert holon_ticks(empty) == 0
    assert holon_tick_mean(empty, "acquired_coverage") is None
    assert holon_tick_mean([], "redundancy_reduction") is None
