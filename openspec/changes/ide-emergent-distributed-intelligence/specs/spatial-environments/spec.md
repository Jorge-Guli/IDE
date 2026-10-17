# Spec Delta: Spatial Environments

## Purpose
Proveer la implementación inicial del entorno espacial `ToroidalGrid2D` cumpliendo el contrato `EnvironmentPort`, garantizando generación determinista de patrones, topología toroidal sin bordes, búsqueda de vecindad en $O(1)$ respecto al tamaño del mapa mediante indexación por celda, y ciclo de vida de recursos con retiro selectivo.

## ADDED Requirements

### Requirement: Generación Determinista de los $N$ Patrones del Mundo
Al instanciar `ToroidalGrid2D(config: SimulationConfig, rng: np.random.Generator)`, el entorno SHALL generar exactamente `N = config.num_world_patterns` patrones con la estructura canónica `Pattern(attributes=(("id", f"p_{i}"),))` para $i \in \{0, \dots, N-1\}$, asignando `true_value = +1.0` a la primera mitad ($i < N // 2$) y `true_value = -1.0` a la segunda mitad ($i \ge N // 2$), e instanciando `config.resources_per_pattern` recursos de cada patrón en celdas elegidas mediante `rng`.

#### Scenario: Equilibrio exacto entre patrones benéficos y dañinos al iniciar
- **WHEN** se instancia `ToroidalGrid2D` con `num_world_patterns = 12` y `resources_per_pattern = 8`
- **THEN** `get_world_patterns()` retorna 6 patrones con valor `+1.0` (`p_0` a `p_5`) y 6 patrones con valor `-1.0` (`p_6` a `p_11`), existiendo 96 recursos en el tablero.

### Requirement: Geometría Toroidal sin Bordes y Cálculo de `recommended_move`
La clase `ToroidalGrid2D` en `src/ide/environments/grid2d.py` SHALL implementar aritmética modular `(x % width, y % height)` para toda operación de movimiento, percepción y cálculo de distancia Chebyshev/Moore entre celdas, calculando para cada `VisibleResource` su `distance = max(|dx|, |dy|)` toroidal y su `recommended_move = (sign(dx), sign(dy))` dentro de los 8 movimientos de Moore `available_moves`.

#### Scenario: Movimiento cruzando el límite derecho y superior del mapa
- **WHEN** un agente situado en `(width - 1, 0)` se mueve en dirección `(+1, -1)` en una grilla de tamaño `width x height`
- **THEN** su nueva ubicación pasa a ser exactamente `(0, height - 1)`.

#### Scenario: Percepción y recommended_move a través de la frontera toroidal
- **WHEN** un agente está en `(0, 0)` con `perception_radius = 2` y existe un recurso en `(width - 2, 0)`
- **THEN** dicho recurso aparece en `Observation.visible_resources` con `distance = 2`, `is_reachable_now = False` y `recommended_move = (-1, 0)`.

### Requirement: Indexación Espacial por Celda en Tiempo Constante
`ToroidalGrid2D` SHALL mantener estructuras de índice inverso por coordenada (`cell_agents: dict[tuple[int, int], set[int]]` y `cell_resources: dict[tuple[int, int], dict[int, Resource]]`) actualizadas en cada movimiento, inserción o eliminación, evitando recorridos $O(M^2)$ sobre toda la población al consultar vecindades.

#### Scenario: Consistencia del índice espacial tras mover o eliminar agentes
- **WHEN** un agente se desplaza de `c_origen` a `c_destino` o es eliminado mediante `remove_agents`
- **THEN** su ID desaparece inmediatamente de `cell_agents[c_origen]` y, si fue un movimiento, se registra en `cell_agents[c_destino]`.

### Requirement: Interacción con Recursos, Reposición y Retiro de Patrones (`retire_pattern_resources`)
Cuando un agente ejecute `AgentAction(ActionType.INTERACT, target=resource_id)` sobre un recurso presente en su misma celda, `ToroidalGrid2D` SHALL devolver `ActionResult` con el `Pattern` y el `true_value` real del recurso, consumir el recurso de la celda actual y reponerlo en una celda aleatoria durante `step_dynamics`, salvo que el patrón haya sido retirado mediante `retire_pattern_resources(pattern: Pattern)`, método que elimina todas las instancias físicas de ese patrón en el tablero e impide su futura reposición.

#### Scenario: Intento de interacción con recurso inexistente o fuera de celda
- **WHEN** un agente envía `INTERACT` hacia un `resource_id` que ya fue consumido por otro agente antes en el mismo tick o está en otra celda
- **THEN** `execute_action` devuelve `ActionResult(action_type=ActionType.INTERACT, interacted_pattern=None, experienced_value=None)` sin lanzar excepción.

#### Scenario: Retiro de estímulo físico para prueba de memoria social pura
- **WHEN** se invoca `env.retire_pattern_resources(pattern_0)` y luego corre `step_dynamics` durante 50 ticks
- **THEN** ningún recurso con `pattern_0` vuelve a aparecer en el tablero ni en ninguna `Observation`.
