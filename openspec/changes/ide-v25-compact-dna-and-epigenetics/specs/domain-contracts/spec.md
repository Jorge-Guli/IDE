# Spec Delta: Domain Contracts

## ADDED Requirements

### Requirement: Enumeración EpigeneticRole
`src/ide/domain/types.py` SHALL definir `EpigeneticRole(Enum)` con exactamente los miembros `NONE`, `EXPLORER`, `LIBRARIAN` y `NERVE`, cuyos valores son sus nombres como `str`, sin modificar los tipos existentes.

#### Scenario: Miembros del rol epigenético
- **WHEN** se enumera `EpigeneticRole`
- **THEN** sus miembros son `NONE`, `EXPLORER`, `LIBRARIAN` y `NERVE`, y `EpigeneticRole.NERVE.value == "NERVE"`.

### Requirement: Tipo Inmutable CompactDNA con Validación de Codones
`CompactDNA` SHALL ser un `@dataclass(frozen=True)` con `chromosome: tuple[int, ...]`, `plasmids: tuple[int, ...] = ()` y `crispr_memory: tuple[int, ...] = ()`, y su `__post_init__` SHALL lanzar `ValueError` si algún codón está fuera de $[0, 2^{32} - 1]$, si `chromosome` está vacío o si `plasmids` o `crispr_memory` tienen codones repetidos.

#### Scenario: Construcciones inválidas
- **WHEN** se construye `CompactDNA(chromosome=())`, `CompactDNA(chromosome=(2**32,))`, `CompactDNA(chromosome=(-1,))`, `CompactDNA(chromosome=(1,), plasmids=(3, 3))` o `CompactDNA(chromosome=(1,), crispr_memory=(5, 5))`
- **THEN** cada construcción lanza `ValueError`.

#### Scenario: Inmutabilidad y codones repetidos en el cromosoma
- **WHEN** se construye `CompactDNA(chromosome=(7, 7))` y se intenta asignar su atributo `plasmids`
- **THEN** la construcción es válida y la asignación lanza `dataclasses.FrozenInstanceError`.

### Requirement: Longitud del Cromosoma Fuera del Tipo
`CompactDNA` SHALL NOT validar la longitud de `chromosome` contra `dna_min_length` ni `dna_max_length`, ni la de `plasmids` contra `max_plasmids`: esas cotas son de la configuración y las aplica la mutación.

#### Scenario: Cromosoma más largo que la cota por defecto
- **WHEN** se construye `CompactDNA(chromosome=tuple(range(40)))`
- **THEN** la construcción no lanza error.

### Requirement: Tipo Inmutable EpigeneticContext
`EpigeneticContext` SHALL ser un `@dataclass(frozen=True)` con `holon_level: int = 0`, `role: EpigeneticRole = EpigeneticRole.NONE` y `energy_ratio: float = 1.0`, sin campo `z_layer` ni estado de endospora.

#### Scenario: Valores por defecto del contexto
- **WHEN** se construye `EpigeneticContext()`
- **THEN** `holon_level == 0`, `role is EpigeneticRole.NONE` y `energy_ratio == 1.0`, y el objeto no tiene atributos `z_layer` ni de endospora.

### Requirement: Tipo Inmutable ExpressedPhenotype
`ExpressedPhenotype` SHALL ser un `@dataclass(frozen=True)` con `genome: AgentGenome`, `lifespan: int`, `spore_threshold: float` y `expressed_codons: int`.

#### Scenario: Fenotipo expresado inmutable
- **WHEN** se construye `ExpressedPhenotype(AgentGenome(), 600, 0.30, 9)` y se intenta asignar `lifespan`
- **THEN** los campos conservan los valores dados y la asignación lanza `dataclasses.FrozenInstanceError`.

