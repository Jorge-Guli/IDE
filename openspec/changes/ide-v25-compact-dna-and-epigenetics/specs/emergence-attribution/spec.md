# Spec Delta: Emergence Attribution

## ADDED Requirements

### Requirement: Inventario de Reglas de la Fase II-B (R24 a R38)
Según el pre-registro aprobado en la tarea 0.5 (design D56), `attribution.py` SHALL definir `PHASE25_DESIGN_RULES` con `R24`..`R38` en orden, cada una con el `name`, el `purpose` no vacío y la ablación de una bandera en `False` de la tabla de D56, sin modificar `DESIGN_RULES`, `PHASE2_DESIGN_RULES` ni `ALL_DESIGN_RULES`.

#### Scenario: Inventario y ablaciones
- **WHEN** se inspecciona `PHASE25_DESIGN_RULES`
- **THEN** contiene `R24`..`R38` en orden; las ablaciones de `R24`, `R28`, `R32`, `R37` y `R38` son `(("enable_compact_dna", False),)`, `(("enable_sporulation", False),)`, `(("enable_genetic_policy", False),)`, `(("enable_predation", False),)` y `(("enable_recombination", False),)`; y `ALL_DESIGN_RULES` sigue con `R1`..`R23`.

#### Scenario: Ablaciones de las reglas ecológicas
- **WHEN** se inspeccionan las ablaciones de `R33`, `R34`, `R35` y `R36`
- **THEN** son `(("enable_resource_depletion", False),)`, `(("enable_heterogeneity", False),)`, `(("enable_carcasses", False),)` y `(("enable_energy_transfer", False),)`.

### Requirement: Sesgos Declarados en el Propósito de las Reglas
Según el pre-registro aprobado en la tarea 0.5 (design D56), el `purpose` de `R24` SHALL declarar que abarata la complejidad latente y el de `R29` que fuerza el recambio; los de `R25`, `R28`, `R36`, `R37` y `R38` SHALL declarar que su uso lo decide el ADN, y ninguno SHALL declarar especialización programada, rescate de poblaciones ni estabilidad por decreto.

#### Scenario: Sesgos vigentes
- **WHEN** se leen los `purpose` de `R24` y `R29`
- **THEN** contienen sus sesgos declarados: complejidad latente y recambio forzado.

#### Scenario: Sesgos retirados por la reformulación
- **WHEN** se leen los `purpose` de `R25`, `R28` y `R31`
- **THEN** ninguno menciona especialización programada, rescate de poblaciones ni estabilidad por decreto, y los de `R25` y `R28` dicen que su uso lo decide el ADN.

### Requirement: Índice Conjunto de Reglas y Ablación
`attribution.py` SHALL definir `PHASE25_ALL_RULES = ALL_DESIGN_RULES + PHASE25_DESIGN_RULES`, y `ablate(config, rule_ids)` SHALL buscar las reglas en las dos tuplas, sin modificar `ALL_DESIGN_RULES`.

#### Scenario: Ablación de reglas de las tres fases
- **WHEN** se invoca `ablate(config, ["R12", "R24", "R37"])` sobre una configuración con `enable_compact_dna=True` y `enable_predation=True`
- **THEN** la configuración resultante tiene `reproduction_mode == "neutral"`, `enable_compact_dna == False` y `enable_predation == False`, y `len(PHASE25_ALL_RULES) == len(ALL_DESIGN_RULES) + 15`.

### Requirement: Configuración del Protocolo 25a
Según el pre-registro aprobado en la tarea 0.5 (design D56), `PHASE25_PROTOCOL_CONFIGS["25a"]` SHALL ser `PHASE2_PROTOCOL_CONFIGS["002a"]` con `enable_compact_dna`, `enable_genetic_policy`, `enable_plasmid_hgt`, `enable_crispr_immunity`, `enable_sporulation`, `enable_telomere_senescence`, `enable_sos_mutation`, `enable_resource_depletion`, `enable_heterogeneity`, `enable_carcasses`, `enable_energy_transfer`, `enable_predation` y `enable_recombination` en `True` y `season_length = 500`.

