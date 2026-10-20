# Spec Delta: Simulation Engine

## ADDED Requirements

### Requirement: Sistemas, Observadores y TickFrame
`src/ide/simulation/pipeline.py` SHALL definir los protocolos `EngineSystem` (`name` y `run(engine, frame)`) y `TickObserver` (`on_decisions(engine, frame)` y `on_tick_end(engine, frame)`), el `@dataclass` mutable `TickFrame` con los campos de design D44.1 (entre ellos `order`, `observations`, `social`, `actions`, `attacks` y `events`), y `build_systems(config) -> tuple[EngineSystem, ...]` con el orden de "Orden de Fases del Tick".

#### Scenario: Mecanismo apagado fuera de la lista
- **WHEN** se invoca `build_systems` con `SimulationConfig()` y con una configuración que activa `enable_compact_dna` y `enable_plasmid_hgt`
- **THEN** la segunda lista contiene un sistema de conjugación que la primera no contiene, y en ambas los sistemas comunes aparecen en el mismo orden relativo.

### Requirement: Ejecución del Pipeline en step()
`SimulationEngine.step()` SHALL crear un `TickFrame` para el tick `next_tick`, ejecutar en orden los sistemas de `build_systems(config)`, invocar `on_decisions` de cada observador inmediatamente después del sistema de decisión y `on_tick_end` al final del tick, e incrementar `next_tick`.

#### Scenario: Momento de los observadores
- **WHEN** se registra un observador de prueba y se ejecuta un tick
- **THEN** `on_decisions` se invoca una vez, con `frame.actions` completo y antes de que cambie la posición de ningún agente, y `on_tick_end` se invoca una vez, después de `env.step_dynamics`.

### Requirement: Telemetría Producida por Observadores
`TickMetricsObserver` SHALL producir `TickMetrics` (M1–M7) y juzgar M2 en `on_decisions`, consultando `get_reachable_true_values` antes de ejecutar las acciones; `EvolutionaryMetricsObserver`, `GeneticMetricsObserver` y `EcologyMetricsObserver` SHALL producir `evolutionary_history`, `genetic_history` y `ecology_history`. Ningún sistema calcula métricas.

#### Scenario: M2 sobre la verdad previa a la ejecución
- **WHEN** los agentes 3 y 8 de la misma celda deciden `INTERACT` sobre el mismo recurso benéfico y 8 aparece antes en la permutación
- **THEN** M2 cuenta una oportunidad de decisión acertada para cada uno, aunque el agente 3 reciba `ActionResult(INTERACT, None, None)` en la Fase 4.

### Requirement: API Pública del Motor sin Cambios
El refactor por sistemas SHALL conservar la firma y la semántica de `history`, `evolutionary_history`, `agents`, `root_nodes`, `step()`, `run()`, `snapshot()` y las perturbaciones (`inject_false_belief`, `ablate_population` y `ablate_discoverers`).

#### Scenario: Tests de las Fases I y II sin modificar
- **WHEN** se ejecutan los tests de las Fases I y II que usan esa API, sin modificarlos
- **THEN** todos pasan.

### Requirement: Accesos del Motor a la Memoria del Agente
`pipeline.py` y `engine.py` SHALL NOT acceder a `agent.memory` salvo en los puntos que lo hacían antes del refactor: $R_{18}$, $R_{19}$, el superávit de conocimiento y las perturbaciones. Un test AST SHALL fijar la lista de funciones que acceden a `.memory`, para que no crezca.

#### Scenario: Auditoría AST de accesos a la memoria
- **WHEN** el test recorre el AST de `pipeline.py` y `engine.py` buscando atributos `memory`
- **THEN** el conjunto de funciones que los usan es exactamente la lista declarada en el test.

### Requirement: Aceptación del Refactor por Sistemas
El refactor por sistemas SHALL NOT cambiar ningún comportamiento: los hashes SHA-256 dorados, las huellas de la Fase II, los historiales de `002a` y `003a` con y sin ADN y la secuencia de consumo de cada generador SHALL ser idénticos a los de antes del refactor, y `python -m ide.experiments.benchmark` SHALL NOT empeorar más de un 10 % en ticks por segundo.

#### Scenario: Historiales idénticos tras el refactor
- **WHEN** se ejecutan `tests/test_performance_equivalence.py` y las huellas de `002a` y `003a` con `enable_compact_dna` en `False` y en `True`
- **THEN** los hashes y los historiales coinciden bit a bit con los registrados antes del refactor.

