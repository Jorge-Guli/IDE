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
`ExpressedPhenotype` SHALL ser un `@dataclass(frozen=True)` con `genome: AgentGenome`, `lifespan: int`, `spore_threshold: float`, `expressed_codons: int` y, en este orden y con valores por defecto iguales a los de sus bases en `SimulationConfig`, `symbiotic_commitment: float = 0.0`, `recombination_propensity: float = 0.0`, `comm_propensity: float = 1.0` y `plasticity_rate: float = 0.0` (design D31, D46.7 y D59.3).

#### Scenario: Fenotipo expresado inmutable
- **WHEN** se construye `ExpressedPhenotype(AgentGenome(), 600, 0.30, 9)` y se intenta asignar `lifespan`
- **THEN** los campos conservan los valores dados, `symbiotic_commitment == 0.0`, `recombination_propensity == 0.0`, `comm_propensity == 1.0`, `plasticity_rate == 0.0` y la asignación lanza `dataclasses.FrozenInstanceError`.

### Requirement: Banderas de la Fase II-B Apagadas por Defecto
`SimulationConfig` SHALL incorporar al final, con valor por defecto `False`, las banderas `enable_compact_dna`, `enable_epigenetic_roles`, `enable_plasmid_hgt`, `enable_crispr_immunity`, `enable_sporulation`, `enable_telomere_senescence`, `enable_sos_mutation`, `enable_symbiotic_ratchet` (D31) y `enable_genetic_policy`, `enable_resource_depletion`, `enable_heterogeneity`, `enable_carcasses`, `enable_energy_transfer`, `enable_predation` y `enable_recombination` (D52.1).

#### Scenario: Configuración por defecto
- **WHEN** se construye `SimulationConfig()`
- **THEN** las quince banderas de la Fase II-B valen `False`.

### Requirement: Hiperparámetros del ADN y de los Plásmidos
`SimulationConfig` SHALL incorporar `dna_codon_cost=0.0002`, `dna_point_mutation_rate=0.05`, `dna_duplication_rate=0.02`, `dna_deletion_rate=0.02`, `dna_min_length=1`, `dna_max_length=32`, `stress_energy_ratio=0.35`, `surplus_energy_ratio=0.85`, `dna_excision_rate=0.02`, `max_plasmids=4`, `hgt_rate=0.05`, `hgt_energy_ratio=0.85`, `crispr_eval_ticks=20`, `crispr_toxicity_threshold=0.20` y `crispr_memory_size=4`.

#### Scenario: Valores por defecto del ADN y los plásmidos
- **WHEN** se construye `SimulationConfig()`
- **THEN** `dna_codon_cost == 0.0002`, `dna_max_length == 32`, `stress_energy_ratio == 0.35`, `surplus_energy_ratio == 0.85`, `max_plasmids == 4`, `hgt_rate == 0.05` y `crispr_memory_size == 4`.

### Requirement: Hiperparámetros de Esporulación, Senescencia, SOS y Trinquete
`SimulationConfig` SHALL incorporar `spore_energy_threshold=0.30`, `spore_cost_fraction=0.05`, `telomere_base_lifespan=600`, `telomere_min_lifespan=150`, `telomere_max_lifespan=1200`, `senescence_cost_rate=1e-5`, `sos_window=50`, `sos_hypermutation_factor=4.0`, `sos_high_fidelity_factor=0.25`, `sos_high_fidelity_energy_ratio=1.5` y `lock_coord_discount=0.5`.

#### Scenario: Valores por defecto de R28 a R31
- **WHEN** se construye `SimulationConfig()`
- **THEN** `spore_energy_threshold == 0.30`, `telomere_base_lifespan == 600`, `senescence_cost_rate == 1e-5`, `sos_hypermutation_factor == 4.0` y `lock_coord_discount == 0.5`.

### Requirement: Eliminación del Umbral de Compuestos del Trinquete
`SimulationConfig` SHALL NOT tener el campo `lock_composite_threshold`: con la reformulación de $R_{31}$ el sello depende del compromiso simbiótico expresado y no de los compuestos completados (design D50.3 y D52.4).

#### Scenario: Campo eliminado
- **WHEN** se construye `SimulationConfig(lock_composite_threshold=3)` y se inspecciona `SimulationConfig().to_dict()`
- **THEN** la construcción lanza `TypeError` y el diccionario no tiene la clave `lock_composite_threshold`.

