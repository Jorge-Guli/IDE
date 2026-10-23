# Registro de resultados empíricos

Resultados tal cual se obtuvieron, positivos o negativos, **sin ajustar parámetros** a la vista de los datos (Decisión 10 de `design.md`). Cada entrada indica el commit del código que la produjo.

> Las referencias a `design.md` y `tasks.md` de las entradas del Experimento 001 apuntan a los artefactos de la Fase I, hoy archivados en `openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/`.

## Experimento 001: expectativas funcionales (bloque 9.5)

- **Código:** el commit que agrega esta entrada (bloque 9 de `tasks.md`; `git log --follow -- docs/RESULTADOS.md`).
- **Comando:** `python -m pytest -m empirical` (16 tests, `SimulationConfig()` por defecto, perfil `quick`: 300 ticks; 001-B con inyección en el tick 80 al 25 %).
- **Resultado:** 16 de 16 pasan.
- **Alcance (regla de atribución):** H1 verifica que los mecanismos de comunicación programados cumplen su propósito. **No** es evidencia de emergencia: C1 y C2 son programadas por construcción (ver 001-D).

| Semilla | Precisión colectiva | Precisión aislada | Superávit | Cob. accesible colectiva | Cob. accesible aislada | Mensajes/agente | Rumor inicial | Rumor pico | Rumor final | Ticks a extinción |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 42 | 0.7998 | 0.5716 | +0.2282 | 0.3469 | 0.1427 | 1.455 | 0.2500 | 0.6000 | 0.0000 | 123 |
| 43 | 0.8480 | 0.6068 | +0.2412 | 0.3302 | 0.1469 | 1.400 | 0.2500 | 0.5250 | 0.0000 | 183 |
| 44 | 0.7849 | 0.5463 | +0.2385 | 0.3625 | 0.1354 | 1.435 | 0.2500 | 0.4500 | 0.0000 | 81 |
| 45 | 0.8224 | 0.5860 | +0.2364 | 0.3312 | 0.1448 | 1.463 | 0.2500 | 0.6750 | 0.0000 | 141 |
| 46 | 0.8314 | 0.5897 | +0.2417 | 0.3000 | 0.1500 | 1.428 | 0.2500 | 0.3625 | 0.0000 | 195 |

- **H1 (superávit):** positivo en las 5 semillas; prueba de signo unilateral `p = 0.03125 < 0.05`. La cobertura accesible colectiva supera a la aislada en las 5.
- **Contención del rumor (001-B):** el rumor falso se extingue por completo en las 5 semillas, entre 81 y 195 ticks después de la inyección.
- **Observación no prevista:** antes de extinguirse, el rumor **se propaga**. La prevalencia pico (0.36 a 0.68) es de 1.5 a 2.7 veces la inicial (0.25). La contención no es inmediata: la población primero amplifica la falsedad y luego la elimina. Si esa dinámica depende de los filtros diseñados (R3, R4, R6, R7) lo decide C3 en 001-D.

## Experimento 001-D: atribución de emergencia (bloque 10.3)

- **Pre-registro:** `DESIGN_RULES`, `EXP001_CLAIMS` y `ATTRIBUTION_PROFILE = "quick"` versionados en el commit `c05b8b3`, **antes** de implementar y ejecutar 001-D. Ningún $R_c$ se modificó a la vista de los resultados.
- **Código:** el commit que agrega esta entrada (bloque 10 de `tasks.md`). La corrida se repitió sobre el árbol final y dio un `exp001_attribution.json` idéntico byte a byte. Tras el cambio posterior que mide C4 sólo con la ablación de descubridores (sin el nivel 0.5, que se descartaba), se volvió a correr y el JSON también fue idéntico byte a byte. Lo mismo tras la optimización de vecindades y en la regresión completa posterior, ambas sobre el commit `6636409`.
- **Comando:** `python -m ide.experiments.exp001_runner --seeds 42 43 44 45 46 --attribution --jobs 4` (185 corridas distintas: unos 2 min 40 s con 4 procesos en la versión original, 1 min 51 s tras el cambio de C4 y alrededor de 1 min tras la optimización de vecindades del commit `6636409`).

### Tabla de estados (tal cual)

| Afirmación | Estado | Por construcción | p E2 (vs. aislada) | p E3 (sin $R_c$ vs. aislada) | p E4 (vs. control nulo) |
| :--- | :--- | :---: | ---: | ---: | ---: |
| C1 Acceso a conocimiento no poseído | `PROGRAMMED` | sí | 0.03125 | — | 0.03125 |
| C2 Superávit de decisión colectiva | `PROGRAMMED` | sí | 0.03125 | — | 0.03125 |
| C3 Inmunidad colectiva a la falsedad | `PROGRAMMED` | no | 0.03125 | 0.50000 | 0.03125 |
| C4 Persistencia extra-individual | `NOT_OBSERVED` | sí | 0.25000 | — | 0.25000 |

Valores por semilla (42..46):

