"""Tests de `bounded-memory`: capacidad, utilidad, reemplazo, decaimiento y orden."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.memory import BoundedMemory
from ide.domain.types import KnowledgeUnit, Pattern


def pat(i: int) -> Pattern:
    return Pattern((("id", f"p_{i}"),))


def ku(i: int, conf: float = 0.9, value: float = 1.0, tau: int = 0) -> KnowledgeUnit:
    return KnowledgeUnit(pat(i), value, conf, 1, tau, True)


# --- Capacidad ---------------------------------------------------------------------------------


def test_insercion_con_espacio_disponible() -> None:
    m = BoundedMemory(capacity=3)
    assert m.upsert(ku(0), 0) and m.upsert(ku(1), 0)
    assert m.upsert(ku(2), 0) is True
    assert len(m) == 3


def test_actualizar_patron_existente_con_memoria_llena() -> None:
    m = BoundedMemory(capacity=3)
    for i in range(3):
        m.upsert(ku(i), 0)
    nueva = ku(1, conf=0.1, value=-1.0, tau=5)
    assert m.upsert(nueva, 5) is True
    assert len(m) == 3
    assert m.get(pat(1)) == nueva


def test_capacidad_invalida() -> None:
    with pytest.raises(ValueError):
        BoundedMemory(capacity=0)


def test_contains_get_y_remove() -> None:
    m = BoundedMemory(capacity=2)
    m.upsert(ku(0), 0)
    assert pat(0) in m and pat(1) not in m
    assert m.get(pat(1)) is None
    assert m.remove(pat(0)) is True
    assert m.remove(pat(0)) is False
    assert len(m) == 0


# --- Utilidad ----------------------------------------------------------------------------------


def test_utilidad_valor_exacto() -> None:
    m = BoundedMemory(capacity=3, lambda_decay=0.005)
    u = m.compute_utility(ku(0, conf=0.2, value=1.0, tau=1), 10)
    assert u == pytest.approx(0.2 * math.exp(-0.045), abs=1e-12)


def test_utilidad_piso_de_relevancia() -> None:
    m = BoundedMemory(capacity=3)
    assert m.compute_utility(ku(0, conf=1.0, value=0.0, tau=4), 4) == pytest.approx(0.1, abs=1e-12)


def test_utilidad_no_penaliza_tau_futuro() -> None:
    m = BoundedMemory(capacity=3)
    assert m.compute_utility(ku(0, conf=0.5, value=1.0, tau=20), 10) == pytest.approx(0.5)


# --- Reemplazo ---------------------------------------------------------------------------------


def test_expulsion_de_creencia_obsoleta_y_debil() -> None:
    m = BoundedMemory(capacity=2, lambda_decay=0.005)
    k1, k2, k3 = ku(1, 0.9, 1.0, 10), ku(2, 0.2, 1.0, 1), ku(3, 0.85, 1.0, 10)
    m.upsert(k1, 10)
    m.upsert(k2, 10)
    assert m.upsert(k3, 10) is True
    assert m.get(pat(2)) is None
    assert m.get(pat(3)) == k3
    assert m.get(pat(1)) == k1


def test_rechazo_de_rumor_debil() -> None:
    m = BoundedMemory(capacity=2)
    m.upsert(ku(0, 0.9), 0)
    m.upsert(ku(1, 0.9), 0)
    antes = m.all_units()
    assert m.upsert(ku(2, conf=0.25), 0) is False
    assert m.all_units() == antes


def test_utilidad_igual_no_reemplaza() -> None:
    m = BoundedMemory(capacity=1)
    m.upsert(ku(0, 0.5), 0)
    assert m.upsert(ku(1, 0.5), 0) is False


def test_desempate_por_tau_y_luego_por_patron() -> None:
    # Misma utilidad en t = 10 con lambda = 0: el desempate decide la víctima.
    m = BoundedMemory(capacity=3, lambda_decay=0.0)
    m.upsert(ku(5, 0.5, 1.0, tau=7), 10)
    m.upsert(ku(4, 0.5, 1.0, tau=3), 10)  # menor tau: víctima
    m.upsert(ku(3, 0.5, 1.0, tau=9), 10)
    m.upsert(ku(9, 0.9), 10)
    assert pat(4) not in m and pat(3) in m and pat(5) in m

    m = BoundedMemory(capacity=2, lambda_decay=0.0)
    m.upsert(ku(7, 0.5, 1.0, tau=3), 10)
    m.upsert(ku(2, 0.5, 1.0, tau=3), 10)  # mismo tau: víctima el menor pattern
    m.upsert(ku(9, 0.9), 10)
    assert pat(2) not in m and pat(7) in m


# --- Inserción forzada -------------------------------------------------------------------------


def test_force_inserta_creencia_de_baja_utilidad() -> None:
    m = BoundedMemory(capacity=2)
    m.upsert(ku(0, 0.95), 0)
    m.upsert(ku(1, 0.9), 0)
    debil = ku(2, conf=0.25)
    assert m.upsert(debil, 0, force=True) is True
    assert len(m) == 2
    assert m.get(pat(2)) == debil
    assert pat(1) not in m  # la víctima es la de menor utilidad


# --- Decaimiento -------------------------------------------------------------------------------


def test_purga_de_creencia_degradada() -> None:
    m = BoundedMemory(capacity=3)
    m.upsert(ku(0, conf=0.06, tau=0), 5)
    m.upsert(ku(1, conf=0.9, tau=0), 5)
    purgados = m.decay_step(5, 0.02, 0.05)
    assert purgados == [pat(0)]
    assert pat(0) not in m
    survivor = m.get(pat(1))
    assert survivor is not None
    assert survivor.confidence == pytest.approx(0.88, abs=1e-9)
    assert survivor.last_updated_tick == 0


def test_confianza_resultante_de_la_purga() -> None:
    m = BoundedMemory(capacity=3)
    m.upsert(ku(0, conf=0.06, tau=0), 5)
    # sin purga: umbral menor que la confianza resultante (0.04)
    assert m.decay_step(5, 0.02, 0.03) == []
    unit = m.get(pat(0))
    assert unit is not None and unit.confidence == pytest.approx(0.04, abs=1e-9)


def test_creencia_validada_en_el_tick_actual_no_decae() -> None:
    m = BoundedMemory(capacity=3)
    m.upsert(ku(0, conf=0.06, tau=5), 5)
    assert m.decay_step(5, 0.02, 0.05) == []
    unit = m.get(pat(0))
    assert unit is not None and unit.confidence == pytest.approx(0.06, abs=1e-9)


def test_patrones_purgados_salen_ordenados() -> None:
    m = BoundedMemory(capacity=3)
    for i in (2, 0, 1):
        m.upsert(ku(i, conf=0.06), 0)
    assert m.decay_step(1, 0.02, 0.05) == [pat(0), pat(1), pat(2)]


# --- Orden -------------------------------------------------------------------------------------


def test_all_units_ordenadas_por_patron() -> None:
    m = BoundedMemory(capacity=3)
    for i in (2, 0, 1):
        m.upsert(ku(i), 0)
    assert [u.pattern.label for u in m.all_units()] == ["id=p_0", "id=p_1", "id=p_2"]


# --- Propiedades (Hypothesis) ------------------------------------------------------------------

_units = st.builds(
    lambda i, c, v, t: ku(i, c, v, t),
    st.integers(0, 7),
    st.floats(0.0, 1.0),
    st.floats(-1.0, 1.0),
    st.integers(0, 50),
)
_ops = st.one_of(
    st.tuples(st.just("upsert"), _units, st.integers(0, 60), st.booleans()),
    st.tuples(st.just("decay"), st.integers(0, 60), st.floats(0.0, 0.2), st.floats(0.0, 0.3)),
)


@given(st.integers(1, 5), st.lists(_ops, max_size=40))
def test_propiedad_capacidad_y_confianza_minima(capacity: int, ops: list[tuple]) -> None:  # type: ignore[type-arg]
    m = BoundedMemory(capacity=capacity)
    for op in ops:
        if op[0] == "upsert":
            m.upsert(op[1], op[2], force=op[3])
        else:
            _, tick, passive, min_conf = op
            m.decay_step(tick, passive, min_conf)
            assert all(u.confidence >= min_conf for u in m.all_units())
        assert len(m) <= capacity
        patrones = [u.pattern for u in m.all_units()]
        assert len(patrones) == len(set(patrones))


# --- Fase II: penalización de redundancia (ψ_red, R18) -----------------------------------------


def test_capacidad_expuesta() -> None:
    assert BoundedMemory(capacity=4).capacity == 4


def test_utilidad_modulada_para_patron_redundante() -> None:
    m = BoundedMemory(capacity=3)
    k0, k1 = ku(0, conf=0.8, tau=10), ku(1, conf=0.8, tau=10)
    sin_penalizar = (m.compute_utility(k0, 10), m.compute_utility(k1, 10))
    assert sin_penalizar == (pytest.approx(0.80, abs=1e-12), pytest.approx(0.80, abs=1e-12))
    m.set_redundant_patterns(frozenset({pat(0)}), penalty=0.25)
    assert m.compute_utility(k0, 10) == pytest.approx(0.20, abs=1e-12)
    assert m.compute_utility(k1, 10) == pytest.approx(0.80, abs=1e-12)


def test_sin_patrones_redundantes_la_utilidad_es_bit_a_bit_la_de_fase_i() -> None:
    m, referencia = BoundedMemory(capacity=3), BoundedMemory(capacity=3)
    m.set_redundant_patterns(frozenset({pat(5)}), penalty=0.3)
    unit = ku(0, conf=0.37, value=-0.61, tau=3)
    assert m.compute_utility(unit, 17) == referencia.compute_utility(unit, 17)
    assert m.compute_utility(unit, 17) == pytest.approx(
        0.37 * 0.61 * math.exp(-0.005 * 14), abs=1e-9
    )


def test_cada_llamada_reemplaza_a_la_anterior() -> None:
    m = BoundedMemory(capacity=3)
    m.set_redundant_patterns(frozenset({pat(0)}), penalty=0.5)
    m.set_redundant_patterns(frozenset({pat(1)}))
    assert m.compute_utility(ku(0), 0) == pytest.approx(0.9, abs=1e-12)
    assert m.compute_utility(ku(1), 0) == pytest.approx(0.9, abs=1e-12)  # penalty=1.0
    m.set_redundant_patterns(frozenset({pat(1)}), penalty=0.5)
    m.set_redundant_patterns(frozenset())
    assert m.compute_utility(ku(1), 0) == pytest.approx(0.9, abs=1e-12)


@pytest.mark.parametrize("penalty", [0.0, -0.1, 1.01, float("nan")])
def test_penalizacion_fuera_de_rango(penalty: float) -> None:
    with pytest.raises(ValueError, match="penalty"):
        BoundedMemory(capacity=3).set_redundant_patterns(frozenset({pat(0)}), penalty)


def test_la_penalizacion_decide_el_desalojo() -> None:
    m = BoundedMemory(capacity=2)
    m.upsert(ku(0, conf=0.9), 0)
    m.upsert(ku(1, conf=0.5), 0)
    m.set_redundant_patterns(frozenset({pat(0)}), penalty=0.2)
    assert m.upsert(ku(2, conf=0.6), 0) is True
    assert sorted(u.pattern for u in m.all_units()) == [pat(1), pat(2)]


# --- Fase II-B: cambio de capacidad en vida (R24, design D34.3) --------------------------------


def test_resize_achica_desalojando_por_menor_utilidad() -> None:
    m = BoundedMemory(capacity=3)
    for unit in (ku(1, conf=0.9, tau=10), ku(2, conf=0.2, tau=10), ku(3, conf=0.6, tau=10)):
        m.upsert(unit, 10)
    m.resize(1, 10)
    assert m.capacity == 1
    assert m.all_units() == [ku(1, conf=0.9, tau=10)]


def test_resize_aplica_la_penalizacion_de_redundancia() -> None:
    m = BoundedMemory(capacity=2)
    m.upsert(ku(0, conf=0.9, tau=4), 4)
    m.upsert(ku(1, conf=0.5, tau=4), 4)
    m.set_redundant_patterns(frozenset({pat(0)}), penalty=0.2)
    m.resize(1, 4)
    assert m.all_units() == [ku(1, conf=0.5, tau=4)]  # 0.18 < 0.5


def test_resize_desempata_por_tau_y_luego_por_patron() -> None:
    # Las tres con la misma utilidad en t=10 (sin decaimiento): primero cae la de menor τ y,
    # entre las de igual τ, la de menor patrón, como en el desalojo de R2.
    m = BoundedMemory(capacity=3, lambda_decay=0.0)
    for unit in (ku(5, tau=7), ku(1, tau=9), ku(2, tau=9)):
        m.upsert(unit, 9)
    m.resize(2, 10)
    assert [u.pattern for u in m.all_units()] == [pat(1), pat(2)]
    m.resize(1, 10)
    assert [u.pattern for u in m.all_units()] == [pat(2)]


def test_resize_usa_la_utilidad_en_el_tick_indicado() -> None:
    # En t=0 gana la más confiable; en t=400, la reciente: la edad entra en la utilidad.
    vieja, reciente = ku(0, conf=0.9, tau=0), ku(1, conf=0.5, tau=400)
    m = BoundedMemory(capacity=2)
    m.upsert(vieja, 0)
    m.upsert(reciente, 0)
    m.resize(1, 400)
    assert m.all_units() == [reciente]


def test_resize_agranda_sin_borrar() -> None:
    m = BoundedMemory(capacity=2)
    m.upsert(ku(0), 0)
    m.upsert(ku(1), 0)
    m.resize(5, 3)
    assert m.capacity == 5
    assert [u.pattern for u in m.all_units()] == [pat(0), pat(1)]
    for i in range(2, 5):
        assert m.upsert(ku(i, conf=0.01), 3) is True  # sin competir por utilidad
    assert len(m) == 5


def test_resize_a_la_misma_capacidad_no_cambia_nada() -> None:
    m = BoundedMemory(capacity=2)
    m.upsert(ku(0), 0)
    m.upsert(ku(1), 0)
    m.resize(2, 50)
    assert (m.capacity, [u.pattern for u in m.all_units()]) == (2, [pat(0), pat(1)])


@pytest.mark.parametrize("capacity", [0, -1])
def test_resize_rechaza_capacidad_menor_que_uno(capacity: int) -> None:
    m = BoundedMemory(capacity=2)
    m.upsert(ku(0), 0)
    m.upsert(ku(1), 0)
    with pytest.raises(ValueError, match="capacity"):
        m.resize(capacity, 0)
    assert (m.capacity, len(m)) == (2, 2)


@given(
    capacity=st.integers(1, 8),
    new_capacity=st.integers(1, 8),
    confs=st.lists(st.floats(0.05, 1.0), min_size=0, max_size=8),
    tick=st.integers(0, 50),
)
def test_propiedad_resize_conserva_las_de_mayor_utilidad(
    capacity: int, new_capacity: int, confs: list[float], tick: int
) -> None:
    m = BoundedMemory(capacity=capacity)
    for i, conf in enumerate(confs[:capacity]):
        m.upsert(ku(i, conf=conf, tau=i), 0)
    before = m.all_units()
    m.resize(new_capacity, tick)
    after = m.all_units()
    assert m.capacity == new_capacity
    assert len(after) == min(len(before), new_capacity)
    assert set(after) <= set(before)
    kept = {u.pattern for u in after}
    rank = {u.pattern: (m.compute_utility(u, tick), u.last_updated_tick, u.pattern) for u in before}
    for dropped in (u for u in before if u.pattern not in kept):
        assert all(rank[dropped.pattern] < rank[p] for p in kept)
