# Tasks: Fase II-B (v2.5) — ADN Compacto de 32 bits, Conducta Evolucionable y Ecología

> **Verificación de cada bloque (CLAUDE.md).** Un bloque sólo está completo cuando pasan `ruff check`, `ruff format --check`, `pyright` y `python -m pytest --cov=ide`, y después `/code-review` sobre el cambio del bloque. Si el bloque toca specs, también corre `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict`. Un commit por bloque.
>
> **Reformulación del 2026-10-20 (design D43–D56).** Con la etapa A completa, la Fase II-B se reformuló para corregir las cuestiones de base de la Fase II: conducta codificada en el ADN, ecología con interacciones físicas, motor por sistemas y medición de evolución abierta. Los bloques 1 a 5 se conservan. Los bloques 6 en adelante reemplazan a los anteriores 6 a 12. La ampliación del 2026-10-21 (design D57–D63: estado interno, plasticidad, señales, entorno cambiante y detección de núcleos) agrega la etapa L.
>
> **Etapas.** El orden es deliberado. Cada etapa termina en un **punto de control**: la ejecución se detiene y espera al responsable del proyecto.
>
> | Etapa | Bloques | Qué contiene | Punto de control al final |
> | :--- | :--- | :--- | :--- |
> | A | 1 a 5 | $R_{24}$ sola, verificada contra la Fase II | completa |
> | R | 6 y 7 | refactor sin cambio de conducta: motor por sistemas y puerto de política | hashes dorados, huellas de la Fase II y benchmark |
> | B | 8 a 12 | conducta en el ADN y ecología ($R_{32}$–$R_{37}$) | fundador genético igual a la política escrita a mano; ablaciones y determinismo |
> | L | 13 a 15 | memoria, aprendizaje y señales construidos por la evolución ($R_{39}$–$R_{41}$, ampliación D57–D63) | ablaciones, fundador neutro y determinismo |
> | M | 16 a 20 | mecanismos del ADN ($R_{25}$–$R_{31}$, $R_{38}$) | ablaciones y determinismo de los mecanismos |
> | C | 21 a 25 | telemetría, atribución, compuerta de viabilidad, prueba de humo y runners | compuerta de viabilidad (bloque 23) y prueba de humo (bloque 24) |
> | D | 26 | corridas de D56 y registro | resultados (2026-10-23: C13–C20 no evaluables) |
> | S | 27 a 32 | control de sombra neutral (reformulación del control, design D64–D74): instrumento, telemetría, atribución con sombra, prueba de humo y corridas con semillas nuevas | inercia e identidad del instrumento (bloque 28), prueba de humo (bloque 31) y resultados (bloque 32) |
>
> **Ejecución automática.** La skill `ejecutar-bloque` (`.claude/skills/ejecutar-bloque/`) ejecuta cada bloque con el ciclo de `CLAUDE.md`:
> - lo delega en el subagente que indica su línea `> Ejecuta:`;
> - lo verifica desde el agente principal y corre `/code-review`;
> - hace un commit por bloque;
> - se detiene en las líneas `> Punto de control:`.
>
> Subagentes disponibles, con su modelo fijado en `.claude/agents/`:
> - `implementador-mecanico` (Sonnet), para bloques con firmas y fórmulas exactas;
> - `implementador-delicado` (Opus), para integración, determinismo y atribución.
>
> Cambiar el subagente de un bloque es editar su línea `> Ejecuta:` en un commit.
>
> **Compatibilidad.** Ningún bloque puede cambiar los hashes dorados de la Fase I ni los historiales de la Fase II con las banderas por defecto. Los tests de los bloques 1 a 5 sólo cambian donde la reformulación lo dice explícitamente (D46.7, D50.3 y D52.4), más el test de firmas canónicas de la Fase I (precisión 22).
>
> **Pre-registro.** Es design D56, **aprobado** el 2026-10-21 en la tarea 0.5, **antes** del bloque 6. Las constantes de `attribution.py` del bloque 22 deben coincidir **exactamente** con él. Se reabrió el 2026-10-21 con la ampliación D57–D63.
>
> **Etapa actual:** las etapas A a C están completas, y la atribución de D56 (tarea 26.1) se corrió y se registró: C13–C20 quedaron no evaluables porque el control de reproducción neutral se extingue (`docs/RESULTADOS.md`). El 2026-10-23 el responsable del proyecto decidió reformular el control con una sombra neutral (design D64–D74). La revisión cruzada (tarea 0.7) y la aprobación del pre-registro D72 (tarea 0.8, 2026-10-23, con la condición conjunta de C25, C27 exploratoria con Holm sobre C21–C26 y C26 endurecida) están hechas. Sigue la etapa S (bloques 27 a 32). Las tareas 26.2 y 26.3 (documentos y cierre) se hacen después del bloque 32.

## 0. Decisiones y pre-registro

- [x] 0.1 **Diagnóstico demográfico previo (decisión P5).** Resultado: hipótesis **confirmada** en las 10 semillas de los dos protocolos (`docs/RESULTADOS.md`). Mide la demografía de la Fase II con `resources_per_pattern = 40`:
  - muertes, nacimientos y edad al morir por tick;
  - con `PHASE2_PROTOCOL_CONFIGS_ORIGINAL["002a"]` y `["003a"]`, y las semillas de calibración 0 a 9.
  - **No** calcula ninguna métrica de afirmación.
  - Aplica el criterio fijado de antemano en design D42: la hipótesis se confirma si, en al menos 8 de 10 semillas de cada protocolo, más de la mitad de los agentes vivos en el tick 2000 nació antes del tick 1000.
  - Registra la salida en `registros/` y en `docs/RESULTADOS.md` como diagnóstico exploratorio de la hipótesis del "Tapón de Matusalén".
- [x] 0.2 **Resolver P4–P7 con el responsable del proyecto** (resueltas el 2026-10-20: todo aprobado sin cambios, ver `proposal.md`):
  - aprobar o corregir D42: inventario, afirmaciones, configuraciones, perfil, reglas inactivas y E4;
  - aprobar los valores por defecto de D31;
  - según el diagnóstico de 0.1, decidir si $R_{29}$ y C10 se mantienen;
  - aprobar los sesgos declarados (P6) y el tratamiento del Exp 004 (P7).
  - Registrar las decisiones con fecha en `proposal.md`.
- [x] 0.3 **Reflejar el diseño aprobado en los documentos raíz** (hecho el 2026-10-20: pre-registro aprobado en `93004ff`):
  - `docs/DEFINICIONES_FORMALES.md`: §3.1 con el inventario $R_{24}$–$R_{31}$ y las afirmaciones C9–C12, más una sección del modelo genético;
  - `docs/DEFINICIONES_TECNICAS.md`: tipos, configuración y ciclo del tick;
  - `docs/vision/ROADMAP.md` y `docs/vision/ARQUITECTURA_ADN_HOLONICO.md`, si cambió algo respecto del borrador.
  - Commitear el pre-registro aprobado.

