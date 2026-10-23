# Spec Delta: Emergence Attribution

## ADDED Requirements

### Requirement: Inventario de Reglas de la Fase II-B (R24 a R41)
Según el pre-registro aprobado en la tarea 0.5 (design D56, reabierto con D57–D63), `attribution.py` SHALL definir `PHASE25_DESIGN_RULES` con `R24`..`R41` en orden, cada una con el `name`, el `purpose` no vacío y la ablación de una bandera en `False` de la tabla de D56, sin modificar `DESIGN_RULES`, `PHASE2_DESIGN_RULES` ni `ALL_DESIGN_RULES`.

#### Scenario: Inventario y ablaciones
- **WHEN** se inspecciona `PHASE25_DESIGN_RULES`
- **THEN** contiene `R24`..`R41` en orden; las ablaciones de `R24`, `R28`, `R32`, `R37` y `R38` son `(("enable_compact_dna", False),)`, `(("enable_sporulation", False),)`, `(("enable_genetic_policy", False),)`, `(("enable_predation", False),)` y `(("enable_recombination", False),)`; y `ALL_DESIGN_RULES` sigue con `R1`..`R23`.

#### Scenario: Ablaciones de las reglas ecológicas
- **WHEN** se inspeccionan las ablaciones de `R33`, `R34`, `R35` y `R36`
- **THEN** son `(("enable_resource_depletion", False),)`, `(("enable_heterogeneity", False),)`, `(("enable_carcasses", False),)` y `(("enable_energy_transfer", False),)`.

#### Scenario: Ablaciones de la ampliación
- **WHEN** se inspeccionan las ablaciones de `R39`, `R40` y `R41`
- **THEN** son `(("enable_internal_state", False),)`, `(("enable_plasticity", False),)` y `(("enable_signals", False),)`, y sus `name` son "Estado interno persistente", "Plasticidad en vida" y "Señales evolucionables".

### Requirement: Sesgos Declarados en el Propósito de las Reglas
Según el pre-registro aprobado en la tarea 0.5 (design D56), el `purpose` de `R24` SHALL declarar que abarata la complejidad latente y el de `R29` que fuerza el recambio; los de `R25`, `R28`, `R36`, `R37`, `R38`, `R39`, `R40` y `R41` SHALL declarar que su uso (y, en `R40`, qué y cuánto se aprende; en `R41`, su significado) lo decide el ADN o lo construye la evolución, y ninguno SHALL declarar especialización programada, rescate de poblaciones ni estabilidad por decreto.

#### Scenario: Sesgos vigentes
- **WHEN** se leen los `purpose` de `R24` y `R29`
- **THEN** contienen sus sesgos declarados: complejidad latente y recambio forzado.

#### Scenario: Sesgos retirados por la reformulación
- **WHEN** se leen los `purpose` de `R25`, `R28` y `R31`
- **THEN** ninguno menciona especialización programada, rescate de poblaciones ni estabilidad por decreto, y los de `R25` y `R28` dicen que su uso lo decide el ADN.

#### Scenario: Capacidades de la ampliación
- **WHEN** se leen los `purpose` de `R39`, `R40` y `R41`
- **THEN** el de `R39` dice que su uso lo decide el ADN, el de `R40` que qué y cuánto se aprende lo decide el ADN, y el de `R41` que su uso y su significado los construye la evolución.

### Requirement: Índice Conjunto de Reglas y Ablación
`attribution.py` SHALL definir `PHASE25_ALL_RULES = ALL_DESIGN_RULES + PHASE25_DESIGN_RULES`, y `ablate(config, rule_ids)` SHALL buscar las reglas en las dos tuplas, sin modificar `ALL_DESIGN_RULES`.

#### Scenario: Ablación de reglas de las tres fases
- **WHEN** se invoca `ablate(config, ["R12", "R24", "R37", "R39", "R40"])` sobre una configuración con `enable_compact_dna=True`, `enable_predation=True`, `enable_internal_state=True` y `enable_plasticity=True`
- **THEN** la configuración resultante tiene `reproduction_mode == "neutral"` y `enable_compact_dna`, `enable_predation`, `enable_internal_state` y `enable_plasticity` en `False`, y `len(PHASE25_ALL_RULES) == len(ALL_DESIGN_RULES) + 18`.

### Requirement: Configuración del Protocolo 25a
Según el pre-registro aprobado en la tarea 0.5 (design D56), `PHASE25_PROTOCOL_CONFIGS["25a"]` SHALL ser `PHASE2_PROTOCOL_CONFIGS["002a"]` con `enable_` `compact_dna`, `genetic_policy`, `plasmid_hgt`, `crispr_immunity`, `sporulation`, `telomere_senescence`, `sos_mutation`, `resource_depletion`, `heterogeneity`, `carcasses`, `energy_transfer`, `predation`, `recombination`, `internal_state`, `plasticity` y `signals` en `True`, `season_length = 500` y `dna_max_length = 64` (D62.2).

#### Scenario: Configuración de 25a
- **WHEN** se compara `PHASE25_PROTOCOL_CONFIGS["25a"]` con `PHASE2_PROTOCOL_CONFIGS["002a"]`
- **THEN** difieren sólo en esas 16 banderas, todas en `True`, en `season_length == 500`, en `dna_max_length == 64` y en `(resources_per_pattern, resource_regen_delay)`, fijados por la compuerta de viabilidad.

### Requirement: Configuraciones de los Protocolos 25b, 25c y 25d
Según el pre-registro aprobado en la tarea 0.5 (design D56), `PHASE25_PROTOCOL_CONFIGS["25b"]` SHALL ser `PHASE2_PROTOCOL_CONFIGS["003a"]` con las banderas, la `season_length` y la `dna_max_length` de `"25a"` más `enable_epigenetic_roles` y `enable_symbiotic_ratchet` en `True`; `["25c"]` SHALL ser `"25a"` con `comm_propensity_base = 0.0`; y `["25d"]` SHALL ser `"25a"` con `world_shift_period = 1000` y `world_shift_fraction = 0.5` (D62.1).

#### Scenario: Configuración de 25b
- **WHEN** se compara `PHASE25_PROTOCOL_CONFIGS["25b"]` con `PHASE2_PROTOCOL_CONFIGS["003a"]`
- **THEN** difieren sólo en las 16 banderas de `25a`, `enable_epigenetic_roles`, `enable_symbiotic_ratchet`, `season_length == 500`, `dna_max_length == 64` y los dos valores de la compuerta.

#### Scenario: Configuración de 25c
- **WHEN** se compara `PHASE25_PROTOCOL_CONFIGS["25c"]` con `["25a"]`
- **THEN** difieren sólo en `comm_propensity_base == 0.0`.

#### Scenario: Configuración de 25d
- **WHEN** se compara `PHASE25_PROTOCOL_CONFIGS["25d"]` con `["25a"]`
- **THEN** difieren sólo en `world_shift_period == 1000`, y `25d` tiene `world_shift_fraction == 0.5`.

#### Scenario: ADN de 64 codones en todos los protocolos
- **WHEN** se inspecciona `dna_max_length` en los cuatro protocolos de `PHASE25_PROTOCOL_CONFIGS` y en `SimulationConfig()`
- **THEN** vale 64 en los cuatro protocolos y 32 en la configuración por defecto.

