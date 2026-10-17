# Spec Delta: Micro Agent

## Purpose
Definir el comportamiento autónomo y estrictamente local del micro-agente (`MicroAgent`), incluyendo sus firmas públicas exactas, percepción sin coordenadas globales, emisión de consultas en vivo (`QUERY_PATTERN`), difusión de conocimiento (`BROADCAST_BELIEF`), respuesta a pares y selección de acciones.

## ADDED Requirements

### Requirement: Aislamiento Arquitectónico Total y Firmas Públicas Canónicas
El módulo `src/ide/agent/micro_agent.py` SHALL operar únicamente sobre objetos `Observation`, `Message`, `AgentAction` y `ActionResult`, teniendo prohibido importar módulos de `src/ide/environments/` o asumir coordenadas cartesianas $(x, y)$, y SHALL exponer exactamente los siguientes métodos públicos:
- `perceive_and_emit_messages(obs: Observation, tick: int) -> list[Message]`
- `process_incoming_messages(messages: list[Message], tick: int) -> list[Message]`
- `decide_action(obs: Observation, tick: int, rng: np.random.Generator) -> AgentAction`
- `learn_from_experience(pattern: Pattern, real_value: float, tick: int) -> None`
- `decay_memory(tick: int) -> None`

#### Scenario: Auditoría de importaciones del paquete agent
- **WHEN** se analiza el árbol de sintaxis abstracta (AST) de todos los archivos dentro de `src/ide/agent/`
- **THEN** ninguna sentencia `import` o `from ... import` referencia a `environments`, `grid2d` ni coordenadas espaciales explícitas.

### Requirement: Emisión de Consultas Colectivas en Vivo (QUERY_PATTERN)
Cuando un `MicroAgent` perciba en `obs.visible_resources` un recurso cuyo `Pattern` no esté en su `BoundedMemory` (o cuya confianza sea inferior a `decision_conf_threshold`) y tenga vecinos en `obs.neighbor_ids`, `perceive_and_emit_messages(obs, tick)` SHALL emitir un mensaje `MessageType.QUERY_PATTERN` dirigido a sus vecinos (`recipient_id=None`).

#### Scenario: Agente encuentra recurso desconocido acompañado de vecinos
- **WHEN** el agente 1 observa un recurso con patrón $\rho_5$ que no está en su memoria y `obs.neighbor_ids` contiene `(2, 3)`
- **THEN** `perceive_and_emit_messages` genera un `Message(msg_type=MessageType.QUERY_PATTERN, sender_id=1, recipient_id=None, pattern=\rho_5)`.

### Requirement: Respuesta a Consultas y Difusión Espontánea
Cuando un `MicroAgent` reciba en `process_incoming_messages(messages, tick)` un `QUERY_PATTERN` sobre un patrón $\rho$ que sí posee en su `BoundedMemory` con confianza $c \ge c_{\text{umbral}}$, SHALL retornar un `MessageType.QUERY_RESPONSE` dirigido a `sender_id` con su `KnowledgeUnit`. Adicionalmente, en `perceive_and_emit_messages(obs, tick)` con vecinos presentes, SHALL emitir hasta `max_broadcast_per_tick` mensajes `BROADCAST_BELIEF` priorizando las creencias de mayor utilidad epistémica.

#### Scenario: Vecino responde a consulta permitiendo decisión informada inmediata
- **WHEN** el agente 2 recibe `QUERY_PATTERN(\rho_5)` del agente 1 y el agente 2 posee en su memoria $k(\rho_5, \hat{v}=-1.0, c=0.85)$
- **THEN** `process_incoming_messages` del agente 2 devuelve `QUERY_RESPONSE` con $k(\rho_5)$, el agente 1 lo procesa en la segunda pasada social del mismo tick guardándolo en `_ephemeral_tick_beliefs` y en `BoundedMemory`, y evita consumir el recurso dañino.

### Requirement: Política de Decisión Guiada por Confianza, Navegación por `recommended_move` y Exploración Acotada
En la fase de decisión, `decide_action(obs, tick, rng)` SHALL:
1. Evaluar primero los recursos alcanzables en la ubicación actual (`is_reachable_now == True`):
   - Si conoce algún patrón con $c \ge c_{\text{umbral}}$ y $\hat{v} > 0$, ejecuta `ActionType.INTERACT` sobre el de mayor $\hat{v} \cdot c$.
   - Si desconoce algún patrón ($c < c_{\text{umbral}}$), explora con probabilidad `epsilon_explore` ejecutando `ActionType.INTERACT`.
   - Si todos los recursos en la celda son conocidos como dañinos ($\hat{v} < 0, c \ge c_{\text{umbral}}$) o decide no explorar, no interactúa.
2. Si no interactúa en la celda actual, evaluar recursos distantes (`is_reachable_now == False`, `distance > 0`):
   - Si existe algún recurso visible con creencia benéfica conocida ($\hat{v} > 0, c \ge c_{\text{umbral}}$), selecciona el de menor `distance` y ejecuta `AgentAction(ActionType.MOVE, target=res.recommended_move)`.
3. Si no hay recursos benéficos visibles, ejecutar `ActionType.MOVE` eligiendo pseudoaleatoriamente una opción de `obs.available_moves` (o `ActionType.IDLE` si `available_moves` está vacío).

#### Scenario: Consumo de recurso conocido como benéfico en celda actual
- **WHEN** hay un recurso alcanzable (`is_reachable_now=True`) con patrón $\rho_1$ y el agente tiene creencia con $\hat{v} = +1.0, c = 0.70 \ge 0.35$
- **THEN** `decide_action` retorna `AgentAction(action_type=ActionType.INTERACT, target=resource_id)`.

#### Scenario: Evitación activa de recurso conocido como tóxico y desplazamiento
- **WHEN** hay únicamente un recurso alcanzable con patrón $\rho_2$ y el agente tiene creencia con $\hat{v} = -1.0, c = 0.70 \ge 0.35$
- **THEN** `decide_action` jamás retorna `INTERACT` sobre ese recurso y selecciona `ActionType.MOVE` hacia un movimiento disponible.

#### Scenario: Acercamiento a recurso benéfico distante usando recommended_move
- **WHEN** la celda actual está vacía pero en `obs.visible_resources` hay un recurso a `distance = 2` con `recommended_move = (1, 0)` cuyo patrón es conocido como benéfico ($\hat{v} = +1.0, c = 0.80$)
- **THEN** `decide_action` retorna `AgentAction(action_type=ActionType.MOVE, target=(1, 0))`.