- [x] 0.4 **Reformular la Fase II-B** (2026-10-20, decisión del responsable del proyecto): design D43–D56, specs delta, `proposal.md`, este `tasks.md` y los documentos raíz, con `openspec validate --all --strict` y revisión cruzada independiente. Sustituye el pre-registro D42 por D56 (entonces borrador); C9–C12 se retiran sin medir.
- [x] 0.6 **Ampliar la Fase II-B** (2026-10-21, decisión del responsable del proyecto): design D57–D63 (estado interno, plasticidad, señales, ADN de 64 codones, entorno cambiante y detección de núcleos), D56 reabierto con C19 y C20, specs, este `tasks.md` y documentos raíz.
- [x] 0.5 **Aprobar el pre-registro D56 con el responsable del proyecto**, antes del bloque 6 (aprobado el 2026-10-21 por delegación del responsable del proyecto, tras dos revisiones cruzadas: commits aa25808 y el siguiente):
  - el inventario $R_{24}$–$R_{41}$ con sus propósitos y ablaciones;
  - los protocolos `25a`, `25b`, `25c` y `25d`, y sus condiciones;
  - las afirmaciones C13–C19 (genuinas) y C20 (funcional), sus métricas, sus comparaciones y sus $\delta_{\min}$;
  - la prueba, la corrección de Holm, el perfil `phase25` (5000 ticks) y las semillas 42–71;
  - la compuerta de viabilidad de D55, con su grilla y su criterio;
  - las correcciones de la revisión cruzada del 2026-10-21 (diferencia de diferencias de C17 y C19, `effective_parents`, ventana final de 1000 ticks y precisiones 66–69);
  - los valores por defecto de D52.
  - Registrar las decisiones con fecha en `proposal.md` y commitear.

- [x] 0.7 **Reformular el control con una sombra neutral** (2026-10-23, decisión del responsable del proyecto): design D64–D74, specs delta (`simulation-engine`, `evolutionary-dynamics`, `micro-agent`, `domain-contracts`, `experimental-suite` y `emergence-attribution`), `proposal.md`, este `tasks.md` y los documentos raíz, con `openspec validate --all --strict` y **revisión cruzada independiente** (cambio grande). Declarar `shadow_rng` (`spawn_key=(6,)`) en `CLAUDE.md`, sección Determinismo. Hecho: borrador en el commit `5f09e29`, primera ronda de la revisión cruzada en `39c1baa` y segunda ronda el 2026-10-23 (condición conjunta de C25, sesgo de mantenimiento por afirmación, C27 exploratoria y lista de grados de libertad post hoc con C26 endurecida; D64.4, D71.3 y D72). La declaración de `shadow_rng` en `CLAUDE.md` se agrega en el commit de esta aprobación.
- [x] 0.8 **Aprobar el pre-registro con sombra D72** con el responsable del proyecto, **antes** del bloque 27 y sin correr ninguna corrida con sombra:
  - las afirmaciones C21–C26 (genuinas y confirmatorias), C27 (genuina y exploratoria) y C28 (funcional), sus métricas real y de sombra, comparaciones, $R_C$, canales y $\delta_{\min}$ (los de D56, salvo C26, endurecida a $\max(0.01,\ 0.25 \cdot M)$), y la condición conjunta de C25;
  - la regla de pares válidos sin condiciones neutrales, la prueba de signo, Holm sobre C21–C26 ($m = 6$), E4 sobre el exceso de la sombra y los efectos de regla exploratorios;
  - las semillas nuevas 72–101 (`PHASE25_SHADOW_SEEDS`) y 72–81 para los efectos de regla, el perfil `phase25` y la abundancia (80, 20), sin compuerta nueva (D72.10);
  - los puntos P-S1 (potencia de `25d`: C27 exploratoria) y P-S2 (E4 y efectos de regla exploratorios), cerrados en D72.12;
  - los sesgos declarados de D71, con el sesgo de mantenimiento por afirmación, y los grados de libertad post hoc de D64.4.
  - Registrar la decisión con fecha en `proposal.md` y commitear antes del bloque 27. Hecho: aprobado el 2026-10-23 por delegación del responsable del proyecto (`proposal.md`).

## 1. Contratos de dominio y configuración (`domain-contracts`)

> Ejecuta: implementador-mecanico

- [x] 1.1 **[RED]** Ampliar `tests/test_domain_contracts.py` con tests para:
  - los tipos `EpigeneticRole`, `CompactDNA` (validación de codones, cromosoma no vacío y plásmidos y firmas sin repetidos), `EpigeneticContext` y `ExpressedPhenotype`, todos inmutables;
  - los campos de D31 con sus valores por defecto y la validación siempre activa;
  - la validación condicionada a `enable_compact_dna=True`: requisitos, bases dentro de sus cotas y mensajes que mencionan el campo;
  - que las dependencias apagadas dejan las banderas inertes y no lanzan error (D30.3).
- [x] 1.2 **[GREEN]** Implementar los tipos en `src/ide/domain/types.py` y los campos y validaciones en `src/ide/config.py`.
- [x] 1.3 **[REFACTOR]** Verificación del bloque, con `tests/test_performance_equivalence.py` intacto. (778 tests, cobertura 99 %; `FOUNDER_DNA_LENGTH` vive en `config.py` y `dna.py` lo reexporta.)

## 2. Codón, ADN fundador y transcripción (`compact-dna`)

> Ejecuta: implementador-mecanico

- [x] 2.1 **[RED]** Crear `tests/test_compact_dna.py` con tests para:
  - (a) `encode_codon` y `decode_codon`: ida y vuelta, campos, `delta` en los extremos ($-128 \to -1.0$, $127 \to 0.9921875$) y `ValueError` fuera de rango;
  - (b) `founder_dna`: longitud 9 y expresión de `genome_from_config` en cualquier contexto;
  - (c) cada promotor de D32, incluidos los reservados, que nunca se activan;
  - (d) la fórmula de D33 con los modos aditivo, represor y multiplicativo, el modo 3 inerte, el redondeo `floor(x + 0.5)` y las cotas;
  - (e) la red regulatoria: canal encendido sólo si `act > rep`, la pasada 2, y que los `EMIT_TF` de la pasada 2 no encienden canales;
  - (f) que los destinos reservados son inertes y que los plásmidos se transcriben y `crispr_memory` no;
  - (g) `phenotype_from_genome`.
- [x] 2.2 **[GREEN]** Crear `src/ide/agent/dna.py` con `Codon`, `encode_codon`, `decode_codon`, `FOUNDER_DNA_LENGTH`, `founder_dna`, `transcribe_phenotype` y `phenotype_from_genome`.
- [x] 2.3 **[REFACTOR]** Agregar pruebas por propiedades con Hypothesis (perfil `ci`):
  - toda transcripción cae dentro de las cotas;
  - el resultado no depende de `PYTHONHASHSEED`;
  - el ADN fundador es neutro para toda configuración válida.
  - Agregar la auditoría AST: `dna.py` no importa `micro_agent`, `holon`, `environments`, `simulation` ni `experiments`.
  - Verificación del bloque. (836 tests, cobertura 99 %; cotas enteras con fuente única `integer_trait_bounds`.)

## 3. Mutación del ADN (`compact-dna`)

> Ejecuta: implementador-mecanico

- [x] 3.1 **[RED]** Tests de `mutate_dna`:
  - puerta de $R_{13}$ sin consumir `rng`;
  - mutación puntual de bit, duplicación y deleción con sus cotas de longitud;
  - escisión a plásmido sólo con `enable_plasmid_hgt`, con FIFO y exclusión de los codones de `crispr_memory`;
  - `crispr_memory` sin mutar;
  - escala `scale` con tope 1;
  - secuencia exacta de extracciones de D35, verificada con un generador sembrado.
- [x] 3.2 **[GREEN]** Implementar `mutate_dna` en `dna.py`.
- [x] 3.3 **[REFACTOR]** Pruebas por propiedades: el ADN mutado siempre es válido y respeta `dna_min_length` y `dna_max_length`. Verificación del bloque. (867 tests, cobertura 99 %.)

