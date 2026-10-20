# Simulation Engine Specification

## Purpose
Orquestar el tiempo discreto mediante un pipeline determinista de 5 fases sin coordinador cognitivo central, con reproducibilidad exacta por semilla y perturbaciones experimentales (falsificación y daño con retiro de estímulo).

## Requirements

### Requirement: Construcción Reproducible
`SimulationEngine(config, env=None, trust_strategy=None)` SHALL crear un único `np.random.Generator(np.random.PCG64(config.seed))`, construir `ToroidalGrid2D(config, rng)` si no se provee entorno, crear un `MicroAgent` por agente activo y lanzar `NotImplementedError` si `enable_specialization` es verdadero, si `epsilon_recheck > 0`, si `tau_policy` no es `"validation"` o si `update_scheme` no es `"synchronous"`.

#### Scenario: Especialización fuera de alcance
- **WHEN** se instancia con `SimulationConfig(enable_specialization=True)`
- **THEN** se lanza `NotImplementedError`.

#### Scenario: Mecanismos del Experimento 004 aún no implementados
- **WHEN** se instancia con `SimulationConfig(epsilon_recheck=0.1)`, con `SimulationConfig(tau_policy="evidence_age")` o con `SimulationConfig(update_scheme="asynchronous")`
- **THEN** se lanza `NotImplementedError`.

### Requirement: Orden de Fases del Tick
`step()` SHALL ejecutar el tick `next_tick` en este orden y luego incrementarlo: (1) observación y emisión; (2) intercambio social en dos pasadas; (3) decisión de todos los agentes; (4) ejecución y aprendizaje directo; (5) decaimiento, `step_dynamics` y registro de `TickMetrics`.

#### Scenario: Decisiones sobre la misma instantánea
- **WHEN** dos agentes de la misma celda observan el mismo recurso benéfico
- **THEN** ambos deciden a partir de la observación de la fase 1, aunque el primero lo consuma en la fase 4.

### Requirement: Resolución de Conflictos por Prioridad Aleatoria
Con `update_scheme="synchronous"`, la percepción, la comunicación y la decisión SHALL ser simultáneas, y cuando varios agentes intenten consumir el mismo recurso en el mismo tick, SHALL obtenerlo el que aparezca primero en la permutación del tick.

#### Scenario: Sorteo de un recurso disputado
- **WHEN** los agentes 3 y 8 están en la misma celda, ambos deciden `INTERACT` sobre el mismo recurso, y en la permutación del tick 8 aparece antes que 3
- **THEN** el agente 8 recibe el valor real y el agente 3 recibe `ActionResult(INTERACT, None, None)`.

### Requirement: Permutación Reproducible del Orden de Agentes
En cada tick el motor SHALL procesar a los agentes en el orden `rng.permutation(sorted(activos))`, usando ese mismo orden en todas las fases del tick.

#### Scenario: Orden independiente del hash
- **WHEN** se ejecuta el mismo tick con dos valores distintos de `PYTHONHASHSEED`
- **THEN** el orden de procesamiento es idéntico.

### Requirement: Intercambio Social en Dos Pasadas
Con `comm_enabled`, el motor SHALL entregar cada mensaje emitido a los `neighbor_ids` de la observación de la fase 1 del emisor (o sólo a `recipient_id` si figura entre ellos), recolectar los `QUERY_RESPONSE` de la primera pasada y entregarlos en una segunda pasada antes de la fase de decisión.

#### Scenario: Consulta resuelta en el mismo tick
- **WHEN** el agente 1 consulta por $\rho_5$ y su vecino 2 lo conoce como dañino con `c = 0.85`
- **THEN** en la fase de decisión del mismo tick el agente 1 ya tiene una creencia efectiva sobre $\rho_5$.

#### Scenario: Ruteo con los vecinos de la observación
- **WHEN** un entorno de prueba devuelve en cada observación `neighbor_ids == (0,)`, salvo para el agente 0, que recibe `(1,)`, distintos de los vecinos reales
- **THEN** en la primera pasada sólo los agentes 0 y 1 reciben mensajes, y el agente 0 recibe los de los demás emisores.

### Requirement: Control Nulo de Contenido en el Ruteo
Con `comm_content_null=True`, el motor SHALL aplicar `nullify_belief` a cada entrega (mensaje × receptor, en orden de emisión y de receptor ascendente, en ambas pasadas) usando `null_rng`, un generador `PCG64(SeedSequence(seed, spawn_key=(1,)))` distinto del principal.

#### Scenario: Determinismo del control nulo
- **WHEN** se ejecutan dos motores con `SimulationConfig(seed=42, comm_content_null=True)` durante 100 ticks
- **THEN** sus historiales son idénticos.

### Requirement: Modo Aislado
Con `comm_enabled` falso, el motor SHALL descartar todos los mensajes emitidos sin entregarlos y registrar `messages_sent = 0`, sin alterar las demás fases.