| Afirmación | Variante | Valores |
| :--- | :--- | :--- |
| C1 (`accessible_coverage_mean` ↑) | completa / aislada / nulo | 0.347 0.330 0.363 0.331 0.300 / 0.143 0.147 0.135 0.145 0.150 / 0.158 0.179 0.163 0.157 0.171 |
| C2 (`cumulative_decision_accuracy` ↑) | completa / aislada / nulo | 0.800 0.848 0.785 0.822 0.831 / 0.572 0.607 0.546 0.586 0.590 / 0.532 0.524 0.487 0.542 0.502 |
| C3 (`final_false_prevalence` ↓) | completa / aislada / sin $R_c$ / nulo | 0 0 0 0 0 / 0.188 0.213 0.213 0.188 0.213 / 0.325 0.025 0.025 0.325 0.138 / 0.188 0.038 0.100 0.100 0.125 |
| C4 (`final_social_persistence_prevalence` ↑) | completa / aislada / nulo | 0 0 0.100 0 0.545 / 0 0 0 0 0 / 0 0 0 0 0 |

### Perfil de contribución (`rule_effects`: media de la diferencia orientada entre la población completa y la población sin esa regla; positivo = la regla ayuda)

| Afirmación | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 | R11 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C1 | +0.036 | +0.022 | +0.007 | +0.005 | +0.000 | +0.088 | −0.036 | +0.334 | +0.012 |
| C2 | −0.000 | −0.012 | +0.038 | +0.088 | +0.000 | +0.023 | +0.047 | +0.331 | +0.163 |
| C3 | +0.000 | +0.010 | +0.000 | +0.000 | +0.000 | +0.045 | +0.003 | +0.982 | +0.000 |
| C4 | −0.079 | −0.201 | +0.114 | −0.198 | +0.000 | −0.183 | +0.125 | +0.129 | +0.092 |

### Lectura

- **C1 y C2: programadas por construcción, como se declaró de antemano.** La comunicación da acceso y mejores decisiones (E2). Para C2, el efecto depende del contenido de los mensajes (E4: el control nulo no lo produce). Para C1, E4 es casi tautológico: bajo el control nulo no hay canal de consulta veraz, así que su cobertura accesible es por definición la individual. Es la verificación de que el mecanismo diseñado funciona, no evidencia de emergencia.
- **C3: la única prueba empírica genuina da negativo para la emergencia.** La población completa extingue el rumor en las 5 semillas, pero sin los filtros diseñados (R3, R4, R6, R7) la contención deja de superar a la población aislada: dos semillas quedan peor (0.325), tres mejor (0.025 a 0.138), y p = 0.5. La inmunidad colectiva depende de las reglas epistémicas programadas para producirla.
- **C4: no observada en el perfil `quick`.** Es por construcción, pero el estado sigue el orden de la clasificación: como falla E2, es `NOT_OBSERVED` y no `PROGRAMMED`. Tras eliminar a los descubridores de `p_0` y retirar su estímulo, el conocimiento social sobrevive 100 ticks sólo en 2 de 5 semillas (en la 46, el 55 % de 11 sobrevivientes lo conserva). Al descartar los empates en cero, la prueba de signo tiene n = 2 y no alcanza significancia.
- **Exploración ε (R10) domina el perfil de contribución:** sin ella, C1 y C2 caen unos 0.33 y el rumor de C3 no se extingue nunca (+0.98). Es la trampa de evitación de la Decisión 12: sin explorar, nadie vuelve a probar el patrón que el rumor declaró dañino.
- **R7 (duda ante contradicción) tiene efecto exactamente nulo en las cuatro afirmaciones.** En C1, C2 y C4 no hay ninguna creencia de signo falso, así que nunca se produce una contradicción; en C3 la población llega a 0 con R7 y sin ella.
- **La difusión espontánea (R9) reduce levemente la cobertura accesible (C1: −0.036).** Es compatible con el *thrashing* de memoria previsto en la Decisión 4.
- **C4 tiene efectos grandes y de signo variable** con sólo 2 de 5 semillas distintas de cero. No conviene interpretarlos sin más semillas o un perfil más largo.

## Cierre del proyecto (bloque 11)

Verificación con `src/` idéntico al del commit `360c771`; `tests/` también, salvo el test del oráculo agregado en la revisión del cierre (es una auditoría sobre el AST de `src/` que no altera lo que ejercitan los demás tests: `slow`, `empirical`, la corrida de la CLI y `openspec validate` se ejecutaron antes de agregarlo y no dependen de él; la suite con cobertura en 3.13 y las pasadas en 3.11 y 3.12 se repitieron con la versión final del test, y dieron 379 pasados en las tres), sin ajustar parámetros:

