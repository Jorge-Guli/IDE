# Spec Delta: Experimental Suite

## Purpose
Proveer la medición científica (`MetricsCollector`) de las métricas M1 a M7 y el ejecutor reproducible de los protocolos del Experimento 001 (001-A Superávit, 001-B Falsificación, 001-C Daño y Persistencia), separando la validación del software de la validación de hipótesis. Los valores numéricos de los escenarios se verifican con tolerancia absoluta `1e-9`.

## ADDED Requirements

### Requirement: Validez de Creencias para las Métricas
Las métricas SHALL considerar sólo las creencias de `BoundedMemory`. Una creencia es válida si `sign(v̂) == sign(F(ρ))` y `c >= decision_conf_threshold`, y es falsa si el signo es opuesto y `c >= decision_conf_threshold`.

#### Scenario: Creencia correcta pero débil
- **WHEN** un agente cree `v̂ = +1.0` con `c = 0.30` sobre un patrón benéfico y el umbral es `0.35`
- **THEN** la creencia no cuenta como válida ni como falsa.

### Requirement: Instantánea Epistémica Pura
`knowledge_snapshot(agents, world_patterns, neighbors, config)` SHALL calcular coberturas y prevalencias sin estado interno, de modo que `record_tick` la reutilice y los protocolos puedan medir entre ticks; sin agentes activos, todos sus valores SHALL ser `0.0`.

#### Scenario: Población extinguida
- **WHEN** se invoca con `agents = {}`
- **THEN** `active_agents == 0`, todas las coberturas son `0.0` y cada patrón tiene prevalencia `0.0`, sin `ZeroDivisionError`.

### Requirement: Cobertura Individual y Colectiva (M1)
`TickMetrics` SHALL incluir `individual_coverage_mean` (media sobre agentes activos de creencias válidas / N) y `collective_coverage` (fracción de patrones con al menos un agente activo que los conoce válidamente).

#### Scenario: Cota superior de la cobertura individual
- **WHEN** se evalúa cualquier población con $C_{\max} = 3$ y $N = 12$
- **THEN** `individual_coverage_mean <= 0.25` en todos los ticks.

### Requirement: Cobertura Accesible a Un Salto (M1)
`TickMetrics.accessible_coverage_mean` SHALL ser la media, sobre agentes activos, de la fracción de patrones conocidos válidamente por el agente o por algún vecino de comunicación; sin un canal de consulta veraz (`comm_enabled` falso, `max_queries_per_tick == 0` o `comm_content_null`) SHALL ser igual a `individual_coverage_mean`.

#### Scenario: Meta-agente de tres vecinos
- **WHEN** tres agentes mutuamente vecinos conocen válidamente 3 patrones disjuntos cada uno, con $N = 12$, y no hay otros agentes
- **THEN** `accessible_coverage_mean == 0.75` mientras `individual_coverage_mean == 0.25`.

#### Scenario: Sin consulta no hay acceso
- **WHEN** los mismos tres agentes se evalúan con `max_queries_per_tick = 0`
- **THEN** `accessible_coverage_mean == individual_coverage_mean == 0.25`.

### Requirement: Juicio de Decisiones por Intención (M2)
`judge_decision(action, reachable_truth)` SHALL considerar correcta una decisión si es `INTERACT` sobre un objetivo con valor real positivo, o si no es `INTERACT` y todos los recursos alcanzables son dañinos; cualquier otro caso es incorrecto.

#### Scenario: Evitación correcta de un recurso tóxico
- **WHEN** la celda sólo contiene un recurso con valor `-1.0` y la acción es `MOVE`
- **THEN** `judge_decision` devuelve `True`.

#### Scenario: Omisión de un recurso benéfico
- **WHEN** la celda contiene un recurso con valor `+1.0` y la acción es `MOVE`
- **THEN** `judge_decision` devuelve `False`.

### Requirement: Precisión de Decisión (M2)
`TickMetrics` SHALL registrar `decision_opportunities` (agentes con recursos alcanzables al decidir), `correct_decisions`, `decision_accuracy` (0.0 sin oportunidades) y `cumulative_decision_accuracy` desde el inicio de la corrida.

#### Scenario: Tick sin oportunidades
- **WHEN** ningún agente tiene recursos alcanzables en un tick
- **THEN** `decision_accuracy == 0.0`, no se lanza `ZeroDivisionError` y `cumulative_decision_accuracy` conserva el valor acumulado.

