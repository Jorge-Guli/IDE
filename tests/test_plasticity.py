"""Tests de la plasticidad en vida (bloque 14, R40).

Cubren el modo 3 plástico sólo sobre destinos de conducta e inerte en el fenotipo, con
`AST_PIPE` mudado al destino reservado `0x3F` (D59.1, D61); el rasgo `plasticity_rate` del destino
`0x0F` con base 0 (D59.3); la recompensa de la Fase 4, los codones elegibles y la actualización
acotada (D59.4); el ciclo de vida de `plastic_weights` (D59.2); el caché único de la evaluación
con los pesos sumados después (D59.5, precisiones 57 y 88), y la inercia sin $R_{40}$ (D59.6),
además del determinismo entre procesos con distinto `PYTHONHASHSEED` con un ADN que aprende.
"""

import dataclasses
import os
import subprocess
import sys
import textwrap
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.dna import (
    BEHAVIOR_TARGETS,
    behavior_terms,
    encode_codon,
    evaluate_behavior,
    founder_dna,
    phenotype_from_genome,
    plasticity_active,
    transcribe_phenotype,
)
from ide.agent.evolution import genome_from_config
from ide.agent.micro_agent import MicroAgent
from ide.agent.policy import GeneticPolicy
from ide.config import SimulationConfig
from ide.domain.types import (
    ActionResult,
    ActionType,
    AgentAction,
    Behavior,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    Observation,
    Pattern,
    SensorySignals,
)
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
from ide.simulation.engine import SimulationEngine
from ide.simulation.pipeline import (
    BaseSystem,
    ExecutionSystem,
    ScheduleSystem,
    TickFrame,
    build_systems,
)

ROOT = Path(__file__).resolve().parents[1]
CONSUME, EXPLORE, NAVIGATE, WANDER, SHARE, ATTACK, FLEE, SPORULATE = BEHAVIOR_TARGETS
SET_STATE, CLEAR_STATE, SIGNAL, AST_PIPE, PLASTICITY = 0x0D, 0x0E, 0x48, 0x3F, 0x0F
PLASTIC = 3
FOUNDER_TRAITS = tuple(encode_codon(0x00, t) for t in range(9))
NO_PLASTIC: tuple[tuple[int, ...], ...] = ((),) * 8
IDLE = AgentAction(ActionType.IDLE)
CTX0 = EpigeneticContext()
SIGNAL_FIELDS = tuple(f.name for f in dataclasses.fields(SensorySignals))


def config_with(**overrides: Any) -> SimulationConfig:
    """Configuración con $R_{32}$ y $R_{40}$ efectivamente activas, salvo que se indique."""
    params: dict[str, Any] = {
        "enable_evolution": True,
        "enable_compact_dna": True,
        "enable_genetic_policy": True,
        "enable_plasticity": True,
    }
    params.update(overrides)
    return SimulationConfig(**params)


R40 = config_with()
NO_R40 = config_with(enable_plasticity=False)
NO_R32 = config_with(enable_genetic_policy=False)
ALL_AMPLIFICATION = config_with(enable_internal_state=True, enable_signals=True)


def signals(**true_fields: bool) -> SensorySignals:
    values = {name: False for name in SIGNAL_FIELDS}
    values.update(true_fields)
    return SensorySignals(**values)


def all_signals(value: bool) -> SensorySignals:
    return SensorySignals(**{name: value for name in SIGNAL_FIELDS})


def dna_of(*codons: int, plasmids: tuple[int, ...] = ()) -> CompactDNA:
    return CompactDNA(chromosome=tuple(codons), plasmids=plasmids)


def plastic(target: int, payload: int, promoter: int = 0x00) -> int:
    return encode_codon(promoter, target, PLASTIC, 0, payload)


def behave(
    *codons: int,
    config: SimulationConfig = R40,
    sig: SensorySignals | None = None,
    weights: dict[int, float] | None = None,
    plasmids: tuple[int, ...] = (),
) -> Any:
    return evaluate_behavior(
        dna_of(*codons, plasmids=plasmids),
        CTX0,
        sig or signals(),
        config,
        plastic_weights=weights,
    )


# --- (a) modo 3 plástico sobre las conductas, inerte en el fenotipo (D59.1, D61) ----------------


def test_codon_plastico_con_peso_aprendido() -> None:
    codon = plastic(WANDER, 32)  # delta = 0.25
    without = behave(codon)
    learned = behave(codon, weights={0: 0.5})
    assert without.drives[3] == pytest.approx(0.25, abs=1e-9)
    assert learned.drives[3] == pytest.approx(0.75, abs=1e-9)
    assert without.plastic[3] == (0,) and learned.plastic[3] == (0,)
    assert all(learned.plastic[b] == () for b in range(8) if b != 3)


def test_modo_3_inerte_sin_r40() -> None:
    evaluation = behave(plastic(WANDER, 32), config=NO_R40, weights={0: 0.5})
    assert evaluation.drives[3] == 0.0
    assert evaluation.plastic == NO_PLASTIC