- `ruff check`, `ruff format --check` y `pyright`: sin errores ni advertencias.
- `python -m pytest --cov=ide`: 378 pasan, 18 deseleccionados; cobertura total 98 %. Tras agregar el test del oráculo: 379 pasan con cobertura total 98 %, y también en Python 3.11 y 3.12 (en la verificación de 360c771 el CI sólo probaba 3.13; un job `Compatibilidad` con 3.11 y 3.12 se agregó después en `ci.yml`, y la suite pasó en las tres versiones tanto en local como en el CI del PR 9).
- `python -m pytest -m slow`: 2 pasan (001-D completo con 5 semillas).
- `python -m pytest -m empirical`: 16 de 16 pasan, repetido sobre el código final (tras la optimización de vecindades y la revisión cruzada).
- `openspec validate --all --strict`: pasa.
- `python -m ide.experiments.exp001_runner --seeds 42 43 44 45 46 --jobs 2` (perfil `full`): superávit positivo en las 5 semillas (+0.145 a +0.177), prueba de signo `p = 0.03125`, rumor final 0.000 en las 5 (inicial 0.250). La persistencia social final de este protocolo (001-C del perfil `full`) es 0.000 en las 5 semillas. Es otra medición que la de 001-D (perfil `quick`, ablación de descubridores con retiro del estímulo, donde 2 de 5 semillas conservan conocimiento social); no se comparan ni se usan como confirmación mutua.
- Invariantes del checklist cubiertos por la suite de software: aislamiento de capas y protocolo aislado (`test_auditoria_de_importaciones` y `test_auditoria_del_protocolo` en `tests/test_micro_agent.py`), ausencia de `true_value` en lo visible (`test_campos_exactos_de_visible_resource` en `tests/test_domain_contracts.py`; que sólo `SimulationEngine` invoque `get_reachable_true_values` lo cubre `test_oraculo_de_verdad_nadie_fuera_del_motor_lo_referencia` en `tests/test_simulation_engine.py`, agregado en la revisión del cierre), invariante de memoria y determinismo intra e inter-proceso (`tests/test_simulation_engine.py`), anti-eco (`tests/test_epistemology.py`), y paralelismo inocuo y determinismo de la CLI con `PYTHONHASHSEED` 0 y 1 y `--jobs 1` frente a `--jobs 2` (`tests/test_exp001_suite.py`). Todos pasan en la corrida de arriba.

## Fase II: prueba de humo del perfil pre-registrado (design D29, tarea 6.2)

- **Pre-registro:** `PHASE2_DESIGN_RULES`, `EXP002_CLAIMS`, `EXP003_CLAIMS` y el perfil de corrida versionados en el commit `7375a8c`, **antes** de implementar los runners 002 y 003.
- **Código:** `7375a8c` (motor del bloque 5, sin los runners).
- **Qué se mide:** sólo que la corrida termina y la generación máxima (`max(m.max_generation)` sobre `engine.evolutionary_history`), como fija D29. **No** se calcularon ni se miraron las métricas de las afirmaciones C5 a C8.
- **Comando:** para cada protocolo `p` y cada semilla `s` de `PHASE2_SEEDS`, `SimulationEngine(replace(PHASE2_PROTOCOL_CONFIGS[p], seed=s))` con las configuraciones de `7375a8c`, que hoy son `PHASE2_PROTOCOL_CONFIGS_ORIGINAL`, durante `PROFILES["phase2"].total_ticks = 2000` ticks.

| Protocolo | Termina (2000 ticks) | Gen. máx. 42 | 43 | 44 | 45 | 46 | 47 | 48 | 49 | 50 | 51 |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `002a` | sí | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 |
| `002b` | sí | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 |
| `003a` | sí | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `003b` | sí | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

- **Resultado:** las 40 corridas terminan. La generación máxima es 0 o 1 en todas: con el perfil pre-registrado la población **no llega a varias generaciones**. Cada corrida de 2000 ticks tardó alrededor de 1 s, mucho menos que una población activa, lo que sugiere una extinción temprana; no se verificó, porque D29 limita la prueba de humo a estas dos observaciones.
- **Lectura, sin ajustar parámetros:** D29 prohíbe cambiar el perfil a la vista de los resultados y pide reportar la extinción o la falta de generaciones como resultado. Es coherente con la física declarada (D21): con los valores por defecto, el costo basal de un fundador es $0.01 + 0.002 \cdot 3^2 + 0.0005 \cdot (2^2 + 2^2) = 0.032$ por tick, y con `initial_energy = 1.5` un agente que no come muere en unos 47 ticks. Con este perfil, las afirmaciones C5 a C8, que dependen de la sucesión generacional, de los holones o de ambas, difícilmente tengan con qué medirse. Cambiar el perfil sería modificar el pre-registro: exige una decisión explícita y un commit que la justifique.

## Fase II: calibración de viabilidad del perfil (Enmienda 1 de D29, tarea 6.4)

- **Procedimiento:** declarado en `02c6a56` y ampliado en `aa47715`, antes de leer cualquier salida. Calibra sólo `resources_per_pattern` en la grilla 10, 20, 40, 80 con las semillas 0 a 9. Una corrida es viable si la población sigue viva a los 2000 ticks y llegó al menos a la generación 5; un valor es viable con al menos 8 de 10 semillas viables en cada condición de comparación. Sólo registra demografía: **no** se calculó ninguna métrica de C5 a C8.
- **Salidas completas:** `registros/phase2_calibration.json` y `registros/phase2_calibration_consola.txt` (corrida con el criterio ampliado, 87 min con 4 procesos); `registros/phase2_calibration_antecedente*` (antecedente).

### Antecedente: criterio limitado a la base (commit `02c6a56`)

