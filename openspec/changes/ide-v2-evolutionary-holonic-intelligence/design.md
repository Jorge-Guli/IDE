# Design: Fase II (v2.0) — Evolución Abierta, Herencia Dual y Arquitectura Holónica Recursiva

## Context

La Fase I (v1.0) del proyecto IDE implementó y verificó un ecosistema de micro-agentes con memoria acotada ($C_{\max} < N$), epistemología local e intercambio de creencias (`QUERY_PATTERN`, `QUERY_RESPONSE`, `BROADCAST_BELIEF`). Los 397 tests de la Fase I (379 en la suite por defecto y 18 marcados `slow` o `empirical`) imponen contratos estructurales y de reproducibilidad muy estrictos:
1. **`tests/test_performance_equivalence.py`:** Calcula hashes SHA-256 sobre `repr((engine.history, positions, memories, direct_discoverers))` para 6 configuraciones canónicas durante 120 ticks. Cualquier cambio en los campos de `TickMetrics`, o cualquier extracción adicional sobre `engine.rng` cuando las banderas de Fase II están apagadas, rompería estos hashes.
2. **`tests/test_domain_contracts.py`:** Verifica que `dataclasses.fields(VisibleResource)` sea exactamente `{resource_id, pattern, recommended_move, distance, is_reachable_now}` y que `vars(EnvironmentPort)` declare exactamente los 10 métodos de Fase I.
3. **`tests/test_micro_agent.py`:** Verifica mediante `ast` sobre todos los archivos `.py` bajo `src/ide/agent/` que:
   - Ningún archivo importe `environments`, `simulation`, `experiments` o `grid2d`.
   - Sólo `protocol.py` construya `Message(...)` o referencie `MessageType`.
   - Sólo `epistemology.py` y `MicroAgent.assimilate_testimony` referencien `merge_social_belief`.
   - Ningún archivo use `import ... as ...` sobre `Message`, `MessageType`, `merge_social_belief`, `types` o `epistemology`.
   - Las firmas públicas de los 8 métodos canónicos de `MicroAgent` coincidan exactamente con las de Fase I.
4. **`tests/test_attribution.py`:** Verifica que `DESIGN_RULES` contenga exactamente las 11 reglas `R1`..`R11`, que cada regla tenga `purpose` no vacío y que `AttributionReport.rules == DESIGN_RULES` en las corridas de 001-D.
5. **`tests/test_simulation_engine.py`:** Verifica sobre el AST que sólo `simulation/engine.py` **referencia** `get_reachable_true_values`; `domain/ports.py` y `environments/grid2d.py` sólo pueden **definirlo**.

**Fuentes normativas.** La Fase I vigente está en `openspec/specs/*/spec.md` y en el diseño archivado (`openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/design.md`, Decisiones D1–D18). Este documento es la **fuente única** de firmas, fórmulas, valores por defecto y desempates de la Fase II; `DEFINICIONES_FORMALES.md` y `DEFINICIONES_TECNICAS.md` lo resumen y, ante una discrepancia, rige este documento.

**Numeración de experimentos (v2).** 001 memoria (completado), 002 evolución y herencia, 003 holones y composición, 004 especialización, 005 shock ambiental, 006 protocolo emergente. Los docstrings del código que todavía usan la numeración v1 (002 confianza, 003 especialización, 005 compuestos, 006 evolución, 007 protocolo) se actualizan durante la implementación (tarea 1.2).

El diseño de la Fase II introduce metabolismo, selección natural, herencia genética y cultural vertical, jerarquía holónica recursiva sin límite de niveles ($L = 0, 1, \dots, K$), reproducción simbiótica de holones, causalidad descendente intra-holón y estigmergia espacial, respetando al $100\%$ todas las invariantes de Fase I.

---

## Goals / Non-Goals

**Goals:**
- Implementar el ciclo metabólico energético ($E_i(t)$) con penalización cuadrática de capacidad cerebral ($C_{\max, i}^2$), muerte por agotamiento ($E_i \le 0$) y reproducción diferencial ($E_i \ge E_{\text{reprod}}$, $R_{12}$).
- Implementar la Herencia Dual Intergeneracional: mutación genética acotada sobre `AgentGenome` ($R_{13}$) y transferencia cultural vertical de creencias madre-hijo con descuento $\gamma_{\text{gen}}$ ($R_{14}$).
- Implementar la Arquitectura Holónica Recursiva Ilimitada mediante el patrón *Composite* (`AgentNode` y `CompositeAgent` para niveles $L = 0, 1, 2, \dots, K$), con operadores dinámicos `BOND` ($R_{15}$) y `SPLIT` ($R_{16}$).
- Incorporar los tres pilares de la Síntesis Evolutiva Extendida: Endosimbiosis Reproductiva Holónica ($R_{17}$), Causalidad Descendente / Particionamiento Epigenético Intra-Holón ($R_{18}$) y Estigmergia Espacial ($R_{19}$).
- Introducir Recursos Compuestos Graduados (`CompositeRule` de orden $m \ge 2$) en `ToroidalGrid2D`, las métricas `M8` a `M12` en `EvolutionaryTickMetrics`, las reglas `R12`–`R19` y afirmaciones `C5`–`C8` en `attribution.py`, y los ejecutores `exp002_runner.py` y `exp003_runner.py`.
- Garantizar compatibilidad regresiva bit a bit con la Fase I cuando los mecanismos de Fase II están en su valor por defecto (inactivos).

**Non-Goals:**
- No se introducen redes neuronales profundas ni optimizadores por gradiente global.
- No se rompe ninguno de los 397 tests existentes de Fase I. Los archivos de test existentes pueden **ampliarse** con tests nuevos, pero los tests de Fase I no se modifican.
- No se altera la representación de `TickMetrics` ni la secuencia de `engine.rng` bajo las configuraciones de Fase I.

---

## Decisions (Numeradas D19 a D29, continuando D1–D18 de Fase I)

### Decisión 19: Aislamiento de Generadores Pseudoaleatorios (`evo_rng`) y Preservación de Hashes Dorados
Para garantizar que los 6 hashes SHA-256 de `tests/test_performance_equivalence.py` permanezcan intactos:
1. Todas las banderas de **activación** de Fase II en `SimulationConfig` tienen valor por defecto `False` y `num_composite_patterns` vale `0`. La única bandera con valor `True` es `enable_holon_splitting`, que sólo modula a `enable_holonic_hierarchy` y no tiene efecto mientras ésta sea `False`.
2. `SimulationEngine.__init__` instancia un generador dedicado `self.evo_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(config.seed, spawn_key=(2,))))`.
3. Toda operación estocástica nueva de Fase II usa un generador derivado de la semilla con `SeedSequence(seed, spawn_key=(k,))`, nunca `engine.rng`:
   - `spawn_key=(1,)`: `null_rng`, el control nulo de contenido (ya existe en Fase I).
   - `spawn_key=(2,)`: `evo_rng` del motor, para la mutación genética (`mutate_genome`) y la selección de celda en `spawn_agent_near`.
   - `spawn_key=(3,)`: `_comp_rng` de `ToroidalGrid2D`, para la ubicación inicial y la reposición de recursos compuestos.
   Cada generador sólo se consume cuando su mecanismo está activo (`enable_evolution=True`, `num_composite_patterns > 0`). Esta lista de generadores derivados es una excepción declarada a la regla "un único generador por motor" de CLAUDE.md, que se actualiza en consecuencia.
4. `TickMetrics` mantiene exactamente sus 14 campos de Fase I; la telemetría de Fase II se almacena en `EvolutionaryTickMetrics` dentro de `engine.evolutionary_history: list[EvolutionaryTickMetrics]`.

### Decisión 20: Extensión de Contratos de Dominio y Tabla Exacta de `SimulationConfig`
En `src/ide/domain/types.py` se agregan tres `@dataclass(frozen=True)` sin tocar `VisibleResource`. `CompositeRule` **ya existe** en `src/ide/domain/extensions.py` (campos `required_patterns`, `composite_value` y método `evaluate`) y se reutiliza sin cambios. Los valores por defecto de `AgentGenome` coinciden con los de `SimulationConfig` (el genoma fundador real se construye siempre con `genome_from_config`):

