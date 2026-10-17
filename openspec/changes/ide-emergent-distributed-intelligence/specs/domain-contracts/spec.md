# Spec Delta: Domain Contracts

## Purpose
Definir los modelos de datos inmutables, la configuración reproducible del sistema y el contrato abstracto `EnvironmentPort` que desacopla el razonamiento del agente de la topología del entorno.

## ADDED Requirements

### Requirement: Estructuras de Datos Inmutables
El sistema SHALL definir `Pattern`, `KnowledgeUnit`, `Resource`, `VisibleResource`, `Observation`, `Message`, `AgentAction` y `ActionResult` como `@dataclass(frozen=True)` en `src/ide/domain/types.py`, con los campos exactos de `design.md`.

#### Scenario: Intento de mutación
- **WHEN** un consumidor intenta reasignar un atributo de un `Pattern` o de un `KnowledgeUnit`
- **THEN** Python lanza `dataclasses.FrozenInstanceError` y el objeto permanece intacto.

### Requirement: Pattern Hashable y con Orden Total
`Pattern` SHALL ser `@dataclass(frozen=True, order=True)`, utilizable como clave de `dict` y elemento de `set`, y SHALL exponer la propiedad `label` que une los pares `clave=valor` con `&`.

#### Scenario: Uso como clave y orden canónico
- **WHEN** se construyen `Pattern((("id", "p_1"),))` y `Pattern((("id", "p_0"),))` y se ordenan con `sorted`
- **THEN** el primero de la lista es `p_0`, ambos pueden usarse como claves de `dict` sin `TypeError` y `Pattern((("id", "p_0"),)).label == "id=p_0"`.

### Requirement: Validación de Coherencia de Mensajes
`Message` SHALL lanzar `ValueError` al construirse si su tipo es `QUERY_RESPONSE` o `BROADCAST_BELIEF` y `belief` es `None`, si `belief.pattern` difiere de `pattern`, o si su tipo es `QUERY_PATTERN` y `belief` no es `None`.

#### Scenario: Respuesta sin creencia
- **WHEN** se instancia `Message(MessageType.QUERY_RESPONSE, sender_id=1, recipient_id=2, pattern=p, belief=None)`
- **THEN** se lanza `ValueError`.

#### Scenario: Consulta que transporta conocimiento
- **WHEN** se instancia `Message(MessageType.QUERY_PATTERN, sender_id=1, recipient_id=2, pattern=p, belief=k)` con `k` un `KnowledgeUnit`
- **THEN** se lanza `ValueError`, porque una consulta no puede introducir conocimiento fuera de `assimilate_testimony`.

### Requirement: Ocultamiento del Valor Real en la Percepción
`VisibleResource` SHALL carecer del atributo `true_value` y SHALL exponer `resource_id`, `pattern`, `recommended_move`, `distance` e `is_reachable_now`, donde `is_reachable_now` es verdadero si y sólo si `distance == 0`.

#### Scenario: Inspección de un recurso visible
- **WHEN** se inspeccionan los campos de `VisibleResource` con `dataclasses.fields`
- **THEN** el conjunto de nombres es exactamente `{resource_id, pattern, recommended_move, distance, is_reachable_now}`.

### Requirement: Guía de Movimiento Agnóstica
Para todo `VisibleResource` con `distance > 0`, `recommended_move` SHALL pertenecer a `Observation.available_moves`; con `distance == 0` SHALL ser `None`.

#### Scenario: Recurso distante
- **WHEN** el entorno construye una `Observation` con un recurso a `distance = 2`
- **THEN** su `recommended_move` es uno de los elementos de `obs.available_moves`.

### Requirement: Contrato EnvironmentPort Verificable en Ejecución
`src/ide/domain/ports.py` SHALL declarar `@runtime_checkable class EnvironmentPort(Protocol)` con `get_active_agent_ids`, `get_observation`, `get_communication_neighbors`, `execute_action`, `remove_agents`, `retire_pattern_resources`, `invert_world_rules`, `step_dynamics`, `get_world_patterns` y `get_reachable_true_values`.

