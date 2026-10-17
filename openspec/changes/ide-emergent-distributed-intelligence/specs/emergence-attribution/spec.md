# Spec Delta: Emergence Attribution

## Purpose
Hacer verificable por software la regla metodológica central del proyecto: *toda propiedad que se afirme como emergente debe poder distinguirse de una capacidad programada explícitamente en el agente.* Para eso se declaran las reglas de diseño y sus propósitos, se pre-registran las afirmaciones y el perfil de corrida, se proveen ablaciones y un control nulo, y cada afirmación se clasifica automáticamente, distinguiendo lo que se decide por construcción de lo que se pone a prueba con datos.

## ADDED Requirements

### Requirement: Inventario de Presupuestos de Diseño
`src/ide/experiments/attribution.py` SHALL definir `DESIGN_RULES` con las reglas R1 a R11 de `design.md`, cada una con identificador, nombre, propósito declarado y overrides de `SimulationConfig` que la desactivan (vacíos para R1 y R2, que no son ablacionables).

#### Scenario: Reglas ablacionables
- **WHEN** se recorren las reglas de `DESIGN_RULES`
- **THEN** hay exactamente 11, sus identificadores son `R1`..`R11`, y sólo `R1` y `R2` tienen `ablation == ()`.

### Requirement: Ablación de Reglas
`ablate(config, rule_ids)` SHALL devolver una copia de la configuración con la unión de los overrides de las reglas indicadas, válida para `SimulationConfig`, y SHALL lanzar `ValueError` si alguna regla no existe o no es ablacionable.

#### Scenario: Ablación conjunta de la comunicación
- **WHEN** se invoca `ablate(SimulationConfig(), ["R8", "R9"])`
- **THEN** el resultado tiene `max_queries_per_tick == 0` y `max_broadcast_per_tick == 0`, el resto de los campos no cambia y `disables_communication(resultado)` es verdadero.

#### Scenario: Regla nuclear o inexistente
- **WHEN** se invoca `ablate(SimulationConfig(), ["R1"])` o `ablate(SimulationConfig(), ["R99"])`
- **THEN** se lanza `ValueError`.

### Requirement: Registro Pre-Declarado de Afirmaciones
El módulo SHALL definir `ATTRIBUTION_PROFILE = "quick"` y `EXP001_CLAIMS` con las afirmaciones C1 a C4 de `design.md`; las afirmaciones sobre disponibilidad o transmisión de conocimiento (C1, C2, C4) SHALL incluir R8 y R9 en $R_c$, y C3 SHALL tener $R_c$ = {R3, R4, R6, R7}.

#### Scenario: Principio conservador acotado
- **WHEN** se recorren las afirmaciones de `EXP001_CLAIMS`
- **THEN** C1, C2 y C4 incluyen `R8` y `R9` en `purpose_rules`, y C3 tiene `purpose_rules == ("R3", "R4", "R6", "R7")`.

### Requirement: Control Nulo de Contenido
`nullify_belief(belief, rng)` en `src/ide/simulation/controls.py` SHALL devolver la creencia con `predicted_value` igual a `+1.0` si `rng.random() < 0.5` y `-1.0` en otro caso, conservando el resto de los campos; con `comm_content_null=True`, el motor SHALL aplicarla a cada entrega usando un generador propio, distinto del principal.

#### Scenario: Signo aleatorio y resto intacto
- **WHEN** se aplica `nullify_belief` 1000 veces a una creencia con `predicted_value = +0.2` usando `np.random.Generator(np.random.PCG64(0))`
- **THEN** cada resultado tiene `predicted_value` en `{+1.0, -1.0}` y los demás campos iguales al original, y la fracción de positivos es `0.473`.

#### Scenario: El control no desplaza el generador principal
- **WHEN** se ejecuta el primer tick de dos motores con la misma semilla, uno con `comm_content_null=True` y otro sin él (en el tick 0 ninguna memoria tiene creencias para transmitir)
- **THEN** ambos `TickMetrics` y ambos estados del generador principal son idénticos.

### Requirement: Detección de Afirmaciones Programadas por Construcción
`disables_communication(config)` SHALL ser verdadero si `comm_enabled` es falso o si `max_queries_per_tick` y `max_broadcast_per_tick` son ambos 0; cuando `disables_communication(ablate(config, R_c))` sea verdadero, la afirmación SHALL evaluarse con `by_construction=True` y sin prueba de E3.

#### Scenario: Persistencia extra-individual
- **WHEN** se prepara la evaluación de C4, cuyo $R_c$ incluye R8 y R9
- **THEN** la evaluación tiene `by_construction == True` y `p_purpose_ablated_vs_isolated is None`.

