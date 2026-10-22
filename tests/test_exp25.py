"""Tests del runner de los protocolos de la Fase II-B (`experimental-suite`, design D56 y D62.3).

Cubren la ejecución corta y la serialización JSON de `25a`, `25b`, `25c` y `25d`, sus
condiciones (incluidas `no_predation_drift` y `stable_drift`), el resumen por condición con los
registros genético y ecológico, los historiales opcionales, la CLI en sus tres modos (protocolos,
`--smoke` y `--attribution`) y el `--jobs` por defecto con los núcleos detectados.
"""

import dataclasses
import json
import multiprocessing
import os
import statistics
from pathlib import Path
from typing import Any

import pytest

from ide.config import SimulationConfig
from ide.experiments import attribution, exp25_runner, phase2_calibration
from ide.experiments.attribution import (
    NULL_CONTENT,
    PHASE25_CLAIMS,
    PHASE25_PROTOCOL_CONFIGS,
    PHASE25_RULE_EFFECT_SEEDS,
    PHASE25_SEEDS,
    ClaimStatus,
    Phase25ClaimEvaluation,
    Phase25Report,
    final_demography,
    phase25_conditions,
)
from ide.experiments.exp001_runner import PROFILES, Profile, report_to_dict
from ide.experiments.exp25_runner import (
    PHASE25_SPECS,
    Phase25ConditionSummary,
    Phase25ProtocolReport,
    build_arg_parser,
    main,
    run_phase25_condition,
    run_phase25_condition_histories,
    run_phase25_protocol,
)
from ide.experiments.metrics import EcologyTickMetrics, GeneticTickMetrics
from ide.simulation.engine import SimulationEngine
from ide.simulation.telemetry import EcologyMetricsObserver, GeneticMetricsObserver

SMALL = {"grid_width": 10, "grid_height": 10, "num_agents": 12}
TICKS = 40
TINY_TICKS = 12
PROTOCOLS = ("25a", "25b", "25c", "25d")

# Condiciones de cada protocolo, en el orden de `phase25_conditions` (D56).
CONDITIONS = {
    "25a": ["full", "drift", "no_predation", "no_predation_drift", NULL_CONTENT],
    "25b": ["full", "drift", NULL_CONTENT],
    "25c": ["full", "drift", NULL_CONTENT],
    "25d": ["full", "drift", "stable", "stable_drift", "no_learning", NULL_CONTENT],
}
LABELS = [(protocol, name) for protocol in PROTOCOLS for name in CONDITIONS[protocol]]

# Únicos campos de una corrida de la prueba de humo (D56): nada de las métricas de C13-C20.
SMOKE_KEYS = {
    "protocol",
    "condition",
    "seed",
    "termination",
    "error",
    "final_agents",
    "final_active_agents",
    "max_generation",
}
CLAIM_METRICS = sorted({claim.metric for claim in PHASE25_CLAIMS})


def protocol_config(key: str, seed: int = 5) -> SimulationConfig:
    return dataclasses.replace(PHASE25_PROTOCOL_CONFIGS[key], **SMALL, seed=seed)


@pytest.fixture
def tiny(monkeypatch: pytest.MonkeyPatch) -> str:
    """Perfil corto y protocolos chicos, sin tocar el pre-registro versionado."""
    monkeypatch.setitem(PROFILES, "tiny", Profile(TINY_TICKS, 4, 8, 4))
    small = {
        key: dataclasses.replace(config, **SMALL)
        for key, config in PHASE25_PROTOCOL_CONFIGS.items()
    }
    monkeypatch.setattr(attribution, "PHASE25_PROTOCOL_CONFIGS", small)
    return "tiny"


def as_json(value: Any) -> Any:
    return json.loads(json.dumps(report_to_dict(value), sort_keys=True))


# --- Condiciones (D56) -------------------------------------------------------------------------


def test_especificaciones_de_los_cuatro_protocolos() -> None:
    assert [spec.key for spec in PHASE25_SPECS] == list(PROTOCOLS)
    for spec in PHASE25_SPECS:
        config = protocol_config(spec.key)
        conditions = spec.conditions(config)
        assert list(conditions) == CONDITIONS[spec.key]
        assert conditions == phase25_conditions(spec.key, config)