### Requirement: Abundancia Fijada por la Compuerta de Viabilidad
`resources_per_pattern` y `resource_regen_delay` de los cuatro protocolos de `PHASE25_PROTOCOL_CONFIGS` SHALL ser los de la configuración elegida por la compuerta de viabilidad (design D55), fijados en un commit propio antes de la prueba de humo; ningún otro campo SHALL ajustarse con la compuerta.

#### Scenario: Valores comunes a los protocolos
- **WHEN** la compuerta elige `(30, 10)`
- **THEN** `25a`, `25b`, `25c` y `25d` tienen `resources_per_pattern == 30` y `resource_regen_delay == 10`, y el resto de sus campos es el del pre-registro.

### Requirement: Tipo Phase25Claim
`attribution.py` SHALL definir `Phase25Claim` como `@dataclass(frozen=True)` con `claim_id`, `statement`, `protocol`, `metric`, `comparison` (`"drift"`, `"no_predation"`, `"stable"` o `"no_learning"`), `rule_ids`, `channel`, `delta_min`, `delta_relative: float = 0.0`, `baseline_drift: str | None = None` y `comparison_drift: str | None = None`, en ese orden, y `PHASE25_CLAIMS` SHALL ser una tupla de `Phase25Claim` (design D56 y precisión 50).

#### Scenario: Campos de la afirmación
- **WHEN** se inspeccionan los campos de `Phase25Claim`
- **THEN** son exactamente esos once, `delta_relative` vale 0.0 y `baseline_drift` y `comparison_drift` valen `None` por defecto, y asignar uno lanza `dataclasses.FrozenInstanceError`.

### Requirement: Tipos de Evaluación y Reporte de la Fase II-B
`Phase25ClaimEvaluation` SHALL ser `frozen` con `claim_id`, `status`, `p_value`, `p_adjusted`, `median_difference`, `values`, `comparison_values`, `demography`, `e4_p_value`, `e4_interpretable` y, al final y en este orden, `excluded_seeds: tuple[int, ...]`, `excluded_pairs: int`, `evaluable: bool` y `joint_median` (design precisiones 45 y 47, D72.2); `Phase25Report` SHALL ser `frozen` con `profile = "phase25"`, `rules = PHASE25_ALL_RULES`, `evaluations` y `rule_effects`.

#### Scenario: Campos de la evaluación y del reporte
- **WHEN** se inspeccionan los campos de `Phase25ClaimEvaluation` y de `Phase25Report`
- **THEN** son exactamente los enumerados, en ese orden, y los dos tipos son inmutables.

### Requirement: Campo joint_median de la Evaluación
El último campo de `Phase25ClaimEvaluation` SHALL ser `joint_median: float | None = None`: SHALL valer `None` en toda evaluación de `PHASE25_CLAIMS` y en las de `PHASE25_SHADOW_CLAIMS` sin `joint_real_comparison`, y SHALL NOT cambiar ningún otro valor de la atribución de D56 (design D72.2).

#### Scenario: D56 con joint_median nulo
- **WHEN** se corre `run_phase25_attribution` con un perfil corto y dos semillas
- **THEN** `joint_median` vale `None` en todas las evaluaciones y los demás campos son los de antes del cambio.

### Requirement: Ejecución de la Atribución de la Fase II-B
`run_phase25_attribution(seeds=PHASE25_SEEDS, claims=PHASE25_CLAIMS, jobs=1, configs=None, rule_effect_seeds=PHASE25_RULE_EFFECT_SEEDS)` SHALL devolver un `Phase25Report` con `PROFILES["phase25"]`, una evaluación por afirmación y, con `configs`, SHALL usar `configs[claim.protocol]` como condición `full`.

#### Scenario: Atribución con un perfil corto de prueba
- **WHEN** se invoca `run_phase25_attribution` con un perfil corto de prueba, dos semillas y `rule_effect_seeds` de una semilla
- **THEN** devuelve un `Phase25Report` con `profile == "phase25"`, `rules == PHASE25_ALL_RULES` y una evaluación por afirmación de `PHASE25_CLAIMS`.

### Requirement: Control Nulo de Contenido de la Fase II-B
La condición `null_content` SHALL aleatorizar el contenido de las creencias en todos los canales epistémicos, como en la Fase II (mensajes, estigmergia, herencia cultural y vista del holón), sin alterar el ADN, los plásmidos, la política ni la puerta de comunicación.

#### Scenario: Genética intacta en el control nulo
- **WHEN** se compara la configuración `null_content` de `25a` con la `full`
- **THEN** difieren sólo en la aleatorización de contenido, y el ADN fundador, la política genética y `comm_propensity_base` son los mismos.

### Requirement: Afirmaciones Pre-Registradas C13 a C15
Según el pre-registro aprobado en la tarea 0.5 (design D56), `PHASE25_CLAIMS` SHALL contener, con métrica creciente, $R_C$ `("R12",)`, canal `()` y comparación `full` frente a `drift`: `C13` (`25a`, `mean_conditional_codons`, $\delta_{\min} = 1.0$), `C14` (`25a`, `policy_divergence`, $0.05$) y `C15` (`25c`, `communicating_fraction`, $0.10$), las tres con `delta_relative = 0.0`.

#### Scenario: Registro de C13 a C15
- **WHEN** se inspeccionan `C13`, `C14` y `C15` en `PHASE25_CLAIMS`
- **THEN** tienen esos protocolos, métricas, comparaciones, $R_C$, canales y $\delta_{\min}$, `delta_relative == 0.0` y métrica creciente.

### Requirement: Afirmaciones Pre-Registradas C16 a C18
Según el pre-registro aprobado en la tarea 0.5 (design D56), `PHASE25_CLAIMS` SHALL contener, crecientes y con canal `()`: `C16` (`25a`, `new_activity_per_birth`, frente a `drift`, $R_C$ `("R12",)`, $\delta_{\min} = 0.001$, `delta_relative = 0.25`), `C17` (`25a`, `mean_expressible_nonattack_codons`, frente a `no_predation`, `("R37",)`, $1.0$) y `C18` (`25b`, `share_rate`, frente a `drift`, `("R12",)`, $0.01$), éstas con `delta_relative = 0.0`; ninguna más salvo `C13`–`C15`, `C19` y `C20`.

#### Scenario: Registro de C16 a C18
- **WHEN** se inspecciona `PHASE25_CLAIMS`
- **THEN** contiene exactamente `C13`..`C20`, y `C16`, `C17` y `C18` tienen esos protocolos, métricas, comparaciones, $R_C$, canales, $\delta_{\min}$ y `delta_relative`.

#### Scenario: C17 por diferencia de diferencias
- **WHEN** se evalúa `C17`
- **THEN** su comparación con `no_predation` sigue el requisito "Diferencia de Diferencias de C17 y C19", no la diferencia simple.

#### Scenario: Enunciado de C18
- **WHEN** se lee el `statement` de `C18`
- **THEN** es "La cooperación material evoluciona en la ecología holónica".

### Requirement: Cesiones Contadas por C18
La métrica de `C18`, `share_rate`, SHALL contar cada `SHARE` ejecutado, sea o no entre hojas del mismo holón: la afirmación mide la cooperación material en la ecología holónica, no sólo dentro de los holones (design D56).

#### Scenario: Cesión fuera del holón
- **WHEN** en un tick de `25b` con 20 decisiones se ejecutan un `SHARE` entre hojas del mismo holón y otro entre hojas de holones distintos
- **THEN** `shares == 2` y `share_rate == pytest.approx(0.1, abs=1e-9)`.