### Requirement: Hiperparámetros de la Conducta, el Compromiso, la Recombinación y la Telemetría
`SimulationConfig` SHALL incorporar al final `comm_propensity_base=1.0`, `crowding_threshold=3`, `symbiotic_commitment_base=0.0`, `recombination_base=0.0` y `activity_threshold=10`, que cuenta nacimientos portadores (design D52.1 y precisión 43).

#### Scenario: Valores por defecto de R31, R32, R38 y la telemetría
- **WHEN** se construye `SimulationConfig()`
- **THEN** `comm_propensity_base == 1.0`, `crowding_threshold == 3`, `symbiotic_commitment_base == 0.0`, `recombination_base == 0.0` y `activity_threshold == 10`.

### Requirement: Hiperparámetros de la Ecología y de las Interacciones
`SimulationConfig` SHALL incorporar al final `resource_regen_delay=20`, `num_regions=3`, `season_length=0` (sin estaciones), `winter_regen_factor=3.0`, `carcass_value=0.6`, `carcass_lifetime=50`, `share_fraction=0.25`, `share_efficiency=0.9`, `attack_power=0.5`, `predation_efficiency=0.6` y `attack_cost=0.01` (design D52.1).

#### Scenario: Valores por defecto de R33 a R37
- **WHEN** se construye `SimulationConfig()`
- **THEN** `resource_regen_delay == 20`, `num_regions == 3`, `season_length == 0`, `winter_regen_factor == 3.0`, `carcass_value == 0.6`, `carcass_lifetime == 50`, `share_fraction == 0.25`, `share_efficiency == 0.9`, `attack_power == 0.5`, `predation_efficiency == 0.6` y `attack_cost == 0.01`.

### Requirement: Validación Siempre Activa de las Proporciones de la Reformulación
`SimulationConfig.__post_init__` SHALL lanzar `ValueError` nombrando el campo, aunque las banderas estén apagadas, si `comm_propensity_base`, `symbiotic_commitment_base`, `recombination_base`, `share_fraction`, `share_efficiency` o `predation_efficiency` están fuera de $[0, 1]$, si `carcass_value` está fuera de $(0, 1]$, o si `attack_power` o `attack_cost` son negativos (design D52.2).

#### Scenario: Proporciones inválidas con las banderas apagadas
- **WHEN** se construye `SimulationConfig(share_efficiency=1.1)`, `SimulationConfig(comm_propensity_base=-0.1)`, `SimulationConfig(carcass_value=0.0)` o `SimulationConfig(attack_cost=-0.01)`
- **THEN** cada construcción lanza `ValueError` cuyo mensaje nombra el campo.

#### Scenario: Interacciones que no crean energía
- **WHEN** se construye `SimulationConfig(share_efficiency=1.0, predation_efficiency=1.0, carcass_value=1.0)`
- **THEN** la construcción es válida.

### Requirement: Validación Siempre Activa de los Enteros de la Reformulación
`SimulationConfig.__post_init__` SHALL lanzar `ValueError` nombrando el campo, aunque las banderas estén apagadas, si `crowding_threshold`, `resource_regen_delay`, `num_regions`, `carcass_lifetime`, `activity_threshold` o `winter_regen_factor` son menores que 1, si `season_length` es negativo, o si `num_regions > grid_width` (design D52.2).

#### Scenario: Valores enteros inválidos
- **WHEN** se construye `SimulationConfig(resource_regen_delay=0)`, `SimulationConfig(winter_regen_factor=0.5)`, `SimulationConfig(season_length=-1)` o `SimulationConfig(grid_width=8, num_regions=9)`
- **THEN** cada construcción lanza `ValueError` cuyo mensaje nombra el campo.

### Requirement: Campos de la Ampliación en SimulationConfig
`SimulationConfig` SHALL incorporar al final, en este orden, `enable_internal_state: bool = False`, `enable_plasticity: bool = False`, `plasticity_rate_base: float = 0.0`, `enable_signals: bool = False`, `signal_cost: float = 0.002`, `world_shift_period: int = 0` (0 = sin cambios del entorno) y `world_shift_fraction: float = 0.5`, sin cambiar el valor por defecto `dna_max_length = 32` (design D62.1, D62.2 y D63.1).

