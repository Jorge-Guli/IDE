"""Tests del estado interno persistente y de los eventos del tick anterior (bloque 13, R39).

Cubren `evaluate_behavior` y `BehaviorEvaluation` con `evaluate_drives` como envoltorio (D60.1);
los destinos `SET_STATE` y `CLEAR_STATE` con la regla de mayoría por bit, `clear` prevaleciente y
la aplicación al terminar la Fase 3 (D58.2, D58.3); los promotores de estado `0x30`-`0x37` y de
eventos `0x28`-`0x2B`, inactivos en el fenotipo (D58.4-D58.6); `EventSignals` calculados por el
motor al final del tick y guardados en `agent.last_events` (D58.5, precisión 64); el ciclo de
vida de `internal_state` (D58.1); la inercia sin $R_{39}$ (D58.7) y la aceptación de D46.5 con
las banderas de la ampliación activas y el ADN fundador (D57.1), además del determinismo entre
procesos con distinto `PYTHONHASHSEED`.
"""

import dataclasses
import os
import subprocess
import sys
import textwrap
from dataclasses import astuple, replace
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.dna import (
    BEHAVIOR_TARGETS,
    encode_codon,
    evaluate_behavior,
    evaluate_drives,
    founder_dna,
    internal_state_active,
    transcribe_phenotype,
)
from ide.agent.micro_agent import MicroAgent
from ide.agent.policy import GeneticPolicy, sensory_signals
from ide.config import SimulationConfig
from ide.domain.types import (
    ActionResult,
    ActionType,
    AgentAction,
    Behavior,
    BehaviorEvaluation,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    EventSignals,
    Observation,
    Pattern,
    SensorySignals,
)
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
from ide.simulation.engine import SimulationEngine
from ide.simulation.pipeline import (
    DECISION_SYSTEM,
    BaseSystem,
    EventsSystem,
    ExecutionSystem,
    ScheduleSystem,
    TickFrame,
    build_systems,
    genetic_policy_active,
)

ROOT = Path(__file__).resolve().parents[1]
CONSUME, EXPLORE, NAVIGATE, WANDER, SHARE, ATTACK, FLEE, SPORULATE = BEHAVIOR_TARGETS
SET_STATE, CLEAR_STATE = 0x0D, 0x0E
FOUNDER_TRAITS = tuple(encode_codon(0x00, t) for t in range(9))
ZERO_DRIVES = (0.0,) * 8
NO_PLASTIC: tuple[tuple[int, ...], ...] = ((),) * 8
IDLE = AgentAction(ActionType.IDLE)
CTX0 = EpigeneticContext()
SIGNAL_FIELDS = tuple(f.name for f in dataclasses.fields(SensorySignals))
EVENT_FIELDS = ("attacked", "ate", "lost_energy", "received_energy")


def config_with(**overrides: Any) -> SimulationConfig:
    """Configuración con $R_{32}$ efectivamente activa y $R_{39}$ salvo que se indique."""
    params: dict[str, Any] = {
        "enable_evolution": True,
        "enable_compact_dna": True,
        "enable_genetic_policy": True,
        "enable_internal_state": True,
    }
    params.update(overrides)
    return SimulationConfig(**params)


R39 = config_with()
NO_R39 = config_with(enable_internal_state=False)
ALL_AMPLIFICATION = config_with(enable_plasticity=True, enable_signals=True)


def signals(**true_fields: bool) -> SensorySignals:
    values = {name: False for name in SIGNAL_FIELDS}
    values.update(true_fields)
    return SensorySignals(**values)


def all_signals(value: bool) -> SensorySignals:
    return SensorySignals(**{name: value for name in SIGNAL_FIELDS})


def dna_of(*codons: int, plasmids: tuple[int, ...] = ()) -> CompactDNA:
    return CompactDNA(chromosome=tuple(codons), plasmids=plasmids)


def behave(
    *codons: int,
    config: SimulationConfig = R39,
    sig: SensorySignals | None = None,
    state: int = 0,
    perceived: int = 0,
) -> BehaviorEvaluation:
    return evaluate_behavior(
        dna_of(*codons), CTX0, sig or signals(), config, state=state, perceived=perceived
    )


# --- (a) evaluate_behavior y BehaviorEvaluation (D60.1) ----------------------------------------


def test_fundador_sin_estado_plasticidad_ni_senales() -> None:
    config = ALL_AMPLIFICATION
    evaluation = evaluate_behavior(
        founder_dna(config),
        CTX0,
        all_signals(True),
        config,
        state=0xFF,
        perceived=0xFF,
        plastic_weights={0: 1.0},
    )
    assert isinstance(evaluation, BehaviorEvaluation)
    assert evaluation.drives == pytest.approx((0.9921875, 0.75, 0.5, 0.25, 0, 0, 0, 0), abs=1e-9)
    assert evaluation.set_mask == evaluation.clear_mask == evaluation.emitted == 0
    assert evaluation.plastic == NO_PLASTIC


