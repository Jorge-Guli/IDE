"""Tests de la endospora como conducta (bloque 17: R28, design D38 con la entrada de D50.2).

Cubren la entrada sólo por `SPORULATE` (factibilidad e inercia sin la política genética), la
germinación en la Fase 1, la física de la endospora (sin mensajes, `IDLE` sin decidir ni consumir
generadores, sin oportunidad de M2, sin reproducción, fuera del alcance de `SHARE` y `ATTACK`), su
costo reducido y el determinismo entre procesos con un ADN que esporula y germina de verdad.
"""

import copy
import os
import subprocess
import sys
import textwrap
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from ide.agent.dna import BEHAVIOR_TARGETS, encode_codon, founder_dna
from ide.config import SimulationConfig, sporulation_active
from ide.domain.types import (
    ActionType,
    AgentAction,
    Behavior,
    CompactDNA,
    KnowledgeUnit,
    Message,
    MessageType,
    Pattern,
)
from ide.environments.grid2d import ToroidalGrid2D
from ide.simulation.engine import SimulationEngine, TickMetricsObserver
from ide.simulation.pipeline import (
    DecisionSystem,
    EmissionSystem,
    MetabolismSystem,
    PerceptionSystem,
    SocialPerceptionSystem,
    TickFrame,
    build_systems,
)

ROOT = Path(__file__).resolve().parents[1]
IDLE = AgentAction(ActionType.IDLE)
SET_STATE = 0x0D


def cfg(**overrides: Any) -> SimulationConfig:
    """Configuración chica con la política genética y R28, sin costos ni reproducción."""
    base = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=6,
        resources_per_pattern=4,
        enable_evolution=True,
        enable_compact_dna=True,
        enable_genetic_policy=True,
        enable_sporulation=True,
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


def crowd(engine: SimulationEngine) -> None:
    for aid in sorted(engine.agents):
        put(engine, aid, (5, 5))


def clear_resources(engine: SimulationEngine) -> None:
    grid = grid_of(engine)
    for cell in grid.cell_resources:
        grid.cell_resources[cell].clear()
    grid._resource_cell.clear()  # pyright: ignore[reportPrivateUsage]


def place_resource(engine: SimulationEngine, aid: int, value: float = 1.0) -> None:
    grid = grid_of(engine)
    cell = grid._agent_cell[aid]  # pyright: ignore[reportPrivateUsage]
    pattern = sorted(grid.get_world_patterns())[0]
    grid._place_resource(pattern, value, cell)  # pyright: ignore[reportPrivateUsage]


def set_energy(engine: SimulationEngine, aid: int, energy: float) -> None:
    agent = engine.agents[aid]
    agent.apply_energy_delta(energy - agent.energy)


def behavior_dna(config: SimulationConfig, behavior: Behavior, payload: int = 127) -> CompactDNA:
    target = BEHAVIOR_TARGETS[list(Behavior).index(behavior)]
    codon = encode_codon(0x00, target, 0, 0, payload)
    return CompactDNA(chromosome=(*founder_dna(config).chromosome, codon, codon))


def idle_all(monkeypatch: pytest.MonkeyPatch, engine: SimulationEngine, skip: int = -1) -> None:
    for aid, agent in engine.agents.items():
        if aid != skip:
            monkeypatch.setattr(agent, "decide_action", lambda *_a: IDLE)


class Spy:
    def __init__(self) -> None:
        self.events: list[dict[str, int]] = []
        self.m2: list[int] = []

    def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.m2.append(frame.decision_opportunities)

    def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.events.append(dict(frame.events))


def spied(engine: SimulationEngine) -> Spy:
    spy = Spy()
    engine.observers.append(spy)
    return spy


def phase1(engine: SimulationEngine, tick: int = 0) -> TickFrame:
    """Ejecuta los sistemas de la Fase 1 que preceden a la decisión, en el orden del motor."""
    frame = TickFrame(tick)
    for system in engine.systems:
        if system.name == "decision":
            break
        system.run(engine, frame)
    return frame


