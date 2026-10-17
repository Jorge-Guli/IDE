# Spec Delta: Micro Agent

## Purpose
Definir el comportamiento autónomo y estrictamente local del micro-agente (`MicroAgent`): percepción sin coordenadas globales, consultas en vivo (`QUERY_PATTERN`), difusión (`BROADCAST_BELIEF`), respuesta a pares y selección de acciones.

## ADDED Requirements

### Requirement: Aislamiento Arquitectónico del Paquete agent
Ningún módulo de `src/ide/agent/` SHALL importar `ide.environments`, `ide.simulation` ni `ide.experiments`; sólo puede depender de `ide.domain`, `ide.config`, la biblioteca estándar y `numpy`.

#### Scenario: Auditoría de importaciones
- **WHEN** se analiza con `ast` cada archivo de `src/ide/agent/`
- **THEN** ninguna sentencia `import` o `from ... import` referencia `environments`, `simulation`, `experiments` ni `grid2d`.

### Requirement: Firmas Públicas Canónicas
`MicroAgent` SHALL exponer `perceive_and_emit_messages(obs, tick) -> list[Message]`, `process_incoming_messages(messages, tick) -> list[Message]`, `decide_action(obs, tick, rng) -> AgentAction`, `learn_from_experience(pattern, real_value, tick) -> None`, `decay_memory(tick) -> None`, `get_effective_belief(pattern)` y `assimilate_testimony(belief, sender_id, tick) -> KnowledgeUnit`.

#### Scenario: Inspección de la interfaz
- **WHEN** se inspeccionan con `inspect.signature` los métodos públicos de `MicroAgent`
- **THEN** los nombres y parámetros coinciden exactamente con los de `design.md`.

### Requirement: Semántica del Protocolo Aislada
Dentro de `src/ide/agent/`, sólo `protocol.py` SHALL construir `Message` o referenciar `MessageType`; `MicroAgent(agent_id, config, trust_strategy=None, protocol=None)` SHALL delegar la emisión y la recepción en el protocolo inyectado (por defecto `BeliefExchangeProtocol`), y todo conocimiento social SHALL entrar por `assimilate_testimony`.

#### Scenario: Auditoría del protocolo
- **WHEN** se analiza con `ast` cada archivo de `src/ide/agent/` distinto de `protocol.py`
- **THEN** ninguno contiene una llamada a `Message(...)` ni una referencia a `MessageType`.

#### Scenario: Protocolo inyectado
- **WHEN** se construye un `MicroAgent` con un protocolo de prueba cuyo `emit` devuelve siempre `[]`
- **THEN** `perceive_and_emit_messages` devuelve `[]` aunque el agente tenga vecinos y creencias difundibles.

### Requirement: Creencia Efectiva y Caché Efímero
`get_effective_belief(p)` SHALL devolver la creencia de `BoundedMemory` si existe y, si no, la del caché efímero del tick. El caché SHALL vaciarse al inicio de cada `perceive_and_emit_messages`.

#### Scenario: Creencia sólo en caché
- **WHEN** una respuesta asimilada en el tick fue rechazada por la memoria llena
- **THEN** `get_effective_belief` la devuelve durante ese tick y devuelve `None` después del siguiente `perceive_and_emit_messages`.

### Requirement: Emisión de Consultas en Vivo
Con vecinos presentes, `perceive_and_emit_messages` SHALL emitir hasta `max_queries_per_tick` mensajes `QUERY_PATTERN` con `recipient_id=None`, uno por cada patrón visible distinto no conocido (sin creencia efectiva o con `c < decision_conf_threshold`), en orden de menor distancia y luego de `pattern`.

#### Scenario: Recurso desconocido con vecinos
- **WHEN** el agente 1 observa un recurso de patrón $\rho_5$ que no conoce y `obs.neighbor_ids == (2, 3)`
- **THEN** la salida incluye `Message(QUERY_PATTERN, sender_id=1, recipient_id=None, pattern=ρ5)`.

#### Scenario: Sin vecinos no hay mensajes
- **WHEN** `obs.neighbor_ids` está vacío
- **THEN** `perceive_and_emit_messages` devuelve `[]`.

### Requirement: Difusión Espontánea Priorizada
Con vecinos presentes, `perceive_and_emit_messages` SHALL emitir, después de las consultas, hasta `max_broadcast_per_tick` mensajes `BROADCAST_BELIEF` con las creencias de memoria de confianza `>= decision_conf_threshold`, en orden de utilidad descendente y luego de `pattern`.

#### Scenario: Sólo se difunde conocimiento confiable
- **WHEN** la memoria contiene una creencia con `c = 0.9` y otra con `c = 0.2`, y `max_broadcast_per_tick = 2`
- **THEN** se emite un único `BROADCAST_BELIEF`, el de la creencia con `c = 0.9`.

### Requirement: Respuesta a Consultas
Ante un `QUERY_PATTERN` de otro agente, `process_incoming_messages` SHALL devolver un `QUERY_RESPONSE` dirigido al emisor con su creencia de memoria si ésta existe con `c >= decision_conf_threshold`; no SHALL responder con creencias del caché efímero.

