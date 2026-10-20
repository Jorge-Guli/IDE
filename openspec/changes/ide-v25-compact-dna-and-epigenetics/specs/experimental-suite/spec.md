# Spec Delta: Experimental Suite

## ADDED Requirements

### Requirement: Telemetría Genética GeneticTickMetrics
`metrics.py` SHALL definir `GeneticTickMetrics` como `@dataclass(frozen=True)` con los 15 de D41 (`tick`, `mean_chromosome_length`, `mean_expressed_codons`, `mean_plasmids`, `endospores`, `senescent_agents`, `mean_age`, `max_age`, `explorers`, `librarians`, `nerves`, `locked_holons`, `hgt_transfers`, `crispr_rejections` y `crispr_purges`) más los 7 de D53.2 y, al final y en orden, los 4 de las precisiones 42, 43 y 49 (D53.2), 26 en total.

#### Scenario: Campos de la telemetría genética
- **WHEN** se inspeccionan los campos de `GeneticTickMetrics`
- **THEN** son exactamente los 15 de D41 más `distinct_genotypes`, `mean_functional_codons`, `regulated_expression_fraction`, `policy_divergence`, `communicating_fraction`, `new_activity` y `cumulative_new_activity`, seguidos de `mean_expressible_codons`, `cumulative_births`, `new_activity_per_birth` y `mean_age_at_death` como los cuatro últimos, en ese orden, y asignar uno de ellos lanza `dataclasses.FrozenInstanceError`.

### Requirement: Historial Genético Separado
El motor SHALL registrar un `GeneticTickMetrics` en cada tick, con cualquier combinación de banderas, en `engine.genetic_history: list[GeneticTickMetrics]`, sin agregar campos a `TickMetrics` (14 campos) ni a `EvolutionaryTickMetrics`.

#### Scenario: Registro por tick sin tocar las métricas previas
- **WHEN** se ejecutan 30 ticks con `enable_compact_dna=True`, y otros 30 con todas las banderas de la Fase II-B en `False`
- **THEN** en los dos casos `len(engine.genetic_history) == 30`, `TickMetrics` conserva sus 14 campos y `EvolutionaryTickMetrics` sus campos de la Fase II.

### Requirement: Semántica de los Campos Genéticos Heredados
En `GeneticTickMetrics`, los promedios SHALL tomarse sobre las hojas vivas al final del tick; las medias genéticas SHALL valer 0.0 sin ADN; `senescent_agents` SHALL contar las hojas con `age > lifespan`, con la edad definida por `birth_tick`; y `hgt_transfers`, `crispr_rejections` y `crispr_purges` SHALL contar los eventos del tick, no acumulados.

#### Scenario: Población sin ADN
- **WHEN** se ejecuta un tick con `enable_evolution=True`, `enable_telomere_senescence=True` y `enable_compact_dna=False`, con un agente de `age = 700` y `telomere_base_lifespan = 600`
- **THEN** el registro del tick tiene `mean_chromosome_length == 0.0`, `mean_expressed_codons == 0.0`, `mean_plasmids == 0.0` y `senescent_agents >= 1`.

#### Scenario: Eventos por tick
- **WHEN** en el tick 30 se aplican 2 transferencias y se bloquea 1, y en el tick 31 no hay conjugación
- **THEN** el registro del tick 30 tiene `crispr_rejections == 1` y el del tick 31 tiene `hgt_transfers == 0` y `crispr_rejections == 0`.

### Requirement: Telemetría Genética con la Población Vacía
Con la población vacía, los promedios de `GeneticTickMetrics` SHALL valer `0.0` y los máximos y conteos `0`; `mean_age` SHALL ser `float` y `max_age` `int`.

#### Scenario: Población extinguida
- **WHEN** se registra un tick en el que no queda ninguna hoja viva
- **THEN** `mean_age == 0.0`, `max_age == 0`, `distinct_genotypes == 0`, `mean_functional_codons == 0.0`, `mean_expressible_codons == 0.0`, `regulated_expression_fraction == 0.0` y `communicating_fraction == 0.0`.

