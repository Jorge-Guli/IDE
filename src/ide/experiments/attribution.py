"""Atribución de emergencia (Decisión 13): emergente vs. programado.

`DESIGN_RULES`, `EXP001_CLAIMS` y `ATTRIBUTION_PROFILE` son un **pre-registro**: se versionan
antes de mirar resultados, y cambiarlos después exige un commit que lo justifique. Lo mismo vale
para el pre-registro de la Fase II (design D29): `PHASE2_DESIGN_RULES`, `EXP002_CLAIMS`,
`EXP003_CLAIMS`, `PHASE2_CLAIM_CHANNELS`, `PHASE2_INACTIVE_RULES` y el perfil de corrida
(`PHASE2_ATTRIBUTION_PROFILE`, `PHASE2_SEEDS` y `PHASE2_PROTOCOL_CONFIGS`), y para el de la
Fase II-B (design D56, aprobado en la tarea 0.5): `PHASE25_DESIGN_RULES`, `PHASE25_CLAIMS`,
`PHASE25_INACTIVE_RULES`, `PHASE25_PROTOCOL_CONFIGS` y su perfil (`PHASE25_ATTRIBUTION_PROFILE`,
`PHASE25_SEEDS`, `PHASE25_RULE_EFFECT_SEEDS` y `PHASE25_FINAL_WINDOW`).
"""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from statistics import median
from typing import Any, TypeVar

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
from ide.experiments.metrics import windowed_accuracy
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
    OBSERVED = "OBSERVED"  # sólo las afirmaciones de la Fase II-B (design D56, precisión 1)


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
    # Salida de respaldo de la Enmienda 1b (D29): en Fase II el control nulo se extingue y E4 se
    # informa sin interpretar
    e4_interpretable: bool = True


@dataclass(frozen=True)
class AttributionReport:
    profile: str
    rules: tuple[DesignRule, ...]
    evaluations: tuple[ClaimEvaluation, ...]


@dataclass(frozen=True)
class Phase25Claim:
    """Afirmación genuina (o funcional, C20) de la Fase II-B; la métrica siempre es creciente.

    Con `baseline_drift` y `comparison_drift` distintos de `None`, la diferencia de la semilla es
    una diferencia de diferencias (design D56, precisión 50).
    """

    claim_id: str  # "C13"
    statement: str
    protocol: str  # "25a" | "25b" | "25c" | "25d"
    metric: str  # campo de `GeneticTickMetrics` o `EcologyTickMetrics`, o `post_shift_accuracy`
    comparison: str  # "drift" | "no_predation" | "stable" | "no_learning"
    rule_ids: tuple[str, ...]  # R_C
    channel: tuple[str, ...]
    delta_min: float
    delta_relative: float = 0.0
    baseline_drift: str | None = None
    comparison_drift: str | None = None


@dataclass(frozen=True)
class Phase25ClaimEvaluation:
    """Evaluación de una afirmación de la Fase II-B (design D56, precisiones 45, 47 y 69).

    `values` y `comparison_values` van por semilla (todas, también las excluidas), de modo que la
    diferencia pareada es siempre `values[s] - comparison_values[s]`. `p_adjusted` es `None` en
    una afirmación programada por construcción (C20), que no entra en la corrección de Holm.
    """

    claim_id: str
    status: ClaimStatus
    p_value: float
    p_adjusted: float | None
    median_difference: float
    values: dict[int, float]
    comparison_values: dict[int, float]
    demography: dict[str, dict[int, dict[str, float]]]  # condición -> semilla -> campo
    e4_p_value: float
    e4_interpretable: bool
    excluded_seeds: tuple[int, ...]
    excluded_pairs: int
    evaluable: bool


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

# Salida de respaldo de la Enmienda 1b (D29): ni la grilla original ni la refinada dieron un
# valor viable. 20 tampoco cumple el criterio: las condiciones de los runners son viables, pero el
# control nulo se extingue. Por eso E4 de C5 a C8 se informa como no interpretable
# (`ClaimEvaluation.e4_interpretable`) y cada `rule_effect` se lee después de revisar su
# `demography`.
PHASE2_RESOURCES_PER_PATTERN = 20

PHASE2_PROTOCOL_CONFIGS: dict[str, SimulationConfig] = {
    key: replace(config, resources_per_pattern=PHASE2_RESOURCES_PER_PATTERN)
    for key, config in PHASE2_PROTOCOL_CONFIGS_ORIGINAL.items()
}

# --- Pre-registro de la Fase II-B (design D56, aprobado en la tarea 0.5) -----------------------

