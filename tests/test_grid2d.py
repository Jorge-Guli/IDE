"""Tests de `spatial-environments`: generación, topología, percepción y ciclo de recursos."""

from dataclasses import replace
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.config import SimulationConfig
from ide.domain.extensions import CompositeRule
from ide.domain.ports import EnvironmentPort, EvolutionaryEnvironmentPort
from ide.domain.types import ActionResult, ActionType, AgentAction, Pattern, Resource
from ide.environments.grid2d import ToroidalGrid2D

Cell = tuple[int, int]
MOVE = ActionType.MOVE


def pat(i: int) -> Pattern:
    return Pattern((("id", f"p_{i}"),))


def make_config(**overrides: Any) -> SimulationConfig:
    base = SimulationConfig(
        grid_width=10, grid_height=10, num_agents=4, num_world_patterns=12, resources_per_pattern=8
    )
    return replace(base, **overrides)


def make_grid(seed: int = 7, **overrides: Any) -> ToroidalGrid2D:
    config = make_config(**overrides)
    return ToroidalGrid2D(config, np.random.Generator(np.random.PCG64(seed)))


def all_resources(grid: ToroidalGrid2D) -> list[Resource]:
    found = [r for cell in sorted(grid.cell_resources) for r in grid.cell_resources[cell].values()]
    return sorted(found, key=lambda r: r.resource_id)


def resource_cell(grid: ToroidalGrid2D, resource_id: int) -> Cell:
    for cell, resources in grid.cell_resources.items():
        if resource_id in resources:
            return cell
    raise AssertionError(f"el recurso {resource_id} no está en el tablero")


