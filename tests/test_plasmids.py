"""Tests de los plásmidos (R26) y de la inmunidad CRISPR (R27) (bloque 19, design D37).

Cubren `receive_plasmid` (bloqueo, duplicado y FIFO) y `purge_plasmid` (FIFO de firmas); la
condición efectiva de las dos reglas; la conjugación con `hgt_rng` (donantes y candidatos fijados
al empezar el paso, sin endosporas, la secuencia exacta de extracciones de D37 y la aplicación
después del sorteo); la apertura y el cierre de los ensayos CRISPR, la purga por toxicidad y el
cierre sin purga si el plásmido se perdió; que `hgt_rng` no se consume con $R_{26}$ apagada; y la
igualdad de historiales entre procesos con distinto `PYTHONHASHSEED`.
"""

import os
import subprocess
import sys
import textwrap
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.dna import (
    crispr_immunity_active,
    founder_dna,
    plasmid_hgt_active,
    purge_plasmid,
    receive_plasmid,
)
from ide.config import SimulationConfig
from ide.domain.types import CompactDNA, Pattern
from ide.environments.grid2d import ToroidalGrid2D
from ide.simulation.engine import SimulationEngine
from ide.simulation.pipeline import (
    ConjugationSystem,
    CrisprTrialSystem,
    DownwardCausationSystem,
    EnvironmentDynamicsSystem,
    ReproductionSystem,
    TickFrame,
    _execute_attack,  # pyright: ignore[reportPrivateUsage]
    _execute_share,  # pyright: ignore[reportPrivateUsage]
    build_systems,
)

ROOT = Path(__file__).resolve().parents[1]


def cfg(**overrides: Any) -> SimulationConfig:
    """Configuración chica con ADN y R26, sin costos ni reproducción."""
    base = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=8,
        resources_per_pattern=4,
        enable_evolution=True,
        enable_compact_dna=True,
        enable_plasmid_hgt=True,
        hgt_rate=1.0,
        metabolic_base_cost=0.0,
        memory_capacity_cost=0.0,
        sensory_radius_cost=0.0,
        move_cost=0.0,
        message_cost=0.0,
        dna_codon_cost=0.0,
        reproduction_threshold=100.0,
    )
    return replace(base, **overrides)


def fresh_hgt_rng(seed: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed, spawn_key=(5,))))


def grid_of(engine: SimulationEngine) -> ToroidalGrid2D:
    return cast(ToroidalGrid2D, engine.env)


def put(engine: SimulationEngine, aid: int, cell: tuple[int, int]) -> None:
    grid = grid_of(engine)
    old = grid._agent_cell[aid]  # pyright: ignore[reportPrivateUsage]
    grid.cell_agents[old].discard(aid)
    grid.cell_agents[cell].add(aid)
    grid._agent_cell[aid] = cell  # pyright: ignore[reportPrivateUsage]


# Celdas a distancia de Chebyshev mayor que 1 entre sí y de (5, 5).
FAR = ((0, 0), (0, 3), (3, 0), (8, 0), (0, 8), (8, 8), (3, 8), (8, 3))


def scatter(engine: SimulationEngine) -> None:
    for aid, cell in zip(sorted(engine.agents), FAR, strict=False):
        put(engine, aid, cell)


def set_energy(engine: SimulationEngine, aid: int, energy: float) -> None:
    agent = engine.agents[aid]
    agent.apply_energy_delta(energy - agent.energy)


def with_plasmids(
    engine: SimulationEngine, aid: int, plasmids: tuple[int, ...], crispr: tuple[int, ...] = ()
) -> None:
    chromosome = founder_dna(engine.config).chromosome
    engine.agents[aid].set_dna(
        CompactDNA(chromosome=chromosome, plasmids=plasmids, crispr_memory=crispr)
    )


def plasmids_of(engine: SimulationEngine, aid: int) -> tuple[int, ...]:
    dna = engine.agents[aid].dna
    assert dna is not None
    return dna.plasmids


def crispr_of(engine: SimulationEngine, aid: int) -> tuple[int, ...]:
    dna = engine.agents[aid].dna
    assert dna is not None
    return dna.crispr_memory


# --- receive_plasmid y purge_plasmid (compact-dna) ------------------------------------------------


