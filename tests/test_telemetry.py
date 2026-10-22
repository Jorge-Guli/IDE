"""Tests de la telemetría de evolución abierta: fuentes de los nacimientos y fuentes únicas.

Cubren, sobre la telemetría del bloque 21 (D53.2, D63.2, precisiones 41, 43, 68, 126, 128,
131, 132 y 137), la fuente genética de cada nacimiento en la reproducción holónica neutral con
ADN (el donante de cada hoja, precisión 41) y con $R_{38}$ (quien inicia el cruce, nunca la
pareja), con selección y en neutral; que `cumulative_births` usa el conteo de nacimientos del
motor y coincide con la suma de `births_this_tick` con $R_{12}$, neutral, $R_{17}$ y $R_{38}$;
que ningún nacimiento queda sin anotar; que la telemetría lee lo que `GeneticPolicy` registró en
la decisión, sin volver a clasificar los recursos; y las funciones puras que comparten la
política, el ADN y la telemetría (orden de prueba, codón funcional, censo de codones e
información de las señales).
"""

import math
from collections import Counter
from dataclasses import fields, replace
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent import policy as policy_module
from ide.agent.dna import (
    canonical_codon,
    codon_census,
    encode_codon,
    expressible_codons,
    founder_dna,
    functional_codon_values,
    is_functional_codon,
    learning_codons,
    trait_or_behavior_codons,
)
from ide.agent.holon import CompositeAgent
from ide.agent.policy import (
    GeneticPolicy,
    behavior_feasibility,
    behavior_order,
    sensory_signals,
)
from ide.config import SimulationConfig
from ide.domain.types import CompactDNA, SensorySignals
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.attribution import PHASE25_PROTOCOL_CONFIGS
from ide.experiments.metrics import (
    NO_DECISIONS,
    GeneticMetricsCollector,
    first_feasible_slot,
    signal_information,
)
from ide.simulation import engine as engine_module
from ide.simulation.engine import SimulationEngine
from ide.simulation.pipeline import ReproductionSystem, TickFrame
from ide.simulation.telemetry import GeneticMetricsObserver, tick_decisions

GRID = {"grid_width": 12, "grid_height": 12, "num_agents": 16, "resources_per_pattern": 6}

# Con `recombination_base = 0.0` y la escala k = 0.60 del destino 0x0B: carga 108 da 0.50625
# (busca pareja), como en `tests/test_recombination.py`.
CROSS = encode_codon(0x00, 0x0B, 0, 0, 108)

# Celdas a distancia de Chebyshev 3 entre sí en una grilla toroidal de 12 x 12.
FAR = tuple((3 * i, 3 * j) for i in range(4) for j in range(4))


def marker(k: int) -> int:
    """`EMIT_TF` de modo 3: inerte (D33.2), sólo distingue ADN en los tests."""
    return encode_codon(0x00, 0x09, 3, k, 0)


