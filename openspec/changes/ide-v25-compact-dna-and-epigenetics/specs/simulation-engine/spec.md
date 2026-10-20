# Spec Delta: Simulation Engine

## ADDED Requirements

### Requirement: Fase 0 de Expresión del Fenotipo
Con `enable_compact_dna=True`, `step()` SHALL ejecutar `_express_phenotypes` al empezar, antes de la permutación y del alcance local: para cada `aid` en `sorted(self.agents)` arma `EpigeneticContext` con el `holon_level` de `self.root_nodes[self.agent_to_root[aid]]` (0 si la hoja es su propia raíz), `agent.epigenetic_role` y `agent.energy / reproduction_threshold`, invoca `agent.express(context, tick)` y, si devuelve `True`, `env.set_agent_radii(aid, r_perc, r_com)`.

#### Scenario: Contexto de una hoja en un holón de nivel 2
- **WHEN** con `reproduction_threshold = 2.2` la hoja 4, con rol `NERVE` y energía `1.1`, pertenece a una raíz de nivel 2 al empezar `step()`
- **THEN** la Fase 0 invoca `express(EpigeneticContext(2, EpigeneticRole.NERVE, 0.5), tick)` sobre la hoja 4.

#### Scenario: Radios actualizados sólo si cambian
- **WHEN** en la Fase 0 un agente cambia su capacidad expresada pero no sus radios, y otro cambia su `perception_radius`
- **THEN** `env.set_agent_radii` se invoca sólo para el segundo, con sus radios expresados.

### Requirement: Fase 0 sin Generadores ni Efectos de Orden
`_express_phenotypes` SHALL NOT consumir ningún generador, y cada agente SHALL expresarse sobre el estado de fin del tick anterior, de modo que el resultado no depende del orden de recorrido; con `enable_compact_dna=False` la Fase 0 no corre.

#### Scenario: Generadores intactos en la Fase 0
- **WHEN** se ejecuta `_express_phenotypes` con `enable_compact_dna=True`
- **THEN** el estado de `self.rng`, `evo_rng`, `donor_rng` y `hgt_rng` es el mismo antes y después.

### Requirement: Generador hgt_rng para la Conjugación
El motor SHALL declarar `self.hgt_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(config.seed, spawn_key=(5,))))`, cuyo único uso es el sorteo de la conjugación de plásmidos, consumido sólo con `enable_compact_dna=True` y `enable_plasmid_hgt=True`, de modo que activar $R_{26}$ no desplaza la secuencia de `evo_rng`.

#### Scenario: hgt_rng sin consumo con R26 apagada
- **WHEN** se ejecutan 50 ticks con `enable_compact_dna=True` y `enable_plasmid_hgt=False`
- **THEN** el estado de `hgt_rng` es igual al de un generador recién construido con `SeedSequence(config.seed, spawn_key=(5,))`.

### Requirement: Nacimiento con ADN Mutado por evo_rng
Con `enable_compact_dna=True`, la mutación del ADN del hijo SHALL usar `evo_rng`, el hijo SHALL expresarse en el acto y `spawn_agent_near` SHALL recibir los radios de ese fenotipo de nacimiento; desde el tick siguiente la Fase 0 lo expresa con su contexto real. La secuencia de `evo_rng` difiere de la Fase II, porque el operador es otro.

#### Scenario: Radios de nacimiento
- **WHEN** nace un hijo cuyo fenotipo de nacimiento tiene `perception_radius = 3` y `comm_radius = 1`
- **THEN** `spawn_agent_near` recibe `perception_radius=3` y `comm_radius=1`, y la mutación de su ADN consumió `evo_rng` y no `self.rng`.

### Requirement: Orden de la Fase 5 con la Fase II-B
La Fase 5 SHALL ejecutar en orden: `decay_memory`; coordinación con el sello y el descuento de $R_{31}$, `SPLIT` y `BOND`; metabolismo con ADN, senescencia y endospora; muerte, registro del estrés y entrada en endospora; reproducción con SOS, ADN e impronta; conjugación ($R_{26}$) y ensayo CRISPR ($R_{27}$); $R_{18}$ y roles ($R_{25}$); `env.step_dynamics`; métricas.

