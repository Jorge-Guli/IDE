# Spatial Environments Specification

## Purpose
Proveer el entorno `ToroidalGrid2D` que cumple `EnvironmentPort`, con generación determinista de patrones, topología toroidal sin bordes, vecindades por índice espacial y ciclo de vida de recursos con retiro selectivo.

## Requirements

### Requirement: Generación Determinista de los Patrones del Mundo
`ToroidalGrid2D(config, rng)` SHALL generar `N = num_world_patterns` patrones `Pattern((("id", f"p_{i}"),))`, con `true_value = +1.0` si `i < N // 2` y `-1.0` en otro caso, y `resources_per_pattern` recursos por patrón con `resource_id` consecutivos desde 0.

#### Scenario: Equilibrio inicial
- **WHEN** se instancia con `num_world_patterns = 12` y `resources_per_pattern = 8`
- **THEN** `get_world_patterns()` asigna `+1.0` a `p_0`..`p_5` y `-1.0` a `p_6`..`p_11`, y hay 96 recursos en el tablero.

#### Scenario: Misma semilla, mismo tablero
- **WHEN** se instancian dos grillas con la misma configuración y generadores `PCG64` con la misma semilla
- **THEN** las posiciones de todos los agentes y recursos son idénticas.

### Requirement: Movimiento Toroidal
`execute_action` con `MOVE` SHALL desplazar al agente aplicando `(x + dx) % width` y `(y + dy) % height`, aceptando sólo los 8 movimientos de Moore de `MOORE_MOVES`.

#### Scenario: Cruce simultáneo de dos bordes
- **WHEN** un agente en `(width - 1, 0)` ejecuta `MOVE` con destino `(+1, -1)`
- **THEN** su nueva posición es `(0, height - 1)`.

### Requirement: Distancia y Dirección Toroidales
Para cada recurso visible, la grilla SHALL calcular `dx = ((x2 - x1 + W//2) % W) - W//2` (ídem `dy`), `distance = max(|dx|, |dy|)` y `recommended_move = (sign(dx), sign(dy))`, o `None` si `distance == 0`.

#### Scenario: Percepción a través del borde
- **WHEN** un agente en `(0, 0)` con `perception_radius = 2` tiene un recurso en `(width - 2, 0)`
- **THEN** el recurso aparece con `distance = 2`, `is_reachable_now = False` y `recommended_move = (-1, 0)`.

### Requirement: Observación Ordenada y Acotada
`get_observation` SHALL incluir sólo recursos con `distance <= perception_radius`, ordenados por `(distance, resource_id)`; `available_moves` igual a `MOORE_MOVES`; y `neighbor_ids` con los agentes a `distance <= comm_radius`, ascendentes y sin el propio agente.

#### Scenario: Recurso fuera de rango
- **WHEN** un recurso está a distancia 3 y `perception_radius = 2`
- **THEN** no aparece en `obs.visible_resources`.

### Requirement: Índice Espacial por Celda
La grilla SHALL mantener `cell_agents` y `cell_resources` actualizados en cada movimiento, consumo, reposición o eliminación, y SHALL resolver vecindades inspeccionando sólo las $(2R+1)^2$ celdas del radio.

#### Scenario: Consistencia tras moverse o ser eliminado
- **WHEN** un agente se mueve de `c_origen` a `c_destino`, o es eliminado con `remove_agents`
- **THEN** su ID ya no está en `cell_agents[c_origen]` y, si se movió, está en `cell_agents[c_destino]`.

### Requirement: Interacción y Consumo de Recursos
Un `INTERACT` sobre un recurso de la celda del agente SHALL devolver `ActionResult(INTERACT, pattern, true_value)` y retirarlo del tablero; si el recurso no existe o está en otra celda SHALL devolver `ActionResult(INTERACT, None, None)`.

#### Scenario: Dos agentes sobre el mismo recurso
- **WHEN** dos agentes de la misma celda envían `INTERACT` al mismo `resource_id` en el mismo tick
- **THEN** el primero recibe el valor real y el segundo recibe `ActionResult(INTERACT, None, None)` sin excepción.

### Requirement: Reposición de Recursos
`step_dynamics` SHALL reponer cada recurso consumido, en orden de consumo, con un `resource_id` nuevo de un contador monótono y en una celda elegida con el `rng` del entorno, salvo que su patrón esté retirado.

#### Scenario: Población estable de recursos
- **WHEN** se consume un recurso de `p_3` y luego se ejecuta `step_dynamics`
- **THEN** la cantidad de recursos de `p_3` vuelve a `resources_per_pattern` y el nuevo recurso tiene un `resource_id` nunca usado.

### Requirement: Retiro Definitivo de un Patrón
`retire_pattern_resources(pattern)` SHALL eliminar todas las instancias físicas del patrón, descartar sus reposiciones pendientes e impedir reposiciones futuras.

#### Scenario: Estímulo retirado
- **WHEN** se invoca `retire_pattern_resources(p_0)` y luego `step_dynamics` durante 50 ticks con interacciones
- **THEN** ningún recurso de `p_0` aparece en el tablero ni en ninguna `Observation`.

### Requirement: Inversión de Reglas del Mundo
`invert_world_rules(fraction, rng)` SHALL invertir el signo de `round(fraction · N)` patrones elegidos con `rng.choice` sobre la lista ordenada de patrones, en la tabla del mundo y en todos los recursos presentes y futuros, y devolver los patrones invertidos ordenados, o lanzar `ValueError` si `fraction` no está en `[0, 1]`.

