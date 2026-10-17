# Spec Delta: Holonic Hierarchy

## Purpose

Proveer la arquitectura holónica recursiva sin tope de niveles ($L = 0, 1, 2, \dots, K$) mediante el patrón *Composite* (`AgentNode` y `CompositeAgent`), permitiendo que micro-agentes y holones formen unidades funcionales de orden superior con memoria colectiva distribuida, operadores dinámicos de fusión simbiótica (`BOND`, $R_{15}$) y fisión (`SPLIT`, $R_{16}$), reproducción simbiótica de holones ($R_{17}$) y causalidad descendente intra-holón ($R_{18}$).

## ADDED Requirements

### Requirement: Protocolo Recursivo AgentNode y Clase CompositeAgent
`src/ide/agent/holon.py` SHALL definir `@runtime_checkable class AgentNode(Protocol)` y `CompositeAgent` (con `node_id`, `holon_level`, `leaf_agents`, `effective_capacity` y `collective_memory()`), aceptando cualquier tupla de $\ge 2$ hijos `AgentNode` sin hojas repetidas y calculando recursivamente `holon_level = 1 + max(c.holon_level for c in children)` sin límite superior de nivel.

#### Scenario: Composición multinivel arbitraria (L=1, L=2, L=3)
- **WHEN** se agrupan dos `MicroAgent` ($L=0$) en un `CompositeAgent` $H_1$, otros dos en $H_2$, luego se agrupan $H_1$ y $H_2$ en $S_1$, y finalmente $S_1$ con un quinto `MicroAgent` en $M_1$
- **THEN** `H1.holon_level == 1`, `S1.holon_level == 2`, `M1.holon_level == 3`, `len(M1.leaf_agents) == 5` y todos cumplen `isinstance(node, AgentNode)`.

#### Scenario: Rechazo de holón degenerado
- **WHEN** se intenta construir un `CompositeAgent` con menos de 2 nodos hijos o con hojas `MicroAgent` duplicadas entre subárboles
- **THEN** se lanza `ValueError`.

### Requirement: Memoria Colectiva Distribuida del Holón
`CompositeAgent.collective_memory()` SHALL devolver el diccionario `dict[Pattern, KnowledgeUnit]` resultante de unir las creencias en `BoundedMemory` de sus hojas, seleccionando para cada `Pattern` la `KnowledgeUnit` que maximiza `(confidence, last_updated_tick, -agent_id)`, manteniendo intacto el límite $C_{\max, \ell}$ de cada hoja.

#### Scenario: Superación holónica de la barrera de capacidad individual
- **WHEN** tres `MicroAgent` con $C_{\max} = 3$ conocen conjuntos disjuntos de 3 patrones cada uno y forman un `CompositeAgent` $U$
- **THEN** cada hoja sigue teniendo `len(leaf.memory) == 3`, pero `len(U.collective_memory()) == 9`.

### Requirement: Operador de Fusión Simbiótica BOND (R15)
Con `enable_holonic_hierarchy=True`, el operador `BOND` SHALL evaluar pares de nodos raíz con hojas a distancia toroidal $\le 1$ cuya masa combinada no supere `max_holon_leaves`, fusionándolos en un nuevo `CompositeAgent` cuando su complementariedad epistémica de Jaccard ponderada por $\bar{\omega}_{\text{bond}}$ alcance `holon_bond_threshold`.

#### Scenario: Fusión entre especialistas complementarios
- **WHEN** dos nodos raíz en la misma celda conocen conjuntos disjuntos no vacíos de patrones ($\mathcal{S}_{\text{comp}} = 1.0$), tienen $\bar{\omega}_{\text{bond}} = 0.8$ y `holon_bond_threshold = 0.5`
- **THEN** el operador `BOND` crea un `CompositeAgent` que los contiene como `children` y ambos dejan de ser nodos raíz independientes.

#### Scenario: Rechazo de fusión entre clones redundantes
- **WHEN** dos nodos raíz conocen exactamente el mismo conjunto de patrones ($\mathcal{S}_{\text{comp}} = 0.0$) y `holon_bond_threshold = 0.3`
- **THEN** no se fusionan.

