# Design: Plataforma de Inteligencia Distribuida Emergente (IDE)

> **Jerarquía normativa.** Ante cualquier discrepancia entre documentos, rige este orden:
> 1. `specs/*/spec.md` (requisitos verificables),
> 2. este `design.md` (firmas, fórmulas y reglas de desempate exactas),
> 3. [`DEFINICIONES_TECNICAS.md`](../../../DEFINICIONES_TECNICAS.md) y [`DEFINICIONES_FORMALES.md`](../../../DEFINICIONES_FORMALES.md) (contexto y fundamento),
> 4. [`DOCUMENTO_FUNDACIONAL.md`](../../../DOCUMENTO_FUNDACIONAL.md) (visión).

## Context

El proyecto IDE parte de los fundamentos establecidos en el Documento Fundacional y las Definiciones Formales y Técnicas. El repositorio contiene únicamente documentación (`greenfield`). El diseño debe permitir implementar el **Experimento 001** (Memoria y Propagación Colectiva en Grilla 2D Toroidal) asegurando que el núcleo cognitivo de los agentes sea reutilizable en entornos futuros (grafos, espacios continuos, microrrobótica) y en los Experimentos 002 a 007.

## Goals / Non-Goals

**Goals:**
- Aislamiento estricto entre la cognición local (`src/ide/agent/`) y la geometría del entorno (`src/ide/environments/`) mediante el puerto `EnvironmentPort`.
- Ningún agente accede a estado global ni a `Resource.true_value` antes de interactuar físicamente.
- Búsqueda de vecindad en `ToroidalGrid2D` con costo independiente del tamaño del tablero (índice espacial por celda).
- Reproducibilidad bit a bit **entre procesos distintos**, no sólo dentro del mismo proceso (ver Decisión 6).
- Contratos extensibles (confianza social, capacidades, reglas compuestas, evolución) para los Experimentos 002–006 sin reescribir el motor.
- Separar la **validación del software** (tests que deben pasar siempre) de la **validación de hipótesis científicas** (resultados que pueden ser negativos y deben reportarse tal cual).
- **Regla de atribución de emergencia** (Decisión 13): ninguna propiedad se declara emergente si no puede distinguirse de una capacidad programada explícitamente en el agente. El software provee las ablaciones, los controles y la clasificación automática que lo verifican.
- Dejar la semántica del protocolo de comunicación aislada en un único módulo reemplazable (Decisión 14), para poder des-programarla progresivamente en experimentos posteriores.

**Non-Goals:**
- Interfaz gráfica acoplada al bucle de simulación; el motor corre *headless* y exporta JSON/CSV.
- Redes neuronales (PyTorch/TensorFlow) en el Experimento 001.
- Paralelismo no determinista.
- Estado interno de energía/salud $E_i(t)$ del agente: definido en el marco formal pero **fuera de alcance del Experimento 001** (los recursos no alteran la supervivencia; sólo se mide la calidad de decisión).
- Recursos neutrales ($v(r) = 0$): el Experimento 001 usa sólo valores $\pm 1.0$.
- Protocolo de comunicación aprendido (Exp 007): sólo se aísla la semántica del protocolo actual (Decisión 14).
- Barrido de densidad y radio para buscar transiciones abruptas (candidatas a emergencia genuina en el Experimento 001): queda para un cambio posterior.
- Lógica de especialización (Exp 003), reputación (Exp 002), shock (Exp 004), composición (Exp 005) y evolución (Exp 006): sólo se entregan los **contratos**; activar `enable_specialization=True`, `epsilon_recheck > 0` o `tau_policy="evidence_age"` lanza `NotImplementedError`.

## Decisions

### 1. Navegación agnóstica (`recommended_move` + `distance`)
- **Decisión:** El agente nunca recibe coordenadas. Cada `VisibleResource` trae `distance: int` y `recommended_move: Any` (el primer paso, perteneciente a `Observation.available_moves`, que acerca al recurso; `None` cuando `distance == 0`).
- **Racional:** Un vector relativo `(+2, 0)` exigiría que el agente conozca la geometría para convertirlo en un paso válido. Con el token de primer paso, el mismo `MicroAgent` funciona en grilla, grafo (primer salto de Dijkstra) o espacio continuo.
- **Reemplaza** al campo `relative_target` de versiones anteriores de `DEFINICIONES_TECNICAS.md`.

### 2. Separación `Resource` / `VisibleResource`
- **Decisión:** El entorno guarda `Resource(resource_id, pattern, true_value)` y proyecta `VisibleResource(resource_id, pattern, recommended_move, distance, is_reachable_now)`.
- **Racional:** Impide por construcción que el agente lea `true_value`.

### 3. Oráculo de telemetría separado del agente (`get_reachable_true_values`)
- **Decisión:** `EnvironmentPort.get_reachable_true_values(agent_id) -> dict[int, float]` (mapa `resource_id → true_value` de los recursos alcanzables) existe **sólo** para que el motor calcule M2. El motor jamás lo pasa a un agente.
- **Racional:** M2 juzga la **intención** de la decisión contra la verdad del entorno en el momento de decidir. Un `list[float]` perdería la correspondencia con el `resource_id` elegido; por eso es un `dict`.

### 4. Doble mecanismo de memoria colectiva: difusión + consulta en vivo
- **Decisión:** Difusión pasiva (`BROADCAST_BELIEF`) de las creencias de mayor utilidad con confianza $\ge c_{\text{umbral}}$, más consulta activa (`QUERY_PATTERN → QUERY_RESPONSE`) resuelta en el mismo tick antes de decidir.
- **Caché efímero:** Toda creencia asimilada socialmente en el tick se guarda en `_ephemeral_tick_beliefs: dict[Pattern, KnowledgeUnit]`, aunque `BoundedMemory.upsert` la rechace. El caché se vacía al inicio de `perceive_and_emit_messages`. No cuenta para la cobertura (M1) porque no es memoria persistente.
- **Racional:** Con $C_{\max}=3$ y $N=12$, la difusión sola produce *thrashing*; la consulta permite que un grupo de $G$ vecinos actúe como un meta-agente con hasta $G \cdot C_{\max}$ creencias.

### 5. Protección anti-cámara de eco (*Bootstrap Illusion*)
- **Decisión:** `KnowledgeUnit.from_direct_experience` + descuento $\gamma$ por salto + en el Escenario B, si el emisor no tiene experiencia directa, la confianza resultante no supera $\max(c_{\text{local}}, \gamma c_{\text{ext}})$ **y `last_updated_tick` no se refresca** (un rumor no valida a otro rumor).
- **Racional:** Sin la cota, dos portadores de un mismo rumor se lo rebotarían hasta $c \to 1.0$ sin evidencia física. Sin congelar τ, ese rebote los eximiría del decaimiento pasivo para siempre, y ni la persistencia social (M4) ni un rumor falso compartido (M6) podrían extinguirse nunca.

### 6. Determinismo entre procesos (hash aleatorizado de `str`)
- **Problema detectado:** Python aleatoriza el hash de `str` por proceso (`PYTHONHASHSEED`). `Pattern` contiene strings, así que el orden de iteración de un `set[Pattern]` varía entre ejecuciones, rompiendo la reproducibilidad bit a bit si alguna lógica itera sobre él.
- **Decisión:**
  - `Pattern` es `@dataclass(frozen=True, order=True)` y se usa como clave de orden canónica.
  - **Prohibido** iterar un `set` o el resultado de una operación de conjuntos sin `sorted(...)`. Los `dict` se recorren en orden de inserción, que debe ser determinista.
  - Toda selección aleatoria (`rng.choice`, `rng.permutation`) opera sobre listas previamente ordenadas.
  - Un único `np.random.Generator(np.random.PCG64(seed))` por `SimulationEngine`, compartido con el entorno que éste construye.
- **Verificación:** Un test ejecuta el mismo protocolo en dos subprocesos con `PYTHONHASHSEED` distintos y exige JSON idéntico.

### 7. Inyección de creencias falsas como rumor plantado
- **Decisión:** `inject_false_belief` crea `KnowledgeUnit(pattern, false_value, confidence, evidence_count=1, last_updated_tick=tick, from_direct_experience=False)` y la inserta con `upsert(..., force=True)`, que sobrescribe la creencia existente del patrón o expulsa la de menor utilidad si la memoria está llena.
- **Racional:** `from_direct_experience` declara que *ese agente* experimentó el recurso; marcar un rumor plantado como directo violaría la semántica del campo y desactivaría la protección anti-eco entre portadores. La variante "agente mentiroso con falsa evidencia directa" queda para el Experimento 002.

### 8. Retiro de estímulo físico en la prueba de persistencia social
- **Decisión:** `ablate_discoverers(pattern, retire_stimulus=True)` elimina a todos los agentes activos en `direct_discoverers[pattern]` e invoca `env.retire_pattern_resources(pattern)`.
- **Racional:** Mide memoria colectiva pura, sin re-descubrimiento físico.