def test_receive_plasmid_bloqueo_duplicado_y_fifo() -> None:
    config = replace(cfg(), max_plasmids=2, enable_crispr_immunity=True)
    dna = CompactDNA(chromosome=(1,), plasmids=(1, 2), crispr_memory=(5,))
    assert receive_plasmid(dna, 5, config) is None
    assert receive_plasmid(dna, 2, config) is dna
    received = receive_plasmid(dna, 3, config)
    assert received is not None
    assert received.plasmids == (2, 3)
    assert received.chromosome == (1,)
    assert received.crispr_memory == (5,)


def test_receive_plasmid_sin_r27_no_bloquea() -> None:
    config = replace(cfg(), max_plasmids=3, enable_crispr_immunity=False)
    dna = CompactDNA(chromosome=(1,), plasmids=(1,), crispr_memory=(5,))
    received = receive_plasmid(dna, 5, config)
    assert received is not None
    assert received.plasmids == (1, 5)


def test_purge_plasmid_con_fifo_de_firmas() -> None:
    config = replace(cfg(), crispr_memory_size=2, enable_crispr_immunity=True)
    dna = CompactDNA(chromosome=(9,), plasmids=(4, 6), crispr_memory=(1, 2))
    purged = purge_plasmid(dna, 4, config)
    assert purged.plasmids == (6,)
    assert purged.crispr_memory == (2, 4)
    assert purged.chromosome == (9,)


def test_purge_plasmid_exige_el_codon_en_plasmids() -> None:
    dna = CompactDNA(chromosome=(9,), plasmids=(6,))
    with pytest.raises(ValueError):
        purge_plasmid(dna, 4, cfg())


@given(
    plasmids=st.lists(st.integers(0, 40), unique=True, max_size=6),
    crispr=st.lists(st.integers(0, 40), unique=True, max_size=6),
    codon=st.integers(0, 40),
    max_plasmids=st.integers(1, 6),
    immunity=st.booleans(),
)
def test_receive_plasmid_invariantes(
    plasmids: list[int], crispr: list[int], codon: int, max_plasmids: int, immunity: bool
) -> None:
    config = replace(
        cfg(), max_plasmids=max(max_plasmids, len(plasmids)), enable_crispr_immunity=immunity
    )
    dna = CompactDNA(chromosome=(1,), plasmids=tuple(plasmids), crispr_memory=tuple(crispr))
    result = receive_plasmid(dna, codon, config)
    if immunity and codon in crispr:
        assert result is None
        return
    assert result is not None
    assert result.crispr_memory == dna.crispr_memory
    assert result.chromosome == dna.chromosome
    if codon in plasmids:
        assert result is dna
    else:
        assert result.plasmids[-1] == codon
        assert len(result.plasmids) <= config.max_plasmids
        expected = (*plasmids, codon)[-config.max_plasmids :]
        assert result.plasmids == expected


# --- Condición efectiva y sistemas ----------------------------------------------------------------


@given(dna=st.booleans(), hgt=st.booleans(), crispr=st.booleans(), evolution=st.booleans())
def test_condicion_efectiva_de_r26_y_r27(
    dna: bool, hgt: bool, crispr: bool, evolution: bool
) -> None:
    config = SimulationConfig(
        enable_evolution=evolution or dna,
        enable_compact_dna=dna,
        enable_plasmid_hgt=hgt,
        enable_crispr_immunity=crispr,
    )
    assert plasmid_hgt_active(config) == (dna and hgt)
    assert crispr_immunity_active(config) == (dna and hgt and crispr)
    names = [system.name for system in build_systems(config)]
    assert ("conjugation" in names) == (dna and hgt)
    assert ("crispr_trials" in names) == (dna and hgt and crispr)


def test_sistemas_en_la_fase_5_tras_la_reproduccion() -> None:
    config = cfg(enable_holonic_hierarchy=True, enable_crispr_immunity=True)
    systems = build_systems(config)
    kinds = [type(system) for system in systems]
    i = kinds.index(ReproductionSystem)
    assert kinds[i + 1 : i + 4] == [
        ConjugationSystem,
        CrisprTrialSystem,
        DownwardCausationSystem,
    ]
    assert kinds.index(EnvironmentDynamicsSystem) > i + 3


def test_r27_sin_r26_es_inerte() -> None:
    config = cfg(enable_plasmid_hgt=False, enable_crispr_immunity=True)
    names = [system.name for system in build_systems(config)]
    assert "conjugation" not in names
    assert "crispr_trials" not in names
    engine = SimulationEngine(config)
    assert not engine.crispr_immunity_active


# --- hgt_rng --------------------------------------------------------------------------------------


