"""Puerto que desacopla la cognición del agente de la geometría del entorno."""

from typing import Protocol, runtime_checkable

import numpy as np

from ide.domain.extensions import CompositeRule
from ide.domain.types import (
    ActionResult,
    AgentAction,
    Observation,
    Pattern,
    StigmergicTrace,
    VisibleAgent,
)


@runtime_checkable
class EnvironmentPort(Protocol):
    """Contrato que cumple cualquier entorno (grilla, grafo, espacio continuo)."""

    def get_active_agent_ids(self) -> list[int]:
        """Identificadores de los agentes activos, ascendentes."""
        ...

    def get_observation(self, agent_id: int, tick: int) -> Observation:
        """Sin acciones de por medio, `neighbor_ids == tuple(get_communication_neighbors(id))`.

        El motor rutea la fase 2 con esos vecinos (Decisión 18).
        """
        ...

    def get_communication_neighbors(self, agent_id: int) -> list[int]:
        """Vecinos de comunicación, ascendentes y sin `agent_id`."""
        ...

    def execute_action(self, agent_id: int, action: AgentAction, tick: int) -> ActionResult:
        """Un `MOVE` inválido es `IDLE`; un `INTERACT` imposible da `ActionResult(INTERACT)`."""
        ...

    def remove_agents(self, agent_ids: list[int]) -> None: ...

    def retire_pattern_resources(self, pattern: Pattern) -> None: ...

    def invert_world_rules(self, fraction: float, rng: np.random.Generator) -> list[Pattern]: ...

    def step_dynamics(self, tick: int) -> None: ...

    def get_world_patterns(self) -> dict[Pattern, float]:
        """Copia del mapa patrón → valor verdadero, en orden de `Pattern`."""
        ...

    def get_reachable_true_values(self, agent_id: int) -> dict[int, float]:
        """Oráculo exclusivo del motor para la métrica M2; jamás se entrega a un agente."""
        ...


@runtime_checkable
class EvolutionaryEnvironmentPort(EnvironmentPort, Protocol):
    """Sub-puerto de la Fase II: nacimiento espacial, radios individuales y estigmergia."""

    def spawn_agent_near(
        self,
        agent_id: int,
        anchor_agent_id: int,
        rng: np.random.Generator,
        perception_radius: int | None = None,
        comm_radius: int | None = None,
    ) -> tuple[int, int]:
        """Ubica a `agent_id` en la celda menos ocupada de la vecindad de Moore del ancla."""
        ...

    def set_agent_radii(self, agent_id: int, perception_radius: int, comm_radius: int) -> None: ...

    def get_agent_distance(self, agent_a: int, agent_b: int) -> int:
        """Distancia de Chebyshev toroidal."""
        ...

    def get_composite_rules(self) -> dict[Pattern, CompositeRule]: ...

    def deposit_stigmergy(
        self, agent_id: int, pattern: Pattern, value: float, confidence: float, tick: int
    ) -> None: ...

    def get_cell_stigmergy(self, agent_id: int) -> tuple[StigmergicTrace, ...]: ...

    def get_active_stigmergy_cells(self) -> int: ...


@runtime_checkable
class EcologicalEnvironmentPort(EvolutionaryEnvironmentPort, Protocol):
    """Sub-puerto de la Fase II-B: agentes visibles, cadáveres y conteo de recursos (D47.2)."""

    def get_visible_agents(self, agent_id: int) -> tuple[VisibleAgent, ...]:
        """Agentes dentro del radio de percepción, ordenados por `(distance, agent_id)`, sin él."""
        ...

    def deposit_carcass(self, agent_id: int, value: float, tick: int) -> None: ...

    def get_resource_count(self) -> int:
        """Todos los recursos presentes en el tablero, incluidos compuestos y cadáveres."""
        ...