#### Scenario: Valores por defecto de la ampliación
- **WHEN** se construye `SimulationConfig()`
- **THEN** `enable_internal_state`, `enable_plasticity` y `enable_signals` valen `False`, `plasticity_rate_base == 0.0`, `signal_cost == 0.002`, `world_shift_period == 0`, `world_shift_fraction == 0.5` y `dna_max_length == 32`, y esos siete campos son los últimos de `dataclasses.fields(SimulationConfig)`, en ese orden.

### Requirement: Validación Siempre Activa de la Ampliación
`SimulationConfig.__post_init__` SHALL lanzar `ValueError` nombrando el campo, aunque las banderas estén apagadas, si `plasticity_rate_base` o `world_shift_fraction` están fuera de $[0, 1]$, o si `signal_cost` o `world_shift_period` son negativos (design D63.1).

#### Scenario: Valores inválidos de la ampliación
- **WHEN** se construye `SimulationConfig(plasticity_rate_base=1.1)`, `SimulationConfig(world_shift_fraction=-0.1)`, `SimulationConfig(signal_cost=-0.001)` o `SimulationConfig(world_shift_period=-1)`
- **THEN** cada construcción lanza `ValueError` cuyo mensaje nombra el campo.

#### Scenario: Valores límite válidos
- **WHEN** se construye `SimulationConfig(plasticity_rate_base=1.0, world_shift_fraction=0.0, signal_cost=0.0, world_shift_period=0)`
- **THEN** la construcción es válida.

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
`SimulationConfig.__post_init__` SHALL lanzar `ValueError` si no se cumple `1 <= dna_min_length <= FOUNDER_DNA_LENGTH <= dna_max_length` (con `FOUNDER_DNA_LENGTH = 9`), si `max_plasmids`, `crispr_eval_ticks`, `crispr_memory_size`, `sos_window` o `telomere_min_lifespan` son menores que 1, o si no se cumple `telomere_min_lifespan <= telomere_base_lifespan <= telomere_max_lifespan`.

#### Scenario: Cotas de longitud y de longevidad incoherentes
- **WHEN** se construye `SimulationConfig(dna_max_length=8)`, `SimulationConfig(dna_min_length=10)`, `SimulationConfig(max_plasmids=0)` o `SimulationConfig(telomere_base_lifespan=100)`
- **THEN** cada construcción lanza `ValueError`.

### Requirement: Requisitos del ADN Compacto
Con `enable_compact_dna=True`, `SimulationConfig.__post_init__` SHALL exigir `enable_evolution=True`, `perception_radius >= 1` y `comm_radius >= 1`, y SHALL lanzar un `ValueError` cuyo mensaje menciona el campo que no se cumple.

#### Scenario: ADN sin evolución
- **WHEN** se construye `SimulationConfig(enable_compact_dna=True, enable_evolution=False)`
- **THEN** se lanza `ValueError` con un mensaje que menciona `enable_evolution`.

### Requirement: Longitud del Cromosoma con la Política Genética
Con `enable_compact_dna=True` y `enable_genetic_policy=True`, `SimulationConfig.__post_init__` SHALL lanzar un `ValueError` que menciona el campo si no se cumple `dna_max_length >= founder_dna_length(config)` (13) o `dna_min_length <= founder_dna_length(config)`, para que el fundador conductual quepa en las cotas de la mutación (precisión 27).

#### Scenario: Cromosoma máximo menor que el fundador conductual
- **WHEN** se construye `SimulationConfig(enable_evolution=True, enable_compact_dna=True, enable_genetic_policy=True, dna_max_length=12)`
- **THEN** se lanza `ValueError` con un mensaje que menciona `dna_max_length`.

#### Scenario: Misma cota sin política genética
- **WHEN** se construye `SimulationConfig(enable_evolution=True, enable_compact_dna=True, dna_max_length=12)`
- **THEN** la construcción es válida, porque sin política genética el fundador tiene 9 codones.

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

### Requirement: Dependencias Inertes de las Banderas de la Reformulación
`SimulationConfig` SHALL NOT lanzar `ValueError` cuando una bandera de la reformulación está activa y su requisito apagado: $R_{31}$, $R_{32}$ y $R_{38}$ sin `enable_compact_dna`; $R_{28}$, $R_{36}$ y $R_{37}$ sin `enable_genetic_policy`; $R_{35}$ y $R_{38}$ sin `enable_evolution`; y las estaciones de $R_{34}$ (`season_length > 0`) sin `enable_resource_depletion`. En esos casos la bandera queda inerte (design D52.3).