```python
@dataclass(frozen=True)
class AgentGenome:
    alpha_learning: float = 0.40
    gamma_social_discount: float = 0.75
    epsilon_explore: float = 0.15
    bond_affinity: float = 0.60
    memory_capacity: int = 3
    perception_radius: int = 2
    comm_radius: int = 2

@dataclass(frozen=True)
class StigmergicTrace:
    pattern: Pattern
    sign_value: float
    intensity: float
    last_updated_tick: int

@dataclass(frozen=True)
class HolonSnapshot:
    node_id: int
    holon_level: int
    child_node_ids: tuple[int, ...]
    leaf_agent_ids: tuple[int, ...]
    effective_capacity: int
    collective_known_patterns: int
```

En `src/ide/domain/ports.py`, `EnvironmentPort` conserva exactamente sus 10 métodos y se declara el sub-protocolo verificable en tiempo de ejecución:

```python
@runtime_checkable
class EvolutionaryEnvironmentPort(EnvironmentPort, Protocol):
    def spawn_agent_near(
        self,
        agent_id: int,
        anchor_agent_id: int,
        rng: np.random.Generator,
        perception_radius: int | None = None,
        comm_radius: int | None = None,
    ) -> tuple[int, int]: ...
    def set_agent_radii(
        self, agent_id: int, perception_radius: int, comm_radius: int
    ) -> None: ...
    def get_agent_distance(self, agent_a: int, agent_b: int) -> int: ...
    def get_composite_rules(self) -> dict[Pattern, CompositeRule]: ...
    def deposit_stigmergy(
        self, agent_id: int, pattern: Pattern, value: float, confidence: float, tick: int
    ) -> None: ...
    def get_cell_stigmergy(self, agent_id: int) -> tuple[StigmergicTrace, ...]: ...
    def get_active_stigmergy_cells(self) -> int: ...
```

En `src/ide/config.py`, `SimulationConfig` incorpora los siguientes campos al final del dataclass (todos con valores por defecto que mantienen inactivos los mecanismos de Fase II cuando se instancia `SimulationConfig()`):

```python
    # --- Fase II: Metabolismo, Evolución y Herencia Dual (R12, R13, R14) ---
    enable_evolution: bool = False
    initial_energy: float = 1.50
    reproduction_threshold: float = 2.20
    offspring_energy_share: float = 0.50
    max_population: int = 160
    metabolic_base_cost: float = 0.01
    memory_capacity_cost: float = 0.002
    sensory_radius_cost: float = 0.0005
    move_cost: float = 0.005
    message_cost: float = 0.001
    energy_gain_scale: float = 0.45
    mutation_rate: float = 0.05
    discrete_mutation_prob: float = 0.10
    max_genome_memory_capacity: int = 6
    initial_bond_affinity: float = 0.60
    enable_cultural_inheritance: bool = False
    inheritance_discount: float = 0.65

    # --- Fase II: Jerarquía Holónica, Endosimbiosis y Causalidad Descendente (R15-R18) ---
    enable_holonic_hierarchy: bool = False
    holon_bond_threshold: float = 0.35
    max_holon_leaves: int = 8
    holon_coord_cost: float = 0.002
    enable_holon_splitting: bool = True
    holon_split_patience: int = 25
    holon_min_energy_per_leaf: float = 0.30
    enable_holon_reproduction: bool = False
    enable_downward_causation: bool = False
    redundancy_penalty: float = 0.25

    # --- Fase II: Recursos Compuestos y Estigmergia Espacial (R19) ---
    num_composite_patterns: int = 0
    composite_order: int = 2
    composite_resources_per_pattern: int = 4
    composite_reward_exponent: float = 1.50
    composite_failure_penalty: float = 0.20
    enable_stigmergy: bool = False
    stigmergy_deposit_rate: float = 0.50
    stigmergy_decay: float = 0.02
```

**Reglas de validación en `SimulationConfig.__post_init__`:**
- Coeficientes en `[0.0, 1.0]`: `discrete_mutation_prob`, `initial_bond_affinity`, `holon_bond_threshold`, `inheritance_discount`, `stigmergy_deposit_rate`, `stigmergy_decay`.
- `offspring_energy_share` estrictamente en `(0.0, 1.0)` ($0 < \kappa_{\text{part}} < 1$).
- `redundancy_penalty` en `(0.0, 1.0]` ($0 < \psi_{\text{red}} \le 1$).
- Estrictamente positivos (`> 0.0`): `initial_energy`, `reproduction_threshold`, `energy_gain_scale`, `composite_reward_exponent`.
- No negativos (`>= 0.0`): `metabolic_base_cost`, `memory_capacity_cost`, `sensory_radius_cost`, `move_cost`, `message_cost`, `mutation_rate`, `holon_coord_cost`, `holon_min_energy_per_leaf`, `composite_failure_penalty`, `num_composite_patterns`.
- `composite_failure_penalty <= 1.0`, para que el valor experimentado de un fracaso compuesto quede en `[-1, 0]`.
- Enteros mínimos: `max_population >= 1`, `max_genome_memory_capacity >= memory_capacity`, `max_holon_leaves >= 2`, `holon_split_patience >= 1`, `composite_order >= 2`, `composite_resources_per_pattern >= 1`.
- Validación de orden compuesto frente a patrones benéficos disponibles: si `num_composite_patterns > 0` y `composite_order > num_world_patterns // 2`, lanza `ValueError` cuyo mensaje menciona `"composite_order"`.

**Reglas de Blindaje de Auditorías AST de Fase I:**
1. En `SimulationEngine.__init__`, las 4 comprobaciones de Fase I (`enable_specialization`, `epsilon_recheck > 0`, `tau_policy != "validation"`, `update_scheme != "synchronous"`) DEBEN seguir lanzando `NotImplementedError` para que `test_mecanismos_fuera_de_alcance_lanzan_not_implemented` siga pasando.
2. En cualquier archivo bajo `src/ide/agent/` (`evolution.py`, `holon.py`, `micro_agent.py`, `memory.py`):
   - Prohibido importar `environments`, `simulation`, `experiments` o `grid2d`.
   - Prohibido construir `Message(...)` o referenciar `MessageType` fuera de `protocol.py`.
   - Prohibido referenciar `merge_social_belief` fuera de `epistemology.py` y `MicroAgent.assimilate_testimony`.
   - Prohibido usar `import ... as ...` sobre `Message`, `MessageType`, `merge_social_belief`, `types` o `epistemology`.
3. Sólo `simulation/engine.py` puede **referenciar** el identificador `get_reachable_true_values`; `domain/ports.py` y `environments/grid2d.py` sólo pueden **definirlo** (auditoría vigente de `tests/test_simulation_engine.py`).
4. `nullify_belief` vive en `ide.simulation.controls`, que `src/ide/agent/` no puede importar. Por eso **sólo el motor** aplica el control nulo de contenido, también a los canales de Fase II (herencia cultural, estigmergia y vista del holón), antes de entregar la creencia al agente.
5. Sin importaciones circulares: `micro_agent.py` importa `evolution.py`, y `evolution.py` no importa `micro_agent.py` (opera sobre `BoundedMemory`, `AgentGenome` y `SimulationConfig`).

### Decisión 21: Metabolismo Energético con Costo Cerebral y Sensorial Cuadrático ($R_{12}$)
Para impedir el "atajo evolutivo trivial" (que la selección natural incremente ilimitadamente $C_{\max, i} \to N$ o los radios $r_{\text{perc}}, r_{\text{com}}$ creando un súper-individuo omnisciente), el costo metabólico basal por tick es cuadrático en la capacidad de memoria y en los radios sensoriales/comunicativos del genoma:
$$c_{\text{base}}(i) = c_{\text{fijo}} + c_{\text{mem}} \cdot C_{\max, i}^2 + c_{\text{sens}} \cdot \left(r_{\text{perc}, i}^2 + r_{\text{com}, i}^2\right)$$
donde `metabolic_base_cost` ($c_{\text{fijo}} = 0.01$), `memory_capacity_cost` ($c_{\text{mem}} = 0.002$) y `sensory_radius_cost` ($c_{\text{sens}} = 0.0005$).
El balance energético del agente $i$ en el tick $t$ es:
$$E_i(t+1) = E_i(t) + \eta_E \cdot r_i(t) - c_{\text{base}}(i) - c_{\text{move}} \cdot \mathbb{I}(\text{mov}_i(t)) - c_{\text{msg}} \cdot m_i(t) - c_{\text{coord\_share}}(i, t)$$
donde:
- $\eta_E =$ `energy_gain_scale` ($0.45$ por defecto), y $r_i(t)$ es el valor real experimentado: `true_value` de un recurso elemental, `-composite_failure_penalty` en un intento compuesto fallido, o la fracción recibida de un recurso compuesto resuelto por su holón (D27).
- $\mathbb{I}(\text{mov}_i(t)) = 1$ si el agente ejecutó una acción `MOVE` válida en el tick $t$, $0$ en otro caso (`move_cost` $= 0.005$).
- $m_i(t)$ es la cantidad de mensajes emitidos por el agente $i$ en Fase 1 + Fase 2 (`message_cost` $= 0.001$).
- $c_{\text{coord\_share}}(i, t)$ es su alícuota del costo de coordinación de los holones a los que pertenece.

