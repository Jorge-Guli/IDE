# Design: Plataforma de Inteligencia Distribuida Emergente (IDE)

## Context

El proyecto IDE parte de los fundamentos establecidos en [DOCUMENTO_FUNDACIONAL.md](file:///c:/Desarrollo/IDE/DOCUMENTO_FUNDACIONAL.md), [DEFINICIONES_FORMALES.md](file:///c:/Desarrollo/IDE/DEFINICIONES_FORMALES.md) y [DEFINICIONES_TECNICAS.md](file:///c:/Desarrollo/IDE/DEFINICIONES_TECNICAS.md). Actualmente el repositorio contiene únicamente la documentación teórica y formal (`greenfield`). El diseño debe permitir implementar el **Experimento 001** (Memoria y Propagación Colectiva en Grilla 2D Toroidal) asegurando que el núcleo cognitivo de los agentes sea $100\%$ reutilizable en entornos futuros más complejos (espacios continuos, grafos dinámicos o microrrobótica) y en los Experimentos 002 a 006.

## Goals / Non-Goals

**Goals:**
- Garantizar aislamiento estricto entre la cognición local del agente (`src/ide/agent/`) y la geometría del entorno (`src/ide/environments/`) mediante el puerto `EnvironmentPort`.
- Garantizar que ningún agente tenga acceso a estado global ni al valor real oculto (`Resource.true_value`) antes de ejecutar una acción física de interacción.
- Asegurar complejidad $O(1)$ respecto al tamaño del tablero para búsquedas de vecindad en `ToroidalGrid2D` mediante indexación espacial por celda.
- Asegurar reproducibilidad determinista bit a bit mediante inyección explícita de `np.random.Generator(np.random.PCG64(seed))` en cada componente estocástico.
- Proveer contratos extensibles (Políticas de Confianza, Reglas de Utilidad de Memoria y Topologías) para habilitar los Experimentos 002–006 sin reescribir el motor base.

**Non-Goals:**
- No se implementará interfaz gráfica pesada (Pygame/OpenGL) acoplada al bucle de simulación; el motor debe correr en modo *headless* de alta velocidad y exportar telemetría limpia (JSON/CSV/consola).
- No se utilizarán redes neuronales pesadas (PyTorch/TensorFlow) en el Experimento 001; la unidad computacional mínima es deliberadamente simbólica/heurística y liviana.
- No se usará paralelismo multihilo no determinista que rompa la reproducibilidad por semilla.

## Decisions

### 1. Arquitectura Hexagonal con Navegación Agnóstica (`recommended_move` + `distance`)
- **Decisión:** El agente (`MicroAgent`) jamás recibe coordenadas $(x, y)$ ni referencias a `ToroidalGrid2D`. En `VisibleResource`, el entorno entrega `distance: int` y `recommended_move: Any` (el movimiento de 1 paso dentro de `Observation.available_moves` que acerca al agente hacia ese recurso).
- **Racional:** Si el entorno entregara un vector relativo como `(+2, 0)`, un agente sin geometría 2D no sabría cómo convertirlo en un movimiento unitario válido `(+1, 0)`. Al hacer que `EnvironmentPort` proyecte cada recurso distante al token de primer paso (`recommended_move`) y su distancia escalar (`distance`), el agente puede dirigirse hacia el recurso benéfico más cercano en una Grilla 2D, un Grafo Espacial (camino más corto Dijkstra) o un Espacio 3D sin cambiar ni una línea de código en `MicroAgent`.

### 2. Separación Estricta `Resource` vs. `VisibleResource`
- **Decisión:** El entorno almacena objetos `Resource(resource_id, pattern, true_value)`, pero al construir `Observation` proyecta cada recurso a `VisibleResource(resource_id, pattern, recommended_move, distance, is_reachable_now)`.
- **Racional:** Previene por construcción (a nivel de sistema de tipos) cualquier fuga accidental de información donde el agente consulte `resource.true_value` antes de interactuar.

### 3. Doble Mecanismo de Memoria Colectiva: Difusión + Consulta en Vivo (`QUERY_PATTERN`)
- **Decisión:** Combinar difusión pasiva (`BROADCAST_BELIEF` de las creencias con mayor utilidad $U(k, t)$) con consulta activa bajo demanda (`QUERY_PATTERN` $\to$ `QUERY_RESPONSE` en el mismo tick antes de decidir).
- **Racional:** Si un agente tiene capacidad $C_{\max} = 3$ frente a $N = 12$ patrones, la difusión pasiva sola provocaría un alto reemplazo ("thrashing") en la memoria individual. Con `QUERY_PATTERN`, cuando un agente ve un recurso desconocido en su vecindad perceptual, consulta a sus vecinos inmediatos en la Fase 1 y recibe la respuesta en la Fase 2 antes de ejecutar su decisión en la Fase 3. Las respuestas recibidas en el tick se guardan además en `_ephemeral_tick_beliefs` durante ese tick para garantizar decisión informada inmediata incluso si la memoria de largo plazo (`BoundedMemory`) está llena de creencias de mayor utilidad.

### 4. Resolución Epistémica Asimétrica y Protección Anti-Cámara de Eco (*Bootstrap Illusion*)
- **Decisión:** Incluir `from_direct_experience: bool` en `KnowledgeUnit`, aplicar descuento multiplicativo $\gamma \in (0, 1)$ en cada salto social, y en el **Escenario B (Consenso)** sólo permitir que la confianza supere $\max(c_{\text{local}}, \gamma c_{\text{ext}})$ cuando `incoming.from_direct_experience == True`.
- **Racional:** Si dos agentes que sólo poseen rumores indirectos (`from_direct_experience == False`) se rebotan el mismo rumor mutuamente en ticks sucesivos, sin esta restricción ambos incrementarían su confianza hasta $c \to 1.0$ sin evidencia física real. Al exigir evidencia directa en el emisor para elevar la confianza por encima del máximo de las partes, se elimina el efecto cámara de eco artificial y se garantiza que sólo la experiencia empírica anclada en el entorno pueda consolidar certeza máxima.

### 5. Retiro de Estímulo Físico (`retire_pattern_resources`) en Prueba de Persistencia Social
- **Decisión:** Cuando `SimulationEngine.ablate_discoverers(pattern, retire_stimulus=True)` elimina a todos los descubridores originales registrados en `direct_discoverers[pattern]`, también invoca `env.retire_pattern_resources(pattern)` para eliminar del mapa los objetos físicos de ese patrón e impedir su reposición.
- **Racional:** Garantiza validez experimental en el Protocolo 001-C: mide pura memoria colectiva transmitida entre agentes sin contaminación por re-descubrimiento físico.

---

## Especificación Estructural de Módulos y Firmas Exactas

### Mapa de Archivos a Crear
- `pyproject.toml`: Configuración de empaquetado, dependencias (`numpy>=1.26`, `pytest>=8.0`), `pythonpath = ["src"]`.
- `src/ide/__init__.py`
- `src/ide/config.py`: `SimulationConfig`
- `src/ide/domain/__init__.py`
- `src/ide/domain/types.py`: `Pattern`, `KnowledgeUnit`, `Resource`, `VisibleResource`, `Observation`, `MessageType`, `Message`, `ActionType`, `AgentAction`, `ActionResult`
- `src/ide/domain/ports.py`: `EnvironmentPort`
- `src/ide/domain/extensions.py`: `TrustStrategyPort`, `UniformTrustStrategy`, `AgentCapabilities`, `CompositeRule`, `AgentHyperParams`, `EvolutionaryPort`, `DefaultEvolutionaryOperator`
- `src/ide/agent/__init__.py`
- `src/ide/agent/memory.py`: `BoundedMemory`
- `src/ide/agent/epistemology.py`: `update_from_direct_experience`, `merge_social_belief`
- `src/ide/agent/micro_agent.py`: `MicroAgent`
- `src/ide/environments/__init__.py`
- `src/ide/environments/grid2d.py`: `ToroidalGrid2D`
- `src/ide/simulation/__init__.py`
- `src/ide/simulation/engine.py`: `SimulationEngine`
- `src/ide/experiments/__init__.py`
- `src/ide/experiments/metrics.py`: `TickMetrics`, `MetricsCollector`
- `src/ide/experiments/exp001_runner.py`: `EmergenceReport`, `FalsificationReport`, `AblationPointResult`, `ResilienceReport`, `run_protocol_001a_emergence`, `run_protocol_001b_falsification`, `run_protocol_001c_resilience`, `main`

### 1. Esquema Exacto de `src/ide/config.py`
```python
@dataclass(frozen=True)
class SimulationConfig:
    seed: int = 42
    grid_width: int = 40
    grid_height: int = 40
    num_agents: int = 80
    num_world_patterns: int = 12
    resources_per_pattern: int = 8
    memory_capacity: int = 3
    perception_radius: int = 2
    comm_radius: int = 2
    comm_enabled: bool = True
    initial_direct_confidence: float = 0.85
    alpha_learning: float = 0.40
    beta_reinforce: float = 0.30
    beta_punish: float = 0.60
    gamma_social_discount: float = 0.75
    eta_consensus: float = 0.15
    eta_doubt: float = 0.20
    lambda_decay: float = 0.005
    passive_conf_decay: float = 0.002
    min_confidence: float = 0.05
    decision_conf_threshold: float = 0.35
    epsilon_explore: float = 0.15
    max_broadcast_per_tick: int = 1
    enable_specialization: bool = False
    enforce_memory_constraint: bool = True

    def __post_init__(self) -> None:
        if self.enforce_memory_constraint and not (1 <= self.memory_capacity < self.num_world_patterns):
            raise ValueError("memory_capacity debe cumplir 1 <= C_max < num_world_patterns")
        for name in (
            "initial_direct_confidence", "alpha_learning", "beta_reinforce",
            "beta_punish", "gamma_social_discount", "eta_consensus",
            "eta_doubt", "min_confidence", "decision_conf_threshold", "epsilon_explore"
        ):
            val = getattr(self, name)
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} debe estar en [0.0, 1.0], recibido: {val}")
```

### 2. Esquemas Exactos de `src/ide/domain/types.py` y `src/ide/domain/ports.py`
```python
# src/ide/domain/types.py
@dataclass(frozen=True)
class Pattern:
    attributes: tuple[tuple[str, str], ...]

@dataclass(frozen=True)
class KnowledgeUnit:
    pattern: Pattern
    predicted_value: float
    confidence: float
    evidence_count: int
    last_updated_tick: int
    from_direct_experience: bool

@dataclass(frozen=True)
class Resource:
    resource_id: int
    pattern: Pattern
    true_value: float

@dataclass(frozen=True)
class VisibleResource:
    resource_id: int
    pattern: Pattern
    recommended_move: Any
    distance: int
    is_reachable_now: bool

@dataclass(frozen=True)
class Observation:
    agent_id: int
    tick: int
    visible_resources: tuple[VisibleResource, ...]
    available_moves: tuple[Any, ...]
    neighbor_ids: tuple[int, ...]

class MessageType(Enum):
    QUERY_PATTERN = "QUERY_PATTERN"
    QUERY_RESPONSE = "QUERY_RESPONSE"
    BROADCAST_BELIEF = "BROADCAST_BELIEF"

@dataclass(frozen=True)
class Message:
    msg_type: MessageType
    sender_id: int
    recipient_id: int | None
    pattern: Pattern
    belief: KnowledgeUnit | None = None

class ActionType(Enum):
    MOVE = "MOVE"
    INTERACT = "INTERACT"
    IDLE = "IDLE"

@dataclass(frozen=True)
class AgentAction:
    action_type: ActionType
    target: Any = None

@dataclass(frozen=True)
class ActionResult:
    action_type: ActionType
    interacted_pattern: Pattern | None = None
    experienced_value: float | None = None
```

```python
# src/ide/domain/ports.py
@runtime_checkable
class EnvironmentPort(Protocol):
    def get_active_agent_ids(self) -> list[int]: ...
    def get_observation(self, agent_id: int, tick: int) -> Observation: ...
    def get_communication_neighbors(self, agent_id: int) -> list[int]: ...
    def execute_action(self, agent_id: int, action: AgentAction, tick: int) -> ActionResult: ...
    def remove_agents(self, agent_ids: list[int]) -> None: ...
    def retire_pattern_resources(self, pattern: Pattern) -> None: ...
    def invert_world_rules(self, fraction: float, rng: np.random.Generator) -> list[Pattern]: ...
    def step_dynamics(self, tick: int) -> None: ...
    def get_world_patterns(self) -> dict[Pattern, float]: ...
    def get_reachable_true_values(self, agent_id: int) -> list[float]: ...
```

### 3. Esquemas Exactos de `src/ide/domain/extensions.py` (Experimentos 002–006)
```python
@runtime_checkable
class TrustStrategyPort(Protocol):
    def compute_sender_trust(self, receiver_id: int, sender_id: int, base_gamma: float) -> float: ...

@dataclass(frozen=True)
class UniformTrustStrategy:
    def compute_sender_trust(self, receiver_id: int, sender_id: int, base_gamma: float) -> float:
        return base_gamma

@dataclass(frozen=True)
class AgentCapabilities:
    perception_multiplier: float = 1.0
    memory_bonus: int = 0
    comm_multiplier: float = 1.0

@dataclass(frozen=True)
class CompositeRule:
    required_patterns: tuple[Pattern, ...]
    composite_value: float

    def evaluate(self, known_patterns: set[Pattern] | dict[Pattern, KnowledgeUnit]) -> float | None:
        keys = set(known_patterns.keys()) if isinstance(known_patterns, dict) else known_patterns
        if all(p in keys for p in self.required_patterns):
            return self.composite_value
        return None

@dataclass(frozen=True)
class AgentHyperParams:
    alpha_learning: float = 0.40
    gamma_social_discount: float = 0.75
    epsilon_explore: float = 0.15

@runtime_checkable
class EvolutionaryPort(Protocol):
    def reproduce_and_mutate(self, parent_params: AgentHyperParams, rng: np.random.Generator) -> AgentHyperParams: ...

@dataclass(frozen=True)
class DefaultEvolutionaryOperator:
    mutation_std: float = 0.05

    def reproduce_and_mutate(self, parent_params: AgentHyperParams, rng: np.random.Generator) -> AgentHyperParams:
        def mutate(val: float) -> float:
            return float(np.clip(val + rng.normal(0.0, self.mutation_std), 0.0, 1.0))
        return AgentHyperParams(
            alpha_learning=mutate(parent_params.alpha_learning),
            gamma_social_discount=mutate(parent_params.gamma_social_discount),
            epsilon_explore=mutate(parent_params.epsilon_explore),
        )
```

### 4. Firmas y Fórmulas Exactas en `src/ide/agent/`

#### `BoundedMemory` (`src/ide/agent/memory.py`)
```python
class BoundedMemory:
    def __init__(self, capacity: int, lambda_decay: float = 0.005) -> None: ...
    def __len__(self) -> int: ...
    def get(self, pattern: Pattern) -> KnowledgeUnit | None: ...
    def all_units(self) -> list[KnowledgeUnit]: ...
    def compute_utility(self, unit: KnowledgeUnit, current_tick: int) -> float:
        # U(k, t) = c * max(|v_hat|, 0.1) * exp(-lambda * max(0, current_tick - tau))
        ...
    def upsert(self, unit: KnowledgeUnit, current_tick: int) -> bool: ...
    def decay_step(self, current_tick: int, passive_decay: float, min_confidence: float) -> None: ...
```

#### `epistemology.py` (`src/ide/agent/epistemology.py`)
1. **`update_from_direct_experience(existing: KnowledgeUnit | None, pattern: Pattern, real_value: float, tick: int, config: SimulationConfig) -> KnowledgeUnit`:**
   - Si `existing is None`:
     - Retorna `KnowledgeUnit(pattern, float(np.clip(real_value, -1.0, 1.0)), config.initial_direct_confidence, 1, tick, True)`.
   - Si `existing.predicted_value * real_value >= 0` (Acuerdo empírico):
     - `new_val = float(np.clip((1.0 - config.alpha_learning) * existing.predicted_value + config.alpha_learning * real_value, -1.0, 1.0))`
     - `new_conf = min(1.0, existing.confidence + config.beta_reinforce * (1.0 - existing.confidence))`
     - Retorna `KnowledgeUnit(pattern, new_val, new_conf, existing.evidence_count + 1, tick, True)`.
   - Si `existing.predicted_value * real_value < 0` (Refutación empírica directa):
     - `penalized_conf = existing.confidence - config.beta_punish`
     - Si `penalized_conf < config.decision_conf_threshold`:
       - Invierte inmediatamente al valor empírico: `KnowledgeUnit(pattern, float(np.clip(real_value, -1.0, 1.0)), config.initial_direct_confidence, 1, tick, True)`.
     - En caso contrario (`penalized_conf >= config.decision_conf_threshold`):
       - `blended = (1.0 - config.alpha_learning) * existing.predicted_value + config.alpha_learning * real_value`
       - `sign = 1.0 if existing.predicted_value >= 0 else -1.0`
       - `new_val = sign * max(0.05, abs(blended))`
       - Retorna `KnowledgeUnit(pattern, new_val, penalized_conf, existing.evidence_count + 1, tick, True)`.

2. **`merge_social_belief(existing: KnowledgeUnit | None, incoming: KnowledgeUnit, tick: int, config: SimulationConfig, sender_trust_factor: float | None = None) -> KnowledgeUnit`:**
   - `gamma = config.gamma_social_discount if sender_trust_factor is None else sender_trust_factor`
   - `eff_ext_conf = gamma * incoming.confidence`
   - **Escenario A (`existing is None`):**
     - Retorna `KnowledgeUnit(incoming.pattern, incoming.predicted_value, eff_ext_conf, 1, tick, False)`.
   - **Escenario B (`existing.predicted_value * incoming.predicted_value >= 0`):**
     - `total_w = existing.confidence + eff_ext_conf`
     - `new_val = (existing.confidence * existing.predicted_value + eff_ext_conf * incoming.predicted_value) / total_w if total_w > 0 else incoming.predicted_value`
     - Si `incoming.from_direct_experience`:
       - `new_conf = min(1.0, existing.confidence + config.eta_consensus * eff_ext_conf * (1.0 - existing.confidence))`
     - Si `not incoming.from_direct_experience` (Regla Anti-Cámara de Eco):
       - `raw_conf = existing.confidence + config.eta_consensus * eff_ext_conf * (1.0 - existing.confidence)`
       - `new_conf = min(max(existing.confidence, eff_ext_conf), raw_conf)`
     - Retorna `KnowledgeUnit(existing.pattern, new_val, new_conf, existing.evidence_count + 1, tick, existing.from_direct_experience)`.
   - **Escenario C (`existing.predicted_value * incoming.predicted_value < 0`):**
     - `resistance = 2.0 if existing.from_direct_experience else 1.0`
     - `doubt_impact = (config.eta_doubt * eff_ext_conf) / resistance`
     - Si `not existing.from_direct_experience and eff_ext_conf > existing.confidence * 1.2`:
       - `new_conf = max(config.min_confidence, eff_ext_conf - existing.confidence * 0.5)`
       - Retorna `KnowledgeUnit(incoming.pattern, incoming.predicted_value, new_conf, 1, tick, False)`.
     - En caso contrario:
       - `new_conf = max(0.0, existing.confidence - doubt_impact)`
       - Retorna `KnowledgeUnit(existing.pattern, existing.predicted_value, new_conf, existing.evidence_count, tick, existing.from_direct_experience)`.

#### `MicroAgent` (`src/ide/agent/micro_agent.py`)
```python
class MicroAgent:
    def __init__(
        self,
        agent_id: int,
        config: SimulationConfig,
        trust_strategy: TrustStrategyPort | None = None,
    ) -> None: ...
    @property
    def agent_id(self) -> int: ...
    @property
    def memory(self) -> BoundedMemory: ...
    def get_effective_belief(self, pattern: Pattern) -> KnowledgeUnit | None: ...
    def perceive_and_emit_messages(self, obs: Observation, tick: int) -> list[Message]: ...
    def process_incoming_messages(self, messages: list[Message], tick: int) -> list[Message]: ...
    def decide_action(self, obs: Observation, tick: int, rng: np.random.Generator) -> AgentAction: ...
    def learn_from_experience(self, pattern: Pattern, real_value: float, tick: int) -> None: ...
    def decay_memory(self, tick: int) -> None: ...
```

#### `ToroidalGrid2D` (`src/ide/environments/grid2d.py`) y `SimulationEngine` (`src/ide/simulation/engine.py`)
```python
class ToroidalGrid2D:
    def __init__(self, config: SimulationConfig, rng: np.random.Generator) -> None:
        # Inicializa agentes 0..config.num_agents-1 y N patrones p_0..p_{N-1}
        # con config.resources_per_pattern instancias por patrón usando rng.
        ...

class SimulationEngine:
    def __init__(self, config: SimulationConfig, env: EnvironmentPort | None = None) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.env: EnvironmentPort = env if env is not None else ToroidalGrid2D(config, self.rng)
        self.agents: dict[int, MicroAgent] = {
            aid: MicroAgent(aid, config) for aid in self.env.get_active_agent_ids()
        }
        self.direct_discoverers: dict[Pattern, set[int]] = defaultdict(set)
        self.collector = MetricsCollector(config)
        self.history: list[TickMetrics] = []

    def step(self, tick: int) -> TickMetrics: ...
    def run(self, ticks: int, start_tick: int = 0) -> list[TickMetrics]: ...
    def inject_false_belief(
        self, pattern: Pattern, false_value: float, confidence: float, fraction: float, tick: int = 0
    ) -> list[int]: ...
    def ablate_population(self, fraction: float) -> list[int]: ...
    def ablate_discoverers(self, pattern: Pattern, retire_stimulus: bool = True) -> list[int]: ...
```

### 5. Esquemas Exactos de `TickMetrics`, `MetricsCollector` y Reportes Experimentales (`src/ide/experiments/`)
```python
# src/ide/experiments/metrics.py
@dataclass(frozen=True)
class TickMetrics:
    tick: int
    active_agents: int
    individual_coverage_mean: float
    collective_coverage: float
    decision_accuracy: float
    cumulative_decision_accuracy: float
    pattern_prevalence: dict[Pattern, float]
    false_belief_prevalence: float
    messages_per_agent: float

class MetricsCollector:
    def __init__(self, config: SimulationConfig) -> None: ...
    def record_tick(
        self,
        tick: int,
        agents: dict[int, MicroAgent],
        world_patterns: dict[Pattern, float],
        tick_opportunities: int,
        tick_correct_decisions: int,
        messages_sent_count: int,
    ) -> TickMetrics: ...

# src/ide/experiments/exp001_runner.py
@dataclass(frozen=True)
class EmergenceReport:
    collective_coverage: float
    isolated_coverage: float
    collective_individual_coverage_mean: float
    collective_accuracy: float
    isolated_accuracy: float
    emergence_surplus: float
    mean_messages_per_agent: float

@dataclass(frozen=True)
class FalsificationReport:
    target_pattern_id: str
    initial_injected_prevalence: float
    peak_false_prevalence: float
    final_false_prevalence: float
    extinguished_or_contained: bool

@dataclass(frozen=True)
class AblationPointResult:
    ablation_fraction: float
    remaining_agents: int
    pre_ablation_coverage: float
    immediate_post_ablation_coverage: float
    final_recovered_coverage: float
    retention_ratio: float

@dataclass(frozen=True)
class ResilienceReport:
    ablation_results: tuple[AblationPointResult, ...]
    discoverers_ablated_count: int
    post_discoverer_ablation_prevalence: float
    final_social_persistence_prevalence: float
```

## Risks / Trade-offs

- **[Riesgo: Saturación de memoria ("Memory Thrashing") por exceso de mensajes broadcast]** $\to$ **Mitigación:** En `BoundedMemory.upsert`, una creencia nueva para un patrón no registrado sólo reemplaza a una existente si su utilidad $U(k_{\text{nueva}}, t)$ supera estrictamente la utilidad mínima actual. Además, las respuestas a `QUERY_PATTERN` se almacenan en `_ephemeral_tick_beliefs` del agente durante ese tick.
- **[Riesgo: Cámara de eco social (Bootstrap Illusion)]** $\to$ **Mitigación:** En el Escenario B de `merge_social_belief`, un rumor indirecto (`from_direct_experience=False`) no puede incrementar la confianza por encima de $\max(c_{\text{local}}, \gamma c_{\text{ext}})$.
- **[Riesgo: Colisión de agentes consumiendo el mismo recurso en el mismo tick]** $\to$ **Mitigación:** El primero en interactuar con `resource_id` en el orden barajado por `rng.permutation` lo consume; cualquier intento posterior en el mismo tick recibe `ActionResult` vacío (`experienced_value=None`).
- **[Riesgo: Denominador cero en `decision_accuracy` (M2)]** $\to$ **Mitigación:** Si `total_opportunities == 0` en un tick, `decision_accuracy` reporta `0.0` (o mantiene el acumulado en `cumulative_decision_accuracy`) sin lanzar `ZeroDivisionError`.

## Checklist de Criterios de Aceptación (Definition of Done - QA)

- [ ] **Aislamiento de Capas:** Ningún archivo en `src/ide/agent/` importa `src/ide/environments/` (verificado por test de AST).
- [ ] **Cero Fuga de Información:** `VisibleResource` no posee el campo `true_value` y expone `recommended_move` y `distance`.
- [ ] **Invariante de Memoria:** Para todo agente $i$ y todo tick $t$, `len(agent.memory) <= config.memory_capacity` ($C_{\max} < N$).
- [ ] **Anti-Cámara de Eco:** Intercambio repetido entre dos agentes con `from_direct_experience=False` jamás supera $\max(c_A, \gamma c_B)$.
- [ ] **Validez de Persistencia Social:** `ablate_discoverers(..., retire_stimulus=True)` elimina tanto a los descubridores como al recurso físico en el tablero.
- [ ] **Determinismo:** Dos ejecuciones con la misma `seed` producen idéntica salida bit a bit.

## Setup, Ejecución y Validación Local

```powershell
# 1. Instalar proyecto en modo editable con dependencias de test
pip install -e ".[dev]"

# 2. Ejecutar suite completa de tests (TDD + Integración)
pytest -v

# 3. Ejecutar los 3 protocolos del Experimento 001 y generar reporte JSON
python -m ide.experiments.exp001_runner
```