def test_modo_3_inerte_sin_r32() -> None:
    evaluation = behave(plastic(WANDER, 32), config=NO_R32, weights={0: 0.5})
    assert evaluation.drives[3] == 0.0
    assert evaluation.plastic == NO_PLASTIC


def test_plasticity_active_es_r32_mas_la_bandera() -> None:
    assert plasticity_active(R40)
    assert not plasticity_active(NO_R40)
    assert not plasticity_active(NO_R32)
    assert not plasticity_active(SimulationConfig(enable_plasticity=True))


def test_plasticity_active_exige_la_evolucion() -> None:
    """La validación del ADN ya exige la evolución; la condición la exige igual (precisión 95)."""
    config = config_with()
    object.__setattr__(config, "enable_evolution", False)  # salta la validación a propósito
    assert not plasticity_active(config)


def test_terminos_sin_codones_plasticos_no_guardan_la_acumulacion() -> None:
    plain = behavior_terms(dna_of(encode_codon(0x00, WANDER, 0, 0, 64)), CTX0, signals(), R40)
    assert plain.additive == plain.repressor == plain.multiplier == ()
    learning = behavior_terms(dna_of(plastic(WANDER, 32)), CTX0, signals(), R40)
    assert len(learning.additive) == len(learning.repressor) == len(learning.multiplier) == 8


def test_combinacion_de_los_cuatro_modos_en_un_impulso() -> None:
    """d_B = mu * rho * (S_B + sum w_i): el peso se suma a la parte aditiva (precisión 57)."""
    codons = (
        encode_codon(0x00, SHARE, 0, 0, 64),  # aditivo 0.5
        plastic(SHARE, 32),  # plástico 0.25 (posición 1)
        encode_codon(0x00, SHARE, 1, 0, -64),  # represor: rho = 0.5
        encode_codon(0x00, SHARE, 2, 0, 64),  # multiplicativo: mu = 1.5
    )
    evaluation = behave(*codons, weights={1: 0.5})
    assert evaluation.drives[4] == pytest.approx(1.5 * 0.5 * (0.5 + 0.25 + 0.5), abs=1e-9)
    assert evaluation.plastic[4] == (1,)


def test_peso_que_vuelve_negativo_el_impulso() -> None:
    evaluation = behave(plastic(ATTACK, 32), weights={0: -1.0})
    assert evaluation.drives[5] == pytest.approx(-0.75, abs=1e-9)


@pytest.mark.parametrize(
    "target", [0x00, 0x07, PLASTICITY, SET_STATE, CLEAR_STATE, SIGNAL, AST_PIPE]
)
def test_modo_3_inerte_fuera_de_las_conductas(target: int) -> None:
    config = ALL_AMPLIFICATION
    founder = founder_dna(config)
    dna = CompactDNA(chromosome=(*founder.chromosome, plastic(target, 127)))
    weights = {len(founder.chromosome): 1.0}
    reference = evaluate_behavior(founder, CTX0, all_signals(True), config, state=0xFF)
    evaluation = evaluate_behavior(
        dna, CTX0, all_signals(True), config, state=0xFF, plastic_weights=weights
    )
    assert evaluation == reference
    assert transcribe_phenotype(dna, CTX0, config) == transcribe_phenotype(founder, CTX0, config)


def test_modo_3_inerte_en_el_fenotipo_sobre_una_conducta() -> None:
    config = R40
    founder = founder_dna(config)
    dna = CompactDNA(chromosome=(*founder.chromosome, plastic(CONSUME, 127)))
    assert transcribe_phenotype(dna, CTX0, config) == transcribe_phenotype(founder, CTX0, config)


def test_ast_pipe_mudado_a_0x3f_inerte() -> None:
    """`AST_PIPE` (Fase IV) es el destino reservado `0x3F`, inerte en los cuatro modos."""
    config = ALL_AMPLIFICATION
    for mode in range(4):
        evaluation = behave(
            encode_codon(0x00, AST_PIPE, mode, 0, 127), config=config, weights={0: 1.0}
        )
        assert evaluation.drives == (0.0,) * 8 and evaluation.plastic == NO_PLASTIC


def test_indices_plasticos_en_cromosoma_mas_plasmidos() -> None:
    evaluation = behave(
        encode_codon(0x00, CONSUME, 0, 0, 64),
        plastic(CONSUME, 16),
        plastic(FLEE, 16),
        plasmids=(plastic(CONSUME, 8),),
    )
    assert evaluation.plastic[0] == (1, 3)
    assert evaluation.plastic[6] == (2,)


def test_solo_cuentan_los_codones_plasticos_activos() -> None:
    codons = (plastic(CONSUME, 32, promoter=0x23), plastic(CONSUME, 16))  # 0x23: vecino adyacente
    on = behave(*codons, sig=signals(neighbor_adjacent=True), weights={0: 0.5, 1: 0.25})
    off = behave(*codons, sig=signals(), weights={0: 0.5, 1: 0.25})
    assert on.plastic[0] == (0, 1) and off.plastic[0] == (1,)
    assert on.drives[0] == pytest.approx(0.25 + 0.125 + 0.5 + 0.25, abs=1e-9)
    assert off.drives[0] == pytest.approx(0.125 + 0.25, abs=1e-9)