Las ganancias y penalizaciones por recursos se acreditan en la Fase 4; el costo de coordinación, en la Fase 5 (D24); el costo basal, de movimiento y de mensajes, al cobrar el metabolismo en la Fase 5. Si al cobrar el metabolismo resulta $E_i(t+1) \le 0$, el agente muere inmediatamente: es eliminado de `engine.agents`, de `env` (`remove_agents`) y podado de cualquier árbol `CompositeAgent` mediante `prune_dead_leaves`. No hay tope superior de energía.
Además, cuando se invoca `SimulationEngine._remove(victims)` (ya sea por muerte metabólica o por las perturbaciones `ablate_population` / `ablate_discoverers`), `_remove` DEBE podar `self.root_nodes` invocando `prune_dead_leaves` con los IDs sobrevivientes `set(self.agents)` y reconstruir el índice inverso `self.agent_to_root`.

### Decisión 22: Reproducción Diferencial, Fenotipo Espacial de Radios Mutados ($R_{13}$) y Herencia Cultural ($R_{14}$)
Ubicación de las funciones: `genome_from_config` y `transfer_cultural_heritage` en `src/ide/agent/evolution.py` (que no importa `micro_agent.py`); `mutate_genome` y `compute_epistemic_synergy` en `src/ide/domain/extensions.py` (que pasa a importar `ide.config`, sin ciclo porque `config.py` no importa nada de `ide`).
1. **Genoma inicial y sincronización con `MicroAgent` y `ToroidalGrid2D`:**
   - `genome_from_config(config: SimulationConfig) -> AgentGenome` construye el genoma fundador ($g=0$) tomando `alpha_learning`, `gamma_social_discount`, `epsilon_explore`, `initial_bond_affinity`, `memory_capacity`, `perception_radius` y `comm_radius`.
   - En `MicroAgent.__init__(self, agent_id, config, trust_strategy=None, protocol=None)`, el agente se inicializa con `self._genome = genome_from_config(config)`, `self._energy = config.initial_energy`, `self._generation = 0`, `self._parent_id = None`, y `self._config = config` (sin llamar a `replace`, de modo que `agent.config == config` sea idéntico en Fase I).
   - En `MicroAgent.from_lineage(cls, agent_id, config, genome, energy, generation, parent_id, trust_strategy=None, protocol=None) -> MicroAgent`, se deriva `agent_config = dataclasses.replace(config, alpha_learning=genome.alpha_learning, gamma_social_discount=genome.gamma_social_discount, epsilon_explore=genome.epsilon_explore, memory_capacity=genome.memory_capacity, perception_radius=genome.perception_radius, comm_radius=genome.comm_radius)` y se construye el `MicroAgent` con `agent_config`, asignando `_genome = genome`, `_energy = energy`, `_generation = generation` y `_parent_id = parent_id`.
   - **Fenotipo real de `perception_radius` y `comm_radius` en `ToroidalGrid2D`:** `ToroidalGrid2D` mantiene un diccionario opcional `self._agent_radii: dict[int, tuple[int, int]] = {}` y un caché de tablas de desplazamiento `self._offsets_cache: dict[int, tuple[tuple[int, int, int, Cell | None], ...]]`. Cuando `agent_id` no figura en `_agent_radii` (caso de todos los agentes en Fase I), `get_observation` y `get_communication_neighbors` usan directamente `self._perception_offsets` y `self._comm_offsets` precalculados sin sobrecosto. Cuando nace un agente con radios mutados, `spawn_agent_near` (o `set_agent_radii`) registra `(genome.perception_radius, genome.comm_radius)` en `self._agent_radii[agent_id]`, de modo que `get_observation` y `get_communication_neighbors` usen los desplazamientos correspondientes al radio individual de ese agente.
2. **Mutación (`mutate_genome` en `src/ide/domain/extensions.py`):**
   - Si `config.mutation_rate == 0.0` y `config.discrete_mutation_prob == 0.0`, devuelve `genome` intacto sin consumir `rng`.
   - Si `config.mutation_rate > 0.0`, extrae 4 valores normales `rng.normal(0.0, config.mutation_rate, size=4)` para $(\alpha, \gamma, \epsilon, \omega_{\text{bond}})$ y recorta $\alpha \in [0.01, 1.0]$ y $\gamma, \epsilon, \omega_{\text{bond}} \in [0.0, 1.0]$.
   - Si `config.discrete_mutation_prob > 0.0`, para cada rasgo entero $(C_{\max}, r_{\text{perc}}, r_{\text{com}})$ en ese orden extrae un `rng.random()`; si es menor que `discrete_mutation_prob`, extrae además `int(rng.integers(0, 2))`, suma `+1` si vale `1` o `-1` si vale `0`, y recorta al intervalo $[lo, hi]$ del rasgo (las dos extracciones se hacen siempre, aunque el recorte anule el salto, para que la secuencia del generador no dependa del valor del rasgo):
     - $C_{\max}$: $lo = 1$ y $hi = \text{config.max\_genome\_memory\_capacity}$, acotado además por $\text{config.num\_world\_patterns} - 1$ cuando `config.enforce_memory_constraint=True`.
     - $r_{\text{perc}}, r_{\text{com}}$: $lo = 1$ y $hi = (\min(\text{config.grid\_width}, \text{config.grid\_height}) - 1) // 2$, que es el mayor radio que admite la validación `2 * max(radios) < min(grilla)` de `SimulationConfig`. Si $hi < lo$, el rasgo no muta (conserva el valor parental) pero las extracciones se consumen igual.
   - La validación de `SimulationConfig` exige `max_genome_memory_capacity >= memory_capacity`, para que el genoma fundador esté dentro de sus cotas.
3. **Transferencia Cultural Vertical (`transfer_cultural_heritage(parent_memory, child_capacity, tick, config) -> tuple[KnowledgeUnit, ...]`):** es una función pura que **no escribe** en la memoria del hijo; sólo prepara los testimonios parentales.
   - Si `config.enable_cultural_inheritance` es `False` o `config.inheritance_discount == 0.0`, devuelve `()`.
   - Si no, ordena `parent_memory.all_units()` por `(-parent_memory.compute_utility(u, tick), u.pattern)`, toma hasta `child_capacity` unidades y, para cada una con `config.inheritance_discount * u.confidence >= config.min_confidence`, devuelve `replace(u, confidence=config.inheritance_discount * u.confidence)`.
   - **Entrega por la puerta única del conocimiento social.** El motor entrega cada testimonio, en el orden devuelto, con `child.assimilate_testimony(belief, sender_id=parent.agent_id, tick=tick)`. Antes, si `config.comm_content_null=True`, le aplica `nullify_belief(belief, self.null_rng)`. Como el hijo nace con memoria vacía, `merge_social_belief` aplica el Escenario A: la creencia heredada queda con confianza `γ · γ_gen · c` (γ = confianza en el emisor de `TrustStrategyPort`, por defecto `gamma_social_discount`), `evidence_count = 1`, `last_updated_tick = tick` y `from_direct_experience = False`. Así se respetan el invariante `evidence_count >= 1` y la regla de CLAUDE.md de que el conocimiento social sólo entra por `assimilate_testimony`.

### Decisión 23: Arquitectura Holónica Recursiva sin Límite de Niveles (`AgentNode`, `CompositeAgent` y Poda Recursiva)
En `src/ide/agent/holon.py` se implementa el patrón estructural *Composite*:

```python
@runtime_checkable
class AgentNode(Protocol):
    @property
    def node_id(self) -> int: ...
    @property
    def holon_level(self) -> int: ...
    @property
    def leaf_agents(self) -> tuple[MicroAgent, ...]: ...
    @property
    def effective_capacity(self) -> int: ...
    def collective_memory(self) -> dict[Pattern, KnowledgeUnit]: ...
```