# --- Condición efectiva (precisión 30) ---------------------------------------------------------


def test_condicion_efectiva_de_r28() -> None:
    on = cast(SimulationConfig, SimpleNamespace(enable_evolution=True, enable_sporulation=True))
    off = cast(SimulationConfig, SimpleNamespace(enable_evolution=False, enable_sporulation=True))
    assert sporulation_active(on) and not sporulation_active(off)
    assert not sporulation_active(cfg(enable_sporulation=False))


def test_germinacion_solo_con_r28_efectiva() -> None:
    assert "germination" in [s.name for s in build_systems(cfg())]
    assert "germination" not in [s.name for s in build_systems(cfg(enable_sporulation=False))]


# --- Entrada sólo por SPORULATE (D50.2) --------------------------------------------------------


def test_entrada_por_la_conducta(monkeypatch: pytest.MonkeyPatch) -> None:
    config = cfg()
    engine = SimulationEngine(config)
    crowd(engine)
    clear_resources(engine)
    engine.agents[1].set_dna(behavior_dna(config, Behavior.SPORULATE))
    set_energy(engine, 1, 0.25)
    idle_all(monkeypatch, engine, skip=1)
    spy = spied(engine)
    engine.step()
    assert engine.agents[1].is_endospore
    assert spy.events == [{"sporulations": 1}]
    assert not any(a.is_endospore for aid, a in engine.agents.items() if aid != 1)


def test_sin_energia_bajo_el_umbral_no_hay_entrada(monkeypatch: pytest.MonkeyPatch) -> None:
    config = cfg()
    engine = SimulationEngine(config)
    clear_resources(engine)
    engine.agents[1].set_dna(behavior_dna(config, Behavior.SPORULATE))
    set_energy(engine, 1, 1.0)  # por encima de spore_energy_threshold (0.30)
    idle_all(monkeypatch, engine, skip=1)
    engine.step()
    assert not engine.agents[1].is_endospore


def test_sin_entrada_por_umbral_en_la_fase_5() -> None:
    engine = SimulationEngine(cfg())
    clear_resources(engine)
    for aid in engine.agents:
        set_energy(engine, aid, 0.1)  # bajo el umbral, sin recursos: D38 los habría dormido
    engine.run(5)
    assert not any(a.is_endospore for a in engine.agents.values())


def test_r28_inerte_sin_la_politica_genetica() -> None:
    config = cfg(enable_genetic_policy=False, spore_energy_threshold=2.0)
    engine = SimulationEngine(config)
    spy = spied(engine)
    engine.run(10)
    assert not any(a.is_endospore for a in engine.agents.values())
    assert all("sporulations" not in e for e in spy.events)


# --- Germinación en la Fase 1 ------------------------------------------------------------------


def test_germina_ante_un_recurso_visible_y_actua(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg())
    clear_resources(engine)
    place_resource(engine, 1)
    agent = engine.agents[1]
    agent.set_endospore(True)
    calls: list[str] = []
    emit, decide = agent.perceive_and_emit_messages, agent.decide_action
    monkeypatch.setattr(
        agent, "perceive_and_emit_messages", lambda *a: (calls.append("emit"), emit(*a))[1]
    )
    monkeypatch.setattr(agent, "decide_action", lambda *a: (calls.append("decide"), decide(*a))[1])
    engine.step()
    assert not agent.is_endospore
    assert calls == ["emit", "decide"]


def test_sigue_en_endospora_sin_estimulos(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg())
    clear_resources(engine)
    agent = engine.agents[1]
    agent.set_endospore(True)

    def boom(*_a: object) -> None:
        raise AssertionError("una endospora no debe llamar a su política ni emitir")

    monkeypatch.setattr(agent, "decide_action", boom)
    monkeypatch.setattr(agent, "perceive_and_emit_messages", boom)
    engine.step()
    assert agent.is_endospore


