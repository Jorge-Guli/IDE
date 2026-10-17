# Tasks: Plataforma de Inteligencia Distribuida Emergente (IDE)

## 1. Scaffolding y Configuración del Proyecto

- [ ] 1.1 Crear `pyproject.toml` con configuración de paquete editable (`src/ide`), dependencias (`numpy>=1.26`, `pytest>=8.0`) y estructura de paquetes (`src/ide/{domain,agent,environments,simulation,experiments}` y `tests/`), verificando la instalación con `pip install -e ".[dev]"` y ejecución de `pytest --collect-only`.

## 2. Contratos de Dominio y Configuración (`domain-contracts`)

- [ ] 2.1 [TDD-RED] Escribir `tests/test_domain_contracts.py` probando inmutabilidad (`FrozenInstanceError`) y hashabilidad de `Pattern` y `KnowledgeUnit`, ausencia del atributo `true_value` y presencia de `recommended_move` y `distance` en `VisibleResource`, verificación de `EnvironmentPort` (incluyendo `retire_pattern_resources` e `invert_world_rules`) con `@runtime_checkable` y validación de invariantes en `SimulationConfig` ($1 \le C_{\max} < N$ y coeficientes en $[0, 1]$), verificando que `pytest tests/test_domain_contracts.py` falle inicialmente.
- [ ] 2.2 [TDD-GREEN] Implementar `src/ide/config.py`, `src/ide/domain/types.py` y `src/ide/domain/ports.py` cumpliendo todas las firmas e invariantes, verificando que `pytest tests/test_domain_contracts.py` pase al 100%.
- [ ] 2.3 [TDD-REFACTOR] Refactorizar anotaciones de tipos y docstrings en `src/ide/domain/` y `src/ide/config.py`, verificando que `pytest tests/test_domain_contracts.py` continúe en verde.

## 3. Contratos de Extensión para Roadmap Exp 002–006 (`roadmap-extensions`)

- [ ] 3.1 [TDD-RED] Escribir `tests/test_roadmap_extensions.py` probando `TrustStrategyPort` y `UniformTrustStrategy` (Exp 002), `AgentCapabilities` con multiplicadores plásticos (Exp 003), `CompositeRule.evaluate` para tareas multi-fragmento (Exp 005) y `DefaultEvolutionaryOperator.reproduce_and_mutate` acotado a $[0.0, 1.0]$ (Exp 006), verificando que `pytest tests/test_roadmap_extensions.py` falle inicialmente.
- [ ] 3.2 [TDD-GREEN] Implementar `src/ide/domain/extensions.py` con todos los protocolos y operadores del roadmap, verificando que `pytest tests/test_roadmap_extensions.py` pase al 100%.

## 4. Subsistema de Memoria Acotada (`bounded-memory`)

- [ ] 4.1 [TDD-RED] Escribir `tests/test_memory.py` cubriendo límite estricto `capacity` ($C_{\max}$), actualización in-place de patrón existente, cálculo exacto de utilidad epistémica $U(k, t) = c \cdot \max(|\hat{v}|, 0.1) \cdot e^{-\lambda(t-\tau)}$, reemplazo de la creencia de menor utilidad (con desempate por menor $\tau$), rechazo de creencias débiles en memoria llena y decaimiento pasivo con purga bajo `min_confidence`, verificando que `pytest tests/test_memory.py` falle inicialmente.
- [ ] 4.2 [TDD-GREEN] Implementar `BoundedMemory` en `src/ide/agent/memory.py`, verificando que todos los casos de `pytest tests/test_memory.py` pasen sin errores.
- [ ] 4.3 [TDD-REFACTOR] Optimizar complejidad de búsqueda y reemplazo en `BoundedMemory`, verificando que `pytest tests/test_memory.py` permanezca en verde.

## 5. Motor Epistemológico (`epistemic-engine`)

- [ ] 5.1 [TDD-RED] Escribir `tests/test_epistemology.py` cubriendo adquisición por experiencia directa (`from_direct_experience=True`), refuerzo empírico, ambas ramas de refutación empírica directa (`penalized_conf < decision_conf_threshold` y `>= decision_conf_threshold`), asimilación social con descuento $\gamma$ (Escenario A), refuerzo por consenso con regla anti-cámara de eco cuando `incoming.from_direct_experience=False` (Escenario B) y conflicto epistémico experiencia directa vs. rumor externo (Escenario C), verificando que `pytest tests/test_epistemology.py` falle inicialmente.
- [ ] 5.2 [TDD-GREEN] Implementar `update_from_direct_experience` y `merge_social_belief` en `src/ide/agent/epistemology.py` soportando `sender_trust_factor`, verificando que `pytest tests/test_epistemology.py` pase al 100%.

