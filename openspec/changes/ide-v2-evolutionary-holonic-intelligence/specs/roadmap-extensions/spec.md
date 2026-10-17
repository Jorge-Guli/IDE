# Spec Delta: Roadmap Extensions

## ADDED Requirements

### Requirement: Operador Evolutivo de Genoma Completo
`src/ide/domain/extensions.py` SHALL mantener `AgentHyperParams`, `EvolutionaryPort` y `DefaultEvolutionaryOperator` compatibles con los tests de Fase I y proveer además la función `mutate_genome(genome: AgentGenome, config: SimulationConfig, rng: np.random.Generator) -> AgentGenome` que aplica mutación gaussiana acotada a los rasgos continuos y mutación discreta acotada a los rasgos enteros del genoma.

#### Scenario: Compatibilidad con DefaultEvolutionaryOperator y mutación de AgentGenome
- **WHEN** se invoca `DefaultEvolutionaryOperator(0.05).reproduce_and_mutate(AgentHyperParams(0.3, 0.75, 0.15), rng)` y `mutate_genome(genome, config, rng)`
- **THEN** ambos devuelven instancias inmutables con valores dentro de sus dominios válidos y secuencias deterministas para la misma semilla.

### Requirement: Función de Sinergia Epistémica para Fusión Holónica
`src/ide/domain/extensions.py` SHALL proveer `compute_epistemic_synergy(patterns_a: frozenset[Pattern], patterns_b: frozenset[Pattern], mean_bond_affinity: float) -> float`, que calcula la distancia de Jaccard $|\mathcal{K}_a \triangle \mathcal{K}_b| / |\mathcal{K}_a \cup \mathcal{K}_b|$ multiplicada por `mean_bond_affinity`, devolviendo `0.0` cuando ambos conjuntos de patrones están vacíos.

#### Scenario: Sinergia máxima entre conjuntos disjuntos
- **WHEN** `patterns_a` y `patterns_b` son disjuntos y no vacíos, y `mean_bond_affinity = 0.8`
- **THEN** `compute_epistemic_synergy` devuelve `0.8`.