#### Scenario: Banderas de la reformulación sin sus requisitos
- **WHEN** se construye `SimulationConfig(enable_genetic_policy=True, enable_recombination=True, enable_carcasses=True)`, `SimulationConfig(enable_evolution=True, enable_compact_dna=True, enable_energy_transfer=True, enable_predation=True, enable_sporulation=True)` o `SimulationConfig(enable_heterogeneity=True, season_length=500)`
- **THEN** ninguna construcción lanza error.

### Requirement: Dependencias Inertes de la Ampliación
`SimulationConfig` SHALL NOT lanzar `ValueError` cuando `enable_internal_state`, `enable_plasticity` o `enable_signals` están activas sin que $R_{32}$ esté efectivamente activa (`enable_compact_dna` y `enable_genetic_policy`): en ese caso $R_{39}$, $R_{40}$ y $R_{41}$ quedan inertes (design D57.3 y precisión 31).

#### Scenario: Banderas de la ampliación sin la política genética
- **WHEN** se construye `SimulationConfig(enable_internal_state=True, enable_plasticity=True, enable_signals=True)` o `SimulationConfig(enable_evolution=True, enable_compact_dna=True, enable_internal_state=True, enable_signals=True)`
- **THEN** ninguna construcción lanza error.

### Requirement: Enumeración Behavior
`src/ide/domain/types.py` SHALL definir `Behavior(Enum)` con exactamente los miembros `CONSUME`, `EXPLORE`, `NAVIGATE`, `WANDER`, `SHARE`, `ATTACK`, `FLEE` y `SPORULATE`, en ese orden, que es el de desempate de la política genética, cada uno con su nombre en texto como valor (design D46.1, D47.1 y precisión 26).

#### Scenario: Miembros y orden de las conductas
- **WHEN** se enumera `list(Behavior)`
- **THEN** la lista es `[CONSUME, EXPLORE, NAVIGATE, WANDER, SHARE, ATTACK, FLEE, SPORULATE]` y `Behavior.FLEE.value == "FLEE"`.

### Requirement: Tipo Inmutable VisibleAgent
`VisibleAgent` SHALL ser un `@dataclass(frozen=True)` con `agent_id: int`, `distance: int` (Chebyshev toroidal), `recommended_move` (hacia el agente; `None` si `distance == 0`) y `flee_move` (el movimiento de Moore que maximiza la distancia, con desempate por el orden de `MOORE_MOVES`), sin coordenadas (design D47.1).

#### Scenario: Agente visible sin coordenadas
- **WHEN** se inspeccionan los campos de `VisibleAgent` con `dataclasses.fields` y se intenta asignar `distance` a una instancia
- **THEN** el conjunto de nombres es exactamente `{agent_id, distance, recommended_move, flee_move}` y la asignación lanza `dataclasses.FrozenInstanceError`.

### Requirement: Tipo Inmutable SocialPerception
`SocialPerception` SHALL ser un `@dataclass(frozen=True)` con `adjacent: tuple[int, ...] = ()`, `weakest_adjacent: int | None = None`, `weaker_adjacent: bool = False`, `flee_move = None`, `crowded: bool = False` y `carcass_visible: bool = False`, con la semántica de design D47.1 y D47.3.

#### Scenario: Percepción social vacía por defecto
- **WHEN** se construye `SocialPerception()`
- **THEN** `adjacent == ()`, `weakest_adjacent is None`, `weaker_adjacent is False`, `flee_move is None`, `crowded is False` y `carcass_visible is False`, y asignar un campo lanza `dataclasses.FrozenInstanceError`.

### Requirement: Tipo Inmutable SensorySignals
`SensorySignals` SHALL ser un `@dataclass(frozen=True)` hashable con los campos booleanos, en este orden, `known_good`, `unknown`, `no_resource`, `neighbor_adjacent`, `weaker_adjacent`, `stronger_near`, `crowded` y `carcass`, que leen los promotores `0x20`–`0x27`, seguidos de los cuatro eventos del tick anterior de `EventSignals`, `attacked`, `ate`, `lost_energy` y `received_energy`, que leen los promotores `0x28`–`0x2B` (design D46.2, D47.1 y D60.1).

