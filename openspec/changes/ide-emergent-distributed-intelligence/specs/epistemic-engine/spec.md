# Spec Delta: Epistemic Engine

## Purpose
Implementar las reglas de aprendizaje individual por experiencia directa y la revalidación social frente a testimonios de otros agentes: adopción con descuento, consenso con protección anti-cámara de eco y resolución de contradicciones. Los valores numéricos de los escenarios se verifican con tolerancia absoluta `1e-9`.

## ADDED Requirements

### Requirement: Adquisición por Experiencia Directa
`update_from_direct_experience(None, pattern, real_value, tick, config)` en `src/ide/agent/epistemology.py` SHALL devolver una creencia con `predicted_value = clip(real_value, -1, 1)`, `confidence = initial_direct_confidence`, `evidence_count = 1`, `last_updated_tick = tick` y `from_direct_experience = True`.

#### Scenario: Primera interacción con un recurso dañino
- **WHEN** el agente no tiene creencia sobre $\rho$ y en `t=5` experimenta `real_value = -1.0`
- **THEN** la creencia resultante tiene `predicted_value = -1.0`, `confidence = 0.85`, `evidence_count = 1`, `last_updated_tick = 5` y `from_direct_experience = True`.

### Requirement: Refuerzo Empírico
Si `existing.predicted_value * real_value >= 0`, la función SHALL devolver `predicted_value = clip((1-α)·v̂ + α·v)`, `confidence = min(1, c + β_reinforce·(1-c))`, `evidence_count + 1` y `from_direct_experience = True`.

#### Scenario: Confirmación de creencia social
- **WHEN** el agente tiene `v̂ = +1.0`, `c = 0.50`, `from_direct_experience = False` y experimenta `real_value = +1.0`
- **THEN** la confianza resultante es `0.65` y `from_direct_experience` pasa a `True`.

### Requirement: Refutación Empírica Severa
Si `existing.predicted_value * real_value < 0` y `c - β_punish < decision_conf_threshold`, la función SHALL reiniciar la creencia al valor empírico con `confidence = initial_direct_confidence`, `evidence_count = 1` y `from_direct_experience = True`.

#### Scenario: Derrumbe de una creencia falsa
- **WHEN** el agente cree `v̂ = +1.0` con `c = 0.80` y experimenta `real_value = -1.0` (`β_punish = 0.60`, umbral `0.35`)
- **THEN** la creencia resultante tiene `predicted_value = -1.0` y `confidence = 0.85`.

### Requirement: Refutación Empírica Atenuada
Si `existing.predicted_value * real_value < 0` y `c - β_punish >= decision_conf_threshold`, la función SHALL conservar el signo previo con `predicted_value = sign(v̂)·max(0.05, |(1-α)·v̂ + α·v|)`, `confidence = c - β_punish` y `evidence_count + 1`.

#### Scenario: Creencia muy sólida que recibe una contradicción
- **WHEN** el agente cree `v̂ = +1.0` con `c = 1.0` y experimenta `real_value = -1.0` (`α = 0.40`, `β_punish = 0.60`)
- **THEN** la creencia resultante tiene `predicted_value = 0.2` y `confidence = 0.4`.

### Requirement: Adopción de Rumor con Descuento (Escenario A)
`merge_social_belief(None, incoming, tick, config, sender_trust_factor)` SHALL devolver una creencia con el valor del emisor, `confidence = clip(γ · incoming.confidence, 0, 1)` (γ = `sender_trust_factor` o, si es `None`, `gamma_social_discount`), `evidence_count = 1` y `from_direct_experience = False`.

#### Scenario: Atenuación en cadena
- **WHEN** A descubre un recurso con confianza `0.85`, lo transmite a B (`γ = 0.75`) y B lo retransmite a C, sin que B ni C interactúen con el recurso
- **THEN** B almacena confianza `0.6375` y C almacena `0.478125`.

#### Scenario: Factor de confianza personalizado
- **WHEN** se invoca con `incoming.confidence = 0.8` y `sender_trust_factor = 0.5`
- **THEN** la confianza resultante es `0.4`.

### Requirement: Consenso con Evidencia Directa del Emisor (Escenario B)
Si los signos coinciden e `incoming.from_direct_experience` es verdadero, la función SHALL promediar el valor ponderado por confianza y devolver `confidence = min(1, c + η_consensus·(γc_ext)·(1-c))` con `evidence_count + 1`.