def test_hgt_rng_declarado_con_spawn_key_5() -> None:
    engine = SimulationEngine(cfg(seed=17))
    assert engine.hgt_rng.bit_generator.state == fresh_hgt_rng(17).bit_generator.state


@pytest.mark.parametrize("crispr", [False, True])
def test_hgt_rng_sin_consumo_con_r26_apagada(crispr: bool) -> None:
    config = cfg(
        enable_plasmid_hgt=False,
        enable_crispr_immunity=crispr,
        reproduction_threshold=2.2,
        metabolic_base_cost=0.01,
    )
    engine = SimulationEngine(config)
    for aid in sorted(engine.agents):
        with_plasmids(engine, aid, (11, 12))
        set_energy(engine, aid, 2.0)
    engine.run(50)
    assert engine.hgt_rng.bit_generator.state == fresh_hgt_rng(config.seed).bit_generator.state
    assert all(engine.agents[aid].plasmid_trials == {} for aid in engine.agents)


def test_hgt_rng_sin_consumo_sin_donantes() -> None:
    engine = SimulationEngine(cfg())  # nadie tiene plásmidos: no hay donantes
    engine.run(5)
    assert engine.hgt_rng.bit_generator.state == fresh_hgt_rng(42).bit_generator.state


# --- Donantes y sorteo (simulation-engine) --------------------------------------------------------


def test_donantes_elegibles() -> None:
    config = cfg(hgt_energy_ratio=0.85, reproduction_threshold=2.2, hgt_rate=0.0)
    engine = SimulationEngine(config)
    scatter(engine)
    for aid in sorted(engine.agents):
        set_energy(engine, aid, 5.0)
    with_plasmids(engine, 1, (11,))
    with_plasmids(engine, 2, (12,))
    with_plasmids(engine, 3, (13,))
    set_energy(engine, 1, 1.87)
    set_energy(engine, 2, 1.86)
    engine.agents[3].set_endospore(True)
    # Con hgt_rate = 0.0 cada donante extrae sólo su `u`: uno solo extrae uno solo.
    assert engine._draw_conjugations() == []  # pyright: ignore[reportPrivateUsage]
    twin = fresh_hgt_rng(config.seed)
    twin.random()
    assert engine.hgt_rng.bit_generator.state == twin.bit_generator.state


def test_secuencia_exacta_de_extracciones() -> None:
    config = cfg(hgt_rate=1.0, hgt_energy_ratio=0.001)
    engine = SimulationEngine(config)
    scatter(engine)
    put(engine, 0, (5, 5))
    put(engine, 2, (5, 6))
    put(engine, 7, (4, 4))
    plasmids = (21, 22, 23)
    with_plasmids(engine, 0, plasmids)
    transfers = engine._draw_conjugations()  # pyright: ignore[reportPrivateUsage]
    twin = fresh_hgt_rng(config.seed)
    assert float(twin.random()) < 1.0
    i = int(twin.integers(2))
    j = int(twin.integers(3))
    assert transfers == [([2, 7][i], plasmids[j])]
    assert engine.hgt_rng.bit_generator.state == twin.bit_generator.state


def test_donante_sin_candidatos_solo_extrae_u() -> None:
    config = cfg(hgt_rate=1.0, hgt_energy_ratio=0.001)
    engine = SimulationEngine(config)
    scatter(engine)
    with_plasmids(engine, 0, (21, 22))
    assert engine._draw_conjugations() == []  # pyright: ignore[reportPrivateUsage]
    twin = fresh_hgt_rng(config.seed)
    twin.random()
    assert engine.hgt_rng.bit_generator.state == twin.bit_generator.state


def test_endospora_no_es_candidata() -> None:
    config = cfg(hgt_rate=1.0, hgt_energy_ratio=0.001)
    engine = SimulationEngine(config)
    scatter(engine)
    put(engine, 0, (5, 5))
    put(engine, 2, (5, 6))
    put(engine, 7, (4, 4))
    engine.agents[7].set_endospore(True)
    with_plasmids(engine, 0, (21,))
    transfers = engine._draw_conjugations()  # pyright: ignore[reportPrivateUsage]
    assert transfers == [(2, 21)]


