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
Con `enable_compact_dna=True` y `reproduction_mode="neutral"`, el donante sorteado con `donor_rng` SHALL aportar su ADN, en lugar de su genoma, como `dna_source` del hijo, sin cambiar la secuencia de `donor_rng` de la reproducción individual; la reproducción holónica neutral agrega sus propios sorteos (design precisión 41).

#### Scenario: Donante de ADN en la reproducción neutral
- **WHEN** con `enable_compact_dna=True`, `reproduction_mode="neutral"`, la ablación de $R_{13}$ y sin reproducción holónica ($R_{17}$ apagada) se reproduce un agente y `donor_rng` sortea al agente 5
- **THEN** el ADN del hijo es igual al ADN del agente 5, y `donor_rng` hace las mismas extracciones que con `enable_compact_dna=False`; con $R_{17}$ activa la secuencia difiere por los sorteos de las hojas (design precisión 41).

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

### Requirement: Entrada en Endospora sólo por la Conducta SPORULATE (R28)
Una hoja SHALL entrar en endospora (`set_endospore(True)`) sólo al ejecutarse en la Fase 4 su acción `SPORULATE`, factible con `enable_genetic_policy`, `enable_evolution` y `enable_sporulation` activas y `energy <= phenotype.spore_threshold`. La entrada automática por umbral de design D38 se elimina: la Fase 5 no pone a nadie en endospora, y sin la política genética $R_{28}$ es inerte.

#### Scenario: Entrada por la conducta
- **WHEN** con la política genética y $R_{28}$ activas una hoja con `energy = 0.25` y `phenotype.spore_threshold = 0.30` decide `SPORULATE`
- **THEN** al ejecutarse su acción en la Fase 4 queda con `is_endospore == True`.

#### Scenario: Sin entrada por umbral
- **WHEN** con $R_{28}$ activa una hoja termina el metabolismo con `energy = 0.25`, `phenotype.spore_threshold = 0.30` y sin recursos visibles, sin haber ejecutado `SPORULATE`
- **THEN** sigue con `is_endospore == False`.

#### Scenario: R28 inerte sin la política genética
- **WHEN** se corre con `enable_sporulation=True` y `enable_genetic_policy=False`
- **THEN** ningún agente entra nunca en endospora y no se lanza error.

### Requirement: Germinación de la Endospora
En la Fase 1, inmediatamente después de `get_observation`, una endospora SHALL germinar con `set_endospore(False)` si su observación tiene algún recurso visible o, con $R_{19}$ activa, su celda tiene un rastro con `sign_value > 0`; germina antes de emitir y actúa normalmente en ese tick.

#### Scenario: Germinación ante un recurso
- **WHEN** una endospora observa un recurso visible en la Fase 1 del tick 50
- **THEN** en ese mismo tick queda con `is_endospore == False`, emite mensajes y decide su acción con su política.

### Requirement: Física de la Endospora
Una endospora SHALL NOT llamar a `perceive_and_emit_messages`, asimilar estigmergia, emitir ni recibir mensajes (se excluye del ruteo como emisora y destinataria), reproducirse, ni donar o recibir plásmidos; su acción de la Fase 3 SHALL ser `IDLE` sin llamar a su política, sin consumir `self.rng` y sin sumar oportunidad de decisión en M2; sigue en su holón y su memoria decae.

#### Scenario: Endospora inmóvil y aislada
- **WHEN** una endospora con energía mayor que `reproduction_threshold` y un vecino que emite atraviesa un tick sin germinar
- **THEN** su acción es `IDLE`, no recibe mensajes, no emite, no se reproduce, el estado de `self.rng` no cambia, su memoria decae y sigue en su holón.

### Requirement: Costo de la Endospora
Una endospora SHALL pagar por tick `spore_cost_fraction * metabolic_base_cost`, más la senescencia de $R_{29}$, en lugar del costo basal, el del ADN, el de movimiento y el de mensajes. $R_{28}$ sólo pone a disposición ese estado de bajo gasto: si se usa lo decide el ADN.

#### Scenario: Gasto reducido en endospora
- **WHEN** con `metabolic_base_cost = 0.01`, `spore_cost_fraction = 0.05`, $R_{29}$ apagada y `enable_compact_dna=True` una endospora con 12 codones atraviesa un tick
- **THEN** su energía baja exactamente `0.0005` (con tolerancia `1e-9`).

### Requirement: Endospora fuera del Alcance de SHARE y ATTACK
Un `SHARE` ($R_{36}$) o un `ATTACK` ($R_{37}$) cuyo objetivo está en endospora al ejecutarse SHALL NOT cambiar la energía de nadie; el ataque cuenta igual como intento para su costo.