### Requirement: Genotipos Distintos y Codones Funcionales
`distinct_genotypes` SHALL contar los cromosomas distintos entre las hojas vivas, y `mean_functional_codons`, que es descriptiva y no mide ninguna afirmación (design precisión 42), SHALL ser la media de los codones con destino de rasgo (`0x00`–`0x08`, `0x0A`–`0x0C`) o de conducta (`0x40`–`0x47`) y modo distinto de 3, cualquiera sea su promotor.

#### Scenario: Codones funcionales del fundador conductual
- **WHEN** se registra el tick de una población con el ADN fundador de `enable_genetic_policy=True`, sin mutación
- **THEN** `distinct_genotypes == 1` y `mean_functional_codons == 13.0`: los 9 codones de rasgo `0x00`–`0x08` y los 4 de conducta.

#### Scenario: Codón inerte por su modo
- **WHEN** una hoja porta un codón con destino `0x40` y modo 3
- **THEN** ese codón no cuenta en `mean_functional_codons`.

### Requirement: Codones Expresables de una Hoja
Para cada hoja viva con ADN, las métricas de C13 y C17 SHALL usar `expressible_codons(agent.dna, config.enable_holonic_hierarchy)`, que depende sólo del genotipo y del protocolo: SHALL NOT depender de si la hoja decidió en el tick, de si está en endospora, de su `last_context` ni de las señales del entorno (design precisión 42).

#### Scenario: Independencia del estado del tick
- **WHEN** dos hojas vivas portan el mismo ADN, una en endospora y sin decidir en el tick y otra activa, con distinta energía y distinto rol
- **THEN** las dos aportan los mismos valores a `mean_expressible_codons` y a `regulated_expression_fraction`.

### Requirement: Complejidad Genética Expresable
`mean_expressible_codons` SHALL ser la media, sobre las hojas vivas con ADN, de `len(expressible_codons(agent.dna, config.enable_holonic_hierarchy))`, la cantidad de valores distintos de sus codones funcionales expresables, de modo que duplicar un codón o acumular codones inertes no suma complejidad (design precisión 42).

#### Scenario: Fundador conductual
- **WHEN** se registra un tick en el que todas las hojas portan el ADN fundador de `enable_genetic_policy=True`, sin mutación
- **THEN** `mean_expressible_codons == 13.0`.

#### Scenario: Duplicados e inertes no suman
- **WHEN** la única hoja viva porta, sin política genética, el ADN fundador más una copia de su codón sobre el destino `0x00`, un codón de modo 3 sobre el destino `0x01` y un codón aditivo sobre el destino reservado `0x0D`
- **THEN** `mean_expressible_codons == 9.0` y `mean_functional_codons == 10.0`, que cuenta la copia.

#### Scenario: Codón con promotor reservado
- **WHEN** la única hoja viva porta el ADN fundador conductual más un codón aditivo de destino `0x43` con el promotor reservado `0x0B`
- **THEN** `mean_expressible_codons == 13.0`, porque ese codón no es expresable.

### Requirement: Fracción de Expresión Regulada
`regulated_expression_fraction` SHALL ser la media, sobre las hojas vivas con ADN, de la fracción de los valores de `expressible_codons(agent.dna, config.enable_holonic_hierarchy)` cuyo promotor es condicional; una hoja sin codones expresables SHALL aportar 0.0 (design precisión 42).

#### Scenario: Fundador sin regulación
- **WHEN** se registra un tick con el ADN fundador sin mutación
- **THEN** `regulated_expression_fraction == 0.0`, porque todos sus codones usan el promotor constitutivo `0x00`.

#### Scenario: Promotor de nivel con holones
- **WHEN** con `enable_holonic_hierarchy=True` la única hoja viva tiene 4 codones expresables distintos y 1 de ellos tiene el promotor `0x01` (`SOLITARY_L0`)
- **THEN** `regulated_expression_fraction == pytest.approx(0.25, abs=1e-9)`.