def test_pesos_de_posiciones_no_plasticas_se_ignoran() -> None:
    codons = (encode_codon(0x00, WANDER, 0, 0, 64),)
    assert behave(*codons, weights={0: 1.0, 7: -1.0}) == behave(*codons)


def test_el_fundador_no_tiene_codones_plasticos() -> None:
    config = ALL_AMPLIFICATION
    evaluation = evaluate_behavior(
        founder_dna(config), CTX0, all_signals(True), config, plastic_weights={0: 1.0}
    )
    assert evaluation.plastic == NO_PLASTIC
    assert evaluation.drives == pytest.approx((0.9921875, 0.75, 0.5, 0.25, 0, 0, 0, 0), abs=1e-9)


# --- (b) rasgo plasticity_rate (D59.3) ---------------------------------------------------------


def founder_traits_config(**overrides: Any) -> SimulationConfig:
    return config_with(enable_genetic_policy=False, **overrides)


def test_codon_sobre_la_tasa_de_plasticidad() -> None:
    config = founder_traits_config()
    founder = founder_dna(config).chromosome
    up = CompactDNA(chromosome=(*founder, encode_codon(0x00, PLASTICITY, 0, 0, 64)))
    down = CompactDNA(chromosome=(*founder, encode_codon(0x00, PLASTICITY, 0, 0, -64)))
    assert transcribe_phenotype(up, CTX0, config).plasticity_rate == pytest.approx(0.30, abs=1e-9)
    assert transcribe_phenotype(down, CTX0, config).plasticity_rate == 0.0


def test_tasa_de_plasticidad_en_el_conteo() -> None:
    config = founder_traits_config()
    dna = CompactDNA(
        chromosome=(*founder_dna(config).chromosome, encode_codon(0x00, PLASTICITY, 0, 0, 64))
    )
    assert transcribe_phenotype(dna, CTX0, config).expressed_codons == 10


def test_tasa_de_plasticidad_acotada_arriba() -> None:
    config = founder_traits_config(plasticity_rate_base=0.9)
    dna = CompactDNA(
        chromosome=(*founder_dna(config).chromosome, encode_codon(0x00, PLASTICITY, 0, 0, 127))
    )
    assert transcribe_phenotype(dna, CTX0, config).plasticity_rate == 1.0


def test_tasa_de_plasticidad_con_los_tres_modos() -> None:
    config = founder_traits_config(plasticity_rate_base=0.2)
    dna = CompactDNA(
        chromosome=(
            *founder_dna(config).chromosome,
            encode_codon(0x00, PLASTICITY, 0, 0, 64),
            encode_codon(0x00, PLASTICITY, 1, 0, -64),
            encode_codon(0x00, PLASTICITY, 2, 0, 64),
            encode_codon(0x00, PLASTICITY, 3, 0, 127),
        )
    )
    phenotype = transcribe_phenotype(dna, CTX0, config)
    assert phenotype.plasticity_rate == pytest.approx(0.2 * 1.5 + 0.6 * 0.5 * 0.5, abs=1e-9)


def test_tasa_condicionada_por_el_estres() -> None:
    config = founder_traits_config()
    dna = CompactDNA(
        chromosome=(*founder_dna(config).chromosome, encode_codon(0x18, PLASTICITY, 0, 0, 64))
    )
    stressed = EpigeneticContext(0, EpigeneticRole.NONE, 0.0)
    relaxed = EpigeneticContext(0, EpigeneticRole.NONE, 1.0)
    assert transcribe_phenotype(dna, stressed, config).plasticity_rate == pytest.approx(0.3)
    assert transcribe_phenotype(dna, relaxed, config).plasticity_rate == 0.0


@pytest.mark.parametrize("genetic", [False, True])
@pytest.mark.parametrize("base", [0.0, 0.4])
def test_el_fundador_expresa_la_base(genetic: bool, base: float) -> None:
    config = config_with(enable_genetic_policy=genetic, plasticity_rate_base=base)
    for ctx in (CTX0, EpigeneticContext(0, EpigeneticRole.NONE, 0.0)):
        assert transcribe_phenotype(founder_dna(config), ctx, config).plasticity_rate == base


def test_base_por_defecto_cero() -> None:
    config = config_with()
    assert MicroAgent(1, config).phenotype.plasticity_rate == 0.0


def test_phenotype_from_genome_usa_la_base() -> None:
    config = SimulationConfig(plasticity_rate_base=0.1)
    phenotype = phenotype_from_genome(genome_from_config(config), config)
    assert phenotype.plasticity_rate == 0.1


# --- (c) regla de aprendizaje del agente (D59.4) -----------------------------------------------


def agent_with(*codons: int, config: SimulationConfig = R40) -> MicroAgent:
    agent = MicroAgent(1, config, policy=GeneticPolicy())
    agent.set_dna(CompactDNA(chromosome=(*FOUNDER_TRAITS, *codons)))
    agent.express(CTX0, 0)
    return agent


