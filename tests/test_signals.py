"""Tests de las señales evolucionables (bloque 15, R41).

Cubren la emisión por mayoría por símbolo con el destino `SIGNAL` (`0x48`), su costo en el
metabolismo y que `SIGNAL` no ocupa la acción (D60.2, D60.3); la percepción en la Fase 1 del tick
siguiente por los vecinos de comunicación del emisor en el tick de emisión, sin endosporas
(D60.4, precisiones 64 y 65); los promotores `HEARD_k` (`0x38`-`0x3F`) sólo en la evaluación de
conducta; el control nulo con `null_rng` en orden de `agent_id` (D60.5); que las señales no pasan
por `protocol.py` ni por la memoria (D60.6), y la inercia sin $R_{41}$ (D60.7), además del
determinismo entre procesos con distinto `PYTHONHASHSEED` con un ADN que emite y percibe.
"""

import ast
import dataclasses
import inspect
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
    founder_dna,
    heard_symbols,
    signals_active,
    transcribe_phenotype,
)
from ide.agent.micro_agent import MicroAgent
from ide.agent.policy import GeneticPolicy
from ide.config import SimulationConfig
from ide.domain.types import (
    ActionType,
    AgentAction,
    CompactDNA,
    EpigeneticContext,
    Observation,
    SensorySignals,
)
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
from ide.simulation.engine import SimulationEngine
from ide.simulation.pipeline import (
    DECISION_SYSTEM,
    BaseSystem,
    DecisionSystem,
    GerminationSystem,
    MetabolismSystem,
    SignalEmissionSystem,
    SignalPerceptionSystem,
    TickFrame,
    build_systems,
)

ROOT = Path(__file__).resolve().parents[1]
CONSUME, EXPLORE, NAVIGATE, WANDER, SHARE, ATTACK, FLEE, SPORULATE = BEHAVIOR_TARGETS
SIGNAL = 0x48
FOUNDER_TRAITS = tuple(encode_codon(0x00, t) for t in range(9))
IDLE = AgentAction(ActionType.IDLE)
CTX0 = EpigeneticContext()
SIGNAL_FIELDS = tuple(f.name for f in dataclasses.fields(SensorySignals))


def config_with(**overrides: Any) -> SimulationConfig:
    """Configuración con $R_{32}$ y $R_{41}$ efectivamente activas, salvo que se indique."""
    params: dict[str, Any] = {
        "enable_evolution": True,
        "enable_compact_dna": True,
        "enable_genetic_policy": True,
        "enable_signals": True,
    }
    params.update(overrides)
    return SimulationConfig(**params)


R41 = config_with()
NO_R41 = config_with(enable_signals=False)
NO_R32 = config_with(enable_genetic_policy=False)


def signals(**true_fields: bool) -> SensorySignals:
    values = {name: False for name in SIGNAL_FIELDS}
    values.update(true_fields)
    return SensorySignals(**values)


def all_signals(value: bool) -> SensorySignals:
    return SensorySignals(**{name: value for name in SIGNAL_FIELDS})


def behave(
    *codons: int,
    config: SimulationConfig = R41,
    sig: SensorySignals | None = None,
    perceived: int = 0,
    state: int = 0,
) -> Any:
    return evaluate_behavior(
        CompactDNA(chromosome=tuple(codons)),
        CTX0,
        sig or signals(),
        config,
        state=state,
        perceived=perceived,
    )


def emit(symbol: int, mode: int = 0, promoter: int = 0x00) -> int:
    return encode_codon(promoter, SIGNAL, mode, symbol, 0)


# --- (a) emisión por mayoría por símbolo (D60.2, D60.3) ----------------------------------------


def test_emision_condicionada_por_un_sensor() -> None:
    codon = encode_codon(0x22, SIGNAL, 0, 3)
    on = behave(codon, sig=signals(no_resource=True))
    off = behave(codon, sig=signals(no_resource=False))
    assert on.emitted == 0b1000 and off.emitted == 0
    assert len(on.drives) == len(off.drives) == 8


def test_sin_emision_con_r41_apagada() -> None:
    codon = encode_codon(0x22, SIGNAL, 0, 3)
    assert behave(codon, config=NO_R41, sig=signals(no_resource=True)).emitted == 0
    assert behave(codon, config=NO_R32, sig=signals(no_resource=True)).emitted == 0


def test_mayoria_por_simbolo() -> None:
    evaluation = behave(
        emit(2),
        emit(10, mode=2),  # canal 10: símbolo 2
        emit(2, mode=1),
        emit(5),
        emit(5, mode=1),  # empate en el símbolo 5
        emit(4, mode=3),  # el modo 3 no cuenta
        emit(7, mode=2),
    )
    assert evaluation.emitted == 0b10000100


