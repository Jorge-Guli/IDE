# Spec Delta: Emergence Attribution

## Purpose
Hacer verificable por software la regla metodológica central del proyecto: *toda propiedad que se afirme como emergente debe poder distinguirse de una capacidad programada explícitamente en el agente.* Para eso se declaran las reglas de diseño y sus propósitos, se pre-registran las afirmaciones, se proveen ablaciones y un control nulo, y cada afirmación se clasifica automáticamente.

## ADDED Requirements

### Requirement: Inventario de Presupuestos de Diseño
`src/ide/experiments/attribution.py` SHALL definir `DESIGN_RULES` con las reglas R1 a R11 de `design.md`, cada una con identificador, nombre, propósito declarado y overrides de `SimulationConfig` que la desactivan (vacíos para R1 y R2, que no son ablacionables).

#### Scenario: Reglas ablacionables
- **WHEN** se recorren las reglas de `DESIGN_RULES`
- **THEN** hay exactamente 11, sus identificadores son `R1`..`R11`, y sólo `R1` y `R2` tienen `ablation == ()`.

### Requirement: Ablación de Reglas
`ablate(config, rule_ids)` SHALL devolver una copia de la configuración con la unión de los overrides de las reglas indicadas, y SHALL lanzar `ValueError` si alguna regla no existe o no es ablacionable.

#### Scenario: Ablación conjunta de la comunicación
- **WHEN** se invoca `ablate(SimulationConfig(), ["R8", "R9"])`
- **THEN** el resultado tiene `max_queries_per_tick == 0` y `max_broadcast_per_tick == 0`, y el resto de los campos no cambia.

#### Scenario: Regla nuclear
- **WHEN** se invoca `ablate(SimulationConfig(), ["R1"])`
- **THEN** se lanza `ValueError`.

### Requirement: Registro Pre-Declarado de Afirmaciones
El módulo SHALL definir `EXP001_CLAIMS` con las afirmaciones C1 a C4 de `design.md`, cada una con protocolo, métrica, dirección y el conjunto $R_c$ de reglas cuyo propósito la produce; toda afirmación sobre conocimiento compartido SHALL incluir R8 y R9 en $R_c$.

#### Scenario: Principio conservador de la comunicación
- **WHEN** se recorren las afirmaciones de `EXP001_CLAIMS`
- **THEN** cada una incluye `R8` y `R9` en `purpose_rules`.

### Requirement: Control Nulo de Contenido
Con `comm_content_null=True`, el motor SHALL entregar cada creencia transmitida transformada por `nullify_belief(belief, rng)`, que reemplaza el signo de `predicted_value` por uno aleatorio y conserva magnitud, patrón, confianza, evidencia, τ y origen, sin alterar el número de mensajes.

#### Scenario: Signo aleatorio y resto intacto
- **WHEN** se aplica `nullify_belief` 1000 veces a una creencia con `predicted_value = +1.0` usando un generador sembrado
- **THEN** cada resultado difiere del original sólo en el signo de `predicted_value`, y la fracción de resultados positivos está en `[0.45, 0.55]`.

#### Scenario: Volumen de mensajes conservado
- **WHEN** se ejecuta un tick desde el mismo estado inicial, con y sin `comm_content_null`
- **THEN** `messages_sent` es igual en ambos.

### Requirement: Criterios de Atribución E2 a E4
`classify(claim, values)` SHALL aplicar la prueba de signo unilateral con α = 0.05 a las diferencias por semilla, orientadas según `higher_is_better`: E2 `full` contra `isolated`; E3 `purpose_ablated` contra `isolated` (verdadero si $R_c$ es vacío); E4 `full` contra `null_content`.

#### Scenario: Diferencias orientadas
- **WHEN** la métrica es `final_false_prevalence` (`higher_is_better = False`) y en cinco semillas `full` vale 0.1 e `isolated` vale 0.3
- **THEN** E2 se cumple con `p_vs_isolated == 0.03125`.

### Requirement: Clasificación de Afirmaciones
`classify` SHALL devolver `INSUFFICIENT_EVIDENCE` con menos de 5 semillas y, si no, en este orden: `NOT_OBSERVED` si falla E2; `PROGRAMMED` si falla E3; `ACTIVITY_ARTIFACT` si falla E4; `EMERGENT` en otro caso.

#### Scenario: Propiedad que desaparece sin su regla
- **WHEN** en cinco semillas `full` supera a `isolated`, pero `purpose_ablated` iguala a `isolated`
- **THEN** el estado es `PROGRAMMED`.

#### Scenario: Propiedad que sólo se debe a la actividad
- **WHEN** en cinco semillas `full` y `purpose_ablated` superan a `isolated`, pero `full` no supera a `null_content`
- **THEN** el estado es `ACTIVITY_ARTIFACT`.

#### Scenario: Pocas semillas
- **WHEN** se clasifica con tres semillas
- **THEN** el estado es `INSUFFICIENT_EVIDENCE`.

### Requirement: Protocolo 001-D de Atribución
`run_protocol_001d_attribution(config, seeds, claims=EXP001_CLAIMS, profile="quick")` SHALL medir cada afirmación en las variantes `full`, `isolated`, `purpose_ablated` y `null_content` para cada semilla mediante `measure_claim`, y devolver un `AttributionReport` con las reglas y una `ClaimEvaluation` por afirmación.

#### Scenario: Reporte completo
- **WHEN** se ejecuta con cinco semillas y las afirmaciones por defecto
- **THEN** el reporte contiene cuatro evaluaciones, cada una con cinco valores por variante y un estado de `ClaimStatus`.

### Requirement: Atribución desde la CLI
La CLI SHALL aceptar `--attribution`, que ejecuta 001-D con las semillas indicadas, escribe `exp001_attribution.json` y muestra en consola una tabla con afirmación, estado y p-valores, avisando si hay menos de 5 semillas.

#### Scenario: Ejecución con pocas semillas
- **WHEN** se ejecuta `--profile quick --seeds 42 --attribution`
- **THEN** se escribe `exp001_attribution.json`, todos los estados son `INSUFFICIENT_EVIDENCE` y la consola muestra el aviso.