def walk_to(grid: ToroidalGrid2D, agent_id: int, target: Cell, tick: int = 0) -> None:
    """Lleva al agente a `target` usando sólo `MOVE` (la API pública del entorno)."""
    width, height = grid.config.grid_width, grid.config.grid_height
    while grid.get_agent_position(agent_id) != target:
        x, y = grid.get_agent_position(agent_id)
        dx = ((target[0] - x + width // 2) % width) - width // 2
        dy = ((target[1] - y + height // 2) % height) - height // 2
        move = (int(np.sign(dx)), int(np.sign(dy)))
        grid.execute_action(agent_id, AgentAction(MOVE, move), tick)


def consume(grid: ToroidalGrid2D, agent_id: int, resource: Resource, tick: int = 0) -> ActionResult:
    walk_to(grid, agent_id, resource_cell(grid, resource.resource_id), tick)
    return grid.execute_action(
        agent_id, AgentAction(ActionType.INTERACT, resource.resource_id), tick
    )


def count_pattern(grid: ToroidalGrid2D, pattern: Pattern) -> int:
    return sum(1 for r in all_resources(grid) if r.pattern == pattern)


# --- Generación determinista -------------------------------------------------------------------


def test_cumple_el_puerto_de_entorno() -> None:
    assert isinstance(make_grid(), EnvironmentPort)


def test_equilibrio_inicial_de_patrones_y_recursos() -> None:
    grid = make_grid()
    world = grid.get_world_patterns()
    assert list(world) == sorted(pat(i) for i in range(12))  # orden canónico de `Pattern`
    assert [world[pat(i)] for i in range(12)] == [1.0] * 6 + [-1.0] * 6
    resources = all_resources(grid)
    assert len(resources) == 96
    assert [r.resource_id for r in resources] == list(range(96))
    assert [r.pattern for r in resources[:8]] == [pat(0)] * 8
    assert all(r.true_value == world[r.pattern] for r in resources)


def test_get_world_patterns_devuelve_una_copia() -> None:
    grid = make_grid()
    grid.get_world_patterns()[pat(0)] = -1.0
    assert grid.get_world_patterns()[pat(0)] == 1.0


def test_patrones_impares_dan_el_extra_a_los_negativos() -> None:
    world = make_grid(num_world_patterns=5, memory_capacity=2).get_world_patterns()
    assert [world[pat(i)] for i in range(5)] == [1.0, 1.0, -1.0, -1.0, -1.0]


def test_misma_semilla_mismo_tablero() -> None:
    a, b = make_grid(seed=3), make_grid(seed=3)
    ids = a.get_active_agent_ids()
    assert ids == b.get_active_agent_ids() == [0, 1, 2, 3]
    assert [a.get_agent_position(i) for i in ids] == [b.get_agent_position(i) for i in ids]
    assert all_resources(a) == all_resources(b)
    assert {c: set(r) for c, r in a.cell_resources.items()} == {
        c: set(r) for c, r in b.cell_resources.items()
    }


def test_semillas_distintas_dan_tableros_distintos() -> None:
    a, b = make_grid(seed=1), make_grid(seed=2)
    pos_a = [a.get_agent_position(i) for i in a.get_active_agent_ids()]
    pos_b = [b.get_agent_position(i) for i in b.get_active_agent_ids()]
    assert pos_a != pos_b or all_resources(a) != all_resources(b)


# --- Movimiento toroidal -----------------------------------------------------------------------


def test_cruce_simultaneo_de_dos_bordes() -> None:
    grid = make_grid()
    walk_to(grid, 0, (grid.config.grid_width - 1, 0))
    result = grid.execute_action(0, AgentAction(MOVE, (1, -1)), 0)
    assert result == ActionResult(MOVE)
    assert grid.get_agent_position(0) == (0, grid.config.grid_height - 1)


def test_movimiento_invalido_es_idle() -> None:
    grid = make_grid()
    before = grid.get_agent_position(0)
    for target in [(5, 5), (0, 0), (2, 0), None, "N"]:
        result = grid.execute_action(0, AgentAction(MOVE, target), 0)
        assert result == ActionResult(ActionType.IDLE)
    assert grid.get_agent_position(0) == before


def test_idle_no_mueve() -> None:
    grid = make_grid()
    before = grid.get_agent_position(0)
    assert grid.execute_action(0, AgentAction(ActionType.IDLE), 0) == ActionResult(ActionType.IDLE)
    assert grid.get_agent_position(0) == before


# --- Distancia y dirección ---------------------------------------------------------------------


def test_percepcion_a_traves_del_borde() -> None:
    grid = make_grid()
    width = grid.config.grid_width
    target = next(
        r for r in all_resources(grid) if resource_cell(grid, r.resource_id)[0] == width - 2
    )
    _, ry = resource_cell(grid, target.resource_id)
    walk_to(grid, 0, (0, ry))
    obs = grid.get_observation(0, 5)
    seen = {v.resource_id: v for v in obs.visible_resources}
    visible = seen[target.resource_id]
    assert visible.distance == 2
    assert visible.is_reachable_now is False
    assert visible.recommended_move == (-1, 0)


def test_recurso_en_la_misma_celda_es_alcanzable() -> None:
    grid = make_grid()
    resource = all_resources(grid)[0]
    walk_to(grid, 0, resource_cell(grid, resource.resource_id))
    seen = {v.resource_id: v for v in grid.get_observation(0, 0).visible_resources}
    assert seen[resource.resource_id].distance == 0
    assert seen[resource.resource_id].is_reachable_now is True
    assert seen[resource.resource_id].recommended_move is None


def test_recurso_fuera_de_rango_no_aparece() -> None:
    grid = make_grid()
    resource = all_resources(grid)[0]
    rx, ry = resource_cell(grid, resource.resource_id)
    walk_to(grid, 0, ((rx + 3) % 10, ry))
    ids = {v.resource_id for v in grid.get_observation(0, 0).visible_resources}
    assert resource.resource_id not in ids


# --- Observación -------------------------------------------------------------------------------


def toroidal_chebyshev(a: Cell, b: Cell, width: int, height: int) -> int:
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return max(min(dx, width - dx), min(dy, height - dy))


def test_observacion_ordenada_y_filtrada() -> None:
    grid = make_grid(num_agents=6, resources_per_pattern=20)
    for aid in grid.get_active_agent_ids():
        pos = grid.get_agent_position(aid)
        obs = grid.get_observation(aid, 3)
        assert obs.agent_id == aid and obs.tick == 3
        keys = [(v.distance, v.resource_id) for v in obs.visible_resources]
        assert keys == sorted(keys)
        assert all(d <= 2 for d, _ in keys)
        expected = {
            r.resource_id
            for r in all_resources(grid)
            if toroidal_chebyshev(pos, resource_cell(grid, r.resource_id), 10, 10) <= 2
        }
        assert {v.resource_id for v in obs.visible_resources} == expected
        assert obs.available_moves == ToroidalGrid2D.MOORE_MOVES


def test_vecinos_ascendentes_sin_el_propio_agente() -> None:
    grid = make_grid(num_agents=12, comm_radius=3, perception_radius=2)
    for aid in grid.get_active_agent_ids():
        pos = grid.get_agent_position(aid)
        neighbors = grid.get_communication_neighbors(aid)
        assert neighbors == sorted(neighbors) and aid not in neighbors
        expected = [
            other
            for other in grid.get_active_agent_ids()
            if other != aid and toroidal_chebyshev(pos, grid.get_agent_position(other), 10, 10) <= 3
        ]
        assert neighbors == expected
        assert grid.get_observation(aid, 0).neighbor_ids == tuple(expected)


def test_la_observacion_no_expone_el_valor_verdadero() -> None:
    grid = make_grid()
    obs = grid.get_observation(0, 0)
    assert all(not hasattr(v, "true_value") for v in obs.visible_resources)


# --- Índice espacial ---------------------------------------------------------------------------


def test_cell_agents_consistente_tras_mover_y_eliminar() -> None:
    grid = make_grid()
    origin = grid.get_agent_position(0)
    grid.execute_action(0, AgentAction(MOVE, (1, 0)), 0)
    dest = grid.get_agent_position(0)
    assert dest != origin
    assert 0 not in grid.cell_agents[origin] and 0 in grid.cell_agents[dest]
    grid.remove_agents([0])
    assert 0 not in grid.cell_agents[dest]
    assert grid.get_active_agent_ids() == [1, 2, 3]
    assert 0 not in grid.get_observation(1, 1).neighbor_ids
    assert all(0 not in ids for ids in grid.cell_agents.values())


def test_cell_resources_consistente_tras_consumir_y_reponer() -> None:
    grid = make_grid()
    resource = all_resources(grid)[0]
    cell = resource_cell(grid, resource.resource_id)
    consume(grid, 0, resource)
    assert resource.resource_id not in grid.cell_resources[cell]
    grid.step_dynamics(1)
    assert sum(len(c) for c in grid.cell_resources.values()) == 96
    assert all(
        r.resource_id in grid.cell_resources[resource_cell(grid, r.resource_id)]
        for r in all_resources(grid)
    )


# --- Interacción y consumo ---------------------------------------------------------------------


def test_interact_devuelve_el_valor_real_y_retira_el_recurso() -> None:
    grid = make_grid()
    resource = all_resources(grid)[0]
    result = consume(grid, 0, resource)
    assert result == ActionResult(ActionType.INTERACT, resource.pattern, resource.true_value)
    assert resource.resource_id not in {r.resource_id for r in all_resources(grid)}


def test_interact_sobre_recurso_inexistente_o_lejano() -> None:
    grid = make_grid()
    empty = ActionResult(ActionType.INTERACT, None, None)
    assert grid.execute_action(0, AgentAction(ActionType.INTERACT, 10_000), 0) == empty
    pos = grid.get_agent_position(0)
    far = next(r for r in all_resources(grid) if resource_cell(grid, r.resource_id) != pos)
    assert grid.execute_action(0, AgentAction(ActionType.INTERACT, far.resource_id), 0) == empty
    assert far.resource_id in {r.resource_id for r in all_resources(grid)}


def test_dos_agentes_sobre_el_mismo_recurso() -> None:
    grid = make_grid()
    resource = all_resources(grid)[0]
    cell = resource_cell(grid, resource.resource_id)
    walk_to(grid, 0, cell)
    walk_to(grid, 1, cell)
    action = AgentAction(ActionType.INTERACT, resource.resource_id)
    first = grid.execute_action(0, action, 0)
    second = grid.execute_action(1, action, 0)
    assert first == ActionResult(ActionType.INTERACT, resource.pattern, resource.true_value)
    assert second == ActionResult(ActionType.INTERACT, None, None)


def test_oraculo_de_valores_alcanzables() -> None:
    grid = make_grid()
    resource = all_resources(grid)[0]
    cell = resource_cell(grid, resource.resource_id)
    walk_to(grid, 0, cell)
    expected = {r.resource_id: r.true_value for r in grid.cell_resources[cell].values()}
    assert grid.get_reachable_true_values(0) == expected
    assert resource.resource_id in expected
    empty_cell = next(c for c in sorted(grid.cell_resources) if not grid.cell_resources[c])
    walk_to(grid, 0, empty_cell)
    assert grid.get_reachable_true_values(0) == {}


# --- Reposición --------------------------------------------------------------------------------


def test_reposicion_mantiene_la_poblacion_con_ids_nuevos() -> None:
    grid = make_grid()
    resource = next(r for r in all_resources(grid) if r.pattern == pat(3))
    consume(grid, 0, resource)
    assert count_pattern(grid, pat(3)) == 7
    grid.step_dynamics(1)
    assert count_pattern(grid, pat(3)) == 8
    new_ids = {r.resource_id for r in all_resources(grid)} - set(range(96))
    assert len(new_ids) == 1 and min(new_ids) >= 96


def test_ids_de_reposicion_son_monotonos_y_en_orden_de_consumo() -> None:
    grid = make_grid()
    first, second = all_resources(grid)[0], all_resources(grid)[20]
    consume(grid, 0, second)
    consume(grid, 0, first)
    grid.step_dynamics(1)
    created = {r.resource_id: r.pattern for r in all_resources(grid) if r.resource_id >= 96}
    assert created == {96: second.pattern, 97: first.pattern}
    consume(grid, 0, next(r for r in all_resources(grid) if r.resource_id >= 96))
    grid.step_dynamics(2)
    assert max(r.resource_id for r in all_resources(grid)) == 98


def test_step_dynamics_sin_consumo_no_cambia_nada() -> None:
    grid = make_grid()
    before = all_resources(grid)
    grid.step_dynamics(1)
    assert all_resources(grid) == before


def test_la_reposicion_es_reproducible() -> None:
    def run() -> list[tuple[int, Cell]]:
        grid = make_grid(seed=11)
        for rid in (0, 9, 30):
            consume(grid, 0, next(r for r in all_resources(grid) if r.resource_id == rid))
        grid.step_dynamics(1)
        return [(r.resource_id, resource_cell(grid, r.resource_id)) for r in all_resources(grid)]

    assert run() == run()


# --- Retiro de patrones ------------------------------------------------------------------------


def test_retirar_un_patron_elimina_sus_recursos_y_reposiciones() -> None:
    grid = make_grid()
    grid.retire_pattern_resources(pat(0))
    assert count_pattern(grid, pat(0)) == 0
    assert all(pat(0) != r.pattern for r in all_resources(grid))


def test_retiro_descarta_reposiciones_pendientes() -> None:
    grid = make_grid()
    resource = next(r for r in all_resources(grid) if r.pattern == pat(0))
    consume(grid, 0, resource)
    grid.retire_pattern_resources(pat(0))
    grid.step_dynamics(1)
    assert count_pattern(grid, pat(0)) == 0
    assert count_pattern(grid, pat(1)) == 8


def test_patron_retirado_no_reaparece_en_50_ticks() -> None:
    grid = make_grid()
    grid.retire_pattern_resources(pat(0))
    for tick in range(50):
        candidates = all_resources(grid)
        consume(grid, 0, candidates[tick % len(candidates)], tick)
        grid.step_dynamics(tick)
        for aid in grid.get_active_agent_ids():
            obs = grid.get_observation(aid, tick)
            assert all(v.pattern != pat(0) for v in obs.visible_resources)
        assert count_pattern(grid, pat(0)) == 0
    assert pat(0) in grid.get_world_patterns()


# --- Inversión de reglas -----------------------------------------------------------------------


def test_shock_del_50_por_ciento() -> None:
    grid = make_grid()
    before = grid.get_world_patterns()
    flipped = grid.invert_world_rules(0.5, np.random.Generator(np.random.PCG64(5)))
    after = grid.get_world_patterns()
    assert len(flipped) == 6 and flipped == sorted(flipped)
    assert all(after[p] == -before[p] for p in flipped)
    assert all(after[p] == before[p] for p in before if p not in flipped)
    assert all(r.true_value == after[r.pattern] for r in all_resources(grid))


def test_la_inversion_se_aplica_a_recursos_futuros() -> None:
    grid = make_grid()
    flipped = grid.invert_world_rules(1.0, np.random.Generator(np.random.PCG64(5)))
    assert len(flipped) == 12
    consume(grid, 0, all_resources(grid)[0])
    grid.step_dynamics(1)
    world = grid.get_world_patterns()
    assert all(r.true_value == world[r.pattern] for r in all_resources(grid))


def test_la_inversion_es_reproducible_y_respeta_la_fraccion() -> None:
    a = make_grid().invert_world_rules(0.25, np.random.Generator(np.random.PCG64(9)))
    b = make_grid().invert_world_rules(0.25, np.random.Generator(np.random.PCG64(9)))
    assert a == b and len(a) == 3
    assert make_grid().invert_world_rules(0.0, np.random.Generator(np.random.PCG64(9))) == []


# --- Propiedades (Hypothesis) ------------------------------------------------------------------


@given(seed=st.integers(0, 10_000), radius=st.integers(0, 4))
def test_la_vecindad_es_simetrica(seed: int, radius: int) -> None:
    grid = make_grid(seed=seed, num_agents=10, comm_radius=radius)
    ids = grid.get_active_agent_ids()
    neighbors = {i: set(grid.get_communication_neighbors(i)) for i in ids}
    for i in ids:
        for j in neighbors[i]:
            assert i in neighbors[j]


@given(
    seed=st.integers(0, 10_000),
    width=st.integers(5, 13),
    height=st.integers(5, 13),
)
def test_la_distancia_percibida_es_la_toroidal(seed: int, width: int, height: int) -> None:
    grid = make_grid(seed=seed, grid_width=width, grid_height=height, num_agents=2)
    pos = grid.get_agent_position(0)
    for v in grid.get_observation(0, 0).visible_resources:
        cell = resource_cell(grid, v.resource_id)
        assert v.distance == toroidal_chebyshev(pos, cell, width, height)
        assert v.is_reachable_now == (v.distance == 0)


@given(
    seed=st.integers(0, 10_000),
    moves=st.lists(st.sampled_from(ToroidalGrid2D.MOORE_MOVES), max_size=12),
)
def test_ida_y_vuelta_de_movimientos(seed: int, moves: list[Cell]) -> None:
    grid = make_grid(seed=seed, num_agents=1)
    start = grid.get_agent_position(0)
    for m in moves:
        grid.execute_action(0, AgentAction(MOVE, m), 0)
    for m in reversed(moves):
        grid.execute_action(0, AgentAction(MOVE, (-m[0], -m[1])), 0)
    assert grid.get_agent_position(0) == start
    assert 0 in grid.cell_agents[start]


@given(seed=st.integers(0, 10_000), ticks=st.integers(1, 15))
def test_el_indice_espacial_sigue_al_estado(seed: int, ticks: int) -> None:
    grid = make_grid(seed=seed, num_agents=3)
    rng = np.random.Generator(np.random.PCG64(seed))
    for tick in range(ticks):
        for aid in grid.get_active_agent_ids():
            move = ToroidalGrid2D.MOORE_MOVES[int(rng.integers(8))]
            grid.execute_action(aid, AgentAction(MOVE, move), tick)
        resource = all_resources(grid)[int(rng.integers(96))]
        consume(grid, 0, resource, tick)
        grid.step_dynamics(tick)
    for aid in grid.get_active_agent_ids():
        cell = grid.get_agent_position(aid)
        assert [c for c, ids in grid.cell_agents.items() if aid in ids] == [cell]
    assert sum(len(c) for c in grid.cell_resources.values()) == 96
    assert count_pattern(grid, pat(0)) <= 8


# --- Casos límite del contrato -----------------------------------------------------------------


def test_interact_acepta_enteros_de_numpy_y_rechaza_ids_mal_tipados() -> None:
    grid = make_grid()
    resource = all_resources(grid)[1]  # resource_id == 1: `True == 1` no debe consumirlo
    walk_to(grid, 0, resource_cell(grid, 1))
    empty = ActionResult(ActionType.INTERACT, None, None)
    for bad_id in (True, np.bool_(True), 1.0, "1"):
        assert grid.execute_action(0, AgentAction(ActionType.INTERACT, bad_id), 0) == empty
        assert 1 in grid.cell_resources[resource_cell(grid, 1)]
    result = grid.execute_action(0, AgentAction(ActionType.INTERACT, np.int64(1)), 0)
    assert result == ActionResult(ActionType.INTERACT, resource.pattern, resource.true_value)


@pytest.mark.parametrize("fraction", [-0.1, 1.2, float("nan"), float("inf"), -float("inf")])
def test_inversion_con_fraccion_fuera_de_rango(fraction: float) -> None:
    grid = make_grid()
    rng = np.random.Generator(np.random.PCG64(5))
    world, resources = grid.get_world_patterns(), all_resources(grid)
    with pytest.raises(ValueError, match="fraction"):
        grid.invert_world_rules(fraction, rng)
    assert grid.get_world_patterns() == world and all_resources(grid) == resources
    assert rng.random() == np.random.Generator(np.random.PCG64(5)).random()  # no consumió estado


@pytest.mark.parametrize("fraction", [0.0, 1.0])
def test_inversion_acepta_los_bordes_del_rango(fraction: float) -> None:
    flipped = make_grid().invert_world_rules(fraction, np.random.Generator(np.random.PCG64(5)))
    assert len(flipped) == round(fraction * 12)


# --- Fase II: nacimiento espacial, radios individuales y distancia -------------------------------


def evo_rng(seed: int = 7) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed, spawn_key=(2,))))


def place(grid: ToroidalGrid2D, agent_id: int, cell: Cell) -> None:
    walk_to(grid, agent_id, cell)
    assert grid.get_agent_position(agent_id) == cell


def test_cumple_el_subpuerto_evolutivo() -> None:
    assert isinstance(make_grid(), EvolutionaryEnvironmentPort)


def test_spawn_agent_near_elige_la_celda_menos_poblada_y_aplica_radios() -> None:
    grid = make_grid()
    place(grid, 1, (5, 5))
    for other, cell in ((0, (5, 5)), (2, (4, 4)), (3, (6, 6))):
        place(grid, other, cell)
    for resources in grid.cell_resources.values():
        resources.clear()
    grid._resource_cell.clear()  # pyright: ignore[reportPrivateUsage]
    chosen = grid.spawn_agent_near(80, 1, evo_rng(), perception_radius=3, comm_radius=1)
    assert grid.get_agent_position(80) == chosen
    assert 80 in grid.get_active_agent_ids()
    assert grid.get_agent_distance(1, 80) <= 1
    assert chosen not in {(5, 5), (4, 4), (6, 6)}  # hay celdas vacías, se prefieren
    ax, ay = chosen
    target = ((ax + 3) % 10, ay)
    grid.cell_resources[target][999] = Resource(999, pat(0), 1.0)
    grid._resource_cell[999] = target  # pyright: ignore[reportPrivateUsage]
    visibles = grid.get_observation(80, 0).visible_resources
    assert [(v.resource_id, v.distance) for v in visibles] == [(999, 3)]
    # el progenitor conserva el radio global (2): no ve a distancia 3
    assert grid.get_observation(2, 0).visible_resources != visibles


def test_spawn_agent_near_con_todas_las_celdas_ocupadas_elige_entre_las_minimas() -> None:
    grid = make_grid(num_agents=2)
    place(grid, 0, (5, 5))
    anchor_cells = [((5 + dx) % 10, (5 + dy) % 10) for dx, dy in ((0, 0), *grid.MOORE_MOVES)]
    for new_id, cell in enumerate(anchor_cells, start=10):
        grid.cell_agents[cell].add(new_id)
        grid._agent_cell[new_id] = cell  # pyright: ignore[reportPrivateUsage]
    # (5, 5) tiene 2 agentes (0 y 10); las otras 8 celdas tienen 1: gana alguna de las 8
    chosen = grid.spawn_agent_near(99, 0, evo_rng())
    assert chosen != (5, 5)
    assert chosen in anchor_cells


def test_spawn_agent_near_consume_una_sola_extraccion_del_rng_dado() -> None:
    grid = make_grid()
    rng, ref = evo_rng(), evo_rng()
    place(grid, 1, (5, 5))
    best = [
        c
        for c in [((5 + dx) % 10, (5 + dy) % 10) for dx, dy in ((0, 0), *grid.MOORE_MOVES)]
        if len(grid.cell_agents[c])
        == min(
            len(grid.cell_agents[k])
            for k in [((5 + dx) % 10, (5 + dy) % 10) for dx, dy in ((0, 0), *grid.MOORE_MOVES)]
        )
    ]
    chosen = grid.spawn_agent_near(80, 1, rng)
    assert chosen == best[int(ref.integers(len(best)))]
    assert rng.bit_generator.state == ref.bit_generator.state


def test_spawn_agent_near_no_toca_el_rng_del_entorno() -> None:
    grid = make_grid(seed=11)
    ref = make_grid(seed=11)
    grid.spawn_agent_near(80, 1, evo_rng())
    assert grid._rng.bit_generator.state == ref._rng.bit_generator.state  # pyright: ignore[reportPrivateUsage]


def test_spawn_agent_near_con_radios_globales_no_registra_radios_individuales() -> None:
    grid = make_grid()
    grid.spawn_agent_near(80, 1, evo_rng(), perception_radius=2, comm_radius=2)
    assert grid._agent_radii == {}  # pyright: ignore[reportPrivateUsage]


def test_set_agent_radii_cambia_percepcion_y_comunicacion() -> None:
    grid = make_grid()
    place(grid, 0, (5, 5))
    place(grid, 1, (5, 8))
    assert 1 not in grid.get_communication_neighbors(0)  # radio de comunicación global: 2
    grid.set_agent_radii(0, 2, 3)
    assert 1 in grid.get_communication_neighbors(0)
    assert 1 not in grid.get_communication_neighbors(1)  # asimetría: 1 conserva el radio global
    grid.set_agent_radii(0, 2, 2)  # vuelve a los globales
    assert 1 not in grid.get_communication_neighbors(0)


def test_set_agent_radii_rechaza_radios_incompatibles_con_el_toro() -> None:
    grid = make_grid()
    with pytest.raises(ValueError, match="radio"):
        grid.set_agent_radii(0, 5, 1)  # 2 * 5 >= 10
    with pytest.raises(ValueError, match="radio"):
        grid.set_agent_radii(0, 1, -1)


def test_remove_agents_olvida_los_radios_individuales() -> None:
    grid = make_grid()
    grid.set_agent_radii(0, 3, 3)
    grid.remove_agents([0])
    assert 0 not in grid._agent_radii  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [((0, 0), (0, 0), 0), ((0, 0), (1, 1), 1), ((0, 0), (9, 9), 1), ((0, 0), (5, 3), 5)],
)
def test_distancia_de_chebyshev_toroidal(a: Cell, b: Cell, expected: int) -> None:
    grid = make_grid()
    place(grid, 0, a)
    place(grid, 1, b)
    assert grid.get_agent_distance(0, 1) == grid.get_agent_distance(1, 0) == expected