def test_signal_no_es_una_conducta() -> None:
    evaluation = behave(emit(0), emit(1), sig=all_signals(True))
    assert evaluation.drives == (0.0,) * 8
    assert evaluation.emitted == 0b11


def test_payload_ignorado_en_signal() -> None:
    a = behave(encode_codon(0x00, SIGNAL, 0, 6, 127))
    b = behave(encode_codon(0x00, SIGNAL, 0, 6, -128))
    assert a.emitted == b.emitted == 0b1000000


def test_signals_active_es_r32_mas_la_bandera() -> None:
    assert signals_active(R41)
    assert not signals_active(NO_R41)
    assert not signals_active(NO_R32)
    assert not signals_active(SimulationConfig(enable_signals=True))


def test_destino_signal_inerte_en_el_fenotipo() -> None:
    founder = founder_dna(NO_R32)
    reference = transcribe_phenotype(founder, CTX0, R41)
    for mode in range(4):
        dna = CompactDNA(chromosome=(*founder.chromosome, encode_codon(0, SIGNAL, mode, 3, 127)))
        assert transcribe_phenotype(dna, CTX0, R41) == reference


@given(
    st.lists(
        st.tuples(st.integers(0, 63), st.sampled_from([0, 1, 2, 3])),
        min_size=1,
        max_size=12,
    )
)
def test_emision_por_propiedades(specs: list[tuple[int, int]]) -> None:
    """El bit k vale 1 si y sólo si los modos 0 y 2 superan a los de modo 1 sobre k."""
    evaluation = behave(*(emit(channel, mode) for channel, mode in specs))
    for k in range(8):
        act = sum(1 for c, m in specs if c & 0x07 == k and m in (0, 2))
        rep = sum(1 for c, m in specs if c & 0x07 == k and m == 1)
        assert bool(evaluation.emitted >> k & 1) == (act > rep)
    assert 0 <= evaluation.emitted <= 0xFF


# --- (c) promotores HEARD_k sólo en la evaluación de conducta ----------------------------------


def test_simbolo_percibido() -> None:
    codon = encode_codon(0x3A, CONSUME, 0, 0, 64)
    assert behave(codon, perceived=0b100).drives[0] == pytest.approx(0.5, abs=1e-9)
    assert behave(codon, perceived=0b011).drives[0] == 0.0
    assert behave(codon, config=NO_R41, perceived=0xFF).drives[0] == 0.0


@pytest.mark.parametrize("bit", range(8))
def test_cada_promotor_de_senal_percibida(bit: int) -> None:
    codon = encode_codon(0x38 + bit, WANDER, 0, 0, 64)
    assert behave(codon, perceived=1 << bit).drives[3] == pytest.approx(0.5, abs=1e-9)
    assert behave(codon, perceived=0xFF & ~(1 << bit)).drives[3] == 0.0


def test_promotores_de_senal_independientes_del_estado() -> None:
    """`HEARD_k` lee `perceived`, no `state`, también con R39 activa."""
    config = config_with(enable_internal_state=True)
    codon = encode_codon(0x38, WANDER, 0, 0, 64)
    assert behave(codon, config=config, state=0xFF, perceived=0).drives[3] == 0.0
    assert behave(codon, config=config, state=0, perceived=1).drives[3] == pytest.approx(0.5)


def test_senal_percibida_puede_disparar_una_emision() -> None:
    assert behave(encode_codon(0x39, SIGNAL, 0, 4), perceived=0b10).emitted == 0b10000
    assert behave(encode_codon(0x39, SIGNAL, 0, 4), perceived=0b01).emitted == 0


@pytest.mark.parametrize("promoter", range(0x38, 0x40))
def test_promotores_de_senal_inactivos_en_el_fenotipo(promoter: int) -> None:
    founder = founder_dna(NO_R32)
    dna = CompactDNA(chromosome=(*founder.chromosome, encode_codon(promoter, 0, 0, 0, 127)))
    assert transcribe_phenotype(dna, CTX0, R41) == transcribe_phenotype(founder, CTX0, R41)


def test_el_fundador_no_emite_ni_escucha() -> None:
    evaluation = evaluate_behavior(founder_dna(R41), CTX0, all_signals(True), R41, perceived=0xFF)
    assert evaluation.emitted == 0
    assert evaluation.drives == pytest.approx((0.9921875, 0.75, 0.5, 0.25, 0.0, 0.0, 0.0, 0.0))


# --- Agente: máscara percibida (precisión 65) ---------------------------------------------------


def agent_with(*codons: int, config: SimulationConfig = R41) -> MicroAgent:
    agent = MicroAgent(1, config, policy=GeneticPolicy())
    agent.set_dna(CompactDNA(chromosome=FOUNDER_TRAITS + codons))
    return agent