### Requirement: Política de los Fundadores
El motor SHALL construir cada fundador con `GeneticPolicy()` si `enable_compact_dna` y `enable_genetic_policy` están activas, y con `HandwrittenPolicy()` en otro caso; cada descendiente hereda la política de su progenitor.

#### Scenario: Política genética inerte sin ADN
- **WHEN** se construye el motor con `enable_genetic_policy=True` y `enable_compact_dna=False`
- **THEN** todos los fundadores usan `HandwrittenPolicy`, sin lanzar error.

### Requirement: Percepción Social Construida por el Motor
Con la política genética activa, el motor SHALL construir en la Fase 1, después de la germinación, un `SocialPerception` por agente con `env.get_visible_agents` y la instantánea de energías al empezar el tick: "activo" excluye a las endosporas; `flee_move` es el del agente activo más cercano con energía estrictamente mayor, desempatando por `(distance, agent_id)`. Sin la política genética SHALL pasar `None` a la decisión.

#### Scenario: Vecinos adyacentes y huida
- **WHEN** el agente 1, con energía 1.0, tiene a distancia 1 a los agentes 4 (energía 0.6) y 2 (energía 1.5), y a distancia 2 al agente 7 (energía 2.0)
- **THEN** su percepción social tiene `adjacent == (2, 4)`, `weakest_adjacent == 4`, `weaker_adjacent == True` y el `flee_move` de la entrada del agente 2.

#### Scenario: Endospora no es un agente activo
- **WHEN** el único agente a distancia 1 del agente 1 es una endospora que no germina en el tick
- **THEN** la percepción social del agente 1 tiene `adjacent == ()` y `weakest_adjacent is None`.

### Requirement: Ejecución de SHARE, ATTACK y SPORULATE en la Fase 4
El motor SHALL ejecutar `SHARE`, `ATTACK` y `SPORULATE` en la Fase 4, en el orden de la permutación del tick junto con las demás acciones, sobre las energías y estados vigentes al ejecutar cada una; SHALL contar cada intento de ataque en `frame.attacks` y registrar los eventos en `frame.events`, con claves iguales a los campos contadores de `EcologyTickMetrics`. `SPORULATE` pone al agente en endospora al ejecutarse.

#### Scenario: Conflicto resuelto por la permutación
- **WHEN** el agente 5 decide `ATTACK` sobre el agente 2 y el agente 2 decide `SPORULATE`, y 2 aparece antes que 5 en la permutación del tick
- **THEN** el agente 2 queda en endospora, el ataque falla, `frame.attacks[5] == 1`, `frame.events` tiene `attacks == 1`, `successful_attacks == 0` y `sporulations == 1`, y la `EcologyTickMetrics` del tick registra los mismos valores.

### Requirement: Transferencia de Energía (R36)
Con $R_{36}$ activa, un `SHARE` sobre `target` SHALL, si el donante tiene energía $> 0$ y el objetivo sigue en `engine.agents` ("sigue vivo": nadie muere en la Fase 4) y no es endospora, restar `amount = share_fraction * energía_del_donante` al donante y sumar `share_efficiency * amount` al receptor; si no, SHALL NOT tener efecto.

#### Scenario: Cesión con pérdida
- **WHEN** con `share_fraction = 0.25` y `share_efficiency = 0.9` el agente 1, con energía 2.0, ejecuta `SHARE` sobre el agente 3, con energía 0.5
- **THEN** el agente 1 queda con 1.5 y el agente 3 con 0.95 (con tolerancia `1e-9`).

#### Scenario: Objetivo en endospora
- **WHEN** el objetivo de un `SHARE` está en endospora al ejecutarse
- **THEN** ninguna energía cambia.

#### Scenario: Donante sin energía
- **WHEN** un agente que decidió `SHARE` con energía 0.3 consume antes, en la misma Fase 4, un recurso dañino que lo deja con energía -0.2, y luego se ejecuta su `SHARE`
- **THEN** ninguna energía cambia por el `SHARE`.

### Requirement: Depredación (R37)
Con $R_{37}$ activa, un `ATTACK` sobre `target` SHALL tener éxito sólo si el objetivo sigue en `engine.agents` (aunque su energía sea $\le 0$), no es endospora y la energía del atacante es estrictamente mayor que la del objetivo al ejecutarse; con éxito, `stolen = min(attack_power, max(0, energía_del_objetivo))`, el objetivo pierde `stolen` y el atacante gana `predation_efficiency * stolen`.