PHASE25_DESIGN_RULES: tuple[DesignRule, ...] = (
    DesignRule(
        "R24",
        "ADN compacto y expresión condicional",
        "Rasgos en codones de 32 bits expresados según el contexto, con costo sobre lo expresado. "
        "Sesgo declarado: abarata la complejidad latente.",
        (("enable_compact_dna", False),),
    ),
    DesignRule(
        "R25",
        "Señal posicional epigenética",
        "Proveer una señal de posición y conocimiento dentro del holón; su uso lo decide el ADN.",
        (("enable_epigenetic_roles", False),),
    ),
    DesignRule(
        "R26",
        "Conjugación de plásmidos",
        "Transferir codones entre vecinos en vida.",
        (("enable_plasmid_hgt", False),),
    ),
    DesignRule(
        "R27",
        "Inmunidad CRISPR",
        "Purgar plásmidos con balance energético negativo y bloquear su reingreso.",
        (("enable_crispr_immunity", False),),
    ),
    DesignRule(
        "R28",
        "Endospora disponible",
        "Permitir un estado de bajo gasto; su uso lo decide el ADN.",
        (("enable_sporulation", False),),
    ),
    DesignRule(
        "R29",
        "Senescencia telomérica",
        "Limitar la vida con una longevidad expresada. Sesgo declarado: fuerza recambio.",
        (("enable_telomere_senescence", False),),
    ),
    DesignRule(
        "R30",
        "Mutación SOS",
        "Aumentar la variación bajo estrés y reducirla en abundancia.",
        (("enable_sos_mutation", False),),
    ),
    DesignRule(
        "R31",
        "Compromiso simbiótico",
        "Permitir que un holón se vuelva indisoluble si sus hojas lo expresan.",
        (("enable_symbiotic_ratchet", False),),
    ),
    DesignRule(
        "R32",
        "Conducta codificada en el ADN",
        "Que la política de acción y la decisión de comunicar se expresen desde el ADN.",
        (("enable_genetic_policy", False),),
    ),
    DesignRule(
        "R33",
        "Recursos agotables",
        "Escasez real: los recursos tardan en reponerse.",
        (("enable_resource_depletion", False),),
    ),
    DesignRule(
        "R34",
        "Heterogeneidad espacial y estacional",
        "Nichos por región y abundancia variable en el tiempo.",
        (("enable_heterogeneity", False),),
    ),
    DesignRule(
        "R35",
        "Cadáveres",
        "Cerrar el ciclo de energía: los muertos son recurso.",
        (("enable_carcasses", False),),
    ),
    DesignRule(
        "R36",
        "Transferencia de energía",
        "Permitir ceder energía a un vecino; su uso lo decide el ADN.",
        (("enable_energy_transfer", False),),
    ),
    DesignRule(
        "R37",
        "Depredación",
        "Permitir robar energía a un vecino más débil; su uso lo decide el ADN.",
        (("enable_predation", False),),
    ),
    DesignRule(
        "R38",
        "Recombinación",
        "Permitir el cruce de cromosomas con una pareja; su uso lo decide el ADN.",
        (("enable_recombination", False),),
    ),
    DesignRule(
        "R39",
        "Estado interno persistente",
        "Permitir que el ADN escriba y lea bits de estado que persisten entre ticks; su uso lo "
        "decide el ADN.",
        (("enable_internal_state", False),),
    ),
    DesignRule(
        "R40",
        "Plasticidad en vida",
        "Permitir codones cuya fuerza se ajusta en vida con una regla de refuerzo mínima; qué y "
        "cuánto se aprende lo decide el ADN.",
        (("enable_plasticity", False),),
    ),
    DesignRule(
        "R41",
        "Señales evolucionables",
        "Permitir emitir y percibir símbolos sin significado de fábrica; su uso y su significado "
        "los construye la evolución.",
        (("enable_signals", False),),
    ),
)

# `ALL_DESIGN_RULES` no cambia; `ablate()` busca en las dos tuplas (D56).
PHASE25_ALL_RULES: tuple[DesignRule, ...] = ALL_DESIGN_RULES + PHASE25_DESIGN_RULES

PHASE25_ATTRIBUTION_PROFILE = "phase25"  # `PROFILES["phase25"]`: 5000 ticks
PHASE25_SEEDS: tuple[int, ...] = tuple(range(42, 72))
PHASE25_RULE_EFFECT_SEEDS: tuple[int, ...] = tuple(range(42, 52))  # exploratorios (precisión 66)
PHASE25_VIABILITY_SEEDS: tuple[int, ...] = tuple(range(0, 10))  # compuerta de viabilidad (D55)
PHASE25_FINAL_WINDOW = 1000  # un ciclo estacional con `season_length = 500` (precisión 4)
PHASE25_POST_SHIFT_WINDOW = 200  # ticks de `post_shift_accuracy` tras cada cambio (precisión 63)
PHASE25_ALPHA = 0.05
PHASE25_FLOAT_TOLERANCE = 1e-9  # empates y umbral con la tolerancia de `CLAUDE.md` (precisión 112)
PHASE25_MIN_VALID_PAIRS = 20  # menos pares válidos: no evaluable (precisión 45)
PHASE25_HOLM_M = 7  # Holm-Bonferroni sobre las genuinas C13-C19 (D56)
PHASE25_MIN_VIABLE_NULL_SEEDS = 9  # de las 10 de viabilidad, para interpretar E4 (D56)

# Banderas de "25a" (D56), en el orden de la tabla.
_PHASE25_ECOLOGY_FLAGS: dict[str, Any] = {
    "enable_compact_dna": True,
    "enable_genetic_policy": True,
    "enable_plasmid_hgt": True,
    "enable_crispr_immunity": True,
    "enable_sporulation": True,
    "enable_telomere_senescence": True,
    "enable_sos_mutation": True,
    "enable_resource_depletion": True,
    "enable_heterogeneity": True,
    "season_length": 500,
    "enable_carcasses": True,
    "enable_energy_transfer": True,
    "enable_predation": True,
    "enable_recombination": True,
    "enable_internal_state": True,
    "enable_plasticity": True,
    "enable_signals": True,
    "dna_max_length": 64,  # D62.2
}

