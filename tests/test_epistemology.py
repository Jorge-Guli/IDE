"""Tests de `epistemic-engine`: experiencia directa y revalidación social (Escenarios A, B y C)."""

from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.epistemology import merge_social_belief, update_from_direct_experience
from ide.agent.memory import BoundedMemory
from ide.config import SimulationConfig
from ide.domain.types import KnowledgeUnit, Pattern

CFG = SimulationConfig()
RHO = Pattern((("id", "p_0"),))


def ku(value: float, conf: float, direct: bool, tau: int = 0, evidence: int = 1) -> KnowledgeUnit:
    return KnowledgeUnit(RHO, value, conf, evidence, tau, direct)


# --- Experiencia directa -----------------------------------------------------------------------


def test_adquisicion_directa_de_recurso_danino() -> None:
    k = update_from_direct_experience(None, RHO, -1.0, 5, CFG)
    assert k.pattern == RHO
    assert k.predicted_value == pytest.approx(-1.0, abs=1e-9)
    assert k.confidence == pytest.approx(0.85, abs=1e-9)
    assert k.evidence_count == 1
    assert k.last_updated_tick == 5
    assert k.from_direct_experience is True


def test_adquisicion_directa_recorta_el_valor() -> None:
    assert update_from_direct_experience(None, RHO, 3.0, 0, CFG).predicted_value == 1.0
    assert update_from_direct_experience(None, RHO, -3.0, 0, CFG).predicted_value == -1.0


def test_refuerzo_confirma_creencia_social() -> None:
    k = update_from_direct_experience(ku(1.0, 0.50, False, tau=2, evidence=3), RHO, 1.0, 7, CFG)
    assert k.confidence == pytest.approx(0.65, abs=1e-9)
    assert k.predicted_value == pytest.approx(1.0, abs=1e-9)
    assert k.evidence_count == 4
    assert k.last_updated_tick == 7
    assert k.from_direct_experience is True


def test_refuerzo_mezcla_el_valor() -> None:
    k = update_from_direct_experience(ku(0.5, 0.5, True), RHO, 1.0, 1, CFG)
    assert k.predicted_value == pytest.approx(0.6 * 0.5 + 0.4 * 1.0, abs=1e-9)


def test_refutacion_severa_reinicia_la_creencia() -> None:
    k = update_from_direct_experience(ku(1.0, 0.80, False, evidence=4), RHO, -1.0, 9, CFG)
    assert k.predicted_value == pytest.approx(-1.0, abs=1e-9)
    assert k.confidence == pytest.approx(0.85, abs=1e-9)
    assert k.evidence_count == 1
    assert k.last_updated_tick == 9
    assert k.from_direct_experience is True


def test_refutacion_atenuada_conserva_el_signo() -> None:
    k = update_from_direct_experience(ku(1.0, 1.0, True, evidence=2), RHO, -1.0, 4, CFG)
    assert k.predicted_value == pytest.approx(0.2, abs=1e-9)
    assert k.confidence == pytest.approx(0.4, abs=1e-9)
    assert k.evidence_count == 3
    assert k.last_updated_tick == 4
    assert k.from_direct_experience is True


def test_refutacion_atenuada_con_piso_de_magnitud() -> None:
    # blended = 0.6·0.5 + 0.4·(-0.8) = -0.02: se conserva el signo previo con |v̂| = 0.05.
    k = update_from_direct_experience(ku(0.5, 1.0, True), RHO, -0.8, 1, CFG)
    assert k.predicted_value == pytest.approx(0.05, abs=1e-9)


def test_refutacion_atenuada_de_creencia_negativa() -> None:
    k = update_from_direct_experience(ku(-1.0, 1.0, True), RHO, 1.0, 1, CFG)
    assert k.predicted_value == pytest.approx(-0.2, abs=1e-9)


# --- Escenario A: adopción con descuento -------------------------------------------------------


def test_escenario_a_atenuacion_en_cadena() -> None:
    a = update_from_direct_experience(None, RHO, 1.0, 0, CFG)
    b = merge_social_belief(None, a, 1, CFG)
    c = merge_social_belief(None, b, 2, CFG)
    assert b.confidence == pytest.approx(0.6375, abs=1e-9)
    assert c.confidence == pytest.approx(0.478125, abs=1e-9)
    assert (b.evidence_count, b.from_direct_experience, b.last_updated_tick) == (1, False, 1)
    assert c.predicted_value == pytest.approx(1.0, abs=1e-9)