### Requirement: Diferencia de Diferencias de C17 y C19
`C17` SHALL tener `baseline_drift == "drift"` y `comparison_drift == "no_predation_drift"`, y `C19` `"drift"` y `"stable_drift"`; las demás afirmaciones SHALL tener los dos en `None`. Con los dos distintos de `None`, la diferencia de la semilla $s$ SHALL ser $[\text{full}(s) - \text{drift}(s)] - [\text{comp}(s) - \text{comp\_drift}(s)]$; si no, $\text{full}(s) - \text{comp}(s)$ (design D56).

#### Scenario: Diferencia de C17
- **WHEN** en una semilla `full`, `drift`, `no_predation` y `no_predation_drift` valen 9.0, 6.0, 7.0 y 5.5
- **THEN** la diferencia de `C17` en esa semilla es `pytest.approx(1.5, abs=1e-9)`.

#### Scenario: Diferencia simple
- **WHEN** se inspeccionan `C13`..`C16`, `C18` y `C20`
- **THEN** `baseline_drift is None` y `comparison_drift is None`, y su diferencia es `full(s) - comp(s)`.

### Requirement: Valores Informados en la Diferencia de Diferencias
En `C17` y `C19`, `values` SHALL guardar por semilla $\text{full}(s) - \text{drift}(s)$ y `comparison_values` $\text{comp}(s) - \text{comp\_drift}(s)$, de modo que la diferencia pareada sea siempre `values[s] - comparison_values[s]` (design precisión 69).

#### Scenario: Valores de C19
- **WHEN** en una semilla `full`, `drift`, `stable` y `stable_drift` valen 4.0, 1.0, 2.0 y 1.0 en `mean_learning_codons`
- **THEN** `values` vale 3.0 y `comparison_values` vale 1.0 en esa semilla, y su diferencia es 2.0.

### Requirement: Afirmación Pre-Registrada C19
Según el pre-registro de design D56 (reabierto con D57–D63), `PHASE25_CLAIMS` SHALL contener `C19` "La memoria y el aprendizaje evolucionan cuando el entorno cambia", genuina, con protocolo `25d`, métrica creciente `mean_learning_codons` (D63.2), comparación `stable` por diferencia de diferencias contra su reproducción neutral (requisito "Diferencia de Diferencias de C17 y C19"), $R_C$ `()`, canal `()`, $\delta_{\min} = 1.0$ y `delta_relative = 0.0`.

#### Scenario: Registro de C19
- **WHEN** se inspecciona `C19` en `PHASE25_CLAIMS`
- **THEN** tiene `protocol == "25d"`, `metric == "mean_learning_codons"`, `comparison == "stable"`, `baseline_drift == "drift"`, `comparison_drift == "stable_drift"`, `rule_ids == ()`, `channel == ()`, `delta_min == 1.0` y `delta_relative == 0.0`.

### Requirement: Afirmación Funcional C20
Según el pre-registro de design D56, `PHASE25_CLAIMS` SHALL contener `C20` "La memoria y la plasticidad aceleran la recuperación tras un cambio del entorno", con protocolo `25d`, métrica creciente `post_shift_accuracy`, comparación `full` frente a `no_learning`, $R_C$ y canal `("R39", "R40")`, $\delta_{\min} = 0.02$ y `delta_relative = 0.0`; es funcional y no genuina: verifica que la capacidad sirve, como C1 y C2.

#### Scenario: Registro de C20
- **WHEN** se inspecciona `C20` en `PHASE25_CLAIMS`
- **THEN** tiene `protocol == "25d"`, `metric == "post_shift_accuracy"`, `comparison == "no_learning"`, `rule_ids == ("R39", "R40")`, `channel == ("R39", "R40")`, `delta_min == 0.02` y `delta_relative == 0.0`.

### Requirement: Estado de C20
Como no entra en Holm, `C20` SHALL ser `OBSERVED` si el p-valor **crudo** de la prueba de signo sobre sus pares válidos es menor que 0.05 y la mediana de sus diferencias pareadas es al menos $\delta_{\min} = 0.02$, y `NOT_OBSERVED` en otro caso; SHALL clasificarse programada por construcción y SHALL NOT recorrer la escalera E1–E5 (design precisión 53).

#### Scenario: Significativa sin corrección
- **WHEN** `C20` tiene p-valor crudo 0.03 y mediana de diferencias 0.05
- **THEN** su estado es `OBSERVED`, sin ajuste de Holm, y la evaluación no contiene pasos E1–E5.

#### Scenario: Efecto menor que el umbral
- **WHEN** `C20` tiene p-valor crudo 0.001 y mediana de diferencias 0.01
- **THEN** su estado es `NOT_OBSERVED`.

### Requirement: Exactitud tras los Cambios del Entorno
`post_shift_accuracy` SHALL ser la suma de `correct_decisions` dividida por la suma de `decision_opportunities` de `ecology_history` en las ventanas $[s, s + 200)$ de cada cambio del entorno en el tick $s$, sobre todos los cambios de la corrida, o 0.0 sin oportunidades en esas ventanas (design D56, D63.4 y precisión 63).

#### Scenario: Ventanas de dos cambios
- **WHEN** una corrida de 2500 ticks con `world_shift_period = 1000` registra 10 oportunidades y 6 aciertos en cada tick de 1000 a 1199 y de 2000 a 2199, y 10 oportunidades y 10 aciertos en los demás, incluidos los ticks 1200 y 2200
- **THEN** `post_shift_accuracy == pytest.approx(0.6, abs=1e-9)`, porque la ventana de un cambio en el tick $s$ es $[s, s + 200)$ (design precisión 63).

#### Scenario: Sin cambios del entorno
- **WHEN** la corrida tiene `world_shift_period = 0`
- **THEN** `post_shift_accuracy == 0.0`.

### Requirement: Métrica de Ventana Final
La métrica de cada afirmación de `PHASE25_CLAIMS` SHALL ser la media de su campo de `GeneticTickMetrics` o `EcologyTickMetrics` sobre la ventana final, los últimos `min(total_ticks, PHASE25_FINAL_WINDOW)` ticks con `PHASE25_FINAL_WINDOW = 1000` (un ciclo estacional), salvo `C16`, que SHALL usar `new_activity_per_birth` del último tick (precisión 43), y `C20`, que SHALL usar `post_shift_accuracy` (design D56 y precisión 4).

#### Scenario: Ventana del perfil phase25
- **WHEN** se mide `C13` en una corrida de 5000 ticks con `season_length = 500`
- **THEN** su valor es la media de `mean_conditional_codons` en los últimos 1000 registros de `engine.genetic_history`, que cubren 500 ticks de verano y 500 de invierno.

#### Scenario: Ventana de 25d tras un cambio del entorno
- **WHEN** se mide `C19` en una corrida de 5000 ticks de `25d` con `world_shift_period = 1000`
- **THEN** la ventana son los ticks 4000 a 4999, que empiezan con el cambio del tick 4000 en `full` y `drift` (design precisiones 4 y 56).

#### Scenario: Actividad en el último tick
- **WHEN** se mide `C16` en una corrida de 5000 ticks
- **THEN** su valor es `new_activity_per_birth` del último registro, no una media.

#### Scenario: Ventana de perfiles cortos
- **WHEN** se mide `C14` en corridas de 45 y de 1500 ticks
- **THEN** la ventana es de los 45 registros y de los últimos 1000, respectivamente.

### Requirement: Clasificación No Programada de C13 a C19
Como su canal es vacío, `_phase25_by_construction` SHALL ser falso para `C13`..`C19`, y ninguna SHALL clasificarse programada por construcción.