#### Scenario: Reducción al orden de la Fase II
- **WHEN** se ejecuta un tick con todas las banderas de la Fase II-B apagadas
- **THEN** la Fase 5 se reduce exactamente al orden de la Fase II: `decay_memory`, coordinación, `SPLIT` y `BOND`, metabolismo, muerte, reproducción, $R_{18}$, `env.step_dynamics` y métricas.

#### Scenario: Conjugación posterior a la reproducción
- **WHEN** con $R_{26}$ activa un agente nace en la Fase 5 del tick 20
- **THEN** el recién nacido figura entre los agentes vivos al empezar la conjugación del tick 20.

### Requirement: Donantes de la Conjugación (R26)
Con `enable_compact_dna` y `enable_plasmid_hgt` activas, `_conjugate` SHALL fijar al empezar el paso como donantes, en orden de `agent_id`, las hojas que no son endospora, tienen `plasmids` no vacío y tienen `energy >= hgt_energy_ratio * reproduction_threshold`.

#### Scenario: Donantes elegibles
- **WHEN** con `hgt_energy_ratio = 0.85` y `reproduction_threshold = 2.2` el agente 1 tiene plásmidos y `energy = 1.87`, el agente 2 tiene plásmidos y `energy = 1.86`, y el agente 3 tiene plásmidos y es endospora
- **THEN** el único donante es el agente 1.

### Requirement: Sorteo de la Conjugación con hgt_rng
Para cada donante en orden, `_conjugate` SHALL extraer `u = float(hgt_rng.random())` y, si `u < hgt_rate`, tomar como candidatos `sorted(b vivo al empezar el paso, b != donante, no endospora, env.get_agent_distance(donante, b) <= 1)` y, si hay, extraer `receptor = candidatos[int(hgt_rng.integers(len(candidatos)))]` y `codón = plasmids_al_empezar[int(hgt_rng.integers(len(plasmids)))]`, registrando `(receptor, codón)`.

#### Scenario: Secuencia exacta de extracciones
- **WHEN** con `hgt_rate = 1.0` un único donante con 3 plásmidos tiene a los agentes 7 y 2 a distancia 1, y un generador gemelo sembrado con `spawn_key=(5,)` extrae `random()`, `integers(2)` e `integers(3)`
- **THEN** el par registrado es `([2, 7][i], plásmidos[j])` con `i` y `j` del gemelo, y ambos generadores terminan en el mismo estado.

#### Scenario: Donante sin candidatos
- **WHEN** con `hgt_rate = 1.0` un donante no tiene agentes a distancia menor o igual que 1
- **THEN** sólo se extrae su `u` y no se registra transferencia.

### Requirement: Aplicación de las Transferencias de Plásmidos
Después de sortear todas las transferencias, el motor SHALL aplicarlas con `receive_plasmid` en el orden de `hgt_rng.permutation(len(transferencias))` sobre la lista registrada si hay dos o más, guardar con `set_dna` el ADN que cambió y, con $R_{27}$ activa, abrir en el receptor el ensayo `trials[codón] = (tick, energía actual)`; un `None` de `receive_plasmid` bloquea la transferencia y cuenta como rechazo.

#### Scenario: Transferencia aplicada con ensayo
- **WHEN** con $R_{26}$ y $R_{27}$ activas el agente 2, con `energy = 1.4`, recibe en el tick 30 un codón que no tiene
- **THEN** el codón queda al final de sus `plasmids` y se abre el ensayo `trials[codón] = (30, 1.4)`.

#### Scenario: Conflicto de llegada resuelto por sorteo
- **WHEN** con `max_plasmids = 1` dos donantes registran transferencias de codones distintos al mismo receptor sin plásmidos
- **THEN** el motor extrae `hgt_rng.permutation(2)` después de sortear todas las transferencias, las aplica en ese orden, y el receptor queda con el codón de la transferencia aplicada en último lugar.