# --- Fase II: recursos compuestos --------------------------------------------------------------


def composite_grid(seed: int = 7, **overrides: Any) -> ToroidalGrid2D:
    return make_grid(
        seed,
        num_composite_patterns=2,
        composite_order=2,
        composite_reward_exponent=1.5,
        **overrides,
    )


def comp_pat(k: int, m: int = 2) -> Pattern:
    return Pattern((("id", f"c_{k}"), ("order", str(m))))


def test_sin_compuestos_no_hay_reglas_ni_se_altera_el_rng_de_fase_i() -> None:
    config = make_config()
    rng, ref = np.random.Generator(np.random.PCG64(7)), np.random.Generator(np.random.PCG64(7))
    grid = ToroidalGrid2D(config, rng)
    assert grid.get_composite_rules() == {}
    # el entorno de Fase I consumió exactamente lo mismo que antes: se compara con el recorrido
    ref_grid = ToroidalGrid2D(config, ref)
    assert rng.bit_generator.state == ref.bit_generator.state
    assert all_resources(grid) == all_resources(ref_grid)


def test_los_compuestos_no_alteran_el_tablero_de_fase_i() -> None:
    plain, comp = make_grid(), composite_grid()
    assert comp._rng.bit_generator.state == plain._rng.bit_generator.state  # pyright: ignore[reportPrivateUsage]
    base = [r for r in all_resources(comp) if r.pattern in plain.get_world_patterns()]
    assert base == all_resources(plain)
    assert [comp.get_agent_position(i) for i in range(4)] == [
        plain.get_agent_position(i) for i in range(4)
    ]


