# Tasks: Fase II (v2.0) — Evolución Abierta, Herencia Dual y Arquitectura Holónica Recursiva

> **Verificación de cada bloque (CLAUDE.md).** Un bloque sólo está completo cuando pasan `ruff check`, `ruff format --check`, `pyright` y `python -m pytest --cov=ide`, y después `/code-review` sobre el cambio del bloque. Si el bloque toca specs, también `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict`. Un commit por bloque.
>
> **Decisiones P1–P3:** resueltas el 2026-10-18 (ver `proposal.md`). El pre-registro de la Fase II es design D29. Las constantes de `attribution.py` del bloque 6 deben coincidir **exactamente** con él; cambiar una exige un commit que lo justifique.

## 0. Decisiones y pre-registro

- [x] 0.1 Resolver P1 (canal de conocimiento del holón) y P2 (conocimiento de recursos compuestos). Actualizar `design.md` (D25 y D27), los specs delta, `DEFINICIONES_FORMALES.md`, `DEFINICIONES_TECNICAS.md` y, si cambia un invariante, `CLAUDE.md`.
- [x] 0.2 Resolver P3 y commitear el pre-registro de Fase II **antes** de implementar los runners y de mirar resultados: `PHASE2_DESIGN_RULES` (con `purpose`), `EXP002_CLAIMS`, `EXP003_CLAIMS`, variantes de comparación y perfil de corrida, reflejados en `DEFINICIONES_FORMALES.md` §3.1.

## 1. Contratos de Dominio, Configuración y Extensiones (`domain-contracts`, `roadmap-extensions`)

- [x] 1.1 **[RED]** Escribir tests en `tests/test_domain_contracts.py` y `tests/test_roadmap_extensions.py` para:
  - los nuevos tipos inmutables `AgentGenome`, `StigmergicTrace` y `HolonSnapshot`;
  - el sub-puerto `EvolutionaryEnvironmentPort`;
  - los hiperparámetros y validaciones de Fase II en `SimulationConfig`, incluidos `reproduction_mode`, `enable_holon_view` y `holon_energy_sharing`;
  - `mutate_genome` y `compute_epistemic_synergy`.

  Verificar que fallan, y que `VisibleResource`, `EnvironmentPort` y `CompositeRule` conservan sus campos y métodos de Fase I.
- [x] 1.2 **[GREEN]** Implementar:
  - `AgentGenome`, `StigmergicTrace` y `HolonSnapshot` en `src/ide/domain/types.py`;
  - `EvolutionaryEnvironmentPort` en `src/ide/domain/ports.py`;
  - los campos y validaciones de Fase II en `src/ide/config.py`;
  - `mutate_genome` y `compute_epistemic_synergy` en `src/ide/domain/extensions.py`.

  Actualizar los docstrings con la numeración de experimentos v2.
- [x] 1.3 **[REFACTOR]** Verificación del bloque.

## 2. Memoria con Penalización de Redundancia y Dinámica Evolutiva (`bounded-memory`, `evolutionary-dynamics`, `micro-agent`)

- [x] 2.1 **[RED]** Crear `tests/test_evolutionary_dynamics.py` y ampliar `tests/test_memory.py` y `tests/test_micro_agent.py` con tests para:
  - (a) `set_redundant_patterns` y la modulación de utilidad por `redundancy_penalty` ($\psi_{\text{red}}$, $R_{18}$) en `BoundedMemory`;
  - (b) `genome_from_config` y `compute_metabolic_cost` en `src/ide/agent/evolution.py`;
  - (c) `transfer_cultural_heritage` como función pura con descuento $\gamma_{\text{gen}}$ ($R_{14}$);
  - (d) las propiedades de `AgentNode` ($L=0$), el estado energético, el linaje, `own_belief`, `apply_energy_delta`, `from_lineage` y `create_offspring` en `MicroAgent`, sin modificar las 8 firmas canónicas de Fase I;
  - (e) que `evolution.py` no importa `micro_agent.py` y que ningún archivo de `src/ide/agent/` referencia `nullify_belief`.