def observation() -> Observation:
    return Observation(1, 0, (), ((0, 1), (1, 0)), ())


def test_mascara_percibida_al_nacer_y_no_heredada() -> None:
    parent = agent_with()
    assert parent.perceived_symbols == 0
    parent.set_perceived_symbols(0b101)
    parent.apply_energy_delta(3.0)
    child = parent.create_offspring(9, 4, np.random.Generator(np.random.PCG64(0)))
    assert child.perceived_symbols == 0
    assert parent.perceived_symbols == 0b101


@pytest.mark.parametrize("mask", [-1, 256])
def test_mascara_percibida_fuera_de_rango(mask: int) -> None:
    with pytest.raises(ValueError, match="perceived_symbols"):
        agent_with().set_perceived_symbols(mask)


def test_la_politica_decide_con_la_mascara_percibida() -> None:
    agent = agent_with(encode_codon(0x3B, WANDER, 0, 0, 64))
    g = np.random.Generator(np.random.PCG64(3))
    assert agent.decide_action(observation(), 0, g) == IDLE
    agent.set_perceived_symbols(0b1000)
    assert agent.decide_action(observation(), 1, g).action_type is ActionType.MOVE


def test_la_decision_registra_lo_emitido() -> None:
    agent = agent_with(emit(1), emit(4))
    g = np.random.Generator(np.random.PCG64(3))
    agent.decide_action(observation(), 0, g)
    decision = agent.decision_evaluation(0)
    assert decision is not None and decision.emitted == 0b10010


@given(
    st.lists(
        st.tuples(
            st.sampled_from([all_signals(False), signals(no_resource=True), all_signals(True)]),
            st.integers(0, 255),
            st.integers(0, 255),
            st.booleans(),
        ),
        max_size=12,
    )
)
def test_cache_de_la_evaluacion_igual_a_la_directa(steps: list[tuple[Any, ...]]) -> None:
    config = config_with(enable_internal_state=True)
    first = (
        encode_codon(0x38, WANDER, 0, 0, 64),
        encode_codon(0x3C, SIGNAL, 0, 2),
        encode_codon(0x22, SIGNAL, 0, 5),
        encode_codon(0x31, CONSUME, 0, 0, 40),
    )
    second = (encode_codon(0x3F, FLEE, 0, 0, 64), encode_codon(0x39, SIGNAL, 2, 1))
    agent = agent_with(*first, config=config)
    for tick, (sig, perceived, state, swap) in enumerate(steps):
        if swap:
            agent.set_dna(CompactDNA(chromosome=FOUNDER_TRAITS + second))
        agent.set_perceived_symbols(perceived)
        agent._internal_state = state  # pyright: ignore[reportPrivateUsage]
        assert agent.dna is not None
        expected = evaluate_behavior(
            agent.dna, agent.last_context, sig, config, state=state, perceived=perceived
        )
        assert agent.evaluate_behavior(sig) == expected
        assert agent.evaluate_for_decision(sig, tick) == expected


def test_heard_symbols() -> None:
    dna = CompactDNA(
        chromosome=(
            *FOUNDER_TRAITS,
            encode_codon(0x38, WANDER, 0, 0, 64),
            encode_codon(0x3D, SIGNAL, 0, 1),
            encode_codon(0x22, SIGNAL, 0, 2),
        ),
        plasmids=(encode_codon(0x3F, CONSUME, 0, 0, 9),),
    )
    assert heard_symbols(dna) == 0b10100001
    assert heard_symbols(founder_dna(R41)) == 0


def test_la_clave_del_cache_acota_la_mascara_a_lo_que_el_adn_oye() -> None:
    """Máscaras que difieren sólo en símbolos que el ADN no oye comparten la entrada del caché."""
    agent = agent_with(encode_codon(0x39, WANDER, 0, 0, 64))
    cache = agent._evaluation_cache  # pyright: ignore[reportPrivateUsage]
    sig = signals()
    agent.set_perceived_symbols(0b10)
    heard = agent.evaluate_behavior(sig)
    for mask in (0b11, 0b11111110, 0b10000010):
        agent.set_perceived_symbols(mask)
        assert agent.evaluate_behavior(sig) == heard
    assert len(cache) == 1
    agent.set_perceived_symbols(0b11111101)
    silent = agent.evaluate_behavior(sig)
    assert silent.drives[3] == 0.0 and heard.drives[3] == pytest.approx(0.5)
    assert len(cache) == 2
    agent.set_dna(CompactDNA(chromosome=(*FOUNDER_TRAITS, encode_codon(0x3A, WANDER, 0, 0, 64))))
    agent.set_perceived_symbols(0b100)
    assert agent.evaluate_behavior(sig).drives[3] == pytest.approx(0.5)  # recalcula lo que oye


