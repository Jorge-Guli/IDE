# Emergence Attribution Specification

## Purpose
Hacer verificable por software la regla metodológica central del proyecto: *toda propiedad que se afirme como emergente debe poder distinguirse de una capacidad programada explícitamente en el agente.* Para eso se declaran las reglas de diseño y sus propósitos, se pre-registran las afirmaciones y el perfil de corrida, se proveen ablaciones y un control nulo, y cada afirmación se clasifica automáticamente, distinguiendo lo que se decide por construcción de lo que se pone a prueba con datos.

## Requirements

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
- **THEN** ambos estados del generador principal son idénticos, y ambos `TickMetrics` coinciden en todos los campos salvo `accessible_coverage_mean`, que bajo el control nulo es por definición la cobertura individual.

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
La CLI SHALL aceptar `--attribution`, que ejecuta sólo 001-D (sin 001-A/B/C) con las semillas indicadas y siempre con `ATTRIBUTION_PROFILE`, escribe `exp001_attribution.json` y muestra en consola una tabla con afirmación, estado, si es por construcción y p-valores, avisando si hay menos de 5 semillas.

#### Scenario: Ejecución con pocas semillas
- **WHEN** se ejecuta con `--seeds 42 --attribution`
- **THEN** se escribe sólo `exp001_attribution.json`, con `profile == "quick"`, todos los estados son `INSUFFICIENT_EVIDENCE` y la consola muestra el aviso.

### Requirement: Catálogo Extendido de Reglas de Fase II (R12 a R23)
`attribution.py` SHALL mantener `DESIGN_RULES` con las 11 reglas `R1`..`R11` y definir `PHASE2_DESIGN_RULES` con `R12`..`R23` (cada una con `purpose` no vacío; `R20` nuclear, con ablación `()`) y `ALL_DESIGN_RULES = DESIGN_RULES + PHASE2_DESIGN_RULES`, de modo que `ablate(config, rule_ids)` opere sobre cualquier regla ablacionable de `ALL_DESIGN_RULES`.

#### Scenario: Preservación de DESIGN_RULES y ablación de reglas de Fase II
- **WHEN** se inspeccionan `DESIGN_RULES` y `PHASE2_DESIGN_RULES`, y se invoca `ablate(SimulationConfig(enable_evolution=True, enable_holonic_hierarchy=True), ["R12", "R22", "R23"])`
- **THEN** `DESIGN_RULES` conserva `R1`..`R11`, `PHASE2_DESIGN_RULES` contiene `R12`..`R23` en orden, y la configuración resultante tiene `reproduction_mode == "neutral"`, `enable_holon_view == False`, `holon_coord_cost == 0.0` y `holon_energy_sharing == False`.

### Requirement: Pre-Registro de Afirmaciones de Fase II (C5 a C8)
`attribution.py` SHALL definir `EXP002_CLAIMS` (`C5` en `002b`, `C6` en `002a`), `EXP003_CLAIMS` (`C7` en `003a`, `C8` en `003b`) y `PHASE2_CLAIM_CHANNELS` exactamente como en design D29, y medirlas con `measure_claim` y `run_phase2_attribution`, que usa la configuración congelada de cada protocolo y el perfil `phase2`.

#### Scenario: Medición de afirmaciones C5 a C8
- **WHEN** se invoca `measure_claim` para cada afirmación de `EXP002_CLAIMS + EXP003_CLAIMS` con un perfil de prueba corto
- **THEN** cada afirmación devuelve el valor de su métrica pre-registrada: un `float`, salvo en C8, que devuelve `float | None` (`None` si no hubo holones elegibles; la clasificación lo trata según el requisito de semillas sin medición) (`cultural_accuracy`, `evolved_accuracy`, `holonic_composite_completions`, `mean_acquired_coverage`).

### Requirement: Criterio Ampliado de Afirmación por Construcción
Para una afirmación de Fase II, `is_by_construction` SHALL ser verdadero si su canal (`PHASE2_CLAIM_CHANNELS`) no es vacío y está contenido en sus `purpose_rules`. La variante `isolated` SHALL ser la ablación de su canal; para `C8`, la ablación de `R22`. Las reglas de `PHASE2_INACTIVE_RULES` del protocolo SHALL quedar fuera de `rule_effects`.

#### Scenario: Clasificación de C5 a C8 por construcción
- **WHEN** se evalúa `is_by_construction` sobre `C5`, `C6`, `C7` y `C8` con sus configuraciones de `PHASE2_PROTOCOL_CONFIGS`
- **THEN** es verdadero para `C5`, `C6`, `C7` y `C8` (cuyo canal y $R_C$ son `("R22",)`), y las afirmaciones de Fase I conservan su clasificación previa.

### Requirement: Perfil Pre-Registrado de la Fase II
`attribution.py` SHALL definir `PHASE2_ATTRIBUTION_PROFILE = "phase2"` (`total_ticks = 2000`), `PHASE2_SEEDS = tuple(range(42, 52))`, `PHASE2_PROTOCOL_CONFIGS` y `PHASE2_PROTOCOL_CONFIGS_ORIGINAL` (las de design D29 antes de su Enmienda 1), versionados antes de implementar los runners 002 y 003.