def set_weights(agent: MicroAgent, weights: dict[int, float]) -> None:
    """Fija los pesos en el orden por posición que mantiene el agente."""
    agent._plastic_weights = dict(sorted(weights.items()))  # pyright: ignore[reportPrivateUsage]


def decided(agent: MicroAgent, behavior: Behavior, tick: int = 0) -> None:
    """Registra la decisión del tick y la conducta elegida, como la política genética."""
    agent.evaluate_for_decision(signals(), tick)
    agent.record_behavior(list(Behavior).index(behavior), tick)


def learner(rate: float = 0.5, config: SimulationConfig | None = None) -> MicroAgent:
    """Agente con codones plásticos en las posiciones 9 (`FLEE`), 11 (`CONSUME`) y 12 (`CONSUME`).

    Las posiciones son las de `chromosome + plasmids`, después de los nueve rasgos fundadores.
    """
    base = config or config_with(plasticity_rate_base=rate)
    return agent_with(
        plastic(FLEE, 16),
        encode_codon(0x00, CONSUME, 0, 0, 64),
        plastic(CONSUME, 16),
        plastic(CONSUME, 8),
        config=base,
    )


def test_refuerzo_acotado() -> None:
    agent = learner()
    set_weights(agent, {11: 0.9, 9: 0.2})
    decided(agent, Behavior.CONSUME)
    agent.reinforce(0, 0.4)
    assert agent.plastic_weights == {9: 0.2, 11: 1.0, 12: pytest.approx(0.2, abs=1e-9)}


def test_refuerzo_negativo_acotado_abajo() -> None:
    agent = learner(rate=1.0)
    set_weights(agent, {11: -0.8})
    decided(agent, Behavior.CONSUME)
    agent.reinforce(0, -0.5)
    assert agent.plastic_weights == {11: -1.0, 12: -0.5}


def test_sin_aprendizaje_con_tasa_nula() -> None:
    agent = learner(rate=0.0)
    set_weights(agent, {11: 0.9})
    decided(agent, Behavior.CONSUME)
    agent.reinforce(0, 0.4)
    assert agent.plastic_weights == {11: 0.9}


def test_sin_aprendizaje_sin_r40() -> None:
    agent = learner(config=config_with(enable_plasticity=False, plasticity_rate_base=0.5))
    set_weights(agent, {11: 0.9})
    decided(agent, Behavior.CONSUME)
    agent.reinforce(0, 0.4)
    assert agent.plastic_weights == {11: 0.9}


def test_sin_recompensa_no_se_crean_pesos() -> None:
    agent = learner()
    decided(agent, Behavior.CONSUME)
    agent.reinforce(0, 0.0)
    assert agent.plastic_weights == {}


def test_sin_decision_del_tick_no_aprende() -> None:
    agent = learner()
    decided(agent, Behavior.CONSUME, tick=0)
    agent.reinforce(1, 0.4)  # la decisión registrada es la del tick 0
    assert agent.plastic_weights == {}
    other = learner()
    other.evaluate_for_decision(signals(), 0)  # decidió, pero sin conducta elegida (IDLE)
    other.reinforce(0, 0.4)
    assert other.plastic_weights == {}


def test_solo_aprende_la_conducta_elegida() -> None:
    agent = learner()
    decided(agent, Behavior.FLEE)
    agent.reinforce(0, 0.4)
    assert agent.plastic_weights == {9: pytest.approx(0.2, abs=1e-9)}


def test_la_conducta_elegida_se_registra_con_la_decision() -> None:
    agent = learner()
    assert agent.decision_behavior(0) is None
    decided(agent, Behavior.FLEE, tick=3)
    assert agent.decision_behavior(3) is Behavior.FLEE
    assert agent.decision_behavior(4) is None
    agent.evaluate_for_decision(signals(), 4)
    assert agent.decision_behavior(4) is None  # la nueva decisión aún no eligió conducta


def test_la_endospora_no_registra_conducta() -> None:
    agent = learner()
    agent.set_endospore(True)
    decided(agent, Behavior.CONSUME)
    assert agent.decision_behavior(0) is None
    agent.reinforce(0, 0.4)
    assert agent.plastic_weights == {}


def test_la_politica_genetica_registra_la_conducta() -> None:
    agent = agent_with(plastic(WANDER, 64))
    obs = Observation(1, 0, (), ((0, 1), (1, 0)), ())
    action = agent.decide_action(obs, 0, np.random.Generator(np.random.PCG64(0)))
    assert action.action_type is ActionType.MOVE
    assert agent.decision_behavior(0) is Behavior.WANDER


@given(
    st.floats(0.0, 1.0),
    st.floats(-3.0, 3.0),
    st.dictionaries(st.sampled_from([9, 11, 12]), st.floats(-1.0, 1.0), max_size=3),
)
def test_pesos_siempre_acotados(rate: float, reward: float, weights: dict[int, float]) -> None:
    agent = learner(rate=rate)
    set_weights(agent, weights)
    decided(agent, Behavior.CONSUME)
    agent.reinforce(0, reward)
    result = agent.plastic_weights
    assert all(-1.0 <= w <= 1.0 for w in result.values())
    assert result.get(9) == weights.get(9)  # FLEE no es la conducta elegida
    for i in (11, 12):
        if rate * reward != 0.0:
            expected = min(1.0, max(-1.0, weights.get(i, 0.0) + rate * reward))
            assert result[i] == expected
        else:
            assert result.get(i) == weights.get(i)


