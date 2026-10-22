"""Tests de la recombinación (R38) en la reproducción (bloque 20, design D51).

Cubren la condición efectiva de la regla; la búsqueda de pareja con la propensión expresada de
los dos, sin endosporas, con ADN y a distancia $\\le 1$, con las candidatas fijadas al empezar el
paso de reproducción (precisión 13); la secuencia exacta de extracciones de `evo_rng` de D51.2 y
su ausencia sin candidatas o con la regla apagada; la reproducción asexual sin pareja; la herencia
de plásmidos y firmas del progenitor y la mutación posterior (D51.3); la reproducción neutral con
el ADN del donante en el cruce (precisiones 14 y 35) y la reproducción holónica neutral con ADN
(precisión 41, con el orden de sorteo de `donor_rng` y sin cambios sin ADN); que la pareja no
cede energía (D51.4) y que $R_{17}$ no recombina; el evento `recombinations` del tick (precisión
20) y la igualdad de historiales entre procesos con distinto `PYTHONHASHSEED`.
"""

import os
import subprocess
import sys
import textwrap
from collections import Counter
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent import micro_agent as micro_agent_module
from ide.agent.dna import encode_codon, founder_dna, mutate_dna, recombine_dna
from ide.agent.holon import CompositeAgent
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig, recombination_active
from ide.domain.types import CompactDNA
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
from ide.simulation.engine import SimulationEngine
from ide.simulation.pipeline import TickFrame

ROOT = Path(__file__).resolve().parents[1]

# Con `recombination_base = 0.0` y la escala k = 0.60 del destino 0x0B (compact-dna): carga 108
# da 0.50625 (busca pareja) y carga 64 da 0.30 (no busca).
CROSS = encode_codon(0x00, 0x0B, 0, 0, 108)
SHY = encode_codon(0x00, 0x0B, 0, 0, 64)

# Celdas a distancia de Chebyshev 3 entre sí en una grilla toroidal de 12 x 12.
FAR = tuple((3 * i, 3 * j) for i in range(4) for j in range(4))
HOME = (3, 3)


def marker(k: int) -> int:
    """`EMIT_TF` de modo 3: inerte (D33.2), sólo distingue cromosomas en los tests."""
    return encode_codon(0x00, 0x09, 3, k, 0)