#### Scenario: Canal vacío
- **WHEN** se evalúa `_phase25_by_construction` sobre `C13`..`C19`
- **THEN** es falso para las siete, y las afirmaciones de las Fases I y II conservan su clasificación previa.

### Requirement: C20 Programada por Construcción y Fuera de Holm
Como su canal `("R39", "R40")` coincide con su $R_C$, `C20` SHALL clasificarse programada por construcción (`_phase25_by_construction` verdadero) y SHALL NOT entrar en la corrección de Holm–Bonferroni; su evaluación se informa sin presentarse como resultado genuino (design D56).

#### Scenario: Clasificación de C20
- **WHEN** se evalúa `_phase25_by_construction` sobre `C20`
- **THEN** es verdadero.

#### Scenario: Holm sin C20
- **WHEN** se cambia el p-valor crudo de `C20` de 0.001 a 0.9, con los de `C13`..`C19` fijos
- **THEN** los p-valores ajustados de `C13`..`C19` no cambian.

### Requirement: Prueba de Signo Pareada de la Fase II-B
Para cada afirmación de `PHASE25_CLAIMS`, el p-valor crudo SHALL ser el de una prueba de signo unilateral (`sign_test_p_value`) sobre las diferencias pareadas por semilla (simples, o de diferencias en `C17` y `C19`), sólo en los pares válidos y descartando los empates.

#### Scenario: Diferencias con empates
- **WHEN** sobre 30 pares válidos hay 20 diferencias positivas, 5 negativas y 5 nulas
- **THEN** el p-valor crudo es `pytest.approx(0.0020386576652526855, abs=1e-9)`, calculado con $n = 25$.

### Requirement: Pares Válidos de la Fase II-B
Un par (semilla) de una afirmación de `PHASE25_CLAIMS` SHALL ser válido si todas las condiciones de su diferencia (dos, o cuatro en `C17` y `C19`) terminan con al menos una hoja activa (`final_active_agents >= 1`); los demás SHALL excluirse de la prueba de signo y de la mediana, y sus semillas SHALL informarse en `excluded_seeds`, con `excluded_pairs == len(excluded_seeds)` (design precisiones 45 y 47).

#### Scenario: Extinción en una condición
- **WHEN** en `C14` la condición `drift` de la semilla 50 termina sin hojas activas y las demás 29 semillas terminan con hojas activas en `full` y en `drift`
- **THEN** la prueba de signo y la mediana usan 29 pares, `excluded_seeds == (50,)` y `excluded_pairs == 1`.

#### Scenario: Extinción en una condición neutral de la diferencia de diferencias
- **WHEN** en `C17` la condición `no_predation_drift` de la semilla 47 termina sin hojas activas y las cuatro condiciones de las demás 29 semillas terminan con hojas activas
- **THEN** la semilla 47 se excluye, `excluded_seeds == (47,)` y la prueba usa 29 pares.

### Requirement: Afirmación No Evaluable
Si una afirmación de `PHASE25_CLAIMS` tiene menos de 20 pares válidos, SHALL quedar `NOT_OBSERVED` con `evaluable = False` y SHALL seguir contando, si es genuina (`C13`..`C19`), en la corrección de Holm con $m = 7$, con el p-valor de la prueba de signo sobre sus pares válidos; con 20 o más, `evaluable` SHALL ser `True` (design D56 y precisiones 45 y 48).

#### Scenario: Demasiadas extinciones
- **WHEN** `C18` tiene 19 pares válidos y una mediana de diferencias de 0.05
- **THEN** su estado es `NOT_OBSERVED`, `evaluable == False`, su p-valor crudo es el de la prueba de signo sobre esos 19 pares y la corrección de Holm se calcula con $m = 7$.

#### Scenario: Sin diferencias distintas de cero
- **WHEN** `C15` tiene 12 pares válidos y todas sus diferencias son nulas
- **THEN** su p-valor crudo es 1.0 y entra así en la corrección de Holm.

#### Scenario: Pares suficientes
- **WHEN** `C13` tiene 20 pares válidos
- **THEN** `evaluable == True` y su estado lo deciden el p-valor ajustado y el umbral de efecto.

### Requirement: P-Valor sin Diferencias Distintas de Cero
El p-valor crudo de una afirmación de `PHASE25_CLAIMS` SHALL ser 1.0 siempre que no quede ninguna diferencia distinta de cero entre sus pares válidos, sea evaluable o no (design precisión 48).

#### Scenario: Evaluable sin diferencias
- **WHEN** `C14` tiene 30 pares válidos y todas sus diferencias son nulas
- **THEN** `evaluable == True`, su p-valor crudo es 1.0 y su estado es `NOT_OBSERVED`.

### Requirement: Demografía de la Evaluación
La `demography` de cada `Phase25ClaimEvaluation`, de tipo `dict[str, dict[int, dict[str, float]]]` (condición → semilla → campo), SHALL contener para cada condición de la afirmación y cada semilla, incluidos los pares excluidos, `final_agents`, `final_active_agents`, `max_generation`, `cumulative_births`, `cumulative_deaths`, `mean_age_at_death` y `effective_parents`, covariables que no deciden el estado (design precisiones 44, 45 y 49).

#### Scenario: Covariables siempre presentes
- **WHEN** se evalúa `C16` con `PHASE25_SEEDS`
- **THEN** su `demography` tiene, para `full` y `drift` y cada una de las 30 semillas, esos siete valores, también para los pares excluidos.

#### Scenario: Cuatro condiciones en la diferencia de diferencias
- **WHEN** se evalúa `C17` con `PHASE25_SEEDS`
- **THEN** las claves de su `demography` son `full`, `drift`, `no_predation` y `no_predation_drift`.

### Requirement: Número Efectivo de Progenitores
`effective_parents` de una condición y semilla SHALL ser $1 / \sum_i p_i^2$, con $p_i$ la fracción de los nacimientos de la ventana final cuya fuente genética es $i$, concatenando `birth_source_ids` de `genetic_history` en esa ventana, o 0.0 sin nacimientos; SHALL informarse siempre junto con `C16` y no decidir su estado (design precisiones 44 y 68).

#### Scenario: Nacimientos concentrados
- **WHEN** los `birth_source_ids` de la ventana final suman `(3, 3, 7, 9)`
- **THEN** `effective_parents == pytest.approx(16 / 6, abs=1e-9)`.

#### Scenario: Sin nacimientos
- **WHEN** la ventana final no registra nacimientos
- **THEN** `effective_parents == 0.0`.

### Requirement: Nacimientos, Muertes y Longevidad de la Demografía
En `demography`, `cumulative_births` y `cumulative_deaths` SHALL ser las sumas, desde el tick 0 hasta el final de la corrida, de `births_this_tick` y `deaths_this_tick` de `evolutionary_history` (nacimientos individuales y holónicos; muertes por hambre y por depredación), sin contar las perturbaciones, y `mean_age_at_death` SHALL ser el del último registro de `genetic_history` (design precisión 49).

#### Scenario: Sumas de la historia evolutiva
- **WHEN** una corrida de 3 ticks registra `births_this_tick` 2, 0 y 3 y `deaths_this_tick` 1, 1 y 0 en `evolutionary_history`
- **THEN** su `demography` tiene `cumulative_births == 5` y `cumulative_deaths == 2`.

