# Registro de resultados empíricos

Resultados tal cual se obtuvieron, positivos o negativos, **sin ajustar parámetros** a la vista de los datos (Decisión 10 de `design.md`). Cada entrada indica el commit del código que la produjo.

## Experimento 001: expectativas funcionales (bloque 9.5)

- **Código:** el commit que agrega esta entrada (bloque 9 de `tasks.md`; `git log -- RESULTADOS.md`).
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

## Rendimiento (línea base, `python -m ide.experiments.benchmark`)

Configuración base del Exp 001, 300 ticks, 3 repeticiones; contenedor compartido, con ruido entre corridas.

| Commit | Cambio | Mediana (ticks/s) |
| :--- | :--- | ---: |
| `e061beb` | Línea base del bloque 8 | 128.8 |
| `6636409` | Vecindades precalculadas y vecinos reutilizados en el ruteo (Decisión 18) | 193.5 (repeticiones de 180 a 234, en el `benchmark.json` de ese commit) |