#### Scenario: Robo acotado
- **WHEN** con `attack_power = 0.5` y `predation_efficiency = 0.6` el agente 4, con energía 1.2, ataca al agente 6, con energía 0.3
- **THEN** el agente 6 queda con 0.0 y el agente 4 con 1.38 (con tolerancia `1e-9`), y el agente 6 muere en el paso de muerte de esa Fase 5.

#### Scenario: Objetivo igual o más fuerte
- **WHEN** el atacante y el objetivo tienen la misma energía al ejecutarse el ataque
- **THEN** el ataque fracasa, ninguna energía cambia en la Fase 4 y el intento se cuenta en `frame.attacks`.

#### Scenario: Objetivo ya sin energía
- **WHEN** el agente 6 quedó con energía 0.0 por un ataque anterior del mismo tick y el agente 8, con energía 0.5, lo ataca
- **THEN** el ataque tiene éxito con `stolen = 0`, ninguna energía cambia y la `EcologyTickMetrics` del tick cuenta los dos ataques exitosos.

### Requirement: M2 Juzga Decisiones con Cualquier Conducta
M2 SHALL juzgar decisiones, no acciones: un agente con recursos elementales alcanzables, incluidos los cadáveres, SHALL sumar una oportunidad de decisión cualquiera sea la conducta elegida (`FLEE`, `SHARE`, `ATTACK` o `SPORULATE` incluidas), y `judge_decision` la juzga como en la Fase II. Una endospora no decide y no suma oportunidad.

#### Scenario: Ataque con recurso benéfico alcanzable
- **WHEN** un agente con un único recurso elemental alcanzable, benéfico, decide `ATTACK`
- **THEN** suma una oportunidad de decisión en `decision_opportunities` de ese tick y no suma decisión correcta.

#### Scenario: Huida con sólo recursos dañinos
- **WHEN** un agente cuyos recursos alcanzables son todos dañinos decide `FLEE`
- **THEN** suma una oportunidad de decisión y una decisión correcta.

#### Scenario: Cadáver en el oráculo
- **WHEN** el único recurso alcanzable de un agente es un cadáver y el agente decide `INTERACT` sobre él
- **THEN** suma una oportunidad de decisión y una decisión correcta.

### Requirement: Aceptación del Fundador Genético
Con el ADN fundador de `founder_dna(config)`, sin mutación y con `dna_codon_cost = 0.0`, las corridas de `002a` y `003a` con `enable_genetic_policy=True` SHALL producir historiales idénticos a los de `enable_genetic_policy=False`, incluido el consumo de `self.rng` (design D46.5).

#### Scenario: Fundador conductual neutro
- **WHEN** se corren `002a` y `003a` con `enable_compact_dna=True`, `mutation_rate = 0.0`, `discrete_mutation_prob = 0.0`, `dna_codon_cost = 0.0` y `enable_genetic_policy` en `True` y en `False`, con la misma semilla
- **THEN** `history` y `evolutionary_history` son idénticos entre las dos corridas.

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

### Requirement: Sin Generadores Nuevos en la Reformulación
Las reglas $R_{32}$–$R_{38}$ SHALL NOT agregar generadores: la conducta de la Fase 3 extrae de `self.rng`, la ubicación de recursos de $R_{34}$ del generador del entorno y la recombinación de `evo_rng`, cada extracción sólo con su regla activa.

#### Scenario: Generadores del motor con todas las reglas nuevas
- **WHEN** se construye el motor con todas las banderas de design D52 activas
- **THEN** sus generadores son `rng`, `null_rng`, `evo_rng`, `donor_rng` y `hgt_rng`, con las `spawn_key` declaradas en `CLAUDE.md`, y ninguno más.

### Requirement: Nacimiento con ADN Mutado por evo_rng
Con `enable_compact_dna=True`, la mutación del ADN del hijo SHALL usar `evo_rng`, el hijo SHALL expresarse en el acto y `spawn_agent_near` SHALL recibir los radios de ese fenotipo de nacimiento; desde el tick siguiente la Fase 0 lo expresa con su contexto real. La secuencia de `evo_rng` difiere de la Fase II, porque el operador es otro.

