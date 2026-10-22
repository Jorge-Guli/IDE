"""Tests de los protocolos 001-A/B/C, la agregación y la CLI (`experimental-suite`)."""

import csv
import dataclasses
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.config import SimulationConfig
from ide.experiments.exp001_runner import (
    PROFILES,
    RECOVERY_WINDOW,
    TARGET_PATTERN,
    AblationPointResult,
    FalsificationReport,
    Profile,
    ResilienceReport,
    SurplusReport,
    aggregate_reports,
    build_arg_parser,
    default_jobs,
    main,
    recovery_ticks,
    report_to_dict,
    run_protocol_001a_surplus,
    run_protocol_001b_falsification,
    run_protocol_001c_resilience,
    run_tasks,
    sign_test_p_value,
)
from ide.experiments.metrics import TickMetrics

ROOT = Path(__file__).resolve().parents[1]

SURPLUS_FIELDS = [
    "collective_accuracy",
    "isolated_accuracy",
    "collective_surplus",
    "collective_accessible_coverage",
    "isolated_accessible_coverage",
    "collective_coverage",
    "isolated_coverage",
    "collective_individual_coverage_mean",
    "mean_messages_per_agent",
    "accuracy_gain_per_message",
    "propagation_t50",
    "propagation_t90",
]
FALSIFICATION_FIELDS = [
    "target_pattern",
    "injected_agents",
    "initial_injected_prevalence",
    "peak_false_prevalence",
    "final_false_prevalence",
    "ticks_to_extinction",
    "extinguished_or_contained",
]
ABLATION_FIELDS = [
    "ablation_fraction",
    "remaining_agents",
    "pre_ablation_coverage",
    "immediate_post_ablation_coverage",
    "final_recovered_coverage",
    "retention_ratio",
    "pre_ablation_accuracy",
    "recovery_ticks",
]
RESILIENCE_FIELDS = [
    "ablation_results",
    "discoverers_ablated_count",
    "remaining_agents_after_discoverer_ablation",
    "post_discoverer_ablation_prevalence",
    "final_social_persistence_prevalence",
    "social_persistence_ticks",
]


def names(cls: type) -> list[str]:
    return [f.name for f in dataclasses.fields(cls)]


def test_esquemas_exactos_de_los_reportes() -> None:
    assert names(SurplusReport) == SURPLUS_FIELDS
    assert names(FalsificationReport) == FALSIFICATION_FIELDS
    assert names(AblationPointResult) == ABLATION_FIELDS
    assert names(ResilienceReport) == RESILIENCE_FIELDS
    assert TARGET_PATTERN.label == "id=p_0"
    assert RECOVERY_WINDOW == 20


# --- Protocolos con corridas cortas ------------------------------------------------------------


@pytest.fixture(scope="module")
def surplus() -> SurplusReport:
    return run_protocol_001a_surplus(SimulationConfig(seed=42), total_ticks=50)


def test_001a_esquema_y_superavit(surplus: SurplusReport) -> None:
    assert isinstance(surplus, SurplusReport)
    assert surplus.collective_surplus == pytest.approx(
        surplus.collective_accuracy - surplus.isolated_accuracy, abs=1e-9
    )
    labels = [f"id=p_{i}" for i in range(12)]
    assert sorted(surplus.propagation_t50) == sorted(labels)
    assert sorted(surplus.propagation_t90) == sorted(labels)
    assert surplus.mean_messages_per_agent > 0
    assert surplus.accuracy_gain_per_message == pytest.approx(
        surplus.collective_surplus / surplus.mean_messages_per_agent, abs=1e-9
    )
    # La corrida aislada no tiene canal de consulta: su cobertura accesible es la individual.
    assert surplus.isolated_accessible_coverage <= 0.25 + 1e-9


def test_001a_sin_mensajes_no_hay_ganancia_por_mensaje() -> None:
    config = SimulationConfig(seed=42, max_queries_per_tick=0, max_broadcast_per_tick=0)
    report = run_protocol_001a_surplus(config, total_ticks=10)
    assert report.mean_messages_per_agent == pytest.approx(0.0, abs=1e-9)
    assert report.accuracy_gain_per_message is None