## 6. Micro-Agente Autónomo (`micro-agent`)

- [ ] 6.1 [TDD-RED] Escribir `tests/test_micro_agent.py` verificando: (a) auditoría AST que compruebe cero imports de `environments` en `src/ide/agent/`, (b) firmas públicas canónicas (`perceive_and_emit_messages`, `process_incoming_messages`, `decide_action`, `learn_from_experience`, `decay_memory`), (c) emisión de `QUERY_PATTERN` y `QUERY_RESPONSE`, y (d) decisión de `INTERACT` en celda actual, evitación de recurso dañino y navegación hacia recurso benéfico distante usando `recommended_move` y menor `distance`, comprobando que `pytest tests/test_micro_agent.py` falle inicialmente.
- [ ] 6.2 [TDD-GREEN] Implementar `MicroAgent` en `src/ide/agent/micro_agent.py` con soporte de caché efímero de consultas del tick (`_ephemeral_tick_beliefs`), verificando que `pytest tests/test_micro_agent.py` pase al 100%.

## 7. Entorno Espacial Grilla 2D Toroidal (`spatial-environments`)

- [ ] 7.1 [TDD-RED] Escribir `tests/test_grid2d.py` probando generación canónica de los $N$ patrones (`p_0` a `p_{N-1}`), aritmética modular toroidal (movimiento, percepción y cálculo de `recommended_move` y `distance` a través de los bordes), consistencia del índice espacial $O(1)$ (`cell_agents` y `cell_resources`), ocultamiento de `true_value` en `get_observation`, colisión segura sobre el mismo `resource_id`, retiro definitivo de patrón mediante `retire_pattern_resources`, e inversión abrupta de reglas `invert_world_rules` (Exp 004), verificando que `pytest tests/test_grid2d.py` falle inicialmente.
- [ ] 7.2 [TDD-GREEN] Implementar `ToroidalGrid2D` en `src/ide/environments/grid2d.py` cumpliendo `EnvironmentPort`, verificando que `pytest tests/test_grid2d.py` pase al 100%.

## 8. Motor de Simulación Discreto (`simulation-engine`)

- [ ] 8.1 [TDD-RED] Escribir `tests/test_simulation_engine.py` probando el pipeline de 5 fases por tick (`step`), bloqueo total de mensajes cuando `comm_enabled=False`, reproducibilidad bit a bit entre dos corridas con `seed=42`, registro histórico `direct_discoverers`, y métodos de perturbación en caliente (`inject_false_belief`, `ablate_population`, y `ablate_discoverers` con `retire_stimulus=True`), verificando que `pytest tests/test_simulation_engine.py` falle inicialmente.
- [ ] 8.2 [TDD-GREEN] Implementar `SimulationEngine` en `src/ide/simulation/engine.py` con permutación reproducible de turnos (`rng.permutation`), verificando que `pytest tests/test_simulation_engine.py` pase al 100%.

## 9. Suite Experimental y Métricas M1–M7 (`experimental-suite`)

- [ ] 9.1 [TDD-RED] Escribir `tests/test_exp001_suite.py` validando el cálculo exacto de las métricas M1 a M7 en `MetricsCollector` (incluyendo invariante $Cov_{\text{ind}}(t) \le C_{\max}/N$, contabilización de oportunidad de decisión en M2 y protección contra división por cero) y los esquemas exactos de retorno (`EmergenceReport`, `FalsificationReport`, `ResilienceReport`) de `run_protocol_001a_emergence`, `run_protocol_001b_falsification` y `run_protocol_001c_resilience`, verificando que `pytest tests/test_exp001_suite.py` falle inicialmente.
- [ ] 9.2 [TDD-GREEN] Implementar `MetricsCollector` en `src/ide/experiments/metrics.py` y los ejecutores de los protocolos 001-A, 001-B y 001-C con salida JSON/CLI en `src/ide/experiments/exp001_runner.py`, verificando que `pytest tests/test_exp001_suite.py` pase al 100%.
- [ ] 9.3 [TDD-REFACTOR] Ejecutar validación integral con `pytest -v` y `python -m ide.experiments.exp001_runner`, verificando el Checklist de Definition of Done completo.