def test_lo_que_oye_un_hijo_sale_de_su_adn() -> None:
    parent = agent_with(encode_codon(0x39, WANDER, 0, 0, 64))
    parent.apply_energy_delta(3.0)
    child = parent.create_offspring(9, 4, np.random.Generator(np.random.PCG64(0)))
    assert child.dna is not None
    child.set_perceived_symbols(0xFF)
    expected = evaluate_behavior(child.dna, child.last_context, signals(), R41, perceived=0xFF)
    assert child.evaluate_behavior(signals()) == expected


# --- Motor: escenas -----------------------------------------------------------------------------


def small(**overrides: Any) -> SimulationConfig:
    """Configuración chica con $R_{32}$ y $R_{41}$, sin costos salvo el de las señales."""
    base = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=14,
        resources_per_pattern=4,
        enable_evolution=True,
        enable_compact_dna=True,
        enable_genetic_policy=True,
        enable_signals=True,
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


CORNERS = [(0, 0), (0, 9), (9, 0), (9, 9), (0, 5), (9, 5), (5, 0), (5, 9)]


def scene(
    monkeypatch: pytest.MonkeyPatch,
    config: SimulationConfig,
    dnas: dict[int, tuple[int, ...]],
    group: tuple[int, ...],
) -> SimulationEngine:
    """Motor con `group` en la celda (5, 5) y los demás lejos.

    Los agentes de `dnas` deciden con la política genética y el ADN fundador de rasgos más sus
    codones; los demás hacen `IDLE` sin evaluar su ADN.
    """
    engine = SimulationEngine(config)
    others = [aid for aid in sorted(engine.agents) if aid not in group]
    for aid, cell in zip(others, CORNERS * 2, strict=False):
        put(engine, aid, cell)
    for aid in group:
        put(engine, aid, (5, 5))
    for aid, codons in dnas.items():
        engine.agents[aid].set_dna(CompactDNA(chromosome=FOUNDER_TRAITS + codons))
    for aid, agent in engine.agents.items():
        if aid not in dnas:
            monkeypatch.setattr(agent, "decide_action", lambda *_args: IDLE)
    return engine


class Recorder:
    """Registra, por tick, la máscara percibida al decidir y los eventos y señales del tick."""

    def __init__(self) -> None:
        self.perceived: list[dict[int, int]] = []
        self.signals: list[dict[int, int]] = []
        self.events: list[dict[str, int]] = []

    def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.perceived.append({a: g.perceived_symbols for a, g in sorted(engine.agents.items())})
        self.signals.append(dict(frame.signals))

    def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.events.append(dict(frame.events))


def record(engine: SimulationEngine) -> Recorder:
    recorder = Recorder()
    engine.observers.append(recorder)
    return recorder


