# Tasks: Fase II-B (v2.5) — ADN Compacto de 32 bits, Regulación Génica, Epigenética, Plásmidos y Senescencia

> **Verificación de cada bloque (CLAUDE.md).** Un bloque sólo está completo cuando pasan `ruff check`, `ruff format --check`, `pyright` y `python -m pytest --cov=ide`, y después `/code-review` sobre el cambio del bloque. Si el bloque toca specs, también corre `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict`. Un commit por bloque.
>
> **Etapas.** El orden es deliberado:
> - primero $R_{24}$ sola (bloques 1 a 5), verificada contra la Fase II;
> - después cada mecanismo en su propio bloque (6 a 9), con su bandera y su ablación;
> - por último la telemetría, los protocolos y las corridas (10 y 11).
>
> **Compatibilidad.** Ningún bloque puede cambiar los hashes dorados de la Fase I ni los historiales de la Fase II con las banderas por defecto.
>
> **Decisiones P4–P7** (ver `proposal.md`). Se resuelven en el bloque 0, **antes** del bloque 1. El pre-registro es design D42. Las constantes de `attribution.py` del bloque 10 deben coincidir **exactamente** con él.

## 0. Decisiones y pre-registro

- [x] 0.1 **Diagnóstico demográfico previo (decisión P5).** Resultado: hipótesis **confirmada** en las 10 semillas de los dos protocolos (`docs/RESULTADOS.md`). Mide la demografía de la Fase II con `resources_per_pattern = 40`:
  - muertes, nacimientos y edad al morir por tick;
  - con `PHASE2_PROTOCOL_CONFIGS_ORIGINAL["002a"]` y `["003a"]`, y las semillas de calibración 0 a 9.
  - **No** calcula ninguna métrica de afirmación.
  - Aplica el criterio fijado de antemano en design D42: la hipótesis se confirma si, en al menos 8 de 10 semillas de cada protocolo, más de la mitad de los agentes vivos en el tick 2000 nació antes del tick 1000.
  - Registra la salida en `registros/` y en `docs/RESULTADOS.md` como diagnóstico exploratorio de la hipótesis del "Tapón de Matusalén".
- [ ] 0.2 **Resolver P4–P7 con el responsable del proyecto:**
  - aprobar o corregir D42: inventario, afirmaciones, configuraciones, perfil, reglas inactivas y E4;
  - aprobar los valores por defecto de D31;
  - según el diagnóstico de 0.1, decidir si $R_{29}$ y C10 se mantienen;
  - aprobar los sesgos declarados (P6) y el tratamiento del Exp 004 (P7).
  - Registrar las decisiones con fecha en `proposal.md`.
- [ ] 0.3 **Reflejar el diseño aprobado en los documentos raíz:**
  - `docs/DEFINICIONES_FORMALES.md`: §3.1 con el inventario $R_{24}$–$R_{31}$ y las afirmaciones C9–C12, más una sección del modelo genético;
  - `docs/DEFINICIONES_TECNICAS.md`: tipos, configuración y ciclo del tick;
  - `docs/vision/ROADMAP.md` y `docs/vision/ARQUITECTURA_ADN_HOLONICO.md`, si cambió algo respecto del borrador.
  - Commitear el pre-registro aprobado.

## 1. Contratos de dominio y configuración (`domain-contracts`)

- [ ] 1.1 **[RED]** Ampliar `tests/test_domain_contracts.py` con tests para:
  - los tipos `EpigeneticRole`, `CompactDNA` (validación de codones, cromosoma no vacío y plásmidos y firmas sin repetidos), `EpigeneticContext` y `ExpressedPhenotype`, todos inmutables;
  - los campos de D31 con sus valores por defecto y la validación siempre activa;
  - la validación condicionada a `enable_compact_dna=True`: requisitos, bases dentro de sus cotas y mensajes que mencionan el campo;
  - que las dependencias apagadas dejan las banderas inertes y no lanzan error (D30.3).
- [ ] 1.2 **[GREEN]** Implementar los tipos en `src/ide/domain/types.py` y los campos y validaciones en `src/ide/config.py`.
- [ ] 1.3 **[REFACTOR]** Verificación del bloque, con `tests/test_performance_equivalence.py` intacto.

## 2. Codón, ADN fundador y transcripción (`compact-dna`)

- [ ] 2.1 **[RED]** Crear `tests/test_compact_dna.py` con tests para:
  - (a) `encode_codon` y `decode_codon`: ida y vuelta, campos, `delta` en los extremos ($-128 \to -1.0$, $127 \to 0.9921875$) y `ValueError` fuera de rango;
  - (b) `founder_dna`: longitud 9 y expresión de `genome_from_config` en cualquier contexto;
  - (c) cada promotor de D32, incluidos los reservados, que nunca se activan;
  - (d) la fórmula de D33 con los modos aditivo, represor y multiplicativo, el modo 3 inerte, el redondeo `floor(x + 0.5)` y las cotas;
  - (e) la red regulatoria: canal encendido sólo si `act > rep`, la pasada 2, y que los `EMIT_TF` de la pasada 2 no encienden canales;
  - (f) que los destinos reservados son inertes y que los plásmidos se transcriben y `crispr_memory` no;
  - (g) `phenotype_from_genome`.
