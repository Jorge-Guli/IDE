"""Equivalencia exacta de las optimizaciones de rendimiento (Decisión 18).

Las huellas se calcularon con la implementación previa a la optimización (el oráculo claro,
commit 56167b5). Una optimización sólo es válida si reproduce historiales, posiciones y
memorias idénticos. Plataforma de referencia: Linux x86-64, Python 3.13, numpy 2.x. Las huellas
exigen igualdad de bits; si otra plataforma o versión de numpy cambiara un float o la secuencia
del generador, se regeneran ejecutando `run_digest` sobre ese commit, no sobre el código nuevo.
"""

import hashlib
from dataclasses import replace
from typing import cast

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.config import SimulationConfig
from ide.domain.types import Pattern, VisibleResource
from ide.environments.grid2d import ToroidalGrid2D
from ide.simulation.engine import SimulationEngine

BASE = SimulationConfig(seed=42)
CASES = {
    "base": BASE,
    "radios_distintos": replace(BASE, seed=7, perception_radius=1, comm_radius=3),
    "control_nulo": replace(BASE, seed=11, comm_content_null=True),
    "perturbaciones": replace(BASE, seed=5),
    "aislado": replace(BASE, seed=3, comm_enabled=False),
    "inversion": replace(BASE, seed=13),
}
GOLDEN = {
    "base": "2c6da2f3fa74be31cd1e9f368ae4c76f956612006f71dc9f42e60239f3585da0",
    "radios_distintos": "da216e36d4946dafc31ecfccbac7b3ce85b492cacd47124fcf2d26bb1a27bebf",
    "control_nulo": "d987ba6b0bcbe75613a88fa6d8586ee3b1b35803bc758ac3babbc2e1555456ca",
    "perturbaciones": "56d84b0bd31fc184eac3f295fe1371160caaf5f44c4985e425bb9f62963329e4",
    "aislado": "38c16b1ca3f79927e398c1279ddeb3c24acaf875a423a2b829caade2573c3e77",
    "inversion": "fb6ded6b73a86f8d9900aa6a14530ff917a27b1207c0e6265ed4acce18d2ad88",
}
TICKS = 120


def run_digest(name: str) -> str:
    engine = SimulationEngine(CASES[name])
    if name == "perturbaciones":  # ablaciones y rumor a mitad de corrida
        engine.run(TICKS // 2)
        engine.ablate_population(0.3)
        engine.inject_false_belief(Pattern((("id", "p_0"),)), -1.0, 0.95, 0.25)
        engine.ablate_discoverers(Pattern((("id", "p_1"),)))
        engine.run(TICKS // 2)
    elif name == "inversion":  # el signo de los recursos presentes cambia a mitad de corrida
        engine.run(TICKS // 2)
        engine.env.invert_world_rules(0.25, engine.rng)
        engine.run(TICKS // 2)
    else:
        engine.run(TICKS)
    grid = cast(ToroidalGrid2D, engine.env)
    state = (
        engine.history,
        [grid.get_agent_position(a) for a in sorted(engine.agents)],
        [engine.agents[a].memory.all_units() for a in sorted(engine.agents)],
        {p: sorted(ids) for p, ids in sorted(engine.direct_discoverers.items())},
    )
    return hashlib.sha256(repr(state).encode()).hexdigest()


@pytest.mark.parametrize("name", sorted(CASES))
def test_historial_identico_al_oraculo(name: str) -> None:
    assert run_digest(name) == GOLDEN[name]


def reference_cells(
    grid: ToroidalGrid2D, origin: tuple[int, int], radius: int
) -> list[tuple[int, int]]:
    """Cálculo directo, sin precálculo: celdas a distancia de Chebyshev toroidal <= radius."""
    width, height = grid.config.grid_width, grid.config.grid_height
    cells = {
        ((origin[0] + dx) % width, (origin[1] + dy) % height)
        for dx in range(-radius, radius + 1)
        for dy in range(-radius, radius + 1)
    }
    return sorted(cells)


@given(
    width=st.integers(5, 12),
    height=st.integers(5, 12),
    perception=st.integers(0, 2),
    comm=st.integers(0, 2),
    seed=st.integers(0, 1000),
)
def test_vecindad_y_observacion_coinciden_con_el_calculo_directo(
    width: int, height: int, perception: int, comm: int, seed: int
) -> None:
    config = SimulationConfig(
        grid_width=width,
        grid_height=height,
        num_agents=6,
        resources_per_pattern=3,
        perception_radius=perception,
        comm_radius=comm,
        seed=seed,
    )
    grid = ToroidalGrid2D(config, np.random.Generator(np.random.PCG64(seed)))
    for aid in grid.get_active_agent_ids():
        origin = grid.get_agent_position(aid)
        near = {
            a
            for cell in reference_cells(grid, origin, comm)
            for a in grid.cell_agents[cell]
            if a != aid
        }
        assert grid.get_communication_neighbors(aid) == sorted(near)
        obs = grid.get_observation(aid, 0)
        assert obs.neighbor_ids == tuple(sorted(near))
        expected: list[VisibleResource] = []
        for cell in reference_cells(grid, origin, perception):
            dx = ((cell[0] - origin[0] + width // 2) % width) - width // 2
            dy = ((cell[1] - origin[1] + height // 2) % height) - height // 2
            distance = max(abs(dx), abs(dy))
            move = None if distance == 0 else (int(np.sign(dx)), int(np.sign(dy)))
            expected += [
                VisibleResource(r.resource_id, r.pattern, move, distance, distance == 0)
                for r in grid.cell_resources[cell].values()
            ]
        expected.sort(key=lambda v: (v.distance, v.resource_id))
        assert obs.visible_resources == tuple(expected)


def test_movimientos_recomendados_son_de_moore() -> None:
    for radius in range(4):
        for dx, dy, distance, move in ToroidalGrid2D._offsets(radius):  # pyright: ignore[reportPrivateUsage]
            assert distance == max(abs(dx), abs(dy))
            assert move is None if distance == 0 else move in ToroidalGrid2D.MOORE_MOVES