#### Scenario: Promotor de nivel sin holones
- **WHEN** con `enable_holonic_hierarchy=False` la única hoja viva tiene 4 codones expresables distintos y 1 de ellos tiene el promotor `0x01` (`SOLITARY_L0`)
- **THEN** `regulated_expression_fraction == 0.0`, porque sin holones ese promotor es constitutivo.

#### Scenario: Promotor de estrés
- **WHEN** con `enable_holonic_hierarchy=False` la única hoja viva tiene 5 codones expresables distintos y 1 de ellos tiene el promotor `0x18`
- **THEN** `regulated_expression_fraction == pytest.approx(0.2, abs=1e-9)`.

#### Scenario: Hoja sin codones expresables
- **WHEN** hay dos hojas vivas con ADN, una con fracción 0.5 y otra sin ningún codón expresable
- **THEN** `regulated_expression_fraction == pytest.approx(0.25, abs=1e-9)`.

### Requirement: Divergencia de la Conducta
`policy_divergence` SHALL ser, entre las decisiones del tick tomadas con la política genética (0.0 si no hay ninguna), la fracción en que la primera conducta factible según el ADN del agente difiere de la del ADN fundador, evaluadas con las mismas señales y factibilidades, con `EXPLORE` factible si hay recursos desconocidos alcanzables, sin extraer de ningún generador.

#### Scenario: Fundador sin divergencia
- **WHEN** toda la población porta el ADN fundador conductual
- **THEN** `policy_divergence == 0.0`.

#### Scenario: Sin decisiones genéticas
- **WHEN** se registra un tick con `enable_genetic_policy=False`
- **THEN** `policy_divergence == 0.0`.

#### Scenario: Sin consumo de generadores
- **WHEN** se calcula `policy_divergence` en un tick
- **THEN** el estado del generador principal y de `evo_rng` es el mismo que sin calcularla, y los historiales no cambian.

### Requirement: Fracción Comunicante
`communicating_fraction` SHALL ser la fracción de hojas vivas que no están en endospora con `comm_propensity >= 0.5` expresada.

#### Scenario: Comunicación desde cero
- **WHEN** se registra el primer tick de una población fundadora con `comm_propensity_base = 0.0`
- **THEN** `communicating_fraction == 0.0`.

### Requirement: Actividad Evolutiva de Bedau–Packard
Para cada codón distinto $c$ ausente del cromosoma de `founder_dna(config)`, la actividad $a_c(t)$ SHALL ser la suma, sobre los ticks $s \le t$, de las hojas vivas que portan $c$, en el cromosoma o en los plásmidos, en $s$; cada hoja aporta 1 por codón distinto. `new_activity` SHALL contar los codones con $a_c(t-1) <$ `activity_threshold` $\le a_c(t)$, y `cumulative_new_activity` SHALL ser su suma acumulada (design precisión 43).

#### Scenario: Cruce del umbral
- **WHEN** con `activity_threshold = 500`, 100 hojas vivas portan durante 5 ticks el ADN fundador más un mismo codón $c$ ausente del fundador
- **THEN** en el quinto tick `new_activity == 1` y `cumulative_new_activity == 1`, y en los ticks anteriores `new_activity == 0`.

#### Scenario: Los codones fundadores no cuentan
- **WHEN** con `activity_threshold = 500` y 100 hojas vivas que portan sólo el ADN fundador durante 5 ticks
- **THEN** en los 5 ticks `new_activity == 0` y `cumulative_new_activity == 0`.

#### Scenario: Una hoja cuenta una vez por codón
- **WHEN** una hoja porta el mismo codón dos veces en el cromosoma y una vez en un plásmido
- **THEN** aporta 1, no 2, a la actividad de ese codón en el tick.

