"""Tests de la línea base de rendimiento (`quality-tooling`)."""

import json
from pathlib import Path

import pytest

from ide.config import SimulationConfig
from ide.experiments.benchmark import BENCHMARK_REPETITIONS, BENCHMARK_TICKS, main


def test_parametros_del_escenario() -> None:
    assert BENCHMARK_TICKS == 300
    assert BENCHMARK_REPETITIONS == 3


def test_medicion_registrada(tmp_path: Path) -> None:
    out = tmp_path / "benchmark.json"
    assert main(["--ticks", "5", "--out", str(out)]) == 0
    data = json.loads(out.read_text())
    assert data["median_ticks_per_second"] > 0
    assert data["repetitions"] == 3
    assert data["ticks"] == 5
    assert len(data["ticks_per_second"]) == 3
    assert isinstance(data["python_version"], str) and data["python_version"]
    assert isinstance(data["platform"], str) and data["platform"]
    assert data["config"] == SimulationConfig().to_dict()


@pytest.mark.parametrize("ticks", ["0", "-3"])
def test_ticks_no_positivos_se_rechazan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], ticks: str
) -> None:
    out = tmp_path / "b.json"
    with pytest.raises(SystemExit) as exc:
        main([f"--ticks={ticks}", "--out", str(out)])
    assert exc.value.code == 2
    assert "debe ser >= 1" in capsys.readouterr().err
    assert not out.exists()
