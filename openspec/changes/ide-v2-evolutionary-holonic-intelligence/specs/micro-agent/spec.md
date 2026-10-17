# Spec Delta: Micro Agent

## ADDED Requirements

### Requirement: Implementación del Protocolo AgentNode de Nivel Cero y Estado de Linaje
`MicroAgent` SHALL preservar las firmas exactas de sus ocho métodos públicos canónicos de Fase I (`__init__`, `perceive_and_emit_messages`, `process_incoming_messages`, `decide_action`, `learn_from_experience`, `decay_memory`, `get_effective_belief`, `assimilate_testimony`) y sus cuatro propiedades (`agent_id`, `config`, `memory`, `capabilities`), y SHALL exponer además las propiedades `energy: float`, `generation: int`, `parent_id: int | None`, `genome: AgentGenome`, `node_id: int`, `holon_level: int` (siempre `0`), `leaf_agents: tuple[MicroAgent, ...]` (siempre `(self,)`) y `effective_capacity: int`, junto con los métodos `collective_memory() -> dict[Pattern, KnowledgeUnit]`, `clear_holon_beliefs() -> None`, `inject_ephemeral_belief(unit: KnowledgeUnit) -> None` (que alimenta un buffer `_holon_tick_beliefs` consultado en tercer nivel por `get_effective_belief` sin ser borrado por `perceive_and_emit_messages`) y el constructor de linaje `MicroAgent.from_lineage(agent_id, config, genome, energy, generation, parent_id, trust_strategy=None, protocol=None)`.

#### Scenario: Compatibilidad de firmas canónicas e implementación de AgentNode
- **WHEN** se instancia `a = MicroAgent(7, SimulationConfig())`
- **THEN** `a.node_id == 7`, `a.holon_level == 0`, `a.leaf_agents == (a,)`, `a.generation == 0`, `a.parent_id is None`, `a.energy == a.config.initial_energy` y las firmas inspeccionadas con `inspect.signature` de los ocho métodos públicos de Fase I permanecen inalteradas.

### Requirement: Creación de Descendiente con Herencia Genética y Cultural
`MicroAgent.create_offspring(child_id: int, tick: int, rng: np.random.Generator, null_rng: np.random.Generator | None = None) -> MicroAgent` SHALL descontar $(1 - \kappa_{\text{part}})$ de la energía del progenitor, transferir $\kappa_{\text{part}} \cdot E_{\text{padre}}$ al hijo, asignar `generation = self.generation + 1` y `parent_id = self.agent_id`, mutar el `AgentGenome` con `rng` si `mutation_rate > 0` o `discrete_mutation_prob > 0`, e inyectar en la memoria del hijo las creencias heredadas según `enable_cultural_inheritance` e `inheritance_discount` (aplicando `nullify_belief` con `null_rng` cuando `comm_content_null=True`).

#### Scenario: Creación de descendiente con conservación de energía
- **WHEN** un `MicroAgent` con `energy = 2.0` y `generation = 1` invoca `create_offspring(child_id=99, tick=25, rng=rng)` con `offspring_energy_share = 0.5`
- **THEN** el progenitor queda con `energy == 1.0` y el hijo retornado tiene `agent_id == 99`, `parent_id == parent.agent_id`, `generation == 2` y `energy == 1.0`.
