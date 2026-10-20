# Spec Delta: Experimental Suite

## ADDED Requirements

### Requirement: Telemetría Genética GeneticTickMetrics
`metrics.py` SHALL definir `GeneticTickMetrics` como `@dataclass(frozen=True)` con los campos `tick`, `mean_chromosome_length`, `mean_expressed_codons`, `mean_plasmids`, `endospores`, `senescent_agents`, `mean_age`, `max_age`, `explorers`, `librarians`, `nerves`, `locked_holons`, `hgt_transfers`, `crispr_rejections` y `crispr_purges`.

#### Scenario: Campos de la telemetría genética
- **WHEN** se inspeccionan los campos de `GeneticTickMetrics`
- **THEN** son exactamente los 15 enumerados, y asignar uno de ellos lanza `dataclasses.FrozenInstanceError`.

### Requirement: Historial Genético Separado
El motor SHALL registrar un `GeneticTickMetrics` en cada tick en `engine.genetic_history: list[GeneticTickMetrics]`, sin agregar campos a `TickMetrics` (14 campos) ni a `EvolutionaryTickMetrics`.

#### Scenario: Registro por tick sin tocar las métricas previas
- **WHEN** se ejecutan 30 ticks con `enable_compact_dna=True`
- **THEN** `len(engine.genetic_history) == 30`, `TickMetrics` conserva sus 14 campos y `EvolutionaryTickMetrics` sus campos de la Fase II.

### Requirement: Semántica de los Campos Genéticos
En `GeneticTickMetrics`, `mean_chromosome_length`, `mean_expressed_codons` y `mean_plasmids` SHALL valer 0.0 sin ADN; `senescent_agents` SHALL contar los agentes con `age > lifespan`; y `hgt_transfers`, `crispr_rejections` y `crispr_purges` SHALL contar los eventos del tick, no acumulados.

#### Scenario: Población sin ADN
- **WHEN** se ejecuta un tick con `enable_evolution=True`, `enable_telomere_senescence=True` y `enable_compact_dna=False`, con un agente de `age = 700` y `telomere_base_lifespan = 600`
- **THEN** el registro del tick tiene `mean_chromosome_length == 0.0`, `mean_expressed_codons == 0.0`, `mean_plasmids == 0.0` y `senescent_agents >= 1`.

#### Scenario: Eventos por tick
- **WHEN** en el tick 30 se aplican 2 transferencias y se bloquea 1, y en el tick 31 no hay conjugación
- **THEN** el registro del tick 30 tiene `crispr_rejections == 1` y el del tick 31 tiene `hgt_transfers == 0` y `crispr_rejections == 0`.

### Requirement: Runner de los Protocolos de la Fase II-B
`src/ide/experiments/exp25_runner.py` SHALL implementar los protocolos `002c`, `002d`, `002e` y `003c` con la infraestructura `ProtocolSpec` de `phase2_cli.py`, con reportes serializables a JSON y CLI, y un resumen por condición que incluye `final_accuracy`, `composite_completions`, `final_agents`, `final_active_agents` (hojas vivas fuera de endospora), `max_generation` y el resumen genético del último tick.

#### Scenario: Ejecución corta y serialización
- **WHEN** se ejecuta cada uno de los cuatro protocolos con `total_ticks=40` y se serializa su reporte a JSON
- **THEN** cada condición del reporte contiene `final_accuracy`, `composite_completions`, `final_agents`, `final_active_agents`, `max_generation` y los campos de `GeneticTickMetrics` del último tick.

### Requirement: Condiciones del Protocolo 002c
El protocolo `002c` SHALL comparar, en este orden, las condiciones `dna` (base), `flat_genome` (sin $R_{24}$), `frozen_dna` (sin $R_{13}$) y `drift` (sin $R_{12}$).

#### Scenario: Condiciones de 002c
- **WHEN** se generan las condiciones de `002c` sobre su configuración base
- **THEN** son `dna`, `flat_genome` con `enable_compact_dna=False`, `frozen_dna` con `mutation_rate == 0.0` y `discrete_mutation_prob == 0.0`, y `drift` con `reproduction_mode == "neutral"`.

### Requirement: Condiciones de los Protocolos 002d, 002e y 003c
El protocolo `002d` SHALL comparar `telomeres` (base) con `no_telomeres` (sin $R_{29}$); `002e`, `sporulation` (base) con `no_sporulation` (sin $R_{28}$); y `003c`, `roles` (base) con `no_roles` (sin $R_{25}$) y `unlocked` (sin $R_{31}$).

#### Scenario: Condiciones de 003c
- **WHEN** se generan las condiciones de `003c` sobre su configuración base
- **THEN** son `roles`, `no_roles` con `enable_epigenetic_roles=False` y `unlocked` con `enable_symbiotic_ratchet=False`.

#### Scenario: Condiciones de 002d y 002e
- **WHEN** se generan las condiciones de `002d` y de `002e`
- **THEN** `002d` tiene `telomeres` y `no_telomeres` con `enable_telomere_senescence=False`, y `002e` tiene `sporulation` y `no_sporulation` con `enable_sporulation=False`.