### 9. Cobertura accesible como medida del meta-agente
- **Problema detectado:** En modo aislado, 80 agentes × 3 creencias directas cubren casi seguro los 12 patrones; la cobertura colectiva aislada tiende a `1.0`, y exigir `collective_coverage > isolated_coverage` sería imposible de cumplir aunque la hipótesis fuera cierta.
- **Decisión:** Se agrega **`accessible_coverage_mean`**: para cada agente, fracción de los $N$ patrones que conoce válidamente él o algún vecino de comunicación a 1 salto; promedio sobre agentes. En modo aislado es igual a la cobertura individual. La comparación de 001-A usa `accessible_coverage_mean` y la precisión de decisión, no la cobertura colectiva (que se sigue reportando). Por la Decisión 13, esta cobertura mide una **capacidad programada** (la consulta en vivo existe para producirla), no una propiedad emergente.
- **Racional:** Es la definición formal de conocimiento colectivo "accesible a $\le d$ saltos" con $d=1$, y mide exactamente el meta-agente de la Decisión 4.

### 10. Hipótesis científica ≠ test de software
- **Decisión:** Las expectativas empíricas sobre los mecanismos programados (superávit en 001-A, contención en 001-B) se verifican sobre las semillas `42..46` con tests marcados `@pytest.mark.empirical`. H1 exige que `collective_surplus > 0` en las 5 semillas, lo que equivale a una prueba de signo unilateral con $p = 1/32 \approx 0.031 < 0.05$. Esos tests están excluidos de la corrida por defecto (`addopts = "-m 'not empirical and not slow'"`) y ejecutados con `python -m pytest -m empirical`. Un resultado negativo **no** autoriza a ajustar parámetros para "hacer pasar" el test: se reporta como hallazgo (criterio de falsabilidad del Documento Fundacional §10).
- **Racional:** Evitar *p-hacking* y mantener la suite de software estable e independiente del resultado científico.

### 11. Protocolos con perfiles `quick` y `full`
- **Decisión:** Las funciones de protocolo tienen como valores por defecto el perfil `quick` (300 ticks, inyección en t=80, warmup 150). La CLI usa por defecto el perfil `full` (1000 ticks, inyección en t=200, warmup 500 y 200 ticks post-ablación) y acepta `--profile quick`.

### 12. Trampa de evitación: medir en 001, contratos para 004
- **Problema:** un agente que cree que un patrón es dañino nunca lo prueba, así que la experiencia directa no puede refutarlo. Hay dos variantes:
  - **Rumor falso (001-B):** tiene salida. Los vecinos que consumen el patrón emiten testimonios directos contrarios (duda social del Escenario C), los portadores del rumor no se eximen del olvido (Decisión 5) y, cuando la confianza cae bajo el umbral, el patrón vuelve a ser "desconocido" y se explora con probabilidad ε.
  - **Evidencia directa obsoleta (004):** no tiene salida. Si el mundo cambia, los agentes con experiencia directa se confirman entre sí por consenso; cada confirmación refresca τ, así que ni el olvido los libera, y la población queda bloqueada con conocimiento obsoleto.
- **Decisión:** el Experimento 001 no agrega ningún mecanismo (el mundo estático es la línea base y no debe contaminarse). Se dejan en `SimulationConfig` dos contratos para comparar en el Experimento 004 sin cambiar firmas, ambos desactivados por defecto:
  - `tau_policy: str = "validation"`. El valor alternativo `"evidence_age"` hará que τ represente la edad de la evidencia empírica más reciente: en el Escenario B, `τ = max(τ_local, τ_ext)` sin importar el origen; en el A y en la sobrescritura del C, `τ = τ_ext`. Como τ sólo puede provenir de un tick de experiencia real, el rebote de mensajes nunca lo rejuvenece, y esto subsume la regla "un rumor no valida a otro rumor". Costo esperado: el conocimiento correcto sobre lo tóxico también se olvida (≈ `(c - c_umbral)/δ` ≈ 250 ticks con los valores base) y se re-aprende consumiendo veneno.
  - `epsilon_recheck: float = 0.0`. Una probabilidad de re-verificación escéptica: ante un recurso alcanzable conocido como dañino, interactuar con probabilidad `epsilon_recheck · (1 - c)`.
- **Racional:** la tensión entre estabilidad y plasticidad es el objeto de estudio del Experimento 004; decidirla a priori sesgaría ese resultado. Mientras no se implementen, el motor rechaza los valores no nulos con `NotImplementedError`, para que ningún experimento crea estar usándolos.

### 13. Regla de atribución: emergente vs. programado
- **Problema:** el agente ya trae mucha inteligencia de diseño (confianza, descuento del rumor, refuerzo, castigo, olvido, consultas, difusión). Si una propiedad poblacional es consecuencia directa de una regla diseñada para producirla, observarla sólo demuestra que el algoritmo distribuido funciona, no que haya emergido una capacidad nueva.
- **Regla metodológica:** *toda propiedad que se afirme como emergente debe poder distinguirse de una capacidad programada explícitamente en el agente.* Las reglas se mantienen, pero cada una se declara, se puede apagar y se mide su contribución.
- **Inventario de presupuestos de diseño** (`DESIGN_RULES` en `src/ide/experiments/attribution.py`): cada regla tiene un identificador, su **propósito declarado** y la ablación que la desactiva (overrides de `SimulationConfig`; vacía si no es ablacionable):

  | ID | Regla | Propósito declarado | Ablación |
  | :--- | :--- | :--- | :--- |
  | R1 | Aprendizaje por experiencia directa | Aprender del entorno | — (núcleo) |
  | R2 | Memoria acotada con reemplazo por utilidad | Restricción experimental $C_{\max} < N$ | — (núcleo) |
  | R3 | Olvido pasivo | Eliminar lo no revalidado | `passive_conf_decay=0.0` |
  | R4 | Descuento por testimonio γ | Atenuar rumores | `gamma_social_discount=1.0` |
  | R5 | Refuerzo por consenso | Consolidar acuerdos | `eta_consensus=0.0` |
  | R6 | Anti-cámara de eco | Impedir certeza sin evidencia | `anti_echo_enabled=False` |
  | R7 | Duda ante contradicción | Filtrar testimonios falsos | `eta_doubt=0.0` |
  | R8 | Consulta en vivo | Acceder a memoria ajena (meta-agente) | `max_queries_per_tick=0` |
  | R9 | Difusión espontánea | Transmitir conocimiento | `max_broadcast_per_tick=0` |
  | R10 | Exploración ε | Descubrir lo desconocido | `epsilon_explore=0.0` |
  | R11 | Navegación hacia benéficos conocidos | Buscar alimento | `enable_navigation=False` |

- **Registro de afirmaciones** (`EXP001_CLAIMS`): cada afirmación tiene una métrica poblacional, su dirección y el conjunto $R_c$ de reglas cuyo propósito declarado la produce. Se versiona en git **antes** de ver resultados (pre-registro), junto con el perfil de corrida (`ATTRIBUTION_PROFILE = "quick"`); cambiar un $R_c$ después exige un commit que lo justifique.
- **Principio conservador, acotado:** toda afirmación sobre **disponibilidad o transmisión** de conocimiento (acceder a lo que otro sabe, decidir mejor gracias a ello, conservarlo después de que desaparezca quien lo descubrió) incluye en $R_c$ las reglas de comunicación R8 y R9. Una afirmación sobre **cómo se procesa** lo transmitido (por ejemplo, filtrar falsedades) incluye las reglas diseñadas para ese procesamiento, no el canal.
- **Variantes** (por semilla): `full`; `isolated` (`comm_enabled=False`); `purpose_ablated` (`ablate(config, R_c)`); `null_content` (control nulo, ver abajo). Además, para el **perfil de contribución**, una variante por cada regla ablacionable apagada de a una.
- **Criterios** (prueba de signo unilateral con $\alpha = 0.05$; con $n < 5$ semillas no hay potencia y el estado es `INSUFFICIENT_EVIDENCE`):
  - **E1 Localidad:** la métrica es poblacional y ningún agente la computa ni la recibe. Se garantiza por arquitectura (los agentes no acceden a métricas ni a estado global).
  - **E2 Superávit sobre el aislamiento:** `m(full)` supera a `m(isolated)`.
  - **E3 Independencia del propósito:** `m(purpose_ablated)` sigue superando a `m(isolated)`. Si $R_c$ es vacío, se cumple trivialmente.
  - **E4 Dependencia del contenido:** `m(full)` supera a `m(null_content)`.