Terminó antes de ampliar el criterio, y su salida se leyó recién después de commitear la ampliación (`aa47715`). Con ese criterio habría elegido `resources_per_pattern = 20`: con 10 se extinguen las 10 semillas de los cuatro protocolos, y con 20 las cuatro bases son viables en 10 de 10. No se usa para elegir.

### Corrida con el criterio ampliado

Semillas viables (de 10) por condición. Entre paréntesis, las semillas con población viva al final cuando difieren de las viables:

| Condición | 10 | 20 | 40 | 80 |
| :--- | ---: | ---: | ---: | ---: |
| 002-A `evolved` | 0 | 10 | 1 (10 vivas) | 0 (10 vivas) |
| 002-A `frozen_genome` | 0 | 10 | 3 (10 vivas) | 0 (10 vivas) |
| 002-A `drift` | 0 | 10 | 0 (10 vivas) | 0 (10 vivas) |
| 002-A `null_content` | 0 | **2** | 10 | 2 (10 vivas) |
| 002-B `cultural` | 0 | 10 | 1 (10 vivas) | 0 (10 vivas) |
| 002-B `tabula_rasa` | 0 | 10 | 1 (10 vivas) | 0 (10 vivas) |
| 002-B `null_content` | 0 | **1** | 10 | 2 (10 vivas) |
| 003-A `holonic` / 003-B `with_view` | 0 | 10 | 10 | 3 (10 vivas) |
| 003-A `individual` | 0 | 9 | 1 (10 vivas) | 0 (10 vivas) |
| 003-B `without_view` | 0 | 10 | 9 | 2 (10 vivas) |
| 003-A/B `null_content` | 0 | **1** | 10 | 7 (10 vivas) |

- **Resultado:** ningún valor es viable; no se elige nada y se consulta, como fija la enmienda. El responsable del proyecto decidió entonces la Enmienda 1b (grilla refinada, abajo).
- **Con 10** se extinguen todas las condiciones.
- **Con 20** todas las condiciones de los runners son viables (la peor, 003-A `individual`, 9 de 10), pero el **control nulo** se extingue en 8 o 9 de 10 semillas: con el contenido de las creencias reemplazado al azar, la población no sobrevive. Es justo el sesgo que la ampliación buscaba detectar: medida con 20, la comparación E4 (completa frente a control nulo) ganaría por extinción del control.
- **Con 40 y 80** todas las poblaciones siguen vivas, pero la mayoría no llega a la generación 5: el criterio falla por falta de recambio generacional, no por extinción. Una explicación posible, **no verificada**, es que con abundancia la población llega pronto al tope `max_population = 160` y casi no nace nadie. El control nulo, que se extingue con 20, es viable con 40.

### Grilla refinada (Enmienda 1b)

- **Código y equipo:** `d60ffa6` (mergeado en main como `f8cdad3`), corrido en el equipo del responsable del proyecto con `python -m ide.experiments.phase2_calibration --refined --jobs $env:NUMBER_OF_PROCESSORS` (el resultado no depende de `--jobs`). Mismo criterio y mismas semillas (0 a 9) que la grilla original. Salida completa en `registros/phase2_calibration_refinada.json` (390 corridas, `chosen: null`, `fallback: 20`) y `registros/phase2_calibration_refinada_consola.txt`; se verificó que las 39 líneas de la consola coinciden con el JSON.

| Condición | 25 | 30 | 35 |
| :--- | ---: | ---: | ---: |
| 002-A `evolved` | 10 | 2 (10 vivas) | 1 (10 vivas) |
| 002-A `frozen_genome` | 8 (10 vivas) | 5 (10 vivas) | 0 (10 vivas) |
| 002-A `drift` | 8 (10 vivas) | 2 (10 vivas) | 0 (10 vivas) |
| 002-A `null_content` | 10 | 10 | 10 |
| 002-B `cultural` | 8 (10 vivas) | 3 (10 vivas) | 1 (10 vivas) |
| 002-B `tabula_rasa` | 10 | 2 (10 vivas) | 1 (10 vivas) |
| 002-B `null_content` | 8 | 10 | 10 |
| 003-A `holonic` / 003-B `with_view` | 10 | 10 | 10 |
| 003-A `individual` | 8 (10 vivas) | 3 (10 vivas) | 2 (10 vivas) |
| 003-B `without_view` | 10 | 10 | 10 |
| 003-A/B `null_content` | **5** | 10 | 10 |