#### Scenario: Ninguna creencia social
- **WHEN** se ejecutan 100 ticks con `comm_enabled = False`
- **THEN** ninguna creencia en ninguna memoria tiene `from_direct_experience = False` y `messages_per_agent` es `0.0` en todos los ticks.

### Requirement: Registro de Descubridores Directos
El motor SHALL agregar `agent_id` a `direct_discoverers[pattern]` cada vez que `execute_action` devuelva un `experienced_value` distinto de `None`, y pasar esa experiencia a `learn_from_experience`.

#### Scenario: Primera interacción registrada
- **WHEN** el agente 7 consume un recurso de $\rho_3$
- **THEN** `7 in engine.direct_discoverers[ρ3]` y su memoria tiene una creencia directa sobre $\rho_3$.

### Requirement: Reproducibilidad Bit a Bit
Dos motores construidos con la misma `SimulationConfig` SHALL producir historiales de `TickMetrics`, posiciones finales y contenidos de memoria idénticos tras el mismo número de ticks.

#### Scenario: Dos corridas con seed=42
- **WHEN** se ejecutan dos motores independientes con `SimulationConfig(seed=42)` durante 200 ticks
- **THEN** los historiales son iguales con `==`, igual que las posiciones de todos los agentes y `all_units()` de cada memoria.

### Requirement: Inyección de Rumor Falso
`inject_false_belief(pattern, false_value, confidence, fraction)` SHALL elegir `round(fraction · M)` agentes con `rng.choice` sin reemplazo sobre los activos ordenados e insertarles con `force=True` la creencia `(pattern, false_value, confidence, 1, next_tick, from_direct_experience=False)`, devolviendo sus IDs ordenados.

#### Scenario: Inyección en el 25 %
- **WHEN** hay 80 agentes activos y se invoca `inject_false_belief(p_0, -1.0, 0.95, 0.25)`
- **THEN** se devuelven 20 IDs y cada uno tiene en memoria `p_0` con `predicted_value = -1.0` y `confidence = 0.95`.

### Requirement: Ablación Poblacional
`ablate_population(fraction)` SHALL eliminar del motor y del entorno `round(fraction · M)` agentes elegidos con `rng.choice` sin reemplazo sobre los activos ordenados, y devolver sus IDs ordenados.

#### Scenario: Ablación del 50 %
- **WHEN** hay 80 agentes activos y se invoca `ablate_population(0.50)`
- **THEN** se eliminan exactamente 40 agentes del motor y del entorno, y quedan 40 activos.

### Requirement: Instantánea Epistémica sin Avanzar el Tiempo
`SimulationEngine.snapshot()` SHALL devolver `knowledge_snapshot` del estado actual sin ejecutar ticks ni modificar `history`, `next_tick` ni el acumulado de M2.

#### Scenario: Medición inmediatamente después de una ablación
- **WHEN** tras 50 ticks se invoca `ablate_population(0.5)` y luego `snapshot()` dos veces
- **THEN** ambas instantáneas son iguales, `active_agents == 40`, y `len(history)` y `next_tick` siguen siendo 50.

### Requirement: Ablación de Descubridores con Retiro de Estímulo
`ablate_discoverers(pattern, retire_stimulus=True)` SHALL eliminar a todos los agentes activos de `direct_discoverers[pattern]` y, si `retire_stimulus` es verdadero, invocar `env.retire_pattern_resources(pattern)`.

#### Scenario: El portador social sobrevive
- **WHEN** el agente 1 descubre $\rho_1$, se lo transmite al agente 2 (que nunca tocó $\rho_1$) y se invoca `ablate_discoverers(ρ1)`
- **THEN** el agente 1 es eliminado, no quedan recursos de $\rho_1$ en el entorno y el agente 2 sigue activo con su creencia social sobre $\rho_1$.

### Requirement: Aislamiento de Secuencia Aleatoria y Compatibilidad Regresiva con Fase I
`SimulationEngine` SHALL crear un generador independiente `evo_rng` (`spawn_key=(2,)`) para las operaciones estocásticas de Fase II y, cuando las banderas de Fase II están en sus valores por defecto (`False`), `step()` SHALL preservar bit a bit `engine.history`, las posiciones y las memorias de Fase I.

#### Scenario: Equivalencia bit a bit con Fase I cuando las banderas están desactivadas
- **WHEN** se ejecuta `SimulationEngine(SimulationConfig(seed=42)).run(120)`
- **THEN** el estado final y el hash SHA-256 del historial, posiciones y memorias coinciden bit a bit con el oráculo de Fase I.