# --- (d) ciclo de vida de plastic_weights (D59.2) ----------------------------------------------


def test_pesos_vacios_al_nacer_y_tras_cambiar_el_adn() -> None:
    parent = learner()
    parent.apply_energy_delta(3.0)
    set_weights(parent, {3: 0.4})
    child = parent.create_offspring(9, 4, np.random.Generator(np.random.PCG64(0)))
    assert child.plastic_weights == {}
    assert parent.plastic_weights == {3: 0.4}
    parent.set_dna(CompactDNA(chromosome=FOUNDER_TRAITS))
    assert parent.plastic_weights == {}


def test_pesos_vacios_en_el_fundador_y_sin_adn() -> None:
    assert MicroAgent(1, R40).plastic_weights == {}
    assert MicroAgent(1, SimulationConfig()).plastic_weights == {}


def test_pesos_conservados_en_endospora() -> None:
    agent = learner()
    set_weights(agent, {11: 0.3})
    agent.set_endospore(True)
    agent.set_endospore(False)
    assert agent.plastic_weights == {11: 0.3}


def test_la_vista_de_los_pesos_es_de_solo_lectura() -> None:
    agent = learner()
    set_weights(agent, {9: 0.2, 12: 0.1})
    view = agent.plastic_weights
    with pytest.raises(TypeError):
        view[9] = 1.0  # type: ignore[index]
    assert agent.plastic_weights == {9: 0.2, 12: 0.1}


def test_los_pesos_nuevos_se_insertan_en_orden_de_posicion() -> None:
    agent = learner()
    set_weights(agent, {9: 0.2})
    decided(agent, Behavior.FLEE)
    assert agent.reinforce(0, 0.4) == 1  # sólo actualiza el 9
    agent2 = learner()
    set_weights(agent2, {13: 0.1})  # una posición mayor que las elegibles 11 y 12
    decided(agent2, Behavior.CONSUME)
    assert agent2.reinforce(0, 0.4) == 2
    assert list(agent2.plastic_weights) == [11, 12, 13]


def test_reinforce_devuelve_las_actualizaciones() -> None:
    agent = learner()
    decided(agent, Behavior.CONSUME)
    assert agent.reinforce(0, 0.0) == 0  # r = 0: no cuenta
    assert agent.reinforce(1, 0.4) == 0  # sin decisión en el tick 1
    assert agent.reinforce(0, 0.4) == 2  # dos codones elegibles
    idle = learner()
    idle.evaluate_for_decision(signals(), 0)
    assert idle.reinforce(0, 0.4) == 0  # decidió IDLE: sin conducta elegida
    still = learner(rate=0.0)
    decided(still, Behavior.CONSUME)
    assert still.reinforce(0, 0.4) == 0  # eta = 0: no mueve ningún peso y no cuenta
    assert still.plastic_weights == {}


def test_set_dna_descarta_la_conducta_elegida() -> None:
    agent = learner()
    decided(agent, Behavior.CONSUME)
    agent.set_dna(CompactDNA(chromosome=(*FOUNDER_TRAITS, plastic(CONSUME, 16))))
    assert agent.decision_behavior(0) is None
    agent.reinforce(0, 0.4)
    assert agent.plastic_weights == {}


# --- (e) caché único de la evaluación con los pesos (D59.5, precisiones 57 y 88) ---------------


def test_el_cache_no_sirve_pesos_viejos() -> None:
    agent = learner()
    first = agent.evaluate_behavior(signals())
    set_weights(agent, {11: 0.5})
    second = agent.evaluate_behavior(signals())
    assert second.drives[0] == pytest.approx(first.drives[0] + 0.5, abs=1e-9)
    assert second == evaluate_behavior(
        agent.dna or CompactDNA(), CTX0, signals(), agent.base_config, plastic_weights={11: 0.5}
    )


