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
- Introducir Recursos Compuestos Graduados (`CompositeRule` de orden $m \ge 2$) en `ToroidalGrid2D`, las métricas `M8` a `M13` en `EvolutionaryTickMetrics`, las reglas `R12`–`R23` y afirmaciones `C5`–`C8` en `attribution.py`, y los ejecutores `exp002_runner.py` y `exp003_runner.py`.
- Garantizar compatibilidad regresiva bit a bit con la Fase I cuando los mecanismos de Fase II están en su valor por defecto (inactivos).

**Non-Goals:**
- No se introducen redes neuronales profundas ni optimizadores por gradiente global.
- No se rompe ninguno de los 397 tests existentes de Fase I. Los archivos de test existentes pueden **ampliarse** con tests nuevos, pero los tests de Fase I no se modifican.
- No se altera la representación de `TickMetrics` ni la secuencia de `engine.rng` bajo las configuraciones de Fase I.

---

## Decisions (Numeradas D19 a D29, continuando D1–D18 de Fase I)

### Decisión 19: Aislamiento de Generadores Pseudoaleatorios (`evo_rng`) y Preservación de Hashes Dorados
Para garantizar que los 6 hashes SHA-256 de `tests/test_performance_equivalence.py` permanezcan intactos:
1. Todas las banderas de **activación** de Fase II en `SimulationConfig` tienen valor por defecto `False` y `num_composite_patterns` vale `0`. Las únicas banderas con valor `True` son `enable_holon_splitting`, `enable_holon_view` y `holon_energy_sharing`, que sólo modulan a `enable_holonic_hierarchy` y no tienen efecto mientras ésta sea `False`.
2. `SimulationEngine.__init__` instancia un generador dedicado `self.evo_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(config.seed, spawn_key=(2,))))`.
3. Toda operación estocástica nueva de Fase II usa un generador derivado de la semilla con `SeedSequence(seed, spawn_key=(k,))`, nunca `engine.rng`:
   - `spawn_key=(1,)`: `null_rng`, el control nulo de contenido (ya existe en Fase I).
   - `spawn_key=(2,)`: `evo_rng` del motor, para la mutación genética (`mutate_genome`) y la selección de celda en `spawn_agent_near`.
   - `spawn_key=(4,)`: `donor_rng` del motor, sólo para sortear el donante de genoma en la reproducción neutral (D26, caso 3). Va aparte para que el sorteo no desplace la secuencia de `evo_rng`: con la misma semilla, los dos modos consumen `evo_rng` igual en el tick.
   - `spawn_key=(3,)`: `_comp_rng` de `ToroidalGrid2D`, para la ubicación inicial y la reposición de recursos compuestos.
   Cada generador sólo se consume cuando su mecanismo está activo: `evo_rng` con `enable_evolution=True`, `_comp_rng` con `num_composite_patterns > 0` y `donor_rng` con `reproduction_mode="neutral"`. Esta lista de generadores derivados es una excepción declarada a la regla "un único generador por motor" de CLAUDE.md, que se actualiza en consecuencia.
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
    reproduction_mode: str = "energy"  # "energy" (R12) | "neutral" (ablación de R12 y control de deriva)
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
    enable_holon_view: bool = True  # R22; sólo actúa con enable_holonic_hierarchy=True
    holon_energy_sharing: bool = True  # parte de R23; sólo actúa con enable_holonic_hierarchy=True
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
- `reproduction_mode` en `{"energy", "neutral"}`; si no, `ValueError` que menciona `"reproduction_mode"`.
- Validación de orden compuesto frente a patrones benéficos disponibles: si `num_composite_patterns > 0` y `composite_order > num_world_patterns // 2`, lanza `ValueError` cuyo mensaje menciona `"composite_order"`.
- Coherencia de la estigmergia con el umbral de depósito (2026-10-19): si `enable_stigmergy=True`, `stigmergy_deposit_rate > 0` y `stigmergy_deposit_rate * initial_direct_confidence < min_confidence`, lanza `ValueError` cuyo mensaje menciona `"stigmergy_deposit_rate"`. Con esa tasa ni siquiera una creencia directa nueva (confianza `initial_direct_confidence`) deja un rastro que alcance `min_confidence` y, por el umbral de depósito de D27, la estigmergia casi sólo borraría rastros. Es una cota de cordura, no una garantía para todo depósito: una experiencia que refuerza un rumor previo o que refuta una creencia puede dejar una confianza menor, y entonces el depósito borra el rastro anterior sin dejar uno, porque la experiencia más reciente prevalece. La regla no alcanza a la ablación preregistrada de $R_{19}$ (`enable_stigmergy=False`, `stigmergy_deposit_rate=0.0`, D29).

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

### Decisión 21: Metabolismo Energético ($R_{20}$) con Costo Cerebral y Sensorial Cuadrático ($R_{21}$)
Para impedir el "atajo evolutivo trivial" (que la selección natural incremente ilimitadamente $C_{\max, i} \to N$ o los radios $r_{\text{perc}}, r_{\text{com}}$ creando un súper-individuo omnisciente), el costo metabólico basal por tick es cuadrático en la capacidad de memoria y en los radios sensoriales/comunicativos del genoma:
$$c_{\text{base}}(i) = c_{\text{fijo}} + c_{\text{mem}} \cdot C_{\max, i}^2 + c_{\text{sens}} \cdot \left(r_{\text{perc}, i}^2 + r_{\text{com}, i}^2\right)$$
donde `metabolic_base_cost` ($c_{\text{fijo}} = 0.01$), `memory_capacity_cost` ($c_{\text{mem}} = 0.002$) y `sensory_radius_cost` ($c_{\text{sens}} = 0.0005$).
El balance energético del agente $i$ en el tick $t$ es:
$$E_i(t+1) = E_i(t) + \eta_E \cdot r_i(t) - c_{\text{base}}(i) - c_{\text{move}} \cdot \mathbb{I}(\text{mov}_i(t)) - c_{\text{msg}} \cdot m_i(t) - c_{\text{coord\_share}}(i, t)$$
donde:
- $\eta_E =$ `energy_gain_scale` ($0.45$ por defecto), y $r_i(t)$ es el valor real experimentado: `true_value` de un recurso elemental, `-composite_failure_penalty` en un intento compuesto fallido, o la fracción recibida de un recurso compuesto resuelto por su holón (D27).
- $\mathbb{I}(\text{mov}_i(t)) = 1$ si el agente ejecutó una acción `MOVE` válida en el tick $t$, $0$ en otro caso (`move_cost` $= 0.005$).
- $m_i(t)$ es la cantidad de mensajes emitidos por el agente $i$ en Fase 1 + Fase 2 (`message_cost` $= 0.001$). Con `comm_enabled=False` ningún mensaje se envía (`messages_sent = 0`), así que $m_i(t) = 0$ (2026-10-19): la variante sin comunicación no paga una comunicación que no tiene.
- $c_{\text{coord\_share}}(i, t)$ es su alícuota del costo de coordinación de los holones a los que pertenece.

Las ganancias y penalizaciones por recursos se acreditan en la Fase 4; el costo de coordinación, en la Fase 5 (D24); el costo basal, de movimiento y de mensajes, al cobrar el metabolismo en la Fase 5. Si al cobrar el metabolismo resulta $E_i(t+1) \le 0$, el agente muere inmediatamente: es eliminado de `engine.agents`, de `env` (`remove_agents`) y podado de cualquier árbol `CompositeAgent` mediante `prune_dead_leaves`. No hay tope superior de energía.

**Orden exacto de la Fase 5.** (i) `decay_memory` de todos los agentes, igual que en Fase I; (ii) el trabajo de Fase II en el orden del spec `simulation-engine`: costo de coordinación con `SPLIT` y `BOND`; metabolismo, muerte y reproducción con su herencia cultural; y por último $R_{18}$ sobre el bosque holónico resultante, de modo que las hojas liberadas por `SPLIT` o por poda pierden la penalización de redundancia antes del tick siguiente; (iii) `env.step_dynamics(tick)`, que incluye la reposición de compuestos y el decaimiento estigmérgico; (iv) registro de `TickMetrics` y de `EvolutionaryTickMetrics`. Así, los recién nacidos y las bajas del tick ya figuran en las métricas de ese tick, y la secuencia de Fase I no cambia cuando el paso (ii) está inactivo.
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
     - $r_{\text{perc}}, r_{\text{com}}$: $lo = 1$ y $hi = (\min(\text{config.grid\_width}, \text{config.grid\_height}) - 1) // 2$, que es el mayor radio que admite la validación `2 * max(radios) < min(grilla)` de `SimulationConfig`. Si $hi < lo$, el rasgo no muta (conserva el valor parental), pero las extracciones se consumen igual. **Declarado:** la mutación no produce radio 0, aunque la Fase I lo admite en la configuración; un fundador con radio 0 pasa a 1 en su primer salto.
   - La validación de `SimulationConfig` exige `max_genome_memory_capacity >= memory_capacity`, para que el genoma fundador esté dentro de sus cotas.
