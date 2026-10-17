# Spec Delta: Experimental Suite

## ADDED Requirements

### Requirement: Telemetría Evolutiva y Holónica (Métricas M8 a M12)
`src/ide/experiments/metrics.py` SHALL mantener `TickMetrics` con sus 14 campos exactos de Fase I y definir `@dataclass(frozen=True) class EvolutionaryTickMetrics` para registrar por tick las métricas de Fase II: `tick`, `active_agents`, `mean_generation` (M8), `max_generation` (M8), `births_this_tick` (M8), `deaths_this_tick` (M8), `mean_energy` (M8), `inherited_coverage_ratio` (M9: fracción de creencias válidas originadas por herencia/transmisión social en agentes de generación $g \ge 1$), `holon_count_by_level` (M10: `dict[int, int]` para $L \ge 1$), `max_holon_level` (M10), `mean_holon_size` (M10), `holonic_coverage_gain` (M11: razón media de cobertura efectiva del holón frente a sus hojas individuales), `composite_completions` (M12) y `stigmergy_active_cells`.

#### Scenario: Preservación de TickMetrics y cálculo de EvolutionaryTickMetrics
- **WHEN** se inspeccionan los campos de `TickMetrics` y se registra un tick con `EvolutionaryMetricsCollector` sobre una población con un holón de nivel 1 formado por dos agentes especialistas
- **THEN** `TickMetrics` conserva exactamente sus 14 campos de Fase I y `EvolutionaryTickMetrics` reporta `holon_count_by_level == {1: 1}`, `max_holon_level == 1`, `mean_holon_size == 2.0` y `holonic_coverage_gain > 1.0`.

### Requirement: Protocolos 002-A y 002-B (Evolución y Herencia Cultural Acumulativa)
`src/ide/experiments/exp002_runner.py` SHALL implementar `run_protocol_002a_adaptation(config, total_ticks=400)` (comparando población con mutación genética activa $R_{13}$ frente a población con genoma congelado $\sigma_{\text{mut}} = 0$) y `run_protocol_002b_cultural_inheritance(config, total_ticks=400)` (comparando población con herencia cultural vertical $R_{14}$ activa $\gamma_{\text{gen}} > 0$ frente a tabula rasa $\gamma_{\text{gen}} = 0$), devolviendo reportes tipados serializables a JSON y exponiendo una CLI reproducible.

#### Scenario: Ejecución rápida de los protocolos 002-A y 002-B
- **WHEN** se invocan `run_protocol_002a_adaptation` y `run_protocol_002b_cultural_inheritance` con `total_ticks=40`
- **THEN** ambos devuelven sus reportes tipados (`AdaptationReport` y `CulturalInheritanceReport`) con métricas generacionales, precisión acumulada y tiempos de convergencia.

### Requirement: Protocolos 003-A y 003-B (Transición Holónica Multinivel y Sinergia Cooperativa)
`src/ide/experiments/exp003_runner.py` SHALL implementar `run_protocol_003a_holonic_transition(config, total_ticks=400)` (comparando población con jerarquía holónica, causalidad descendente y reproducción simbiótica frente a población sin fusión holónica en un entorno con recursos compuestos de orden $m > C_{\max}$) y `run_protocol_003b_multilevel_scaling(config, total_ticks=400)` (midiendo la emergencia de niveles jerárquicos $L \ge 2$ y la ganancia de cobertura holónica M11), devolviendo reportes tipados serializables a JSON y exponiendo una CLI reproducible.

#### Scenario: Superación de recursos compuestos por holones en 003-A
- **WHEN** se ejecuta `run_protocol_003a_holonic_transition` en un entorno con recursos compuestos de orden $m > C_{\max}$
- **THEN** el reporte registra las completaciones de recursos compuestos, el nivel máximo holónico alcanzado (`max_holon_level`) y la ganancia de cobertura (`holonic_coverage_gain`) de la condición holónica frente a la condición individualista.