def test_001b_prevalencia_inicial_exacta() -> None:
    report = run_protocol_001b_falsification(
        SimulationConfig(seed=42), total_ticks=40, injection_tick=20
    )
    assert report.target_pattern == "id=p_0"
    assert report.injected_agents == 20
    assert report.initial_injected_prevalence == pytest.approx(0.25, abs=1e-9)
    assert report.peak_false_prevalence >= report.initial_injected_prevalence
    assert report.extinguished_or_contained == (
        report.final_false_prevalence < report.initial_injected_prevalence
    )
    if report.ticks_to_extinction is not None:
        assert 1 <= report.ticks_to_extinction <= 20


@pytest.fixture(scope="module")
def resilience() -> ResilienceReport:
    return run_protocol_001c_resilience(
        SimulationConfig(seed=42), warmup_ticks=30, post_ablation_ticks=25
    )


def test_001c_un_resultado_por_nivel(resilience: ResilienceReport) -> None:
    results = resilience.ablation_results
    assert [r.ablation_fraction for r in results] == [0.10, 0.30, 0.50, 0.70]
    assert [r.remaining_agents for r in results] == [72, 56, 40, 24]
    # Por determinismo, el estado antes de la ablación es el mismo en todos los niveles.
    assert len({r.pre_ablation_coverage for r in results}) == 1
    assert len({r.pre_ablation_accuracy for r in results}) == 1
    for r in results:
        pre = r.pre_ablation_coverage
        expected = r.immediate_post_ablation_coverage / pre if pre else 0.0
        assert r.retention_ratio == pytest.approx(expected, abs=1e-9)
        assert r.recovery_ticks is None or 1 <= r.recovery_ticks <= 25


def test_001c_ablacion_de_descubridores(resilience: ResilienceReport) -> None:
    assert resilience.discoverers_ablated_count >= 1
    assert resilience.remaining_agents_after_discoverer_ablation == (
        80 - resilience.discoverers_ablated_count
    )
    if resilience.social_persistence_ticks is not None:
        assert 1 <= resilience.social_persistence_ticks <= 25
        assert resilience.final_social_persistence_prevalence == pytest.approx(0.0, abs=1e-9)


# --- Recuperación (M5) -------------------------------------------------------------------------


def post_tick(tick: int, opportunities: int, correct: int) -> TickMetrics:
    return TickMetrics(
        tick, 1, 0.0, 0.0, 0.0, opportunities, correct, 0.0, 0.0, {}, {}, 0.0, 0, 0.0
    )


def test_ventana_sin_ticks_previos_a_la_ablacion() -> None:
    # k = 1..4: 0 de 10; k = 5: 50 de 10 (ventana 1..5 -> 50/50 = 1.0).
    post = [post_tick(100 + k, 10, 0) for k in range(1, 5)] + [post_tick(105, 10, 50)]
    assert recovery_ticks(post, 0.9) == 5
    # Con una precisión previa de 1.2 el umbral 0.9·1.2 = 1.08 es inalcanzable.
    assert recovery_ticks(post, 1.2) is None


def test_ventana_deslizante_de_20_ticks() -> None:
    # 20 ticks sin aciertos y luego aciertos plenos: la ventana k-19..k olvida el pasado.
    post = [post_tick(k, 1, 0) for k in range(1, 21)] + [post_tick(k, 1, 1) for k in range(21, 61)]
    k = recovery_ticks(post, 1.0)
    assert k is not None
    window = post[k - RECOVERY_WINDOW : k]
    assert sum(m.correct_decisions for m in window) / len(window) >= 0.9
    assert k == 38  # 18 aciertos de 20 en la ventana 19..38