def test_donantes_y_candidatos_fijados_al_empezar() -> None:
    """Las transferencias se aplican después de sortearlas todas: lo recibido en el paso no
    convierte al receptor en donante ni cambia los plásmidos que sortea un donante."""
    config = cfg(hgt_rate=1.0, hgt_energy_ratio=0.001, max_plasmids=4)
    engine = SimulationEngine(config)
    scatter(engine)
    put(engine, 0, (5, 5))
    put(engine, 1, (5, 6))
    with_plasmids(engine, 0, (21,))
    # El agente 1 no tiene plásmidos al empezar: no es donante aunque reciba uno del 0.
    events: Counter[str] = Counter()
    engine._conjugate(0, events)  # pyright: ignore[reportPrivateUsage]
    # Un solo donante (el 0) con un solo candidato: `random`, `integers(1)` e `integers(1)`, sin
    # la `u` que extraería el 1 si lo recibido lo volviera donante, ni permutación.
    twin = fresh_hgt_rng(config.seed)
    twin.random()
    twin.integers(1)
    twin.integers(1)
    assert engine.hgt_rng.bit_generator.state == twin.bit_generator.state
    assert plasmids_of(engine, 1) == (21,)
    assert events["hgt_transfers"] == 1


def test_recien_nacido_entre_los_candidatos() -> None:
    config = cfg(
        hgt_rate=1.0, hgt_energy_ratio=0.001, reproduction_threshold=1.0, max_population=50
    )
    engine = SimulationEngine(config)
    scatter(engine)
    for aid in sorted(engine.agents):
        set_energy(engine, aid, 0.5)
    put(engine, 0, (5, 5))
    with_plasmids(engine, 0, (21,))
    set_energy(engine, 0, 4.0)
    recorded: list[list[tuple[int, int]]] = []
    original = engine._draw_conjugations  # pyright: ignore[reportPrivateUsage]

    def spy() -> list[tuple[int, int]]:
        transfers = original()
        recorded.append(transfers)
        return transfers

    engine._draw_conjugations = spy  # type: ignore[method-assign]
    engine.step()
    child = max(engine.agents)
    assert child == 8
    # El donante 0 es el primero en el sorteo y su único candidato es el hijo recién nacido
    # (que, al heredar el plásmido, también dona después).
    assert len(recorded) == 1
    assert recorded[0][0] == (child, 21)


# --- Aplicación de las transferencias -------------------------------------------------------------


def test_transferencia_aplicada_con_ensayo() -> None:
    engine = SimulationEngine(cfg(enable_crispr_immunity=True))
    with_plasmids(engine, 2, (11,))
    set_energy(engine, 2, 1.4)
    events: Counter[str] = Counter()
    engine._apply_conjugations([(2, 33)], 30, events)  # pyright: ignore[reportPrivateUsage]
    assert plasmids_of(engine, 2) == (11, 33)
    assert engine.agents[2].plasmid_trials == {33: (30, 1.4, 0.0)}
    assert events == Counter({"hgt_transfers": 1})


def test_transferencia_sin_r27_no_abre_ensayo() -> None:
    engine = SimulationEngine(cfg())
    events: Counter[str] = Counter()
    engine._apply_conjugations([(2, 33)], 30, events)  # pyright: ignore[reportPrivateUsage]
    assert plasmids_of(engine, 2) == (33,)
    assert engine.agents[2].plasmid_trials == {}
    assert events == Counter({"hgt_transfers": 1})


def test_set_dna_vacia_las_caches_al_recibir() -> None:
    engine = SimulationEngine(cfg())
    agent = engine.agents[2]
    before = agent.dna
    engine._apply_conjugations([(2, 33)], 0, Counter())  # pyright: ignore[reportPrivateUsage]
    assert agent.dna is not before
    assert dict(agent.plastic_weights) == {}


def test_conflicto_de_llegada_resuelto_por_sorteo() -> None:
    config = cfg(hgt_rate=1.0, hgt_energy_ratio=0.001, max_plasmids=1)
    engine = SimulationEngine(config)
    scatter(engine)
    put(engine, 0, (5, 5))
    put(engine, 1, (6, 6))
    put(engine, 4, (5, 6))  # receptor, adyacente a los dos donantes y sin plásmidos
    with_plasmids(engine, 0, (21,))
    with_plasmids(engine, 1, (22,))
    # Los donantes 0 y 1 son adyacentes entre sí: sus candidatos son [1, 4] y [0, 4].
    events: Counter[str] = Counter()
    engine._conjugate(0, events)  # pyright: ignore[reportPrivateUsage]
    twin = fresh_hgt_rng(config.seed)
    transfers: list[tuple[int, int]] = []
    for donor, cands, plasmids in ((0, [1, 4], (21,)), (1, [0, 4], (22,))):
        assert float(twin.random()) < 1.0
        receptor = cands[int(twin.integers(len(cands)))]
        transfers.append((receptor, plasmids[int(twin.integers(len(plasmids)))]))
        assert donor in (0, 1)
    order = [int(k) for k in twin.permutation(len(transfers))]
    assert engine.hgt_rng.bit_generator.state == twin.bit_generator.state
    expected: dict[int, tuple[int, ...]] = {0: (21,), 1: (22,), 4: ()}
    for k in order:
        receptor, codon = transfers[k]
        expected[receptor] = (codon,)
    for aid, plasmids in expected.items():
        assert plasmids_of(engine, aid) == plasmids