- **Resultado:** ningún valor es viable. Con 25 sólo falla el control nulo de 003 (5 de 10); con 30 y 35 las condiciones de 002 y 003-A `individual` siguen vivas pero casi no llegan a la generación 5, el mismo patrón que con 40 y 80.
- **Salida de respaldo, fijada antes de esta corrida:** `resources_per_pattern = 20` (`PHASE2_RESOURCES_PER_PATTERN`), con E4 de C5 a C8 no interpretable (`ClaimEvaluation.e4_interpretable = False`) y cada `rule_effect` leído después de revisar su demografía (`ClaimEvaluation.demography`). Con 20, todas las condiciones de los runners son viables (9 o 10 de 10), pero el control nulo se extingue en 8 o 9 de 10.
- La extinción del control nulo con 20 es una observación demográfica de la calibración, con las semillas 0 a 9. No es una medición de C5 a C8, y el control nulo aleatoriza a la vez todos los canales (horizontal, herencia, estigmergia y vista), así que no aísla un mecanismo.
- **Sobre la hipótesis de saturación** (población final de los JSON, sin contar el control nulo): con 20, 80 de las 90 corridas terminan exactamente en el tope `max_population = 160`; con 40 y 80, las 90; con 25, 30 y 35, 267 de 270. Que la población llegue al tope es casi universal desde 20, incluso con 20, donde esas mismas condiciones sí llegan a las generaciones 7 a 12. Por lo tanto, alcanzar el tope **no explica por sí solo** la falta de recambio con más recursos. La causa sigue sin verificar (una posibilidad es que con abundancia casi nadie muere y el cupo no se libera, pero no se midió la mortalidad).

## Fase II: Experimentos 002 y 003 y su atribución (bloque 7.1)

- **Pre-registro:** `PHASE2_DESIGN_RULES`, `EXP002_CLAIMS`, `EXP003_CLAIMS`, canales, reglas inactivas y perfil `phase2` versionados en `7375a8c`, antes de los runners; enmiendas del perfil (Enmiendas 1 y 1b de D29) con sus commits y la salida de respaldo `resources_per_pattern = 20` (arriba). Ninguna afirmación ni $R_C$ se modificó a la vista de estos resultados.
- **Código:** main en `60c5dcb`. Corrido en el equipo del responsable del proyecto con los comandos del bloque 7 (`exp002_runner` y `exp003_runner`, con `--seeds 42 … 51`, `--attribution` y `--reference`). Se verificó que las 80 configuraciones de los 40 JSON por semilla y las de las 4 atribuciones son exactamente las de `PHASE2_PROTOCOL_CONFIGS` y `PHASE2_PROTOCOL_CONFIGS_ORIGINAL` del código. **Reproducibilidad entre plataformas:** `exp002_runner --reference --seeds 42`, regenerado en Linux, da un JSON idéntico byte a byte al del equipo Windows (salvo fines de línea).
- **Salidas completas:** `registros/fase2/` (JSON por semilla, agregados, atribuciones y consolas, normalizados a UTF-8).

### Tabla de estados (tal cual)

| Afirmación | Estado | Por construcción | p E2 (vs. aislada) | p E4 (vs. control nulo, **no interpretable**) |
| :--- | :--- | :---: | ---: | ---: |
| C5 Aceleración cultural intergeneracional | `NOT_OBSERVED` | sí | 0.37695 | 0.00098 |
| C6 Adaptación evolutiva por selección | `NOT_OBSERVED` | sí | 0.82812 | 0.00098 |
| C7 Superávit cooperativo sobre recursos compuestos | `NOT_OBSERVED` | sí | 0.14453 | 0.01562 |
| C8 Cobertura colectiva adquirida sin causalidad descendente | `NOT_OBSERVED` | sí | 0.82812 | 1.00000 |

Valores por semilla (42..51), población completa / variante aislada:

| Afirmación (métrica ↑) | Completa | Aislada |
| :--- | :--- | :--- |
| C5 (`cultural_accuracy`; aislada: sin $R_{14}$) | 0.853 0.872 0.865 0.837 0.841 0.822 0.846 0.803 0.859 0.847 | 0.838 0.854 0.834 0.841 0.848 0.818 0.840 0.832 0.860 0.817 |
| C6 (`evolved_accuracy`; aislada: deriva, sin $R_{12}$) | 0.838 0.854 0.834 0.841 0.848 0.818 0.840 0.832 0.860 0.817 | 0.822 0.847 0.842 0.844 0.841 0.841 0.852 0.839 0.847 0.838 |
| C7 (`holonic_composite_completions`; aislada: sin $R_{15}$) | 1 0 0 1 1 1 0 1 0 1 | 0 0 1 0 0 0 0 0 2 0 |
| C8 (`mean_acquired_coverage`; aislada: sin $R_{22}$) | −0.005 −0.025 0.064 −0.000 −0.046 −0.037 −0.095 −0.035 −0.005 −0.014 | 0.012 −0.110 −0.009 0.009 −0.010 −0.052 −0.040 −0.044 0.012 0.023 |

### Lectura