### Requirement: Prevalencia por Patrón y Tiempo de Propagación (M3)
`TickMetrics.pattern_prevalence` SHALL dar, por patrón, la fracción de agentes activos que lo conocen válidamente; `propagation_time(history, pattern, theta)` SHALL devolver el menor `t - t_0` con prevalencia `>= theta · P_max`, donde `t_0` es el primer tick con prevalencia positiva.

#### Scenario: Patrón nunca descubierto
- **WHEN** la prevalencia de un patrón es 0 en todo el historial
- **THEN** `propagation_time` devuelve `None`.

### Requirement: Prevalencia de Creencias Falsas (M6)
`TickMetrics` SHALL incluir `pattern_false_prevalence` (por patrón, fracción de agentes con creencia falsa) y `false_belief_prevalence` (fracción de agentes con al menos una creencia falsa).

#### Scenario: Población sin falsedades
- **WHEN** ningún agente sostiene creencias de signo opuesto al real con confianza suficiente
- **THEN** `false_belief_prevalence == 0.0`.

### Requirement: Costo de Comunicación (M7)
`TickMetrics` SHALL incluir `messages_sent` (cada mensaje emitido cuenta una vez, sin importar cuántos receptores tenga) y `messages_per_agent = messages_sent / activos`, o `0.0` si no hay agentes activos. `SurplusReport.accuracy_gain_per_message` SHALL ser `collective_surplus / mean_messages_per_agent`, o `None` si el divisor es 0.

#### Scenario: Un broadcast con tres receptores
- **WHEN** en un tick el único mensaje es un `BROADCAST_BELIEF` entregado a tres vecinos
- **THEN** `messages_sent == 1`.

### Requirement: Protocolo 001-A Superávit
`run_protocol_001a_surplus(config, total_ticks=300)` SHALL correr dos motores con la misma semilla, con y sin comunicación, y devolver un `SurplusReport` con precisión, coberturas, `collective_surplus`, costo de comunicación y tiempos `t50`/`t90` por patrón.

#### Scenario: Esquema del reporte
- **WHEN** se ejecuta con `SimulationConfig(seed=42)` y `total_ticks=50`
- **THEN** devuelve un `SurplusReport` cuyos campos son exactamente los de `design.md` y `collective_surplus == collective_accuracy - isolated_accuracy`.

### Requirement: Protocolo 001-B Falsificación
`run_protocol_001b_falsification(config, total_ticks=300, injection_tick=80, injection_fraction=0.25)` SHALL inyectar en `injection_tick` el rumor `(p_0, -1.0, 0.95)` y devolver un `FalsificationReport` con prevalencia inicial (instantánea tras inyectar), pico (que incluye la inicial), final y `ticks_to_extinction` (con `k = 1` para el primer tick posterior).

#### Scenario: Prevalencia inicial exacta
- **WHEN** se ejecuta con 80 agentes e `injection_fraction = 0.25`
- **THEN** `injected_agents == 20`, `initial_injected_prevalence == 0.25`, `peak_false_prevalence >= 0.25` y `target_pattern == "id=p_0"`.

### Requirement: Protocolo 001-C Resiliencia y Persistencia
`run_protocol_001c_resilience(config, warmup_ticks=150, post_ablation_ticks=100, ablation_levels=(0.10, 0.30, 0.50, 0.70))` SHALL hacer, por cada nivel y para la ablación de descubridores de `p_0` con retiro de estímulo, una corrida nueva de `warmup_ticks` ticks, la perturbación y `post_ablation_ticks` ticks, y devolver un `ResilienceReport`.

#### Scenario: Un resultado por nivel
- **WHEN** se ejecuta con los niveles por defecto y 80 agentes
- **THEN** `ablation_results` tiene 4 elementos con `remaining_agents` iguales a 72, 56, 40 y 24.

### Requirement: Tiempo de Recuperación (M5)
`recovery_ticks` SHALL ser el menor `k` en `1..post_ablation_ticks` tal que la precisión ponderada (`Σ correctas / Σ oportunidades`) de los ticks post-ablación `max(1, k-19)..k` sea `>= 0.9 · pre_ablation_accuracy`, calculada ésta igual sobre los últimos 20 ticks de warmup; o `None` si no ocurre o si `pre_ablation_accuracy == 0`.

#### Scenario: Ventana sin ticks previos a la ablación
- **WHEN** se calcula `recovery_ticks` para `k = 5`
- **THEN** la ventana contiene exactamente los 5 primeros ticks posteriores a la ablación.