#### Scenario: Receptor ante un descubridor directo
- **WHEN** el receptor tiene `v̂ = +1.0`, `c = 0.60` y recibe `v̂ = +1.0`, `c = 0.80`, `from_direct_experience = True` (`γ = 0.75`, `η = 0.15`)
- **THEN** la confianza resultante es `0.636` y `evidence_count` aumenta en 1.

### Requirement: Protección Anti-Cámara de Eco (Escenario B)
Si los signos coinciden e `incoming.from_direct_experience` es falso, la confianza resultante SHALL ser `min(max(c, γc_ext), c + η_consensus·(γc_ext)·(1-c))` y `last_updated_tick` SHALL conservar el valor de la creencia local: un rumor no valida a otro rumor.

#### Scenario: Dos portadores de rumores en bucle
- **WHEN** A y B tienen `from_direct_experience = False` y `c = 0.50` sobre el mismo patrón con igual signo, e intercambian sus creencias 100 veces (`γ = 0.75`)
- **THEN** la confianza de ambos permanece en `0.50`.

#### Scenario: El rumor compartido no se exime del olvido
- **WHEN** el receptor tiene un rumor con `τ = 10` y en `t = 50` recibe un rumor del mismo signo de otro portador sin experiencia directa
- **THEN** la creencia resultante conserva `last_updated_tick = 10`, de modo que `decay_step(50, ...)` le sigue restando confianza.

#### Scenario: El consenso con evidencia directa sí valida
- **WHEN** el receptor tiene una creencia con `τ = 10` y en `t = 50` recibe una del mismo signo con `from_direct_experience = True`
- **THEN** la creencia resultante tiene `last_updated_tick = 50`.

### Requirement: Ablación de la Protección Anti-Eco
Con `anti_echo_enabled=False`, el Escenario B SHALL tratar todo testimonio como si tuviera evidencia directa: `confidence = min(1, c + η_consensus·(γc_ext)·(1-c))` y `last_updated_tick = tick`.

#### Scenario: Cámara de eco sin protección
- **WHEN** `anti_echo_enabled=False`, A y B tienen rumores con `c = 0.50` del mismo signo e intercambian sus creencias 100 veces (`γ = 0.75`, `η = 0.15`)
- **THEN** la confianza de ambos supera `0.50` y crece en cada intercambio.

### Requirement: Resistencia ante Contradicción (Escenario C)
Si los signos difieren y no corresponde sobrescritura, la función SHALL conservar el valor, el origen y el `last_updated_tick` de la creencia local y reducir su confianza a `max(0, c - η_doubt·(γc_ext)/r)`, con `r = 2.0` si la creencia local es directa y `r = 1.0` si no.

#### Scenario: Experiencia directa frente a un rumor falso
- **WHEN** el agente tiene una creencia directa `v̂ = +1.0`, `c = 0.85`, `τ = 3` y en `t = 9` recibe `v̂ = -1.0`, `c = 0.90` (`γ = 0.75`, `η_doubt = 0.20`)
- **THEN** conserva `v̂ = +1.0`, su confianza pasa a `0.7825` (por encima del umbral `0.35`) y `last_updated_tick` sigue siendo `3`.

### Requirement: Sobrescritura de Rumor Débil (Escenario C)
Si los signos difieren, la creencia local no es directa y `γc_ext > 1.2·c`, la función SHALL reemplazarla por el valor del emisor con `confidence = max(min_confidence, γc_ext - 0.5·c)`, `evidence_count = 1` y `from_direct_experience = False`.

#### Scenario: Testimonio fuerte contra un rumor viejo
- **WHEN** el agente tiene un rumor `v̂ = -1.0`, `c = 0.25` y recibe `v̂ = +1.0`, `c = 0.90` (`γ = 0.75`)
- **THEN** la creencia resultante tiene `predicted_value = +1.0` y `confidence = 0.55`.

### Requirement: Testimonio Acotado
`merge_social_belief` SHALL acotar `γ·incoming.confidence` al intervalo `[0, 1]` antes de aplicar los Escenarios A, B y C.

#### Scenario: Factor de confianza mayor que uno
- **WHEN** se invoca con `existing = None`, `incoming.confidence = 0.9` y `sender_trust_factor = 1.2`
- **THEN** la confianza resultante es `1.0`.

### Requirement: Coherencia de Patrones en la Fusión
`merge_social_belief` SHALL lanzar `ValueError` si `existing` no es `None` y su `pattern` difiere de `incoming.pattern`.

#### Scenario: Patrones distintos
- **WHEN** `existing` es una creencia sobre $\rho_1$ e `incoming` una sobre $\rho_2$
- **THEN** la función lanza `ValueError`.