def test_germinacion_por_rastro_positivo_con_r19() -> None:
    config = cfg(enable_stigmergy=True)
    pattern = Pattern((("id", "p_0"),))
    for value, germinates in ((1.0, True), (-1.0, False)):
        engine = SimulationEngine(config)
        clear_resources(engine)
        engine.agents[1].set_endospore(True)
        engine._evo.deposit_stigmergy(1, pattern, value, 0.9, 0)  # pyright: ignore[reportPrivateUsage]
        phase1(engine)
        assert (not engine.agents[1].is_endospore) is germinates


def test_germinacion_antes_de_la_percepcion_social() -> None:
    engine = SimulationEngine(cfg())
    crowd(engine)
    place_resource(engine, 1)
    engine.agents[1].set_endospore(True)
    frame = phase1(engine)
    assert not engine.agents[1].is_endospore
    assert 1 in frame.social  # germinó antes: se percibe socialmente como cualquier agente


# --- Física de la endospora --------------------------------------------------------------------


def test_endospora_no_decide_ni_consume_rng() -> None:
    engine = SimulationEngine(cfg())
    clear_resources(engine)
    engine.agents[2].set_endospore(True)
    frame = TickFrame(0, order=[2])
    frame.observations[2] = engine.env.get_observation(2, 0)
    state = copy.deepcopy(engine.rng.bit_generator.state)
    engine.agents[2].decide_action = lambda *_a: (_ for _ in ()).throw(AssertionError("decide"))  # type: ignore[method-assign]
    DecisionSystem().run(engine, frame)
    assert frame.actions == {2: IDLE}
    assert engine.rng.bit_generator.state == state


def test_endospora_no_emite_ni_se_percibe_socialmente() -> None:
    engine = SimulationEngine(cfg())
    crowd(engine)
    clear_resources(engine)
    engine.agents[3].set_endospore(True)
    frame = TickFrame(0, order=sorted(engine.agents))
    PerceptionSystem().run(engine, frame)
    SocialPerceptionSystem().run(engine, frame)
    EmissionSystem().run(engine, frame)
    assert 3 not in frame.social
    assert all(msg.sender_id != 3 for msg in frame.emitted)
    assert all(aid in frame.social for aid in engine.agents if aid != 3)


def test_ruteo_excluye_a_la_endospora(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(comm_radius=3))
    crowd(engine)
    clear_resources(engine)
    engine.agents[3].set_endospore(True)
    pattern = Pattern((("id", "p_0"),))
    belief = KnowledgeUnit(pattern, 1.0, 0.8, 1, 0, True)
    broadcast = Message(MessageType.BROADCAST_BELIEF, 1, None, pattern, belief)
    received: list[int] = []
    for aid, agent in engine.agents.items():
        monkeypatch.setattr(
            agent,
            "process_incoming_messages",
            lambda msgs, _t, a=aid: (received.extend([a] * len(msgs)), [])[1],
        )
    order = sorted(engine.agents)
    neighbors = {aid: [b for b in order if b != aid] for aid in order}
    for aid, inbox in engine._route([broadcast], neighbors, order).items():  # pyright: ignore[reportPrivateUsage]
        engine.agents[aid].process_incoming_messages(inbox, 0)
    assert 3 not in received and {0, 2, 4, 5} <= set(received)


def test_endospora_sin_oportunidad_en_m2() -> None:
    engine = SimulationEngine(cfg())
    clear_resources(engine)
    place_resource(engine, 2)
    engine.agents[2].set_endospore(True)
    frame = TickFrame(0, order=[2], actions={2: IDLE})
    TickMetricsObserver().on_decisions(engine, frame)
    assert frame.decision_opportunities == 0
    engine.agents[2].set_endospore(False)  # el control: decidiendo, sí suma
    TickMetricsObserver().on_decisions(engine, frame)
    assert frame.decision_opportunities == 1


def test_endospora_no_se_reproduce() -> None:
    engine = SimulationEngine(cfg(reproduction_threshold=2.0, max_population=50))
    clear_resources(engine)
    for aid in sorted(engine.agents):
        engine.agents[aid].set_endospore(True)
        set_energy(engine, aid, 2.4)
    spy = spied(engine)
    engine.step()
    assert len(engine.agents) == 6 and spy.events == [{}]