## 4. Agente y memoria (`micro-agent`, `bounded-memory`, `evolutionary-dynamics`)

> Ejecuta: implementador-delicado

- [x] 4.1 **[RED]** Ampliar `tests/test_memory.py`, `tests/test_micro_agent.py` y `tests/test_evolutionary_dynamics.py` con tests para:
  - (a) `BoundedMemory.resize`: desalojo por menor utilidad con el desempate de $R_2$ y la penalización de $R_{18}$, sin borrar al agrandar, y `ValueError` con capacidad menor que 1;
  - (b) el estado nuevo de `MicroAgent` (D34.1), sin cambiar las 8 firmas de la Fase I ni el comportamiento sin ADN;
  - (c) `express`: reemplazo del genoma y de la configuración fenotípica, `resize` de la memoria, el valor de retorno con los radios, y el caché igual a la transcripción directa;
  - (d) bases tomadas de `base_config`, sin acumulación tick a tick;
  - (e) `create_offspring` con `dna_source` y `mutation_scale`, herencia de plásmidos y firmas sin ensayos, expresión al nacer y `birth_tick`;
  - (f) `compute_dna_cost`.
- [x] 4.2 **[GREEN]** Implementar `resize` en `memory.py`, el estado y los métodos de `MicroAgent`, y `compute_dna_cost` en `evolution.py`.
- [x] 4.3 **[REFACTOR]** Auditorías AST de `tests/test_micro_agent.py` y verificación del bloque. (934 tests, cobertura 99 %; una transcripción por nacimiento.)

## 5. Motor con ADN, R24 (`simulation-engine`)

> Ejecuta: implementador-delicado
>
> Punto de control: fin de la etapa A. Mostrar que los historiales de los protocolos de la Fase II son idénticos con las banderas por defecto, los hashes dorados intactos y los ticks por segundo con y sin ADN del benchmark.

- [x] 5.1 **[RED]** Ampliar `tests/test_simulation_engine.py` con tests para:
  - (a) la Fase 0: contexto con nivel, rol y energía; `set_agent_radii` sólo si cambian los radios; sin consumo de generadores;
  - (b) el costo metabólico sobre el genoma expresado más `compute_dna_cost`;
  - (c) el nacimiento con ADN mutado por `evo_rng` y expresado en el acto;
  - (d) la reproducción neutral con el ADN del donante;
  - (e) la igualdad de historiales entre procesos con distinto `PYTHONHASHSEED` con `enable_compact_dna=True`;
  - (f) con las banderas por defecto, historiales de los protocolos `002a` y `003a` idénticos a los de la Fase II.
- [x] 5.2 **[GREEN]** Extender `SimulationEngine`: `_express_phenotypes`, el costo y el nacimiento.
- [x] 5.3 **[REFACTOR]** Correr `python -m pytest tests/test_simulation_engine.py tests/test_performance_equivalence.py` y `python -m ide.experiments.benchmark` con y sin ADN, y registrar los ticks por segundo. Verificación del bloque. (960 tests, cobertura 99 %; benchmark sin ADN 253.8 y 272.6 ticks/s, `--compact-dna` sobre `002a` 148.9 y 136.0 ticks/s; historiales de la Fase II idénticos a 20305df en 8 huellas doradas.)

## 6. Motor por sistemas y observadores (`simulation-engine`, `experimental-suite`)

> Ejecuta: implementador-delicado

- [x] 6.1 Registrar la línea base de rendimiento: `python -m ide.experiments.benchmark` y `--compact-dna`, con sus ticks por segundo en la nota de esta tarea (D54.1). (Contenedor de 4 núcleos, 2026-10-21: 268.1 ticks/s sin ADN y 147.0 con `--compact-dna`.)
- [x] 6.2 **[RED]** Tests para:
  - (a) `EngineSystem`, `TickObserver`, `TickFrame` y `build_systems`: el orden de D53.1 y la ausencia de los sistemas de los mecanismos apagados;
  - (b) que la telemetría la producen observadores y que M2 se juzga en `on_decisions`, antes de ejecutar;
  - (c) la auditoría AST de los accesos a `agent.memory` desde el motor (D44.3);
  - (d) la aceptación de D44.4: hashes dorados, huellas de la Fase II e historiales de `002a` y `003a` con y sin ADN idénticos a los de antes del refactor.
- [x] 6.3 **[GREEN]** Crear `src/ide/simulation/pipeline.py` y mover `step()` a sistemas y observadores, sin cambiar ninguna conducta.
- [x] 6.4 **[REFACTOR]** Benchmark contra 6.1 (no peor que un 10 %, D54.2) y verificación del bloque. (986 tests, cobertura 99 %; corridas intercaladas contra el motor previo: sin ADN 247.7–264.6 frente a 234.5–254.6 ticks/s, con ADN 144.0–148.0 frente a 123.4–143.6, dentro del ruido; hashes dorados, 8 huellas de la Fase II y 5 huellas nuevas con ADN idénticos, también con `PYTHONHASHSEED=123`; precisiones 70–74.)

## 7. Puerto de política (`micro-agent`)

> Ejecuta: implementador-mecanico
>
> Punto de control: fin de la etapa R. Mostrar los hashes dorados, las huellas de la Fase II y los historiales del bloque 5 idénticos, y el benchmark contra la línea base de 6.1.

- [x] 7.1 **[RED]** Tests para `PolicyPort`, `HandwrittenPolicy` (misma conducta y mismas extracciones de `rng` que el `decide_action` actual), la delegación de `MicroAgent.decide_action` con y sin `social`, la herencia de la política en `create_offspring` y la auditoría AST de `policy.py`.
- [x] 7.2 **[GREEN]** Crear `src/ide/agent/policy.py` con `PolicyPort` y `HandwrittenPolicy`, y delegar desde `MicroAgent` (D45).
- [x] 7.3 **[REFACTOR]** Verificación del bloque, con los hashes dorados y las huellas de la Fase II intactos. (998 tests, cobertura 99 %; `test_firmas_publicas_canonicas` actualizado según la precisión 22; `social` queda tipado `object | None` hasta el bloque 8. Punto de control de la etapa R: hashes dorados, 8 huellas de la Fase II y 6 huellas con ADN idénticos, también con `PYTHONHASHSEED=123`; benchmark intercalado contra el motor del bloque 6: 238–278 frente a 213–247 ticks/s, sin costo medible.)

## 8. Contratos de la reformulación (`domain-contracts`)

> Ejecuta: implementador-mecanico

- [x] 8.1 **[RED]** Ampliar `tests/test_domain_contracts.py` con tests para:
  - `Behavior`, `VisibleAgent`, `SocialPerception`, `SensorySignals` y los miembros nuevos de `ActionType` (D47.1);
  - los campos nuevos de `ExpressedPhenotype` con sus valores por defecto (D46.7);
  - los campos de D52 con sus valores por defecto, la validación siempre activa y las dependencias inertes;
  - la eliminación de `lock_composite_threshold` (D52.4), retirando sus tests;
  - `EcologicalEnvironmentPort` (D47.2);
  - los tipos y campos de la ampliación: `EventSignals`, `BehaviorEvaluation`, los campos nuevos de `SensorySignals` y `ExpressedPhenotype` (`plasticity_rate`) y los de D62 y D63.1.
