# Spec Delta: Experimental Suite

## ADDED Requirements

### Requirement: Telemetría Evolutiva y Holónica (Métricas M8 a M13)
`src/ide/experiments/metrics.py` SHALL mantener `TickMetrics` con sus 14 campos exactos de Fase I y definir `@dataclass(frozen=True) class EvolutionaryTickMetrics` y `EvolutionaryMetricsCollector`, que registran por tick las métricas generacionales (M8), la proporción social de los descendientes (M9), la estructura holónica (M10), la ganancia holónica (M11), las completaciones compuestas (M12) y la redundancia intra-holón con su control barajado (M13).

#### Scenario: Preservación de TickMetrics y cálculo de EvolutionaryTickMetrics
- **WHEN** se inspeccionan los campos de `TickMetrics` y se registra un tick con `EvolutionaryMetricsCollector` sobre una población con un holón de nivel 1 formado por dos agentes especialistas
- **THEN** `TickMetrics` conserva sus 14 campos de Fase I y `EvolutionaryTickMetrics` incluye `tick`, `active_agents`, `mean_generation`, `max_generation`, `births_this_tick`, `deaths_this_tick`, `mean_energy`, `offspring_social_ratio`, `holon_count_by_level == ((1, 1),)`, `max_holon_level == 1`, `mean_holon_size == 2.0`, `holonic_coverage_gain > 1.0`, `composite_completions`, `intra_holon_redundancy`, `shuffled_holon_redundancy` y `stigmergy_active_cells`.

### Requirement: Redundancia Intra-Holón y Control de Pertenencia Barajada (M13)
`intra_holon_redundancy` SHALL ser la media, sobre los holones raíz con creencias válidas, de $(S - |\bigcup K(\ell)|)/S$ con $S = \sum |K(\ell)|$, y `shuffled_holon_redundancy` la misma media sobre grupos del mismo tamaño formados al permutar las hojas con `shuffle_rng` (`spawn_key=(4,)`), sin alterar la dinámica; ambas valen `None` sin holones con creencias.

#### Scenario: Memorias disjuntas y duplicadas
- **WHEN** un holón tiene dos hojas con $K = \{\rho_0, \rho_1\}$ y $K = \{\rho_2\}$, y otro holón tiene dos hojas con $K = \{\rho_0\}$ y $K = \{\rho_0\}$
- **THEN** `intra_holon_redundancy == 0.25` (media de `0.0` y `0.5`), y con la misma semilla `shuffled_holon_redundancy` es idéntica entre corridas y la historia de la simulación no cambia por calcularla.

### Requirement: Protocolos 002-A y 002-B (Selección y Herencia Cultural)
`src/ide/experiments/exp002_runner.py` SHALL implementar `run_protocol_002a_adaptation(config, total_ticks)` (evolución frente a genoma congelado y frente al control de deriva) y `run_protocol_002b_cultural_inheritance(config, total_ticks)` (herencia cultural frente a tabula rasa), con reportes tipados serializables a JSON y una CLI reproducible.

#### Scenario: Ejecución rápida de los protocolos 002-A y 002-B
- **WHEN** se invocan `run_protocol_002a_adaptation` y `run_protocol_002b_cultural_inheritance` con `total_ticks=40`
- **THEN** devuelven un `AdaptationReport` con `evolved_accuracy`, `frozen_genome_accuracy`, `drift_accuracy`, `selection_gain == evolved_accuracy - drift_accuracy` y los rasgos medios finales, y un `CulturalInheritanceReport` con `social_ratio_gain` y los ticks de convergencia.

### Requirement: Protocolos 003-A y 003-B (Cooperación Compuesta y Ortogonalización)
`src/ide/experiments/exp003_runner.py` SHALL implementar `run_protocol_003a_holonic_transition(config, total_ticks)` (holones frente a individuos ante recursos compuestos de orden $m > C_{\max}$) y `run_protocol_003b_orthogonalization(config, total_ticks)` (redundancia intra-holón sin $R_{18}$ frente al control barajado), con reportes JSON y CLI reproducible.

#### Scenario: Superación de recursos compuestos por holones en 003-A
- **WHEN** se ejecuta `run_protocol_003a_holonic_transition` con `total_ticks=40` en un entorno con recursos compuestos de orden $m > C_{\max}$
- **THEN** el reporte registra `holonic_composite_completions`, `individual_composite_completions`, la precisión de ambas condiciones y `max_holon_level`.

#### Scenario: Ortogonalización medida contra el control barajado en 003-B
- **WHEN** se ejecuta `run_protocol_003b_orthogonalization` con `total_ticks=40` y `enable_downward_causation=False`
- **THEN** el `OrthogonalizationReport` contiene `mean_intra_holon_redundancy`, `mean_shuffled_redundancy`, `orthogonalization_advantage == mean_shuffled_redundancy - mean_intra_holon_redundancy` y `ticks_with_holons`, y si `ticks_with_holons == 0` ambas medias valen `0.0`.