### Requirement: Vista del Holón en Dos Tiempos (R22)
Con `enable_holonic_hierarchy=True` y `enable_holon_view=True`, el motor SHALL inyectar en `_holon_tick_beliefs` de cada hoja, antes de `perceive_and_emit_messages` (leyendo memorias) y al final de la Fase 2 (leyendo `own_belief`), la mejor creencia de las hojas de su holón en alcance local, calculando primero la vista de todos y luego inyectando.

#### Scenario: El holón evita consultas sobre lo que ya sabe
- **WHEN** con `max_broadcast_per_tick=0` (sin difusión espontánea) los agentes 1 y 2 forman un holón en alcance local, el agente 2 conoce válidamente $\rho_1$ en su memoria (`confidence >= decision_conf_threshold`) y el agente 1 ve un recurso de patrón $\rho_1$ en el tick
- **THEN** el agente 1 no emite `QUERY_PATTERN` sobre $\rho_1$ en ese tick y su `own_belief(ρ_1)` sigue siendo `None`.

#### Scenario: Ablación de la vista del holón
- **WHEN** se repite la situación anterior con `enable_holon_view=False`
- **THEN** el agente 1 emite `QUERY_PATTERN` sobre $\rho_1$ como en Fase I y su `_holon_tick_beliefs` queda vacío.

### Requirement: Recursos Compuestos Aprendidos por Experiencia y M2 Elemental
Con `num_composite_patterns > 0`, el motor SHALL resolver en Fase 4 el `INTERACT` sobre un compuesto con el conocimiento propio (`own_belief`) de las hojas locales del nodo raíz del agente, hacer que el agente aprenda `+1.0` si tiene éxito o `-composite_failure_penalty` si fracasa, no inyectar compuestos a ningún agente y excluir los compuestos de M2.

#### Scenario: Holón localmente conectado con memorias complementarias resuelve recurso compuesto
- **WHEN** un recurso compuesto exige $(\rho_0, \rho_1)$, el agente 1 conoce válidamente $\rho_0$, el agente 2 conoce válidamente $\rho_1$, ambos pertenecen al mismo `CompositeAgent` $U$ en celdas vecinas y el agente 1 ejecuta `INTERACT` sobre el recurso compuesto
- **THEN** la interacción tiene éxito, incrementa `composite_completions` (sin añadir el patrón compuesto a `direct_discoverers`), el agente 1 queda con una creencia directa del patrón compuesto con $\hat{v} > 0$, y $U$ registra superávit cooperativo en ese tick.

#### Scenario: Individuo solitario incapaz de cubrir todos los fragmentos
- **WHEN** un `MicroAgent` fuera de cualquier holón, con capacidad $C_{\max} = 2$ y sin creencias en su caché efímero del tick, intenta consumir un recurso compuesto de orden $m = 3$
- **THEN** la interacción fracasa, no incrementa `composite_completions` y el agente aprende el patrón compuesto con $\hat{v} < 0$ (valor experimentado `-composite_failure_penalty`).

#### Scenario: Reparto de la ganancia compuesta (R23)
- **WHEN** con `enable_evolution=True` el holón del primer escenario resuelve el recurso compuesto de valor $v$, primero con `holon_energy_sharing=True` y luego con `holon_energy_sharing=False`
- **THEN** en el primer caso cada una de las dos hojas gana `energy_gain_scale * v / 2`, y en el segundo el agente 1 gana `energy_gain_scale * v` y el agente 2 no gana nada por esa interacción.

#### Scenario: M2 se mide sólo sobre recursos elementales
- **WHEN** con `num_composite_patterns > 0` la única opción alcanzable de un agente en el tick es un recurso compuesto, o el agente decide `INTERACT` sobre un recurso compuesto
- **THEN** ese agente no suma oportunidad de decisión en `decision_opportunities` de ese tick.

### Requirement: Ciclo Metabólico, Reproductivo y Holónico en Fase 5 y Poda en Perturbaciones
En la Fase 5 de `step()`, el motor SHALL ejecutar en orden determinista: (a) coordinación ($R_{23}$), `SPLIT` ($R_{16}$) y `BOND` ($R_{15}$), (b) metabolismo, muerte (poda con `prune_dead_leaves`, como en las ablaciones) y reproducción ($R_{17}$, $R_{12}$), (c) $R_{18}$ sobre el bosque resultante, todo entre `decay_memory` y `env.step_dynamics`; y (d) tras `step_dynamics`, registro en `evolutionary_history`.

#### Scenario: Sucesión generacional y formación de holones en una corrida evolutiva
- **WHEN** se ejecuta `SimulationEngine` con `enable_evolution=True`, `enable_cultural_inheritance=True` y `enable_holonic_hierarchy=True` durante 100 ticks en un entorno con recursos abundantes
- **THEN** `len(engine.evolutionary_history) == 100`, la población se mantiene `<= max_population` y se registran nacimientos (`births_this_tick > 0`) con `max_generation >= 1`.
