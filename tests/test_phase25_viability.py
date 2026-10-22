"""Tests de la compuerta de viabilidad de la Fase II-B (design D55, D62.3 y precisión 55)."""

import ast
import dataclasses
import inspect
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.config import SimulationConfig
from ide.experiments import attribution, exp001_runner, phase25_viability
from ide.experiments.attribution import (
    NULL_CONTENT,
    PHASE25_PROTOCOL_CONFIGS,
    PHASE25_SEEDS,
    final_demography,
    phase25_conditions,
)
from ide.experiments.exp001_runner import PROFILES
from ide.experiments.phase25_viability import (
    AMENDMENT2_DEFAULT_OUT,
    AMENDMENT2_GRID,
    DECIDING_CONDITIONS,
    DEFAULT_OUT,
    MIN_GENERATION,
    MIN_VIABLE_SEEDS,
    NOT_PREREGISTERED,
    ORIGINAL_RECORD,
    VIABILITY_GRID,
    Amendment2Report,
    ConfigurationResult,
    ViabilityReport,
    ViabilityRun,
    build_arg_parser,
    deciding_viable_seeds,
    default_jobs,
    fallback_configuration,
    is_viable_configuration,
    main,
    report_from_json,
    report_to_json,
    run_amendment2,
    run_viability,
    viability_conditions,
)
from ide.simulation.engine import SimulationEngine

SMALL = {"grid_width": 10, "grid_height": 10, "num_agents": 12}
FEW_SEEDS = (0, 1)

# (protocolo, condición) de los cuatro protocolos de D56, en el orden de `phase25_conditions`.
LABELS = [
    ("25a", "full"), ("25a", "drift"), ("25a", "no_predation"), ("25a", "no_predation_drift"),
    ("25a", "null_content"),
    ("25b", "full"), ("25b", "drift"), ("25b", "null_content"),
    ("25c", "full"), ("25c", "drift"), ("25c", "null_content"),
    ("25d", "full"), ("25d", "drift"), ("25d", "stable"), ("25d", "stable_drift"),
    ("25d", "no_learning"), ("25d", "null_content"),
]  # fmt: skip

# Únicos campos de una corrida: la compuerta registra sólo demografía (D55.1).
RUN_KEYS = {
    "seed",
    "termination",
    "final_agents",
    "final_active_agents",
    "max_generation",
    "viable",
}


def run(
    protocol: str, condition: str, seed: int, active: int = 5, generation: int = 25
) -> ViabilityRun:
    return ViabilityRun(protocol, condition, seed, active, active, generation)


def all_runs(**exceptions: int) -> list[ViabilityRun]:
    """Corridas viables en las 10 semillas, salvo `protocolo__condición = semillas viables`."""
    found: list[ViabilityRun] = []
    for protocol, condition in LABELS:
        viable = exceptions.get(f"{protocol}__{condition}", 10)
        found += [
            run(protocol, condition, seed, active=5 if seed < viable else 0) for seed in range(10)
        ]
    return found


# --- Lo declarado (D55) ------------------------------------------------------------------------


def test_semillas_reexportadas_de_attribution() -> None:
    """Una sola definición en `attribution.py` (precisión 118), disjunta de `PHASE25_SEEDS`."""
    assert phase25_viability.PHASE25_VIABILITY_SEEDS is attribution.PHASE25_VIABILITY_SEEDS
    assert tuple(range(0, 10)) == phase25_viability.PHASE25_VIABILITY_SEEDS
    assert not set(phase25_viability.PHASE25_VIABILITY_SEEDS) & set(PHASE25_SEEDS)


def test_procedimiento_declarado() -> None:
    assert VIABILITY_GRID == ((20, 20), (20, 10), (30, 20), (30, 10), (40, 40), (40, 20))
    assert (MIN_VIABLE_SEEDS, MIN_GENERATION) == (9, 20)
    assert DECIDING_CONDITIONS == (
        "full",
        "drift",
        "no_predation",
        "no_predation_drift",
        "stable",
        "stable_drift",
        "no_learning",
    )
    assert NULL_CONTENT not in DECIDING_CONDITIONS


def test_condiciones_de_los_cuatro_protocolos() -> None:
    found = viability_conditions(PHASE25_PROTOCOL_CONFIGS)
    assert [(p, c) for p, c, _ in found] == LABELS
    for protocol, condition, config in found:
        expected = phase25_conditions(protocol, PHASE25_PROTOCOL_CONFIGS[protocol])[condition]
        assert config == expected


# --- Criterio por corrida (D55.3) --------------------------------------------------------------