#### Scenario: Ataque a una endospora
- **WHEN** con $R_{37}$ activa un agente con energía 1.5 ataca a una endospora con energía 0.2
- **THEN** las energías no cambian en la Fase 4 y el atacante paga `attack_cost` en el metabolismo del tick.

### Requirement: Costo de los Ataques en el Metabolismo (R37)
Con $R_{37}$ activa, al cobrar el metabolismo, el costo de cada agente SHALL sumar `attack_cost` por cada intento de ataque registrado en `frame.attacks` en el tick, haya tenido éxito o no.

#### Scenario: Ataque fallido con costo
- **WHEN** con `attack_cost = 0.01`, `metabolic_base_cost = 0.01`, `memory_capacity_cost = 0.0`, `sensory_radius_cost = 0.0` y `dna_codon_cost = 0.0` un agente sin mensajes ejecuta un `ATTACK` que fracasa
- **THEN** su energía baja `0.02` en el metabolismo del tick (con tolerancia `1e-9`).

### Requirement: Recombinación en la Reproducción Individual (R38)
Con `enable_compact_dna`, `enable_evolution` y `enable_recombination` activas, en la reproducción de $R_{12}$, un progenitor con `recombination_propensity` expresada $\ge 0.5$ SHALL buscar pareja entre las hojas vivas al empezar el paso de reproducción, distintas de él, ordenadas por `agent_id`, no endosporas, con ADN, a distancia $\le 1$ y con `recombination_propensity >= 0.5`; sin candidatas es asexual. La pareja SHALL NOT ceder energía.

#### Scenario: Pareja sin costo energético
- **WHEN** el progenitor 4 y el agente 6, a distancia 1 y ambos con `recombination_propensity = 0.7`, están vivos y el agente 4 se reproduce con $R_{38}$ activa
- **THEN** el agente 6 es candidato, la energía del agente 6 no cambia por la reproducción y la partición de energía del agente 4 es la de $R_{12}$.

#### Scenario: Recién nacidos fuera de las candidatas
- **WHEN** el único agente a distancia 1 del progenitor nació antes, en el mismo paso de reproducción, con `recombination_propensity = 0.9`
- **THEN** no es candidato y la reproducción es asexual.

#### Scenario: Propensión insuficiente
- **WHEN** el progenitor expresa `recombination_propensity = 0.4`
- **THEN** no busca pareja y la reproducción es asexual.

### Requirement: Sin Recombinación en la Reproducción Holónica
La reproducción holónica ($R_{17}$) SHALL NOT recombinar: cada hoja hija deriva su ADN sólo del de su hoja progenitora o, en la reproducción neutral con ADN, sólo del de su donante.

#### Scenario: Réplica sin cruce
- **WHEN** con $R_{38}$ y $R_{17}$ activas y todas las hojas con `recombination_propensity = 1.0` se reproduce un holón
- **THEN** ninguna hoja hija recombina y `evo_rng` no hace extracciones de recombinación en esa reproducción.

### Requirement: Reproducción Holónica Neutral con ADN
Con `reproduction_mode="neutral"` y `enable_compact_dna=True`, la reproducción holónica ($R_{17}$) SHALL sortear con `donor_rng`, para cada hoja progenitora y en el orden de `leaf_agents`, un donante entre los mismos donantes que la reproducción individual, y la hoja hija SHALL recibir el ADN de ese donante, mutado después; sin ADN, $R_{17}$ SHALL conservar la herencia de la Fase II sin extraer de `donor_rng` (design D56 y precisión 41).

#### Scenario: Un donante por hoja
- **WHEN** con ADN, `reproduction_mode="neutral"`, `mutation_rate = 0` y `discrete_mutation_prob = 0` se reproduce un holón cuyas `leaf_agents` son 2, 5 y 7, y `donor_rng` sortea en ese orden a los agentes 9, 3 y 9
- **THEN** las hojas hijas de 2, 5 y 7 tienen el ADN de los agentes 9, 3 y 9, y conservan el `parent_id`, la topología, el rol y la partición de energía de $R_{17}$.

#### Scenario: Orden de los sorteos del tick
- **WHEN** con ADN y `reproduction_mode="neutral"` en un tick se reproducen un holón de 3 hojas y después 2 agentes individuales
- **THEN** `donor_rng` hace 5 extracciones: las 3 primeras para las hojas del holón, en el orden de `leaf_agents`, y las 2 siguientes para los agentes individuales, en orden de `agent_id`.

