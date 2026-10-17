# Tasks: Fase II (v2.0) — Evolución Abierta, Herencia Dual y Arquitectura Holónica Recursiva

> **Verificación de cada bloque (CLAUDE.md).** Un bloque sólo está completo cuando pasan `ruff check`, `ruff format --check`, `pyright` y `python -m pytest --cov=ide`, y después `/code-review` sobre el cambio del bloque. Si el bloque toca specs, también `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict`. Un commit por bloque.
>
> **Decisiones abiertas** (ver `proposal.md`): P1 bloquea los bloques 3 y 5, P2 los bloques 4 y 5, y P3 el bloque 6. Los bloques 1 y 2 no dependen de ellas, salvo los métodos de la vista del holón de la tarea 2.2 (`own_belief`, `clear_holon_beliefs`, `inject_ephemeral_belief`), que dependen de P1.

## 0. Decisiones abiertas y pre-registro

- [ ] 0.1 Resolver P1 (canal de conocimiento del holón) y P2 (conocimiento de recursos compuestos). Actualizar `design.md` (D25 y D27), los specs delta, `DEFINICIONES_FORMALES.md`, `DEFINICIONES_TECNICAS.md` y, si cambia un invariante, `CLAUDE.md`.
- [ ] 0.2 Resolver P3 y commitear el pre-registro de Fase II **antes** de implementar los runners y de mirar resultados: `PHASE2_DESIGN_RULES` (con `purpose`), `EXP002_CLAIMS`, `EXP003_CLAIMS`, variantes de comparación y perfil de corrida, reflejados en `DEFINICIONES_FORMALES.md` §3.1.

## 1. Contratos de Dominio, Configuración y Extensiones (`domain-contracts`, `roadmap-extensions`)

- [ ] 1.1 **[RED]** Escribir tests en `tests/test_domain_contracts.py` y `tests/test_roadmap_extensions.py` para:
  - los nuevos tipos inmutables `AgentGenome`, `StigmergicTrace` y `HolonSnapshot`;
  - el sub-puerto `EvolutionaryEnvironmentPort`;
  - los hiperparámetros y validaciones de Fase II en `SimulationConfig`;
  - `mutate_genome` y `compute_epistemic_synergy`.

  Verificar que fallan, y que `VisibleResource`, `EnvironmentPort` y `CompositeRule` conservan sus campos y métodos de Fase I.
- [ ] 1.2 **[GREEN]** Implementar:
  - `AgentGenome`, `StigmergicTrace` y `HolonSnapshot` en `src/ide/domain/types.py`;
  - `EvolutionaryEnvironmentPort` en `src/ide/domain/ports.py`;
  - los campos y validaciones de Fase II en `src/ide/config.py`;
  - `mutate_genome` y `compute_epistemic_synergy` en `src/ide/domain/extensions.py`.

  Actualizar los docstrings con la numeración de experimentos v2.
- [ ] 1.3 **[REFACTOR]** Verificación del bloque.

## 2. Memoria con Penalización de Redundancia y Dinámica Evolutiva (`bounded-memory`, `evolutionary-dynamics`, `micro-agent`)

- [ ] 2.1 **[RED]** Crear `tests/test_evolutionary_dynamics.py` y ampliar `tests/test_memory.py` y `tests/test_micro_agent.py` con tests para:
  - (a) `set_redundant_patterns` y la modulación de utilidad por `redundancy_penalty` ($\psi_{\text{red}}$, $R_{18}$) en `BoundedMemory`;
  - (b) `genome_from_config` y `compute_metabolic_cost` en `src/ide/agent/evolution.py`;
  - (c) `transfer_cultural_heritage` como función pura con descuento $\gamma_{\text{gen}}$ ($R_{14}$);
  - (d) las propiedades de `AgentNode` ($L=0$), el estado energético, el linaje, `own_belief`, `apply_energy_delta`, `from_lineage` y `create_offspring` en `MicroAgent`, sin modificar las 8 firmas canónicas de Fase I;
  - (e) que `evolution.py` no importa `micro_agent.py` y que ningún archivo de `src/ide/agent/` referencia `nullify_belief`.
- [ ] 2.2 **[GREEN]** Implementar:
  - `set_redundant_patterns` en `src/ide/agent/memory.py`;
  - `src/ide/agent/evolution.py` (`genome_from_config`, `compute_metabolic_cost`, `transfer_cultural_heritage`);
  - en `MicroAgent`: `energy`, `generation`, `parent_id`, `genome`, `node_id`, `holon_level`, `leaf_agents`, `effective_capacity`, `collective_memory`, `apply_energy_delta`, `from_lineage` y `create_offspring`;
  - si P1 se resolvió por la variante (a): `own_belief`, `clear_holon_beliefs` e `inject_ephemeral_belief`, con el requisito `MODIFIED` de `micro-agent`.
- [ ] 2.3 **[REFACTOR]** Pruebas por propiedades con Hypothesis (perfil `ci`) sobre `mutate_genome` (cotas y aceptación por `SimulationConfig`) y `transfer_cultural_heritage`; auditorías AST de `tests/test_micro_agent.py`; verificación del bloque.

## 3. Jerarquía Holónica Recursiva (`holonic-hierarchy`) — requiere P1