#### Scenario: Transferencia bloqueada
- **WHEN** con $R_{27}$ activa el codón transferido está en `crispr_memory` del receptor
- **THEN** el ADN del receptor no cambia, no se abre ensayo y se cuenta un rechazo CRISPR del tick.

### Requirement: Ensayo CRISPR (R27)
Con `enable_crispr_immunity` activa, después de la conjugación, para cada agente en orden de `agent_id` y cada ensayo en orden de codón, un ensayo vencido (`tick - t0 >= crispr_eval_ticks`) SHALL purgar el codón con `purge_plasmid` si sigue en `plasmids` y `energy - e0 + cedida < -crispr_toxicity_threshold` (`cedida`: energía dada a hijos en la ventana), y SHALL cerrarse siempre; un plásmido perdido por FIFO se cierra al vencer, sin purga.

#### Scenario: Plásmido tóxico purgado
- **WHEN** con `crispr_eval_ticks = 20` y `crispr_toxicity_threshold = 0.20` un ensayo abierto en el tick 30 con `e0 = 1.4` llega al tick 50 con `energy = 1.1` y el codón en `plasmids`
- **THEN** el codón sale de `plasmids`, entra en `crispr_memory`, el ensayo se cierra y se cuenta una purga.

#### Scenario: Plásmido inocuo
- **WHEN** el mismo ensayo llega al tick 50 con `energy = 1.3`
- **THEN** el codón sigue en `plasmids` y el ensayo se cierra sin purga.

#### Scenario: La reproducción no cuenta como toxicidad
- **WHEN** el mismo ensayo llega al tick 50 con `energy = 1.1` después de que el agente cediera `1.2` de energía a un hijo dentro de la ventana
- **THEN** el balance es `1.1 - 1.4 + 1.2 = 0.9`, el codón sigue en `plasmids` y el ensayo se cierra sin purga.

### Requirement: Plásmidos sin Contenido Epistémico
La conjugación SHALL transportar sólo codones y SHALL NOT pasar por `assimilate_testimony` ni por el control nulo de contenido; el control nulo de E4 no altera los plásmidos.

#### Scenario: Memoria intacta tras la conjugación
- **WHEN** un agente recibe un plásmido en la Fase 5 con `comm_content_null=True`
- **THEN** su memoria epistémica no cambia por la transferencia y el codón recibido es el del donante.

### Requirement: Compatibilidad Bit a Bit con las Banderas por Defecto
Con todas las banderas de la Fase II-B en `False`, el motor, el agente, la memoria, la grilla, `TickMetrics`, `EvolutionaryTickMetrics` y todos los generadores SHALL comportarse exactamente como en la Fase II: ninguna rama nueva consume un generador ni cambia un valor o un orden de iteración.

#### Scenario: Hashes dorados y protocolos de la Fase II
- **WHEN** se ejecutan `tests/test_performance_equivalence.py` y los protocolos `002a` y `003a` con las banderas por defecto
- **THEN** los hashes SHA-256 dorados no cambian y los historiales `history` y `evolutionary_history` son idénticos a los de la Fase II.

### Requirement: Reproducibilidad del ADN entre Procesos
Con `enable_compact_dna=True` y las reglas de la Fase II-B activas, los historiales SHALL ser idénticos entre procesos con distinto `PYTHONHASHSEED`.

#### Scenario: Igualdad entre procesos
- **WHEN** se ejecuta la misma configuración de `003c` con la misma semilla en dos procesos con `PYTHONHASHSEED=0` y `PYTHONHASHSEED=123`
- **THEN** `history`, `evolutionary_history` y `genetic_history` son idénticos.

## MODIFIED Requirements

### Requirement: Orden de Fases del Tick
`step()` SHALL ejecutar el tick `next_tick` en este orden y luego incrementarlo: (0) sólo con `enable_compact_dna=True`, la expresión de "Fase 0 de Expresión del Fenotipo"; (1) observación y emisión; (2) intercambio social en dos pasadas; (3) decisión de todos los agentes; (4) ejecución y aprendizaje directo; (5) decaimiento, `step_dynamics` y registro de `TickMetrics`. Con $R_{28}$, las endosporas siguen en (1) a (3) lo que fijan "Germinación de la Endospora" y "Física de la Endospora".

