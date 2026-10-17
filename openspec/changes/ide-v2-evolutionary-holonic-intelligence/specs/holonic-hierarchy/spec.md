# Spec Delta: Holonic Hierarchy

## Purpose

Proveer la arquitectura holónica recursiva sin tope de niveles ($L = 0, 1, 2, \dots, K$) mediante el patrón *Composite* (`AgentNode` y `CompositeAgent`), permitiendo que micro-agentes y holones formen unidades funcionales de orden superior con memoria colectiva distribuida, operadores dinámicos de fusión simbiótica (`BOND`, $R_{15}$) y fisión (`SPLIT`, $R_{16}$), reproducción simbiótica de holones ($R_{17}$) y causalidad descendente intra-holón ($R_{18}$).

## ADDED Requirements

### Requirement: Protocolo Recursivo AgentNode y Clase CompositeAgent
El sistema SHALL definir en `src/ide/agent/holon.py` el protocolo `@runtime_checkable class AgentNode(Protocol)` y la clase `CompositeAgent`, de modo que tanto `MicroAgent` ($L=0$) como `CompositeAgent` ($L \ge 1$) implementen `AgentNode` con las propiedades `node_id: int`, `holon_level: int`, `leaf_agents: tuple[MicroAgent, ...]`, `effective_capacity: int` y el método `collective_memory() -> dict[Pattern, KnowledgeUnit]`. Un `CompositeAgent` SHALL aceptar como hijos cualquier tupla no vacía de al menos 2 `AgentNode` (`MicroAgent` o `CompositeAgent` de niveles cualesquiera), calculando recursivamente `holon_level = 1 + max(c.holon_level for c in children)` sin límite superior de nivel.

#### Scenario: Composición multinivel arbitraria (L=1, L=2, L=3)
- **WHEN** se agrupan dos `MicroAgent` ($L=0$) en un `CompositeAgent` $H_1$, otros dos en $H_2$, luego se agrupan $H_1$ y $H_2$ en $S_1$, y finalmente $S_1$ con un quinto `MicroAgent` en $M_1$
- **THEN** `H1.holon_level == 1`, `S1.holon_level == 2`, `M1.holon_level == 3`, `len(M1.leaf_agents) == 5` y todos cumplen `isinstance(node, AgentNode)`.

#### Scenario: Rechazo de holón degenerado
- **WHEN** se intenta construir un `CompositeAgent` con menos de 2 nodos hijos o con hojas `MicroAgent` duplicadas entre subárboles
- **THEN** se lanza `ValueError`.

### Requirement: Memoria Colectiva Distribuida del Holón
`CompositeAgent.collective_memory()` SHALL devolver el diccionario `dict[Pattern, KnowledgeUnit]` resultante de unir las creencias en `BoundedMemory` de todas sus hojas `leaf_agents`, seleccionando para cada `Pattern` la `KnowledgeUnit` de mayor `confidence` (desempatando por mayor `last_updated_tick` y menor `agent_id` de la hoja portadora), sin violar la restricción de que cada hoja individual almacena a lo sumo $C_{\max, \ell}$ creencias.

#### Scenario: Superación holónica de la barrera de capacidad individual
- **WHEN** tres `MicroAgent` con $C_{\max} = 3$ conocen conjuntos disjuntos de 3 patrones cada uno y forman un `CompositeAgent` $U$
- **THEN** cada hoja sigue teniendo `len(leaf.memory) == 3`, pero `len(U.collective_memory()) == 9`.

### Requirement: Operador de Fusión Simbiótica BOND (R15)
Con `enable_holonic_hierarchy=True`, el operador de fusión SHALL evaluar pares de nodos raíz co-localizados en la misma celda (o dentro de `bond_radius = 1`) cuya masa combinada no supere `max_holon_leaves`, calculando la complementariedad epistémica de Jaccard $\mathcal{S}_{\text{comp}}(U_a, U_b) = |\mathcal{K}_a \triangle \mathcal{K}_b| / |\mathcal{K}_a \cup \mathcal{K}_b|$ sobre sus patrones conocidos válidamente ($0.0$ si ambos conjuntos son vacíos) ponderada por la media de $\omega_{\text{bond}}$ de sus hojas, y fusionándolos en un nuevo `CompositeAgent` de orden superior si dicho puntaje alcanza o supera `holon_bond_threshold` ($\theta_{\text{sinergia}}$).

#### Scenario: Fusión entre especialistas complementarios
- **WHEN** dos nodos raíz en la misma celda conocen conjuntos disjuntos no vacíos de patrones ($\mathcal{S}_{\text{comp}} = 1.0$), tienen $\bar{\omega}_{\text{bond}} = 0.8$ y `holon_bond_threshold = 0.5`
- **THEN** el operador `BOND` crea un `CompositeAgent` que los contiene como `children` y ambos dejan de ser nodos raíz independientes.

#### Scenario: Rechazo de fusión entre clones redundantes
- **WHEN** dos nodos raíz conocen exactamente el mismo conjunto de patrones ($\mathcal{S}_{\text{comp}} = 0.0$) y `holon_bond_threshold = 0.3`
- **THEN** no se fusionan.