def test_holon_con_una_endospora_no_se_reproduce() -> None:
    config = cfg(
        reproduction_threshold=2.0,
        max_population=50,
        enable_holonic_hierarchy=True,
        enable_holon_reproduction=True,
    )
    engine = SimulationEngine(config)
    clear_resources(engine)
    from ide.agent.holon import CompositeAgent

    ids = [0, 1, 2]
    children = tuple(engine.root_nodes.pop(engine.agent_to_root[a]) for a in ids)
    holon = CompositeAgent(engine.next_holon_id, children, 0, True)
    engine.next_holon_id -= 1
    engine.root_nodes[holon.node_id] = holon
    for leaf in holon.leaf_agents:
        engine.agent_to_root[leaf.agent_id] = holon.node_id
    for aid in ids:
        set_energy(engine, aid, 2.5)
    engine.agents[1].set_endospore(True)
    births = engine._reproduce(0)  # pyright: ignore[reportPrivateUsage]
    # Ningún holón se reproduce por R17; sólo las hojas activas con energía suficiente (R12).
    assert not any(
        isinstance(n, CompositeAgent) and n is not holon for n in engine.root_nodes.values()
    )
    assert 1 in engine.agents and births == 2


def test_donantes_neutrales_sin_endosporas() -> None:
    engine = SimulationEngine(cfg(reproduction_mode="neutral", reproduction_threshold=2.0))
    for aid in sorted(engine.agents):
        set_energy(engine, aid, 1.0)
    for aid in (0, 1, 2):
        engine.agents[aid].set_endospore(aid == 1)
    for aid in (3, 4, 5):
        engine.agents[aid].set_endospore(True)
    set_energy(engine, 0, 2.5)
    sizes: list[int] = []

    class Stub:
        def integers(self, n: int) -> int:
            sizes.append(n)
            return 0

    engine.donor_rng = Stub()  # type: ignore[assignment]
    engine._reproduce(0)  # pyright: ignore[reportPrivateUsage]
    assert sizes == [2]  # donantes: los agentes 0 y 2; el 1 y los 3 a 5 están en endospora


def test_endospora_fuera_del_alcance_de_share_y_attack(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(enable_energy_transfer=True, enable_predation=True))
    crowd(engine)
    clear_resources(engine)
    set_energy(engine, 1, 2.0)
    set_energy(engine, 4, 2.0)
    set_energy(engine, 3, 0.5)
    engine.agents[3].set_endospore(True)
    for aid, agent in engine.agents.items():
        action = {
            1: AgentAction(ActionType.SHARE, 3),
            4: AgentAction(ActionType.ATTACK, 3),
        }.get(aid, IDLE)
        if aid != 3:
            monkeypatch.setattr(agent, "decide_action", lambda *_a, a=action: a)
    engine.step()
    assert engine.agents[3].energy == pytest.approx(0.5, abs=1e-9)
    assert engine.agents[1].energy == pytest.approx(2.0, abs=1e-9)


# --- Costo -------------------------------------------------------------------------------------


def test_gasto_reducido_en_endospora() -> None:
    config = cfg(
        metabolic_base_cost=0.01,
        spore_cost_fraction=0.05,
        move_cost=0.5,
        message_cost=0.5,
        dna_codon_cost=0.1,
        memory_capacity_cost=0.3,
        sensory_radius_cost=0.3,
    )
    engine = SimulationEngine(config)
    engine.agents[2].set_endospore(True)
    before = {aid: a.energy for aid, a in engine.agents.items()}
    frame = TickFrame(0, moved={2}, emitted=[], responses=[])
    MetabolismSystem().run(engine, frame)
    assert before[2] - engine.agents[2].energy == pytest.approx(0.0005, abs=1e-9)
    assert before[1] - engine.agents[1].energy > 0.0005  # el activo paga el costo completo