@given(
    st.lists(
        st.tuples(
            st.sampled_from(
                [all_signals(False), signals(attacked=True), signals(neighbor_adjacent=True)]
            ),
            st.integers(0, 255),
            st.sampled_from(
                [EpigeneticContext(0), EpigeneticContext(2, EpigeneticRole.NERVE, 0.05)]
            ),
            st.dictionaries(st.integers(0, 16), st.floats(-1.0, 1.0), max_size=4),
            st.booleans(),
        ),
        max_size=12,
    )
)
def test_cache_de_la_evaluacion_igual_a_la_directa(steps: list[tuple[Any, ...]]) -> None:
    config = ALL_AMPLIFICATION
    first = (
        plastic(WANDER, 32, promoter=0x30),
        encode_codon(0x28, SET_STATE, 0, 1),
        plastic(CONSUME, 64),
        encode_codon(0x00, CONSUME, 2, 0, 32),
        plastic(FLEE, -20, promoter=0x23),
        encode_codon(0x18, ATTACK, 1, 0, -40),
        plastic(ATTACK, 90, promoter=0x18),
    )
    second = (plastic(SHARE, 50), encode_codon(0x31, SHARE, 0, 0, 64), plastic(EXPLORE, 10))
    agent = MicroAgent(1, config, policy=GeneticPolicy())
    agent.set_dna(CompactDNA(chromosome=FOUNDER_TRAITS + first))
    for tick, (sig, state, context, weights, swap) in enumerate(steps):
        if swap:
            agent.set_dna(CompactDNA(chromosome=FOUNDER_TRAITS + second))
        agent.express(context, 0)
        agent._internal_state = state  # pyright: ignore[reportPrivateUsage]
        set_weights(agent, weights)
        assert agent.dna is not None
        expected = evaluate_behavior(
            agent.dna,
            agent.last_context,
            sig,
            agent.base_config,
            state=state,
            plastic_weights=agent.plastic_weights,
        )
        assert agent.evaluate_behavior(sig) == expected
        assert agent.evaluate_behavior(sig) == expected  # segunda lectura, desde el caché
        assert agent.evaluate_for_decision(sig, tick) == expected
        assert agent.decision_evaluation(tick) == expected


# --- Motor: recompensa de la Fase 4 (D59.4) ----------------------------------------------------


def small(**overrides: Any) -> SimulationConfig:
    """Configuración chica con $R_{32}$, $R_{36}$, $R_{37}$ y $R_{40}$, sin costos."""
    base = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=14,
        resources_per_pattern=4,
        enable_evolution=True,
        enable_compact_dna=True,
        enable_genetic_policy=True,
        enable_plasticity=True,
        plasticity_rate_base=0.5,
        enable_energy_transfer=True,
        enable_predation=True,
        metabolic_base_cost=0.0,
        memory_capacity_cost=0.0,
        sensory_radius_cost=0.0,
        move_cost=0.0,
        message_cost=0.0,
        dna_codon_cost=0.0,
        attack_cost=0.0,
        reproduction_threshold=100.0,
    )
    return replace(base, **overrides)


def grid_of(engine: SimulationEngine) -> ToroidalGrid2D:
    return cast(ToroidalGrid2D, engine.env)


def put(engine: SimulationEngine, aid: int, cell: tuple[int, int]) -> None:
    grid = grid_of(engine)
    old = grid._agent_cell[aid]  # pyright: ignore[reportPrivateUsage]
    grid.cell_agents[old].discard(aid)
    grid.cell_agents[cell].add(aid)
    grid._agent_cell[aid] = cell  # pyright: ignore[reportPrivateUsage]


def set_energy(engine: SimulationEngine, aid: int, energy: float) -> None:
    agent = engine.agents[aid]
    agent.apply_energy_delta(energy - agent.energy)


class FixedOrder(BaseSystem):
    name = "schedule"

    def __init__(self, order: list[int]) -> None:
        self.order = order

    def run(self, engine: SimulationEngine, frame: TickFrame) -> None:
        rest = [aid for aid in sorted(engine.agents) if aid not in self.order]
        frame.order = [*self.order, *rest]


def fix_order(engine: SimulationEngine, order: list[int]) -> None:
    engine.systems = tuple(
        FixedOrder(order) if isinstance(system, ScheduleSystem) else system
        for system in engine.systems
    )


def scene(
    monkeypatch: pytest.MonkeyPatch,
    config: SimulationConfig,
    learner_id: int,
    codon: int,
    group: dict[int, float],
    actions: dict[int, AgentAction] | None = None,
) -> SimulationEngine:
    """Motor con `group` (agente -> energía) en la celda (5, 5) y los demás lejos.

    `learner_id` decide con la política genética y el ADN fundador de rasgos más `codon` (en la
    posición 9); los demás hacen `actions` o `IDLE`.
    """
    engine = SimulationEngine(config)
    corners = [(0, 0), (0, 9), (9, 0), (9, 9), (0, 5), (9, 5), (5, 0), (5, 9)]
    others = [aid for aid in sorted(engine.agents) if aid not in group]
    for aid, cell in zip(others, corners * 2, strict=False):
        put(engine, aid, cell)
    for aid, energy in group.items():
        put(engine, aid, (5, 5))
        set_energy(engine, aid, energy)
    engine.agents[learner_id].set_dna(CompactDNA(chromosome=(*FOUNDER_TRAITS, codon)))
    actions = actions or {}
    for aid, agent in engine.agents.items():
        if aid != learner_id:
            action = actions.get(aid, IDLE)
            monkeypatch.setattr(agent, "decide_action", lambda *_args, a=action: a)
    return engine


def test_recompensa_de_un_robo(monkeypatch: pytest.MonkeyPatch) -> None:
    config = small(predation_efficiency=0.6, attack_power=0.5)
    engine = scene(
        monkeypatch,
        config,
        5,
        plastic(ATTACK, 64),
        {5: 2.0, 4: 1.0, 9: 3.0},
        {9: AgentAction(ActionType.ATTACK, 5)},
    )
    fix_order(engine, [5, 9])
    engine.step()
    attacker = engine.agents[5]
    assert attacker.decision_behavior(0) is Behavior.ATTACK
    assert attacker.energy == pytest.approx(2.0 + 0.3 - 0.5, abs=1e-9)  # robó y le robaron
    assert attacker.plastic_weights == {9: pytest.approx(0.15, abs=1e-9)}