#### Scenario: Configuración de 25a
- **WHEN** se compara `PHASE25_PROTOCOL_CONFIGS["25a"]` con `PHASE2_PROTOCOL_CONFIGS["002a"]`
- **THEN** difieren sólo en esas 13 banderas, todas en `True`, en `season_length == 500` y en `(resources_per_pattern, resource_regen_delay)`, fijados por la compuerta de viabilidad.

### Requirement: Configuraciones de los Protocolos 25b y 25c
Según el pre-registro aprobado en la tarea 0.5 (design D56), `PHASE25_PROTOCOL_CONFIGS["25b"]` SHALL ser `PHASE2_PROTOCOL_CONFIGS["003a"]` con las banderas y la `season_length` de `"25a"` más `enable_epigenetic_roles` y `enable_symbiotic_ratchet` en `True`; y `["25c"]` SHALL ser `"25a"` con `comm_propensity_base = 0.0`.

#### Scenario: Configuración de 25b
- **WHEN** se compara `PHASE25_PROTOCOL_CONFIGS["25b"]` con `PHASE2_PROTOCOL_CONFIGS["003a"]`
- **THEN** difieren sólo en las 13 banderas de `25a`, `enable_epigenetic_roles`, `enable_symbiotic_ratchet`, `season_length == 500` y los dos valores de la compuerta.

#### Scenario: Configuración de 25c
- **WHEN** se compara `PHASE25_PROTOCOL_CONFIGS["25c"]` con `["25a"]`
- **THEN** difieren sólo en `comm_propensity_base == 0.0`.

### Requirement: Abundancia Fijada por la Compuerta de Viabilidad
`resources_per_pattern` y `resource_regen_delay` de los tres protocolos de `PHASE25_PROTOCOL_CONFIGS` SHALL ser los de la configuración elegida por la compuerta de viabilidad (design D55), fijados en un commit propio antes de la prueba de humo; ningún otro campo SHALL ajustarse con la compuerta.

#### Scenario: Valores comunes a los protocolos
- **WHEN** la compuerta elige `(30, 10)`
- **THEN** `25a`, `25b` y `25c` tienen `resources_per_pattern == 30` y `resource_regen_delay == 10`, y el resto de sus campos es el del pre-registro.

### Requirement: Tipo Phase25Claim
`attribution.py` SHALL definir `Phase25Claim` como `@dataclass(frozen=True)` con `claim_id`, `statement`, `protocol`, `metric`, `comparison` (`"drift"` o `"no_predation"`), `rule_ids`, `channel`, `delta_min` y `delta_relative: float = 0.0`, en ese orden, y `PHASE25_CLAIMS` SHALL ser una tupla de `Phase25Claim` (design D56).

#### Scenario: Campos de la afirmación
- **WHEN** se inspeccionan los campos de `Phase25Claim`
- **THEN** son exactamente esos nueve, `delta_relative` vale 0.0 por defecto, y asignar uno lanza `dataclasses.FrozenInstanceError`.

### Requirement: Tipos de Evaluación y Reporte de la Fase II-B
`Phase25ClaimEvaluation` SHALL ser `frozen` con `claim_id`, `status`, `p_value`, `p_adjusted`, `median_difference`, `values`, `comparison_values`, `demography`, `e4_p_value`, `e4_interpretable` y, al final y en este orden, `excluded_seeds: tuple[int, ...]`, `excluded_pairs: int` y `evaluable: bool` (design precisiones 45 y 47); `Phase25Report` SHALL ser `frozen` con `profile = "phase25"`, `rules = PHASE25_ALL_RULES`, `evaluations` y `rule_effects`.

#### Scenario: Campos de la evaluación y del reporte
- **WHEN** se inspeccionan los campos de `Phase25ClaimEvaluation` y de `Phase25Report`
- **THEN** son exactamente los enumerados, en ese orden, y los dos tipos son inmutables.

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
Según el pre-registro aprobado en la tarea 0.5 (design D56), `PHASE25_CLAIMS` SHALL contener, con métrica creciente, $R_C$ `("R12",)`, canal `()` y comparación `full` frente a `drift`: `C13` (`25a`, `regulated_expression_fraction`, $\delta_{\min} = 0.05$), `C14` (`25a`, `policy_divergence`, $0.05$) y `C15` (`25c`, `communicating_fraction`, $0.10$), las tres con `delta_relative = 0.0`.