def test_valores_por_defecto_de_evaluate_behavior() -> None:
    dna = dna_of(encode_codon(0x00, WANDER, 0, 0, 64))
    assert evaluate_behavior(dna, CTX0, signals(), R39) == evaluate_behavior(
        dna, CTX0, signals(), R39, state=0, perceived=0, plastic_weights=None
    )


def test_destinos_reservados_inertes_en_la_conducta() -> None:
    config = ALL_AMPLIFICATION
    extra = tuple(
        encode_codon(0x00, target, mode, 0, 127)
        for target in (0x10, 0x3E, 0x3F, 0x49, 0x80, 0xFF)
        for mode in (0, 3)
    )
    founder = founder_dna(replace(config, enable_genetic_policy=False))
    dna = CompactDNA(chromosome=founder.chromosome + extra)
    phenotype = transcribe_phenotype(dna, CTX0, config)
    assert phenotype == transcribe_phenotype(founder, CTX0, config)
    assert phenotype.expressed_codons == 9
    evaluation = evaluate_behavior(dna, CTX0, all_signals(True), config, state=0xFF)
    assert evaluation == BehaviorEvaluation(ZERO_DRIVES, 0, 0, 0, NO_PLASTIC)


@pytest.mark.parametrize("promoter", [0x0B, 0x1A, 0x2C, 0x2F, 0x40, 0x7F, 0xC0])
def test_promotores_reservados_en_la_evaluacion_de_conducta(promoter: int) -> None:
    evaluation = behave(
        encode_codon(promoter, WANDER, 0, 0, 64),
        config=ALL_AMPLIFICATION,
        sig=all_signals(True),
        state=0xFF,
        perceived=0xFF,
    )
    assert evaluation.drives[3] == 0.0


@st.composite
def evaluation_inputs(draw: st.DrawFn) -> tuple[Any, ...]:
    promoters = st.sampled_from(
        [0x00, 0x01, 0x02, 0x11, 0x18, 0x19, 0x20, 0x23, 0x28, 0x2A, 0x2B, 0x30, 0x35, 0x81, 0x83]
    )
    targets = st.sampled_from([0x00, 0x09, SET_STATE, CLEAR_STATE, *BEHAVIOR_TARGETS, 0x48])
    codon = st.builds(
        encode_codon,
        promoters,
        targets,
        st.integers(0, 3),
        st.integers(0, 5),
        st.integers(-128, 127),
    )
    chromosome = tuple(draw(st.lists(codon, min_size=1, max_size=12)))
    plasmids = tuple(draw(st.lists(codon, max_size=3, unique=True)))
    context = EpigeneticContext(
        draw(st.integers(0, 3)),
        draw(st.sampled_from(list(EpigeneticRole))),
        draw(st.sampled_from([0.1, 0.5, 1.0])),
    )
    sig = SensorySignals(*(draw(st.booleans()) for _ in SIGNAL_FIELDS))
    config = draw(
        st.sampled_from([R39, NO_R39, ALL_AMPLIFICATION, config_with(enable_genetic_policy=False)])
    )
    return CompactDNA(chromosome, plasmids), context, sig, config


@given(evaluation_inputs())
def test_evaluate_drives_es_envoltorio_de_evaluate_behavior(inputs: tuple[Any, ...]) -> None:
    dna, context, sig, config = inputs
    assert (
        evaluate_drives(dna, context, sig, config)
        == evaluate_behavior(dna, context, sig, config).drives
    )


@given(evaluation_inputs(), st.integers(0, 255))
def test_evaluacion_de_conducta_determinista(inputs: tuple[Any, ...], state: int) -> None:
    dna, context, sig, config = inputs
    first = evaluate_behavior(dna, context, sig, config, state=state)
    second = evaluate_behavior(dna, context, sig, config, state=state)
    assert first == second
    assert 0 <= first.set_mask <= 0xFF and 0 <= first.clear_mask <= 0xFF


# --- (b) SET_STATE, CLEAR_STATE y la regla de mayoría (D58.2, D58.3) ---------------------------


MAJORITY = (
    encode_codon(0x00, SET_STATE, 0, 2),
    encode_codon(0x00, SET_STATE, 2, 10),
    encode_codon(0x00, SET_STATE, 1, 10),
    encode_codon(0x00, SET_STATE, 0, 5),
    encode_codon(0x00, SET_STATE, 1, 5),
    encode_codon(0x00, SET_STATE, 3, 4),
)


def test_mayoria_por_bit() -> None:
    evaluation = behave(*MAJORITY)
    assert evaluation.set_mask == 0b100
    assert evaluation.clear_mask == 0
    assert evaluation.drives == ZERO_DRIVES


def test_mayoria_en_clear_state() -> None:
    clear = tuple(
        encode_codon(decode_promoter, CLEAR_STATE, mode, channel)
        for decode_promoter, mode, channel in ((0x00, 0, 7), (0x00, 2, 15), (0x00, 1, 6))
    )
    assert behave(*clear).clear_mask == 0b10000000


