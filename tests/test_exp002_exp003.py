"""Tests de los protocolos 002 y 003 (`experimental-suite`): reportes, JSON y CLI."""

import dataclasses
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from ide.config import SimulationConfig
from ide.experiments import attribution, exp002_runner, exp003_runner, phase2_cli
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS, ablate
from ide.experiments.exp001_runner import PROFILES, Profile, default_jobs
from ide.experiments.exp002_runner import (
    AdaptationReport,
    CulturalInheritanceReport,
    convergence_tick,
    run_evolution_condition,
    run_protocol_002a_adaptation,
    run_protocol_002b_cultural_inheritance,
)
from ide.experiments.exp003_runner import (
    HolonicTransitionReport,
    OrthogonalizationReport,
    run_holonic_condition,
    run_protocol_003a_holonic_transition,
    run_protocol_003b_orthogonalization,
)
from ide.experiments.metrics import TickMetrics, holon_tick_mean, holon_ticks
from ide.simulation.engine import SimulationEngine

ROOT = Path(__file__).resolve().parents[1]
SMALL = {"grid_width": 10, "grid_height": 10, "num_agents": 12, "resources_per_pattern": 6}
TICKS = 40


def protocol_config(key: str, **overrides: Any) -> SimulationConfig:
    return dataclasses.replace(PHASE2_PROTOCOL_CONFIGS[key], **{**SMALL, **overrides})


def field_names(report_type: type) -> list[str]:
    return [f.name for f in dataclasses.fields(report_type)]


def run_engine(config: SimulationConfig, ticks: int = TICKS) -> SimulationEngine:
    engine = SimulationEngine(config)
    engine.run(ticks)
    return engine


# --- 002-A: selección frente a genoma congelado y deriva ---------------------------------------


def test_protocolo_002a_rapido() -> None:
    """Escenario de la spec: `total_ticks=40`, tres condiciones con la misma semilla."""
    config = protocol_config("002a", seed=5)
    report = run_protocol_002a_adaptation(config, TICKS)
    assert field_names(AdaptationReport) == [
        "seed", "total_ticks", "evolved_accuracy", "frozen_genome_accuracy", "drift_accuracy",
        "adaptation_gain", "selection_gain", "final_mean_memory_capacity",
        "final_mean_bond_affinity", "evolved_max_generation", "evolved_mean_energy",
        "total_births", "total_deaths",
        "condition_demography",
    ]  # fmt: skip
    evolved = run_engine(config)
    frozen = run_engine(ablate(config, ["R13"]))
    drift = run_engine(ablate(config, ["R12"]))
    accuracy = {
        name: engine.history[-1].cumulative_decision_accuracy
        for name, engine in (("evolved", evolved), ("frozen", frozen), ("drift", drift))
    }
    assert (report.seed, report.total_ticks) == (5, TICKS)
    assert report.evolved_accuracy == pytest.approx(accuracy["evolved"], abs=1e-9)
    assert report.frozen_genome_accuracy == pytest.approx(accuracy["frozen"], abs=1e-9)
    assert report.drift_accuracy == pytest.approx(accuracy["drift"], abs=1e-9)
    assert report.adaptation_gain == pytest.approx(
        report.evolved_accuracy - report.frozen_genome_accuracy, abs=1e-9
    )
    assert report.selection_gain == pytest.approx(
        report.evolved_accuracy - report.drift_accuracy, abs=1e-9
    )
    history = evolved.evolutionary_history
    assert report.total_births == sum(m.births_this_tick for m in history)
    assert report.total_deaths == sum(m.deaths_this_tick for m in history)
    assert report.evolved_max_generation == max(m.max_generation for m in history)
    assert report.evolved_mean_energy == pytest.approx(history[-1].mean_energy, abs=1e-9)
    alive = list(evolved.agents.values())
    if alive:
        capacity = sum(a.genome.memory_capacity for a in alive) / len(alive)
        affinity = sum(a.genome.bond_affinity for a in alive) / len(alive)
    else:
        capacity = affinity = 0.0
    assert report.final_mean_memory_capacity == pytest.approx(capacity, abs=1e-9)
    assert report.final_mean_bond_affinity == pytest.approx(affinity, abs=1e-9)