- [ ] 2.2 **[GREEN]** Crear `src/ide/agent/dna.py` con `Codon`, `encode_codon`, `decode_codon`, `FOUNDER_DNA_LENGTH`, `founder_dna`, `transcribe_phenotype` y `phenotype_from_genome`.
- [ ] 2.3 **[REFACTOR]** Agregar pruebas por propiedades con Hypothesis (perfil `ci`):
  - toda transcripción cae dentro de las cotas;
  - el resultado no depende de `PYTHONHASHSEED`;
  - el ADN fundador es neutro para toda configuración válida.
  - Agregar la auditoría AST: `dna.py` no importa `micro_agent`, `holon`, `environments`, `simulation` ni `experiments`.
  - Verificación del bloque.

## 3. Mutación del ADN (`compact-dna`)

- [ ] 3.1 **[RED]** Tests de `mutate_dna`:
  - puerta de $R_{13}$ sin consumir `rng`;
  - mutación puntual de bit, duplicación y deleción con sus cotas de longitud;
  - escisión a plásmido sólo con `enable_plasmid_hgt`, con FIFO y exclusión de los codones de `crispr_memory`;
  - `crispr_memory` sin mutar;
  - escala `scale` con tope 1;
  - secuencia exacta de extracciones de D35, verificada con un generador sembrado.
- [ ] 3.2 **[GREEN]** Implementar `mutate_dna` en `dna.py`.
- [ ] 3.3 **[REFACTOR]** Pruebas por propiedades: el ADN mutado siempre es válido y respeta `dna_min_length` y `dna_max_length`. Verificación del bloque.

## 4. Agente y memoria (`micro-agent`, `bounded-memory`, `evolutionary-dynamics`)

- [ ] 4.1 **[RED]** Ampliar `tests/test_memory.py`, `tests/test_micro_agent.py` y `tests/test_evolutionary_dynamics.py` con tests para:
  - (a) `BoundedMemory.resize`: desalojo por menor utilidad con el desempate de $R_2$ y la penalización de $R_{18}$, sin borrar al agrandar, y `ValueError` con capacidad menor que 1;
  - (b) el estado nuevo de `MicroAgent` (D34.1), sin cambiar las 8 firmas de la Fase I ni el comportamiento sin ADN;
  - (c) `express`: reemplazo del genoma y de la configuración fenotípica, `resize` de la memoria, el valor de retorno con los radios, y el caché igual a la transcripción directa;
  - (d) bases tomadas de `base_config`, sin acumulación tick a tick;
  - (e) `create_offspring` con `dna_source` y `mutation_scale`, herencia de plásmidos y firmas sin ensayos, expresión al nacer y `birth_tick`;
  - (f) `compute_dna_cost`.
- [ ] 4.2 **[GREEN]** Implementar `resize` en `memory.py`, el estado y los métodos de `MicroAgent`, y `compute_dna_cost` en `evolution.py`.
- [ ] 4.3 **[REFACTOR]** Auditorías AST de `tests/test_micro_agent.py` y verificación del bloque.

## 5. Motor con ADN, R24 (`simulation-engine`)

- [ ] 5.1 **[RED]** Ampliar `tests/test_simulation_engine.py` con tests para:
  - (a) la Fase 0: contexto con nivel, rol y energía; `set_agent_radii` sólo si cambian los radios; sin consumo de generadores;
  - (b) el costo metabólico sobre el genoma expresado más `compute_dna_cost`;
  - (c) el nacimiento con ADN mutado por `evo_rng` y expresado en el acto;
  - (d) la reproducción neutral con el ADN del donante;
  - (e) la igualdad de historiales entre procesos con distinto `PYTHONHASHSEED` con `enable_compact_dna=True`;
  - (f) con las banderas por defecto, historiales de los protocolos `002a` y `003a` idénticos a los de la Fase II.
- [ ] 5.2 **[GREEN]** Extender `SimulationEngine`: `_express_phenotypes`, el costo y el nacimiento.
- [ ] 5.3 **[REFACTOR]** Correr `python -m pytest tests/test_simulation_engine.py tests/test_performance_equivalence.py` y `python -m ide.experiments.benchmark` con y sin ADN, y registrar los ticks por segundo. Verificación del bloque.

## 6. Senescencia (R29) y mutación SOS (R30) (`evolutionary-dynamics`, `simulation-engine`)

- [ ] 6.1 **[RED]** Tests para:
  - `compute_senescence_cost`;
  - la edad y la longevidad expresada (con y sin ADN);
  - el cobro también a las endosporas;
  - el registro de `last_stress_tick`;
  - las tres escalas de SOS decididas antes de partir la energía, por hoja en la reproducción holónica;
  - la escala 1.0 con la regla apagada, con Fase II bit a bit.
- [ ] 6.2 **[GREEN]** Implementar D39.
- [ ] 6.3 **[REFACTOR]** Verificación del bloque.

