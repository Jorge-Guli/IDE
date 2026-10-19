"""Tests de la calibración de viabilidad del perfil de la Fase II (enmienda de design D29)."""

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from ide.config import SimulationConfig
from ide.experiments import attribution, phase2_calibration
from ide.experiments.attribution import (
    EXP002_CLAIMS,
    EXP003_CLAIMS,
    PHASE2_PROTOCOL_CONFIGS_ORIGINAL,
    PHASE2_SEEDS,
    ablate,
)
from ide.experiments.phase2_calibration import (
    CALIBRATION_GRID,
    CALIBRATION_PARAMETER,
    CALIBRATION_SEEDS,
    MIN_GENERATION,
    MIN_VIABLE_SEEDS,
    CalibrationReport,
    ViabilityRun,
    calibration_conditions,
    is_viable_value,
    main,
    run_calibration,
)

SMALL = {"grid_width": 10, "grid_height": 10, "num_agents": 12}


def run(
    protocol: str, condition: str, seed: int, agents: int = 5, generation: int = 6
) -> ViabilityRun:
    return ViabilityRun(protocol, condition, 10, seed, agents, generation)


CONDITIONS = [
    ("002a", "evolved"), ("002a", "frozen_genome"), ("002a", "drift"), ("002a", "null_content"),
    ("002b", "cultural"), ("002b", "tabula_rasa"), ("002b", "null_content"),
    ("003a", "holonic"), ("003a", "individual"), ("003a", "null_content"),
    ("003b", "with_view"), ("003b", "without_view"), ("003b", "null_content"),
]  # fmt: skip


def test_procedimiento_declarado() -> None:
    assert CALIBRATION_PARAMETER == "resources_per_pattern"
    assert CALIBRATION_GRID == (10, 20, 40, 80)
    assert tuple(range(10)) == CALIBRATION_SEEDS
    assert not set(CALIBRATION_SEEDS) & set(PHASE2_SEEDS)  # semillas distintas de las de medición
    assert (MIN_VIABLE_SEEDS, MIN_GENERATION) == (8, 5)


def test_condiciones_de_comparacion() -> None:
    """Las condiciones de cada runner, derivadas de sus `ProtocolSpec`, más el control nulo."""
    base = PHASE2_PROTOCOL_CONFIGS_ORIGINAL
    found = calibration_conditions(base)
    assert [(p, c) for p, c, _ in found] == CONDITIONS
    configs = {(p, c): config for p, c, config in found}
    assert configs[("002a", "evolved")] == base["002a"]
    assert configs[("002a", "frozen_genome")] == ablate(base["002a"], ["R13"])
    assert configs[("002a", "drift")] == ablate(base["002a"], ["R12"])
    assert configs[("002b", "tabula_rasa")] == ablate(base["002b"], ["R14"])
    assert configs[("003a", "individual")] == ablate(base["003a"], ["R15"])
    assert configs[("003b", "without_view")] == ablate(base["003b"], ["R22"])
    for protocol in base:
        null = configs[(protocol, "null_content")]
        assert null == dataclasses.replace(base[protocol], comm_content_null=True)


