"""Grilla 2D toroidal con índice espacial por celda (`spatial-environments`)."""

import heapq
import math
from collections import deque
from dataclasses import replace
from typing import cast

import numpy as np

from ide.config import SimulationConfig
from ide.domain.extensions import CompositeRule
from ide.domain.types import (
    CARCASS_PATTERN,
    ActionResult,
    ActionType,
    AgentAction,
    Observation,
    Pattern,
    Resource,
    StigmergicTrace,
    VisibleAgent,
    VisibleResource,
)

Cell = tuple[int, int]


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


class ToroidalGrid2D:
    """Entorno sin bordes: los agentes sólo perciben distancia y dirección, nunca coordenadas.

    Con las reglas ecológicas de la Fase II-B (design D48) apagadas, ubica, consume y repone los
    recursos exactamente como en la Fase II, con la misma secuencia de extracciones de su
    generador. Con $R_{33}$, un recurso elemental consumido se agenda y se repone `delay` ticks
    después; con $R_{34}$, los recursos elementales viven en la franja vertical de su patrón y,
    con estaciones, el retardo de invierno se alarga; con $R_{35}$, el motor deposita cadáveres,
    que no se reponen y se retiran solos tras `carcass_lifetime` ticks.
    """

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
        self._comm_offsets_cache: dict[int, tuple[tuple[int, int], ...]] = {}
        self._composite_rules: dict[Pattern, CompositeRule] = {}
        self._pending_composite: list[Pattern] = []
        self.cell_stigmergy: dict[Cell, dict[Pattern, StigmergicTrace]] = {}
        # R33 (D48.1): agenda de reposición `(due, orden de consumo, patrón)`, como montículo.
        self._depletion = config.enable_resource_depletion
        self._agenda: list[tuple[int, int, Pattern]] = []
        self._consumed = 0  # contador del orden de consumo de la agenda
        # R34 (D48.2): las estaciones sólo actúan con R33 y `season_length > 0`.
        self._seasons = config.enable_heterogeneity and self._depletion and config.season_length > 0
        # R35 (D48.3): `resource_id` de los cadáveres presentes y cola FIFO `(depósito, id)` de
        # todos los depositados: con una vida fija, vencen en el orden en que se depositaron.
        self._carcasses: set[int] = set()
        self._carcass_queue: deque[tuple[int, int]] = deque()
        # Huida de cada desplazamiento `(dx, dy)`: depende sólo de él y del tamaño de la grilla.
        self._flee_cache: dict[tuple[int, int], Cell] = {}
        # Franja propia `(x0, ancho)` de cada patrón elemental con R34; vacío sin la regla.
        self._regions: dict[Pattern, tuple[int, int]] = {}

        count = config.num_world_patterns
        self._world: dict[Pattern, float] = {}
        for i in range(count):
            pattern = Pattern((("id", f"p_{i}"),))
            self._world[pattern] = 1.0 if i < count // 2 else -1.0
        if config.enable_heterogeneity:
            self._regions = self._build_regions(count)
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

    def _random_cell(self, rng: np.random.Generator | None = None) -> Cell:
        rng = self._rng if rng is None else rng
        return int(rng.integers(self._width)), int(rng.integers(self._height))

    def _spawn(self, pattern: Pattern) -> None:
        region = self._regions.get(pattern)
        if region is None:
            cell = self._random_cell()
        else:
            # R34 (D48.2): una celda sorteada dentro de la franja propia del patrón.
            x0, width = region
            cell = x0 + int(self._rng.integers(width)), int(self._rng.integers(self._height))
        self._place_resource(pattern, self._world[pattern], cell)

    def _build_regions(self, count: int) -> dict[Pattern, tuple[int, int]]:
        """Franja propia de cada patrón elemental `p_i`: la de índice `i mod num_regions`.

        La grilla se divide en `num_regions` franjas verticales de ancho
        `grid_width // num_regions`; la última absorbe el resto (D48.2). El índice es el del
        nombre del patrón, no su posición en el orden de `Pattern` (precisión 15).
        """
        regions = self.config.num_regions
        base = self._width // regions
        strips = [
            (k * base, base if k < regions - 1 else self._width - k * base) for k in range(regions)
        ]
        return {Pattern((("id", f"p_{i}"),)): strips[i % regions] for i in range(count)}

    def _regen_delay(self, tick: int) -> int:
        """Retardo de R33 para un recurso consumido en `tick`, con el invierno de R34 (D48.2).

        La estación es la del tick de consumo (precisión 16): en invierno (estación 1) el
        retardo se multiplica por `winter_regen_factor` y se redondea con `floor(x + 0.5)`.
        """
        delay = self.config.resource_regen_delay
        if self._seasons and (tick // self.config.season_length) % 2 == 1:
            return math.floor(delay * self.config.winter_regen_factor + 0.5)
        return delay

    def _place_resource(self, pattern: Pattern, value: float, cell: Cell) -> None:
        resource = Resource(self._next_resource_id, pattern, value)
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
        value = self._composite_rules[pattern].composite_value
        self._place_resource(pattern, value, self._random_cell(self._comp_rng))

    def _offsets_for(self, radius: int) -> tuple[tuple[int, int, int, Cell | None], ...]:
        cached = self._offsets_cache.get(radius)
        if cached is None:
            cached = self._offsets_cache[radius] = self._offsets(radius)
        return cached

    def _comm_offsets_for(self, radius: int) -> tuple[tuple[int, int], ...]:
        cached = self._comm_offsets_cache.get(radius)
        if cached is None:
            cached = tuple((dx, dy) for dx, dy, _, _ in self._offsets_for(radius))
            self._comm_offsets_cache[radius] = cached
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
        if self._carcasses:
            self._carcasses.discard(resource_id)

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
        comm_offsets = self._comm_offsets if radii is None else self._comm_offsets_for(radii[1])
        for dx, dy in comm_offsets:
            found.update(self.cell_agents[((x + dx) % width, (y + dy) % height)])
        found.discard(agent_id)
        return sorted(found)

    def execute_action(self, agent_id: int, action: AgentAction, tick: int) -> ActionResult:
        if action.action_type is ActionType.MOVE:
            return self._move(agent_id, action.target)
        if action.action_type is ActionType.INTERACT:
            return self._interact(agent_id, action.target, tick)
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

    def _interact(self, agent_id: int, resource_id: object, tick: int) -> ActionResult:
        cell = self._agent_cell[agent_id]
        resource = None
        if isinstance(resource_id, int | np.integer) and not isinstance(resource_id, bool):
            resource = self.cell_resources[cell].get(cast(int, resource_id))
        if resource is None:
            return ActionResult(ActionType.INTERACT, None, None)
        carcass = resource.resource_id in self._carcasses  # antes de quitarlo del registro
        self._remove_resource(resource.resource_id)
        if resource.pattern in self._composite_rules:
            self._pending_composite.append(resource.pattern)
        elif carcass:
            pass  # R35: un cadáver no se repone (D48.3)
        elif self._depletion:
            # R33 (D48.1): se repone `delay` ticks después, en orden de (due, consumo).
            due = tick + self._regen_delay(tick)
            heapq.heappush(self._agenda, (due, self._consumed, resource.pattern))
            self._consumed += 1
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
        if any(entry[2] == pattern for entry in self._agenda):
            self._agenda = [entry for entry in self._agenda if entry[2] != pattern]
            heapq.heapify(self._agenda)
        self._pending_composite = [p for p in self._pending_composite if p != pattern]
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
        agenda = self._agenda
        while agenda and agenda[0][0] <= tick:
            pattern = heapq.heappop(agenda)[2]
            if pattern not in self._retired:
                self._spawn(pattern)
        pending_composite, self._pending_composite = self._pending_composite, []
        for pattern in pending_composite:
            if pattern not in self._retired:
                self._spawn_composite(pattern)
        if self._carcass_queue:
            self._retire_carcasses(tick)
        self._decay_stigmergy(tick)

    def _retire_carcasses(self, tick: int) -> None:
        """Retira los cadáveres con `tick >= depósito + carcass_lifetime` (D48.3).

        La cola está en orden de depósito, que es el de vencimiento y, dentro de un tick, el de
        `resource_id`. Los ya comidos se descartan al llegar a la cabeza.
        """
        lifetime, queue = self.config.carcass_lifetime, self._carcass_queue
        while queue and tick >= queue[0][0] + lifetime:
            resource_id = queue.popleft()[1]
            if resource_id in self._carcasses:
                self._remove_resource(resource_id)

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
        perception = (
            self.config.perception_radius if perception_radius is None else perception_radius
        )
        comm = self.config.comm_radius if comm_radius is None else comm_radius
        self._check_radii(perception, comm)
        ax, ay = self._agent_cell[anchor_agent_id]
        offsets = ((0, 0), *self.MOORE_MOVES)
        candidates = [((ax + dx) % self._width, (ay + dy) % self._height) for dx, dy in offsets]
        min_occupation = min(len(self.cell_agents[c]) for c in candidates)
        best = [c for c in candidates if len(self.cell_agents[c]) == min_occupation]
        chosen = best[int(rng.integers(len(best)))]
        self._agent_cell[agent_id] = chosen
        self.cell_agents[chosen].add(agent_id)
        self._store_radii(agent_id, perception, comm)
        return chosen

    def set_agent_radii(self, agent_id: int, perception_radius: int, comm_radius: int) -> None:
        """Fija los radios del agente; si coinciden con los globales no guarda nada."""
        if agent_id not in self._agent_cell:
            raise KeyError(f"el agente {agent_id} no está en el entorno")
        self._check_radii(perception_radius, comm_radius)
        self._store_radii(agent_id, perception_radius, comm_radius)

    def _check_radii(self, perception_radius: int, comm_radius: int) -> None:
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

    def _store_radii(self, agent_id: int, perception_radius: int, comm_radius: int) -> None:
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
        traces = self.cell_stigmergy.get(cell)
        old = None if traces is None else traces.get(pattern)
        if (
            old is not None
            and old.last_updated_tick == tick
            and (old.intensity, old.sign_value) >= (new.intensity, new.sign_value)
        ):
            return
        if new.intensity < self.config.min_confidence:
            # Reemplaza y se purga en el acto (D27): ningún rastro existe bajo el umbral.
            if old is not None and traces is not None:
                del traces[pattern]
                if not traces:
                    del self.cell_stigmergy[cell]
            return
        self.cell_stigmergy.setdefault(cell, {})[pattern] = new

    def get_cell_stigmergy(self, agent_id: int) -> tuple[StigmergicTrace, ...]:
        traces = self.cell_stigmergy.get(self._agent_cell[agent_id], {})
        return tuple(traces[pattern] for pattern in sorted(traces))

    def get_active_stigmergy_cells(self) -> int:
        return len(self.cell_stigmergy)

    def _decay_stigmergy(self, tick: int) -> None:
        # El resultado no depende del orden de recorrido ni consume rng: no hace falta ordenar.
        for cell, traces in list(self.cell_stigmergy.items()):
            for pattern, trace in list(traces.items()):
                if trace.last_updated_tick >= tick:
                    continue
                intensity = trace.intensity - self.config.stigmergy_decay
                if intensity < self.config.min_confidence:
                    del traces[pattern]
                else:
                    traces[pattern] = replace(trace, intensity=intensity)
            if not traces:
                del self.cell_stigmergy[cell]

    # --- EcologicalEnvironmentPort (Fase II-B, D47.2 y D48) --------------------------------------

    def get_visible_agents(self, agent_id: int) -> tuple[VisibleAgent, ...]:
        """Agentes a distancia <= radio de percepción del observador, sin él (D47.2).

        Ordenados por `(distance, agent_id)`, con el movimiento hacia cada uno y el de huida.
        No consume generadores ni expone coordenadas. Los ocupantes de cada celda se recorren
        con `sorted(...)`, como exige la regla de determinismo, aunque el orden final
        `(distance, agent_id)` ya es total.
        """
        x, y = self._agent_cell[agent_id]
        width, height = self._width, self._height
        radii = self._agent_radii.get(agent_id)
        offsets = self._perception_offsets if radii is None else self._offsets_for(radii[0])
        found: list[tuple[int, int, Cell | None, int, int]] = []
        for dx, dy, distance, move in offsets:
            occupants = self.cell_agents[((x + dx) % width, (y + dy) % height)]
            if occupants:
                found.extend(
                    (distance, other, move, dx, dy)
                    for other in sorted(occupants)
                    if other != agent_id
                )
        found.sort(key=lambda entry: (entry[0], entry[1]))
        flee = self._flee_move
        return tuple(
            VisibleAgent(other, distance, move, flee(dx, dy))
            for distance, other, move, dx, dy in found
        )

    def _flee_move(self, dx: int, dy: int) -> Cell:
        """Movimiento de Moore que maximiza la distancia al agente en `(dx, dy)` (D47.1).

        Desempate por el orden de `MOORE_MOVES`: `max` devuelve el primero de los máximos. Se
        calcula una vez por desplazamiento y se memoriza.
        """
        cached = self._flee_cache.get((dx, dy))
        if cached is None:
            cached = self._flee_cache[(dx, dy)] = self._compute_flee_move(dx, dy)
        return cached

    def _compute_flee_move(self, dx: int, dy: int) -> Cell:
        width, height = self._width, self._height

        def distance(move: Cell) -> int:
            ddx, ddy = abs(dx - move[0]) % width, abs(dy - move[1]) % height
            return max(min(ddx, width - ddx), min(ddy, height - ddy))

        return max(self.MOORE_MOVES, key=distance)

    def deposit_carcass(self, agent_id: int, value: float, tick: int) -> None:
        """Coloca en la celda del agente un cadáver de valor `value` (R35, D48.3).

        Lo invoca el motor antes de quitar al agente. El cadáver toma su `resource_id` del
        contador monótono, no se repone y se retira en `step_dynamics` tras `carcass_lifetime`.
        Los depósitos llegan con `tick` no decreciente, como los ticks del motor: así la cola
        de retiro queda en orden de vencimiento (precisión 81).
        """
        queue = self._carcass_queue
        if queue and tick < queue[-1][0]:
            raise ValueError(f"tick de depósito decreciente: {tick} < {queue[-1][0]}")
        resource_id = self._next_resource_id
        self._place_resource(CARCASS_PATTERN, value, self._agent_cell[agent_id])
        self._carcasses.add(resource_id)
        queue.append((tick, resource_id))

    def get_resource_count(self) -> int:
        """Todos los recursos presentes: elementales, compuestos y cadáveres (precisión 18)."""
        return len(self._resource_cell)