- **Programada por construcción:** si `ablate(config, R_c)` deja a la población sin ningún canal de emisión (`comm_enabled` falso, o `max_queries_per_tick == 0` y `max_broadcast_per_tick == 0`), la variante `purpose_ablated` es idéntica a la aislada y E3 **no es una prueba sino una tautología**. En ese caso el estado es `PROGRAMMED` con `by_construction=True`, sin p-valor de E3. No se presenta como resultado empírico sino como consecuencia de la regla.
- **E5 Robustez al esquema de actualización (Decisión 15):** bajo `update_scheme="asynchronous"`, la afirmación vuelve a cumplir E2 y E3.
- **Clasificación:** `INSUFFICIENT_EVIDENCE` con menos de 5 semillas; `NOT_OBSERVED` si falla E2; `PROGRAMMED` (por construcción o porque falla E3); `ACTIVITY_ARTIFACT` si cumple E2 y E3 pero falla E4; si cumple E1–E4: `EMERGENT_PENDING_ROBUSTNESS` cuando E5 no puede evaluarse, `SCHEDULING_ARTIFACT` si falla E5 y `EMERGENT` si la cumple.
- **Control nulo de contenido** (`comm_content_null=True`): las reglas de emisión, recepción y ruteo no cambian, pero cada **entrega** (mensaje × receptor) recibe la creencia con `predicted_value` reemplazado por `+1.0` o `-1.0` al azar, conservando patrón, confianza, evidencia, τ y origen. Las extracciones salen de un generador **propio** (`PCG64(SeedSequence(seed, spawn_key=(1,)))`), así que el control no desplaza la secuencia aleatoria principal. El volumen de mensajes **no** se fija: depende de las creencias, por lo que cada variante reporta su propio `mean_messages_per_agent`.
- **Qué puede y qué no puede concluir el Experimento 001:**
  - C1, C2 y C4 (acceso, superávit de decisión y persistencia) son **programadas por construcción** bajo el protocolo N0. No es una predicción: es lo que la regla establece mientras el canal transmita creencias con semántica de fábrica.
  - C3 (inmunidad colectiva a la falsedad) es la única afirmación con una **prueba empírica genuina** de E3: ¿la contención del rumor sobrevive cuando se apagan los filtros epistémicos diseñados (R3, R4, R6, R7) y quedan sólo la transmisión y el aprendizaje directo? El resultado está abierto en ambos sentidos.
  - El **perfil de contribución** cuantifica cuánto aporta cada regla a cada afirmación, que es lo que el Documento Fundacional pide medir en el Exp 001.
  - Candidatas a emergencia genuina en este nivel son las propiedades que ninguna regla persigue, por ejemplo transiciones abruptas al variar densidad o radio, que se estudiarán en un barrido posterior.
- **Racional:** convierte una advertencia metodológica en un procedimiento verificable, y distingue explícitamente lo que se decide por definición de lo que se pone a prueba con datos.

### 14. Semántica del protocolo aislada para des-programarla después
- **Decisión:** toda la semántica de comunicación (qué se pregunta, qué se responde, qué se difunde y cómo se interpreta lo recibido) vive en `src/ide/agent/protocol.py`, en la clase `BeliefExchangeProtocol`. `MicroAgent` delega en ella `perceive_and_emit_messages` y `process_incoming_messages`. Dentro de `src/ide/agent/`, ningún otro módulo construye `Message` ni referencia `MessageType` (test sobre el AST).
- **Inyección:** `MicroAgent(agent_id, config, trust_strategy=None, protocol=None)`; con `protocol=None` se usa `BeliefExchangeProtocol()`.
- **Racional:** hoy el agente recibe de fábrica `QUERY_PATTERN`, `QUERY_RESPONSE` y `BROADCAST_BELIEF`. El programa de investigación prevé eliminar esa semántica de forma progresiva (Documento Fundacional §8) hasta preguntar si una población puede inventar su propio protocolo (Experimento 007).
- **Alcance real del aislamiento:** el nivel N1 (sin consultas) es sólo configuración (`max_queries_per_tick=0`). Desde N2, el contenido del mensaje deja de ser un `KnowledgeUnit`, así que además del protocolo cambiarán el tipo de carga útil de `Message`, su validación en `domain/types.py`, la puerta de entrada social del agente (`assimilate_testimony`) y el control nulo del motor. Lo que este cambio garantiza es que **dentro del agente** la construcción e interpretación de mensajes esté en un solo lugar, y que el ruteo del motor no dependa del contenido salvo en el control nulo.

### 15. Simultaneidad declarada y robustez al esquema de actualización
- **Esquema por defecto (`update_scheme="synchronous"`):** la percepción, la comunicación y la decisión son **simultáneas**: todos los agentes observan la misma instantánea, emiten antes de que nadie procese y deciden sin ver lo que otro hace en el mismo tick. Lo único que se ordena es la **resolución de conflictos** físicos: si dos agentes intentan consumir el mismo recurso en el mismo tick, lo obtiene el de mayor prioridad en una permutación aleatoria uniforme (`rng.permutation`), que funciona como un sorteo justo.
- **Por qué importa:** ni el reloj sincrónico ni el orden barajado son "realistas"; una comunidad real es asíncrona. En simulación basada en agentes hay patrones que aparecen con actualización sincrónica y desaparecen con la asíncrona (Huberman y Glance, 1993). Una propiedad que depende del esquema de actualización es un **artefacto del reloj**, no de la población.
- **Contrato del esquema alternativo (`update_scheme="asynchronous"`):** secuencial aleatorio. En cada tick los agentes se activan de a uno en el orden de la permutación, y cada uno completa su ciclo (observar, comunicarse con sus vecinos, decidir y actuar) viendo el mundo ya modificado por los anteriores. Se implementará junto con el barrido de densidad; hasta entonces el motor lo rechaza con `NotImplementedError`.
- **Criterio E5 (Decisión 13):** una afirmación que cumple E1–E4 debe volver a cumplir E2 y E3 bajo el esquema alternativo antes de declararse `EMERGENT`. Mientras E5 no pueda evaluarse, su estado es `EMERGENT_PENDING_ROBUSTNESS`.

### 16. Pruebas por propiedades
- **Decisión:** además de los escenarios de las specs, los invariantes se verifican con **Hypothesis**, que genera entradas al azar y reduce cualquier contraejemplo al caso mínimo. Los invariantes mínimos son:
  - **Memoria:** `len(memory) <= capacity` tras cualquier secuencia de `upsert` y `decay_step`; ninguna creencia queda con confianza menor que `min_confidence` después de `decay_step`.
  - **Epistemología:** para cualquier entrada válida, `update_from_direct_experience` y `merge_social_belief` devuelven `predicted_value` en `[-1, 1]` y `confidence` en `[0, 1]`; el intercambio repetido de rumores nunca supera `max(c_A, γ c_B)`.
  - **Grilla:** la distancia toroidal es simétrica, y mover `d` y luego `-d` vuelve a la celda original.
  - **Determinismo:** para cualquier semilla, dos motores pequeños producen historiales idénticos.
- **Reproducibilidad:** el perfil `ci` usa `derandomize=True`, así que la generación de casos también es determinista.

### 17. Herramientas de calidad
- **Decisión:** `ruff check` y `ruff format --check` (estilo y errores comunes), `pyright` en modo estricto sobre `src/` (el tipado "verificable estáticamente" de `DEFINICIONES_TECNICAS.md` deja de ser una promesa) y `python -m pytest --cov=ide` (cobertura). Las cuatro verificaciones deben pasar antes de marcar un bloque como completo.

### 18. Rendimiento por diseño, sin cambiar el modelo
- **Decisión:** desde el día 0 se hace todo lo que acelera **sin tocar la semántica**:
  - **Paralelismo entre corridas:** cada corrida es una función pura de su configuración, así que la CLI acepta `--jobs N` (por defecto 1) y reparte las corridas independientes (semillas, niveles de ablación y variantes de 001-D) en un `ProcessPoolExecutor`. Los resultados se reúnen por clave y en orden fijo; la salida es idéntica byte a byte para cualquier `N`.
  - **Línea base medida:** `python -m ide.experiments.benchmark` mide ticks por segundo en una configuración fija (la base del Exp 001, 300 ticks, 3 repeticiones) y escribe `benchmark.json` con la mediana, la versión de Python y la plataforma. El valor de referencia se registra al cerrar el bloque 8.
  - **Perfiladores instalados** (`py-spy`, `line_profiler`), sin usarlos hasta que una medición lo justifique.
- **Lo que no se hace ahora:** vectorizar o compilar el bucle de agentes. Fundiría a los agentes en matrices compartidas y dificultaría la ablación de reglas y la des-programación del protocolo. Cuando se escale (Exp 006 o el barrido de densidad), la versión rápida se validará contra esta implementación clara, exigiendo historiales idénticos; la versión clara actúa como **oráculo**.

## Especificación Estructural de Módulos y Firmas Exactas

### Mapa de archivos a crear
- `pyproject.toml` (ver Decisión 17):
  - Paquete `ide` en `src/`, `requires-python = ">=3.11"`, dependencia `numpy>=1.26`.
  - Extra `dev`: `pytest>=8.0`, `pytest-cov>=5.0`, `hypothesis>=6.100`, `ruff>=0.6`, `pyright>=1.1.380`, `py-spy>=0.3`, `line_profiler>=4.1`.
  - `[tool.pytest.ini_options]`: `pythonpath = ["src"]`, `testpaths = ["tests"]`, `markers = ["empirical: expectativas empíricas sobre los mecanismos (lentas, pueden fallar legítimamente)", "slow: corridas largas de software, como 001-D completo"]`, `addopts = "-m 'not empirical and not slow'"`.
  - `[tool.ruff]`: `target-version = "py311"`, `line-length = 100`, `src = ["src", "tests"]`; `[tool.ruff.lint] select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF"]`.
  - `[tool.pyright]`: `include = ["src"]`, `typeCheckingMode = "strict"`, `pythonVersion = "3.11"`.