def test_generacion_de_reglas_compuestas_de_orden_m() -> None:
    rules = composite_grid().get_composite_rules()
    assert list(rules) == [comp_pat(0), comp_pat(1)]
    assert rules[comp_pat(0)].required_patterns == (pat(0), pat(1))
    assert rules[comp_pat(1)].required_patterns == (pat(1), pat(2))
    for rule in rules.values():
        assert isinstance(rule, CompositeRule)
        assert rule.composite_value == pytest.approx(2**1.5, abs=1e-9)


def test_los_requeridos_se_eligen_ciclicamente_y_ordenados() -> None:
    grid = make_grid(num_composite_patterns=4, composite_order=3, num_world_patterns=8)
    rules = grid.get_composite_rules()
    # beneficiosos: p_0..p_3 (8 // 2); k=2 -> p_2, p_3, p_0 ordenados
    assert rules[comp_pat(2, 3)].required_patterns == (pat(0), pat(2), pat(3))
    assert rules[comp_pat(3, 3)].required_patterns == (pat(0), pat(1), pat(3))
    assert rules[comp_pat(3, 3)].composite_value == pytest.approx(3**1.5, abs=1e-9)


def test_hay_los_recursos_compuestos_configurados_y_con_ids_nuevos() -> None:
    grid = composite_grid(composite_resources_per_pattern=3)
    comps = [r for r in all_resources(grid) if r.pattern in grid.get_composite_rules()]
    assert len(comps) == 6
    assert sorted(r.resource_id for r in comps) == list(range(96, 102))
    assert all(r.true_value == pytest.approx(2**1.5, abs=1e-9) for r in comps)
    assert set(grid.get_world_patterns()) == {pat(i) for i in range(12)}  # sin compuestos


