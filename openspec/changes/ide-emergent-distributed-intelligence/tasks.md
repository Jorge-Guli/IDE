# Tasks: Plataforma de Inteligencia Distribuida Emergente (IDE)

Convenciones: cada bloque sigue TDD (RED → GREEN → REFACTOR). Las firmas, fórmulas y desempates exactos están en `design.md`; los criterios verificables, en `specs/`. Un test en rojo de una expectativa empírica (`-m empirical`) **no** bloquea ninguna tarea: se reporta. Los valores numéricos se comparan con `pytest.approx(abs=1e-9)`; sólo el determinismo exige igualdad exacta. Un bloque sólo se marca completo si pasan `ruff check`, `ruff format --check`, `pyright` y `python -m pytest --cov=ide`.

## 1. Scaffolding y Configuración del Proyecto

- [x] 1.1 Crear `pyproject.toml` según `design.md` (paquete `ide` en `src/`; dependencia `numpy`; extra `dev` con `pytest`, `pytest-cov`, `hypothesis`, `ruff`, `pyright`, `py-spy` y `line_profiler`; marcadores `empirical` y `slow` excluidos por defecto; configuración de Ruff y de Pyright estricto), `.gitignore`, `tests/conftest.py` con el perfil `ci` de Hypothesis (`derandomize=True`) y los `__init__.py` de `src/ide/{domain,agent,environments,simulation,experiments}`. Verificar con `pip install -e ".[dev]"`, `python -m pytest --collect-only`, `ruff check` y `pyright`.

## 2. Contratos de Dominio y Configuración (`domain-contracts`)

- [x] 2.1 [RED] Escribir `tests/test_domain_contracts.py`: inmutabilidad, hashabilidad y orden total de `Pattern` (incluido `label`), validación de `Message`, campos exactos de `VisibleResource`, `EnvironmentPort` con sus 10 métodos y `@runtime_checkable`, todas las validaciones de `SimulationConfig.__post_init__` (incluida `memory_capacity = 0` con `enforce_memory_constraint=False`, `epsilon_recheck`/`tau_policy`, y los valores por defecto de `anti_echo_enabled`, `enable_navigation` y `comm_content_null`) y la ida y vuelta por JSON de `to_dict()`.
- [x] 2.2 [GREEN] Implementar `src/ide/config.py`, `src/ide/domain/types.py` y `src/ide/domain/ports.py`.
- [x] 2.3 [REFACTOR] Docstrings y tipos; la suite sigue en verde.

## 3. Contratos de Extensión (`roadmap-extensions`)

- [x] 3.1 [RED] Escribir `tests/test_roadmap_extensions.py`: `UniformTrustStrategy`, `AgentCapabilities` por defecto (la invariancia durante 100 ticks se prueba en 8.1), validación y `evaluate` de `CompositeRule` (con `set` y `dict`), y mutación acotada y reproducible de `DefaultEvolutionaryOperator`.
- [x] 3.2 [GREEN] Implementar `src/ide/domain/extensions.py`.

## 4. Memoria Acotada (`bounded-memory`)

- [x] 4.1 [RED] Escribir `tests/test_memory.py`: límite de capacidad, actualización de un patrón existente, valor exacto de $U(k,t)$ con piso 0.1, reemplazo de la creencia de menor utilidad con desempate triple, rechazo de creencias débiles, `force=True`, decaimiento que respeta `last_updated_tick == t`, purga bajo `min_confidence` y orden determinista de `all_units()`, y propiedades con Hypothesis: `len(memory) <= capacity` y ninguna confianza bajo `min_confidence` tras secuencias arbitrarias de `upsert` y `decay_step`.
- [x] 4.2 [GREEN] Implementar `BoundedMemory` en `src/ide/agent/memory.py`.
- [x] 4.3 [REFACTOR] Simplificar búsqueda y reemplazo; la suite sigue en verde.

## 5. Motor Epistemológico (`epistemic-engine`)