- [x] 8.2 **[GREEN]** Implementar los tipos, los campos y la validación en `types.py`, `config.py` y `ports.py`.
- [x] 8.3 **[REFACTOR]** Verificación del bloque. (1041 tests, cobertura 99 %; `social` tipado como `SocialPerception`; precisión 75: `num_regions <= grid_width` sólo con R34 activa; los escenarios de `ToroidalGrid2D` como `EcologicalEnvironmentPort` quedan para el bloque 11.)

## 9. ADN conductual (`compact-dna`)

> Ejecuta: implementador-mecanico

- [x] 9.1 **[RED]** Ampliar `tests/test_compact_dna.py` con tests para:
  - (a) los destinos de rasgo `0x0A`–`0x0C`, sus bases, escalas y cotas, y el conteo nuevo de `expressed_codons` (D46.7);
  - (b) los promotores sensoriales `0x20`–`0x27`: inactivos en la transcripción del fenotipo y activos en `evaluate_drives` según `SensorySignals` (D46.2);
  - (c) `evaluate_drives`: las dos pasadas con sensores, $d_B = \mu_B \cdot \rho_B \cdot S_B$, impulsos nulos sin codones y destinos de conducta inertes en el fenotipo (D46.3);
  - (d) `founder_dna` y `founder_dna_length` con y sin la política genética, y los cuatro impulsos fundadores (D46.5);
  - (e) `recombine_dna`, con el truncado y el mínimo de longitud (D51.2);
  - (e2) `expressible_codons`: promotores expresables y condicionales según el protocolo, valores distintos y la aproximación de los canales regulados (precisión 42);
  - (f) propiedades con Hypothesis: impulsos deterministas e independientes de `PYTHONHASHSEED`.
- [x] 9.2 **[GREEN]** Implementar en `dna.py`.
- [x] 9.3 **[REFACTOR]** Actualizar los tests de los bloques 2 y 3 que la reformulación modifica (destinos `0x0A`–`0x0C` y conteo de `expressed_codons`, D46.7) y verificación del bloque. (1135 tests, cobertura 99 %; dos huellas con ADN de `test_pipeline.py` actualizadas sólo por el conteo de D46.7; precisión 76: los promotores sensoriales son expresables sobre conducta, estado y señal, como fija la precisión 59; `plasticity_rate` se transcribe en el bloque 14.)

## 10. Política genética, percepción social y puerta de comunicación (`micro-agent`, `simulation-engine`)

> Ejecuta: implementador-delicado

- [x] 10.1 **[RED]** Tests para:
  - (a) `GeneticPolicy.decide`: factibilidad de cada conducta, orden por $(-d_B, \text{posición})$, `IDLE` sin factibles y extracciones de `rng` sólo donde D46.1 las declara;
  - (b) `SensorySignals` construido desde la observación, las creencias y `social`;
  - (c) la percepción social del motor sobre la instantánea de energías, sin endosporas, con `flee_move` y `crowded` (D47.3), y `None` sin la política genética;
  - (d) la puerta de comunicación de `protocol.py` (D46.6);
  - (e) el caché de impulsos igual a la evaluación directa (D46.8);
  - (f) **aceptación de D46.5:** con el ADN fundador, sin mutación y con `dna_codon_cost = 0.0`, `002a` y `003a` con `enable_genetic_policy=True` dan historiales idénticos a los de `False`.
- [x] 10.2 **[GREEN]** Implementar `GeneticPolicy`, la percepción social en el sistema de la Fase 1 y la puerta de comunicación.
- [x] 10.3 **[REFACTOR]** Benchmark con la política genética y verificación del bloque. (1262 tests, cobertura 99 %; aceptación de D46.5 en `002a` y `003a`; `002a` con ADN, 300 ticks: 108 ticks/s con la política genética frente a 156 sin ella, a optimizar en 23.1 si hace falta; la endospora decide y se percibe hasta el bloque 17, precisión 82.)

## 11. Ecología del entorno: R33, R34 y R35 (`spatial-environments`, `simulation-engine`)

> Ejecuta: implementador-delicado

- [x] 11.1 **[RED]** Tests para:
  - (a) $R_{33}$: la agenda de reposición con `due`, su orden y la reposición de la Fase II con la regla apagada;
  - (b) $R_{34}$: las franjas, la región propia de cada patrón, la ubicación inicial y de reposición, y las estaciones con `winter_regen_factor`;
  - (c) $R_{35}$: el depósito del cadáver antes de quitar al agente, su consumo, su aprendizaje, su retiro tras `carcass_lifetime` y su ausencia de `get_world_patterns()`;
  - (d) `get_visible_agents`, `deposit_carcass` y `get_resource_count`;
  - (e) los hashes dorados y las huellas de la Fase II con las reglas apagadas;
  - (f) los cambios del entorno de D62.1 (`world_shift_period`, `invert_world_rules` con el generador principal al empezar cada tick múltiplo).
- [x] 11.2 **[GREEN]** Implementar D48 en `grid2d.py`, el depósito de cadáveres en el sistema de muerte y los cambios del entorno de D62.1.
- [x] 11.3 **[REFACTOR]** Verificación del bloque. (1194 tests, cobertura 99 %; hashes dorados y huellas idénticos, también con `PYTHONHASHSEED=123`; `CARCASS_PATTERN` en el dominio, depósito dentro del paso de muerte, el motor exige el puerto ecológico con R33, R34 o R35, y M9 y M11 no ven el cadáver: precisiones 77 a 81.)

## 12. Interacciones: transferencia y depredación (`simulation-engine`, `evolutionary-dynamics`)

> Ejecuta: implementador-delicado
>
> Punto de control: fin de la etapa B. Mostrar la aceptación de D46.5, que cada ablación de $R_{32}$–$R_{37}$ deja su regla inerte y que los historiales son iguales entre procesos con distinto `PYTHONHASHSEED`.

- [x] 12.1 **[RED]** Tests para:
  - (a) `SHARE`: cantidad, eficiencia, objetivo muerto o en endospora (D49.1);
  - (b) `ATTACK`: éxito sólo contra un objetivo más débil en el momento de ejecutarse, robo acotado, eficiencia, costo por intento y muerte con cadáver (D49.2);
  - (c) conflictos resueltos por la permutación del tick;
  - (d) que M2 juzga la decisión cualquiera sea la conducta elegida (D49.4 y precisión 21);
  - (e) los eventos del tick en `frame.events`.
- [x] 12.2 **[GREEN]** Implementar D49 en el sistema de la Fase 4 y el costo de los ataques en el metabolismo.
- [x] 12.3 **[REFACTOR]** Verificación del bloque. (1309 tests, cobertura 99 %; conservación de energía por propiedades; `shares` cuenta las cesiones que transfieren energía y `predation_deaths` exige energía robada mayor que 0, precisiones 37, 84 y 85. Punto de control de la etapa B: aceptación de D46.5 en `002a` y `003a`, ablaciones de R32–R37 inertes y historiales iguales con `PYTHONHASHSEED` 0 y 123, cubiertos por `test_genetic_policy.py`, `test_ecology.py` y `test_interactions.py`.)

## 13. Estado interno persistente y eventos (R39) (`compact-dna`, `micro-agent`, `simulation-engine`)

> Ejecuta: implementador-delicado