def test_generacion_compuesta_es_determinista_por_semilla() -> None:
    assert all_resources(composite_grid(seed=5)) == all_resources(composite_grid(seed=5))


def test_consumir_un_compuesto_lo_repone_con_el_generador_dedicado() -> None:
    grid = composite_grid()
    resource = next(r for r in all_resources(grid) if r.pattern == comp_pat(0))
    result = consume(grid, 0, resource)
    assert result.interacted_pattern == comp_pat(0)
    assert result.experienced_value == pytest.approx(2**1.5, abs=1e-9)
    rng_state = grid._rng.bit_generator.state  # pyright: ignore[reportPrivateUsage]
    comp_state = grid._comp_rng.bit_generator.state  # pyright: ignore[reportPrivateUsage]
    assert count_pattern(grid, comp_pat(0)) == 3
    grid.step_dynamics(1)
    assert count_pattern(grid, comp_pat(0)) == 4
    assert grid._rng.bit_generator.state == rng_state  # pyright: ignore[reportPrivateUsage]
    assert grid._comp_rng.bit_generator.state != comp_state  # pyright: ignore[reportPrivateUsage]


def test_reponer_elementales_no_consume_el_generador_compuesto() -> None:
    grid = composite_grid()
    resource = next(r for r in all_resources(grid) if r.pattern == pat(0))
    consume(grid, 0, resource)
    comp_state = grid._comp_rng.bit_generator.state  # pyright: ignore[reportPrivateUsage]
    grid.step_dynamics(1)
    assert grid._comp_rng.bit_generator.state == comp_state  # pyright: ignore[reportPrivateUsage]