### Requirement: Banderas de la Fase II-B Apagadas por Defecto
`SimulationConfig` SHALL incorporar al final, con valor por defecto `False`, las banderas `enable_compact_dna`, `enable_epigenetic_roles`, `enable_plasmid_hgt`, `enable_crispr_immunity`, `enable_sporulation`, `enable_telomere_senescence`, `enable_sos_mutation` y `enable_symbiotic_ratchet`.

#### Scenario: Configuración por defecto
- **WHEN** se construye `SimulationConfig()`
- **THEN** las ocho banderas de la Fase II-B valen `False`.

### Requirement: Hiperparámetros del ADN y de los Plásmidos
`SimulationConfig` SHALL incorporar `dna_codon_cost=0.0002`, `dna_point_mutation_rate=0.05`, `dna_duplication_rate=0.02`, `dna_deletion_rate=0.02`, `dna_min_length=1`, `dna_max_length=32`, `stress_energy_ratio=0.35`, `surplus_energy_ratio=0.85`, `dna_excision_rate=0.02`, `max_plasmids=4`, `hgt_rate=0.05`, `hgt_energy_ratio=0.85`, `crispr_eval_ticks=20`, `crispr_toxicity_threshold=0.20` y `crispr_memory_size=4`.

#### Scenario: Valores por defecto del ADN y los plásmidos
- **WHEN** se construye `SimulationConfig()`
- **THEN** `dna_codon_cost == 0.0002`, `dna_max_length == 32`, `stress_energy_ratio == 0.35`, `surplus_energy_ratio == 0.85`, `max_plasmids == 4`, `hgt_rate == 0.05` y `crispr_memory_size == 4`.

### Requirement: Hiperparámetros de Esporulación, Senescencia, SOS y Trinquete
`SimulationConfig` SHALL incorporar `spore_energy_threshold=0.30`, `spore_cost_fraction=0.05`, `telomere_base_lifespan=600`, `telomere_min_lifespan=150`, `telomere_max_lifespan=1200`, `senescence_cost_rate=1e-5`, `sos_window=50`, `sos_hypermutation_factor=4.0`, `sos_high_fidelity_factor=0.25`, `sos_high_fidelity_energy_ratio=1.5`, `lock_composite_threshold=3` y `lock_coord_discount=0.5`.

#### Scenario: Valores por defecto de R28 a R31
- **WHEN** se construye `SimulationConfig()`
- **THEN** `spore_energy_threshold == 0.30`, `telomere_base_lifespan == 600`, `senescence_cost_rate == 1e-5`, `sos_hypermutation_factor == 4.0`, `lock_composite_threshold == 3` y `lock_coord_discount == 0.5`.

### Requirement: Validación Siempre Activa de Probabilidades y Costos
`SimulationConfig.__post_init__` SHALL lanzar `ValueError`, aunque las banderas estén apagadas, si `dna_point_mutation_rate`, `dna_duplication_rate`, `dna_deletion_rate`, `dna_excision_rate`, `hgt_rate`, `spore_cost_fraction`, `sos_high_fidelity_factor` o `lock_coord_discount` están fuera de $[0, 1]$, o si `dna_codon_cost`, `crispr_toxicity_threshold`, `senescence_cost_rate` o `spore_energy_threshold` son negativos.

#### Scenario: Rangos inválidos con las banderas apagadas
- **WHEN** se construye `SimulationConfig(hgt_rate=1.5)`, `SimulationConfig(lock_coord_discount=-0.1)` o `SimulationConfig(dna_codon_cost=-0.001)`
- **THEN** cada construcción lanza `ValueError`.

### Requirement: Validación Siempre Activa de Razones Positivas
`SimulationConfig.__post_init__` SHALL lanzar `ValueError`, aunque las banderas estén apagadas, si `stress_energy_ratio`, `surplus_energy_ratio`, `hgt_energy_ratio`, `sos_hypermutation_factor` o `sos_high_fidelity_energy_ratio` no son estrictamente positivos, o si no se cumple `stress_energy_ratio < surplus_energy_ratio`.

