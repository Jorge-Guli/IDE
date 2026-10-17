"""Reglas de aprendizaje: experiencia directa y revalidación social de testimonios."""

from dataclasses import replace

from ide.config import SimulationConfig
from ide.domain.types import KnowledgeUnit, Pattern

_MIN_ATTENUATED_MAGNITUDE = 0.05
_OVERWRITE_RATIO = 1.2
_OVERWRITE_PENALTY = 0.5
_DIRECT_RESISTANCE = 2.0


def _clip(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


def update_from_direct_experience(
    existing: KnowledgeUnit | None,
    pattern: Pattern,
    real_value: float,
    tick: int,
    config: SimulationConfig,
) -> KnowledgeUnit:
    """Adquisición, refuerzo o refutación por interacción física con un recurso."""
    fresh = KnowledgeUnit(
        pattern, _clip(real_value), config.initial_direct_confidence, 1, tick, True
    )
    if existing is None:
        return fresh
    v_hat, c = existing.predicted_value, existing.confidence
    alpha = config.alpha_learning
    blended = (1.0 - alpha) * v_hat + alpha * real_value
    if v_hat * real_value >= 0:
        confidence = min(1.0, c + config.beta_reinforce * (1.0 - c))
        return KnowledgeUnit(
            pattern, _clip(blended), confidence, existing.evidence_count + 1, tick, True
        )
    penalized = c - config.beta_punish
    if penalized < config.decision_conf_threshold:
        return fresh
    sign = 1.0 if v_hat >= 0 else -1.0
    value = sign * max(_MIN_ATTENUATED_MAGNITUDE, abs(blended))
    return KnowledgeUnit(pattern, _clip(value), penalized, existing.evidence_count + 1, tick, True)


def merge_social_belief(
    existing: KnowledgeUnit | None,
    incoming: KnowledgeUnit,
    tick: int,
    config: SimulationConfig,
    sender_trust_factor: float | None = None,
) -> KnowledgeUnit:
    """Fusiona un testimonio ajeno con la creencia local (Escenarios A, B y C)."""
    gamma = config.gamma_social_discount if sender_trust_factor is None else sender_trust_factor
    e = gamma * incoming.confidence
    v_ext = incoming.predicted_value
    if existing is None:
        return KnowledgeUnit(incoming.pattern, v_ext, e, 1, tick, False)
    v_hat, c = existing.predicted_value, existing.confidence
    if v_hat * v_ext >= 0:
        value = (c * v_hat + e * v_ext) / (c + e) if c + e > 0 else v_ext
        raw = c + config.eta_consensus * e * (1.0 - c)
        # Un rumor no valida a otro rumor: sin evidencia directa del emisor no hay
        # refuerzo por encima del mejor testimonio ni se refresca τ (R6, ablacionable).
        validated = incoming.from_direct_experience or not config.anti_echo_enabled
        confidence = min(1.0, raw) if validated else min(max(c, e), raw)
        tau = tick if validated else existing.last_updated_tick
        return KnowledgeUnit(
            existing.pattern,
            value,
            confidence,
            existing.evidence_count + 1,
            tau,
            existing.from_direct_experience,
        )
    if not existing.from_direct_experience and e > _OVERWRITE_RATIO * c:
        confidence = max(config.min_confidence, e - _OVERWRITE_PENALTY * c)
        return KnowledgeUnit(existing.pattern, v_ext, confidence, 1, tick, False)
    # La duda no es una validación: conserva valor, origen y τ.
    resistance = _DIRECT_RESISTANCE if existing.from_direct_experience else 1.0
    return replace(existing, confidence=max(0.0, c - config.eta_doubt * e / resistance))