`CompositeAgent` implementa `AgentNode` para cualquier nivel $L \ge 1$:
- **Atributos:**
  - `node_id: int` (identificador único asignado por un contador monótono decreciente `self.next_holon_id` del motor, que empieza en `-1`). Los holones usan IDs negativos y los `MicroAgent` sus `agent_id >= 0`, de modo que las claves de `root_nodes` nunca colisionan por más nacimientos que haya.
  - `children: tuple[AgentNode, ...]` (mínimo 2 hijos; pueden ser `MicroAgent` o `CompositeAgent` de cualquier nivel, permitiendo árboles de profundidad arbitraria $L = 1, 2, 3, \dots, K$).
  - `created_tick: int`.
  - `ticks_without_surplus: int = 0` (contador para evaluar `SPLIT`).
  - `cooperative_completions: int = 0`.
- **Propiedades derivadas recursivamente:**
  - `holon_level: int`: $1 + \max_{c \in \text{children}} c.\text{holon\_level}$.
  - `leaf_agents: tuple[MicroAgent, ...]`: concatenación ordenada por `agent_id` de las hojas de todos sus hijos (en `__init__` se verifica que no existan hojas repetidas entre hijos y que `len(children) >= 2`, lanzando `ValueError` en caso contrario).
  - `effective_capacity: int`: $\sum_{\ell \in \text{leaf\_agents}} \ell.\text{memory.capacity}$.
  - `total_energy: float`: $\sum_{\ell \in \text{leaf\_agents}} \ell.\text{energy}$.
  - `mean_bond_affinity: float`: media aritmética de `leaf.genome.bond_affinity` sobre sus hojas.
- **Memoria Colectiva (`collective_memory(allowed_leaf_ids: set[int] | None = None) -> dict[Pattern, KnowledgeUnit]`):**
  Recorre `self.leaf_agents` en orden de `agent_id` (filtrando por `leaf.agent_id in allowed_leaf_ids` si `allowed_leaf_ids` no es `None`) y para cada `unit` en `leaf.memory.all_units()` conserva para cada `Pattern` la `KnowledgeUnit` que maximiza `(unit.confidence, unit.last_updated_tick, -leaf.agent_id)`.
- **Poda Recursiva ante Muerte o Ablación de Hojas (`prune_dead_leaves(node: AgentNode, alive_ids: set[int]) -> AgentNode | None`):**
  - Si `node` es `MicroAgent`: devuelve `node` si `node.agent_id in alive_ids`, o `None` si fue eliminado.
  - Si `node` es `CompositeAgent`: poda recursivamente cada hijo $c \in \text{node.children}$ obteniendo `surviving = [p for c in node.children if (p := prune_dead_leaves(c, alive_ids)) is not None]`.
    - Si `len(surviving) == 0`, devuelve `None`.
    - Si `len(surviving) == 1`, el holón pierde su condición compuesta y colapsa devolviendo directamente `surviving[0]`.
    - Si `len(surviving) >= 2`, actualiza `node.children = tuple(surviving)` (recalculando hojas y nivel) y devuelve `node`.

**Firmas públicas de `src/ide/agent/evolution.py` y `src/ide/agent/holon.py`** (las nombra `tasks.md`; ninguna recibe el entorno, así que las distancias llegan ya calculadas por el motor):

```python
# evolution.py
def genome_from_config(config: SimulationConfig) -> AgentGenome: ...
def compute_metabolic_cost(genome: AgentGenome, config: SimulationConfig) -> float: ...  # c_base de D21
def transfer_cultural_heritage(
    parent_memory: BoundedMemory, child_capacity: int, tick: int, config: SimulationConfig
) -> tuple[KnowledgeUnit, ...]: ...

# micro_agent.py (métodos nuevos de MicroAgent)
def apply_energy_delta(self, delta: float) -> None: ...  # suma `delta` (negativo para costos) a `energy`

# holon.py
def prune_dead_leaves(node: AgentNode, alive_ids: set[int]) -> AgentNode | None: ...
def evaluate_bond_candidates(
    roots: Sequence[AgentNode], adjacent_pairs: Sequence[tuple[int, int]], config: SimulationConfig
) -> list[tuple[int, int]]: ...  # pares (node_id_a, node_id_b) elegidos por D24.3, en orden de selección
def should_split_holon(holon: CompositeAgent, config: SimulationConfig) -> bool: ...  # D24.2
def apply_downward_causation(
    holon: CompositeAgent, local_reach: Mapping[int, Sequence[int]], config: SimulationConfig
) -> None: ...  # D25.1; local_reach[aid] = hojas en alcance local de aid, ordenadas
def reproduce_holon(
    holon: CompositeAgent, offspring: Mapping[int, MicroAgent], node_id_source: Callable[[], int], tick: int
) -> CompositeAgent: ...  # replica el árbol sustituyendo cada hoja por offspring[hoja.agent_id]
```

### Decisión 24: Operadores Dinámicos de Fusión (`BOND`, $R_{15}$) y Fisión (`SPLIT`, $R_{16}$) con Localidad Espacial
El motor mantiene un registro de nodos raíz activos `self.root_nodes: dict[int, AgentNode]` (inicialmente cada `MicroAgent` es su propio nodo raíz con clave `agent_id`) y un mapa inverso `self.agent_to_root: dict[int, int]` que asocia cada `agent_id` de hoja con el `node_id` de su nodo raíz actual:
1. **Localidad Espacial Intra-Holón (`local_holon_leaves`):**
   - Para evitar "telepatía holónica" a través del toro, dos hojas $\ell_a, \ell_b$ de un mismo `CompositeAgent` $U$ están en alcance local en el tick $t$ si su distancia de Chebyshev toroidal `env.get_agent_distance(a, b)` es $\le \max(\ell_a.\text{genome.comm\_radius}, \ell_b.\text{genome.comm\_radius}) + 1$.
   - Cuando una hoja `aid` consulta la memoria colectiva de su holón raíz $U$ o intenta resolver un recurso compuesto en la Fase 4, sólo participan las hojas de $U$ en alcance local de `aid` (`local_ids = {l.agent_id for l in U.leaf_agents if env.get_agent_distance(aid, l.agent_id) <= max(aid_comm, l.genome.comm_radius) + 1}`).
2. **Costo de coordinación y `SPLIT` ($R_{16}$):**
   - Para cada `CompositeAgent` raíz $U$ (en orden ascendente de `node_id`):
     - Calcula $c_{\text{coord}}(U) = \text{config.holon\_coord\_cost} \cdot |U| \cdot L(U)$, donde $|U|$ = `len(U.leaf_agents)`, y, si `enable_evolution=True`, descuenta $c_{\text{coord}}(U) / |U|$ de la energía de cada hoja $\ell \in \text{leaves}(U)$. El costo se cobra sólo al holón raíz: los sub-holones no pagan aparte, porque el factor $L(U)$ ya pondera la profundidad.
     - **Superávit del tick.** El holón tuvo superávit en el tick $t$ si y sólo si (a) registró al menos una resolución compuesta exitosa en la Fase 4 de $t$, o (b) $|\mathcal{K}_{\text{loc}}(U)| > \max_{\ell} |\mathcal{K}(\ell)|$, donde $\mathcal{K}(\ell)$ son los patrones de la memoria de $\ell$ con `confidence >= decision_conf_threshold` y $\mathcal{K}_{\text{loc}}(U)$ es la unión de $\mathcal{K}(\ell)$ sobre la **componente conexa más grande** del grafo de alcance local entre las hojas de $U$ (arista si $\ell_a, \ell_b$ están en alcance local según el punto 1; desempate de componentes del mismo tamaño por menor `agent_id` mínimo). Con superávit, `U.ticks_without_surplus = 0`; sin superávit, `U.ticks_without_surplus += 1`.
     - Si `config.enable_holon_splitting` es `True` y (`U.ticks_without_surplus >= config.holon_split_patience` o `U.total_energy < len(U.leaf_agents) * config.holon_min_energy_per_leaf`), el holón $U$ se disuelve: se elimina `U.node_id` de `root_nodes` y cada hijo directo $c \in U.\text{children}$ pasa a ser un nodo raíz en `root_nodes[c.node_id] = c` (preservando sub-holones intermedios si $L(U) \ge 2$).
