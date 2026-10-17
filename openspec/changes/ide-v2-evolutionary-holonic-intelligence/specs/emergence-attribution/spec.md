# Spec Delta: Emergence Attribution

## ADDED Requirements

### Requirement: Catálogo Extendido de Reglas de Fase II (R12 a R19)
`src/ide/experiments/attribution.py` SHALL mantener `DESIGN_RULES` con las 11 reglas exactas `R1`..`R11` de Fase I y definir `PHASE2_DESIGN_RULES` con las reglas `R12` a `R19` junto con `ALL_DESIGN_RULES = DESIGN_RULES + PHASE2_DESIGN_RULES`, permitiendo que `ablate(config, rule_ids)` opere sobre cualquiera de las reglas ablacionables de `ALL_DESIGN_RULES`.

#### Scenario: Preservación de DESIGN_RULES y ablación de reglas de Fase II
- **WHEN** se inspeccionan `DESIGN_RULES` y `PHASE2_DESIGN_RULES`, y se invoca `ablate(SimulationConfig(enable_evolution=True, enable_holonic_hierarchy=True), ["R13", "R15", "R18"])`
- **THEN** `DESIGN_RULES` conserva `R1`..`R11`, `PHASE2_DESIGN_RULES` contiene `R12` (reproducción), `R13` (mutación), `R14` (herencia cultural), `R15` (`BOND`), `R16` (`SPLIT`), `R17` (reproducción de holón), `R18` (causalidad descendente) y `R19` (estigmergia), y la configuración ablacionada desactiva `R13`, `R15` y `R18`.

### Requirement: Pre-Registro de Afirmaciones de Fase II (C5 a C8)
`src/ide/experiments/attribution.py` SHALL definir `EXP002_CLAIMS` (`C5` sobre protocolo `002b`; `C6` sobre protocolo `002a`) y `EXP003_CLAIMS` (`C7` sobre protocolo `003a`; `C8` sobre protocolo `003b`), permitiendo evaluar su atribución con `measure_claim` y `run_protocol_001d_attribution`.

#### Scenario: Medición de afirmaciones C5 a C8 en el marco de atribución
- **WHEN** se invoca `measure_claim` para cada afirmación en `EXP002_CLAIMS + EXP003_CLAIMS` con un perfil de prueba corto
- **THEN** cada afirmación devuelve un `float` válido correspondiente a su métrica y protocolo pre-registrados (`C5`: aceleración cultural, `C6`: adaptación de linajes, `C7`: superávit cooperativo, `C8`: ganancia holónica M11).