#### Scenario: Sin precisión previa no hay recuperación medible
- **WHEN** `pre_ablation_accuracy == 0`
- **THEN** `recovery_ticks` es `None`, aunque cualquier ventana alcance el umbral `0`.

### Requirement: Separación entre Software e Hipótesis
Los tests que afirman resultados empíricos sobre los mecanismos programados (por ejemplo, `collective_surplus > 0`) SHALL marcarse con `@pytest.mark.empirical` y quedar excluidos de `python -m pytest` por defecto; su fracaso SHALL reportarse como hallazgo, no corregirse ajustando parámetros.

#### Scenario: Corrida por defecto
- **WHEN** se ejecuta `python -m pytest` sin argumentos
- **THEN** no se ejecuta ningún test marcado `empirical`.

### Requirement: Expectativa Funcional de Superávit (H1)
H1 verifica que los mecanismos de comunicación programados cumplen su propósito; por la regla de atribución no constituye una afirmación de emergencia. Bajo `python -m pytest -m empirical`, la suite SHALL ejecutar 001-A con `total_ticks=300` para las semillas 42 a 46 y verificar en las cinco que `collective_accessible_coverage > isolated_accessible_coverage` y `collective_surplus > 0` (prueba de signo unilateral, p = 1/32).

#### Scenario: Verificación del superávit multi-semilla
- **WHEN** se ejecuta `run_protocol_001a_surplus(SimulationConfig(seed=s), total_ticks=300)` para `s` en 42..46
- **THEN** se espera que en cada reporte la cobertura accesible colectiva supere a la aislada, y que `sign_test_p_value` de los cinco `collective_surplus` sea `< 0.05`.

### Requirement: Hipótesis de Contención de Falsedad
Bajo `python -m pytest -m empirical`, la suite SHALL verificar, para las semillas 42 a 46, que la prevalencia final del rumor falso es menor que la inicial.

#### Scenario: Contención del rumor
- **WHEN** se ejecuta `run_protocol_001b_falsification(SimulationConfig(seed=s), total_ticks=300, injection_tick=80, injection_fraction=0.25)` para `s` en 42..46
- **THEN** se espera `report.final_false_prevalence < report.initial_injected_prevalence`.

### Requirement: Agregación Multi-Semilla y Prueba de Signo
`aggregate_reports` SHALL devolver por campo numérico `mean`, `std` (`ddof=0`) y `n`, por campo `bool` la fracción de `True`, por campo `dict` la misma agregación por clave, excluyendo `None`; `sign_test_p_value(d)` SHALL devolver `Σ_{i=s..n} C(n,i)/2^n` descartando ceros (1.0 si `n == 0`).

#### Scenario: Cinco diferencias positivas
- **WHEN** se invoca `sign_test_p_value([0.1, 0.2, 0.05, 0.3, 0.01])`
- **THEN** devuelve `0.03125`.

#### Scenario: Valores ausentes
- **WHEN** se agregan dos reportes cuyo `propagation_t50["id=p_3"]` vale `12` y `None`
- **THEN** la entrada de `id=p_3` tiene `mean == 12` y `n == 1`.

### Requirement: CLI Reproducible Multi-Semilla
`python -m ide.experiments.exp001_runner` SHALL aceptar `--profile {quick,full}` (por defecto `full`), `--seeds` (por defecto `42`), `--out` (por defecto `results/`) y `--jobs` (por defecto `1`), y escribir por semilla un JSON con la configuración y los tres reportes, un CSV de series temporales de 001-A y, con varias semillas, un JSON agregado con media y desvío.

#### Scenario: Valores por defecto
- **WHEN** se ejecuta `build_arg_parser().parse_args([])`
- **THEN** el perfil es `full`, las semillas son `[42]`, el directorio de salida es `results/` y `jobs == 1`.

#### Scenario: Paralelismo inocuo
- **WHEN** se ejecuta `--profile quick --seeds 42 43` una vez con `--jobs 1` y otra con `--jobs 2`
- **THEN** todos los archivos generados son idénticos byte a byte.

#### Scenario: Determinismo entre procesos
- **WHEN** se ejecuta `--profile quick --seeds 42` dos veces, con `PYTHONHASHSEED=0` y con `PYTHONHASHSEED=1`
- **THEN** los archivos `exp001_seed42.json` generados son idénticos byte a byte.