3. **Evaluación de `BOND` ($R_{15}$):**
   - Dos nodos raíz $U_a, U_b$ ($a < b$) son candidatos a fusionarse en el tick $t$ si:
     - `len(U_a.leaf_agents) + len(U_b.leaf_agents) <= config.max_holon_leaves`.
     - Al menos una hoja de $U_a$ y una hoja de $U_b$ están a distancia de Chebyshev toroidal $\le 1$ (`env.get_agent_distance(la, lb) <= 1`).
   - Su puntaje de sinergia es:
     $$\text{score}(U_a, U_b) = \mathcal{S}_{\text{comp}}(\mathcal{K}_a, \mathcal{K}_b) \cdot \frac{\bar{\omega}_{\text{bond}}(U_a) + \bar{\omega}_{\text{bond}}(U_b)}{2}$$
     donde $\mathcal{K}_a, \mathcal{K}_b$ son los patrones con `confidence >= config.decision_conf_threshold` en las memorias colectivas de $U_a$ y $U_b$, y $\mathcal{S}_{\text{comp}}(\mathcal{K}_a, \mathcal{K}_b) = |\mathcal{K}_a \triangle \mathcal{K}_b| / |\mathcal{K}_a \cup \mathcal{K}_b|$ (o `0.0` si $\mathcal{K}_a \cup \mathcal{K}_b = \emptyset$).
   - Los pares candidatos con `score >= config.holon_bond_threshold` se ordenan por `(-score, a, b)` y se fusionan codiciosamente (*greedy matching* sin solapamiento en el mismo tick): cada par seleccionado $(U_a, U_b)$ se retira de `root_nodes` y es reemplazado por un nuevo `CompositeAgent(node_id=next_holon_id, children=(U_a, U_b), created_tick=tick)`.

### Decisión 25: Causalidad Descendente Intra-Holón ($R_{18}$) y Sincronización Efímera en Dos Tiempos (Fase 1 y Fase 2)
Cuando dos o más agentes forman parte de un mismo `CompositeAgent` raíz $U$:
1. **Particionamiento Epigenético de Memoria (`apply_downward_causation`):**
   - Si `config.enable_downward_causation` es `True`, para cada `CompositeAgent` raíz $U$:
     - La regulación es **local**, con el mismo criterio de alcance que la memoria compartida (D24, punto 1). Para cada hoja $\ell \in \text{leaves}(U)$, sea $\text{loc}(\ell)$ el conjunto de hojas de $U$ en alcance local de $\ell$ (incluida $\ell$). Para cada patrón $\rho$ de la memoria de $\ell$, la "especialista titular" local es $\ell^*(\rho) = \arg\max_{\ell' \in \text{loc}(\ell),\ \rho \in \mathcal{M}_{\ell'}} (c_{\ell'}(\rho), -\ell'.\text{agent\_id})$.
     - El conjunto de patrones redundantes de $\ell$ es $\{\rho \in \mathcal{M}_\ell \mid \ell \neq \ell^*(\rho)\}$ (en empate de confianza conserva el patrón la hoja de menor `agent_id`), y se invoca `leaf.memory.set_redundant_patterns(redundant, config.redundancy_penalty)`.
     - La penalización afecta a todo uso de `compute_utility`: desalojo, orden de difusión de `BROADCAST_BELIEF` y orden de la herencia cultural. Es un efecto declarado de $R_{18}$.
     - Para los `MicroAgent` que no pertenecen a ningún holón (o cuando `enable_downward_causation=False`), `leaf.memory.set_redundant_patterns(frozenset(), 1.0)`.
2. **Sincronización Efímera en Dos Tiempos (`inject_ephemeral_belief` sobre `_holon_tick_beliefs`) sin Desperdiciar Consultas en Fase 1 y Verdad Efectiva en Fase 3:**
   - > **Decisión abierta P1 (canal de conocimiento del holón).** La vista compartida del holón es un canal de conocimiento social que **no** pasa por `assimilate_testimony`, en contra del invariante vigente de CLAUDE.md y de `openspec/specs/micro-agent/spec.md`. No se implementa hasta que se elija entre: (a) declararlo como canal efímero excepcional, con regla propia y ablación; o (b) reemplazarlo por mensajes ordinarios entre miembros del holón. El texto siguiente describe la variante (a). Las opciones están en el reporte de revisión que acompaña a este cambio.
   - Como `MicroAgent.perceive_and_emit_messages(obs, tick)` vacía `self._ephemeral_tick_beliefs` al empezar (`micro_agent.py:80`; lo verifica por comportamiento `test_creencia_solo_en_cache_vive_un_tick`), `MicroAgent` mantiene un segundo diccionario efímero `self._holon_tick_beliefs: dict[Pattern, KnowledgeUnit] = {}`, con los métodos `clear_holon_beliefs(self) -> None` e `inject_ephemeral_belief(self, unit: KnowledgeUnit) -> None` (que escribe `self._holon_tick_beliefs[unit.pattern] = unit`).
   - **Separación entre creencia propia y vista del holón.** `get_effective_belief(pattern)` sigue el orden memoria → caché efímero propio → vista del holón, y sólo la usan la decisión (`decide_action`) y el protocolo de emisión. `learn_from_experience` y `assimilate_testimony` parten de un nuevo método público `own_belief(pattern)` (memoria → caché efímero propio, exactamente la `get_effective_belief` de Fase I), para que la experiencia directa y los testimonios nunca se fusionen con la creencia de un compañero. Con `_holon_tick_beliefs` vacío, ambos métodos coinciden bit a bit con Fase I. Es una modificación del requisito "Creencia Efectiva y Caché Efímero" de `micro-agent` y se declara como `MODIFIED` en el spec delta.
   - **Tiempo 1 (En Fase 1, antes de `perceive_and_emit_messages`):** En `SimulationEngine.step()`, cuando `enable_holonic_hierarchy=True` o `num_composite_patterns > 0`, se ejecuta `_sync_holon_and_composite_beliefs(aid, tick)`:
     - Llama a `agent.clear_holon_beliefs()`.
     - Si `aid` pertenece a un `CompositeAgent` raíz $U$, inyecta vía `inject_ephemeral_belief` las creencias de las hojas localmente conectadas de $U$ (aplicando `nullify_belief` con `self.null_rng` si `config.comm_content_null=True`).
     - > **Decisión abierta P2 (cómo conoce el agente un recurso compuesto).** En la variante descrita aquí, el motor lee la estructura verdadera de las reglas en `env.get_composite_rules()` y le inyecta al agente el patrón compuesto "desbloqueado". Funciona como un oráculo parcial, similar al que CLAUDE.md prohíbe para `true_value`. La alternativa es que el agente aprenda el valor del patrón compuesto por experiencia, como cualquier otro patrón. No se implementa hasta elegir.
     - Si existen reglas en `env.get_composite_rules()`, para cada `(comp_pattern, rule)` cuyos `required_patterns` sean todos conocidos como benéficos (`predicted_value > 0` y `confidence >= config.decision_conf_threshold`) por `get_effective_belief` de `aid` (que ya incluye las del holón local), inyecta `KnowledgeUnit(pattern=comp_pattern, predicted_value=1.0, confidence=min_conf, evidence_count=1, last_updated_tick=tick, from_direct_experience=False)`, con `min_conf` la menor confianza de los fragmentos requeridos. `predicted_value` vale `1.0`, y no `rule.composite_value`, porque las creencias viven en $\hat{v} \in [-1, 1]$; la recompensa superlineal sólo se refleja en la energía (D27). Así, en la Fase 1 `BeliefExchangeProtocol.emit` reconoce `comp_pattern` y los patrones del holón como conocidos y **no desperdicia `QUERY_PATTERN` sobre ellos**, sin que `self._ephemeral_tick_beliefs.clear()` los borre.
   - **Tiempo 2 (al final de la Fase 2, tras asimilar respuestas de vecinos y antes de la Fase 3 de decisión):** Si `num_composite_patterns > 0` o `enable_holonic_hierarchy=True`, se vuelve a invocar `_sync_holon_and_composite_beliefs(aid, tick)` para que cualquier fragmento aprendido socialmente en la Fase 2 habilite de inmediato la decisión sobre recursos compuestos en la Fase 3. Para no introducir efectos de orden, primero se calcula la vista de **todos** los agentes, leyendo las memorias tal como quedaron al terminar la Fase 2 de toda la población, y recién después se inyecta, en un bucle separado y en orden de `agent_id`. Lo mismo vale para el Tiempo 1.
   - **M2 sobre recursos compuestos.** Para que M2 siga siendo objetiva (la verdad no puede depender de lo que cree el agente juzgado), los recursos compuestos **no entran** en el `truth` de `judge_decision`. M2 se calcula sólo sobre recursos elementales, exactamente como en Fase I: el motor filtra de `get_reachable_true_values(aid)` los recursos compuestos; si el resultado queda vacío, o si la acción de `aid` es `INTERACT` sobre un recurso compuesto, ese agente no suma oportunidad de decisión en el tick. El desempeño sobre compuestos se mide con M12 (`composite_completions`). Esta elección está ligada a la decisión abierta P2 y puede revisarse con ella.

### Decisión 26: Endosimbiosis Reproductiva Holónica ($R_{17}$) y Límite de Un Evento Reproductivo por Tick
En la Fase 5, cuando `config.enable_evolution` es `True`:
- El motor lleva un contador monótono `self.next_agent_id: int` inicializado en `max(env.get_active_agent_ids()) + 1` (o `0` si no hay agentes), porque el motor admite entornos externos cuyos IDs no son necesariamente `0 .. num_agents - 1`.
- `MicroAgent.create_offspring(self, child_id: int, tick: int, rng: np.random.Generator) -> MicroAgent` hace sólo lo que es del agente: parte la energía (`offspring_energy_share`), muta el genoma con `mutate_genome(self.genome, self.config, rng)` y construye el hijo con `MicroAgent.from_lineage`. **No** transfiere creencias: la herencia cultural la entrega después el motor con `transfer_cultural_heritage` y `assimilate_testimony` (D22, punto 3), en el mismo tick y antes de procesar al siguiente progenitor.
- En cada tick se instancia un conjunto `reproduced_this_tick: set[int] = set()` para garantizar que **ningún `MicroAgent` pueda reproducirse más de una vez en el mismo tick** (ni engendrar como parte de un holón y luego volver a engendrar individualmente):
  - **Caso 1: `node` es un `CompositeAgent` en `sorted(self.root_nodes)` y `config.enable_holon_reproduction` es `True`:**
    - Si ninguna hoja de `node` está en `reproduced_this_tick`, `node.total_energy >= len(node.leaf_agents) * config.reproduction_threshold` y `len(self.agents) + len(node.leaf_agents) <= config.max_population`:
      - Se invoca `reproduce_holon(node, ...)`, donde cada hoja $\ell \in \text{node.leaf\_agents}$ (en orden de `agent_id`) engendra su hoja hija $\ell'$ mediante `ell.create_offspring(next_agent_id, tick, evo_rng)`, ubicada en el entorno con `env.spawn_agent_near(ell'.agent_id, ell.agent_id, evo_rng, ell'.genome.perception_radius, ell'.genome.comm_radius)`, se añade `ell.agent_id` (y `ell'.agent_id`) a `reproduced_this_tick`, y se replica la topología arbórea en un nuevo `CompositeAgent` raíz $U_{\text{hijo}}$.
  - **Caso 2: Reproducción individual de hojas (`MicroAgent`, $R_{12}$):**
    - Para cada `aid` en `sorted(self.agents)` que **no** pertenezca a `reproduced_this_tick`, si `agent.energy >= config.reproduction_threshold` y `len(self.agents) < config.max_population`:
      - Engendra un `MicroAgent` hijo con `child_id = self.next_agent_id` (`self.next_agent_id += 1`), lo ubica con `env.spawn_agent_near(child.agent_id, aid, evo_rng, child.genome.perception_radius, child.genome.comm_radius)`, lo registra como nodo raíz de nivel 0 en `self.root_nodes` y añade `aid` y `child.agent_id` a `reproduced_this_tick`.

