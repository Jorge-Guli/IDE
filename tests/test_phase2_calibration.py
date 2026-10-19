"""Tests de la calibración de viabilidad del perfil de la Fase II (enmienda de design D29)."""

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from ide.experiments import attribution, phase2_calibration
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS, PHASE2_SEEDS
from ide.experiments.phase2_calibration import (
    CALIBRATION_GRID,
    CALIBRATION_PARAMETER,
    CALIBRATION_SEEDS,
    MIN_GENERATION,
    MIN_VIABLE_SEEDS,
    CalibrationReport,
    ViabilityRun,
    is_viable_value,
    main,
    run_calibration,
)

SMALL = {"grid_width": 10, "grid_height": 10, "num_agents": 12}


def run(protocol: str, seed: int, agents: int = 5, generation: int = 6) -> ViabilityRun:
    return ViabilityRun(protocol, 10, seed, agents, generation)


def test_procedimiento_declarado() -> None:
    assert CALIBRATION_PARAMETER == "resources_per_pattern"
    assert CALIBRATION_GRID == (10, 20, 40, 80)
    assert tuple(range(10)) == CALIBRATION_SEEDS
    assert not set(CALIBRATION_SEEDS) & set(PHASE2_SEEDS)  # semillas distintas de las de medición
    assert (MIN_VIABLE_SEEDS, MIN_GENERATION) == (8, 5)


def test_solo_registra_demografia() -> None:
    """La calibración no calcula ninguna métrica de las afirmaciones C5 a C8."""
    assert [f.name for f in dataclasses.fields(ViabilityRun)] == [
        "protocol",
        "value",
        "seed",
        "final_agents",
        "max_generation",
    ]


@pytest.mark.parametrize(
    ("agents", "generation", "viable"),
    [(5, 6, True), (1, 5, True), (0, 9, False), (40, 4, False)],
)
def test_criterio_de_una_corrida(agents: int, generation: int, viable: bool) -> None:
    assert run("002a", 0, agents, generation).viable is viable


def test_criterio_de_un_valor() -> None:
    protocols = sorted(PHASE2_PROTOCOL_CONFIGS)
    good = [run(p, s, agents=0 if s >= 8 else 5) for p in protocols for s in CALIBRATION_SEEDS]
    assert is_viable_value(good)  # 8 de 10 en cada protocolo
    bad = [r if r.protocol != "003b" or r.seed != 0 else run("003b", 0, agents=0) for r in good]
    assert not is_viable_value(bad)  # 003-B queda con 7 de 10
    assert not is_viable_value([r for r in good if r.protocol != "002a"])  # falta un protocolo


FEW_SEEDS = (0, 1, 2)


@pytest.fixture
def small(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configuraciones chicas y 3 semillas (2 viables bastan), sin tocar lo declarado."""
    configs = {k: dataclasses.replace(c, **SMALL) for k, c in PHASE2_PROTOCOL_CONFIGS.items()}
    monkeypatch.setattr(attribution, "PHASE2_PROTOCOL_CONFIGS", configs)
    monkeypatch.setattr(phase2_calibration, "CALIBRATION_SEEDS", FEW_SEEDS)
    monkeypatch.setattr(phase2_calibration, "MIN_VIABLE_SEEDS", 2)


def test_sin_valor_viable_evalua_toda_la_grilla(small: None) -> None:
    report = run_calibration(total_ticks=12)  # en 12 ticks nadie llega a la generación 5
    assert report.chosen is None
    assert sorted({r.value for r in report.runs}) == list(CALIBRATION_GRID)
    assert all(not r.viable for r in report.runs)


def test_elige_el_menor_valor_viable_y_se_detiene(
    small: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(phase2_calibration, "MIN_GENERATION", 0)
    report = run_calibration(total_ticks=12)
    assert report.chosen == CALIBRATION_GRID[0]
    assert {r.value for r in report.runs} == {CALIBRATION_GRID[0]}
    expected = [(p, s) for p in sorted(PHASE2_PROTOCOL_CONFIGS) for s in FEW_SEEDS]
    assert [(r.protocol, r.seed) for r in report.runs] == expected


def test_corridas_identicas_se_ejecutan_una_vez(
    small: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """003-A y 003-B tienen la misma configuración: cada semilla corre una sola vez."""
    monkeypatch.setattr(phase2_calibration, "MIN_GENERATION", 0)
    sizes: list[int] = []
    original = phase2_calibration.map_in_order

    def counting(function: Any, items: Any, jobs: int) -> Any:
        sizes.append(len(items))
        return original(function, items, jobs)

    monkeypatch.setattr(phase2_calibration, "map_in_order", counting)
    report = run_calibration(total_ticks=12)
    assert sizes == [3 * len(FEW_SEEDS)]
    by_key = {(r.protocol, r.seed): r for r in report.runs}
    for seed in FEW_SEEDS:
        a, b = by_key[("003a", seed)], by_key[("003b", seed)]
        assert (a.final_agents, a.max_generation) == (b.final_agents, b.max_generation)


def test_paralelismo_inocuo(small: None) -> None:
    assert run_calibration(total_ticks=12) == run_calibration(total_ticks=12, jobs=2)


def test_cli(tmp_path: Path, small: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--ticks", "12", "--out", str(tmp_path)]) == 0
    data = json.loads((tmp_path / "phase2_calibration.json").read_text())
    assert data["chosen"] is None
    assert data["parameter"] == CALIBRATION_PARAMETER
    assert len(data["runs"]) == len(CALIBRATION_GRID) * 4 * len(FEW_SEEDS)
    assert "ningún valor" in capsys.readouterr().out


def test_reporte_inmutable() -> None:
    report = CalibrationReport("resources_per_pattern", 12, None, ())
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.chosen = 10  # type: ignore[misc]