def test_rasgos_finales_de_una_poblacion_extinguida() -> None:
    config = protocol_config("002a", initial_energy=0.01, metabolic_base_cost=0.5)
    summary = run_evolution_condition(config, 3)
    assert summary.total_deaths == SMALL["num_agents"]
    assert (summary.final_mean_memory_capacity, summary.final_mean_bond_affinity) == (0.0, 0.0)
    assert summary.final_mean_energy == 0.0


# --- 002-B: herencia cultural frente a tabula rasa ---------------------------------------------


def test_protocolo_002b_rapido() -> None:
    config = protocol_config("002b", seed=6, reproduction_threshold=1.6)
    report = run_protocol_002b_cultural_inheritance(config, TICKS)
    assert field_names(CulturalInheritanceReport) == [
        "seed", "total_ticks", "cultural_accuracy", "tabula_rasa_accuracy",
        "cultural_accuracy_surplus", "final_offspring_social_ratio",
        "final_offspring_social_ratio_tabula_rasa", "social_ratio_gain",
        "cultural_convergence_tick", "tabula_rasa_convergence_tick",
        "condition_demography",
    ]  # fmt: skip
    cultural = run_engine(config)
    tabula = run_engine(ablate(config, ["R14"]))
    assert report.cultural_accuracy == pytest.approx(
        cultural.history[-1].cumulative_decision_accuracy, abs=1e-9
    )
    assert report.tabula_rasa_accuracy == pytest.approx(
        tabula.history[-1].cumulative_decision_accuracy, abs=1e-9
    )
    assert report.cultural_accuracy_surplus == pytest.approx(
        report.cultural_accuracy - report.tabula_rasa_accuracy, abs=1e-9
    )
    assert report.final_offspring_social_ratio == pytest.approx(
        cultural.evolutionary_history[-1].offspring_social_ratio, abs=1e-9
    )
    assert report.final_offspring_social_ratio_tabula_rasa == pytest.approx(
        tabula.evolutionary_history[-1].offspring_social_ratio, abs=1e-9
    )
    assert report.social_ratio_gain == pytest.approx(
        report.final_offspring_social_ratio - report.final_offspring_social_ratio_tabula_rasa,
        abs=1e-9,
    )
    assert report.cultural_convergence_tick == convergence_tick(cultural.history)
    assert report.tabula_rasa_convergence_tick == convergence_tick(tabula.history)


def metrics_at(tick: int, opportunities: int, cumulative: float) -> TickMetrics:
    return TickMetrics(
        tick, 1, 0.0, 0.0, 0.0, opportunities, 0, 0.0, cumulative, {}, {}, 0.0, 0, 0.0
    )


def test_tick_de_convergencia() -> None:
    """D28: menor tick con oportunidades y precisión acumulada >= 0.70."""
    history = [
        metrics_at(0, 0, 0.9),  # sin oportunidades: no cuenta
        metrics_at(1, 2, 0.5),
        metrics_at(2, 1, 0.70),
        metrics_at(3, 3, 0.8),
    ]
    assert convergence_tick(history) == 2
    assert convergence_tick(history[:2]) is None
    assert convergence_tick([]) is None


# --- 003-A: holones frente a individuos ante recursos compuestos -------------------------------


def test_protocolo_003a_rapido() -> None:
    """Escenario de la spec: recursos compuestos de orden m > C_max."""
    config = protocol_config("003a", seed=7)
    assert config.composite_order > config.memory_capacity
    report = run_protocol_003a_holonic_transition(config, TICKS)
    assert field_names(HolonicTransitionReport) == [
        "seed", "total_ticks", "holonic_composite_completions",
        "individual_composite_completions", "composite_completion_surplus", "holonic_accuracy",
        "individual_accuracy", "holonic_surplus", "max_holon_level", "peak_holonic_coverage_gain",
        "condition_demography",
    ]  # fmt: skip
    holonic = run_engine(config)
    individual = run_engine(ablate(config, ["R15"]))
    assert report.holonic_composite_completions == holonic.composite_completions
    assert report.individual_composite_completions == individual.composite_completions
    assert report.composite_completion_surplus == float(
        holonic.composite_completions - individual.composite_completions
    )
    assert report.holonic_accuracy == pytest.approx(
        holonic.history[-1].cumulative_decision_accuracy, abs=1e-9
    )
    assert report.individual_accuracy == pytest.approx(
        individual.history[-1].cumulative_decision_accuracy, abs=1e-9
    )
    assert report.holonic_surplus == pytest.approx(
        report.holonic_accuracy - report.individual_accuracy, abs=1e-9
    )
    evo = holonic.evolutionary_history
    assert report.max_holon_level == max(m.max_holon_level for m in evo)
    assert report.peak_holonic_coverage_gain == max(m.holonic_coverage_gain for m in evo)