def test_sin_precision_previa_no_hay_recuperacion_medible() -> None:
    # El umbral 0.9 · 0 se alcanzaría en k = 1: sin referencia, la recuperación no es medible.
    assert recovery_ticks([post_tick(1, 0, 0)], 0.0) is None
    assert recovery_ticks([post_tick(1, 10, 10), post_tick(2, 10, 10)], 0.0) is None
    assert recovery_ticks([], 0.5) is None


@given(st.lists(st.tuples(st.integers(0, 20), st.integers(0, 20)), max_size=40))
def test_sin_precision_previa_nunca_hay_recuperacion(pairs: list[tuple[int, int]]) -> None:
    post = [post_tick(k, n, min(c, n)) for k, (n, c) in enumerate(pairs, start=1)]
    assert recovery_ticks(post, 0.0) is None


# --- Prueba de signo y agregación --------------------------------------------------------------


def test_cinco_diferencias_positivas() -> None:
    assert sign_test_p_value([0.1, 0.2, 0.05, 0.3, 0.01]) == pytest.approx(0.03125, abs=1e-9)


def test_prueba_de_signo_descarta_ceros() -> None:
    assert sign_test_p_value([]) == 1.0
    assert sign_test_p_value([0.0, 0.0]) == 1.0
    assert sign_test_p_value([0.0, 0.1, 0.2]) == pytest.approx(0.25, abs=1e-9)
    assert sign_test_p_value([-0.1, -0.2]) == pytest.approx(1.0, abs=1e-9)
    assert sign_test_p_value([0.1, -0.2, 0.3]) == pytest.approx(0.5, abs=1e-9)


def make_surplus(**fields: Any) -> SurplusReport:
    base: dict[str, Any] = dict.fromkeys(SURPLUS_FIELDS, 0.0)
    base.update(propagation_t50={}, propagation_t90={}, accuracy_gain_per_message=None)
    base.update(fields)
    return SurplusReport(**base)


def test_valores_ausentes() -> None:
    reports = [
        make_surplus(propagation_t50={"id=p_3": 12}, collective_surplus=0.1),
        make_surplus(propagation_t50={"id=p_3": None}, collective_surplus=0.3),
    ]
    agg = aggregate_reports(reports)
    assert agg["propagation_t50"]["id=p_3"]["mean"] == pytest.approx(12, abs=1e-9)
    assert agg["propagation_t50"]["id=p_3"]["n"] == 1
    assert agg["collective_surplus"]["mean"] == pytest.approx(0.2, abs=1e-9)
    assert agg["collective_surplus"]["std"] == pytest.approx(0.1, abs=1e-9)  # ddof = 0
    assert agg["collective_surplus"]["n"] == 2
    assert agg["accuracy_gain_per_message"]["n"] == 0
    assert agg["surplus_sign_test_p"] == pytest.approx(0.25, abs=1e-9)


def test_agregacion_de_booleanos_y_cadenas() -> None:
    reports = [
        FalsificationReport("id=p_0", 20, 0.25, 0.3, 0.1, None, True),
        FalsificationReport("id=p_0", 20, 0.25, 0.4, 0.3, 7, False),
        FalsificationReport("id=p_0", 20, 0.25, 0.3, 0.0, 9, True),
    ]
    agg = aggregate_reports(reports)
    assert agg["extinguished_or_contained"] == pytest.approx(2 / 3, abs=1e-9)
    assert agg["target_pattern"] == "id=p_0"
    assert agg["ticks_to_extinction"]["n"] == 2
    assert agg["ticks_to_extinction"]["mean"] == pytest.approx(8, abs=1e-9)
    assert "surplus_sign_test_p" not in agg


def test_agregacion_de_resultados_por_nivel(resilience: ResilienceReport) -> None:
    agg = aggregate_reports([resilience, resilience])
    first = agg["ablation_results"][0]["remaining_agents"]
    assert first["mean"] == pytest.approx(72.0, abs=1e-9)
    assert first["std"] == pytest.approx(0.0, abs=1e-9)
    assert first["n"] == 2
    json.dumps(agg)