### Requirement: Actividad Evolutiva por Nacimiento
`cumulative_births` SHALL ser la suma de `births` de `evolutionary_history` desde el tick 0 hasta el tick registrado (nacimientos individuales y holónicos; las perturbaciones no cuentan), y `new_activity_per_birth` SHALL ser `cumulative_new_activity / cumulative_births`, o 0.0 sin nacimientos (design precisiones 43 y 49).

#### Scenario: Sin nacimientos
- **WHEN** en el quinto tick, con hojas iniciales construidas con codones ausentes del fundador, `cumulative_new_activity == 2` y todavía no nació ningún agente
- **THEN** `cumulative_births == 0` y `new_activity_per_birth == 0.0`.

#### Scenario: Normalización por nacimientos
- **WHEN** un tick registra `cumulative_new_activity == 12` y, hasta ese tick, nacieron 300 agentes
- **THEN** `cumulative_births == 300` y `new_activity_per_birth == pytest.approx(0.04, abs=1e-9)`.

### Requirement: Edad Media al Morir
`mean_age_at_death` SHALL ser la media acumulada, sobre todas las muertes desde el tick 0 hasta el tick registrado (por hambre y por depredación), de `tick - birth_tick` del agente muerto, y 0.0 sin muertes; se informa como covariable de la longevidad (design precisiones 43 y 49).

#### Scenario: Sin muertes
- **WHEN** se registra un tick sin ninguna muerte desde el tick 0
- **THEN** `mean_age_at_death == 0.0`.

#### Scenario: Media acumulada
- **WHEN** muere en el tick 50 un agente nacido en el tick 10 y en el tick 80 otro nacido en el tick 0
- **THEN** el registro del tick 50 tiene `mean_age_at_death == pytest.approx(40.0, abs=1e-9)` y el del tick 80, `pytest.approx(60.0, abs=1e-9)`.

### Requirement: Telemetría Ecológica EcologyTickMetrics
`metrics.py` SHALL definir `EcologyTickMetrics` como `@dataclass(frozen=True)` con `tick`, `resources_available`, `shares`, `attacks`, `successful_attacks`, `predation_deaths`, `starvation_deaths`, `carcasses_deposited`, `carcasses_eaten`, `sporulations`, `recombinations`, `share_rate` y `behavior_counts`, y el motor SHALL registrar uno en cada tick en `engine.ecology_history`.

#### Scenario: Registro ecológico por tick
- **WHEN** se ejecutan 20 ticks con cualquier combinación de banderas
- **THEN** `len(engine.ecology_history) == 20`, los campos son exactamente los 13 enumerados y asignar uno lanza `dataclasses.FrozenInstanceError`.

### Requirement: Decisiones del Tick
Las decisiones del tick SHALL ser las de las hojas vivas que no estaban en endospora en la Fase 3, incluidas las que terminan en `IDLE`; son el denominador de `share_rate` y, entre las tomadas con la política genética, el de `policy_divergence`.

#### Scenario: Endosporas e IDLE
- **WHEN** en un tick deciden 10 hojas, 2 de ellas con `IDLE`, y otras 3 hojas están en endospora
- **THEN** el tick tiene 10 decisiones.

### Requirement: Semántica de los Campos Ecológicos
`share_rate` SHALL ser `shares` dividido por las decisiones del tick (0.0 sin decisiones); `behavior_counts` SHALL ser una tupla con las decisiones de cada `Behavior` del tick, en el orden de la tabla de design D46; y `predation_deaths` SHALL contar las muertes del tick de agentes atacados con éxito en ese tick.

#### Scenario: Tasa de transferencia
- **WHEN** en un tick hay 40 decisiones y 2 transferencias `SHARE` ejecutadas
- **THEN** `shares == 2` y `share_rate == pytest.approx(0.05, abs=1e-9)`.

#### Scenario: Sin decisiones
- **WHEN** en un tick no decide ninguna hoja
- **THEN** `share_rate == 0.0`.