- [x] 5.1 [RED] Escribir `tests/test_epistemology.py` con los valores numéricos exactos de las specs: adquisición directa, refuerzo, ambas ramas de refutación, Escenario A (cadena y `sender_trust_factor`), Escenario B con emisor directo (refresca `τ`), anti-cámara de eco en 100 intercambios (no refresca `τ`), resistencia del Escenario C (incluido que `last_updated_tick` no cambie), sobrescritura de rumor débil y ablación de la protección anti-eco (`anti_echo_enabled=False`), y propiedades con Hypothesis: rangos `[-1, 1]` y `[0, 1]` para entradas válidas arbitrarias, y cota anti-eco en intercambios arbitrarios.
- [x] 5.2 [GREEN] Implementar `update_from_direct_experience` y `merge_social_belief` en `src/ide/agent/epistemology.py`.

## 6. Micro-Agente (`micro-agent`)

- [x] 6.1 [RED] Escribir `tests/test_micro_agent.py`: auditoría de imports con `ast`, auditoría del protocolo (sólo `protocol.py` construye `Message` o usa `MessageType`), `assimilate_testimony` como única entrada social, ablación de la navegación, firmas con `inspect.signature`, caché efímero (vida de un tick), emisión de consultas (límite y orden) y broadcasts (sólo con confianza suficiente), respuesta sólo desde memoria, asimilación con `TrustStrategyPort`, consumo de un benéfico conocido, exploración con ε = 1 y ε = 0, evitación de un tóxico, navegación por `recommended_move`, caminata e `IDLE`, y `learn_from_experience` con memoria llena.
- [x] 6.2 [GREEN] Implementar `BeliefExchangeProtocol` en `src/ide/agent/protocol.py` y `MicroAgent` en `src/ide/agent/micro_agent.py`.

## 7. Grilla 2D Toroidal (`spatial-environments`)

- [x] 7.1 [RED] Escribir `tests/test_grid2d.py`: generación canónica y determinista, cruce de bordes, distancia y `recommended_move` toroidales, filtro y orden de la observación, consistencia de `cell_agents`/`cell_resources`, colisión sobre el mismo recurso, reposición con IDs nuevos, `retire_pattern_resources`, `invert_world_rules`, `get_reachable_true_values` y movimiento inválido tratado como `IDLE`, y propiedades con Hypothesis: simetría de la distancia toroidal e ida y vuelta de movimientos.
- [x] 7.2 [GREEN] Implementar `ToroidalGrid2D` en `src/ide/environments/grid2d.py`.

## 8. Motor de Simulación (`simulation-engine`)

- [x] 8.1 [RED] Escribir `tests/test_simulation_engine.py`: `NotImplementedError` con especialización, `epsilon_recheck > 0`, `tau_policy="evidence_age"` o `update_scheme="asynchronous"`, sorteo de un recurso disputado según la permutación, orden de procesamiento idéntico con distintos `PYTHONHASHSEED` (subproceso), `capabilities` invariantes durante 100 ticks, `snapshot()` sin efectos secundarios, decisiones sobre la instantánea de la fase 1, consulta resuelta en el mismo tick, modo aislado sin creencias sociales y con 0 mensajes, registro de `direct_discoverers`, reproducibilidad bit a bit con 200 ticks, `inject_false_belief` (20 de 80), `ablate_population` (40 de 80), `ablate_discoverers` preservando al portador social y el control nulo (`comm_content_null`: determinismo, una extracción por entrega desde `null_rng`, y generador principal intacto en el primer tick), y propiedad con Hypothesis: determinismo de un motor pequeño para semillas arbitrarias.
- [x] 8.2 [GREEN] Implementar `SimulationEngine` en `src/ide/simulation/engine.py`.
- [x] 8.3 Implementar `src/ide/experiments/benchmark.py` (escenario de `quality-tooling`), ejecutarlo y registrar la línea base de ticks por segundo en `benchmark.json` y en el mensaje del commit.

## 9. Métricas y Protocolos (`experimental-suite`)