- [x] 13.1 **[RED]** Tests para:
  - (a) `evaluate_behavior` y `BehaviorEvaluation` (D60.1), con `evaluate_drives` como envoltorio que devuelve los mismos impulsos;
  - (b) los destinos `SET_STATE` y `CLEAR_STATE`, la regla de mayoría por bit, `clear` prevaleciente y la aplicación al terminar la Fase 3 (D58.3);
  - (c) los promotores de estado `0x30`–`0x37` y de eventos `0x28`–`0x2B`, inactivos en la transcripción del fenotipo (D58.4–D58.6);
  - (d) `EventSignals` calculados por el motor al final del tick y guardados en `agent.last_events` (D58.5);
  - (e) `internal_state` en 0 al nacer, conservado en la endospora y no heredado;
  - (f) la inercia sin $R_{39}$ y la aceptación de D46.5 con las banderas de la ampliación activas y el ADN fundador.
- [x] 13.2 **[GREEN]** Implementar D58 y la parte de D60.1 que corresponde al estado.
- [x] 13.3 **[REFACTOR]** Verificación del bloque. (1404 tests, cobertura 99 %; la decisión registra su evaluación y el estado se aplica una vez, también conservado en endospora; precisiones 87 y 88.)

## 14. Plasticidad en vida (R40) (`compact-dna`, `micro-agent`, `simulation-engine`)

> Ejecuta: implementador-delicado

- [x] 14.1 **[RED]** Tests para:
  - (a) el modo 3 plástico sólo sobre destinos de conducta e inerte en el fenotipo, y `AST_PIPE` mudado a `0x3F` (D59.1, D61);
  - (b) el rasgo `plasticity_rate` (`0x0F`) con base 0 (D59.3);
  - (c) la recompensa de la Fase 4, los codones elegibles y la actualización acotada (D59.4);
  - (d) `plastic_weights` vacío al nacer, no heredado y vaciado en `set_dna` (D59.2);
  - (e) el caché único de la evaluación (precisión 88), extendido con los pesos, igual a la evaluación directa (D59.5);
  - (f) la inercia sin $R_{40}$.
- [x] 14.2 **[GREEN]** Implementar D59.
- [x] 14.3 **[REFACTOR]** Verificación del bloque. (1503 tests, cobertura 99 %; un solo registro de la decisión del tick, `plastic_updates` cuenta sólo los pesos que se mueven y R40 exige la evolución; precisiones 94 a 96.)

## 15. Señales evolucionables (R41) (`compact-dna`, `simulation-engine`)

> Ejecuta: implementador-delicado
>
> Punto de control: fin de la etapa L. Mostrar, para $R_{39}$–$R_{41}$, que cada ablación deja la regla inerte, que el ADN fundador sigue reproduciendo la política escrita a mano y que los historiales son iguales entre procesos con distinto `PYTHONHASHSEED`.

- [x] 15.1 **[RED]** Tests para:
  - (a) la emisión por mayoría por símbolo, su costo en el metabolismo y que `SIGNAL` no ocupa la acción (D60.2, D60.3);
  - (b) la percepción en la Fase 1 del tick siguiente por los vecinos del emisor en el tick de emisión, sin endosporas (D60.4);
  - (c) los promotores `0x38`–`0x3F` sólo en la evaluación de conducta;
  - (d) el control nulo con `null_rng`, en orden de `agent_id` (D60.5);
  - (e) que las señales no pasan por `protocol.py` ni por la memoria (D60.6);
  - (f) la inercia sin $R_{41}$.
- [x] 15.2 **[GREEN]** Implementar D60.
- [x] 15.3 **[REFACTOR]** Verificación del bloque. (1604 tests, cobertura 99 %; las señales son independientes de `comm_enabled` y la clave del caché sólo usa los símbolos que el ADN escucha; precisiones 97, 104 y 105. Punto de control de la etapa L: ablaciones de R39–R41 inertes, aceptación de D46.5 con la ampliación activa e historiales iguales con `PYTHONHASHSEED` 0 y 123, en `test_internal_state.py`, `test_plasticity.py` y `test_signals.py`.)

## 16. Senescencia (R29) y mutación SOS (R30) (`evolutionary-dynamics`, `simulation-engine`)

> Ejecuta: implementador-delicado

- [x] 16.1 **[RED]** Tests para:
  - `compute_senescence_cost`;
  - la edad y la longevidad expresada (con y sin ADN);
  - el cobro también a las endosporas;
  - el registro de `last_stress_tick`;
  - las tres escalas de SOS decididas antes de partir la energía, por hoja en la reproducción holónica;
  - la escala 1.0 con la regla apagada, con Fase II bit a bit.
- [x] 16.2 **[GREEN]** Implementar D39 como sistemas del pipeline.
- [x] 16.3 **[REFACTOR]** Verificación del bloque. (Integrado con el bloque 13: 1436 tests y un xfail estricto del costo de la endospora, que es del bloque 17; precisiones 89 a 93, con tolerancia 1e-9 en los umbrales de R30.)

## 17. Endospora como conducta (R28) (`evolutionary-dynamics`, `simulation-engine`)

> Ejecuta: implementador-mecanico

- [x] 17.1 **[RED]** Tests para:
  - la entrada en endospora sólo por `SPORULATE` (D50.2), con su factibilidad y su inercia sin la política genética;
  - la germinación en la Fase 1;
  - la física de la endospora de D38: sin emisión ni recepción de mensajes, `IDLE` sin decidir ni consumir `rng`, sin oportunidad de decisión en M2, sin reproducción, sin ser objetivo de `SHARE` ni de `ATTACK`, y el costo `spore_cost_fraction * metabolic_base_cost`.
- [x] 17.2 **[GREEN]** Implementar D38 con la entrada de D50.2.
- [x] 17.3 **[REFACTOR]** Verificación del bloque. (Integrado con el bloque 15: 1598 tests, cobertura 99 %; `frame.dormant` es la única fuente de las endosporas dormidas y el costo reducido rige sólo para quien estuvo en endospora todo el tick; precisiones 98 a 103.)

## 18. Señal posicional (R25) y compromiso simbiótico (R31) (`holonic-hierarchy`, `simulation-engine`)

> Ejecuta: implementador-delicado

- [x] 18.1 **[RED]** Ampliar `tests/test_holonic_hierarchy.py` y `tests/test_simulation_engine.py` con tests para:
  - (a) `assign_epigenetic_roles` de D36, con su asignación por el motor, el regreso a `NONE` y la impronta;
  - (b) el sello de $R_{31}$ por compromiso expresado medio $\ge 0.5$ (D50.3), su permanencia, `should_split_holon` en `False`, el descuento de coordinación sólo en la raíz soldada y la poda;
  - (c) que con `symbiotic_commitment_base = 0.0` y el ADN fundador ningún holón se suelda.
- [x] 18.2 **[GREEN]** Implementar D36 y D50.3.
- [x] 18.3 **[REFACTOR]** Verificación del bloque. (1744 tests; sello con tolerancia y heredado en la poda de un holón anidado; precisiones 108 a 111, 122 y 123.)

## 19. Plásmidos (R26) e inmunidad CRISPR (R27) (`compact-dna`, `simulation-engine`)

> Ejecuta: implementador-delicado

- [x] 19.1 **[RED]** Tests para:
  - `receive_plasmid` (bloqueo, duplicado y FIFO) y `purge_plasmid` (FIFO de firmas);
  - la conjugación con `hgt_rng` (`spawn_key=(5,)`): donantes y candidatos fijados al empezar el paso, sin endosporas, la secuencia exacta de extracciones de D37 y la aplicación después del sorteo;
  - la apertura y el cierre de ensayos CRISPR, la purga por toxicidad y el cierre sin purga si el plásmido se perdió;
  - que `hgt_rng` no se consume con $R_{26}$ apagada;
  - la igualdad entre procesos con distinto `PYTHONHASHSEED`.
