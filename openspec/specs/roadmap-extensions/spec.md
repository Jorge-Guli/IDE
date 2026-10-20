# Roadmap Extensions (Experimentos 002 a 006) Specification

## Purpose
Definir en `src/ide/domain/extensions.py` los contratos que permiten escalar de Experimento 001 a los Experimentos 002 (Revalidación Social), 003 (Especialización), 004 (Shock Ambiental), 005 (Inteligencia Composicional) y 006 (Evolución) sin romper la compatibilidad de `MicroAgent` ni `SimulationEngine`. Este cambio entrega sólo los contratos, no la lógica de esos experimentos.

## Requirements

### Requirement: Estrategias Enchufables de Confianza Social (Exp 002)
`extensions.py` SHALL definir `@runtime_checkable class TrustStrategyPort(Protocol)` con `compute_sender_trust(receiver_id, sender_id, base_gamma) -> float` y la implementación por defecto `UniformTrustStrategy`, que devuelve siempre `base_gamma`.

#### Scenario: Estrategia uniforme
- **WHEN** se invoca `UniformTrustStrategy().compute_sender_trust(1, 2, 0.75)`
- **THEN** devuelve `0.75`.

### Requirement: Inyección de Estrategia en el Agente
`MicroAgent` y `SimulationEngine` SHALL aceptar un `TrustStrategyPort` opcional y usar su resultado como `sender_trust_factor` de `merge_social_belief`.

#### Scenario: Estrategia que penaliza a un emisor
- **WHEN** el agente usa una estrategia que devuelve `0.25` para el emisor 9 y recibe de él un `BROADCAST_BELIEF` con `c = 0.8` sobre un patrón desconocido
- **THEN** la creencia asimilada tiene `confidence = 0.2`, sin cambios en la firma de `MicroAgent`.

### Requirement: Perfil de Capacidades Plásticas (Exp 003)
`extensions.py` SHALL definir `AgentCapabilities(perception_multiplier=1.0, memory_bonus=0, comm_multiplier=1.0)`, y `MicroAgent.capabilities` SHALL permanecer en esos valores durante todo el Experimento 001.

#### Scenario: Capacidades invariantes
- **WHEN** se ejecutan 100 ticks con `enable_specialization = False`
- **THEN** todos los agentes tienen `capabilities == AgentCapabilities()`.

### Requirement: Shock Ambiental en el Contrato del Entorno (Exp 004)
`EnvironmentPort` SHALL incluir `invert_world_rules(fraction, rng) -> list[Pattern]`, cuya implementación en `ToroidalGrid2D` se define en la capacidad `spatial-environments`.

#### Scenario: Entorno conforme
- **WHEN** se verifica `isinstance(ToroidalGrid2D(config, rng), EnvironmentPort)`
- **THEN** el resultado es `True`, lo que incluye la presencia de `invert_world_rules`.

### Requirement: Contratos contra la Trampa de Evitación (Exp 004)
`SimulationConfig` SHALL incluir `epsilon_recheck: float = 0.0` (re-verificación escéptica de recursos conocidos como dañinos) y `tau_policy: str = "validation"` (alternativa `"evidence_age"`: τ como edad de la evidencia empírica más reciente), validando que `epsilon_recheck` esté en `[0.0, 1.0]` y `tau_policy` en `{"validation", "evidence_age"}`.

#### Scenario: Valores por defecto del Experimento 001
- **WHEN** se instancia `SimulationConfig()`
- **THEN** `epsilon_recheck == 0.0` y `tau_policy == "validation"`.

#### Scenario: Política desconocida
- **WHEN** se instancia `SimulationConfig(tau_policy="siempre")`
- **THEN** se lanza `ValueError` cuyo mensaje menciona `tau_policy`.

### Requirement: Reglas Composicionales Multi-Fragmento (Exp 005)
`extensions.py` SHALL definir `CompositeRule(required_patterns, composite_value)` que rechaza con `ValueError` menos de dos patrones o patrones repetidos, y cuyo `evaluate(known)` devuelve `composite_value` si todos los requeridos están en `known` (`set` o `dict`) y `None` si falta alguno.

#### Scenario: Reconstrucción con dos fragmentos
- **WHEN** una `CompositeRule` requiere $\rho_A$ y $\rho_B$ y se evalúa con un diccionario que contiene ambos
- **THEN** devuelve `composite_value`.

#### Scenario: Fragmento faltante
- **WHEN** se evalúa con un conjunto que sólo contiene $\rho_A$
- **THEN** devuelve `None`.

### Requirement: Operadores Evolutivos (Exp 006)
`extensions.py` SHALL definir `@runtime_checkable class EvolutionaryPort(Protocol)` con `reproduce_and_mutate(parent_params, rng) -> AgentHyperParams` y `DefaultEvolutionaryOperator(mutation_std=0.05)`, que suma ruido gaussiano a α, γ y ε y recorta a `[0.0, 1.0]`.

#### Scenario: Mutación acotada y reproducible
- **WHEN** se invoca `reproduce_and_mutate` 1000 veces desde `AgentHyperParams(1.0, 0.0, 0.5)` y luego se repite con un generador de la misma semilla
- **THEN** todos los coeficientes quedan en `[0.0, 1.0]` y ambas secuencias son idénticas.

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