#### Scenario: Registro de C13 a C15
- **WHEN** se inspeccionan `C13`, `C14` y `C15` en `PHASE25_CLAIMS`
- **THEN** tienen esos protocolos, métricas, comparaciones, $R_C$, canales y $\delta_{\min}$, `delta_relative == 0.0` y métrica creciente.

### Requirement: Afirmaciones Pre-Registradas C16 a C18
Según el pre-registro aprobado en la tarea 0.5 (design D56), `PHASE25_CLAIMS` SHALL contener, con métrica creciente y canal `()`: `C16` (`25a`, `new_activity_per_birth`, `full` frente a `drift`, $R_C$ `("R12",)`, $\delta_{\min} = 0.001$, `delta_relative = 0.25`), `C17` (`25a`, `mean_expressible_codons`, `full` frente a `no_predation`, `("R37",)`, $1.0$) y `C18` (`25b`, `share_rate`, `full` frente a `drift`, `("R12",)`, $0.01$), éstas con `delta_relative = 0.0`; ninguna más salvo `C13`–`C15`.

#### Scenario: Registro de C16 a C18
- **WHEN** se inspecciona `PHASE25_CLAIMS`
- **THEN** contiene exactamente `C13`..`C18`, y `C16`, `C17` y `C18` tienen esos protocolos, métricas, comparaciones, $R_C$, canales, $\delta_{\min}$ y `delta_relative`.

### Requirement: Métrica de Ventana Final
La métrica de cada afirmación de `PHASE25_CLAIMS` SHALL ser la media de su campo de `GeneticTickMetrics` o `EcologyTickMetrics` sobre la ventana final, los últimos `max(1, math.ceil(0.1 * total_ticks))` ticks; la de `C16` SHALL ser el valor de `new_activity_per_birth` en el último tick (design precisión 43).

#### Scenario: Ventana del perfil phase25
- **WHEN** se mide `C13` en una corrida de 5000 ticks
- **THEN** su valor es la media de `regulated_expression_fraction` en los últimos 500 registros de `engine.genetic_history`.

#### Scenario: Actividad en el último tick
- **WHEN** se mide `C16` en una corrida de 5000 ticks
- **THEN** su valor es `new_activity_per_birth` del último registro, no una media.

#### Scenario: Ventana de perfiles cortos
- **WHEN** se mide `C14` en corridas de 45 y de 5 ticks
- **THEN** la ventana es de los últimos 5 y del último registro, respectivamente.

### Requirement: Clasificación No Programada de C13 a C18
Como su canal es vacío, `is_by_construction` SHALL ser falso para `C13`..`C18`, y ninguna SHALL clasificarse programada por construcción.

#### Scenario: Canal vacío
- **WHEN** se evalúa `is_by_construction` sobre `C13`..`C18` con sus configuraciones de `PHASE25_PROTOCOL_CONFIGS`
- **THEN** es falso para las seis, y las afirmaciones de las Fases I y II conservan su clasificación previa.

### Requirement: Prueba de Signo Pareada de la Fase II-B
Para cada afirmación de `PHASE25_CLAIMS`, el p-valor crudo SHALL ser el de una prueba de signo unilateral (`sign_test_p_value`) sobre las diferencias pareadas por semilla entre `full` y su comparación, sólo en los pares válidos y descartando los empates.

#### Scenario: Diferencias con empates
- **WHEN** sobre 30 pares válidos hay 20 diferencias positivas, 5 negativas y 5 nulas
- **THEN** el p-valor crudo es `pytest.approx(0.0020386576652526855, abs=1e-9)`, calculado con $n = 25$.

### Requirement: Pares Válidos de la Fase II-B
Un par (semilla) de una afirmación de `PHASE25_CLAIMS` SHALL ser válido si sus dos condiciones terminan con al menos una hoja activa (`final_active_agents >= 1`); los demás SHALL excluirse de la prueba de signo y de la mediana, y sus semillas SHALL informarse en `excluded_seeds`, con `excluded_pairs == len(excluded_seeds)` (design precisiones 45 y 47).