- [x] 19.2 **[GREEN]** Implementar D37.
- [x] 19.3 **[REFACTOR]** Verificación del bloque. (Integrado con el 18: 1787 tests, cobertura 99 %; el balance CRISPR no cuenta como toxicidad lo cedido ni lo robado; precisiones 124 a 126.)

## 20. Recombinación (R38) (`compact-dna`, `simulation-engine`)

> Ejecuta: implementador-delicado
>
> Punto de control: fin de la etapa M. Mostrar, para $R_{25}$–$R_{31}$ y $R_{38}$, que cada ablación deja la regla inerte y que los historiales son iguales entre procesos con distinto `PYTHONHASHSEED`.

- [x] 20.1 **[RED]** Tests para:
  - la búsqueda de pareja con la propensión expresada de los dos, sin endosporas y a distancia $\le 1$;
  - la secuencia exacta de extracciones de `evo_rng` de D51.2 y su ausencia sin candidatas o con la regla apagada;
  - la reproducción asexual sin pareja, la herencia de plásmidos y firmas del progenitor y la mutación posterior;
  - la reproducción neutral: el ADN del donante en la recombinación (precisiones 14 y 35) y la reproducción holónica neutral con ADN, con el orden de sorteo de `donor_rng` y sin cambios sin ADN (precisión 41);
  - que la pareja no cede energía y que $R_{17}$ no recombina.
- [x] 20.2 **[GREEN]** Implementar D51 y la precisión 41 en el sistema de reproducción.
- [x] 20.3 **[REFACTOR]** Verificación del bloque. (1825 tests, cobertura 99 %; precisiones 127 a 129. Punto de control de la etapa M: cada ablación de R25–R31 y R38 deja su regla inerte y los historiales son iguales con `PYTHONHASHSEED` 0 y 123, en `test_holonic_hierarchy.py`, `test_simulation_engine.py`, `test_plasmids.py`, `test_sporulation.py`, `test_senescence_sos.py` y `test_recombination.py`.)

## 21. Telemetría de evolución abierta (`experimental-suite`)

> Ejecuta: implementador-delicado

- [x] 21.1 **[RED]** Ampliar `tests/test_metrics.py` y `tests/test_simulation_engine.py` con tests para:
  - `GeneticTickMetrics` de D53.2, incluidas `mean_conditional_codons`, `mean_expressible_nonattack_codons`, `regulated_expression_fraction` y `mean_expressible_codons` con los valores canónicos expresables de la precisión 42, `policy_divergence` (sin extraer de `rng`), `communicating_fraction`, `distinct_genotypes`, `mean_functional_codons`, la actividad de Bedau–Packard por nacimientos portadores y sin los codones fundadores, `cumulative_births`, `new_activity_per_birth` y `mean_age_at_death` (precisiones 43 y 49);
  - `EcologyTickMetrics` de D53.3, con `signals_emitted`, `plastic_updates`, `decision_opportunities` y `correct_decisions` (D63.3, D63.4);
  - los campos de la ampliación en `GeneticTickMetrics` (D63.2), incluidos `mean_learning_codons` (con la `plasticity_rate` expresada según `last_context`, precisión 52) y `max_signal_information`;
  - `birth_source_ids` como último campo de `GeneticTickMetrics` (precisión 68): la fuente genética de cada nacimiento (el progenitor con selección, el donante en neutral, también en $R_{17}$, y con $R_{38}$ el que inicia el cruce, sin la pareja), sin repeticiones de reproductores dentro de un tick;
  - el registro en cada tick con cualquier combinación de banderas y los valores con la población vacía;
  - que `TickMetrics` y `EvolutionaryTickMetrics` no cambian.
- [x] 21.2 **[GREEN]** Implementar los observadores y los tipos de métricas.
- [x] 21.3 **[REFACTOR]** Verificación del bloque. (1910 tests, cobertura 99 %; la telemetría cuesta menos del 10 % en `25a`, `25d` y la Fase I y no cambia ningún historial; precisiones 130 a 139.)

## 22. Atribución del pre-registro (`emergence-attribution`)

> Ejecuta: implementador-delicado

- [x] 22.1 **[RED]** Ampliar `tests/test_attribution.py` con tests para:
  - `PHASE25_DESIGN_RULES` (`R24`–`R41`) con sus `purpose`, `PHASE25_ALL_RULES` y `ablate()` con las reglas nuevas;
  - `PHASE25_PROTOCOL_CONFIGS` (`25a`, `25b`, `25c` y `25d`, con `dna_max_length = 64`), sus condiciones (incluidas `no_predation_drift`, `stable` con `dataclasses.replace`, `stable_drift` y `no_learning`, y la identidad de `stable` y `stable_drift` con `full` y `drift` de `25a`) y `PHASE25_CLAIMS` (C13–C19 genuinas y C20 funcional, con `post_shift_accuracy`) con métricas, comparaciones, `baseline_drift`, `comparison_drift`, $R_C$, canales y $\delta_{\min}$;
  - la diferencia de diferencias de C17 y C19, con `values` y `comparison_values` de la precisión 69 y los pares válidos sobre sus cuatro condiciones;
  - la ventana final de 1000 ticks (precisión 4), los pares válidos con `excluded_seeds`, `excluded_pairs` y `evaluable` (precisiones 45 y 47), la prueba de signo pareada sobre los pares válidos, la corrección de Holm–Bonferroni sobre C13–C19 ($m = 7$) con las afirmaciones no evaluables (precisión 48), C20 fuera de Holm y clasificada programada por construcción y el estado `OBSERVED` sólo con significancia ajustada y mediana mayor o igual que el umbral de efecto, incluido el umbral relativo de C16 (`delta_relative`);
  - `demography` (`dict[str, dict[int, dict[str, float]]]`) con sus covariables, incluido `effective_parents` calculado desde `birth_source_ids` de la ventana final (precisiones 44, 45, 49 y 68), y el p-valor 1.0 sin diferencias distintas de cero (precisión 48);
  - la clasificación no programada de C13–C19, C20 programada por construcción, y E4 condicionado a la compuerta;
  - los `rule_effects` exploratorios con las semillas 42–51, por afirmación, con la regla de pares válidos de la precisión 45, la métrica simple también en C17 y C19 y `None` sin semillas válidas (precisión 66);
  - el caché de corridas por (protocolo, variante, semilla) (precisión 67);
  - que los reportes de C1–C8 no cambian.
- [x] 22.2 **[GREEN]** Implementar en `attribution.py` el pre-registro aprobado en 0.5. Las constantes deben coincidir exactamente con design D56.
- [x] 22.3 **[REFACTOR]** Verificación del bloque. (Con la telemetría del bloque 21 corre el test de extremo a extremo; precisiones 112 a 121; `PHASE25_ABUNDANCE` y la viabilidad de `null_content` son provisionales hasta 23.4.)

## 23. Rendimiento del perfil largo y compuerta de viabilidad (`experimental-suite`)

> Ejecuta: implementador-delicado
>
> Punto de control: compuerta de viabilidad. Mostrar, por configuración de la grilla, protocolo y condición, las semillas viables, y la configuración elegida o la ausencia de una. Si ninguna es viable, decide el responsable del proyecto.

