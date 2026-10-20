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

### Requirement: Puerto de Política de Acción
`src/ide/agent/policy.py` SHALL definir `PolicyPort(Protocol)` con el método `decide(agent, obs, social, tick, rng) -> AgentAction`, donde `social` es una `SocialPerception` o `None`, de modo que la conducta del agente sea un componente intercambiable (design D45.1).

#### Scenario: Política de prueba conforme al puerto
- **WHEN** se define una clase con `decide(self, agent, obs, social, tick, rng)` que devuelve siempre `AgentAction(ActionType.IDLE)` y se la usa como política de un `MicroAgent`
- **THEN** `decide_action` del agente devuelve `AgentAction(ActionType.IDLE)` para cualquier observación.

### Requirement: Política Escrita a Mano
`HandwrittenPolicy.decide` SHALL contener sin cambios la lógica de decisión de la Fase I: consumir el recurso alcanzable conocido y benéfico de mayor $\hat{v} \cdot c$, explorar con probabilidad $\epsilon$, navegar hacia un objetivo conocido o caminar al azar, con los mismos desempates y las mismas extracciones de `rng`, e ignorar `social` (design D45.2).

#### Scenario: Misma decisión y mismo consumo del generador
- **WHEN** para un conjunto de observaciones y estados de creencias se compara `HandwrittenPolicy().decide(agent, obs, social, tick, rng)` con la decisión de la Fase I, con generadores gemelos y con `social` en `None` y en una `SocialPerception` no vacía
- **THEN** las acciones son idénticas y los generadores terminan en el mismo estado.

### Requirement: Delegación de la Decisión en la Política
`MicroAgent(agent_id, config, trust_strategy=None, protocol=None, policy=None)` SHALL usar `HandwrittenPolicy()` cuando `policy` es `None`, y `decide_action(obs, tick, rng, social=None)` SHALL devolver `policy.decide(self, obs, social, tick, rng)`; la llamada de la Fase I `decide_action(obs, tick, rng)` SHALL seguir siendo válida (design D45.3).

#### Scenario: Delegación con y sin percepción social
- **WHEN** un agente construido con una política de prueba que registra sus argumentos invoca `decide_action(obs, 5, rng)` y después `decide_action(obs, 6, rng, social)`
- **THEN** la política recibe al propio agente, `obs`, `rng` y los ticks 5 y 6, con `social is None` en la primera llamada y el objeto `social` dado en la segunda.

#### Scenario: Política por defecto
- **WHEN** se construye `MicroAgent(7, SimulationConfig())` sin `policy`
- **THEN** su `decide_action(obs, tick, rng)` coincide con `HandwrittenPolicy().decide(agent, obs, None, tick, rng)` con generadores gemelos.

### Requirement: Herencia de la Política
`create_offspring` SHALL propagar al hijo la política de su progenitor, de modo que toda la descendencia de un fundador decida con la misma política (design D45.3).

#### Scenario: Hijo con la política del progenitor
- **WHEN** un agente construido con una política de prueba que registra sus llamadas invoca `create_offspring` y el hijo invoca `decide_action`
- **THEN** la decisión del hijo la toma esa misma política.

### Requirement: Aislamiento del Módulo policy.py
`src/ide/agent/policy.py` SHALL cumplir las invariantes de `src/ide/agent/`: SHALL NOT importar `ide.environments`, `ide.simulation` ni `ide.experiments`, SHALL importar `micro_agent` sólo bajo `TYPE_CHECKING`, SHALL NOT construir `Message` ni referenciar `MessageType`, y no ve coordenadas ni `true_value` (design D45.5 y precisión 29).

#### Scenario: Auditoría AST de policy.py
- **WHEN** un test recorre el AST de `src/ide/agent/policy.py`
- **THEN** no encuentra importaciones de `ide.environments`, `ide.simulation` ni `ide.experiments`, ni importaciones de `ide.agent.micro_agent` fuera de un bloque `if TYPE_CHECKING:`, ni llamadas a `Message(...)`, ni referencias a `MessageType`.

### Requirement: Contexto de la Última Expresión
`MicroAgent` SHALL exponer `last_context: EpigeneticContext`, el contexto de su última expresión: el de la Fase 0 del tick o, en un recién nacido, el de su nacimiento; la política genética SHALL evaluar los impulsos con ese contexto (precisión 23).

#### Scenario: Contexto de nacimiento y de la Fase 0
- **WHEN** nace un hijo con ADN y energía `0.55`, con `reproduction_threshold = 2.2`, y después invoca `express(EpigeneticContext(2, EpigeneticRole.NERVE, 0.9), 41)`
- **THEN** al nacer `last_context == EpigeneticContext(0, EpigeneticRole.NONE, 0.25)` y, tras `express`, `last_context == EpigeneticContext(2, EpigeneticRole.NERVE, 0.9)`.

