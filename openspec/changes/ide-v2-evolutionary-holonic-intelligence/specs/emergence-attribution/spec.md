# Spec Delta: Emergence Attribution

## ADDED Requirements

### Requirement: Catálogo Extendido de Reglas de Fase II (R12 a R19)
`src/ide/experiments/attribution.py` SHALL mantener `DESIGN_RULES` con las 11 reglas exactas `R1`..`R11` del Experimento 001 y definir `PHASE2_DESIGN_RULES` con las reglas `R12` (Reproducción diferencial por umbral energético), `R13` (Mutación genética acotada), `R14` (Herencia cultural vertical madre-hijo), `R15` (Fusión holónica `BOND`), `R16` (Fisión holónica `SPLIT`), `R17` (Reproducción simbiótica de holón completo), `R18` (Causalidad descendente y particionamiento epigenético intra-holón) y `R19` (Estigmergia y construcción de nicho espacial), además de `ALL_DESIGN_RULES = DESIGN_RULES + PHASE2_DESIGN_RULES`, permitiendo que `ablate(config, rule_ids)` opere sobre cualquiera de las reglas ablacionables de `ALL_DESIGN_RULES`.

#### Scenario: Preservación de DESIGN_RULES y ablación de reglas de Fase II
- **WHEN** se inspeccionan `DESIGN_RULES` y `PHASE2_DESIGN_RULES`, y se invoca `ablate(SimulationConfig(enable_evolution=True, enable_holonic_hierarchy=True), ["R13", "R15", "R18"])`
- **THEN** `DESIGN_RULES` sigue teniendo exactamente `R1`..`R11`, `PHASE2_DESIGN_RULES` tiene exactamente `R12`..`R19`, y la configuración ablacionada desactiva la mutación genética, la fusión holónica y la causalidad descendente.

### Requirement: Pre-Registro de Afirmaciones de Fase II (C5 a C8)
`src/ide/experiments/attribution.py` SHALL definir `EXP002_CLAIMS` (`C5`: Aceleración cultural intergeneracional en protocolo `002b`; `C6`: Adaptación evolutiva de linajes en protocolo `002a`) y `EXP003_CLAIMS` (`C7`: Superávit cooperativo sobre recursos compuestos en protocolo `003a`; `C8`: Ortogonalización espontánea y ganancia de capacidad efectiva intra-holón en protocolo `003b`), permitiendo evaluar su atribución con `measure_claim` y `run_protocol_001d_attribution`.

#### Scenario: Medición de afirmaciones C5 a C8 en el marco de atribución
- **WHEN** se invoca `measure_claim` para cada afirmación en `EXP002_CLAIMS + EXP003_CLAIMS` con un perfil de prueba corto
- **THEN** cada afirmación devuelve un `float` válido correspondiente a su métrica y protocolo pre-registrados.
