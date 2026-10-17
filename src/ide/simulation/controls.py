"""Controles experimentales del motor (Decisión 13)."""

from dataclasses import replace

import numpy as np

from ide.domain.types import KnowledgeUnit


def nullify_belief(belief: KnowledgeUnit, rng: np.random.Generator) -> KnowledgeUnit:
    """Control nulo E4: reemplaza el valor por `±1.0` al azar y conserva el resto.

    Fijar la magnitud evita filtrar información: una creencia atenuada por refutación tiene
    magnitud menor que una recién adquirida.
    """
    value = 1.0 if rng.random() < 0.5 else -1.0
    return replace(belief, predicted_value=value)
