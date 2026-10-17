"""Tests de `roadmap-extensions`: contratos para los Experimentos 002 a 006."""

import numpy as np
import pytest

from ide.domain.extensions import (
    AgentCapabilities,
    AgentHyperParams,
    CompositeRule,
    DefaultEvolutionaryOperator,
    EvolutionaryPort,
    TrustStrategyPort,
    UniformTrustStrategy,
)
from ide.domain.types import KnowledgeUnit, Pattern


def pat(name: str) -> Pattern:
    return Pattern((("id", name),))


def test_estrategia_uniforme_devuelve_gamma_base() -> None:
    assert UniformTrustStrategy().compute_sender_trust(1, 2, 0.75) == 0.75


def test_estrategia_uniforme_cumple_el_puerto() -> None:
    assert isinstance(UniformTrustStrategy(), TrustStrategyPort)
    assert not isinstance(object(), TrustStrategyPort)


def test_capacidades_por_defecto() -> None:
    caps = AgentCapabilities()
    assert (caps.perception_multiplier, caps.memory_bonus, caps.comm_multiplier) == (1.0, 0, 1.0)
    assert caps == AgentCapabilities()


def test_composite_rule_rechaza_menos_de_dos_patrones() -> None:
    with pytest.raises(ValueError):
        CompositeRule((pat("p_0"),), 1.0)
    with pytest.raises(ValueError):
        CompositeRule((), 1.0)


def test_composite_rule_rechaza_patrones_repetidos() -> None:
    with pytest.raises(ValueError):
        CompositeRule((pat("p_0"), pat("p_0")), 1.0)


def test_evaluate_con_diccionario_completo() -> None:
    a, b = pat("p_0"), pat("p_1")
    regla = CompositeRule((a, b), 2.5)
    memoria = {
        a: KnowledgeUnit(a, 1.0, 0.9, 1, 0, True),
        b: KnowledgeUnit(b, 1.0, 0.9, 1, 0, True),
    }
    assert regla.evaluate(memoria) == 2.5


def test_evaluate_con_conjunto_y_fragmento_faltante() -> None:
    a, b = pat("p_0"), pat("p_1")
    regla = CompositeRule((a, b), 2.5)
    assert regla.evaluate({a}) is None
    assert regla.evaluate({a, b, pat("p_2")}) == 2.5
    assert regla.evaluate({}) is None


def test_operador_evolutivo_cumple_el_puerto() -> None:
    assert isinstance(DefaultEvolutionaryOperator(), EvolutionaryPort)


def test_mutacion_acotada_y_reproducible() -> None:
    padre = AgentHyperParams(1.0, 0.0, 0.5)
    op = DefaultEvolutionaryOperator()

    def secuencia() -> list[AgentHyperParams]:
        rng = np.random.Generator(np.random.PCG64(7))
        return [op.reproduce_and_mutate(padre, rng) for _ in range(1000)]

    primera, segunda = secuencia(), secuencia()
    assert primera == segunda
    for h in primera:
        for valor in (h.alpha_learning, h.gamma_social_discount, h.epsilon_explore):
            assert 0.0 <= valor <= 1.0


def test_mutacion_con_desviacion_nula_no_cambia_nada() -> None:
    padre = AgentHyperParams(0.4, 0.75, 0.15)
    rng = np.random.Generator(np.random.PCG64(1))
    assert DefaultEvolutionaryOperator(mutation_std=0.0).reproduce_and_mutate(padre, rng) == padre