def cfg(**overrides: Any) -> SimulationConfig:
    """Configuración chica con ADN, sin costos, sin mutación y sin reproducción espontánea."""
    base = SimulationConfig(
        grid_width=12,
        grid_height=12,
        num_agents=10,
        resources_per_pattern=4,
        enable_evolution=True,
        enable_compact_dna=True,
        recombination_base=0.0,
        mutation_rate=0.0,
        dna_point_mutation_rate=0.0,
        dna_duplication_rate=0.0,
        dna_deletion_rate=0.0,
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


def put(engine: SimulationEngine, aid: int, cell: tuple[int, int]) -> None:
    grid = cast(ToroidalGrid2D, engine.env)
    old = grid._agent_cell[aid]  # pyright: ignore[reportPrivateUsage]
    grid.cell_agents[old].discard(aid)
    grid.cell_agents[cell].add(aid)
    grid._agent_cell[aid] = cell  # pyright: ignore[reportPrivateUsage]


def tag_all(engine: SimulationEngine, *extra: int) -> dict[int, int]:
    """Da a cada agente un plásmido propio (lo hereda el hijo del primer ADN, precisión 35) y
    devuelve, por plásmido, su dueño."""
    owners: dict[int, int] = {}
    for aid in sorted(engine.agents):
        dna = CompactDNA(founder_dna(engine.config).chromosome + extra, plasmids=(marker(aid),))
        engine.agents[aid].set_dna(dna)
        owners[marker(aid)] = aid
    engine._express_phenotypes(engine.next_tick)  # pyright: ignore[reportPrivateUsage]
    return owners


def set_energy(engine: SimulationEngine, aid: int, energy: float) -> None:
    agent = engine.agents[aid]
    agent.apply_energy_delta(energy - agent.energy)


def make_holon(engine: SimulationEngine, ids: tuple[int, ...]) -> None:
    children = tuple(engine.root_nodes.pop(engine.agent_to_root[aid]) for aid in ids)
    holon = CompositeAgent(engine.next_holon_id, children, engine.next_tick, True)
    engine.next_holon_id -= 1
    engine.root_nodes[holon.node_id] = holon
    for leaf in holon.leaf_agents:
        engine.agent_to_root[leaf.agent_id] = holon.node_id


def reproduce_and_record(engine: SimulationEngine) -> tuple[TickFrame, tuple[int, ...]]:
    """Corre el sistema de reproducción y el registro de la telemetría genética del tick."""
    frame = TickFrame(engine.next_tick)
    ReproductionSystem().run(engine, frame)
    GeneticMetricsObserver().on_tick_end(engine, frame)
    return frame, engine.genetic_history[-1].birth_source_ids


def newborns(engine: SimulationEngine, before: set[int]) -> list[int]:
    return [aid for aid in sorted(engine.agents) if aid not in before]


def plasmid_owner(engine: SimulationEngine, aid: int, owners: dict[int, int]) -> int:
    dna = engine.agents[aid].dna
    assert dna is not None and len(dna.plasmids) == 1
    return owners[dna.plasmids[0]]


# --- Fuente genética de los nacimientos (precisiones 41, 68, 128 y 132) -------------------------


def test_fuente_de_cada_hoja_en_r17_neutral_con_adn_es_su_donante() -> None:
    config = cfg(
        enable_holonic_hierarchy=True, enable_holon_reproduction=True, reproduction_mode="neutral"
    )
    engine = SimulationEngine(config)
    for aid, cell in zip(sorted(engine.agents), FAR, strict=False):
        put(engine, aid, cell)
    owners = tag_all(engine)
    for k, aid in enumerate((2, 5, 7)):
        put(engine, aid, (3 + k % 2, 3 + k // 2))
        set_energy(engine, aid, 200.0)
    make_holon(engine, (2, 5, 7))
    before = set(engine.agents)
    frame, sources = reproduce_and_record(engine)
    born = newborns(engine, before)
    assert len(born) == frame.births == 3
    donors = [plasmid_owner(engine, aid, owners) for aid in born]
    assert sources == tuple(sorted(donors))
    # La fuente es el donante, no la hoja progenitora (salvo que el sorteo la elija).
    assert [b.source_id for b in frame.born] == donors
    assert [engine.agents[aid].parent_id for aid in born] == [2, 5, 7]


@pytest.mark.parametrize("neutral", [False, True])
def test_fuente_con_r38_es_quien_inicia_el_cruce_nunca_la_pareja(neutral: bool) -> None:
    """El primer ADN del cruce (su plásmido lo hereda el hijo, precisión 35) es la fuente; la
    pareja (3 u 8, reconocible por la cola del cromosoma del hijo) nunca se anota."""
    config = cfg(enable_recombination=True, reproduction_mode="neutral" if neutral else "energy")
    engine = SimulationEngine(config)
    for aid, cell in zip(sorted(engine.agents), FAR, strict=False):
        put(engine, aid, cell)
    put(engine, 5, (3, 3))
    put(engine, 3, (4, 3))
    put(engine, 8, (3, 4))
    owners = tag_all(engine, CROSS)
    for aid in sorted(engine.agents):  # la cola del cromosoma identifica a la pareja
        dna = cast(CompactDNA, engine.agents[aid].dna)
        engine.agents[aid].set_dna(replace(dna, chromosome=(*dna.chromosome, marker(40 + aid))))
    engine._express_phenotypes(engine.next_tick)  # pyright: ignore[reportPrivateUsage]
    partners: set[int] = set()
    firsts: set[int] = set()
    for _ in range(12):
        set_energy(engine, 5, 200.0)
        before = set(engine.agents)
        frame, sources = reproduce_and_record(engine)
        (child,) = newborns(engine, before)
        assert frame.events["recombinations"] == 1
        tail = cast(CompactDNA, engine.agents[child].dna).chromosome[-1]
        partner = (tail - marker(40)) >> 8  # `channel` de la marca
        assert partner in (3, 8)
        first = plasmid_owner(engine, child, owners)
        assert sources == (first,)  # una sola fuente por nacimiento: la pareja no se anota
        if not neutral:
            assert first == 5  # con selección, el progenitor inicia el cruce
        partners.add(partner)
        firsts.add(first)
        engine._remove([child], None)  # pyright: ignore[reportPrivateUsage]
    assert partners == {3, 8}
    if neutral:
        assert len(firsts) > 2  # los donantes sorteados, no la pareja


def test_cada_nacimiento_se_anota_en_el_motor() -> None:
    """`_give_birth` anota la fuente siempre, sin parámetros opcionales (precisión 68)."""
    engine = SimulationEngine(cfg(reproduction_mode="neutral"))
    tag_all(engine)
    parent, donor = engine.agents[1], engine.agents[6]
    set_energy(engine, 1, 200.0)
    engine.born.clear()
    child = engine._give_birth(parent, 0, donor)  # pyright: ignore[reportPrivateUsage]
    assert [(b.source_id, b.dna) for b in engine.born] == [(6, child.dna)]


def test_un_nacimiento_sin_anotar_detiene_la_telemetria() -> None:
    engine = SimulationEngine(cfg())
    frame = TickFrame(0)
    frame.births = 1  # el motor contó un nacimiento que nadie anotó
    with pytest.raises(RuntimeError, match="nacimientos"):
        GeneticMetricsObserver().on_tick_end(engine, frame)


class _BirthSpy:
    def __init__(self) -> None:
        self.frames: list[tuple[int, int]] = []

    def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
        pass

    def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.frames.append((frame.births, len(frame.born)))


STRESS = {
    "dna_point_mutation_rate": 0.6,
    "dna_duplication_rate": 0.1,
    "hgt_rate": 0.3,
    "recombination_base": 1.0,
}


_R17 = {"enable_holon_reproduction": True, "reproduction_threshold": 0.8}


@pytest.mark.parametrize(
    ("config", "holonic"),
    [
        (replace(PHASE25_PROTOCOL_CONFIGS["25a"], **GRID, **STRESS), False),  # R12 y R38
        (
            replace(PHASE25_PROTOCOL_CONFIGS["25a"], **GRID, **STRESS, reproduction_mode="neutral"),
            False,
        ),
        (
            replace(
                PHASE25_PROTOCOL_CONFIGS["25b"],
                **GRID,
                **STRESS,
                **_R17,
                reproduction_mode="neutral",
            ),
            True,
        ),  # R17 neutral con ADN y R38
        (replace(PHASE25_PROTOCOL_CONFIGS["25b"], **GRID, **_R17), True),  # R17 con selección
    ],
    ids=["seleccion-r38", "neutral-r38", "r17-neutral-r38", "r17-seleccion"],
)
def test_nacimientos_acumulados_coinciden_con_el_historial_evolutivo(
    config: SimulationConfig, holonic: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    holon_births = 0
    original = engine_module.reproduce_holon

    def spy(*args: Any, **kwargs: Any) -> Any:
        nonlocal holon_births
        holon_births += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(engine_module, "reproduce_holon", spy)
    engine = SimulationEngine(config)
    births_spy = _BirthSpy()
    engine.observers.append(births_spy)
    engine.run(150)
    total = 0
    for genetic, evo in zip(engine.genetic_history, engine.evolutionary_history, strict=True):
        total += evo.births_this_tick
        assert genetic.cumulative_births == total
    assert all(births == annotated for births, annotated in births_spy.frames)
    assert total > 0
    assert (holon_births > 0) is holonic  # R17 ocurre en las corridas holónicas
    if config.enable_recombination and config.recombination_base > 0:
        assert sum(m.recombinations for m in engine.ecology_history) > 0


# --- La telemetría lee la decisión registrada (precisiones 126 y 137) ---------------------------


def test_la_politica_registra_lo_que_calculo_al_decidir() -> None:
    engine = SimulationEngine(replace(PHASE25_PROTOCOL_CONFIGS["25a"], **GRID))
    seen = 0

    class Spy:
        def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
            nonlocal seen
            for aid in tick_decisions(engine, frame):
                agent = engine.agents[aid]
                trace = agent.decision_trace(frame.tick)
                evaluation = agent.decision_evaluation(frame.tick)
                assert (trace is None) == (evaluation is None)
                if trace is None or evaluation is None:
                    continue
                obs, social = frame.observations[aid], frame.social.get(aid)
                signals, feasible = behavior_feasibility(agent, obs, social)
                assert trace.signals == signals == sensory_signals(agent, obs, social)
                assert [trace.feasible(s) for s in range(len(feasible))] == list(feasible)
                slot = first_feasible_slot(evaluation.drives, feasible)
                assert trace.first_feasible(behavior_order(evaluation.drives)) == slot
                seen += 1

        def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
            pass

    engine.observers.append(Spy())
    engine.run(20)
    assert seen > 50


def test_una_sola_clasificacion_por_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(replace(PHASE25_PROTOCOL_CONFIGS["25a"], **GRID))
    engine.run(3)
    calls = 0
    original = policy_module._survey  # pyright: ignore[reportPrivateUsage]

    def spy(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    decided = 0

    class Count:
        def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
            nonlocal decided
            decided += sum(
                1
                for aid in tick_decisions(engine, frame)
                if engine.agents[aid].decision_evaluation(frame.tick) is not None
            )

        def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
            pass

    engine.observers.insert(0, Count())
    monkeypatch.setattr(policy_module, "_survey", spy)
    engine.run(5)
    assert decided > 0
    assert calls == decided


def test_las_decisiones_del_tick_se_calculan_una_vez() -> None:
    engine = SimulationEngine(replace(PHASE25_PROTOCOL_CONFIGS["25a"], **GRID))
    captured: list[bool] = []

    class Spy:
        def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
            captured.append(tick_decisions(engine, frame) is tick_decisions(engine, frame))

        def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
            pass

    engine.observers.append(Spy())
    engine.run(3)
    assert captured == [True, True, True]


# --- Funciones puras compartidas ----------------------------------------------------------------


@given(st.lists(st.floats(-1.0, 1.0, allow_nan=False), min_size=8, max_size=8))
def test_orden_de_prueba_de_la_politica(drives: list[float]) -> None:
    order = behavior_order(drives)
    assert list(order) == [
        slot for _, slot in sorted((-d, slot) for slot, d in enumerate(drives) if d > 0)
    ]


def test_genetic_policy_usa_el_orden_compartido() -> None:
    assert "behavior_order" in GeneticPolicy.decide.__code__.co_names


@given(st.integers(0, 2**32 - 1))
def test_codon_funcional_puro(codon: int) -> None:
    expected = canonical_codon(codon) in functional_codon_values(CompactDNA((codon,)))
    assert is_functional_codon(codon) is expected


_CODONS = st.integers(0, 2**32 - 1) | st.builds(
    encode_codon,
    st.sampled_from((0x00, 0x01, 0x0A, 0x10, 0x18, 0x22, 0x30, 0x35, 0x38, 0x80, 0x81, 0xC0)),
    st.sampled_from((0x00, 0x04, 0x09, 0x0B, 0x0D, 0x0E, 0x0F, 0x40, 0x45, 0x47, 0x48, 0x3F)),
    st.integers(0, 3),
    st.integers(0, 3),
    st.integers(-128, 127),
)


@given(
    st.lists(_CODONS, min_size=1, max_size=20),
    st.lists(_CODONS, max_size=4, unique=True),
    st.booleans(),
    st.booleans(),
)
def test_censo_de_codones_en_una_pasada(
    chromosome: list[int], plasmids: list[int], holonic: bool, roles: bool
) -> None:
    dna = CompactDNA(tuple(chromosome), plasmids=tuple(plasmids))
    values = expressible_codons(dna, holonic, roles)
    census = codon_census(dna, holonic, roles)
    assert census.expressible == len(values)
    assert census.nonattack == sum(1 for v, _ in values if (v >> 16) & 0xFF != 0x45)
    assert census.conditional == sum(1 for _, conditional in values if conditional)
    assert census.functional == trait_or_behavior_codons(dna)
    assert census.learning == len(learning_codons(dna, holonic, roles, False))
    assert census.learning_plastic == len(learning_codons(dna, holonic, roles, True))


def test_el_cache_de_genotipos_es_por_contenido() -> None:
    config = cfg()
    engine = SimulationEngine(config)
    founder = founder_dna(config)
    for aid in sorted(engine.agents):  # instancias distintas con el mismo contenido
        engine.agents[aid].set_dna(CompactDNA(tuple(founder.chromosome)))
    collector = GeneticMetricsCollector(config)
    collector.record_tick(0, engine.agents, engine.root_nodes, {}, [], [], [], NO_DECISIONS)
    assert len(collector._genotypes) == 1  # pyright: ignore[reportPrivateUsage]


_NAMES = tuple(f.name for f in fields(SensorySignals))


def _naive_information(samples: list[tuple[int, SensorySignals]]) -> float:
    """La definición de D63.2 escrita directamente, como referencia."""
    total = len(samples)
    best = 0.0
    for k in range(8):
        for name in _NAMES:
            cells = Counter(
                (bool(mask >> k & 1), bool(getattr(signals, name))) for mask, signals in samples
            )
            if not cells[(True, True)] + cells[(True, False)]:
                continue
            info = 0.0
            for (x, y), count in cells.items():
                px = sum(c for (a, _), c in cells.items() if a == x)
                py = sum(c for (_, b), c in cells.items() if b == y)
                info += count / total * math.log2(count * total / (px * py))
            best = max(best, info)
    return best


@given(
    st.lists(
        st.tuples(st.integers(0, 255), st.lists(st.booleans(), min_size=12, max_size=12)),
        max_size=30,
    )
)
def test_informacion_de_las_senales_con_sumas_precalculadas(
    samples: list[tuple[int, list[bool]]],
) -> None:
    data = [(mask, SensorySignals(*flags)) for mask, flags in samples]
    assert signal_information(data) == pytest.approx(_naive_information(data), abs=1e-9)


def test_sin_registro_de_la_politica_la_telemetria_da_lo_mismo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Una evaluación registrada sin `DecisionTrace` se resume con las mismas señales y
    factibilidades, calculadas desde el marco."""
    config = replace(PHASE25_PROTOCOL_CONFIGS["25a"], **GRID, **STRESS)
    reference = SimulationEngine(config)
    reference.run(40)
    original = GeneticPolicy.decide

    def without_trace(self: GeneticPolicy, agent: Any, *args: Any) -> Any:
        action = original(self, agent, *args)
        decision = agent._decision  # pyright: ignore[reportPrivateUsage]
        if decision is not None:
            agent._decision = (*decision[:3], None)  # pyright: ignore[reportPrivateUsage]
        return action

    monkeypatch.setattr(GeneticPolicy, "decide", without_trace)
    engine = SimulationEngine(config)
    engine.run(40)
    assert engine.genetic_history == reference.genetic_history
    assert any(m.policy_divergence > 0 for m in engine.genetic_history)
