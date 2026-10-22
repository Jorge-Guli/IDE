"""Tests de las métricas M1 a M7 y de la telemetría evolutiva M8 a M13 (`experimental-suite`)."""

import dataclasses
from dataclasses import replace
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.dna import encode_codon, founder_dna, learning_codons
from ide.agent.holon import AgentNode, CompositeAgent
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.types import (
    ActionType,
    AgentAction,
    Behavior,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    KnowledgeUnit,
    Pattern,
    SensorySignals,
)
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.metrics import (
    NO_DECISIONS,
    Birth,
    DecisionEcology,
    DecisionGenetics,
    DecisionRecord,
    EcologyTickMetrics,
    EvolutionaryMetricsCollector,
    EvolutionaryTickMetrics,
    GeneticMetricsCollector,
    GeneticTickMetrics,
    MetricsCollector,
    TickMetrics,
    correct_known_patterns,
    ecology_tick_metrics,
    first_feasible_slot,
    holon_tick_mean,
    holon_ticks,
    judge_decision,
    knowledge_snapshot,
    propagation_time,
    signal_information,
    summarize_decisions,
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


# --- Fase II-B: telemetría de evolución abierta (bloque 21; D53.2, D53.3, D63.2-D63.4) ---------

GENETIC_FIELDS = [
    "tick", "mean_chromosome_length", "mean_expressed_codons", "mean_plasmids", "endospores",
    "senescent_agents", "mean_age", "max_age", "explorers", "librarians", "nerves",
    "locked_holons", "hgt_transfers", "crispr_rejections", "crispr_purges",
    "distinct_genotypes", "mean_functional_codons", "regulated_expression_fraction",
    "policy_divergence", "communicating_fraction", "new_activity", "cumulative_new_activity",
    "mean_expressible_codons", "cumulative_births", "new_activity_per_birth",
    "mean_age_at_death", "mean_conditional_codons", "mean_expressible_nonattack_codons",
    "mean_internal_state_bits", "mean_plasticity_rate", "mean_abs_plastic_weight",
    "mean_learning_codons", "signaling_rate", "symbol_diversity", "max_signal_information",
    "birth_source_ids",
]  # fmt: skip
ECOLOGY_FIELDS = [
    "tick", "resources_available", "shares", "attacks", "successful_attacks",
    "predation_deaths", "starvation_deaths", "carcasses_deposited", "carcasses_eaten",
    "sporulations", "recombinations", "share_rate", "behavior_counts", "signals_emitted",
    "plastic_updates", "decision_opportunities", "correct_decisions",
]  # fmt: skip
DNA_CFG = SimulationConfig(enable_evolution=True, enable_compact_dna=True)
GENETIC_CFG = replace(DNA_CFG, enable_genetic_policy=True)
HOLONIC_DNA_CFG = replace(DNA_CFG, enable_holonic_hierarchy=True)
TRAITS = tuple(encode_codon(0x00, t) for t in range(9))
FOUNDER13 = founder_dna(GENETIC_CFG).chromosome
NEW_C = encode_codon(0x00, 0x44, 0, 0, 10)  # SHARE: ausente del fundador
SIGNAL_NAMES = tuple(f.name for f in dataclasses.fields(SensorySignals))


def dna_agent(
    aid: int,
    chromosome: tuple[int, ...],
    plasmids: tuple[int, ...] = (),
    config: SimulationConfig = GENETIC_CFG,
) -> MicroAgent:
    agent = MicroAgent(aid, config)
    agent.set_dna(CompactDNA(chromosome=chromosome, plasmids=plasmids))
    return agent


def genetic(
    tick: int,
    agents: list[MicroAgent],
    config: SimulationConfig = GENETIC_CFG,
    collector: GeneticMetricsCollector | None = None,
    roots: list[AgentNode] | None = None,
    events: dict[str, int] | None = None,
    births: list[Birth] | None = None,
    death_ages: list[int] | None = None,
    receptions: list[tuple[CompactDNA, int]] | None = None,
    decisions: DecisionGenetics = NO_DECISIONS,
) -> GeneticTickMetrics:
    """Un registro de `GeneticTickMetrics`; sin `roots`, cada agente es su propio nodo raíz."""
    nodes = roots if roots is not None else list(agents)
    collector = collector if collector is not None else GeneticMetricsCollector(config)
    return collector.record_tick(
        tick,
        {a.agent_id: a for a in agents},
        {n.node_id: n for n in nodes},
        events or {},
        births or [],
        death_ages or [],
        receptions or [],
        decisions,
    )


def sig(**true_fields: bool) -> SensorySignals:
    values = dict.fromkeys(SIGNAL_NAMES, False)
    values.update(true_fields)
    return SensorySignals(**values)


def set_phenotype(agent: MicroAgent, **fields: Any) -> None:
    agent._phenotype = replace(agent.phenotype, **fields)  # pyright: ignore[reportPrivateUsage]


def test_campos_de_la_telemetria_genetica() -> None:
    assert [f.name for f in dataclasses.fields(GeneticTickMetrics)] == GENETIC_FIELDS
    assert len(GENETIC_FIELDS) == 36
    registered = genetic(0, [])
    with pytest.raises(dataclasses.FrozenInstanceError):
        registered.tick = 1  # type: ignore[misc]


def test_campos_de_la_telemetria_ecologica() -> None:
    assert [f.name for f in dataclasses.fields(EcologyTickMetrics)] == ECOLOGY_FIELDS
    assert len(ECOLOGY_FIELDS) == 17
    registered = ecology_tick_metrics(0, 3, {}, DecisionEcology(0, (0,) * 8), 0, 0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        registered.shares = 1  # type: ignore[misc]


def test_metricas_previas_sin_cambios() -> None:
    assert len(TICK_METRICS_FIELDS) == 14
    assert [f.name for f in dataclasses.fields(TickMetrics)] == TICK_METRICS_FIELDS
    assert [f.name for f in dataclasses.fields(EvolutionaryTickMetrics)] == EVOLUTIONARY_FIELDS


def test_telemetria_genetica_con_la_poblacion_vacia() -> None:
    m = genetic(9, [])
    assert (m.tick, m.mean_age, m.max_age) == (9, 0.0, 0)
    assert isinstance(m.mean_age, float) and isinstance(m.max_age, int)
    assert m.distinct_genotypes == 0
    assert m.mean_functional_codons == 0.0
    assert m.mean_expressible_codons == 0.0
    assert m.mean_expressible_nonattack_codons == 0.0
    assert m.mean_conditional_codons == 0.0
    assert m.regulated_expression_fraction == 0.0
    assert m.communicating_fraction == 0.0
    assert m.mean_internal_state_bits == 0.0
    assert m.mean_plasticity_rate == 0.0
    assert m.mean_abs_plastic_weight == 0.0
    assert m.mean_learning_codons == 0.0
    assert m.signaling_rate == 0.0
    assert m.symbol_diversity == 0
    assert m.max_signal_information == 0.0
    assert m.birth_source_ids == ()
    assert (m.mean_chromosome_length, m.mean_expressed_codons, m.mean_plasmids) == (0.0, 0.0, 0.0)
    assert (m.endospores, m.senescent_agents, m.locked_holons) == (0, 0, 0)
    assert (m.explorers, m.librarians, m.nerves) == (0, 0, 0)
    assert (m.new_activity, m.cumulative_new_activity, m.cumulative_births) == (0, 0, 0)
    assert (m.new_activity_per_birth, m.mean_age_at_death, m.policy_divergence) == (0.0, 0.0, 0.0)


def test_poblacion_sin_adn() -> None:
    """Escenario de la spec: sin ADN las medias genéticas valen 0.0 y la edad sale de birth_tick."""
    config = SimulationConfig(
        enable_evolution=True, enable_telomere_senescence=True, telomere_base_lifespan=600
    )
    old = MicroAgent(0, config)  # nacido en el tick 0
    m = genetic(700, [old, MicroAgent(1, config)], config=config)
    assert (m.mean_chromosome_length, m.mean_expressed_codons, m.mean_plasmids) == (0.0, 0.0, 0.0)
    assert m.senescent_agents == 2
    assert m.mean_age == pytest.approx(700.0, abs=1e-9)
    assert m.max_age == 700
    assert m.distinct_genotypes == 0
    assert m.mean_expressible_codons == 0.0
    assert m.mean_learning_codons == 0.0
    assert genetic(600, [old], config=config).senescent_agents == 0  # `age > lifespan`, estricto


def test_campos_heredados_de_d41() -> None:
    config = replace(GENETIC_CFG, enable_holonic_hierarchy=True)
    a = dna_agent(0, FOUNDER13, plasmids=(NEW_C,), config=config)
    b = dna_agent(1, FOUNDER13[:9], config=config)
    c = dna_agent(2, FOUNDER13, config=config)
    a.set_epigenetic_role(EpigeneticRole.EXPLORER)
    b.set_epigenetic_role(EpigeneticRole.NERVE)
    c.set_epigenetic_role(EpigeneticRole.NERVE)
    c.set_endospore(True)
    m = genetic(
        4,
        [a, b, c],
        config=config,
        events={"hgt_transfers": 2, "crispr_rejections": 1, "crispr_purges": 3, "shares": 9},
    )
    assert m.mean_chromosome_length == pytest.approx((13 + 9 + 13) / 3, abs=1e-9)
    assert m.mean_plasmids == pytest.approx(1 / 3, abs=1e-9)
    expressed = sum(x.phenotype.expressed_codons for x in (a, b, c))
    assert m.mean_expressed_codons == pytest.approx(expressed / 3, abs=1e-9)
    assert (m.endospores, m.explorers, m.librarians, m.nerves) == (1, 1, 0, 2)
    assert (m.hgt_transfers, m.crispr_rejections, m.crispr_purges) == (2, 1, 3)
    assert m.distinct_genotypes == 2  # cromosomas distintos: los plásmidos no cuentan


def test_eventos_de_conjugacion_por_tick() -> None:
    """Escenario de la spec: los contadores son del tick, no acumulados."""
    collector = GeneticMetricsCollector(GENETIC_CFG)
    t30 = genetic(30, [], collector=collector, events={"hgt_transfers": 2, "crispr_rejections": 1})
    t31 = genetic(31, [], collector=collector)
    assert (t30.hgt_transfers, t30.crispr_rejections) == (2, 1)
    assert (t31.hgt_transfers, t31.crispr_rejections) == (0, 0)


def test_holones_soldados() -> None:
    config = replace(GENETIC_CFG, enable_holonic_hierarchy=True, enable_symbiotic_ratchet=True)
    a, b, c, d = (dna_agent(i, FOUNDER13, config=config) for i in range(4))
    inner = CompositeAgent(-2, (a, b), 0, True)
    outer = CompositeAgent(-3, (inner, c), 0, True)
    inner.is_locked = True
    outer.is_locked = True
    assert genetic(1, [a, b, c, d], config=config, roots=[outer, d]).locked_holons == 2
    inert = replace(config, enable_symbiotic_ratchet=False)  # R31 inerte: el sello no rige
    assert genetic(1, [a, b, c, d], config=inert, roots=[outer, d]).locked_holons == 0


@pytest.mark.parametrize(
    ("births", "expected"),
    [
        ([Birth(30, None), Birth(4, None)], (4, 30)),  # neutral: los donantes, no los padres
        ([Birth(12, None), Birth(5, None)], (5, 12)),  # selección: los progenitores
        ([Birth(30, None), Birth(30, None)], (30, 30)),  # un donante repetido
        ([Birth(30, None)], (30,)),  # recombinación neutral: sin la pareja
        ([], ()),
    ],
)
def test_fuentes_geneticas_de_los_nacimientos(
    births: list[Birth], expected: tuple[int, ...]
) -> None:
    assert genetic(3, [], births=births).birth_source_ids == expected


def test_codones_funcionales_y_expresables_del_fundador_conductual() -> None:
    m = genetic(0, [dna_agent(i, FOUNDER13) for i in range(3)])
    assert m.distinct_genotypes == 1
    assert m.mean_functional_codons == 13.0
    assert m.mean_expressible_codons == 13.0
    assert m.mean_expressible_nonattack_codons == 13.0
    assert m.mean_conditional_codons == 0.0
    assert m.regulated_expression_fraction == 0.0
    assert m.mean_learning_codons == 0.0


def test_codon_inerte_por_su_modo() -> None:
    m = genetic(0, [dna_agent(0, (*FOUNDER13, encode_codon(0x00, 0x40, 3)))])
    assert m.mean_functional_codons == 13.0


def test_duplicados_e_inertes_no_suman() -> None:
    extra = (encode_codon(0x00, 0x00), encode_codon(0x00, 0x01, 3), encode_codon(0x00, 0x10))
    m = genetic(0, [dna_agent(0, (*TRAITS, *extra), config=DNA_CFG)], config=DNA_CFG)
    assert m.mean_expressible_codons == 9.0
    assert m.mean_functional_codons == 10.0


def test_codon_con_promotor_reservado() -> None:
    m = genetic(0, [dna_agent(0, (*FOUNDER13, encode_codon(0x0B, 0x43)))])
    assert m.mean_expressible_codons == 13.0


def test_sinonimo_por_el_campo_channel() -> None:
    synonym = encode_codon(0x00, 0x03, 0, 12)
    m = genetic(0, [dna_agent(0, (*TRAITS, synonym), config=DNA_CFG)], config=DNA_CFG)
    assert m.mean_expressible_codons == 9.0
    assert m.mean_functional_codons == 10.0


def test_un_codon_attack_no_suma() -> None:
    m = genetic(0, [dna_agent(0, (*FOUNDER13, encode_codon(0x00, 0x45, 0, 0, 64)))])
    assert m.mean_expressible_codons == 14.0
    assert m.mean_expressible_nonattack_codons == 13.0


def test_borrar_codones_constitutivos_no_sube_los_condicionales() -> None:
    stress = encode_codon(0x18, 0x01, 0, 0, 10)
    with_founders = genetic(0, [dna_agent(0, (*TRAITS, stress), config=DNA_CFG)], config=DNA_CFG)
    alone = genetic(0, [dna_agent(0, (stress,), config=DNA_CFG)], config=DNA_CFG)
    assert with_founders.regulated_expression_fraction == pytest.approx(0.1, abs=1e-9)
    assert alone.regulated_expression_fraction == pytest.approx(1.0, abs=1e-9)
    assert with_founders.mean_conditional_codons == alone.mean_conditional_codons == 1.0


def test_promotor_de_nivel_con_y_sin_holones() -> None:
    chromosome = (
        encode_codon(0x00, 0x00),
        encode_codon(0x00, 0x01),
        encode_codon(0x00, 0x02),
        encode_codon(0x01, 0x03),
    )
    agent = dna_agent(0, chromosome, config=DNA_CFG)
    holonic = genetic(0, [agent], config=HOLONIC_DNA_CFG)
    flat = genetic(0, [agent], config=DNA_CFG)
    assert holonic.regulated_expression_fraction == pytest.approx(0.25, abs=1e-9)
    assert flat.regulated_expression_fraction == 0.0


def test_promotor_de_estres() -> None:
    chromosome = (*(encode_codon(0x00, t) for t in range(4)), encode_codon(0x18, 0x04))
    m = genetic(0, [dna_agent(0, chromosome, config=DNA_CFG)], config=DNA_CFG)
    assert m.regulated_expression_fraction == pytest.approx(0.2, abs=1e-9)


def test_hoja_sin_codones_expresables_aporta_cero() -> None:
    half = dna_agent(0, (encode_codon(0x00, 0x00), encode_codon(0x18, 0x01)), config=DNA_CFG)
    none = dna_agent(1, (encode_codon(0x0B, 0x00),), config=DNA_CFG)
    m = genetic(0, [half, none], config=DNA_CFG)
    assert m.regulated_expression_fraction == pytest.approx(0.25, abs=1e-9)
    assert m.mean_expressible_codons == pytest.approx(1.0, abs=1e-9)


def test_independencia_del_estado_del_tick() -> None:
    chromosome = (*FOUNDER13, encode_codon(0x18, 0x42, 0, 0, 40), encode_codon(0x00, 0x45))
    active = dna_agent(0, chromosome)
    dormant = dna_agent(1, chromosome)
    dormant.set_endospore(True)
    dormant.apply_energy_delta(-1.0)
    dormant.set_epigenetic_role(EpigeneticRole.LIBRARIAN)
    a = genetic(0, [active])
    b = genetic(0, [dormant])
    for name in (
        "mean_conditional_codons",
        "mean_expressible_nonattack_codons",
        "mean_expressible_codons",
        "regulated_expression_fraction",
    ):
        assert getattr(a, name) == getattr(b, name)
    assert a.mean_conditional_codons == 1.0


def test_fraccion_comunicante() -> None:
    zero = replace(GENETIC_CFG, comm_propensity_base=0.0)
    founders = [MicroAgent(i, zero) for i in range(3)]
    assert genetic(0, founders, config=zero).communicating_fraction == 0.0
    talker, mute, spore = (MicroAgent(i, GENETIC_CFG) for i in range(3))
    set_phenotype(mute, comm_propensity=0.49)
    set_phenotype(spore, comm_propensity=0.0)
    spore.set_endospore(True)  # las endosporas no cuentan, ni en el denominador
    assert genetic(0, [talker, mute, spore]).communicating_fraction == pytest.approx(0.5, abs=1e-9)


# --- Actividad de Bedau-Packard por nacimientos (precisión 43) ----------------------------------


def carrier(*extra: int, plasmids: tuple[int, ...] = ()) -> CompactDNA:
    return CompactDNA(chromosome=(*FOUNDER13, *extra), plasmids=plasmids)


def activity_run(
    threshold: int, ticks: dict[int, dict[str, Any]], last: int
) -> list[GeneticTickMetrics]:
    config = replace(GENETIC_CFG, activity_threshold=threshold)
    collector = GeneticMetricsCollector(config)
    return [
        genetic(t, [], config=config, collector=collector, **ticks.get(t, {}))
        for t in range(last + 1)
    ]


def test_una_hoja_longeva_no_hace_cruzar_el_umbral() -> None:
    history = activity_run(10, {1: {"births": [Birth(0, carrier(NEW_C))]}}, 500)
    assert all(m.new_activity == 0 for m in history)
    assert history[-1].cumulative_new_activity == 0


def test_los_codones_fundadores_no_cuentan() -> None:
    births = [Birth(0, carrier()) for _ in range(100)]
    history = activity_run(10, {1: {"births": births}}, 3)
    assert all(m.new_activity == 0 and m.cumulative_new_activity == 0 for m in history)
    assert history[-1].cumulative_births == 100


def test_un_individuo_cuenta_una_vez_por_valor_canonico() -> None:
    synonym = encode_codon(0x00, 0x44, 0, 5, 10)  # difiere de NEW_C sólo en `channel`
    dna = carrier(NEW_C, NEW_C, synonym, plasmids=(NEW_C,))
    one = activity_run(2, {1: {"births": [Birth(0, dna)]}}, 2)
    two = activity_run(2, {1: {"births": [Birth(0, dna)]}, 2: {"births": [Birth(0, dna)]}}, 2)
    assert [m.new_activity for m in one] == [0, 0, 0]  # a_c = 1, no 4
    assert [m.new_activity for m in two] == [0, 0, 1]


def test_recepcion_por_conjugacion() -> None:
    receptions = [(carrier(), NEW_C), (carrier(NEW_C), NEW_C)]
    crossed = activity_run(1, {0: {"receptions": receptions}}, 0)
    not_twice = activity_run(2, {0: {"receptions": receptions}}, 0)
    assert crossed[0].new_activity == 1
    assert not_twice[0].new_activity == 0  # la segunda recepción no suma


def test_cruce_del_umbral_por_nacimientos() -> None:
    four = [Birth(0, carrier(NEW_C)) for _ in range(4)]
    history = activity_run(10, {t: {"births": four} for t in (1, 2, 3)}, 5)
    assert [m.new_activity for m in history] == [0, 0, 0, 1, 0, 0]
    assert [m.cumulative_new_activity for m in history] == [0, 0, 0, 1, 1, 1]


def test_actividad_sin_nacimientos() -> None:
    other = encode_codon(0x00, 0x46, 0, 0, 10)
    receptions = [(carrier(), NEW_C), (carrier(), other)]
    m = activity_run(1, {5: {"receptions": receptions}}, 5)[-1]
    assert m.cumulative_new_activity == 2
    assert m.cumulative_births == 0
    assert m.new_activity_per_birth == 0.0


def test_normalizacion_por_nacimientos() -> None:
    births = [Birth(0, carrier()) for _ in range(288)]
    births += [Birth(0, carrier(encode_codon(0x00, 0x44, 0, 0, k))) for k in range(1, 13)]
    m = activity_run(1, {0: {"births": births}}, 0)[-1]
    assert m.cumulative_new_activity == 12
    assert m.cumulative_births == 300
    assert m.new_activity_per_birth == pytest.approx(0.04, abs=1e-9)


def test_edad_media_al_morir() -> None:
    collector = GeneticMetricsCollector(GENETIC_CFG)
    assert genetic(0, [], collector=collector).mean_age_at_death == 0.0
    at_50 = genetic(50, [], collector=collector, death_ages=[40])
    at_80 = genetic(80, [], collector=collector, death_ages=[80])
    assert at_50.mean_age_at_death == pytest.approx(40.0, abs=1e-9)
    assert at_80.mean_age_at_death == pytest.approx(60.0, abs=1e-9)


# --- Estado interno, plasticidad y codones de aprendizaje (D63.2, precisión 52) -----------------


def test_medias_de_estado_y_de_pesos() -> None:
    a, b = MicroAgent(0, GENETIC_CFG), MicroAgent(1, GENETIC_CFG)
    a._internal_state = 0b11  # pyright: ignore[reportPrivateUsage]
    b._internal_state = 0b1  # pyright: ignore[reportPrivateUsage]
    set_phenotype(a, plasticity_rate=0.2)
    set_phenotype(b, plasticity_rate=0.4)
    a._plastic_weights.update({0: 0.5, 2: -0.3})  # pyright: ignore[reportPrivateUsage]
    m = genetic(0, [a, b])
    assert m.mean_internal_state_bits == pytest.approx(1.5, abs=1e-9)
    assert m.mean_plasticity_rate == pytest.approx(0.3, abs=1e-9)
    assert m.mean_abs_plastic_weight == pytest.approx(0.4, abs=1e-9)
    assert genetic(0, [b]).mean_abs_plastic_weight == 0.0


def test_codon_plastico_segun_la_tasa() -> None:
    extra = (
        encode_codon(0x00, 0x0D, 0, 1),
        encode_codon(0x31, 0x40, 0, 0, 64),
        encode_codon(0x00, 0x43, 3, 0, 32),
    )
    agent = dna_agent(0, (*FOUNDER13, *extra))
    set_phenotype(agent, plasticity_rate=0.0)
    assert genetic(0, [agent]).mean_learning_codons == 2.0
    set_phenotype(agent, plasticity_rate=0.3)
    assert genetic(0, [agent]).mean_learning_codons == 3.0


def test_promotor_de_estado_sobre_un_rasgo() -> None:
    m = genetic(0, [dna_agent(0, (*FOUNDER13, encode_codon(0x31, 0x00, 0, 0, 64)))])
    assert m.mean_learning_codons == 0.0


def test_tasa_de_plasticidad_segun_el_ultimo_contexto() -> None:
    config = replace(GENETIC_CFG, enable_plasticity=True, plasticity_rate_base=0.0)
    extra = (encode_codon(0x18, 0x0F, 0, 0, 64), encode_codon(0x00, 0x43, 3, 0, 32))
    agent = dna_agent(0, (*FOUNDER13, *extra), config=config)
    agent.express(EpigeneticContext(0, EpigeneticRole.NONE, 0.1), 1)  # estrés
    assert agent.phenotype.plasticity_rate > 0
    assert genetic(1, [agent], config=config).mean_learning_codons == 1.0
    agent.express(EpigeneticContext(0, EpigeneticRole.NONE, 0.9), 2)
    assert genetic(2, [agent], config=config).mean_learning_codons == 0.0


# --- Decisiones del tick: divergencia y señales (D53.2, D63.2) ----------------------------------


def test_primera_conducta_factible() -> None:
    drives = (0.5, 0.9, 0.0, 0.9, -1.0, 0.1, 0.0, 0.0)
    assert first_feasible_slot(drives, (True,) * 8) == 1  # empate: menor posición
    assert first_feasible_slot(drives, (True, False, True, True, True, True, True, True)) == 3
    assert first_feasible_slot(drives, (False, False, True, False, True, False, True, True)) is None
    assert first_feasible_slot((0.0,) * 8, (True,) * 8) is None


def test_tasa_y_diversidad_de_las_senales() -> None:
    records = [DecisionRecord(mask, sig(), False) for mask in (0b10010, 0b10000, 0b10000)]
    records += [DecisionRecord(0, sig(), False) for _ in range(7)]
    d = summarize_decisions(records)
    assert d.signaling_rate == pytest.approx(0.3, abs=1e-9)
    assert d.symbol_diversity == 2


def test_senal_perfectamente_informativa() -> None:
    records = [
        DecisionRecord(1, sig(known_good=True), False),
        DecisionRecord(1, sig(known_good=True), False),
        DecisionRecord(0, sig(), False),
        DecisionRecord(0, sig(), False),
    ]
    assert summarize_decisions(records).max_signal_information == pytest.approx(1.0, abs=1e-9)


def test_sin_emisiones() -> None:
    d = summarize_decisions([DecisionRecord(0, sig(unknown=True), False) for _ in range(5)])
    assert (d.signaling_rate, d.symbol_diversity, d.max_signal_information) == (0.0, 0, 0.0)
    assert summarize_decisions([]) == NO_DECISIONS


def test_divergencia_sobre_las_decisiones_geneticas() -> None:
    records = [
        DecisionRecord(0, sig(), True),
        DecisionRecord(0, sig(), False),
        DecisionRecord(0, None, False),  # decidió sin la política genética: no cuenta
    ]
    assert summarize_decisions(records).policy_divergence == pytest.approx(0.5, abs=1e-9)
    assert summarize_decisions([DecisionRecord(0, None, False)]).policy_divergence == 0.0


@given(
    st.lists(
        st.tuples(st.integers(0, 255), st.lists(st.booleans(), min_size=12, max_size=12)),
        max_size=30,
    )
)
def test_informacion_mutua_acotada(samples: list[tuple[int, list[bool]]]) -> None:
    value = signal_information([(mask, SensorySignals(*flags)) for mask, flags in samples])
    assert 0.0 <= value <= 1.0 + 1e-9


# --- Telemetría ecológica (D53.3, D63.3, D63.4) -------------------------------------------------


def test_tasa_de_transferencia_y_conteos() -> None:
    counts = (3, 0, 0, 1, 0, 0, 0, 0)
    events = {"shares": 2, "attacks": 5, "successful_attacks": 2, "predation_deaths": 1}
    events |= {"starvation_deaths": 4, "carcasses_deposited": 5, "carcasses_eaten": 1}
    events |= {"sporulations": 2, "recombinations": 3, "signals_emitted": 3}
    events |= {"plastic_updates": 1, "hgt_transfers": 7}
    m = ecology_tick_metrics(6, 11, events, DecisionEcology(40, counts), 2, 1)
    assert m.shares == 2 and m.share_rate == pytest.approx(0.05, abs=1e-9)
    assert (m.tick, m.resources_available) == (6, 11)
    assert (m.attacks, m.successful_attacks, m.predation_deaths, m.starvation_deaths) == (
        5,
        2,
        1,
        4,
    )
    assert (m.carcasses_deposited, m.carcasses_eaten, m.sporulations) == (5, 1, 2)
    assert (m.recombinations, m.signals_emitted, m.plastic_updates) == (3, 3, 1)
    assert (m.decision_opportunities, m.correct_decisions) == (2, 1)
    assert m.behavior_counts == counts
    assert len(m.behavior_counts) == len(Behavior)


def test_tasa_de_transferencia_sin_decisiones() -> None:
    m = ecology_tick_metrics(0, 0, {"shares": 0}, DecisionEcology(0, (0,) * 8), 0, 0)
    assert m.share_rate == 0.0


# --- Propiedades de las métricas por genotipo ---------------------------------------------------

_CODONS = st.integers(0, 2**32 - 1)
_LOW_CODONS = st.builds(
    encode_codon,
    st.sampled_from([0x00, 0x01, 0x05, 0x10, 0x18, 0x22, 0x31, 0x3A, 0x80, 0x81, 0xC0]),
    st.sampled_from([0x00, 0x03, 0x09, 0x0D, 0x0E, 0x0F, 0x10, 0x40, 0x43, 0x45, 0x48]),
    st.integers(0, 3),
    st.integers(0, 2),
    st.integers(-128, 127),
)


@given(
    st.lists(st.one_of(_CODONS, _LOW_CODONS), min_size=1, max_size=20),
    st.booleans(),
    st.booleans(),
)
def test_metricas_por_genotipo_acotadas(chromosome: list[int], holonic: bool, roles: bool) -> None:
    config = replace(DNA_CFG, enable_holonic_hierarchy=holonic, enable_epigenetic_roles=roles)
    dna = CompactDNA(chromosome=tuple(chromosome))
    m = genetic(0, [dna_agent(0, dna.chromosome, config=DNA_CFG)], config=config)
    assert 0.0 <= m.mean_conditional_codons <= m.mean_expressible_codons
    assert m.mean_expressible_nonattack_codons <= m.mean_expressible_codons
    assert 0.0 <= m.regulated_expression_fraction <= 1.0
    assert m.mean_expressible_codons <= m.mean_functional_codons + len(chromosome)
    fixed = set(learning_codons(dna, holonic, roles, False))
    assert fixed <= set(learning_codons(dna, holonic, roles, True))