### Requirement: Costo de Coordinación y Operador de Fisión SPLIT (R16)
En cada tick con `enable_holonic_hierarchy=True`, cada `CompositeAgent` raíz $U$ SHALL descontar, si `enable_evolution=True`, $c_{\text{enlace}} \cdot |U| \cdot L(U)$ repartido entre sus hojas y, si `enable_holon_splitting=True` y acumula `holon_split_patience` ticks sin superávit (definido en design D24) o su energía cae bajo $|U| \cdot E_{\text{min\_holon}}$, SHALL disolverse liberando a sus `children` directos como nodos raíz.

#### Scenario: Fisión de holón deficitario
- **WHEN** un `CompositeAgent` de nivel 1 supera `holon_split_patience` ticks consecutivos sin obtener superávit cooperativo con `enable_holon_splitting=True`
- **THEN** el holón se disuelve y sus nodos hijos vuelven a operar como nodos raíz autónomos sin pérdida de sus memorias individuales.

### Requirement: Causalidad Descendente y Particionamiento Epigenético Intra-Holón (R18)
Con `enable_downward_causation=True`, para cada hoja de un `CompositeAgent` raíz el sistema SHALL marcar como redundantes, vía `set_redundant_patterns` con `redundancy_penalty` ($\psi_{\text{red}} \in (0, 1]$), los patrones que otra hoja en alcance local conoce con más confianza (empate: menor `agent_id`). Esta regla está diseñada para ortogonalizar memorias.

#### Scenario: Desalojo preferente de creencia redundante dentro del holón
- **WHEN** los agentes 1 y 2 forman un holón, están en alcance local, tienen `enable_downward_causation=True` y `redundancy_penalty = 0.2`, ambos conocen $\rho_0$ con `c = 0.9`, el agente 2 también conoce $\rho_1$ con `c = 0.5` (que el agente 1 no conoce), y el agente 2 de capacidad 2 recibe un nuevo patrón $\rho_2$ con `c = 0.6`
- **THEN** (con $|\hat{v}| = 1$ y la misma edad para todas las creencias) en la memoria del agente 2 la utilidad de $\rho_0$ se penaliza por `0.2` (`0.18 < 0.5`), por lo que el agente 2 desaloja la copia redundante de $\rho_0$ y conserva $\rho_1$ junto con $\rho_2$, elevando la cobertura colectiva del holón de 2 a 3 patrones.

### Requirement: Endosimbiosis Reproductiva Holónica (R17)
Cuando `enable_holon_reproduction=True` y `enable_evolution=True`, un nodo raíz `CompositeAgent` $U$ con energía agregada $\ge |U| \cdot E_{\text{reprod}}$ y cupo poblacional (`len(agents) + |U| <= max_population`) SHALL reproducirse como unidad simbiótica completa (`reproduce_holon`), engendrando una hoja hija por cada hoja parental y replicando la topología arbórea de $U$.

#### Scenario: Reproducción de un holón preservando su topología y especialización
- **WHEN** un `CompositeAgent` $U$ de nivel 2 formado por 3 hojas especialistas alcanza energía total `>= 3 * reproduction_threshold` con `enable_holon_reproduction=True` y hay cupo para 3 nuevos agentes
- **THEN** nacen 3 nuevos `MicroAgent` hijos ensamblados en un nuevo `CompositeAgent` $U_{\text{hijo}}$ de nivel 2 con idéntica estructura de árbol y memorias heredadas complementarias.

### Requirement: Poda Recursiva de Hojas Muertas en Árboles Holónicos
`prune_dead_leaves(node, alive_ids)` SHALL actualizar recursivamente cualquier `CompositeAgent` tras la muerte de uno o más `MicroAgent`: si un sub-holón queda con una única hoja sobreviviente, SHALL colapsar directamente a ese nodo sobreviviente; si queda con cero hojas sobrevivientes, SHALL devolver `None`.

#### Scenario: Colapso parcial de un sub-holón en un árbol de nivel 2
- **WHEN** un `CompositeAgent` $S$ de nivel 2 tiene como hijos a $H_1 = (a_1, a_2)$ y $H_2 = (a_3, a_4)$, y el agente $a_1$ muere (`alive_ids = {2, 3, 4}`)
- **THEN** tras `prune_dead_leaves(S, {2, 3, 4})`, $H_1$ colapsa a $a_2$ y los hijos de $S$ pasan a ser `(a_2, H_2)` con `len(S.leaf_agents) == 3`.