#### Scenario: Conteo de conductas
- **WHEN** en un tick se decide `CONSUME` 3 veces y `WANDER` 1 vez con la política genética
- **THEN** `behavior_counts` tiene 8 entradas, `behavior_counts[0] == 3`, `behavior_counts[3] == 1` y las demás valen 0.

### Requirement: Observadores de Telemetría
La telemetría SHALL producirse en observadores (`TickObserver`): `TickMetricsObserver` produce `TickMetrics` y juzga M2 en `on_decisions`, antes de ejecutar las acciones; `EvolutionaryMetricsObserver`, `GeneticMetricsObserver` y `EcologyMetricsObserver` producen sus historiales en `on_tick_end`.

#### Scenario: M2 antes de ejecutar
- **WHEN** un agente decide consumir un recurso que en la Fase 4 se agota por la acción de otro
- **THEN** M2 juzga su decisión con el oráculo consultado en `on_decisions`, igual que antes del refactor.

#### Scenario: Historiales idénticos tras el refactor
- **WHEN** se corren `002a` y `003a` con las banderas por defecto antes y después de mover la telemetría a observadores
- **THEN** `history` y `evolutionary_history` son idénticos.

### Requirement: Línea Base y Criterio de Rendimiento del Refactor
Antes del bloque 6 SHALL registrarse el benchmark (`python -m ide.experiments.benchmark` y `--compact-dna`); después de los bloques 6 y 7, los ticks por segundo de cada una de las dos variantes SHALL no empeorar más de un 10 % respecto de su línea base.

#### Scenario: Refactor demasiado lento
- **WHEN** la línea base sin ADN no cambia y la de `--compact-dna` registra 150 ticks por segundo y, tras el refactor, da 132
- **THEN** el bloque no se da por completo, porque la variante con ADN empeoró un 12 %.

### Requirement: Rendimiento del Perfil Largo
Antes de la compuerta de viabilidad SHALL medirse el costo de un tick con todas las reglas de design D56 activas; si una corrida del perfil `phase25` supera los 5 minutos, el bucle SHALL optimizarse sólo con una medición previa e historiales idénticos entre la versión rápida y la actual.

#### Scenario: Optimización validada
- **WHEN** una corrida de `phase25` tarda 8 minutos y se optimiza el bucle de agentes
- **THEN** la versión optimizada produce historiales idénticos a la anterior para las mismas semillas.

### Requirement: Compuerta de Viabilidad de la Fase II-B
`src/ide/experiments/phase25_viability.py` SHALL definir `PHASE25_VIABILITY_SEEDS = tuple(range(0, 10))`, disjuntas de `PHASE25_SEEDS`, y una CLI que corre cada configuración durante el perfil `phase25` (5000 ticks) y registra por corrida sólo su población final y su generación máxima, sin calcular ninguna métrica de afirmación.

#### Scenario: Sólo demografía
- **WHEN** se corre la compuerta sobre una configuración de la grilla
- **THEN** su salida contiene, por protocolo, condición y semilla, sólo la población final y la generación máxima, y ningún valor de las métricas de `C13`–`C18`.

### Requirement: Criterio de Viabilidad
Una corrida SHALL ser viable si termina con al menos una hoja viva que no está en endospora y `max_generation >= 20`. Una configuración SHALL ser viable si, para cada protocolo de design D56 y cada una de sus condiciones `full`, `drift` y `no_predation`, al menos 9 de las 10 semillas son viables; `null_content` SHALL correrse y registrarse sin decidir la viabilidad.

#### Scenario: Una condición inviable descarta la configuración
- **WHEN** con una configuración de la grilla todas las condiciones son viables en 10 semillas salvo `no_predation` de `25a`, viable en 8
- **THEN** la configuración no es viable.

#### Scenario: Generación insuficiente
- **WHEN** una corrida termina con 30 hojas vivas y `max_generation == 19`
- **THEN** la corrida no es viable.

#### Scenario: Sólo endosporas
- **WHEN** una corrida termina con `max_generation == 25` y todas sus hojas vivas en endospora
- **THEN** la corrida no es viable.