#### Scenario: Sin ADN, como en la Fase II
- **WHEN** con `enable_compact_dna=False` y `reproduction_mode="neutral"` se reproduce un holón
- **THEN** cada hoja hija deriva su genoma del de su hoja progenitora, `donor_rng` no extrae para el holón y los historiales son idénticos a los de la Fase II.

## MODIFIED Requirements

### Requirement: Metabolismo Energético con Penalización Cuadrática de Capacidad y Radios
Cuando `enable_evolution=True`, cada `MicroAgent` SHALL iniciar con energía `initial_energy` ($E_0$), descontar por tick el costo basal $c_{\text{fijo}} + c_{\text{mem}} C_{\max, i}^2 + c_{\text{sens}}(r_{\text{perc}, i}^2 + r_{\text{com}, i}^2)$ más $c_{\text{move}}$ (si se movió) y $c_{\text{msg}} m_i$, y sumar $\eta_E \cdot v$ al consumir un recurso de valor $v$; suma ADN ($R_{24}$), senescencia ($R_{29}$) y ataques ($R_{37}$), y una endospora paga su propio costo ($R_{28}$).

#### Scenario: Penalización cuadrática del cerebro individual
- **WHEN** dos agentes en reposo y sin emitir mensajes tienen capacidades $C_{\max} = 3$ y $C_{\max} = 6$ respectivamente, con `metabolic_base_cost = 0.02`, `memory_capacity_cost = 0.005` y `sensory_radius_cost = 0.0`
- **THEN** tras un tick el primero pierde `0.02 + 0.005 * 9 = 0.065` de energía y el segundo pierde `0.02 + 0.005 * 36 = 0.200` de energía (con tolerancia `1e-9`).

#### Scenario: Ganancia y pérdida por interacción con recursos
- **WHEN** un agente con energía `1.0` consume un recurso benéfico de valor `+1.0` con `energy_gain_scale = 0.5`
- **THEN** antes del descuento basal su energía aumenta a `1.5`, y si consume uno dañino de valor `-1.0` disminuye a `0.5`.

#### Scenario: Costo basal con ADN y senescencia
- **WHEN** con `metabolic_base_cost = 0.01`, `memory_capacity_cost = 0.005`, `sensory_radius_cost = 0.0`, `dna_codon_cost = 0.0002` y `senescence_cost_rate = 1e-5`, un agente en reposo y sin mensajes, con 9 codones, `memory_capacity = 3` expresada y `age - lifespan = 10`, paga el metabolismo con $R_{24}$ y $R_{29}$ activas
- **THEN** pierde `0.01 + 0.045 + 0.0018 + 0.001 = 0.0578` de energía (con tolerancia `1e-9`).

### Requirement: Muerte por Agotamiento Energético
En la Fase 5 de cada tick con `enable_evolution=True`, todo `MicroAgent` cuya energía resultante cumpla $E_i(t) \le 0$, por el metabolismo o por la depredación de $R_{37}$ en la Fase 4, SHALL ser eliminado del motor, del entorno espacial y podado de cualquier árbol holónico antes de la fase de reproducción, incrementando el contador `deaths_this_tick`; con $R_{35}$ activa deja antes un cadáver.

#### Scenario: Eliminación por inanición
- **WHEN** la energía de un agente cae a `0.0` o a un valor negativo al finalizar el cobro metabólico de la Fase 5
- **THEN** el agente deja de figurar en `engine.agents` y en `env.get_active_agent_ids()` en ese mismo tick.

#### Scenario: Muerte por depredación
- **WHEN** con $R_{37}$ activa un agente queda con energía `0.0` por un ataque exitoso en la Fase 4 del tick 12
- **THEN** muere en el paso de muerte de la Fase 5 del tick 12 y cuenta en `deaths_this_tick`.

### Requirement: Reproducción Diferencial con Partición Conservativa y Límite de Un Evento por Tick (R12)
En la Fase 5 con `enable_evolution=True`, todo `MicroAgent` sobreviviente no reproducido aún en ese tick y que no esté en endospora ($R_{28}$) cuya energía cumpla $E_i(t) \ge E_{\text{reprod}}$ SHALL engendrar a lo sumo un hijo (en orden ascendente de `agent_id`) si `len(agents) < max_population`, reteniendo $(1 - \kappa_{\text{part}}) E_i(t)$ y transfiriendo $\kappa_{\text{part}} E_i(t)$ al hijo.