- [x] 2.2 **[GREEN]** Implementar:
  - `set_redundant_patterns` en `src/ide/agent/memory.py`;
  - `src/ide/agent/evolution.py` (`genome_from_config`, `compute_metabolic_cost`, `transfer_cultural_heritage`);
  - en `MicroAgent`: `energy`, `generation`, `parent_id`, `genome`, `node_id`, `holon_level`, `leaf_agents`, `effective_capacity`, `collective_memory`, `own_belief`, `apply_energy_delta`, `from_lineage` y `create_offspring`;
  - `clear_holon_beliefs` e `inject_ephemeral_belief` (vista del holón, $R_{22}$), con los requisitos `MODIFIED` de `micro-agent`.
- [x] 2.3 **[REFACTOR]** Pruebas por propiedades con Hypothesis (perfil `ci`) sobre `mutate_genome` (cotas y aceptación por `SimulationConfig`) y `transfer_cultural_heritage`; auditorías AST de `tests/test_micro_agent.py`; verificación del bloque.

## 3. Jerarquía Holónica Recursiva (`holonic-hierarchy`)

- [x] 3.1 **[RED]** Crear `tests/test_holonic_hierarchy.py` con tests para:
  - (a) el protocolo `AgentNode` y la construcción recursiva de `CompositeAgent` en $L = 1, 2, 3, 4$;
  - (b) `ValueError` con menos de 2 hijos o con hojas duplicadas;
  - (c) `collective_memory()` con desempate determinista;
  - (d) `evaluate_bond_candidates` ($R_{15}$) entre especialistas complementarios, y el rechazo de clones;
  - (e) `should_split_holon` ($R_{16}$) por paciencia o por energía mínima;
  - (f) `apply_downward_causation` ($R_{18}$) con alcance local;
  - (g) `reproduce_holon` ($R_{17}$) preservando la topología, con `formed_by_bond = False` y `formation_tick = tick` en todos los nodos replicados;
  - (h) `prune_dead_leaves` con colapso de sub-holones.
- [x] 3.2 **[GREEN]** Implementar `src/ide/agent/holon.py` con `AgentNode`, `CompositeAgent`, `prune_dead_leaves`, `evaluate_bond_candidates`, `should_split_holon`, `apply_downward_causation` y `reproduce_holon`, según las firmas de design D23.
- [x] 3.3 **[REFACTOR]** Verificación del bloque.

## 4. Entorno Espacial Evolutivo (`spatial-environments`)

- [x] 4.1 **[RED]** Ampliar `tests/test_grid2d.py` con tests para:
  - (a) `spawn_agent_near` (celdas de menor ocupación en `((0, 0), *MOORE_MOVES)`), `set_agent_radii` y `get_agent_distance`;
  - (b) la generación cíclica y la reposición de recursos compuestos con `_comp_rng` (`spawn_key=(3,)`), sin consumir el `rng` de Fase I cuando `num_composite_patterns == 0`;
  - (c) el depósito independiente del orden, la consulta y el decaimiento de `StigmergicTrace` ($R_{19}$).
- [x] 4.2 **[GREEN]** Implementar en `src/ide/environments/grid2d.py`:
  - `spawn_agent_near`, `set_agent_radii` y `get_agent_distance`;
  - `get_composite_rules`;
  - `deposit_stigmergy`, `get_cell_stigmergy` y `get_active_stigmergy_cells`;
  - el decaimiento estigmérgico.
- [x] 4.3 **[REFACTOR]** `python -m pytest tests/test_grid2d.py tests/test_performance_equivalence.py` (hashes de Fase I intactos) y verificación del bloque.

## 5. Motor de Simulación Evolutivo y Holónico (`simulation-engine`)

- [x] 5.1 **[RED]** Ampliar `tests/test_simulation_engine.py` con tests para:
  - (a) el aislamiento de `evo_rng` (`spawn_key=(2,)`);
  - (b) la vista del holón en dos tiempos sin efectos de orden y su ablación (`enable_holon_view`, $R_{22}$); los recursos compuestos aprendidos por experiencia, sin inyección, con reparto de energía y su ablación (`holon_energy_sharing`, $R_{23}$); y la exclusión de compuestos en M2;
  - (c) la Fase 5: metabolismo, muerte ($E_i \le 0$), poda en `_remove` (incluidas las ablaciones), a lo sumo una reproducción por agente y por tick, reproducción neutral (`reproduction_mode="neutral"`, $R_{12}$), herencia cultural por `assimilate_testimony` (con control nulo aplicado por el motor), $R_{18}$, `SPLIT` y `BOND`;
  - (d) `engine.evolutionary_history`, y que el motor completa `formation_knowledge` al crear un holón y reinicia el estado de formación (con `formation_tick`) cuando un holón pierde un miembro, también desde `ablate_population`;
  - (e) igualdad de historiales entre procesos con distinto `PYTHONHASHSEED` con todas las banderas de Fase II activas.
