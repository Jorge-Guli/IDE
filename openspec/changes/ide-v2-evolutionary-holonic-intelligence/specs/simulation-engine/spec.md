# Spec Delta: Simulation Engine

## ADDED Requirements

### Requirement: Aislamiento de Secuencia Aleatoria y Compatibilidad Regresiva con Fase I
`SimulationEngine` SHALL crear un generador independiente `evo_rng` (`spawn_key=(2,)`) para las operaciones estocásticas de Fase II y, cuando las banderas de Fase II están en sus valores por defecto (`False`), `step()` SHALL preservar bit a bit `engine.history`, las posiciones y las memorias de Fase I.

#### Scenario: Equivalencia bit a bit con Fase I cuando las banderas están desactivadas
- **WHEN** se ejecuta `SimulationEngine(SimulationConfig(seed=42)).run(120)`
- **THEN** el estado final y el hash SHA-256 del historial, posiciones y memorias coinciden bit a bit con el oráculo de Fase I.

### Requirement: Sincronización Efímera en Dos Tiempos, M2 Elemental y Resolución Cooperativa Local en Fase 4
Con `enable_holonic_hierarchy=True` o `num_composite_patterns > 0`, el motor SHALL sincronizar en `_holon_tick_beliefs`, en Fase 1 y Fase 2, las creencias del holón local y los compuestos desbloqueados, excluir los recursos compuestos de M2, y resolver en Fase 4 la interacción cooperativa local o aplicar `-composite_failure_penalty`.

#### Scenario: Holón localmente conectado con memorias complementarias resuelve recurso compuesto
- **WHEN** un recurso compuesto exige $(\rho_0, \rho_1)$, el agente 1 conoce válidamente $\rho_0$, el agente 2 conoce válidamente $\rho_1$, ambos pertenecen al mismo `CompositeAgent` $U$ en celdas vecinas y el agente 1 ejecuta `INTERACT` sobre el recurso compuesto
- **THEN** la interacción tiene éxito, incrementa `composite_completions` (sin añadir el patrón compuesto a `direct_discoverers`) y el holón $U$ registra superávit cooperativo en ese tick sin emitir `QUERY_PATTERN` sobre el patrón compuesto.

#### Scenario: Individuo solitario incapaz de cubrir todos los fragmentos
- **WHEN** un `MicroAgent` fuera de cualquier holón, con capacidad $C_{\max} = 2$ y sin creencias en su caché efímero del tick, intenta consumir un recurso compuesto de orden $m = 3$
- **THEN** la interacción fracasa, no incrementa `composite_completions` y aplica la penalización `-composite_failure_penalty`.

#### Scenario: M2 se mide sólo sobre recursos elementales
- **WHEN** con `num_composite_patterns > 0` la única opción alcanzable de un agente en el tick es un recurso compuesto, o el agente decide `INTERACT` sobre un recurso compuesto
- **THEN** ese agente no suma oportunidad de decisión en `decision_opportunities` de ese tick.

### Requirement: Ciclo Metabólico, Reproductivo y Holónico en Fase 5 y Poda en Perturbaciones
En la Fase 5 de `step()`, el motor SHALL ejecutar en orden determinista: (a) causalidad descendente intra-holón ($R_{18}$), (b) costo de coordinación, fisión `SPLIT` ($R_{16}$) y fusión `BOND` ($R_{15}$), (c) cobro metabólico, muerte por inanición (podando árboles con `prune_dead_leaves`, igual que en `ablate_population` y `ablate_discoverers`) y reproducción ($R_{17}$ / $R_{12}$), y (d) registro en `evolutionary_history`.

#### Scenario: Sucesión generacional y formación de holones en una corrida evolutiva
- **WHEN** se ejecuta `SimulationEngine` con `enable_evolution=True`, `enable_cultural_inheritance=True` y `enable_holonic_hierarchy=True` durante 100 ticks en un entorno con recursos abundantes
- **THEN** `len(engine.evolutionary_history) == 100`, la población se mantiene `<= max_population` y se registran nacimientos (`births_this_tick > 0`) con `max_generation >= 1`.