def test_costo_de_dos_simbolos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Emite los símbolos 1 y 4 y ejecuta `MOVE`: paga `0.004` más que uno igual que no emite."""
    walk = encode_codon(0x00, WANDER, 0, 0, 64)
    engine = scene(monkeypatch, small(), {5: (walk, emit(1), emit(4)), 6: (walk,)}, group=(5,))
    put(engine, 6, (2, 2))
    recorder = record(engine)
    start = {aid: engine.agents[aid].energy for aid in (5, 6)}
    engine.step()
    emitter, silent = engine.agents[5], engine.agents[6]
    assert emitter.decision_behavior(0) is not None
    assert recorder.signals[0] == {5: 0b10010}
    assert recorder.events[0]["signals_emitted"] == 2
    lost_emitter = start[5] - emitter.energy
    lost_silent = start[6] - silent.energy
    assert lost_emitter - lost_silent == pytest.approx(0.004, abs=1e-9)


def test_signal_no_ocupa_la_accion(monkeypatch: pytest.MonkeyPatch) -> None:
    walk = encode_codon(0x00, WANDER, 0, 0, 64)
    engine = scene(monkeypatch, small(), {5: (walk, emit(1), emit(4))}, group=(5,))
    actions: list[AgentAction] = []

    class Spy:
        def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
            actions.append(frame.actions[5])

        def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
            pass

    engine.observers.append(Spy())
    engine.step()
    assert actions[0].action_type is ActionType.MOVE


class KeepDormant(BaseSystem):
    """Sustituye a la germinación: ninguna endospora germina y `frame.dormant` es la de D38."""

    name = "germination"

    def run(self, engine: SimulationEngine, frame: TickFrame) -> None:
        agents = engine.agents
        frame.dormant = frozenset(aid for aid in frame.order if agents[aid].is_endospore)


def keep_dormant(engine: SimulationEngine) -> None:
    engine.systems = tuple(
        KeepDormant() if isinstance(system, GerminationSystem) else system
        for system in engine.systems
    )


def test_la_endospora_dormida_no_emite(monkeypatch: pytest.MonkeyPatch) -> None:
    config = small(enable_sporulation=True)
    engine = scene(monkeypatch, config, {5: (emit(1),), 6: (emit(2),)}, group=(5, 6))
    keep_dormant(engine)
    engine.agents[5].set_endospore(True)
    recorder = record(engine)
    engine.step()
    assert engine.agents[5].decision_evaluation(0) is None
    assert recorder.signals[0] == {6: 0b100}
    assert recorder.events[0]["signals_emitted"] == 1
    assert engine.pending_signals.get(6, 0) == 0  # el 6 no oye nada de la endospora 5


def test_metabolismo_cobra_por_simbolo() -> None:
    engine = SimulationEngine(small(signal_cost=0.01))
    before = {aid: agent.energy for aid, agent in engine.agents.items()}
    frame = TickFrame(0, order=sorted(engine.agents), signals={3: 0b1011, 4: 0b1})
    MetabolismSystem().run(engine, frame)
    lost = {aid: before[aid] - agent.energy for aid, agent in engine.agents.items()}
    base = lost[0]
    assert lost[3] - base == pytest.approx(0.03, abs=1e-9)
    assert lost[4] - base == pytest.approx(0.01, abs=1e-9)


# --- (b) percepción en el tick siguiente (D60.4) -----------------------------------------------


def test_recepcion_en_el_tick_siguiente(monkeypatch: pytest.MonkeyPatch) -> None:
    """El 2 emite el 3 en el tick 0; el 7 muere y el 9 se acerca después de la observación."""
    engine = scene(monkeypatch, small(), {2: (emit(3),)}, group=(2, 5, 7))
    recorder = record(engine)
    engine.step()  # tick 0: emite
    assert all(mask == 0 for mask in recorder.perceived[0].values())  # nadie en el mismo tick
    engine._remove([7])  # pyright: ignore[reportPrivateUsage]
    put(engine, 9, (5, 5))  # se acerca después de la observación del tick 0
    engine.step()  # tick 1: perciben los vecinos de comunicación del tick 0
    perceived = recorder.perceived[1]
    assert perceived[5] & 0b1000
    assert 7 not in perceived
    assert perceived[9] == 0
    assert perceived[2] == 0  # el emisor no se oye a sí mismo


def test_or_de_varios_emisores(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = scene(monkeypatch, small(), {2: (emit(0),), 3: (emit(0), emit(6))}, group=(2, 3, 5))
    recorder = record(engine)
    engine.run(2)
    assert recorder.perceived[1][5] == 0b1000001
    assert recorder.perceived[1][2] == 0b1000001  # el 2 oye al 3
    assert recorder.perceived[1][3] == 0b1  # el 3 oye al 2


def test_la_endospora_dormida_no_percibe(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = scene(monkeypatch, small(enable_sporulation=True), {2: (emit(3),)}, group=(2, 5, 6))
    keep_dormant(engine)
    recorder = record(engine)
    engine.step()
    engine.agents[6].set_endospore(True)
    engine.step()
    assert recorder.perceived[1][5] == 0b1000
    assert recorder.perceived[1][6] == 0


def test_el_emisor_que_muere_igual_es_percibido(monkeypatch: pytest.MonkeyPatch) -> None:
    """Precisión 97: el emisor muere en la Fase 5 del tick t (por el costo de su señal) y su
    símbolo se percibe en t + 1; D60.4 sólo exige que el receptor siga vivo y activo."""
    engine = scene(monkeypatch, small(signal_cost=0.01), {2: (emit(3),)}, group=(2, 5))
    engine.agents[2].apply_energy_delta(0.005 - engine.agents[2].energy)
    recorder = record(engine)
    engine.step()
    assert 2 not in engine.agents  # murió en la Fase 5 del tick 0
    engine.step()
    assert recorder.perceived[1][5] == 0b1000


def test_las_senales_no_dependen_de_comm_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Precisión 104: canal sensorial independiente de `comm_enabled`; su ablación es R41."""
    engine = scene(monkeypatch, small(comm_enabled=False), {2: (emit(3),)}, group=(2, 5))
    assert "signal_perception" in names(engine.config)
    assert "signal_emission" in names(engine.config)
    recorder = record(engine)
    start = engine.agents[2].energy
    engine.run(2)
    assert recorder.perceived[1][5] == 0b1000
    assert recorder.signals[0] == {2: 0b1000}
    assert start - engine.agents[2].energy == pytest.approx(2 * 0.002, abs=1e-9)


