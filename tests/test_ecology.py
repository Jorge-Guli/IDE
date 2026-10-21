"""Tests de la ecología del entorno (bloque 11, design D48 y D62.1).

Cubren $R_{33}$ (recursos agotables con agenda de reposición), $R_{34}$ (regiones de nicho y
estaciones), $R_{35}$ (cadáveres: depósito en el paso de muerte, consumo, aprendizaje y retiro),
las consultas nuevas de `EcologicalEnvironmentPort` (`get_visible_agents`, `deposit_carcass` y
`get_resource_count`), los cambios del entorno al empezar el tick (`world_shift_period`) y la
compatibilidad con las Fases I y II con las reglas apagadas.
"""

import copy
import math
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

from ide.agent.holon import CompositeAgent
from ide.config import SimulationConfig
from ide.domain.ports import EcologicalEnvironmentPort, EnvironmentPort, EvolutionaryEnvironmentPort
from ide.domain.types import (
    CARCASS_PATTERN,
    ActionResult,
    ActionType,
    AgentAction,
    Pattern,
    Resource,
)
from ide.environments import grid2d
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
from ide.experiments.metrics import EvolutionaryMetricsCollector
from ide.simulation.engine import SimulationEngine
from ide.simulation.pipeline import build_systems

Cell = tuple[int, int]
ROOT = Path(__file__).resolve().parents[1]
IDLE = AgentAction(ActionType.IDLE)


def pat(i: int) -> Pattern:
    return Pattern((("id", f"p_{i}"),))


def make_config(**overrides: Any) -> SimulationConfig:
    base = SimulationConfig(
        grid_width=10, grid_height=10, num_agents=4, num_world_patterns=12, resources_per_pattern=8
    )
    return replace(base, **overrides)


def make_grid(seed: int = 7, **overrides: Any) -> ToroidalGrid2D:
    return ToroidalGrid2D(make_config(**overrides), np.random.Generator(np.random.PCG64(seed)))


def all_resources(grid: ToroidalGrid2D) -> list[tuple[Cell, Resource]]:
    found = [
        (cell, r)
        for cell in sorted(grid.cell_resources)
        for r in grid.cell_resources[cell].values()
    ]
    return sorted(found, key=lambda item: item[1].resource_id)


def resource_cell(grid: ToroidalGrid2D, resource_id: int) -> Cell:
    for cell, resources in grid.cell_resources.items():
        if resource_id in resources:
            return cell
    raise AssertionError(f"el recurso {resource_id} no está en el tablero")