- **Ninguna de las cuatro afirmaciones se observa.** Las cuatro estaban declaradas programadas por construcción (D29): ni siquiera los mecanismos diseñados para producirlas muestran el efecto con el perfil pre-registrado. Con 10 semillas y estos tamaños de efecto, el resultado es "no detectado", no "efecto nulo demostrado". Es un resultado negativo y se reporta tal cual.
- **C5:** la herencia cultural no supera a la tabula rasa (diferencia media +0.006; 6 de 10 semillas a favor, p = 0.38). La proporción social de los descendientes (M9) es la misma con y sin $R_{14}$ (0.158 frente a 0.160), y el tick de convergencia también (45.1 frente a 44.7, con desvíos de 30 y 38).
- **C6:** la selección no supera a la deriva (diferencia media −0.003, p = 0.83). **Observación exploratoria no prevista:** el genoma congelado supera a la evolución en las 10 semillas (`adaptation_gain` medio −0.047; precisión 0.885 frente a 0.838), y la capacidad de memoria media final baja de 3 (fundadores) a 1.9. El sesgo declarado de $R_{21}$ es encarecer la hipertrofia individual ($C_{\max}^2$ y radios²) y favorecer la cooperación; una **hipótesis no verificada** es que ese costo seleccione memorias chicas a costa de la precisión. Sin $R_{21}$ la precisión es 0.886, casi la del genoma congelado, pero esas poblaciones apenas llegan a las generaciones 2 a 5, así que el dato no separa las dos explicaciones.
- **C7:** los recursos compuestos casi nunca se resuelven: 0.6 resoluciones por corrida de 2000 ticks con holones y 0.3 sin ellos (6 semillas a favor, 2 en contra y 2 empates; p = 0.14, con poca potencia para conteos de 0 a 2). Una **hipótesis no verificada** es que, con `composite_order = 4`, el grupo local casi nunca reúne a la vez los cuatro fragmentos con confianza suficiente. Los holones alcanzan en las 10 semillas el nivel 7, que es el techo estructural (con `max_holon_leaves = 8`, sólo se llega con una cadena de fusiones de 8 hojas), y la condición con holones tiene mucho más recambio que la aislada (generación máxima media 21.0 frente a 9.3). La condición completa de 003 se **extingue en la semilla 44** (población final 0, generación 11), en C7 y en C8.
- **C8:** la cobertura colectiva adquirida es prácticamente nula y algo negativa con y sin la vista del holón (−0.020 frente a −0.021, p = 0.83). Las exposiciones medias se parecen (12 641 y 14 206 pares tick-holón), pero no en todas las semillas: en la 44, la condición con vista se extingue y su valor (0.064, el más alto de la serie) se mide con 1224 pares frente a 13 867 sin la vista. Sin la vista, varias poblaciones terminan lejos del tope (28, 62, 99 y 103 agentes; media 120 frente a 138 con vista). La reducción de redundancia es negativa en ambas condiciones (−0.052 y −0.043): como D29 la define como $\text{red}_0 - \text{red}$, las hojas de un holón tienden a duplicar más, no menos, desde que se formaron.
- **E4 no se interpreta** (salida de respaldo de la Enmienda 1b): el control nulo se extingue en 9 o 10 de 10 semillas en las cuatro afirmaciones, así que sus valores reflejan la extinción. En C8 el control nulo da incluso una cobertura adquirida mayor (media 0.116, p E4 = 1.0), medida mientras su población colapsa.
- **Efectos de regla (`rule_effects`), leídos con su demografía (`ClaimEvaluation.demography`):**
  - **No interpretables por extinción:** sin $R_{10}$ (exploración) o sin $R_{11}$ (navegación) la población se extingue en las 10 semillas de las cuatro afirmaciones (efectos de +0.25 a +0.36 en precisión en C5 y C6, +0.6 compuestos en C7, −0.28 en C8 para $R_{11}$). Sin $R_{9}$ (difusión) se extingue en 9 de 10 semillas en 003 (efectos +0.6 en C7 y −0.107 en C8). En C8 no tienen medición las variantes sin $R_{10}$ y sin $R_{15}$ (efecto `None`).
  - **C5 y C6:** sin contar los anteriores, los efectos son menores que 0.05 en valor absoluto, salvo $R_{13}$ (−0.041 en C5 y −0.047 en C6, que en C6 es el mismo `adaptation_gain` comentado arriba) y $R_{21}$ (−0.042 y −0.048, con poblaciones que casi no llegan a la generación 5). En C6, sin $R_{9}$ hay 3 extinciones de 10 y sin $R_{6}$ una, así que esos efectos chicos tampoco tienen demografía del todo comparable.
  - **C7, con efectos grandes:** sin $R_{5}$ (consenso), 3.3 compuestos frente a 0.6 (efecto −2.7), con demografía comparable (160 agentes en 9 de 10 semillas, generaciones 16 a 26): es el efecto más claro con demografía comparable. Sin $R_{21}$, 5 compuestos más por corrida (efecto −5.0), con poblaciones que casi no llegan a la generación 5. Sin $R_{23}$ (coordinación y reparto energético del holón), 2.9 (efecto −2.3), con generaciones 6 a 10. Sin $R_{13}$ (mutación), 2.6 (efecto −2.0), con una extinción y poblaciones de 66 a 98 agentes. Varias ablaciones distintas multiplican los compuestos, así que ninguna explicación de una sola regla queda sostenida. Además, que quitar $R_{21}$ aumente las resoluciones va en sentido contrario a su sesgo declarado a favor de cooperar.
  - **C8:** sin $R_{5}$, +0.066 con demografía comparable; sin $R_{13}$, −0.061, con una extinción. Los demás son menores.