def test_condiciones_de_25a() -> None:
    config = protocol_config("25a")
    c = PHASE25_SPECS[0].conditions(config)
    assert c["full"] == config
    assert c["drift"].reproduction_mode == "neutral"
    assert c["no_predation"].enable_predation is False
    assert c["no_predation"].reproduction_mode == config.reproduction_mode
    assert c["no_predation_drift"].enable_predation is False
    assert c["no_predation_drift"].reproduction_mode == "neutral"


def test_condiciones_de_25b_y_25c() -> None:
    for spec in PHASE25_SPECS[1:3]:
        names = list(spec.conditions(protocol_config(spec.key)))
        assert names == ["full", "drift", NULL_CONTENT]


def test_condiciones_de_25d() -> None:
    config = protocol_config("25d")
    c = PHASE25_SPECS[3].conditions(config)
    assert "no_predation" not in c
    assert c["stable"].world_shift_period == 0
    assert c["stable_drift"].world_shift_period == 0
    assert c["stable_drift"].reproduction_mode == "neutral"
    assert c["no_learning"].enable_internal_state is False
    assert c["no_learning"].enable_plasticity is False


def test_identidad_de_las_condiciones_estables() -> None:
    """`stable` y `stable_drift` de 25d son `full` y `drift` de 25a, con los mismos historiales."""
    a = PHASE25_SPECS[0].conditions(protocol_config("25a", seed=3))
    d = PHASE25_SPECS[3].conditions(protocol_config("25d", seed=3))
    assert d["stable"] == a["full"]
    assert d["stable_drift"] == a["drift"]
    for left, right in ((d["stable"], a["full"]), (d["stable_drift"], a["drift"])):
        left_run = run_phase25_condition_histories(left, TINY_TICKS)
        assert left_run == run_phase25_condition_histories(right, TINY_TICKS)


# --- Resumen por condición ---------------------------------------------------------------------


def test_resumen_por_condicion_de_25b() -> None:
    """Escenario de la spec: `25b` con `total_ticks=40`."""
    config = protocol_config("25b", seed=4)
    report = run_phase25_protocol("25b", config, TICKS)
    assert isinstance(report, Phase25ProtocolReport)
    assert (report.protocol, report.seed, report.total_ticks) == ("25b", 4, TICKS)
    assert list(report.conditions) == CONDITIONS["25b"]
    for name, condition in phase25_conditions("25b", config).items():
        summary = report.conditions[name]
        assert isinstance(summary, Phase25ConditionSummary)
        engine = SimulationEngine(condition)
        engine.run(TICKS)
        agents, active, generation = final_demography(engine)
        assert summary.final_agents == agents
        assert summary.final_active_agents == active
        assert summary.final_active_agents <= summary.final_agents
        assert summary.max_generation == generation
        assert summary.final_accuracy == pytest.approx(
            engine.history[-1].cumulative_decision_accuracy, abs=1e-9
        )
        assert isinstance(summary.last_genetic, GeneticTickMetrics)
        assert isinstance(summary.last_ecology, EcologyTickMetrics)
        assert summary.last_genetic == engine.genetic_history[-1]
        assert summary.last_ecology == engine.ecology_history[-1]


def test_campos_del_resumen() -> None:
    assert [f.name for f in dataclasses.fields(Phase25ConditionSummary)] == [
        "final_accuracy",
        "final_agents",
        "final_active_agents",
        "max_generation",
        "last_genetic",
        "last_ecology",
    ]


def test_historiales_genetico_y_ecologico() -> None:
    config = protocol_config("25a", seed=2)
    summary, histories = run_phase25_condition_histories(config, TINY_TICKS)
    assert summary == run_phase25_condition(config, TINY_TICKS)
    assert len(histories.genetic_history) == TINY_TICKS
    assert len(histories.ecology_history) == TINY_TICKS
    assert histories.genetic_history[-1] == summary.last_genetic
    assert histories.ecology_history[-1] == summary.last_ecology
    assert [m.tick for m in histories.genetic_history] == [
        m.tick for m in histories.ecology_history
    ]


@pytest.mark.parametrize("key", PROTOCOLS)
def test_ejecucion_corta_y_serializacion(key: str) -> None:
    """Escenario de la spec: cada protocolo con `total_ticks=40` y su reporte en JSON."""
    report = run_phase25_protocol(key, protocol_config(key), TICKS)
    data = as_json(report)
    assert data["protocol"] == key and data["total_ticks"] == TICKS
    assert sorted(data["conditions"]) == sorted(CONDITIONS[key])
    for summary in data["conditions"].values():
        assert summary["last_genetic"]["tick"] == summary["last_ecology"]["tick"]
        assert summary["final_active_agents"] <= summary["final_agents"]