def test_report_to_dict_serializable(surplus: SurplusReport, resilience: ResilienceReport) -> None:
    for report in (surplus, resilience):
        data = report_to_dict(report)
        assert json.loads(json.dumps(data)) == data
    data = report_to_dict(resilience)
    assert isinstance(data["ablation_results"], list)
    assert data["ablation_results"][0]["remaining_agents"] == 72


# --- CLI ---------------------------------------------------------------------------------------


def test_valores_por_defecto_de_la_cli() -> None:
    args = build_arg_parser().parse_args([])
    assert args.profile == "full"
    assert args.seeds == [42]
    assert Path(args.out) == Path("results/")
    assert args.jobs == default_jobs()  # los núcleos detectados (D62.3 y precisión 55)


def _affinity(_: int) -> set[int]:
    return {0, 1, 2}


def test_jobs_por_defecto_con_los_nucleos_detectados(monkeypatch: pytest.MonkeyPatch) -> None:
    """Escenarios de la spec "Procesos por Defecto con los Núcleos Detectados" (D62.3)."""
    monkeypatch.setattr(os, "sched_getaffinity", _affinity, raising=False)
    assert build_arg_parser().parse_args([]).jobs == 3
    monkeypatch.delattr(os, "sched_getaffinity", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: None)
    assert build_arg_parser().parse_args([]).jobs == 1


def run_cli(out: Path, hash_seed: str, *extra: str) -> None:
    env = {**os.environ, "PYTHONHASHSEED": hash_seed}
    command = [sys.executable, "-m", "ide.experiments.exp001_runner", "--out", str(out), *extra]
    subprocess.run(command, env=env, cwd=ROOT, check=True, capture_output=True, text=True)


