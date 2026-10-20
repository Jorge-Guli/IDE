"""Memoria local acotada de un micro-agente, con reemplazo por utilidad epistémica."""

import math
from dataclasses import replace

from ide.domain.types import KnowledgeUnit, Pattern

_RELEVANCE_FLOOR = 0.1


class BoundedMemory:
    """Almacena a lo sumo `capacity` creencias, una por `Pattern` (C_max << N)."""

    def __init__(self, capacity: int, lambda_decay: float = 0.005) -> None:
        if capacity < 1:
            raise ValueError(f"capacity debe ser >= 1, recibido {capacity}")
        self._capacity = capacity
        self._lambda_decay = lambda_decay
        self._units: dict[Pattern, KnowledgeUnit] = {}
        # Penalización de redundancia ψ_red (R18): por defecto ningún patrón es redundante.
        self._redundant: frozenset[Pattern] = frozenset()
        self._redundancy_penalty = 1.0

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return len(self._units)

    def __contains__(self, pattern: Pattern) -> bool:
        return pattern in self._units

    def get(self, pattern: Pattern) -> KnowledgeUnit | None:
        return self._units.get(pattern)

    def all_units(self) -> list[KnowledgeUnit]:
        """Creencias ordenadas por `pattern`, sin depender del orden de inserción."""
        return [self._units[p] for p in sorted(self._units)]

    def set_redundant_patterns(self, patterns: frozenset[Pattern], penalty: float = 1.0) -> None:
        """Patrones redundantes en el holón (R18); cada llamada reemplaza a la anterior."""
        if not 0.0 < penalty <= 1.0:  # `not` también rechaza NaN
            raise ValueError(f"penalty debe estar en (0, 1], recibido {penalty}")
        self._redundant = patterns
        self._redundancy_penalty = penalty

    def compute_utility(self, unit: KnowledgeUnit, current_tick: int) -> float:
        """U(k, t) = ψ · c · max(|v̂|, 0.1) · exp(-λ · max(0, t - τ)); ψ = 1 si no es redundante."""
        age = max(0, current_tick - unit.last_updated_tick)
        relevance = max(abs(unit.predicted_value), _RELEVANCE_FLOOR)
        utility = unit.confidence * relevance * math.exp(-self._lambda_decay * age)
        if self._redundant and unit.pattern in self._redundant:
            # Se multiplica aparte para que, sin redundancia, U sea bit a bit la de Fase I.
            utility *= self._redundancy_penalty
        return utility

    def upsert(self, unit: KnowledgeUnit, current_tick: int, force: bool = False) -> bool:
        """Inserta o reemplaza una creencia; con la memoria llena compite por utilidad."""
        if unit.pattern in self._units or len(self._units) < self._capacity:
            self._units[unit.pattern] = unit
            return True
        victim = self._weakest(current_tick)
        if not force and self.compute_utility(unit, current_tick) <= self.compute_utility(
            victim, current_tick
        ):
            return False
        del self._units[victim.pattern]
        self._units[unit.pattern] = unit
        return True

    def resize(self, capacity: int, tick: int) -> None:
        """Cambia la capacidad en vida (R24, design D34.3); agrandarla no borra nada.

        Al achicarla desaloja, de a una, la creencia de menor utilidad en `tick`, con el mismo
        criterio y desempate que el desalojo de R2, incluida la penalización de R18. El olvido
        forzado es parte declarada de R24.
        """
        if capacity < 1:
            raise ValueError(f"capacity debe ser >= 1, recibido {capacity}")
        self._capacity = capacity
        while len(self._units) > capacity:
            del self._units[self._weakest(tick).pattern]

    def remove(self, pattern: Pattern) -> bool:
        return self._units.pop(pattern, None) is not None

    def decay_step(
        self, current_tick: int, passive_decay: float, min_confidence: float
    ) -> list[Pattern]:
        """Olvido pasivo de lo no revalidado; purga lo que queda bajo `min_confidence`."""
        for pattern, unit in list(self._units.items()):
            if unit.last_updated_tick < current_tick:
                self._units[pattern] = replace(unit, confidence=unit.confidence - passive_decay)
        purged = sorted(p for p, u in self._units.items() if u.confidence < min_confidence)
        for pattern in purged:
            del self._units[pattern]
        return purged

    def _weakest(self, current_tick: int) -> KnowledgeUnit:
        """Menor utilidad; empates por menor `last_updated_tick` y luego por menor `pattern`."""
        return min(
            self._units.values(),
            key=lambda u: (self.compute_utility(u, current_tick), u.last_updated_tick, u.pattern),
        )
