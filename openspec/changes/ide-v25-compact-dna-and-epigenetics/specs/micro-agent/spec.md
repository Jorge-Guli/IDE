# Spec Delta: Micro Agent

## ADDED Requirements

### Requirement: Estado Genético, Epigenético y de Vida del Agente
`MicroAgent` SHALL incorporar `dna: CompactDNA | None` (`None` sin ADN), `phenotype: ExpressedPhenotype`, `base_config: SimulationConfig`, `epigenetic_role: EpigeneticRole` (`NONE` al nacer), `birth_tick: int` (0 en los fundadores), `is_endospore: bool` (`False`) y `last_stress_tick: int | None` (`None`), con los métodos `set_epigenetic_role(role)`, `set_dna(dna)` y `set_endospore(flag)`, sin cambiar las firmas de la Fase I.

#### Scenario: Estado inicial de un fundador sin ADN
- **WHEN** se construye un `MicroAgent` fundador con `enable_compact_dna=False`
- **THEN** `dna is None`, `epigenetic_role is EpigeneticRole.NONE`, `birth_tick == 0`, `is_endospore == False`, `last_stress_tick is None` y `base_config` es la configuración del motor.

#### Scenario: Setters del estado nuevo
- **WHEN** se invocan `set_epigenetic_role(EpigeneticRole.NERVE)`, `set_endospore(True)` y `set_dna(dna2)`
- **THEN** `epigenetic_role is EpigeneticRole.NERVE`, `is_endospore == True` y `dna == dna2`.

### Requirement: Configuración Base de la Población
Un `MicroAgent` fundador SHALL recibir como `base_config` la configuración del motor y un descendiente SHALL recibir la `base_config` de su progenitor, nunca la configuración fenotípica, de modo que las bases de la expresión no se acumulen de un tick a otro.

#### Scenario: Expresión repetida sin acumulación
- **WHEN** un agente con `alpha_learning = 0.40` en `base_config` y un codón `ALWAYS_BASAL` aditivo con $\delta = 0.5$ sobre el destino `0x00` invoca `express` en 5 ticks consecutivos con el mismo contexto
- **THEN** después de cada invocación `genome.alpha_learning` vale `0.60` (con tolerancia `1e-9`), y su descendiente tiene `base_config.alpha_learning == 0.40`.

### Requirement: Genoma Expresado
La propiedad `MicroAgent.genome` SHALL devolver el genoma expresado: con ADN, `phenotype.genome`; sin ADN, el genoma de la Fase II.

#### Scenario: Genoma del fenotipo
- **WHEN** un agente con ADN invoca `express` con un contexto en el que su fenotipo tiene `memory_capacity = 4`
- **THEN** `agent.genome == agent.phenotype.genome` y `agent.genome.memory_capacity == 4`.

### Requirement: Expresión sin ADN
`MicroAgent.express(context, tick) -> bool` SHALL no hacer nada y devolver `False` cuando `dna is None`.

#### Scenario: Agente de la Fase II
- **WHEN** un agente con `dna is None` invoca `express(EpigeneticContext(2, EpigeneticRole.NERVE, 0.1), 7)`
- **THEN** devuelve `False` y su genoma, su configuración y su memoria no cambian.

### Requirement: Expresión con ADN y Configuración Fenotípica
Con ADN, `express` SHALL calcular `transcribe_phenotype(dna, context, base_config)` y, si `genome` cambió, reemplazar `_genome`, reemplazar `_config` con el mismo `replace` de los 6 campos que `from_lineage` y llamar a `memory.resize(genome.memory_capacity, tick)`; SHALL devolver `True` si y sólo si cambió algún radio.

#### Scenario: Cambio de capacidad sin cambio de radios
- **WHEN** un agente con `memory_capacity = 3` en `base_config`, 3 creencias y el ADN fundador más `encode_codon(0x18, 0x04, 0, 0, -86)` invoca `express` con `energy_ratio` menor que `stress_energy_ratio`
- **THEN** $x = 3 + 3 \cdot (-86/128) = 0.984375$, `genome.memory_capacity == 1`, `config.memory_capacity == 1`, la memoria queda con 1 creencia por desalojo de menor utilidad y `express` devuelve `False`.