#### Scenario: Perfil y configuraciones congelados
- **WHEN** se inspeccionan `PROFILES[PHASE2_ATTRIBUTION_PROFILE]`, `PHASE2_SEEDS` y `PHASE2_PROTOCOL_CONFIGS["003a"]`
- **THEN** `total_ticks == 2000`, hay 10 semillas de 42 a 51, y la configuración de `003a` tiene `num_composite_patterns == 3` y `composite_order == 4 > memory_capacity`.

### Requirement: Semillas sin Medición en C8
En una comparación de C8, una semilla sin `mean_acquired_coverage` en alguna de las dos variantes SHALL contar como empate y listarse; con menos de `MIN_SEEDS` semillas medidas en E2, C8 SHALL ser `INSUFFICIENT_EVIDENCE`; un efecto de regla sin semillas medidas SHALL valer `None`.

#### Scenario: C8 sin holones
- **WHEN** en las 10 semillas de `phase2` ninguna corrida `full` de 003-B forma holones elegibles
- **THEN** `measure_claim` devuelve `None` para C8 en cada semilla, la evaluación es `INSUFFICIENT_EVIDENCE` (no `NOT_OBSERVED`) y ningún efecto de regla de C8 vale `0.0`.

### Requirement: Calibración de Viabilidad del Perfil (Enmienda 1 de D29)
`phase2_calibration.py` SHALL elegir, sobre `PHASE2_PROTOCOL_CONFIGS_ORIGINAL`, el menor `resources_per_pattern` de la grilla 10, 20, 40, 80 con el que, en cada condición de comparación de los runners 002 y 003 y en su control nulo, al menos 8 de las semillas 0 a 9 siguen vivas a los 2000 ticks y llegan a la generación 5, registrando sólo demografía.

#### Scenario: Una variante de comparación inviable descarta el valor
- **WHEN** con un valor de la grilla la base de 002-A es viable en 10 semillas pero la condición `drift` sólo en 7
- **THEN** el valor no es viable, la calibración pasa al siguiente y, si ninguno lo es, `chosen is None`.

### Requirement: Registro Demográfico de las Variantes de Fase II
`ClaimEvaluation.demography` SHALL registrar, para cada variante de una afirmación de Fase II y cada semilla, la población final y la generación máxima de la corrida, y SHALL quedar vacío en Fase I.

#### Scenario: Demografía por variante
- **WHEN** se ejecuta `run_phase2_attribution` para C6 con dos semillas
- **THEN** `demography` tiene las mismas variantes que `values`, con un par `(población final, generación máxima)` por semilla, igual al de la corrida de esa variante.

### Requirement: Atribución de Referencia sobre las Configuraciones Originales
`run_phase2_attribution` SHALL aceptar `configs` y usar `configs[claim.protocol]` como población completa, para medir como referencia sobre `PHASE2_PROTOCOL_CONFIGS_ORIGINAL`.

#### Scenario: Atribución sobre otras configuraciones
- **WHEN** se invoca `run_phase2_attribution` con `configs` distintas de `PHASE2_PROTOCOL_CONFIGS`
- **THEN** el valor `full` de cada afirmación es el de su métrica medida sobre `configs[claim.protocol]` con esa semilla.

### Requirement: Grilla Refinada y Salida de Respaldo (Enmienda 1b de D29)
Si la grilla original no da un valor viable, `run_calibration` SHALL evaluar con el mismo criterio y las mismas semillas `CALIBRATION_REFINED_GRID = (25, 30, 35)` y, si tampoco hay un valor viable, SHALL registrar `fallback = CALIBRATION_FALLBACK = 20`, con E4 de C5 a C8 declarado no interpretable.

#### Scenario: Grilla refinada sin valor viable
- **WHEN** se ejecuta `run_calibration(grid=CALIBRATION_REFINED_GRID)` y ningún valor es viable
- **THEN** `chosen is None`, `grid == (25, 30, 35)` y `fallback == 20`; con la grilla original, `fallback is None`.

### Requirement: Abundancia Incorporada al Perfil (Salida de Respaldo de la Enmienda 1b)
`PHASE2_PROTOCOL_CONFIGS` SHALL ser `PHASE2_PROTOCOL_CONFIGS_ORIGINAL` con `resources_per_pattern = PHASE2_RESOURCES_PER_PATTERN = 20`, sin otro cambio.

#### Scenario: Configuraciones enmendadas
- **WHEN** se compara cada configuración de `PHASE2_PROTOCOL_CONFIGS` con la de `PHASE2_PROTOCOL_CONFIGS_ORIGINAL`
- **THEN** sólo difieren en `resources_per_pattern`, que vale 20 en las enmendadas y 8 en las originales.

### Requirement: E4 No Interpretable en la Fase II (Salida de Respaldo de la Enmienda 1b)
Toda `ClaimEvaluation` de una afirmación de Fase II medida con `resources_per_pattern = PHASE2_RESOURCES_PER_PATTERN` SHALL tener `e4_interpretable = False`, y la tabla de la CLI de atribución SHALL advertirlo; en otro caso, y en Fase I, SHALL valer `True`.

#### Scenario: Marca de E4
- **WHEN** se ejecuta `run_phase2_attribution` para C6 con las configuraciones del perfil y con las originales, y se clasifica una afirmación de Fase I
- **THEN** C6 tiene `e4_interpretable is False` con el perfil y `True` con las originales, y la de Fase I `True`.