def test_solo_registra_demografia() -> None:
    """La calibración no calcula ninguna métrica de las afirmaciones C5 a C8."""
    assert [f.name for f in dataclasses.fields(ViabilityRun)] == [
        "protocol",
        "condition",
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
    assert run("002a", "evolved", 0, agents, generation).viable is viable


def test_criterio_de_un_valor() -> None:
    good = [
        run(p, c, s, agents=0 if s >= 8 else 5) for p, c in CONDITIONS for s in CALIBRATION_SEEDS
    ]
    assert is_viable_value(good)  # 8 de 10 en cada condición de comparación
    bad = [
        run("002a", "drift", 0, agents=0)
        if (r.protocol, r.condition, r.seed) == ("002a", "drift", 0)
        else r
        for r in good
    ]
    assert not is_viable_value(bad)  # la deriva queda con 7 de 10, aunque la base sea viable
    assert not is_viable_value([r for r in good if r.condition != "without_view"])  # falta una


FEW_SEEDS = (0, 1, 2)


@pytest.fixture
def small(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configuraciones chicas y 3 semillas (2 viables bastan), sin tocar lo declarado.

    La calibración parte de las configuraciones originales; las vigentes quedan vacías para que
    leerlas falle.
    """
    configs = {
        k: dataclasses.replace(c, **SMALL) for k, c in PHASE2_PROTOCOL_CONFIGS_ORIGINAL.items()
    }
    monkeypatch.setattr(attribution, "PHASE2_PROTOCOL_CONFIGS_ORIGINAL", configs)
    monkeypatch.setattr(attribution, "PHASE2_PROTOCOL_CONFIGS", {})
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
    expected = [(p, c, s) for p, c in CONDITIONS for s in FEW_SEEDS]
    assert [(r.protocol, r.condition, r.seed) for r in report.runs] == expected


def test_corridas_identicas_se_ejecutan_una_vez(
    small: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """003-A y 003-B comparten base y control nulo: 11 configuraciones distintas por semilla."""
    monkeypatch.setattr(phase2_calibration, "MIN_GENERATION", 0)
    sizes: list[int] = []
    original = phase2_calibration.map_in_order

    def counting(function: Any, items: Any, jobs: int) -> Any:
        sizes.append(len(items))
        return original(function, items, jobs)

    monkeypatch.setattr(phase2_calibration, "map_in_order", counting)
    report = run_calibration(total_ticks=12)
    assert sizes == [11 * len(FEW_SEEDS)]
    by_key = {(r.protocol, r.condition, r.seed): r for r in report.runs}
    for seed in FEW_SEEDS:
        a, b = by_key[("003a", "holonic", seed)], by_key[("003b", "with_view", seed)]
        assert (a.final_agents, a.max_generation) == (b.final_agents, b.max_generation)


def test_paralelismo_inocuo(small: None) -> None:
    assert run_calibration(total_ticks=12) == run_calibration(total_ticks=12, jobs=2)


def test_cli(tmp_path: Path, small: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--ticks", "12", "--out", str(tmp_path)]) == 0
    data = json.loads((tmp_path / "phase2_calibration.json").read_text())
    assert data["chosen"] is None
    assert data["parameter"] == CALIBRATION_PARAMETER
    assert len(data["runs"]) == len(CALIBRATION_GRID) * len(CONDITIONS) * len(FEW_SEEDS)
    assert "ningún valor" in capsys.readouterr().out


def test_reporte_inmutable() -> None:
    report = CalibrationReport("resources_per_pattern", 12, None, ())
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.chosen = 10  # type: ignore[misc]


def test_cubre_las_variantes_de_e2_y_e4_de_cada_afirmacion() -> None:
    """La aislada y el control nulo de cada afirmación de Fase II están en el criterio."""
    base = PHASE2_PROTOCOL_CONFIGS_ORIGINAL
    covered = {config for _, _, config in calibration_conditions(base)}
    for claim in EXP002_CLAIMS + EXP003_CLAIMS:
        variants = attribution._variants(claim, base[claim.protocol])  # pyright: ignore[reportPrivateUsage]
        assert variants["isolated"] in covered, claim.claim_id
        assert variants["null_content"] in covered, claim.claim_id


def test_una_variante_inviable_hace_pasar_al_valor_siguiente(
    small: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Escenario de la spec: base viable y deriva una semilla por debajo del mínimo."""
    monkeypatch.setattr(phase2_calibration, "MIN_GENERATION", 0)
    first_value = {
        key: dataclasses.replace(config, resources_per_pattern=CALIBRATION_GRID[0])
        for key, config in attribution.PHASE2_PROTOCOL_CONFIGS_ORIGINAL.items()
    }
    drift = next(
        config
        for protocol, name, config in calibration_conditions(first_value)
        if (protocol, name) == ("002a", "drift")
    )
    # Con 3 semillas y un mínimo de 2, extinguir 2 deja a la deriva con 1: una de menos.
    extinct = {dataclasses.replace(drift, seed=seed) for seed in FEW_SEEDS[:2]}
    original = phase2_calibration._demography  # pyright: ignore[reportPrivateUsage]

    def extinct_drift(task: tuple[SimulationConfig, int]) -> tuple[int, int]:
        return (0, 0) if task[0] in extinct else original(task)

    monkeypatch.setattr(phase2_calibration, "_demography", extinct_drift)
    report = run_calibration(total_ticks=12)
    assert report.chosen == CALIBRATION_GRID[1]
    first = [r for r in report.runs if r.value == CALIBRATION_GRID[0]]
    assert all(r.viable for r in first if r.condition == "evolved")
    assert sum(r.viable for r in first if r.condition == "drift") == 1


def test_exige_condiciones_para_cada_protocolo() -> None:
    extra = {**PHASE2_PROTOCOL_CONFIGS_ORIGINAL, "004a": PHASE2_PROTOCOL_CONFIGS_ORIGINAL["002a"]}
    with pytest.raises(ValueError, match="004a"):
        calibration_conditions(extra)
    with_r18 = dict(PHASE2_PROTOCOL_CONFIGS_ORIGINAL)
    with_r18["003b"] = dataclasses.replace(with_r18["003b"], enable_downward_causation=True)
    with pytest.raises(ValueError, match="R18"):
        calibration_conditions(with_r18)