def test_solo_se_ponen_en_cero_los_receptores_anteriores() -> None:
    """La percepción no recorre a toda la población: sólo toca a los receptores."""
    engine = SimulationEngine(small())
    touched: list[int] = []
    for aid, agent in engine.agents.items():
        original = agent.set_perceived_symbols

        def spy(mask: int, aid: int = aid, original: Any = original) -> None:
            touched.append(aid)
            original(mask)

        object.__setattr__(agent, "set_perceived_symbols", spy)
    engine.pending_signals = {7: 0b1, 3: 0b10, 5: 0}
    SignalPerceptionSystem().run(engine, TickFrame(1))
    assert touched == [3, 7]
    assert engine.signal_receivers == (3, 7)
    touched.clear()
    engine.pending_signals = {4: 0b100}
    SignalPerceptionSystem().run(engine, TickFrame(2))
    assert touched == [3, 7, 4]
    assert [engine.agents[a].perceived_symbols for a in (3, 4, 7)] == [0, 0b100, 0]
    assert engine.signal_receivers == (4,)


def test_la_mascara_se_recalcula_en_cada_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin emisión en el tick anterior, la máscara vuelve a 0."""
    engine = scene(monkeypatch, small(), {2: (emit(3),)}, group=(2, 5))
    recorder = record(engine)
    engine.step()
    monkeypatch.setattr(engine.agents[2], "decide_action", lambda *_args: IDLE)
    engine.run(2)
    assert [tick[5] for tick in recorder.perceived] == [0, 0b1000, 0]


def test_vecinos_de_comunicacion_del_emisor() -> None:
    """La percepción usa los `neighbor_ids` de la observación del emisor en el tick de emisión."""
    engine = SimulationEngine(small())
    engine.pending_signals = {}
    frame = TickFrame(4, order=[1, 2])
    frame.observations = {
        1: Observation(1, 4, (), (), (3, 4)),
        2: Observation(2, 4, (), (), (4,)),
    }
    for aid in (1, 2):
        engine.agents[aid].set_dna(CompactDNA(chromosome=(*FOUNDER_TRAITS, emit(aid))))
        engine.agents[aid].evaluate_for_decision(signals(), 4)
    frame.actions = {1: IDLE, 2: IDLE}
    SignalEmissionSystem().run(engine, frame)
    assert frame.signals == {1: 0b10, 2: 0b100}
    assert engine.pending_signals == {3: 0b10, 4: 0b110}
    perception = TickFrame(5)
    SignalPerceptionSystem().run(engine, perception)
    assert engine.agents[3].perceived_symbols == 0b10
    assert engine.agents[4].perceived_symbols == 0b110
    assert engine.agents[1].perceived_symbols == 0
    assert engine.pending_signals == {}


# --- (d) control nulo con null_rng (D60.5) -----------------------------------------------------


def test_secuencia_del_control_nulo() -> None:
    engine = SimulationEngine(small(comm_content_null=True))
    engine.pending_signals = {8: 0b1, 3: 0b100, 5: 0}
    twin = np.random.Generator(np.random.PCG64(0))
    twin.bit_generator.state = engine.null_rng.bit_generator.state
    SignalPerceptionSystem().run(engine, TickFrame(1))
    first, second = int(twin.integers(1, 256)), int(twin.integers(1, 256))
    assert engine.agents[3].perceived_symbols == first
    assert engine.agents[8].perceived_symbols == second
    assert engine.agents[5].perceived_symbols == 0
    assert engine.null_rng.bit_generator.state == twin.bit_generator.state


def test_control_nulo_sin_mascaras_no_consume() -> None:
    engine = SimulationEngine(small(comm_content_null=True))
    state = engine.null_rng.bit_generator.state
    engine.pending_signals = {5: 0}
    SignalPerceptionSystem().run(engine, TickFrame(1))
    assert engine.null_rng.bit_generator.state == state


def test_sin_control_nulo_no_consume_null_rng() -> None:
    engine = SimulationEngine(small())
    state = engine.null_rng.bit_generator.state
    engine.pending_signals = {3: 0b100}
    SignalPerceptionSystem().run(engine, TickFrame(1))
    assert engine.agents[3].perceived_symbols == 0b100
    assert engine.null_rng.bit_generator.state == state


def test_control_nulo_omite_receptores_muertos_o_endosporas() -> None:
    engine = SimulationEngine(small(comm_content_null=True))
    engine.pending_signals = {4: 0b1, 99: 0b1, 6: 0b10}
    twin = np.random.Generator(np.random.PCG64(0))
    twin.bit_generator.state = engine.null_rng.bit_generator.state
    SignalPerceptionSystem().run(engine, TickFrame(1, dormant=frozenset({4})))
    assert engine.agents[6].perceived_symbols == int(twin.integers(1, 256))
    assert engine.agents[4].perceived_symbols == 0
    assert engine.null_rng.bit_generator.state == twin.bit_generator.state


def test_generadores_con_la_ampliacion_activa() -> None:
    engine = SimulationEngine(small(enable_internal_state=True, enable_plasticity=True))
    generators = {
        name for name, value in vars(engine).items() if isinstance(value, np.random.Generator)
    }
    assert {"rng", "null_rng", "evo_rng", "donor_rng"} <= generators
    assert generators <= {"rng", "null_rng", "evo_rng", "donor_rng", "hgt_rng"}


# --- (e) fuera del protocolo y de la memoria (D60.6) -------------------------------------------


def test_memoria_intacta_con_senales(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(small())
    agent = engine.agents[5]
    before = agent.memory.all_units()
    engine.pending_signals = {5: 0b1011}
    SignalPerceptionSystem().run(engine, TickFrame(1))
    assert agent.perceived_symbols == 0b1011
    assert agent.memory.all_units() == before


def _referenced_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            names.add(sub.attr)
    return names


FORBIDDEN = {
    "Message",
    "MessageType",
    "assimilate_testimony",
    "memory",
    "_memory",
    "protocol",
    "_protocol",
    "perceive_and_emit_messages",
    "process_incoming_messages",
    "inject_ephemeral_belief",
    "learn_from_experience",
}


@pytest.mark.parametrize("system", [SignalEmissionSystem, SignalPerceptionSystem])
def test_los_sistemas_de_senales_no_tocan_mensajes_ni_memoria(system: type) -> None:
    tree = ast.parse(textwrap.dedent(inspect.getsource(system)))
    assert not _referenced_names(tree) & FORBIDDEN


def test_set_perceived_symbols_no_toca_la_memoria() -> None:
    source = textwrap.dedent(inspect.getsource(MicroAgent.set_perceived_symbols))
    assert not _referenced_names(ast.parse(source)) & FORBIDDEN


def test_el_protocolo_no_conoce_las_senales() -> None:
    tree = ast.parse((ROOT / "src/ide/agent/protocol.py").read_text(encoding="utf-8"))
    names = _referenced_names(tree)
    assert not names & {"perceived_symbols", "set_perceived_symbols", "emitted", "signals_active"}


def test_ningun_mensaje_transporta_la_senal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Los mensajes del tick son los mismos con y sin $R_{41}$: la señal no viaja en `Message`."""

    def messages(config: SimulationConfig) -> tuple[list[list[Any]], Recorder]:
        engine = scene(monkeypatch, config, {2: (emit(3),)}, group=(2, 5))
        recorder = record(engine)
        sent: list[list[Any]] = []

        class Spy:
            def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
                sent.append([*frame.emitted, *frame.responses])

            def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
                pass

        engine.observers.append(Spy())
        engine.run(2)
        return sent, recorder

    with_signals, recorder = messages(small())
    without, _ = messages(small(enable_signals=False))
    assert recorder.perceived[1][5] == 0b1000
    assert with_signals == without
    assert any(with_signals)  # hubo mensajes: la comparación no es trivial


