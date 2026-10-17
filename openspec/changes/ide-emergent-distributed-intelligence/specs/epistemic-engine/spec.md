# Spec Delta: Epistemic Engine

## Purpose
Implementar las reglas matemáticas de aprendizaje individual por experiencia directa y la epistemología de revalidación social frente a testimonios de otros agentes (adopción con descuento, consenso con protección anti-cámara de eco y resolución de contradicciones).

## ADDED Requirements

### Requirement: Aprendizaje por Experiencia Directa y Prioridad Empírica
El módulo `src/ide/agent/epistemology.py` SHALL proveer la función `update_from_direct_experience(existing: KnowledgeUnit | None, pattern: Pattern, real_value: float, tick: int, config: SimulationConfig) -> KnowledgeUnit` que asigne confianza alta inicial (`initial_direct_confidence`) si el patrón es nuevo, refuerce la confianza si el signo de `real_value` coincide con `predicted_value`, o aplique castigo severo (`beta_punish`) si la experiencia empírica contradice una creencia previa:
- Si `penalized_conf < config.decision_conf_threshold`: invierte el signo directamente hacia `float(np.clip(real_value, -1.0, 1.0))` con `confidence = config.initial_direct_confidence` y `from_direct_experience = True`.
- Si `penalized_conf >= config.decision_conf_threshold`: conserva temporalmente el signo original acotando el valor a `new_val = np.sign(existing.predicted_value) * max(0.05, abs((1.0 - config.alpha_learning) * existing.predicted_value + config.alpha_learning * real_value))` con `confidence = penalized_conf`.

#### Scenario: Adquisición de creencia nueva por interacción directa
- **WHEN** el agente no tiene creencia previa sobre $\rho$ e interactúa con un recurso de patrón $\rho$ recibiendo `real_value = -1.0` en $t=5$
- **THEN** se genera un `KnowledgeUnit` con `predicted_value = -1.0`, `confidence = config.initial_direct_confidence`, `evidence_count = 1`, `last_updated_tick = 5` y `from_direct_experience = True`.

#### Scenario: Refutación empírica de una creencia falsa inyectada o heredada
- **WHEN** el agente sostiene una creencia falsa con `predicted_value = +1.0` y `confidence = 0.80`, pero al interactuar directamente con el recurso recibe `real_value = -1.0` (`beta_punish = 0.60`, `decision_conf_threshold = 0.35`)
- **THEN** `penalized_conf` cae a `0.20 < 0.35` y el motor invierte inmediatamente `predicted_value` a `-1.0` con `confidence = config.initial_direct_confidence` y `from_direct_experience = True`.

### Requirement: Asimilación Social con Descuento por Testimonio Indirecto (Escenario A)
Cuando un agente reciba una creencia externa $k_{\text{ext}}$ sobre un patrón $\rho$ que no posee en su memoria, `merge_social_belief` SHALL crear una creencia derivada con `confidence = sender_trust_factor * k_ext.confidence` (donde `sender_trust_factor` por defecto es `config.gamma_social_discount`) y `from_direct_experience = False`.

#### Scenario: Atenuación de rumor en cadena de transmisión
- **WHEN** el agente A descubre un recurso con confianza `0.85`, lo transmite a B ($\gamma = 0.75$) y B lo retransmite a C sin que B ni C hayan interactuado con el recurso
- **THEN** B almacena la creencia con confianza `0.6375` y C la recibe con confianza `0.478125`.

### Requirement: Refuerzo por Consenso Social con Protección Anti-Cámara de Eco (Escenario B)
Cuando el agente receptor ya posea una creencia $k_{\text{local}}$ sobre $\rho$ cuyo signo coincida con el de $k_{\text{ext}}$, `merge_social_belief` SHALL combinar `predicted_value` mediante media ponderada por confianza y actualizar la confianza local aplicando protección contra el efecto cámara de eco (*Bootstrap Illusion*):
- Si `k_ext.from_direct_experience` es `True` (el emisor tiene evidencia empírica directa):
  $$c_{\text{nueva}} = \min\left(1.0, \; c_{\text{local}} + \eta_{\text{consensus}} \cdot (\gamma c_{\text{ext}}) \cdot (1 - c_{\text{local}})\right)$$
- Si `k_ext.from_direct_experience` es `False` (el emisor sólo transmite un rumor indirecto):
  la confianza resultante no puede superar el máximo entre su confianza actual y la confianza descontada recibida ($\max(c_{\text{local}}, \gamma c_{\text{ext}})$), evitando que dos portadores de rumores inflen su certeza hacia `1.0` rebotando el mismo rumor.

#### Scenario: Dos agentes con evidencia directa o receptor ante descubridor directo refuerzan confianza
- **WHEN** el receptor tiene $k_{\text{local}}$ con $\hat{v} = +1.0, c = 0.60$ y recibe $k_{\text{ext}}$ con `from_direct_experience = True`, $\hat{v} = +1.0, c = 0.80$ ($\gamma = 0.75, \eta_{\text{consensus}} = 0.15$)
- **THEN** la confianza del receptor se incrementa por encima de `0.60` y `evidence_count` aumenta en 1.

#### Scenario: Dos portadores de rumores indirectos no inflan la confianza artificialmente
- **WHEN** tanto A como B tienen `from_direct_experience = False` con $c = 0.50$ e intercambian sus creencias en bucle ($\gamma = 0.75$)
- **THEN** la confianza de ambos permanece acotada en `0.50` sin escalar hacia `1.0`.

### Requirement: Resolución de Conflicto Epistémico (Escenario C)
Cuando el signo de $k_{\text{ext}}$ contradiga el signo de $k_{\text{local}}$ ($\text{sign}(\hat{v}_{\text{local}}) \neq \text{sign}(\hat{v}_{\text{ext}})$), `merge_social_belief` SHALL proteger el conocimiento empírico directo frente a rumores externos, aplicando un factor de resistencia mayor (`resistance = 2.0`) si `k_local.from_direct_experience` es `True`.

#### Scenario: Resistencia de experiencia directa frente a rumor falso externo
- **WHEN** el agente posee una creencia obtenida por experiencia directa (`from_direct_experience = True`, $\hat{v} = +1.0, c = 0.85$) y recibe un mensaje externo falso ($\hat{v} = -1.0, c = 0.90$)
- **THEN** el agente conserva el signo $\hat{v} = +1.0$ y su confianza permanece por encima del umbral de decisión (`decision_conf_threshold`).

#### Scenario: Sobrescritura de rumor débil por testimonio de alta evidencia
- **WHEN** el agente posee un rumor antiguo no verificado (`from_direct_experience = False`, $\hat{v} = -1.0, c = 0.25$) y recibe un testimonio opuesto con alta confianza ($\hat{v} = +1.0, c = 0.90, \gamma = 0.75$)
- **THEN** dado que $\gamma c_{\text{ext}} = 0.675 > 1.2 \times 0.25$, la creencia débil es reemplazada por la nueva creencia con signo $+1.0$ y `confidence = 0.675 - 0.5 * 0.25 = 0.55`.
