# Spec Delta: Simulation Engine

## ADDED Requirements

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
