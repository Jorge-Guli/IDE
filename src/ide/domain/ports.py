"""Puerto que desacopla la cognición del agente de la geometría del entorno."""

from typing import Protocol, runtime_checkable

import numpy as np

from ide.domain.types import ActionResult, AgentAction, Observation, Pattern


@runtime_checkable
class EnvironmentPort(Protocol):
    """Contrato que cumple cualquier entorno (grilla, grafo, espacio continuo)."""

    def get_active_agent_ids(self) -> list[int]:
        """Identificadores de los agentes activos, ascendentes."""
        ...

    def get_observation(self, agent_id: int, tick: int) -> Observation: ...

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