### Requirement: Sesgos Residuales de la Reproducción Neutral
La condición `drift` SHALL ser la reproducción neutral de `ablate(config, ["R12"])` y SHALL conservar los mecanismos ajenos a $R_{12}$ que siguen sesgando la herencia: la supervivencia de los donantes, la conjugación de $R_{26}$, la purga de $R_{27}$, la escala de $R_{30}$, la reproducción de holones de $R_{17}$ y la decisión de recombinar de $R_{38}$, que la documentación declara como sesgos residuales (design D56 y precisión 44). Su dirección es una expectativa declarada, no un requisito.

#### Scenario: Mecanismos conservados en drift
- **WHEN** se compara la condición `drift` de `25a` con la `full`
- **THEN** difieren sólo en `reproduction_mode == "neutral"`, y `enable_plasmid_hgt`, `enable_crispr_immunity`, `enable_sos_mutation` y `enable_recombination` siguen en `True`.

### Requirement: Dirección Declarada de los Sesgos
La documentación del pre-registro SHALL declarar los sesgos residuales de `drift` como conservadores para `C13`, `C14`, `C15` y `C18`, y como anticonservadores para `C16`: la reproducción neutral con donante uniforme no es una sombra neutral de Bedau–Packard, porque en `full` la descendencia se concentra en los progenitores con más energía (design precisión 44).

#### Scenario: Covariable de C16
- **WHEN** se evalúa `C16`
- **THEN** su evaluación informa `effective_parents` de `full` y de `drift` en `demography`, y su estado no depende de esa covariable.

### Requirement: Corrección de Holm–Bonferroni
Los p-valores crudos de las afirmaciones genuinas `C13`..`C19` SHALL corregirse por Holm–Bonferroni con $m = 7$ y $\alpha = 0.05$, sin `C20`: ordenados de menor a mayor, el ajustado de la posición $i$ es $\max_{j \le i} \min(1, (m - j + 1)\, p_{(j)})$.

#### Scenario: Ajuste de Holm
- **WHEN** los p-valores crudos de `C13`..`C19` son 0.001, 0.004, 0.03, 0.02, 0.2, 0.5 y 0.01
- **THEN** los ajustados son 0.007, 0.024, 0.09, 0.08, 0.4, 0.5 y 0.05 (con tolerancia `1e-9`), y sólo `C13` y `C14` quedan por debajo de $\alpha$: `C19` queda en el límite y no es menor.

### Requirement: Estado de las Afirmaciones de la Fase II-B
`ClaimStatus` SHALL agregar `OBSERVED = "OBSERVED"`, sólo para la Fase II-B. Una afirmación genuina (`C13`..`C19`) SHALL ser `OBSERVED` si su p-valor ajustado es menor que $\alpha = 0.05$ y la mediana de sus diferencias pareadas es al menos su umbral de efecto, y `NOT_OBSERVED` en otro caso; su evaluación SHALL informar siempre el p-valor crudo, el ajustado, la mediana y la demografía.

#### Scenario: Significativa pero con efecto chico
- **WHEN** `C13` tiene p-valor ajustado 0.006 y mediana de diferencias 0.5, menor que su umbral de efecto $\delta_{\min} = 1.0$
- **THEN** su estado es `NOT_OBSERVED`, y la evaluación informa los dos p-valores, la mediana y la demografía.

#### Scenario: Efecto grande sin significancia
- **WHEN** `C17` tiene mediana 2.0 y p-valor ajustado 0.08
- **THEN** su estado es `NOT_OBSERVED`.

#### Scenario: Estados previos intactos
- **WHEN** se evalúan `C1`..`C8`
- **THEN** ninguna recibe `ClaimStatus.OBSERVED`, y los demás miembros de `ClaimStatus` no cambian.

### Requirement: Mediana de las Diferencias con Empates
La mediana de las diferencias pareadas de una afirmación de `PHASE25_CLAIMS` SHALL tomarse sobre todas las diferencias de sus pares válidos, incluidas las nulas, aunque la prueba de signo descarte los empates (design D56).

#### Scenario: Mediana con empates
- **WHEN** `C17` tiene 30 pares válidos, 14 diferencias de 2.0 y 16 nulas, y p-valor ajustado 0.0004
- **THEN** la prueba de signo usa $n = 14$, la mediana de las diferencias es 0.0 porque incluye las 16 nulas, y su estado es `NOT_OBSERVED`.

### Requirement: Umbral de Efecto de la Fase II-B
El umbral de efecto de una afirmación de `PHASE25_CLAIMS` SHALL ser $\max(\delta_{\min},\ \text{delta\_relative} \cdot M)$, con $M$ la mediana de los valores de su condición de comparación sobre los pares válidos; con `delta_relative = 0.0` SHALL ser $\delta_{\min}$ (design D56).

#### Scenario: Umbral relativo de C16
- **WHEN** en `C16` la mediana de `drift` sobre los pares válidos es 0.02 y la mediana de las diferencias pareadas es 0.004, con p-valor ajustado 0.01
- **THEN** su umbral de efecto es `pytest.approx(0.005, abs=1e-9)` y su estado es `NOT_OBSERVED`.

#### Scenario: Piso absoluto de C16
- **WHEN** en `C16` la mediana de `drift` sobre los pares válidos es 0.002
- **THEN** su umbral de efecto es `pytest.approx(0.001, abs=1e-9)`, el $\delta_{\min}$.

### Requirement: E4 Condicionado a la Compuerta de Viabilidad
E4 de una afirmación de `PHASE25_CLAIMS` SHALL informarse contra `null_content` en `e4_p_value`, y `e4_interpretable` SHALL ser verdadero sólo si, con la configuración elegida por la compuerta (design D55), la condición `null_content` de su protocolo fue viable en al menos 9 de las 10 semillas de viabilidad; si no, SHALL ser falso sin consultar la métrica.

#### Scenario: Control nulo inviable
- **WHEN** con la configuración elegida, la condición `null_content` de `25b` fue viable en 8 de 10 semillas de viabilidad
- **THEN** `C18` tiene `e4_interpretable == False`, sin depender de su métrica, y las afirmaciones de `25a` dependen sólo de su propio `null_content`.

### Requirement: Pares Válidos de E4
`e4_p_value` SHALL calcularse con `PHASE25_SEEDS`, pareando por semilla `full` con `null_content` del mismo protocolo en la métrica simple, también en `C17` y `C19` (sin diferencia de diferencias), sólo sobre los pares válidos (las dos condiciones con `final_active_agents >= 1`), con la prueba de signo unilateral que descarta empates; un control nulo extinguido SHALL NOT contar como un 0.0 a favor de `full` (design D56 y precisiones 38 y 45).

#### Scenario: Control nulo extinguido excluido
- **WHEN** en `C14` la condición `null_content` de la semilla 45 termina sin hojas activas y las otras 29 semillas terminan con hojas activas en `full` y en `null_content`
- **THEN** `e4_p_value` se calcula sólo sobre esos 29 pares, y la semilla 45 no aporta una diferencia positiva.

#### Scenario: E4 simple en la diferencia de diferencias
- **WHEN** se calcula `e4_p_value` de `C19`
- **THEN** usa por semilla `full(s) - null_content(s)` en `mean_learning_codons`, sin `drift`, `stable` ni `stable_drift`.

### Requirement: Efectos de Regla Exploratorios
Los `rule_effects` de la Fase II-B, por afirmación, SHALL tener una variante por regla de `PHASE25_ALL_RULES`, salvo las de `PHASE25_INACTIVE_RULES` del protocolo, SHALL medirse sólo con `PHASE25_RULE_EFFECT_SEEDS = tuple(range(42, 52))` y SHALL quedar fuera de la corrección de Holm y del estado de las afirmaciones (design precisión 66).