def test_payload_ignorado_en_los_destinos_de_estado() -> None:
    for payload in (-128, 0, 127):
        assert behave(encode_codon(0x00, SET_STATE, 0, 3, payload)).set_mask == 0b1000


def test_mascaras_nulas_sin_r39() -> None:
    for config in (
        NO_R39,
        config_with(enable_genetic_policy=False),
        config_with(enable_compact_dna=False, enable_genetic_policy=False),
    ):
        evaluation = behave(*MAJORITY, encode_codon(0x00, CLEAR_STATE, 0, 1), config=config)
        assert evaluation.set_mask == 0 and evaluation.clear_mask == 0


def test_codones_de_estado_regulados_y_condicionados() -> None:
    # Un codón regulado por un canal encendido por un sensor también escribe el estado.
    codons = (encode_codon(0x23, 0x09, 0, 2), encode_codon(0x82, SET_STATE, 0, 1))
    assert behave(*codons, sig=signals(neighbor_adjacent=True)).set_mask == 0b10
    assert behave(*codons).set_mask == 0
    # Un evento del tick anterior condiciona la escritura.
    on_attack = encode_codon(0x28, SET_STATE, 0, 6)
    assert behave(on_attack, sig=signals(attacked=True)).set_mask == 0b1000000
    assert behave(on_attack).set_mask == 0


def test_plasmidos_cuentan_en_la_mayoria() -> None:
    plasmids = (encode_codon(0x00, SET_STATE, 0, 0), encode_codon(0x00, SET_STATE, 2, 8))
    dna = dna_of(encode_codon(0x00, SET_STATE, 1, 0), plasmids=plasmids)
    assert evaluate_behavior(dna, CTX0, signals(), R39).set_mask == 0b1


def agent_with(*codons: int, config: SimulationConfig = R39) -> MicroAgent:
    agent = MicroAgent(1, config, policy=GeneticPolicy())
    agent.set_dna(CompactDNA(chromosome=FOUNDER_TRAITS + codons))
    return agent


def set_state(agent: MicroAgent, value: int) -> None:
    agent._internal_state = value  # pyright: ignore[reportPrivateUsage]


def test_escribir_y_borrar_el_mismo_bit() -> None:
    agent = agent_with(encode_codon(0x00, SET_STATE, 0, 1), encode_codon(0x00, CLEAR_STATE, 0, 1))
    set_state(agent, 0b10000000)
    evaluation = agent.evaluate_behavior(signals())
    assert evaluation.set_mask == 0b10 and evaluation.clear_mask == 0b10
    agent.commit_internal_state()
    assert agent.internal_state == 0b10000000


def test_estado_siguiente_conserva_los_bits_sin_cambios() -> None:
    agent = agent_with(encode_codon(0x00, SET_STATE, 0, 0), encode_codon(0x00, CLEAR_STATE, 0, 3))
    set_state(agent, 0b10001000)
    agent.evaluate_behavior(signals())
    assert agent.internal_state == 0b10001000  # la evaluación no aplica el estado
    agent.commit_internal_state()
    assert agent.internal_state == 0b10000001


def test_aplicar_sin_evaluacion_no_cambia_el_estado() -> None:
    agent = agent_with(encode_codon(0x00, SET_STATE, 0, 0))
    agent.commit_internal_state()
    assert agent.internal_state == 0
    agent.evaluate_behavior(signals())
    agent.commit_internal_state()
    assert agent.internal_state == 1
    set_state(agent, 0)
    agent.commit_internal_state()  # la evaluación ya se aplicó: no se aplica dos veces
    assert agent.internal_state == 0


@given(
    st.integers(0, 255),
    st.lists(
        st.tuples(st.sampled_from([SET_STATE, CLEAR_STATE]), st.integers(0, 3), st.integers(0, 63)),
        max_size=10,
    ),
)
def test_estado_siguiente_por_propiedades(start: int, specs: list[tuple[int, int, int]]) -> None:
    agent = agent_with(
        *(encode_codon(0x00, target, mode, channel) for target, mode, channel in specs)
    )
    set_state(agent, start)
    evaluation = agent.evaluate_behavior(signals())
    agent.commit_internal_state()
    expected = (start | evaluation.set_mask) & ~evaluation.clear_mask & 0xFF
    assert agent.internal_state == expected
    assert 0 <= agent.internal_state <= 0xFF


# --- (c) promotores de estado y de eventos (D58.4-D58.6) ---------------------------------------


def test_promotor_de_estado_segun_el_bit() -> None:
    codon = encode_codon(0x33, WANDER, 0, 0, 64)
    assert behave(codon, state=0b00001000).drives[3] == pytest.approx(0.5, abs=1e-9)
    assert behave(codon, state=0b11110111).drives[3] == 0.0


@pytest.mark.parametrize("bit", range(8))
def test_cada_promotor_de_estado(bit: int) -> None:
    codon = encode_codon(0x30 + bit, CONSUME, 0, 0, 64)
    assert behave(codon, state=1 << bit).drives[0] == pytest.approx(0.5, abs=1e-9)
    assert behave(codon, state=0xFF & ~(1 << bit)).drives[0] == 0.0