@pytest.mark.parametrize(
    ("agents", "active", "generation", "viable"),
    [
        (30, 30, 19, False),  # generación insuficiente
        (30, 0, 25, False),  # sólo endosporas
        (0, 0, 40, False),  # extinta
        (1, 1, 20, True),
        (12, 3, 31, True),
    ],
)
def test_criterio_de_una_corrida(agents: int, active: int, generation: int, viable: bool) -> None:
    result = ViabilityRun("25a", "full", 0, agents, active, generation)
    assert result.viable is viable
    assert result.termination == ("alive" if agents > 0 else "extinct")


# --- Criterio por configuración (D55.3) --------------------------------------------------------


def test_todas_viables() -> None:
    assert is_viable_configuration(all_runs())


@pytest.mark.parametrize(
    "condition",
    [
        "25a__no_predation",
        "25a__no_predation_drift",
        "25d__no_learning",
        "25d__stable_drift",
        "25d__stable",
        "25b__drift",
        "25c__full",
    ],
)
def test_una_condicion_inviable_descarta_la_configuracion(condition: str) -> None:
    assert not is_viable_configuration(all_runs(**{condition: 8}))


def test_nueve_de_diez_alcanza() -> None:
    nine = {f"{p}__{c}": 9 for p, c in LABELS if c != NULL_CONTENT}
    assert is_viable_configuration(all_runs(**nine))


def test_el_control_nulo_no_decide() -> None:
    nine = {f"{p}__{c}": 9 for p, c in LABELS if c != NULL_CONTENT}
    assert is_viable_configuration(all_runs(**nine, **{"25a__null_content": 3}))
    nulls = {f"{p}__null_content": 0 for p in ("25a", "25b", "25c", "25d")}
    assert is_viable_configuration(all_runs(**nulls))


def test_falta_una_condicion() -> None:
    runs = [r for r in all_runs() if (r.protocol, r.condition) != ("25d", "stable_drift")]
    assert not is_viable_configuration(runs)


# --- Grilla, detención y deduplicación ---------------------------------------------------------


@pytest.fixture
def small(monkeypatch: pytest.MonkeyPatch) -> None:
    """Protocolos chicos y dos semillas, sin tocar lo declarado."""
    original = attribution.phase25_protocol_configs

    def small_configs(rpp: int, delay: int) -> dict[str, SimulationConfig]:
        return {k: dataclasses.replace(c, **SMALL) for k, c in original(rpp, delay).items()}

    monkeypatch.setattr(attribution, "phase25_protocol_configs", small_configs)
    monkeypatch.setattr(phase25_viability, "PHASE25_VIABILITY_SEEDS", FEW_SEEDS)
    monkeypatch.setattr(attribution, "PHASE25_VIABILITY_SEEDS", FEW_SEEDS)
    monkeypatch.setattr(phase25_viability, "MIN_VIABLE_SEEDS", 2)


Demography = Callable[[tuple[SimulationConfig, int]], tuple[int, int, int]]


def fake_demography(viable_at: set[tuple[int, int]], calls: list[Any]) -> Demography:
    """Demografía simulada: viable sólo en las abundancias de `viable_at`."""

    def demography(task: tuple[SimulationConfig, int]) -> tuple[int, int, int]:
        config, _ = task
        calls.append(task)
        if (config.resources_per_pattern, config.resource_regen_delay) in viable_at:
            return 10, 10, 30
        return 0, 0, 3

    return demography