### Requirement: Costo de Coordinación y Operador de Fisión SPLIT (R16)
En cada tick con `enable_holonic_hierarchy=True`, cada `CompositeAgent` activo $U$ SHALL incurrir en un costo metabólico de coordinación $c_{\text{coord}}(U) = c_{\text{enlace}} \cdot |U| \cdot L(U)$ repartido equitativamente entre sus hojas (`holon_coord_cost` = $c_{\text{enlace}}$); si el holón acumula `holon_split_patience` ticks sin superávit cooperativo neto o si su energía agregada cae por debajo de $|U| \cdot E_{\text{min\_holon}}$, y `enable_holon_splitting=True`, el holón SHALL disolverse liberando a sus `children` directos como nodos raíz independientes.

#### Scenario: Fisión de holón deficitario
- **WHEN** un `CompositeAgent` de nivel 1 supera `holon_split_patience` ticks consecutivos sin obtener superávit cooperativo con `enable_holon_splitting=True`
- **THEN** el holón se disuelve y sus nodos hijos vuelven a operar como nodos raíz autónomos sin pérdida de sus memorias individuales.

### Requirement: Causalidad Descendente y Particionamiento Epigenético Intra-Holón (R18)
Cuando `enable_downward_causation=True`, para cada `CompositeAgent` activo $U$, el sistema SHALL calcular el mapa de confianza máxima por patrón entre sus hojas y actualizar en cada hoja $\ell \in \text{leaves}(U)$ el conjunto de patrones redundantes (aquellos donde otra hoja $\ell' \neq \ell$ del mismo holón posee mayor confianza, o igual confianza y menor `agent_id`), de modo que la utilidad de memoria $U(k, t)$ de $\ell$ multiplique por `redundancy_penalty` ($\psi_{\text{red}} \in (0, 1]$) los patrones redundantes, induciendo ortogonalización espontánea de memorias ($\mathcal{M}_i \cap \mathcal{M}_j \to \emptyset$).

#### Scenario: Desalojo preferente de creencia redundante dentro del holón
- **WHEN** los agentes 1 y 2 forman un holón con `enable_downward_causation=True` y `redundancy_penalty = 0.2`, ambos conocen $\rho_0$ con `c = 0.9`, el agente 2 también conoce $\rho_1$ con `c = 0.5` (que el agente 1 no conoce), y el agente 2 de capacidad 2 recibe un nuevo patrón $\rho_2$ con `c = 0.6`
- **THEN** en la memoria del agente 2 la utilidad de $\rho_0$ se penaliza por `0.2` (`0.18 < 0.5`), por lo que el agente 2 desaloja la copia redundante de $\rho_0$ y conserva $\rho_1$ junto con $\rho_2$, elevando la cobertura colectiva del holón de 2 a 3 patrones.

### Requirement: Endosimbiosis Reproductiva Holónica (R17)
Cuando `enable_holon_reproduction=True` y `enable_evolution=True`, un nodo raíz `CompositeAgent` $U$ cuya energía agregada de hojas alcance o supere $|U| \cdot E_{\text{reprod}}$ y para el cual exista cupo poblacional (`len(agents) + |U| <= max_population`) SHALL reproducirse como unidad simbiótica completa (`reproduce_holon`), engendrando una hoja hija por cada hoja parental (con herencia genética $R_{13}$ y cultural $R_{14}$) y ensamblándolas inmediatamente con la misma topología jerárquica arbórea que $U$.

#### Scenario: Reproducción de un holón preservando su topología y especialización
- **WHEN** un `CompositeAgent` $U$ de nivel 2 formado por 3 hojas especialistas alcanza energía total `>= 3 * reproduction_threshold` con `enable_holon_reproduction=True` y hay cupo para 3 nuevos agentes
- **THEN** nacen 3 nuevos `MicroAgent` hijos ensamblados en un nuevo `CompositeAgent` $U_{\text{hijo}}$ de nivel 2 con idéntica estructura de árbol y memorias heredadas complementarias.

### Requirement: Poda Recursiva de Hojas Muertas en Árboles Holónicos
`prune_dead_leaves(node, alive_ids)` SHALL actualizar recursivamente cualquier `CompositeAgent` tras la muerte de uno o más `MicroAgent`: si un sub-holón queda con una única hoja sobreviviente, SHALL colapsar directamente a ese nodo sobreviviente; si queda con cero hojas sobrevivientes, SHALL devolver `None`.

#### Scenario: Colapso parcial de un sub-holón en un árbol de nivel 2
- **WHEN** un `CompositeAgent` $S$ de nivel 2 tiene como hijos a $H_1 = (a_1, a_2)$ y $H_2 = (a_3, a_4)$, y el agente $a_1$ muere (`alive_ids = {2, 3, 4}`)
- **THEN** tras `prune_dead_leaves(S, {2, 3, 4})`, $H_1$ colapsa a $a_2$ y los hijos de $S$ pasan a ser `(a_2, H_2)` con `len(S.leaf_agents) == 3`.
