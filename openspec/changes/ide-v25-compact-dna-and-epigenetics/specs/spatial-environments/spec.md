# Spec Delta: Spatial Environments

## ADDED Requirements

### Requirement: Puerto de Entorno Ecológico
`ToroidalGrid2D` SHALL cumplir `EcologicalEnvironmentPort`, que extiende `EvolutionaryEnvironmentPort` con `get_visible_agents(agent_id) -> tuple[VisibleAgent, ...]`, `deposit_carcass(agent_id, value, tick) -> None` y `get_resource_count() -> int`. Ninguno de los tres consume generadores, y los agentes siguen sin recibir coordenadas.

#### Scenario: Consultas sin consumo de generadores
- **WHEN** se invocan `get_visible_agents` y `get_resource_count` sobre una grilla
- **THEN** el estado del generador del entorno es el mismo antes y después.

### Requirement: Agentes Visibles Ordenados
`get_visible_agents(agent_id)` SHALL devolver un `VisibleAgent` por cada otro agente a distancia de Chebyshev toroidal menor o igual que el `perception_radius` del observador, sin el propio observador, ordenados por `(distance, agent_id)`, con `recommended_move = (sign(dx), sign(dy))` hacia el agente, o `None` si `distance == 0`.

#### Scenario: Orden y dirección
- **WHEN** con `perception_radius = 2` el agente 1 está en `(5, 5)`, el agente 9 en `(6, 5)`, el agente 3 en `(5, 7)` y el agente 4 en `(5, 5)`
- **THEN** devuelve las entradas de 4, 9 y 3 en ese orden, con distancias 0, 1 y 2 y `recommended_move` `None`, `(1, 0)` y `(0, 1)`.

#### Scenario: Agente fuera del radio
- **WHEN** otro agente está a distancia 3 de un observador con `perception_radius = 2`
- **THEN** no aparece en `get_visible_agents` del observador.

### Requirement: Movimiento de Huida de un Agente Visible
El `flee_move` de cada `VisibleAgent` SHALL ser el movimiento de `MOORE_MOVES` que maximiza la distancia de Chebyshev toroidal entre la celda de destino del observador y la celda del agente visible, con desempate por el orden de `MOORE_MOVES`.

#### Scenario: Huida hacia el lado opuesto
- **WHEN** el observador está en `(5, 5)` y el agente visible en `(6, 5)`, en una grilla de 20 × 20
- **THEN** el `flee_move` de esa entrada es `(-1, -1)`, el primero de `MOORE_MOVES` entre los que dejan la distancia en 2.

### Requirement: Recursos Agotables con Agenda de Reposición (R33)
Con `enable_resource_depletion=True`, un recurso elemental consumido en el tick `t` SHALL agendarse con `due = t + delay`, con `delay = resource_regen_delay` salvo lo que fija $R_{34}$, y `step_dynamics(tick)` SHALL reponer, en orden de `(due, orden de consumo)`, los agendados con `due <= tick`, cada uno en una celda sorteada con el generador del entorno. Los recursos compuestos no cambian.

#### Scenario: Reposición diferida
- **WHEN** con `resource_regen_delay = 20` se consume en el tick 10 un recurso de `p_3`
- **THEN** después de `step_dynamics(29)` falta un recurso de `p_3`, y después de `step_dynamics(30)` la cantidad de `p_3` vuelve a `resources_per_pattern`.

#### Scenario: Orden de reposición
- **WHEN** con `resource_regen_delay = 20` se consume un recurso de `p_1` en el tick 10 y, en el tick 12, uno de `p_5` y después uno de `p_2`
- **THEN** `step_dynamics(30)` repone `p_1`, `step_dynamics(32)` repone `p_5` y luego `p_2`, y los `resource_id` nuevos crecen en ese orden.

### Requirement: Regiones de Nicho (R34)
Con `enable_heterogeneity=True`, la grilla SHALL dividirse en `num_regions` franjas verticales de ancho `grid_width // num_regions`, con la última absorbiendo el resto; el patrón elemental `p_i` (con $i$ el índice de su nombre, no su posición en el orden de `Pattern`) tiene como región propia $i \bmod$ `num_regions`, y sus recursos, al inicio y al reponerse, SHALL ubicarse en `x = x0 + int(rng.integers(ancho))` e `y = int(rng.integers(grid_height))`, con `x0` y `ancho` los de su región.

#### Scenario: Franjas con resto
- **WHEN** con `grid_width = 20` y `num_regions = 3` se instancia la grilla
- **THEN** las franjas empiezan en `x0 = 0`, `6` y `12`, con anchos 6, 6 y 8, todos los recursos de `p_4` están en `x` dentro de `[6, 11]` y, con `num_world_patterns = 12`, los de `p_10` en `x` dentro de `[6, 11]`.

#### Scenario: Reposición en la región propia
- **WHEN** con $R_{34}$ activa se consume y se repone un recurso de `p_2` con `num_regions = 3`
- **THEN** el recurso repuesto está en la franja de índice 2.

### Requirement: Estaciones (R34)
Con `enable_heterogeneity=True`, `enable_resource_depletion=True` y `season_length > 0`, la estación de un tick SHALL ser `(tick // season_length) % 2`, y si el tick de consumo de un recurso está en la estación 1 (invierno), su retardo de $R_{33}$ SHALL multiplicarse por `winter_regen_factor` y redondearse con `math.floor(x + 0.5)`. Sin $R_{33}$ o con `season_length = 0`, las estaciones son inertes.

