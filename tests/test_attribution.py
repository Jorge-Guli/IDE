"""Tests de `emergence-attribution`: reglas, pre-registro, ablación y clasificación."""

import dataclasses
import hashlib
import json
import math
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.config import SimulationConfig
from ide.experiments import attribution, exp001_runner
from ide.experiments.attribution import (
    ALL_DESIGN_RULES,
    ATTRIBUTION_PROFILE,
    DESIGN_RULES,
    EXP001_CLAIMS,
    EXP002_CLAIMS,
    EXP003_CLAIMS,
    PHASE2_ATTRIBUTION_PROFILE,
    PHASE2_CLAIM_CHANNELS,
    PHASE2_DESIGN_RULES,
    PHASE2_INACTIVE_RULES,
    PHASE2_PROTOCOL_CONFIGS,
    PHASE2_PROTOCOL_CONFIGS_ORIGINAL,
    PHASE2_SEEDS,
    PHASE25_ABUNDANCE,
    PHASE25_ALL_RULES,
    PHASE25_ATTRIBUTION_PROFILE,
    PHASE25_CLAIMS,
    PHASE25_DESIGN_RULES,
    PHASE25_FINAL_WINDOW,
    PHASE25_HOLM_M,
    PHASE25_INACTIVE_RULES,
    PHASE25_MIN_VALID_PAIRS,
    PHASE25_PROTOCOL_CONFIGS,
    PHASE25_RULE_EFFECT_SEEDS,
    PHASE25_SEEDS,
    PHASE25_VIABILITY_SEEDS,
    ClaimEvaluation,
    ClaimStatus,
    EmergenceClaim,
    Phase25Claim,
    Phase25ClaimEvaluation,
    Phase25Report,
    Phase25RunRecord,
    ablate,
    claim_conditions,
    classify,
    disables_communication,
    e4_interpretable,
    effect_threshold,
    effective_parents,
    evaluate_phase25_claims,
    final_window,
    holm_bonferroni,
    is_by_construction,
    measure_claim,
    phase25_conditions,
    phase25_metric_value,
    phase25_protocol_configs,
    phase25_rule_effect,
    phase25_run_record,
    phase25_status,
    post_shift_accuracy,
    run_phase2_attribution,
    run_phase25_attribution,
    run_protocol_001d_attribution,
)
from ide.experiments.exp001_runner import (
    PROFILES,
    Profile,
    build_arg_parser,
    main,
    map_in_order,
    run_protocol_001b_falsification,
    run_protocol_001c_resilience,
)
from ide.simulation.engine import SimulationEngine

ROOT = Path(__file__).resolve().parents[1]

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


# --- Clasificación -----------------------------------------------------------------------------

UP = EXP001_CLAIMS[0]  # C1, R_c = {R8, R9}, higher_is_better
DOWN = EXP001_CLAIMS[2]  # C3, R_c = {R3, R4, R6, R7}, lower is better
HIGH, LOW = (0.6, 0.7, 0.8, 0.9, 1.0), (0.1, 0.2, 0.3, 0.4, 0.5)


def evaluate(
    claim: EmergenceClaim = DOWN, by_construction: bool = False, **values: Sequence[float]
) -> ClaimEvaluation:
    base: dict[str, Sequence[float]] = {
        "full": HIGH,
        "isolated": LOW,
        "purpose_ablated": HIGH,
        "null_content": LOW,
    }
    base.update({k.replace("__", ":"): v for k, v in values.items()})
    if not claim.higher_is_better:  # misma situación, con la métrica orientada al revés
        base = {k: tuple(-x for x in v) for k, v in base.items()}
    return classify(claim, base, by_construction)


def test_diferencias_orientadas() -> None:
    result = classify(
        DOWN,
        {
            "full": (0.1,) * 5,
            "isolated": (0.3,) * 5,
            "null_content": (0.3,) * 5,
            "purpose_ablated": (0.2,) * 5,
        },
        False,
    )
    assert result.p_vs_isolated == pytest.approx(0.03125, abs=1e-9)
    assert result.p_purpose_ablated_vs_isolated == pytest.approx(0.03125, abs=1e-9)
    assert result.status is ClaimStatus.EMERGENT_PENDING_ROBUSTNESS


def test_programada_por_construccion() -> None:
    values = {"full": HIGH, "isolated": LOW, "null_content": LOW}
    result = classify(UP, values, by_construction=True)
    assert result.status is ClaimStatus.PROGRAMMED
    assert result.by_construction is True
    assert result.p_purpose_ablated_vs_isolated is None
    assert result.p_vs_null_content == pytest.approx(0.03125, abs=1e-9)


def test_propiedad_que_desaparece_sin_su_regla() -> None:
    assert evaluate(purpose_ablated=LOW).status is ClaimStatus.PROGRAMMED


def test_propiedad_que_solo_se_debe_a_la_actividad() -> None:
    assert evaluate(null_content=HIGH).status is ClaimStatus.ACTIVITY_ARTIFACT


def test_candidata_sin_prueba_de_robustez() -> None:
    result = evaluate()
    assert result.status is ClaimStatus.EMERGENT_PENDING_ROBUSTNESS
    assert result.e5_evaluated is False


def test_no_observada() -> None:
    assert evaluate(full=LOW).status is ClaimStatus.NOT_OBSERVED
    assert evaluate(UP, full=LOW, by_construction=True).status is ClaimStatus.NOT_OBSERVED


def test_artefacto_del_reloj() -> None:
    result = evaluate(async__full=LOW, async__isolated=LOW, async__purpose_ablated=HIGH)
    assert result.e5_evaluated is True
    assert result.status is ClaimStatus.SCHEDULING_ARTIFACT
    result = evaluate(async__full=HIGH, async__isolated=LOW, async__purpose_ablated=LOW)
    assert result.status is ClaimStatus.SCHEDULING_ARTIFACT


def test_emergente_con_variantes_asincronas() -> None:
    result = evaluate(async__full=HIGH, async__isolated=LOW, async__purpose_ablated=HIGH)
    assert result.e5_evaluated is True
    assert result.status is ClaimStatus.EMERGENT


def test_e5_requiere_purpose_ablated_asincrono_cuando_hay_e3() -> None:
    result = evaluate(async__full=HIGH, async__isolated=LOW)
    assert result.e5_evaluated is False
    assert result.status is ClaimStatus.EMERGENT_PENDING_ROBUSTNESS


def test_r_c_vacio_cumple_e3_trivialmente() -> None:
    empty = dataclasses.replace(UP, purpose_rules=())
    values = {"full": HIGH, "isolated": LOW, "null_content": LOW}
    result = classify(empty, values, by_construction=False)
    assert result.p_purpose_ablated_vs_isolated is None
    assert result.status is ClaimStatus.EMERGENT_PENDING_ROBUSTNESS
    values |= {"async:full": HIGH, "async:isolated": LOW}
    assert classify(empty, values, False).status is ClaimStatus.EMERGENT


def test_pocas_semillas() -> None:
    values = {"full": HIGH[:3], "isolated": LOW[:3], "null_content": LOW[:3]}
    result = classify(UP, values, by_construction=True)
    assert result.status is ClaimStatus.INSUFFICIENT_EVIDENCE
    assert result.values["full"] == HIGH[:3]


def test_rule_effects_orientados() -> None:
    values = {
        "full": HIGH,
        "isolated": LOW,
        "null_content": LOW,
        "without:R3": tuple(x - 0.1 for x in HIGH),
        "without:R10": tuple(x + 0.2 for x in HIGH),
    }
    up = classify(UP, values, by_construction=True)
    assert list(up.rule_effects) == ["R3", "R10"]
    assert up.rule_effects["R3"] == pytest.approx(0.1, abs=1e-9)
    assert up.rule_effects["R10"] == pytest.approx(-0.2, abs=1e-9)
    down = classify(DOWN, {**values, "purpose_ablated": HIGH}, by_construction=False)
    assert down.rule_effects["R3"] == pytest.approx(-0.1, abs=1e-9)


# --- Medición ----------------------------------------------------------------------------------

SMALL = SimulationConfig(grid_width=10, grid_height=10, num_agents=12, resources_per_pattern=4)


@pytest.fixture(autouse=False)
def tiny_profile(monkeypatch: pytest.MonkeyPatch) -> str:
    tiny = Profile(total_ticks=30, injection_tick=10, warmup_ticks=20, post_ablation_ticks=10)
    monkeypatch.setitem(PROFILES, "tiny", tiny)
    return "tiny"


def test_measure_claim_001a(tiny_profile: str) -> None:
    engine = SimulationEngine(SMALL)
    last = engine.run(30)[-1]
    c1 = measure_claim(EXP001_CLAIMS[0], SMALL, tiny_profile)
    c2 = measure_claim(EXP001_CLAIMS[1], SMALL, tiny_profile)
    assert c1 == pytest.approx(last.accessible_coverage_mean, abs=1e-9)
    assert c2 == pytest.approx(last.cumulative_decision_accuracy, abs=1e-9)


def test_measure_claim_001b(tiny_profile: str) -> None:
    report = run_protocol_001b_falsification(SMALL, 30, 10)
    value = measure_claim(EXP001_CLAIMS[2], SMALL, tiny_profile)
    assert value == pytest.approx(report.final_false_prevalence, abs=1e-9)