### Requirement: Criterios de Atribución E2 a E4
`classify(claim, values, by_construction)` SHALL aplicar la prueba de signo unilateral con α = 0.05 a las diferencias por semilla, orientadas según `higher_is_better`: E2 `full` contra `isolated`; E3 `purpose_ablated` contra `isolated` (verdadero si $R_c$ es vacío; no evaluado si `by_construction`); E4 `full` contra `null_content`.

#### Scenario: Diferencias orientadas
- **WHEN** la métrica es `final_false_prevalence` (`higher_is_better = False`) y en cinco semillas `full` vale 0.1 e `isolated` vale 0.3
- **THEN** E2 se cumple con `p_vs_isolated == 0.03125`.

### Requirement: Clasificación de Afirmaciones
`classify` SHALL devolver `INSUFFICIENT_EVIDENCE` con menos de 5 semillas y, si no, en orden: `NOT_OBSERVED` si falla E2; `PROGRAMMED` si `by_construction` o falla E3; `ACTIVITY_ARTIFACT` si falla E4; y si cumple E1–E4: `EMERGENT_PENDING_ROBUSTNESS` sin E5 evaluable, `SCHEDULING_ARTIFACT` si falla E5, `EMERGENT` si la cumple.

#### Scenario: Programada por construcción
- **WHEN** en cinco semillas `full` supera a `isolated` y `by_construction` es verdadero
- **THEN** el estado es `PROGRAMMED` aunque `full` también supere a `null_content`.

#### Scenario: Propiedad que desaparece sin su regla
- **WHEN** en cinco semillas `full` supera a `isolated`, `by_construction` es falso y `purpose_ablated` iguala a `isolated`
- **THEN** el estado es `PROGRAMMED`.

#### Scenario: Propiedad que sólo se debe a la actividad
- **WHEN** en cinco semillas `full` y `purpose_ablated` superan a `isolated`, pero `full` no supera a `null_content`
- **THEN** el estado es `ACTIVITY_ARTIFACT`.

#### Scenario: Candidata sin prueba de robustez
- **WHEN** en cinco semillas `full` y `purpose_ablated` superan a `isolated`, `full` supera a `null_content` y E5 no puede evaluarse
- **THEN** el estado es `EMERGENT_PENDING_ROBUSTNESS` y `e5_evaluated` es falso.

#### Scenario: Artefacto del reloj
- **WHEN** una afirmación cumple E1–E4 pero, bajo el esquema asíncrono, `full` deja de superar a `isolated`
- **THEN** el estado es `SCHEDULING_ARTIFACT`.

#### Scenario: Pocas semillas
- **WHEN** se clasifica con tres semillas
- **THEN** el estado es `INSUFFICIENT_EVIDENCE`.

### Requirement: Perfil de Contribución de Reglas
Para cada afirmación, 001-D SHALL medir además una variante por cada regla ablacionable apagada de a una y reportar en `rule_effects` la media sobre semillas de la diferencia orientada entre `full` y esa variante.

#### Scenario: Efectos por regla
- **WHEN** se ejecuta 001-D con cinco semillas
- **THEN** cada evaluación tiene `rule_effects` con exactamente las claves `R3`..`R11`.

### Requirement: Protocolo 001-D de Atribución
`run_protocol_001d_attribution(config, seeds, claims=EXP001_CLAIMS, jobs=1)` SHALL medir cada afirmación con `ATTRIBUTION_PROFILE` en las variantes `full`, `isolated`, `purpose_ablated` (salvo por construcción o $R_c$ vacío), `null_content` y `without:<Rk>`, y devolver un `AttributionReport` con el perfil, las reglas y una `ClaimEvaluation` por afirmación.

#### Scenario: Reporte completo
- **WHEN** se ejecuta con cinco semillas y las afirmaciones por defecto
- **THEN** el reporte tiene `profile == "quick"`, cuatro evaluaciones con cinco valores por cada variante medida, C1, C2 y C4 con `by_construction == True`, y C3 con `by_construction == False`.

### Requirement: Atribución desde la CLI
La CLI SHALL aceptar `--attribution`, que ejecuta 001-D con las semillas indicadas y siempre con `ATTRIBUTION_PROFILE`, escribe `exp001_attribution.json` y muestra en consola una tabla con afirmación, estado, si es por construcción y p-valores, avisando si hay menos de 5 semillas.

#### Scenario: Ejecución con pocas semillas
- **WHEN** se ejecuta con `--seeds 42 --attribution`
- **THEN** se escribe `exp001_attribution.json` con `profile == "quick"`, todos los estados son `INSUFFICIENT_EVIDENCE` y la consola muestra el aviso.
