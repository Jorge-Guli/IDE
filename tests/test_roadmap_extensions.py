"""Tests de `roadmap-extensions`: contratos para los Experimentos 002 a 006."""

import numpy as np
import pytest

from ide.config import SimulationConfig
from ide.domain.extensions import (
    AgentCapabilities,
    AgentHyperParams,
    CompositeRule,
    DefaultEvolutionaryOperator,
    EvolutionaryPort,
    TrustStrategyPort,
    UniformTrustStrategy,
    compute_epistemic_synergy,
    mutate_genome,
)
from ide.domain.types import AgentGenome, KnowledgeUnit, Pattern


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


# --- Fase II: mutate_genome y compute_epistemic_synergy ----------------------------------------


def rng_for(seed: int = 5) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))


def test_mutate_genome_sin_mutacion_devuelve_el_genoma_sin_consumir_rng() -> None:
    cfg = SimulationConfig(mutation_rate=0.0, discrete_mutation_prob=0.0)
    rng = rng_for()
    estado = rng.bit_generator.state
    genome = AgentGenome()
    assert mutate_genome(genome, cfg, rng) is genome
    assert rng.bit_generator.state == estado


def test_mutate_genome_es_determinista_y_devuelve_un_genoma() -> None:
    cfg = SimulationConfig(mutation_rate=0.1, discrete_mutation_prob=0.5)
    a = mutate_genome(AgentGenome(), cfg, rng_for(9))
    b = mutate_genome(AgentGenome(), cfg, rng_for(9))
    assert isinstance(a, AgentGenome)
    assert a == b


def test_mutate_genome_extrae_exactamente_lo_declarado() -> None:
    """4 normales y, por rasgo entero, un `random()` (y un `integers` si salta)."""
    cfg = SimulationConfig(mutation_rate=0.1, discrete_mutation_prob=1.0)
    genome = AgentGenome(
        alpha_learning=0.5,
        gamma_social_discount=0.5,
        epsilon_explore=0.5,
        bond_affinity=0.5,
        memory_capacity=3,
        perception_radius=2,
        comm_radius=2,
    )
    ref = rng_for(3)
    ruido = ref.normal(0.0, 0.1, size=4)
    esperado_enteros: list[int] = []
    for valor in (3, 2, 2):
        ref.random()
        esperado_enteros.append(valor + (1 if int(ref.integers(0, 2)) == 1 else -1))
    mutado = mutate_genome(genome, cfg, rng_for(3))
    assert mutado.alpha_learning == pytest.approx(0.5 + ruido[0], abs=1e-9)
    assert mutado.gamma_social_discount == pytest.approx(0.5 + ruido[1], abs=1e-9)
    assert mutado.epsilon_explore == pytest.approx(0.5 + ruido[2], abs=1e-9)
    assert mutado.bond_affinity == pytest.approx(0.5 + ruido[3], abs=1e-9)
    assert (mutado.memory_capacity, mutado.perception_radius, mutado.comm_radius) == tuple(
        esperado_enteros
    )


def test_mutate_genome_recorta_alfa_a_su_minimo_y_el_resto_a_cero_uno() -> None:
    cfg = SimulationConfig(mutation_rate=1.0, discrete_mutation_prob=0.0)
    for seed in range(30):
        g = mutate_genome(
            AgentGenome(alpha_learning=0.01, gamma_social_discount=0.0, bond_affinity=1.0),
            cfg,
            rng_for(seed),
        )
        assert 0.01 <= g.alpha_learning <= 1.0
        assert 0.0 <= g.gamma_social_discount <= 1.0
        assert 0.0 <= g.epsilon_explore <= 1.0
        assert 0.0 <= g.bond_affinity <= 1.0


def test_mutate_genome_respeta_cotas_enteras() -> None:
    cfg = SimulationConfig(
        mutation_rate=0.0,
        discrete_mutation_prob=1.0,
        memory_capacity=3,
        max_genome_memory_capacity=6,
        num_world_patterns=12,
        grid_width=10,
        grid_height=10,
    )
    for seed in range(40):
        g = mutate_genome(AgentGenome(memory_capacity=1), cfg, rng_for(seed))
        assert 1 <= g.memory_capacity <= 2
        g = mutate_genome(AgentGenome(memory_capacity=6), cfg, rng_for(seed))
        assert 5 <= g.memory_capacity <= 6
        g = mutate_genome(AgentGenome(perception_radius=4, comm_radius=1), cfg, rng_for(seed))
        assert 3 <= g.perception_radius <= 4  # hi = (10 - 1) // 2 = 4
        assert 1 <= g.comm_radius <= 2


def test_mutate_genome_acota_memoria_por_patrones_si_se_impone_la_restriccion() -> None:
    cfg = SimulationConfig(
        mutation_rate=0.0,
        discrete_mutation_prob=1.0,
        memory_capacity=3,
        max_genome_memory_capacity=6,
        num_world_patterns=5,
    )
    for seed in range(40):
        assert (
            mutate_genome(AgentGenome(memory_capacity=4), cfg, rng_for(seed)).memory_capacity <= 4
        )


def test_mutate_genome_radio_cero_pasa_a_uno_y_el_consumo_no_depende_del_valor() -> None:
    cfg = SimulationConfig(mutation_rate=0.0, discrete_mutation_prob=1.0)
    estados = []
    for radio in (1, 4):
        rng = rng_for(2)
        mutate_genome(AgentGenome(perception_radius=radio), cfg, rng)
        estados.append(rng.bit_generator.state)
    assert estados[0] == estados[1]
    g = mutate_genome(AgentGenome(perception_radius=0), cfg, rng_for(2))
    assert g.perception_radius >= 1


def test_sinergia_maxima_entre_conjuntos_disjuntos() -> None:
    a = frozenset({pat("p_0"), pat("p_1")})
    b = frozenset({pat("p_2")})
    assert compute_epistemic_synergy(a, b, 0.8) == pytest.approx(0.8, abs=1e-9)


def test_sinergia_es_jaccard_por_afinidad() -> None:
    a = frozenset({pat("p_0"), pat("p_1")})
    b = frozenset({pat("p_1"), pat("p_2")})
    assert compute_epistemic_synergy(a, b, 0.5) == pytest.approx(2 / 3 * 0.5, abs=1e-9)


def test_sinergia_nula_entre_clones_y_entre_vacios() -> None:
    a = frozenset({pat("p_0")})
    assert compute_epistemic_synergy(a, a, 0.9) == 0.0
    assert compute_epistemic_synergy(frozenset(), frozenset(), 0.9) == 0.0