def test_dos_transferencias_al_mismo_receptor_permutadas() -> None:
    """Escenario del spec: con max_plasmids = 1 queda el codón aplicado en último lugar."""
    config = cfg(max_plasmids=1)
    for seed in range(6):
        engine = SimulationEngine(replace(config, seed=seed))
        events: Counter[str] = Counter()
        transfers = [(4, 21), (4, 22)]
        engine._apply_conjugations(transfers, 0, events)  # pyright: ignore[reportPrivateUsage]
        twin = fresh_hgt_rng(seed)
        last = [int(k) for k in twin.permutation(2)][-1]
        assert plasmids_of(engine, 4) == (transfers[last][1],)
        assert events["hgt_transfers"] == 2
        assert engine.hgt_rng.bit_generator.state == twin.bit_generator.state


def test_una_sola_transferencia_no_permuta() -> None:
    engine = SimulationEngine(cfg())
    engine._apply_conjugations([(4, 21)], 0, Counter())  # pyright: ignore[reportPrivateUsage]
    assert engine.hgt_rng.bit_generator.state == fresh_hgt_rng(42).bit_generator.state


def test_transferencia_bloqueada_por_crispr() -> None:
    engine = SimulationEngine(cfg(enable_crispr_immunity=True))
    with_plasmids(engine, 2, (11,), crispr=(33,))
    before = engine.agents[2].dna
    events: Counter[str] = Counter()
    engine._apply_conjugations([(2, 33)], 30, events)  # pyright: ignore[reportPrivateUsage]
    assert engine.agents[2].dna is before
    assert engine.agents[2].plasmid_trials == {}
    assert events == Counter({"crispr_rejections": 1})


def test_codon_ya_presente_no_cuenta() -> None:
    engine = SimulationEngine(cfg(enable_crispr_immunity=True))
    with_plasmids(engine, 2, (33,))
    before = engine.agents[2].dna
    events: Counter[str] = Counter()
    engine._apply_conjugations([(2, 33)], 30, events)  # pyright: ignore[reportPrivateUsage]
    assert engine.agents[2].dna is before
    assert engine.agents[2].plasmid_trials == {}
    assert events == Counter()


def test_memoria_intacta_tras_la_conjugacion_con_control_nulo() -> None:
    config = cfg(hgt_rate=1.0, hgt_energy_ratio=0.001, comm_content_null=True)
    engine = SimulationEngine(config)
    scatter(engine)
    put(engine, 0, (5, 5))
    put(engine, 2, (5, 6))
    with_plasmids(engine, 0, (21,))
    pattern = Pattern((1,))
    engine.agents[2].learn_from_experience(pattern, 0.5, 0)
    memory = engine.agents[2].memory.all_units()
    null_state = engine.null_rng.bit_generator.state
    engine._conjugate(0, Counter())  # pyright: ignore[reportPrivateUsage]
    assert plasmids_of(engine, 2) == (21,)
    assert engine.agents[2].memory.all_units() == memory
    assert engine.null_rng.bit_generator.state == null_state


# --- Ensayo CRISPR --------------------------------------------------------------------------------


def trial_engine(energy_at_end: float) -> tuple[SimulationEngine, Counter[str]]:
    """Ensayo abierto en el tick 30 con `e0 = 1.4` y energía final `energy_at_end`."""
    engine = SimulationEngine(
        cfg(enable_crispr_immunity=True, crispr_eval_ticks=20, crispr_toxicity_threshold=0.20)
    )
    set_energy(engine, 2, 1.4)
    engine._apply_conjugations([(2, 33)], 30, Counter())  # pyright: ignore[reportPrivateUsage]
    set_energy(engine, 2, energy_at_end)
    return engine, Counter()