@pytest.fixture(scope="module")
def cli_runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Corridas `quick` en paralelo: `--jobs 1` y `--jobs 2` con el mismo hash, y otro hash."""
    dirs = {name: tmp_path_factory.mktemp(name) for name in ("jobs1", "jobs2", "hash1")}
    quick = ("--profile", "quick")
    with ThreadPoolExecutor(max_workers=3) as pool:
        runs = [
            pool.submit(run_cli, dirs["jobs1"], "0", *quick, "--seeds", "42", "43", "--jobs", "1"),
            pool.submit(run_cli, dirs["jobs2"], "0", *quick, "--seeds", "42", "43", "--jobs", "2"),
            pool.submit(run_cli, dirs["hash1"], "1", *quick, "--seeds", "42", "--jobs", "1"),
        ]
        for run in runs:
            run.result()
    return dirs


def test_paralelismo_inocuo(cli_runs: dict[str, Path]) -> None:
    sequential, parallel = cli_runs["jobs1"], cli_runs["jobs2"]
    files = sorted(p.name for p in sequential.iterdir())
    assert files == [
        "exp001_aggregate.json",
        "exp001_seed42.json",
        "exp001_seed43.json",
        "exp001a_seed42_timeseries.csv",
        "exp001a_seed43_timeseries.csv",
    ]
    assert sorted(p.name for p in parallel.iterdir()) == files
    for name in files:
        assert (sequential / name).read_bytes() == (parallel / name).read_bytes(), name


def test_determinismo_entre_procesos(cli_runs: dict[str, Path]) -> None:
    """`PYTHONHASHSEED=0` (corrida `jobs1`) contra `PYTHONHASHSEED=1`, con `--jobs 1`."""
    for name in ("exp001_seed42.json", "exp001a_seed42_timeseries.csv"):
        assert (cli_runs["jobs1"] / name).read_bytes() == (cli_runs["hash1"] / name).read_bytes()


def test_contenido_del_json_por_semilla(cli_runs: dict[str, Path]) -> None:
    data = json.loads((cli_runs["jobs1"] / "exp001_seed42.json").read_text())
    assert data["config"] == SimulationConfig(seed=42).to_dict()
    assert data["profile"] == "quick"
    assert sorted(data["protocol_001a"]) == sorted(SURPLUS_FIELDS)
    assert sorted(data["protocol_001b"]) == sorted(FALSIFICATION_FIELDS)
    assert sorted(data["protocol_001c"]) == sorted(RESILIENCE_FIELDS)
    aggregate = json.loads((cli_runs["jobs1"] / "exp001_aggregate.json").read_text())
    assert aggregate["seeds"] == [42, 43]
    assert aggregate["protocol_001a"]["collective_surplus"]["n"] == 2
    assert "surplus_sign_test_p" in aggregate["protocol_001a"]


def test_columnas_del_csv(cli_runs: dict[str, Path]) -> None:
    with (cli_runs["jobs1"] / "exp001a_seed42_timeseries.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))
    scalars = [
        f.name
        for f in dataclasses.fields(TickMetrics)
        if f.name not in ("pattern_prevalence", "pattern_false_prevalence")
    ]
    labels = sorted(f"id=p_{i}" for i in range(12))  # orden de `Pattern`: p_10 antes que p_2
    assert rows[0] == (
        ["mode", *scalars]
        + [f"prevalence[{label}]" for label in labels]
        + [f"false_prevalence[{label}]" for label in labels]
    )
    body = rows[1:]
    assert len(body) == 600
    assert [r[0] for r in body] == ["collective"] * 300 + ["isolated"] * 300
    assert [int(r[1]) for r in body[:3]] == [0, 1, 2]


def test_una_semilla_no_escribe_agregado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tiny = Profile(total_ticks=12, injection_tick=4, warmup_ticks=8, post_ablation_ticks=4)
    monkeypatch.setitem(PROFILES, "tiny", tiny)
    assert main(["--profile", "tiny", "--seeds", "7", "--out", str(tmp_path)]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "exp001_seed7.json",
        "exp001a_seed7_timeseries.csv",
    ]


def test_semillas_repetidas_se_rechazan(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--profile", "quick", "--seeds", "42", "42", "--out", str(tmp_path / "r")])
    assert exc.value.code == 2
    assert not (tmp_path / "r").exists()


@pytest.mark.parametrize(
    "argv",
    [["--seeds", "-1"], ["--seeds", "abc"], ["--out", "FILE"], ["--out", "FILE/sub"]],
)
def test_argumentos_invalidos_fallan_antes_de_simular(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]
) -> None:
    from ide.experiments import exp001_runner

    def no_simular(*_: object, **__: object) -> None:
        raise AssertionError("no debe simular con argumentos inválidos")

    monkeypatch.setattr(exp001_runner, "run_tasks", no_simular)
    (tmp_path / "FILE").write_text("x")
    argv = [a.replace("FILE", str(tmp_path / "FILE")) for a in argv]
    if "--out" not in argv:
        argv += ["--out", str(tmp_path / "r")]
    with pytest.raises(SystemExit) as exc:
        main(["--profile", "quick", *argv])
    assert exc.value.code == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == ["FILE"]
    assert (tmp_path / "FILE").read_text() == "x"


@pytest.mark.parametrize(
    ("call", "kwargs"),
    [
        (run_protocol_001a_surplus, {"total_ticks": 0}),
        (run_protocol_001b_falsification, {"total_ticks": 50, "injection_tick": 50}),
        (run_protocol_001b_falsification, {"total_ticks": 50, "injection_tick": -1}),
        (run_protocol_001c_resilience, {"warmup_ticks": 0}),
        (run_protocol_001c_resilience, {"post_ablation_ticks": 0}),
        (run_protocol_001b_falsification, {"injection_fraction": 1.5}),
        (run_protocol_001c_resilience, {"ablation_levels": (0.1, 1.5)}),
    ],
)
def test_parametros_invalidos(call: Any, kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        call(SimulationConfig(), **kwargs)


def test_unidad_de_trabajo_desconocida() -> None:
    profile = PROFILES["quick"]
    with pytest.raises(ValueError, match="desconocida"):
        run_tasks([(SimulationConfig(), profile, (42, "001C", None))], jobs=1)
    with pytest.raises(ValueError, match="nivel"):
        run_tasks([(SimulationConfig(), profile, (42, "001c", None))], jobs=1)