#### Scenario: Partición exacta de energía y linaje
- **WHEN** el agente 4 con generación `g = 2` alcanza energía `2.4` con `reproduction_threshold = 2.0`, `offspring_energy_share = 0.5` y hay cupo bajo `max_population`
- **THEN** nace un nuevo agente con `parent_id == 4`, `generation == 3`, `energy == 1.2`, y el agente 4 queda con `energy == 1.2` (con tolerancia `1e-9`), conservando la suma total `2.4`.

#### Scenario: Respeto estricto de la capacidad de carga
- **WHEN** la población activa ya tiene `len(engine.agents) == max_population` y un agente supera `reproduction_threshold`
- **THEN** no nace ningún descendiente y el agente conserva su energía íntegra.

#### Scenario: Una endospora no se reproduce
- **WHEN** con $R_{28}$ activa una endospora llega a la reproducción con energía `2.4`, `reproduction_threshold = 2.0` y cupo bajo `max_population`
- **THEN** no nace ningún descendiente suyo y su energía no se parte.

### Requirement: Reproducción Neutral como Ablación de R12 y Control de Deriva
Con `reproduction_mode="neutral"`, los mismos agentes que con `"energy"` SHALL reproducirse con igual partición de energía, ubicación, linaje y herencia cultural, pero el genoma (o ADN) de cada hijo individual SHALL mutarse a partir del de un donante sorteado con `donor_rng` (`spawn_key=(4,)`) entre los vivos no endosporas al empezar la reproducción, primero del cruce con $R_{38}$. Una hoja hija de $R_{17}$ recibe con ADN el de su donante y sin ADN el de su progenitora (precisión 41).

#### Scenario: Misma demografía, genoma independiente del éxito
- **WHEN** se corren dos motores con la misma semilla y `reproduction_mode` `"energy"` y `"neutral"`, sin reproducción holónica, con `mutation_rate = 0`, `discrete_mutation_prob = 0` y genomas fundadores distintos
- **THEN** en el primer tick con nacimientos las dos corridas tienen los mismos `parent_id`, energías y posiciones de los hijos, y en `"neutral"` el genoma de cada hijo es el de su donante sorteado, no necesariamente el de su progenitor.

#### Scenario: Endosporas fuera del sorteo de donantes
- **WHEN** con $R_{28}$ activa y `reproduction_mode="neutral"` los agentes vivos al empezar la reproducción son 1, 2 y 3, y el agente 2 está en endospora
- **THEN** el donante se sortea con `donor_rng` sobre la lista ordenada `[1, 3]`.

### Requirement: Herencia Genética con Mutación Acotada (R13)
Al reproducirse un agente sin ADN con `mutation_rate > 0` o `discrete_mutation_prob > 0` (escalados por $R_{30}$), el `AgentGenome` del hijo SHALL derivarse del parental aplicando ruido normal $\mathcal{N}(0, \sigma_{\text{mut}}^2)$ a los rasgos continuos y saltos en $\{-1, 0, +1\}$ a los discretos dentro de sus cotas; si ambos son `0.0`, SHALL clonarse sin extraer del RNG. Con ADN, el hijo SHALL derivar su ADN (recombinado si hubo $R_{38}$) con `mutate_dna`, bajo la puerta de $R_{13}$.

#### Scenario: Clonación exacta bajo ablación de mutación
- **WHEN** un agente sin ADN se reproduce con `mutation_rate = 0.0` y `discrete_mutation_prob = 0.0`
- **THEN** `child.genome == parent.genome`.

#### Scenario: Mutación acotada dentro de invariantes de dominio
- **WHEN** se muta repetidamente un `AgentGenome` durante 500 eventos reproductivos con `mutation_rate = 0.2` y `discrete_mutation_prob = 0.5`
- **THEN** todos los coeficientes continuos permanecen en `[0.0, 1.0]` (`alpha_learning` en `[0.01, 1.0]`), `memory_capacity` permanece en `[1, max_genome_memory_capacity]` y además `< num_world_patterns` cuando `enforce_memory_constraint=True`, y los radios permanecen en `[1, (min(grid_width, grid_height) - 1) // 2]` (o con el valor parental si ese intervalo es vacío), de modo que `SimulationConfig` acepta el genoma del hijo.

#### Scenario: ADN congelado bajo ablación de mutación
- **WHEN** con `enable_compact_dna=True`, `mutation_rate = 0.0` y `discrete_mutation_prob = 0.0` un agente se reproduce
- **THEN** `child.dna == parent.dna` y la mutación no consume extracciones de `evo_rng`.