def test_estado_inerte_sin_r39() -> None:
    codon = encode_codon(0x33, WANDER, 0, 0, 64)
    assert behave(codon, config=NO_R39, state=0xFF).drives[3] == 0.0
    no_policy = config_with(enable_genetic_policy=False)
    assert behave(codon, config=no_policy, state=0xFF).drives[3] == 0.0


def test_evento_de_ataque_sin_estado_interno() -> None:
    codon = encode_codon(0x28, FLEE, 0, 0, 64)
    assert behave(codon, config=NO_R39, sig=signals(attacked=True)).drives[6] == pytest.approx(
        0.5, abs=1e-9
    )
    assert behave(codon, config=NO_R39, sig=signals(attacked=False)).drives[6] == 0.0


@pytest.mark.parametrize("config", [R39, NO_R39])
@pytest.mark.parametrize("index", range(4))
def test_cada_promotor_de_eventos(config: SimulationConfig, index: int) -> None:
    codon = encode_codon(0x28 + index, ATTACK, 0, 0, 64)
    field = EVENT_FIELDS[index]
    assert behave(codon, config=config, sig=signals(**{field: True})).drives[5] == pytest.approx(
        0.5, abs=1e-9
    )
    others = {name: True for name in SIGNAL_FIELDS if name != field}
    assert behave(codon, config=config, sig=signals(**others)).drives[5] == 0.0


def test_evaluate_drives_lee_los_eventos() -> None:
    dna = dna_of(encode_codon(0x29, CONSUME, 0, 0, 64))
    assert evaluate_drives(dna, CTX0, signals(ate=True), NO_R39)[0] == pytest.approx(0.5, abs=1e-9)
    # `evaluate_drives` evalúa con `state=0`: un promotor de estado nunca se activa.
    state_dna = dna_of(encode_codon(0x30, CONSUME, 0, 0, 64))
    assert evaluate_drives(state_dna, CTX0, all_signals(True), R39) == ZERO_DRIVES


@pytest.mark.parametrize("promoter", [0x28, 0x29, 0x2A, 0x2B, *range(0x30, 0x38)])
def test_promotores_de_eventos_y_estado_inactivos_en_el_fenotipo(promoter: int) -> None:
    config = R39
    founder = founder_dna(config)
    dna = CompactDNA(chromosome=(*founder.chromosome, encode_codon(promoter, 0x00, 0, 0, 64)))
    for level in (0, 1, 5):
        for role in EpigeneticRole:
            for ratio in (0.1, 0.5, 1.0):
                ctx = EpigeneticContext(level, role, ratio)
                assert transcribe_phenotype(dna, ctx, config) == transcribe_phenotype(
                    founder, ctx, config
                )


def test_internal_state_active_es_r32_mas_la_bandera() -> None:
    for dna_flag in (False, True):
        for policy in (False, True):
            for flag in (False, True):
                config = SimulationConfig(
                    enable_evolution=True,
                    enable_compact_dna=dna_flag,
                    enable_genetic_policy=policy,
                    enable_internal_state=flag,
                )
                assert internal_state_active(config) == (genetic_policy_active(config) and flag)


# --- Señales y caché del agente (D58.5, D46.8) -------------------------------------------------


def observation() -> Observation:
    return Observation(1, 0, (), ((0, 1), (1, 0)), ())


def test_eventos_del_tick_anterior_en_las_senales() -> None:
    agent = agent_with()
    agent.set_last_events(EventSignals(attacked=True, lost_energy=True))
    sig = sensory_signals(agent, observation(), None)
    assert sig.attacked and sig.lost_energy
    assert not sig.ate and not sig.received_energy


def test_la_politica_decide_con_los_eventos() -> None:
    agent = agent_with(encode_codon(0x2B, WANDER, 0, 0, 64))
    g = np.random.Generator(np.random.PCG64(3))
    assert agent.decide_action(observation(), 0, g) == IDLE
    agent.set_last_events(EventSignals(received_energy=True))
    assert agent.decide_action(observation(), 0, g).action_type is ActionType.MOVE


def test_la_politica_decide_con_el_estado_anterior() -> None:
    agent = agent_with(encode_codon(0x30, WANDER, 0, 0, 64), encode_codon(0x00, SET_STATE, 0, 0))
    g = np.random.Generator(np.random.PCG64(3))
    assert agent.decide_action(observation(), 0, g) == IDLE
    assert agent.last_evaluation is not None and agent.last_evaluation.set_mask == 1
    agent.commit_internal_state()
    assert agent.decide_action(observation(), 1, g).action_type is ActionType.MOVE


