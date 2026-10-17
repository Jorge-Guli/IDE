# Spec Delta: Simulation Engine

## Purpose
Orquestar el tiempo discreto mediante un pipeline determinista de 5 fases sin coordinador cognitivo central, con reproducibilidad exacta por semilla y perturbaciones experimentales (falsificación y daño con retiro de estímulo).

## ADDED Requirements

### Requirement: Construcción Reproducible
`SimulationEngine(config, env=None, trust_strategy=None)` SHALL crear un único `np.random.Generator(np.random.PCG64(config.seed))`, construir `ToroidalGrid2D(config, rng)` si no se provee entorno, crear un `MicroAgent` por agente activo y lanzar `NotImplementedError` si `config.enable_specialization` es verdadero.

#### Scenario: Especialización fuera de alcance
- **WHEN** se instancia con `SimulationConfig(enable_specialization=True)`
- **THEN** se lanza `NotImplementedError`.

### Requirement: Orden de Fases del Tick
`step()` SHALL ejecutar el tick `next_tick` en este orden y luego incrementarlo: (1) observación y emisión; (2) intercambio social en dos pasadas; (3) decisión de todos los agentes; (4) ejecución y aprendizaje directo; (5) decaimiento, `step_dynamics` y registro de `TickMetrics`.

#### Scenario: Decisiones sobre la misma instantánea
- **WHEN** dos agentes de la misma celda observan el mismo recurso benéfico
- **THEN** ambos deciden a partir de la observación de la fase 1, aunque el primero lo consuma en la fase 4.

### Requirement: Permutación Reproducible del Orden de Agentes
En cada tick el motor SHALL procesar a los agentes en el orden `rng.permutation(sorted(activos))`, usando ese mismo orden en todas las fases del tick.

#### Scenario: Orden independiente del hash
- **WHEN** se ejecuta el mismo tick con dos valores distintos de `PYTHONHASHSEED`
- **THEN** el orden de procesamiento es idéntico.

### Requirement: Intercambio Social en Dos Pasadas
Con `comm_enabled`, el motor SHALL entregar cada mensaje emitido a los vecinos de comunicación del emisor (o sólo a `recipient_id` si es vecino), recolectar los `QUERY_RESPONSE` de la primera pasada y entregarlos en una segunda pasada antes de la fase de decisión.

#### Scenario: Consulta resuelta en el mismo tick
- **WHEN** el agente 1 consulta por $\rho_5$ y su vecino 2 lo conoce como dañino con `c = 0.85`
- **THEN** en la fase de decisión del mismo tick el agente 1 ya tiene una creencia efectiva sobre $\rho_5$.

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
