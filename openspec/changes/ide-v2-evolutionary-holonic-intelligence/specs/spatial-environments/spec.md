# Spec Delta: Spatial Environments

## ADDED Requirements

### Requirement: Inserción Espacial de Descendientes y Radios Individuales por Agente
`ToroidalGrid2D` SHALL implementar `spawn_agent_near(agent_id, anchor_agent_id, rng, perception_radius=None, comm_radius=None) -> tuple[int, int]`, evaluando las 9 celdas en orden `((0, 0), *MOORE_MOVES)` alrededor de `anchor_agent_id`, filtrando las celdas `best` que minimizan `len(cell_agents[c])`, eligiendo `best[int(rng.integers(len(best)))]`, y registrando los radios individuales del agente si se especifican (o mediante `set_agent_radii`), de modo que `get_observation` y `get_communication_neighbors` respeten los radios mutados de cada agente; además SHALL proveer `get_agent_distance(agent_a, agent_b) -> int` con la distancia de Chebyshev toroidal entre dos agentes activos.

#### Scenario: Nacimiento contiguo en la celda menos poblada y radio individual efectivo
- **WHEN** el progenitor `1` está en `(5, 5)`, se invoca `spawn_agent_near(80, 1, evo_rng, perception_radius=3, comm_radius=1)` y existe un recurso a distancia 3 de la celda asignada a `80`
- **THEN** el agente `80` aparece en `get_active_agent_ids()`, `get_agent_distance(1, 80) <= 1` y `get_observation(80, 0)` percibe el recurso a distancia 3.

### Requirement: Recursos Compuestos Graduados de Orden Superior
Cuando `num_composite_patterns > 0`, `ToroidalGrid2D` SHALL generar determinísticamente `num_composite_patterns` reglas `CompositeRule` para los patrones `Pattern((("id", f"c_{k}"), ("order", str(m))))` ($0 \le k < \text{num\_composite\_patterns}$) cuyos `required_patterns` son `tuple(sorted(beneficial[(k + j) % len(beneficial)] for j in range(m)))` sobre los primeros `N // 2` patrones benéficos y cuyo valor real es `float(m ** composite_reward_exponent)`, exponiéndolas mediante `get_composite_rules() -> dict[Pattern, CompositeRule]` y generando `composite_resources_per_pattern` instancias en la grilla usando un generador dedicado (`spawn_key=(3,)`); cuando `num_composite_patterns == 0` (por defecto), no se genera ningún recurso compuesto ni se realiza ninguna extracción adicional del `rng`.

#### Scenario: Configuración por defecto sin recursos compuestos
- **WHEN** se instancia `ToroidalGrid2D(SimulationConfig(), rng)`
- **THEN** `get_composite_rules()` devuelve `{}` y el estado de `rng` es idéntico al de Fase I.

#### Scenario: Generación de recursos compuestos de orden m
- **WHEN** se instancia `ToroidalGrid2D` con `num_composite_patterns = 2`, `composite_order = 2` y `composite_reward_exponent = 1.5`
- **THEN** `get_composite_rules()` contiene 2 entradas cuyos `CompositeRule` exigen `(p_0, p_1)` y `(p_1, p_2)` respectivamente y tienen `composite_value == 2 ** 1.5` (con tolerancia `1e-9`).

### Requirement: Construcción de Nicho y Estigmergia Espacial (R19)
`ToroidalGrid2D` SHALL implementar `deposit_stigmergy(agent_id: int, pattern: Pattern, value: float, confidence: float, tick: int) -> None` y `get_cell_stigmergy(agent_id: int) -> tuple[StigmergicTrace, ...]`, almacenando rastros epistémicos por celda cuando `enable_stigmergy=True` y aplicando en `step_dynamics(tick)` un decaimiento `stigmergy_decay` ($\delta_{\text{suelo}}$) a la intensidad de cada rastro con `last_updated_tick < tick`, purgando aquellos cuya intensidad caiga por debajo de `min_confidence`.

#### Scenario: Depósito, lectura y decaimiento estigmérgico
- **WHEN** con `enable_stigmergy=True` y `stigmergy_decay=0.1` el agente 1 deposita en `tick=10` un rastro de `p_0` con `confidence=0.5` en su celda, otro agente en esa celda consulta `get_cell_stigmergy` en `tick=10` y luego se ejecuta `step_dynamics(11)`
- **THEN** en `tick=10` el rastro tiene `intensity == 0.5`, y tras `step_dynamics(11)` su `intensity` es `0.4` (con tolerancia `1e-9`).