- **Referencia con las configuraciones originales** (`resources_per_pattern = 8`): la condición completa llega a la generación 0 o 1, y las cuatro afirmaciones también son `NOT_OBSERVED` (p E2 de 0.5 a 1.0). Es coherente con la prueba de humo, que no había llegado a verificar la extinción. **Observación exploratoria:** con esas configuraciones, quitar $R_{21}$ evita la inviabilidad. En 002 ninguna semilla se extingue (generaciones 4 a 7, precisión 0.886); en 003 se extinguen 2 de 10 y se resuelven 12.1 compuestos de media. No se afirma una causa.
- **Consecuencia para la Fase II:** el diseño ya declaraba que la Fase II no tenía ninguna prueba genuina pre-registrada. Con este perfil, además, ninguno de sus mecanismos diseñados (herencia cultural, selección, holones, vista compartida) produce el beneficio funcional que se le atribuía. Las observaciones exploratorias quedan como preguntas para un diseño nuevo, no como resultados de éste: el genoma congelado rinde más que la evolución; los compuestos casi no se resuelven y varias ablaciones ($R_{5}$, $R_{13}$, $R_{21}$, $R_{23}$) los multiplican; la redundancia de los holones crece; y sin $R_{21}$ el perfil original deja de ser inviable.

## Fase II-B: diagnóstico del "Tapón de Matusalén" (tarea 0.1, design D42)

- **Qué es:** un diagnóstico **exploratorio y sólo demográfico**, previo a aprobar el pre-registro de la Fase II-B. Decide si se mantienen la regla $R_{29}$ (senescencia) y la afirmación C10. No calcula ninguna métrica de afirmación.
- **Criterio, fijado de antemano** (decisión del 2026-10-20, commiteado con el script en `e186dd6` antes de correrlo): la hipótesis se confirma si, en al menos 8 de las 10 semillas de cada protocolo, más de la mitad de los agentes vivos en el tick 2000 nació antes del tick 1000.
- **Comando y configuraciones:** `python registros/diagnostico_tapon/diagnostico_tapon.py --jobs 4`. Corre `PHASE2_PROTOCOL_CONFIGS_ORIGINAL["002a"]` y `["003a"]` (genoma plano de la Fase II) con `resources_per_pattern = 40`, las semillas de calibración 0 a 9 y 2000 ticks. La salida completa está en `registros/diagnostico_tapon/`.

| Protocolo | Población final | Vivos nacidos antes del tick 1000 | Muertes por tick (ticks 1000–2000) | Mediana de edad al morir |
| :--- | :--- | :--- | :--- | :--- |
| `002a` | 160 en las 10 semillas | 99 % en las 10 semillas | 0.001 a 0.002 | 75 a 110 ticks |
| `003a` | 160 en las 10 semillas | 71 % a 97 % | 0.006 a 0.065 | 89 a 126 ticks |

- **Resultado: confirmada.** Las 10 semillas de cada protocolo cumplen el criterio.
- **Lectura:**
  - **Con abundancia, la población queda congelada en el tope.** Los agentes que mueren, mueren jóvenes, con una mediana de alrededor de 100 ticks. Los que se establecen casi no mueren más: en `002a` hay 1 o 2 muertes en los últimos 1000 ticks. Sin muertes, el cupo no se libera y casi no nace nadie.
  - **Esto verifica la causa que la calibración de la Fase II dejó abierta.** Explica la falta de recambio generacional con abundancia.
  - **Los holones (`003a`) dan algo más de recambio,** pero el congelamiento domina igual.
  - **Alcance.** Es una observación demográfica con el genoma plano de la Fase II, no una medición de ninguna afirmación. No dice nada sobre el efecto de la senescencia, que es lo que pondrá a prueba C10.

## Fase II-B: compuerta de viabilidad (D55, tarea 23.4)

Corrida el 2026-10-22 con `python -m ide.experiments.phase25_viability --out registros/phase25_viability.json`, el perfil pre-registrado `phase25` (5000 ticks) y las semillas de viabilidad 0 a 9. La salida completa está en `registros/phase25_viability.json` y `registros/phase25_viability_consola.txt`. Es sólo demografía: no se calculó ni se miró ninguna métrica de afirmación.

**Resultado (tal cual): ninguna configuración de la grilla declarada es viable.** Según D55.5, decide el responsable del proyecto; no se prueba nada fuera de la grilla sin una enmienda.

Semillas viables (de 10) por condición que decide, en las dos configuraciones más abundantes:

| Protocolo y condición | (30, 10) | (40, 20) |
| :--- | ---: | ---: |
| `25a` full / drift | 7 / 5 | 8 / 4 |
| `25a` no_predation / no_predation_drift | 10 / 9 | 10 / 9 |
| `25b` full / drift | 6 / 7 | 7 / 6 |
| `25c` full / drift | 0 / 4 | 7 / 1 |
| `25d` full / drift / stable / stable_drift / no_learning | 3 / 2 / 7 / 5 / 2 | 3 / 1 / 8 / 4 / 3 |

Observaciones demográficas (exploratorias, no son afirmaciones):
- La viabilidad crece con la abundancia en todos los protocolos; con (20, 20) se extinguen todas las corridas.
- Las condiciones con reproducción neutral (`drift`) sobreviven mucho menos que las de selección (en `25c`, 7 frente a 1 con (40, 20)): sin selección la población no se sostiene.
- El entorno cambiante de `25d` es muy letal: `full` 3/10 frente a `stable` 8/10 con la misma abundancia.
- Sin comunicación de partida (`25c`), con poca abundancia la población muere en las primeras generaciones (generación máxima 1 a 5).

