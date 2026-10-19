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
- **THEN** cada afirmación devuelve un `float` de su métrica pre-registrada (`cultural_accuracy`, `evolved_accuracy`, `holonic_composite_completions`, `mean_acquired_orthogonalization`).

### Requirement: Criterio Ampliado de Afirmación por Construcción
Para una afirmación de Fase II, `is_by_construction` SHALL ser verdadero si su canal (`PHASE2_CLAIM_CHANNELS`) no es vacío y está contenido en sus `purpose_rules`. La variante `isolated` SHALL ser la ablación de su canal; para `C8`, la ablación de `R22`. Las reglas de `PHASE2_INACTIVE_RULES` del protocolo SHALL quedar fuera de `rule_effects`.

#### Scenario: Clasificación de C5 a C8 por construcción
- **WHEN** se evalúa `is_by_construction` sobre `C5`, `C6`, `C7` y `C8` con sus configuraciones de `PHASE2_PROTOCOL_CONFIGS`
- **THEN** es verdadero para `C5`, `C6` y `C7` y falso para `C8`, y las afirmaciones de Fase I conservan su clasificación previa.

### Requirement: Perfil Pre-Registrado de la Fase II
`attribution.py` SHALL definir `PHASE2_ATTRIBUTION_PROFILE = "phase2"` (`total_ticks = 2000`), `PHASE2_SEEDS = tuple(range(42, 52))` y `PHASE2_PROTOCOL_CONFIGS` con las configuraciones de design D29, versionados antes de implementar los runners 002 y 003.

#### Scenario: Perfil y configuraciones congelados
- **WHEN** se inspeccionan `PROFILES[PHASE2_ATTRIBUTION_PROFILE]`, `PHASE2_SEEDS` y `PHASE2_PROTOCOL_CONFIGS["003a"]`
- **THEN** `total_ticks == 2000`, hay 10 semillas de 42 a 51, y la configuración de `003a` tiene `num_composite_patterns == 3` y `composite_order == 4 > memory_capacity`.

### Requirement: Semillas sin Medición en C8
En una comparación de C8, una semilla sin `mean_acquired_orthogonalization` en alguna de las dos variantes SHALL contar como empate y listarse; con menos de `MIN_SEEDS` semillas medidas en E2, C8 SHALL ser `INSUFFICIENT_EVIDENCE`; un efecto de regla sin semillas medidas SHALL valer `None`.

#### Scenario: C8 sin holones
- **WHEN** en las 10 semillas de `phase2` ninguna corrida `full` de 003-B forma holones elegibles
- **THEN** `measure_claim` devuelve `None` para C8 en cada semilla, la evaluación es `INSUFFICIENT_EVIDENCE` (no `NOT_OBSERVED`) y ningún efecto de regla de C8 vale `0.0`.