- [x] 5.2 **[GREEN]** Extender `SimulationEngine` en `src/ide/simulation/engine.py` y agregar `EvolutionaryMetricsCollector` en `src/ide/experiments/metrics.py`, manteniendo bit a bit la Fase I con los valores por defecto.
- [x] 5.3 **[REFACTOR]** `python -m pytest tests/test_simulation_engine.py tests/test_performance_equivalence.py`, `python -m ide.experiments.benchmark` (comparar ticks por segundo con la línea base) y verificación del bloque.

## 6. Telemetría M8–M13, Protocolos 002/003 y Atribución R12–R23 (`experimental-suite`, `emergence-attribution`)

- [x] 6.1 **[RED]** Crear `tests/test_exp002_exp003.py` y ampliar `tests/test_metrics.py` y `tests/test_attribution.py` con tests para:
  - (a) `EvolutionaryTickMetrics` (M8–M13, incluida la cobertura colectiva adquirida (y la reducción de redundancia descriptiva) con `formation_knowledge`, holones elegibles por `BOND`, reinicio del estado de formación con `formation_tick` cuando el holón pierde un miembro y media por par tick-holón) sin alterar los 14 campos de `TickMetrics`;
  - (b) `PHASE2_DESIGN_RULES` (`R12`–`R23`) con `purpose`, `ALL_DESIGN_RULES`, `PHASE2_CLAIM_CHANNELS`, el criterio ampliado de `is_by_construction`, el perfil `phase2`, `PHASE2_SEEDS`, `PHASE2_PROTOCOL_CONFIGS`, `run_phase2_attribution` (una sola condición por variante) y las variantes pre-registradas para `EXP002_CLAIMS` y `EXP003_CLAIMS` (para C8, la ablación de `R22`) y `PHASE2_INACTIVE_RULES` fuera de `rule_effects` (con el test que la contrasta con `PHASE2_PROTOCOL_CONFIGS`), preservando `report.rules == DESIGN_RULES` y `rule_effects == R3..R11` para `EXP001_CLAIMS`;
  - (c) la ejecución y la serialización JSON/CLI de los cuatro protocolos 002 y 003.
- [x] 6.2 **[GREEN]** Antes de los runners, correr la prueba de humo de design D29 (sólo termina y generación máxima, sin mirar las métricas de las afirmaciones) y registrar su salida. Implementar las métricas en `src/ide/experiments/metrics.py`, extender `src/ide/experiments/attribution.py` y crear `src/ide/experiments/exp002_runner.py` y `src/ide/experiments/exp003_runner.py`.
- [x] 6.3 **[REFACTOR]** Verificación completa:
  - `ruff check`, `ruff format --check`, `pyright` y `python -m pytest --cov=ide` (cobertura $\ge 90\%$);
  - `python -m pytest -m slow`;
  - `openspec validate --all --strict`;
  - actualizar `.github/workflows/ci.yml` si cambian los pasos de verificación.

- [ ] 6.4 Calibración de viabilidad (Enmienda 1 de design D29): declarar y testear el procedimiento en `src/ide/experiments/phase2_calibration.py` **antes** de ejecutarlo; correrlo, registrar su salida en `RESULTADOS.md` e incorporar el valor elegido a `PHASE2_PROTOCOL_CONFIGS`, sin mirar las métricas de las afirmaciones. Si ningún valor es viable, consultar.

## 7. Corridas y registro

- [ ] 7.1 Correr los protocolos 002 y 003 con el perfil pre-registrado y registrar los resultados, incluidos los negativos, en `RESULTADOS.md`, sin tocar el pre-registro.
- [ ] 7.2 Actualizar `CLAUDE.md` (estado y comandos nuevos) y `README.md`.