# --- 003-B: cobertura colectiva adquirida con y sin vista --------------------------------------


def test_protocolo_003b_rapido() -> None:
    """Escenario de la spec: R18 apagada; medias por par (tick, holón elegible)."""
    config = protocol_config("003b", seed=8)
    assert not config.enable_downward_causation
    report = run_protocol_003b_orthogonalization(config, TICKS)
    assert field_names(OrthogonalizationReport) == [
        "seed", "total_ticks", "mean_acquired_coverage", "mean_acquired_coverage_without_view",
        "coverage_advantage", "mean_redundancy_reduction",
        "mean_redundancy_reduction_without_view", "holon_ticks", "holon_ticks_without_view",
        "max_holon_level", "level_counts_peak",
        "condition_demography",
    ]  # fmt: skip
    with_view = run_engine(config).evolutionary_history
    without_view = run_engine(ablate(config, ["R22"])).evolutionary_history
    assert report.mean_acquired_coverage == holon_tick_mean(with_view, "acquired_coverage")
    assert report.mean_acquired_coverage_without_view == holon_tick_mean(
        without_view, "acquired_coverage"
    )
    assert report.mean_redundancy_reduction == holon_tick_mean(with_view, "redundancy_reduction")
    assert report.mean_redundancy_reduction_without_view == holon_tick_mean(
        without_view, "redundancy_reduction"
    )
    assert report.holon_ticks == holon_ticks(with_view)
    assert report.holon_ticks_without_view == holon_ticks(without_view)
    if report.mean_acquired_coverage is None or report.mean_acquired_coverage_without_view is None:
        assert report.coverage_advantage is None
    else:
        assert report.coverage_advantage == pytest.approx(
            report.mean_acquired_coverage - report.mean_acquired_coverage_without_view, abs=1e-9
        )
    assert report.max_holon_level == max(m.max_holon_level for m in with_view)
    peak: dict[int, int] = {}
    for m in with_view:
        for level, count in m.holon_count_by_level:
            peak[level] = max(peak.get(level, 0), count)
    assert report.level_counts_peak == tuple(sorted(peak.items()))


def test_003b_sin_holones_elegibles() -> None:
    report = run_protocol_003b_orthogonalization(protocol_config("003b"), 1)
    assert report.mean_acquired_coverage is None
    assert report.mean_acquired_coverage_without_view is None
    assert report.coverage_advantage is None
    assert (report.holon_ticks, report.holon_ticks_without_view) == (0, 0)


def test_003b_exige_r18_apagada() -> None:
    with pytest.raises(ValueError, match="R18"):
        run_protocol_003b_orthogonalization(
            protocol_config("003b", enable_downward_causation=True), TICKS
        )


def test_resumen_holonico_de_una_condicion() -> None:
    config = protocol_config("003a", seed=9)
    summary = run_holonic_condition(config, TICKS)
    engine = run_engine(config)
    assert summary.final_accuracy == engine.history[-1].cumulative_decision_accuracy
    assert summary.composite_completions == engine.composite_completions


ProtocolCall = Callable[[SimulationConfig, int], Any]
PROTOCOLS: list[tuple[ProtocolCall, str]] = [
    (run_protocol_002a_adaptation, "002a"),
    (run_protocol_002b_cultural_inheritance, "002b"),
    (run_protocol_003a_holonic_transition, "003a"),
    (run_protocol_003b_orthogonalization, "003b"),
]


@pytest.mark.parametrize(("call", "key"), PROTOCOLS)
def test_duracion_invalida(call: ProtocolCall, key: str) -> None:
    with pytest.raises(ValueError, match="total_ticks"):
        call(protocol_config(key), 0)


@pytest.mark.parametrize(("call", "key"), PROTOCOLS)
def test_protocolos_deterministas(call: ProtocolCall, key: str) -> None:
    config = protocol_config(key, seed=11)
    assert call(config, 15) == call(config, 15)


# --- Serialización JSON y CLI ------------------------------------------------------------------

RUNNERS: list[tuple[ModuleType, str, tuple[str, str]]] = [
    (exp002_runner, "exp002", ("002a", "002b")),
    (exp003_runner, "exp003", ("003a", "003b")),
]