- [ ] 3.1 **[RED]** Crear `tests/test_holonic_hierarchy.py` con tests para:
  - (a) el protocolo `AgentNode` y la construcción recursiva de `CompositeAgent` en $L = 1, 2, 3, 4$;
  - (b) `ValueError` con menos de 2 hijos o con hojas duplicadas;
  - (c) `collective_memory()` con desempate determinista;
  - (d) `evaluate_bond_candidates` ($R_{15}$) entre especialistas complementarios, y el rechazo de clones;
  - (e) `should_split_holon` ($R_{16}$) por paciencia o por energía mínima;
  - (f) `apply_downward_causation` ($R_{18}$) con alcance local;
  - (g) `reproduce_holon` ($R_{17}$) preservando la topología;
  - (h) `prune_dead_leaves` con colapso de sub-holones.
- [ ] 3.2 **[GREEN]** Implementar `src/ide/agent/holon.py` con `AgentNode`, `CompositeAgent`, `prune_dead_leaves`, `evaluate_bond_candidates`, `should_split_holon`, `apply_downward_causation` y `reproduce_holon`, según las firmas de design D23.
- [ ] 3.3 **[REFACTOR]** Verificación del bloque.

## 4. Entorno Espacial Evolutivo (`spatial-environments`) — la parte compuesta requiere P2

- [ ] 4.1 **[RED]** Ampliar `tests/test_grid2d.py` con tests para:
  - (a) `spawn_agent_near` (celdas de menor ocupación en `((0, 0), *MOORE_MOVES)`), `set_agent_radii` y `get_agent_distance`;
  - (b) la generación cíclica y la reposición de recursos compuestos con `_comp_rng` (`spawn_key=(3,)`), sin consumir el `rng` de Fase I cuando `num_composite_patterns == 0`;
  - (c) el depósito independiente del orden, la consulta y el decaimiento de `StigmergicTrace` ($R_{19}$).
- [ ] 4.2 **[GREEN]** Implementar en `src/ide/environments/grid2d.py`:
  - `spawn_agent_near`, `set_agent_radii` y `get_agent_distance`;
  - `get_composite_rules`;
  - `deposit_stigmergy`, `get_cell_stigmergy` y `get_active_stigmergy_cells`;
  - el decaimiento estigmérgico.
- [ ] 4.3 **[REFACTOR]** `python -m pytest tests/test_grid2d.py tests/test_performance_equivalence.py` (hashes de Fase I intactos) y verificación del bloque.

## 5. Motor de Simulación Evolutivo y Holónico (`simulation-engine`) — requiere P1 y P2

- [ ] 5.1 **[RED]** Ampliar `tests/test_simulation_engine.py` con tests para:
  - (a) el aislamiento de `evo_rng` (`spawn_key=(2,)`);
  - (b) la sincronización en dos tiempos sin efectos de orden, y la exclusión de compuestos en M2;
  - (c) la Fase 5: metabolismo, muerte ($E_i \le 0$), poda en `_remove` (incluidas las ablaciones), a lo sumo una reproducción por agente y por tick, herencia cultural por `assimilate_testimony` (con control nulo aplicado por el motor), $R_{18}$, `SPLIT` y `BOND`;
  - (d) `engine.evolutionary_history`;
  - (e) igualdad de historiales entre procesos con distinto `PYTHONHASHSEED` con todas las banderas de Fase II activas.
- [ ] 5.2 **[GREEN]** Extender `SimulationEngine` en `src/ide/simulation/engine.py` y agregar `EvolutionaryMetricsCollector` en `src/ide/experiments/metrics.py`, manteniendo bit a bit la Fase I con los valores por defecto.
- [ ] 5.3 **[REFACTOR]** `python -m pytest tests/test_simulation_engine.py tests/test_performance_equivalence.py`, `python -m ide.experiments.benchmark` (comparar ticks por segundo con la línea base) y verificación del bloque.

## 6. Telemetría M8–M12, Protocolos 002/003 y Atribución R12–R19 (`experimental-suite`, `emergence-attribution`) — requiere P3

- [ ] 6.1 **[RED]** Crear `tests/test_exp002_exp003.py` y ampliar `tests/test_metrics.py` y `tests/test_attribution.py` con tests para:
  - (a) `EvolutionaryTickMetrics` (M8–M12) sin alterar los 14 campos de `TickMetrics`;
  - (b) `PHASE2_DESIGN_RULES` con `purpose`, `ALL_DESIGN_RULES`, el parámetro `rules` de `run_protocol_001d_attribution` y las variantes pre-registradas para `EXP002_CLAIMS` y `EXP003_CLAIMS`, preservando `report.rules == DESIGN_RULES` y `rule_effects == R3..R11` para `EXP001_CLAIMS`;
  - (c) la ejecución y la serialización JSON/CLI de los cuatro protocolos 002 y 003.
- [ ] 6.2 **[GREEN]** Implementar las métricas en `src/ide/experiments/metrics.py`, extender `src/ide/experiments/attribution.py` y crear `src/ide/experiments/exp002_runner.py` y `src/ide/experiments/exp003_runner.py`.
- [ ] 6.3 **[REFACTOR]** Verificación completa:
  - `ruff check`, `ruff format --check`, `pyright` y `python -m pytest --cov=ide` (cobertura $\ge 90\%$);
  - `python -m pytest -m slow`;
  - `openspec validate --all --strict`;
  - actualizar `.github/workflows/ci.yml` si cambian los pasos de verificación.

## 7. Corridas y registro

- [ ] 7.1 Correr los protocolos 002 y 003 con el perfil pre-registrado y registrar los resultados, incluidos los negativos, en `RESULTADOS.md`, sin tocar el pre-registro.
- [ ] 7.2 Actualizar `CLAUDE.md` (estado y comandos nuevos) y `README.md`.