# --- (f) inercia sin R41 y orden de los sistemas (D60.7, D53.1) --------------------------------


def names(config: SimulationConfig) -> list[str]:
    return [system.name for system in build_systems(config)]


def test_sistemas_de_senales_en_su_lugar() -> None:
    order = names(small(enable_internal_state=True))
    assert order.index("signal_perception") == order.index("social_perception") + 1
    assert order.index("signal_perception") < order.index("emission")
    assert order.index("signal_emission") == order.index(DECISION_SYSTEM) + 1
    assert order.index("internal_state") == order.index("signal_emission") + 1


def test_la_marca_pasa_a_la_emision_de_senales() -> None:
    marked = [s for s in build_systems(small()) if s.notifies_decisions]
    assert len(marked) == 1 and isinstance(marked[0], SignalEmissionSystem)
    decision = next(s for s in build_systems(small()) if isinstance(s, DecisionSystem))
    assert not decision.notifies_decisions
    without = [s for s in build_systems(small(enable_signals=False)) if s.notifies_decisions]
    assert len(without) == 1 and isinstance(without[0], DecisionSystem)


def test_sin_r41_no_hay_sistemas_de_senales() -> None:
    for config in (small(enable_signals=False), small(enable_genetic_policy=False)):
        assert "signal_perception" not in names(config)
        assert "signal_emission" not in names(config)
    assert names(small(enable_signals=False)) == [
        n for n in names(small()) if n not in ("signal_perception", "signal_emission")
    ]


def test_on_decisions_ve_las_senales_del_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = scene(monkeypatch, small(), {2: (emit(3),)}, group=(2,))
    recorder = record(engine)
    engine.step()
    assert recorder.signals[0] == {2: 0b1000}