def test_escenario_a_factor_de_confianza_personalizado() -> None:
    k = merge_social_belief(None, ku(1.0, 0.8, True), 0, CFG, sender_trust_factor=0.5)
    assert k.confidence == pytest.approx(0.4, abs=1e-9)


# --- Escenario B: consenso ---------------------------------------------------------------------


def test_escenario_b_con_emisor_directo() -> None:
    local = ku(1.0, 0.60, False, tau=10, evidence=2)
    k = merge_social_belief(local, ku(1.0, 0.80, True), 50, CFG)
    assert k.confidence == pytest.approx(0.636, abs=1e-9)
    assert k.evidence_count == 3
    assert k.last_updated_tick == 50
    assert k.from_direct_experience is False


def test_escenario_b_promedia_el_valor_ponderado() -> None:
    k = merge_social_belief(ku(0.5, 0.6, True), ku(1.0, 0.8, True), 1, CFG)
    assert k.predicted_value == pytest.approx((0.6 * 0.5 + 0.6 * 1.0) / 1.2, abs=1e-9)
    assert k.from_direct_experience is True


def test_escenario_b_sin_confianza_toma_el_valor_externo() -> None:
    k = merge_social_belief(ku(0.0, 0.0, False), ku(0.7, 0.0, False), 1, CFG)
    assert k.predicted_value == pytest.approx(0.7, abs=1e-9)


def test_anti_eco_cien_intercambios() -> None:
    a, b = ku(1.0, 0.50, False), ku(1.0, 0.50, False)
    for t in range(1, 101):
        a, b = merge_social_belief(a, b, t, CFG), merge_social_belief(b, a, t, CFG)
    assert a.confidence == pytest.approx(0.50, abs=1e-9)
    assert b.confidence == pytest.approx(0.50, abs=1e-9)


def test_anti_eco_el_rumor_no_refresca_tau() -> None:
    k = merge_social_belief(ku(1.0, 0.5, False, tau=10), ku(1.0, 0.5, False), 50, CFG)
    assert k.last_updated_tick == 10
    m = BoundedMemory(capacity=3)
    m.upsert(k, 50)
    m.decay_step(50, CFG.passive_conf_decay, CFG.min_confidence)
    unit = m.get(RHO)
    assert unit is not None
    assert unit.confidence == pytest.approx(k.confidence - CFG.passive_conf_decay, abs=1e-9)


def test_anti_eco_adopta_un_rumor_mas_fuerte_sin_superarlo() -> None:
    # max(c, e) = max(0.2, 0.675): el rumor fuerte eleva hasta su propio nivel, no más.
    k = merge_social_belief(ku(1.0, 0.2, False), ku(1.0, 0.9, False), 1, CFG)
    raw = 0.2 + 0.15 * 0.675 * 0.8
    assert k.confidence == pytest.approx(min(0.675, raw), abs=1e-9)


def test_ablacion_anti_eco_crece_en_cada_intercambio() -> None:
    cfg = replace(CFG, anti_echo_enabled=False)
    a, b = ku(1.0, 0.50, False), ku(1.0, 0.50, False)
    previous = 0.50
    for t in range(1, 101):
        a, b = merge_social_belief(a, b, t, cfg), merge_social_belief(b, a, t, cfg)
        assert a.confidence > previous
        assert b.confidence > 0.50
        previous = a.confidence
    assert a.last_updated_tick == 100


def test_ablacion_anti_eco_refresca_tau() -> None:
    cfg = replace(CFG, anti_echo_enabled=False)
    k = merge_social_belief(ku(1.0, 0.5, False, tau=10), ku(1.0, 0.5, False), 50, cfg)
    assert k.last_updated_tick == 50


# --- Escenario C: contradicción ----------------------------------------------------------------


def test_escenario_c_resistencia_de_experiencia_directa() -> None:
    local = ku(1.0, 0.85, True, tau=3, evidence=2)
    k = merge_social_belief(local, ku(-1.0, 0.90, False), 9, CFG)
    assert k.predicted_value == pytest.approx(1.0, abs=1e-9)
    assert k.confidence == pytest.approx(0.7825, abs=1e-9)
    assert k.confidence > CFG.decision_conf_threshold
    assert k.last_updated_tick == 3
    assert k.from_direct_experience is True
    assert k.evidence_count == 2


