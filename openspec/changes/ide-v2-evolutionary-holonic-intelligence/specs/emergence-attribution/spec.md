# Spec Delta: Emergence Attribution

## ADDED Requirements

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
