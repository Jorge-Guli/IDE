# Spec Delta: Evolutionary Dynamics

## ADDED Requirements

### Requirement: Costo Metabólico sobre el Fenotipo Expresado más el Costo del ADN (R24)
Con `enable_compact_dna=True`, el costo basal de cada agente SHALL ser `compute_metabolic_cost(agent.genome, config)` sobre el genoma expresado en la Fase 0 del tick, más `compute_dna_cost(agent.dna, config) = config.dna_codon_cost * (len(chromosome) + len(plasmids) + len(crispr_memory))`, más la senescencia de $R_{29}$; sin ADN, `compute_dna_cost` SHALL valer 0.

#### Scenario: Costo lineal por codón
- **WHEN** con `dna_codon_cost = 0.0002` se invoca `compute_dna_cost` sobre un ADN con 9 codones en el cromosoma, 2 plásmidos y 1 firma CRISPR, y después con `None`
- **THEN** devuelve `0.0024` y después `0.0` (con tolerancia `1e-9`).

#### Scenario: Costo cuadrático sobre la capacidad expresada
- **WHEN** con `metabolic_base_cost = 0.01`, `memory_capacity_cost = 0.005`, `sensory_radius_cost = 0.0` y `dna_codon_cost = 0.0` un agente en reposo y sin mensajes expresa `memory_capacity = 1` en un contexto, con base 3
- **THEN** su costo basal del tick es `0.01 + 0.005 * 1 = 0.015` y no `0.01 + 0.005 * 9` (con tolerancia `1e-9`).

### Requirement: Reproducción Neutral con el ADN del Donante
Con `enable_compact_dna=True` y `reproduction_mode="neutral"`, el donante sorteado con `donor_rng` SHALL aportar su ADN, en lugar de su genoma, como `dna_source` del hijo, sin cambiar la secuencia de `donor_rng`.

#### Scenario: Donante de ADN en la deriva
- **WHEN** con `enable_compact_dna=True`, `reproduction_mode="neutral"` y la ablación de $R_{13}$ se reproduce un agente y `donor_rng` sortea al agente 5
- **THEN** el ADN del hijo es igual al ADN del agente 5, y `donor_rng` hace las mismas extracciones que con `enable_compact_dna=False`.

### Requirement: Costo de Senescencia Telomérica (R29)
Con `enable_evolution` y `enable_telomere_senescence` activas, al cobrar el metabolismo, con `age = tick - birth_tick`, el costo SHALL sumar `senescence_cost_rate * (age - lifespan) ** 2` si `age > phenotype.lifespan`; `lifespan` se expresa por el destino `0x07` con ADN y vale `telomere_base_lifespan` sin ADN; con la regla apagada, la senescencia SHALL valer 0.

#### Scenario: Agente senescente sin ADN
- **WHEN** con `telomere_base_lifespan = 600` y `senescence_cost_rate = 1e-5` un agente sin ADN nacido en el tick 100 paga el metabolismo del tick 800
- **THEN** `age = 700` y la senescencia suma `1e-5 * 100 ** 2 = 0.1` al costo (con tolerancia `1e-9`).

#### Scenario: Agente dentro de su longevidad
- **WHEN** el mismo agente paga el metabolismo del tick 700 (`age = 600`)
- **THEN** la senescencia suma `0.0`.

### Requirement: Senescencia también en las Endosporas
El costo de senescencia de $R_{29}$ SHALL cobrarse también a los agentes en endospora, sumado a su costo de endospora.

#### Scenario: Endospora senescente
- **WHEN** con $R_{28}$ y $R_{29}$ activas, `metabolic_base_cost = 0.01`, `spore_cost_fraction = 0.05` y `senescence_cost_rate = 1e-5`, una endospora tiene `age - lifespan = 10`
- **THEN** paga `0.0005 + 0.001 = 0.0015` en el tick (con tolerancia `1e-9`).

### Requirement: Registro del Estrés Energético
Siempre, después del cobro metabólico y de la muerte, cada sobreviviente con `energy < stress_energy_ratio * reproduction_threshold` SHALL registrar `last_stress_tick = tick`, sin consumir generadores.

#### Scenario: Registro del último tick de estrés
- **WHEN** con `stress_energy_ratio = 0.35` y `reproduction_threshold = 2.2` un agente sobrevive al tick 30 con `energy = 0.70`, y otro con `energy = 0.80`
- **THEN** el primero tiene `last_stress_tick == 30` (`0.70 < 0.77`) y el segundo conserva su valor anterior.

