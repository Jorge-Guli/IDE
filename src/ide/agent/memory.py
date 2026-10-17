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

    def __len__(self) -> int:
        return len(self._units)

    def __contains__(self, pattern: Pattern) -> bool:
        return pattern in self._units

    def get(self, pattern: Pattern) -> KnowledgeUnit | None:
        return self._units.get(pattern)

    def all_units(self) -> list[KnowledgeUnit]:
        """Creencias ordenadas por `pattern`, sin depender del orden de inserción."""
        return [self._units[p] for p in sorted(self._units)]

    def compute_utility(self, unit: KnowledgeUnit, current_tick: int) -> float:
        """U(k, t) = c · max(|v̂|, 0.1) · exp(-λ · max(0, t - τ))."""
        age = max(0, current_tick - unit.last_updated_tick)
        relevance = max(abs(unit.predicted_value), _RELEVANCE_FLOOR)
        return unit.confidence * relevance * math.exp(-self._lambda_decay * age)

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

    def remove(self, pattern: Pattern) -> bool:
        return self._units.pop(pattern, None) is not None

    def decay_step(
        self, current_tick: int, passive_decay: float, min_confidence: float
    ) -> list[Pattern]:
        """Olvido pasivo de lo no revalidado; purga lo que queda bajo `min_confidence`."""
        for pattern, unit in self._units.items():
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
