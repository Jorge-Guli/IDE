# Spec Delta: Simulation Engine

## Purpose
Orquestar el paso del tiempo discreto ($t = 0, 1, \dots, T$) mediante un pipeline determinista de 5 fases sin coordinador cognitivo central, asegurando reproducibilidad exacta por semilla y soporte para perturbaciones experimentales (falsificación y daño con retiro de estímulo físico).

## ADDED Requirements

### Requirement: Pipeline Determinista de 5 Fases por Tick
La clase `SimulationEngine` en `src/ide/simulation/engine.py` SHALL ejecutar cada tick mediante el método `step(tick: int) -> TickMetrics` exactamente en el siguiente orden lógico:
1. **Percepción y Emisión:** Obtención de `Observation` para cada agente activo y llamada a `agent.perceive_and_emit_messages(obs, tick)` recolectando `QUERY_PATTERN` y `BROADCAST_BELIEF`.
2. **Intercambio Social y Revalidación:** Si `config.comm_enabled == True`, entrega de mensajes a vecinos dentro de `get_communication_neighbors`, llamada a `agent.process_incoming_messages(inbox, tick)` para asimilar broadcasts y generar respuestas `QUERY_RESPONSE`, y segunda entrega inmediata de `QUERY_RESPONSE` a los agentes consultantes antes de decidir.
3. **Decisión Local:** Invocación de `agent.decide_action(obs, tick, self.rng)` en cada agente activo.
4. **Ejecución Física y Aprendizaje Directo:** Aplicación de acciones en `EnvironmentPort.execute_action`, llamada a `agent.learn_from_experience` para quienes interactuaron con recursos y registro en `direct_discoverers[pattern].add(agent_id)`.
5. **Mantenimiento y Telemetría:** Llamada a `agent.decay_memory(tick)`, `env.step_dynamics(tick)` y registro de `TickMetrics`.

#### Scenario: Modo Aislado desactiva completamente el flujo social sin alterar otras fases
- **WHEN** `SimulationEngine` se ejecuta con `config.comm_enabled = False`
- **THEN** ningún mensaje `QUERY_PATTERN`, `QUERY_RESPONSE` ni `BROADCAST_BELIEF` es entregado entre agentes, y `messages_per_agent` del tick es exactamente `0.0`.

### Requirement: Eliminación de Sesgo de Orden mediante Permutación Reproducible
En cada tick $t$, `SimulationEngine` SHALL barajar el orden de procesamiento de los agentes activos utilizando exclusivamente su instancia local de `np.random.Generator` (`self.rng.permutation`).

#### Scenario: Reproducibilidad bit a bit entre dos corridas con igual semilla
- **WHEN** se instancian y ejecutan dos `SimulationEngine` independientes con el mismo objeto `SimulationConfig(seed=42)` durante 200 ticks
- **THEN** el historial de métricas, las posiciones finales de todos los agentes y el contenido exacto de cada `BoundedMemory` son 100% idénticos.

### Requirement: API de Perturbaciones Experimentales en Caliente
`SimulationEngine` SHALL mantener un registro histórico `direct_discoverers: dict[Pattern, set[int]]` con todos los agentes que alguna vez hayan experimentado directamente cada patrón, y proveer métodos explícitos para intervenir la población durante la simulación:
- `inject_false_belief(pattern: Pattern, false_value: float, confidence: float, fraction: float, tick: int) -> list[int]`
- `ablate_population(fraction: float) -> list[int]`
- `ablate_discoverers(pattern: Pattern, retire_stimulus: bool = True) -> list[int]`

#### Scenario: Ablación exacta de porcentaje poblacional
- **WHEN** hay 80 agentes activos y se invoca `ablate_population(0.50)`
- **THEN** exactamente 40 agentes seleccionados pseudoaleatoriamente son eliminados tanto del registro de agentes como del `EnvironmentPort`, quedando 40 agentes activos.

#### Scenario: Eliminación de descubridores originales y retiro de estímulo físico preserva portadores sociales
- **WHEN** el agente 1 descubre directamente el patrón $\rho_1$, lo transmite socialmente al agente 2 (quien nunca tocó el recurso físico $\rho_1$) y posteriormente se invoca `ablate_discoverers(\rho_1, retire_stimulus=True)`
- **THEN** el agente 1 es eliminado de la simulación, `env.retire_pattern_resources(\rho_1)` retira el recurso físico del mapa para impedir re-descubrimientos, y el agente 2 permanece activo conservando su creencia social sobre $\rho_1$.