#### Scenario: Efectos fuera de la prueba
- **WHEN** se evalúa `C14` con `PHASE25_SEEDS`
- **THEN** sus `rule_effects` usan sólo `PHASE25_RULE_EFFECT_SEEDS`, y cambiar sus valores no altera el p-valor ajustado ni el estado de ninguna afirmación.

#### Scenario: Regla inactiva sin variante
- **WHEN** se generan los `rule_effects` de `C13` sobre `25a`
- **THEN** ninguna regla de `PHASE25_INACTIVE_RULES["25a"]`, como `R25` o `R31`, recibe variante.

### Requirement: Cálculo de los Efectos de Regla
El efecto de una regla sobre una afirmación SHALL ser la mediana de `full(s) − ablate(full, [regla])(s)` en la métrica simple de la afirmación, sin diferencia de diferencias, sobre las semillas de `PHASE25_RULE_EFFECT_SEEDS` en que las dos corridas terminan con hojas activas (regla de la precisión 45), o `None` sin semillas válidas; `rule_effects` SHALL ser `dict[str, dict[str, float | None]]` (design precisión 66).

#### Scenario: Efecto de regla de C17
- **WHEN** se calcula el efecto de `R36` sobre `C17`
- **THEN** compara `full` con `ablate(full, ["R36"])` en `mean_expressible_nonattack_codons`, sin usar `drift` ni `no_predation_drift`.

#### Scenario: Variante extinguida
- **WHEN** la variante sin `R33` termina sin hojas activas en las 10 semillas
- **THEN** su efecto es `None`, no 0.0.

### Requirement: Caché de Corridas de la Atribución
`run_phase25_attribution` SHALL ejecutar cada corrida una sola vez por (protocolo, variante, semilla), con la variante una condición de D56 o la regla ablacionada de un efecto de regla, y SHALL usar esa corrida para todas las afirmaciones del protocolo, E4 y los `rule_effects` (design precisión 67).

#### Scenario: Una corrida para varias afirmaciones
- **WHEN** se evalúan `C13`, `C14`, `C16` y `C17` sobre `25a` con dos semillas
- **THEN** la condición `full` de `25a` se ejecuta una sola vez por semilla.

### Requirement: Reglas Inactivas por Protocolo de la Fase II-B
Según el pre-registro aprobado en la tarea 0.5 (design D56), `PHASE25_INACTIVE_RULES` SHALL ser `R14`–`R19`, `R22`, `R23`, `R25` y `R31` para `"25a"`, `"25c"` y `"25d"` (precisión 51), y `R14`, `R18` y `R19` para `"25b"`. Un test SHALL contrastarlas con las configuraciones.

#### Scenario: Coherencia con las configuraciones
- **WHEN** un test ablaciona cada regla inactiva de cada protocolo sobre su configuración de `PHASE25_PROTOCOL_CONFIGS`
- **THEN** la regla está apagada o es inerte en esa configuración.

### Requirement: Perfil Pre-Registrado de la Fase II-B
Según el pre-registro aprobado en la tarea 0.5 (design D56), `attribution.py` SHALL definir el perfil `phase25` con `total_ticks = 5000` y `PHASE25_SEEDS = tuple(range(42, 72))`, sin modificar `PHASE2_SEEDS` ni el perfil `phase2`.

#### Scenario: Perfil y semillas
- **WHEN** se inspeccionan `PROFILES["phase25"]`, `PHASE25_SEEDS` y `PHASE2_SEEDS`
- **THEN** `total_ticks == 5000`, hay 30 semillas de 42 a 71, y `PHASE2_SEEDS == tuple(range(42, 52))`.

### Requirement: Prueba de Humo de la Fase II-B
Después de la compuerta de viabilidad y antes de los runners, la prueba de humo SHALL registrar, por protocolo, condición y semilla, sólo si la corrida termina, la generación máxima y la población final, sin calcular ni mirar las métricas de las afirmaciones.

#### Scenario: Registro de la prueba de humo
- **WHEN** se corre la prueba de humo de `25a`, `25b`, `25c` y `25d` con `PHASE25_SEEDS`
- **THEN** su registro contiene, por protocolo, condición y semilla, sólo la terminación, la generación máxima y la población final, y ningún valor de las métricas de `C13`..`C20`.

### Requirement: Reportes de las Fases I y II sin Cambios
La atribución de la Fase II-B SHALL no alterar la de las fases anteriores: los reportes de `C1`..`C8` SHALL ser idénticos a los de antes del cambio.

#### Scenario: Reportes previos idénticos
- **WHEN** se corren la atribución 001-D y `run_phase2_attribution` con el mismo perfil corto y las mismas semillas antes y después del cambio
- **THEN** las evaluaciones de `C1`..`C8` son idénticas.

### Requirement: Pre-Registro D56 Conservado ante la Sombra
La reformulación del control (design D64) SHALL NOT modificar `PHASE25_CLAIMS`, `PHASE25_SEEDS`, `PHASE25_PROTOCOL_CONFIGS`, sus condiciones con reproducción neutral ni `run_phase25_attribution`: la atribución de D56 SHALL reproducirse igual, y sus configuraciones SHALL tener `enable_neutral_shadow == False`.

#### Scenario: D56 reproducible
- **WHEN** se corre `run_phase25_attribution` con un perfil corto y dos semillas antes y después de la etapa S
- **THEN** las evaluaciones y los `rule_effects` son idénticos, y ninguna configuración de `PHASE25_PROTOCOL_CONFIGS` activa la sombra.

### Requirement: Tipo Phase25ShadowClaim
`Phase25ShadowClaim` SHALL ser `frozen` con `claim_id`, `statement`, `protocol`, `metric`, `shadow_metric: str | None`, `comparison: str | None`, `rule_ids`, `channel`, `delta_min`, `delta_relative: float = 0.0`, `exploratory: bool = False` y `joint_real_comparison: bool = False`. `shadow_metric is None` SHALL implicar `comparison == "no_learning"`, y `comparison` SHALL valer `None`, `"no_predation"`, `"stable"` o `"no_learning"` (design D72.2).

#### Scenario: Funcional sin sombra
- **WHEN** se construye un `Phase25ShadowClaim` con `shadow_metric=None` y `comparison="no_predation"`
- **THEN** se lanza `ValueError`.

### Requirement: Validación de la Condición Conjunta
`Phase25ShadowClaim` con `joint_real_comparison=True` SHALL lanzar `ValueError` si no es una diferencia de diferencias, es decir, si `shadow_metric is None` o `comparison is None` (design D72.2).

#### Scenario: Condición conjunta sin diferencia de diferencias
- **WHEN** se construye un `Phase25ShadowClaim` con `shadow_metric` definido, `comparison=None` y `joint_real_comparison=True`
- **THEN** se lanza `ValueError`.

### Requirement: Diferencia contra la Sombra
La diferencia de la semilla $s$ SHALL ser $\text{real}_{full}(s) - \text{sombra}_{full}(s)$ con `comparison is None`; $[\text{real} - \text{sombra}]_{full}(s) - [\text{real} - \text{sombra}]_{comp}(s)$ con `shadow_metric` y `comparison` definidos; y $\text{full}(s) - \text{no\_learning}(s)$ en la métrica real con `shadow_metric is None`. Real y sombra SHALL leerse de la misma corrida (design D72.2).