#### Scenario: El control nulo no decide
- **WHEN** todas las condiciones `full`, `drift` y `no_predation` son viables en 9 de 10 semillas y `null_content` de `25a` sólo en 3
- **THEN** la configuración es viable, y la viabilidad de `null_content` queda registrada para E4.

### Requirement: Grilla Ordenada de la Compuerta
La compuerta SHALL probar `(resources_per_pattern, resource_regen_delay)` en el orden de menos a más abundancia `(20, 20)`, `(20, 10)`, `(30, 20)`, `(30, 10)`, `(40, 40)` y `(40, 20)`, elegir la primera configuración viable y detenerse al encontrarla, sin cambiar ningún otro campo.

#### Scenario: Detención en la primera viable
- **WHEN** `(20, 20)` no es viable y `(20, 10)` sí
- **THEN** la compuerta elige `(20, 10)` y no corre `(30, 20)` ni las siguientes.

### Requirement: Compuerta sin Configuración Viable y Registro
Si ninguna configuración de la grilla es viable, la compuerta SHALL reportarlo como resultado sin probar valores fuera de la grilla; su salida completa SHALL registrarse en `registros/` y en `docs/RESULTADOS.md` antes de la prueba de humo.

#### Scenario: Grilla sin viables
- **WHEN** ninguna de las seis configuraciones es viable
- **THEN** la compuerta informa que no hay configuración elegida y no corre ninguna corrida con otros valores.

### Requirement: Runner de los Protocolos de la Fase II-B
`src/ide/experiments/exp25_runner.py` SHALL implementar los protocolos `25a`, `25b` y `25c` sobre `PHASE25_PROTOCOL_CONFIGS`, con la infraestructura `ProtocolSpec` y la CLI de `phase2_cli.py` (semillas por defecto `PHASE25_SEEDS`) y reportes serializables a JSON. Los protocolos `002c`, `002d`, `002e` y `003c` no existen.

#### Scenario: Ejecución corta y serialización
- **WHEN** se ejecuta cada uno de los tres protocolos con `total_ticks=40` y se serializa su reporte a JSON
- **THEN** cada condición tiene su resumen, y el JSON es idéntico con `--jobs 1` y `--jobs 2`.

#### Scenario: Semillas por defecto
- **WHEN** se interpreta la CLI de `exp25_runner` sin `--seeds`
- **THEN** las semillas son las de `PHASE25_SEEDS`.

### Requirement: Resumen por Condición de los Protocolos 25a a 25c
El resumen de cada condición de `25a`, `25b` y `25c` SHALL incluir `final_accuracy`, `final_agents`, `final_active_agents` (hojas vivas que no están en endospora), `max_generation` y el último registro de `genetic_history` y de `ecology_history`.

#### Scenario: Contenido del resumen
- **WHEN** se ejecuta `25b` con `total_ticks=40`
- **THEN** cada condición del reporte contiene esos cuatro campos y los registros del último tick de `GeneticTickMetrics` y de `EcologyTickMetrics`, con `final_active_agents <= final_agents`.

### Requirement: Condiciones de los Protocolos 25a, 25b y 25c
Cada protocolo SHALL comparar las condiciones `full` (su configuración), `drift` (`ablate(config, ["R12"])`, reproducción neutral) y `null_content` (el control nulo de contenido); `25a` SHALL agregar `no_predation` (`ablate(config, ["R37"])`).

#### Scenario: Condiciones de 25a
- **WHEN** se generan las condiciones de `25a` sobre su configuración
- **THEN** son `full`, `drift` con `reproduction_mode == "neutral"`, `no_predation` con `enable_predation == False` y `null_content`.

#### Scenario: Condiciones de 25b y 25c
- **WHEN** se generan las condiciones de `25b` y de `25c`
- **THEN** cada una tiene exactamente `full`, `drift` y `null_content`, sin `no_predation`.
