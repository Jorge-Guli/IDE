"""Tests de `emergence-attribution`: reglas, pre-registro, ablación y clasificación."""

import dataclasses

import pytest

from ide.config import SimulationConfig
from ide.experiments.attribution import (
    ATTRIBUTION_PROFILE,
    DESIGN_RULES,
    EXP001_CLAIMS,
    ablate,
    disables_communication,
)

CFG = SimulationConfig()


# --- Inventario de reglas y pre-registro -------------------------------------------------------


def test_reglas_ablacionables() -> None:
    assert [r.rule_id for r in DESIGN_RULES] == [f"R{i}" for i in range(1, 12)]
    assert [r.rule_id for r in DESIGN_RULES if r.ablation == ()] == ["R1", "R2"]
    assert all(r.name and r.purpose for r in DESIGN_RULES)


def test_overrides_de_cada_regla() -> None:
    overrides = {r.rule_id: dict(r.ablation) for r in DESIGN_RULES}
    assert overrides["R3"] == {"passive_conf_decay": 0.0}
    assert overrides["R4"] == {"gamma_social_discount": 1.0}
    assert overrides["R5"] == {"eta_consensus": 0.0}
    assert overrides["R6"] == {"anti_echo_enabled": False}
    assert overrides["R7"] == {"eta_doubt": 0.0}
    assert overrides["R8"] == {"max_queries_per_tick": 0}
    assert overrides["R9"] == {"max_broadcast_per_tick": 0}
    assert overrides["R10"] == {"epsilon_explore": 0.0}
    assert overrides["R11"] == {"enable_navigation": False}


def test_principio_conservador_acotado() -> None:
    claims = {c.claim_id: c for c in EXP001_CLAIMS}
    assert list(claims) == ["C1", "C2", "C3", "C4"]
    for cid in ("C1", "C2", "C4"):
        assert {"R8", "R9"} <= set(claims[cid].purpose_rules)
    assert claims["C3"].purpose_rules == ("R3", "R4", "R6", "R7")


def test_metricas_y_direcciones_pre_registradas() -> None:
    table = [(c.protocol, c.metric, c.higher_is_better) for c in EXP001_CLAIMS]
    assert table == [
        ("001a", "accessible_coverage_mean", True),
        ("001a", "cumulative_decision_accuracy", True),
        ("001b", "final_false_prevalence", False),
        ("001c", "final_social_persistence_prevalence", True),
    ]
    assert ATTRIBUTION_PROFILE == "quick"


# --- Ablación ----------------------------------------------------------------------------------


def test_ablacion_conjunta_de_la_comunicacion() -> None:
    ablated = ablate(CFG, ["R8", "R9"])
    assert ablated.max_queries_per_tick == 0
    assert ablated.max_broadcast_per_tick == 0
    assert dataclasses.replace(ablated, max_queries_per_tick=2, max_broadcast_per_tick=1) == CFG
    assert disables_communication(ablated)


def test_ablacion_de_todas_las_reglas_es_valida() -> None:
    every = [r.rule_id for r in DESIGN_RULES if r.ablation]
    ablated = ablate(CFG, every)
    assert isinstance(ablated, SimulationConfig)
    for rule in DESIGN_RULES:
        for name, value in rule.ablation:
            assert getattr(ablated, name) == value


@pytest.mark.parametrize("rule_ids", [["R1"], ["R2"], ["R99"], ["R3", "R1"]])
def test_regla_nuclear_o_inexistente(rule_ids: list[str]) -> None:
    with pytest.raises(ValueError):
        ablate(CFG, rule_ids)


def test_ablacion_vacia_no_cambia_nada() -> None:
    assert ablate(CFG, []) == CFG


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, False),
        ({"comm_enabled": False}, True),
        ({"max_queries_per_tick": 0}, False),
        ({"max_broadcast_per_tick": 0}, False),
        ({"max_queries_per_tick": 0, "max_broadcast_per_tick": 0}, True),
    ],
)
def test_disables_communication(overrides: dict[str, object], expected: bool) -> None:
    assert disables_communication(dataclasses.replace(CFG, **overrides)) is expected  # type: ignore[arg-type]