### Decisión 27: Inserción Espacial Exacta, Recursos Compuestos y Estigmergia ($R_{19}$) en `ToroidalGrid2D`
1. **Algoritmo Exacto de `spawn_agent_near`:**
   - Dada la celda `(ax, ay) = self._agent_cell[anchor_agent_id]`, construye la lista ordenada de las 9 celdas candidatas:
     `offsets = ((0, 0), *self.MOORE_MOVES)`
     `candidates = [((ax + dx) % self._width, (ay + dy) % self._height) for dx, dy in offsets]`
   - Calcula la ocupación mínima `min_occ = min(len(self.cell_agents[c]) for c in candidates)` y filtra `best = [c for c in candidates if len(self.cell_agents[c]) == min_occ]`.
   - Selecciona la celda destino con una única extracción entera: `chosen = best[int(rng.integers(len(best)))]`.
   - Registra `self._agent_cell[agent_id] = chosen`, `self.cell_agents[chosen].add(agent_id)`, y si `perception_radius` o `comm_radius` difieren de los globales de `self.config`, guarda `(perception_radius, comm_radius)` en `self._agent_radii[agent_id]`. Devuelve `chosen`.
2. **Recursos Compuestos (`CompositeRule`):**
   - Si `num_composite_patterns > 0`, `ToroidalGrid2D` crea un generador dedicado `self._comp_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(config.seed, spawn_key=(3,))))` para no tocar `self._rng` de Fase I.
   - Sea `beneficial = [Pattern((("id", f"p_{i}"),)) for i in range(config.num_world_patterns // 2)]`.
   - Para cada $k \in \{0, \dots, \text{num\_composite\_patterns} - 1\}$:
     - El patrón compuesto es `comp_pat = Pattern((("id", f"c_{k}"), ("order", str(m))))` donde $m = \text{config.composite\_order}$.
     - Los patrones requeridos se eligen cíclicamente y se ordenan:
       `req = tuple(sorted(beneficial[(k + j) % len(beneficial)] for j in range(m)))`
     - El valor compuesto es `val = float(m ** config.composite_reward_exponent)`.
     - Se guarda `self._composite_rules[comp_pat] = CompositeRule(req, val)` y se generan `config.composite_resources_per_pattern` instancias de `Resource(resource_id, comp_pat, val)` en celdas sorteadas con `self._comp_rng` (y cuando se consumen, se encolan en `self._pending_composite` y se reponen en `step_dynamics` usando `self._comp_rng`).
   - **Semántica exacta de interacción en Fase 4:**
     - Cuando `aid` ejecuta `INTERACT` sobre un recurso en su celda cuyo patrón `comp_pat` pertenece a `env.get_composite_rules()`:
       - `env.execute_action` consume el recurso físico (y lo encola en `_pending_composite` para reposición en `step_dynamics`) devolviendo `ActionResult(ActionType.INTERACT, comp_pat, rule.composite_value)`.
       - En Fase 4, el motor intercepta `result.interacted_pattern in composite_rules`:
         - Sea $\mathcal{K}_{\text{eff}}$ el conjunto de patrones $\rho$ para los que alguna hoja $\ell$ en alcance local de `aid` dentro de su nodo raíz $U$ (o sólo `aid`, si no pertenece a un holón) tiene `ell.own_belief(ρ)` con `predicted_value > 0` y `confidence >= decision_conf_threshold`. `own_belief` incluye el caché efímero propio, así que cuenta lo que cada hoja obtuvo de sus vecinos en ese tick, igual que en la Fase 3. El motor verifica si `rule.evaluate(K_eff) is not None`.
         - **Si tiene éxito:** incrementa `self.composite_completions += 1`; si $U$ es `CompositeAgent`, incrementa `U.cooperative_completions += 1` y reinicia `U.ticks_without_surplus = 0`; y si `enable_evolution=True`, reparte la ganancia energética `config.energy_gain_scale * rule.composite_value` en partes iguales entre las hojas localmente conectadas de $U$. (No se inserta `comp_pat` en `BoundedMemory` individual ni se añade `aid` a `self.direct_discoverers`, ya que `direct_discoverers` rastrea exclusivamente patrones elementales `p_0 .. p_{P-1}`).
         - **Si fracasa:** el agente `aid` recibe la penalización energética `-config.composite_failure_penalty` (si `enable_evolution=True`) y no registra éxito compuesto.