## 7. Esporulación (R28) (`evolutionary-dynamics`, `simulation-engine`)

- [ ] 7.1 **[RED]** Tests para:
  - la entrada en endospora (umbral expresado, sin recursos visibles, sin rastro positivo con $R_{19}$, sin evaluar a los recién nacidos);
  - la germinación en la Fase 1;
  - la física de la endospora: sin emisión ni recepción de mensajes, `IDLE` sin `decide_action` ni consumo de `rng`, sin oportunidad de decisión en M2, sin reproducción, y el costo `spore_cost_fraction * metabolic_base_cost`.
- [ ] 7.2 **[GREEN]** Implementar D38.
- [ ] 7.3 **[REFACTOR]** Verificación del bloque.

## 8. Roles epigenéticos (R25) y trinquete simbiótico (R31) (`holonic-hierarchy`, `simulation-engine`)

- [ ] 8.1 **[RED]** Ampliar `tests/test_holonic_hierarchy.py` y `tests/test_simulation_engine.py` con tests para:
  - (a) `assign_epigenetic_roles`: `LIBRARIAN`, `EXPLORER` y `NERVE` con sus desempates, holones de 2 hojas, todo en `NONE` con la regla apagada, y la validación de `local_reach` también apagada;
  - (b) la asignación del motor sólo al cambiar la composición, el regreso a `NONE` de las hojas sueltas, y la impronta en $R_{17}$;
  - (c) el sello de $R_{31}$ por reproducción y por compuestos, `should_split_holon` en `False`, el descuento de coordinación, la poda con sello y la conservación del sello al quedar como raíz.
- [ ] 8.2 **[GREEN]** Implementar D36 y D40.
- [ ] 8.3 **[REFACTOR]** Verificación del bloque.

## 9. Plásmidos (R26) e inmunidad CRISPR (R27) (`compact-dna`, `simulation-engine`)

- [ ] 9.1 **[RED]** Tests para:
  - `receive_plasmid` (bloqueo, duplicado y FIFO) y `purge_plasmid` (FIFO de firmas);
  - la conjugación con `hgt_rng` (`spawn_key=(5,)`): donantes y candidatos fijados al empezar el paso, sin endosporas, la secuencia exacta de extracciones de D37 y la aplicación después del sorteo;
  - la apertura y el cierre de ensayos CRISPR, la purga por toxicidad y el cierre sin purga si el plásmido se perdió;
  - que `hgt_rng` no se consume con $R_{26}$ apagada;
  - la igualdad entre procesos con distinto `PYTHONHASHSEED`.
- [ ] 9.2 **[GREEN]** Implementar D37.
- [ ] 9.3 **[REFACTOR]** Verificación del bloque.

## 10. Telemetría, protocolos y atribución (`experimental-suite`, `emergence-attribution`)

- [ ] 10.1 **[RED]** Crear `tests/test_exp25.py` y ampliar `tests/test_metrics.py` y `tests/test_attribution.py` con tests para:
  - `GeneticTickMetrics` y `engine.genetic_history`, sin alterar `TickMetrics` ni `EvolutionaryTickMetrics`;
  - `PHASE25_DESIGN_RULES` con su `purpose`, `PHASE25_ALL_RULES`, `ablate()` con las reglas nuevas, `PHASE25_PROTOCOL_CONFIGS`, `PHASE25_CLAIMS` y `PHASE25_INACTIVE_RULES` (contrastadas con las configuraciones), y E4 declarado de antemano;
  - `run_phase25_attribution`, con `is_phase25_claim`, `PHASE25_CLAIM_CHANNELS`, `PHASE25_METRIC_FIELDS` y `PHASE25_E4_INTERPRETABLE` (design D42), incluido que `002e` da `e4_interpretable=False` aunque su abundancia no sea la de la Fase II;
  - que los reportes de atribución de C5–C8 no cambian;
  - la ejecución y la serialización JSON y CLI de los cuatro protocolos.
- [ ] 10.2 **[GREEN]** Correr la prueba de humo de D42 **antes** de los runners, sin mirar las métricas de las afirmaciones, y registrar su salida. Después:
  - implementar `GeneticTickMetrics`;
  - extender `attribution.py` con lo aprobado en 0.2;
  - crear `src/ide/experiments/exp25_runner.py`.
- [ ] 10.3 **[REFACTOR]** Verificación completa:
  - `ruff check`, `ruff format --check`, `pyright` y `python -m pytest --cov=ide` (cobertura $\ge 90\%$);
  - `python -m pytest -m slow`;
  - `openspec validate --all --strict`;
  - actualizar `.github/workflows/ci.yml` si cambian los pasos de verificación.

## 11. Corridas y registro

- [ ] 11.1 Correr los cuatro protocolos y su atribución con el perfil pre-registrado, y registrar todos los resultados, incluidos los negativos, en `docs/RESULTADOS.md`, sin tocar el pre-registro.
- [ ] 11.2 Actualizar `CLAUDE.md` (estado y comandos), `README.md` y los documentos de `docs/`.
- [ ] 11.3 Completar la Definition of Done de `design.md` con su evidencia y archivar el cambio.
