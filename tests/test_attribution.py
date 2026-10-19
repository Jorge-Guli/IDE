"""Tests de `emergence-attribution`: reglas, pre-registro, ablación y clasificación."""

import dataclasses
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

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
    PHASE2_SEEDS,
    ClaimEvaluation,
    ClaimStatus,
    EmergenceClaim,
    ablate,
    classify,
    disables_communication,
    measure_claim,
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
    with pytest.raises(ValueError, match="R24"):
        ablate(EVO, ["R24"])


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
    base = SimulationConfig()
    assert {
        "002a": dataclasses.replace(base, enable_evolution=True),
        "002b": dataclasses.replace(base, enable_evolution=True, enable_cultural_inheritance=True),
        "003a": dataclasses.replace(base, **holonic),
        "003b": dataclasses.replace(base, **holonic, enable_downward_causation=False),
    } == PHASE2_PROTOCOL_CONFIGS
    c003a = PHASE2_PROTOCOL_CONFIGS["003a"]
    assert c003a.num_composite_patterns == 3
    assert c003a.composite_order == 4 > c003a.memory_capacity


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