#### Scenario: Decisiones sobre la misma instantánea
- **WHEN** dos agentes de la misma celda observan el mismo recurso benéfico
- **THEN** ambos deciden a partir de la observación de la fase 1, aunque el primero lo consuma en la fase 4.

#### Scenario: Sin Fase 0 con las banderas por defecto
- **WHEN** se ejecuta un tick con `enable_compact_dna=False`
- **THEN** no se invoca `_express_phenotypes` y el tick empieza por la observación de la fase 1, como en la Fase II.

#### Scenario: Fase 0 antes de la observación
- **WHEN** con `enable_compact_dna=True` un agente cambia su `perception_radius` expresado de 2 a 3 en la Fase 0 del tick
- **THEN** su observación de la fase 1 de ese mismo tick se calcula con `perception_radius = 3`.

### Requirement: Intercambio Social en Dos Pasadas
Con `comm_enabled`, el motor SHALL entregar cada mensaje emitido a los `neighbor_ids` de la observación de la fase 1 del emisor (o sólo a `recipient_id` si figura entre ellos), recolectar los `QUERY_RESPONSE` de la primera pasada y entregarlos en una segunda pasada antes de la fase de decisión; con $R_{28}$ activa, una endospora no emite ni recibe en ninguna pasada, según "Física de la Endospora".

#### Scenario: Consulta resuelta en el mismo tick
- **WHEN** el agente 1 consulta por $\rho_5$ y su vecino 2 lo conoce como dañino con `c = 0.85`
- **THEN** en la fase de decisión del mismo tick el agente 1 ya tiene una creencia efectiva sobre $\rho_5$.

#### Scenario: Ruteo con los vecinos de la observación
- **WHEN** un entorno de prueba devuelve en cada observación `neighbor_ids == (0,)`, salvo para el agente 0, que recibe `(1,)`, distintos de los vecinos reales
- **THEN** en la primera pasada sólo los agentes 0 y 1 reciben mensajes, y el agente 0 recibe los de los demás emisores.

#### Scenario: Endospora excluida del ruteo
- **WHEN** con $R_{28}$ activa el agente 3, endospora que no germina en el tick, figura en los `neighbor_ids` del agente 1, que emite un `BROADCAST_BELIEF`
- **THEN** el agente 3 no recibe ese mensaje en ninguna de las dos pasadas, y los demás vecinos del agente 1 sí lo reciben.

### Requirement: Ciclo Metabólico, Reproductivo y Holónico en Fase 5 y Poda en Perturbaciones
En la Fase 5 de `step()`, el motor SHALL ejecutar en orden determinista: (a) coordinación ($R_{23}$), `SPLIT` ($R_{16}$) y `BOND` ($R_{15}$), (b) metabolismo, muerte (poda con `prune_dead_leaves`) y reproducción ($R_{17}$, $R_{12}$), (c) $R_{18}$ sobre el bosque resultante, todo entre `decay_memory` y `env.step_dynamics`; y (d) tras `step_dynamics`, registro en `evolutionary_history`. La Fase II-B intercala sus pasos según "Orden de la Fase 5 con la Fase II-B".

#### Scenario: Sucesión generacional y formación de holones en una corrida evolutiva
- **WHEN** se ejecuta `SimulationEngine` con `enable_evolution=True`, `enable_cultural_inheritance=True` y `enable_holonic_hierarchy=True` durante 100 ticks en un entorno con recursos abundantes
- **THEN** `len(engine.evolutionary_history) == 100`, la población se mantiene `<= max_population` y se registran nacimientos (`births_this_tick > 0`) con `max_generation >= 1`.

#### Scenario: Pasos de la Fase II-B intercalados
- **WHEN** se ejecuta un tick con `enable_compact_dna`, `enable_plasmid_hgt`, `enable_epigenetic_roles` y `enable_holonic_hierarchy` activas
- **THEN** la conjugación ocurre después de la reproducción y antes de $R_{18}$, y la asignación de roles después de $R_{18}$ y antes de `env.step_dynamics`.