def cfg(**overrides: Any) -> SimulationConfig:
    """Configuración chica con ADN y R38, sin costos, sin mutación y sin reproducción."""
    base = SimulationConfig(
        grid_width=12,
        grid_height=12,
        num_agents=10,
        resources_per_pattern=4,
        enable_evolution=True,
        enable_compact_dna=True,
        enable_recombination=True,
        recombination_base=0.0,
        mutation_rate=0.0,
        discrete_mutation_prob=0.0,
        metabolic_base_cost=0.0,
        memory_capacity_cost=0.0,
        sensory_radius_cost=0.0,
        move_cost=0.0,
        message_cost=0.0,
        dna_codon_cost=0.0,
        reproduction_threshold=100.0,
        max_population=200,
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


def scatter(engine: SimulationEngine) -> None:
    for aid, cell in zip(sorted(engine.agents), FAR, strict=False):
        put(engine, aid, cell)


def set_energy(engine: SimulationEngine, aid: int, energy: float) -> None:
    agent = engine.agents[aid]
    agent.apply_energy_delta(energy - agent.energy)


def give(
    engine: SimulationEngine,
    aid: int,
    *extra: int,
    plasmids: tuple[int, ...] = (),
    crispr: tuple[int, ...] = (),
) -> CompactDNA:
    dna = CompactDNA(
        chromosome=founder_dna(engine.config).chromosome + extra,
        plasmids=plasmids,
        crispr_memory=crispr,
    )
    engine.agents[aid].set_dna(dna)
    return dna


def express(engine: SimulationEngine) -> None:
    engine._express_phenotypes(engine.next_tick)  # pyright: ignore[reportPrivateUsage]


def twin(generator: np.random.Generator) -> np.random.Generator:
    copy = np.random.Generator(np.random.PCG64())
    copy.bit_generator.state = generator.bit_generator.state
    return copy


def dna_of(agent: MicroAgent) -> CompactDNA:
    assert agent.dna is not None
    return agent.dna


def children_of(engine: SimulationEngine, parent: int, before: set[int]) -> list[MicroAgent]:
    return [
        engine.agents[a]
        for a in sorted(engine.agents)
        if a not in before and engine.agents[a].parent_id == parent
    ]


def reproduce(engine: SimulationEngine) -> Counter[str]:
    events: Counter[str] = Counter()
    engine._reproduce(engine.next_tick, events)  # pyright: ignore[reportPrivateUsage]
    return events


def spy_mutations(monkeypatch: pytest.MonkeyPatch) -> list[tuple[CompactDNA, dict[str, Any]]]:
    """Registra el ADN que muta cada nacimiento y el estado del generador al empezar."""
    calls: list[tuple[CompactDNA, dict[str, Any]]] = []
    original = micro_agent_module.mutate_dna

    def spy(
        dna: CompactDNA, config: SimulationConfig, rng: np.random.Generator, scale: float = 1.0
    ) -> CompactDNA:
        calls.append((dna, rng.bit_generator.state))
        return original(dna, config, rng, scale)

    monkeypatch.setattr(micro_agent_module, "mutate_dna", spy)
    return calls


def pair_engine(**overrides: Any) -> SimulationEngine:
    """El agente 5 en `HOME` con 3 y 8 adyacentes, todos con propensión alta; 5 se reproduce."""
    engine = SimulationEngine(cfg(**overrides))
    scatter(engine)
    put(engine, 5, HOME)
    put(engine, 3, (4, 3))
    put(engine, 8, (3, 4))
    give(engine, 5, CROSS, marker(1))
    give(engine, 3, CROSS, marker(2), marker(3))
    give(engine, 8, CROSS, marker(4))
    express(engine)
    set_energy(engine, 5, 200.0)
    return engine


# --- Condición efectiva (D51, D52.3) ------------------------------------------------------------


@pytest.mark.parametrize("dna", [False, True])
@pytest.mark.parametrize("evolution", [False, True])
@pytest.mark.parametrize("flag", [False, True])
def test_condicion_efectiva_de_r38(dna: bool, evolution: bool, flag: bool) -> None:
    config = cast(
        SimulationConfig,
        SimpleNamespace(
            enable_compact_dna=dna, enable_evolution=evolution, enable_recombination=flag
        ),
    )
    assert recombination_active(config) is (dna and evolution and flag)


def test_el_motor_guarda_la_condicion() -> None:
    assert SimulationEngine(cfg()).recombination_active is True
    assert SimulationEngine(cfg(enable_recombination=False)).recombination_active is False


# --- Secuencia exacta de extracciones de evo_rng (D51.2) ----------------------------------------


def test_secuencia_exacta_de_extracciones(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = pair_engine()
    parent = dna_of(engine.agents[5])
    partners = {3: dna_of(engine.agents[3]), 8: dna_of(engine.agents[8])}
    gemelo = twin(engine.evo_rng)
    calls = spy_mutations(monkeypatch)
    before = set(engine.agents)
    events = reproduce(engine)

    candidates = [3, 8]
    partner = candidates[int(gemelo.integers(len(candidates)))]
    a = int(gemelo.integers(1, len(parent.chromosome) + 1))
    b = int(gemelo.integers(0, len(partners[partner].chromosome)))
    expected = recombine_dna(parent, partners[partner], a, b, engine.config)
    assert len(calls) == 1
    source, state = calls[0]
    assert source == expected
    assert state == gemelo.bit_generator.state  # la mutación empieza tras las tres extracciones
    (child,) = children_of(engine, 5, before)
    assert child.dna == expected  # sin mutación (R13 ablacionada), el hijo es el recombinado
    assert events["recombinations"] == 1


def test_pareja_sin_costo_energetico() -> None:
    engine = pair_engine()
    partners = {aid: engine.agents[aid].energy for aid in (3, 8)}
    share = engine.config.offspring_energy_share
    before = set(engine.agents)
    events = reproduce(engine)
    assert events["recombinations"] == 1
    assert {aid: engine.agents[aid].energy for aid in (3, 8)} == partners
    (child,) = children_of(engine, 5, before)
    assert engine.agents[5].energy == pytest.approx(200.0 * (1 - share), abs=1e-9)
    assert child.energy == pytest.approx(200.0 * share, abs=1e-9)


# --- Búsqueda de pareja (D51.1, precisión 13) ---------------------------------------------------


def test_candidatas_con_propension_sin_endosporas_y_adyacentes() -> None:
    engine = SimulationEngine(cfg())
    scatter(engine)
    put(engine, 0, HOME)
    put(engine, 1, (4, 3))  # elegible
    put(engine, 2, (2, 3))  # propensión 0.30
    put(engine, 4, (3, 2))  # endospora
    put(engine, 6, (5, 3))  # a distancia 2
    put(engine, 7, (4, 4))  # elegible (diagonal)
    for aid in (0, 1, 4, 6, 7):
        give(engine, aid, CROSS)
    give(engine, 2, SHY)
    engine.agents[4].set_endospore(True)
    express(engine)
    pool = engine._mating_pool()  # pyright: ignore[reportPrivateUsage]
    # Fijadas al empezar el paso: con propensión, con ADN y sin endosporas, por `agent_id`.
    assert [m.agent_id for m in pool] == [0, 1, 6, 7]
    candidates = engine._mate_candidates(engine.agents[0], pool)  # pyright: ignore[reportPrivateUsage]
    assert [m.agent_id for m in candidates] == [1, 7]


def test_propension_insuficiente_reproduccion_asexual() -> None:
    def run(enable: bool) -> tuple[SimulationEngine, Counter[str], list[MicroAgent]]:
        engine = pair_engine(enable_recombination=enable)
        give(engine, 5, SHY, marker(1))
        express(engine)
        before = set(engine.agents)
        events = reproduce(engine)
        return engine, events, children_of(engine, 5, before)

    engine, events, (child,) = run(True)
    off, _, _ = run(False)
    assert engine.agents[5].phenotype.recombination_propensity == pytest.approx(0.30, abs=1e-9)
    assert "recombinations" not in events
    assert child.dna == engine.agents[5].dna
    assert engine.evo_rng.bit_generator.state == off.evo_rng.bit_generator.state


def test_sin_candidatas_no_extrae() -> None:
    def run(enable: bool) -> tuple[SimulationEngine, Counter[str], list[MicroAgent]]:
        engine = pair_engine(enable_recombination=enable)
        put(engine, 3, (6, 3))
        put(engine, 8, (3, 6))
        before = set(engine.agents)
        events = reproduce(engine)
        return engine, events, children_of(engine, 5, before)

    engine, events, (child,) = run(True)
    off, _, _ = run(False)
    assert engine.agents[5].phenotype.recombination_propensity >= 0.5
    assert "recombinations" not in events
    assert child.dna == engine.agents[5].dna
    assert engine.evo_rng.bit_generator.state == off.evo_rng.bit_generator.state


def test_recien_nacidos_fuera_de_las_candidatas(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg())
    scatter(engine)
    # 1 (fuera del alcance de todos) nace primero; su hijo se ubica junto a 6, que se reproduce
    # después en el mismo paso.
    give(engine, 1, CROSS, marker(1))
    give(engine, 6, CROSS, marker(6))
    express(engine)
    set_energy(engine, 1, 200.0)
    set_energy(engine, 6, 200.0)
    grid = grid_of(engine)
    original = grid.spawn_agent_near

    def spawn(agent_id: int, anchor: int, *args: Any, **kwargs: Any) -> tuple[int, int]:
        return original(agent_id, 6 if anchor == 1 else anchor, *args, **kwargs)

    monkeypatch.setattr(grid, "spawn_agent_near", spawn)
    before = set(engine.agents)
    events = reproduce(engine)
    (newborn,) = children_of(engine, 1, before)
    (child,) = children_of(engine, 6, before)
    assert grid.get_agent_distance(newborn.agent_id, 6) <= 1
    assert newborn.phenotype.recombination_propensity >= 0.5
    assert "recombinations" not in events
    assert child.dna == engine.agents[6].dna


# --- Herencia del progenitor y mutación posterior (D51.2, D51.3) --------------------------------


def test_plasmidos_y_firmas_del_progenitor() -> None:
    engine = pair_engine()
    p1, p2, s1, s2 = (encode_codon(0x00, 0x0A, 0, 0, k) for k in (5, 6, 7, 8))
    give(engine, 5, CROSS, marker(1), plasmids=(p1,), crispr=(s1,))
    for aid in (3, 8):
        give(engine, aid, CROSS, marker(aid), plasmids=(p2,), crispr=(s2,))
    express(engine)
    before = set(engine.agents)
    events = reproduce(engine)
    (child,) = children_of(engine, 5, before)
    assert events["recombinations"] == 1
    assert dna_of(child).plasmids == (p1,)
    assert dna_of(child).crispr_memory == (s1,)


def test_mutacion_posterior_al_cruce(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = pair_engine(mutation_rate=0.1, discrete_mutation_prob=0.1, dna_point_mutation_rate=0.5)
    parent = dna_of(engine.agents[5])
    partners = {3: dna_of(engine.agents[3]), 8: dna_of(engine.agents[8])}
    gemelo = twin(engine.evo_rng)
    calls = spy_mutations(monkeypatch)
    before = set(engine.agents)
    reproduce(engine)
    partner = [3, 8][int(gemelo.integers(2))]
    a = int(gemelo.integers(1, len(parent.chromosome) + 1))
    b = int(gemelo.integers(0, len(partners[partner].chromosome)))
    crossed = recombine_dna(parent, partners[partner], a, b, engine.config)
    assert calls[0][0] == crossed
    (child,) = children_of(engine, 5, before)
    assert child.dna == mutate_dna(crossed, engine.agents[5].base_config, gemelo)


# --- Reproducción neutral con recombinación (precisiones 14 y 35) -------------------------------


def test_reproduccion_neutral_con_el_adn_del_donante(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(reproduction_mode="neutral"))
    scatter(engine)
    put(engine, 0, HOME)
    put(engine, 1, (4, 3))
    for aid in sorted(engine.agents):
        extra = (CROSS,) if aid in (0, 1) else ()
        give(
            engine,
            aid,
            *extra,
            *(marker(10 + k) for k in range(aid + 1)),
            plasmids=(encode_codon(0x00, 0x0A, 0, 0, aid),),
            crispr=(encode_codon(0x00, 0x0A, 0, 0, 50 + aid),),
        )
    express(engine)
    set_energy(engine, 0, 200.0)
    dnas = {aid: dna_of(engine.agents[aid]) for aid in sorted(engine.agents)}
    gemelo_donante = twin(engine.donor_rng)
    gemelo = twin(engine.evo_rng)
    calls = spy_mutations(monkeypatch)
    before = set(engine.agents)
    events = reproduce(engine)

    donor = sorted(dnas)[int(gemelo_donante.integers(len(dnas)))]
    assert donor not in (0, 1)  # el donante no busca pareja: la búsqueda es la de 0
    candidates = [1]  # la única adyacente a 0 con propensión: la búsqueda es la de 0
    partner = candidates[int(gemelo.integers(len(candidates)))]
    a = int(gemelo.integers(1, len(dnas[donor].chromosome) + 1))
    b = int(gemelo.integers(0, len(dnas[partner].chromosome)))
    expected = recombine_dna(dnas[donor], dnas[partner], a, b, engine.config)
    assert events["recombinations"] == 1
    # Orden: el donante con `donor_rng`, el cruce con `evo_rng` y después la mutación.
    assert calls[0][0] == expected
    assert calls[0][1] == gemelo.bit_generator.state
    (child,) = children_of(engine, 0, before)
    assert child.dna == expected
    assert dna_of(child).chromosome[:a] == dnas[donor].chromosome[:a]
    assert dna_of(child).plasmids == dnas[donor].plasmids
    assert dna_of(child).crispr_memory == dnas[donor].crispr_memory
    assert engine.donor_rng.bit_generator.state == gemelo_donante.bit_generator.state


# --- Reproducción holónica: sin cruce y neutral con ADN (precisión 41) --------------------------


def make_holon(engine: SimulationEngine, ids: tuple[int, ...]) -> CompositeAgent:
    """Agrupa en un holón raíz nuevo los nodos raíz de las hojas `ids`, en ese orden."""
    children = tuple(engine.root_nodes.pop(engine.agent_to_root[aid]) for aid in ids)
    holon = CompositeAgent(engine.next_holon_id, children, engine.next_tick, True)
    engine.next_holon_id -= 1
    engine.root_nodes[holon.node_id] = holon
    for leaf in holon.leaf_agents:
        engine.agent_to_root[leaf.agent_id] = holon.node_id
    return holon


def holon_engine(leaves: tuple[int, ...], **overrides: Any) -> SimulationEngine:
    """Las hojas `leaves` juntas en un holón con energía para R17, cada agente con su marca."""
    config = cfg(enable_holonic_hierarchy=True, enable_holon_reproduction=True, **overrides)
    engine = SimulationEngine(config)
    scatter(engine)
    if config.enable_compact_dna:
        for aid in sorted(engine.agents):
            give(engine, aid, marker(aid))
        express(engine)
    for k, aid in enumerate(leaves):
        put(engine, aid, (3 + k % 2, 3 + k // 2))
        set_energy(engine, aid, 200.0)
    make_holon(engine, leaves)
    return engine


def test_un_donante_por_hoja_en_la_reproduccion_holonica_neutral() -> None:
    engine = holon_engine((2, 5, 7), reproduction_mode="neutral")
    dnas = {aid: dna_of(engine.agents[aid]) for aid in sorted(engine.agents)}
    gemelo = twin(engine.donor_rng)
    share = engine.config.offspring_energy_share
    before = set(engine.agents)
    reproduce(engine)
    donors = [sorted(dnas)[int(gemelo.integers(len(dnas)))] for _ in range(3)]
    for leaf, donor in zip((2, 5, 7), donors, strict=True):
        (child,) = children_of(engine, leaf, before)
        assert child.dna == dnas[donor]  # sin mutación, el ADN del donante
        assert engine.agents[leaf].energy == pytest.approx(200.0 * (1 - share), abs=1e-9)
    assert engine.donor_rng.bit_generator.state == gemelo.bit_generator.state
    replica = engine.root_nodes[engine.agent_to_root[children_of(engine, 2, before)[0].agent_id]]
    assert isinstance(replica, CompositeAgent)
    assert [leaf.parent_id for leaf in replica.leaf_agents] == [2, 5, 7]


def test_orden_de_los_sorteos_holon_y_despues_individuos() -> None:
    engine = holon_engine((2, 5, 7), reproduction_mode="neutral")
    set_energy(engine, 9, 200.0)
    set_energy(engine, 0, 200.0)
    dnas = {aid: dna_of(engine.agents[aid]) for aid in sorted(engine.agents)}
    leaves = [leaf.agent_id for leaf in engine.root_nodes[engine.agent_to_root[2]].leaf_agents]
    gemelo = twin(engine.donor_rng)
    before = set(engine.agents)
    reproduce(engine)
    # Primero las hojas del holón, en el orden de `leaf_agents`; después 0 y 9, por `agent_id`.
    for parent in [*leaves, 0, 9]:
        donor = sorted(dnas)[int(gemelo.integers(len(dnas)))]
        (child,) = children_of(engine, parent, before)
        assert child.dna == dnas[donor]
    assert engine.donor_rng.bit_generator.state == gemelo.bit_generator.state  # 5 extracciones


def test_reproduccion_holonica_neutral_sin_adn_como_en_la_fase_2() -> None:
    engine = holon_engine(
        (2, 5, 7), reproduction_mode="neutral", enable_compact_dna=False, enable_recombination=False
    )
    state = engine.donor_rng.bit_generator.state
    before = set(engine.agents)
    reproduce(engine)
    for leaf in (2, 5, 7):
        (child,) = children_of(engine, leaf, before)
        assert child.dna is None
        assert child.genome == engine.agents[leaf].genome
    assert engine.donor_rng.bit_generator.state == state


def test_r17_no_recombina() -> None:
    def run(enable: bool) -> tuple[SimulationEngine, Counter[str], set[int]]:
        engine = holon_engine((2, 5, 7), recombination_base=1.0, enable_recombination=enable)
        before = set(engine.agents)
        return engine, reproduce(engine), before

    engine, events, before = run(True)
    off, _, _ = run(False)
    assert all(engine.agents[a].phenotype.recombination_propensity == 1.0 for a in (2, 5, 7))
    assert "recombinations" not in events
    for leaf in (2, 5, 7):
        (child,) = children_of(engine, leaf, before)
        assert child.dna == engine.agents[leaf].dna
    assert engine.evo_rng.bit_generator.state == off.evo_rng.bit_generator.state


# --- Propiedad: las candidatas son exactamente las de D51.1 -------------------------------------


@given(
    cells=st.lists(st.tuples(st.integers(0, 11), st.integers(0, 11)), min_size=10, max_size=10),
    high=st.lists(st.booleans(), min_size=10, max_size=10),
    spores=st.lists(st.booleans(), min_size=10, max_size=10),
    parent=st.integers(0, 9),
)
def test_candidatas_por_definicion(
    cells: list[tuple[int, int]], high: list[bool], spores: list[bool], parent: int
) -> None:
    engine = SimulationEngine(cfg())
    for aid in sorted(engine.agents):
        put(engine, aid, cells[aid])
        give(engine, aid, CROSS if high[aid] else SHY)
        engine.agents[aid].set_endospore(spores[aid])
    express(engine)
    pool = engine._mating_pool()  # pyright: ignore[reportPrivateUsage]
    found = engine._mate_candidates(engine.agents[parent], pool)  # pyright: ignore[reportPrivateUsage]
    grid = grid_of(engine)
    expected = [
        b
        for b in range(10)
        if b != parent and high[b] and not spores[b] and grid.get_agent_distance(parent, b) <= 1
    ]
    assert [m.agent_id for m in found] == expected


# --- Evento del tick, inercia y determinismo ----------------------------------------------------


class EventSpy:
    def __init__(self) -> None:
        self.events: list[dict[str, int]] = []

    def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
        pass

    def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.events.append(dict(frame.events))


def protocol_002a(**overrides: Any) -> SimulationConfig:
    return replace(PHASE2_PROTOCOL_CONFIGS["002a"], **overrides)


def test_evento_recombinations_en_el_marco() -> None:
    config = protocol_002a(
        enable_compact_dna=True, enable_recombination=True, recombination_base=1.0
    )
    engine = SimulationEngine(config)
    spy = EventSpy()
    engine.observers.append(spy)
    engine.run(40)
    assert sum(e.get("recombinations", 0) for e in spy.events) > 0
    assert all(v > 0 for e in spy.events for v in e.values())


def run_snapshot(config: SimulationConfig, ticks: int) -> tuple[Any, ...]:
    engine = SimulationEngine(config)
    engine.run(ticks)
    agents = [engine.agents[a] for a in sorted(engine.agents)]
    return (
        engine.history,
        engine.evolutionary_history,
        [(a.agent_id, a.energy, a.dna, a.genome) for a in agents],
        engine.rng.bit_generator.state,
        engine.evo_rng.bit_generator.state,
        engine.donor_rng.bit_generator.state,
    )


@pytest.mark.parametrize("dna", [False, True])
def test_r38_inerte_sin_quien_busque_pareja_o_sin_adn(dna: bool) -> None:
    # Con el fundador (`recombination_base = 0`) nadie busca pareja; sin ADN la regla es inerte.
    base = protocol_002a(enable_compact_dna=dna)
    on = run_snapshot(replace(base, enable_recombination=True), 40)
    off = run_snapshot(base, 40)
    assert on == off


def test_historiales_iguales_entre_procesos_con_r38() -> None:
    script = textwrap.dedent(
        """
        from collections import Counter
        from dataclasses import replace
        from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
        from ide.simulation.engine import SimulationEngine

        totals = Counter()

        class Spy:
            def on_decisions(self, engine, frame):
                pass

            def on_tick_end(self, engine, frame):
                totals.update(frame.events)

        for mode in ("energy", "neutral"):
            config = replace(
                PHASE2_PROTOCOL_CONFIGS["002a"], enable_compact_dna=True,
                enable_recombination=True, recombination_base=1.0, reproduction_mode=mode,
            )
            engine = SimulationEngine(config)
            engine.observers.append(Spy())
            engine.run(60)
            print(engine.history)
            print(engine.evolutionary_history)
            agents = [engine.agents[a] for a in sorted(engine.agents)]
            print([(a.agent_id, a.energy, a.dna) for a in agents])
            print([a.memory.all_units() for a in agents])
            print(engine.rng.bit_generator.state, engine.evo_rng.bit_generator.state)
            print(engine.donor_rng.bit_generator.state)
        print(totals["recombinations"])
        """
    )
    outputs = []
    for hash_seed in ("0", "123"):
        # El `src` de este árbol primero: la instalación editable puede apuntar a otro.
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
    # La corrida tiene recombinaciones reales: la igualdad no es trivial.
    assert int(outputs[0].strip().splitlines()[-1]) > 0