def test_detencion_en_la_primera_viable(small: None, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(phase25_viability, "demography", fake_demography({(20, 10)}, calls))
    report = run_viability(total_ticks=7, jobs=1)
    assert report.chosen == (20, 10)
    assert [c.abundance for c in report.configurations] == [(20, 20), (20, 10)]
    assert [c.viable for c in report.configurations] == [False, True]
    assert {(c.resources_per_pattern, c.resource_regen_delay) for c, _ in calls} == {
        (20, 20),
        (20, 10),
    }
    for configuration in report.configurations:
        expected = [(p, c, s) for p, c in LABELS for s in FEW_SEEDS]
        assert [(r.protocol, r.condition, r.seed) for r in configuration.runs] == expected


def test_sin_viables_recorre_la_grilla_en_orden(
    small: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(phase25_viability, "demography", fake_demography(set(), calls))
    report = run_viability(total_ticks=7, jobs=1)
    assert report.chosen is None
    assert [c.abundance for c in report.configurations] == list(VIABILITY_GRID)
    seen = list(dict.fromkeys((c.resources_per_pattern, c.resource_regen_delay) for c, _ in calls))
    assert seen == list(VIABILITY_GRID)  # en orden, y nada fuera de la grilla


def test_solo_cambia_la_abundancia(small: None, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(phase25_viability, "demography", fake_demography({(20, 20)}, calls))
    run_viability(total_ticks=7, jobs=1)
    configs = attribution.phase25_protocol_configs(20, 20)
    expected = {
        dataclasses.replace(config, seed=seed)
        for _, _, config in viability_conditions(configs)
        for seed in FEW_SEEDS
    }
    assert {config for config, _ in calls} == expected
    assert all(ticks == 7 for _, ticks in calls)


def test_configuraciones_identicas_corren_una_vez(
    small: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`stable` y `stable_drift` de 25d son `full` y `drift` de 25a (D56): corren una vez, y
    cada corrida recibe la demografía de su propia configuración."""
    configs = attribution.phase25_protocol_configs(20, 20)
    planned = {
        (p, c, seed): dataclasses.replace(config, seed=seed)
        for p, c, config in viability_conditions(configs)
        for seed in FEW_SEEDS
    }
    unique = list(dict.fromkeys(planned.values()))
    # Valores distintos por configuración: identifican protocolo, condición y semilla.
    values = {config: (i + 1, i + 1, MIN_GENERATION + i) for i, config in enumerate(unique)}
    calls: list[SimulationConfig] = []

    def identifying(task: tuple[SimulationConfig, int]) -> tuple[int, int, int]:
        calls.append(task[0])
        return values[task[0]]

    monkeypatch.setattr(phase25_viability, "demography", identifying)
    report = run_viability(total_ticks=7, jobs=1)
    assert calls == unique
    assert len(unique) == (len(LABELS) - 2) * len(FEW_SEEDS)
    runs = report.configurations[0].runs
    assert len(runs) == len(LABELS) * len(FEW_SEEDS)
    for r in runs:
        expected = values[planned[(r.protocol, r.condition, r.seed)]]
        assert (r.final_agents, r.final_active_agents, r.max_generation) == expected
    by_label = {(r.protocol, r.condition, r.seed): r for r in runs}
    for seed in FEW_SEEDS:
        assert (
            by_label[("25d", "stable", seed)].final_agents
            == by_label[("25a", "full", seed)].final_agents
        )
        assert (
            by_label[("25d", "stable_drift", seed)].final_agents
            == by_label[("25a", "drift", seed)].final_agents
        )
        assert (
            by_label[("25d", "full", seed)].final_agents
            != by_label[("25a", "full", seed)].final_agents
        )


def test_semillas_repetidas_se_rechazan() -> None:
    with pytest.raises(ValueError, match="repetidas"):
        run_viability(total_ticks=3, jobs=1, seeds=(0, 0))
    with pytest.raises(ValueError):
        run_viability(total_ticks=3, jobs=1, seeds=())


def test_registra_el_control_nulo_de_la_elegida(
    small: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(phase25_viability, "demography", fake_demography({(20, 20)}, calls))
    report = run_viability(total_ticks=7, jobs=1)
    assert report.null_content_viable_seeds == {"25a": 2, "25b": 2, "25c": 2, "25d": 2}


def test_perfil_por_defecto(small: None, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(phase25_viability, "demography", fake_demography({(20, 20)}, calls))
    report = run_viability(jobs=1)
    assert report.total_ticks == PROFILES["phase25"].total_ticks == 5000
    assert all(ticks == 5000 for _, ticks in calls)


# --- Sólo demografía (D55.1) -------------------------------------------------------------------


def test_no_calcula_metricas_de_afirmacion(
    small: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def forbidden(*_: Any, **__: Any) -> Any:
        raise AssertionError("la compuerta no calcula métricas de afirmación")

    for name in (
        "phase25_metric_value",
        "phase25_run_record",
        "post_shift_accuracy",
        "effective_parents",
        "final_window",
        "evaluate_phase25_claims",
    ):
        monkeypatch.setattr(attribution, name, forbidden)
    out = tmp_path / "gate.json"
    assert main(["--jobs", "1", "--ticks", "6", "--out", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    text = out.read_text(encoding="utf-8")
    for claim in attribution.PHASE25_CLAIMS:
        assert claim.metric not in text
    for configuration in data["configurations"]:
        for condition in configuration["conditions"]:
            for record in condition["runs"]:
                assert set(record) == RUN_KEYS


# Símbolos de `attribution` que la compuerta puede usar: ninguno es de métricas ni afirmaciones.
ALLOWED_ATTRIBUTION = {
    "NULL_CONTENT",
    "PHASE25_ATTRIBUTION_PROFILE",
    "PHASE25_PROTOCOL_CONFIGS",
    "PHASE25_VIABILITY_SEEDS",
    "final_demography",
    "phase25_conditions",
    "phase25_protocol_configs",
}


def test_auditoria_de_imports() -> None:
    """Sobre el AST: no importa `metrics` ni usa símbolos de métricas o afirmaciones."""
    tree = ast.parse(inspect.getsource(phase25_viability))
    used: set[str] = set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            modules.add(module)
            names = {alias.name for alias in node.names}
            if module == "ide.experiments.attribution":
                used |= names
            if module == "ide.experiments":
                modules |= {f"ide.experiments.{name}" for name in names}
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "attribution"
        ):
            used.add(node.attr)
    assert "ide.experiments.metrics" not in modules
    assert not any("telemetry" in module for module in modules)
    assert used <= ALLOWED_ATTRIBUTION, sorted(used - ALLOWED_ATTRIBUTION)


# --- CLI, JSON y --jobs (D62.3 y precisión 55) ---------------------------------------------------


def test_default_jobs_compartido() -> None:
    """Vive junto a `map_in_order` y la compuerta la reexporta (D62.3)."""
    assert phase25_viability.default_jobs is exp001_runner.default_jobs


def test_jobs_por_defecto_con_la_afinidad(monkeypatch: pytest.MonkeyPatch) -> None:
    def affinity(_: int) -> set[int]:
        return {0, 1, 2}

    monkeypatch.setattr(os, "sched_getaffinity", affinity, raising=False)
    assert default_jobs() == 3
    assert build_arg_parser().parse_args([]).jobs == 3


def test_jobs_por_defecto_sin_afinidad(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(os, "sched_getaffinity", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: None)
    assert default_jobs() == 1
    assert build_arg_parser().parse_args([]).jobs == 1
    monkeypatch.setattr(os, "cpu_count", lambda: 5)
    assert build_arg_parser().parse_args([]).jobs == 5


def test_jobs_explicito() -> None:
    assert build_arg_parser().parse_args(["--jobs", "2"]).jobs == 2
    with pytest.raises(SystemExit):
        build_arg_parser().parse_args(["--jobs", "0"])


def test_salida_identica_para_cualquier_jobs(small: None, tmp_path: Path) -> None:
    one, two = tmp_path / "uno.json", tmp_path / "dos.json"
    assert main(["--jobs", "1", "--ticks", "6", "--out", str(one)]) == 0
    assert main(["--jobs", "2", "--ticks", "6", "--out", str(two)]) == 0
    assert one.read_bytes() == two.read_bytes()


def test_json_de_la_cli(
    small: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(phase25_viability, "demography", fake_demography({(20, 10)}, calls))
    out = tmp_path / "sub" / "gate.json"
    assert main(["--jobs", "1", "--ticks", "7", "--out", str(out)]) == 0
    data: dict[str, Any] = json.loads(out.read_text(encoding="utf-8"))
    assert data["total_ticks"] == 7
    assert (data["preregistered"], data["note"]) == (False, NOT_PREREGISTERED)
    assert data["seeds"] == list(FEW_SEEDS)
    assert data["grid"] == [list(point) for point in VIABILITY_GRID]
    assert data["chosen"] == {"resources_per_pattern": 20, "resource_regen_delay": 10}
    assert data["null_content_viable_seeds"] == {"25a": 2, "25b": 2, "25c": 2, "25d": 2}
    first, second = data["configurations"]
    assert (first["resources_per_pattern"], first["resource_regen_delay"]) == (20, 20)
    assert (first["viable"], second["viable"]) == (False, True)
    assert [(c["protocol"], c["condition"]) for c in second["conditions"]] == LABELS
    decides = {c["condition"]: c["decides"] for c in second["conditions"]}
    assert decides["null_content"] is False and decides["stable_drift"] is True
    full = second["conditions"][0]
    assert full["viable_seeds"] == 2
    assert full["runs"][0] == {
        "seed": 0,
        "termination": "alive",
        "final_agents": 10,
        "final_active_agents": 10,
        "max_generation": 30,
        "viable": True,
    }
    assert first["conditions"][0]["runs"][0]["termination"] == "extinct"
    printed = capsys.readouterr().out
    assert "(20, 10)" in printed and "25d stable_drift" in printed


def test_json_sin_configuracion_elegida(
    small: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(phase25_viability, "demography", fake_demography(set(), calls))
    out = tmp_path / "gate.json"
    assert main(["--jobs", "1", "--ticks", "7", "--out", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["chosen"] is None
    assert data["null_content_viable_seeds"] is None
    assert len(data["configurations"]) == len(VIABILITY_GRID)
    printed = capsys.readouterr().out
    assert "primera viable: ninguna" in printed and NOT_PREREGISTERED in printed
    assert "configuración elegida" not in printed


def test_ticks_de_prueba_exigen_out_explicito(small: None, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["--jobs", "1", "--ticks", "7"])
    with pytest.raises(SystemExit):
        main(["--jobs", "1", "--ticks", "7", "--out", str(DEFAULT_OUT)])
    assert not (tmp_path / "x.json").exists()


def test_semillas_distintas_de_las_preregistradas(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(phase25_viability, "PHASE25_VIABILITY_SEEDS", (0, 1, 2))
    with pytest.raises(SystemExit):
        main(["--jobs", "1", "--ticks", "7", "--out", str(tmp_path / "gate.json")])


def test_compuerta_preregistrada_anuncia_la_elegida(
    small: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(phase25_viability, "demography", fake_demography({(20, 10)}, calls))
    out = tmp_path / "gate.json"
    assert main(["--jobs", "1", "--out", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert (data["preregistered"], data["note"], data["total_ticks"]) == (True, None, 5000)
    printed = capsys.readouterr().out
    assert "configuración elegida" in printed and "(20, 10)" in printed
    assert NOT_PREREGISTERED not in printed


def test_demografia_real_de_una_corrida(small: None) -> None:
    config = dataclasses.replace(attribution.phase25_protocol_configs(20, 20)["25a"], seed=3)
    agents, active, generation = phase25_viability.demography((config, 5))
    assert 0 <= active <= agents
    assert generation >= 0


def test_final_demography_coincide_con_el_motor(small: None) -> None:
    config = dataclasses.replace(attribution.phase25_protocol_configs(20, 20)["25b"], seed=4)
    engine = SimulationEngine(config)
    engine.run(30)
    agents = [engine.agents[agent_id] for agent_id in sorted(engine.agents)]
    assert final_demography(engine) == (
        len(agents),
        sum(1 for agent in agents if not agent.is_endospore),
        max(m.max_generation for m in engine.evolutionary_history),
    )


# --- Propiedades del veredicto (Hypothesis, perfil `ci`) ---------------------------------------

_counts = st.lists(st.integers(0, 10), min_size=len(LABELS), max_size=len(LABELS))


def _runs_from(counts: list[int]) -> list[ViabilityRun]:
    return all_runs(**{f"{p}__{c}": n for (p, c), n in zip(LABELS, counts, strict=True)})


@given(_counts, st.randoms(use_true_random=False))
def test_veredicto_independiente_del_orden(counts: list[int], rnd: Any) -> None:
    runs = _runs_from(counts)
    shuffled = list(runs)
    rnd.shuffle(shuffled)
    assert is_viable_configuration(shuffled) == is_viable_configuration(runs)


@given(_counts, st.lists(st.integers(0, 10), min_size=4, max_size=4))
def test_el_control_nulo_nunca_cambia_el_veredicto(counts: list[int], nulls: list[int]) -> None:
    changed = list(counts)
    null_positions = [i for i, (_, c) in enumerate(LABELS) if c == NULL_CONTENT]
    for position, value in zip(null_positions, nulls, strict=True):
        changed[position] = value
    assert is_viable_configuration(_runs_from(changed)) == is_viable_configuration(
        _runs_from(counts)
    )


@given(_counts, st.integers(0, len(LABELS) - 1), st.integers(0, 10))
def test_veredicto_monotono_en_las_semillas_viables(
    counts: list[int], position: int, extra: int
) -> None:
    more = list(counts)
    more[position] = min(10, more[position] + extra)
    if is_viable_configuration(_runs_from(counts)):
        assert is_viable_configuration(_runs_from(more))
    expected = all(
        n >= MIN_VIABLE_SEEDS for (_, c), n in zip(LABELS, counts, strict=True) if c != NULL_CONTENT
    )
    assert is_viable_configuration(_runs_from(counts)) is expected


# --- Enmienda 2 de D55 (2026-10-22): grilla extendida y salida de respaldo ----------------------


def test_enmienda2_declarada() -> None:
    """Grilla extendida en orden de menos a más abundancia, y rutas de entrada y salida."""
    assert AMENDMENT2_GRID == ((60, 20), (60, 10), (80, 20), (80, 10))
    assert not set(AMENDMENT2_GRID) & set(VIABILITY_GRID)
    assert Path("registros/phase25_viability.json") == ORIGINAL_RECORD
    assert AMENDMENT2_DEFAULT_OUT not in (DEFAULT_OUT, ORIGINAL_RECORD)


def configuration(abundance: tuple[int, int], **exceptions: int) -> ConfigurationResult:
    runs = tuple(all_runs(**exceptions))
    return ConfigurationResult(abundance, is_viable_configuration(runs), runs)


def test_semillas_viables_de_las_condiciones_que_deciden() -> None:
    """Suma sobre las 13 (protocolo, condición) que deciden; `null_content` no cuenta."""
    assert deciding_viable_seeds(all_runs()) == 13 * 10
    nulls = {f"{p}__null_content": 0 for p in ("25a", "25b", "25c", "25d")}
    assert deciding_viable_seeds(all_runs(**nulls)) == 130
    assert deciding_viable_seeds(all_runs(**{"25c__full": 3, "25d__no_learning": 0})) == 130 - 17


def test_respaldo_elige_la_de_mas_semillas_viables() -> None:
    results = [
        configuration((40, 20), **{"25c__full": 2}),
        configuration((60, 20), **{"25c__full": 5}),
        configuration((60, 10), **{"25c__full": 1}),
    ]
    assert fallback_configuration(results) == (60, 20)


def test_respaldo_desempata_por_menos_abundancia() -> None:
    """Empate: gana la primera en el orden de las grillas (original y después extendida)."""
    results = [
        configuration((30, 10), **{"25c__full": 4}),
        configuration((40, 20), **{"25c__full": 6, "25b__drift": 9}),  # 125
        configuration((60, 20), **{"25c__full": 5, "25a__null_content": 0}),  # 125
        configuration((80, 10), **{"25c__full": 5}),
    ]
    assert fallback_configuration(results) == (40, 20)
    assert fallback_configuration(results[2:]) == (60, 20)
    with pytest.raises(ValueError):
        fallback_configuration([])


@given(st.lists(st.integers(0, 10), min_size=1, max_size=6))
def test_respaldo_maximo_y_primero(full_counts: list[int]) -> None:
    grid = [*VIABILITY_GRID, *AMENDMENT2_GRID][: len(full_counts)]
    results = [
        configuration(point, **{"25c__full": n}) for point, n in zip(grid, full_counts, strict=True)
    ]
    best = max(full_counts)
    assert fallback_configuration(results) == grid[full_counts.index(best)]


def original_report(
    small: None, monkeypatch: pytest.MonkeyPatch, ticks: int = 7
) -> ViabilityReport:
    """Compuerta original simulada, sin viables: (30, 10) con la semilla 0 viable en todo."""
    calls: list[Any] = []

    def demography(task: tuple[SimulationConfig, int]) -> tuple[int, int, int]:
        config, _ = task
        calls.append(task)
        point = (config.resources_per_pattern, config.resource_regen_delay)
        return (10, 10, 30) if point == (30, 10) and config.seed == 0 else (0, 0, 3)

    monkeypatch.setattr(phase25_viability, "demography", demography)
    report = run_viability(total_ticks=ticks, jobs=1)
    assert report.chosen is None
    return report


def test_json_de_la_compuerta_original_ida_y_vuelta(
    small: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = original_report(small, monkeypatch)
    data = json.loads(json.dumps(report_to_json(original)))
    assert report_from_json(data) == original


def test_json_original_incoherente_se_rechaza(small: None, monkeypatch: pytest.MonkeyPatch) -> None:
    data = report_to_json(original_report(small, monkeypatch))
    broken = json.loads(json.dumps(data))
    broken["configurations"][3]["conditions"][0]["viable_seeds"] = 2
    with pytest.raises(ValueError):
        report_from_json(broken)
    broken = json.loads(json.dumps(data))
    broken["grid"] = [[20, 20]]
    with pytest.raises(ValueError):
        report_from_json(broken)


def test_enmienda2_detencion_en_la_primera_viable(
    small: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = original_report(small, monkeypatch)
    calls: list[Any] = []
    monkeypatch.setattr(phase25_viability, "demography", fake_demography({(60, 10)}, calls))
    report = run_amendment2(original, total_ticks=7, jobs=1)
    assert isinstance(report, Amendment2Report)
    assert (report.chosen, report.fallback) == ((60, 10), False)
    assert [c.abundance for c in report.extended.configurations] == [(60, 20), (60, 10)]
    seen = list(dict.fromkeys((c.resources_per_pattern, c.resource_regen_delay) for c, _ in calls))
    assert seen == [(60, 20), (60, 10)]  # no corre (80, 20) ni (80, 10) ni repite la original
    assert report.null_content_viable_seeds == {"25a": 2, "25b": 2, "25c": 2, "25d": 2}


def test_enmienda2_sin_viables_usa_el_respaldo(
    small: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = original_report(small, monkeypatch)
    calls: list[Any] = []

    def demography(task: tuple[SimulationConfig, int]) -> tuple[int, int, int]:
        """Sólo (80, 20) con la semilla 0 viable en todo: empata con (30, 10) de la original."""
        config, _ = task
        calls.append(task)
        point = (config.resources_per_pattern, config.resource_regen_delay)
        return (10, 10, 30) if point == (80, 20) and config.seed == 0 else (0, 0, 3)

    monkeypatch.setattr(phase25_viability, "demography", demography)
    report = run_amendment2(original, total_ticks=7, jobs=1)
    assert [c.abundance for c in report.extended.configurations] == list(AMENDMENT2_GRID)
    seen = list(dict.fromkeys((c.resources_per_pattern, c.resource_regen_delay) for c, _ in calls))
    assert seen == list(AMENDMENT2_GRID)
    assert report.fallback is True
    assert report.chosen == (30, 10)  # empate en 13: gana la de menos abundancia
    assert report.null_content_viable_seeds == {"25a": 1, "25b": 1, "25c": 1, "25d": 1}
    totals = report.deciding_viable_seeds
    assert list(totals) == [*VIABILITY_GRID, *AMENDMENT2_GRID]
    assert totals[(30, 10)] == totals[(80, 20)] == 13
    assert sum(totals.values()) == 26


def test_enmienda2_exige_la_misma_compuerta(small: None, monkeypatch: pytest.MonkeyPatch) -> None:
    original = original_report(small, monkeypatch)
    with pytest.raises(ValueError, match="ticks"):
        run_amendment2(original, total_ticks=8, jobs=1)
    with pytest.raises(ValueError, match="semillas"):
        run_amendment2(original, total_ticks=7, jobs=1, seeds=(0, 1, 2))
    chosen = dataclasses.replace(original, chosen=(20, 20))
    with pytest.raises(ValueError, match="viable"):
        run_amendment2(chosen, total_ticks=7, jobs=1)
    partial = dataclasses.replace(original, configurations=original.configurations[:5])
    with pytest.raises(ValueError, match="grilla"):
        run_amendment2(partial, total_ticks=7, jobs=1)


def test_enmienda2_cli_json_y_no_calcula_metricas(
    small: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    original_path = tmp_path / "original.json"
    original = original_report(small, monkeypatch, ticks=6)
    original_path.write_text(json.dumps(report_to_json(original)), encoding="utf-8")

    def forbidden(*_: Any, **__: Any) -> Any:
        raise AssertionError("la compuerta no calcula métricas de afirmación")

    for name in (
        "phase25_metric_value",
        "phase25_run_record",
        "post_shift_accuracy",
        "effective_parents",
        "final_window",
        "evaluate_phase25_claims",
    ):
        monkeypatch.setattr(attribution, name, forbidden)
    monkeypatch.setattr(phase25_viability, "demography", fake_demography(set(), []))
    out = tmp_path / "enmienda2.json"
    argv = ["--amendment2", "--original", str(original_path), "--jobs", "1", "--ticks", "6"]
    assert main([*argv, "--out", str(out)]) == 0
    data: dict[str, Any] = json.loads(out.read_text(encoding="utf-8"))
    assert data["amendment"] == 2
    assert (data["preregistered"], data["note"]) == (False, NOT_PREREGISTERED)
    assert data["grid"] == [list(point) for point in AMENDMENT2_GRID]
    assert data["original_grid"] == [list(point) for point in VIABILITY_GRID]
    assert data["chosen"] == {"resources_per_pattern": 30, "resource_regen_delay": 10}
    assert data["fallback"] is True
    assert data["null_content_viable_seeds"] == {"25a": 1, "25b": 1, "25c": 1, "25d": 1}
    totals = data["deciding_viable_seeds"]
    assert [[t["resources_per_pattern"], t["resource_regen_delay"]] for t in totals] == [
        list(point) for point in (*VIABILITY_GRID, *AMENDMENT2_GRID)
    ]
    assert [t["viable_seeds"] for t in totals] == [0, 0, 0, 13, 0, 0, 0, 0, 0, 0]
    assert len(data["configurations"]) == len(AMENDMENT2_GRID)
    text = out.read_text(encoding="utf-8")
    for claim in attribution.PHASE25_CLAIMS:
        assert claim.metric not in text
    for configuration_json in data["configurations"]:
        for condition in configuration_json["conditions"]:
            for record in condition["runs"]:
                assert set(record) == RUN_KEYS
    printed = capsys.readouterr().out
    assert "respaldo" in printed and "(30, 10)" in printed and NOT_PREREGISTERED in printed


def test_enmienda2_salida_identica_para_cualquier_jobs(small: None, tmp_path: Path) -> None:
    """Con la demografía real (6 ticks: nada es viable, así que aplica el respaldo)."""
    original_path = tmp_path / "original.json"
    assert main(["--jobs", "1", "--ticks", "6", "--out", str(original_path)]) == 0
    argv = ["--amendment2", "--original", str(original_path), "--ticks", "6"]
    one, two = tmp_path / "uno.json", tmp_path / "dos.json"
    assert main([*argv, "--jobs", "1", "--out", str(one)]) == 0
    assert main([*argv, "--jobs", "2", "--out", str(two)]) == 0
    assert one.read_bytes() == two.read_bytes()
    assert json.loads(one.read_text(encoding="utf-8"))["fallback"] is True


def test_enmienda2_cli_validaciones(
    small: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(SystemExit):  # --original sólo con --amendment2
        main(["--original", str(tmp_path / "x.json"), "--ticks", "6", "--out", str(tmp_path)])
    with pytest.raises(SystemExit):  # original inexistente
        main(["--amendment2", "--original", str(tmp_path / "no.json"), "--ticks", "6",
              "--out", str(tmp_path / "e.json")])  # fmt: skip
    original_path = tmp_path / "original.json"
    original_path.write_text(
        json.dumps(report_to_json(original_report(small, monkeypatch, ticks=6))), encoding="utf-8"
    )
    with pytest.raises(SystemExit):  # prueba sin --out explícito
        main(["--amendment2", "--original", str(original_path), "--ticks", "6"])
    with pytest.raises(SystemExit):  # prueba con el --out predeterminado
        main(["--amendment2", "--original", str(original_path), "--ticks", "6",
              "--out", str(AMENDMENT2_DEFAULT_OUT)])  # fmt: skip
    with pytest.raises(SystemExit):  # otra duración que la de la original
        main(["--amendment2", "--original", str(original_path), "--ticks", "7",
              "--out", str(tmp_path / "e.json")])  # fmt: skip
    assert not (tmp_path / "e.json").exists()


def test_enmienda2_preregistrada_anuncia_la_elegida(
    small: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    original_path = tmp_path / "original.json"
    original = original_report(small, monkeypatch, ticks=PROFILES["phase25"].total_ticks)
    original_path.write_text(json.dumps(report_to_json(original)), encoding="utf-8")
    monkeypatch.setattr(phase25_viability, "demography", fake_demography({(80, 20)}, []))
    out = tmp_path / "enmienda2.json"
    assert main(["--amendment2", "--original", str(original_path), "--jobs", "1",
                 "--out", str(out)]) == 0  # fmt: skip
    data = json.loads(out.read_text(encoding="utf-8"))
    assert (data["preregistered"], data["fallback"]) == (True, False)
    assert data["chosen"] == {"resources_per_pattern": 80, "resource_regen_delay": 20}
    printed = capsys.readouterr().out
    assert "configuración elegida" in printed and "(80, 20)" in printed
    assert "respaldo" not in printed.split("Resultado")[-1]


def test_el_registro_original_sirve_para_la_enmienda2() -> None:
    """El registro de la tarea 23.4 se relee y cumple lo que exige la enmienda."""
    path = Path(__file__).resolve().parents[1] / ORIGINAL_RECORD
    original = report_from_json(json.loads(path.read_text(encoding="utf-8")))
    assert original.preregistered and original.chosen is None
    phase25_viability.check_original(
        original, PROFILES["phase25"].total_ticks, attribution.PHASE25_VIABILITY_SEEDS
    )
    totals = [deciding_viable_seeds(c.runs) for c in original.configurations]
    assert len(totals) == len(VIABILITY_GRID)


def _corrupt(data: dict[str, Any], change: str) -> dict[str, Any]:
    broken = json.loads(json.dumps(data))
    configuration = broken["configurations"][0]
    if change == "criterio":
        broken["min_generation"] = 5
    elif change == "condiciones":
        configuration["conditions"].pop()
    elif change == "semillas":
        configuration["conditions"][0]["runs"].pop()
    elif change == "corrida":
        configuration["conditions"][0]["runs"][0]["viable"] = True
    elif change == "configuracion":
        configuration["viable"] = True
    elif change == "elegida":
        broken["chosen"] = {"resources_per_pattern": 20, "resource_regen_delay": 20}
    elif change == "nulo":
        broken["null_content_viable_seeds"] = {"25a": 0, "25b": 0, "25c": 0, "25d": 0}
    return broken


@pytest.mark.parametrize(
    "change",
    ["criterio", "condiciones", "semillas", "corrida", "configuracion", "elegida", "nulo"],
)
def test_report_from_json_rechaza_incoherencias(
    small: None, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    data = report_to_json(original_report(small, monkeypatch))
    with pytest.raises(ValueError):
        report_from_json(_corrupt(data, change))


def test_report_from_json_con_elegida(small: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phase25_viability, "demography", fake_demography({(20, 10)}, []))
    report = run_viability(total_ticks=7, jobs=1)
    assert report_from_json(json.loads(json.dumps(report_to_json(report)))) == report


def test_grilla_repetida_o_vacia_se_rechaza() -> None:
    with pytest.raises(ValueError, match="grilla"):
        run_viability(total_ticks=3, jobs=1, grid=[(60, 20), (60, 20)])
    with pytest.raises(ValueError, match="grilla"):
        run_viability(total_ticks=3, jobs=1, grid=[])


def test_enmienda2_preregistrada_con_respaldo(
    small: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    original_path = tmp_path / "original.json"
    original = original_report(small, monkeypatch, ticks=PROFILES["phase25"].total_ticks)
    original_path.write_text(json.dumps(report_to_json(original)), encoding="utf-8")
    monkeypatch.setattr(phase25_viability, "demography", fake_demography(set(), []))
    out = tmp_path / "enmienda2.json"
    assert main(["--amendment2", "--original", str(original_path), "--jobs", "1",
                 "--out", str(out)]) == 0  # fmt: skip
    data = json.loads(out.read_text(encoding="utf-8"))
    assert (data["preregistered"], data["fallback"]) == (True, True)
    assert data["chosen"] == {"resources_per_pattern": 30, "resource_regen_delay": 10}
    printed = capsys.readouterr().out
    assert "configuración de respaldo" in printed and "(30, 10)" in printed
    assert NOT_PREREGISTERED not in printed