### Requirement: Escala de Mutación SOS (R30)
Con `enable_evolution` y `enable_sos_mutation` activas, al reproducirse y con el estado del progenitor antes de partir la energía, la escala de mutación SHALL ser `sos_hypermutation_factor` si `last_stress_tick is not None` y `tick - last_stress_tick <= sos_window`; si no, `sos_high_fidelity_factor` si `energy >= sos_high_fidelity_energy_ratio * reproduction_threshold`; y si no, 1.0.

#### Scenario: Las tres escalas
- **WHEN** con `sos_window = 50`, `reproduction_threshold = 2.2` y `sos_high_fidelity_energy_ratio = 1.5` se reproducen en el tick 140 un agente con `last_stress_tick = 100` y `energy = 2.5`, otro con `last_stress_tick = 80` y `energy = 3.4`, y otro sin estrés y con `energy = 2.5`
- **THEN** sus escalas son `4.0`, `0.25` y `1.0`, respectivamente.

### Requirement: SOS Apagada y por Hoja en la Reproducción Holónica
Con `enable_sos_mutation=False`, la escala de mutación SHALL valer 1.0 y la Fase II no cambia en ningún bit; con la regla activa, la reproducción holónica ($R_{17}$) SHALL decidir la escala para cada hoja con su propio estado.

#### Scenario: Escala por hoja
- **WHEN** con $R_{30}$ activa se reproduce un holón cuya hoja 1 registró estrés 10 ticks antes y cuya hoja 2 no registró estrés y tiene energía intermedia
- **THEN** la réplica de la hoja 1 muta con escala `sos_hypermutation_factor` y la de la hoja 2 con escala 1.0.

### Requirement: Entrada en Endospora (R28)
Con `enable_evolution` y `enable_sporulation` activas, en la Fase 5, después de la muerte y antes de la reproducción, en orden de `agent_id`, cada hoja que no es endospora ni nació en el tick SHALL entrar en endospora con `set_endospore(True)` si `energy <= phenotype.spore_threshold`, su observación de la Fase 1 del tick no tiene recursos visibles y, con $R_{19}$ activa, su celda no tiene un rastro con `sign_value > 0`.

#### Scenario: Hambruna sin estímulos
- **WHEN** con `spore_energy_threshold = 0.30` un agente sin ADN termina el cobro metabólico con `energy = 0.25` y su observación del tick no tenía recursos visibles
- **THEN** queda con `is_endospore == True`.

#### Scenario: Recurso visible
- **WHEN** el mismo agente tenía un recurso visible en su observación del tick
- **THEN** no entra en endospora.

### Requirement: Germinación de la Endospora
En la Fase 1, inmediatamente después de `get_observation`, una endospora SHALL germinar con `set_endospore(False)` si su observación tiene algún recurso visible o, con $R_{19}$ activa, su celda tiene un rastro con `sign_value > 0`; germina antes de emitir y actúa normalmente en ese tick.

#### Scenario: Germinación ante un recurso
- **WHEN** una endospora observa un recurso visible en la Fase 1 del tick 50
- **THEN** en ese mismo tick queda con `is_endospore == False`, emite mensajes y decide su acción con `decide_action`.

### Requirement: Física de la Endospora
Una endospora SHALL NOT llamar a `perceive_and_emit_messages`, asimilar estigmergia, emitir ni recibir mensajes (se excluye del ruteo como emisora y destinataria), reproducirse, ni donar o recibir plásmidos; su acción de la Fase 3 SHALL ser `IDLE` sin llamar a `decide_action`, sin consumir `self.rng` y sin sumar oportunidad de decisión en M2; sigue en su holón y su memoria decae.

#### Scenario: Endospora inmóvil y aislada
- **WHEN** una endospora con energía mayor que `reproduction_threshold` y un vecino que emite atraviesa un tick sin germinar
- **THEN** su acción es `IDLE`, no recibe mensajes, no emite, no se reproduce, el estado de `self.rng` no cambia, su memoria decae y sigue en su holón.

### Requirement: Costo de la Endospora
Una endospora SHALL pagar por tick `spore_cost_fraction * metabolic_base_cost`, más la senescencia de $R_{29}$, en lugar del costo basal, el del ADN, el de movimiento y el de mensajes. La supervivencia que produzca $R_{28}$ es programada y se declara así.

#### Scenario: Gasto reducido en endospora
- **WHEN** con `metabolic_base_cost = 0.01`, `spore_cost_fraction = 0.05`, $R_{29}$ apagada y `enable_compact_dna=True` una endospora con 12 codones atraviesa un tick
- **THEN** su energía baja exactamente `0.0005` (con tolerancia `1e-9`).