3. **Transferencia Cultural Vertical (`transfer_cultural_heritage(parent_memory, child_capacity, tick, config) -> tuple[KnowledgeUnit, ...]`):** es una función pura que **no escribe** en la memoria del hijo; sólo prepara los testimonios parentales.
   - Primero, con `child_capacity < 0` lanza `ValueError`, **también con la herencia apagada** (sin el control, `ranked[:child_capacity]` cortaría desde el final, y la ablación ocultaría el error del motor); con `child_capacity == 0` devuelve `()`.
   - Si `config.enable_cultural_inheritance` es `False` o `config.inheritance_discount == 0.0`, devuelve `()`.
   - Si no, ordena `parent_memory.all_units()` por `(-parent_memory.compute_utility(u, tick), u.pattern)`, toma hasta `child_capacity` unidades y, para cada una con `config.gamma_social_discount * config.inheritance_discount * u.confidence >= config.min_confidence`, devuelve `replace(u, confidence=config.inheritance_discount * u.confidence)`.
   - El motor llama a `transfer_cultural_heritage(parent.memory, child.memory.capacity, tick, child.config)`, con la configuración **del hijo** (su `gamma_social_discount` es el que aplicará). Con la confianza uniforme por defecto, el filtro garantiza que la creencia guardada no queda bajo `min_confidence`. Con una `TrustStrategyPort` no uniforme, la confianza final puede diferir, y la creencia que quede bajo el umbral se purga en el siguiente `decay_memory`.
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
  - `node_id: int` (identificador único asignado por un contador monótono decreciente `self.next_holon_id` del motor, que empieza en `-2`; el `-1` queda reservado como emisor sintético de la estigmergia, D27). Los holones usan IDs negativos y los `MicroAgent` sus `agent_id >= 0`, de modo que las claves de `root_nodes` nunca colisionan por más nacimientos que haya.
  - `children: tuple[AgentNode, ...]` (mínimo 2 hijos; pueden ser `MicroAgent` o `CompositeAgent` de cualquier nivel, permitiendo árboles de profundidad arbitraria $L = 1, 2, 3, \dots, K$).
  - `created_tick: int` y `formation_tick: int` (al crearlo, igual a `created_tick`; se reinicia cuando el holón pierde un miembro, ver M13 en D28).
  - `ticks_without_surplus: int = 0` (contador para evaluar `SPLIT`).
  - `cooperative_completions: int = 0`.
  - `formed_by_bond: bool` (`True` si lo creó `BOND`; `False` si lo creó $R_{17}$) y `formation_knowledge: tuple[tuple[int, frozenset[Pattern]], ...] = ()` (lo que sabía cada hoja al formarse, en pares `(agent_id, K)` ordenados por `agent_id`). **Constructor:** `CompositeAgent(node_id, children, created_tick, formed_by_bond)`, con `formation_tick = created_tick` y `formation_knowledge = ()`. `holon.py` **nunca** calcula $K$, porque exige saber si el signo es correcto (la verdad del mundo): el motor completa `formation_knowledge` justo después de crear el holón (por `BOND` o $R_{17}$) y lo reinicia cuando corresponde (D28, M13).
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
) -> None: ...  # D25.1; local_reach[aid] = hojas en alcance local de aid (contrato en D25.1)
def reproduce_holon(
    holon: CompositeAgent, offspring: Mapping[int, MicroAgent], node_id_source: Callable[[], int], tick: int
) -> CompositeAgent: ...  # replica el árbol sustituyendo cada hoja por offspring[hoja.agent_id] (contrato en D26)
```

### Decisión 24: Operadores Dinámicos de Fusión (`BOND`, $R_{15}$) y Fisión (`SPLIT`, $R_{16}$) con Localidad Espacial
El motor mantiene un registro de nodos raíz activos `self.root_nodes: dict[int, AgentNode]` (inicialmente cada `MicroAgent` es su propio nodo raíz con clave `agent_id`) y un mapa inverso `self.agent_to_root: dict[int, int]` que asocia cada `agent_id` de hoja con el `node_id` de su nodo raíz actual:
1. **Localidad Espacial Intra-Holón (`local_holon_leaves`):**
   - Para evitar "telepatía holónica" a través del toro, dos hojas $\ell_a, \ell_b$ de un mismo `CompositeAgent` $U$ están en alcance local en el tick $t$ si su distancia de Chebyshev toroidal `env.get_agent_distance(a, b)` es $\le \max(\ell_a.\text{genome.comm\_radius}, \ell_b.\text{genome.comm\_radius}) + 1$.
   - Cuando una hoja `aid` consulta la memoria colectiva de su holón raíz $U$ o intenta resolver un recurso compuesto en la Fase 4, sólo participan las hojas de $U$ en alcance local de `aid` (`local_ids = {l.agent_id for l in U.leaf_agents if env.get_agent_distance(aid, l.agent_id) <= max(aid_comm, l.genome.comm_radius) + 1}`).
2. **Costo de coordinación y `SPLIT` ($R_{16}$):**
   - Para cada `CompositeAgent` raíz $U$ (en orden ascendente de `node_id`):
     - Calcula $c_{\text{coord}}(U) = \text{config.holon\_coord\_cost} \cdot |U| \cdot L(U)$, donde $|U|$ = `len(U.leaf_agents)`, y, si `enable_evolution=True`, descuenta $c_{\text{coord}}(U) / |U|$ de la energía de cada hoja $\ell \in \text{leaves}(U)$. El costo se cobra sólo al holón raíz: los sub-holones no pagan aparte, porque el factor $L(U)$ ya pondera la profundidad. Este costo y el reparto de la ganancia compuesta (D27) forman la regla $R_{23}$.
     - **Superávit del tick.** El holón tuvo superávit en el tick $t$ si y sólo si (a) registró al menos una resolución compuesta exitosa en la Fase 4 de $t$, o (b) $|\mathcal{K}_{\text{loc}}(U)| > \max_{\ell} |\mathcal{K}(\ell)|$, donde $\mathcal{K}(\ell)$ son los patrones de la memoria de $\ell$ con `confidence >= decision_conf_threshold` y $\mathcal{K}_{\text{loc}}(U)$ es la unión de $\mathcal{K}(\ell)$ sobre la **componente conexa más grande** del grafo de alcance local entre las hojas de $U$ (arista si $\ell_a, \ell_b$ están en alcance local según el punto 1; desempate de componentes del mismo tamaño por menor `agent_id` mínimo). Con superávit, `U.ticks_without_surplus = 0`; sin superávit, `U.ticks_without_surplus += 1`.
     - Si `config.enable_holon_splitting` es `True` y (`U.ticks_without_surplus >= config.holon_split_patience` o `U.total_energy < len(U.leaf_agents) * config.holon_min_energy_per_leaf`), el holón $U$ se disuelve: se elimina `U.node_id` de `root_nodes` y cada hijo directo $c \in U.\text{children}$ pasa a ser un nodo raíz en `root_nodes[c.node_id] = c` (preservando sub-holones intermedios si $L(U) \ge 2$). Un sub-holón que pasa a raíz reinicia `ticks_without_surplus = 0` (2026-10-19): el contador sólo se evalúa en los holones raíz, así que el valor que traía de antes de anidarse no describe su desempeño como raíz.
3. **Evaluación de `BOND` ($R_{15}$):**
   - Dos nodos raíz $U_a, U_b$ ($a < b$) son candidatos a fusionarse en el tick $t$ si:
     - `len(U_a.leaf_agents) + len(U_b.leaf_agents) <= config.max_holon_leaves`.
     - Al menos una hoja de $U_a$ y una hoja de $U_b$ están a distancia de Chebyshev toroidal $\le 1$ (`env.get_agent_distance(la, lb) <= 1`).
   - Su puntaje de sinergia es:
     $$\text{score}(U_a, U_b) = \mathcal{S}_{\text{comp}}(\mathcal{K}_a, \mathcal{K}_b) \cdot \frac{\bar{\omega}_{\text{bond}}(U_a) + \bar{\omega}_{\text{bond}}(U_b)}{2}$$
     donde $\mathcal{K}_a, \mathcal{K}_b$ son los patrones con `confidence >= config.decision_conf_threshold` en las memorias colectivas de $U_a$ y $U_b$, y $\mathcal{S}_{\text{comp}}(\mathcal{K}_a, \mathcal{K}_b) = |\mathcal{K}_a \triangle \mathcal{K}_b| / |\mathcal{K}_a \cup \mathcal{K}_b|$ (o `0.0` si $\mathcal{K}_a \cup \mathcal{K}_b = \emptyset$).
   - Los pares candidatos con `score >= config.holon_bond_threshold` se ordenan por `(-score, a, b)` y se fusionan codiciosamente (*greedy matching* sin solapamiento en el mismo tick): cada par seleccionado $(U_a, U_b)$ se retira de `root_nodes` y es reemplazado por un nuevo `CompositeAgent(node_id=next_holon_id, children=(U_a, U_b), created_tick=tick, formed_by_bond=True)`; el motor completa enseguida su `formation_knowledge`.

### Decisión 25: Causalidad Descendente ($R_{18}$), Vista Compartida del Holón ($R_{22}$) y Recursos Compuestos Aprendidos
Cuando dos o más agentes forman parte de un mismo `CompositeAgent` raíz $U$:
1. **Particionamiento Epigenético de Memoria (`apply_downward_causation`):**
   - Si `config.enable_downward_causation` es `True`, para cada `CompositeAgent` raíz $U$:
     - La regulación es **local**, con el mismo criterio de alcance que la memoria compartida (D24, punto 1). Para cada hoja $\ell \in \text{leaves}(U)$, sea $\text{loc}(\ell)$ el conjunto de hojas de $U$ en alcance local de $\ell$ (incluida $\ell$). Para cada patrón $\rho$ de la memoria de $\ell$, la "especialista titular" local es $\ell^*(\rho) = \arg\max_{\ell' \in \text{loc}(\ell),\ \rho \in \mathcal{M}_{\ell'}} (c_{\ell'}(\rho), -\ell'.\text{agent\_id})$.
     - El conjunto de patrones redundantes de $\ell$ es $\{\rho \in \mathcal{M}_\ell \mid \ell \neq \ell^*(\rho)\}$ (en empate de confianza conserva el patrón la hoja de menor `agent_id`), y se invoca `leaf.memory.set_redundant_patterns(redundant, config.redundancy_penalty)`.
     - La penalización afecta a todo uso de `compute_utility`: desalojo, orden de difusión de `BROADCAST_BELIEF` y orden de la herencia cultural. Es un efecto declarado de $R_{18}$.
     - Para los `MicroAgent` que no pertenecen a ningún holón (o cuando `enable_downward_causation=False`), `leaf.memory.set_redundant_patterns(frozenset(), 1.0)`. Con la regla apagada, `apply_downward_causation` hace esa limpieza sobre las hojas del holón que recibe.
     - **Contrato de `local_reach` (2026-10-19).** El motor pasa `local_reach: Mapping[int, Sequence[int]]` con **exactamente una clave por hoja** de $U$ (ni faltan ni sobran claves); `local_reach[aid]` lista hojas de $U$ en alcance local de `aid`, en cualquier orden y con o sin `aid` (la función toma $\text{loc}(\ell)$ = `sorted({*local_reach[aid], aid})`). Si las claves no son exactamente las hojas de $U$, o una lista contiene un id que no es hoja de $U$, lanza `ValueError`, **también con `enable_downward_causation=False`**, para que la ablación de $R_{18}$ no oculte un error de cableado del motor. Las penalizaciones se calculan para todas las hojas antes de escribir ninguna, así que no hay efectos de orden.
2. **Vista compartida del holón ($R_{22}$, decisión P1 resuelta por la variante (a)):**
   - **Qué es.** Es un canal de conocimiento social **efímero y declarado**: cada hoja ve en el tick lo que saben las hojas de su holón en alcance local, sin copiarlo a su memoria. Es la única excepción a la regla de CLAUDE.md de que el conocimiento social entra sólo por `assimilate_testimony`. Se justifica porque no persiste, no pasa por la fusión epistémica y se puede apagar: es la regla $R_{22}$, con la bandera `enable_holon_view` (por defecto `True`; sólo actúa con `enable_holonic_hierarchy=True`). Con `enable_holon_view=False`, los holones siguen existiendo (BOND, SPLIT, energía y resolución compuesta), pero sus miembros no ven el conocimiento ajeno.
   - **Estado del agente.** Como `MicroAgent.perceive_and_emit_messages(obs, tick)` vacía `self._ephemeral_tick_beliefs` al empezar (`micro_agent.py:80`; lo verifica por comportamiento `test_creencia_solo_en_cache_vive_un_tick`), `MicroAgent` mantiene un segundo diccionario efímero `self._holon_tick_beliefs: dict[Pattern, KnowledgeUnit] = {}`, con los métodos `clear_holon_beliefs(self) -> None` e `inject_ephemeral_belief(self, unit: KnowledgeUnit) -> None` (que escribe `self._holon_tick_beliefs[unit.pattern] = unit`).
   - **Separación entre creencia propia y vista del holón.** `get_effective_belief(pattern)` sigue el orden memoria → caché efímero propio → vista del holón, y sólo la usan la decisión (`decide_action`) y la decisión de consultar del protocolo. `learn_from_experience` y `assimilate_testimony` parten del nuevo método público `own_belief(pattern)` (memoria → caché efímero propio, exactamente la `get_effective_belief` de Fase I), para que la experiencia directa y los testimonios nunca se fusionen con la creencia de un compañero. Las respuestas a consultas y los broadcasts siguen saliendo sólo de la memoria propia (`protocol.py`): nadie retransmite la vista del holón. Con `_holon_tick_beliefs` vacío, ambos métodos coinciden bit a bit con Fase I. Es una modificación de requisitos vigentes de `micro-agent`, declarada como `MODIFIED` en el spec delta.
   - **Sincronización en dos tiempos (`_sync_holon_view`).** Sólo actúa con `enable_holonic_hierarchy=True` y `enable_holon_view=True`. En cada tiempo, el motor primero calcula la vista de **todos** los agentes y recién después llama, en orden de `agent_id`, a `clear_holon_beliefs()` y a `inject_ephemeral_belief` de cada uno. Así, ningún cálculo lee una inyección del mismo tiempo y no hay efectos de orden.
     - La vista de `aid` contiene, para cada patrón, la creencia de mayor `(confidence, last_updated_tick, -agent_id)` entre las hojas de su holón raíz en alcance local (D24, punto 1), sin contar a `aid`. Si `config.comm_content_null=True`, el motor la pasa por `nullify_belief(unit, self.null_rng)` antes de inyectarla.
     - **Tiempo 1** (Fase 1, antes de `perceive_and_emit_messages`): lee las **memorias** (`BoundedMemory`) de las hojas, no su caché efímero, que todavía es del tick anterior. Así, el protocolo no gasta `QUERY_PATTERN` en lo que el holón ya sabe.
     - **Tiempo 2** (al final de la Fase 2, antes de decidir): lee `own_belief` de las hojas (memoria más caché del tick en curso), para que la decisión de la Fase 3 aproveche lo que cada hoja obtuvo de sus vecinos. Para recorrer esas creencias, `MicroAgent` expone `own_beliefs(self) -> dict[Pattern, KnowledgeUnit]` (2026-10-19): para cada patrón de la memoria o del caché efímero propio, `own_belief(pattern)`, ordenado por patrón. No incluye la vista del holón.
3. **Recursos compuestos aprendidos por experiencia (decisión P2 resuelta por la variante (b)):**
   - El motor **no** inyecta patrones compuestos "desbloqueados" ni lee la estructura de las reglas para informar al agente. Para el agente, un recurso compuesto es un recurso más, con su propio patrón `c_k`: lo ve como `VisibleResource`, lo explora con $\epsilon$ como a cualquier desconocido, lo consulta y lo difunde con el protocolo, y aprende su valor con `learn_from_experience` (D27, punto 2). Sólo el motor conoce `CompositeRule`, y sólo para resolver la interacción en la Fase 4, igual que conoce `true_value`.
   - El valor que aprende el agente no es estacionario: el mismo recurso paga o castiga según lo que sepa su grupo local en ese tick. Es una propiedad declarada del entorno, no un defecto. Un individuo solo tenderá a aprender que `c_k` es dañino; si los holones superan esa trampa es parte de lo que se mide.
   - **M2 sobre recursos compuestos.** Para que M2 siga siendo objetiva, los recursos compuestos **no entran** en el `truth` de `judge_decision`. M2 se calcula sólo sobre recursos elementales, exactamente como en Fase I. El motor quita de `get_reachable_true_values(aid)` (un `dict[resource_id, true_value]` sin patrón) los `resource_id` de las entradas de `observations[aid].visible_resources` cuyo `pattern` está en `env.get_composite_rules()`. Si el resultado queda vacío, o si la acción de `aid` es `INTERACT` sobre un recurso compuesto, ese agente no suma oportunidad de decisión en el tick. El desempeño sobre compuestos se mide con M12 (`composite_completions`).

### Decisión 26: Endosimbiosis Reproductiva Holónica ($R_{17}$) y Límite de Un Evento Reproductivo por Tick
En la Fase 5, cuando `config.enable_evolution` es `True`:
- El motor lleva un contador monótono `self.next_agent_id: int` inicializado en `max(env.get_active_agent_ids()) + 1` (o `0` si no hay agentes), porque el motor admite entornos externos cuyos IDs no son necesariamente `0 .. num_agents - 1`.
- `MicroAgent.create_offspring(self, child_id: int, tick: int, rng: np.random.Generator, genome_source: AgentGenome | None = None) -> MicroAgent` hace sólo lo que es del agente: parte la energía (`offspring_energy_share`), muta el genoma con `mutate_genome(genome_source if genome_source is not None else self.genome, self.config, rng)` (`genome_source` sólo lo pasa el modo neutral, Caso 3) y construye el hijo con `MicroAgent.from_lineage`, pasándole la misma `trust_strategy` y el mismo `protocol` del progenitor, para que una estrategia inyectada en el motor no se pierda en la descendencia. **No** transfiere creencias: la herencia cultural la entrega después el motor con `transfer_cultural_heritage` y `assimilate_testimony` (D22, punto 3), en el mismo tick y antes de procesar al siguiente progenitor.
- En cada tick se instancia un conjunto `reproduced_this_tick: set[int] = set()` para garantizar que **ningún `MicroAgent` pueda reproducirse más de una vez en el mismo tick** (ni engendrar como parte de un holón y luego volver a engendrar individualmente):
  - **Caso 1: `node` es un `CompositeAgent` en `sorted(self.root_nodes)` y `config.enable_holon_reproduction` es `True`:**
    - Si ninguna hoja de `node` está en `reproduced_this_tick`, `node.total_energy >= len(node.leaf_agents) * config.reproduction_threshold` y `len(self.agents) + len(node.leaf_agents) <= config.max_population`:
      - El motor procesa las hojas $\ell \in \text{node.leaf\_agents}$ en orden de `agent_id`. Para cada una toma `child_id = self.next_agent_id` (y hace `self.next_agent_id += 1`), crea la hoja hija $\ell'$ con `ell.create_offspring(child_id, tick, evo_rng)` y le entrega su herencia cultural antes de pasar a la hoja siguiente. Recién con todos los hijos creados llama a `reproduce_holon(node, offspring, ...)`, que sólo replica el árbol. Cada hoja hija se ubica en el entorno con `env.spawn_agent_near(ell'.agent_id, ell.agent_id, evo_rng, ell'.genome.perception_radius, ell'.genome.comm_radius)`, se añaden `ell.agent_id` y `ell'.agent_id` a `reproduced_this_tick`, y la topología arbórea se replica en un nuevo `CompositeAgent` raíz $U_{\text{hijo}}$.
      - **Contrato de `reproduce_holon` (2026-10-19).** Antes de pedir ningún `node_id`, valida que `offspring` asigne a cada hoja de `node` un hijo, que los hijos tengan `agent_id` distintos y que ninguno sea el `agent_id` de una hoja de `node`; si no, lanza `ValueError` sin consumir IDs. Después pide los `node_id` de los holones nuevos a `node_id_source` (en el motor, `next_holon_id`) en **preorden en profundidad**: cada nodo compuesto antes que sus descendientes, y los hermanos en el orden de `children` (raíz $R$ con hijos $A$ y $B$, y $A$ con hijo $A_1$: $R, A, A_1, B$). Así, el nuevo `CompositeAgent` raíz recibe el primer ID y la asignación es determinista. Que los `agent_id` de los hijos no choquen con otros agentes vivos lo garantiza `next_agent_id`, que `holon.py` no ve.
  - **Caso 2: Reproducción individual de hojas (`MicroAgent`, $R_{12}$), con `reproduction_mode="energy"`:**
    - Para cada `aid` en `sorted(self.agents)` que **no** pertenezca a `reproduced_this_tick`, si `agent.energy >= config.reproduction_threshold` y `len(self.agents) < config.max_population`:
      - Engendra un `MicroAgent` hijo con `child_id = self.next_agent_id` (`self.next_agent_id += 1`), lo ubica con `env.spawn_agent_near(child.agent_id, aid, evo_rng, child.genome.perception_radius, child.genome.comm_radius)`, lo registra como nodo raíz de nivel 0 en `self.root_nodes` y añade `aid` y `child.agent_id` a `reproduced_this_tick`.

  - **Caso 3: Reproducción neutral (`reproduction_mode="neutral"`, ablación de $R_{12}$ y control de deriva de C6).** Quita el vínculo entre éxito y herencia sin cambiar **la regla** demográfica. Los mismos agentes que en el Caso 2 (no reproducidos, con `energy >= reproduction_threshold`, en orden de `agent_id`, respetando el cupo) se reproducen exactamente igual: misma partición de energía, misma ubicación junto a ellos, mismo `parent_id`, misma `generation` y misma herencia cultural. Lo único que cambia es el **genoma** del hijo: antes de cada nacimiento se sortea un donante con `donors[int(donor_rng.integers(len(donors)))]`, donde `donors` es la lista ordenada por `agent_id` de los agentes vivos al empezar la fase de reproducción del tick, y el hijo recibe `mutate_genome(donante.genome, ...)` en vez del genoma de su progenitor. En un tick dado, con el mismo estado de partida, quién se reproduce, la partición de energía y las posiciones son las mismas que en el modo `"energy"`; sólo se rompe la herencia de los rasgos de los exitosos. A partir de ahí las dos corridas **divergen**, porque los hijos tienen genomas distintos (costo metabólico, percepción y decisiones), y ésa es justamente la diferencia que mide `selection_gain`. No es un control de demografía idéntica a lo largo de la corrida. La reproducción holónica ($R_{17}$) no cambia.

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
     - **Alcance frente al shock (2026-10-19):** `composite_value` es fijo. `invert_world_rules` sólo toca `_world` (patrones elementales), así que un compuesto no sigue las inversiones de sus fragmentos requeridos. Combinar compuestos con el shock ambiental (Exp 005) queda fuera del alcance de los Exp 002 y 003; si el 005 lo necesita, se decide en su propio cambio.
     - Los patrones requeridos se eligen cíclicamente y se ordenan:
       `req = tuple(sorted(beneficial[(k + j) % len(beneficial)] for j in range(m)))`
     - El valor compuesto es `val = float(m ** config.composite_reward_exponent)`.
     - Se guarda `self._composite_rules[comp_pat] = CompositeRule(req, val)` y se generan `config.composite_resources_per_pattern` instancias de `Resource(resource_id, comp_pat, val)` en celdas sorteadas con `self._comp_rng` (y cuando se consumen, se encolan en `self._pending_composite` y se reponen en `step_dynamics` usando `self._comp_rng`).
   - **Semántica exacta de interacción en Fase 4:**
     - Cuando `aid` ejecuta `INTERACT` sobre un recurso en su celda cuyo patrón `comp_pat` pertenece a `env.get_composite_rules()`:
       - `env.execute_action` consume el recurso físico (y lo encola en `_pending_composite` para reposición en `step_dynamics`) devolviendo `ActionResult(ActionType.INTERACT, comp_pat, rule.composite_value)`. El agente nunca ve ese valor.
       - En Fase 4, el motor intercepta `result.interacted_pattern in composite_rules`:
         - Sea $\mathcal{K}_{\text{eff}}$ el conjunto de patrones $\rho$ para los que alguna hoja $\ell$ en alcance local de `aid` dentro de su nodo raíz $U$ (o sólo `aid`, si no pertenece a un holón) tiene `ell.own_belief(ρ)` con `predicted_value > 0` y `confidence >= decision_conf_threshold`. `own_belief` incluye el caché efímero propio, así que cuenta lo que cada hoja obtuvo de sus vecinos en ese tick. La resolución usa los conocimientos de las hojas aunque $R_{22}$ esté apagada: es física declarada del entorno ("el recurso se libera si el grupo local conoce los fragmentos"), no un canal de conocimiento hacia el agente. El motor verifica si `rule.evaluate(K_eff) is not None`. **Simultaneidad (2026-10-19):** $\mathcal{K}_{\text{eff}}$ y las hojas en alcance local que reciben el reparto se calculan con el estado **al empezar la Fase 4** (posiciones y creencias tras la Fase 3), para cada agente cuya acción es `INTERACT` sobre un recurso compuesto alcanzable. Así, lo que otra hoja aprende o el movimiento que hace antes en la permutación de la Fase 4 no cambia el resultado: la permutación sólo decide quién se lleva un recurso disputado.
         - **Si tiene éxito:** el agente aprende `learn_from_experience(comp_pat, +1.0, tick)`. La creencia y la energía van por separado: la creencia guarda el signo y la magnitud acotada a $[-1, 1]$, y la energía recibe la recompensa superlineal. Además, se incrementa `self.composite_completions`; si $U$ es `CompositeAgent`, se incrementa `U.cooperative_completions` y se reinicia `U.ticks_without_surplus = 0`. Si `enable_evolution=True`, la ganancia energética `config.energy_gain_scale * rule.composite_value` se reparte en partes iguales entre las hojas en alcance local de $U$ ($R_{23}$); con `holon_energy_sharing=False`, o fuera de un holón, va entera a `aid`. `aid` no se agrega a `self.direct_discoverers`, que rastrea sólo patrones elementales, y no se deposita rastro estigmérgico.
         - **Si fracasa:** el agente aprende `learn_from_experience(comp_pat, -config.composite_failure_penalty, tick)`. Si `enable_evolution=True`, ese valor experimentado le cuesta `config.energy_gain_scale * config.composite_failure_penalty` de energía según la fórmula de D21. No registra éxito compuesto.
3. **Estigmergia Espacial ($R_{19}$) y Conversión Exacta a `KnowledgeUnit`:**
   - `ToroidalGrid2D` mantiene `self.cell_stigmergy: dict[Cell, dict[Pattern, StigmergicTrace]]`.
   - En Fase 4, tras una experiencia directa con un patrón elemental $\rho$ de valor real $v$, si `config.enable_stigmergy=True` y `config.stigmergy_deposit_rate > 0`, el motor invoca `env.deposit_stigmergy(aid, pattern, value, confidence, tick)` que deposita en la celda actual del agente un `StigmergicTrace(pattern, float(np.sign(value)), min(1.0, config.stigmergy_deposit_rate * confidence), tick)`. Si la celda ya tiene un rastro de ese patrón con `last_updated_tick < tick`, el depósito nuevo lo **reemplaza** (la experiencia más reciente prevalece y refresca el decaimiento). Si el rastro existente es del mismo tick, se conserva el de mayor `(intensity, sign_value)`, de modo que dos depósitos del mismo tick dan el mismo resultado en cualquier orden de la permutación de la Fase 4. **Umbral de depósito (2026-10-19):** si la intensidad del depósito nuevo es menor que `config.min_confidence`, no queda en la celda: reemplaza y se purga en el acto, así que borra un rastro de ese patrón de un tick anterior, y no altera uno del mismo tick (que por construcción tiene mayor intensidad). Así un rastro nunca existe bajo el umbral con el que el decaimiento lo purgaría, no cuenta en `get_active_stigmergy_cells` ni llega como testimonio casi nulo, y el resultado sigue sin depender del orden. `confidence` es la de la creencia del agente tras `learn_from_experience`.
   - En Fase 1, si `config.enable_stigmergy=True`, **después** de que todos los agentes ejecutaron `perceive_and_emit_messages` (que vacía el caché efímero), y en orden de `agent_id`, para cada `trace` en `env.get_cell_stigmergy(aid)` se construye:
     `trace_unit = KnowledgeUnit(pattern=trace.pattern, predicted_value=trace.sign_value, confidence=trace.intensity, evidence_count=1, last_updated_tick=trace.last_updated_tick, from_direct_experience=False)`
     (si `config.comm_content_null=True`, se pasa por `nullify_belief(trace_unit, self.null_rng)`) y se asimila invocando `self.agents[aid].assimilate_testimony(trace_unit, sender_id=-1, tick=tick)`.
   - En `step_dynamics(tick)`, cada rastro con `last_updated_tick < tick` reduce su `intensity` en `config.stigmergy_decay` y se elimina si `intensity < config.min_confidence`.

### Decisión 28: Telemetría de Fase II (`EvolutionaryTickMetrics`), Fórmulas Exactas de M8–M13 y Esquemas de Reportes (`002` y `003`)
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
    offspring_social_ratio: float  # M9 (descriptiva: incluye testimonios horizontales)
    holon_count_by_level: tuple[tuple[int, int], ...]  # M10: pares (L, conteo) para L >= 1, ordenados por L
    max_holon_level: int  # M10
    mean_holon_size: float  # M10 (0.0 si no hay holones L >= 1)
    holonic_coverage_gain: float  # M11 (1.0 si no hay holones L >= 1)
    composite_completions: int  # M12 (acumulado de recursos compuestos resueltos)
    acquired_coverage: float | None  # M13, métrica de C8 (None si no hay holones elegibles en el tick)
    redundancy_reduction: float | None  # M13, descriptiva
    eligible_holons: int  # M13: holones raíz que entran en la media del tick
    stigmergy_active_cells: int
```

**Fórmulas exactas para casos borde en `EvolutionaryMetricsCollector`.** En M9 y M11, una creencia **válida** es una de la memoria con `confidence >= decision_conf_threshold`, sin importar si su signo es correcto: esas métricas describen qué se retiene, no si es verdad. M13 es la excepción: cuenta sólo creencias de signo correcto (ver abajo).
- **`mean_generation`, `max_generation`, `mean_energy` (M8):** Si `active_agents == 0`, valen `0.0`, `0` y `0.0` respectivamente.
- **`offspring_social_ratio` (M9):** Sobre los agentes activos con `generation >= 1`, sea $V_{\text{total}}$ el número total de creencias válidas en `BoundedMemory` y $V_{\text{social}}$ aquellas con `from_direct_experience == False`. Si $V_{\text{total}} == 0$, vale `0.0`; de lo contrario, `V_social / V_total`. Es **descriptiva**: cuenta también los testimonios horizontales, así que no mide sola la herencia. La contribución de la herencia se mide comparando contra la ablación de $R_{14}$ en 002-B (`social_ratio_gain` del reporte).
- **`holon_count_by_level`, `max_holon_level`, `mean_holon_size` (M10):** Recorriendo todos los nodos `CompositeAgent` activos ($L \ge 1$) del bosque holónico, cuenta cuántos hay en cada nivel $L$ (como tupla de pares `(L, conteo)` ordenada por $L$, para que el dataclass congelado sea realmente inmutable y hasheable), el máximo $L$ (o `0` si no hay `CompositeAgent`) y el tamaño medio en hojas $|\text{leaf\_agents}|$ de los `CompositeAgent` raíz (o `0.0` si no hay ninguno).
- **`holonic_coverage_gain` (M11):** Para cada `CompositeAgent` raíz $U$, sea $|\mathcal{K}(U)|$ la cantidad de patrones válidos en `U.collective_memory()` y sea $\overline{|\mathcal{K}_{\text{leaf}}(U)|}$ el promedio de patrones válidos en la memoria individual de sus hojas. La razón de ganancia de $U$ es $|\mathcal{K}(U)| / \overline{|\mathcal{K}_{\text{leaf}}(U)|}$ si $\overline{|\mathcal{K}_{\text{leaf}}(U)|} > 0$, o `1.0` en caso contrario. `holonic_coverage_gain` es la media sobre todos los `CompositeAgent` raíz activos (o `1.0` si no existe ninguno).
- **`acquired_coverage` (M13, métrica de C8) y `redundancy_reduction` (M13, descriptiva):** miden qué ganó cada holón **desde que se formó**, para que el sesgo de `BOND` ($R_{15}$), que ya junta memorias distintas al fusionar, no cuente. La métrica de C8 es la **cobertura colectiva adquirida**: cuántos patrones correctos *distintos* ganó el holón, por miembro. Con memoria acotada, ésa es la ventaja funcional de no duplicar: una hoja que duplica lo que sabe un compañero desaloja algo propio. A diferencia de la redundancia, olvidar algo duplicado no suma y olvidar algo único resta, así que la métrica no premia saber menos.
  - **Creencias que cuentan.** Para una hoja $\ell$, $K(\ell)$ es el conjunto de patrones **elementales** de su memoria con `confidence >= decision_conf_threshold` **y signo correcto** ($\text{sign}(\hat{v}) = \text{sign}(v)$ del patrón en el mundo). El colector conoce la verdad del mundo, como para M1 y M2; el agente no.
  - **Cobertura y redundancia.** $\text{cov}(U) = |\bigcup_{\ell} K(\ell)|$, el número de patrones correctos distintos que conoce el holón. Con $S(U) = \sum_{\ell} |K(\ell)|$, $\text{red}(U) = (S(U) - \text{cov}(U)) / S(U)$ si $S(U) > 0$ y $0$ si no; vale 0 si las memorias son disjuntas.
  - **Estado de formación.** Al crear un `CompositeAgent`, el motor guarda en `formation_knowledge` el conjunto $K(\ell)$ de cada hoja, y $\text{cov}_0(U)$ y $\text{red}_0(U)$ se calculan con esos $K$. **Cuando el holón pierde un miembro** (por muerte o por cualquier poda) y sigue siendo un holón, el motor **reinicia** su estado de formación: `formation_knowledge` pasa a ser el $K$ actual de las hojas que quedan y `formation_tick = tick`. Como `prune_dead_leaves` modifica los árboles en el lugar, `_remove` guarda antes de podar el conjunto de hojas de **cada** nodo compuesto del bosque (incluidos los anidados), y después reinicia los que siguen existiendo con menos hojas. El `tick` es el del paso en curso si la poda ocurre dentro de `step()` (muerte en la Fase 5), o `self.next_tick` si la piden las perturbaciones entre pasos (`ablate_population`, `ablate_discoverers`), de modo que el holón no es elegible en el tick siguiente. Es como si el holón se formara de nuevo, de modo que una muerte nunca cuenta como ganancia ni como pérdida. Un sub-holón que pasa a raíz por `SPLIT` conserva su propio estado de formación y su `formed_by_bond`.
  - **Holones elegibles.** Un holón raíz entra en M13 en el tick $t$ si `formed_by_bond` es `True` y `tick - formation_tick >= 1`. Los holones creados por $R_{17}$ no entran: su composición la impone la reproducción, no una fusión entre nodos que ya sabían algo, y su punto de partida es lo que heredaron (nada sin $R_{14}$), así que su cambio no mide la misma cosa. `reproduce_holon` crea **todos** los nodos compuestos que replica, incluidos los sub-holones internos, con `formed_by_bond = False` y `created_tick = formation_tick = tick`; después el motor completa el `formation_knowledge` de cada uno con las hojas hijas que realmente contiene. Así, si un sub-holón replicado pasa a raíz por `SPLIT`, sigue sin ser elegible.
  - **Valor del tick.** `acquired_coverage` es la media de $(\text{cov}(U) - \text{cov}_0(U)) / |U|$ sobre los holones elegibles ($|U|$ = hojas vivas), `redundancy_reduction` la media de $\text{red}_0(U) - \text{red}(U)$ sobre los mismos holones, y `eligible_holons` es cuántos son. `acquired_coverage` es positiva si el holón sabe más cosas distintas que al formarse y negativa si perdió cobertura. Sin holones elegibles, las dos valen `None`: no hay nada que medir, y ese tick no cuenta.
  - **Media de una corrida.** Para los reportes y para C8 se promedia sobre los pares (tick, holón elegible): la suma del valor de cada par dividida por la cantidad de pares (igual para `redundancy_reduction`). Así, una condición con menos holones no se acerca a 0 por tener menos exposición. Si una corrida no tiene ningún par, su media es `None`.
- **`cultural_convergence_tick` y `tabula_rasa_convergence_tick` en `CulturalInheritanceReport` (`002-B`):** Se define exactamente como el menor `m.tick` en `engine.history` tal que `m.decision_opportunities > 0` y `m.cumulative_decision_accuracy >= 0.70` (o `None` si ningún tick de la corrida alcanza ese umbral).

En `src/ide/experiments/exp002_runner.py` se definen los reportes inmutables:

```python
@dataclass(frozen=True)
class AdaptationReport:
    seed: int
    total_ticks: int
    evolved_accuracy: float
    frozen_genome_accuracy: float
    drift_accuracy: float  # reproduction_mode="neutral" con mutación (control de deriva)
    adaptation_gain: float  # evolved_accuracy - frozen_genome_accuracy
    selection_gain: float  # evolved_accuracy - drift_accuracy
    final_mean_memory_capacity: float  # exploratorio: qué rasgos evolucionan
    final_mean_bond_affinity: float  # exploratorio
    evolved_max_generation: int
    evolved_mean_energy: float
    total_births: int
    total_deaths: int
    condition_demography: tuple[tuple[str, int, int], ...]  # (condición, población final, generación máxima), Enmienda 1

@dataclass(frozen=True)
class CulturalInheritanceReport:
    seed: int
    total_ticks: int
    cultural_accuracy: float
    tabula_rasa_accuracy: float
    cultural_accuracy_surplus: float  # cultural_accuracy - tabula_rasa_accuracy
    final_offspring_social_ratio: float
    final_offspring_social_ratio_tabula_rasa: float
    social_ratio_gain: float  # final_offspring_social_ratio - final_offspring_social_ratio_tabula_rasa
    cultural_convergence_tick: int | None
    tabula_rasa_convergence_tick: int | None
    condition_demography: tuple[tuple[str, int, int], ...]  # (condición, población final, generación máxima), Enmienda 1
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
    condition_demography: tuple[tuple[str, int, int], ...]  # (condición, población final, generación máxima), Enmienda 1

@dataclass(frozen=True)
class OrthogonalizationReport:
    seed: int
    total_ticks: int
    mean_acquired_coverage: float | None  # media de M13 sobre los pares (tick, holón elegible); R18 apagada, R22 activa
    mean_acquired_coverage_without_view: float | None  # misma media con R22 apagada
    coverage_advantage: float | None  # con vista - sin vista; None si alguna media es None
    mean_redundancy_reduction: float | None  # descriptiva, condición con vista
    mean_redundancy_reduction_without_view: float | None  # descriptiva, sin vista
    holon_ticks: int  # pares (tick, holón elegible) de la condición con vista
    holon_ticks_without_view: int  # lo mismo sin vista: muestra si las dos medias descansan en exposiciones muy distintas
    max_holon_level: int
    level_counts_peak: tuple[tuple[int, int], ...]  # pares (L, conteo) ordenados por L
    condition_demography: tuple[tuple[str, int, int], ...]  # (condición, población final, generación máxima), Enmienda 1
```

**Funciones de los runners** (cada una corre sus condiciones con la misma semilla y devuelve su reporte):
- `run_protocol_002a_adaptation(config, total_ticks) -> AdaptationReport`: `evolved` = `config`, `frozen_genome` = `ablate(config, ["R13"])`, `drift` = `ablate(config, ["R12"])`.
- `run_protocol_002b_cultural_inheritance(config, total_ticks) -> CulturalInheritanceReport`: `cultural` = `config`, `tabula_rasa` = `ablate(config, ["R14"])`.
- `run_protocol_003a_holonic_transition(config, total_ticks) -> HolonicTransitionReport`: `holonic` = `config`, `individual` = `ablate(config, ["R15"])`.
- `run_protocol_003b_orthogonalization(config, total_ticks) -> OrthogonalizationReport`: `with_view` = `config` (con `R18` apagada), `without_view` = `ablate(config, ["R22"])`.

Las precisiones (`*_accuracy`) son la `cumulative_decision_accuracy` del último tick (M2, sólo recursos elementales).

**Campos derivados de los reportes (2026-10-19).** Se calculan sobre la condición indicada, al final de la corrida o sobre toda ella:
- 002-A, condición `evolved`: `evolved_max_generation` es el máximo de `max_generation` en la corrida; `evolved_mean_energy`, la `mean_energy` del último tick; `total_births` y `total_deaths`, las sumas de `births_this_tick` y `deaths_this_tick`; `final_mean_memory_capacity` y `final_mean_bond_affinity`, la media de `genome.memory_capacity` y `genome.bond_affinity` de los agentes vivos al final (`0.0` si la población se extinguió).
- 002-B: `final_offspring_social_ratio*` es la M9 del último tick de cada condición.
- 003-A, condición `holonic`: `max_holon_level` es el máximo de la corrida y `peak_holonic_coverage_gain`, el máximo de M11 (que vale `1.0` en un tick sin holones).
- 003-B, condición `with_view`: `max_holon_level` es el máximo de la corrida y `level_counts_peak`, para cada nivel $L$ que apareció, el **máximo conteo** de holones de ese nivel en un mismo tick, como pares `(L, conteo)` ordenados por $L$. `holon_ticks*` es la suma de `eligible_holons` de cada condición.

**Ejecución común (2026-10-19).** `src/ide/experiments/phase2_cli.py` describe cada protocolo con sus condiciones (en orden fijo, todas con la semilla de `config`), la función que corre una condición (`run_evolution_condition` en `exp002_runner.py` y `run_holonic_condition` en `exp003_runner.py`, que devuelven un resumen tipado de la corrida) y la que arma el reporte. La CLI de cada runner (`python -m ide.experiments.exp002_runner` y `exp003_runner`, con `--profile` (por defecto `phase2`; sólo se usa `total_ticks`), `--seeds`, `--out`, `--jobs` y `--attribution`) parte de `PHASE2_PROTOCOL_CONFIGS[protocolo]` con cada semilla, reparte las condiciones en `--jobs` procesos (una condición idéntica en dos protocolos, como `holonic` de 003-A y `with_view` de 003-B, corre una vez) y escribe `expNNN_seed{s}.json` (configuración y reporte de cada protocolo) y, con varias semillas, `expNNN_aggregate.json`, donde `level_counts_peak` se agrega por nivel, con 0 en las semillas que no lo alcanzaron. Con `--attribution` corre sólo `run_phase2_attribution` con las afirmaciones del experimento, por defecto sobre `PHASE2_SEEDS` (sin `--attribution`, `--seeds` vale `[42]`), y escribe `expNNN_attribution.json`. En la atribución, una corrida se identifica por la condición que ejecuta (evolutiva u holónica) y no por el protocolo, así que C7 y C8, con configuraciones idénticas, comparten corridas. La CLI, la atribución y `run_protocol_003b_orthogonalization` rechazan con `ValueError` una configuración de 003-B con `enable_downward_causation=True`, porque C8 se define con $R_{18}$ apagada.

### Decisión 29: Pre-Registro de la Fase II: Reglas `R12`–`R23`, Afirmaciones `C5`–`C8`, Variantes y Perfil
Esta decisión es **pre-registro** (decisión P3, resuelta). Se versiona antes de implementar los runners y de mirar resultados, y cambiarla después exige un commit que lo justifique.

En `src/ide/experiments/attribution.py`:
- `DESIGN_RULES` permanece intacto con las 11 reglas `R1`..`R11`, para preservar los tests de `tests/test_attribution.py`.
- Se define `PHASE2_DESIGN_RULES: tuple[DesignRule, ...]`. Cada `DesignRule` lleva sus cuatro campos (`rule_id`, `name`, `purpose`, `ablation`); `test_attribution.py` exige `purpose` no vacío. `ablation = ()` marca una regla nuclear, como `R1` y `R2` en Fase I:

| Regla | `name` | `purpose` (capacidad que se diseñó para producir) | `ablation` |
| :--- | :--- | :--- | :--- |
| `R12` | Reproducción diferencial por energía | Que los agentes con más energía dejen más descendencia (selección). | `(("reproduction_mode", "neutral"),)`: misma demografía, genoma del hijo tomado de un donante al azar (D26, caso 3). Es también el control de deriva de C6. |
| `R13` | Mutación genética acotada | Variación heredable sobre la que actúa la selección. | `(("mutation_rate", 0.0), ("discrete_mutation_prob", 0.0))` |
| `R14` | Herencia cultural vertical | Transmitir conocimiento de padres a hijos. | `(("enable_cultural_inheritance", False), ("inheritance_discount", 0.0))` |
| `R15` | Fusión holónica (BOND) | Asociar nodos complementarios en unidades de nivel superior. | `(("enable_holonic_hierarchy", False),)`. Apagarla deja inertes `R16`, `R17`, `R18`, `R22` y `R23`. |
| `R16` | Fisión holónica (SPLIT) | Disolver holones sin superávit. | `(("enable_holon_splitting", False),)` |
| `R17` | Reproducción de holón completo | Transmitir la estructura simbiótica a la descendencia. | `(("enable_holon_reproduction", False),)` |
| `R18` | Causalidad descendente intra-holón | Reducir la redundancia de memoria entre hojas de un holón (ortogonalización). | `(("enable_downward_causation", False), ("redundancy_penalty", 1.0))` |
| `R19` | Estigmergia | Externalizar conocimiento en el entorno. | `(("enable_stigmergy", False), ("stigmergy_deposit_rate", 0.0))` |
| `R20` | Física metabólica | Vida y muerte por energía: costo basal fijo, de movimiento y de emisión, muerte con $E \le 0$ y capacidad de carga. Sin ella no hay selección. | `()` (nuclear) |
| `R21` | Costo cuadrático de cerebro y sentidos | Encarecer la hipertrofia individual ($C_{\max}^2$, radios²). Sesga a favor de cooperar; se declara como sesgo. | `(("memory_capacity_cost", 0.0), ("sensory_radius_cost", 0.0))` |
| `R22` | Vista compartida del holón | Dar a cada hoja acceso efímero al conocimiento de las hojas cercanas de su holón (D25). | `(("enable_holon_view", False),)` |
| `R23` | Coordinación y reparto energético del holón | Que pertenecer a un holón tenga un costo y un beneficio energético compartido. | `(("holon_coord_cost", 0.0), ("holon_energy_sharing", False))` |

  **Física del entorno sin regla:** cómo paga un recurso compuesto (éxito si el grupo local conoce los fragmentos, fracaso si no, D27). Es una propiedad del entorno diseñado, como `true_value`; el agente no la recibe, la aprende.
- `ALL_DESIGN_RULES: tuple[DesignRule, ...] = DESIGN_RULES + PHASE2_DESIGN_RULES`, y `ablate()` busca en `_ALL_RULES_BY_ID = {r.rule_id: r for r in ALL_DESIGN_RULES}`.
- **Observaciones exploratorias de 003-B** (no son afirmaciones y no se clasifican). Se registran, en las dos condiciones de 003-B, la cobertura colectiva adquirida (M13), la reducción de redundancia y la exposición a holones. **Mecanismo hipotético, declarado de antemano:** con la vista, una hoja deja de consultar lo que ya saben sus compañeros (D25), no lo duplica y conserva capacidad para patrones propios. No se pre-registra ningún veredicto esperado. E4 compara contra el control nulo, que anula el contenido de **todos** los canales (horizontal, herencia, estigmergia y vista), así que pone a prueba si importa el contenido de toda la comunicación, no sólo el de la vista.
- **Afirmaciones de Fase II.** `EmergenceClaim` no cambia. Cada afirmación declara además su **canal**: las reglas sin las cuales el mecanismo que se pone a prueba no existe. El canal se guarda en `PHASE2_CLAIM_CHANNELS: dict[str, tuple[str, ...]]`:

| Afirmación | `EmergenceClaim(...)` | Canal | Variante `isolated` | Clasificación esperable |
| :--- | :--- | :--- | :--- | :--- |
| `C5` | `("C5", "Aceleración cultural intergeneracional", "002b", "cultural_accuracy", True, ("R14",))` | `("R14",)` | `ablate(config, ["R14"])`: sin herencia, con comunicación horizontal | Programada por construcción. |
| `C6` | `("C6", "Adaptación evolutiva por selección", "002a", "evolved_accuracy", True, ("R12", "R13"))` | `("R12",)` | `ablate(config, ["R12"])`: el control de deriva | Programada por construcción: adaptarse por selección es el propósito de R12 y R13. Qué rasgos evolucionan (`final_mean_memory_capacity`, `final_mean_bond_affinity`) se registra como **observación exploratoria**, no como afirmación. |
| `C7` | `("C7", "Superávit cooperativo sobre recursos compuestos", "003a", "holonic_composite_completions", True, ("R15", "R17"))` | `("R15",)` | `ablate(config, ["R15"])`: sin holones, con comunicación | Programada por construcción: el entorno impide por diseño que un individuo con $C_{\max} < m$ y sin ayuda resuelva el recurso. |
| `C8` | `("C8", "Cobertura colectiva adquirida sin causalidad descendente", "003b", "mean_acquired_coverage", True, ("R22",))` | `("R22",)` | `ablate(config, ["R22"])`: holones formados por la misma regla `BOND`, sin la vista compartida | Programada por construcción. Saber más patrones correctos es una afirmación sobre **disponibilidad** de conocimiento, y por el principio conservador (Documento Fundacional §9, punto 5) se atribuye a la regla que da acceso a ese conocimiento, $R_{22}$. `R18` está apagada en la condición base y el sesgo de `BOND` se cancela porque M13 mide el cambio desde la formación, pero eso no basta para llamarla emergente. Con esta clasificación, **la Fase II no tiene ninguna prueba genuina pre-registrada**: sus cuatro afirmaciones verifican que mecanismos diseñados funcionan. Se declara así, como resultado del diseño. |

- **Criterio "por construcción" ampliado.** Para las afirmaciones de Fase I, `is_by_construction` no cambia (quitar $R_C$ deja a la población sin comunicación). Para las de Fase II, una afirmación es por construcción si su canal no es vacío y está contenido en $R_C$: quitar $R_C$ elimina el mecanismo que se pone a prueba, y E3 sería una tautología. Con este criterio, C5, C6, C7 y C8 salen por construcción.
- **Variantes de Fase II** (`_variants`):
  - `isolated`: la indicada en la tabla.
  - **Semillas sin medición en C8.** Una semilla **tiene medición** en una comparación si las dos variantes comparadas (por ejemplo, `full` e `isolated` en E2, o `full` y `null_content` en E4) tienen `mean_acquired_coverage` distinto de `None`. Si a cualquiera de las dos le falta, la comparación de esa semilla cuenta como empate (la prueba de signo la descarta) y el reporte la lista en `ClaimEvaluation.unmeasured_seeds: dict[str, tuple[int, ...]]` (variante -> semillas en que ella o `full` no tienen valor; sólo las variantes con alguna; en Fase I queda vacío). Si menos de `MIN_SEEDS` semillas tienen medición en E2, C8 es `INSUFFICIENT_EVIDENCE`, no `NOT_OBSERVED`: no se midió nada. En `rule_effects`, el efecto de una regla promedia sólo las semillas con medición en `full` y en la variante sin la regla; si no hay ninguna, el efecto es `None` ("sin medición") y nunca `0.0`, que se leería como "no influye". `ClaimEvaluation.rule_effects` pasa a tipar `dict[str, float | None]`; en Fase I nunca hay `None`.
  - `purpose_ablated`: `ablate(config, R_C)`, sólo si $R_C$ no es vacío y la afirmación no es por construcción.
  - `null_content`: `replace(config, comm_content_null=True)`. Con él, el motor aplica `nullify_belief` al ruteo horizontal, a la herencia cultural ($R_{14}$), a la estigmergia ($R_{19}$) y a la vista del holón ($R_{22}$).
  - `rule_effects`: una variante sin cada regla ablacionable de `ALL_DESIGN_RULES`, **salvo las inactivas** en el protocolo de la afirmación. Para ellas, quitar la regla no cambia nada, y un efecto 0 se leería como "no influye". Las inactivas se declaran en `PHASE2_INACTIVE_RULES: dict[str, tuple[str, ...]]` y no reciben variante ni efecto:
    - `"002a"`: `R14`, `R15`, `R16`, `R17`, `R18`, `R19`, `R22`, `R23` (sin herencia cultural, sin holones, sin estigmergia).
    - `"002b"`: `R15`, `R16`, `R17`, `R18`, `R19`, `R22`, `R23`.
    - `"003a"` y `"003b"`: `R14`, `R18`, `R19`.
    - Un test contrasta esta lista con `PHASE2_PROTOCOL_CONFIGS`: cada regla listada debe tener apagada su bandera principal en la configuración del protocolo, y ninguna regla con la bandera apagada puede faltar. Así la lista no se desincroniza en silencio.
- **Compatibilidad con Fase I.** `run_protocol_001d_attribution(config, seeds, claims=EXP001_CLAIMS, jobs=1)` no cambia: sigue usando `DESIGN_RULES` y el perfil `ATTRIBUTION_PROFILE`, y sólo acepta afirmaciones de Fase I. Así siguen valiendo exactamente `report.rules == DESIGN_RULES` y `list(evaluation.rule_effects) == [f"R{i}" for i in range(3, 12)]` en los tests de Fase I. Para C1–C4, `_variants` no cambia.
- **Perfil pre-registrado de la Fase II:**
  - `PHASE2_ATTRIBUTION_PROFILE = "phase2"`, con `PROFILES["phase2"] = Profile(total_ticks=2000, injection_tick=80, warmup_ticks=150, post_ablation_ticks=100)`. Sólo `total_ticks` se usa en los protocolos 002 y 003.
  - `PHASE2_SEEDS = tuple(range(42, 52))`: 10 semillas. La prueba de signo unilateral puede llegar a $p = 1/1024$.
  - `PHASE2_PROTOCOL_CONFIGS: dict[str, SimulationConfig]`, sobre los valores por defecto de `SimulationConfig`:
    - `"002a"`: `enable_evolution=True`.
    - `"002b"`: `enable_evolution=True`, `enable_cultural_inheritance=True`.
    - `"003a"` y `"003b"`: `enable_evolution=True`, `enable_holonic_hierarchy=True`, `enable_holon_reproduction=True`, `num_composite_patterns=3`, `composite_order=4` (> `memory_capacity = 3`). En `"003b"`, `enable_downward_causation=False` es parte de la condición base de C8.
  - Ningún parámetro de este perfil se cambia a la vista de los resultados de las afirmaciones. La única excepción es la Enmienda 1, que se apoya sólo en la demografía de la prueba de humo y de una calibración declarada de antemano. Si la población se extingue o no llega a varias generaciones, eso se reporta como resultado. Antes de implementar los runners se corre una prueba de humo que sólo comprueba que la corrida termina y registra la generación máxima, **sin calcular ni mirar las métricas de las afirmaciones**.
  - **Enmienda 1 del perfil (2026-10-19, decisión del responsable del proyecto).** La prueba de humo (registrada en `RESULTADOS.md`, commit `58bf283`) mostró que con estas configuraciones la población no pasa de la generación 1 en ninguna de las 40 corridas: el perfil es inviable para medir C5 a C8, que dependen de la sucesión generacional o de los holones. Se calibra **una** variable del entorno con un procedimiento declarado antes de ejecutarlo y ciego a las afirmaciones (`src/ide/experiments/phase2_calibration.py`):
    - **Parámetro:** `resources_per_pattern` (abundancia del entorno; no toca ninguna regla $R_{12}$–$R_{23}$). **Efecto declarado sobre C7:** los recursos compuestos siguen fijos (`composite_resources_per_pattern`), así que más recursos elementales cambian la escasez relativa de los compuestos, de la que depende `holonic_composite_completions`. No es un sesgo de selección, porque todas las condiciones comparten el valor, pero el parámetro no es neutral para C7.
    - **Grilla cerrada**, en orden ascendente: 10, 20, 40 y 80. Se elige el menor valor viable, el mismo para los cuatro protocolos, y la evaluación se detiene ahí. Si ningún valor es viable, no se elige nada ni se amplía la grilla sin una decisión nueva.
    - **Semillas de calibración** 0 a 9, distintas de las de medición (`PHASE2_SEEDS`).
    - **Criterio.** Una corrida es viable si al final de los 2000 ticks la población sigue viva y llegó al menos a la generación 5. Un valor es viable si al menos 8 de las 10 semillas son viables en **cada condición de comparación** (`calibration_conditions`): las condiciones de cada runner, derivadas de sus `ProtocolSpec` (002-A: `evolved`, `frozen_genome` sin $R_{13}$ y `drift` sin $R_{12}$; 002-B: `cultural` y `tabula_rasa` sin $R_{14}$; 003-A: `holonic` e `individual` sin $R_{15}$; 003-B: `with_view` y `without_view` sin $R_{22}$), más el control nulo de cada protocolo (`null_content`, la variante de E4 en la atribución). Las configuraciones idénticas, como las bases de 003-A y 003-B, corren una sola vez. Exigir la viabilidad sólo a la base dejaría a esa condición en el borde de la supervivencia, y una variante algo más débil podría extinguirse antes y perder en las métricas acumuladas por pura demografía, a favor de la afirmación (hallazgo de la revisión cruzada). Las variantes de `rule_effects` no entran en el criterio: su registro demográfico (abajo) permite auditarlas.
    - **Ceguera.** La calibración sólo registra población final y generación máxima: nunca calcula ni mira las métricas de las afirmaciones.
    - **Antecedente.** Una primera corrida, con el criterio limitado a la base (commit `02c6a56`), terminó, pero su salida no se leyó antes de ampliar el criterio. Su JSON y su salida de consola se commitean sin leer junto con el criterio ampliado (`registros/phase2_calibration_antecedente.json` y `registros/phase2_calibration_antecedente_consola.txt`), se registra en `RESULTADOS.md` como antecedente y no se usa para elegir el valor.
    - **Registro demográfico.** Para distinguir una diferencia por extinción de una diferencia de mecanismo, los reportes de 002 y 003 registran por condición la población final y la generación máxima (`condition_demography`, D28), y la atribución hace lo mismo por variante y semilla (`ClaimEvaluation.demography`, vacío en Fase I).
    - **Firmas (2026-10-19).** En `attribution.py`: `PHASE2_PROTOCOL_CONFIGS_ORIGINAL: dict[str, SimulationConfig]`, `NULL_CONTENT = "null_content"`, `null_content_variant(config: SimulationConfig) -> SimulationConfig` (la variante de E4, `replace(config, comm_content_null=True)`) y `ClaimEvaluation.demography: dict[str, tuple[tuple[int, int], ...]]`. En `phase2_calibration.py`: `calibration_conditions(configs: Mapping[str, SimulationConfig]) -> list[tuple[str, str, SimulationConfig]]` (protocolo, condición, configuración; exige un `ProtocolSpec` por protocolo y valida cada base), `ViabilityRun(protocol, condition, value, seed, final_agents, max_generation)` con la propiedad `viable`, `is_viable_value(runs) -> bool`, `run_calibration(total_ticks=None, jobs=1, grid=CALIBRATION_GRID) -> CalibrationReport(parameter, total_ticks, grid, chosen, runs, fallback=None)` (la grilla debe ser ascendente y sin repetidos), `CALIBRATION_GRID = (10, 20, 40, 80)`, `CALIBRATION_REFINED_GRID = (25, 30, 35)` y `CALIBRATION_FALLBACK = 20` (Enmienda 1b). `ProtocolSpec` incorpora `validate: Callable[[SimulationConfig], None]`, y la atribución de la CLI guarda también las configuraciones base (`configs`).
    - **Enmienda 1b (2026-10-19, decisión del responsable del proyecto, antes de correrla).** Con la grilla original ningún valor fue viable (`RESULTADOS.md`): con 20 se extingue el control nulo y con 40 y 80 casi no hay recambio generacional. Se evalúa, con el mismo criterio, las mismas semillas y el mismo procedimiento, la grilla refinada 25, 30, 35 (`CALIBRATION_REFINED_GRID`, `python -m ide.experiments.phase2_calibration --refined`, que escribe `phase2_calibration_refinada.json`), en orden ascendente y con parada en el primer valor viable. **Salida fijada de antemano:** si tampoco hay un valor viable, se usa `resources_per_pattern = 20` (todas las condiciones de los runners son viables) y la comparación E4 de C5 a C8 se declara **no interpretable**, porque con 20 se extingue el control nulo. No cambia ninguna clasificación: las cuatro afirmaciones son programadas por construcción, y en la clasificación de la Decisión 13 su estado se decide antes de E4; el p de E4 se informa con esa advertencia. Las variantes de `rule_effects` no entran en el criterio y con 20 también podrían extinguirse: su `ClaimEvaluation.demography` se revisa antes de interpretar cada efecto, y un efecto con la variante extinguida se informa como no interpretable.
    - **Incorporación.** El valor elegido se incorpora a `PHASE2_PROTOCOL_CONFIGS` en un commit que lo justifica, antes de correr los protocolos con `PHASE2_SEEDS`. Las configuraciones originales quedan en `PHASE2_PROTOCOL_CONFIGS_ORIGINAL`: su inviabilidad queda registrada como resultado, y los protocolos y la atribución también se corren con ellas como referencia (`--reference` en la CLI de los runners, que escribe `expNNN_reference_*.json`, y `run_phase2_attribution(configs=PHASE2_PROTOCOL_CONFIGS_ORIGINAL)`).
- **Ejecución del pre-registro de Fase II.** Se agrega `run_phase2_attribution(seeds=PHASE2_SEEDS, claims=EXP002_CLAIMS + EXP003_CLAIMS, jobs=1, configs=None) -> AttributionReport`. Para cada afirmación usa `configs[claim.protocol]` como `full` (con `configs=None`, `PHASE2_PROTOCOL_CONFIGS`; la referencia de la Enmienda 1 pasa `PHASE2_PROTOCOL_CONFIGS_ORIGINAL`) y `PROFILES[PHASE2_ATTRIBUTION_PROFILE]` como perfil, y devuelve `AttributionReport(profile="phase2", rules=ALL_DESIGN_RULES, ...)`. `run_protocol_001d_attribution` queda para la Fase I y no recibe afirmaciones de Fase II.
- **Una sola condición por variante.** `_protocol_result` se extiende a `"002a"`, `"002b"`, `"003a"` y `"003b"` con `total_ticks = profile.total_ticks`, pero para medir una afirmación corre **sólo** la condición base del protocolo sobre la configuración de la variante, sin las condiciones de comparación del runner (genoma congelado, deriva, tabula rasa o individuos). Las comparaciones ya las hacen las variantes. Los runners completos (D28) siguen corriendo todas sus condiciones para sus reportes. La métrica de la afirmación es el campo equivalente del resumen de esa condición: `final_accuracy` para `evolved_accuracy` y `cultural_accuracy`, `composite_completions` para `holonic_composite_completions` y `mean_acquired_coverage` para C8.

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
    ├── metrics.py                # MODIFICADO: +EvolutionaryTickMetrics (M8-M13), +EvolutionaryMetricsCollector
    ├── attribution.py            # MODIFICADO: +PHASE2_DESIGN_RULES (R12-R23), +PHASE2_CLAIM_CHANNELS, perfil phase2, +EXP002_CLAIMS, +EXP003_CLAIMS
    ├── exp002_runner.py          # NUEVO: Protocolos 002-A y 002-B + CLI
    ├── exp003_runner.py          # NUEVO: Protocolos 003-A y 003-B + CLI
    └── phase2_cli.py             # NUEVO: ejecución común de los protocolos 002 y 003 y su CLI
```

---

## Risks / Trade-offs

- **Riesgo 1: Alterar accidentalmente el estado de `engine.rng` o `repr(TickMetrics)` y romper `tests/test_performance_equivalence.py`.**
  - *Mitigación:* Uso exclusivo de los generadores derivados de D19 (`evo_rng` y `_comp_rng`) para todo muestreo nuevo, guardas booleanas estrictas cuando las flags de Fase II son `False`, y separación entre `TickMetrics` (14 campos fijos) y `EvolutionaryTickMetrics`.
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