3. **Estigmergia Espacial ($R_{19}$) y Conversión Exacta a `KnowledgeUnit`:**
   - `ToroidalGrid2D` mantiene `self.cell_stigmergy: dict[Cell, dict[Pattern, StigmergicTrace]]`.
   - En Fase 4, tras una experiencia directa con un patrón elemental $\rho$ de valor real $v$, si `config.enable_stigmergy=True` y `config.stigmergy_deposit_rate > 0`, el motor invoca `env.deposit_stigmergy(aid, pattern, value, confidence, tick)` que deposita en la celda actual del agente un `StigmergicTrace(pattern, float(np.sign(value)), min(1.0, config.stigmergy_deposit_rate * confidence), tick)`. Si la celda ya tiene un rastro de ese patrón, se conserva el de mayor `(intensity, last_updated_tick, sign_value)`. Esta regla es independiente del orden de la permutación de la Fase 4, de modo que dos depósitos en el mismo tick dan el mismo resultado en cualquier orden. `confidence` es la de la creencia del agente tras `learn_from_experience`.
   - En Fase 1, si `config.enable_stigmergy=True`, para cada `trace` en `env.get_cell_stigmergy(aid)` se construye:
     `trace_unit = KnowledgeUnit(pattern=trace.pattern, predicted_value=trace.sign_value, confidence=trace.intensity, evidence_count=1, last_updated_tick=trace.last_updated_tick, from_direct_experience=False)`
     (si `config.comm_content_null=True`, se pasa por `nullify_belief(trace_unit, self.null_rng)`) y se asimila invocando `self.agents[aid].assimilate_testimony(trace_unit, sender_id=-1, tick=tick)`.
   - En `step_dynamics(tick)`, cada rastro con `last_updated_tick < tick` reduce su `intensity` en `config.stigmergy_decay` y se elimina si `intensity < config.min_confidence`.

### Decisión 28: Telemetría de Fase II (`EvolutionaryTickMetrics`), Fórmulas Exactas de M8–M12 y Esquemas de Reportes (`002` y `003`)
En `src/ide/experiments/metrics.py` se define:

```python
@dataclass(frozen=True)
class EvolutionaryTickMetrics:
    tick: int
    active_agents: int
    mean_generation: float  # M8
    max_generation: int  # M8
    births_this_tick: int  # M8
    deaths_this_tick: int  # M8
    mean_energy: float  # M8
    inherited_coverage_ratio: float  # M9
    holon_count_by_level: tuple[tuple[int, int], ...]  # M10: pares (L, conteo) para L >= 1, ordenados por L
    max_holon_level: int  # M10
    mean_holon_size: float  # M10 (0.0 si no hay holones L >= 1)
    holonic_coverage_gain: float  # M11 (1.0 si no hay holones L >= 1)
    composite_completions: int  # M12 (acumulado de recursos compuestos resueltos)
    stigmergy_active_cells: int
```

**Fórmulas exactas para casos borde en `EvolutionaryMetricsCollector`:**
- **`mean_generation`, `max_generation`, `mean_energy` (M8):** Si `active_agents == 0`, valen `0.0`, `0` y `0.0` respectivamente.
- **`inherited_coverage_ratio` (M9):** Sobre los agentes activos con `generation >= 1`, sea $V_{\text{total}}$ el número total de creencias válidas en `BoundedMemory` y $V_{\text{social}}$ aquellas con `from_direct_experience == False`. Si $V_{\text{total}} == 0$, vale `0.0`; de lo contrario, `V_social / V_total`.
- **`holon_count_by_level`, `max_holon_level`, `mean_holon_size` (M10):** Recorriendo todos los nodos `CompositeAgent` activos ($L \ge 1$) del bosque holónico, cuenta cuántos hay en cada nivel $L$ (como tupla de pares `(L, conteo)` ordenada por $L$, para que el dataclass congelado sea realmente inmutable y hasheable), el máximo $L$ (o `0` si no hay `CompositeAgent`) y el tamaño medio en hojas $|\text{leaf\_agents}|$ de los `CompositeAgent` raíz (o `0.0` si no hay ninguno).
- **`holonic_coverage_gain` (M11):** Para cada `CompositeAgent` raíz $U$, sea $|\mathcal{K}(U)|$ la cantidad de patrones válidos en `U.collective_memory()` y sea $\overline{|\mathcal{K}_{\text{leaf}}(U)|}$ el promedio de patrones válidos en la memoria individual de sus hojas. La razón de ganancia de $U$ es $|\mathcal{K}(U)| / \overline{|\mathcal{K}_{\text{leaf}}(U)|}$ si $\overline{|\mathcal{K}_{\text{leaf}}(U)|} > 0$, o `1.0` en caso contrario. `holonic_coverage_gain` es la media sobre todos los `CompositeAgent` raíz activos (o `1.0` si no existe ninguno).
- **`cultural_convergence_tick` y `tabula_rasa_convergence_tick` en `CulturalInheritanceReport` (`002-B`):** Se define exactamente como el menor `m.tick` en `engine.history` tal que `m.decision_opportunities > 0` y `m.cumulative_decision_accuracy >= 0.70` (o `None` si ningún tick de la corrida alcanza ese umbral).

En `src/ide/experiments/exp002_runner.py` se definen los reportes inmutables:

```python
@dataclass(frozen=True)
class AdaptationReport:
    seed: int
    total_ticks: int
    evolved_accuracy: float
    frozen_genome_accuracy: float
    adaptation_gain: float  # evolved_accuracy - frozen_genome_accuracy
    evolved_max_generation: int
    evolved_mean_energy: float
    total_births: int
    total_deaths: int

@dataclass(frozen=True)
class CulturalInheritanceReport:
    seed: int
    total_ticks: int
    cultural_accuracy: float
    tabula_rasa_accuracy: float
    cultural_accuracy_surplus: float  # cultural_accuracy - tabula_rasa_accuracy
    final_inherited_coverage_ratio: float
    cultural_convergence_tick: int | None
    tabula_rasa_convergence_tick: int | None
```

En `src/ide/experiments/exp003_runner.py` se definen los reportes inmutables:

```python
@dataclass(frozen=True)
class HolonicTransitionReport:
    seed: int
    total_ticks: int
    holonic_composite_completions: int
    individual_composite_completions: int
    composite_completion_surplus: float  # float(holonic - individual)
    holonic_accuracy: float
    individual_accuracy: float
    holonic_surplus: float  # holonic_accuracy - individual_accuracy
    max_holon_level: int
    peak_holonic_coverage_gain: float

@dataclass(frozen=True)
class MultilevelScalingReport:
    seed: int
    total_ticks: int
    downward_causation_coverage_gain: float
    unmodulated_coverage_gain: float
    orthogonalization_advantage: float  # downward_causation_coverage_gain - unmodulated_coverage_gain
    max_holon_level: int
    level_counts_peak: tuple[tuple[int, int], ...]  # pares (L, conteo) ordenados por L
```

### Decisión 29: Extensión del Marco de Atribución (`R12`–`R19` y `C5`–`C8`) y Semántica de Variantes E2/E4 en Fase II
En `src/ide/experiments/attribution.py`:
- `DESIGN_RULES` permanece intacto con las 11 reglas `R1`..`R11` para preservar todos los tests de `tests/test_attribution.py`.
- Se define `PHASE2_DESIGN_RULES: tuple[DesignRule, ...]`. Cada `DesignRule` lleva sus cuatro campos (`rule_id`, `name`, `purpose`, `ablation`); `test_attribution.py` exige `purpose` no vacío:

| Regla | `name` | `purpose` (capacidad que se diseñó para producir) | `ablation` |
| :--- | :--- | :--- | :--- |
| `R12` | Reproducción diferencial por umbral energético | Que los agentes con más energía dejen más descendencia (selección). | `(("reproduction_threshold", 1e9),)` |
| `R13` | Mutación genética acotada | Variación heredable sobre la que actúa la selección. | `(("mutation_rate", 0.0), ("discrete_mutation_prob", 0.0))` |
| `R14` | Herencia cultural vertical | Transmitir conocimiento de padres a hijos. | `(("enable_cultural_inheritance", False), ("inheritance_discount", 0.0))` |
| `R15` | Fusión holónica (BOND) | Asociar nodos complementarios en unidades de nivel superior. | `(("enable_holonic_hierarchy", False),)` |
| `R16` | Fisión holónica (SPLIT) | Disolver holones sin superávit. | `(("enable_holon_splitting", False),)` |
| `R17` | Reproducción de holón completo | Transmitir la estructura simbiótica a la descendencia. | `(("enable_holon_reproduction", False),)` |
| `R18` | Causalidad descendente intra-holón | Reducir la redundancia de memoria entre hojas de un holón (ortogonalización). | `(("enable_downward_causation", False), ("redundancy_penalty", 1.0))` |
| `R19` | Estigmergia | Externalizar conocimiento en el entorno. | `(("enable_stigmergy", False), ("stigmergy_deposit_rate", 0.0))` |

  > **Pendiente de aprobación (decisión abierta P3).** El inventario de reglas, las afirmaciones C5–C8 y sus variantes de comparación son **pre-registro**. Lo que sigue es la propuesta original. Hay que revisarla antes de versionarla, porque en su forma actual C7 y C8 pueden quedar clasificadas como emergentes cuando una regla diseñada las persigue. Las opciones están en el reporte de revisión. Tampoco hay todavía reglas para mecanismos diseñados como el metabolismo y la muerte, el costo de coordinación, el pozo de energía compartido y la vista compartida del holón (P1).