@given(
    st.lists(
        st.tuples(
            st.sampled_from(
                [all_signals(False), signals(attacked=True), signals(ate=True, crowded=True)]
            ),
            st.integers(0, 255),
            st.sampled_from(
                [EpigeneticContext(0), EpigeneticContext(2, EpigeneticRole.NERVE, 0.9)]
            ),
            st.booleans(),
        ),
        max_size=12,
    )
)
def test_cache_de_la_evaluacion_igual_a_la_directa(steps: list[tuple[Any, ...]]) -> None:
    first = (
        encode_codon(0x30, WANDER, 0, 0, 64),
        encode_codon(0x28, SET_STATE, 0, 1),
        encode_codon(0x31, CLEAR_STATE, 0, 0),
        encode_codon(0x03, FLEE, 0, 0, 32),
    )
    second = (encode_codon(0x31, CONSUME, 0, 0, 64), encode_codon(0x29, SET_STATE, 0, 0))
    agent = agent_with(*first)
    for sig, state, context, swap in steps:
        if swap:
            agent.set_dna(CompactDNA(chromosome=FOUNDER_TRAITS + second))
        agent.express(context, 0)
        set_state(agent, state)
        assert agent.dna is not None
        expected = evaluate_behavior(
            agent.dna, agent.last_context, sig, agent.base_config, state=state
        )
        assert agent.evaluate_behavior(sig) == expected
        assert agent.evaluate_behavior(sig) == expected  # segunda lectura, desde el caché
        assert agent.last_evaluation == expected


# --- (e) ciclo de vida de internal_state y last_events (D58.1, D58.5) --------------------------


def test_estado_y_eventos_del_fundador() -> None:
    agent = MicroAgent(1, R39, policy=GeneticPolicy())
    assert agent.internal_state == 0
    assert agent.last_events == EventSignals()
    assert agent.last_evaluation is None


def test_estado_no_heredado() -> None:
    parent = agent_with()
    parent.apply_energy_delta(3.0)
    set_state(parent, 0b101)
    parent.set_last_events(EventSignals(ate=True))
    child = parent.create_offspring(9, 4, np.random.Generator(np.random.PCG64(0)))
    assert child.internal_state == 0
    assert child.last_events == EventSignals()
    assert child.last_evaluation is None
    assert parent.internal_state == 0b101
    assert parent.last_events == EventSignals(ate=True)


def test_estado_no_heredado_sin_adn() -> None:
    config = SimulationConfig(enable_evolution=True)
    parent = MicroAgent(1, config)
    parent.apply_energy_delta(3.0)
    set_state(parent, 0b11)
    child = parent.create_offspring(9, 4, np.random.Generator(np.random.PCG64(0)))
    assert child.internal_state == 0 and child.last_events == EventSignals()


def test_estado_conservado_en_endospora() -> None:
    agent = agent_with()
    set_state(agent, 0b11)
    agent.set_endospore(True)
    agent.set_endospore(False)
    assert agent.internal_state == 0b11


def test_estado_conservado_al_cambiar_el_adn() -> None:
    agent = agent_with()
    set_state(agent, 0b110)
    agent.set_dna(CompactDNA(chromosome=FOUNDER_TRAITS))
    assert agent.internal_state == 0b110


# --- Motor: sistemas, aplicación del estado y eventos ------------------------------------------


def small(**overrides: Any) -> SimulationConfig:
    """Configuración chica con $R_{32}$, $R_{36}$ y $R_{37}$, sin costos ni reproducción."""
    base = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=14,
        resources_per_pattern=4,
        enable_evolution=True,
        enable_compact_dna=True,
        enable_genetic_policy=True,
        enable_internal_state=True,
        enable_energy_transfer=True,
        enable_predation=True,
        metabolic_base_cost=0.0,
        memory_capacity_cost=0.0,
        sensory_radius_cost=0.0,
        move_cost=0.0,
        message_cost=0.0,
        dna_codon_cost=0.0,
        attack_cost=0.0,
        reproduction_threshold=100.0,
    )
    return replace(base, **overrides)


def grid_of(engine: SimulationEngine) -> ToroidalGrid2D:
    return cast(ToroidalGrid2D, engine.env)


def put(engine: SimulationEngine, aid: int, cell: tuple[int, int]) -> None:
    grid = grid_of(engine)
    old = grid._agent_cell[aid]  # pyright: ignore[reportPrivateUsage]
    grid.cell_agents[old].discard(aid)
    grid.cell_agents[cell].add(aid)
    grid._agent_cell[aid] = cell  # pyright: ignore[reportPrivateUsage]


def crowded_engine(config: SimulationConfig) -> SimulationEngine:
    engine = SimulationEngine(config)
    for aid in sorted(engine.agents):
        put(engine, aid, (5, 5))
    return engine


def set_energy(engine: SimulationEngine, aid: int, energy: float) -> None:
    agent = engine.agents[aid]
    agent.apply_energy_delta(energy - agent.energy)


def act(
    monkeypatch: pytest.MonkeyPatch,
    engine: SimulationEngine,
    actions: dict[int, AgentAction] | None = None,
) -> None:
    actions = actions or {}
    for aid, agent in engine.agents.items():
        action = actions.get(aid, IDLE)
        monkeypatch.setattr(agent, "decide_action", lambda *_args, a=action: a)