#### Scenario: Extinción en una condición
- **WHEN** en `C14` la condición `drift` de la semilla 50 termina sin hojas activas y las demás 29 semillas terminan con hojas activas en `full` y en `drift`
- **THEN** la prueba de signo y la mediana usan 29 pares, `excluded_seeds == (50,)` y `excluded_pairs == 1`.

### Requirement: Afirmación No Evaluable
Si una afirmación de `PHASE25_CLAIMS` tiene menos de 20 pares válidos, SHALL quedar `NOT_OBSERVED` con `evaluable = False` y SHALL seguir contando en la corrección de Holm con $m = 6$, con el p-valor de la prueba de signo sobre sus pares válidos (1.0 si no queda ninguna diferencia distinta de cero); con 20 o más, `evaluable` SHALL ser `True` (design D56 y precisiones 45 y 48).

#### Scenario: Demasiadas extinciones
- **WHEN** `C18` tiene 19 pares válidos y una mediana de diferencias de 0.05
- **THEN** su estado es `NOT_OBSERVED`, `evaluable == False`, su p-valor crudo es el de la prueba de signo sobre esos 19 pares y la corrección de Holm se calcula con $m = 6$.

#### Scenario: Sin diferencias distintas de cero
- **WHEN** `C15` tiene 12 pares válidos y todas sus diferencias son nulas
- **THEN** su p-valor crudo es 1.0 y entra así en la corrección de Holm.

#### Scenario: Pares suficientes
- **WHEN** `C13` tiene 20 pares válidos
- **THEN** `evaluable == True` y su estado lo deciden el p-valor ajustado y el umbral de efecto.

### Requirement: Demografía de la Evaluación
La `demography` de cada `Phase25ClaimEvaluation` SHALL contener, por semilla y condición, incluidos los pares excluidos, `final_agents`, `final_active_agents`, `max_generation`, `cumulative_births`, `cumulative_deaths` y `mean_age_at_death`, que se informan siempre como covariables y no deciden el estado (design precisiones 45 y 49).

#### Scenario: Covariables siempre presentes
- **WHEN** se evalúa `C16` con `PHASE25_SEEDS`
- **THEN** su `demography` tiene, para cada una de las 30 semillas y para `full` y `drift`, esos seis valores, también para los pares excluidos.

### Requirement: Nacimientos, Muertes y Longevidad de la Demografía
En `demography`, `cumulative_births` y `cumulative_deaths` SHALL ser las sumas, desde el tick 0 hasta el final de la corrida, de `births` y `deaths` de `evolutionary_history` (nacimientos individuales y holónicos; muertes por hambre y por depredación), sin contar las perturbaciones, y `mean_age_at_death` SHALL ser el del último registro de `genetic_history` (design precisión 49).

#### Scenario: Sumas de la historia evolutiva
- **WHEN** una corrida de 3 ticks registra `births` 2, 0 y 3 y `deaths` 1, 1 y 0 en `evolutionary_history`
- **THEN** su `demography` tiene `cumulative_births == 5` y `cumulative_deaths == 2`.

### Requirement: Sesgos Residuales de la Reproducción Neutral
La condición `drift` SHALL ser la reproducción neutral de `ablate(config, ["R12"])` y SHALL conservar los mecanismos ajenos a $R_{12}$ que siguen sesgando la herencia: la supervivencia de los donantes, la conjugación de $R_{26}$, la purga de $R_{27}$, la escala de $R_{30}$, la reproducción de holones de $R_{17}$ y la decisión de recombinar de $R_{38}$, que la documentación declara como sesgos residuales (design D56 y precisión 44). Su dirección es una expectativa declarada, no un requisito.

#### Scenario: Mecanismos conservados en drift
- **WHEN** se compara la condición `drift` de `25a` con la `full`
- **THEN** difieren sólo en `reproduction_mode == "neutral"`, y `enable_plasmid_hgt`, `enable_crispr_immunity`, `enable_sos_mutation` y `enable_recombination` siguen en `True`.