@pytest.fixture
def tiny(monkeypatch: pytest.MonkeyPatch) -> str:
    """Perfil corto y configuraciones chicas, sin tocar el pre-registro versionado."""
    monkeypatch.setitem(PROFILES, "tiny", Profile(12, 4, 8, 4))
    small = {key: dataclasses.replace(c, **SMALL) for key, c in PHASE2_PROTOCOL_CONFIGS.items()}
    monkeypatch.setattr(attribution, "PHASE2_PROTOCOL_CONFIGS", small)
    return "tiny"


@pytest.mark.parametrize(("runner", "name", "keys"), RUNNERS)
def test_cli_por_semilla_y_agregado(
    tmp_path: Path, tiny: str, runner: ModuleType, name: str, keys: tuple[str, str]
) -> None:
    sequential, parallel = tmp_path / "jobs1", tmp_path / "jobs2"
    for out, jobs in ((sequential, "1"), (parallel, "2")):
        argv = ["--profile", tiny, "--seeds", "7", "8", "--jobs", jobs, "--out", str(out)]
        assert runner.main(argv) == 0
    files = sorted(p.name for p in sequential.iterdir())
    assert files == [f"{name}_aggregate.json", f"{name}_seed7.json", f"{name}_seed8.json"]
    for file in files:
        assert (sequential / file).read_bytes() == (parallel / file).read_bytes(), file
    data = json.loads((sequential / f"{name}_seed7.json").read_text())
    assert data["profile"] == tiny and data["seed"] == 7
    small = attribution.PHASE2_PROTOCOL_CONFIGS
    calls = dict((key, call) for call, key in PROTOCOLS)
    for key in keys:
        config = dataclasses.replace(small[key], seed=7)
        section = data[f"protocol_{key}"]
        assert section["config"] == config.to_dict()
        expected = json.loads(json.dumps(dataclasses.asdict(calls[key](config, 12))))
        assert section["report"] == expected
    aggregate = json.loads((sequential / f"{name}_aggregate.json").read_text())
    assert aggregate["seeds"] == [7, 8] and aggregate["profile"] == tiny
    assert all(aggregate[f"protocol_{key}"]["total_ticks"]["n"] == 2 for key in keys)
    if name == "exp003":  # por nivel, con 0 en las semillas que no lo alcanzaron
        peaks = aggregate["protocol_003b"]["level_counts_peak"]
        assert [level for level, _ in peaks] == sorted(level for level, _ in peaks)
        assert all(stats["n"] == 2 for _, stats in peaks)


@pytest.mark.parametrize(("runner", "name", "keys"), RUNNERS)
def test_cli_una_semilla_no_escribe_agregado(
    tmp_path: Path, tiny: str, runner: ModuleType, name: str, keys: tuple[str, str]
) -> None:
    assert runner.main(["--profile", tiny, "--seeds", "7", "--out", str(tmp_path)]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == [f"{name}_seed7.json"]


@pytest.mark.parametrize(("runner", "name", "keys"), RUNNERS)
def test_cli_atribucion_con_pocas_semillas(
    tmp_path: Path,
    tiny: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runner: ModuleType,
    name: str,
    keys: tuple[str, str],
) -> None:
    monkeypatch.setattr(attribution, "PHASE2_ATTRIBUTION_PROFILE", tiny)
    # Las configuraciones chicas usan 6 recursos: se toman como la abundancia del perfil.
    monkeypatch.setattr(attribution, "PHASE2_RESOURCES_PER_PATTERN", SMALL["resources_per_pattern"])
    argv = ["--seeds", "42", "--attribution", "--profile", "quick", "--out", str(tmp_path)]
    assert runner.main(argv) == 0
    out = capsys.readouterr().out
    data = json.loads((tmp_path / f"{name}_attribution.json").read_text())
    assert data["profile"] == tiny
    assert [e["status"] for e in data["evaluations"]] == ["INSUFFICIENT_EVIDENCE"] * 2
    assert [r["rule_id"] for r in data["rules"]] == [f"R{i}" for i in range(1, 24)]
    claims = ("C5", "C6") if name == "exp002" else ("C7", "C8")
    assert [e["claim_id"] for e in data["evaluations"]] == list(claims)
    assert "Aviso" in out and f"perfil {tiny}" in out
    assert "E4 no interpretable" in out
    assert out.index("E4 no interpretable") < out.index("Afirmación")  # antes de la tabla
    assert all(e["e4_interpretable"] is False for e in data["evaluations"])
    for claim in claims:
        assert claim in out
    assert sorted(p.name for p in tmp_path.iterdir()) == [f"{name}_attribution.json"]


@pytest.mark.parametrize(("runner", "name", "keys"), RUNNERS)
@pytest.mark.parametrize("argv", [["--seeds", "-1"], ["--seeds", "3", "3"], ["--jobs", "0"]])
def test_cli_argumentos_invalidos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runner: ModuleType,
    name: str,
    keys: tuple[str, str],
    argv: list[str],
) -> None:
    def no_simular(*_: object, **__: object) -> None:
        raise AssertionError("no debe simular con argumentos inválidos")

    monkeypatch.setattr(phase2_cli, "map_in_order", no_simular)
    with pytest.raises(SystemExit) as exc:
        runner.main([*argv, "--out", str(tmp_path / "r")])
    assert exc.value.code == 2
    assert not (tmp_path / "r").exists()