def test_protocolo_desconocido() -> None:
    with pytest.raises(ValueError, match="protocolo"):
        run_phase25_protocol("002c", protocol_config("25a"), TICKS)


# --- --jobs por defecto con los núcleos detectados (D62.3 y precisión 55) ----------------------


def _affinity(_: int) -> set[int]:
    return {0, 1, 2}


def test_jobs_por_defecto_con_la_afinidad(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "sched_getaffinity", _affinity, raising=False)
    assert build_arg_parser().parse_args([]).jobs == 3
    assert phase2_calibration.build_arg_parser().parse_args([]).jobs == 3


def test_jobs_por_defecto_sin_afinidad(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(os, "sched_getaffinity", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: None)
    assert build_arg_parser().parse_args([]).jobs == 1
    assert phase2_calibration.build_arg_parser().parse_args([]).jobs == 1


def test_jobs_explicito() -> None:
    assert build_arg_parser().parse_args(["--jobs", "2"]).jobs == 2
    with pytest.raises(SystemExit):
        build_arg_parser().parse_args(["--jobs", "0"])


# --- CLI: modo protocolos ----------------------------------------------------------------------


def test_parser_por_defecto() -> None:
    args = build_arg_parser().parse_args([])
    assert args.seeds == list(PHASE25_SEEDS)
    assert args.profile == "phase25"
    assert (
        args.rule_effect_seeds is None
    )  # sólo con --attribution; por defecto, las pre-registradas
    assert (args.attribution, args.smoke, args.histories) == (False, False, False)
    assert Path(args.out) == Path("results/")


def test_modos_excluyentes(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--smoke", "--attribution", "--out", str(tmp_path / "r")])
    assert exc.value.code == 2


def test_semillas_repetidas(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--seeds", "7", "7", "--out", str(tmp_path / "r")])
    assert exc.value.code == 2
    assert not (tmp_path / "r").exists()


@pytest.mark.parametrize(
    "argv",
    [
        ["--rule-effect-seeds", "42"],
        ["--smoke", "--rule-effect-seeds", "42"],
        ["--rule-effect-seeds"],
        ["--attribution", "--profile", "quick"],
        ["--smoke", "--histories"],
        ["--attribution", "--histories"],
    ],
)
def test_opciones_que_no_aplican_al_modo(tmp_path: Path, argv: list[str]) -> None:
    """Una opción ajena al modo elegido es un error de argumentos, antes de crear `--out`."""
    with pytest.raises(SystemExit) as exc:
        main([*argv, "--out", str(tmp_path / "r")])
    assert exc.value.code == 2
    assert not (tmp_path / "r").exists()


@pytest.mark.parametrize("mode", [[], ["--smoke"], ["--attribution"]])
def test_configuracion_que_no_respeta_su_protocolo(
    tmp_path: Path, tiny: str, monkeypatch: pytest.MonkeyPatch, mode: list[str]
) -> None:
    """`_check_phase25_protocol` rechaza la configuración antes de crear `--out` (código 2)."""
    broken = dict(attribution.PHASE25_PROTOCOL_CONFIGS)
    broken["25a"] = dataclasses.replace(broken["25a"], enable_predation=False)
    monkeypatch.setattr(attribution, "PHASE25_PROTOCOL_CONFIGS", broken)
    profile = [] if mode == ["--attribution"] else ["--profile", tiny]
    with pytest.raises(SystemExit) as exc:
        main([*mode, *profile, "--seeds", "7", "--jobs", "1", "--out", str(tmp_path / "r")])
    assert exc.value.code == 2
    assert not (tmp_path / "r").exists()


def test_falta_un_protocolo(tmp_path: Path, tiny: str, monkeypatch: pytest.MonkeyPatch) -> None:
    partial = {k: v for k, v in attribution.PHASE25_PROTOCOL_CONFIGS.items() if k != "25c"}
    monkeypatch.setattr(attribution, "PHASE25_PROTOCOL_CONFIGS", partial)
    with pytest.raises(SystemExit) as exc:
        main(["--profile", tiny, "--seeds", "7", "--out", str(tmp_path / "r")])
    assert exc.value.code == 2
    assert not (tmp_path / "r").exists()


def test_protocolo_valida_su_configuracion() -> None:
    config = dataclasses.replace(protocol_config("25c"), comm_propensity_base=0.5)
    with pytest.raises(ValueError, match="25c"):
        run_phase25_protocol("25c", config, TICKS)


def test_out_inutilizable(tmp_path: Path, tiny: str) -> None:
    blocker = tmp_path / "archivo"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["--profile", tiny, "--seeds", "7", "--out", str(blocker / "sub")])
    assert exc.value.code == 2


def condition_files(profile: str) -> list[str]:
    return sorted(f"exp25_{profile}_{protocol}_{name}.json" for protocol, name in LABELS)


def history_files(profile: str, seeds: tuple[int, ...]) -> list[str]:
    return sorted(
        f"exp25_{profile}_{protocol}_{name}_seed{seed}_histories.json"
        for protocol, name in LABELS
        for seed in seeds
    )


def test_cli_de_protocolos(tmp_path: Path, tiny: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Un JSON por condición, con el perfil en el nombre, idéntico con `--jobs 1` y `--jobs 2`."""
    sequential, parallel = tmp_path / "jobs1", tmp_path / "jobs2"
    for out, jobs in ((sequential, "1"), (parallel, "2")):
        argv = ["--profile", tiny, "--seeds", "7", "8", "--jobs", jobs, "--out", str(out)]
        assert main(argv) == 0
    files = sorted(p.name for p in sequential.iterdir())
    assert files == condition_files(tiny)
    for file in files:
        assert (sequential / file).read_bytes() == (parallel / file).read_bytes(), file
    small = attribution.PHASE25_PROTOCOL_CONFIGS
    for protocol, name in LABELS:
        data = json.loads((sequential / f"exp25_{tiny}_{protocol}_{name}.json").read_text())
        assert (data["protocol"], data["condition"]) == (protocol, name)
        assert (data["profile"], data["total_ticks"], data["seeds"]) == (tiny, TINY_TICKS, [7, 8])
        assert [run["seed"] for run in data["runs"]] == [7, 8]
        for run in data["runs"]:
            condition = phase25_conditions(
                protocol, dataclasses.replace(small[protocol], seed=run["seed"])
            )[name]
            assert run["config"] == condition.to_dict()
            assert run["summary"] == as_json(run_phase25_condition(condition, TINY_TICKS))
            assert "histories" not in run
    output = capsys.readouterr().out
    assert "25d stable_drift" in output
    # La consola del modo protocolos sólo muestra demografía, nunca las métricas de C13-C20.
    assert not any(metric in output for metric in CLAIM_METRICS)


def test_cli_con_historiales(tmp_path: Path, tiny: str) -> None:
    """Historiales con perfil, semilla y configuración, idénticos con `--jobs 1` y `--jobs 2`."""
    outs = {jobs: tmp_path / f"jobs{jobs}" for jobs in ("1", "2")}
    for jobs, out in outs.items():
        argv = ["--profile", tiny, "--seeds", "7", "8", "--jobs", jobs, "--histories"]
        assert main([*argv, "--out", str(out)]) == 0
    histories = sorted(p.name for p in outs["1"].iterdir() if p.name.endswith("_histories.json"))
    assert histories == history_files(tiny, (7, 8))
    for file in sorted(p.name for p in outs["1"].iterdir()):
        assert (outs["1"] / file).read_bytes() == (outs["2"] / file).read_bytes(), file
    small = attribution.PHASE25_PROTOCOL_CONFIGS
    condition = phase25_conditions("25d", dataclasses.replace(small["25d"], seed=7))["full"]
    _, expected = run_phase25_condition_histories(condition, TINY_TICKS)
    data = json.loads((outs["1"] / f"exp25_{tiny}_25d_full_seed7_histories.json").read_text())
    assert (data["profile"], data["protocol"], data["condition"]) == (tiny, "25d", "full")
    assert (data["seed"], data["total_ticks"]) == (7, TINY_TICKS)
    assert data["config"] == condition.to_dict()
    assert data["genetic_history"] == as_json(expected.genetic_history)
    assert data["ecology_history"] == as_json(expected.ecology_history)
    assert len(data["genetic_history"]) == TINY_TICKS
    # `stable` de 25d es `full` de 25a: una sola corrida, dos archivos con sus propias etiquetas.
    stable = json.loads((outs["1"] / f"exp25_{tiny}_25d_stable_seed7_histories.json").read_text())
    full = json.loads((outs["1"] / f"exp25_{tiny}_25a_full_seed7_histories.json").read_text())
    assert (stable["protocol"], stable["condition"]) == ("25d", "stable")
    assert stable["genetic_history"] == full["genetic_history"]


def test_historiales_se_escriben_al_terminar_cada_corrida(
    tmp_path: Path, tiny: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cada corrida escribe sus historiales al terminar: no se acumulan hasta el final."""
    written_before: list[int] = []
    original = exp25_runner.run_phase25_condition_histories

    def spying(config: SimulationConfig, total_ticks: int) -> Any:
        written_before.append(len(list(tmp_path.glob("*_histories.json"))))
        return original(config, total_ticks)

    monkeypatch.setattr(exp25_runner, "run_phase25_condition_histories", spying)
    argv = ["--profile", tiny, "--seeds", "7", "--jobs", "1", "--histories"]
    assert main([*argv, "--out", str(tmp_path)]) == 0
    # Antes de la corrida k ya están los historiales de las k anteriores (alguna escribe dos).
    assert all(count >= k for k, count in enumerate(written_before))
    assert len(list(tmp_path.glob("*_histories.json"))) == len(LABELS)


def test_condiciones_identicas_corren_una_vez(
    tmp_path: Path, tiny: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[SimulationConfig] = []
    original = exp25_runner.run_phase25_condition_histories

    def counting(config: SimulationConfig, total_ticks: int) -> Any:
        calls.append(config)
        return original(config, total_ticks)

    monkeypatch.setattr(exp25_runner, "run_phase25_condition_histories", counting)
    assert main(["--profile", tiny, "--seeds", "7", "--jobs", "1", "--out", str(tmp_path)]) == 0
    # 17 condiciones; `stable` y `stable_drift` de 25d repiten `full` y `drift` de 25a.
    assert len(calls) == len(LABELS) - 2
    assert len(set(calls)) == len(calls)


# --- CLI: prueba de humo (D56) -----------------------------------------------------------------


def _forbidden(*_: Any, **__: Any) -> Any:
    raise AssertionError("la prueba de humo no calcula resúmenes, historiales ni métricas")


@pytest.fixture
def no_claim_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    """La prueba de humo no arma resúmenes, historiales ni métricas de afirmación (D56).

    La telemetría de evolución abierta queda vetada: si un motor de la prueba de humo la
    notificara, su corrida fallaría y se registraría con `termination == "error"`. Los parches
    llegan a los procesos de `--jobs 2` porque se crean con `fork`.
    """
    monkeypatch.setattr(exp25_runner, "run_phase25_condition", _forbidden)
    monkeypatch.setattr(exp25_runner, "run_phase25_condition_histories", _forbidden)
    monkeypatch.setattr(attribution, "phase25_metric_value", _forbidden)
    monkeypatch.setattr(attribution, "phase25_run_record", _forbidden)
    for observer in (GeneticMetricsObserver, EcologyMetricsObserver):
        monkeypatch.setattr(observer, "on_decisions", _forbidden)
        monkeypatch.setattr(observer, "on_tick_end", _forbidden)


requires_fork = pytest.mark.skipif(
    multiprocessing.get_start_method() != "fork",
    reason="los parches del test sólo llegan a los procesos hijos con fork",
)


@requires_fork
@pytest.mark.usefixtures("no_claim_metrics")
def test_prueba_de_humo(tmp_path: Path, tiny: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Sólo terminación, generación máxima y población final; sin métricas de afirmación."""
    outs = {jobs: tmp_path / f"jobs{jobs}" for jobs in ("1", "2")}
    for jobs, out in outs.items():
        argv = ["--smoke", "--profile", tiny, "--seeds", "7", "8", "--jobs", jobs]
        assert main([*argv, "--out", str(out)]) == 0
    name = f"exp25_{tiny}_smoke.json"
    assert sorted(p.name for p in outs["1"].iterdir()) == [name]
    assert (outs["1"] / name).read_bytes() == (outs["2"] / name).read_bytes()
    data = json.loads((outs["1"] / name).read_text())
    assert (data["profile"], data["total_ticks"], data["seeds"]) == (tiny, TINY_TICKS, [7, 8])
    small = attribution.PHASE25_PROTOCOL_CONFIGS
    assert data["configs"] == {key: small[key].to_dict() for key in PROTOCOLS}
    runs = data["runs"]
    assert [(r["protocol"], r["condition"], r["seed"]) for r in runs] == [
        (protocol, name, seed) for protocol, name in LABELS for seed in (7, 8)
    ]
    for run in runs:
        assert set(run) == SMOKE_KEYS
        condition = phase25_conditions(
            run["protocol"], dataclasses.replace(small[run["protocol"]], seed=run["seed"])
        )[run["condition"]]
        engine = SimulationEngine(condition)
        engine.telemetry_observers.clear()  # vetada por el fixture; no cambia la demografía
        engine.run(TINY_TICKS)
        agents, active, generation = final_demography(engine)
        assert (run["termination"], run["error"]) == ("finished", None)
        assert (run["final_agents"], run["final_active_agents"]) == (agents, active)
        assert run["max_generation"] == generation
    output = capsys.readouterr().out
    assert "25a no_predation_drift" in output
    assert not any(metric in output for metric in CLAIM_METRICS)


def test_motores_de_la_prueba_de_humo_sin_telemetria(
    tmp_path: Path, tiny: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """En el mismo proceso: sin `telemetry_observers` ni historiales genético y ecológico."""
    engines: list[SimulationEngine] = []

    class Recording(SimulationEngine):
        def __init__(self, config: SimulationConfig) -> None:
            super().__init__(config)
            engines.append(self)

    monkeypatch.setattr(exp25_runner, "SimulationEngine", Recording)
    argv = ["--smoke", "--profile", tiny, "--seeds", "7", "--jobs", "1"]
    assert main([*argv, "--out", str(tmp_path)]) == 0
    assert len(engines) == len(LABELS) - 2  # las configuraciones idénticas corren una vez
    for engine in engines:
        assert engine.next_tick == TINY_TICKS
        assert engine.telemetry_observers == []
        assert engine.genetic_history == [] and engine.ecology_history == []


@requires_fork
@pytest.mark.parametrize("jobs", ["1", "2"])
def test_prueba_de_humo_registra_las_fallas(
    tmp_path: Path,
    tiny: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    jobs: str,
) -> None:
    """Una corrida que falla se registra con su tipo y mensaje, sin abortar las demás."""

    class Failing(SimulationEngine):
        def run(self, num_ticks: int) -> Any:
            if self.config.seed == 8 and not self.config.enable_predation:
                raise RuntimeError(f"falla simulada en la semilla {self.config.seed}")
            return super().run(num_ticks)

    monkeypatch.setattr(exp25_runner, "SimulationEngine", Failing)
    argv = ["--smoke", "--profile", tiny, "--seeds", "7", "8", "--jobs", jobs]
    assert main([*argv, "--out", str(tmp_path)]) == 1
    data = json.loads((tmp_path / f"exp25_{tiny}_smoke.json").read_text())
    assert len(data["runs"]) == 2 * len(LABELS)
    for run in data["runs"]:
        assert set(run) == SMOKE_KEYS
        failed = run["seed"] == 8 and run["condition"] in ("no_predation", "no_predation_drift")
        if failed:
            assert run["termination"] == "error"
            assert run["error"] == {
                "type": "RuntimeError",
                "message": "falla simulada en la semilla 8",
            }
            assert run["final_agents"] is None and run["max_generation"] is None
            assert run["final_active_agents"] is None
        else:
            assert (run["termination"], run["error"]) == ("finished", None)
            assert isinstance(run["final_agents"], int)
    assert "RuntimeError" in capsys.readouterr().out


# --- CLI: atribución ---------------------------------------------------------------------------


def fake_evaluation(claim_id: str, seeds: list[int]) -> Phase25ClaimEvaluation:
    conditions = ("full", "drift")
    record = {
        "final_agents": 10.0,
        "final_active_agents": 9.0,
        "max_generation": 25.0,
        "cumulative_births": 40.0,
        "cumulative_deaths": 30.0,
        "mean_age_at_death": 12.0,
        "effective_parents": 5.0,
    }
    return Phase25ClaimEvaluation(
        claim_id=claim_id,
        status=ClaimStatus.NOT_OBSERVED,
        p_value=0.5,
        p_adjusted=None if claim_id == "C20" else 1.0,
        median_difference=0.25,
        values={s: 1.0 for s in seeds},
        comparison_values={s: 0.75 + 0.01 * i for i, s in enumerate(seeds)},
        demography={c: {s: dict(record) for s in seeds} for c in conditions},
        e4_p_value=0.25,
        e4_interpretable=False,
        excluded_seeds=(seeds[0],),
        excluded_pairs=1,
        evaluable=False,
    )


def test_cli_de_atribucion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    received: dict[str, Any] = {}
    seeds = list(PHASE25_SEEDS)

    def fake(
        seeds: Any, claims: Any, jobs: int, configs: Any, rule_effect_seeds: Any
    ) -> Phase25Report:
        received.update(
            seeds=list(seeds),
            claims=claims,
            jobs=jobs,
            configs=configs,
            rule=list(rule_effect_seeds),
        )
        return Phase25Report(
            evaluations=tuple(fake_evaluation(c.claim_id, list(seeds)) for c in claims),
            rule_effects={c.claim_id: {"R12": 0.5, "R37": None} for c in claims},
        )

    monkeypatch.setattr(exp25_runner, "run_phase25_attribution", fake)
    out = tmp_path / "r"
    assert main(["--attribution", "--jobs", "3", "--out", str(out)]) == 0
    assert received["seeds"] == seeds
    assert received["claims"] == PHASE25_CLAIMS
    assert received["jobs"] == 3
    assert received["rule"] == list(PHASE25_RULE_EFFECT_SEEDS)
    assert received["configs"] == attribution.PHASE25_PROTOCOL_CONFIGS
    assert sorted(p.name for p in out.iterdir()) == ["exp25_phase25_attribution.json"]
    data = json.loads((out / "exp25_phase25_attribution.json").read_text())
    assert data["profile"] == "phase25"
    assert data["seeds"] == seeds
    assert data["rule_effect_seeds"] == list(PHASE25_RULE_EFFECT_SEEDS)
    assert [e["claim_id"] for e in data["evaluations"]] == [c.claim_id for c in PHASE25_CLAIMS]
    assert data["rule_effects"]["C13"] == {"R12": 0.5, "R37": None}
    assert data["valid_pairs"]["C13"] == len(seeds) - 1
    # Umbral: max(δ_min, delta_relative · mediana de comparison_values en los pares válidos).
    valid = [0.75 + 0.01 * i for i in range(1, len(seeds))]
    expected = max(0.001, 0.25 * statistics.median(valid))
    assert data["thresholds"]["C16"] == pytest.approx(expected, abs=1e-9)
    assert data["thresholds"]["C13"] == pytest.approx(1.0, abs=1e-9)
    assert sorted(data["configs"]) == list(PROTOCOLS)
    output = capsys.readouterr().out
    for header in ("Estado", "p crudo", "p ajustado", "Mediana", "Umbral", "Pares", "E4"):
        assert header in output
    assert "C20" in output and "not_observed" in output.lower()


def test_atribucion_real_corta(tmp_path: Path, tiny: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Integración con `run_phase25_attribution`, perfil corto y sin `rule_effects`."""
    monkeypatch.setitem(PROFILES, "phase25", PROFILES[tiny])
    out = tmp_path / "r"
    argv = ["--attribution", "--seeds", "7", "8", "--rule-effect-seeds", "--jobs", "1"]
    assert main([*argv, "--out", str(out)]) == 0
    data = json.loads((out / "exp25_phase25_attribution.json").read_text())
    assert data["seeds"] == [7, 8] and data["rule_effect_seeds"] == []
    assert all(e["evaluable"] is False for e in data["evaluations"])  # menos de 20 pares
    assert all(effects == {} or all(v is None for v in effects.values())
               for effects in data["rule_effects"].values())  # fmt: skip


def test_atribucion_acepta_el_perfil_pre_registrado(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--profile phase25` con `--attribution` es redundante y se acepta; queda en el JSON."""

    def fake(seeds: Any, claims: Any, jobs: int, configs: Any, rule_effect_seeds: Any) -> Any:
        return Phase25Report(
            evaluations=tuple(fake_evaluation(c.claim_id, list(seeds)) for c in claims),
            rule_effects={c.claim_id: {} for c in claims},
        )

    monkeypatch.setattr(exp25_runner, "run_phase25_attribution", fake)
    argv = ["--attribution", "--profile", "phase25", "--jobs", "1", "--out", str(tmp_path)]
    assert main(argv) == 0
    data = json.loads((tmp_path / "exp25_phase25_attribution.json").read_text())
    assert data["profile"] == "phase25"
