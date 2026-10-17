"""Atribución de emergencia (Decisión 13): emergente vs. programado.

`DESIGN_RULES`, `EXP001_CLAIMS` y `ATTRIBUTION_PROFILE` son un **pre-registro**: se versionan
antes de mirar resultados, y cambiarlos después exige un commit que lo justifique.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any

from ide.config import SimulationConfig


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