def test_sin_r41_nada_cambia(monkeypatch: pytest.MonkeyPatch) -> None:
    config = small(enable_signals=False)
    engine = scene(
        monkeypatch, config, {2: (emit(3), encode_codon(0x3B, WANDER, 0, 0, 64))}, group=(2, 5)
    )
    recorder = record(engine)
    start = engine.agents[2].energy
    engine.run(3)
    assert all(mask == 0 for tick in recorder.perceived for mask in tick.values())
    assert all("signals_emitted" not in events for events in recorder.events)
    assert engine.agents[2].energy == start
    decision = engine.agents[2].decision_evaluation(2)
    assert decision is not None and decision.emitted == 0
    assert not hasattr(engine, "pending_signals") or engine.pending_signals == {}


def test_frame_signals_vacio_por_defecto() -> None:
    assert TickFrame(0).signals == {}


def acceptance_history(signals_on: bool, genetic: bool, null: bool = False) -> Any:
    config = replace(
        PHASE2_PROTOCOL_CONFIGS["002a"],
        enable_compact_dna=True,
        mutation_rate=0.0,
        discrete_mutation_prob=0.0,
        dna_codon_cost=0.0,
        enable_genetic_policy=genetic,
        enable_signals=signals_on,
        comm_content_null=null,
    )
    engine = SimulationEngine(config)
    engine.run(80)
    ids = sorted(engine.agents)
    return (
        engine.history,
        [astuple(m) for m in engine.evolutionary_history],
        [grid_of(engine).get_agent_position(a) for a in ids],
        [engine.agents[a].memory.all_units() for a in ids],
        [
            g.bit_generator.state
            for g in (engine.rng, engine.null_rng, engine.evo_rng, engine.donor_rng)
        ],
        engine.next_agent_id,
    )


def test_aceptacion_del_fundador_con_r41() -> None:
    assert acceptance_history(True, True) == acceptance_history(False, False)


def test_aceptacion_del_fundador_con_r41_y_control_nulo() -> None:
    """El fundador no emite: el control nulo de las señales no consume `null_rng`."""
    assert acceptance_history(True, True, null=True) == acceptance_history(False, True, null=True)


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
            enable_plasticity=True,
            plasticity_rate_base=0.4,
            enable_signals=True,
            enable_energy_transfer=True,
            enable_predation=True,
            mutation_rate=0.2,
            comm_content_null=NULL,
        )
        engine = SimulationEngine(config)
        extra = (
            encode_codon(0x22, 0x48, 0, 1),
            encode_codon(0x20, 0x48, 0, 2),
            encode_codon(0x2A, 0x48, 0, 6),
            encode_codon(0x39, 0x43, 0, 0, 120),
            encode_codon(0x3A, 0x46, 0, 0, 125),
            encode_codon(0x3E, 0x0D, 0, 1),
            encode_codon(0x38, 0x48, 0, 7),
            encode_codon(0x31, 0x40, 3, 0, 40),
        )
        for aid in sorted(engine.agents):
            agent = engine.agents[aid]
            agent.set_dna(CompactDNA(chromosome=agent.dna.chromosome + extra))

        class Spy:
            emitted = heard = 0

            def on_decisions(self, engine, frame):
                self.heard += sum(1 for a in engine.agents.values() if a.perceived_symbols)

            def on_tick_end(self, engine, frame):
                self.emitted += frame.events["signals_emitted"]

        spy = Spy()
        engine.observers.append(spy)
        engine.run(60)
        print([astuple(m) for m in engine.history])
        print([astuple(m) for m in engine.evolutionary_history])
        agents = sorted(engine.agents.items())
        print([(a, g.perceived_symbols, g.internal_state) for a, g in agents])
        print(engine.rng.bit_generator.state, engine.null_rng.bit_generator.state)
        print(engine.evo_rng.bit_generator.state)
        print(spy.emitted, spy.heard)
        """
    )
    for null in ("False", "True"):
        outputs = []
        for hash_seed in ("0", "123"):
            path = os.pathsep.join(
                filter(None, [str(ROOT / "src"), str(ROOT), os.environ.get("PYTHONPATH")])
            )
            env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": path}
            done = subprocess.run(
                [sys.executable, "-c", script.replace("NULL", null)],
                capture_output=True,
                text=True,
                env=env,
                check=True,
                cwd=ROOT,
            )
            outputs.append(done.stdout)
        assert outputs[0] == outputs[1]
        # La corrida emite y percibe de verdad: no es una igualdad trivial.
        emitted, heard = (int(n) for n in outputs[0].splitlines()[-1].split())
        assert emitted > 0 and heard > 0