#### Scenario: Radios de nacimiento
- **WHEN** nace un hijo cuyo fenotipo de nacimiento tiene `perception_radius = 3` y `comm_radius = 1`
- **THEN** `spawn_agent_near` recibe `perception_radius=3` y `comm_radius=1`, y la mutación de su ADN consumió `evo_rng` y no `self.rng`.

### Requirement: Recombinación al Nacer con evo_rng (R38)
Con $R_{38}$ activa, si un progenitor de $R_{12}$ tiene candidatas a pareja, el sistema de reproducción SHALL extraer de `evo_rng`, en este orden y antes de mutar el ADN del hijo, `pareja = candidatas[int(evo_rng.integers(len(candidatas)))]`, `a = int(evo_rng.integers(1, len(primer_cromosoma) + 1))` y `b = int(evo_rng.integers(0, len(cromosoma_pareja)))`, y mutar `recombine_dna(primero, pareja, a, b, config)`; sin candidatas SHALL NOT extraer.

#### Scenario: Secuencia exacta de extracciones
- **WHEN** un progenitor con cromosoma de 9 codones tiene como candidatas a los agentes 3 y 8, y un generador gemelo sembrado con `spawn_key=(2,)` extrae `integers(2)`, `integers(1, 10)` e `integers(0, n_pareja)`
- **THEN** la pareja, `a` y `b` coinciden con los del gemelo, y la mutación del hijo empieza con `evo_rng` en el estado del gemelo tras esas tres extracciones.

#### Scenario: Sin candidatas
- **WHEN** con $R_{38}$ activa un progenitor con `recombination_propensity >= 0.5` no tiene candidatas
- **THEN** la reproducción es asexual y `evo_rng` no hace extracciones de recombinación.

### Requirement: Recombinación en la Reproducción Neutral
Con $R_{38}$ activa y `reproduction_mode="neutral"`, el primer ADN del cruce SHALL ser el del donante sorteado con `donor_rng`, mientras la búsqueda de pareja y la propensión son las del agente que se reproduce; el orden de extracciones SHALL ser el donante con `donor_rng`, el cruce con `evo_rng` y la mutación con `evo_rng`.

#### Scenario: Reproducción neutral con recombinación
- **WHEN** con `reproduction_mode="neutral"` el agente 4, con una candidata a pareja, se reproduce y `donor_rng` sortea al agente 9
- **THEN** el cromosoma recombinado empieza con un prefijo del cromosoma del agente 9, y `evo_rng` hace las extracciones del cruce antes de las de la mutación.

### Requirement: Depósito de Cadáveres en el Paso de Muerte (R35)
Con $R_{35}$ activa y `enable_evolution=True`, en el paso de muerte de la Fase 5, el motor SHALL invocar `env.deposit_carcass(agent_id, carcass_value, tick)`, en orden de `agent_id`, por cada agente con energía $\le 0$, por hambre o por depredación, **antes** de quitarlo del entorno. Las perturbaciones (`ablate_population`, `ablate_discoverers`) SHALL NOT dejar cadáver.

#### Scenario: Cadáver en la celda del muerto
- **WHEN** con `carcass_value = 0.6` el agente 9 muere de hambre en el tick 40
- **THEN** después del paso de muerte su celda contiene un recurso de patrón `CARCASS_PATTERN` y valor `0.6`, y el agente 9 ya no figura en `env.get_active_agent_ids()`.

#### Scenario: Varios muertos en el mismo tick
- **WHEN** los agentes 12 y 5 mueren en el paso de muerte del mismo tick
- **THEN** el cadáver del agente 5 recibe un `resource_id` menor que el del agente 12.

#### Scenario: Ablación sin cadáver
- **WHEN** con $R_{35}$ activa se invoca `ablate_population(0.5)`
- **THEN** no se deposita ningún cadáver.

### Requirement: Consumo de Cadáveres como Recurso Elemental
Comer un cadáver SHALL seguir en la Fase 4 el camino de cualquier recurso elemental: aprendizaje directo, suma a `direct_discoverers`, ganancia `energy_gain_scale * carcass_value` y, con $R_{19}$, depósito de estigmergia.

#### Scenario: Cadáver comido
- **WHEN** con `energy_gain_scale = 0.5` el agente 3 consume un cadáver de valor 0.6
- **THEN** gana 0.3 de energía (con tolerancia `1e-9`), aprende `CARCASS_PATTERN` por experiencia directa y figura en `direct_discoverers[CARCASS_PATTERN]`.