def test_plasmido_toxico_purgado() -> None:
    engine, events = trial_engine(1.1)
    engine._evaluate_crispr(49, events)  # pyright: ignore[reportPrivateUsage]
    assert 33 in plasmids_of(engine, 2)  # no venció todavía
    assert list(engine.agents[2].plasmid_trials) == [33]
    engine._evaluate_crispr(50, events)  # pyright: ignore[reportPrivateUsage]
    assert 33 not in plasmids_of(engine, 2)
    assert crispr_of(engine, 2) == (33,)
    assert engine.agents[2].plasmid_trials == {}
    assert events == Counter({"crispr_purges": 1})


def test_plasmido_inocuo() -> None:
    engine, events = trial_engine(1.3)
    engine._evaluate_crispr(50, events)  # pyright: ignore[reportPrivateUsage]
    assert plasmids_of(engine, 2) == (33,)
    assert crispr_of(engine, 2) == ()
    assert engine.agents[2].plasmid_trials == {}
    assert events == Counter()


def test_la_reproduccion_no_cuenta_como_toxicidad() -> None:
    engine = SimulationEngine(
        cfg(enable_crispr_immunity=True, crispr_eval_ticks=20, crispr_toxicity_threshold=0.20)
    )
    set_energy(engine, 2, 1.4)
    engine._apply_conjugations([(2, 33)], 30, Counter())  # pyright: ignore[reportPrivateUsage]
    agent = engine.agents[2]
    # Cede 1.2 a un hijo: con offspring_energy_share = 0.5, desde una energía de 2.4.
    set_energy(engine, 2, 2.4)
    agent.create_offspring(99, 40, np.random.Generator(np.random.PCG64(0)))
    assert agent.plasmid_trials[33][2] == pytest.approx(1.2, abs=1e-9)
    set_energy(engine, 2, 1.1)
    events: Counter[str] = Counter()
    engine._evaluate_crispr(50, events)  # pyright: ignore[reportPrivateUsage]
    assert 33 in plasmids_of(engine, 2)
    assert engine.agents[2].plasmid_trials == {}
    assert events == Counter()


def test_plasmido_perdido_se_cierra_sin_purga() -> None:
    engine = SimulationEngine(
        cfg(
            enable_crispr_immunity=True,
            crispr_eval_ticks=20,
            crispr_toxicity_threshold=0.20,
            max_plasmids=1,
        )
    )
    set_energy(engine, 2, 1.4)
    engine._apply_conjugations([(2, 33)], 30, Counter())  # pyright: ignore[reportPrivateUsage]
    engine._apply_conjugations([(2, 34)], 35, Counter())  # pyright: ignore[reportPrivateUsage]
    assert plasmids_of(engine, 2) == (34,)  # 33 se perdió por FIFO
    set_energy(engine, 2, 0.1)
    events: Counter[str] = Counter()
    engine._evaluate_crispr(49, events)  # pyright: ignore[reportPrivateUsage]
    assert list(engine.agents[2].plasmid_trials) == [33, 34]  # sólo se cierra al vencer
    engine._evaluate_crispr(50, events)  # pyright: ignore[reportPrivateUsage]
    assert list(engine.agents[2].plasmid_trials) == [34]
    assert crispr_of(engine, 2) == ()
    assert plasmids_of(engine, 2) == (34,)
    assert events == Counter()
    engine._evaluate_crispr(55, events)  # pyright: ignore[reportPrivateUsage]
    assert crispr_of(engine, 2) == (34,)  # el 34 sí era tóxico
    assert events == Counter({"crispr_purges": 1})


def test_ensayos_en_orden_de_codon_y_purga_con_fifo() -> None:
    engine = SimulationEngine(
        cfg(
            enable_crispr_immunity=True,
            crispr_eval_ticks=1,
            crispr_toxicity_threshold=0.0,
            crispr_memory_size=1,
        )
    )
    set_energy(engine, 2, 1.0)
    engine._apply_conjugations([(2, 40)], 0, Counter())  # pyright: ignore[reportPrivateUsage]
    engine._apply_conjugations([(2, 30)], 0, Counter())  # pyright: ignore[reportPrivateUsage]
    set_energy(engine, 2, 0.5)
    events: Counter[str] = Counter()
    engine._evaluate_crispr(1, events)  # pyright: ignore[reportPrivateUsage]
    # Se purga 30 y después 40: la memoria de una firma conserva la última.
    assert plasmids_of(engine, 2) == ()
    assert crispr_of(engine, 2) == (40,)
    assert events == Counter({"crispr_purges": 2})