class FixedOrder(BaseSystem):
    name = "schedule"

    def __init__(self, order: list[int]) -> None:
        self.order = order

    def run(self, engine: SimulationEngine, frame: TickFrame) -> None:
        rest = [aid for aid in sorted(engine.agents) if aid not in self.order]
        frame.order = [*self.order, *rest]


def fix_order(engine: SimulationEngine, order: list[int]) -> None:
    engine.systems = tuple(
        FixedOrder(order) if isinstance(system, ScheduleSystem) else system
        for system in engine.systems
    )


def names(config: SimulationConfig) -> list[str]:
    return [system.name for system in build_systems(config)]


def test_sistema_de_estado_tras_la_decision_solo_con_r39() -> None:
    order = names(small())
    assert order.index("internal_state") == order.index(DECISION_SYSTEM) + 1
    assert order.index("internal_state") < order.index("execution")
    for config in (small(enable_internal_state=False), small(enable_genetic_policy=False)):
        assert "internal_state" not in names(config)


def test_sistema_de_eventos_al_final_solo_con_r32() -> None:
    for config in (small(), small(enable_internal_state=False)):
        assert names(config)[-1] == "events"
    no_policy = small(enable_genetic_policy=False, enable_internal_state=False)
    assert "events" not in names(no_policy)
    assert "events" not in names(SimulationConfig())
    base = PHASE2_PROTOCOL_CONFIGS["002a"]
    assert "events" not in names(replace(base, enable_compact_dna=True))


class Recorder:
    """Registra, por tick, la evaluación y el estado al decidir y el estado al final del tick."""

    def __init__(self, aid: int) -> None:
        self.aid = aid
        self.at_decision: list[tuple[BehaviorEvaluation | None, int]] = []
        self.at_end: list[int] = []

    def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
        agent = engine.agents[self.aid]
        self.at_decision.append((agent.last_evaluation, agent.internal_state))

    def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.at_end.append(engine.agents[self.aid].internal_state)


def test_estado_escrito_en_un_tick_y_leido_en_el_siguiente() -> None:
    engine = SimulationEngine(small())
    agent = engine.agents[2]
    agent.set_dna(
        CompactDNA(
            chromosome=(
                *FOUNDER_TRAITS,
                encode_codon(0x00, SET_STATE, 0, 0),
                encode_codon(0x30, WANDER, 0, 0, 64),
            )
        )
    )
    recorder = Recorder(2)
    engine.observers.append(recorder)
    engine.run(2)
    (first, state_1), (second, state_2) = recorder.at_decision
    assert first is not None and second is not None
    assert first.drives[3] == 0.0 and state_1 == 0
    assert recorder.at_end[0] == 1
    assert second.drives[3] == pytest.approx(0.5, abs=1e-9) and state_2 == 1