def test_endospora_senescente_pierde_costo_y_senescencia() -> None:
    config = cfg(
        enable_telomere_senescence=True,
        senescence_cost_rate=1e-5,
        metabolic_base_cost=0.01,
        spore_cost_fraction=0.05,
        telomere_min_lifespan=1,
        telomere_base_lifespan=5,
    )
    engine = SimulationEngine(config)
    engine.agents[2].set_endospore(True)
    before = engine.agents[2].energy
    frame = TickFrame(15)  # edad 15, longevidad 5: exceso 10
    from ide.simulation.pipeline import SenescenceSystem

    MetabolismSystem().run(engine, frame)
    SenescenceSystem().run(engine, frame)
    assert before - engine.agents[2].energy == pytest.approx(0.0015, abs=1e-9)


def test_sin_r28_la_endospora_manual_paga_el_costo_completo() -> None:
    """Inercia: con la bandera apagada el costo no cambia (la Fase II no tiene endosporas)."""
    config = cfg(enable_sporulation=False, metabolic_base_cost=0.01)
    engine = SimulationEngine(config)
    engine.agents[2].set_endospore(True)
    before = engine.agents[2].energy
    MetabolismSystem().run(engine, TickFrame(0))
    assert before - engine.agents[2].energy > 0.0005 + 1e-6


# --- Estado interno en la germinación (precisión E1) -------------------------------------------


def test_estado_interno_germinacion_y_endospora(monkeypatch: pytest.MonkeyPatch) -> None:
    config = cfg(enable_internal_state=True)
    engine = SimulationEngine(config)
    clear_resources(engine)
    codon = encode_codon(0x00, SET_STATE, 0, 2)
    dna = CompactDNA(chromosome=(*founder_dna(config).chromosome, codon))
    for aid in (1, 2):
        engine.agents[aid].set_dna(dna)
        engine.agents[aid].set_endospore(True)
    place_resource(engine, 1)  # el 1 germina y decide; el 2 sigue en endospora
    engine.step()
    assert not engine.agents[1].is_endospore and engine.agents[1].internal_state == 0b100
    assert engine.agents[2].is_endospore and engine.agents[2].internal_state == 0


# --- Determinismo ------------------------------------------------------------------------------


def test_endosporas_independientes_del_hash() -> None:
    script = textwrap.dedent(
        """
        from tests.test_sporulation import cfg, behavior_dna, set_energy
        from ide.domain.types import Behavior
        from ide.simulation.engine import SimulationEngine

        config = cfg(
            num_agents=10, resources_per_pattern=1, spore_energy_threshold=1.2,
            metabolic_base_cost=0.05, initial_energy=1.0, enable_telomere_senescence=True,
        )
        engine = SimulationEngine(config)
        for aid in sorted(engine.agents):
            engine.agents[aid].set_dna(behavior_dna(config, Behavior.SPORULATE, 100))
        counts = {"seen": 0, "germinations": 0}
        prev = {}
        class Spy:
            def on_decisions(self, engine, frame):
                # Germinó en la Fase 1 del tick: era endospora al final del tick anterior.
                counts["germinations"] += sum(
                    1 for a, v in prev.items() if v and a in engine.agents
                    and not engine.agents[a].is_endospore
                )
            def on_tick_end(self, engine, frame):
                counts["seen"] += frame.events.get("sporulations", 0)
                prev.clear()
                prev.update({a: x.is_endospore for a, x in engine.agents.items()})
        engine.observers.append(Spy())
        engine.run(40)
        print(counts["seen"], counts["germinations"])
        print(engine.history)
        print(engine.evolutionary_history)
        print([engine.agents[a].energy for a in sorted(engine.agents)])
        print(engine.rng.bit_generator.state, engine.evo_rng.bit_generator.state)
        """
    )
    outputs: list[str] = []
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
    seen, germinations = (int(x) for x in outputs[0].splitlines()[0].split())
    assert seen > 0 and germinations > 0  # esporula y germina de verdad