- `tests/conftest.py`: registra el perfil de Hypothesis `ci` (`derandomize=True`, `deadline=None`, `max_examples=200`) y lo carga por defecto. Las pruebas por propiedades son así reproducibles entre corridas.
- `.gitignore`: `__pycache__/`, `*.egg-info/`, `.pytest_cache/`, `results/`.
- `src/ide/__init__.py`
- `src/ide/config.py`: `SimulationConfig`
- `src/ide/domain/{__init__,types,ports,extensions}.py`
- `src/ide/agent/{__init__,memory,epistemology,protocol,micro_agent}.py`
- `src/ide/environments/{__init__,grid2d}.py`
- `src/ide/simulation/{__init__,engine,controls}.py`
- `src/ide/experiments/{__init__,metrics,attribution,exp001_runner,benchmark}.py`

### 1. `src/ide/config.py`
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
    max_queries_per_tick: int = 2
    enable_specialization: bool = False
    epsilon_recheck: float = 0.0           # contrato Exp 004 (Decisión 12)
    tau_policy: str = "validation"         # contrato Exp 004: "validation" | "evidence_age"
    anti_echo_enabled: bool = True         # ablación de R6 (Decisión 13)
    enable_navigation: bool = True         # ablación de R11 (Decisión 13)
    comm_content_null: bool = False        # control nulo E4 (Decisión 13)
    update_scheme: str = "synchronous"     # Decisión 15: "synchronous" | "asynchronous" (contrato)
    enforce_memory_constraint: bool = True

    def __post_init__(self) -> None: ...
    def to_dict(self) -> dict[str, Any]: ...   # dataclasses.asdict, serializable a JSON
```
**Validaciones de `__post_init__` (todas lanzan `ValueError` con mensaje que nombra el campo):**
1. Siempre `memory_capacity >= 1`; además, si `enforce_memory_constraint`, `memory_capacity < num_world_patterns`.
2. `num_world_patterns >= 2`, `num_agents >= 1`, `resources_per_pattern >= 1`, `grid_width >= 1`, `grid_height >= 1`.
3. `perception_radius >= 0`, `comm_radius >= 0` y `2 * max(perception_radius, comm_radius) < min(grid_width, grid_height)` (evita que una misma celda se vea por dos lados del toro y que `dx` toroidal sea ambiguo).
4. En `[0.0, 1.0]`: `initial_direct_confidence`, `alpha_learning`, `beta_reinforce`, `beta_punish`, `gamma_social_discount`, `eta_consensus`, `eta_doubt`, `min_confidence`, `decision_conf_threshold`, `epsilon_explore`.
5. `lambda_decay >= 0`, `passive_conf_decay >= 0`, `max_broadcast_per_tick >= 0`, `max_queries_per_tick >= 0`.
6. `min_confidence < decision_conf_threshold`.
7. `epsilon_recheck` en `[0.0, 1.0]` y `tau_policy` en `{"validation", "evidence_age"}`.
8. `update_scheme` en `{"synchronous", "asynchronous"}`.

Variantes de configuración se construyen con `dataclasses.replace(config, ...)`.

### 2. `src/ide/domain/types.py` y `src/ide/domain/ports.py`
```python
# src/ide/domain/types.py
@dataclass(frozen=True, order=True)
class Pattern:
    attributes: tuple[tuple[str, str], ...]

    @property
    def label(self) -> str:
        # "id=p_0" ; varios atributos se unen con "&": "color=azul&forma=esfera"
        ...

@dataclass(frozen=True)
class KnowledgeUnit:
    pattern: Pattern
    predicted_value: float        # en [-1.0, 1.0]
    confidence: float             # en [0.0, 1.0]
    evidence_count: int           # >= 1
    last_updated_tick: int        # tau
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
    recommended_move: Any         # None si distance == 0
    distance: int
    is_reachable_now: bool        # True sii distance == 0

@dataclass(frozen=True)
class Observation:
    agent_id: int
    tick: int
    visible_resources: tuple[VisibleResource, ...]   # ordenados por (distance, resource_id)
    available_moves: tuple[Any, ...]                  # orden fijo definido por el entorno
    neighbor_ids: tuple[int, ...]                     # ordenados ascendentemente, sin el propio agente

class MessageType(Enum):
    QUERY_PATTERN = "QUERY_PATTERN"
    QUERY_RESPONSE = "QUERY_RESPONSE"
    BROADCAST_BELIEF = "BROADCAST_BELIEF"

@dataclass(frozen=True)
class Message:
    msg_type: MessageType
    sender_id: int
    recipient_id: int | None      # None = todos los vecinos de comunicación del emisor
    pattern: Pattern
    belief: KnowledgeUnit | None = None   # obligatorio en QUERY_RESPONSE y BROADCAST_BELIEF

class ActionType(Enum):
    MOVE = "MOVE"
    INTERACT = "INTERACT"
    IDLE = "IDLE"

@dataclass(frozen=True)
class AgentAction:
    action_type: ActionType
    target: Any = None            # movimiento si MOVE, resource_id si INTERACT

@dataclass(frozen=True)
class ActionResult:
    action_type: ActionType
    interacted_pattern: Pattern | None = None
    experienced_value: float | None = None
```

`KnowledgeUnit` **no** valida rangos en construcción (las funciones de `epistemology.py` garantizan los rangos con `clip`); `Message.__post_init__` sí valida que `belief is not None` en `QUERY_RESPONSE` y `BROADCAST_BELIEF` y que `belief.pattern == pattern`.

```python
# src/ide/domain/ports.py
@runtime_checkable
class EnvironmentPort(Protocol):
    def get_active_agent_ids(self) -> list[int]: ...                    # ascendente
    def get_observation(self, agent_id: int, tick: int) -> Observation: ...
    def get_communication_neighbors(self, agent_id: int) -> list[int]: ...  # ascendente, sin agent_id
    def execute_action(self, agent_id: int, action: AgentAction, tick: int) -> ActionResult: ...
    def remove_agents(self, agent_ids: list[int]) -> None: ...
    def retire_pattern_resources(self, pattern: Pattern) -> None: ...
    def invert_world_rules(self, fraction: float, rng: np.random.Generator) -> list[Pattern]: ...
    def step_dynamics(self, tick: int) -> None: ...
    def get_world_patterns(self) -> dict[Pattern, float]: ...            # copia, en orden de Pattern
    def get_reachable_true_values(self, agent_id: int) -> dict[int, float]: ...  # SÓLO telemetría
```

**Semántica de `execute_action`:**
- `MOVE` con `target` en `available_moves`: desplaza al agente. Con `target` inválido: se trata como `IDLE` (sin excepción).
- `INTERACT` sobre un recurso presente en la celda del agente: lo consume y devuelve `ActionResult(INTERACT, pattern, true_value)`. Si el recurso no existe o no está en su celda: `ActionResult(INTERACT, None, None)`.
- `IDLE`: `ActionResult(IDLE)`.
- Un `agent_id` inexistente lanza `KeyError` (error de programación del motor).

### 3. `src/ide/domain/extensions.py` (Experimentos 002–006)
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
    required_patterns: tuple[Pattern, ...]   # al menos 2, sin repetidos (ValueError si no)
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

### 4. `src/ide/agent/`

#### `BoundedMemory` (`memory.py`)
```python
class BoundedMemory:
    def __init__(self, capacity: int, lambda_decay: float = 0.005) -> None: ...  # capacity >= 1
    def __len__(self) -> int: ...
    def __contains__(self, pattern: Pattern) -> bool: ...
    def get(self, pattern: Pattern) -> KnowledgeUnit | None: ...
    def all_units(self) -> list[KnowledgeUnit]: ...        # ordenadas por pattern
    def compute_utility(self, unit: KnowledgeUnit, current_tick: int) -> float: ...
    def upsert(self, unit: KnowledgeUnit, current_tick: int, force: bool = False) -> bool: ...
    def remove(self, pattern: Pattern) -> bool: ...
    def decay_step(self, current_tick: int, passive_decay: float, min_confidence: float) -> list[Pattern]: ...