# --- Fase II: estigmergia (R19) -----------------------------------------------------------------


def stigmergy_grid(**overrides: Any) -> ToroidalGrid2D:
    defaults: dict[str, Any] = {
        "enable_stigmergy": True,
        "stigmergy_deposit_rate": 1.0,
        "stigmergy_decay": 0.1,
    }
    return make_grid(**{**defaults, **overrides})


def test_deposito_lectura_y_decaimiento_estigmergico() -> None:
    grid = stigmergy_grid()
    place(grid, 0, (3, 3))
    place(grid, 1, (3, 3))
    assert grid.get_cell_stigmergy(1) == ()
    grid.deposit_stigmergy(0, pat(0), 1.0, 0.5, 10)
    (trace,) = grid.get_cell_stigmergy(1)
    assert trace.pattern == pat(0)
    assert trace.sign_value == 1.0
    assert trace.intensity == pytest.approx(0.5, abs=1e-9)
    assert trace.last_updated_tick == 10
    grid.step_dynamics(10)  # mismo tick: no decae
    assert grid.get_cell_stigmergy(1)[0].intensity == pytest.approx(0.5, abs=1e-9)
    grid.step_dynamics(11)
    assert grid.get_cell_stigmergy(1)[0].intensity == pytest.approx(0.4, abs=1e-9)