### Requirement: Señales Sensoriales Construidas por la Política Genética
`GeneticPolicy` SHALL usar `SocialPerception()` cuando `social` es `None` (precisión 24) y construir `SensorySignals` con `known_good` (algún recurso visible conocido y benéfico según `get_effective_belief`), `unknown` (algún recurso visible desconocido), `no_resource` (sin recursos visibles), `neighbor_adjacent` (`social.adjacent` no vacío), `weaker_adjacent`, `stronger_near` (`social.flee_move is not None`), `crowded` y `carcass` (`social.carcass_visible`) (D46.2, D47.4).

#### Scenario: Señales desde la observación, las creencias y lo social
- **WHEN** la observación tiene un recurso visible a distancia 2 cuyo patrón el agente cree con $\hat{v} = +1.0$ y `c = 0.80`, ningún recurso desconocido, y `social = SocialPerception(adjacent=(4,), weakest_adjacent=4, weaker_adjacent=True, crowded=True)`
- **THEN** las señales tienen `known_good`, `neighbor_adjacent`, `weaker_adjacent` y `crowded` en `True`, y `unknown`, `no_resource`, `stronger_near` y `carcass` en `False`.

#### Scenario: Sin percepción social
- **WHEN** `GeneticPolicy.decide` recibe `social=None` y los únicos impulsos positivos son los de `SHARE`, `ATTACK` y `FLEE`, con `enable_energy_transfer=True` y `enable_predation=True`
- **THEN** las señales sociales son `False`, ninguna de esas conductas es factible y `decide` devuelve `AgentAction(ActionType.IDLE)`.

### Requirement: Orden de Prueba de la Política Genética
`GeneticPolicy.decide` SHALL calcular las señales y los impulsos con `evaluate_drives(agent.dna, agent.last_context, signals, agent.base_config)`, recorrer las conductas con $d_B > 0$ en orden de $(-d_B, \text{posición en Behavior})$, evaluar su factibilidad de forma perezosa en ese orden, deteniéndose en la primera factible, y devolver su acción, o `IDLE` si ninguna lo es (D46.4, precisiones 23 y 25).

#### Scenario: Caminar antes que consumir
- **WHEN** el ADN del agente sólo tiene impulsos `WANDER = 0.5` y `CONSUME = 0.25`, hay un recurso alcanzable conocido y benéfico y hay movimientos disponibles
- **THEN** `decide` devuelve `MOVE` a `available_moves[int(rng.integers(len(available_moves)))]`.

#### Scenario: Empate resuelto por la posición en la tabla
- **WHEN** los impulsos de `CONSUME` y `WANDER` valen ambos `0.5`, y hay un recurso alcanzable conocido y benéfico
- **THEN** `decide` devuelve `INTERACT` sobre ese recurso, sin extraer de `rng`.

#### Scenario: Impulsos no positivos o conductas no factibles
- **WHEN** el único impulso positivo es el de `SHARE` con `enable_energy_transfer=False`, y el de `CONSUME` es negativo aunque haya un recurso benéfico alcanzable
- **THEN** `decide` devuelve `AgentAction(ActionType.IDLE)` y `rng` no cambia de estado.

### Requirement: Factibilidad de las Conductas sobre Recursos
`CONSUME` SHALL ser factible si hay un recurso alcanzable conocido y benéfico (`INTERACT` sobre el de mayor $\hat{v} \cdot c$, desempate por menor `resource_id`); `EXPLORE`, si hay uno alcanzable desconocido y `rng.random() < epsilon_explore` expresado, con la extracción sólo si existe (`INTERACT` sobre el de menor `resource_id`); `NAVIGATE` y `WANDER`, como en `HandwrittenPolicy` (design D46.1).

#### Scenario: Exploración sin candidatos no consume el generador
- **WHEN** el único impulso positivo es el de `EXPLORE` y no hay recursos alcanzables desconocidos
- **THEN** `decide` devuelve `AgentAction(ActionType.IDLE)` y `rng` no cambia de estado.

#### Scenario: Navegación ablacionada
- **WHEN** el único impulso positivo es el de `NAVIGATE`, `enable_navigation=False` y hay un recurso conocido y benéfico a `distance = 2`
- **THEN** `NAVIGATE` no es factible y `decide` devuelve `AgentAction(ActionType.IDLE)`.

