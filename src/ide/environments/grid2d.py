"""Grilla 2D toroidal con índice espacial por celda (`spatial-environments`)."""

from dataclasses import replace
from typing import cast

import numpy as np

from ide.config import SimulationConfig
from ide.domain.types import (
    ActionResult,
    ActionType,
    AgentAction,
    Observation,
    Pattern,
    Resource,
    VisibleResource,
)

Cell = tuple[int, int]


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


class ToroidalGrid2D:
    """Entorno sin bordes: los agentes sólo perciben distancia y dirección, nunca coordenadas."""

    MOORE_MOVES: tuple[tuple[int, int], ...] = (
        (-1, -1),
        (0, -1),
        (1, -1),
        (-1, 0),
        (1, 0),
        (-1, 1),
        (0, 1),
        (1, 1),
    )

    def __init__(self, config: SimulationConfig, rng: np.random.Generator) -> None:
        self.config = config
        self._rng = rng
        self._width = config.grid_width
        self._height = config.grid_height
        self.cell_agents: dict[Cell, set[int]] = {}
        self.cell_resources: dict[Cell, dict[int, Resource]] = {}
        for x in range(self._width):
            for y in range(self._height):
                self.cell_agents[(x, y)] = set()
                self.cell_resources[(x, y)] = {}
        self._agent_cell: dict[int, Cell] = {}
        self._resource_cell: dict[int, Cell] = {}
        self._retired: set[Pattern] = set()  # patrones que no se vuelven a reponer
        self._pending: list[Pattern] = []  # patrones de recursos consumidos, en orden de consumo
        self._next_resource_id = 0

        count = config.num_world_patterns
        self._world: dict[Pattern, float] = {}
        for i in range(count):
            pattern = Pattern((("id", f"p_{i}"),))
            self._world[pattern] = 1.0 if i < count // 2 else -1.0
        for agent_id in range(config.num_agents):
            cell = self._random_cell()
            self._agent_cell[agent_id] = cell
            self.cell_agents[cell].add(agent_id)
        for pattern in sorted(self._world):
            for _ in range(config.resources_per_pattern):
                self._spawn(pattern)

    # --- Utilidades internas -------------------------------------------------------------------

    def _random_cell(self) -> Cell:
        return int(self._rng.integers(self._width)), int(self._rng.integers(self._height))

    def _spawn(self, pattern: Pattern) -> None:
        cell = self._random_cell()
        resource = Resource(self._next_resource_id, pattern, self._world[pattern])
        self._next_resource_id += 1
        self.cell_resources[cell][resource.resource_id] = resource
        self._resource_cell[resource.resource_id] = cell

    def _delta(self, origin: Cell, target: Cell) -> tuple[int, int]:
        half_w, half_h = self._width // 2, self._height // 2
        dx = ((target[0] - origin[0] + half_w) % self._width) - half_w
        dy = ((target[1] - origin[1] + half_h) % self._height) - half_h
        return dx, dy

    def _cells_within(self, origin: Cell, radius: int) -> list[Cell]:
        """Celdas a distancia <= radius; la config garantiza 2·radio < lado (sin repetidas)."""
        cells = {
            ((origin[0] + dx) % self._width, (origin[1] + dy) % self._height)
            for dx in range(-radius, radius + 1)
            for dy in range(-radius, radius + 1)
        }
        return sorted(cells)

    def _remove_resource(self, resource_id: int) -> None:
        cell = self._resource_cell.pop(resource_id)
        del self.cell_resources[cell][resource_id]

    # --- EnvironmentPort -----------------------------------------------------------------------

    def get_agent_position(self, agent_id: int) -> Cell:
        """Posición del agente. Sólo para tests y telemetría."""
        return self._agent_cell[agent_id]

    def get_active_agent_ids(self) -> list[int]:
        return sorted(self._agent_cell)

    def get_observation(self, agent_id: int, tick: int) -> Observation:
        origin = self._agent_cell[agent_id]
        visible: list[VisibleResource] = []
        for cell in self._cells_within(origin, self.config.perception_radius):
            dx, dy = self._delta(origin, cell)
            distance = max(abs(dx), abs(dy))
            move = None if distance == 0 else (_sign(dx), _sign(dy))
            for resource in self.cell_resources[cell].values():
                visible.append(
                    VisibleResource(
                        resource.resource_id, resource.pattern, move, distance, distance == 0
                    )
                )
        visible.sort(key=lambda v: (v.distance, v.resource_id))
        return Observation(
            agent_id=agent_id,
            tick=tick,
            visible_resources=tuple(visible),
            available_moves=self.MOORE_MOVES,
            neighbor_ids=tuple(self.get_communication_neighbors(agent_id)),
        )

    def get_communication_neighbors(self, agent_id: int) -> list[int]:
        origin = self._agent_cell[agent_id]
        found: set[int] = set()
        for cell in self._cells_within(origin, self.config.comm_radius):
            found.update(self.cell_agents[cell])
        found.discard(agent_id)
        return sorted(found)

    def execute_action(self, agent_id: int, action: AgentAction, tick: int) -> ActionResult:
        if action.action_type is ActionType.MOVE:
            return self._move(agent_id, action.target)
        if action.action_type is ActionType.INTERACT:
            return self._interact(agent_id, action.target)
        return ActionResult(ActionType.IDLE)

    def _move(self, agent_id: int, move: object) -> ActionResult:
        if not isinstance(move, tuple) or move not in self.MOORE_MOVES:
            return ActionResult(ActionType.IDLE)
        dx, dy = cast(Cell, move)
        x, y = self._agent_cell[agent_id]
        destination = ((x + dx) % self._width, (y + dy) % self._height)
        self.cell_agents[(x, y)].discard(agent_id)
        self.cell_agents[destination].add(agent_id)
        self._agent_cell[agent_id] = destination
        return ActionResult(ActionType.MOVE)

    def _interact(self, agent_id: int, resource_id: object) -> ActionResult:
        cell = self._agent_cell[agent_id]
        resource = None
        if isinstance(resource_id, int | np.integer) and not isinstance(resource_id, bool):
            resource = self.cell_resources[cell].get(cast(int, resource_id))
        if resource is None:
            return ActionResult(ActionType.INTERACT, None, None)
        self._remove_resource(resource.resource_id)
        self._pending.append(resource.pattern)
        return ActionResult(ActionType.INTERACT, resource.pattern, resource.true_value)

    def remove_agents(self, agent_ids: list[int]) -> None:
        for agent_id in agent_ids:
            cell = self._agent_cell.pop(agent_id, None)
            if cell is not None:
                self.cell_agents[cell].discard(agent_id)

    def retire_pattern_resources(self, pattern: Pattern) -> None:
        self._retired.add(pattern)
        self._pending = [p for p in self._pending if p != pattern]
        doomed = sorted(
            rid
            for cell in self.cell_resources.values()
            for rid, r in cell.items()
            if r.pattern == pattern
        )
        for resource_id in doomed:
            self._remove_resource(resource_id)

    def invert_world_rules(self, fraction: float, rng: np.random.Generator) -> list[Pattern]:
        if not 0.0 <= fraction <= 1.0:
            raise ValueError(f"fraction debe estar en [0, 1], recibido {fraction}")
        patterns = sorted(self._world)
        k = round(fraction * len(patterns))
        chosen = cast(
            list[int],
            rng.choice(np.arange(len(patterns)), size=k, replace=False).tolist(),  # pyright: ignore[reportUnknownMemberType]
        )
        flipped = sorted(patterns[i] for i in chosen)
        for pattern in flipped:
            self._world[pattern] = -self._world[pattern]
        for resources in self.cell_resources.values():
            for rid, resource in resources.items():
                if resource.pattern in flipped:
                    resources[rid] = replace(resource, true_value=self._world[resource.pattern])
        return flipped

    def step_dynamics(self, tick: int) -> None:
        pending, self._pending = self._pending, []
        for pattern in pending:
            if pattern not in self._retired:
                self._spawn(pattern)

    def get_world_patterns(self) -> dict[Pattern, float]:
        return {pattern: self._world[pattern] for pattern in sorted(self._world)}

    def get_reachable_true_values(self, agent_id: int) -> dict[int, float]:
        cell = self._agent_cell[agent_id]
        return {rid: r.true_value for rid, r in sorted(self.cell_resources[cell].items())}