#### Scenario: Shock del 50 %
- **WHEN** hay 12 patrones y se invoca `invert_world_rules(0.5, rng)`
- **THEN** se devuelven exactamente 6 patrones y cada recurso de esos patrones tiene ahora el valor opuesto.

#### Scenario: Fracción fuera de rango
- **WHEN** se invoca `fraction` es negativo, mayor que 1, infinito o NaN (por ejemplo `invert_world_rules(1.2, rng)`)
- **THEN** se lanza `ValueError` cuyo mensaje menciona `fraction`, sin consumir estado de `rng` ni alterar el mundo.

### Requirement: Inserción Espacial de Descendientes y Radios Individuales por Agente
`ToroidalGrid2D` SHALL implementar `spawn_agent_near(agent_id, anchor_agent_id, rng, perception_radius=None, comm_radius=None)` eligiendo entre las celdas de menor ocupación en la vecindad de Moore de `anchor_agent_id`, además de `set_agent_radii(agent_id, perception_radius, comm_radius)` y `get_agent_distance(agent_a, agent_b) -> int` con la distancia de Chebyshev toroidal.

#### Scenario: Nacimiento contiguo en la celda menos poblada y radio individual efectivo
- **WHEN** el progenitor `1` está en `(5, 5)`, se invoca `spawn_agent_near(80, 1, evo_rng, perception_radius=3, comm_radius=1)` y existe un recurso a distancia 3 de la celda asignada a `80`
- **THEN** el agente `80` aparece en `get_active_agent_ids()`, `get_agent_distance(1, 80) <= 1` y `get_observation(80, 0)` percibe el recurso a distancia 3.

### Requirement: Recursos Compuestos Graduados de Orden Superior
Cuando `num_composite_patterns > 0`, `ToroidalGrid2D` SHALL generar determinísticamente `num_composite_patterns` reglas `CompositeRule` de orden $m = \text{composite\_order}$ y valor $m^{\text{composite\_reward\_exponent}}$ usando un generador dedicado (`spawn_key=(3,)`), exponiéndolas vía `get_composite_rules() -> dict[Pattern, CompositeRule]`.

#### Scenario: Configuración por defecto sin recursos compuestos
- **WHEN** se instancia `ToroidalGrid2D(SimulationConfig(), rng)`
- **THEN** `get_composite_rules()` devuelve `{}` y el estado de `rng` es idéntico al de Fase I.

#### Scenario: Generación de recursos compuestos de orden m
- **WHEN** se instancia `ToroidalGrid2D` con `num_composite_patterns = 2`, `composite_order = 2` y `composite_reward_exponent = 1.5`
- **THEN** `get_composite_rules()` contiene 2 entradas para `c_0` y `c_1` cuyos `CompositeRule` exigen `(p_0, p_1)` y `(p_1, p_2)` respectivamente y tienen `composite_value == 2 ** 1.5` (con tolerancia `1e-9`).

### Requirement: Construcción de Nicho y Estigmergia Espacial (R19)
`ToroidalGrid2D` SHALL implementar `deposit_stigmergy(agent_id, pattern, value, confidence, tick)` y `get_cell_stigmergy(agent_id) -> tuple[StigmergicTrace, ...]`, aplicando en `step_dynamics(tick)` un decaimiento `stigmergy_decay` a cada rastro con `last_updated_tick < tick`, purgando aquellos bajo `min_confidence` y sin dejar en la celda un depósito cuya intensidad sea menor que `min_confidence`.

#### Scenario: Depósito, lectura y decaimiento estigmérgico
- **WHEN** con `enable_stigmergy=True`, `stigmergy_deposit_rate=1.0` y `stigmergy_decay=0.1` el agente 1 deposita en `tick=10` un rastro de `p_0` con `confidence=0.5` en su celda, otro agente en esa celda consulta `get_cell_stigmergy` en `tick=10` y luego se ejecuta `step_dynamics(11)`
- **THEN** en `tick=10` el rastro tiene `intensity == 0.5`, y tras `step_dynamics(11)` su `intensity` es `0.4` (con tolerancia `1e-9`).

#### Scenario: Depósito bajo el umbral de confianza mínima
- **WHEN** con `stigmergy_deposit_rate=0.5` y `min_confidence=0.05` la celda tiene un rastro de `p_0` depositado en `tick=3` y el agente 1 deposita en `tick=4` un rastro de `p_0` con `confidence=0.06` (intensidad `0.03`)
- **THEN** `get_cell_stigmergy` no devuelve ningún rastro de `p_0` y la celda no cuenta en `get_active_stigmergy_cells()`.

#### Scenario: Depósito bajo el umbral frente a un rastro del mismo tick
- **WHEN** con `stigmergy_deposit_rate=0.5` y `min_confidence=0.05` el agente 1 deposita en `tick=4` un rastro de `p_0` con `confidence=0.9` y otro agente de la misma celda deposita en `tick=4` un rastro de `p_0` con `confidence=0.06`, en cualquier orden
- **THEN** `get_cell_stigmergy` devuelve un único rastro de `p_0` con `intensity == 0.45` (con tolerancia `1e-9`).