- Se define `ALL_DESIGN_RULES: tuple[DesignRule, ...] = DESIGN_RULES + PHASE2_DESIGN_RULES`, y `ablate()` busca en `_ALL_RULES_BY_ID = {r.rule_id: r for r in ALL_DESIGN_RULES}`.
- **Regla de compatibilidad con `test_001d_con_pocas_semillas` y semántica de `isolated`/`null_content`:**
  - La firma actual es `run_protocol_001d_attribution(config, seeds, claims=EXP001_CLAIMS, jobs=1)` y devuelve `AttributionReport(..., DESIGN_RULES, ...)` fijo. Se extiende a `run_protocol_001d_attribution(config, seeds, claims=EXP001_CLAIMS, jobs=1, rules=None)`. Si `rules is None`, se selecciona `DESIGN_RULES` cuando todas las afirmaciones pertenecen a `EXP001_CLAIMS`, y `ALL_DESIGN_RULES` cuando se evalúan afirmaciones de Fase II. `AttributionReport.rules` es la tupla seleccionada. Así se siguen cumpliendo exactamente `report.rules == DESIGN_RULES` y `list(evaluation.rule_effects) == [f"R{i}" for i in range(3, 12)]` en los tests de Fase I.
  - Para las afirmaciones de Fase I (`C1`–`C4`), `_variants` mantiene exactamente `isolated = replace(config, comm_enabled=False)` y `null_content = replace(config, comm_content_null=True)`.
  - Para las afirmaciones de Fase II (`C5`–`C8`), `isolated` desactiva además los canales colectivos de Fase II (`comm_enabled=False`, `enable_cultural_inheritance=False`, `enable_holonic_hierarchy=False`, `enable_stigmergy=False`) y `null_content` (`comm_content_null=True`) aplica `nullify_belief(..., self.null_rng)` tanto al ruteo horizontal como a la herencia cultural vertical ($R_{14}$), la estigmergia ($R_{19}$) y la compartición holónica ($R_{15}$).
- Se pre-registran las afirmaciones de Fase II:
  - `EXP002_CLAIMS: tuple[EmergenceClaim, ...]`:
    - `C5`: `EmergenceClaim("C5", "Aceleración cultural intergeneracional", "002b", "cultural_accuracy", True, ("R14",))`
    - `C6`: `EmergenceClaim("C6", "Adaptación evolutiva de linajes", "002a", "evolved_accuracy", True, ("R12", "R13"))`
  - `EXP003_CLAIMS: tuple[EmergenceClaim, ...]`:
    - `C7`: `EmergenceClaim("C7", "Superávit cooperativo sobre recursos compuestos", "003a", "holonic_composite_completions", True, ("R15", "R17"))`
    - `C8`: `EmergenceClaim("C8", "Ortogonalización espontánea intra-holón", "003b", "downward_causation_coverage_gain", True, ("R18",))`
- Se extiende `_protocol_result` en `attribution.py` para soportar los protocolos `"002a"`, `"002b"`, `"003a"` y `"003b"` usando `total_ticks = profile.total_ticks`.

---

## Arquitectura de Módulos y Árbol de Archivos

```text
src/ide/
├── config.py                     # MODIFICADO: Banderas e hiperparámetros de Fase II (defaults=False)
├── domain/
│   ├── types.py                  # MODIFICADO: +AgentGenome, +StigmergicTrace, +HolonSnapshot
│   ├── ports.py                  # MODIFICADO: +EvolutionaryEnvironmentPort (EnvironmentPort intacto)
│   └── extensions.py             # MODIFICADO: +mutate_genome, +compute_epistemic_synergy (CompositeRule ya existe)
├── agent/
│   ├── memory.py                 # MODIFICADO: +set_redundant_patterns y penalización ψ_red (R18)
│   ├── micro_agent.py            # MODIFICADO: +AgentNode L=0, energy, generation, genome, create_offspring, own_belief
│   ├── evolution.py              # NUEVO: genome_from_config, compute_metabolic_cost, transfer_cultural_heritage (no importa micro_agent)
│   └── holon.py                  # NUEVO: AgentNode Protocol, CompositeAgent recursivo, BOND, SPLIT, R17, R18
├── environments/
│   └── grid2d.py                 # MODIFICADO: +spawn_agent_near, +CompositeRule, +StigmergicTrace (R19)
├── simulation/
│   └── engine.py                 # MODIFICADO: +evo_rng, resolución compuesta Fase 4, ciclo Fase 5
└── experiments/
    ├── metrics.py                # MODIFICADO: +EvolutionaryTickMetrics (M8-M12), +EvolutionaryMetricsCollector
    ├── attribution.py            # MODIFICADO: +PHASE2_DESIGN_RULES (R12-R19), +EXP002_CLAIMS, +EXP003_CLAIMS
    ├── exp002_runner.py          # NUEVO: Protocolos 002-A y 002-B + CLI
    └── exp003_runner.py          # NUEVO: Protocolos 003-A y 003-B + CLI
```

---

## Risks / Trade-offs

- **Riesgo 1: Alterar accidentalmente el estado de `engine.rng` o `repr(TickMetrics)` y romper `tests/test_performance_equivalence.py`.**
  - *Mitigación:* Uso exclusivo de `evo_rng` (`spawn_key=(2,)`) y `_comp_rng` (`spawn_key=(3,)`) para todo muestreo nuevo, guardas booleanas estrictas cuando las flags de Fase II son `False`, y separación entre `TickMetrics` (14 campos fijos) y `EvolutionaryTickMetrics`.
- **Riesgo 2: Violar las auditorías AST de `tests/test_micro_agent.py` al añadir `evolution.py` y `holon.py` en `src/ide/agent/`.**
  - *Mitigación:* `evolution.py` sólo importa `ide.domain`, `ide.config`, `ide.agent.memory`, `numpy` y la biblioteca estándar (no importa `micro_agent.py`, para evitar el ciclo). `holon.py` puede importar además `ide.agent.micro_agent`. Ninguno referencia `Message`, `MessageType`, `merge_social_belief` ni `nullify_belief`, ni usa alias `import ... as ...` sobre nombres vigilados.
- **Riesgo 3: Explosión poblacional o extinción prematura bajo `enable_evolution=True`.**
  - *Mitigación:* Cota dura `max_population` ($N_{\max} = 160$ por defecto). Los hiperparámetros metabólicos de los protocolos 002 y 003 se fijan en el perfil pre-registrado **antes** de mirar resultados (P3). Si con ellos la población se extingue o explota, eso se reporta como resultado; no se recalibran a la vista de las afirmaciones.

---

## Definition of Done (Checklist de Cierre de Fase II)

- [ ] `ruff check` termina con 0 errores.
- [ ] `ruff format --check` termina con 0 diferencias.
- [ ] `pyright` termina con `0 errors, 0 warnings`.
- [ ] `python -m pytest --cov=ide` pasa en verde: los tests de Fase I más los nuevos de Fase II, incluido `tests/test_performance_equivalence.py` sin cambiar ningún hash dorado. Pasa también con otro `PYTHONHASHSEED`, igual que en CI.
- [ ] `python -m pytest -m slow` pasa en verde.
- [ ] Cobertura de código $\ge 90\%$ en `src/ide`.
- [ ] `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict` pasa sin advertencias.
- [ ] El pre-registro de Fase II (`PHASE2_DESIGN_RULES`, `EXP002_CLAIMS`, `EXP003_CLAIMS` y el perfil de corrida) está commiteado antes del primer commit de los runners 002 y 003.
- [ ] `/code-review` sin hallazgos accionables pendientes en cada bloque, según CLAUDE.md.