### Requirement: Corrección de Holm–Bonferroni
Los p-valores crudos de `C13`..`C18` SHALL corregirse por Holm–Bonferroni con $m = 6$ y $\alpha = 0.05$: ordenados de menor a mayor, el ajustado de la posición $i$ es $\max_{j \le i} \min(1, (m - j + 1)\, p_{(j)})$.

#### Scenario: Ajuste de Holm
- **WHEN** los p-valores crudos de `C13`..`C18` son 0.001, 0.004, 0.03, 0.02, 0.2 y 0.5
- **THEN** los ajustados son 0.006, 0.02, 0.09, 0.08, 0.4 y 0.5, y sólo `C13` y `C14` quedan por debajo de $\alpha$.

### Requirement: Estado de las Afirmaciones de la Fase II-B
`ClaimStatus` SHALL agregar `OBSERVED = "OBSERVED"`, sólo para la Fase II-B. Una afirmación de `PHASE25_CLAIMS` SHALL ser `OBSERVED` si su p-valor ajustado es menor que $\alpha = 0.05$ y la mediana de sus diferencias pareadas es al menos su umbral de efecto, y `NOT_OBSERVED` en otro caso; su evaluación SHALL informar siempre el p-valor crudo, el ajustado, la mediana y la demografía.

#### Scenario: Significativa pero con efecto chico
- **WHEN** `C13` tiene p-valor ajustado 0.006 y mediana de diferencias 0.03, menor que su umbral de efecto $\delta_{\min} = 0.05$
- **THEN** su estado es `NOT_OBSERVED`, y la evaluación informa los dos p-valores, la mediana y la demografía.

#### Scenario: Efecto grande sin significancia
- **WHEN** `C17` tiene mediana 2.0 y p-valor ajustado 0.08
- **THEN** su estado es `NOT_OBSERVED`.

#### Scenario: Estados previos intactos
- **WHEN** se evalúan `C1`..`C8`
- **THEN** ninguna recibe `ClaimStatus.OBSERVED`, y los demás miembros de `ClaimStatus` no cambian.

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

### Requirement: Efectos de Regla Exploratorios
Los `rule_effects` de la Fase II-B SHALL tener una variante por regla de `PHASE25_ALL_RULES`, salvo las de `PHASE25_INACTIVE_RULES` del protocolo, SHALL medirse sólo con `PHASE25_RULE_EFFECT_SEEDS = tuple(range(42, 52))` y SHALL quedar fuera de la corrección de Holm y del estado de las afirmaciones.

#### Scenario: Efectos fuera de la prueba
- **WHEN** se evalúa `C14` con `PHASE25_SEEDS`
- **THEN** sus `rule_effects` usan sólo `PHASE25_RULE_EFFECT_SEEDS`, y cambiar sus valores no altera el p-valor ajustado ni el estado de ninguna afirmación.

#### Scenario: Regla inactiva sin variante
- **WHEN** se generan los `rule_effects` de `C13` sobre `25a`
- **THEN** ninguna regla de `PHASE25_INACTIVE_RULES["25a"]`, como `R25` o `R31`, recibe variante.

### Requirement: Reglas Inactivas por Protocolo de la Fase II-B
Según el pre-registro aprobado en la tarea 0.5 (design D56), `PHASE25_INACTIVE_RULES` SHALL ser `R14`–`R19`, `R22`, `R23`, `R25` y `R31` para `"25a"` y `"25c"`, y `R14`, `R18` y `R19` para `"25b"`. Un test SHALL contrastarlas con las configuraciones.

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
- **WHEN** se corre la prueba de humo de `25a`, `25b` y `25c` con `PHASE25_SEEDS`
- **THEN** su registro contiene, por protocolo, condición y semilla, sólo la terminación, la generación máxima y la población final, y ningún valor de las métricas de `C13`..`C18`.

### Requirement: Reportes de las Fases I y II sin Cambios
La atribución de la Fase II-B SHALL no alterar la de las fases anteriores: los reportes de `C1`..`C8` SHALL ser idénticos a los de antes del cambio.

#### Scenario: Reportes previos idénticos
- **WHEN** se corren la atribución 001-D y `run_phase2_attribution` con el mismo perfil corto y las mismas semillas antes y después del cambio
- **THEN** las evaluaciones de `C1`..`C8` son idénticas.