```
- **Utilidad:** $U(k,t) = c \cdot \max(|\hat{v}|, 0.1) \cdot e^{-\lambda \cdot \max(0,\, t - \tau)}$.
- **`upsert`:**
  1. Patrón ya presente → reemplaza la entrada, devuelve `True`.
  2. Memoria con espacio → inserta, devuelve `True`.
  3. Memoria llena → la víctima es la creencia de menor $U$; empates por menor `last_updated_tick`; persistiendo el empate, por menor `pattern`. Si `force` o $U(k_{\text{nueva}}) > U(\text{víctima})$ (estricto), reemplaza y devuelve `True`; si no, devuelve `False` sin cambios.
- **`decay_step`:** a toda creencia con `last_updated_tick < current_tick` le resta `passive_decay` a la confianza (sin tocar `last_updated_tick`); purga las que queden con `confidence < min_confidence` y devuelve los patrones purgados ordenados.

#### `epistemology.py`
1. **`update_from_direct_experience(existing, pattern, real_value, tick, config) -> KnowledgeUnit`** (siempre `from_direct_experience=True`, `last_updated_tick=tick`):
   - `existing is None` → `(pattern, clip(real_value), initial_direct_confidence, 1)`.
   - Acuerdo (`existing.predicted_value * real_value >= 0`) → `new_val = clip((1-α)·v̂ + α·v)`, `new_conf = min(1, c + β_ref·(1-c))`, `n+1`.
   - Refutación (`< 0`), con `penalized = c - β_cast`:
     - `penalized < decision_conf_threshold` → reinicia: `(pattern, clip(real_value), initial_direct_confidence, 1)`.
     - si no → `blended = (1-α)·v̂ + α·v`; `new_val = sign(v̂) · max(0.05, |blended|)` con `sign(v̂) = 1.0 if v̂ >= 0 else -1.0`; `confidence = penalized`; `n+1`.
2. **`merge_social_belief(existing, incoming, tick, config, sender_trust_factor=None) -> KnowledgeUnit`:**
   - `gamma = config.gamma_social_discount if sender_trust_factor is None else sender_trust_factor`; `e = gamma · incoming.confidence`.
   - **A** (`existing is None`) → `(incoming.pattern, incoming.predicted_value, e, 1, tick, False)`.
   - **B** (`existing.predicted_value * incoming.predicted_value >= 0`):
     - `new_val = (c·v̂ + e·v̂_ext)/(c + e)` si `c + e > 0`, si no `v̂_ext`.
     - `raw = c + η_cons · e · (1 - c)`.
     - `new_conf = min(1, raw)` si `incoming.from_direct_experience`; si no, `min(max(c, e), raw)`.
     - `new_tau = tick` si `incoming.from_direct_experience`; si no, `existing.last_updated_tick`.
     - Con `anti_echo_enabled=False` (ablación de R6), ambas salvaguardas se omiten: `new_conf = min(1, raw)` y `new_tau = tick` sin importar el origen.
     - Devuelve `(pattern, new_val, new_conf, n+1, new_tau, existing.from_direct_experience)`.
     - **Un rumor no valida a otro rumor:** el consenso sin evidencia directa del emisor no refresca τ. Si lo hiciera, dos portadores de un rumor que se lo re-difunden en cada tick quedarían exentos del decaimiento pasivo para siempre: la persistencia social (M4) nunca terminaría y un rumor falso compartido (M6) nunca se olvidaría.
   - **C** (`< 0`):
     - Sobrescritura si `not existing.from_direct_experience and e > 1.2 · c` → `(pattern, v̂_ext, max(min_confidence, e - 0.5·c), 1, tick, False)`.
     - Resistencia en otro caso → `resistance = 2.0 if existing.from_direct_experience else 1.0`; `new_conf = max(0, c - η_duda · e / resistance)`; devuelve `existing` con esa confianza **conservando su `last_updated_tick`** (la duda no es una validación, no debe refrescar la utilidad ni eximir del decaimiento).

#### `MicroAgent` (`micro_agent.py`)
```python
class MicroAgent:
    def __init__(self, agent_id: int, config: SimulationConfig,
                 trust_strategy: TrustStrategyPort | None = None,
                 protocol: BeliefExchangeProtocol | None = None) -> None: ...
    @property
    def agent_id(self) -> int: ...
    @property
    def memory(self) -> BoundedMemory: ...
    @property
    def capabilities(self) -> AgentCapabilities: ...       # constante en Exp 001
    def get_effective_belief(self, pattern: Pattern) -> KnowledgeUnit | None: ...
    def assimilate_testimony(self, belief: KnowledgeUnit, sender_id: int, tick: int) -> KnowledgeUnit: ...
    def perceive_and_emit_messages(self, obs: Observation, tick: int) -> list[Message]: ...
    def process_incoming_messages(self, messages: list[Message], tick: int) -> list[Message]: ...
    def decide_action(self, obs: Observation, tick: int, rng: np.random.Generator) -> AgentAction: ...
    def learn_from_experience(self, pattern: Pattern, real_value: float, tick: int) -> None: ...
    def decay_memory(self, tick: int) -> None: ...
```
- **Creencia "conocida"**: `get_effective_belief(p)` (memoria primero; si no está, caché efímero) no es `None` y tiene `confidence >= decision_conf_threshold`.
- **Delegación del protocolo (Decisión 14):** `perceive_and_emit_messages` vacía el caché efímero y delega en `BeliefExchangeProtocol.emit(agent, obs, tick)`; `process_incoming_messages` delega en `BeliefExchangeProtocol.receive(agent, messages, tick)`. Las reglas siguientes describen ese protocolo por defecto.
- **`assimilate_testimony`:** `merged = merge_social_belief(get_effective_belief(p), belief, tick, config, trust_strategy.compute_sender_trust(self.id, sender_id, γ))`; guarda `merged` en el caché efímero, intenta `memory.upsert(merged, tick)` y lo devuelve. Es la única puerta de entrada del conocimiento social, y no depende del formato de los mensajes.
- **Emisión (`emit`):** si `obs.neighbor_ids` está vacío devuelve `[]`. Si no:
  1. Hasta `max_queries_per_tick` `QUERY_PATTERN` (broadcast) por patrones **distintos no conocidos** entre los visibles, en orden de `(distance mínima del patrón, pattern)`.
  2. Hasta `max_broadcast_per_tick` `BROADCAST_BELIEF` con las creencias de memoria con `confidence >= decision_conf_threshold`, ordenadas por utilidad descendente y luego por `pattern`.
  3. Orden de la lista devuelta: primero las consultas, luego los broadcasts.
- **Recepción (`receive`):** recorre los mensajes en el orden recibido e ignora los propios y los dirigidos a otro destinatario.
  - `QUERY_PATTERN`: si `memory.get(p)` existe con `confidence >= decision_conf_threshold`, agrega `QUERY_RESPONSE(recipient_id=sender_id, belief=unit)` a la salida. (El caché efímero no se re-difunde: sólo responde lo que el agente sostiene en memoria.)
  - `BROADCAST_BELIEF` y `QUERY_RESPONSE`: `agent.assimilate_testimony(belief, sender_id, tick)`.
  - Devuelve sólo los `QUERY_RESPONSE` generados.
- **`decide_action`** (determinista dado `rng`; desempates por menor `resource_id`):
  1. Alcanzables (`is_reachable_now`): si hay alguno conocido benéfico (`v̂ > 0`) → `INTERACT` sobre el de mayor `v̂·c`.
  2. Si no, y hay alcanzables **no conocidos** → se extrae **un** `rng.random()`; si `< epsilon_explore` → `INTERACT` sobre el no conocido de menor `resource_id`.
  3. Si no interactúa y `enable_navigation` (R11): entre los distantes conocidos benéficos, `MOVE` hacia `recommended_move` del de menor `distance`.
  4. Si no: `MOVE` a `available_moves[rng.integers(len(available_moves))]`, o `IDLE` si no hay movimientos.
- **`learn_from_experience`:** `memory.upsert(update_from_direct_experience(memory.get(p) or caché efímero, ...), tick, force=True)`. La experiencia directa siempre se retiene (prioridad empírica).
- **`decay_memory`:** `memory.decay_step(tick, passive_conf_decay, min_confidence)`.

### 5. `ToroidalGrid2D` (`src/ide/environments/grid2d.py`)
```python
class ToroidalGrid2D:
    MOORE_MOVES: tuple[tuple[int, int], ...] = (
        (-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))
    def __init__(self, config: SimulationConfig, rng: np.random.Generator) -> None: ...
    cell_agents: dict[tuple[int, int], set[int]]
    cell_resources: dict[tuple[int, int], dict[int, Resource]]
    def get_agent_position(self, agent_id: int) -> tuple[int, int]: ...   # sólo para tests/telemetría
    # + todos los métodos de EnvironmentPort
```
- **Generación (en este orden, consumiendo `rng`):** patrones `p_0..p_{N-1}` con `+1.0` para `i < N//2` y `-1.0` para el resto; luego posiciones de los agentes `0..M-1` (`rng.integers`), luego `resources_per_pattern` recursos por patrón en orden de patrón, con `resource_id` consecutivos desde 0. Se permiten varios agentes y varios recursos por celda.
- **Distancia toroidal:** `dx = ((x2 - x1 + W//2) % W) - W//2` (ídem `dy`); `distance = max(|dx|, |dy|)`; `recommended_move = (sign(dx), sign(dy))`.
- **Percepción:** recursos con `distance <= perception_radius`; vecinos de comunicación: agentes con `distance <= comm_radius`, excluido el propio.
- **Reposición:** cada recurso consumido se encola; `step_dynamics` repone los pendientes en orden de consumo, con un `resource_id` nuevo (contador monótono) en una celda elegida por `rng`, salvo que su patrón esté retirado.
- **`retire_pattern_resources`:** elimina todas las instancias del patrón, descarta sus reposiciones pendientes y lo registra como retirado.
- **`invert_world_rules(fraction, rng)`:** `k = round(fraction · N)` patrones elegidos con `rng.choice(sorted(patrones), k, replace=False)`; invierte su signo en la tabla del mundo y en todos los recursos presentes (y por ende futuros); devuelve los patrones invertidos ordenados.