def test_ensayo_no_heredado_por_el_hijo_nacido_en_el_motor() -> None:
    engine = SimulationEngine(cfg(enable_crispr_immunity=True))
    engine._apply_conjugations([(2, 33)], 0, Counter())  # pyright: ignore[reportPrivateUsage]
    child = engine.agents[2].create_offspring(99, 1, np.random.Generator(np.random.PCG64(0)))
    assert child.plasmid_trials == {}


# --- Eventos del tick y determinismo --------------------------------------------------------------


class EventSpy:
    def __init__(self) -> None:
        self.events: list[dict[str, int]] = []

    def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
        pass

    def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.events.append(dict(frame.events))


def test_eventos_del_tick_en_el_marco() -> None:
    config = cfg(
        hgt_rate=1.0,
        hgt_energy_ratio=0.001,
        enable_crispr_immunity=True,
        crispr_eval_ticks=1,
        crispr_toxicity_threshold=0.0,
        metabolic_base_cost=0.05,
    )
    engine = SimulationEngine(config)
    for aid in sorted(engine.agents):
        put(engine, aid, (5, 5))
        set_energy(engine, aid, 3.0)
    with_plasmids(engine, 0, (21,))
    spy = EventSpy()
    engine.observers.append(spy)
    engine.run(4)
    assert sum(e.get("hgt_transfers", 0) for e in spy.events) > 0
    assert sum(e.get("crispr_purges", 0) for e in spy.events) > 0
    assert all(v > 0 for e in spy.events for v in e.values())