#### Scenario: Vecino informado responde
- **WHEN** el agente 2 recibe `QUERY_PATTERN(ρ5)` del agente 1 y tiene en memoria $k(\rho_5, \hat{v}=-1.0, c=0.85)$
- **THEN** devuelve `[Message(QUERY_RESPONSE, sender_id=2, recipient_id=1, pattern=ρ5, belief=k)]`.

### Requirement: Asimilación Social de Mensajes
Ante un `BROADCAST_BELIEF` o un `QUERY_RESPONSE` de otro agente, `process_incoming_messages` SHALL fusionar la creencia con `merge_social_belief` usando el factor de `TrustStrategyPort`, guardarla en el caché efímero e intentar `memory.upsert`, procesando los mensajes en el orden recibido e ignorando los propios.

#### Scenario: Respuesta que permite evitar un recurso dañino
- **WHEN** el agente 1 procesa la respuesta del agente 2 sobre $\rho_5$ ($\hat{v} = -1.0$, `c = 0.85`) y luego decide frente a un recurso alcanzable de $\rho_5$
- **THEN** su creencia efectiva sobre $\rho_5$ tiene `c = 0.6375` y `decide_action` no devuelve `INTERACT` sobre ese recurso.

### Requirement: Consumo de Recurso Conocido como Benéfico
Si entre los recursos alcanzables hay alguno conocido como benéfico (`v̂ > 0`, `c >= decision_conf_threshold`), `decide_action` SHALL devolver `INTERACT` sobre el de mayor `v̂·c`, desempatando por menor `resource_id`.

#### Scenario: Recurso benéfico en la celda actual
- **WHEN** hay un recurso alcanzable de $\rho_1$ y el agente cree `v̂ = +1.0`, `c = 0.70`
- **THEN** `decide_action` devuelve `AgentAction(ActionType.INTERACT, target=resource_id)`.

### Requirement: Exploración Acotada de lo Desconocido
Si no hay benéficos conocidos alcanzables pero sí alcanzables no conocidos, `decide_action` SHALL extraer un único `rng.random()` y, si es menor que `epsilon_explore`, devolver `INTERACT` sobre el no conocido de menor `resource_id`.

#### Scenario: Exploración garantizada
- **WHEN** hay un único recurso alcanzable desconocido y `epsilon_explore = 1.0`
- **THEN** `decide_action` devuelve `INTERACT` sobre ese recurso.

#### Scenario: Exploración deshabilitada
- **WHEN** hay un único recurso alcanzable desconocido y `epsilon_explore = 0.0`
- **THEN** `decide_action` no devuelve `INTERACT`.

### Requirement: Evitación de Recursos Conocidos como Dañinos
`decide_action` SHALL NOT devolver `INTERACT` sobre un recurso cuyo patrón sea conocido como dañino (`v̂ < 0`, `c >= decision_conf_threshold`).

#### Scenario: Única opción tóxica
- **WHEN** hay únicamente un recurso alcanzable de $\rho_2$, el agente cree `v̂ = -1.0`, `c = 0.70`, y hay movimientos disponibles
- **THEN** `decide_action` devuelve una acción `MOVE` con destino en `obs.available_moves`.

### Requirement: Navegación hacia Recursos Benéficos Distantes
Si no interactúa, `decide_action` SHALL devolver `MOVE` hacia el `recommended_move` del recurso distante conocido como benéfico de menor `distance`, desempatando por menor `resource_id`.

#### Scenario: Acercamiento usando recommended_move
- **WHEN** la celda actual está vacía y hay un recurso visible a `distance = 2` con `recommended_move = (1, 0)` cuyo patrón se cree `v̂ = +1.0`, `c = 0.80`
- **THEN** `decide_action` devuelve `AgentAction(ActionType.MOVE, target=(1, 0))`.

### Requirement: Ablación de la Navegación
Con `enable_navigation=False`, `decide_action` SHALL omitir el paso de navegación hacia recursos distantes y pasar directamente a la caminata aleatoria.

#### Scenario: Recurso benéfico distante ignorado
- **WHEN** `enable_navigation=False`, la celda está vacía y hay un recurso conocido como benéfico a `distance = 2` con `recommended_move = (1, 0)`, y `rng` está sembrado
- **THEN** `decide_action` devuelve el mismo `MOVE` que la caminata aleatoria con ese `rng`, sin consultar `recommended_move`.

### Requirement: Caminata Aleatoria por Defecto
Sin interacción ni objetivo distante, `decide_action` SHALL devolver `MOVE` a `available_moves[rng.integers(len(available_moves))]`, o `IDLE` si no hay movimientos disponibles.

#### Scenario: Sin movimientos posibles
- **WHEN** no hay recursos visibles y `obs.available_moves == ()`
- **THEN** `decide_action` devuelve `AgentAction(ActionType.IDLE)`.

### Requirement: Prioridad de la Experiencia Directa en Memoria
`learn_from_experience` SHALL actualizar la creencia con `update_from_direct_experience`, partiendo de la creencia efectiva, y almacenarla con `upsert(..., force=True)`.

#### Scenario: Memoria llena de creencias fuertes
- **WHEN** la memoria está llena de creencias con utilidad mayor a la de una nueva experiencia directa
- **THEN** tras `learn_from_experience` el patrón experimentado está en la memoria con `from_direct_experience = True`.