def test_parser_por_defecto() -> None:
    for runner, _, _ in RUNNERS:
        args = runner.build_arg_parser().parse_args([])
        assert (args.profile, args.seeds, args.attribution) == ("phase2", None, False)
        assert args.jobs == default_jobs()  # los núcleos detectados (D62.3 y precisión 55)
        assert Path(args.out) == Path("results/")


def _affinity(_: int) -> set[int]:
    return {0, 1, 2}


def test_jobs_por_defecto_con_los_nucleos_detectados(monkeypatch: pytest.MonkeyPatch) -> None:
    """Escenarios de la spec "Procesos por Defecto con los Núcleos Detectados" (D62.3)."""
    monkeypatch.setattr(os, "sched_getaffinity", _affinity, raising=False)
    for runner, _, _ in RUNNERS:
        assert runner.build_arg_parser().parse_args([]).jobs == 3
    monkeypatch.delattr(os, "sched_getaffinity", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: None)
    for runner, _, _ in RUNNERS:
        assert runner.build_arg_parser().parse_args([]).jobs == 1


@pytest.mark.parametrize(("runner", "name", "keys"), RUNNERS)
def test_atribucion_usa_por_defecto_las_semillas_pre_registradas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runner: ModuleType,
    name: str,
    keys: tuple[str, str],
) -> None:
    received: list[Any] = []

    configs_received: list[Any] = []

    def fake(seeds: Any, claims: Any, jobs: int, configs: Any) -> Any:
        received.append(tuple(seeds))
        configs_received.append(configs)
        return attribution.AttributionReport("phase2", attribution.ALL_DESIGN_RULES, ())

    monkeypatch.setattr(phase2_cli, "run_phase2_attribution", fake)
    assert runner.main(["--attribution", "--out", str(tmp_path)]) == 0
    assert received == [attribution.PHASE2_SEEDS]
    assert configs_received[0] is attribution.PHASE2_PROTOCOL_CONFIGS  # sin --reference