def test_el_agente_que_no_decide_conserva_su_estado(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(small())
    agent = engine.agents[2]
    agent.set_dna(CompactDNA(chromosome=(*FOUNDER_TRAITS, encode_codon(0x00, SET_STATE, 0, 4))))
    agent.evaluate_behavior(signals())  # evaluación de un tick anterior ya aplicada
    agent.commit_internal_state()
    set_state(agent, 0b1)
    monkeypatch.setattr(agent, "decide_action", lambda *_args: IDLE)
    engine.step()
    assert agent.internal_state == 0b1


def test_sin_r39_el_estado_queda_en_cero() -> None:
    config = small(enable_internal_state=False)
    engine = SimulationEngine(config)
    for agent in engine.agents.values():
        agent.set_dna(
            CompactDNA(
                chromosome=(
                    *FOUNDER_TRAITS,
                    encode_codon(0x00, SET_STATE, 0, 0),
                    encode_codon(0x00, SET_STATE, 0, 5),
                    *founder_dna(config).chromosome[9:],
                )
            )
        )
    engine.run(5)
    assert all(agent.internal_state == 0 for agent in engine.agents.values())
    assert all(
        agent.last_evaluation is None or agent.last_evaluation.set_mask == 0
        for agent in engine.agents.values()
    )


def interacting(
    monkeypatch: pytest.MonkeyPatch, engine: SimulationEngine, values: dict[int, float]
) -> None:
    """`INTERACT` de los agentes de `values` devuelve ese valor experimentado sobre un patrón."""
    grid = grid_of(engine)
    original = grid.execute_action
    pattern = Pattern((("id", "p_0"),))

    def execute(agent_id: int, action: AgentAction, tick: int) -> ActionResult:
        if action.action_type is ActionType.INTERACT and agent_id in values:
            return ActionResult(ActionType.INTERACT, pattern, values[agent_id])
        return original(agent_id, action, tick)

    monkeypatch.setattr(grid, "execute_action", execute)


def test_eventos_de_un_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    config = small(attack_power=0.3, energy_gain_scale=0.1, share_fraction=0.25)
    engine = crowded_engine(config)
    for aid, energy in ((5, 2.0), (4, 1.0), (1, 2.0), (6, 0.5), (3, 0.8)):
        set_energy(engine, aid, energy)
    act(
        monkeypatch,
        engine,
        {
            5: AgentAction(ActionType.ATTACK, 4),
            4: AgentAction(ActionType.INTERACT, 0),
            1: AgentAction(ActionType.SHARE, 6),
            3: AgentAction(ActionType.INTERACT, 0),
        },
    )
    interacting(monkeypatch, engine, {4: 1.0, 3: -1.0})
    engine.step()
    assert engine.agents[4].energy == pytest.approx(0.8, abs=1e-9)
    assert engine.agents[4].last_events == EventSignals(attacked=True, ate=True, lost_energy=True)
    assert engine.agents[6].last_events == EventSignals(received_energy=True)
    assert engine.agents[1].last_events == EventSignals(lost_energy=True)
    assert engine.agents[5].last_events == EventSignals()  # ganó energía al robar
    assert engine.agents[3].last_events == EventSignals(lost_energy=True)  # valor negativo
    assert engine.agents[7].last_events == EventSignals()


def test_ataque_sin_botin_no_es_un_evento() -> None:
    engine = crowded_engine(small())
    set_energy(engine, 5, 1.0)
    set_energy(engine, 6, 0.0)
    actions = {aid: IDLE for aid in engine.agents}
    actions[5] = AgentAction(ActionType.ATTACK, 6)
    frame = TickFrame(0, order=sorted(engine.agents), actions=actions)
    frame.start_energy = {aid: agent.energy for aid, agent in engine.agents.items()}
    ExecutionSystem().run(engine, frame)
    EventsSystem().run(engine, frame)
    assert frame.events["successful_attacks"] == 1
    assert engine.agents[6].last_events.attacked is False


def test_ataque_sin_botin_en_el_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = crowded_engine(small())
    set_energy(engine, 5, 1.0)
    set_energy(engine, 6, 0.0)
    victim = engine.agents[6]
    act(monkeypatch, engine, {5: AgentAction(ActionType.ATTACK, 6)})
    engine.step()
    assert 6 not in engine.agents  # murió de hambre: su energía era 0.0
    assert victim.last_events.attacked is False


def test_cesion_sin_efecto_no_es_un_evento(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = crowded_engine(small())
    set_energy(engine, 1, 2.0)
    engine.agents[6].set_endospore(True)
    act(monkeypatch, engine, {1: AgentAction(ActionType.SHARE, 6)})
    engine.step()
    assert engine.agents[6].last_events == EventSignals()
    assert engine.agents[1].last_events == EventSignals()


def test_compuesto_resuelto_con_exito_cuenta_como_comida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = small(num_composite_patterns=1, energy_gain_scale=0.1)
    engine = crowded_engine(config)
    rules = engine._composite_rules  # pyright: ignore[reportPrivateUsage]
    pattern = sorted(rules)[0]
    grid = grid_of(engine)
    original = grid.execute_action

    def execute(agent_id: int, action: AgentAction, tick: int) -> ActionResult:
        if action.action_type is ActionType.INTERACT and agent_id in (2, 3):
            return ActionResult(ActionType.INTERACT, pattern, 2.0)
        return original(agent_id, action, tick)

    monkeypatch.setattr(grid, "execute_action", execute)
    actions = {aid: IDLE for aid in engine.agents}
    actions[2] = actions[3] = AgentAction(ActionType.INTERACT, 0)
    frame = TickFrame(0, order=sorted(engine.agents), actions=actions)
    frame.start_energy = {aid: agent.energy for aid, agent in engine.agents.items()}
    frame.composite_contexts = {2: (True, [2], None), 3: (False, [3], None)}
    ExecutionSystem().run(engine, frame)
    EventsSystem().run(engine, frame)
    assert engine.agents[2].last_events.ate is True
    assert engine.agents[3].last_events.ate is False


def test_recien_nacido_arranca_sin_eventos() -> None:
    config = small(reproduction_threshold=1.2, initial_energy=1.0, energy_gain_scale=1.0)
    engine = SimulationEngine(config)
    for agent in engine.agents.values():
        agent.apply_energy_delta(1.0)  # todos superan el umbral y se reproducen en el tick 0
    before = set(engine.agents)
    engine.step()
    born = sorted(set(engine.agents) - before)
    assert born
    for aid in born:
        assert engine.agents[aid].last_events == EventSignals()
    # Los progenitores perdieron la energía que cedieron al hijo.
    assert any(engine.agents[aid].last_events.lost_energy for aid in sorted(before))


def test_instantanea_de_energias_al_empezar_el_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = crowded_engine(small())
    engine.agents[3].set_endospore(True)
    snapshots: list[dict[int, float]] = []

    class Spy:
        def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
            snapshots.append(dict(frame.start_energy))

        def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
            pass

    expected = {aid: agent.energy for aid, agent in engine.agents.items()}
    engine.observers.append(Spy())
    act(monkeypatch, engine)
    engine.step()
    assert snapshots == [expected]


def test_eventos_sin_r39_con_r32(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = crowded_engine(small(enable_internal_state=False, attack_power=0.3))
    set_energy(engine, 5, 2.0)
    set_energy(engine, 4, 1.0)
    act(monkeypatch, engine, {5: AgentAction(ActionType.ATTACK, 4)})
    engine.step()
    assert engine.agents[4].last_events == EventSignals(attacked=True, lost_energy=True)


def test_sin_r32_no_hay_eventos(monkeypatch: pytest.MonkeyPatch) -> None:
    config = small(enable_genetic_policy=False, enable_internal_state=False)
    engine = crowded_engine(config)
    for aid in sorted(engine.agents):
        set_energy(engine, aid, 1.0)
    engine.run(3)
    assert all(agent.last_events == EventSignals() for agent in engine.agents.values())


# --- (f) inercia y aceptación de D46.5 con la ampliación (D57.1, D58.7) ------------------------


def acceptance_history(protocol: str, genetic: bool, amplification: bool, ticks: int = 120) -> Any:
    config = replace(
        PHASE2_PROTOCOL_CONFIGS[protocol],
        enable_compact_dna=True,
        mutation_rate=0.0,
        discrete_mutation_prob=0.0,
        dna_codon_cost=0.0,
        enable_genetic_policy=genetic,
        enable_internal_state=amplification,
        enable_plasticity=amplification,
        enable_signals=amplification,
    )
    engine = SimulationEngine(config)
    engine.run(ticks)
    grid = grid_of(engine)
    ids = sorted(engine.agents)
    return (
        engine.history,
        [astuple(m) for m in engine.evolutionary_history],
        [grid.get_agent_position(a) for a in ids],
        [engine.agents[a].memory.all_units() for a in ids],
        [engine.agents[a].genome for a in ids],
        [engine.agents[a].internal_state for a in ids],
        [
            g.bit_generator.state
            for g in (engine.rng, engine.null_rng, engine.evo_rng, engine.donor_rng)
        ],
        engine.next_agent_id,
    )


@pytest.mark.parametrize("protocol", ["002a", "003a"])
def test_aceptacion_del_fundador_con_la_ampliacion(protocol: str) -> None:
    amplified = acceptance_history(protocol, True, True)
    handwritten = acceptance_history(protocol, False, False)
    assert len(amplified[0]) == 120
    assert amplified[7] > PHASE2_PROTOCOL_CONFIGS[protocol].num_agents  # hubo nacimientos
    assert amplified == handwritten


def test_ampliacion_sin_consumo_con_el_adn_fundador() -> None:
    assert acceptance_history("002a", True, True) == acceptance_history("002a", True, False)


# --- Determinismo entre procesos ---------------------------------------------------------------


def test_historiales_iguales_con_distinto_pythonhashseed() -> None:
    script = textwrap.dedent(
        """
        from dataclasses import astuple, replace
        from ide.agent.dna import encode_codon
        from ide.domain.types import CompactDNA
        from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
        from ide.simulation.engine import SimulationEngine

        config = replace(
            PHASE2_PROTOCOL_CONFIGS["002a"],
            enable_compact_dna=True,
            enable_genetic_policy=True,
            enable_internal_state=True,
            enable_energy_transfer=True,
            enable_predation=True,
            mutation_rate=0.2,
        )
        engine = SimulationEngine(config)
        extra = (
            encode_codon(0x2A, 0x0D, 0, 0),
            encode_codon(0x29, 0x0E, 0, 0),
            encode_codon(0x28, 0x0D, 0, 3),
            encode_codon(0x30, 0x46, 0, 0, 90),
            encode_codon(0x33, 0x45, 0, 0, 120),
            encode_codon(0x2B, 0x44, 0, 0, 100),
        )
        for aid in sorted(engine.agents):
            agent = engine.agents[aid]
            agent.set_dna(CompactDNA(chromosome=agent.dna.chromosome + extra))
        engine.run(60)
        print([astuple(m) for m in engine.history])
        print([astuple(m) for m in engine.evolutionary_history])
        agents = engine.agents.items()
        print(sorted((a, g.internal_state, astuple(g.last_events)) for a, g in agents))
        print(engine.rng.bit_generator.state, engine.evo_rng.bit_generator.state)
        print(sum(1 for a in engine.agents.values() if a.internal_state))
        print(sum(1 for a in engine.agents.values() if a.last_events != type(a.last_events)()))
        """
    )
    outputs = []
    for hash_seed in ("0", "123"):
        path = os.pathsep.join(
            filter(None, [str(ROOT / "src"), str(ROOT), os.environ.get("PYTHONPATH")])
        )
        env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": path}
        done = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            check=True,
            cwd=ROOT,
        )
        outputs.append(done.stdout)
    assert outputs[0] == outputs[1]
    # La corrida usa el estado y los eventos de verdad: no es una igualdad trivial.
    with_state, with_events = (int(line) for line in outputs[0].splitlines()[-2:])
    assert with_state > 0 and with_events > 0


def test_behavior_targets_en_el_orden_de_behavior() -> None:
    assert len(BEHAVIOR_TARGETS) == len(Behavior)
