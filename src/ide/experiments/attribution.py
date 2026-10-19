"""Atribución de emergencia (Decisión 13): emergente vs. programado.

`DESIGN_RULES`, `EXP001_CLAIMS` y `ATTRIBUTION_PROFILE` son un **pre-registro**: se versionan
antes de mirar resultados, y cambiarlos después exige un commit que lo justifique. Lo mismo vale
para el pre-registro de la Fase II (design D29): `PHASE2_DESIGN_RULES`, `EXP002_CLAIMS`,
`EXP003_CLAIMS`, `PHASE2_CLAIM_CHANNELS`, `PHASE2_INACTIVE_RULES` y el perfil de corrida
(`PHASE2_ATTRIBUTION_PROFILE`, `PHASE2_SEEDS` y `PHASE2_PROTOCOL_CONFIGS`).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
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
    protocol: str  # "001a" | "001b" | "001c" | "002a" | "002b" | "003a" | "003b"
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
    values: dict[str, tuple[float | None, ...]]  # variante -> valor por semilla (None: sin medir)
    p_vs_isolated: float  # E2
    p_purpose_ablated_vs_isolated: float | None  # E3 (None si R_c es vacío o by_construction)
    p_vs_null_content: float  # E4
    e5_evaluated: bool  # False mientras el esquema asíncrono no exista
    rule_effects: dict[str, float | None]  # regla -> media de d(full, sin ella); None sin medición
    # variante -> semillas en que ella o `full` no tienen valor (sólo C8 puede no tenerlo)
    unmeasured_seeds: dict[str, tuple[int, ...]] = field(default_factory=dict[str, tuple[int, ...]])
    # variante -> (población final, generación máxima) por semilla; Enmienda 1 de D29, sólo Fase II
    demography: dict[str, tuple[tuple[int, int], ...]] = field(
        default_factory=dict[str, tuple[tuple[int, int], ...]]
    )


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


# --- Pre-registro de la Fase II (design D29) ---------------------------------------------------

PHASE2_DESIGN_RULES: tuple[DesignRule, ...] = (
    DesignRule(
        "R12",
        "Reproducción diferencial por energía",
        "Que los agentes con más energía dejen más descendencia (selección)",
        (("reproduction_mode", "neutral"),),
    ),
    DesignRule(
        "R13",
        "Mutación genética acotada",
        "Variación heredable sobre la que actúa la selección",
        (("mutation_rate", 0.0), ("discrete_mutation_prob", 0.0)),
    ),
    DesignRule(
        "R14",
        "Herencia cultural vertical",
        "Transmitir conocimiento de padres a hijos",
        (("enable_cultural_inheritance", False), ("inheritance_discount", 0.0)),
    ),
    DesignRule(
        "R15",
        "Fusión holónica (BOND)",
        "Asociar nodos complementarios en unidades de nivel superior",
        (("enable_holonic_hierarchy", False),),
    ),
    DesignRule(
        "R16",
        "Fisión holónica (SPLIT)",
        "Disolver holones sin superávit",
        (("enable_holon_splitting", False),),
    ),
    DesignRule(
        "R17",
        "Reproducción de holón completo",
        "Transmitir la estructura simbiótica a la descendencia",
        (("enable_holon_reproduction", False),),
    ),
    DesignRule(
        "R18",
        "Causalidad descendente intra-holón",
        "Reducir la redundancia de memoria entre hojas de un holón (ortogonalización)",
        (("enable_downward_causation", False), ("redundancy_penalty", 1.0)),
    ),
    DesignRule(
        "R19",
        "Estigmergia",
        "Externalizar conocimiento en el entorno",
        (("enable_stigmergy", False), ("stigmergy_deposit_rate", 0.0)),
    ),
    DesignRule(
        "R20",
        "Física metabólica",
        "Vida y muerte por energía: costo basal fijo, de movimiento y de emisión, muerte con "
        "E <= 0 y capacidad de carga. Sin ella no hay selección",
        (),
    ),
    DesignRule(
        "R21",
        "Costo cuadrático de cerebro y sentidos",
        "Encarecer la hipertrofia individual (C_max², radios²). Sesga a favor de cooperar; se "
        "declara como sesgo",
        (("memory_capacity_cost", 0.0), ("sensory_radius_cost", 0.0)),
    ),
    DesignRule(
        "R22",
        "Vista compartida del holón",
        "Dar a cada hoja acceso efímero al conocimiento de las hojas cercanas de su holón",
        (("enable_holon_view", False),),
    ),
    DesignRule(
        "R23",
        "Coordinación y reparto energético del holón",
        "Que pertenecer a un holón tenga un costo y un beneficio energético compartido",
        (("holon_coord_cost", 0.0), ("holon_energy_sharing", False)),
    ),
)

ALL_DESIGN_RULES: tuple[DesignRule, ...] = DESIGN_RULES + PHASE2_DESIGN_RULES

EXP002_CLAIMS: tuple[EmergenceClaim, ...] = (
    EmergenceClaim(
        "C5",
        "Aceleración cultural intergeneracional",
        "002b",
        "cultural_accuracy",
        True,
        ("R14",),
    ),
    EmergenceClaim(
        "C6",
        "Adaptación evolutiva por selección",
        "002a",
        "evolved_accuracy",
        True,
        ("R12", "R13"),
    ),
)

EXP003_CLAIMS: tuple[EmergenceClaim, ...] = (
    EmergenceClaim(
        "C7",
        "Superávit cooperativo sobre recursos compuestos",
        "003a",
        "holonic_composite_completions",
        True,
        ("R15", "R17"),
    ),
    EmergenceClaim(
        "C8",
        "Cobertura colectiva adquirida sin causalidad descendente",
        "003b",
        "mean_acquired_coverage",
        True,
        ("R22",),
    ),
)

# Canal: las reglas sin las cuales el mecanismo que se pone a prueba no existe.
PHASE2_CLAIM_CHANNELS: dict[str, tuple[str, ...]] = {
    "C5": ("R14",),
    "C6": ("R12",),
    "C7": ("R15",),
    "C8": ("R22",),
}

# Reglas sin efecto en la configuración del protocolo: no reciben variante ni `rule_effects`.
PHASE2_INACTIVE_RULES: dict[str, tuple[str, ...]] = {
    "002a": ("R14", "R15", "R16", "R17", "R18", "R19", "R22", "R23"),
    "002b": ("R15", "R16", "R17", "R18", "R19", "R22", "R23"),
    "003a": ("R14", "R18", "R19"),
    "003b": ("R14", "R18", "R19"),
}

PHASE2_ATTRIBUTION_PROFILE = "phase2"
PHASE2_SEEDS: tuple[int, ...] = tuple(range(42, 52))

_HOLONIC_PROTOCOL = SimulationConfig(
    enable_evolution=True,
    enable_holonic_hierarchy=True,
    enable_holon_reproduction=True,
    num_composite_patterns=3,
    composite_order=4,  # > memory_capacity = 3
)

# Configuraciones previas a la Enmienda 1 de D29: se corren como referencia.
PHASE2_PROTOCOL_CONFIGS_ORIGINAL: dict[str, SimulationConfig] = {
    "002a": SimulationConfig(enable_evolution=True),
    "002b": SimulationConfig(enable_evolution=True, enable_cultural_inheritance=True),
    "003a": _HOLONIC_PROTOCOL,
    # R18 apagada es parte de la condición base de C8.
    "003b": replace(_HOLONIC_PROTOCOL, enable_downward_causation=False),
}

PHASE2_PROTOCOL_CONFIGS: dict[str, SimulationConfig] = dict(PHASE2_PROTOCOL_CONFIGS_ORIGINAL)

_ALL_RULES_BY_ID = {rule.rule_id: rule for rule in ALL_DESIGN_RULES}


# --- Ablación ----------------------------------------------------------------------------------


def ablate(config: SimulationConfig, rule_ids: Sequence[str]) -> SimulationConfig:
    """Copia de `config` con la unión de los overrides que desactivan esas reglas."""
    overrides: dict[str, Any] = {}
    for rule_id in rule_ids:
        rule = _ALL_RULES_BY_ID.get(rule_id)
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
NULL_CONTENT = "null_content"  # nombre de la variante de E4

# Métrica de cada afirmación de Fase II como campo del resumen de la condición base (D29).
_PHASE2_METRIC_FIELDS = {
    "evolved_accuracy": "final_accuracy",
    "cultural_accuracy": "final_accuracy",
    "holonic_composite_completions": "composite_completions",
    "mean_acquired_coverage": "mean_acquired_coverage",
}


def is_phase2_claim(claim: EmergenceClaim) -> bool:
    return claim.protocol in PHASE2_PROTOCOL_CONFIGS


# Corrida que mide cada protocolo. 003-A y 003-B (y 002-A y 002-B) corren la misma condición
# base, así que una configuración repetida entre ellos se ejecuta una sola vez.
_RUN_KIND = {
    "001a": "001a",
    "001b": "001b",
    "001c": "001c",
    "002a": "evolution",
    "002b": "evolution",
    "003a": "holonic",
    "003b": "holonic",
}


def _run_kind(protocol: str) -> str:
    kind = _RUN_KIND.get(protocol)
    if kind is None:
        raise ValueError(f"protocolo desconocido: {protocol}")
    return kind


def require_r18_off(config: SimulationConfig) -> None:
    """C8 se define con R18 apagada (D29): 003-B no admite causalidad descendente."""
    if config.enable_downward_causation:
        raise ValueError("003-B exige R18 apagada (enable_downward_causation=False), design D29")


def _check_protocol(protocol: str, config: SimulationConfig) -> None:
    if protocol == "003b":
        require_r18_off(config)


def _protocol_result(protocol: str, config: SimulationConfig, profile: Profile) -> Any:
    """Corre el protocolo de una afirmación con los parámetros del perfil."""
    kind = _run_kind(protocol)
    _check_protocol(protocol, config)
    return _run(kind, config, profile)


def _run(kind: str, config: SimulationConfig, profile: Profile) -> Any:
    """En la Fase II corre sólo la condición base del protocolo: las comparaciones las hacen las
    variantes (D29, "una sola condición por variante").
    """
    if kind == "001a":
        return SimulationEngine(config).run(profile.total_ticks)[-1]
    if kind == "001b":
        return run_protocol_001b_falsification(config, profile.total_ticks, profile.injection_tick)
    if kind == "001c":
        # Sólo la ablación de descubridores produce la métrica de C4; un nivel de ablación
        # poblacional sería una corrida independiente que se calcula y se descarta.
        return run_protocol_001c_resilience(
            config, profile.warmup_ticks, profile.post_ablation_ticks, ablation_levels=()
        )
    # Importación diferida: los runners de Fase II dependen de este módulo (`ablate`).
    if kind == "evolution":
        from ide.experiments.exp002_runner import run_evolution_condition

        return run_evolution_condition(config, profile.total_ticks)
    if kind == "holonic":
        from ide.experiments.exp003_runner import run_holonic_condition

        return run_holonic_condition(config, profile.total_ticks)
    raise ValueError(f"tipo de corrida desconocido: {kind}")


def _metric(result: Any, claim: EmergenceClaim) -> float | None:
    name = _PHASE2_METRIC_FIELDS[claim.metric] if is_phase2_claim(claim) else claim.metric
    value = getattr(result, name)
    return None if value is None else float(value)


def measure_claim(claim: EmergenceClaim, config: SimulationConfig, profile: str) -> float | None:
    """Valor de la métrica de la afirmación: el último tick (001a) o el campo del reporte.

    Sólo C8 puede devolver `None`: una corrida sin holones elegibles no tiene medición.
    """
    return _metric(_protocol_result(claim.protocol, config, PROFILES[profile]), claim)


# --- Clasificación -----------------------------------------------------------------------------


def _measured(a: Sequence[float | None], b: Sequence[float | None]) -> list[bool]:
    return [x is not None and y is not None for x, y in zip(a, b, strict=True)]


def _differences(
    claim: EmergenceClaim, a: Sequence[float | None], b: Sequence[float | None]
) -> list[float]:
    """`d(a, b)` por semilla, orientada para que positivo signifique "a es mejor".

    Una semilla sin medición en alguna de las dos variantes cuenta como empate (`0.0`), que la
    prueba de signo descarta.
    """
    sign = 1.0 if claim.higher_is_better else -1.0
    return [0.0 if x is None or y is None else sign * (x - y) for x, y in zip(a, b, strict=True)]


def _p(
    claim: EmergenceClaim, values: Mapping[str, Sequence[float | None]], a: str, b: str
) -> float:
    return sign_test_p_value(_differences(claim, values[a], values[b]))


def _rule_effect(
    claim: EmergenceClaim, full: Sequence[float | None], without: Sequence[float | None]
) -> float | None:
    """Media de `d(full, sin la regla)` sobre las semillas medidas; `None` si no hay ninguna."""
    measured = _measured(full, without)
    if not any(measured):
        return None
    differences = _differences(claim, full, without)
    return sum(d for d, ok in zip(differences, measured, strict=True) if ok) / sum(measured)


def classify(
    claim: EmergenceClaim,
    values: Mapping[str, Sequence[float | None]],
    by_construction: bool,
    alpha: float = 0.05,
    seeds: Sequence[int] | None = None,
) -> ClaimEvaluation:
    """Aplica E2 a E5 (prueba de signo unilateral) y la clasificación de la Decisión 13.

    Un valor `None` es una semilla sin medición (D29): cuenta como empate en cada comparación y
    se lista en `unmeasured_seeds` (por su semilla, o por su posición si no se pasan `seeds`).
    La evidencia es insuficiente si menos de `MIN_SEEDS` semillas tienen medición en E2.
    """
    required = ["full", "isolated", NULL_CONTENT]
    tests_e3 = bool(claim.purpose_rules) and not by_construction
    if tests_e3:
        required.append("purpose_ablated")
    missing = [name for name in required if name not in values]
    if missing:
        raise ValueError(f"{claim.claim_id}: faltan las variantes {missing}")
    count = len(values["full"])
    if count == 0:
        raise ValueError(f"{claim.claim_id}: no hay valores por semilla")
    uneven = sorted(name for name, seq in values.items() if len(seq) != count)
    if uneven:
        raise ValueError(f"{claim.claim_id}: {uneven} no tienen {count} valores como 'full'")
    if seeds is not None and len(seeds) != count:
        raise ValueError(f"{claim.claim_id}: {len(seeds)} semillas para {count} valores")
    labels = list(seeds) if seeds is not None else list(range(count))
    full = values["full"]
    unmeasured = {
        name: tuple(s for s, ok in zip(labels, _measured(full, seq), strict=True) if not ok)
        for name, seq in values.items()
        if name != "full"
    }
    p_iso = _p(claim, values, "full", "isolated")
    p_purpose = _p(claim, values, "purpose_ablated", "isolated") if tests_e3 else None
    p_null = _p(claim, values, "full", NULL_CONTENT)
    async_needed = ["async:full", "async:isolated"] + (
        ["async:purpose_ablated"] if tests_e3 else []
    )
    e5_evaluated = all(name in values for name in async_needed)
    rule_effects = {
        name.removeprefix(_WITHOUT): _rule_effect(claim, full, seq)
        for name, seq in values.items()
        if name.startswith(_WITHOUT)
    }

    if sum(_measured(full, values["isolated"])) < MIN_SEEDS:
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
        seeds=tuple(seeds) if seeds is not None else (),
        values={name: tuple(seq) for name, seq in values.items()},
        p_vs_isolated=p_iso,
        p_purpose_ablated_vs_isolated=p_purpose,
        p_vs_null_content=p_null,
        e5_evaluated=e5_evaluated,
        rule_effects=rule_effects,
        unmeasured_seeds={name: s for name, s in unmeasured.items() if s},
    )


# --- Protocolos de atribución (001-D y Fase II) ------------------------------------------------

_Run = tuple[str, SimulationConfig, Profile]  # (tipo de corrida, configuración, perfil)


def _execute_run(run: _Run) -> Any:
    return _run(*run)


def is_by_construction(claim: EmergenceClaim, config: SimulationConfig) -> bool:
    """E3 sería una tautología: quitar `R_c` elimina lo que se pone a prueba.

    En Fase I, quitar `R_c` deja a la población sin canal de emisión. En Fase II (criterio
    ampliado, D29), el canal de la afirmación no es vacío y está contenido en `R_c`.
    """
    if is_phase2_claim(claim):
        channel = PHASE2_CLAIM_CHANNELS.get(claim.claim_id, ())
        return bool(channel) and set(channel) <= set(claim.purpose_rules)
    return bool(claim.purpose_rules) and disables_communication(ablate(config, claim.purpose_rules))


def null_content_variant(config: SimulationConfig) -> SimulationConfig:
    """Control nulo (E4): mismas reglas, contenido de cada creencia entregada reemplazado."""
    return replace(config, comm_content_null=True)


def _variants(claim: EmergenceClaim, config: SimulationConfig) -> dict[str, SimulationConfig]:
    """Variantes de una semilla, en orden fijo.

    En Fase II la aislada es la ablación del canal y no reciben variante las reglas inactivas
    del protocolo (D29); en Fase I las variantes no cambian.
    """
    phase2 = is_phase2_claim(claim)
    if phase2:
        isolated = ablate(config, PHASE2_CLAIM_CHANNELS[claim.claim_id])
        inactive = set(PHASE2_INACTIVE_RULES[claim.protocol])
        rules = [r for r in ALL_DESIGN_RULES if r.rule_id not in inactive]
    else:
        isolated = replace(config, comm_enabled=False)
        rules = list(DESIGN_RULES)
    variants = {"full": config, "isolated": isolated}
    if claim.purpose_rules and not is_by_construction(claim, config):
        variants["purpose_ablated"] = ablate(config, claim.purpose_rules)
    variants[NULL_CONTENT] = null_content_variant(config)
    for rule in rules:
        if rule.ablation:
            variants[_WITHOUT + rule.rule_id] = ablate(config, [rule.rule_id])
    return variants


def _attribute(
    claims: Sequence[EmergenceClaim],
    seeds: Sequence[int],
    base: Callable[[EmergenceClaim], SimulationConfig],
    profile_name: str,
    jobs: int,
) -> list[ClaimEvaluation]:
    """Mide cada afirmación en todas sus variantes y la clasifica.

    Las corridas idénticas (mismo protocolo y configuración) se ejecutan una sola vez; las
    independientes se reparten en `jobs` procesos y se reúnen por clave, en orden fijo.
    """
    # Los llamadores ya validaron la lista; la regla `seed >= 0` de `SimulationConfig` se
    # comprueba aquí antes de planificar, también sin afirmaciones.
    for seed in seeds:
        SimulationConfig(seed=seed)
    profile = PROFILES[profile_name]
    plans: list[tuple[EmergenceClaim, str, bool, dict[str, list[SimulationConfig]]]] = []
    runs: dict[_Run, None] = {}  # conjunto ordenado por inserción
    for claim in claims:
        config = base(claim)
        kind = _run_kind(claim.protocol)
        _check_protocol(claim.protocol, config)
        seed_configs = [replace(config, seed=seed) for seed in seeds]
        by_construction = is_by_construction(claim, config)
        per_variant: dict[str, list[SimulationConfig]] = {}
        for seed_config in seed_configs:
            for name, variant in _variants(claim, seed_config).items():
                per_variant.setdefault(name, []).append(variant)
                runs[(kind, variant, profile)] = None
        plans.append((claim, kind, by_construction, per_variant))

    keys = list(runs)
    results = dict(zip(keys, map_in_order(_execute_run, keys, jobs), strict=True))

    evaluations: list[ClaimEvaluation] = []
    for claim, kind, by_construction, per_variant in plans:
        values: dict[str, Sequence[float | None]] = {}
        demography: dict[str, tuple[tuple[int, int], ...]] = {}
        for name, cfgs in per_variant.items():
            outcomes = [results[(kind, c, profile)] for c in cfgs]
            values[name] = [_metric(outcome, claim) for outcome in outcomes]
            if is_phase2_claim(claim):
                demography[name] = tuple((o.final_agents, o.max_generation) for o in outcomes)
        evaluation = classify(claim, values, by_construction, seeds=seeds)
        if demography:
            evaluation = replace(evaluation, demography=demography)
        evaluations.append(evaluation)
    return evaluations


def run_protocol_001d_attribution(
    config: SimulationConfig,
    seeds: Sequence[int],
    claims: Sequence[EmergenceClaim] = EXP001_CLAIMS,
    jobs: int = 1,
) -> AttributionReport:
    """Mide cada afirmación de Fase I en todas sus variantes con `ATTRIBUTION_PROFILE`."""
    validate_seeds(seeds)
    phase2 = [c.claim_id for c in claims if is_phase2_claim(c)]
    if phase2:
        raise ValueError(f"001-D sólo mide afirmaciones de Fase I; recibió {phase2}")
    evaluations = _attribute(claims, seeds, lambda _: config, ATTRIBUTION_PROFILE, jobs)
    return AttributionReport(ATTRIBUTION_PROFILE, DESIGN_RULES, tuple(evaluations))


def run_phase2_attribution(
    seeds: Sequence[int] = PHASE2_SEEDS,
    claims: Sequence[EmergenceClaim] = EXP002_CLAIMS + EXP003_CLAIMS,
    jobs: int = 1,
    configs: Mapping[str, SimulationConfig] | None = None,
) -> AttributionReport:
    """Pre-registro de Fase II: cada afirmación sobre la configuración congelada de su protocolo.

    Usa `configs[claim.protocol]` (por defecto `PHASE2_PROTOCOL_CONFIGS`; la referencia de la
    Enmienda 1 pasa `PHASE2_PROTOCOL_CONFIGS_ORIGINAL`) como población completa y el perfil
    `PHASE2_ATTRIBUTION_PROFILE`; el reporte lleva `ALL_DESIGN_RULES` (D29).
    """
    validate_seeds(seeds)
    phase1 = [c.claim_id for c in claims if not is_phase2_claim(c)]
    if phase1:
        raise ValueError(f"la atribución de Fase II no mide afirmaciones de Fase I: {phase1}")
    unchanneled = [c.claim_id for c in claims if c.claim_id not in PHASE2_CLAIM_CHANNELS]
    if unchanneled:
        raise ValueError(f"afirmaciones de Fase II sin canal declarado: {unchanneled}")
    profile = PHASE2_ATTRIBUTION_PROFILE
    chosen = PHASE2_PROTOCOL_CONFIGS if configs is None else configs
    evaluations = _attribute(claims, seeds, lambda c: chosen[c.protocol], profile, jobs)
    return AttributionReport(profile, ALL_DESIGN_RULES, tuple(evaluations))