- [x] 23.1 Medir el costo de un tick con todas las reglas de `25b` activas (D54.3). Si una corrida de `phase25` supera los 5 minutos, optimizar con historiales idénticos antes de seguir. (2026-10-22, contenedor de 4 núcleos, abundancia (40, 20): con todas las reglas de `25b`, unos 18 ms por tick con 70 a 85 agentes; la corrida más lenta de 5000 ticks tardó 58,5 s, así que no hace falta optimizar.)
- [x] 23.2 **[RED]** Tests de `phase25_viability.py`: el `--jobs` por defecto con los núcleos detectados y la salida idéntica para cualquier `--jobs` (D62.3), el criterio por corrida y por configuración (con `no_predation_drift` y `stable_drift`), el orden de la grilla, la detención en la primera viable y que no calcula ninguna métrica de afirmación.
- [x] 23.3 **[GREEN]** Crear `src/ide/experiments/phase25_viability.py` con su CLI (D55).
- [x] 23.4 Correr la compuerta con `PHASE25_VIABILITY_SEEDS` y registrar la salida en `registros/` y en `docs/RESULTADOS.md`. Fijar en `PHASE25_PROTOCOL_CONFIGS` la configuración elegida, en un commit propio. (Corrida el 2026-10-22: **ninguna configuración de la grilla es viable**; decide el responsable del proyecto, D55.5.)
- [x] 23.5 Correr la Enmienda 2 de D55 (D55.7, decisión del responsable del proyecto del 2026-10-22) con `python -m ide.experiments.phase25_viability --amendment2 --out registros/phase25_viability_enmienda2.json`: la grilla extendida `(60, 20)`, `(60, 10)`, `(80, 20)` y `(80, 10)` con el mismo criterio, semillas y perfil, y, si no hay viable, la salida de respaldo fijada de antemano. Registrar la salida en `registros/` y en `docs/RESULTADOS.md` (declarando si la configuración es de respaldo) y fijar en `PHASE25_PROTOCOL_CONFIGS` la configuración elegida, en un commit propio. (Corrida el 2026-10-22: ninguna configuración viable; rige el respaldo pre-registrado (80, 20), fijado en `PHASE25_ABUNDANCE` con `PHASE25_NULL_CONTENT_VIABLE_SEEDS` en 10/10 para los cuatro protocolos.)

## 24. Prueba de humo (`experimental-suite`)

> Ejecuta: implementador-delicado
>
> Punto de control: prueba de humo, antes de los runners. Mostrar, por protocolo, condición y semilla, sólo la terminación, la generación máxima y la población final.

- [x] 24.1 Correr la prueba de humo de D56 sobre `PHASE25_PROTOCOL_CONFIGS` y `PHASE25_SEEDS`, **sin** calcular ni mirar las métricas de las afirmaciones. Registrar su salida en `registros/` y en `docs/RESULTADOS.md`.

## 25. Runners de los protocolos (`experimental-suite`)

> Ejecuta: implementador-delicado

- [x] 25.1 **[RED]** Crear `tests/test_exp25.py` con tests para la ejecución, la serialización JSON y la CLI de `25a`, `25b`, `25c` y `25d`, el `--jobs` por defecto con los núcleos detectados (D62.3), sus condiciones (incluidas `no_predation_drift` y `stable_drift`) y el resumen por condición, con los historiales genético y ecológico.
- [x] 25.2 **[GREEN]** Crear `src/ide/experiments/exp25_runner.py` con la infraestructura de `phase2_cli.py`.
- [x] 25.3 **[REFACTOR]** Verificación completa (2046 tests, cobertura 99 %; `pytest -m slow`: 4 pasan; comandos en `CLAUDE.md` y `README.md`; `ci.yml` sin cambios; tres rondas de revisión):
  - `ruff check`, `ruff format --check`, `pyright` y `python -m pytest --cov=ide` (cobertura $\ge 90\%$);
  - `python -m pytest -m slow`;
  - `openspec validate --all --strict`;
  - agregar los comandos nuevos a `CLAUDE.md` y `README.md`;
  - actualizar `.github/workflows/ci.yml` si cambian los pasos de verificación.

## 26. Corridas y registro

> Ejecuta: agente principal. Sin subagente: las corridas largas se hacen en el equipo del responsable del proyecto, como en la Fase II, y el agente principal registra e interpreta.
>
> Punto de control: resultados. Presentarlos tal cual, incluidos los negativos, antes de archivar.

- [x] 26.1 Correr los cuatro protocolos con sus condiciones y `PHASE25_SEEDS`, y los `rule_effects` exploratorios con las semillas 42–51. Registrar todos los resultados, incluidos los negativos y las métricas descriptivas de evolución abierta, en `docs/RESULTADOS.md`, sin tocar el pre-registro. Hecha: corrida en el equipo del responsable y registrada en el commit e8db059 (`registros/exp25_phase25_attribution.json`); C13–C20 no evaluables.
> Las tareas 26.2 y 26.3 se posponen hasta después del bloque 32 (etapa S), para cerrar la fase con los resultados del control de sombra.

- [ ] 26.2 Actualizar `CLAUDE.md` (estado), `README.md` y los documentos de `docs/`, incluida la hoja de ruta de la Fase III con lo aprendido.
- [ ] 26.3 Completar la Definition of Done de `design.md` con su evidencia y archivar el cambio.

## 27. Contratos y generador de la sombra (`domain-contracts`, `micro-agent`, `simulation-engine`)

> Ejecuta: implementador-mecanico

- [ ] 27.1 **[RED]** Tests para:
  - `enable_neutral_shadow: bool = False` como último campo de `SimulationConfig`, y el escenario de los campos de la ampliación actualizado (D65.1);
  - `MicroAgent.shadow_dna`, `shadow_internal_state`, `set_shadow_dna` y `set_shadow_internal_state` (con `ValueError` fuera de $[0, 255]$), y que `create_offspring`, `express` y `decide_action` no los usan (D65.2);
  - `shadow_rng` con `spawn_key=(6,)`, sin consumo con la sombra apagada o inerte, y los escenarios de generadores del motor con `shadow_rng` (D66, D73.6);
  - la sombra inerte sin `enable_compact_dna` o sin `enable_evolution`, sin error (D65.1);
  - los fundadores con `shadow_dna == dna` y estado de sombra 0 (D65.3).
- [ ] 27.2 **[GREEN]** Implementar la bandera, el estado del agente, el generador y la sombra de los fundadores.
- [ ] 27.3 **[REFACTOR]** Verificación del bloque, con los hashes dorados, las huellas de la Fase II y los historiales de la Fase II-B intactos con la sombra apagada.

## 28. Herencia, mutación y conjugación de la sombra (`evolutionary-dynamics`, `simulation-engine`, `experimental-suite`)

> Ejecuta: implementador-delicado
>
> Punto de control: compuerta del instrumento. Mostrar las pruebas de inercia (D73.2) en los cuatro protocolos, con `drift` y $R_{17}$, la de identidad sin mutación (D73.3, con $R_{13}$, $R_{26}$ y $R_{27}$ ablacionadas), los tests dirigidos de la conjugación espejo y de la sombra sin CRISPR, y el test AST de accesos (D73.4). Sin ellas no se corre ninguna corrida con sombra.