#### Scenario: Sombra simple
- **WHEN** en una semilla `full` tiene `mean_conditional_codons` 5.0 y `shadow_mean_conditional_codons` 3.5
- **THEN** la diferencia de `C21` en esa semilla es `pytest.approx(1.5, abs=1e-9)`.

#### Scenario: Diferencia de diferencias con sombra
- **WHEN** en una semilla real y sombra valen 9.0 y 6.0 en `full` y 7.0 y 5.5 en `no_predation`
- **THEN** la diferencia de `C25` es `pytest.approx(1.5, abs=1e-9)`.

### Requirement: Valores Informados con Sombra
La evaluación SHALL reutilizar `Phase25ClaimEvaluation` con `values` igual a $\text{real}_{full}$, $[\text{real} - \text{sombra}]_{full}$ o `full`, y `comparison_values` igual a $\text{sombra}_{full}$, $[\text{real} - \text{sombra}]_{comp}$ o `no_learning`, según sea sombra simple, diferencia de diferencias o funcional, de modo que la diferencia sea siempre `values[s] - comparison_values[s]` (design D72.2).

#### Scenario: Valores de C27
- **WHEN** en una semilla real y sombra valen 4.0 y 1.0 en `25d` `full` y 2.0 y 1.0 en `stable`
- **THEN** `values` vale 3.0, `comparison_values` vale 1.0 y la diferencia es 2.0.

### Requirement: Afirmaciones con Sombra C21 a C24
`PHASE25_SHADOW_CLAIMS` SHALL contener, crecientes, con canal `()`, $R_C$ `("R12",)` y `comparison=None`: `C21` (`25a`, `mean_conditional_codons`, $\delta_{\min} = 1.0$), `C22` (`25a`, `innate_policy_divergence`, $0.05$), `C23` (`25c`, `communicating_fraction`, $0.10$) y `C24` (`25a`, `new_activity_per_birth`, $0.001$, `delta_relative = 0.25`), cada una con su métrica `shadow_` homóloga (design D72.3).

#### Scenario: Registro de C21 a C24
- **WHEN** se inspeccionan `C21`..`C24`
- **THEN** tienen esos protocolos, métricas, `shadow_metric` igual a `"shadow_" + metric`, $R_C$, canales, $\delta_{\min}$ y `delta_relative` (0.0 salvo en `C24`).

### Requirement: Afirmaciones con Sombra C25 a C27
`PHASE25_SHADOW_CLAIMS` SHALL contener, crecientes, con canal `()` y su métrica `shadow_` homóloga: `C25` (`25a`, `mean_expressible_nonattack_codons`, `"no_predation"`, `("R37",)`, $1.0$, `joint_real_comparison=True`), `C26` (`25b`, `innate_share_choice`, `None`, `("R12",)`, $0.01$, `delta_relative = 0.25`) y `C27` (`25d`, `mean_learning_codons`, `"stable"`, `()`, $1.0$, `exploratory=True`) (design D72.3).

#### Scenario: Registro de C25 a C27
- **WHEN** se inspeccionan `C25`, `C26` y `C27`
- **THEN** tienen esos protocolos, métricas, `shadow_metric`, comparaciones, $R_C$, canales, $\delta_{\min}$ y `delta_relative`, sólo `C27` tiene `exploratory=True` y sólo `C25` tiene `joint_real_comparison=True` entre `C21`..`C28`.

#### Scenario: Enunciados iguales a los de D56
- **WHEN** se comparan los `statement` de `C21`..`C23` y `C25`..`C28` con los de `C13`..`C15` y `C17`..`C20`
- **THEN** son iguales, y el de `C24` es "Actividad evolutiva por encima de la sombra neutral".

### Requirement: Afirmación Funcional C28
`PHASE25_SHADOW_CLAIMS` SHALL contener `C28` (`25d`, `post_shift_accuracy`, `shadow_metric=None`, `comparison="no_learning"`, $R_C$ y canal `("R39", "R40")`, $\delta_{\min} = 0.02$): programada por construcción, fuera de Holm y con estado por el p-valor crudo (design D72.3, precisión 53); `PHASE25_SHADOW_CLAIMS` SHALL contener exactamente `C21`..`C28`.

#### Scenario: Registro de C28
- **WHEN** se inspecciona `PHASE25_SHADOW_CLAIMS`
- **THEN** contiene exactamente `C21`..`C28`, y `C28` es programada por construcción, sin `p_adjusted` (`None`).

### Requirement: Pares Válidos con Sombra
Una semilla SHALL ser válida si terminan con al menos una hoja activa todas las corridas de su diferencia: `full` en la sombra simple, `full` y `comp` en la diferencia de diferencias y `full` y `no_learning` en `C28`. Con menos de 20 pares válidos la afirmación SHALL ser `NOT_OBSERVED` con `evaluable = False` y, si es confirmatoria (`C21`..`C26`), SHALL seguir contando en Holm (design D72.5).

#### Scenario: Sombra simple con full viva
- **WHEN** `full` de `25a` termina con hojas activas en 25 de 30 semillas
- **THEN** `C21` tiene 25 pares válidos, 5 `excluded_seeds` y `evaluable == True`, sin ninguna corrida neutral.

#### Scenario: Diferencia de diferencias con comp extinta
- **WHEN** en una semilla `full` de `25d` sobrevive y `stable` termina sin hojas activas
- **THEN** esa semilla no es par válido de `C27`.

### Requirement: Prueba, Holm y Estado con Sombra
Las afirmaciones con sombra SHALL usar la prueba de signo unilateral sobre los pares válidos (empates con $|d| \le 10^{-9}$ descartados, p-valor 1.0 sin diferencias distintas de cero), Holm–Bonferroni sólo sobre las confirmatorias `C21`..`C26` con $m = \max(6, \text{confirmatorias evaluadas})$ y $\alpha = 0.05$, y el estado de la precisión 112 sobre la mediana de todas las diferencias (design D72.5).

#### Scenario: Familia de Holm propia
- **WHEN** se evalúa `PHASE25_SHADOW_CLAIMS`
- **THEN** la corrección usa sólo `C21`..`C26`, con $m = 6$, y no incluye `C27`, `C28` ni ninguna afirmación de `PHASE25_CLAIMS`.

#### Scenario: Holm con un subconjunto
- **WHEN** se evalúan sólo `C21` y `C27` de `PHASE25_SHADOW_CLAIMS`
- **THEN** `C21` se corrige con $m = 6$ y `C27` tiene `p_adjusted` igual a `None`.

### Requirement: Umbrales Relativos de C24 y C26
El umbral de efecto SHALL ser $\max(0.001,\ 0.25 \cdot M)$ en `C24` y $\max(0.01,\ 0.25 \cdot M)$ en `C26`, con $M$ la mediana de `comparison_values` (la sombra) sobre los pares válidos; los demás umbrales SHALL ser su $\delta_{\min}$ (design D72.4, precisión 119).

#### Scenario: Umbral de C24
- **WHEN** la mediana de `shadow_new_activity_per_birth` sobre los pares válidos es 0.02
- **THEN** el umbral de `C24` es `pytest.approx(0.005, abs=1e-9)`.

#### Scenario: Umbral de C26
- **WHEN** la mediana de `shadow_innate_share_choice` sobre los pares válidos es 0.02 en una evaluación y 0.12 en otra
- **THEN** el umbral de `C26` es `pytest.approx(0.01, abs=1e-9)` en la primera y `pytest.approx(0.03, abs=1e-9)` en la segunda.

