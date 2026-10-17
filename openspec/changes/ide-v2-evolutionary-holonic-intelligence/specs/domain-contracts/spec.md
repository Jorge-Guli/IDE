# Spec Delta: Domain Contracts

## ADDED Requirements

### Requirement: Tipos Inmutables de Fase II (Genoma, Reglas Compuestas, Estigmergia y Holones)
`src/ide/domain/types.py` SHALL definir como `@dataclass(frozen=True)` los tipos `AgentGenome`, `StigmergicTrace` y `HolonSnapshot` con los campos exactos de `design.md`, preservando intactos los campos de `Pattern`, `KnowledgeUnit`, `Resource`, `VisibleResource`, `Observation`, `Message`, `AgentAction` y `ActionResult`.

#### Scenario: Inmutabilidad de los nuevos tipos y preservación de VisibleResource
- **WHEN** se inspeccionan `AgentGenome`, `StigmergicTrace` y `HolonSnapshot` y los campos de `VisibleResource`
- **THEN** los tres nuevos tipos son `frozen=True` y el conjunto de nombres de campos de `VisibleResource` sigue siendo exactamente `{resource_id, pattern, recommended_move, distance, is_reachable_now}`.

### Requirement: Sub-Puerto EvolutionaryEnvironmentPort Compatible con EnvironmentPort
`src/ide/domain/ports.py` SHALL mantener intactos los 10 métodos declarados en `EnvironmentPort` y definir `@runtime_checkable class EvolutionaryEnvironmentPort(EnvironmentPort, Protocol)` añadiendo los métodos de Fase II (`spawn_agent_near`, `set_agent_radii`, `get_agent_distance`, `get_composite_rules`, `deposit_stigmergy`, `get_cell_stigmergy`, `get_active_stigmergy_cells`).

#### Scenario: Preservación de los diez métodos de EnvironmentPort
- **WHEN** se inspeccionan los métodos públicos de `EnvironmentPort` y se verifica `isinstance(ToroidalGrid2D(config, rng), EvolutionaryEnvironmentPort)`
- **THEN** `EnvironmentPort` declara exactamente los diez métodos canónicos de Fase I y `ToroidalGrid2D` cumple tanto `EnvironmentPort` como `EvolutionaryEnvironmentPort`.

### Requirement: Banderas e Hiperparámetros de Fase II con Retrocompatibilidad por Defecto
`SimulationConfig` SHALL incluir las banderas booleanas `enable_evolution: bool = False`, `enable_cultural_inheritance: bool = False`, `enable_holonic_hierarchy: bool = False`, `enable_holon_splitting: bool = True`, `enable_holon_reproduction: bool = False`, `enable_downward_causation: bool = False` y `enable_stigmergy: bool = False`, junto con los hiperparámetros metabólicos, genéticos, holónicos y de recursos compuestos de `design.md`, validando sus rangos en `__post_init__` (incluyendo `composite_order <= num_world_patterns // 2` cuando `num_composite_patterns > 0`) y serializándolos en `to_dict()`.

#### Scenario: Configuración por defecto inalterada para Fase I
- **WHEN** se instancia `SimulationConfig()` sin argumentos
- **THEN** todas las banderas de activación de Fase II (`enable_evolution`, `enable_cultural_inheritance`, `enable_holonic_hierarchy`, `enable_holon_reproduction`, `enable_downward_causation`, `enable_stigmergy`) son `False` y `SimulationConfig(**json.loads(json.dumps(cfg.to_dict()))) == cfg`.

#### Scenario: Validación de hiperparámetros evolutivos y compuestos fuera de rango
- **WHEN** se instancia `SimulationConfig(initial_energy=0.0)` o `SimulationConfig(offspring_energy_share=1.0)` o `SimulationConfig(inheritance_discount=1.5)` o `SimulationConfig(redundancy_penalty=0.0)` o `SimulationConfig(num_world_patterns=6, num_composite_patterns=1, composite_order=4)`
- **THEN** se lanza `ValueError` cuyo mensaje nombra el campo inválido.