- [ ] 28.1 **[RED]** Tests para:
  - la herencia por la fuente genética, con selección, en la reproducción neutral y en $R_{17}$ (D67.1, D67.4);
  - la mutación de la sombra con `shadow_rng`, los mismos operadores y la misma escala SOS, sin consumo con $R_{13}$ ablacionada (D67.3);
  - la recombinación de la sombra con la misma pareja (no otra candidata) y los cortes proporcionales `round(a·L_s/L_r)` y `round(b·L_s/L_r)` acotados a `[0, L_s]`, iguales a los reales con largos iguales, sin generadores (D67.2);
  - la sombra recombinada que cae por debajo de `dna_min_length` (y usa la sombra de la fuente) mientras el ADN real recombinado no (D67.2, precisión 28);
  - la conjugación espejo con transferencias fijadas a mano: también cuando CRISPR bloquea la transferencia real, sin extracción si la sombra del donante no tiene plásmidos, y con la sombra del donante tomada al empezar el paso cuando el donante fue receptor antes en el orden de aplicación (D67.5); la sombra sin ensayos ni purgas CRISPR (D67.6);
  - `Birth.shadow_dna` (D67.7);
  - la inercia: historiales reales y estado de todos los generadores salvo `shadow_rng` idénticos con la sombra activa y apagada, y con la sombra reemplazada a mitad de corrida (D73.2);
  - la identidad sin mutación en `25a` y `25b`, con $R_{13}$, $R_{26}$ y $R_{27}$ ablacionadas y $R_{38}$ y $R_{17}$ activas (D73.3);
  - el test AST de accesos (D73.4) y la igualdad entre procesos con distinto `PYTHONHASHSEED` (D73.5).
- [ ] 28.2 **[GREEN]** Implementar la herencia en `_give_birth` (con la pareja del cruce y los cortes proporcionales), la conjugación espejo y la sombra sin CRISPR. Ampliar la firma interna de `_draw_conjugations` para que devuelva también el donante (`(donante, receptor, codón)`), y copiar las sombras al empezar el paso de conjugación (D67.5).
- [ ] 28.3 **[REFACTOR]** Verificación del bloque.

## 29. Evaluación y telemetría de la sombra (`simulation-engine`, `experimental-suite`)

> Ejecuta: implementador-delicado

- [ ] 29.1 **[RED]** Tests para:
  - `ShadowEvaluationSystem` inmediatamente después del núcleo de la Fase 3 y antes de `InternalStateSystem`, **sin** la marca `notifies_decisions` (que sigue en el último sistema del núcleo, con `validate_systems` en verde, con y sin $R_{41}$), las elecciones innatas del fundador, real y de la sombra sin generadores y sin pesos plásticos, la lectura de `frame.shadow_decisions` en `on_tick_end`, y `ShadowStateSystem` con $R_{39}$ (D68.5, D68.6);
  - `ShadowTickMetrics` con sus campos en orden, `engine.shadow_history`, la población vacía y los nombres únicos (D69);
  - cada campo de sombra, incluidas `shadow_communicating_fraction` con el fenotipo de la sombra en `last_context`, `innate_share_choice` frente a `share_rate` y la actividad de la sombra con el mismo denominador (D69.2, D70). Al implementar la actividad de la sombra (y cualquier conjunto de codones o de agentes de la sombra), iterar los conjuntos con `sorted(...)`, como exige `CLAUDE.md` (Determinismo);
  - que la caché de la transcripción y de la evaluación de la sombra coincide con el cálculo directo;
  - que `GeneticTickMetrics`, `EcologyTickMetrics`, `TickMetrics` y `EvolutionaryTickMetrics` no cambian.
  - Exploratorio, marcado `empirical` (no bloquea): con `dna_codon_cost` alto, `mean_chromosome_length` real queda por debajo de `shadow_mean_chromosome_length` (control positivo del instrumento).
- [ ] 29.2 **[GREEN]** Implementar los sistemas, el observador y el colector de la sombra.
- [ ] 29.3 **[REFACTOR]** Verificación del bloque, con la inercia de D73.2 todavía en verde.

## 30. Atribución con sombra (`emergence-attribution`)

> Ejecuta: implementador-delicado

- [ ] 30.1 **[RED]** Ampliar `tests/test_attribution.py` con tests para:
  - `Phase25ShadowClaim` y su validación (incluidos `exploratory` y `joint_real_comparison`), `PHASE25_SHADOW_CLAIMS` (C21–C28) con métricas, `shadow_metric`, comparaciones, $R_C$, canales, $\delta_{\min}$ y enunciados (D72.2, D72.3);
  - las tres formas de diferencia, `values` y `comparison_values`, los pares válidos sin condiciones neutrales, la prueba de signo, Holm sobre C21–C26 ($m = 6$), C27 exploratoria y C28 fuera de Holm (`p_adjusted = None`), los umbrales relativos de C24 y C26, y la condición conjunta de C25 con `joint_median` (`None` en las demás y en D56) (D72.2–D72.5);
  - E4 sobre el exceso de la sombra y los efectos de regla con las semillas 72–81 (D72.7, D72.8), con `None` sin correr la variante para $R_{12}$, $R_{13}$ y $R_{24}$ en todas las afirmaciones y para $R_{32}$ en C22 y C26;
  - `PHASE25_SHADOW_PROTOCOL_CONFIGS`, sus condiciones y `PHASE25_SHADOW_SEEDS` disjuntas de las anteriores (D72.6);
  - `run_phase25_shadow_attribution`, su validación de configuraciones (sólo las base; no las variantes ablacionadas, como la de $R_{32}$) y la salida idéntica para cualquier `jobs` (D72.11);
  - que `PHASE25_CLAIMS` y la atribución de D56 no cambian.
- [ ] 30.2 **[GREEN]** Implementar en `attribution.py` el pre-registro aprobado en 0.8. Las constantes deben coincidir exactamente con design D72.
- [ ] 30.3 **[REFACTOR]** Verificación del bloque.

## 31. Runner, rendimiento y prueba de humo con semillas nuevas (`experimental-suite`)

> Ejecuta: implementador-delicado
>
> Punto de control: prueba de humo con sombra. Mostrar el costo por tick con sombra y, por protocolo, condición y semilla de 72–101, sólo la terminación, la generación máxima y la población final, con los pares válidos que anticipan.

- [ ] 31.1 **[RED]** Tests de `exp25_runner --shadow` con `--smoke` y `--attribution`: semillas por defecto, condiciones sin reproducción neutral, archivos de salida y salida idéntica para cualquier `--jobs`.
- [ ] 31.2 **[GREEN]** Implementar `--shadow` en `exp25_runner.py`, con el caché persistente (precisión 140).
- [ ] 31.3 Medir el costo por tick de `25b` con la sombra (D74.5). Si una corrida de `phase25` supera los 5 minutos, optimizar con historiales y `shadow_history` idénticos.
- [ ] 31.4 Correr la prueba de humo con sombra (D72.10) sobre `PHASE25_SHADOW_SEEDS`, **sin** calcular ni mirar ninguna métrica de C21–C28, y registrarla en `registros/` y en `docs/RESULTADOS.md`.
- [ ] 31.5 Actualizar `CLAUDE.md` (comandos y estado) y `README.md` con los comandos nuevos.

## 32. Corridas con sombra y registro

> Ejecuta: agente principal. Sin subagente: las corridas largas se hacen en el equipo del responsable del proyecto, y el agente principal registra e interpreta.
>
> Punto de control: resultados. Presentarlos tal cual, incluidos los negativos y las afirmaciones no evaluables, antes de cerrar la fase con 26.2 y 26.3.

- [ ] 32.1 Correr `python -m ide.experiments.exp25_runner --shadow --attribution` con `PHASE25_SHADOW_SEEDS` y los efectos de regla exploratorios con las semillas 72–81. Registrar todos los resultados en `registros/` y en `docs/RESULTADOS.md`, junto a los de D56 y sin tocar ninguno de los dos pre-registros.