#### Scenario: Umbrales de energía invertidos
- **WHEN** se construye `SimulationConfig(stress_energy_ratio=0.9, surplus_energy_ratio=0.85)` o `SimulationConfig(sos_hypermutation_factor=0.0)`
- **THEN** cada construcción lanza `ValueError`.

### Requirement: Validación Siempre Activa de los Mínimos Enteros
`SimulationConfig.__post_init__` SHALL lanzar `ValueError` si no se cumple `1 <= dna_min_length <= FOUNDER_DNA_LENGTH <= dna_max_length` (con `FOUNDER_DNA_LENGTH = 9`), si `max_plasmids`, `crispr_eval_ticks`, `crispr_memory_size`, `sos_window`, `lock_composite_threshold` o `telomere_min_lifespan` son menores que 1, o si no se cumple `telomere_min_lifespan <= telomere_base_lifespan <= telomere_max_lifespan`.

#### Scenario: Cotas de longitud y de longevidad incoherentes
- **WHEN** se construye `SimulationConfig(dna_max_length=8)`, `SimulationConfig(dna_min_length=10)`, `SimulationConfig(max_plasmids=0)` o `SimulationConfig(telomere_base_lifespan=100)`
- **THEN** cada construcción lanza `ValueError`.

### Requirement: Requisitos del ADN Compacto
Con `enable_compact_dna=True`, `SimulationConfig.__post_init__` SHALL exigir `enable_evolution=True`, `perception_radius >= 1` y `comm_radius >= 1`, y SHALL lanzar un `ValueError` cuyo mensaje menciona el campo que no se cumple.

#### Scenario: ADN sin evolución
- **WHEN** se construye `SimulationConfig(enable_compact_dna=True, enable_evolution=False)`
- **THEN** se lanza `ValueError` con un mensaje que menciona `enable_evolution`.

### Requirement: Bases dentro de las Cotas de Expresión
Con `enable_compact_dna=True`, `SimulationConfig.__post_init__` SHALL lanzar un `ValueError` que menciona el campo si `alpha_learning` está fuera de $[0.01, 1]$, si `memory_capacity` supera $C^{\text{tope}}$, si `perception_radius` o `comm_radius` superan $r^{\text{tope}}$, o si `spore_energy_threshold > reproduction_threshold`, para que el ADN fundador exprese exactamente la base.

#### Scenario: Umbral de esporulación mayor que el de reproducción
- **WHEN** se construye `SimulationConfig(enable_evolution=True, enable_compact_dna=True, spore_energy_threshold=3.0, reproduction_threshold=2.2)`
- **THEN** se lanza `ValueError` con un mensaje que menciona `spore_energy_threshold`.

#### Scenario: Alfa fuera de la cota de expresión
- **WHEN** se construye `SimulationConfig(enable_evolution=True, enable_compact_dna=True, alpha_learning=0.005)`
- **THEN** se lanza `ValueError` con un mensaje que menciona `alpha_learning`.

### Requirement: Dependencias Inertes de las Banderas Nuevas
`SimulationConfig` SHALL NOT lanzar `ValueError` cuando una bandera nueva está activa y su requisito apagado: $R_{25}$, $R_{26}$ y $R_{27}$ sin `enable_compact_dna`, $R_{25}$ y $R_{31}$ sin `enable_holonic_hierarchy`, $R_{27}$ sin $R_{26}$, y $R_{28}$, $R_{29}$ y $R_{30}$ sin `enable_evolution`; en esos casos la bandera queda inerte.

#### Scenario: Ablación de R24 con R25 activa
- **WHEN** se construye `SimulationConfig(enable_evolution=True, enable_holonic_hierarchy=True, enable_epigenetic_roles=True, enable_compact_dna=False)` o `SimulationConfig(enable_crispr_immunity=True, enable_sporulation=True)`
- **THEN** ninguna construcción lanza error.