### 6. `SimulationEngine` (`src/ide/simulation/engine.py`)
```python
class SimulationEngine:
    def __init__(self, config: SimulationConfig, env: EnvironmentPort | None = None,
                 trust_strategy: TrustStrategyPort | None = None) -> None:
        if config.enable_specialization:
            raise NotImplementedError("Especialización (Exp 003) fuera de alcance del Exp 001")
        if config.epsilon_recheck > 0 or config.tau_policy != "validation":
            raise NotImplementedError("Mecanismos anti-trampa de evitación (Exp 004) fuera de alcance del Exp 001")
        if config.update_scheme != "synchronous":
            raise NotImplementedError("Esquema asíncrono (Decisión 15) previsto para el barrido de densidad")
        self.config = config
        self.rng = np.random.Generator(np.random.PCG64(config.seed))
        self.env: EnvironmentPort = env if env is not None else ToroidalGrid2D(config, self.rng)
        self.agents: dict[int, MicroAgent] = {
            aid: MicroAgent(aid, config, trust_strategy) for aid in self.env.get_active_agent_ids()
        }
        self.direct_discoverers: dict[Pattern, set[int]] = defaultdict(set)
        self.collector = MetricsCollector(config)
        self.history: list[TickMetrics] = []
        self.next_tick: int = 0

    def step(self) -> TickMetrics: ...                 # ejecuta el tick self.next_tick y lo incrementa
    def run(self, ticks: int) -> list[TickMetrics]: ...
    def inject_false_belief(self, pattern: Pattern, false_value: float,
                            confidence: float, fraction: float) -> list[int]: ...
    def ablate_population(self, fraction: float) -> list[int]: ...
    def ablate_discoverers(self, pattern: Pattern, retire_stimulus: bool = True) -> list[int]: ...
    def snapshot(self) -> KnowledgeSnapshot: ...      # estado epistémico actual, sin ejecutar ticks
```
**Pipeline de un tick `t` (5 fases):**
1. **Percepción y emisión.** `order = rng.permutation(sorted(activos))`. Para cada agente en `order`: `obs = env.get_observation(aid, t)`; `emitted += agent.perceive_and_emit_messages(obs, t)`.
2. **Intercambio social** (sólo si `comm_enabled`; si no, se descarta `emitted` y `messages_sent = 0`):
   - Ruteo: cada mensaje, en orden de emisión, se entrega a `env.get_communication_neighbors(sender)` (o sólo a `recipient_id` si es vecino).
   - Control nulo (`comm_content_null=True`, E4): cada entrega de un mensaje con `belief` (en orden de emisión y, dentro de un mensaje, de receptor ascendente, en ambas pasadas) recibe `nullify_belief(belief, self.null_rng)`. `self.null_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(config.seed, spawn_key=(1,))))` se crea siempre, pero sólo se usa en el control, así que no altera la secuencia principal. `nullify_belief` vive en `src/ide/simulation/controls.py`.
   - Primera pasada: para cada agente en `order`, `responses += agent.process_incoming_messages(inbox, t)`.
   - Segunda pasada: se rutean las respuestas y cada agente en `order` procesa su bandeja (su salida debe ser vacía).
   - `messages_sent = len(emitted) + len(responses)` (un mensaje cuenta una vez, sin importar el número de receptores).
3. **Decisión.** Para cada agente en `order`: `truth = env.get_reachable_true_values(aid)`; `action = agent.decide_action(obs, t, rng)`; si `truth` no está vacío se cuenta una oportunidad y se juzga la decisión (ver M2).
4. **Ejecución y aprendizaje.** Para cada agente en `order`: `result = env.execute_action(aid, action, t)`; si `result.experienced_value is not None`, `agent.learn_from_experience(...)` y `direct_discoverers[pattern].add(aid)`.
5. **Mantenimiento y telemetría.** `agent.decay_memory(t)` para cada agente en `order`; `env.step_dynamics(t)`; `collector.record_tick(...)` con el mapa de vecinos posterior al movimiento; se agrega a `history`.

**Perturbaciones** (aplican sobre el estado entre ticks; `tick` efectivo = `next_tick`):
- `k = round(fraction · len(activos))`; víctimas/objetivos = `sorted(rng.choice(sorted(activos), k, replace=False))`.
- `inject_false_belief`: inserta el rumor plantado (Decisión 7) en los objetivos y los devuelve.
- `ablate_population`: elimina víctimas de `self.agents` y del entorno.
- `ablate_discoverers`: víctimas = `sorted(direct_discoverers[pattern] ∩ activos)`; si `retire_stimulus`, retira el patrón del entorno.

### 7. Métricas (`src/ide/experiments/metrics.py`)
Una creencia sobre $\rho$ es **válida** si `sign(v̂) == sign(F(ρ))` y `c >= decision_conf_threshold`; es **falsa** si el signo es opuesto y `c >= decision_conf_threshold`. Sólo cuenta la `BoundedMemory`.

```python
@dataclass(frozen=True)
class TickMetrics:
    tick: int
    active_agents: int
    individual_coverage_mean: float          # M1
    collective_coverage: float               # M1
    accessible_coverage_mean: float          # M1 (1 salto)
    decision_opportunities: int              # M2
    correct_decisions: int                   # M2
    decision_accuracy: float                 # M2 (0.0 si no hubo oportunidades)
    cumulative_decision_accuracy: float      # M2
    pattern_prevalence: dict[Pattern, float]       # M3/M4
    pattern_false_prevalence: dict[Pattern, float] # M6
    false_belief_prevalence: float           # M6 (agentes con >=1 creencia falsa)
    messages_sent: int                       # M7
    messages_per_agent: float                # M7 (0.0 si no hay agentes)

class MetricsCollector:
    def __init__(self, config: SimulationConfig) -> None: ...
    def record_tick(self, tick: int, agents: dict[int, MicroAgent],
                    world_patterns: dict[Pattern, float],
                    neighbors: dict[int, list[int]],
                    decision_opportunities: int, correct_decisions: int,
                    messages_sent: int) -> TickMetrics: ...

@dataclass(frozen=True)
class KnowledgeSnapshot:                     # estado epistémico sin decisiones ni mensajes
    active_agents: int
    individual_coverage_mean: float
    collective_coverage: float
    accessible_coverage_mean: float
    pattern_prevalence: dict[Pattern, float]
    pattern_false_prevalence: dict[Pattern, float]
    false_belief_prevalence: float

def knowledge_snapshot(agents: dict[int, MicroAgent], world_patterns: dict[Pattern, float],
                       neighbors: dict[int, list[int]], config: SimulationConfig) -> KnowledgeSnapshot: ...
def judge_decision(action: AgentAction, reachable_truth: dict[int, float]) -> bool: ...
def propagation_time(history: Sequence[TickMetrics], pattern: Pattern, theta: float) -> int | None: ...
```
- **M2 `judge_decision`** (sólo se invoca si `reachable_truth` no está vacío): correcta si (a) `INTERACT` sobre un `target` con valor `> 0`, o (b) no `INTERACT` y todos los valores son `< 0`. Incorrecta en cualquier otro caso (incluye `INTERACT` sobre un `target` que no está en `reachable_truth`).
- **M3 `propagation_time`:** sea `t_0` el primer tick con `pattern_prevalence[p] > 0` y `P_max` el máximo de la serie; devuelve el menor `t - t_0` con prevalencia `>= theta · P_max`, o `None` si `P_max == 0`. (Tiempo de subida normalizado: la prevalencia absoluta de un patrón está acotada por $C_{\max}/N$ en promedio, así que un umbral absoluto podría no alcanzarse nunca.)
- Si `comm_enabled == False`, `accessible_coverage_mean == individual_coverage_mean`.
- **Cobertura accesible y canal veraz:** el mapa de vecinos que reciben `record_tick` y `knowledge_snapshot` es vacío por agente si no existe un canal de consulta veraz, es decir, si `comm_enabled` es falso, `max_queries_per_tick == 0` o `comm_content_null` es verdadero. "Accesible" significa "obtenible mediante una consulta en vivo que transmite el contenido real"; sin ese canal, la cobertura accesible es la individual.
- **`knowledge_snapshot`** es una función pura: `record_tick` la usa para los campos epistémicos de `TickMetrics`, y los protocolos la usan para medir el estado entre ticks (justo después de una ablación o inyección) sin alterar el acumulado de M2. `SimulationEngine.snapshot() -> KnowledgeSnapshot` la invoca con el mapa de vecinos actual (vacío por agente si `comm_enabled` es falso). Sin agentes activos, todos los campos valen `0.0` (y los diccionarios, `0.0` por patrón).
- **Precisión ponderada en una ventana:** `windowed_accuracy(history_slice) = Σ correct_decisions / Σ decision_opportunities` (0.0 si no hubo oportunidades). Promediar `decision_accuracy` tick a tick sesgaría el resultado con los ticks sin oportunidades.
- **Tolerancia numérica:** los valores de los escenarios de las specs se verifican con `pytest.approx(valor, abs=1e-9)`; ningún test compara floats calculados con `==`, salvo el determinismo entre corridas, que exige igualdad exacta.