def test_escenario_c_resistencia_de_rumor() -> None:
    # e = 0.3 no supera 1.2·0.5: resistencia con r = 1.
    k = merge_social_belief(ku(1.0, 0.5, False, tau=4), ku(-1.0, 0.4, True), 9, CFG)
    assert k.confidence == pytest.approx(0.5 - 0.2 * 0.3, abs=1e-9)
    assert (k.predicted_value, k.last_updated_tick, k.from_direct_experience) == (1.0, 4, False)


def test_escenario_c_sobrescritura_de_rumor_debil() -> None:
    k = merge_social_belief(ku(-1.0, 0.25, False, tau=1, evidence=5), ku(1.0, 0.90, True), 8, CFG)
    assert k.predicted_value == pytest.approx(1.0, abs=1e-9)
    assert k.confidence == pytest.approx(0.55, abs=1e-9)
    assert (k.evidence_count, k.last_updated_tick, k.from_direct_experience) == (1, 8, False)


def test_escenario_c_sobrescritura_con_piso_min_confidence() -> None:
    # e = 0.075 > 1.2·0.06 = 0.072, pero e - 0.5·c = 0.045 < min_confidence.
    k = merge_social_belief(ku(-1.0, 0.06, False), ku(1.0, 0.1, False), 1, CFG)
    assert k.confidence == pytest.approx(CFG.min_confidence, abs=1e-9)


def test_escenario_c_experiencia_directa_nunca_se_sobrescribe() -> None:
    k = merge_social_belief(ku(-1.0, 0.1, True), ku(1.0, 1.0, True), 1, CFG)
    assert k.predicted_value == -1.0
    assert k.confidence == pytest.approx(0.1 - 0.2 * 0.75 / 2.0, abs=1e-9)


# --- Propiedades -------------------------------------------------------------------------------

values = st.floats(min_value=-1.0, max_value=1.0, allow_nan=False)
confidences = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
beliefs = st.builds(
    KnowledgeUnit,
    st.just(RHO),
    values,
    confidences,
    st.integers(min_value=1, max_value=50),
    st.integers(min_value=0, max_value=100),
    st.booleans(),
)


def assert_in_range(k: KnowledgeUnit) -> None:
    assert -1.0 <= k.predicted_value <= 1.0
    assert 0.0 <= k.confidence <= 1.0
    assert k.evidence_count >= 1


@given(st.none() | beliefs, st.floats(-5.0, 5.0, allow_nan=False), st.integers(0, 200))
def test_propiedad_rangos_experiencia_directa(
    existing: KnowledgeUnit | None, real_value: float, tick: int
) -> None:
    k = update_from_direct_experience(existing, RHO, real_value, tick, CFG)
    assert_in_range(k)
    assert k.from_direct_experience is True
    assert k.last_updated_tick == tick


@given(st.none() | beliefs, beliefs, st.integers(0, 200), st.none() | confidences, st.booleans())
def test_propiedad_rangos_fusion_social(
    existing: KnowledgeUnit | None,
    incoming: KnowledgeUnit,
    tick: int,
    trust: float | None,
    anti_echo: bool,
) -> None:
    cfg = replace(CFG, anti_echo_enabled=anti_echo)
    assert_in_range(merge_social_belief(existing, incoming, tick, cfg, trust))


@given(
    st.lists(st.tuples(values, confidences), min_size=2, max_size=6),
    st.lists(st.tuples(st.integers(0, 5), st.integers(0, 5)), max_size=60),
)
def test_propiedad_cota_anti_eco(
    initial: list[tuple[float, float]], exchanges: list[tuple[int, int]]
) -> None:
    # Entre portadores de rumores del mismo signo, ningún intercambio eleva la confianza máxima.
    beliefs_ = [ku(abs(v), c, False) for v, c in initial]
    bound = max(k.confidence for k in beliefs_)
    for tick, (i, j) in enumerate(exchanges, start=1):
        receiver, sender = i % len(beliefs_), j % len(beliefs_)
        if receiver == sender:
            continue
        beliefs_[receiver] = merge_social_belief(beliefs_[receiver], beliefs_[sender], tick, CFG)
        assert beliefs_[receiver].confidence <= bound + 1e-12
        assert beliefs_[receiver].from_direct_experience is False
