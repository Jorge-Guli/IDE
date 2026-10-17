"""Expectativas empíricas sobre los mecanismos programados (Decisión 10).

Se ejecutan con `python -m pytest -m empirical`. Pueden fallar legítimamente: un fracaso es un
hallazgo que se reporta tal cual, nunca un motivo para ajustar parámetros.
"""

import pytest

from ide.config import SimulationConfig
from ide.experiments.exp001_runner import (
    FalsificationReport,
    SurplusReport,
    run_protocol_001a_surplus,
    run_protocol_001b_falsification,
    sign_test_p_value,
)

SEEDS = (42, 43, 44, 45, 46)
pytestmark = pytest.mark.empirical


@pytest.fixture(scope="module")
def surplus_reports() -> dict[int, SurplusReport]:
    return {s: run_protocol_001a_surplus(SimulationConfig(seed=s), total_ticks=300) for s in SEEDS}


@pytest.fixture(scope="module")
def falsification_reports() -> dict[int, FalsificationReport]:
    return {
        s: run_protocol_001b_falsification(
            SimulationConfig(seed=s), total_ticks=300, injection_tick=80, injection_fraction=0.25
        )
        for s in SEEDS
    }


@pytest.mark.parametrize("seed", SEEDS)
def test_h1_cobertura_accesible(surplus_reports: dict[int, SurplusReport], seed: int) -> None:
    report = surplus_reports[seed]
    assert report.collective_accessible_coverage > report.isolated_accessible_coverage


@pytest.mark.parametrize("seed", SEEDS)
def test_h1_superavit_positivo(surplus_reports: dict[int, SurplusReport], seed: int) -> None:
    assert surplus_reports[seed].collective_surplus > 0


def test_h1_prueba_de_signo(surplus_reports: dict[int, SurplusReport]) -> None:
    p_value = sign_test_p_value([r.collective_surplus for r in surplus_reports.values()])
    assert p_value < 0.05


@pytest.mark.parametrize("seed", SEEDS)
def test_contencion_del_rumor(
    falsification_reports: dict[int, FalsificationReport], seed: int
) -> None:
    report = falsification_reports[seed]
    assert report.final_false_prevalence < report.initial_injected_prevalence