- [x] 9.1 [RED] Escribir `tests/test_metrics.py`: `knowledge_snapshot` con población vacía, cobertura accesible igual a la individual sin canal de consulta veraz, `windowed_accuracy` ponderada, validez de creencias, M1 (incluida la cota $C_{\max}/N$ y la cobertura accesible del meta-agente), `judge_decision` en sus cuatro casos, M2 sin oportunidades, `propagation_time` (incluido `None`), M6 y M7 (un broadcast cuenta una vez).
- [x] 9.2 [GREEN] Implementar `KnowledgeSnapshot`, `knowledge_snapshot`, `MetricsCollector`, `judge_decision`, `windowed_accuracy` y `propagation_time` en `src/ide/experiments/metrics.py`.
- [x] 9.3 [RED] Escribir `tests/test_exp001_suite.py`: esquemas exactos de los tres reportes con corridas cortas, `injected_agents == 20` y `target_pattern == "id=p_0"`, `remaining_agents` por nivel de ablación, ventana de `recovery_ticks` sin ticks previos a la ablación, `sign_test_p_value` (0.03125 con cinco positivas), `aggregate_reports` con `None`, valores por defecto de `build_arg_parser()` (incluido `--jobs 1`), salida idéntica con `--jobs 1` y `--jobs 2`, columnas del CSV, `report_to_dict` serializable y el test de determinismo entre procesos (CLI `--profile quick` con dos `PYTHONHASHSEED` distintos).
- [x] 9.4 [GREEN] Implementar los protocolos, `report_to_dict`, `aggregate_reports`, `sign_test_p_value`, `build_arg_parser`, el paralelismo entre corridas (`ProcessPoolExecutor`, reunión ordenada por clave) y la CLI en `src/ide/experiments/exp001_runner.py`.
- [x] 9.5 Escribir `tests/test_empirical.py` con `@pytest.mark.empirical` (expectativas funcionales: superávit H1 y contención de falsedad sobre las semillas 42..46), ejecutar `python -m pytest -m empirical` y registrar el resultado, positivo o negativo, sin ajustar parámetros.

## 10. Atribución de Emergencia (`emergence-attribution`)

- [ ] 10.1 [RED] Escribir `tests/test_attribution.py`: `DESIGN_RULES` (11 reglas, sólo R1 y R2 sin ablación), `ablate` (unión de overrides, validez de la configuración resultante y `ValueError` para reglas nucleares o inexistentes), `disables_communication`, `EXP001_CLAIMS` (R8 y R9 en C1, C2 y C4; C3 con R3, R4, R6 y R7) y `ATTRIBUTION_PROFILE == "quick"`, `nullify_belief` en `tests/test_controls.py` (`PCG64(0)`: valores en `{±1.0}`, resto intacto, fracción positiva `0.473`), `classify` con datos sintéticos para cada estado (incluidos `by_construction`, `EMERGENT_PENDING_ROBUSTNESS` sin variantes `async:*`, `SCHEDULING_ARTIFACT` y `EMERGENT` con variantes `async:*` sintéticas, la orientación `higher_is_better=False` e `INSUFFICIENT_EVIDENCE` con 3 semillas), `measure_claim` para cada protocolo con una configuración pequeña, la CLI con `--seeds 42 --attribution` (perfil `quick` forzado y aviso), y, marcado `@pytest.mark.slow`, el reporte completo con 5 semillas (`by_construction` en C1, C2 y C4, no en C3, y `rule_effects` con claves `R3`..`R11`).
- [ ] 10.2 [GREEN] Implementar `src/ide/simulation/controls.py` (`nullify_belief`), el control nulo en el motor, `src/ide/experiments/attribution.py` y la opción `--attribution` de la CLI.
- [ ] 10.3 Versionar `DESIGN_RULES` y `EXP001_CLAIMS` (pre-registro) **antes** de la primera corrida de 001-D; ejecutar `--seeds 42 43 44 45 46 --attribution` y registrar la tabla de estados y el perfil de contribución tal cual, sin modificar $R_c$ a la vista de los resultados.

## 11. Cierre

- [ ] 11.1 Ejecutar `ruff check`, `ruff format --check`, `pyright`, `python -m pytest -v --cov=ide`, `python -m pytest -m slow`, `python -m ide.experiments.exp001_runner --seeds 42 43 44 45 46` y verificar el checklist de Definition of Done de `design.md`.
- [ ] 11.2 Crear `README.md` con instalación, ejecución, estructura, la regla de atribución y enlaces a los documentos de fundamento.
