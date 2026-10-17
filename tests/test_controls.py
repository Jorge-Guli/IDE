"""Tests del control nulo de contenido (`emergence-attribution`)."""

import dataclasses

import numpy as np
import pytest

from ide.domain.types import KnowledgeUnit, Pattern
from ide.simulation.controls import nullify_belief


def test_signo_aleatorio_y_resto_intacto() -> None:
    belief = KnowledgeUnit(Pattern((("id", "p_4"),)), 0.2, 0.7, 3, 12, True)
    rng = np.random.Generator(np.random.PCG64(0))
    results = [nullify_belief(belief, rng) for _ in range(1000)]
    assert {r.predicted_value for r in results} == {1.0, -1.0}
    for r in results:
        assert dataclasses.replace(r, predicted_value=0.2) == belief
    assert sum(r.predicted_value > 0 for r in results) / 1000 == pytest.approx(0.473, abs=1e-9)


def test_una_extraccion_por_llamada() -> None:
    belief = KnowledgeUnit(Pattern((("id", "p_0"),)), -0.5, 0.9, 1, 0, False)
    rng = np.random.Generator(np.random.PCG64(9))
    reference = np.random.Generator(np.random.PCG64(9))
    for _ in range(10):
        draw = reference.random()
        assert nullify_belief(belief, rng).predicted_value == (1.0 if draw < 0.5 else -1.0)
    assert rng.bit_generator.state == reference.bit_generator.state