def test_historiales_iguales_entre_procesos_con_r26_y_r27() -> None:
    script = textwrap.dedent(
        """
        from collections import Counter
        from dataclasses import replace
        from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
        from ide.simulation.engine import SimulationEngine

        config = replace(
            PHASE2_PROTOCOL_CONFIGS["002a"], enable_compact_dna=True,
            enable_plasmid_hgt=True, enable_crispr_immunity=True,
            dna_excision_rate=0.5, hgt_rate=0.5, hgt_energy_ratio=0.3,
            crispr_eval_ticks=3, crispr_toxicity_threshold=0.0,
        )
        totals = Counter()

        class Spy:
            def on_decisions(self, engine, frame):
                pass

            def on_tick_end(self, engine, frame):
                totals.update(frame.events)

        engine = SimulationEngine(config)
        engine.observers.append(Spy())
        engine.run(60)
        print(engine.history)
        print(engine.evolutionary_history)
        agents = [engine.agents[a] for a in sorted(engine.agents)]
        print([(a.agent_id, a.energy, a.dna, a.plasmid_trials) for a in agents])
        print([a.memory.all_units() for a in agents])
        print(engine.rng.bit_generator.state, engine.evo_rng.bit_generator.state)
        print(engine.hgt_rng.bit_generator.state)
        print(totals["hgt_transfers"], totals["crispr_purges"], totals["crispr_rejections"])
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
    # La corrida tiene conjugaciones y purgas reales: la igualdad no es trivial.
    transfers, purges, _ = (int(x) for x in outputs[0].strip().splitlines()[-1].split())
    assert transfers > 0
    assert purges > 0


# --- Precisión 125: lo cedido por SHARE y lo robado no cuentan como toxicidad ---


def test_credit_plasmid_trials_suma_a_todos_los_ensayos_abiertos() -> None:
    engine = SimulationEngine(cfg(enable_crispr_immunity=True))
    agent = engine.agents[2]
    assert not agent.has_plasmid_trials
    agent.credit_plasmid_trials(0.3)  # sin ensayos no hace nada
    assert agent.plasmid_trials == {}
    set_energy(engine, 2, 1.0)
    engine._apply_conjugations([(2, 40)], 3, Counter())  # pyright: ignore[reportPrivateUsage]
    engine._apply_conjugations([(2, 30)], 4, Counter())  # pyright: ignore[reportPrivateUsage]
    assert agent.has_plasmid_trials
    agent.credit_plasmid_trials(0.25)
    assert agent.plasmid_trials == {30: (4, 1.0, 0.25), 40: (3, 1.0, 0.25)}


def crispr_pair() -> SimulationEngine:
    """Agente 2 con un ensayo abierto en el tick 30 con `e0 = 1.4`, adyacente al agente 3."""
    engine = SimulationEngine(
        cfg(
            enable_crispr_immunity=True,
            crispr_eval_ticks=20,
            crispr_toxicity_threshold=0.20,
            share_fraction=0.25,
            attack_power=0.5,
        )
    )
    scatter(engine)
    put(engine, 2, (5, 5))
    put(engine, 3, (5, 6))
    set_energy(engine, 2, 1.4)
    engine._apply_conjugations([(2, 33)], 30, Counter())  # pyright: ignore[reportPrivateUsage]
    return engine


def test_un_cooperador_que_cede_energia_no_purga_por_eso() -> None:
    engine = crispr_pair()
    _execute_share(engine, 2, 3, TickFrame(31))
    assert engine.agents[2].energy == pytest.approx(1.05, abs=1e-9)
    assert engine.agents[2].plasmid_trials[33][2] == pytest.approx(0.35, abs=1e-9)
    events: Counter[str] = Counter()
    engine._evaluate_crispr(50, events)  # pyright: ignore[reportPrivateUsage]
    # Sin descontar lo cedido el balance sería -0.35 < -0.20; con la precisión 125 es 0.
    assert plasmids_of(engine, 2) == (33,)
    assert engine.agents[2].plasmid_trials == {}
    assert events == Counter()


def test_una_presa_no_purga_por_lo_que_le_roban() -> None:
    engine = crispr_pair()
    set_energy(engine, 3, 5.0)  # el atacante es más fuerte: el ataque tiene éxito
    frame = TickFrame(31)
    _execute_attack(engine, 3, 2, frame)
    assert frame.predated == {2}
    assert engine.agents[2].energy == pytest.approx(0.9, abs=1e-9)
    assert engine.agents[2].plasmid_trials[33][2] == pytest.approx(0.5, abs=1e-9)
    events: Counter[str] = Counter()
    engine._evaluate_crispr(50, events)  # pyright: ignore[reportPrivateUsage]
    assert plasmids_of(engine, 2) == (33,)
    assert events == Counter()


def test_lo_recibido_por_share_no_se_descuenta() -> None:
    engine = crispr_pair()
    set_energy(engine, 3, 1.0)
    _execute_share(engine, 3, 2, TickFrame(31))  # el 2 recibe, no cede
    assert engine.agents[2].plasmid_trials[33][2] == 0.0
    assert engine.agents[3].plasmid_trials == {}


def test_una_perdida_metabolica_sigue_purgando() -> None:
    engine = crispr_pair()
    _execute_share(engine, 2, 3, TickFrame(31))  # cede 0.35: balance 0
    set_energy(engine, 2, 0.8)  # y además pierde 0.25 por metabolismo
    events: Counter[str] = Counter()
    engine._evaluate_crispr(50, events)  # pyright: ignore[reportPrivateUsage]
    assert crispr_of(engine, 2) == (33,)
    assert events == Counter({"crispr_purges": 1})


# --- Precisión 126: set_dna en la Fase 5 descarta la decisión ya consumida del tick ---


class DecisionSpy:
    """Registra en `on_decisions` la decisión y el ADN de cada agente y, al final del tick, el
    estado de los que cambiaron de ADN por conjugación en la Fase 5."""

    def __init__(self) -> None:
        self.at_decision: dict[int, tuple[bool, CompactDNA | None]] = {}
        self.receptors: list[tuple[bool, bool, int]] = []

    def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.at_decision = {
            aid: (agent.decision_evaluation(frame.tick) is not None, agent.dna)
            for aid, agent in sorted(engine.agents.items())
        }

    def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
        for aid, (seen, dna) in sorted(self.at_decision.items()):
            agent = engine.agents.get(aid)
            if agent is None or agent.dna is dna:
                continue
            self.receptors.append(
                (seen, agent.decision_evaluation(frame.tick) is None, len(agent.plastic_weights))
            )


def test_la_conjugacion_descarta_la_decision_ya_consumida() -> None:
    config = cfg(
        enable_genetic_policy=True,
        hgt_energy_ratio=0.001,
        num_agents=4,
        max_plasmids=8,
        initial_energy=5.0,
    )
    engine = SimulationEngine(config)
    for aid in sorted(engine.agents):
        put(engine, aid, (5, 5))
    with_plasmids(engine, 0, (21, 22, 23, 24))
    spy = DecisionSpy()
    engine.observers.append(spy)
    engine.run(3)
    assert spy.receptors
    # En `on_decisions` la decisión existía; tras `set_dna` en la Fase 5 queda descartada y los
    # pesos plásticos vacíos (D59.2, precisiones 88 y 94; precisión 126).
    assert all(seen and dropped and weights == 0 for seen, dropped, weights in spy.receptors)