#### Scenario: Cambio de radio
- **WHEN** el fenotipo expresado cambia `perception_radius` de 2 a 3
- **THEN** `express` devuelve `True` y `config.perception_radius == 3`.

### Requirement: Caché de Expresión Equivalente a la Transcripción Directa
`express` MAY memoizar el fenotipo por `(min(context.holon_level, 9), context.role, banda)`, con `banda` estrés, normal o superávit según `stress_energy_ratio` y `surplus_energy_ratio`; el caché SHALL invalidarse cuando cambia el ADN y SHALL dar siempre el mismo fenotipo que `transcribe_phenotype`.

#### Scenario: Caché frente a transcripción directa
- **WHEN** un agente con ADN invoca `express` en una secuencia de contextos con niveles 0 a 12, los cuatro roles y energías en las tres bandas, con un `set_dna` intermedio
- **THEN** después de cada invocación `phenotype == transcribe_phenotype(agent.dna, context, agent.base_config)`.

### Requirement: Descendencia con ADN y Escala de Mutación
`MicroAgent.create_offspring(child_id, tick, rng, genome_source=None, dna_source=None, mutation_scale=1.0)` SHALL, con ADN, mutar `dna_source` o, si es `None`, el ADN propio con `mutate_dna(..., self.base_config, rng, mutation_scale)`, y dar al hijo `birth_tick = tick`, `is_endospore = False`, `last_stress_tick = None` y la `base_config` del progenitor.

#### Scenario: Hijo con el ADN de un donante
- **WHEN** un progenitor con ADN invoca `create_offspring(child_id=9, tick=40, rng=rng, dna_source=donor_dna)` con `mutation_rate = 0.0` y `discrete_mutation_prob = 0.0`
- **THEN** `child.dna == donor_dna`, `child.birth_tick == 40`, `child.is_endospore == False` y `child.last_stress_tick is None`.

### Requirement: Expresión del Hijo al Nacer
Con ADN, el hijo SHALL expresarse en el acto de nacer con `EpigeneticContext(0, EpigeneticRole.NONE, energía_del_hijo / reproduction_threshold)` y `epigenetic_role = NONE`.

#### Scenario: Fenotipo de nacimiento en estrés
- **WHEN** con `reproduction_threshold = 2.2` y `stress_energy_ratio = 0.35` nace un hijo con energía `0.55` cuyo ADN tiene un codón de promotor `0x18` sobre el destino `0x05`
- **THEN** el fenotipo del hijo es `transcribe_phenotype(child.dna, EpigeneticContext(0, EpigeneticRole.NONE, 0.25), base_config)`, con el codón de estrés activo.

### Requirement: Descendencia sin ADN con Escala de Mutación
Sin ADN, `create_offspring` SHALL conservar el comportamiento de la Fase II y, con `mutation_scale != 1.0`, mutar con `replace(config, mutation_rate=scale * mutation_rate, discrete_mutation_prob=min(1.0, scale * discrete_mutation_prob))`; con `mutation_scale == 1.0` SHALL pasar la configuración intacta.

#### Scenario: Escala neutra bit a bit
- **WHEN** dos agentes sin ADN y con la misma semilla invocan `create_offspring` con `mutation_scale=1.0` y sin el argumento
- **THEN** los genomas de los hijos son idénticos y los generadores terminan en el mismo estado.

#### Scenario: Hipermutación del genoma plano
- **WHEN** con `discrete_mutation_prob = 0.10` un agente sin ADN invoca `create_offspring` con `mutation_scale=4.0`
- **THEN** la mutación usa `mutation_rate = 4 * mutation_rate` y `discrete_mutation_prob = 0.40` (con tolerancia `1e-9`).

### Requirement: Herencia de Plásmidos y Firmas sin Ensayos Pendientes
El hijo SHALL heredar `plasmids` y `crispr_memory` dentro del ADN mutado, y SHALL NOT heredar los ensayos CRISPR pendientes del progenitor.

#### Scenario: Ensayos no heredados
- **WHEN** un progenitor con `plasmids = (11,)`, `crispr_memory = (13,)` y un ensayo CRISPR abierto sobre el codón `11` se reproduce sin mutaciones
- **THEN** el hijo tiene `plasmids == (11,)`, `crispr_memory == (13,)` y ningún ensayo abierto.