### Requirement: Orden de la Fase 5 con la Fase II-B
La Fase 5 SHALL ejecutar en orden: (i) `decay_memory`; (ii) sello de $R_{31}$, costo de coordinación, `SPLIT` y `BOND`; (iii) metabolismo con ADN, senescencia, endospora y costo de los ataques; (iv) muerte, cadáveres ($R_{35}$) y registro del estrés; (v) reproducción con SOS, recombinación, ADN e impronta; (vi) conjugación y ensayo CRISPR; (vii) $R_{18}$ y roles; (viii) `env.step_dynamics`; y después `on_tick_end` de los observadores.

#### Scenario: Reducción al orden de la Fase II
- **WHEN** se ejecuta un tick con todas las banderas de la Fase II-B apagadas
- **THEN** la Fase 5 se reduce exactamente al orden de la Fase II: `decay_memory`, coordinación, `SPLIT` y `BOND`, metabolismo, muerte, reproducción, $R_{18}$, `env.step_dynamics` y métricas.

#### Scenario: Conjugación posterior a la reproducción
- **WHEN** con $R_{26}$ activa un agente nace en la Fase 5 del tick 20
- **THEN** el recién nacido figura entre los agentes vivos al empezar la conjugación del tick 20.

#### Scenario: Sin entrada en endospora en la Fase 5
- **WHEN** con $R_{28}$ activa una hoja termina el metabolismo con `energy <= phenotype.spore_threshold` sin haber ejecutado `SPORULATE`
- **THEN** la Fase 5 no la pone en endospora.

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
Después de sortear todas las transferencias, el motor SHALL aplicarlas con `receive_plasmid` en el orden de `hgt_rng.permutation(len(transferencias))` sobre la lista registrada si hay dos o más, guardar con `set_dna` el ADN que cambió y, con $R_{27}$ activa, abrir en el receptor el ensayo `trials[codón] = (tick, energía actual, 0.0)`; un `None` de `receive_plasmid` bloquea la transferencia y cuenta como rechazo.

#### Scenario: Transferencia aplicada con ensayo
- **WHEN** con $R_{26}$ y $R_{27}$ activas el agente 2, con `energy = 1.4`, recibe en el tick 30 un codón que no tiene
- **THEN** el codón queda al final de sus `plasmids` y se abre el ensayo `trials[codón] = (30, 1.4, 0.0)`.

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
Con todas las banderas de la Fase II-B (design D31 y D52) en `False`, el motor, el agente, la memoria, la grilla, `TickMetrics`, `EvolutionaryTickMetrics` y todos los generadores SHALL comportarse exactamente como en la Fase II: ninguna rama nueva consume un generador ni cambia un valor o un orden de iteración.

#### Scenario: Hashes dorados y protocolos de la Fase II
- **WHEN** se ejecutan `tests/test_performance_equivalence.py` y los protocolos `002a` y `003a` con las banderas por defecto
- **THEN** los hashes SHA-256 dorados no cambian y los historiales `history` y `evolutionary_history` son idénticos a los de la Fase II.

### Requirement: Reproducibilidad del ADN entre Procesos
Con `enable_compact_dna=True` y las reglas de la Fase II-B activas, los historiales SHALL ser idénticos entre procesos con distinto `PYTHONHASHSEED`.

#### Scenario: Igualdad entre procesos
- **WHEN** se ejecuta la misma configuración de `25b` con la misma semilla en dos procesos con `PYTHONHASHSEED=0` y `PYTHONHASHSEED=123`
- **THEN** `history`, `evolutionary_history`, `genetic_history` y `ecology_history` son idénticos.

## MODIFIED Requirements

### Requirement: Orden de Fases del Tick
`step()` SHALL ejecutar el tick `next_tick` en este orden y luego incrementarlo: (0) con `enable_compact_dna=True`, expresión del fenotipo; (1) percepción, germinación, percepción social, emisión, estigmergia y vista del holón; (2) intercambio social en dos pasadas y vista del holón; (3) decisión con la política de cada agente, contexto de los compuestos y `on_decisions`; (4) ejecución en el orden de la permutación y aprendizaje directo; (5) los pasos de "Orden de la Fase 5 con la Fase II-B".

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
