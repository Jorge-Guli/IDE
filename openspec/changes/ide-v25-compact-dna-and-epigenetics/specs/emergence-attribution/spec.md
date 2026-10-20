# Spec Delta: Emergence Attribution

## ADDED Requirements

### Requirement: Inventario de Reglas de la Fase II-B (R24 a R31)
Según el pre-registro aprobado en la tarea 0.2 (design D42), `attribution.py` SHALL definir `PHASE25_DESIGN_RULES` con `R24`..`R31`, cada una con su `name`, su `purpose` no vacío y su ablación de una bandera (`enable_compact_dna`, `enable_epigenetic_roles`, `enable_plasmid_hgt`, `enable_crispr_immunity`, `enable_sporulation`, `enable_telomere_senescence`, `enable_sos_mutation` y `enable_symbiotic_ratchet` en `False`), sin modificar `DESIGN_RULES`, `PHASE2_DESIGN_RULES` ni `ALL_DESIGN_RULES`.

#### Scenario: Inventario y ablaciones
- **WHEN** se inspecciona `PHASE25_DESIGN_RULES`
- **THEN** contiene `R24`..`R31` en orden, la ablación de `R24` es `(("enable_compact_dna", False),)`, la de `R31` es `(("enable_symbiotic_ratchet", False),)`, y `ALL_DESIGN_RULES` sigue con `R1`..`R23`.

### Requirement: Sesgos Declarados en el Propósito de las Reglas
Según el pre-registro aprobado en la tarea 0.2 (design D42), el `purpose` de `R24` SHALL declarar que abarata la complejidad latente, el de `R25` que la especialización que produzca es programada, el de `R28` que rescata poblaciones y el de `R31` que su estabilidad es por decreto.

#### Scenario: Sesgos visibles en el inventario
- **WHEN** se leen los `purpose` de `R24`, `R25`, `R28` y `R31`
- **THEN** cada uno contiene su sesgo declarado: complejidad latente, especialización programada, rescate de poblaciones y estabilidad por decreto.

### Requirement: Índice Conjunto de Reglas y Ablación
`attribution.py` SHALL definir `PHASE25_ALL_RULES = ALL_DESIGN_RULES + PHASE25_DESIGN_RULES`, y `ablate(config, rule_ids)` SHALL buscar las reglas en un índice que incluye las dos tuplas, sin modificar `ALL_DESIGN_RULES`.

#### Scenario: Ablación de reglas de las tres fases
- **WHEN** se invoca `ablate(config, ["R12", "R24", "R29"])` sobre una configuración con `enable_compact_dna=True` y `enable_telomere_senescence=True`
- **THEN** la configuración resultante tiene `reproduction_mode == "neutral"`, `enable_compact_dna == False` y `enable_telomere_senescence == False`, y `len(PHASE25_ALL_RULES) == len(ALL_DESIGN_RULES) + 8`.

### Requirement: Configuraciones de los Protocolos de la Fase II-B
Según el pre-registro aprobado en la tarea 0.2 (design D42), `PHASE25_PROTOCOL_CONFIGS` SHALL definir, sobre `PHASE2_PROTOCOL_CONFIGS`: `"002c"` como `"002a"` con `enable_compact_dna`, `enable_plasmid_hgt`, `enable_crispr_immunity` y `enable_sos_mutation`; `"002d"` como `"002c"` con `enable_telomere_senescence=True` y `resources_per_pattern=40`; y `"002e"` como `"002c"` con `enable_sporulation=True` y `resources_per_pattern=10`.

#### Scenario: Configuraciones de 002c a 002e
- **WHEN** se inspeccionan `PHASE25_PROTOCOL_CONFIGS["002c"]`, `["002d"]` y `["002e"]`
- **THEN** `002c` tiene `resources_per_pattern == 20` y las cuatro banderas en `True`; `002d` difiere de `002c` sólo en `enable_telomere_senescence=True` y `resources_per_pattern == 40`; y `002e` sólo en `enable_sporulation=True` y `resources_per_pattern == 10`.

### Requirement: Configuración del Protocolo 003c
Según el pre-registro aprobado en la tarea 0.2 (design D42), `PHASE25_PROTOCOL_CONFIGS["003c"]` SHALL ser `PHASE2_PROTOCOL_CONFIGS["003a"]` con `enable_compact_dna`, `enable_epigenetic_roles`, `enable_symbiotic_ratchet`, `enable_plasmid_hgt`, `enable_crispr_immunity` y `enable_sos_mutation` en `True`.

#### Scenario: Configuración de 003c
- **WHEN** se inspecciona `PHASE25_PROTOCOL_CONFIGS["003c"]`
- **THEN** difiere de `PHASE2_PROTOCOL_CONFIGS["003a"]` sólo en esas seis banderas, todas en `True`.