def test_recompensa_de_una_cesion(monkeypatch: pytest.MonkeyPatch) -> None:
    config = small(share_fraction=0.25, plasticity_rate_base=1.0)
    engine = scene(monkeypatch, config, 5, plastic(SHARE, 64), {5: 2.0, 4: 1.0})
    engine.step()
    donor = engine.agents[5]
    assert donor.decision_behavior(0) is Behavior.SHARE
    assert donor.plastic_weights == {9: pytest.approx(-0.5, abs=1e-9)}


def test_movimiento_sin_recompensa(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = scene(monkeypatch, small(), 5, plastic(WANDER, 64), {5: 2.0})
    engine.step()
    walker = engine.agents[5]
    assert walker.decision_behavior(0) is Behavior.WANDER
    assert walker.plastic_weights == {}


def test_recompensa_de_un_consumo(monkeypatch: pytest.MonkeyPatch) -> None:
    """La recompensa de `INTERACT` es la energía ganada con el valor experimentado."""
    config = small(energy_gain_scale=0.1, plasticity_rate_base=1.0)
    engine = SimulationEngine(config)
    agent = engine.agents[3]
    agent.set_dna(CompactDNA(chromosome=(*FOUNDER_TRAITS, plastic(CONSUME, 64))))
    agent.express(CTX0, 0)
    decided(agent, Behavior.CONSUME)
    grid = grid_of(engine)
    pattern = Pattern((("id", "p_0"),))
    original = grid.execute_action

    def execute(agent_id: int, action: AgentAction, tick: int) -> ActionResult:
        if action.action_type is ActionType.INTERACT and agent_id == 3:
            return ActionResult(ActionType.INTERACT, pattern, 2.0)
        return original(agent_id, action, tick)

    monkeypatch.setattr(grid, "execute_action", execute)
    actions = {aid: IDLE for aid in engine.agents}
    actions[3] = AgentAction(ActionType.INTERACT, 0)
    frame = TickFrame(0, order=sorted(engine.agents), actions=actions)
    ExecutionSystem().run(engine, frame)
    assert agent.plastic_weights == {9: pytest.approx(0.2, abs=1e-9)}
    assert frame.events["plastic_updates"] == 1


def test_movimiento_no_cuenta_actualizaciones(monkeypatch: pytest.MonkeyPatch) -> None:
    """Escenario de `plastic_updates`: el consumo con r != 0 cuenta y el `MOVE` no."""
    engine = SimulationEngine(small(energy_gain_scale=0.1))
    eater, walker = engine.agents[3], engine.agents[4]
    eater.set_dna(CompactDNA(chromosome=(*FOUNDER_TRAITS, plastic(CONSUME, 64))))
    walker.set_dna(CompactDNA(chromosome=(*FOUNDER_TRAITS, plastic(WANDER, 64))))
    for agent, behavior in ((eater, Behavior.CONSUME), (walker, Behavior.WANDER)):
        agent.express(CTX0, 0)
        decided(agent, behavior)
    grid = grid_of(engine)
    pattern = Pattern((("id", "p_0"),))
    original = grid.execute_action

    def execute(agent_id: int, action: AgentAction, tick: int) -> ActionResult:
        if action.action_type is ActionType.INTERACT and agent_id == 3:
            return ActionResult(ActionType.INTERACT, pattern, 1.0)
        return original(agent_id, action, tick)

    monkeypatch.setattr(grid, "execute_action", execute)
    actions = {aid: IDLE for aid in engine.agents}
    actions[3] = AgentAction(ActionType.INTERACT, 0)
    actions[4] = AgentAction(ActionType.MOVE, grid.get_observation(4, 0).available_moves[0])
    frame = TickFrame(0, order=sorted(engine.agents), actions=actions)
    ExecutionSystem().run(engine, frame)
    assert frame.events["plastic_updates"] == 1


def test_sin_r40_no_hay_evento_de_actualizaciones(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = scene(
        monkeypatch, small(enable_plasticity=False), 5, plastic(SHARE, 64), {5: 2.0, 4: 1.0}
    )
    spy: list[dict[str, int]] = []

    class Spy:
        def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
            pass

        def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
            spy.append(dict(frame.events))

    engine.observers.append(Spy())
    engine.step()
    assert "plastic_updates" not in spy[0]


def test_la_recompensa_no_incluye_la_cesion_recibida(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quien recibe energía de otro en la Fase 4 no la cuenta como recompensa propia."""
    config = small(share_fraction=0.5, share_efficiency=1.0, plasticity_rate_base=1.0)
    engine = scene(
        monkeypatch,
        config,
        5,
        plastic(WANDER, 64),
        {5: 1.0, 7: 3.0},
        {7: AgentAction(ActionType.SHARE, 5)},
    )
    fix_order(engine, [7, 5])
    engine.step()
    assert engine.agents[5].energy == pytest.approx(2.5, abs=1e-9)
    assert engine.agents[5].plastic_weights == {}


# --- (f) inercia sin R40 y aceptación (D59.6, D57.1) -------------------------------------------


def names(config: SimulationConfig) -> list[str]:
    return [system.name for system in build_systems(config)]


def test_r40_no_agrega_sistemas() -> None:
    assert names(small()) == names(small(enable_plasticity=False))


def test_el_motor_guarda_la_condicion_efectiva() -> None:
    assert SimulationEngine(small()).plasticity_active
    assert not SimulationEngine(small(enable_plasticity=False)).plasticity_active
    assert not SimulationEngine(SimulationConfig()).plasticity_active


LEARNING_CODONS = (
    plastic(ATTACK, 100),
    plastic(SHARE, 60, promoter=0x18),
    plastic(CONSUME, 40),
    plastic(EXPLORE, 30, promoter=0x21),
    plastic(WANDER, 20),
)


def learning_run(config: SimulationConfig, ticks: int = 30) -> SimulationEngine:
    engine = SimulationEngine(config)
    for aid in sorted(engine.agents):
        agent = engine.agents[aid]
        assert agent.dna is not None
        agent.set_dna(CompactDNA(chromosome=agent.dna.chromosome + LEARNING_CODONS))
    engine.run(ticks)
    return engine


def protocol_config(**overrides: Any) -> SimulationConfig:
    return replace(
        PHASE2_PROTOCOL_CONFIGS["002a"],
        enable_compact_dna=True,
        enable_genetic_policy=True,
        enable_energy_transfer=True,
        enable_predation=True,
        **overrides,
    )


def test_sin_r40_los_pesos_no_cambian() -> None:
    engine = learning_run(protocol_config(enable_plasticity=False, plasticity_rate_base=0.8))
    assert all(agent.plastic_weights == {} for agent in engine.agents.values())
    for agent in engine.agents.values():
        decision = agent.decision_evaluation(29)
        assert decision is None or decision.plastic == NO_PLASTIC


def test_con_tasa_base_nula_nadie_aprende() -> None:
    engine = learning_run(protocol_config(enable_plasticity=True, mutation_rate=0.0))
    assert all(agent.plastic_weights == {} for agent in engine.agents.values())


def test_con_r40_y_tasa_positiva_los_pesos_cambian() -> None:
    engine = learning_run(protocol_config(enable_plasticity=True, plasticity_rate_base=0.8))
    learned = [agent.plastic_weights for agent in engine.agents.values() if agent.plastic_weights]
    assert learned
    assert all(-1.0 <= w <= 1.0 for weights in learned for w in weights.values())


# --- Determinismo entre procesos ---------------------------------------------------------------


def test_historiales_iguales_con_distinto_pythonhashseed() -> None:
    script = textwrap.dedent(
        """
        from dataclasses import astuple, replace
        from ide.agent.dna import encode_codon
        from ide.domain.types import CompactDNA
        from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
        from ide.simulation.engine import SimulationEngine

        config = replace(
            PHASE2_PROTOCOL_CONFIGS["002a"],
            enable_compact_dna=True,
            enable_genetic_policy=True,
            enable_internal_state=True,
            enable_plasticity=True,
            plasticity_rate_base=0.6,
            enable_energy_transfer=True,
            enable_predation=True,
            mutation_rate=0.2,
        )
        engine = SimulationEngine(config)
        extra = (
            encode_codon(0x00, 0x45, 3, 0, 100),
            encode_codon(0x18, 0x44, 3, 0, 60),
            encode_codon(0x00, 0x40, 3, 0, 40),
            encode_codon(0x21, 0x41, 3, 0, 30),
            encode_codon(0x29, 0x0D, 0, 0),
            encode_codon(0x30, 0x40, 3, 0, 20),
            encode_codon(0x00, 0x0F, 0, 0, 20),
        )
        for aid in sorted(engine.agents):
            agent = engine.agents[aid]
            agent.set_dna(CompactDNA(chromosome=agent.dna.chromosome + extra))
        engine.run(60)
        print([astuple(m) for m in engine.history])
        print([astuple(m) for m in engine.evolutionary_history])
        agents = sorted(engine.agents.items())
        print([(a, sorted(g.plastic_weights.items()), g.internal_state) for a, g in agents])
        print(engine.rng.bit_generator.state, engine.evo_rng.bit_generator.state)
        print(sum(1 for _, g in agents if any(w != 0.0 for w in g.plastic_weights.values())))
        """
    )
    outputs = []
    for hash_seed in ("0", "123"):
        path = os.pathsep.join(
            filter(None, [str(ROOT / "src"), str(ROOT), os.environ.get("PYTHONPATH")])
        )
        env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": path}
        done = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            check=True,
            cwd=ROOT,
        )
        outputs.append(done.stdout)
    assert outputs[0] == outputs[1]
    # La corrida aprende de verdad: no es una igualdad trivial.
    assert int(outputs[0].splitlines()[-1]) > 0