### 8. Protocolos (`src/ide/experiments/exp001_runner.py`)
```python
TARGET_PATTERN = Pattern((("id", "p_0"),))
RECOVERY_WINDOW = 20

@dataclass(frozen=True)
class SurplusReport:
    collective_accuracy: float               # cumulative_decision_accuracy final, comm on
    isolated_accuracy: float                 # ídem, comm off
    collective_surplus: float                 # collective_accuracy - isolated_accuracy
    collective_accessible_coverage: float    # accessible_coverage_mean final, comm on
    isolated_accessible_coverage: float      # accessible_coverage_mean final, comm off
    collective_coverage: float
    isolated_coverage: float
    collective_individual_coverage_mean: float
    mean_messages_per_agent: float           # media de messages_per_agent sobre todos los ticks, comm on
    accuracy_gain_per_message: float | None  # collective_surplus / mean_messages_per_agent; None si es 0
    propagation_t50: dict[str, int | None]   # por pattern.label, corrida colectiva
    propagation_t90: dict[str, int | None]

@dataclass(frozen=True)
class FalsificationReport:
    target_pattern: str                      # TARGET_PATTERN.label == "id=p_0"
    injected_agents: int
    initial_injected_prevalence: float       # knowledge_snapshot() inmediatamente tras inyectar
    peak_false_prevalence: float             # máximo entre la inicial y la de cada tick posterior
    final_false_prevalence: float            # pattern_false_prevalence[p_0] del último tick
    ticks_to_extinction: int | None          # menor k >= 1 (k-ésimo tick tras inyectar) con prevalencia falsa 0
    extinguished_or_contained: bool          # final < initial

@dataclass(frozen=True)
class AblationPointResult:
    ablation_fraction: float
    remaining_agents: int
    pre_ablation_coverage: float             # collective_coverage del último tick de warmup
    immediate_post_ablation_coverage: float  # engine.snapshot() inmediatamente tras la ablación
    final_recovered_coverage: float          # collective_coverage del último tick
    retention_ratio: float                   # immediate_post / pre (0.0 si pre == 0)
    pre_ablation_accuracy: float             # windowed_accuracy de los últimos RECOVERY_WINDOW ticks de warmup
    recovery_ticks: int | None               # ver regla de recuperación abajo

@dataclass(frozen=True)
class ResilienceReport:
    ablation_results: tuple[AblationPointResult, ...]
    discoverers_ablated_count: int
    remaining_agents_after_discoverer_ablation: int
    post_discoverer_ablation_prevalence: float   # pattern_prevalence[p_0] de engine.snapshot() tras la ablación
    final_social_persistence_prevalence: float   # pattern_prevalence[p_0] del último tick
    social_persistence_ticks: int | None         # menor k >= 1 con pattern_prevalence[p_0] == 0; None si sobrevive

def run_protocol_001a_surplus(config: SimulationConfig, total_ticks: int = 300) -> SurplusReport: ...
def run_protocol_001b_falsification(config: SimulationConfig, total_ticks: int = 300,
        injection_tick: int = 80, injection_fraction: float = 0.25) -> FalsificationReport: ...
def run_protocol_001c_resilience(config: SimulationConfig, warmup_ticks: int = 150,
        post_ablation_ticks: int = 100,
        ablation_levels: tuple[float, ...] = (0.10, 0.30, 0.50, 0.70)) -> ResilienceReport: ...
def report_to_dict(report: Any) -> dict[str, Any]: ...      # Pattern -> label, tuplas -> listas
def aggregate_reports(reports: Sequence[Any]) -> dict[str, Any]: ...
def sign_test_p_value(differences: Sequence[float]) -> float: ...
def build_arg_parser() -> argparse.ArgumentParser: ...
def main(argv: list[str] | None = None) -> int: ...
```
- **001-A:** dos motores independientes con la misma `config`, uno con `comm_enabled=True` y otro con `dataclasses.replace(config, comm_enabled=False)`, `total_ticks` cada uno.
- **001-B:** corre `injection_tick` ticks, inyecta `(p_0, -1.0, 0.95, injection_fraction)`, corre `total_ticks - injection_tick` ticks más.
- **001-C:** para cada nivel, un motor nuevo con la misma `config` (por determinismo, su estado tras `warmup_ticks` es idéntico al de los demás), ablación, `post_ablation_ticks` ticks. Una corrida adicional, también nueva: `warmup_ticks` ticks, `ablate_discoverers(p_0, retire_stimulus=True)`, `post_ablation_ticks` ticks.
- **Regla de recuperación (M5):** tras la ablación, para cada `k = 1..post_ablation_ticks`, se calcula `windowed_accuracy` sobre los ticks post-ablación `max(1, k - RECOVERY_WINDOW + 1)..k` (nunca se mezclan ticks previos a la ablación). `recovery_ticks` es el menor `k` cuyo valor es `>= 0.9 · pre_ablation_accuracy`, o `None` si no ocurre.
- **Convención de offsets:** todo conteo "k ticks después" de una perturbación empieza en `k = 1` (el primer tick ejecutado tras ella).
- **`aggregate_reports`** (varias semillas del mismo protocolo): por campo escalar numérico, `{"mean", "std", "n"}` con desvío poblacional (`ddof=0`); por campo `bool`, la fracción de `True`; por campo `dict`, la misma agregación por clave; los valores `None` se excluyen y `n` cuenta los restantes. Para 001-A agrega además `surplus_sign_test_p = sign_test_p_value([r.collective_surplus ...])`.
- **`sign_test_p_value`:** prueba de signo unilateral (H1: diferencia > 0). Se descartan los ceros; con `n` restantes y `s` positivos, `p = Σ_{i=s..n} C(n, i) / 2^n` (1.0 si `n == 0`). No requiere `scipy`.
- **CLI:** `python -m ide.experiments.exp001_runner [--profile {quick,full}] [--seeds 42 43 ...] [--out results/] [--jobs N]`, con valores por defecto `full`, `42`, `results/` y `1`. `--jobs` reparte las corridas independientes en procesos (Decisión 18) sin alterar la salida. Escribe `exp001_seed{seed}.json` (config + los tres reportes vía `report_to_dict`, con claves ordenadas e `indent=2`), `exp001_aggregate.json` cuando hay más de una semilla, y `exp001a_seed{seed}_timeseries.csv`. Imprime un resumen legible en consola y devuelve 0.
- **CSV de series temporales:** una fila por `(mode, tick)` con `mode ∈ {collective, isolated}`; columnas en este orden: `mode`, los campos escalares de `TickMetrics` en orden de declaración, `prevalence[<label>]` y `false_prevalence[<label>]` por patrón en orden de `Pattern`.

