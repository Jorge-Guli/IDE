# Spec Delta: Roadmap Extensions (Experimentos 002 a 006)

## Purpose
Definir los contratos e interfaces extensibles en `src/ide/domain/extensions.py` que permiten escalar la plataforma desde el Experimento 001 hacia los Experimentos 002 (Revalidación Social), 003 (Especialización Emergente), 004 (Reorganización ante Shock Ambiental), 005 (Inteligencia Composicional) y 006 (Evolución y Selección) sin romper la compatibilidad de `MicroAgent` ni `SimulationEngine`.

## ADDED Requirements

### Requirement: Estrategias Enchufables de Confianza Social (Experimento 002)
El módulo `src/ide/domain/extensions.py` SHALL definir el protocolo `@runtime_checkable class TrustStrategyPort(Protocol)` con el método `compute_sender_trust(receiver_id: int, sender_id: int, base_gamma: float) -> float`, junto con una implementación por defecto `UniformTrustStrategy` que devuelva siempre `base_gamma` en el Experimento 001.

#### Scenario: Inyección de estrategia de confianza personalizada
- **WHEN** un agente o motor utiliza una implementación de `TrustStrategyPort` que penaliza a emisores que enviaron creencias refutadas previamente
- **THEN** `compute_sender_trust` devuelve un factor de descuento menor a `base_gamma` para dicho emisor sin requerir cambios en la firma de `MicroAgent`.

### Requirement: Perfil de Especialización Plástica (Experimento 003)
El sistema SHALL definir la estructura `AgentCapabilities` en `src/ide/domain/extensions.py` con multiplicadores plásticos (`perception_multiplier: float = 1.0`, `memory_bonus: int = 0`, `comm_multiplier: float = 1.0`) que puedan ser modulados por la experiencia acumulada del agente cuando `config.enable_specialization == True`.

#### Scenario: Comportamiento estático por defecto en Experimento 001
- **WHEN** `config.enable_specialization` es `False` (valor por defecto en Experimento 001)
- **THEN** todos los agentes mantienen `AgentCapabilities` uniformes e invariantes durante toda la simulación.

### Requirement: Perturbación de Reglas del Mundo para Shock Ambiental (Experimento 004)
El contrato `EnvironmentPort` y la clase `ToroidalGrid2D` SHALL proveer el método `invert_world_rules(fraction: float, rng: np.random.Generator) -> list[Pattern]` que invierta el signo de `true_value` ($+v \leftrightarrow -v$) de una fracción de los patrones del mundo en pleno vuelo para medir la plasticidad y reorganización colectiva.

#### Scenario: Inversión abrupta del 50% de las reglas del entorno
- **WHEN** existen 12 patrones en el mundo y se invoca `env.invert_world_rules(0.5, rng)` en el tick $t=500$
- **THEN** exactamente 6 patrones invierten el signo de su `true_value` en todos los recursos actuales y futuros de ese patrón, devolviendo la lista de los 6 patrones alterados.

### Requirement: Reglas Composicionales Multi-Fragmento (Experimento 005)
El módulo `src/ide/domain/extensions.py` SHALL definir `CompositeRule` donde la evaluación de un recurso compuesto depende de combinar al menos dos patrones elementales ($\rho_A \land \rho_B \implies v_{\text{comp}}$), permitiendo evaluar tareas donde distintos subgrupos poseen fragmentos complementarios.

#### Scenario: Reconstrucción de valor compuesto mediante dos fragmentos
- **WHEN** una `CompositeRule` requiere los fragmentos $\rho_A$ y $\rho_B$ y el agente reúne ambos fragmentos en su contexto de decisión (memoria local + respuestas `QUERY_RESPONSE` del tick)
- **THEN** `CompositeRule.evaluate(known_patterns)` retorna el valor compuesto verdadero.

### Requirement: Operadores Evolutivos de Reproducción y Mutación (Experimento 006)
El módulo `src/ide/domain/extensions.py` SHALL definir el protocolo `@runtime_checkable class EvolutionaryPort(Protocol)` con el método `reproduce_and_mutate(parent_params: AgentHyperParams, rng: np.random.Generator) -> AgentHyperParams` para mutar tasas locales ($\alpha, \gamma, \epsilon$) en experimentos evolutivos futuros.

#### Scenario: Mutación acotada de hiperparámetros de agente
- **WHEN** se invoca `DefaultEvolutionaryOperator().reproduce_and_mutate(params, rng)` con `mutation_std = 0.05`
- **THEN** el nuevo objeto `AgentHyperParams` mantiene todos sus coeficientes dentro del intervalo válido $[0.0, 1.0]$ y es reproducible dada la misma semilla.
