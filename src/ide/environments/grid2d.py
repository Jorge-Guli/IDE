"""Grilla 2D toroidal con índice espacial por celda (`spatial-environments`)."""

from dataclasses import replace
from typing import cast

import numpy as np

from ide.config import SimulationConfig
from ide.domain.extensions import CompositeRule
from ide.domain.types import (
    ActionResult,
    ActionType,
    AgentAction,
    Observation,
    Pattern,
    Resource,
    StigmergicTrace,
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
        # Vecindades del toro precalculadas una sola vez (Decisión 18): son iguales desde
        # cualquier celda salvo traslación, así que basta una tabla de desplazamientos.
        self._perception_offsets = self._offsets(config.perception_radius)
        self._comm_offsets = tuple((dx, dy) for dx, dy, _, _ in self._offsets(config.comm_radius))
        # Radios individuales de la Fase II (D22): vacío en Fase I, sin sobrecosto.
        self._agent_radii: dict[int, tuple[int, int]] = {}
        self._offsets_cache: dict[int, tuple[tuple[int, int, int, Cell | None], ...]] = {}
        self._composite_rules: dict[Pattern, CompositeRule] = {}
        self._pending_composite: list[Pattern] = []
        self.cell_stigmergy: dict[Cell, dict[Pattern, StigmergicTrace]] = {}

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
        if config.num_composite_patterns > 0:
            self._init_composites()

    # --- Utilidades internas -------------------------------------------------------------------

    def _random_cell(self) -> Cell:
        return int(self._rng.integers(self._width)), int(self._rng.integers(self._height))

    def _spawn(self, pattern: Pattern) -> None:
        cell = self._random_cell()
        resource = Resource(self._next_resource_id, pattern, self._world[pattern])
        self._next_resource_id += 1
        self.cell_resources[cell][resource.resource_id] = resource
        self._resource_cell[resource.resource_id] = cell

    def _init_composites(self) -> None:
        """Reglas compuestas cíclicas (D27); su generador propio no toca el `rng` de Fase I."""
        config = self.config
        self._comp_rng = np.random.Generator(
            np.random.PCG64(np.random.SeedSequence(config.seed, spawn_key=(3,)))
        )
        beneficial = [Pattern((("id", f"p_{i}"),)) for i in range(config.num_world_patterns // 2)]
        order = config.composite_order
        value = float(order**config.composite_reward_exponent)
        for k in range(config.num_composite_patterns):
            pattern = Pattern((("id", f"c_{k}"), ("order", str(order))))
            required = tuple(sorted(beneficial[(k + j) % len(beneficial)] for j in range(order)))
            self._composite_rules[pattern] = CompositeRule(required, value)
            for _ in range(config.composite_resources_per_pattern):
                self._spawn_composite(pattern)

    def _spawn_composite(self, pattern: Pattern) -> None:
        cell = (
            int(self._comp_rng.integers(self._width)),
            int(self._comp_rng.integers(self._height)),
        )
        resource = Resource(
            self._next_resource_id, pattern, self._composite_rules[pattern].composite_value
        )
        self._next_resource_id += 1
        self.cell_resources[cell][resource.resource_id] = resource
        self._resource_cell[resource.resource_id] = cell

    def _offsets_for(self, radius: int) -> tuple[tuple[int, int, int, Cell | None], ...]:
        cached = self._offsets_cache.get(radius)
        if cached is None:
            cached = self._offsets_cache[radius] = self._offsets(radius)
        return cached

    @staticmethod
    def _offsets(radius: int) -> tuple[tuple[int, int, int, Cell | None], ...]:
        """`(dx, dy, distance, recommended_move)` de cada celda a distancia <= radius.

        La config garantiza 2·radio < lado, así que no hay celdas repetidas y `(dx, dy)` es el
        desplazamiento toroidal mínimo.
        """
        reach = range(-radius, radius + 1)
        return tuple(
            (dx, dy, max(abs(dx), abs(dy)), None if dx == dy == 0 else (_sign(dx), _sign(dy)))
            for dx in reach
            for dy in reach
        )

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
        x, y = self._agent_cell[agent_id]
        width, height = self._width, self._height
        visible: list[VisibleResource] = []
        radii = self._agent_radii.get(agent_id)
        offsets = self._perception_offsets if radii is None else self._offsets_for(radii[0])
        for dx, dy, distance, move in offsets:
            for resource in self.cell_resources[((x + dx) % width, (y + dy) % height)].values():
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
        x, y = self._agent_cell[agent_id]
        width, height = self._width, self._height
        found: set[int] = set()
        radii = self._agent_radii.get(agent_id)
        comm_offsets = (
            self._comm_offsets
            if radii is None
            else tuple((dx, dy) for dx, dy, _, _ in self._offsets_for(radii[1]))
        )
        for dx, dy in comm_offsets:
            found.update(self.cell_agents[((x + dx) % width, (y + dy) % height)])
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
        if resource.pattern in self._composite_rules:
            self._pending_composite.append(resource.pattern)
        else:
            self._pending.append(resource.pattern)
        return ActionResult(ActionType.INTERACT, resource.pattern, resource.true_value)

    def remove_agents(self, agent_ids: list[int]) -> None:
        for agent_id in agent_ids:
            cell = self._agent_cell.pop(agent_id, None)
            self._agent_radii.pop(agent_id, None)
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
        pending_composite, self._pending_composite = self._pending_composite, []
        for pattern in pending_composite:
            self._spawn_composite(pattern)
        self._decay_stigmergy(tick)

    def get_world_patterns(self) -> dict[Pattern, float]:
        return {pattern: self._world[pattern] for pattern in sorted(self._world)}

    def get_reachable_true_values(self, agent_id: int) -> dict[int, float]:
        cell = self._agent_cell[agent_id]
        return {rid: r.true_value for rid, r in sorted(self.cell_resources[cell].items())}

    # --- EvolutionaryEnvironmentPort (Fase II) -------------------------------------------------

    def spawn_agent_near(
        self,
        agent_id: int,
        anchor_agent_id: int,
        rng: np.random.Generator,
        perception_radius: int | None = None,
        comm_radius: int | None = None,
    ) -> Cell:
        """Ubica al agente en la celda menos ocupada de la vecindad de Moore del ancla (D27)."""
        if agent_id in self._agent_cell:
            raise ValueError(f"el agente {agent_id} ya existe")
        ax, ay = self._agent_cell[anchor_agent_id]
        offsets = ((0, 0), *self.MOORE_MOVES)
        candidates = [((ax + dx) % self._width, (ay + dy) % self._height) for dx, dy in offsets]
        min_occupation = min(len(self.cell_agents[c]) for c in candidates)
        best = [c for c in candidates if len(self.cell_agents[c]) == min_occupation]
        chosen = best[int(rng.integers(len(best)))]
        self._agent_cell[agent_id] = chosen
        self.cell_agents[chosen].add(agent_id)
        self.set_agent_radii(
            agent_id,
            self.config.perception_radius if perception_radius is None else perception_radius,
            self.config.comm_radius if comm_radius is None else comm_radius,
        )
        return chosen

    def set_agent_radii(self, agent_id: int, perception_radius: int, comm_radius: int) -> None:
        """Fija los radios del agente; si coinciden con los globales no guarda nada."""
        side = min(self._width, self._height)
        for name, radius in (
            ("perception_radius", perception_radius),
            ("comm_radius", comm_radius),
        ):
            if radius < 0 or 2 * radius >= side:
                raise ValueError(
                    f"radio {name} fuera de rango: {radius} "
                    f"(se exige 0 <= radio y 2 * radio < {side})"
                )
        if (perception_radius, comm_radius) == (
            self.config.perception_radius,
            self.config.comm_radius,
        ):
            self._agent_radii.pop(agent_id, None)
        else:
            self._agent_radii[agent_id] = (perception_radius, comm_radius)

    def get_agent_distance(self, agent_a: int, agent_b: int) -> int:
        """Distancia de Chebyshev toroidal."""
        ax, ay = self._agent_cell[agent_a]
        bx, by = self._agent_cell[agent_b]
        dx, dy = abs(ax - bx), abs(ay - by)
        return max(min(dx, self._width - dx), min(dy, self._height - dy))

    def get_composite_rules(self) -> dict[Pattern, CompositeRule]:
        return dict(self._composite_rules)

    def deposit_stigmergy(
        self, agent_id: int, pattern: Pattern, value: float, confidence: float, tick: int
    ) -> None:
        """Deposita un rastro en la celda del agente; el resultado no depende del orden (R19)."""
        cell = self._agent_cell[agent_id]
        new = StigmergicTrace(
            pattern,
            float(np.sign(value)),
            min(1.0, self.config.stigmergy_deposit_rate * confidence),
            tick,
        )
        traces = self.cell_stigmergy.setdefault(cell, {})
        old = traces.get(pattern)
        if (
            old is not None
            and old.last_updated_tick == tick
            and (old.intensity, old.sign_value) >= (new.intensity, new.sign_value)
        ):
            return
        traces[pattern] = new

    def get_cell_stigmergy(self, agent_id: int) -> tuple[StigmergicTrace, ...]:
        traces = self.cell_stigmergy.get(self._agent_cell[agent_id], {})
        return tuple(traces[pattern] for pattern in sorted(traces))

    def get_active_stigmergy_cells(self) -> int:
        return len(self.cell_stigmergy)

    def _decay_stigmergy(self, tick: int) -> None:
        for cell in sorted(self.cell_stigmergy):
            traces = self.cell_stigmergy[cell]
            for pattern in sorted(traces):
                trace = traces[pattern]
                if trace.last_updated_tick >= tick:
                    continue
                intensity = trace.intensity - self.config.stigmergy_decay
                if intensity < self.config.min_confidence:
                    del traces[pattern]
                else:
                    traces[pattern] = replace(trace, intensity=intensity)
            if not traces:
                del self.cell_stigmergy[cell]
