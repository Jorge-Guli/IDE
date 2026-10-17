# Spec Delta: Micro Agent

## ADDED Requirements

### Requirement: Implementación del Protocolo AgentNode de Nivel Cero y Estado de Linaje
`MicroAgent` SHALL preservar las firmas exactas de sus 8 métodos y 4 propiedades de Fase I, y exponer además `energy`, `generation`, `parent_id`, `genome`, `node_id`, `holon_level` (`0`), `leaf_agents` (`(self,)`), `effective_capacity`, `collective_memory()`, `clear_holon_beliefs()`, `inject_ephemeral_belief(unit)` y `MicroAgent.from_lineage(...)`.

#### Scenario: Compatibilidad de firmas canónicas e implementación de AgentNode
- **WHEN** se instancia `a = MicroAgent(7, SimulationConfig())`
- **THEN** `a.node_id == 7`, `a.holon_level == 0`, `a.leaf_agents == (a,)`, `a.generation == 0`, `a.parent_id is None`, `a.energy == a.config.initial_energy`, `inject_ephemeral_belief` alimenta `_holon_tick_beliefs` sin ser borrado por `perceive_and_emit_messages`, y las firmas de los 8 métodos de Fase I permanecen inalteradas.

### Requirement: Creación de Descendiente con Herencia Genética y Cultural
`MicroAgent.create_offspring(child_id: int, tick: int, rng: np.random.Generator, null_rng: np.random.Generator | None = None) -> MicroAgent` SHALL particionar la energía con `offspring_energy_share`, asignar `generation = self.generation + 1` y `parent_id = self.agent_id`, mutar el `AgentGenome` e inyectar las creencias heredadas según `enable_cultural_inheritance` e `inheritance_discount`.

#### Scenario: Creación de descendiente con conservación de energía
- **WHEN** un `MicroAgent` con `energy = 2.0` y `generation = 1` invoca `create_offspring(child_id=99, tick=25, rng=rng)` con `offspring_energy_share = 0.5`
- **THEN** el progenitor queda con `energy == 1.0` y el hijo retornado tiene `agent_id == 99`, `parent_id == parent.agent_id`, `generation == 2` y `energy == 1.0`.