#### Scenario: Retardo de invierno
- **WHEN** con `season_length = 100`, `resource_regen_delay = 20` y `winter_regen_factor = 3.0` se consume un recurso elemental en el tick 190
- **THEN** se agenda con `due = 250`, aunque ese tick caiga en verano.

#### Scenario: Retardo de verano
- **WHEN** con la misma configuración se consume un recurso elemental en el tick 250
- **THEN** se agenda con `due = 270`.

### Requirement: Depósito y Consumo de Cadáveres (R35)
`deposit_carcass(agent_id, value, tick)` SHALL colocar en la celda del agente, antes de que se lo quite del entorno, un recurso de patrón `CARCASS_PATTERN = Pattern((("id", "carcass"),))`, `true_value = value` y `resource_id` tomado del contador monótono del entorno. Se consume con `INTERACT` como cualquier recurso elemental y SHALL NOT reponerse.

#### Scenario: Consumo del cadáver
- **WHEN** se deposita un cadáver de valor 0.6 en la celda de un agente y otro agente de esa celda ejecuta `INTERACT` sobre él
- **THEN** recibe `ActionResult(INTERACT, CARCASS_PATTERN, 0.6)`, el cadáver sale del tablero y ningún `step_dynamics` posterior lo repone.

#### Scenario: Identificador del cadáver
- **WHEN** el contador de recursos del entorno vale 120 y se deposita un cadáver
- **THEN** el cadáver tiene `resource_id == 120` y el contador pasa a 121.

### Requirement: Retiro de Cadáveres y Patrones del Mundo
Un cadáver no consumido SHALL retirarse en `step_dynamics(tick)` cuando `tick >= tick_de_depósito + carcass_lifetime`. `CARCASS_PATTERN` SHALL NOT figurar en `get_world_patterns()`, y sí en `get_reachable_true_values`, porque es un recurso alcanzable.

#### Scenario: Vida del cadáver
- **WHEN** con `carcass_lifetime = 50` se deposita un cadáver en el tick 100 y nadie lo consume
- **THEN** sigue en el tablero después de `step_dynamics(149)`, ya no está después de `step_dynamics(150)` y `get_world_patterns()` nunca contiene `CARCASS_PATTERN`.

#### Scenario: Cadáver alcanzable para M2
- **WHEN** hay un cadáver en la celda del agente 2
- **THEN** `get_reachable_true_values(2)` incluye su `resource_id` con su valor.

### Requirement: Depósitos de Cadáveres en Orden de Tick
`deposit_carcass` SHALL recibir ticks no decrecientes, como los del motor, y lanzar `ValueError` si `tick` es menor que el del último depósito; los cadáveres SHALL retirarse en orden de depósito, y uno ya comido SHALL NOT afectar el retiro de los demás (design precisión 81).

#### Scenario: Tick decreciente
- **WHEN** se deposita un cadáver en el tick 5 y después otro en el tick 4
- **THEN** el segundo depósito lanza `ValueError`.

#### Scenario: Cadáver comido antes de vencer
- **WHEN** con `carcass_lifetime = 3` se depositan cadáveres en los ticks 0 y 1 y el primero se come en el tick 1
- **THEN** `step_dynamics(3)` no retira nada y `step_dynamics(4)` retira el segundo.

### Requirement: Conteo de Recursos Presentes
`get_resource_count()` SHALL devolver la cantidad de todos los recursos presentes en el tablero en el momento de la consulta: elementales, compuestos y cadáveres.

#### Scenario: Conteo tras un consumo diferido
- **WHEN** con $R_{33}$ activa, `num_world_patterns = 12` y `resources_per_pattern = 8` se consume un recurso y se ejecuta `step_dynamics` antes de su `due`
- **THEN** `get_resource_count()` devuelve 95, y 96 después de depositar un cadáver.

### Requirement: Entorno de la Fase II con las Reglas Ecológicas Apagadas
Con `enable_resource_depletion`, `enable_heterogeneity` y `enable_carcasses` en `False`, `ToroidalGrid2D` SHALL ubicar, consumir y reponer recursos exactamente como en la Fase II, con la misma secuencia de extracciones de su generador.

#### Scenario: Tablero idéntico al de la Fase II
- **WHEN** se ejecutan los hashes dorados de `tests/test_performance_equivalence.py` y las huellas de la Fase II con las banderas ecológicas por defecto
- **THEN** coinciden bit a bit con los registrados.

## MODIFIED Requirements

### Requirement: Reposición de Recursos
Con `enable_resource_depletion=False`, `step_dynamics` SHALL reponer cada recurso consumido, en orden de consumo, con un `resource_id` nuevo de un contador monótono y en una celda elegida con el `rng` del entorno (dentro de la región propia del patrón con $R_{34}$), salvo que su patrón esté retirado; con $R_{33}$ rige "Recursos Agotables con Agenda de Reposición (R33)", y los cadáveres de $R_{35}$ nunca se reponen.

#### Scenario: Población estable de recursos
- **WHEN** se consume un recurso de `p_3` y luego se ejecuta `step_dynamics`
- **THEN** la cantidad de recursos de `p_3` vuelve a `resources_per_pattern` y el nuevo recurso tiene un `resource_id` nunca usado.
