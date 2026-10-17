# Spec Delta: Experimental Suite

## ADDED Requirements

### Requirement: Telemetría Evolutiva y Holónica (Métricas M8 a M12)
`src/ide/experiments/metrics.py` SHALL mantener `TickMetrics` con sus 14 campos exactos de Fase I y definir `@dataclass(frozen=True) class EvolutionaryTickMetrics` junto con `EvolutionaryMetricsCollector` para registrar por tick las métricas generacionales (M8), de herencia cultural (M9), de estructura holónica multinivel (M10), de ganancia holónica (M11) y de completaciones compuestas (M12).

#### Scenario: Preservación de TickMetrics y cálculo de EvolutionaryTickMetrics
- **WHEN** se inspeccionan los campos de `TickMetrics` y se registra un tick con `EvolutionaryMetricsCollector` sobre una población con un holón de nivel 1 formado por dos agentes especialistas
- **THEN** `TickMetrics` conserva sus 14 campos de Fase I y `EvolutionaryTickMetrics` incluye `tick`, `active_agents`, `mean_generation`, `max_generation`, `births_this_tick`, `deaths_this_tick`, `mean_energy`, `inherited_coverage_ratio`, `holon_count_by_level == {1: 1}`, `max_holon_level == 1`, `mean_holon_size == 2.0`, `holonic_coverage_gain > 1.0`, `composite_completions` y `stigmergy_active_cells`.

### Requirement: Protocolos 002-A y 002-B (Evolución y Herencia Cultural Acumulativa)
`src/ide/experiments/exp002_runner.py` SHALL implementar `run_protocol_002a_adaptation(config, total_ticks=400)` (mutación genética $R_{13}$ activa vs. genoma congelado) y `run_protocol_002b_cultural_inheritance(config, total_ticks=400)` (herencia cultural vertical $R_{14}$ activa vs. tabula rasa), devolviendo reportes tipados serializables a JSON y exponiendo una CLI reproducible.

#### Scenario: Ejecución rápida de los protocolos 002-A y 002-B
- **WHEN** se invocan `run_protocol_002a_adaptation` y `run_protocol_002b_cultural_inheritance` con `total_ticks=40`
- **THEN** ambos devuelven sus reportes tipados (`AdaptationReport` y `CulturalInheritanceReport`) con métricas generacionales, precisión acumulada y tiempos de convergencia.

### Requirement: Protocolos 003-A y 003-B (Transición Holónica Multinivel y Sinergia Cooperativa)
`src/ide/experiments/exp003_runner.py` SHALL implementar `run_protocol_003a_holonic_transition(config, total_ticks=400)` (jerarquía holónica vs. individualismo ante recursos compuestos de orden $m > C_{\max}$) y `run_protocol_003b_multilevel_scaling(config, total_ticks=400)` (emergencia de niveles $L \ge 2$ y ganancia de cobertura M11), con reportes JSON y CLI reproducible.

#### Scenario: Superación de recursos compuestos por holones en 003-A
- **WHEN** se ejecuta `run_protocol_003a_holonic_transition` en un entorno con recursos compuestos de orden $m > C_{\max}$
- **THEN** el reporte registra las completaciones de recursos compuestos, el nivel máximo holónico alcanzado (`max_holon_level`) y la ganancia de cobertura (`holonic_coverage_gain`) de la condición holónica frente a la condición individualista.