def walk_to(grid: ToroidalGrid2D, agent_id: int, target: Cell, tick: int = 0) -> None:
    """Lleva al agente a `target` usando sólo `MOVE`, que no consume el generador."""
    width, height = grid.config.grid_width, grid.config.grid_height
    while grid.get_agent_position(agent_id) != target:
        x, y = grid.get_agent_position(agent_id)
        dx = ((target[0] - x + width // 2) % width) - width // 2
        dy = ((target[1] - y + height // 2) % height) - height // 2
        move = (int(np.sign(dx)), int(np.sign(dy)))
        grid.execute_action(agent_id, AgentAction(ActionType.MOVE, move), tick)


def first_of(grid: ToroidalGrid2D, pattern: Pattern) -> Resource:
    return next(r for _, r in all_resources(grid) if r.pattern == pattern)


def consume(grid: ToroidalGrid2D, agent_id: int, resource: Resource, tick: int) -> ActionResult:
    walk_to(grid, agent_id, resource_cell(grid, resource.resource_id), tick)
    return grid.execute_action(
        agent_id, AgentAction(ActionType.INTERACT, resource.resource_id), tick
    )


def count_pattern(grid: ToroidalGrid2D, pattern: Pattern) -> int:
    return sum(1 for _, r in all_resources(grid) if r.pattern == pattern)


def rng_state(grid: ToroidalGrid2D) -> Any:
    return copy.deepcopy(grid._rng.bit_generator.state)  # pyright: ignore[reportPrivateUsage]


def strips(width: int, regions: int) -> list[tuple[int, int]]:
    """`(x0, ancho)` de cada franja vertical de $R_{34}$ (D48.2)."""
    base = width // regions
    return [(k * base, base if k < regions - 1 else width - k * base) for k in range(regions)]


def index_of(pattern: Pattern) -> int:
    """Índice $i$ del nombre `p_i` del patrón (precisión 15)."""
    return int(dict(pattern.attributes)["id"].removeprefix("p_"))


def toroidal(a: Cell, b: Cell, width: int, height: int) -> int:
    dx, dy = abs(a[0] - b[0]) % width, abs(a[1] - b[1]) % height
    return max(min(dx, width - dx), min(dy, height - dy))


# --- (d) Puerto ecológico y consultas ----------------------------------------------------------


def test_la_grilla_cumple_los_tres_puertos() -> None:
    grid = make_grid()
    assert isinstance(grid, EcologicalEnvironmentPort)
    assert isinstance(grid, EvolutionaryEnvironmentPort)
    assert isinstance(grid, EnvironmentPort)


def test_consultas_sin_consumo_de_generadores() -> None:
    grid = make_grid()
    before = rng_state(grid)
    for aid in grid.get_active_agent_ids():
        grid.get_visible_agents(aid)
    grid.get_resource_count()
    grid.deposit_carcass(0, 0.6, 3)
    assert rng_state(grid) == before


def visible_setup(**overrides: Any) -> ToroidalGrid2D:
    """Grilla de 20 × 20 con radio de percepción 2 y los agentes 0 a 9 lejos de `(5, 5)`."""
    grid = make_grid(grid_width=20, grid_height=20, num_agents=10, perception_radius=2, **overrides)
    for aid in grid.get_active_agent_ids():
        walk_to(grid, aid, (15, 15))
    return grid


def test_orden_y_direccion_de_los_agentes_visibles() -> None:
    grid = visible_setup()
    walk_to(grid, 1, (5, 5))
    walk_to(grid, 9, (6, 5))
    walk_to(grid, 3, (5, 7))
    walk_to(grid, 4, (5, 5))
    seen = grid.get_visible_agents(1)
    assert [v.agent_id for v in seen] == [4, 9, 3]
    assert [v.distance for v in seen] == [0, 1, 2]
    assert [v.recommended_move for v in seen] == [None, (1, 0), (0, 1)]


def test_orden_de_los_agentes_visibles_por_distancia_e_id() -> None:
    grid = visible_setup()
    walk_to(grid, 5, (5, 5))
    walk_to(grid, 9, (6, 6))
    walk_to(grid, 3, (4, 5))
    walk_to(grid, 2, (7, 5))
    seen = grid.get_visible_agents(5)
    assert [v.agent_id for v in seen] == [3, 9, 2]
    assert all(v.agent_id != 5 for v in seen)


def test_agente_fuera_del_radio_no_es_visible() -> None:
    grid = visible_setup()
    walk_to(grid, 1, (5, 5))
    walk_to(grid, 2, (8, 5))
    assert all(v.agent_id != 2 for v in grid.get_visible_agents(1))


def test_huida_hacia_el_lado_opuesto() -> None:
    grid = visible_setup()
    walk_to(grid, 1, (5, 5))
    walk_to(grid, 9, (6, 5))
    (entry,) = grid.get_visible_agents(1)
    assert entry.agent_id == 9
    assert entry.flee_move == (-1, -1)


def test_los_agentes_visibles_usan_el_radio_propio_del_observador() -> None:
    grid = visible_setup()
    walk_to(grid, 1, (5, 5))
    walk_to(grid, 2, (8, 5))
    grid.set_agent_radii(1, 3, grid.config.comm_radius)
    assert [v.agent_id for v in grid.get_visible_agents(1)] == [2]
    # El radio del observado no importa: 2 conserva el radio global y no ve a 1.
    assert grid.get_visible_agents(2) == ()


@given(
    seed=st.integers(0, 10_000),
    width=st.integers(5, 12),
    height=st.integers(5, 12),
    radius=st.integers(0, 2),
)
def test_agentes_visibles_iguales_a_la_fuerza_bruta(
    seed: int, width: int, height: int, radius: int
) -> None:
    grid = make_grid(
        seed, grid_width=width, grid_height=height, num_agents=8, perception_radius=radius
    )
    moves = ToroidalGrid2D.MOORE_MOVES
    for aid in grid.get_active_agent_ids():
        me = grid.get_agent_position(aid)
        expected: list[tuple[int, int]] = []
        for other in grid.get_active_agent_ids():
            distance = toroidal(me, grid.get_agent_position(other), width, height)
            if other != aid and distance <= radius:
                expected.append((distance, other))
        seen = grid.get_visible_agents(aid)
        assert [(v.distance, v.agent_id) for v in seen] == sorted(expected)
        for v in seen:
            there = grid.get_agent_position(v.agent_id)
            if v.distance == 0:
                assert v.recommended_move is None
            else:
                assert v.recommended_move in moves
                step = cast(Cell, v.recommended_move)
                closer = ((me[0] + step[0]) % width, (me[1] + step[1]) % height)
                assert toroidal(closer, there, width, height) == v.distance - 1
            flee = [
                toroidal(((me[0] + dx) % width, (me[1] + dy) % height), there, width, height)
                for dx, dy in moves
            ]
            assert v.flee_move == moves[flee.index(max(flee))]


# --- (a) R33: agenda de reposición -------------------------------------------------------------


def test_reposicion_diferida() -> None:
    grid = make_grid(enable_resource_depletion=True, resource_regen_delay=20)
    consume(grid, 0, first_of(grid, pat(3)), tick=10)
    for tick in range(10, 30):
        grid.step_dynamics(tick)
    assert count_pattern(grid, pat(3)) == grid.config.resources_per_pattern - 1
    grid.step_dynamics(30)
    assert count_pattern(grid, pat(3)) == grid.config.resources_per_pattern


def test_la_reposicion_diferida_no_consume_el_generador_antes_de_tiempo() -> None:
    grid = make_grid(enable_resource_depletion=True, resource_regen_delay=20)
    consume(grid, 0, first_of(grid, pat(3)), tick=10)
    before = rng_state(grid)
    for tick in range(10, 30):
        grid.step_dynamics(tick)
    assert rng_state(grid) == before
    grid.step_dynamics(30)
    assert rng_state(grid) != before


def test_orden_de_reposicion() -> None:
    grid = make_grid(enable_resource_depletion=True, resource_regen_delay=20)
    consume(grid, 0, first_of(grid, pat(1)), tick=10)
    consume(grid, 0, first_of(grid, pat(5)), tick=12)
    consume(grid, 1, first_of(grid, pat(2)), tick=12)
    known = {r.resource_id for _, r in all_resources(grid)}
    for tick in range(10, 30):
        grid.step_dynamics(tick)
    assert {r.resource_id for _, r in all_resources(grid)} == known

    def new_ones() -> list[Resource]:
        return [r for _, r in all_resources(grid) if r.resource_id not in known]

    grid.step_dynamics(30)
    assert [r.pattern for r in new_ones()] == [pat(1)]
    grid.step_dynamics(31)
    assert [r.pattern for r in new_ones()] == [pat(1)]
    grid.step_dynamics(32)
    fresh = new_ones()
    assert [r.pattern for r in fresh] == [pat(1), pat(5), pat(2)]
    ids = [r.resource_id for r in fresh]
    assert ids == sorted(ids)


def test_la_agenda_respeta_el_retiro_de_un_patron() -> None:
    grid = make_grid(enable_resource_depletion=True, resource_regen_delay=5)
    consume(grid, 0, first_of(grid, pat(3)), tick=0)
    grid.retire_pattern_resources(pat(3))
    for tick in range(10):
        grid.step_dynamics(tick)
    assert count_pattern(grid, pat(3)) == 0


def test_r33_no_cambia_los_compuestos() -> None:
    config: dict[str, Any] = {
        "num_composite_patterns": 1,
        "composite_resources_per_pattern": 2,
        "composite_order": 2,
    }
    grid = make_grid(enable_resource_depletion=True, resource_regen_delay=20, **config)
    composite = next(r for _, r in all_resources(grid) if dict(r.pattern.attributes)["id"] == "c_0")
    consume(grid, 0, composite, tick=3)
    grid.step_dynamics(3)
    assert count_pattern(grid, composite.pattern) == 2


def test_sin_r33_la_reposicion_es_la_de_la_fase_ii() -> None:
    a = make_grid()
    b = make_grid(resource_regen_delay=7, season_length=10, winter_regen_factor=2.0)
    for grid in (a, b):
        consume(grid, 0, first_of(grid, pat(3)), tick=10)
        grid.step_dynamics(10)
    assert all_resources(a) == all_resources(b)
    assert count_pattern(a, pat(3)) == a.config.resources_per_pattern
    assert rng_state(a) == rng_state(b)


# --- (b) R34: regiones y estaciones ------------------------------------------------------------


def test_franjas_con_resto() -> None:
    grid = make_grid(grid_width=20, grid_height=20, enable_heterogeneity=True, num_regions=3)
    assert strips(20, 3) == [(0, 6), (6, 6), (12, 8)]
    for cell, resource in all_resources(grid):
        if resource.pattern == pat(4) or resource.pattern == pat(10):
            assert 6 <= cell[0] <= 11
    assert count_pattern(grid, pat(10)) == grid.config.resources_per_pattern


@pytest.mark.parametrize("regions", [1, 2, 3, 5])
def test_cada_patron_ocupa_su_region_propia(regions: int) -> None:
    grid = make_grid(grid_width=11, grid_height=10, enable_heterogeneity=True, num_regions=regions)
    bounds = strips(11, regions)
    for cell, resource in all_resources(grid):
        index = index_of(resource.pattern)
        x0, width = bounds[index % regions]
        assert x0 <= cell[0] < x0 + width


@pytest.mark.parametrize("depletion", [False, True])
def test_reposicion_en_la_region_propia(depletion: bool) -> None:
    grid = make_grid(
        grid_width=20,
        grid_height=20,
        enable_heterogeneity=True,
        num_regions=3,
        enable_resource_depletion=depletion,
        resource_regen_delay=1,
    )
    known = {r.resource_id for _, r in all_resources(grid)}
    consume(grid, 0, first_of(grid, pat(2)), tick=0)
    grid.step_dynamics(0)
    grid.step_dynamics(1)
    (fresh,) = [(c, r) for c, r in all_resources(grid) if r.resource_id not in known]
    assert fresh[1].pattern == pat(2)
    assert 12 <= fresh[0][0] <= 19


def test_retardo_de_invierno() -> None:
    grid = make_grid(
        enable_resource_depletion=True,
        enable_heterogeneity=True,
        season_length=100,
        resource_regen_delay=20,
        winter_regen_factor=3.0,
    )
    consume(grid, 0, first_of(grid, pat(3)), tick=190)
    for tick in range(190, 250):
        grid.step_dynamics(tick)
    assert count_pattern(grid, pat(3)) == grid.config.resources_per_pattern - 1
    grid.step_dynamics(250)
    assert count_pattern(grid, pat(3)) == grid.config.resources_per_pattern


def test_retardo_de_verano() -> None:
    grid = make_grid(
        enable_resource_depletion=True,
        enable_heterogeneity=True,
        season_length=100,
        resource_regen_delay=20,
        winter_regen_factor=3.0,
    )
    consume(grid, 0, first_of(grid, pat(3)), tick=250)
    for tick in range(250, 270):
        grid.step_dynamics(tick)
    assert count_pattern(grid, pat(3)) == grid.config.resources_per_pattern - 1
    grid.step_dynamics(270)
    assert count_pattern(grid, pat(3)) == grid.config.resources_per_pattern


def test_el_retardo_de_invierno_redondea_hacia_arriba_las_mitades() -> None:
    # 3 · 1.5 = 4.5 se redondea a 5 con floor(x + 0.5), no a 4 como `round`.
    grid = make_grid(
        enable_resource_depletion=True,
        enable_heterogeneity=True,
        season_length=10,
        resource_regen_delay=3,
        winter_regen_factor=1.5,
    )
    assert math.floor(3 * 1.5 + 0.5) == 5 != round(3 * 1.5)
    consume(grid, 0, first_of(grid, pat(3)), tick=10)
    for tick in range(10, 15):
        grid.step_dynamics(tick)
    assert count_pattern(grid, pat(3)) == grid.config.resources_per_pattern - 1
    grid.step_dynamics(15)
    assert count_pattern(grid, pat(3)) == grid.config.resources_per_pattern


@pytest.mark.parametrize(
    "overrides",
    [
        {"enable_heterogeneity": False, "season_length": 100},
        {"enable_heterogeneity": True, "season_length": 0},
    ],
)
def test_estaciones_inertes(overrides: dict[str, Any]) -> None:
    grid = make_grid(
        enable_resource_depletion=True,
        resource_regen_delay=20,
        winter_regen_factor=3.0,
        **overrides,
    )
    consume(grid, 0, first_of(grid, pat(3)), tick=190)
    for tick in range(190, 211):
        grid.step_dynamics(tick)
    assert count_pattern(grid, pat(3)) == grid.config.resources_per_pattern


def test_estaciones_inertes_sin_r33() -> None:
    a = make_grid(enable_heterogeneity=True)
    b = make_grid(enable_heterogeneity=True, season_length=100, winter_regen_factor=3.0)
    for grid in (a, b):
        consume(grid, 0, first_of(grid, pat(3)), tick=190)
        grid.step_dynamics(190)
    assert all_resources(a) == all_resources(b)


# --- (c) R35 en la grilla ----------------------------------------------------------------------


def test_identificador_del_cadaver() -> None:
    grid = make_grid(resources_per_pattern=10)
    assert grid.get_resource_count() == 120
    grid.deposit_carcass(2, 0.6, 5)
    cell = grid.get_agent_position(2)
    carcass = grid.cell_resources[cell][120]
    assert carcass == Resource(120, CARCASS_PATTERN, 0.6)
    walk_to(grid, 0, cell)
    grid.deposit_carcass(0, 0.6, 5)
    assert 121 in grid.cell_resources[cell]


def test_consumo_del_cadaver() -> None:
    grid = make_grid()
    grid.deposit_carcass(1, 0.6, 4)
    carcass_id = max(r.resource_id for _, r in all_resources(grid))
    walk_to(grid, 0, grid.get_agent_position(1))
    total = grid.get_resource_count()
    result = grid.execute_action(0, AgentAction(ActionType.INTERACT, carcass_id), 4)
    assert result == ActionResult(ActionType.INTERACT, CARCASS_PATTERN, 0.6)
    assert grid.get_resource_count() == total - 1
    for tick in range(4, 100):
        grid.step_dynamics(tick)
    assert count_pattern(grid, CARCASS_PATTERN) == 0
    assert grid.get_resource_count() == total - 1


def test_vida_del_cadaver() -> None:
    grid = make_grid(carcass_lifetime=50)
    grid.deposit_carcass(1, 0.6, 100)
    for tick in range(100, 150):
        grid.step_dynamics(tick)
        assert CARCASS_PATTERN not in grid.get_world_patterns()
    assert count_pattern(grid, CARCASS_PATTERN) == 1
    grid.step_dynamics(150)
    assert count_pattern(grid, CARCASS_PATTERN) == 0
    assert CARCASS_PATTERN not in grid.get_world_patterns()


def test_cadaver_alcanzable_para_m2() -> None:
    grid = make_grid()
    grid.deposit_carcass(2, 0.6, 0)
    carcass_id = max(r.resource_id for _, r in all_resources(grid))
    assert grid.get_reachable_true_values(2)[carcass_id] == 0.6


def test_el_cadaver_es_visible_como_cualquier_recurso() -> None:
    grid = make_grid()
    grid.deposit_carcass(2, 0.6, 0)
    visible = grid.get_observation(2, 0).visible_resources
    assert any(v.pattern == CARCASS_PATTERN and v.is_reachable_now for v in visible)


def test_conteo_tras_un_consumo_diferido() -> None:
    grid = make_grid(enable_resource_depletion=True, resource_regen_delay=20)
    assert grid.get_resource_count() == 96
    consume(grid, 0, first_of(grid, pat(3)), tick=0)
    grid.step_dynamics(0)
    assert grid.get_resource_count() == 95
    grid.deposit_carcass(1, 0.6, 0)
    assert grid.get_resource_count() == 96


def test_el_conteo_incluye_los_compuestos() -> None:
    grid = make_grid(num_composite_patterns=2, composite_resources_per_pattern=3)
    assert grid.get_resource_count() == 96 + 6


@given(
    seed=st.integers(0, 10_000),
    ops=st.lists(st.tuples(st.integers(0, 2), st.integers(0, 3), st.integers(0, 50)), max_size=40),
)
def test_el_indice_de_recursos_sigue_al_estado_con_la_ecologia(
    seed: int, ops: list[tuple[int, int, int]]
) -> None:
    grid = make_grid(
        seed,
        enable_resource_depletion=True,
        resource_regen_delay=3,
        enable_heterogeneity=True,
        num_regions=3,
        season_length=4,
        carcass_lifetime=5,
    )
    bounds = strips(10, 3)
    tick = 0
    for kind, aid, pick in ops:
        if kind == 0:
            resources = all_resources(grid)
            consume(grid, aid, resources[pick % len(resources)][1], tick)
        elif kind == 1:
            grid.deposit_carcass(aid, 0.5, tick)
        else:
            grid.step_dynamics(tick)
            tick += 1
        cells = [
            (c, r) for c in sorted(grid.cell_resources) for r in grid.cell_resources[c].values()
        ]
        assert grid.get_resource_count() == len(cells)
        for cell, resource in cells:
            assert resource_cell(grid, resource.resource_id) == cell
            if resource.pattern != CARCASS_PATTERN:
                index = index_of(resource.pattern)
                x0, width = bounds[index % 3]
                assert x0 <= cell[0] < x0 + width
    for _ in range(10):
        grid.step_dynamics(tick)
        tick += 1
    # Pasada la vida y la agenda, no quedan cadáveres y todos los patrones están completos.
    assert count_pattern(grid, CARCASS_PATTERN) == 0
    assert grid.get_resource_count() == 96


# --- (c) R35 en el motor -----------------------------------------------------------------------


def quiet(**overrides: Any) -> SimulationConfig:
    """Configuración chica con evolución, sin costos energéticos ni reproducción."""
    base = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=14,
        resources_per_pattern=4,
        enable_evolution=True,
        metabolic_base_cost=0.0,
        memory_capacity_cost=0.0,
        sensory_radius_cost=0.0,
        move_cost=0.0,
        message_cost=0.0,
        reproduction_threshold=100.0,
    )
    return replace(base, **overrides)


def grid_of(engine: SimulationEngine) -> ToroidalGrid2D:
    return cast(ToroidalGrid2D, engine.env)


def act(
    monkeypatch: pytest.MonkeyPatch,
    engine: SimulationEngine,
    actions: dict[int, AgentAction] | None = None,
) -> None:
    """Fija la acción de cada agente actual: la de `actions` o `IDLE`."""
    actions = actions or {}
    for aid, agent in engine.agents.items():
        action = actions.get(aid, IDLE)
        monkeypatch.setattr(agent, "decide_action", lambda *_args, a=action: a)


def carcasses(grid: ToroidalGrid2D) -> list[tuple[Cell, Resource]]:
    return [(c, r) for c, r in all_resources(grid) if r.pattern == CARCASS_PATTERN]


def test_cadaver_en_la_celda_del_muerto(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(quiet(enable_carcasses=True, carcass_value=0.6))
    act(monkeypatch, engine)
    engine.run(40)
    grid = grid_of(engine)
    cell = grid.get_agent_position(9)
    deposits: list[tuple[int, float, int]] = []
    original = grid.deposit_carcass

    def spy(agent_id: int, value: float, tick: int) -> None:
        # Se deposita antes de quitar al agente: su celda sigue en el entorno.
        assert agent_id in grid.get_active_agent_ids()
        deposits.append((agent_id, value, tick))
        original(agent_id, value, tick)

    monkeypatch.setattr(grid, "deposit_carcass", spy)
    engine.agents[9].apply_energy_delta(-engine.agents[9].energy)
    engine.step()
    assert deposits == [(9, 0.6, 40)]
    assert [(c, r.true_value) for c, r in carcasses(grid)] == [(cell, 0.6)]
    assert 9 not in grid.get_active_agent_ids()


def test_varios_muertos_en_el_mismo_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(quiet(enable_carcasses=True))
    act(monkeypatch, engine)
    grid = grid_of(engine)
    cells = {aid: grid.get_agent_position(aid) for aid in (5, 12)}
    for aid in (12, 5):
        engine.agents[aid].apply_energy_delta(-engine.agents[aid].energy - 0.1)
    engine.step()
    found = carcasses(grid)
    assert [c for c, _ in found] == [cells[5], cells[12]]
    assert found[0][1].resource_id < found[1][1].resource_id


def test_ablacion_sin_cadaver() -> None:
    engine = SimulationEngine(quiet(enable_carcasses=True))
    grid = grid_of(engine)
    total = grid.get_resource_count()
    engine.ablate_population(0.5)
    engine.ablate_discoverers(pat(0), retire_stimulus=False)
    assert carcasses(grid) == []
    assert grid.get_resource_count() == total


def test_el_patron_del_cadaver_vive_en_el_dominio() -> None:
    # El agente lo necesitará y no puede importar `environments` (precisión 77).
    assert Pattern((("id", "carcass"),)) == CARCASS_PATTERN
    assert "CARCASS_PATTERN" not in vars(grid2d) or grid2d.CARCASS_PATTERN is CARCASS_PATTERN


def test_el_deposito_ocurre_dentro_del_paso_de_muerte() -> None:
    # R35 no agrega un sistema: el cadáver lo deposita el paso de muerte (precisión 78).
    names = [s.name for s in build_systems(quiet(enable_carcasses=True))]
    assert names == [s.name for s in build_systems(quiet())]
    config = replace(quiet(enable_carcasses=True), enable_evolution=False)
    assert [s.name for s in build_systems(config)] == [
        s.name for s in build_systems(replace(quiet(), enable_evolution=False))
    ]


def test_el_deposito_usa_la_lista_de_muertos_del_paso_de_muerte(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = SimulationEngine(quiet(enable_carcasses=True))
    act(monkeypatch, engine)
    grid = grid_of(engine)
    removed: list[list[int]] = []
    deposited: list[int] = []
    original_remove = engine._remove  # pyright: ignore[reportPrivateUsage]
    original_deposit = grid.deposit_carcass

    def spy_remove(dead: list[int], tick: int) -> None:
        removed.append(list(dead))
        original_remove(dead, tick)

    def spy_deposit(agent_id: int, value: float, tick: int) -> None:
        assert not removed  # antes de quitar a ningún muerto
        deposited.append(agent_id)
        original_deposit(agent_id, value, tick)

    monkeypatch.setattr(engine, "_remove", spy_remove)
    monkeypatch.setattr(grid, "deposit_carcass", spy_deposit)
    for aid in (12, 5):
        engine.agents[aid].apply_energy_delta(-engine.agents[aid].energy)
    engine.step()
    assert removed == [[5, 12]]
    assert deposited == [5, 12]


def test_la_retirada_de_cadaveres_es_fifo_y_saltea_los_comidos() -> None:
    grid = make_grid(carcass_lifetime=3)
    grid.deposit_carcass(1, 0.6, 0)
    eaten = max(r.resource_id for _, r in all_resources(grid))
    grid.deposit_carcass(2, 0.6, 1)
    walk_to(grid, 0, grid.get_agent_position(1))
    grid.execute_action(0, AgentAction(ActionType.INTERACT, eaten), 1)
    total = grid.get_resource_count()
    grid.step_dynamics(3)
    assert grid.get_resource_count() == total
    grid.step_dynamics(4)
    assert grid.get_resource_count() == total - 1
    assert count_pattern(grid, CARCASS_PATTERN) == 0


def test_el_deposito_exige_ticks_no_decrecientes() -> None:
    grid = make_grid()
    grid.deposit_carcass(1, 0.6, 5)
    with pytest.raises(ValueError, match="decreciente"):
        grid.deposit_carcass(2, 0.6, 4)


def test_las_metricas_de_la_fase_2_no_ven_el_cadaver(monkeypatch: pytest.MonkeyPatch) -> None:
    # D48.3: M9 no cuenta la creencia sobre el cadáver que aprende un descendiente al comerlo.
    engine = SimulationEngine(quiet(enable_carcasses=True))
    grid = grid_of(engine)
    grid.deposit_carcass(3, 0.6, 0)
    (_, carcass), *_ = carcasses(grid)
    act(monkeypatch, engine, {3: AgentAction(ActionType.INTERACT, carcass.resource_id)})
    engine.step()
    agent = engine.agents[3]
    learned = agent.memory.get(CARCASS_PATTERN)
    assert learned is not None and learned.confidence >= engine.config.decision_conf_threshold
    agent._generation = 1  # pyright: ignore[reportPrivateUsage]  # un descendiente para M9
    world = grid.get_world_patterns()
    collector = EvolutionaryMetricsCollector(engine.config)
    valid = collector._valid(agent)  # pyright: ignore[reportPrivateUsage]
    expected = [
        u.from_direct_experience
        for u in agent.memory.all_units()
        if u.confidence >= engine.config.decision_conf_threshold and u.pattern in world
    ]
    assert valid == expected
    metrics = collector.record_tick(1, {3: agent}, {}, world, 0, 0, 0, 0)
    assert metrics.offspring_social_ratio == pytest.approx(
        (len(expected) - sum(expected)) / len(expected) if expected else 0.0, abs=1e-9
    )


def test_m11_no_cuenta_el_cadaver(monkeypatch: pytest.MonkeyPatch) -> None:
    # D48.3: la ganancia holónica compara creencias válidas sin el cadáver, en el holón y en hojas.
    engine = SimulationEngine(quiet(enable_carcasses=True))
    grid = grid_of(engine)
    grid.deposit_carcass(3, 0.6, 0)
    (_, carcass), *_ = carcasses(grid)
    act(monkeypatch, engine, {3: AgentAction(ActionType.INTERACT, carcass.resource_id)})
    engine.step()
    leaves = (engine.agents[3], engine.agents[4])
    assert leaves[0].memory.get(CARCASS_PATTERN) is not None
    holon = CompositeAgent(-1, cast(Any, leaves), 0, False)
    world = grid.get_world_patterns()
    threshold = engine.config.decision_conf_threshold

    def known(units: Any) -> int:
        return sum(u.confidence >= threshold and u.pattern in world for u in units)

    collective = known(holon.collective_memory().values())
    mean_leaf = sum(known(leaf.memory.all_units()) for leaf in leaves) / len(leaves)
    expected = collective / mean_leaf if mean_leaf > 0 else 1.0
    collector = EvolutionaryMetricsCollector(engine.config)
    agents = {leaf.agent_id: leaf for leaf in leaves}
    metrics = collector.record_tick(1, agents, {-1: holon}, world, 0, 0, 0, 0)
    assert metrics.holonic_coverage_gain == pytest.approx(expected, abs=1e-9)


def test_cadaver_comido(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(quiet(enable_carcasses=True, energy_gain_scale=0.5))
    grid = grid_of(engine)
    grid.deposit_carcass(3, 0.6, 0)
    (_, carcass), *_ = carcasses(grid)
    act(monkeypatch, engine, {3: AgentAction(ActionType.INTERACT, carcass.resource_id)})
    before = engine.agents[3].energy
    engine.step()
    assert engine.agents[3].energy - before == pytest.approx(0.3, abs=1e-9)
    learned = engine.agents[3].memory.get(CARCASS_PATTERN)
    assert learned is not None and learned.from_direct_experience
    assert learned.predicted_value == pytest.approx(0.6, abs=1e-9)
    assert 3 in engine.direct_discoverers[CARCASS_PATTERN]
    assert carcasses(grid) == []


def test_cadaver_comido_deposita_estigmergia(monkeypatch: pytest.MonkeyPatch) -> None:
    config = quiet(enable_carcasses=True, enable_stigmergy=True, stigmergy_deposit_rate=0.5)
    engine = SimulationEngine(config)
    grid = grid_of(engine)
    grid.deposit_carcass(3, 0.6, 0)
    (_, carcass), *_ = carcasses(grid)
    act(monkeypatch, engine, {3: AgentAction(ActionType.INTERACT, carcass.resource_id)})
    engine.step()
    assert CARCASS_PATTERN in [t.pattern for t in grid.get_cell_stigmergy(3)]


def test_eventos_de_los_cadaveres(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(quiet(enable_carcasses=True))
    grid = grid_of(engine)
    grid.deposit_carcass(3, 0.6, 0)
    (_, carcass), *_ = carcasses(grid)
    act(monkeypatch, engine, {3: AgentAction(ActionType.INTERACT, carcass.resource_id)})
    for aid in (5, 12):
        engine.agents[aid].apply_energy_delta(-engine.agents[aid].energy)
    events: list[dict[str, int]] = []

    class Spy:
        def on_decisions(self, engine: SimulationEngine, frame: Any) -> None:
            pass

        def on_tick_end(self, engine: SimulationEngine, frame: Any) -> None:
            events.append(dict(frame.events))

    engine.observers.append(Spy())
    engine.step()
    assert events == [{"carcasses_eaten": 1, "carcasses_deposited": 2}]


def test_la_ecologia_exige_un_entorno_ecologico() -> None:
    class Evolutivo(ToroidalGrid2D):
        """Grilla de la Fase II sin las consultas ecológicas (`None` bloquea el protocolo)."""

        get_visible_agents = None  # pyright: ignore[reportAssignmentType, reportIncompatibleMethodOverride]

    config = quiet(enable_carcasses=True)
    env = Evolutivo(config, np.random.Generator(np.random.PCG64(config.seed)))
    assert isinstance(env, EvolutionaryEnvironmentPort)
    assert not isinstance(env, EcologicalEnvironmentPort)
    with pytest.raises(TypeError, match="EcologicalEnvironmentPort"):
        SimulationEngine(config, env)
    # Sin evolución, R35 es inerte y no exige el puerto ecológico.
    SimulationEngine(replace(config, enable_evolution=False), env)
    # R33 y R34 actúan con o sin evolución, así que siempre lo exigen (precisión 79).
    for flag in ("enable_resource_depletion", "enable_heterogeneity"):
        for evolution in (True, False):
            ecological = replace(quiet(), enable_evolution=evolution, **{flag: True})
            with pytest.raises(TypeError, match="EcologicalEnvironmentPort"):
                SimulationEngine(ecological, env)


# --- (f) Cambios del entorno (D62.1) -----------------------------------------------------------


def shift_engine(
    monkeypatch: pytest.MonkeyPatch, **overrides: Any
) -> tuple[SimulationEngine, list[tuple[int, float, Any]]]:
    engine = SimulationEngine(quiet(**overrides))
    act(monkeypatch, engine)
    grid = grid_of(engine)
    calls: list[tuple[int, float, Any]] = []
    original = grid.invert_world_rules

    def spy(fraction: float, rng: np.random.Generator) -> list[Pattern]:
        calls.append((engine.next_tick, fraction, rng))
        return original(fraction, rng)

    monkeypatch.setattr(grid, "invert_world_rules", spy)
    return engine, calls


def test_cambios_en_los_ticks_multiplos(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, calls = shift_engine(monkeypatch, world_shift_period=1000, world_shift_fraction=0.25)
    for tick in (0, 1, 999, 1000, 1001, 1999, 2000, 2500, 3000):
        engine.next_tick = tick
        engine.step()
    assert [tick for tick, _, _ in calls] == [1000, 2000, 3000]
    assert all(fraction == 0.25 and rng is engine.rng for _, fraction, rng in calls)


def test_sin_cambios_por_defecto(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, calls = shift_engine(monkeypatch)
    engine.run(100)
    assert calls == []
    assert "world_shift" not in [s.name for s in engine.systems]


def test_el_cambio_ocurre_antes_de_la_fase_0() -> None:
    config = quiet(world_shift_period=5, enable_compact_dna=True)
    names = [s.name for s in build_systems(config)]
    assert names[:3] == ["world_shift", "expression", "schedule"]
    names = [s.name for s in build_systems(quiet(world_shift_period=5))]
    assert names[:2] == ["world_shift", "schedule"]


def test_el_cambio_invierte_el_mundo_antes_de_percibir(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, calls = shift_engine(monkeypatch, world_shift_period=3, world_shift_fraction=0.5)
    before = engine.env.get_world_patterns()
    engine.run(3)
    assert calls == []
    seen: list[dict[Pattern, float]] = []
    grid = grid_of(engine)
    original = grid.get_observation

    def spy(agent_id: int, tick: int) -> Any:
        seen.append(grid.get_world_patterns())
        return original(agent_id, tick)

    monkeypatch.setattr(grid, "get_observation", spy)
    engine.step()
    assert [tick for tick, _, _ in calls] == [3]
    flipped = [p for p in sorted(before) if seen[0][p] != before[p]]
    assert len(flipped) == round(0.5 * len(before))
    assert engine.history[-1].tick == 3


def test_el_cambio_consume_solo_el_generador_principal() -> None:
    base = quiet(seed=5)
    a = SimulationEngine(replace(base, world_shift_period=4))
    b = SimulationEngine(base)
    a.run(4)
    b.run(4)
    gens = ("null_rng", "evo_rng", "donor_rng")
    assert all(getattr(a, g).bit_generator.state == getattr(b, g).bit_generator.state for g in gens)
    assert a.rng.bit_generator.state == b.rng.bit_generator.state
    a.step()
    b.step()
    assert a.rng.bit_generator.state != b.rng.bit_generator.state


# --- (e) Compatibilidad con las reglas apagadas ------------------------------------------------


def digest(config: SimulationConfig, ticks: int = 60) -> Any:
    engine = SimulationEngine(config)
    engine.run(ticks)
    grid = grid_of(engine)
    ids = sorted(engine.agents)
    return (
        engine.history,
        [astuple(m) for m in engine.evolutionary_history],
        [grid.get_agent_position(a) for a in ids],
        [engine.agents[a].memory.all_units() for a in ids],
        all_resources(grid),
        [g.bit_generator.state for g in (engine.rng, engine.null_rng, engine.evo_rng)],
        engine.donor_rng.bit_generator.state,
    )


INERT = {
    "resource_regen_delay": 3,
    "num_regions": 2,
    "season_length": 7,
    "winter_regen_factor": 2.5,
    "carcass_value": 0.9,
    "carcass_lifetime": 4,
    "world_shift_fraction": 0.75,
}


@pytest.mark.parametrize("name", ["002a", "003a"])
def test_parametros_ecologicos_inertes_con_las_reglas_apagadas(name: str) -> None:
    config = PHASE2_PROTOCOL_CONFIGS[name]
    assert digest(config) == digest(replace(config, **INERT))


def test_cadaveres_inertes_sin_evolucion() -> None:
    config = replace(SimulationConfig(), num_agents=20, resources_per_pattern=6)
    assert digest(config) == digest(replace(config, enable_carcasses=True, **INERT))


def test_la_ecologia_activa_cambia_la_corrida() -> None:
    config = PHASE2_PROTOCOL_CONFIGS["002a"]
    full = replace(
        config, enable_resource_depletion=True, enable_heterogeneity=True, enable_carcasses=True
    )
    assert digest(config) != digest(full)


def test_ecologia_independiente_del_hash() -> None:
    script = textwrap.dedent(
        """
        from dataclasses import replace
        from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
        from ide.simulation.engine import SimulationEngine

        config = replace(
            PHASE2_PROTOCOL_CONFIGS["003a"], enable_resource_depletion=True,
            resource_regen_delay=5, enable_heterogeneity=True, season_length=7,
            enable_carcasses=True, carcass_lifetime=6, world_shift_period=9,
            enable_stigmergy=True,
        )
        engine = SimulationEngine(config)
        engine.run(30)
        print(engine.history)
        print(engine.evolutionary_history)
        print(sorted(engine.root_nodes), sorted(engine.agents))
        print([engine.agents[a].memory.all_units() for a in sorted(engine.agents)])
        print(sorted(engine.direct_discoverers))
        print(engine.env.get_resource_count(), engine.rng.bit_generator.state)
        """
    )
    outputs = []
    for hash_seed in ("0", "123"):
        # El `src` de este árbol primero: la instalación editable puede apuntar a otro.
        path = os.pathsep.join(filter(None, [str(ROOT / "src"), os.environ.get("PYTHONPATH")]))
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
    assert outputs[0].strip()
