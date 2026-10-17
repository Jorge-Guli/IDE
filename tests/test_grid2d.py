"""Tests de `spatial-environments`: generación, topología, percepción y ciclo de recursos."""

from dataclasses import replace

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.config import SimulationConfig
from ide.domain.ports import EnvironmentPort
from ide.domain.types import ActionResult, ActionType, AgentAction, Pattern, Resource
from ide.environments.grid2d import ToroidalGrid2D

Cell = tuple[int, int]
MOVE = ActionType.MOVE


def pat(i: int) -> Pattern:
    return Pattern((("id", f"p_{i}"),))


def make_config(**overrides: int) -> SimulationConfig:
    base = SimulationConfig(
        grid_width=10, grid_height=10, num_agents=4, num_world_patterns=12, resources_per_pattern=8
    )
    return replace(base, **overrides)


def make_grid(seed: int = 7, **overrides: int) -> ToroidalGrid2D:
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