#### Scenario: Campos y orden de las señales
- **WHEN** se inspeccionan los campos de `SensorySignals` con `dataclasses.fields` y se usa una instancia como clave de `dict`
- **THEN** los nombres, en orden, son `known_good`, `unknown`, `no_resource`, `neighbor_adjacent`, `weaker_adjacent`, `stronger_near`, `crowded`, `carcass`, `attacked`, `ate`, `lost_energy` y `received_energy`, y el uso como clave no lanza `TypeError`.

### Requirement: Tipo Inmutable EventSignals
`src/ide/domain/types.py` SHALL definir `EventSignals` como `@dataclass(frozen=True)` con cuatro campos booleanos, en este orden y en `False` por defecto: `attacked` (fue objetivo de un ataque con éxito y `stolen > 0`), `ate` (consumió un recurso con valor experimentado positivo), `lost_energy` (su energía al final del tick fue menor que al principio) y `received_energy` (fue objetivo de un `SHARE` que lo alcanzó) (design D58.5).

#### Scenario: Eventos por defecto
- **WHEN** se construye `EventSignals()` y se intenta asignar `ate`
- **THEN** los cuatro campos valen `False`, sus nombres en orden son `attacked`, `ate`, `lost_energy` y `received_energy`, y la asignación lanza `dataclasses.FrozenInstanceError`.

### Requirement: Tipo Inmutable BehaviorEvaluation
`BehaviorEvaluation` SHALL ser un `@dataclass(frozen=True)` con, en este orden, `drives: tuple[float, ...]` (uno por `Behavior`), `set_mask: int`, `clear_mask: int`, `emitted: int` (máscara de símbolos emitidos) y `plastic: tuple[tuple[int, ...], ...]` (índices de los codones plásticos activos por conducta, en el orden de `Behavior`); `SIGNAL` no es una conducta y no tiene impulso (design D60.1 y D60.2).

#### Scenario: Campos de la evaluación de conducta
- **WHEN** se inspeccionan los campos de `BehaviorEvaluation` y se intenta asignar `emitted` a una instancia
- **THEN** los nombres, en orden, son `drives`, `set_mask`, `clear_mask`, `emitted` y `plastic`, y la asignación lanza `dataclasses.FrozenInstanceError`.

### Requirement: Acciones de Interacción entre Agentes
`ActionType` SHALL agregar los miembros `SHARE`, `ATTACK` y `SPORULATE`, con su nombre en texto como valor, sin cambiar `MOVE`, `INTERACT` ni `IDLE`, y `AgentAction.target` SHALL ser el `agent_id` del objetivo en `SHARE` y `ATTACK`, y `None` en `SPORULATE` (design D47.1 y precisión 26).

#### Scenario: Acciones nuevas
- **WHEN** se construyen `AgentAction(ActionType.SHARE, 4)`, `AgentAction(ActionType.ATTACK, 4)` y `AgentAction(ActionType.SPORULATE)`
- **THEN** los dos primeros tienen `target == 4`, el tercero `target is None`, `ActionType.SPORULATE.value == "SPORULATE"` y `ActionType` conserva `MOVE`, `INTERACT` e `IDLE`.

### Requirement: Sub-Puerto EcologicalEnvironmentPort
`src/ide/domain/ports.py` SHALL definir `@runtime_checkable class EcologicalEnvironmentPort(EvolutionaryEnvironmentPort, Protocol)` que agrega `get_visible_agents(agent_id) -> tuple[VisibleAgent, ...]` (los agentes dentro del radio de percepción, ordenados por `(distance, agent_id)` y sin el observador), `deposit_carcass(agent_id, value, tick) -> None` y `get_resource_count() -> int`, sin cambiar `EnvironmentPort` ni `EvolutionaryEnvironmentPort` (design D47.2 y precisión 29).

#### Scenario: La grilla cumple los tres puertos
- **WHEN** se verifica `isinstance(ToroidalGrid2D(config, rng), EcologicalEnvironmentPort)` y se inspeccionan los métodos de `EnvironmentPort` y `EvolutionaryEnvironmentPort`
- **THEN** es `True`, y los dos puertos anteriores declaran exactamente los mismos métodos que en la Fase II.

#### Scenario: Orden de los agentes visibles
- **WHEN** un observador tiene dentro de su radio de percepción a los agentes 9 y 3 a distancia 1 y al agente 2 a distancia 2
- **THEN** `get_visible_agents` devuelve sus entradas en el orden 3, 9 y 2, y ninguna es la del observador.