### Requirement: Condición Conjunta de C25
`C25` SHALL ser `OBSERVED` sólo si, además del p-valor ajustado y la mediana, `joint_median`, la mediana sobre sus pares válidos de $\text{real}_{full}(s) - \text{real}_{no\_predation}(s)$, es mayor que $10^{-9}$. Es un requisito de dirección, no una prueba: SHALL NOT cambiar ningún p-valor ni $m$ (design D72.3).

#### Scenario: Mantenimiento sin construcción
- **WHEN** `C25` tiene p-valor ajustado 0.01, mediana de diferencias 1.5 y `joint_median` igual a -0.5
- **THEN** su estado es `NOT_OBSERVED`, y su p-valor ajustado y los de `C21`..`C26` son los mismos que con `joint_median` positiva.

#### Scenario: Condición conjunta cumplida
- **WHEN** `C25` tiene p-valor ajustado 0.01, mediana de diferencias 1.5 y `joint_median` igual a 2.0
- **THEN** su estado es `OBSERVED`.

#### Scenario: joint_median fuera de C25
- **WHEN** se evalúan `PHASE25_SHADOW_CLAIMS` y `PHASE25_CLAIMS`
- **THEN** `joint_median` es un número en `C25` y `None` en todas las demás evaluaciones.

### Requirement: C27 Exploratoria
`C27` SHALL computarse e informarse como las demás, con `p_adjusted = None` y su estado por el p-valor crudo y el umbral, y SHALL NOT entrar en Holm; su estado SHALL informarse como exploratorio, sin valor confirmatorio (design D72.5).

#### Scenario: C27 fuera de Holm
- **WHEN** `C27` tiene p-valor crudo 0.01 y mediana de diferencias 1.5 con 20 pares válidos
- **THEN** su estado es `OBSERVED` con `p_adjusted` igual a `None`, y la corrección de `C21`..`C26` es la misma que sin `C27`.

### Requirement: E4 con Sombra
E4 SHALL compararse contra `null_content`: en `C21`..`C27`, $[\text{real} - \text{sombra}]_{full}(s) - [\text{real} - \text{sombra}]_{null\_content}(s)$ en la métrica simple, también en `C25` y `C27`; en `C28`, $\text{full}(s) - \text{null\_content}(s)$. SHALL usar pares con las dos corridas con hojas activas y la interpretabilidad de la precisión 113 (design D72.7).

#### Scenario: E4 sobre el exceso de la sombra
- **WHEN** en una semilla real y sombra valen 5.0 y 3.0 en `full` y 4.0 y 3.5 en `null_content`
- **THEN** la diferencia de E4 de `C21` en esa semilla es `pytest.approx(1.5, abs=1e-9)`.

### Requirement: Efectos de Regla con Sombra
Los `rule_effects` de la atribución con sombra SHALL ser exploratorios, con `PHASE25_SHADOW_RULE_EFFECT_SEEDS = tuple(range(72, 82))`: la mediana, sobre las semillas con `full` y la variante con hojas activas, de $D_{full}(s) - D_{variante}(s)$ con $D = \text{real} - \text{sombra}$ en la métrica simple (la real en `C28`), o `None` sin semillas válidas (design D72.8).

#### Scenario: Efecto de regla sobre el exceso
- **WHEN** con una regla ablacionada $D$ vale 1.0 en `full` y 0.25 en la variante en las únicas dos semillas válidas
- **THEN** el efecto de esa regla es `pytest.approx(0.75, abs=1e-9)`.

### Requirement: Efectos de Regla no Definidos con Sombra
En la atribución con sombra, el efecto de regla SHALL valer `None`, sin correr su variante, para $R_{12}$ (su ablación es la reproducción neutral), $R_{13}$ ($D \equiv 0$ por construcción) y $R_{24}$ (sombra inerte) en todas las afirmaciones, y para $R_{32}$ en `C22` y `C26` (sin decisiones genéticas) (design D72.8).

#### Scenario: Reglas sin efecto definido
- **WHEN** se calculan los `rule_effects` de la atribución con sombra
- **THEN** los de `R12`, `R13` y `R24` valen `None` en `C21`..`C28`, el de `R32` vale `None` en `C22` y `C26`, y ninguna corrida tiene `reproduction_mode == "neutral"`.

#### Scenario: Efecto de R32 definido fuera de C22 y C26
- **WHEN** `R32` está activa en `25a` y hay semillas válidas con `full` y la variante
- **THEN** el efecto de `R32` en `C21` es un número, no `None`.

### Requirement: Protocolos y Condiciones con Sombra
`PHASE25_SHADOW_PROTOCOL_CONFIGS` SHALL ser `PHASE25_PROTOCOL_CONFIGS` con `enable_neutral_shadow=True`, y sus condiciones SHALL ser `full`, `no_predation` (`25a`), `stable` y `no_learning` (`25d`) y `null_content`, todas con la sombra activa; las condiciones con reproducción neutral SHALL NOT correrse (design D72.6).

#### Scenario: Sin condiciones neutrales
- **WHEN** se enumeran las corridas de la atribución con sombra
- **THEN** ninguna tiene `reproduction_mode == "neutral"`, todas tienen `enable_neutral_shadow == True` y la abundancia es (80, 20).

### Requirement: Semillas y Perfil con Sombra
La atribución con sombra SHALL usar `PHASE25_SHADOW_SEEDS = tuple(range(72, 102))`, disjuntas de `PHASE25_VIABILITY_SEEDS`, `PHASE2_SEEDS` y `PHASE25_SEEDS`, el perfil `phase25` y la ventana final de la precisión 4 (último tick en `C24`; `post_shift_accuracy` en `C28`) (design D72.3 y D72.6).

#### Scenario: Semillas nuevas
- **WHEN** se inspecciona `PHASE25_SHADOW_SEEDS`
- **THEN** tiene 30 semillas, de 72 a 101, y su intersección con `PHASE25_SEEDS`, `PHASE2_SEEDS` y `PHASE25_VIABILITY_SEEDS` es vacía.

### Requirement: Ejecución de la Atribución con Sombra
`run_phase25_shadow_attribution(seeds=PHASE25_SHADOW_SEEDS, claims=PHASE25_SHADOW_CLAIMS, jobs=1, configs=None, rule_effect_seeds=PHASE25_SHADOW_RULE_EFFECT_SEEDS)` SHALL devolver un `Phase25Report` con `profile == "phase25"`, y SHALL rechazar con `ValueError` un `configs[protocolo]` sin la sombra efectiva o que no respete su protocolo (precisión 121); la validación SHALL aplicarse sólo a las configuraciones base, no a las variantes ablacionadas (design D72.11).

#### Scenario: Configuración sin sombra
- **WHEN** se llama con `configs["25a"]` igual a `PHASE25_PROTOCOL_CONFIGS["25a"]`
- **THEN** se lanza `ValueError`.

#### Scenario: Variante ablacionada fuera de la validación
- **WHEN** las configuraciones base son válidas y la variante de `R32` de `25a` (sin `enable_genetic_policy`) no cumpliría la validación de su protocolo
- **THEN** no se lanza `ValueError`, y la variante se corre para los efectos de regla en que está definida.

#### Scenario: Salida idéntica para cualquier jobs
- **WHEN** se corre con un perfil corto, dos semillas y `jobs` 1 y 3
- **THEN** los dos reportes son idénticos.
