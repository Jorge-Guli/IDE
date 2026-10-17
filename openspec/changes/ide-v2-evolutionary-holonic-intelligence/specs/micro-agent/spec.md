# Spec Delta: Micro Agent

## ADDED Requirements

### Requirement: Implementación del Protocolo AgentNode de Nivel Cero y Estado de Linaje
`MicroAgent` SHALL conservar sus 8 firmas y 4 propiedades de Fase I y exponer `energy`, `generation`, `parent_id`, `genome`, `node_id`, `holon_level` (`0`), `leaf_agents` (`(self,)`), `effective_capacity`, `collective_memory()`, `own_belief(pattern)`, `apply_energy_delta(delta)`, `clear_holon_beliefs()`, `inject_ephemeral_belief(unit)` y `MicroAgent.from_lineage(...)`. Los dos métodos de la vista del holón (`clear_*`, `inject_*`) dependen de P1.

#### Scenario: Compatibilidad de firmas canónicas e implementación de AgentNode
- **WHEN** se instancia `a = MicroAgent(7, SimulationConfig())`
- **THEN** `a.node_id == 7`, `a.holon_level == 0`, `a.leaf_agents == (a,)`, `a.generation == 0`, `a.parent_id is None`, `a.energy == a.config.initial_energy`, `inject_ephemeral_belief` alimenta `_holon_tick_beliefs` sin ser borrado por `perceive_and_emit_messages`, y las firmas de los 8 métodos de Fase I permanecen inalteradas.

### Requirement: Creación de Descendiente con Herencia Genética
`MicroAgent.create_offspring(child_id: int, tick: int, rng: np.random.Generator) -> MicroAgent` SHALL particionar la energía con `offspring_energy_share`, asignar `generation = self.generation + 1` y `parent_id = self.agent_id` y mutar el `AgentGenome` con `mutate_genome`, sin transferir creencias: la herencia cultural la entrega el motor por `assimilate_testimony`.

#### Scenario: Creación de descendiente con conservación de energía
- **WHEN** un `MicroAgent` con `energy = 2.0` y `generation = 1` invoca `create_offspring(child_id=99, tick=25, rng=rng)` con `offspring_energy_share = 0.5`
- **THEN** el progenitor queda con `energy == 1.0` y el hijo retornado tiene `agent_id == 99`, `parent_id == parent.agent_id`, `generation == 2`, `energy == 1.0` y `len(child.memory) == 0`.

## MODIFIED Requirements

### Requirement: Creencia Efectiva y Caché Efímero
`own_belief(p)` SHALL devolver la creencia de `BoundedMemory` si existe y, si no, la del caché efímero del tick; `get_effective_belief(p)` SHALL devolver `own_belief(p)` o, si es `None`, la vista del holón del tick. `assimilate_testimony` SHALL partir de `own_belief`. El caché propio SHALL vaciarse al inicio de `perceive_and_emit_messages`, y la vista con `clear_holon_beliefs` (vista: variante (a) de P1).

#### Scenario: Creencia sólo en caché
- **WHEN** una respuesta asimilada en el tick fue rechazada por la memoria llena
- **THEN** `get_effective_belief` la devuelve durante ese tick y devuelve `None` después del siguiente `perceive_and_emit_messages`.

#### Scenario: La vista del holón no contamina el aprendizaje propio
- **WHEN** un agente sin creencia propia sobre $\rho_0$ recibe por `inject_ephemeral_belief` una creencia de un compañero con $\hat{v} = -1.0$ y luego aprende por experiencia directa que $\rho_0$ vale `+1.0`
- **THEN** la creencia resultante en memoria es la de Fase I para un agente sin creencia previa (`update_from_direct_experience(None, ...)`), y `own_belief` no devuelve nunca la creencia inyectada.

### Requirement: Prioridad de la Experiencia Directa en Memoria
`learn_from_experience` SHALL actualizar la creencia con `update_from_direct_experience`, partiendo de `own_belief` (sin la vista del holón), y almacenarla con `upsert(..., force=True)`.

#### Scenario: Memoria llena de creencias fuertes
- **WHEN** la memoria está llena de creencias con utilidad mayor a la de una nueva experiencia directa
- **THEN** tras `learn_from_experience` el patrón experimentado está en la memoria con `from_direct_experience = True`.
