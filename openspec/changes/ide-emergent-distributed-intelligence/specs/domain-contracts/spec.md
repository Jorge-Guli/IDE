# Spec Delta: Domain Contracts

## Purpose
Definir los modelos de datos inmutables, la configuración reproducible del sistema y el contrato abstracto `EnvironmentPort` que desacopla el razonamiento del agente de la topología física o espacial del entorno.

## ADDED Requirements

### Requirement: Estructuras de Datos Inmutables y Hashables
El sistema SHALL definir todas las entidades de intercambio entre agentes y entorno (`Pattern`, `KnowledgeUnit`, `Resource`, `VisibleResource`, `Observation`, `Message`, `AgentAction`, `ActionResult`) como `@dataclass(frozen=True)` en `src/ide/domain/types.py`.

#### Scenario: Inmutabilidad de Pattern y KnowledgeUnit
- **WHEN** se instancia un `Pattern(attributes=(("id", "p_0"),))` o un `KnowledgeUnit` y un consumidor intenta reasignar cualquiera de sus atributos
- **THEN** Python lanza `dataclasses.FrozenInstanceError` y el objeto original permanece intacto.

#### Scenario: Uso de Pattern como clave de diccionario
- **WHEN** se utiliza una instancia de `Pattern` como clave en un `dict` o elemento en un `set`
- **THEN** el hash se calcula de manera determinista a partir de su tupla ordenada de atributos sin lanzar `TypeError`.

### Requirement: Ocultamiento Estricto del Valor Real y Guía Agnóstica de Movimiento en la Percepción
El sistema SHALL separar la entidad interna del entorno (`Resource`, que contiene `true_value: float`) de la entidad percibida por el agente (`VisibleResource`, que omite `true_value`), e incluir en `VisibleResource` los campos `recommended_move: Any`, `distance: int` e `is_reachable_now: bool` para que el agente pueda acercarse a recursos distantes sin conocer coordenadas cartesianas.

#### Scenario: Inspección de Observation por parte del agente
- **WHEN** el entorno construye un objeto `Observation` para un agente con recursos cercanos
- **THEN** cada elemento dentro de `obs.visible_resources` es una instancia de `VisibleResource` que contiene únicamente `resource_id`, `pattern`, `recommended_move`, `distance` e `is_reachable_now`, carece del atributo `true_value`, y su `recommended_move` (cuando `distance > 0`) pertenece a `obs.available_moves`.

### Requirement: Contrato Abstracto EnvironmentPort Agnóstico de Topología
El módulo `src/ide/domain/ports.py` SHALL declarar un `Protocol` verificable en tiempo de ejecución (`@runtime_checkable`) llamado `EnvironmentPort` con los métodos `get_active_agent_ids`, `get_observation`, `get_communication_neighbors`, `execute_action`, `remove_agents`, `retire_pattern_resources`, `invert_world_rules`, `step_dynamics` y `get_world_patterns`.

#### Scenario: Sustitución de entorno sin modificar el agente
- **WHEN** se pasa al motor de simulación cualquier implementación de `EnvironmentPort` (sea `ToroidalGrid2D` o un entorno simulado basado en grafos)
- **THEN** `isinstance(env, EnvironmentPort)` evalúa a `True` y `MicroAgent` opera sin cambios de código ni conversiones de coordenadas.

### Requirement: Configuración Centralizada y Validada
El módulo `src/ide/config.py` SHALL proveer la clase `SimulationConfig` con validación en `__post_init__` que verifique las invariantes matemáticas del sistema, incluyendo la restricción crítica $1 \le C_{\max} < N$ y rangos válidos de probabilidades en $[0.0, 1.0]$.

#### Scenario: Rechazo de configuración que viola la restricción de memoria insuficiente
- **WHEN** se instancia `SimulationConfig(num_world_patterns=8, memory_capacity=8)` donde $C_{\max} \ge N$ (y `enforce_memory_constraint=True`)
- **THEN** `SimulationConfig` lanza `ValueError` indicando que la capacidad de memoria individual debe ser estrictamente menor al número de patrones del mundo.