def test_cli_corre_una_vez_cada_condicion_identica(
    tmp_path: Path, tiny: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """En 003, la condición `holonic` de 003-A es la `with_view` de 003-B: corre una vez."""
    sizes: list[int] = []
    original = phase2_cli.map_in_order

    def counting(function: Any, items: Any, jobs: int) -> Any:
        sizes.append(len(items))
        return original(function, items, jobs)

    monkeypatch.setattr(phase2_cli, "map_in_order", counting)
    assert exp003_runner.main(["--profile", tiny, "--seeds", "7", "--out", str(tmp_path)]) == 0
    assert sizes == [3]


def test_003b_rechaza_r18_tambien_en_la_cli(
    tmp_path: Path, tiny: str, capsys: pytest.CaptureFixture[str]
) -> None:
    configs = attribution.PHASE2_PROTOCOL_CONFIGS
    configs["003b"] = dataclasses.replace(configs["003b"], enable_downward_causation=True)
    with pytest.raises(SystemExit) as exc:
        exp003_runner.main(["--profile", tiny, "--seeds", "7", "--out", str(tmp_path / "r")])
    assert exc.value.code == 2
    assert "R18" in capsys.readouterr().err
    assert not (tmp_path / "r").exists()
    with pytest.raises(SystemExit) as exc:
        exp003_runner.main(["--attribution", "--seeds", "7", "--out", str(tmp_path / "r")])
    assert exc.value.code == 2
    assert not (tmp_path / "r").exists()


@pytest.mark.slow
@pytest.mark.parametrize("module", ["exp002_runner", "exp003_runner"])
def test_cli_determinista_entre_procesos(tmp_path: Path, module: str) -> None:
    outputs = []
    for hash_seed in ("0", "1"):
        out = tmp_path / hash_seed
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        command = [
            sys.executable, "-m", f"ide.experiments.{module}",
            "--profile", "quick", "--seeds", "42", "--out", str(out),
        ]  # fmt: skip
        subprocess.run(command, env=env, cwd=ROOT, check=True, capture_output=True, text=True)
        outputs.append({p.name: p.read_bytes() for p in sorted(out.iterdir())})
    assert outputs[0] == outputs[1]


def demography(engine: SimulationEngine) -> tuple[int, int]:
    return len(engine.agents), max(m.max_generation for m in engine.evolutionary_history)


def test_demografia_de_cada_condicion() -> None:
    """Enmienda 1 de D29: población final y generación máxima de cada condición, en orden."""
    config = protocol_config("002a", seed=5)
    report = run_protocol_002a_adaptation(config, TICKS)
    expected = [
        (name, *demography(run_engine(c)))
        for name, c in (
            ("evolved", config),
            ("frozen_genome", ablate(config, ["R13"])),
            ("drift", ablate(config, ["R12"])),
        )
    ]
    assert list(report.condition_demography) == expected
    b = run_protocol_002b_cultural_inheritance(protocol_config("002b", seed=6), 5)
    assert [name for name, _, _ in b.condition_demography] == ["cultural", "tabula_rasa"]
    c3 = protocol_config("003a", seed=7)
    a3 = run_protocol_003a_holonic_transition(c3, TICKS)
    assert list(a3.condition_demography) == [
        ("holonic", *demography(run_engine(c3))),
        ("individual", *demography(run_engine(ablate(c3, ["R15"])))),
    ]
    b3 = run_protocol_003b_orthogonalization(protocol_config("003b", seed=8), 5)
    assert [name for name, _, _ in b3.condition_demography] == ["with_view", "without_view"]


@pytest.mark.parametrize(("runner", "name", "keys"), RUNNERS)
def test_cli_referencia_con_configuraciones_originales(
    tmp_path: Path,
    tiny: str,
    monkeypatch: pytest.MonkeyPatch,
    runner: ModuleType,
    name: str,
    keys: tuple[str, str],
) -> None:
    """Enmienda 1 de D29: `--reference` corre sobre `PHASE2_PROTOCOL_CONFIGS_ORIGINAL`."""
    original = {
        k: dataclasses.replace(c, **{**SMALL, "resources_per_pattern": 3})
        for k, c in attribution.PHASE2_PROTOCOL_CONFIGS_ORIGINAL.items()
    }
    monkeypatch.setattr(attribution, "PHASE2_PROTOCOL_CONFIGS_ORIGINAL", original)
    argv = ["--profile", tiny, "--seeds", "7", "--reference", "--out", str(tmp_path)]
    assert runner.main(argv) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == [f"{name}_reference_seed7.json"]
    data = json.loads((tmp_path / f"{name}_reference_seed7.json").read_text())
    for key in keys:
        expected = dataclasses.replace(original[key], seed=7).to_dict()
        assert data[f"protocol_{key}"]["config"] == expected


def test_atribucion_de_referencia(
    tmp_path: Path, tiny: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: list[Any] = []

    def fake(seeds: Any, claims: Any, jobs: int, configs: Any) -> Any:
        received.append(configs)
        return attribution.AttributionReport("phase2", attribution.ALL_DESIGN_RULES, ())

    monkeypatch.setattr(phase2_cli, "run_phase2_attribution", fake)
    argv = ["--attribution", "--reference", "--seeds", "7", "--out", str(tmp_path)]
    assert exp002_runner.main(argv) == 0
    assert len(received) == 1
    assert received[0] is attribution.PHASE2_PROTOCOL_CONFIGS_ORIGINAL
    data = json.loads((tmp_path / "exp002_reference_attribution.json").read_text())
    original = attribution.PHASE2_PROTOCOL_CONFIGS_ORIGINAL
    assert data["configs"] == {key: original[key].to_dict() for key in sorted(original)}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["exp002_reference_attribution.json"]