#### Scenario: Sustitución de entorno
- **WHEN** se pasa a `SimulationEngine` un objeto que implementa los diez métodos (sea `ToroidalGrid2D` o un entorno de prueba basado en grafos)
- **THEN** `isinstance(env, EnvironmentPort)` es `True` y `MicroAgent` opera sin cambios de código.

### Requirement: Oráculo de Verdad Restringido a Telemetría
`get_reachable_true_values(agent_id)` SHALL devolver un `dict[int, float]` de `resource_id` a `true_value` de los recursos alcanzables por el agente, y SHALL ser invocado únicamente por `SimulationEngine` para calcular M2, nunca entregado a un `MicroAgent`.

#### Scenario: Agente sin recursos alcanzables
- **WHEN** el agente está en una celda sin recursos
- **THEN** `get_reachable_true_values(agent_id)` devuelve `{}`.

### Requirement: Semántica Tolerante de execute_action
`execute_action` SHALL tratar un `MOVE` con destino fuera de `available_moves` como `IDLE` y un `INTERACT` sobre un recurso inexistente o en otra celda como `ActionResult(INTERACT, None, None)`, sin lanzar excepciones.

#### Scenario: Movimiento inválido
- **WHEN** un agente envía `AgentAction(ActionType.MOVE, target=(5, 5))` en una grilla de Moore
- **THEN** el agente no cambia de posición y no se lanza ninguna excepción.

### Requirement: Restricción de Memoria Insuficiente en la Configuración
`SimulationConfig.__post_init__` SHALL lanzar `ValueError` si `memory_capacity < 1`, o si `enforce_memory_constraint` es verdadero y `memory_capacity >= num_world_patterns`.

#### Scenario: Capacidad igual al número de patrones
- **WHEN** se instancia `SimulationConfig(num_world_patterns=8, memory_capacity=8)`
- **THEN** se lanza `ValueError` cuyo mensaje menciona `memory_capacity`.

#### Scenario: Capacidad nula sin restricción
- **WHEN** se instancia `SimulationConfig(memory_capacity=0, enforce_memory_constraint=False)`
- **THEN** se lanza `ValueError`.

### Requirement: Validación de Rangos de Hiperparámetros
`SimulationConfig.__post_init__` SHALL lanzar `ValueError` nombrando el campo si un coeficiente probabilístico sale de `[0.0, 1.0]`, si `num_agents`, `resources_per_pattern` o las dimensiones son menores que 1, si `num_world_patterns < 2`, si un radio o tasa es negativo, si `min_confidence >= decision_conf_threshold`, o si `2 * max(perception_radius, comm_radius) >= min(grid_width, grid_height)`.

#### Scenario: Coeficiente fuera de rango
- **WHEN** se instancia `SimulationConfig(gamma_social_discount=1.5)`
- **THEN** se lanza `ValueError` cuyo mensaje menciona `gamma_social_discount`.

#### Scenario: Radio que da la vuelta al toro
- **WHEN** se instancia `SimulationConfig(grid_width=4, grid_height=4, perception_radius=2)`
- **THEN** se lanza `ValueError`.

### Requirement: Interruptores de Ablación y Control
`SimulationConfig` SHALL incluir `anti_echo_enabled: bool = True`, `enable_navigation: bool = True`, `comm_content_null: bool = False` y `update_scheme: str = "synchronous"`, de modo que la configuración por defecto active todas las reglas de diseño y ningún control; `update_scheme` SHALL validarse en `{"synchronous", "asynchronous"}`.

#### Scenario: Valores por defecto
- **WHEN** se instancia `SimulationConfig()`
- **THEN** `anti_echo_enabled` y `enable_navigation` son verdaderos, `comm_content_null` es falso y `update_scheme == "synchronous"`.

#### Scenario: Esquema desconocido
- **WHEN** se instancia `SimulationConfig(update_scheme="continuo")`
- **THEN** se lanza `ValueError` cuyo mensaje menciona `update_scheme`.

### Requirement: Configuración Serializable
`SimulationConfig.to_dict()` SHALL devolver un diccionario con todos los campos, serializable con `json.dumps` sin conversiones adicionales.

#### Scenario: Ida y vuelta por JSON
- **WHEN** se ejecuta `SimulationConfig(**json.loads(json.dumps(cfg.to_dict())))`
- **THEN** el resultado es igual a `cfg`.