def test_measure_claim_001c(tiny_profile: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # La persistencia social sale de una corrida independiente: el nivel 0.5 no la altera.
    with_level = run_protocol_001c_resilience(SMALL, 20, 10, ablation_levels=(0.5,))
    only_discoverers = run_protocol_001c_resilience(SMALL, 20, 10, ablation_levels=())
    assert only_discoverers.ablation_results == ()
    assert only_discoverers.final_social_persistence_prevalence == pytest.approx(
        with_level.final_social_persistence_prevalence, abs=1e-9
    )

    def no_level(*_: object, **__: object) -> None:
        raise AssertionError("C4 no debe correr una ablación poblacional que se descarta")

    monkeypatch.setattr(exp001_runner, "_ablation_point", no_level)
    value = measure_claim(EXP001_CLAIMS[3], SMALL, tiny_profile)
    assert value == pytest.approx(with_level.final_social_persistence_prevalence, abs=1e-9)


def test_measure_claim_protocolo_desconocido(tiny_profile: str) -> None:
    bogus = dataclasses.replace(EXP001_CLAIMS[0], protocol="001z")
    with pytest.raises(ValueError, match="001z"):
        measure_claim(bogus, SMALL, tiny_profile)


def test_001d_con_pocas_semillas(tiny_profile: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attribution, "ATTRIBUTION_PROFILE", tiny_profile)
    report = run_protocol_001d_attribution(SMALL, [3, 4])
    assert report.profile == tiny_profile
    assert report.rules == DESIGN_RULES
    assert [e.claim_id for e in report.evaluations] == ["C1", "C2", "C3", "C4"]
    for evaluation, claim in zip(report.evaluations, EXP001_CLAIMS, strict=True):
        assert evaluation.status is ClaimStatus.INSUFFICIENT_EVIDENCE
        assert evaluation.seeds == (3, 4)
        assert all(len(v) == 2 for v in evaluation.values.values())
        assert list(evaluation.rule_effects) == [f"R{i}" for i in range(3, 12)]
        assert ("purpose_ablated" in evaluation.values) is (claim.claim_id == "C3")
        assert evaluation.by_construction is (claim.claim_id != "C3")
    c1 = report.evaluations[0]
    assert c1.values["full"][0] == measure_claim(
        EXP001_CLAIMS[0], dataclasses.replace(SMALL, seed=3), tiny_profile
    )


def test_001d_paralelismo_inocuo(tiny_profile: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attribution, "ATTRIBUTION_PROFILE", tiny_profile)
    sequential = run_protocol_001d_attribution(SMALL, [3], claims=EXP001_CLAIMS[2:3])
    # El perfil viaja dentro de cada tarea, así que no depende de que los procesos hijos hereden
    # el monkeypatch. Con `fork` (Linux) lo heredan igual: esto verifica la igualdad de
    # resultados entre `jobs`, no el transporte del perfil.
    parallel = run_protocol_001d_attribution(SMALL, [3], claims=EXP001_CLAIMS[2:3], jobs=2)
    assert sequential == parallel


# --- CLI ---------------------------------------------------------------------------------------


def test_cli_con_pocas_semillas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Escenario de la spec en proceso: el perfil `quick` se acorta para que sea rápido."""
    short = Profile(total_ticks=20, injection_tick=5, warmup_ticks=10, post_ablation_ticks=5)
    monkeypatch.setitem(PROFILES, "quick", short)
    argv = ["--seeds", "42", "--attribution", "--profile", "full", "--out", str(tmp_path)]
    assert main(argv) == 0
    out = capsys.readouterr().out
    data = json.loads((tmp_path / "exp001_attribution.json").read_text())
    assert data["profile"] == "quick"
    assert [e["status"] for e in data["evaluations"]] == ["INSUFFICIENT_EVIDENCE"] * 4
    assert [r["rule_id"] for r in data["rules"]] == [f"R{i}" for i in range(1, 12)]
    assert "Aviso" in out and "5 semillas" in out and "perfil quick" in out
    for claim in ("C1", "C2", "C3", "C4"):
        assert claim in out
    assert sorted(p.name for p in tmp_path.iterdir()) == ["exp001_attribution.json"]


@pytest.mark.slow
def test_cli_con_pocas_semillas_completa(tmp_path: Path) -> None:
    command = [
        sys.executable, "-m", "ide.experiments.exp001_runner",
        "--seeds", "42", "--attribution", "--profile", "full", "--jobs", "4",
        "--out", str(tmp_path),
    ]  # fmt: skip
    done = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    data = json.loads((tmp_path / "exp001_attribution.json").read_text())
    assert data["profile"] == "quick"
    assert [e["status"] for e in data["evaluations"]] == ["INSUFFICIENT_EVIDENCE"] * 4
    assert "Aviso" in done.stdout
    for claim in ("C1", "C2", "C3", "C4"):
        assert claim in done.stdout
    assert sorted(p.name for p in tmp_path.iterdir()) == ["exp001_attribution.json"]


def test_classify_exige_el_mismo_numero_de_semillas() -> None:
    values = {"full": HIGH, "isolated": LOW, "null_content": LOW, "without:R3": HIGH[:4]}
    with pytest.raises(ValueError, match="without:R3"):
        classify(UP, values, by_construction=True)


def test_001d_valida_las_semillas() -> None:
    with pytest.raises(ValueError, match="repetidas"):
        run_protocol_001d_attribution(SMALL, [3, 3, 4])
    with pytest.raises(ValueError, match="al menos una"):
        run_protocol_001d_attribution(SMALL, [])


def test_classify_exige_las_variantes() -> None:
    with pytest.raises(ValueError, match="null_content"):
        classify(UP, {"full": (0.1,), "isolated": (0.0,)}, by_construction=True)
    with pytest.raises(ValueError, match="purpose_ablated"):
        classify(DOWN, {"full": (0.1,), "isolated": (0.0,), "null_content": (0.0,)}, False)


def test_parser_acepta_attribution() -> None:
    assert build_arg_parser().parse_args([]).attribution is False
    assert build_arg_parser().parse_args(["--attribution"]).attribution is True


# --- Reporte completo (lento) ------------------------------------------------------------------


@pytest.mark.slow
def test_reporte_completo_con_cinco_semillas() -> None:
    report = run_protocol_001d_attribution(SimulationConfig(), [42, 43, 44, 45, 46], jobs=4)
    assert report.profile == "quick"
    by_id = {e.claim_id: e for e in report.evaluations}
    assert [by_id[c].by_construction for c in ("C1", "C2", "C3", "C4")] == [True, True, False, True]
    for evaluation in report.evaluations:
        assert evaluation.seeds == (42, 43, 44, 45, 46)
        assert all(len(v) == 5 for v in evaluation.values.values())
        assert list(evaluation.rule_effects) == [f"R{i}" for i in range(3, 12)]
        assert evaluation.status is not ClaimStatus.INSUFFICIENT_EVIDENCE
        assert evaluation.e5_evaluated is False
    assert by_id["C4"].p_purpose_ablated_vs_isolated is None


def test_classify_sin_valores() -> None:
    with pytest.raises(ValueError, match="no hay valores"):
        classify(UP, {"full": (), "isolated": (), "null_content": ()}, by_construction=True)


@pytest.mark.parametrize(
    ("seeds", "message", "claims"),
    [
        ([-1, 2], "seed no puede ser negativo", EXP001_CLAIMS),
        ([-1, 2], "seed no puede ser negativo", ()),
        ([3, 3], "repetidas", EXP001_CLAIMS),
        ([3, 3], "repetidas", ()),
    ],
)
def test_001d_rechaza_semillas_invalidas(
    monkeypatch: pytest.MonkeyPatch,
    seeds: list[int],
    message: str,
    claims: tuple[EmergenceClaim, ...],
) -> None:
    def no_correr(*_: object, **__: object) -> None:
        raise AssertionError("debe fallar antes de ejecutar corridas")

    monkeypatch.setattr(attribution, "map_in_order", no_correr)
    with pytest.raises(ValueError, match=message):
        run_protocol_001d_attribution(SMALL, seeds, claims=claims)


@pytest.mark.parametrize(("items", "jobs"), [([], 4), ([5], 8), ([1, 2, 3], 1)])
def test_map_in_order_sin_pool_innecesario(
    monkeypatch: pytest.MonkeyPatch, items: list[int], jobs: int
) -> None:
    def no_pool(*_: object, **__: object) -> None:
        raise AssertionError("no debe crear un pool con un solo trabajo útil")

    monkeypatch.setattr(exp001_runner, "ProcessPoolExecutor", no_pool)
    assert map_in_order(abs, [-x for x in items], jobs) == items


def test_map_in_order_en_paralelo_conserva_el_orden() -> None:
    assert map_in_order(abs, [-3, -1, -2, -5], 3) == [3, 1, 2, 5]


# --- Fase II: pre-registro (design D29) --------------------------------------------------------

EVO = SimulationConfig(enable_evolution=True, enable_holonic_hierarchy=True)


def test_reglas_de_fase_ii() -> None:
    assert [r.rule_id for r in DESIGN_RULES] == [f"R{i}" for i in range(1, 12)]
    assert [r.rule_id for r in PHASE2_DESIGN_RULES] == [f"R{i}" for i in range(12, 24)]
    assert [r.rule_id for r in PHASE2_DESIGN_RULES if r.ablation == ()] == ["R20"]
    assert all(r.name and r.purpose for r in PHASE2_DESIGN_RULES)
    assert ALL_DESIGN_RULES == DESIGN_RULES + PHASE2_DESIGN_RULES


def test_overrides_de_cada_regla_de_fase_ii() -> None:
    overrides = {r.rule_id: dict(r.ablation) for r in PHASE2_DESIGN_RULES}
    assert overrides == {
        "R12": {"reproduction_mode": "neutral"},
        "R13": {"mutation_rate": 0.0, "discrete_mutation_prob": 0.0},
        "R14": {"enable_cultural_inheritance": False, "inheritance_discount": 0.0},
        "R15": {"enable_holonic_hierarchy": False},
        "R16": {"enable_holon_splitting": False},
        "R17": {"enable_holon_reproduction": False},
        "R18": {"enable_downward_causation": False, "redundancy_penalty": 1.0},
        "R19": {"enable_stigmergy": False, "stigmergy_deposit_rate": 0.0},
        "R20": {},
        "R21": {"memory_capacity_cost": 0.0, "sensory_radius_cost": 0.0},
        "R22": {"enable_holon_view": False},
        "R23": {"holon_coord_cost": 0.0, "holon_energy_sharing": False},
    }


def test_ablacion_de_reglas_de_fase_ii() -> None:
    """Escenario de la spec: `ablate` opera sobre cualquier regla de `ALL_DESIGN_RULES`."""
    ablated = ablate(EVO, ["R12", "R22", "R23"])
    assert ablated.reproduction_mode == "neutral"
    assert ablated.enable_holon_view is False
    assert ablated.holon_coord_cost == 0.0
    assert ablated.holon_energy_sharing is False
    assert ablate(EVO, ["R4", "R13"]) == dataclasses.replace(
        EVO, gamma_social_discount=1.0, mutation_rate=0.0, discrete_mutation_prob=0.0
    )
    with pytest.raises(ValueError, match="nuclear"):
        ablate(EVO, ["R20"])
    # Desde la Fase II-B `ablate` también busca R24-R41 (D56); la regla inexistente es R42.
    with pytest.raises(ValueError, match="R42"):
        ablate(EVO, ["R42"])


def test_ablacion_de_todas_las_reglas_de_ambas_fases_es_valida() -> None:
    every = [r.rule_id for r in ALL_DESIGN_RULES if r.ablation]
    for config in PHASE2_PROTOCOL_CONFIGS.values():
        ablated = ablate(config, every)
        for rule in ALL_DESIGN_RULES:
            for name, value in rule.ablation:
                assert getattr(ablated, name) == value


def test_afirmaciones_de_fase_ii() -> None:
    assert (
        EmergenceClaim(
            "C5", "Aceleración cultural intergeneracional", "002b", "cultural_accuracy", True,
            ("R14",),
        ),
        EmergenceClaim(
            "C6", "Adaptación evolutiva por selección", "002a", "evolved_accuracy", True,
            ("R12", "R13"),
        ),
    ) == EXP002_CLAIMS  # fmt: skip
    assert (
        EmergenceClaim(
            "C7", "Superávit cooperativo sobre recursos compuestos", "003a",
            "holonic_composite_completions", True, ("R15", "R17"),
        ),
        EmergenceClaim(
            "C8", "Cobertura colectiva adquirida sin causalidad descendente", "003b",
            "mean_acquired_coverage", True, ("R22",),
        ),
    ) == EXP003_CLAIMS  # fmt: skip
    assert PHASE2_CLAIM_CHANNELS == {
        "C5": ("R14",),
        "C6": ("R12",),
        "C7": ("R15",),
        "C8": ("R22",),
    }


def test_perfil_y_configuraciones_congelados() -> None:
    """Escenario de la spec: perfil `phase2`, 10 semillas y la configuración de 003-A."""
    assert PHASE2_ATTRIBUTION_PROFILE == "phase2"
    assert PROFILES[PHASE2_ATTRIBUTION_PROFILE] == Profile(
        total_ticks=2000, injection_tick=80, warmup_ticks=150, post_ablation_ticks=100
    )
    assert tuple(range(42, 52)) == PHASE2_SEEDS
    holonic = {
        "enable_evolution": True,
        "enable_holonic_hierarchy": True,
        "enable_holon_reproduction": True,
        "num_composite_patterns": 3,
        "composite_order": 4,
    }
    base = SimulationConfig(resources_per_pattern=attribution.PHASE2_RESOURCES_PER_PATTERN)
    assert {
        "002a": dataclasses.replace(base, enable_evolution=True),
        "002b": dataclasses.replace(base, enable_evolution=True, enable_cultural_inheritance=True),
        "003a": dataclasses.replace(base, **holonic),
        "003b": dataclasses.replace(base, **holonic, enable_downward_causation=False),
    } == PHASE2_PROTOCOL_CONFIGS
    c003a = PHASE2_PROTOCOL_CONFIGS["003a"]
    assert c003a.num_composite_patterns == 3
    assert c003a.composite_order == 4 > c003a.memory_capacity
    assert attribution.PHASE2_RESOURCES_PER_PATTERN == 20


def _rule_is_active(rule_id: str, config: SimulationConfig) -> bool:
    """Bandera principal de cada regla ablacionable, con sus dependencias (design D29)."""
    evolution = config.enable_evolution
    holonic = config.enable_holonic_hierarchy
    active = {
        "R12": evolution,
        "R13": evolution and (config.mutation_rate > 0 or config.discrete_mutation_prob > 0),
        "R14": evolution and config.enable_cultural_inheritance and config.inheritance_discount > 0,
        "R15": holonic,
        "R16": holonic and config.enable_holon_splitting,
        "R17": holonic and evolution and config.enable_holon_reproduction,
        "R18": holonic and config.enable_downward_causation,
        "R19": config.enable_stigmergy and config.stigmergy_deposit_rate > 0,
        "R21": evolution and (config.memory_capacity_cost > 0 or config.sensory_radius_cost > 0),
        "R22": holonic and config.enable_holon_view,
        "R23": holonic and (config.holon_coord_cost > 0 or config.holon_energy_sharing),
    }
    return active.get(rule_id, True)  # las reglas de Fase I actúan en todos los protocolos


def test_reglas_inactivas_coinciden_con_las_configuraciones() -> None:
    assert PHASE2_INACTIVE_RULES == {
        "002a": ("R14", "R15", "R16", "R17", "R18", "R19", "R22", "R23"),
        "002b": ("R15", "R16", "R17", "R18", "R19", "R22", "R23"),
        "003a": ("R14", "R18", "R19"),
        "003b": ("R14", "R18", "R19"),
    }
    assert sorted(PHASE2_INACTIVE_RULES) == sorted(PHASE2_PROTOCOL_CONFIGS)
    ablatable = [r.rule_id for r in ALL_DESIGN_RULES if r.ablation]
    for protocol, config in PHASE2_PROTOCOL_CONFIGS.items():
        inactive = [rid for rid in ablatable if not _rule_is_active(rid, config)]
        assert tuple(inactive) == PHASE2_INACTIVE_RULES[protocol], protocol


# --- Fase II: criterio ampliado, variantes y semillas sin medición -----------------------------

PHASE2_CLAIMS = EXP002_CLAIMS + EXP003_CLAIMS
C5, C6, C7, C8 = PHASE2_CLAIMS
SMALL_GRID = {"grid_width": 10, "grid_height": 10, "num_agents": 12, "resources_per_pattern": 6}
PHASE1_EFFECTS = [f"R{i}" for i in range(3, 12)]
EXPECTED_EFFECTS = {
    "C5": [*PHASE1_EFFECTS, "R12", "R13", "R14", "R21"],
    "C6": [*PHASE1_EFFECTS, "R12", "R13", "R21"],
    "C7": [*PHASE1_EFFECTS, "R12", "R13", "R15", "R16", "R17", "R21", "R22", "R23"],
    "C8": [*PHASE1_EFFECTS, "R12", "R13", "R15", "R16", "R17", "R21", "R22", "R23"],
}


def test_clasificacion_de_c5_a_c8_por_construccion() -> None:
    """Escenario de la spec: el canal está contenido en R_C; Fase I conserva su criterio."""
    for claim in PHASE2_CLAIMS:
        assert is_by_construction(claim, PHASE2_PROTOCOL_CONFIGS[claim.protocol]), claim.claim_id
    assert [is_by_construction(c, CFG) for c in EXP001_CLAIMS] == [True, True, False, True]
    widened = dataclasses.replace(C6, purpose_rules=("R13",))  # canal R12 fuera de R_C
    assert not is_by_construction(widened, PHASE2_PROTOCOL_CONFIGS["002a"])


def test_c8_sin_medicion_en_ninguna_semilla() -> None:
    """Escenario de la spec: sin holones elegibles, C8 es INSUFFICIENT_EVIDENCE."""
    nothing: tuple[float | None, ...] = (None,) * 10
    values: dict[str, Sequence[float | None]] = {
        "full": nothing,
        "isolated": (0.1,) * 10,
        "null_content": (0.2,) * 10,
        "without:R22": (0.1,) * 10,
        "without:R12": nothing,
    }
    evaluation = classify(C8, values, by_construction=True, seeds=PHASE2_SEEDS)
    assert evaluation.status is ClaimStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.p_vs_isolated == 1.0
    assert evaluation.rule_effects == {"R22": None, "R12": None}
    assert evaluation.seeds == PHASE2_SEEDS
    assert evaluation.unmeasured_seeds == {
        "isolated": PHASE2_SEEDS,
        "null_content": PHASE2_SEEDS,
        "without:R22": PHASE2_SEEDS,
        "without:R12": PHASE2_SEEDS,
    }


def test_semillas_sin_medicion_cuentan_como_empate() -> None:
    full = (0.5, 0.6, None, 0.7, 0.8, 0.9)
    values: dict[str, Sequence[float | None]] = {
        "full": full,
        "isolated": (0.1, 0.1, 0.1, 0.1, 0.1, None),
        "null_content": (0.0,) * 6,
        "without:R22": (0.4, None, 0.0, 0.6, 0.6, 0.6),
    }
    seeds = (1, 2, 3, 4, 5, 6)
    evaluation = classify(C8, values, by_construction=True, seeds=seeds)
    # E2 mide 4 semillas (< MIN_SEEDS): evidencia insuficiente, aunque `full` tenga 5 valores.
    assert evaluation.status is ClaimStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.p_vs_isolated == pytest.approx(1 / 16, abs=1e-9)
    assert evaluation.p_vs_null_content == pytest.approx(1 / 32, abs=1e-9)
    assert evaluation.unmeasured_seeds == {
        "isolated": (3, 6),
        "null_content": (3,),
        "without:R22": (2, 3),
    }
    effect = evaluation.rule_effects["R22"]
    assert effect == pytest.approx((0.1 + 0.1 + 0.2 + 0.3) / 4, abs=1e-9)
    measured = dict(values, isolated=(0.1,) * 6)
    assert classify(C8, measured, True, seeds=seeds).status is ClaimStatus.PROGRAMMED


def test_fase_i_sin_semillas_sin_medicion() -> None:
    evaluation = evaluate(UP, by_construction=True)
    assert evaluation.unmeasured_seeds == {}
    assert evaluation.seeds == ()


def test_measure_claim_de_fase_ii(tiny_profile: str) -> None:
    """Escenario de la spec: cada afirmación devuelve su métrica; C8 puede ser `None`."""
    from ide.experiments.exp002_runner import run_evolution_condition
    from ide.experiments.exp003_runner import run_holonic_condition

    ticks = PROFILES[tiny_profile].total_ticks
    for claim in PHASE2_CLAIMS:
        config = dataclasses.replace(PHASE2_PROTOCOL_CONFIGS[claim.protocol], **SMALL_GRID)
        value = measure_claim(claim, config, tiny_profile)
        if claim.protocol.startswith("002"):
            expected = run_evolution_condition(config, ticks).final_accuracy
            assert isinstance(value, float) and value == pytest.approx(expected, abs=1e-9)
        elif claim is C7:
            completions = run_holonic_condition(config, ticks).composite_completions
            assert isinstance(value, float) and value == float(completions)
        else:
            coverage = run_holonic_condition(config, ticks).mean_acquired_coverage
            assert value == (None if coverage is None else pytest.approx(coverage, abs=1e-9))


def test_measure_claim_c8_sin_holones_elegibles(monkeypatch: pytest.MonkeyPatch) -> None:
    # En un único tick ningún holón tiene edad >= 1: no hay nada que medir.
    monkeypatch.setitem(PROFILES, "one", Profile(1, 0, 1, 1))
    assert measure_claim(C8, PHASE2_PROTOCOL_CONFIGS["003b"], "one") is None


@pytest.fixture
def small_phase2(monkeypatch: pytest.MonkeyPatch, tiny_profile: str) -> str:
    """Perfil corto y configuraciones chicas, sin tocar el pre-registro versionado."""
    monkeypatch.setattr(attribution, "PHASE2_ATTRIBUTION_PROFILE", tiny_profile)
    small = {
        key: dataclasses.replace(config, **SMALL_GRID)
        for key, config in PHASE2_PROTOCOL_CONFIGS.items()
    }
    monkeypatch.setattr(attribution, "PHASE2_PROTOCOL_CONFIGS", small)
    return tiny_profile


def test_atribucion_de_fase_ii_con_pocas_semillas(small_phase2: str) -> None:
    report = run_phase2_attribution(seeds=(3,))
    assert report.profile == small_phase2
    assert report.rules == ALL_DESIGN_RULES
    assert [e.claim_id for e in report.evaluations] == ["C5", "C6", "C7", "C8"]
    for evaluation in report.evaluations:
        assert evaluation.status is ClaimStatus.INSUFFICIENT_EVIDENCE
        assert evaluation.by_construction is True
        assert evaluation.seeds == (3,)
        assert list(evaluation.rule_effects) == EXPECTED_EFFECTS[evaluation.claim_id]
        assert "purpose_ablated" not in evaluation.values
    c6 = report.evaluations[1]
    configs = attribution.PHASE2_PROTOCOL_CONFIGS
    drift = ablate(dataclasses.replace(configs["002a"], seed=3), ["R12"])
    assert c6.values["isolated"][0] == measure_claim(C6, drift, small_phase2)
    assert c6.values["isolated"] == c6.values["without:R12"]
    c8 = report.evaluations[3]
    without_view = ablate(dataclasses.replace(configs["003b"], seed=3), ["R22"])
    assert c8.values["isolated"][0] == measure_claim(C8, without_view, small_phase2)


def test_atribucion_de_fase_ii_paralelismo_inocuo(small_phase2: str) -> None:
    sequential = run_phase2_attribution(seeds=(3,), claims=(C8,))
    parallel = run_phase2_attribution(seeds=(3,), claims=(C8,), jobs=2)
    assert sequential == parallel


def test_cada_atribucion_acepta_solo_sus_afirmaciones() -> None:
    with pytest.raises(ValueError, match="C5"):
        run_protocol_001d_attribution(SMALL, [3], claims=EXP002_CLAIMS)
    with pytest.raises(ValueError, match="C1"):
        run_phase2_attribution(seeds=(3,), claims=EXP001_CLAIMS[:1])
    with pytest.raises(ValueError, match="repetidas"):
        run_phase2_attribution(seeds=(3, 3), claims=(C8,))


def test_c7_y_c8_comparten_sus_corridas_identicas(
    small_phase2: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """003-A y 003-B tienen la misma configuración: C8 no repite las corridas de C7."""
    sizes: list[int] = []
    original = attribution.map_in_order

    def counting(function: Any, items: Any, jobs: int) -> Any:
        sizes.append(len(items))
        return original(function, items, jobs)

    monkeypatch.setattr(attribution, "map_in_order", counting)
    alone = run_phase2_attribution(seeds=(3,), claims=(C7,))
    both = run_phase2_attribution(seeds=(3,), claims=(C7, C8))
    assert sizes[0] == sizes[1]
    assert both.evaluations[0] == alone.evaluations[0]


def test_c8_exige_r18_apagada(small_phase2: str) -> None:
    configs = attribution.PHASE2_PROTOCOL_CONFIGS
    with_r18 = dataclasses.replace(configs["003b"], enable_downward_causation=True)
    with pytest.raises(ValueError, match="R18"):
        measure_claim(C8, with_r18, small_phase2)
    configs["003b"] = with_r18
    with pytest.raises(ValueError, match="R18"):
        run_phase2_attribution(seeds=(3,), claims=(C8,))


def test_tipo_de_corrida_desconocido() -> None:
    with pytest.raises(ValueError, match="tipo de corrida desconocido"):
        attribution._run("foo", SMALL, PROFILES["quick"])  # pyright: ignore[reportPrivateUsage]


def test_configuraciones_originales_conservadas() -> None:
    """Enmienda 1 de D29: las configuraciones previas a la calibración se corren como referencia."""
    holonic = SimulationConfig(
        enable_evolution=True,
        enable_holonic_hierarchy=True,
        enable_holon_reproduction=True,
        num_composite_patterns=3,
        composite_order=4,
    )
    assert {
        "002a": SimulationConfig(enable_evolution=True),
        "002b": SimulationConfig(enable_evolution=True, enable_cultural_inheritance=True),
        "003a": holonic,
        "003b": holonic,
    } == PHASE2_PROTOCOL_CONFIGS_ORIGINAL
    assert all(c.resources_per_pattern == 8 for c in PHASE2_PROTOCOL_CONFIGS_ORIGINAL.values())


def test_demografia_por_variante(small_phase2: str) -> None:
    """Registro de la Enmienda 1: población final y generación máxima por variante y semilla."""
    from ide.experiments.exp002_runner import run_evolution_condition

    report = run_phase2_attribution(seeds=(3, 4), claims=(C6,))
    evaluation = report.evaluations[0]
    assert list(evaluation.demography) == list(evaluation.values)
    ticks = PROFILES[small_phase2].total_ticks
    drift = ablate(
        dataclasses.replace(attribution.PHASE2_PROTOCOL_CONFIGS["002a"], seed=4), ["R12"]
    )
    summary = run_evolution_condition(drift, ticks)
    assert evaluation.demography["isolated"][1] == (summary.final_agents, summary.max_generation)
    assert all(len(per_seed) == 2 for per_seed in evaluation.demography.values())


def test_fase_i_sin_demografia() -> None:
    assert evaluate(UP, by_construction=True).demography == {}


def test_atribucion_sobre_configuraciones_de_referencia(small_phase2: str) -> None:
    reference = {
        k: dataclasses.replace(c, resources_per_pattern=3)
        for k, c in attribution.PHASE2_PROTOCOL_CONFIGS.items()
    }
    report = run_phase2_attribution(seeds=(3,), claims=(C6,), configs=reference)
    config = dataclasses.replace(reference["002a"], seed=3)
    assert report.evaluations[0].values["full"][0] == measure_claim(C6, config, small_phase2)


def test_e4_no_interpretable_en_fase_ii(small_phase2: str) -> None:
    """Respaldo de la Enmienda 1b: con 20 recursos el control nulo se extingue; E4 no se lee."""
    configs = attribution.PHASE2_PROTOCOL_CONFIGS
    amended = {k: dataclasses.replace(c, resources_per_pattern=20) for k, c in configs.items()}
    reference = {k: dataclasses.replace(c, resources_per_pattern=8) for k, c in configs.items()}
    report = run_phase2_attribution(seeds=(3,), claims=(C6,), configs=amended)
    assert report.evaluations[0].e4_interpretable is False
    # Fuera de la abundancia del perfil (p. ej., la referencia con 8) la marca no aplica.
    report = run_phase2_attribution(seeds=(3,), claims=(C6,), configs=reference)
    assert report.evaluations[0].e4_interpretable is True
    assert evaluate(UP, by_construction=True).e4_interpretable is True  # Fase I no cambia


# --- Fase II-B: pre-registro D56 (bloque 22) ---------------------------------------------------

PHASE25_RULE_TABLE = [
    (
        "R24",
        "ADN compacto y expresión condicional",
        "Rasgos en codones de 32 bits expresados según el contexto, con costo sobre lo expresado. "
        "Sesgo declarado: abarata la complejidad latente.",
        "enable_compact_dna",
    ),
    (
        "R25",
        "Señal posicional epigenética",
        "Proveer una señal de posición y conocimiento dentro del holón; su uso lo decide el ADN.",
        "enable_epigenetic_roles",
    ),
    (
        "R26",
        "Conjugación de plásmidos",
        "Transferir codones entre vecinos en vida.",
        "enable_plasmid_hgt",
    ),
    (
        "R27",
        "Inmunidad CRISPR",
        "Purgar plásmidos con balance energético negativo y bloquear su reingreso.",
        "enable_crispr_immunity",
    ),
    (
        "R28",
        "Endospora disponible",
        "Permitir un estado de bajo gasto; su uso lo decide el ADN.",
        "enable_sporulation",
    ),
    (
        "R29",
        "Senescencia telomérica",
        "Limitar la vida con una longevidad expresada. Sesgo declarado: fuerza recambio.",
        "enable_telomere_senescence",
    ),
    (
        "R30",
        "Mutación SOS",
        "Aumentar la variación bajo estrés y reducirla en abundancia.",
        "enable_sos_mutation",
    ),
    (
        "R31",
        "Compromiso simbiótico",
        "Permitir que un holón se vuelva indisoluble si sus hojas lo expresan.",
        "enable_symbiotic_ratchet",
    ),
    (
        "R32",
        "Conducta codificada en el ADN",
        "Que la política de acción y la decisión de comunicar se expresen desde el ADN.",
        "enable_genetic_policy",
    ),
    (
        "R33",
        "Recursos agotables",
        "Escasez real: los recursos tardan en reponerse.",
        "enable_resource_depletion",
    ),
    (
        "R34",
        "Heterogeneidad espacial y estacional",
        "Nichos por región y abundancia variable en el tiempo.",
        "enable_heterogeneity",
    ),
    (
        "R35",
        "Cadáveres",
        "Cerrar el ciclo de energía: los muertos son recurso.",
        "enable_carcasses",
    ),
    (
        "R36",
        "Transferencia de energía",
        "Permitir ceder energía a un vecino; su uso lo decide el ADN.",
        "enable_energy_transfer",
    ),
    (
        "R37",
        "Depredación",
        "Permitir robar energía a un vecino más débil; su uso lo decide el ADN.",
        "enable_predation",
    ),
    (
        "R38",
        "Recombinación",
        "Permitir el cruce de cromosomas con una pareja; su uso lo decide el ADN.",
        "enable_recombination",
    ),
    (
        "R39",
        "Estado interno persistente",
        "Permitir que el ADN escriba y lea bits de estado que persisten entre ticks; su uso lo "
        "decide el ADN.",
        "enable_internal_state",
    ),
    (
        "R40",
        "Plasticidad en vida",
        "Permitir codones cuya fuerza se ajusta en vida con una regla de refuerzo mínima; qué y "
        "cuánto se aprende lo decide el ADN.",
        "enable_plasticity",
    ),
    (
        "R41",
        "Señales evolucionables",
        "Permitir emitir y percibir símbolos sin significado de fábrica; su uso y su significado "
        "los construye la evolución.",
        "enable_signals",
    ),
]

PHASE25_FLAGS_25A = (
    "enable_compact_dna",
    "enable_genetic_policy",
    "enable_plasmid_hgt",
    "enable_crispr_immunity",
    "enable_sporulation",
    "enable_telomere_senescence",
    "enable_sos_mutation",
    "enable_resource_depletion",
    "enable_heterogeneity",
    "enable_carcasses",
    "enable_energy_transfer",
    "enable_predation",
    "enable_recombination",
    "enable_internal_state",
    "enable_plasticity",
    "enable_signals",
)
ABUNDANCE_FIELDS = {"resources_per_pattern", "resource_regen_delay"}
NULL = "null_content"


def _changed(a: SimulationConfig, b: SimulationConfig) -> dict[str, Any]:
    """Campos en que `a` difiere de `b`, con el valor de `a`."""
    return {
        f.name: getattr(a, f.name)
        for f in dataclasses.fields(SimulationConfig)
        if getattr(a, f.name) != getattr(b, f.name)
    }


def test_inventario_de_reglas_de_fase_ii_b() -> None:
    """Escenarios de la spec: inventario `R24`..`R41`, nombres, propósitos y ablaciones (D56)."""
    table = [(r.rule_id, r.name, r.purpose, r.ablation[0][0]) for r in PHASE25_DESIGN_RULES]
    assert table == PHASE25_RULE_TABLE
    for rule, (*_, flag) in zip(PHASE25_DESIGN_RULES, PHASE25_RULE_TABLE, strict=True):
        assert rule.ablation == ((flag, False),)
    assert [r.rule_id for r in ALL_DESIGN_RULES] == [f"R{i}" for i in range(1, 24)]
    assert PHASE25_ALL_RULES == ALL_DESIGN_RULES + PHASE25_DESIGN_RULES
    assert len(PHASE25_ALL_RULES) == len(ALL_DESIGN_RULES) + 18


def test_sesgos_declarados_en_el_proposito() -> None:
    purposes = {r.rule_id: r.purpose for r in PHASE25_DESIGN_RULES}
    assert "complejidad latente" in purposes["R24"]
    assert "recambio" in purposes["R29"]
    for rule_id in ("R25", "R28", "R36", "R37", "R38", "R39"):
        assert "su uso lo decide el ADN" in purposes[rule_id], rule_id
    assert "qué y cuánto se aprende lo decide el ADN" in purposes["R40"]
    assert "su uso y su significado los construye la evolución" in purposes["R41"]
    for purpose in purposes.values():
        lowered = purpose.lower()
        assert "especializ" not in lowered
        assert "rescate" not in lowered
        assert "estabilidad" not in lowered


def test_ablacion_de_reglas_de_las_tres_fases() -> None:
    config = SimulationConfig(
        enable_evolution=True,
        enable_compact_dna=True,
        enable_predation=True,
        enable_genetic_policy=True,
        enable_internal_state=True,
        enable_plasticity=True,
    )
    ablated = ablate(config, ["R12", "R24", "R37", "R39", "R40"])
    assert ablated.reproduction_mode == "neutral"
    assert not ablated.enable_compact_dna
    assert not ablated.enable_predation
    assert not ablated.enable_internal_state
    assert not ablated.enable_plasticity


def test_ablacion_de_todas_las_reglas_de_las_tres_fases_es_valida() -> None:
    ablatable = [r.rule_id for r in PHASE25_ALL_RULES if r.ablation]
    for config in PHASE25_PROTOCOL_CONFIGS.values():
        for rule_id in ablatable:
            ablate(config, [rule_id])
        ablate(config, ablatable)


def test_configuracion_de_25a() -> None:
    a = PHASE25_PROTOCOL_CONFIGS["25a"]
    changed = _changed(a, PHASE2_PROTOCOL_CONFIGS["002a"])
    expected = dict.fromkeys(PHASE25_FLAGS_25A, True) | {
        "season_length": 500,
        "dna_max_length": 64,
    }
    assert {k: v for k, v in changed.items() if k not in ABUNDANCE_FIELDS} == expected
    assert (a.resources_per_pattern, a.resource_regen_delay) == PHASE25_ABUNDANCE


def test_configuraciones_de_25b_25c_y_25d() -> None:
    a, b, c, d = (PHASE25_PROTOCOL_CONFIGS[k] for k in ("25a", "25b", "25c", "25d"))
    changed_b = _changed(b, PHASE2_PROTOCOL_CONFIGS["003a"])
    expected_b = dict.fromkeys(PHASE25_FLAGS_25A, True) | {
        "enable_epigenetic_roles": True,
        "enable_symbiotic_ratchet": True,
        "season_length": 500,
        "dna_max_length": 64,
    }
    assert {k: v for k, v in changed_b.items() if k not in ABUNDANCE_FIELDS} == expected_b
    assert (b.resources_per_pattern, b.resource_regen_delay) == PHASE25_ABUNDANCE
    assert _changed(c, a) == {"comm_propensity_base": 0.0}
    assert _changed(d, a) == {"world_shift_period": 1000}
    assert d.world_shift_fraction == 0.5
    assert list(PHASE25_PROTOCOL_CONFIGS) == ["25a", "25b", "25c", "25d"]


def test_adn_de_64_codones_en_los_protocolos() -> None:
    assert all(c.dna_max_length == 64 for c in PHASE25_PROTOCOL_CONFIGS.values())
    assert SimulationConfig().dna_max_length == 32


def test_abundancia_comun_fijada_por_la_compuerta() -> None:
    """Escenario de la spec: la compuerta elige `(30, 10)` y sólo cambian esos dos campos."""
    chosen = phase25_protocol_configs(30, 10)
    assert list(chosen) == list(PHASE25_PROTOCOL_CONFIGS)
    for key, config in chosen.items():
        assert config.resources_per_pattern == 30
        assert config.resource_regen_delay == 10
        assert set(_changed(config, PHASE25_PROTOCOL_CONFIGS[key])) <= ABUNDANCE_FIELDS
    assert phase25_protocol_configs(*PHASE25_ABUNDANCE) == PHASE25_PROTOCOL_CONFIGS


def test_condiciones_de_25a() -> None:
    config = PHASE25_PROTOCOL_CONFIGS["25a"]
    conditions = phase25_conditions("25a", config)
    assert list(conditions) == ["full", "drift", "no_predation", "no_predation_drift", NULL]
    assert conditions["full"] == config
    assert _changed(conditions["drift"], config) == {"reproduction_mode": "neutral"}
    assert _changed(conditions["no_predation"], config) == {"enable_predation": False}
    assert _changed(conditions["no_predation_drift"], config) == {
        "enable_predation": False,
        "reproduction_mode": "neutral",
    }
    assert _changed(conditions[NULL], config) == {"comm_content_null": True}


def test_condiciones_de_25b_y_25c() -> None:
    for protocol in ("25b", "25c"):
        conditions = phase25_conditions(protocol, PHASE25_PROTOCOL_CONFIGS[protocol])
        assert list(conditions) == ["full", "drift", NULL], protocol


def test_condiciones_de_25d_e_identidad_de_las_estables() -> None:
    config = PHASE25_PROTOCOL_CONFIGS["25d"]
    conditions = phase25_conditions("25d", config)
    assert list(conditions) == ["full", "drift", "stable", "stable_drift", "no_learning", NULL]
    assert _changed(conditions["stable"], config) == {"world_shift_period": 0}
    assert _changed(conditions["stable_drift"], config) == {
        "world_shift_period": 0,
        "reproduction_mode": "neutral",
    }
    assert _changed(conditions["no_learning"], config) == {
        "enable_internal_state": False,
        "enable_plasticity": False,
    }
    a = phase25_conditions("25a", PHASE25_PROTOCOL_CONFIGS["25a"])
    assert conditions["stable"] == a["full"]
    assert conditions["stable_drift"] == a["drift"]


def test_condiciones_de_un_protocolo_desconocido() -> None:
    with pytest.raises(ValueError, match="25z"):
        phase25_conditions("25z", PHASE25_PROTOCOL_CONFIGS["25a"])


def test_drift_conserva_los_mecanismos_residuales() -> None:
    config = PHASE25_PROTOCOL_CONFIGS["25a"]
    drift = phase25_conditions("25a", config)["drift"]
    assert _changed(drift, config) == {"reproduction_mode": "neutral"}
    assert drift.enable_plasmid_hgt and drift.enable_crispr_immunity
    assert drift.enable_sos_mutation and drift.enable_recombination


def test_control_nulo_conserva_la_genetica() -> None:
    config = PHASE25_PROTOCOL_CONFIGS["25a"]
    null = phase25_conditions("25a", config)[NULL]
    assert _changed(null, config) == {"comm_content_null": True}
    assert null.enable_genetic_policy
    assert null.comm_propensity_base == config.comm_propensity_base


def _phase25_rule_is_active(rule_id: str, config: SimulationConfig) -> bool:
    """Bandera de cada regla de la Fase II-B, con sus dependencias; las anteriores, como D29."""
    flags = {r.rule_id: r.ablation[0][0] for r in PHASE25_DESIGN_RULES}
    if rule_id not in flags:
        return _rule_is_active(rule_id, config)
    active = bool(getattr(config, flags[rule_id]))
    if rule_id in ("R25", "R31"):  # sin holones (y R31 sin ADN, precisión 32) son inertes
        active = active and config.enable_holonic_hierarchy and config.enable_compact_dna
    return active


def test_reglas_inactivas_de_fase_ii_b_coinciden_con_las_configuraciones() -> None:
    individual = ("R14", "R15", "R16", "R17", "R18", "R19", "R22", "R23", "R25", "R31")
    assert {
        "25a": individual,
        "25b": ("R14", "R18", "R19"),
        "25c": individual,
        "25d": individual,
    } == PHASE25_INACTIVE_RULES
    ablatable = [r.rule_id for r in PHASE25_ALL_RULES if r.ablation]
    for protocol, config in PHASE25_PROTOCOL_CONFIGS.items():
        inactive = [rid for rid in ablatable if not _phase25_rule_is_active(rid, config)]
        assert tuple(inactive) == PHASE25_INACTIVE_RULES[protocol], protocol
        for rule_id in PHASE25_INACTIVE_RULES[protocol]:
            assert not _phase25_rule_is_active(rule_id, ablate(config, [rule_id]))


def test_perfil_y_semillas_de_fase_ii_b() -> None:
    assert PHASE25_ATTRIBUTION_PROFILE == "phase25"
    assert PROFILES["phase25"].total_ticks == 5000
    assert tuple(range(42, 72)) == PHASE25_SEEDS
    assert len(PHASE25_SEEDS) == 30
    assert tuple(range(42, 52)) == PHASE25_RULE_EFFECT_SEEDS == PHASE2_SEEDS
    assert tuple(range(0, 10)) == PHASE25_VIABILITY_SEEDS
    assert not set(PHASE25_VIABILITY_SEEDS) & set(PHASE25_SEEDS)
    assert PHASE25_FINAL_WINDOW == 1000
    assert PHASE25_MIN_VALID_PAIRS == 20
    assert PHASE25_HOLM_M == 7
    assert PROFILES[PHASE2_ATTRIBUTION_PROFILE].total_ticks == 2000


# --- Fase II-B: afirmaciones y tipos -----------------------------------------------------------

CLAIMS25 = {c.claim_id: c for c in PHASE25_CLAIMS}


def test_campos_de_phase25claim() -> None:
    names = [f.name for f in dataclasses.fields(Phase25Claim)]
    assert names == [
        "claim_id",
        "statement",
        "protocol",
        "metric",
        "comparison",
        "rule_ids",
        "channel",
        "delta_min",
        "delta_relative",
        "baseline_drift",
        "comparison_drift",
    ]
    claim = Phase25Claim("CX", "x", "25a", "m", "drift", ("R12",), (), 1.0)
    assert claim.delta_relative == 0.0
    assert claim.baseline_drift is None
    assert claim.comparison_drift is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        claim.delta_min = 2.0  # type: ignore[misc]


def test_afirmaciones_pre_registradas_de_fase_ii_b() -> None:
    """Escenarios de la spec: C13-C20 con protocolos, métricas, comparaciones y umbrales (D56)."""
    table = [
        (
            c.claim_id,
            c.protocol,
            c.metric,
            c.comparison,
            c.rule_ids,
            c.channel,
            c.delta_min,
            c.delta_relative,
            c.baseline_drift,
            c.comparison_drift,
        )
        for c in PHASE25_CLAIMS
    ]
    assert table == [
        ("C13", "25a", "mean_conditional_codons", "drift", ("R12",), (), 1.0, 0.0, None, None),
        ("C14", "25a", "policy_divergence", "drift", ("R12",), (), 0.05, 0.0, None, None),
        ("C15", "25c", "communicating_fraction", "drift", ("R12",), (), 0.10, 0.0, None, None),
        ("C16", "25a", "new_activity_per_birth", "drift", ("R12",), (), 0.001, 0.25, None, None),
        (
            "C17",
            "25a",
            "mean_expressible_nonattack_codons",
            "no_predation",
            ("R37",),
            (),
            1.0,
            0.0,
            "drift",
            "no_predation_drift",
        ),
        ("C18", "25b", "share_rate", "drift", ("R12",), (), 0.01, 0.0, None, None),
        ("C19", "25d", "mean_learning_codons", "stable", (), (), 1.0, 0.0, "drift", "stable_drift"),
        (
            "C20",
            "25d",
            "post_shift_accuracy",
            "no_learning",
            ("R39", "R40"),
            ("R39", "R40"),
            0.02,
            0.0,
            None,
            None,
        ),
    ]
    statements = {c.claim_id: c.statement for c in PHASE25_CLAIMS}
    assert statements == {
        "C13": "La regulación génica evoluciona",
        "C14": "La conducta evoluciona",
        "C15": "La comunicación evoluciona desde cero",
        "C16": "Actividad evolutiva por encima de la reproducción neutral",
        "C17": "La depredación aumenta la complejidad genética",
        "C18": "La cooperación material evoluciona en la ecología holónica",
        "C19": "La memoria y el aprendizaje evolucionan cuando el entorno cambia",
        "C20": "La memoria y la plasticidad aceleran la recuperación tras un cambio del entorno",
    }


def test_condiciones_de_cada_afirmacion() -> None:
    assert claim_conditions(CLAIMS25["C13"]) == ("full", "drift")
    assert claim_conditions(CLAIMS25["C17"]) == (
        "full",
        "drift",
        "no_predation",
        "no_predation_drift",
    )
    assert claim_conditions(CLAIMS25["C19"]) == ("full", "drift", "stable", "stable_drift")
    assert claim_conditions(CLAIMS25["C20"]) == ("full", "no_learning")


def test_campos_de_la_evaluacion_y_del_reporte() -> None:
    assert [f.name for f in dataclasses.fields(Phase25ClaimEvaluation)] == [
        "claim_id",
        "status",
        "p_value",
        "p_adjusted",
        "median_difference",
        "values",
        "comparison_values",
        "demography",
        "e4_p_value",
        "e4_interpretable",
        "excluded_seeds",
        "excluded_pairs",
        "evaluable",
    ]
    assert [f.name for f in dataclasses.fields(Phase25Report)] == [
        "profile",
        "rules",
        "evaluations",
        "rule_effects",
    ]
    report = Phase25Report(evaluations=(), rule_effects={})
    assert report.profile == "phase25"
    assert report.rules == PHASE25_ALL_RULES
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.profile = "x"  # type: ignore[misc]


def test_estado_observed_solo_agrega_un_miembro() -> None:
    assert [s.name for s in ClaimStatus] == [
        "INSUFFICIENT_EVIDENCE",
        "NOT_OBSERVED",
        "PROGRAMMED",
        "ACTIVITY_ARTIFACT",
        "EMERGENT_PENDING_ROBUSTNESS",
        "SCHEDULING_ARTIFACT",
        "EMERGENT",
        "OBSERVED",
    ]
    assert ClaimStatus.OBSERVED.value == "OBSERVED"


def test_clasificacion_de_c13_a_c20() -> None:
    """C13-C19 con canal vacío no son programadas; C20 sí (canal contenido en R_C)."""
    by_construction = attribution._phase25_by_construction  # pyright: ignore[reportPrivateUsage]
    for claim in PHASE25_CLAIMS:
        assert by_construction(claim) is (claim.claim_id == "C20"), claim.claim_id
    for claim in EXP002_CLAIMS + EXP003_CLAIMS:
        assert is_by_construction(claim, PHASE2_PROTOCOL_CONFIGS[claim.protocol])
    assert [is_by_construction(c, CFG) for c in EXP001_CLAIMS] == [True, True, False, True]


# --- Fase II-B: métricas de una corrida --------------------------------------------------------


def test_ventana_final() -> None:
    assert final_window(list(range(45))) == list(range(45))
    assert final_window(list(range(1500))) == list(range(500, 1500))
    assert final_window(list(range(5000))) == list(range(4000, 5000))


def _history(
    ticks: int, **fields: Callable[[int], object] | float | tuple[int, ...]
) -> list[SimpleNamespace]:
    """Historial sintético: cada campo es una función del tick o un valor fijo."""
    return [
        SimpleNamespace(tick=t, **{k: (v(t) if callable(v) else v) for k, v in fields.items()})
        for t in range(ticks)
    ]


def test_metrica_de_ventana_final_y_ultimo_tick() -> None:
    genetic = _history(
        5000,
        mean_conditional_codons=float,
        new_activity_per_birth=lambda t: t / 10_000,
    )
    ecology = _history(5000, share_rate=lambda t: 1.0 if t >= 4000 else 0.0)
    assert phase25_metric_value("mean_conditional_codons", genetic, ecology, 0) == (
        pytest.approx(4499.5, abs=1e-9)
    )
    assert phase25_metric_value("new_activity_per_birth", genetic, ecology, 0) == (
        pytest.approx(0.4999, abs=1e-9)
    )
    assert phase25_metric_value("share_rate", genetic, ecology, 0) == pytest.approx(1.0, abs=1e-9)
    short = _history(45, policy_divergence=lambda t: 1.0 if t == 0 else 0.0)
    assert phase25_metric_value("policy_divergence", short, short, 0) == (
        pytest.approx(1 / 45, abs=1e-9)
    )
    with pytest.raises(ValueError, match="desconocida"):
        phase25_metric_value("evolved_accuracy", genetic, ecology, 0)


def test_ventana_de_25d_empieza_en_un_cambio() -> None:
    """La ventana final de 5000 ticks son los ticks 4000-4999 (precisiones 4 y 56)."""
    genetic = _history(5000, mean_learning_codons=lambda t: 1.0 if t >= 4000 else 100.0)
    assert phase25_metric_value("mean_learning_codons", genetic, genetic, 1000) == 1.0


def _ecology_with_shifts(ticks: int) -> list[SimpleNamespace]:
    def correct(t: int) -> int:
        return 6 if 1000 <= t < 1200 or 2000 <= t < 2200 else 10

    return _history(ticks, decision_opportunities=10, correct_decisions=correct)


def test_exactitud_tras_los_cambios_del_entorno() -> None:
    ecology = _ecology_with_shifts(2500)
    assert post_shift_accuracy(ecology, 1000) == pytest.approx(0.6, abs=1e-9)
    assert post_shift_accuracy(ecology, 0) == 0.0
    assert phase25_metric_value("post_shift_accuracy", [], ecology, 1000) == pytest.approx(
        0.6, abs=1e-9
    )
    none = _history(2500, decision_opportunities=0, correct_decisions=0)
    assert post_shift_accuracy(none, 1000) == 0.0
    assert post_shift_accuracy(_ecology_with_shifts(900), 1000) == 0.0  # ningún cambio


def test_numero_efectivo_de_progenitores() -> None:
    genetic = _history(3, birth_source_ids=lambda t: [(3,), (), (3, 7, 9)][t])
    assert effective_parents(genetic) == pytest.approx(16 / 6, abs=1e-9)
    assert effective_parents(_history(3, birth_source_ids=())) == 0.0

    def sources(t: int) -> tuple[int, ...]:
        if t < 500:
            return (1, 2)
        return (5,) if t == 999 else ()

    # Sólo cuenta la ventana final: los nacimientos de los ticks 0-499 no entran.
    assert effective_parents(_history(1500, birth_source_ids=sources)) == 1.0


def _fake_engine() -> SimpleNamespace:
    genetic = _history(
        3,
        birth_source_ids=lambda t: [(3,), (), (3, 7, 9)][t],
        mean_age_at_death=lambda t: [0.0, 4.0, 7.5][t],
        mean_conditional_codons=float,
        new_activity_per_birth=0.25,
    )
    ecology = _history(3, share_rate=0.5, decision_opportunities=2, correct_decisions=1)
    evolution = [
        SimpleNamespace(max_generation=g, births_this_tick=b, deaths_this_tick=d)
        for g, b, d in [(1, 2, 1), (2, 0, 1), (2, 3, 0)]
    ]
    agents = {
        1: SimpleNamespace(is_endospore=False),
        2: SimpleNamespace(is_endospore=True),
        5: SimpleNamespace(is_endospore=False),
    }
    return SimpleNamespace(
        agents=agents,
        genetic_history=genetic,
        ecology_history=ecology,
        evolutionary_history=evolution,
    )


def test_registro_de_una_corrida() -> None:
    """Demografía de la corrida (precisiones 44, 45, 49 y 68) y métricas pedidas."""
    metrics = ("mean_conditional_codons", "new_activity_per_birth", "share_rate")
    record = phase25_run_record(_fake_engine(), metrics, 0)
    assert record.final_agents == 3
    assert record.final_active_agents == 2
    assert record.max_generation == 2
    assert record.cumulative_births == 5
    assert record.cumulative_deaths == 2
    assert record.mean_age_at_death == pytest.approx(7.5, abs=1e-9)
    assert record.effective_parents == pytest.approx(16 / 6, abs=1e-9)
    assert record.metrics == {
        "mean_conditional_codons": pytest.approx(1.0, abs=1e-9),
        "new_activity_per_birth": pytest.approx(0.25, abs=1e-9),
        "share_rate": pytest.approx(0.5, abs=1e-9),
    }
    demography = record.demography()
    assert demography == {
        "final_agents": 3.0,
        "final_active_agents": 2.0,
        "max_generation": 2.0,
        "cumulative_births": 5.0,
        "cumulative_deaths": 2.0,
        "mean_age_at_death": 7.5,
        "effective_parents": pytest.approx(16 / 6, abs=1e-9),
    }
    assert all(isinstance(v, float) for v in demography.values())


# --- Fase II-B: evaluación ---------------------------------------------------------------------

SEEDS30 = PHASE25_SEEDS
DEMOGRAPHY_FIELDS = {
    "final_agents",
    "final_active_agents",
    "max_generation",
    "cumulative_births",
    "cumulative_deaths",
    "mean_age_at_death",
    "effective_parents",
}
Records = dict[str, dict[str, dict[int, Phase25RunRecord]]]


def _rec(metrics: Mapping[str, float], active: int = 4) -> Phase25RunRecord:
    return Phase25RunRecord(
        final_agents=active + 1,
        final_active_agents=active,
        max_generation=25,
        cumulative_births=10,
        cumulative_deaths=4,
        mean_age_at_death=12.5,
        effective_parents=3.0,
        metrics=dict(metrics),
    )


def _records(
    claims: Sequence[Phase25Claim],
    values: Mapping[tuple[str, str], Sequence[float]],
    seeds: Sequence[int] = SEEDS30,
    extinct: Sequence[tuple[str, str, int]] = (),
) -> Records:
    """Corridas sintéticas: `values[(afirmación, condición)]` por semilla; 0.0 si falta.

    `extinct` lista las (protocolo, condición, semilla) que terminan sin hojas activas.
    """
    records: Records = {}
    for claim in claims:
        for condition in (*claim_conditions(claim), NULL):
            per_seed = records.setdefault(claim.protocol, {}).setdefault(condition, {})
            series = values.get((claim.claim_id, condition), [0.0] * len(seeds))
            for seed, value in zip(seeds, series, strict=True):
                old = per_seed.get(seed)
                metrics = {**(old.metrics if old else {}), claim.metric: value}
                dead = (claim.protocol, condition, seed) in extinct
                per_seed[seed] = _rec(metrics, active=0 if dead else 4)
    return records


def _evaluate(
    claims: Sequence[Phase25Claim],
    values: Mapping[tuple[str, str], Sequence[float]],
    seeds: Sequence[int] = SEEDS30,
    extinct: Sequence[tuple[str, str, int]] = (),
    e4: Mapping[str, bool] | None = None,
) -> dict[str, Phase25ClaimEvaluation]:
    records = _records(claims, values, seeds, extinct)
    evaluations = evaluate_phase25_claims(claims, records, seeds, e4)
    return {e.claim_id: e for e in evaluations}


def test_diferencia_de_diferencias_de_c17() -> None:
    values = {
        ("C17", "full"): [9.0],
        ("C17", "drift"): [6.0],
        ("C17", "no_predation"): [7.0],
        ("C17", "no_predation_drift"): [5.5],
    }
    evaluation = _evaluate([CLAIMS25["C17"]], values, seeds=(42,))["C17"]
    assert evaluation.values == {42: pytest.approx(3.0, abs=1e-9)}
    assert evaluation.comparison_values == {42: pytest.approx(1.5, abs=1e-9)}
    assert evaluation.median_difference == pytest.approx(1.5, abs=1e-9)


def test_valores_de_c19() -> None:
    values = {
        ("C19", "full"): [4.0],
        ("C19", "drift"): [1.0],
        ("C19", "stable"): [2.0],
        ("C19", "stable_drift"): [1.0],
    }
    evaluation = _evaluate([CLAIMS25["C19"]], values, seeds=(42,))["C19"]
    assert evaluation.values == {42: pytest.approx(3.0, abs=1e-9)}
    assert evaluation.comparison_values == {42: pytest.approx(1.0, abs=1e-9)}
    assert evaluation.median_difference == pytest.approx(2.0, abs=1e-9)


def test_diferencia_simple() -> None:
    values = {("C13", "full"): [5.0], ("C13", "drift"): [3.5]}
    evaluation = _evaluate([CLAIMS25["C13"]], values, seeds=(42,))["C13"]
    assert evaluation.values == {42: 5.0}
    assert evaluation.comparison_values == {42: 3.5}
    assert evaluation.median_difference == pytest.approx(1.5, abs=1e-9)


def test_prueba_de_signo_con_empates() -> None:
    """Escenario de la spec: 20 positivas, 5 negativas y 5 nulas; n = 25."""
    full = [1.0] * 20 + [0.0] * 5 + [0.5] * 5
    drift = [0.0] * 20 + [1.0] * 5 + [0.5] * 5
    evaluation = _evaluate([CLAIMS25["C14"]], {("C14", "full"): full, ("C14", "drift"): drift})
    assert evaluation["C14"].p_value == pytest.approx(0.0020386576652526855, abs=1e-9)
    assert evaluation["C14"].evaluable is True


def test_pares_validos_con_extincion() -> None:
    evaluation = _evaluate(
        [CLAIMS25["C14"]], {("C14", "full"): [1.0] * 30}, extinct=[("25a", "drift", 50)]
    )["C14"]
    assert evaluation.excluded_seeds == (50,)
    assert evaluation.excluded_pairs == 1
    assert evaluation.p_value == pytest.approx(0.5**29, abs=1e-15)


def test_pares_validos_en_la_diferencia_de_diferencias() -> None:
    evaluation = _evaluate(
        [CLAIMS25["C17"]],
        {("C17", "full"): [2.0] * 30},
        extinct=[("25a", "no_predation_drift", 47)],
    )["C17"]
    assert evaluation.excluded_seeds == (47,)
    assert evaluation.excluded_pairs == 1
    assert evaluation.p_value == pytest.approx(0.5**29, abs=1e-15)


def test_afirmacion_no_evaluable() -> None:
    """Escenario de la spec: C18 con 19 pares válidos y mediana 0.05."""
    extinct = [("25b", "full", s) for s in SEEDS30[19:]]
    evaluation = _evaluate([CLAIMS25["C18"]], {("C18", "full"): [0.05] * 30}, extinct=extinct)[
        "C18"
    ]
    assert evaluation.evaluable is False
    assert evaluation.status is ClaimStatus.NOT_OBSERVED
    assert evaluation.excluded_seeds == SEEDS30[19:]
    assert evaluation.excluded_pairs == 11
    assert evaluation.p_value == pytest.approx(0.5**19, abs=1e-15)
    # Sigue en la corrección de Holm con m = 7 (las ausentes cuentan como p = 1).
    assert evaluation.p_adjusted == pytest.approx(7 * 0.5**19, abs=1e-15)
    assert evaluation.median_difference == pytest.approx(0.05, abs=1e-9)


def test_sin_diferencias_distintas_de_cero() -> None:
    extinct = [("25c", "drift", s) for s in SEEDS30[12:]]
    c15 = _evaluate([CLAIMS25["C15"]], {}, extinct=extinct)["C15"]
    assert c15.evaluable is False
    assert c15.p_value == 1.0
    assert c15.p_adjusted == 1.0
    c14 = _evaluate([CLAIMS25["C14"]], {})["C14"]
    assert c14.evaluable is True
    assert c14.p_value == 1.0
    assert c14.status is ClaimStatus.NOT_OBSERVED


def test_pares_suficientes() -> None:
    extinct = [("25a", "drift", s) for s in SEEDS30[20:]]
    c13 = _evaluate([CLAIMS25["C13"]], {("C13", "full"): [2.0] * 30}, extinct=extinct)["C13"]
    assert c13.evaluable is True
    assert c13.status is ClaimStatus.OBSERVED  # p ajustado 7 · 2⁻²⁰ y mediana 2.0 >= 1.0


def test_ajuste_de_holm() -> None:
    """Escenario de la spec: los siete p-valores crudos de C13-C19."""
    raw = [0.001, 0.004, 0.03, 0.02, 0.2, 0.5, 0.01]
    adjusted = holm_bonferroni(raw)
    assert adjusted == pytest.approx([0.007, 0.024, 0.09, 0.08, 0.4, 0.5, 0.05], abs=1e-9)
    assert [p < 0.05 for p in adjusted] == [True, True, False, False, False, False, False]
    # Con menos p-valores que m, las ausentes cuentan como p = 1 (conservador).
    assert holm_bonferroni([0.01], m=7) == pytest.approx([0.07], abs=1e-12)
    with pytest.raises(ValueError, match="m"):
        holm_bonferroni([0.1, 0.2], m=1)


@given(st.lists(st.floats(min_value=0.0, max_value=1.0), max_size=12))
def test_propiedades_de_holm(raw: list[float]) -> None:
    adjusted = holm_bonferroni(raw)
    assert len(adjusted) == len(raw)
    assert all(p <= a <= 1.0 for p, a in zip(raw, adjusted, strict=True))
    order = sorted(range(len(raw)), key=lambda i: raw[i])
    in_order = [adjusted[i] for i in order]
    assert in_order == sorted(in_order)
    assert holm_bonferroni(raw[::-1]) == adjusted[::-1]


@given(st.lists(st.integers(min_value=0, max_value=6), max_size=40))
def test_propiedades_de_effective_parents(sources: list[int]) -> None:
    genetic = [SimpleNamespace(tick=0, birth_source_ids=tuple(sorted(sources)))]
    value = effective_parents(genetic)
    if not sources:
        assert value == 0.0
    else:
        assert 1.0 - 1e-9 <= value <= len(set(sources)) + 1e-9


def _all_claim_values(c20_up: bool) -> dict[tuple[str, str], list[float]]:
    """Diferencias fijas en C13-C19 y una C20 que cambia de dirección."""
    values: dict[tuple[str, str], list[float]] = {}
    for index, claim in enumerate(PHASE25_CLAIMS):
        positives = 10 + 2 * index
        values[(claim.claim_id, "full")] = [1.0] * positives + [0.0] * (30 - positives)
    if not c20_up:
        values[("C20", "no_learning")] = [2.0] * 30
    return values


def test_holm_sin_c20() -> None:
    """Escenario de la spec: el p-valor de C20 no altera los ajustados de C13-C19."""
    up = _evaluate(PHASE25_CLAIMS, _all_claim_values(c20_up=True))
    down = _evaluate(PHASE25_CLAIMS, _all_claim_values(c20_up=False))
    assert up["C20"].p_value < 0.001
    assert down["C20"].p_value > 0.9
    genuine = [f"C{i}" for i in range(13, 20)]
    for claim_id in genuine:
        assert up[claim_id].p_adjusted == down[claim_id].p_adjusted
    expected = holm_bonferroni([up[c].p_value for c in genuine])
    assert [up[c].p_adjusted for c in genuine] == expected
    assert up["C20"].p_adjusted is None
    assert down["C20"].p_adjusted is None


@pytest.mark.parametrize(
    ("p_value", "p_adjusted", "median", "expected"),
    [
        (0.001, 0.006, 0.5, False),  # C13 significativa con efecto chico
        (0.01, 0.08, 2.0, False),  # C17 con efecto grande sin significancia
        (0.001, 0.04, 1.0, True),
        (0.001, 0.05, 2.0, False),  # en el límite no es menor que α
    ],
)
def test_estado_de_las_genuinas(
    p_value: float, p_adjusted: float, median: float, expected: bool
) -> None:
    kwargs = {"p_value": p_value, "p_adjusted": p_adjusted, "median_difference": median}
    status = phase25_status(by_construction=False, evaluable=True, threshold=1.0, **kwargs)
    assert status is (ClaimStatus.OBSERVED if expected else ClaimStatus.NOT_OBSERVED)
    unevaluable = phase25_status(by_construction=False, evaluable=False, threshold=1.0, **kwargs)
    assert unevaluable is ClaimStatus.NOT_OBSERVED


def test_estado_de_c20() -> None:
    """Escenarios de la spec: C20 usa el p-valor crudo, sin Holm (precisión 53)."""
    observed = phase25_status(
        by_construction=True,
        evaluable=True,
        p_value=0.03,
        p_adjusted=None,
        median_difference=0.05,
        threshold=0.02,
    )
    assert observed is ClaimStatus.OBSERVED
    small = phase25_status(
        by_construction=True,
        evaluable=True,
        p_value=0.001,
        p_adjusted=None,
        median_difference=0.01,
        threshold=0.02,
    )
    assert small is ClaimStatus.NOT_OBSERVED
    with pytest.raises(ValueError, match="ajustado"):
        phase25_status(
            by_construction=False,
            evaluable=True,
            p_value=0.01,
            p_adjusted=None,
            median_difference=1.0,
            threshold=1.0,
        )


def test_c20_observada_sin_escalera() -> None:
    evaluation = _evaluate([CLAIMS25["C20"]], {("C20", "full"): [0.05] * 30})["C20"]
    assert evaluation.status is ClaimStatus.OBSERVED
    assert evaluation.p_adjusted is None
    assert not hasattr(evaluation, "p_vs_isolated")


def test_mediana_con_empates() -> None:
    """Escenario de la spec: 14 diferencias de 2.0 y 16 nulas; la mediana es 0.0."""
    full = [2.0] * 14 + [0.0] * 16
    evaluation = _evaluate([CLAIMS25["C17"]], {("C17", "full"): full})["C17"]
    assert evaluation.p_value == pytest.approx(0.5**14, abs=1e-15)
    assert evaluation.p_adjusted is not None
    assert evaluation.p_adjusted < 0.05
    assert evaluation.median_difference == 0.0
    assert evaluation.status is ClaimStatus.NOT_OBSERVED


def test_umbral_de_efecto() -> None:
    c16, c13 = CLAIMS25["C16"], CLAIMS25["C13"]
    assert effect_threshold(c16, 0.02) == pytest.approx(0.005, abs=1e-9)
    assert effect_threshold(c16, 0.002) == pytest.approx(0.001, abs=1e-9)
    assert effect_threshold(c13, 100.0) == 1.0


def test_umbral_relativo_de_c16_en_la_evaluacion() -> None:
    """Escenario de la spec: mediana de drift 0.02 y de las diferencias 0.004: no observada."""
    drift = [0.02] * 30
    evaluation = _evaluate(
        [CLAIMS25["C16"]], {("C16", "full"): [0.024] * 30, ("C16", "drift"): drift}
    )["C16"]
    assert evaluation.p_adjusted is not None
    assert evaluation.p_adjusted < 0.05
    assert evaluation.median_difference == pytest.approx(0.004, abs=1e-9)
    assert evaluation.status is ClaimStatus.NOT_OBSERVED
    bigger = _evaluate([CLAIMS25["C16"]], {("C16", "full"): [0.026] * 30, ("C16", "drift"): drift})[
        "C16"
    ]
    assert bigger.status is ClaimStatus.OBSERVED


def test_demografia_de_la_evaluacion() -> None:
    c16 = _evaluate([CLAIMS25["C16"]], {}, extinct=[("25a", "drift", 50)])["C16"]
    assert list(c16.demography) == ["full", "drift"]
    for per_seed in c16.demography.values():
        assert list(per_seed) == list(SEEDS30)  # también las semillas excluidas
        for fields in per_seed.values():
            assert set(fields) == DEMOGRAPHY_FIELDS
            assert all(isinstance(v, float) for v in fields.values())
    assert c16.demography["drift"][50]["final_active_agents"] == 0.0
    assert c16.demography["full"][42]["effective_parents"] == 3.0
    c17 = _evaluate([CLAIMS25["C17"]], {})["C17"]
    assert list(c17.demography) == ["full", "drift", "no_predation", "no_predation_drift"]


def test_e4_con_control_nulo_extinguido() -> None:
    evaluation = _evaluate(
        [CLAIMS25["C14"]],
        {("C14", "full"): [1.0] * 30},
        extinct=[("25a", NULL, 45)],
        e4={"25a": True},
    )["C14"]
    assert evaluation.e4_p_value == pytest.approx(0.5**29, abs=1e-15)
    assert evaluation.e4_interpretable is True
    assert evaluation.excluded_seeds == ()  # E4 no excluye pares de la afirmación


def test_e4_simple_en_la_diferencia_de_diferencias() -> None:
    values = {
        ("C19", "full"): [3.0] * 30,
        ("C19", "drift"): [5.0] * 30,
        ("C19", "stable"): [9.0] * 30,
        ("C19", "stable_drift"): [9.0] * 30,
        ("C19", NULL): [2.0] * 30,
    }
    evaluation = _evaluate([CLAIMS25["C19"]], values)["C19"]
    assert evaluation.e4_p_value == pytest.approx(0.5**30, abs=1e-15)
    assert evaluation.p_value == 1.0  # la diferencia de diferencias es negativa


def test_e4_condicionado_a_la_compuerta() -> None:
    assert e4_interpretable(9) is True
    assert e4_interpretable(10) is True
    assert e4_interpretable(8) is False
    assert e4_interpretable(None) is False
    claims = [CLAIMS25["C14"], CLAIMS25["C18"]]
    evaluations = _evaluate(claims, {}, e4={"25a": True, "25b": False})
    assert evaluations["C14"].e4_interpretable is True
    assert evaluations["C18"].e4_interpretable is False
    assert _evaluate(claims, {})["C14"].e4_interpretable is False


def test_evaluacion_exige_sus_corridas() -> None:
    records = _records([CLAIMS25["C13"]], {})
    del records["25a"]["drift"]
    with pytest.raises(ValueError, match="drift"):
        evaluate_phase25_claims([CLAIMS25["C13"]], records, SEEDS30)


# --- Fase II-B: efectos de regla y corridas ----------------------------------------------------


def test_efecto_de_regla() -> None:
    metric = "mean_expressible_nonattack_codons"
    seeds = PHASE25_RULE_EFFECT_SEEDS
    full = {s: _rec({metric: 3.0 + i}) for i, s in enumerate(seeds)}
    variant = {s: _rec({metric: 1.0}, active=0 if s == 42 else 4) for s in seeds}
    # La semilla 42 se excluye: quedan las diferencias 3..11, de mediana 7.0.
    assert phase25_rule_effect(full, variant, metric, seeds) == pytest.approx(7.0, abs=1e-9)
    extinct = {s: _rec({metric: 0.0}, active=0) for s in seeds}
    assert phase25_rule_effect(full, extinct, metric, seeds) is None


Job = tuple[SimulationConfig, int, tuple[str, ...]]


def _fake_record(job: Job) -> Phase25RunRecord:
    """Corrida falsa y determinista: el valor depende de la configuración y de la semilla."""
    config, _, metrics = job
    value = float(config.seed % 7)
    if config.reproduction_mode == "energy":
        value += 1.0
    if not config.enable_predation:
        value -= 0.5
    return _rec(dict.fromkeys(metrics, value))


@pytest.fixture
def fake_phase25(monkeypatch: pytest.MonkeyPatch) -> list[SimulationConfig]:
    calls: list[SimulationConfig] = []

    def execute(job: Job) -> Phase25RunRecord:
        calls.append(job[0])
        assert job[1] == 40
        return _fake_record(job)

    monkeypatch.setitem(PROFILES, "phase25", Profile(40, 0, 1, 1))
    monkeypatch.setattr(attribution, "_execute_phase25_run", execute)
    return calls


def test_atribucion_de_fase_ii_b_con_corridas_falsas(
    fake_phase25: list[SimulationConfig],
) -> None:
    report = run_phase25_attribution(seeds=(42, 43), rule_effect_seeds=(42,))
    assert report.profile == "phase25"
    assert report.rules == PHASE25_ALL_RULES
    assert [e.claim_id for e in report.evaluations] == [c.claim_id for c in PHASE25_CLAIMS]
    assert list(report.rule_effects) == [c.claim_id for c in PHASE25_CLAIMS]
    ablatable = [r.rule_id for r in PHASE25_ALL_RULES if r.ablation]
    for claim in PHASE25_CLAIMS:
        inactive = PHASE25_INACTIVE_RULES[claim.protocol]
        expected = [rid for rid in ablatable if rid not in inactive]
        assert list(report.rule_effects[claim.claim_id]) == expected
    assert "R25" not in report.rule_effects["C13"]
    assert "R31" in report.rule_effects["C18"]
    # full − sin la regla en la métrica simple: sin R12 la corrida falsa pierde 1.0.
    assert report.rule_effects["C13"]["R12"] == pytest.approx(1.0, abs=1e-9)
    assert report.rule_effects["C17"]["R37"] == pytest.approx(0.5, abs=1e-9)
    # Los efectos de regla usan sólo `rule_effect_seeds`.
    full_25a = PHASE25_PROTOCOL_CONFIGS["25a"]
    for rule_id in ("R33", "R36"):
        ablated = ablate(full_25a, [rule_id])
        seeds = {c.seed for c in fake_phase25 if c == dataclasses.replace(ablated, seed=c.seed)}
        assert seeds == {42}, rule_id
    c13 = report.evaluations[0]
    assert c13.values == {42: 1.0, 43: 2.0}
    assert c13.comparison_values == {42: 0.0, 43: 1.0}
    assert c13.evaluable is False  # 2 pares < 20


def test_cache_de_corridas_por_protocolo_variante_y_semilla(
    fake_phase25: list[SimulationConfig],
) -> None:
    """Escenario de la spec: `full` de 25a se ejecuta una sola vez por semilla."""
    claims = [CLAIMS25[c] for c in ("C13", "C14", "C16", "C17")]
    run_phase25_attribution(seeds=(42, 43), claims=claims, rule_effect_seeds=(42,))
    full = PHASE25_PROTOCOL_CONFIGS["25a"]
    for seed in (42, 43):
        assert fake_phase25.count(dataclasses.replace(full, seed=seed)) == 1
    assert len(fake_phase25) == len(set(fake_phase25))


def test_atribucion_con_configuraciones_propias(fake_phase25: list[SimulationConfig]) -> None:
    configs = phase25_protocol_configs(30, 10)
    run_phase25_attribution(
        seeds=(42,), claims=[CLAIMS25["C18"]], configs=configs, rule_effect_seeds=(42,)
    )
    assert all(c.resources_per_pattern == 30 for c in fake_phase25)
    assert dataclasses.replace(configs["25b"], seed=42) in fake_phase25


def test_atribucion_de_fase_ii_b_determinista_y_validaciones(
    fake_phase25: list[SimulationConfig],
) -> None:
    claims = [CLAIMS25["C13"]]
    first = run_phase25_attribution(seeds=(42, 43), claims=claims, rule_effect_seeds=(42,))
    second = run_phase25_attribution(seeds=(42, 43), claims=claims, rule_effect_seeds=(42,))
    assert first == second
    with pytest.raises(ValueError, match="repetidas"):
        run_phase25_attribution(seeds=(42, 42), claims=claims)
    with pytest.raises(ValueError, match="repetidas"):
        run_phase25_attribution(seeds=(42,), claims=claims, rule_effect_seeds=(42, 42))
    with pytest.raises(ValueError, match="C6"):
        run_phase25_attribution(seeds=(42,), claims=[EXP002_CLAIMS[1]])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="25z"):
        bogus = dataclasses.replace(CLAIMS25["C13"], protocol="25z")
        run_phase25_attribution(seeds=(42,), claims=[bogus])


def test_atribucion_de_fase_ii_b_sin_semillas_de_efectos(
    fake_phase25: list[SimulationConfig],
) -> None:
    report = run_phase25_attribution(seeds=(42,), claims=[CLAIMS25["C13"]], rule_effect_seeds=())
    assert all(v is None for v in report.rule_effects["C13"].values())


def _has_phase25_telemetry() -> bool:
    from ide.experiments import metrics

    return hasattr(metrics, "GeneticTickMetrics") and hasattr(metrics, "EcologyTickMetrics")


@pytest.mark.skipif(
    not _has_phase25_telemetry(),
    reason="GeneticTickMetrics y EcologyTickMetrics llegan con el bloque 21",
)
def test_atribucion_de_fase_ii_b_con_un_perfil_corto(monkeypatch: pytest.MonkeyPatch) -> None:
    """Escenario de la spec: perfil corto, dos semillas y una semilla de efectos de regla."""
    monkeypatch.setitem(PROFILES, "phase25", Profile(40, 0, 1, 1))
    small = {
        key: dataclasses.replace(config, **SMALL_GRID)
        for key, config in PHASE25_PROTOCOL_CONFIGS.items()
    }
    report = run_phase25_attribution(seeds=(42, 43), configs=small, rule_effect_seeds=(42,))
    assert report.profile == "phase25"
    assert report.rules == PHASE25_ALL_RULES
    assert [e.claim_id for e in report.evaluations] == [c.claim_id for c in PHASE25_CLAIMS]
    assert all(not math.isnan(e.p_value) for e in report.evaluations)


# --- Reportes de C1-C8 sin cambios -------------------------------------------------------------

# Hashes del `repr` de los reportes de 001-D y de la Fase II con un perfil corto, calculados
# antes del bloque 22 (commit abc71cd): la atribución de la Fase II-B no los altera.
GOLDEN_001D = "f304e8a40efa9fab386cdeba1fab03c98001e5a905f44eeae491282e8a850f23"
GOLDEN_PHASE2 = "d7a59fec5888617c59d2a0200b8fdaaaa17ea72c4d1bc176a409a0ecd20f8e49"


def test_reportes_de_c1_a_c8_sin_cambios(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(PROFILES, "tiny", Profile(30, 10, 20, 10))
    monkeypatch.setattr(attribution, "ATTRIBUTION_PROFILE", "tiny")
    monkeypatch.setattr(attribution, "PHASE2_ATTRIBUTION_PROFILE", "tiny")
    report_001d = run_protocol_001d_attribution(SMALL, [3, 4])
    small = {k: dataclasses.replace(c, **SMALL_GRID) for k, c in PHASE2_PROTOCOL_CONFIGS.items()}
    report_phase2 = run_phase2_attribution(seeds=(3, 4), configs=small)
    assert hashlib.sha256(repr(report_001d).encode()).hexdigest() == GOLDEN_001D
    assert hashlib.sha256(repr(report_phase2).encode()).hexdigest() == GOLDEN_PHASE2
    assert all(e.status is not ClaimStatus.OBSERVED for e in report_001d.evaluations)
    assert all(e.status is not ClaimStatus.OBSERVED for e in report_phase2.evaluations)


# --- Fase II-B: correcciones de la revisión de código del bloque 22 -----------------------------


def test_empate_con_tolerancia_en_la_diferencia_de_diferencias() -> None:
    """(0.3 − 0.1) − (0.5 − 0.3) es -2.8e-17 en flotante: empate descartado (precisión 112)."""
    seeds = SEEDS30[:21]
    values = {
        ("C19", "full"): [0.3] * 20 + [1.0],
        ("C19", "drift"): [0.1] * 20 + [0.0],
        ("C19", "stable"): [0.5] * 20 + [0.0],
        ("C19", "stable_drift"): [0.3] * 20 + [0.0],
    }
    evaluation = _evaluate([CLAIMS25["C19"]], values, seeds=seeds)["C19"]
    assert evaluation.p_value == pytest.approx(0.5, abs=1e-12)  # n = 1, una positiva
    assert attribution.phase25_sign_test([-2.7755575615628914e-17, 1.0]) == 0.5


def test_mediana_que_alcanza_el_umbral_con_tolerancia() -> None:
    """Una mediana de 0.9999999999999998 alcanza δ_min = 1.0 en C17 (precisión 112)."""
    values = {
        ("C17", "full"): [0.0] * 30,
        ("C17", "drift"): [0.0] * 30,
        ("C17", "no_predation"): [1.3] * 30,
        ("C17", "no_predation_drift"): [2.3] * 30,
    }
    evaluation = _evaluate([CLAIMS25["C17"]], values)["C17"]
    assert evaluation.median_difference == 0.9999999999999998
    assert evaluation.status is ClaimStatus.OBSERVED
    below = phase25_status(
        by_construction=False,
        evaluable=True,
        p_value=0.001,
        p_adjusted=0.001,
        median_difference=1.0 - 2e-9,
        threshold=1.0,
    )
    assert below is ClaimStatus.NOT_OBSERVED


def test_umbral_relativo_en_la_diferencia_de_diferencias() -> None:
    """En una diferencia de diferencias, M es la mediana de `comparison_values` (precisión 119)."""
    relative = dataclasses.replace(CLAIMS25["C17"], delta_min=0.0, delta_relative=1.0)
    values = {
        ("C17", "full"): [10.0] * 30,
        ("C17", "drift"): [5.0] * 30,
        ("C17", "no_predation"): [100.0] * 30,
        ("C17", "no_predation_drift"): [98.0] * 30,
    }
    # d = 5 − 2 = 3; M = 2 (no 100): el umbral es 2 y la afirmación alcanza el efecto.
    evaluation = _evaluate([relative], values)["C17"]
    assert evaluation.median_difference == pytest.approx(3.0, abs=1e-9)
    assert evaluation.status is ClaimStatus.OBSERVED


def test_actividad_del_ultimo_tick_con_historial_vacio() -> None:
    assert phase25_metric_value("new_activity_per_birth", [], [], 0) == 0.0
    assert phase25_metric_value("policy_divergence", [], [], 0) == 0.0


def test_exactitud_tras_los_cambios_con_ventanas_por_indice() -> None:
    """Con un historial que empieza en el tick 1, las ventanas se ubican por el tick."""
    ecology = _ecology_with_shifts(2500)[1:]
    assert post_shift_accuracy(ecology, 1000) == pytest.approx(0.6, abs=1e-9)
    assert post_shift_accuracy([], 1000) == 0.0


def test_e4_depende_de_la_abundancia_corrida(
    fake_phase25: list[SimulationConfig], monkeypatch: pytest.MonkeyPatch
) -> None:
    """E4 sólo es interpretable con la abundancia elegida por la compuerta (precisión 113)."""
    monkeypatch.setattr(attribution, "PHASE25_NULL_CONTENT_VIABLE_SEEDS", {"25a": 10, "25b": 8})
    claims = [CLAIMS25["C13"], CLAIMS25["C18"]]
    chosen = run_phase25_attribution(seeds=(42,), claims=claims, rule_effect_seeds=())
    assert [e.e4_interpretable for e in chosen.evaluations] == [True, False]
    other = run_phase25_attribution(
        seeds=(42,), claims=claims, configs=phase25_protocol_configs(30, 10), rule_effect_seeds=()
    )
    assert [e.e4_interpretable for e in other.evaluations] == [False, False]


@pytest.mark.parametrize(
    ("protocol", "overrides"),
    [
        ("25d", {"world_shift_period": 0}),
        ("25a", {"world_shift_period": 1000}),
        ("25c", {"comm_propensity_base": 1.0}),
        ("25a", {"comm_propensity_base": 0.0}),
        ("25b", {"enable_holonic_hierarchy": False}),
        ("25a", {"enable_holonic_hierarchy": True}),
        ("25a", {"enable_predation": False}),
        ("25d", {"enable_plasticity": False}),
        ("25a", {"enable_genetic_policy": False}),
    ],
)
def test_atribucion_valida_la_configuracion_de_cada_protocolo(
    fake_phase25: list[SimulationConfig], protocol: str, overrides: dict[str, Any]
) -> None:
    configs = dict(PHASE25_PROTOCOL_CONFIGS)
    configs[protocol] = dataclasses.replace(configs[protocol], **overrides)
    claim = next(c for c in PHASE25_CLAIMS if c.protocol == protocol)
    with pytest.raises(ValueError, match=f"{protocol} no respeta su protocolo"):
        run_phase25_attribution(seeds=(42,), claims=[claim], configs=configs)
    assert fake_phase25 == []


def test_cada_corrida_calcula_solo_las_metricas_de_sus_protocolos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`stable` de 25d es `full` de 25a: una corrida, métricas de los dos (precisión 121)."""
    jobs: list[Job] = []

    def execute(job: Job) -> Phase25RunRecord:
        jobs.append(job)
        return _fake_record(job)

    monkeypatch.setitem(PROFILES, "phase25", Profile(40, 0, 1, 1))
    monkeypatch.setattr(attribution, "_execute_phase25_run", execute)
    claims = [CLAIMS25["C13"], CLAIMS25["C18"], CLAIMS25["C19"]]
    run_phase25_attribution(seeds=(42,), claims=claims, rule_effect_seeds=())
    metrics = {job[0]: job[2] for job in jobs}
    assert len(metrics) == len(jobs)  # sin corridas repetidas
    full_a = dataclasses.replace(PHASE25_PROTOCOL_CONFIGS["25a"], seed=42)
    full_b = dataclasses.replace(PHASE25_PROTOCOL_CONFIGS["25b"], seed=42)
    full_d = dataclasses.replace(PHASE25_PROTOCOL_CONFIGS["25d"], seed=42)
    assert metrics[full_a] == ("mean_conditional_codons", "mean_learning_codons")
    assert metrics[full_b] == ("share_rate",)
    assert metrics[full_d] == ("mean_learning_codons",)