def test_el_signo_del_rastro_es_el_de_la_experiencia() -> None:
    grid = stigmergy_grid()
    grid.deposit_stigmergy(0, pat(7), -0.8, 0.5, 1)
    assert grid.get_cell_stigmergy(0)[0].sign_value == -1.0


def test_la_intensidad_es_la_tasa_por_la_confianza() -> None:
    grid = stigmergy_grid(stigmergy_deposit_rate=0.5)
    grid.deposit_stigmergy(0, pat(0), 1.0, 0.8, 1)
    assert grid.get_cell_stigmergy(0)[0].intensity == pytest.approx(0.4, abs=1e-9)
    full = stigmergy_grid()
    full.deposit_stigmergy(0, pat(0), 1.0, 1.0, 1)
    assert full.get_cell_stigmergy(0)[0].intensity == 1.0


def test_un_deposito_de_un_tick_posterior_reemplaza_al_anterior() -> None:
    grid = stigmergy_grid()
    grid.deposit_stigmergy(0, pat(0), 1.0, 0.9, 3)
    grid.deposit_stigmergy(0, pat(0), -1.0, 0.2, 4)
    (trace,) = grid.get_cell_stigmergy(0)
    assert (trace.sign_value, trace.last_updated_tick) == (-1.0, 4)
    assert trace.intensity == pytest.approx(0.2, abs=1e-9)


