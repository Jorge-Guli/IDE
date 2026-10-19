# Spec Delta: Experimental Suite

## ADDED Requirements

### Requirement: Telemetría Evolutiva y Holónica (Métricas M8 a M13)
`src/ide/experiments/metrics.py` SHALL mantener `TickMetrics` con sus 14 campos exactos de Fase I y definir `@dataclass(frozen=True) class EvolutionaryTickMetrics` y `EvolutionaryMetricsCollector`, que registran por tick las métricas generacionales (M8), la proporción social de los descendientes (M9), la estructura holónica (M10), la ganancia holónica (M11), las completaciones compuestas (M12) y la cobertura colectiva adquirida con su reducción de redundancia (M13).

#### Scenario: Preservación de TickMetrics y cálculo de EvolutionaryTickMetrics
- **WHEN** se inspeccionan los campos de `TickMetrics` y se registra un tick con `EvolutionaryMetricsCollector` sobre una población con un holón de nivel 1 formado por dos agentes especialistas
- **THEN** `TickMetrics` conserva sus 14 campos de Fase I y `EvolutionaryTickMetrics` incluye `tick`, `active_agents`, `mean_generation`, `max_generation`, `births_this_tick`, `deaths_this_tick`, `mean_energy`, `offspring_social_ratio`, `holon_count_by_level == ((1, 1),)`, `max_holon_level == 1`, `mean_holon_size == 2.0`, `holonic_coverage_gain > 1.0`, `composite_completions`, `acquired_coverage`, `redundancy_reduction`, `eligible_holons` y `stigmergy_active_cells`.

### Requirement: Cobertura Colectiva Adquirida desde la Formación (M13)
`acquired_coverage` SHALL ser la media, sobre los holones raíz formados por `BOND` con edad $\ge 1$, de $(\text{cov}(U) - \text{cov}_0(U))/|U|$, donde `cov` cuenta patrones elementales distintos con confianza $\ge$ `decision_conf_threshold` y signo correcto y $\text{cov}_0$ sale de `formation_knowledge`, que se reinicia al estado actual cuando el holón pierde un miembro; SHALL valer `None` sin holones elegibles.

#### Scenario: Holón que gana cobertura después de formarse
- **WHEN** un holón formado por `BOND` con dos hojas que conocen correctamente $\{\rho_0, \rho_1\}$ y $\{\rho_0\}$ pasa, dos ticks después, a $\{\rho_0, \rho_1\}$ y $\{\rho_2\}$, y una creencia de signo incorrecto en una hoja no cuenta
- **THEN** `acquired_coverage == 0.5` (de 2 a 3 patrones distintos, entre 2 hojas) y `redundancy_reduction == 1/3` (con tolerancia `1e-9`), y sin holones elegibles ambas valen `None`.

#### Scenario: Olvidar un duplicado no suma
- **WHEN** un holón formado por `BOND` con hojas $\{\rho_0\}$ y $\{\rho_0\}$ pasa a $\{\rho_0\}$ y $\{\}$ porque una hoja olvidó $\rho_0$
- **THEN** su aporte a `acquired_coverage` es `0.0`, aunque su `redundancy_reduction` sea `0.5`.

#### Scenario: La muerte de una hoja no cuenta como ganancia
- **WHEN** un holón formado por `BOND` con hojas $A = \{\rho_0\}$ y $B = \{\rho_1\}$ y una tercera hoja $C = \{\rho_2\}$ ve que $A$ aprende $\rho_1$ (lo duplica) y después muere $B$ en el tick $t$
- **THEN** el holón reinicia su estado de formación al de $A$ y $C$ en $t$ (`formation_tick == t`), no es elegible en $t$, y en $t+1$, sin otros cambios, su aporte a `acquired_coverage` es `0.0`.

#### Scenario: Los holones nacidos por R17 no entran
- **WHEN** el único holón raíz de edad $\ge 1$ fue creado por `reproduce_holon`
- **THEN** `acquired_coverage is None` y `eligible_holons == 0`.

### Requirement: Protocolos 002-A y 002-B (Selección y Herencia Cultural)
`src/ide/experiments/exp002_runner.py` SHALL implementar `run_protocol_002a_adaptation(config, total_ticks)` (evolución frente a genoma congelado y frente al control de deriva) y `run_protocol_002b_cultural_inheritance(config, total_ticks)` (herencia cultural frente a tabula rasa), con reportes tipados serializables a JSON y una CLI reproducible.

#### Scenario: Ejecución rápida de los protocolos 002-A y 002-B
- **WHEN** se invocan `run_protocol_002a_adaptation` y `run_protocol_002b_cultural_inheritance` con `total_ticks=40`
- **THEN** devuelven un `AdaptationReport` con `evolved_accuracy`, `frozen_genome_accuracy`, `drift_accuracy`, `selection_gain == evolved_accuracy - drift_accuracy` y los rasgos medios finales, y un `CulturalInheritanceReport` con `social_ratio_gain` y los ticks de convergencia.

### Requirement: Protocolos 003-A y 003-B (Cooperación Compuesta y Cobertura Colectiva)
`src/ide/experiments/exp003_runner.py` SHALL implementar `run_protocol_003a_holonic_transition(config, total_ticks)` (holones frente a individuos ante recursos compuestos de orden $m > C_{\max}$) y `run_protocol_003b_orthogonalization(config, total_ticks)` (cobertura colectiva adquirida sin $R_{18}$, con y sin la vista del holón $R_{22}$), con reportes JSON y CLI reproducible.

#### Scenario: Superación de recursos compuestos por holones en 003-A
- **WHEN** se ejecuta `run_protocol_003a_holonic_transition` con `total_ticks=40` en un entorno con recursos compuestos de orden $m > C_{\max}$
- **THEN** el reporte registra `holonic_composite_completions`, `individual_composite_completions`, la precisión de ambas condiciones y `max_holon_level`.

#### Scenario: Cobertura colectiva con y sin la vista del holón en 003-B
- **WHEN** se ejecuta `run_protocol_003b_orthogonalization` con `total_ticks=40` y `enable_downward_causation=False`
- **THEN** el `OrthogonalizationReport` contiene `mean_acquired_coverage`, `mean_acquired_coverage_without_view`, `coverage_advantage` igual a su diferencia, las reducciones de redundancia descriptivas de ambas condiciones, `holon_ticks` y `holon_ticks_without_view`, y las medias son promedios por par (tick, holón elegible).