## Fase II-B: Enmienda 2 de la compuerta de viabilidad (D55.7, tarea 23.5)

Corrida el 2026-10-22 con `python -m ide.experiments.phase25_viability --amendment2 --out registros/phase25_viability_enmienda2.json`, con el mismo perfil (5000 ticks), las mismas semillas (0 a 9) y el mismo criterio, sobre la grilla extendida (60, 20), (60, 10), (80, 20) y (80, 10). Salida completa en `registros/phase25_viability_enmienda2.json` y `registros/phase25_viability_enmienda2_consola.txt`. Sólo demografía: ninguna métrica de afirmación.

**Resultado (tal cual): ninguna configuración de la grilla extendida es viable. Rige la salida de respaldo fijada de antemano: (80, 20)**, la de más semillas viables sumadas sobre las condiciones que deciden (95 de 130; le siguen (60, 10) con 84 y (60, 20) con 80). Las afirmaciones con menos de 20 pares válidos quedarán `NOT_OBSERVED` con `evaluable = False` (precisión 45). `null_content` es viable en 10 de 10 semillas en los cuatro protocolos, así que E4 es interpretable.

Semillas viables (de 10) con (80, 20):

| Protocolo | Condiciones que deciden |
| :--- | :--- |
| `25a` | full 10, drift 5, no_predation 10, no_predation_drift 10 |
| `25b` | full 10, drift 2 |
| `25c` | full 10, drift 5 |
| `25d` | full 6, drift 7, stable 10, stable_drift 5, no_learning 5 |

Observaciones demográficas (exploratorias, no son afirmaciones):
- Lo que limita la viabilidad es siempre la reproducción neutral (`drift`, 2 a 7 de 10) y el entorno cambiante de `25d`; con selección y entorno estable, la población sobrevive en 10 de 10.
- Con abundancia alta y reposición rápida (retardo 10), muchas corridas terminan con hojas vivas pero menos de 20 generaciones (por ejemplo, `25a` no_predation con (80, 10): 10/10 vivas y 0/10 viables): sin escasez casi no hay recambio generacional, el mismo "Tapón de Matusalén" que diagnosticó la tarea 0.1 en la Fase II.

## Fase II-B: prueba de humo (D56, tarea 24.1)

Corrida el 2026-10-23 con `python -m ide.experiments.exp25_runner --smoke --cache --out registros` sobre la configuración fijada por la compuerta, (80, 20) (commit `536c845`), el perfil `phase25` (5000 ticks) y `PHASE25_SEEDS` (42 a 71): 510 corridas, todas terminaron sin error. Salida completa en `registros/exp25_phase25_smoke.json` y `registros/exp25_phase25_smoke_consola.txt`. Sólo terminación, generación máxima y población final; los motores corrieron sin telemetría, así que no se calculó ninguna métrica de afirmación.

| Protocolo | Condición | Con población final | Generación máxima (mediana) | Población final (mediana) |
| :--- | :--- | ---: | ---: | ---: |
| `25a` | drift | 16/30 | 41.5 | 23.5 |
| `25a` | full | 30/30 | 177 | 52.5 |
| `25a` | no_predation | 30/30 | 26 | 103 |
| `25a` | no_predation_drift | 30/30 | 28 | 127 |
| `25a` | null_content | 29/30 | 69 | 49 |
| `25b` | drift | 19/30 | 80.5 | 39.5 |
| `25b` | full | 29/30 | 177 | 48.5 |
| `25b` | null_content | 30/30 | 66 | 40 |
| `25c` | drift | 9/30 | 20.5 | 0 |
| `25c` | full | 30/30 | 33.5 | 55.5 |
| `25c` | null_content | 30/30 | 33.5 | 55.5 |
| `25d` | drift | 7/30 | 41.5 | 0 |
| `25d` | full | 19/30 | 142 | 16.5 |
| `25d` | no_learning | 20/30 | 143.5 | 20 |
| `25d` | null_content | 18/30 | 56.5 | 13 |
| `25d` | stable | 30/30 | 177 | 52.5 |
| `25d` | stable_drift | 16/30 | 41.5 | 23.5 |

Observaciones demográficas (no son afirmaciones): con 30 semillas se repite el patrón de la compuerta. Con selección y entorno estable la población sobrevive (30 de 30). Con reproducción neutral (`drift`) sobreviven entre 7 y 19 de 30, menos que los 20 pares válidos que exige la precisión 45, y lo mismo pasa con `25d` full (19 de 30).

## Rendimiento (línea base, `python -m ide.experiments.benchmark`)

Configuración base del Exp 001, 300 ticks, 3 repeticiones; contenedor compartido, con ruido entre corridas.

| Commit | Cambio | Mediana (ticks/s) |
| :--- | :--- | ---: |
| `e061beb` | Línea base del bloque 8 | 128.8 |
| `6636409` | Vecindades precalculadas y vecinos reutilizados en el ruteo (Decisión 18) | 193.5 (repeticiones de 180 a 234, en el `benchmark.json` de ese commit) |