def test_el_deposito_del_mismo_tick_no_depende_del_orden() -> None:
    first = stigmergy_grid()
    second = stigmergy_grid()
    place(first, 0, (3, 3))
    place(first, 1, (3, 3))
    place(second, 0, (3, 3))
    place(second, 1, (3, 3))
    for grid, order in ((first, (0, 1)), (second, (1, 0))):
        for agent, (value, conf) in zip(order, ((1.0, 0.4), (-1.0, 0.7)), strict=True):
            grid.deposit_stigmergy(agent, pat(0), value, conf, 5)
    assert first.get_cell_stigmergy(0) == second.get_cell_stigmergy(0)
    assert first.get_cell_stigmergy(0)[0].intensity == pytest.approx(0.7, abs=1e-9)
    # mismo tick e igual intensidad: gana el mayor signo
    third = stigmergy_grid()
    third.deposit_stigmergy(0, pat(0), -1.0, 0.5, 5)
    third.deposit_stigmergy(0, pat(0), 1.0, 0.5, 5)
    assert third.get_cell_stigmergy(0)[0].sign_value == 1.0


def test_el_rastro_se_purga_bajo_la_confianza_minima_y_se_cuentan_las_celdas() -> None:
    grid = stigmergy_grid(min_confidence=0.05, stigmergy_decay=0.1)
    place(grid, 0, (1, 1))
    place(grid, 1, (8, 8))
    grid.deposit_stigmergy(0, pat(0), 1.0, 0.12, 0)
    grid.deposit_stigmergy(1, pat(1), 1.0, 0.9, 0)
    assert grid.get_active_stigmergy_cells() == 2
    grid.step_dynamics(1)  # 0.12 -> 0.02 < 0.05: se purga
    assert grid.get_active_stigmergy_cells() == 1
    assert grid.get_cell_stigmergy(0) == ()


def test_los_rastros_se_devuelven_en_orden_canonico_de_patron() -> None:
    grid = stigmergy_grid()
    for i in (5, 2, 9):
        grid.deposit_stigmergy(0, pat(i), 1.0, 0.5, 1)
    assert [t.pattern for t in grid.get_cell_stigmergy(0)] == sorted(pat(i) for i in (5, 2, 9))


def test_sin_estigmergia_el_estado_inicial_es_vacio() -> None:
    grid = make_grid()
    assert grid.get_active_stigmergy_cells() == 0
    assert grid.get_cell_stigmergy(0) == ()


# --- Fase II: robustez (revisión) ---------------------------------------------------------------


def test_spawn_agent_near_con_radio_invalido_no_deja_un_agente_a_medias() -> None:
    grid = make_grid()
    with pytest.raises(ValueError, match="radio"):
        grid.spawn_agent_near(80, 1, evo_rng(), perception_radius=5)
    assert 80 not in grid.get_active_agent_ids()
    assert all(80 not in agents for agents in grid.cell_agents.values())
    grid.spawn_agent_near(80, 1, evo_rng(), perception_radius=3)  # el reintento es posible


def test_retirar_un_compuesto_descarta_su_reposicion() -> None:
    grid = composite_grid()
    resource = next(r for r in all_resources(grid) if r.pattern == comp_pat(0))
    consume(grid, 0, resource)
    grid.retire_pattern_resources(comp_pat(0))
    for tick in range(1, 4):
        grid.step_dynamics(tick)
    assert count_pattern(grid, comp_pat(0)) == 0
    assert count_pattern(grid, comp_pat(1)) == 4