# `(resources_per_pattern, resource_regen_delay)` de los cuatro protocolos, fijado por la compuerta
# de viabilidad (tareas 23.4 y 23.5): ninguna configuración de la grilla de D55 ni de la grilla
# extendida de la Enmienda 2 (D55.7) fue viable, y rige la salida de respaldo pre-registrada, la de
# más semillas viables en las condiciones que deciden (registros/phase25_viability_enmienda2.json).
PHASE25_ABUNDANCE: tuple[int, int] = (80, 20)


def phase25_protocol_configs(
    resources_per_pattern: int, resource_regen_delay: int
) -> dict[str, SimulationConfig]:
    """Protocolos de D56 con una abundancia de la grilla de la compuerta (D55); nada más cambia."""
    abundance = {
        "resources_per_pattern": resources_per_pattern,
        "resource_regen_delay": resource_regen_delay,
    }
    individual = replace(PHASE2_PROTOCOL_CONFIGS["002a"], **_PHASE25_ECOLOGY_FLAGS, **abundance)
    holonic = replace(
        PHASE2_PROTOCOL_CONFIGS["003a"],
        **_PHASE25_ECOLOGY_FLAGS,
        **abundance,
        enable_epigenetic_roles=True,
        enable_symbiotic_ratchet=True,
    )
    return {
        "25a": individual,  # ecología individual
        "25b": holonic,  # ecología holónica
        "25c": replace(individual, comm_propensity_base=0.0),  # comunicación desde cero
        # Entorno cambiante (D62.1); 0.5 es el valor por defecto de `world_shift_fraction`.
        "25d": replace(individual, world_shift_period=1000, world_shift_fraction=0.5),
    }


PHASE25_PROTOCOL_CONFIGS: dict[str, SimulationConfig] = phase25_protocol_configs(*PHASE25_ABUNDANCE)

_PHASE25_INDIVIDUAL_INACTIVE = (
    "R14",
    "R15",
    "R16",
    "R17",
    "R18",
    "R19",
    "R22",
    "R23",
    "R25",
    "R31",
)

# Reglas sin efecto en la configuración del protocolo: no reciben `rule_effects` (precisiones 2
# y 51).
PHASE25_INACTIVE_RULES: dict[str, tuple[str, ...]] = {
    "25a": _PHASE25_INDIVIDUAL_INACTIVE,
    "25b": ("R14", "R18", "R19"),
    "25c": _PHASE25_INDIVIDUAL_INACTIVE,
    "25d": _PHASE25_INDIVIDUAL_INACTIVE,
}

PHASE25_CLAIMS: tuple[Phase25Claim, ...] = (
    Phase25Claim(
        "C13",
        "La regulación génica evoluciona",
        "25a",
        "mean_conditional_codons",
        "drift",
        ("R12",),
        (),
        1.0,
    ),
    Phase25Claim(
        "C14", "La conducta evoluciona", "25a", "policy_divergence", "drift", ("R12",), (), 0.05
    ),
    Phase25Claim(
        "C15",
        "La comunicación evoluciona desde cero",
        "25c",
        "communicating_fraction",
        "drift",
        ("R12",),
        (),
        0.10,
    ),
    Phase25Claim(
        "C16",
        "Actividad evolutiva por encima de la reproducción neutral",
        "25a",
        "new_activity_per_birth",
        "drift",
        ("R12",),
        (),
        0.001,
        delta_relative=0.25,
    ),
    Phase25Claim(
        "C17",
        "La depredación aumenta la complejidad genética",
        "25a",
        "mean_expressible_nonattack_codons",
        "no_predation",
        ("R37",),
        (),
        1.0,
        baseline_drift="drift",
        comparison_drift="no_predation_drift",
    ),
    Phase25Claim(
        "C18",
        "La cooperación material evoluciona en la ecología holónica",
        "25b",
        "share_rate",
        "drift",
        ("R12",),
        (),
        0.01,
    ),
    Phase25Claim(
        "C19",
        "La memoria y el aprendizaje evolucionan cuando el entorno cambia",
        "25d",
        "mean_learning_codons",
        "stable",
        (),
        (),
        1.0,
        baseline_drift="drift",
        comparison_drift="stable_drift",
    ),
    # Funcional y no genuina: su canal coincide con su R_C (programada por construcción).
    Phase25Claim(
        "C20",
        "La memoria y la plasticidad aceleran la recuperación tras un cambio del entorno",
        "25d",
        "post_shift_accuracy",
        "no_learning",
        ("R39", "R40"),
        ("R39", "R40"),
        0.02,
    ),
)

# Viabilidad de `null_content` por protocolo en las semillas de viabilidad, con la configuración
# fijada por la compuerta (Enmienda 2 de D55, registros/phase25_viability_enmienda2.json). Con 9 o
# más de 10, E4 es interpretable en ese protocolo (D56).
PHASE25_NULL_CONTENT_VIABLE_SEEDS: dict[str, int] = {"25a": 10, "25b": 10, "25c": 10, "25d": 10}


