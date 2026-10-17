# Spec Delta: Spatial Environments

## ADDED Requirements

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
`ToroidalGrid2D` SHALL implementar `deposit_stigmergy(agent_id, pattern, value, confidence, tick)` y `get_cell_stigmergy(agent_id) -> tuple[StigmergicTrace, ...]`, aplicando en `step_dynamics(tick)` un decaimiento `stigmergy_decay` a cada rastro con `last_updated_tick < tick` y purgando aquellos bajo `min_confidence`.

#### Scenario: Depósito, lectura y decaimiento estigmérgico
- **WHEN** con `enable_stigmergy=True` y `stigmergy_decay=0.1` el agente 1 deposita en `tick=10` un rastro de `p_0` con `confidence=0.5` en su celda, otro agente en esa celda consulta `get_cell_stigmergy` en `tick=10` y luego se ejecuta `step_dynamics(11)`
- **THEN** en `tick=10` el rastro tiene `intensity == 0.5`, y tras `step_dynamics(11)` su `intensity` es `0.4` (con tolerancia `1e-9`).
