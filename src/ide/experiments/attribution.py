"""Atribución de emergencia (Decisión 13): emergente vs. programado.

`DESIGN_RULES`, `EXP001_CLAIMS` y `ATTRIBUTION_PROFILE` son un **pre-registro**: se versionan
antes de mirar resultados, y cambiarlos después exige un commit que lo justifique.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from ide.config import SimulationConfig
from ide.experiments.exp001_runner import (
    PROFILES,
    Profile,
    map_in_order,
    run_protocol_001b_falsification,
    run_protocol_001c_resilience,
    sign_test_p_value,
    validate_seeds,
)
from ide.simulation.engine import SimulationEngine


@dataclass(frozen=True)
class DesignRule:
    rule_id: str  # "R8"
    name: str
    purpose: str
    ablation: tuple[tuple[str, Any], ...]  # overrides de SimulationConfig; () si es nuclear


@dataclass(frozen=True)
class EmergenceClaim:
    claim_id: str  # "C1"
    description: str
    protocol: str  # "001a" | "001b" | "001c"
    metric: str
    higher_is_better: bool
    purpose_rules: tuple[str, ...]  # R_c


class ClaimStatus(Enum):
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_OBSERVED = "NOT_OBSERVED"
    PROGRAMMED = "PROGRAMMED"
    ACTIVITY_ARTIFACT = "ACTIVITY_ARTIFACT"
    EMERGENT_PENDING_ROBUSTNESS = "EMERGENT_PENDING_ROBUSTNESS"
    SCHEDULING_ARTIFACT = "SCHEDULING_ARTIFACT"
    EMERGENT = "EMERGENT"


@dataclass(frozen=True)
class ClaimEvaluation:
    claim_id: str
    status: ClaimStatus
    by_construction: bool  # E3 tautológico (Decisión 13)
    seeds: tuple[int, ...]
    values: dict[str, tuple[float, ...]]  # variante -> valor por semilla
    p_vs_isolated: float  # E2
    p_purpose_ablated_vs_isolated: float | None  # E3 (None si R_c es vacío o by_construction)
    p_vs_null_content: float  # E4
    e5_evaluated: bool  # False mientras el esquema asíncrono no exista
    rule_effects: dict[str, float]  # regla -> media de d(full, sin esa regla)


@dataclass(frozen=True)
class AttributionReport:
    profile: str
    rules: tuple[DesignRule, ...]
    evaluations: tuple[ClaimEvaluation, ...]


# --- Pre-registro ------------------------------------------------------------------------------

ATTRIBUTION_PROFILE = "quick"

DESIGN_RULES: tuple[DesignRule, ...] = (
    DesignRule("R1", "Aprendizaje por experiencia directa", "Aprender del entorno", ()),
    DesignRule(
        "R2",
        "Memoria acotada con reemplazo por utilidad",
        "Restricción experimental C_max < N",
        (),
    ),
    DesignRule("R3", "Olvido pasivo", "Eliminar lo no revalidado", (("passive_conf_decay", 0.0),)),
    DesignRule(
        "R4", "Descuento por testimonio γ", "Atenuar rumores", (("gamma_social_discount", 1.0),)
    ),
    DesignRule("R5", "Refuerzo por consenso", "Consolidar acuerdos", (("eta_consensus", 0.0),)),
    DesignRule(
        "R6",
        "Anti-cámara de eco",
        "Impedir certeza sin evidencia",
        (("anti_echo_enabled", False),),
    ),
    DesignRule(
        "R7", "Duda ante contradicción", "Filtrar testimonios falsos", (("eta_doubt", 0.0),)
    ),
    DesignRule(
        "R8",
        "Consulta en vivo",
        "Acceder a memoria ajena (meta-agente)",
        (("max_queries_per_tick", 0),),
    ),
    DesignRule(
        "R9", "Difusión espontánea", "Transmitir conocimiento", (("max_broadcast_per_tick", 0),)
    ),
    DesignRule("R10", "Exploración ε", "Descubrir lo desconocido", (("epsilon_explore", 0.0),)),
    DesignRule(
        "R11",
        "Navegación hacia benéficos conocidos",
        "Buscar alimento",
        (("enable_navigation", False),),
    ),
)

EXP001_CLAIMS: tuple[EmergenceClaim, ...] = (
    EmergenceClaim(
        "C1",
        "Acceso a conocimiento no poseído",
        "001a",
        "accessible_coverage_mean",
        True,
        ("R8", "R9"),
    ),
    EmergenceClaim(
        "C2",
        "Superávit de decisión colectiva",
        "001a",
        "cumulative_decision_accuracy",
        True,
        ("R8", "R9"),
    ),
    EmergenceClaim(
        "C3",
        "Inmunidad colectiva a la falsedad",
        "001b",
        "final_false_prevalence",
        False,
        ("R3", "R4", "R6", "R7"),
    ),
    EmergenceClaim(
        "C4",
        "Persistencia extra-individual",
        "001c",
        "final_social_persistence_prevalence",
        True,
        ("R8", "R9"),
    ),
)

_RULES_BY_ID = {rule.rule_id: rule for rule in DESIGN_RULES}


# --- Ablación ----------------------------------------------------------------------------------


def ablate(config: SimulationConfig, rule_ids: Sequence[str]) -> SimulationConfig:
    """Copia de `config` con la unión de los overrides que desactivan esas reglas."""
    overrides: dict[str, Any] = {}
    for rule_id in rule_ids:
        rule = _RULES_BY_ID.get(rule_id)
        if rule is None:
            raise ValueError(f"regla inexistente: {rule_id}")
        if not rule.ablation:
            raise ValueError(f"la regla {rule_id} es nuclear y no es ablacionable")
        overrides.update(rule.ablation)
    return replace(config, **overrides)


def disables_communication(config: SimulationConfig) -> bool:
    """La población no tiene ningún canal de emisión: la variante equivale a la aislada."""
    return not config.comm_enabled or (
        config.max_queries_per_tick == 0 and config.max_broadcast_per_tick == 0
    )


# --- Medición ----------------------------------------------------------------------------------

MIN_SEEDS = 5
_WITHOUT = "without:"


def _protocol_result(protocol: str, config: SimulationConfig, profile: Profile) -> Any:
    """Corre el protocolo de una afirmación con los parámetros del perfil."""
    if protocol == "001a":
        return SimulationEngine(config).run(profile.total_ticks)[-1]
    if protocol == "001b":
        return run_protocol_001b_falsification(config, profile.total_ticks, profile.injection_tick)
    if protocol == "001c":
        # Sólo la ablación de descubridores produce la métrica de C4; un nivel de ablación
        # poblacional sería una corrida independiente que se calcula y se descarta.
        return run_protocol_001c_resilience(
            config, profile.warmup_ticks, profile.post_ablation_ticks, ablation_levels=()
        )
    raise ValueError(f"protocolo desconocido: {protocol}")


def _metric(result: Any, claim: EmergenceClaim) -> float:
    return float(getattr(result, claim.metric))


def measure_claim(claim: EmergenceClaim, config: SimulationConfig, profile: str) -> float:
    """Valor de la métrica de la afirmación: el último tick (001a) o el campo del reporte."""
    return _metric(_protocol_result(claim.protocol, config, PROFILES[profile]), claim)


# --- Clasificación -----------------------------------------------------------------------------


def _differences(claim: EmergenceClaim, a: Sequence[float], b: Sequence[float]) -> list[float]:
    """`d(a, b)` por semilla, orientada para que positivo signifique "a es mejor"."""
    sign = 1.0 if claim.higher_is_better else -1.0
    return [sign * (x - y) for x, y in zip(a, b, strict=True)]


def _p(claim: EmergenceClaim, values: Mapping[str, Sequence[float]], a: str, b: str) -> float:
    return sign_test_p_value(_differences(claim, values[a], values[b]))


def classify(
    claim: EmergenceClaim,
    values: Mapping[str, Sequence[float]],
    by_construction: bool,
    alpha: float = 0.05,
) -> ClaimEvaluation:
    """Aplica E2 a E5 (prueba de signo unilateral) y la clasificación de la Decisión 13.

    `seeds` queda vacío: lo completa `run_protocol_001d_attribution`, que conoce las semillas.
    """
    required = ["full", "isolated", "null_content"]
    tests_e3 = bool(claim.purpose_rules) and not by_construction
    if tests_e3:
        required.append("purpose_ablated")
    missing = [name for name in required if name not in values]
    if missing:
        raise ValueError(f"{claim.claim_id}: faltan las variantes {missing}")
    seeds = len(values["full"])
    if seeds == 0:
        raise ValueError(f"{claim.claim_id}: no hay valores por semilla")
    uneven = sorted(name for name, seq in values.items() if len(seq) != seeds)
    if uneven:
        raise ValueError(f"{claim.claim_id}: {uneven} no tienen {seeds} valores como 'full'")
    p_iso = _p(claim, values, "full", "isolated")
    p_purpose = _p(claim, values, "purpose_ablated", "isolated") if tests_e3 else None
    p_null = _p(claim, values, "full", "null_content")
    async_needed = ["async:full", "async:isolated"] + (
        ["async:purpose_ablated"] if tests_e3 else []
    )
    e5_evaluated = all(name in values for name in async_needed)
    rule_effects = {
        name.removeprefix(_WITHOUT): sum(_differences(claim, values["full"], seq)) / len(seq)
        for name, seq in values.items()
        if name.startswith(_WITHOUT)
    }

    if seeds < MIN_SEEDS:
        status = ClaimStatus.INSUFFICIENT_EVIDENCE
    elif p_iso >= alpha:
        status = ClaimStatus.NOT_OBSERVED
    elif by_construction or (p_purpose is not None and p_purpose >= alpha):
        status = ClaimStatus.PROGRAMMED
    elif p_null >= alpha:
        status = ClaimStatus.ACTIVITY_ARTIFACT
    elif not e5_evaluated:
        status = ClaimStatus.EMERGENT_PENDING_ROBUSTNESS
    else:
        e5 = _p(claim, values, "async:full", "async:isolated") < alpha and (
            not tests_e3 or _p(claim, values, "async:purpose_ablated", "async:isolated") < alpha
        )
        status = ClaimStatus.EMERGENT if e5 else ClaimStatus.SCHEDULING_ARTIFACT

    return ClaimEvaluation(
        claim_id=claim.claim_id,
        status=status,
        by_construction=by_construction,
        seeds=(),
        values={name: tuple(seq) for name, seq in values.items()},
        p_vs_isolated=p_iso,
        p_purpose_ablated_vs_isolated=p_purpose,
        p_vs_null_content=p_null,
        e5_evaluated=e5_evaluated,
        rule_effects=rule_effects,
    )


# --- Protocolo 001-D ---------------------------------------------------------------------------

_Run = tuple[str, SimulationConfig, Profile]  # (protocolo, configuración, perfil)


def _execute_run(run: _Run) -> Any:
    return _protocol_result(*run)


def is_by_construction(claim: EmergenceClaim, config: SimulationConfig) -> bool:
    """Quitar `R_c` deja a la población sin canal de emisión: E3 sería una tautología."""
    return bool(claim.purpose_rules) and disables_communication(ablate(config, claim.purpose_rules))


def _variants(claim: EmergenceClaim, config: SimulationConfig) -> dict[str, SimulationConfig]:
    """Variantes de una semilla, en orden fijo."""
    variants = {"full": config, "isolated": replace(config, comm_enabled=False)}
    if claim.purpose_rules and not is_by_construction(claim, config):
        variants["purpose_ablated"] = ablate(config, claim.purpose_rules)
    variants["null_content"] = replace(config, comm_content_null=True)
    for rule in DESIGN_RULES:
        if rule.ablation:
            variants[_WITHOUT + rule.rule_id] = ablate(config, [rule.rule_id])
    return variants


def run_protocol_001d_attribution(
    config: SimulationConfig,
    seeds: Sequence[int],
    claims: Sequence[EmergenceClaim] = EXP001_CLAIMS,
    jobs: int = 1,
) -> AttributionReport:
    """Mide cada afirmación en todas sus variantes con `ATTRIBUTION_PROFILE` y la clasifica.

    Las corridas idénticas (mismo protocolo y configuración) se ejecutan una sola vez; las
    independientes se reparten en `jobs` procesos y se reúnen por clave, en orden fijo.
    """
    validate_seeds(seeds)
    # Construir las configuraciones valida cada semilla (`seed >= 0`) antes de planificar.
    seed_configs = [replace(config, seed=seed) for seed in seeds]
    profile = PROFILES[ATTRIBUTION_PROFILE]
    plans: list[tuple[EmergenceClaim, bool, dict[str, list[SimulationConfig]]]] = []
    runs: dict[_Run, None] = {}  # conjunto ordenado por inserción
    for claim in claims:
        by_construction = is_by_construction(claim, config)
        per_variant: dict[str, list[SimulationConfig]] = {}
        for seed_config in seed_configs:
            for name, variant in _variants(claim, seed_config).items():
                per_variant.setdefault(name, []).append(variant)
                runs[(claim.protocol, variant, profile)] = None
        plans.append((claim, by_construction, per_variant))

    keys = list(runs)
    results = dict(zip(keys, map_in_order(_execute_run, keys, jobs), strict=True))

    evaluations: list[ClaimEvaluation] = []
    for claim, by_construction, per_variant in plans:
        values: dict[str, Sequence[float]] = {
            name: [_metric(results[(claim.protocol, c, profile)], claim) for c in cfgs]
            for name, cfgs in per_variant.items()
        }
        evaluation = classify(claim, values, by_construction)
        evaluations.append(replace(evaluation, seeds=tuple(seeds)))
    return AttributionReport(ATTRIBUTION_PROFILE, DESIGN_RULES, tuple(evaluations))