### 9. Atribución de emergencia (`src/ide/experiments/attribution.py`)
```python
@dataclass(frozen=True)
class DesignRule:
    rule_id: str                               # "R8"
    name: str
    purpose: str
    ablation: tuple[tuple[str, Any], ...]      # overrides de SimulationConfig; () si no es ablacionable

@dataclass(frozen=True)
class EmergenceClaim:
    claim_id: str                              # "C1"
    description: str
    protocol: str                              # "001a" | "001b" | "001c"
    metric: str
    higher_is_better: bool
    purpose_rules: tuple[str, ...]             # R_c

class ClaimStatus(Enum):
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_OBSERVED = "NOT_OBSERVED"
    PROGRAMMED = "PROGRAMMED"
    ACTIVITY_ARTIFACT = "ACTIVITY_ARTIFACT"
    EMERGENT_PENDING_ROBUSTNESS = "EMERGENT_PENDING_ROBUSTNESS"
    SCHEDULING_ARTIFACT = "SCHEDULING_ARTIFACT"
    EMERGENT = "EMERGENT"

@dataclass(frozen=True)
class ClaimEvaluation:
    claim_id: str
    status: ClaimStatus
    by_construction: bool                      # E3 tautológico (Decisión 13)
    seeds: tuple[int, ...]
    values: dict[str, tuple[float, ...]]       # variante -> valor por semilla
    p_vs_isolated: float                       # E2
    p_purpose_ablated_vs_isolated: float | None  # E3 (None si R_c es vacío o by_construction)
    p_vs_null_content: float                   # E4
    e5_evaluated: bool                         # False mientras el esquema asíncrono no exista
    rule_effects: dict[str, float]             # regla -> media de d(full, sin esa regla)

@dataclass(frozen=True)
class AttributionReport:
    profile: str
    rules: tuple[DesignRule, ...]
    evaluations: tuple[ClaimEvaluation, ...]

ATTRIBUTION_PROFILE = "quick"                  # parte del pre-registro
DESIGN_RULES: tuple[DesignRule, ...]           # R1..R11 de la Decisión 13
EXP001_CLAIMS: tuple[EmergenceClaim, ...]
def ablate(config: SimulationConfig, rule_ids: Sequence[str]) -> SimulationConfig: ...
def disables_communication(config: SimulationConfig) -> bool: ...
def measure_claim(claim: EmergenceClaim, config: SimulationConfig, profile: str) -> float: ...
def classify(claim: EmergenceClaim, values: dict[str, Sequence[float]], by_construction: bool,
             alpha: float = 0.05) -> ClaimEvaluation: ...
def run_protocol_001d_attribution(config: SimulationConfig, seeds: Sequence[int],
        claims: Sequence[EmergenceClaim] = EXP001_CLAIMS, jobs: int = 1) -> AttributionReport: ...

# src/ide/simulation/controls.py
def nullify_belief(belief: KnowledgeUnit, rng: np.random.Generator) -> KnowledgeUnit: ...
```
- **`EXP001_CLAIMS`** (pre-registro):

  | ID | Afirmación | Protocolo / métrica | Dirección | $R_c$ |
  | :--- | :--- | :--- | :---: | :--- |
  | C1 | Acceso a conocimiento no poseído | 001a / `accessible_coverage_mean` final | ↑ | R8, R9 |
  | C2 | Superávit de decisión colectiva | 001a / `cumulative_decision_accuracy` final | ↑ | R8, R9 |
  | C3 | Inmunidad colectiva a la falsedad | 001b / `final_false_prevalence` | ↓ | R3, R4, R6, R7 |
  | C4 | Persistencia extra-individual | 001c / `final_social_persistence_prevalence` | ↑ | R8, R9 |

- **`ablate`:** aplica con `dataclasses.replace` la unión de los overrides de las reglas indicadas; lanza `ValueError` si alguna no existe o no es ablacionable.
- **`disables_communication`:** verdadero si `comm_enabled` es falso, o si `max_queries_per_tick == 0` y `max_broadcast_per_tick == 0`.
- **`nullify_belief`:** devuelve la creencia con `predicted_value = +1.0` si `rng.random() < 0.5`, si no `-1.0`, y el resto de los campos intactos. Fijar la magnitud evita filtrar información (una creencia atenuada por refutación tiene magnitud menor).
- **`measure_claim`:** para `001a` corre un único motor con `config` durante los ticks del perfil y lee la métrica del último `TickMetrics`; para `001b` y `001c` corre el protocolo con los parámetros del perfil (`001c` sólo con el nivel `0.5`) y lee el campo del reporte.
- **Variantes por semilla:** `full` (config de la semilla), `isolated` (`comm_enabled=False`), `purpose_ablated` (`ablate(config, R_c)`; se omite si $R_c$ es vacío o si `disables_communication(ablate(config, R_c))`), `null_content` (`comm_content_null=True`) y `without:<Rk>` para cada regla ablacionable (perfil de contribución). Todas usan `ATTRIBUTION_PROFILE`.
- **`classify`:** con `d(a, b)_s = m_a,s - m_b,s` si `higher_is_better`, o `m_b,s - m_a,s` si no: E2 = `sign_test_p_value(d(full, isolated)) < α`; E3 = `sign_test_p_value(d(purpose_ablated, isolated)) < α` (verdadero si $R_c$ es vacío; no se evalúa si `by_construction`); E4 = `sign_test_p_value(d(full, null_content)) < α`. Con menos de 5 semillas devuelve `INSUFFICIENT_EVIDENCE`; si no, aplica la clasificación de la Decisión 13 en ese orden. E5 se evalúa sólo si `values` contiene las variantes `async:full` y `async:isolated` (y `async:purpose_ablated` cuando corresponde a E3), medidas con `update_scheme="asynchronous"`. En el Exp 001 no existen (`e5_evaluated=False`), así que el mejor estado alcanzable es `EMERGENT_PENDING_ROBUSTNESS`. `rule_effects[Rk]` es la media sobre semillas de `d(full, without:Rk)`.
- **Costo:** con 5 semillas, 4 afirmaciones y hasta 13 variantes, 001-D ejecuta unas 260 corridas del perfil `quick`. Es un análisis lento y no forma parte de la suite por defecto.
- **CLI:** `--attribution` ejecuta 001-D (definido en `attribution.py`) siempre con `ATTRIBUTION_PROFILE`, sin importar `--profile`, y agrega `exp001_attribution.json` con el `AttributionReport` más una tabla en consola (afirmación, estado, si es por construcción y p-valores). Con menos de 5 semillas avisa que el resultado será `INSUFFICIENT_EVIDENCE`.

## Risks / Trade-offs

- **[Thrashing de memoria por broadcasts]** → `upsert` exige utilidad estrictamente mayor; caché efímero para decidir en el tick; sólo se difunden creencias con $c \ge c_{\text{umbral}}$.
- **[Cámara de eco]** → regla anti-eco del Escenario B (Decisión 5).
- **[Trampa de evitación]** → un agente que cree (falsamente) que un patrón benéfico es dañino nunca lo prueba, así que la experiencia directa no puede refutarlo. La variante por rumor se corrige por duda social, olvido y exploración, y se **mide** en 001-B; la variante por evidencia obsoleta queda para el Experimento 004 con los contratos de la Decisión 12.
- **[Descubridores masivos en 001-C]** → `p_0` es benéfico y muy consumido, así que `direct_discoverers[p_0]` puede abarcar a gran parte de la población. Por eso el reporte incluye `discoverers_ablated_count` y `remaining_agents_after_discoverer_ablation`; si quedan 0 agentes, las prevalencias se reportan como `0.0`.
- **[Colisión sobre el mismo recurso]** → gana el primero en `order`; los demás reciben `ActionResult(INTERACT, None, None)`. M2 juzga la intención, no el éxito físico.
- **[División por cero en M2/M7]** → se reporta `0.0`.
- **[Hash aleatorizado de `str`]** → Decisión 6.

## Checklist de Criterios de Aceptación (Definition of Done)

- [ ] **Aislamiento de capas:** ningún archivo en `src/ide/agent/` importa `environments`, `grid2d` ni `simulation` (test sobre el AST).
- [ ] **Protocolo aislado:** dentro de `src/ide/agent/`, sólo `protocol.py` construye `Message` o referencia `MessageType` (test sobre el AST).
- [ ] **Atribución pre-registrada:** `DESIGN_RULES` y `EXP001_CLAIMS` versionados antes de la primera corrida de 001-D, y `--attribution` ejecutado con las semillas 42..46, con su tabla de estados registrada tal cual.
- [ ] **Cero fuga de información:** `VisibleResource` no tiene `true_value`; `get_reachable_true_values` sólo es invocado por `SimulationEngine`.
- [ ] **Invariante de memoria:** para todo agente y todo tick, `len(agent.memory) <= config.memory_capacity`.
- [ ] **Anti-cámara de eco:** el intercambio repetido de rumores indirectos nunca supera $\max(c_A, \gamma c_B)$.
- [ ] **Persistencia social válida:** `ablate_discoverers(..., retire_stimulus=True)` elimina descubridores y recursos físicos.
- [ ] **Determinismo intra-proceso:** dos motores con la misma `seed` producen historiales, posiciones y memorias idénticas.
- [ ] **Determinismo inter-proceso:** la CLI con `--profile quick` genera JSON idéntico bajo `PYTHONHASHSEED=0` y `PYTHONHASHSEED=1`.
- [ ] **Suite de software verde:** `python -m pytest --cov=ide` (sin los marcadores `empirical` ni `slow`), `ruff check`, `ruff format --check` y `pyright`.
- [ ] **Paralelismo inocuo:** la CLI produce archivos idénticos con `--jobs 1` y `--jobs 4`.
- [ ] **Línea base de rendimiento registrada:** `benchmark.json` generado al cerrar el bloque 8.
- [ ] **Hipótesis ejecutadas y reportadas:** `python -m pytest -m empirical` corrido sobre las semillas 42..46 y su resultado (positivo o negativo) registrado.

## Setup, Ejecución y Validación Local

```bash
pip install -e ".[dev]"                                   # instalar
ruff check && ruff format --check && pyright              # calidad estática
python -m pytest -v --cov=ide                                       # suite de software
python -m pytest -m empirical -v                                   # hipótesis científicas (lento)
python -m ide.experiments.exp001_runner --profile quick   # corrida rápida
python -m ide.experiments.exp001_runner --seeds 42 43 44 45 46 --out results/ --jobs 4
python -m ide.experiments.benchmark                       # línea base de rendimiento
python -m ide.experiments.exp001_runner --seeds 42 43 44 45 46 --attribution   # 001-D, perfil pre-registrado
```