### Requirement: Afirmaciones Pre-Registradas C9 a C12
Según el pre-registro aprobado en la tarea 0.2 (design D42), `PHASE25_CLAIMS` SHALL contener `C9` (`002c`, `evolved_accuracy`), `C10` (`002d`, `evolved_accuracy`), `C11` (`002e`, `final_population`) y `C12` (`003c`, `holonic_composite_completions`), todas con métrica creciente y con $R_C$ y canal iguales a `("R24",)`, `("R29",)`, `("R28",)` y `("R25",)`, respectivamente.

#### Scenario: Registro de afirmaciones
- **WHEN** se inspecciona `PHASE25_CLAIMS`
- **THEN** contiene exactamente `C9`, `C10`, `C11` y `C12` con esos protocolos, métricas, $R_C$ y canales.

### Requirement: Variantes y Clasificación Esperable de C9 a C12
Cada afirmación de `PHASE25_CLAIMS` SHALL medirse con las variantes `isolated` (`ablate(config, R_C)`), `null_content` y `rule_effects` (una por regla ablacionable de `PHASE25_ALL_RULES` salvo las inactivas), y SHALL clasificarse con el criterio de la Fase II: por construcción si el canal no es vacío y está contenido en $R_C$.

#### Scenario: Afirmaciones programadas por construcción
- **WHEN** se clasifican `C9`..`C12` con cualquier resultado de medición
- **THEN** las cuatro se marcan programadas por construcción, porque su canal coincide con su $R_C$.

#### Scenario: Variante aislada de C9
- **WHEN** se generan las variantes de `C9` para una semilla
- **THEN** la variante `isolated` es `ablate(PHASE25_PROTOCOL_CONFIGS["002c"], ["R24"])`, con genoma plano y lo demás igual.

### Requirement: Reglas Inactivas por Protocolo de la Fase II-B
Según el pre-registro aprobado en la tarea 0.2 (design D42), `PHASE25_INACTIVE_RULES` SHALL ser `R14`–`R19`, `R22`, `R23`, `R25`, `R28`, `R29` y `R31` para `"002c"`; las de `"002c"` salvo `R29` para `"002d"`; las de `"002c"` salvo `R28` para `"002e"`; y `R14`, `R18`, `R19`, `R28` y `R29` para `"003c"`. Un test SHALL contrastarlas con las configuraciones.

#### Scenario: Coherencia con las configuraciones
- **WHEN** un test ablaciona cada regla inactiva de cada protocolo sobre su configuración de `PHASE25_PROTOCOL_CONFIGS`
- **THEN** la regla está apagada o es inerte en esa configuración, y ninguna regla inactiva recibe variante en `rule_effects`.

### Requirement: E4 Declarado de Antemano en la Fase II-B
Según el pre-registro aprobado en la tarea 0.2 (design D42), E4 SHALL declararse no interpretable de antemano para `002c`, `002e` y `003c`, e interpretable para `002d`.

#### Scenario: Interpretabilidad de E4 por protocolo
- **WHEN** se evalúan `C9`, `C10`, `C11` y `C12`
- **THEN** sólo `C10` tiene E4 interpretable; las otras tres lo informan como no interpretable, sin depender del resultado.

### Requirement: Ejecución de la Atribución de la Fase II-B
`run_phase25_attribution(seeds=PHASE2_SEEDS, claims=PHASE25_CLAIMS, jobs=1, configs=None)` SHALL devolver `AttributionReport(profile="phase2", rules=PHASE25_ALL_RULES, ...)`, con el perfil `phase2` de 2000 ticks y las semillas 42 a 51, según el pre-registro aprobado en la tarea 0.2 (design D42).

#### Scenario: Atribución con un perfil corto de prueba
- **WHEN** se invoca `run_phase25_attribution` con un perfil corto de prueba y dos semillas
- **THEN** devuelve un `AttributionReport` con `profile == "phase2"`, `rules == PHASE25_ALL_RULES` y una evaluación por afirmación de `PHASE25_CLAIMS`.

### Requirement: Prueba de Humo antes de los Runners
Antes de los runners de la Fase II-B, la prueba de humo SHALL registrar sólo si cada corrida termina, la generación máxima y la población final, sin calcular ni mirar las métricas de las afirmaciones; un protocolo inviable SHALL reportarse como resultado, sin calibración salvo con una decisión nueva.

#### Scenario: Registro de la prueba de humo
- **WHEN** se corre la prueba de humo de los cuatro protocolos
- **THEN** su registro contiene, por protocolo y semilla, sólo la terminación, la generación máxima y la población final, y ningún valor de `evolved_accuracy`, `final_population` ni `holonic_composite_completions`.