@dataclass(frozen=True)
class Phase25Report:
    profile: str = PHASE25_ATTRIBUTION_PROFILE
    rules: tuple[DesignRule, ...] = PHASE25_ALL_RULES
    evaluations: tuple[Phase25ClaimEvaluation, ...] = field(kw_only=True)
    # afirmación -> regla -> efecto exploratorio (precisión 66); `None` sin semillas válidas
    rule_effects: dict[str, dict[str, float | None]] = field(kw_only=True)


_ALL_RULES_BY_ID = {rule.rule_id: rule for rule in PHASE25_ALL_RULES}


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
    ampliado, D29), el canal de la afirmación no es vacío y está contenido en `R_c`. Las
    afirmaciones de la Fase II-B se clasifican con `_phase25_by_construction`.
    """
    if is_phase2_claim(claim):
        channel = PHASE2_CLAIM_CHANNELS.get(claim.claim_id, ())
        return bool(channel) and set(channel) <= set(claim.purpose_rules)
    return bool(claim.purpose_rules) and disables_communication(ablate(config, claim.purpose_rules))


def _phase25_by_construction(claim: Phase25Claim) -> bool:
    """Programada por construcción (D56): canal no vacío contenido en `R_C`.

    C13-C19 tienen canal vacío y no lo son; C20 sí, y queda fuera de Holm.
    """
    return bool(claim.channel) and set(claim.channel) <= set(claim.rule_ids)


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
        if is_phase2_claim(claim):
            # Con la abundancia del perfil, el control nulo se extingue (calibración, D29).
            abundance = per_variant["full"][0].resources_per_pattern
            e4_ok = abundance != PHASE2_RESOURCES_PER_PATTERN
            evaluation = replace(evaluation, demography=demography, e4_interpretable=e4_ok)
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


# --- Fase II-B: condiciones de los protocolos (design D56) -------------------------------------


def phase25_conditions(protocol: str, config: SimulationConfig) -> dict[str, SimulationConfig]:
    """Condiciones de comparación de un protocolo de la Fase II-B, en orden fijo (D56).

    Todas parten de `config` (la condición `full`). `stable` no usa `ablate`: el entorno cambiante
    no es una regla de diseño (D62.1).
    """
    if protocol not in PHASE25_INACTIVE_RULES:
        raise ValueError(f"protocolo desconocido de la Fase II-B: {protocol}")
    conditions = {"full": config, "drift": ablate(config, ["R12"])}
    if protocol == "25a":
        conditions["no_predation"] = ablate(config, ["R37"])
        conditions["no_predation_drift"] = ablate(config, ["R37", "R12"])
    if protocol == "25d":
        stable = replace(config, world_shift_period=0)
        conditions["stable"] = stable
        conditions["stable_drift"] = ablate(stable, ["R12"])
        conditions["no_learning"] = ablate(config, ["R39", "R40"])
    conditions[NULL_CONTENT] = null_content_variant(config)
    return conditions


def claim_conditions(claim: Phase25Claim) -> tuple[str, ...]:
    """Condiciones de la diferencia de una afirmación: dos, o cuatro en C17 y C19 (D56)."""
    if claim.baseline_drift is not None and claim.comparison_drift is not None:
        return ("full", claim.baseline_drift, claim.comparison, claim.comparison_drift)
    return ("full", claim.comparison)


# --- Fase II-B: métricas de una corrida (design D56, precisiones 4, 43, 44, 49, 63 y 68) -------

_T = TypeVar("_T")

# Historial que registra cada métrica de afirmación (D53.2, D53.3, D63.2 y precisión 42).
_PHASE25_METRIC_HISTORY = {
    "mean_conditional_codons": "genetic",
    "policy_divergence": "genetic",
    "communicating_fraction": "genetic",
    "new_activity_per_birth": "genetic",
    "mean_expressible_nonattack_codons": "genetic",
    "mean_learning_codons": "genetic",
    "share_rate": "ecology",
}
# C16 usa el último tick, no la media de la ventana (precisión 43).
_PHASE25_LAST_TICK_METRICS = frozenset({"new_activity_per_birth"})
_POST_SHIFT_ACCURACY = "post_shift_accuracy"  # métrica de C20 (D56 y D63.4)


def final_window(history: Sequence[_T]) -> list[_T]:
    """Los últimos `min(len(history), PHASE25_FINAL_WINDOW)` registros (precisión 4)."""
    return list(history[max(0, len(history) - PHASE25_FINAL_WINDOW) :])


def _window_mean(history: Sequence[Any], name: str) -> float:
    window = final_window(history)
    return sum(float(getattr(m, name)) for m in window) / len(window) if window else 0.0


def post_shift_accuracy(ecology_history: Sequence[Any], world_shift_period: int) -> float:
    """Aciertos sobre oportunidades de M2 en `[s, s + 200)` de cada cambio `s` (precisión 63).

    Los cambios ocurren en los ticks `t > 0` múltiplos de `world_shift_period` (precisión 56); la
    suma recorre todos los cambios de la corrida. 0.0 sin cambios o sin oportunidades.
    """
    if world_shift_period <= 0 or not ecology_history:
        return 0.0
    first = ecology_history[0].tick  # el historial registra un tick por posición
    last = ecology_history[-1].tick
    windows: list[Any] = []
    for shift in range(world_shift_period, last + 1, world_shift_period):
        start = shift - first
        if start >= 0:
            windows.extend(ecology_history[start : start + PHASE25_POST_SHIFT_WINDOW])
    return windowed_accuracy(windows)


def phase25_metric_value(
    metric: str,
    genetic_history: Sequence[Any],
    ecology_history: Sequence[Any],
    world_shift_period: int,
) -> float:
    """Valor de la métrica de una afirmación de la Fase II-B en una corrida (D56, precisión 4)."""
    if metric == _POST_SHIFT_ACCURACY:
        return post_shift_accuracy(ecology_history, world_shift_period)
    source = _PHASE25_METRIC_HISTORY.get(metric)
    if source is None:
        raise ValueError(f"métrica desconocida de la Fase II-B: {metric}")
    history = genetic_history if source == "genetic" else ecology_history
    if metric in _PHASE25_LAST_TICK_METRICS:
        return float(getattr(history[-1], metric)) if history else 0.0
    return _window_mean(history, metric)


def effective_parents(genetic_history: Sequence[Any]) -> float:
    """`1 / Σ p_i²` de las fuentes genéticas de los nacimientos de la ventana final.

    Concatena `birth_source_ids` de la ventana (precisiones 44 y 68); 0.0 sin nacimientos.
    """
    counts = Counter(source for m in final_window(genetic_history) for source in m.birth_source_ids)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return 1.0 / sum((count / total) ** 2 for _, count in sorted(counts.items()))


@dataclass(frozen=True)
class Phase25RunRecord:
    """Resumen de una corrida de la atribución: su demografía y las métricas pedidas."""

    final_agents: int
    final_active_agents: int  # hojas vivas que no están en endospora
    max_generation: int
    cumulative_births: int
    cumulative_deaths: int
    mean_age_at_death: float  # del último registro de `genetic_history` (precisión 49)
    effective_parents: float  # precisión 44
    metrics: dict[str, float]

    def demography(self) -> dict[str, float]:
        """Covariables de la evaluación, con los enteros como `float` (precisión 45)."""
        return {
            "final_agents": float(self.final_agents),
            "final_active_agents": float(self.final_active_agents),
            "max_generation": float(self.max_generation),
            "cumulative_births": float(self.cumulative_births),
            "cumulative_deaths": float(self.cumulative_deaths),
            "mean_age_at_death": float(self.mean_age_at_death),
            "effective_parents": float(self.effective_parents),
        }


def final_demography(engine: Any) -> tuple[int, int, int]:
    """(hojas vivas, hojas vivas que no están en endospora, generación máxima) de un motor ya
    corrido. Es la demografía que comparten el registro de una corrida y la compuerta de
    viabilidad (D55); los conteos no dependen del orden de `agents`.
    """
    agents = engine.agents.values()
    return (
        len(engine.agents),
        sum(1 for agent in agents if not agent.is_endospore),
        max((m.max_generation for m in engine.evolutionary_history), default=0),
    )


def phase25_run_record(
    engine: Any, metrics: Sequence[str], world_shift_period: int
) -> Phase25RunRecord:
    """Resume un motor ya corrido: lee `agents` y los historiales evolutivo, genético y ecológico.

    Los nacimientos y las muertes son las sumas de `evolutionary_history` desde el tick 0
    (precisión 49).
    """
    genetic = engine.genetic_history
    ecology = engine.ecology_history
    evolution = engine.evolutionary_history
    final_agents, final_active_agents, max_generation = final_demography(engine)
    return Phase25RunRecord(
        final_agents=final_agents,
        final_active_agents=final_active_agents,
        max_generation=max_generation,
        cumulative_births=sum(m.births_this_tick for m in evolution),
        cumulative_deaths=sum(m.deaths_this_tick for m in evolution),
        mean_age_at_death=float(genetic[-1].mean_age_at_death) if genetic else 0.0,
        effective_parents=effective_parents(genetic),
        metrics={
            name: phase25_metric_value(name, genetic, ecology, world_shift_period)
            for name in metrics
        },
    )


_Phase25Job = tuple[SimulationConfig, int, tuple[str, ...]]  # (configuración, ticks, métricas)


def _execute_phase25_run(job: _Phase25Job) -> Phase25RunRecord:
    """Unidad independiente de trabajo: una corrida completa de la configuración."""
    config, total_ticks, metrics = job
    engine = SimulationEngine(config)
    engine.run(total_ticks)
    return phase25_run_record(engine, metrics, config.world_shift_period)


# --- Fase II-B: prueba, corrección y estado (design D56, precisiones 45, 47, 48 y 53) ----------


def holm_bonferroni(p_values: Sequence[float], m: int | None = None) -> list[float]:
    """P-valores ajustados por Holm-Bonferroni, en el orden de entrada.

    Ordenados de menor a mayor (los empates, por posición), el ajustado de la posición `i` es
    `max_{j <= i} min(1, (m - j + 1) p_(j))`. Con `m` mayor que la cantidad de p-valores, los
    ausentes cuentan como `p = 1`: es lo conservador.
    """
    count = len(p_values)
    total = count if m is None else m
    if total < count:
        raise ValueError(f"m ({total}) debe ser >= la cantidad de p-valores ({count})")
    order = sorted(range(count), key=lambda i: (p_values[i], i))
    adjusted = [0.0] * count
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (total - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def effect_threshold(claim: Phase25Claim, comparison_median: float) -> float:
    """`max(δ_min, delta_relative · M)`, con `M` la mediana de `comparison_values` (D56).

    En una diferencia simple `M` es la mediana de la condición de comparación; en C17 y C19, la de
    `comp − comp_drift` (precisiones 69 y 119). Sólo C16 tiene `delta_relative` distinto de cero.
    """
    return max(claim.delta_min, claim.delta_relative * comparison_median)


def claim_threshold_and_valid_seeds(
    claim: Phase25Claim,
    comparison_values: Mapping[int, float],
    seeds: Sequence[int],
    excluded_seeds: Sequence[int],
) -> tuple[float, tuple[int, ...]]:
    """Umbral de efecto de D56 y pares válidos de una afirmación (precisiones 45, 116 y 119).

    Los pares válidos son las semillas de `seeds`, en su orden, que no están en `excluded_seeds`;
    el umbral es `effect_threshold` con `M` la mediana de `comparison_values` sobre ellos (0.0 si no
    queda ninguno). Es la misma cuenta con la que `evaluate_phase25_claims` decide el estado, y la
    usan también los reportes, para no recalcularla aparte.
    """
    excluded = set(excluded_seeds)
    valid = tuple(s for s in seeds if s not in excluded)
    comparison_median = median([comparison_values[s] for s in valid]) if valid else 0.0
    return effect_threshold(claim, comparison_median), valid


def phase25_status(
    *,
    by_construction: bool,
    evaluable: bool,
    p_value: float,
    p_adjusted: float | None,
    median_difference: float,
    threshold: float,
    alpha: float = PHASE25_ALPHA,
) -> ClaimStatus:
    """`OBSERVED` con significancia y efecto; `NOT_OBSERVED` en otro caso (D56).

    Una genuina usa el p-valor ajustado por Holm; una programada por construcción (C20), el crudo
    (precisión 53). Una afirmación no evaluable nunca es `OBSERVED` (precisión 45).
    """
    if by_construction:
        p = p_value
    elif p_adjusted is None:
        raise ValueError("una afirmación genuina exige su p-valor ajustado")
    else:
        p = p_adjusted
    reaches = median_difference >= threshold - PHASE25_FLOAT_TOLERANCE  # precisión 112
    observed = evaluable and p < alpha and reaches
    return ClaimStatus.OBSERVED if observed else ClaimStatus.NOT_OBSERVED


def phase25_sign_test(differences: Sequence[float]) -> float:
    """Prueba de signo unilateral con `|d| <= 1e-9` como empate, que se descarta (precisión 112)."""
    return sign_test_p_value([0.0 if abs(d) <= PHASE25_FLOAT_TOLERANCE else d for d in differences])


def e4_interpretable(viable_null_seeds: int | None) -> bool:
    """E4 se interpreta si `null_content` fue viable en al menos 9 de las 10 semillas (D56)."""
    return viable_null_seeds is not None and viable_null_seeds >= PHASE25_MIN_VIABLE_NULL_SEEDS


_Phase25Runs = Mapping[str, Mapping[str, Mapping[int, Phase25RunRecord]]]


@dataclass(frozen=True)
class _Partial:
    """Evaluación sin la corrección de Holm, que necesita a todas las afirmaciones."""

    evaluation: Phase25ClaimEvaluation
    threshold: float
    by_construction: bool


def _active(record: Phase25RunRecord) -> bool:
    return record.final_active_agents >= 1


def _evaluate_one(
    claim: Phase25Claim,
    runs: Mapping[str, Mapping[int, Phase25RunRecord]],
    seeds: Sequence[int],
    e4_ok: bool,
) -> _Partial:
    conditions = claim_conditions(claim)
    missing = [
        name
        for name in (*conditions, NULL_CONTENT)
        if name not in runs or any(seed not in runs[name] for seed in seeds)
    ]
    if missing:
        raise ValueError(f"{claim.claim_id}: faltan corridas de {missing}")

    def value(condition: str, seed: int) -> float:
        return runs[condition][seed].metrics[claim.metric]

    if claim.baseline_drift is not None and claim.comparison_drift is not None:
        baseline, comparison_drift = claim.baseline_drift, claim.comparison_drift
        values = {s: value("full", s) - value(baseline, s) for s in seeds}
        comparison_values = {
            s: value(claim.comparison, s) - value(comparison_drift, s) for s in seeds
        }
    else:
        values = {s: value("full", s) for s in seeds}
        comparison_values = {s: value(claim.comparison, s) for s in seeds}
    active = {s for s in seeds if all(_active(runs[c][s]) for c in conditions)}
    excluded = tuple(s for s in seeds if s not in active)
    threshold, valid = claim_threshold_and_valid_seeds(claim, comparison_values, seeds, excluded)
    differences = [values[s] - comparison_values[s] for s in valid]
    e4_valid = [s for s in seeds if _active(runs["full"][s]) and _active(runs[NULL_CONTENT][s])]
    evaluation = Phase25ClaimEvaluation(
        claim_id=claim.claim_id,
        status=ClaimStatus.NOT_OBSERVED,  # se decide después de Holm
        p_value=phase25_sign_test(differences),
        p_adjusted=None,
        median_difference=median(differences) if differences else 0.0,
        values=values,
        comparison_values=comparison_values,
        demography={c: {s: runs[c][s].demography() for s in seeds} for c in conditions},
        e4_p_value=phase25_sign_test([value("full", s) - value(NULL_CONTENT, s) for s in e4_valid]),
        e4_interpretable=e4_ok,
        excluded_seeds=excluded,
        excluded_pairs=len(excluded),
        evaluable=len(valid) >= PHASE25_MIN_VALID_PAIRS,
    )
    return _Partial(evaluation, threshold, _phase25_by_construction(claim))


def evaluate_phase25_claims(
    claims: Sequence[Phase25Claim],
    records: _Phase25Runs,
    seeds: Sequence[int],
    e4_flags: Mapping[str, bool] | None = None,
) -> tuple[Phase25ClaimEvaluation, ...]:
    """Prueba de signo sobre los pares válidos, Holm sobre las genuinas y estado (D56).

    `records` es protocolo -> condición -> semilla -> corrida. Las genuinas se corrigen con
    `m = max(PHASE25_HOLM_M, cantidad de genuinas)`; C20 queda fuera de Holm. `e4_flags` dice, por
    protocolo, si E4 es interpretable según la compuerta (falso si falta).
    """
    flags = e4_flags or {}
    partials = [
        _evaluate_one(
            claim, records.get(claim.protocol, {}), seeds, flags.get(claim.protocol, False)
        )
        for claim in claims
    ]
    genuine = [i for i, partial in enumerate(partials) if not partial.by_construction]
    adjusted = holm_bonferroni(
        [partials[i].evaluation.p_value for i in genuine], m=max(PHASE25_HOLM_M, len(genuine))
    )
    adjusted_by_index = dict(zip(genuine, adjusted, strict=True))
    evaluations: list[Phase25ClaimEvaluation] = []
    for index, partial in enumerate(partials):
        evaluation = partial.evaluation
        p_adjusted = adjusted_by_index.get(index)
        status = phase25_status(
            by_construction=partial.by_construction,
            evaluable=evaluation.evaluable,
            p_value=evaluation.p_value,
            p_adjusted=p_adjusted,
            median_difference=evaluation.median_difference,
            threshold=partial.threshold,
        )
        evaluations.append(replace(evaluation, status=status, p_adjusted=p_adjusted))
    return tuple(evaluations)


def phase25_rule_effect(
    full: Mapping[int, Phase25RunRecord],
    variant: Mapping[int, Phase25RunRecord],
    metric: str,
    seeds: Sequence[int],
) -> float | None:
    """Mediana de `full(s) − variante(s)` en la métrica simple, sobre las semillas válidas.

    Una semilla es válida si las dos corridas terminan con hojas activas (precisión 45); sin
    semillas válidas el efecto es `None`, nunca 0.0 (precisión 66).
    """
    valid = [
        s for s in seeds if s in full and s in variant and _active(full[s]) and _active(variant[s])
    ]
    if not valid:
        return None
    return median([full[s].metrics[metric] - variant[s].metrics[metric] for s in valid])


# --- Fase II-B: atribución (design D56, precisiones 66 y 67) -----------------------------------


def check_phase25_protocol(protocol: str, config: SimulationConfig) -> None:
    """La configuración `full` debe respetar los rasgos que definen su protocolo (D56)."""
    holonic = config.enable_holonic_hierarchy
    problems = [
        name
        for name, ok in (
            ("enable_evolution", config.enable_evolution),
            ("enable_compact_dna", config.enable_compact_dna),
            ("enable_genetic_policy", config.enable_genetic_policy),
            ("enable_holonic_hierarchy", holonic if protocol == "25b" else not holonic),
            ("enable_predation", config.enable_predation or protocol != "25a"),
            (
                "comm_propensity_base",
                (config.comm_propensity_base == 0.0) is (protocol == "25c"),
            ),
            (
                "world_shift_period",
                (config.world_shift_period > 0) is (protocol == "25d"),
            ),
            (
                "enable_internal_state/enable_plasticity",
                protocol != "25d" or (config.enable_internal_state and config.enable_plasticity),
            ),
        )
        if not ok
    ]
    if problems:
        raise ValueError(f"la configuración de {protocol} no respeta su protocolo: {problems}")


def _phase25_e4_flags(configs: Mapping[str, SimulationConfig]) -> dict[str, bool]:
    """E4 se interpreta sólo con la abundancia elegida por la compuerta y su `null_content` viable.

    Con otra abundancia la viabilidad registrada no aplica y E4 no es interpretable (precisión 113).
    """
    return {
        protocol: (config.resources_per_pattern, config.resource_regen_delay) == PHASE25_ABUNDANCE
        and e4_interpretable(PHASE25_NULL_CONTENT_VIABLE_SEEDS.get(protocol))
        for protocol, config in configs.items()
    }


def _phase25_effect_rules(protocol: str) -> list[str]:
    """Reglas que reciben variante: las ablacionables, salvo las inactivas del protocolo."""
    inactive = set(PHASE25_INACTIVE_RULES[protocol])
    return [r.rule_id for r in PHASE25_ALL_RULES if r.ablation and r.rule_id not in inactive]


def validate_phase25_attribution(
    seeds: Sequence[int] = PHASE25_SEEDS,
    claims: Sequence[Phase25Claim] = PHASE25_CLAIMS,
    configs: Mapping[str, SimulationConfig] | None = None,
    rule_effect_seeds: Sequence[int] = PHASE25_RULE_EFFECT_SEEDS,
) -> dict[str, SimulationConfig]:
    """Comprobaciones previas de `run_phase25_attribution`, sin correr nada; `ValueError` si fallan.

    Devuelve la configuración `full` de cada protocolo que miden las afirmaciones, en el orden en
    que aparecen: son las que se validan y se corren. Una CLI la llama antes de crear directorios.
    """
    validate_seeds(seeds)
    if rule_effect_seeds:
        validate_seeds(rule_effect_seeds)
    # Un llamador sin tipos puede pasar afirmaciones de otra fase.
    foreign = [
        getattr(c, "claim_id", repr(c))
        for c in claims
        if not isinstance(c, Phase25Claim)  # pyright: ignore[reportUnnecessaryIsInstance]
    ]
    if foreign:
        raise ValueError(f"la atribución de la Fase II-B sólo mide afirmaciones de D56: {foreign}")
    chosen = PHASE25_PROTOCOL_CONFIGS if configs is None else configs
    unknown = sorted({c.protocol for c in claims if c.protocol not in chosen})
    if unknown:
        raise ValueError(f"protocolos desconocidos de la Fase II-B: {unknown}")
    protocols = dict.fromkeys(c.protocol for c in claims)
    for protocol in protocols:
        check_phase25_protocol(protocol, chosen[protocol])
    for seed in (*seeds, *rule_effect_seeds):  # la regla `seed >= 0` de `SimulationConfig`
        SimulationConfig(seed=seed)
    return {protocol: chosen[protocol] for protocol in protocols}


def run_phase25_attribution(
    seeds: Sequence[int] = PHASE25_SEEDS,
    claims: Sequence[Phase25Claim] = PHASE25_CLAIMS,
    jobs: int = 1,
    configs: Mapping[str, SimulationConfig] | None = None,
    rule_effect_seeds: Sequence[int] = PHASE25_RULE_EFFECT_SEEDS,
) -> Phase25Report:
    """Pre-registro de la Fase II-B: cada afirmación sobre la configuración de su protocolo.

    Usa `configs[claim.protocol]` (por defecto `PHASE25_PROTOCOL_CONFIGS`) como condición `full`
    y `PROFILES["phase25"]`. Cada corrida se identifica por (protocolo, variante, semilla) y se
    ejecuta una sola vez (precisión 67); las configuraciones idénticas, aun con claves distintas,
    también se ejecutan una sola vez. Las corridas se reparten en `jobs` procesos y se reúnen en
    orden fijo, así que el reporte no depende de `jobs`.
    """
    chosen = validate_phase25_attribution(seeds, claims, configs, rule_effect_seeds)
    protocols = list(chosen)
    total_ticks = PROFILES[PHASE25_ATTRIBUTION_PROFILE].total_ticks

    plan: dict[tuple[str, str, int], SimulationConfig] = {}  # (protocolo, variante, semilla)
    for protocol in protocols:
        base = chosen[protocol]
        needed = dict.fromkeys(
            name
            for c in claims
            if c.protocol == protocol
            for name in (*claim_conditions(c), NULL_CONTENT)
        )
        for seed in seeds:
            conditions = phase25_conditions(protocol, replace(base, seed=seed))
            for name in needed:
                if name not in conditions:
                    raise ValueError(f"el protocolo {protocol} no tiene la condición {name}")
                plan[(protocol, name, seed)] = conditions[name]
        for seed in rule_effect_seeds:
            seeded = replace(base, seed=seed)
            plan[(protocol, "full", seed)] = seeded
            for rule_id in _phase25_effect_rules(protocol):
                plan[(protocol, rule_id, seed)] = ablate(seeded, [rule_id])

    # Cada configuración se corre una vez y calcula sólo las métricas de las afirmaciones de los
    # protocolos que la usan (una configuración puede repetirse entre protocolos).
    metrics_of: dict[SimulationConfig, set[str]] = {}
    for (protocol, _, _), config in plan.items():
        metrics_of.setdefault(config, set()).update(
            c.metric for c in claims if c.protocol == protocol
        )
    jobs_list: list[_Phase25Job] = [
        (config, total_ticks, tuple(sorted(names))) for config, names in metrics_of.items()
    ]
    outcomes = map_in_order(_execute_phase25_run, jobs_list, jobs)
    results = {job[0]: outcome for job, outcome in zip(jobs_list, outcomes, strict=True)}
    records: dict[str, dict[str, dict[int, Phase25RunRecord]]] = {}
    for (protocol, variant, seed), config in plan.items():
        records.setdefault(protocol, {}).setdefault(variant, {})[seed] = results[config]

    flags = _phase25_e4_flags({protocol: chosen[protocol] for protocol in protocols})
    evaluations = evaluate_phase25_claims(claims, records, seeds, flags)
    rule_effects: dict[str, dict[str, float | None]] = {}
    for claim in claims:
        runs = records[claim.protocol]
        rule_effects[claim.claim_id] = {
            rule_id: phase25_rule_effect(
                runs.get("full", {}), runs.get(rule_id, {}), claim.metric, rule_effect_seeds
            )
            for rule_id in _phase25_effect_rules(claim.protocol)
        }
    return Phase25Report(
        profile=PHASE25_ATTRIBUTION_PROFILE,
        rules=PHASE25_ALL_RULES,
        evaluations=evaluations,
        rule_effects=rule_effects,
    )