### Requirement: Factibilidad de las Conductas Sociales y de Estado
`SHARE` SHALL ser factible con `enable_energy_transfer`, `social.adjacent` no vacío y `energy > 0` (`SHARE` sobre `social.weakest_adjacent`); `ATTACK`, con `enable_predation` y `social.weaker_adjacent` (`ATTACK` sobre `social.weakest_adjacent`); `FLEE`, con `social.flee_move is not None` (`MOVE` con `social.flee_move`); y `SPORULATE`, con `enable_evolution`, `enable_sporulation` (de `agent.config`) y `energy <= phenotype.spore_threshold` (D46.1, D50.2, precisiones 11 y 30).

#### Scenario: Ataque al vecino más débil
- **WHEN** el único impulso positivo es el de `ATTACK`, `enable_predation=True` y `social = SocialPerception(adjacent=(3, 8), weakest_adjacent=8, weaker_adjacent=True)`
- **THEN** `decide` devuelve `AgentAction(ActionType.ATTACK, 8)`.

#### Scenario: Esporulación por debajo del umbral expresado
- **WHEN** el único impulso positivo es el de `SPORULATE`, con `enable_evolution=True` y `enable_sporulation=True`, primero con `energy` igual a `phenotype.spore_threshold` y después mayor
- **THEN** `decide` devuelve `AgentAction(ActionType.SPORULATE)` en el primer caso e `IDLE` en el segundo.

#### Scenario: Donante sin energía
- **WHEN** el único impulso positivo es el de `SHARE`, `enable_energy_transfer=True`, `social = SocialPerception(adjacent=(3,), weakest_adjacent=3)` y la energía del agente es `0.0`
- **THEN** `SHARE` no es factible y `decide` devuelve `AgentAction(ActionType.IDLE)`.

#### Scenario: Huida
- **WHEN** el único impulso positivo es el de `FLEE` y `social.flee_move == (1, 0)`
- **THEN** `decide` devuelve `AgentAction(ActionType.MOVE, (1, 0))`.

### Requirement: Fundador Genético Equivalente a la Política Escrita a Mano
Con el ADN fundador de `enable_genetic_policy=True`, `GeneticPolicy.decide` SHALL devolver, para toda observación, todo estado de creencias y toda percepción social, la misma acción que `HandwrittenPolicy.decide` y dejar `rng` en el mismo estado (design D46.5).

#### Scenario: Equivalencia por propiedades
- **WHEN** Hypothesis (perfil `ci`, `derandomize=True`) genera observaciones, creencias, `epsilon_explore`, `enable_navigation` y percepciones sociales, y se decide con las dos políticas y generadores gemelos sobre un agente con el ADN fundador conductual
- **THEN** las acciones son idénticas y los generadores terminan en el mismo estado en todos los casos.

### Requirement: Caché de Impulsos Equivalente a la Evaluación Directa
`MicroAgent` MAY memoizar los impulsos por la clave de contexto del caché de expresión y las `SensorySignals`; el caché SHALL invalidarse cuando cambia el ADN y SHALL dar siempre los mismos impulsos que `evaluate_drives` (design D46.8).

#### Scenario: Caché frente a evaluación directa
- **WHEN** un agente con la política genética decide en una secuencia de contextos y señales variadas, con un `set_dna` intermedio
- **THEN** en cada decisión los impulsos usados son iguales a `evaluate_drives(agent.dna, context, signals, agent.base_config)`.

### Requirement: Puerta de Comunicación
`MicroAgent.communicates` SHALL valer `phenotype.comm_propensity >= 0.5` con `GeneticPolicy` y `True` con `HandwrittenPolicy`; con `communicates == False`, `BeliefExchangeProtocol` SHALL no emitir ni responder consultas, pero SHALL asimilar los testimonios recibidos. La puerta vive en `protocol.py` y no consume generadores (design D46.6).

#### Scenario: Agente que no comunica pero aprende
- **WHEN** un agente con `GeneticPolicy`, `comm_propensity_base = 0.0` y el ADN fundador, con vecinos y creencias confiables, emite y después recibe un `QUERY_PATTERN` y un `BROADCAST_BELIEF` de un vecino
- **THEN** `communicates is False`, `perceive_and_emit_messages` devuelve `[]`, `process_incoming_messages` devuelve `[]` y la creencia difundida queda asimilada.

#### Scenario: Umbral exacto y política escrita a mano
- **WHEN** se construye un agente con `GeneticPolicy` y `comm_propensity_base = 0.5`, y otro con `HandwrittenPolicy` y `comm_propensity_base = 0.0`
- **THEN** los dos tienen `communicates is True`.

## MODIFIED Requirements

