# Spec Delta: Simulation Engine

## ADDED Requirements

### Requirement: Aislamiento de Secuencia Aleatoria y Compatibilidad Regresiva con Fase I
`SimulationEngine` SHALL crear un tercer generador independiente `evo_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(config.seed, spawn_key=(2,))))` para todas las operaciones estocásticas de Fase II (mutación genética, reproducción y dinámica holónica), y cuando las banderas de Fase II están en sus valores por defecto (`False`), `step()` SHALL ejecutar exactamente las mismas llamadas y extracciones sobre `self.rng` que en Fase I, preservando bit a bit `engine.history`, las posiciones y las memorias.

#### Scenario: Equivalencia bit a bit con Fase I cuando las banderas están desactivadas
- **WHEN** se ejecuta `SimulationEngine(SimulationConfig(seed=42)).run(120)`
- **THEN** el estado final y el hash SHA-256 del historial, posiciones y memorias coinciden bit a bit con el oráculo de Fase I.

### Requirement: Sincronización Efímera en Dos Tiempos, Verdad Efectiva en Fase 3 y Resolución Cooperativa Local en Fase 4
Cuando `enable_holonic_hierarchy=True` o `num_composite_patterns > 0`, el motor SHALL sincronizar en el buffer efímero de holón del agente (`clear_holon_beliefs` + `inject_ephemeral_belief`) las creencias de las hojas localmente conectadas de su holón (distancia toroidal $\le \max(r_{\text{com}}) + 1$) y las creencias compuestas sintetizadas tanto en la Fase 1 (antes de `perceive_and_emit_messages`, evitando consultas `QUERY_PATTERN` redundantes sin ser borradas por `_ephemeral_tick_beliefs.clear()`) como al cierre de la Fase 2 (antes de `decide_action`). En la Fase 3, al evaluar `judge_decision` sobre un recurso compuesto en la celda del agente, su valor efectivo en `truth` SHALL ser `+rule.composite_value` si el agente tiene el patrón compuesto desbloqueado en `get_effective_belief` y `-composite_failure_penalty` en caso contrario. En la Fase 4, cuando un agente interactúa con un recurso cuyo `pattern` pertenece a `env.get_composite_rules()`, el motor SHALL verificar si las hojas localmente conectadas del nodo raíz $U$ conocen como benéficos todos los `required_patterns` de la `CompositeRule`: si es así, incrementa `composite_completions`, registra superávit cooperativo en $U$ y reparte la ganancia energética entre dichas hojas (sin registrar patrones compuestos en `direct_discoverers`); si no, aplica al agente la penalización `-composite_failure_penalty`.

#### Scenario: Holón localmente conectado con memorias complementarias resuelve recurso compuesto
- **WHEN** un recurso compuesto exige $(\rho_0, \rho_1)$, el agente 1 conoce válidamente $\rho_0$, el agente 2 conoce válidamente $\rho_1$, ambos pertenecen al mismo `CompositeAgent` $U$ en celdas vecinas y el agente 1 ejecuta `INTERACT` sobre el recurso compuesto
- **THEN** la interacción tiene éxito, incrementa `composite_completions` y el holón $U$ registra superávit cooperativo en ese tick sin emitir `QUERY_PATTERN` sobre el patrón compuesto.

#### Scenario: Individuo solitario incapaz de cubrir todos los fragmentos
- **WHEN** un `MicroAgent` fuera de cualquier holón y con capacidad $C_{\max} = 2$ intenta consumir un recurso compuesto de orden $m = 3$
- **THEN** la interacción fracasa, no incrementa `composite_completions` y aplica la penalización `-composite_failure_penalty`.

### Requirement: Ciclo Metabólico, Reproductivo y Holónico en Fase 5 y Poda en Perturbaciones
En la Fase 5 de `step()`, tras el decaimiento de memoria y `env.step_dynamics(tick)`, el motor SHALL ejecutar en orden determinista: (a) si `enable_downward_causation=True`, actualizar la penalización de redundancia intra-holón ($\psi_{\text{red}}$) en las memorias de las hojas de cada `CompositeAgent`; (b) si `enable_holonic_hierarchy=True`, aplicar el costo de coordinación, evaluar fisiones `SPLIT` ($R_{16}$) y evaluar fusiones `BOND` ($R_{15}$); (c) si `enable_evolution=True`, aplicar el metabolismo energético, eliminar a los agentes con $E_i(t) \le 0$ (podando con `prune_dead_leaves` los árboles holónicos afectados, igual que en `ablate_population` y `ablate_discoverers`), y ejecutar a lo sumo un evento reproductivo por agente por tick (vía reproducción simbiótica de holones $R_{17}$ o individual $R_{12}$) respetando `max_population`; y (d) registrar `EvolutionaryTickMetrics` en `engine.evolutionary_history`.

#### Scenario: Sucesión generacional y formación de holones en una corrida evolutiva
- **WHEN** se ejecuta `SimulationEngine` con `enable_evolution=True`, `enable_cultural_inheritance=True` y `enable_holonic_hierarchy=True` durante 100 ticks en un entorno con recursos abundantes
- **THEN** `len(engine.evolutionary_history) == 100`, la población se mantiene `<= max_population` y se registran nacimientos (`births_this_tick > 0`) con `max_generation >= 1`.