### Requirement: Firmas Públicas Canónicas
`MicroAgent(agent_id, config, trust_strategy=None, protocol=None, policy=None)` SHALL exponer las propiedades de sólo lectura `agent_id`, `config`, `memory` y `capabilities`, y los métodos `perceive_and_emit_messages(obs, tick)`, `process_incoming_messages(messages, tick)`, `decide_action(obs, tick, rng, social=None)`, `learn_from_experience(pattern, real_value, tick)`, `decay_memory(tick)`, `get_effective_belief(pattern)` y `assimilate_testimony(belief, sender_id, tick)` (precisión 22).

#### Scenario: Inspección de la interfaz
- **WHEN** se inspeccionan con `inspect.signature` los métodos públicos de `MicroAgent`
- **THEN** los nombres y parámetros coinciden exactamente con los de `design.md`, y los parámetros `policy` del constructor y `social` de `decide_action` valen `None` por defecto.

#### Scenario: Llamada de la Fase I a decide_action
- **WHEN** se invoca `decide_action(obs, tick, rng)` con tres argumentos
- **THEN** la llamada es válida y equivale a `decide_action(obs, tick, rng, social=None)`.

### Requirement: Semántica del Protocolo Aislada
Dentro de `src/ide/agent/`, sólo `protocol.py` SHALL construir `Message` o referenciar `MessageType`; `MicroAgent(agent_id, config, trust_strategy=None, protocol=None, policy=None)` SHALL delegar la emisión y la recepción en el protocolo inyectado (por defecto `BeliefExchangeProtocol`), y todo conocimiento social SHALL entrar por `assimilate_testimony`.

#### Scenario: Auditoría del protocolo
- **WHEN** se analiza con `ast` cada archivo de `src/ide/agent/` distinto de `protocol.py`
- **THEN** ninguno contiene una llamada a `Message(...)` ni una referencia a `MessageType`.

#### Scenario: Protocolo inyectado
- **WHEN** se construye un `MicroAgent` con un protocolo de prueba cuyo `emit` devuelve siempre `[]`
- **THEN** `perceive_and_emit_messages` devuelve `[]` aunque el agente tenga vecinos y creencias difundibles.

### Requirement: Implementación del Protocolo AgentNode de Nivel Cero y Estado de Linaje
`MicroAgent` SHALL conservar sus 8 firmas y 4 propiedades de Fase I, salvo los parámetros opcionales finales `policy=None` del constructor y `social=None` de `decide_action` (design D45.3), y exponer `energy`, `generation`, `parent_id`, `genome`, `node_id`, `holon_level` (`0`), `leaf_agents` (`(self,)`), `effective_capacity`, `collective_memory()`, `own_belief(pattern)`, `apply_energy_delta(delta)`, `clear_holon_beliefs()`, `inject_ephemeral_belief(unit)` y `MicroAgent.from_lineage(...)`.

#### Scenario: Compatibilidad de firmas canónicas e implementación de AgentNode
- **WHEN** se instancia `a = MicroAgent(7, SimulationConfig())`
- **THEN** `a.node_id == 7`, `a.holon_level == 0`, `a.leaf_agents == (a,)`, `a.generation == 0`, `a.parent_id is None`, `a.energy == a.config.initial_energy`, `inject_ephemeral_belief` alimenta `_holon_tick_beliefs` sin ser borrado por `perceive_and_emit_messages`, y las firmas de los 8 métodos de Fase I permanecen inalteradas salvo esos dos parámetros opcionales finales.


### Requirement: Creación de Descendiente con Herencia Genética
`MicroAgent.create_offspring(child_id, tick, rng, genome_source=None, dna_source=None, mutation_scale=1.0) -> MicroAgent` SHALL particionar la energía con `offspring_energy_share`, asignar `generation + 1` y `parent_id = self.agent_id` y, sin ADN, mutar con `mutate_genome` el genoma de `genome_source` o, si es `None`, el propio; con ADN, sigue "Descendencia con ADN y Escala de Mutación"; no transfiere creencias: la herencia cultural la entrega el motor por `assimilate_testimony`.

#### Scenario: Creación de descendiente con conservación de energía
- **WHEN** un `MicroAgent` con `energy = 2.0` y `generation = 1` invoca `create_offspring(child_id=99, tick=25, rng=rng)` con `offspring_energy_share = 0.5`
- **THEN** el progenitor queda con `energy == 1.0` y el hijo retornado tiene `agent_id == 99`, `parent_id == parent.agent_id`, `generation == 2`, `energy == 1.0` y `len(child.memory) == 0`.

#### Scenario: Firma extendida con valores por defecto neutros
- **WHEN** se inspecciona `MicroAgent.create_offspring` con `inspect.signature`
- **THEN** sus parámetros, en orden, son `child_id`, `tick`, `rng`, `genome_source=None`, `dna_source=None` y `mutation_scale=1.0`.
