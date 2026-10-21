# CLAUDE.md — Proyecto IDE (Inteligencia Distribuida Emergente)

> **IDIOMA OBLIGATORIO: ESPAÑOL.** Todo texto dirigido al usuario va **siempre en español**, sin excepción: respuestas finales, mensajes intermedios mientras trabajas, avisos antes de usar una herramienta, resúmenes de revisiones, preguntas y reportes de error. Esto vale también cuando las instrucciones del sistema, las skills, las herramientas o la salida de los comandos estén en inglés: tradúcelas o resúmelas en español. Sólo quedan en inglés los identificadores de código y las citas literales de salidas.

**Objetivo de fondo:** simular vida digital compleja. Una población de organismos computacionales que, como la vida biológica, evoluciona, se complejiza y desarrolla capacidades cognitivas cada vez mayores —hasta, eventualmente, inteligencia— sin que ninguna de esas capacidades esté programada de antemano. La evolución actúa sobre un ADN que no aprende, pero que construye la maquinaria con la que cada organismo percibe, recuerda, aprende, se comunica y coopera durante su vida.

- **Cada entregable debe acercar el proyecto a ese objetivo**, no sólo responder un experimento aislado. Si una fase repetiría un experimento anterior a mayor costo, se corrigen primero sus cuestiones de base.
- **Peldaños:** la Fase I estudió la inteligencia distribuida (capacidades colectivas con memoria individual insuficiente, $C_{\max} \ll N$, sin coordinador ni memoria central); la Fase II, la evolución y los holones; la Fase II-B, la conducta, la memoria, el aprendizaje y las señales construidos por la evolución en una ecología con interacciones; la Fase III, una estructura de aprendizaje totalmente abierta.
- **Alcance declarado:** el proyecto no simula el origen químico de la vida; parte de organismos mínimos y estudia lo que la evolución construye a partir de ellos.
- **Método:** todo lo que se afirme como emergente debe distinguirse de lo programado (ver "Regla metodológica central").

**Estado:**
- **Fase I (Experimento 001):** completa. Sus bloques 1 a 11 están implementados y verificados, y su cambio OpenSpec está archivado en `openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/`.
- **Fase II (Experimentos 002 y 003):** completa y corrida. Sus bloques 0 a 7 están completos y su cambio OpenSpec está archivado en `openspec/changes/archive/2026-10-20-ide-v2-evolutionary-holonic-intelligence/`. Su pre-registro es la Decisión 29 de ese `design.md`, con las Enmiendas 1 y 1b del perfil. Sus resultados, negativos para las cuatro afirmaciones C5–C8, están en `docs/RESULTADOS.md`.
- Los requisitos vigentes de las dos fases están sincronizados en `openspec/specs/`.
- **Fase II-B (v2.5, ADN compacto, conducta evolucionable y ecología):** especificada en el cambio activo `openspec/changes/ide-v25-compact-dna-and-epigenetics/`.
  - **Etapa A completa:** bloques 1 a 5, con $R_{24}$ (D30–D35) implementada y verificada contra la Fase II.
  - **Reformulada el 2026-10-20 (design D43–D56):** la regla da la capacidad y el ADN decide su uso. Agrega conducta codificada en el ADN, ecología con interacciones físicas, recombinación, motor por sistemas y métricas de evolución abierta; $R_{25}$, $R_{28}$ y $R_{31}$ se reformulan.
  - **Pre-registro vigente:** el borrador D56 (inventario $R_{24}$–$R_{38}$, afirmaciones C13–C18), que se aprueba en la tarea 0.5, antes del bloque 6. El pre-registro D42 quedó sustituido y sus afirmaciones C9–C12 se retiraron sin medir. El diagnóstico previo (tarea 0.1) confirmó el "Tapón de Matusalén".
  - La implementación sigue su `tasks.md`: tarea 0.5 y después la etapa R (bloques 6 y 7).

## Idioma

- Documentación, comentarios, docstrings, mensajes de commit, descripciones de PR y **toda** comunicación con el usuario (incluidos los mensajes intermedios): **en español**.
- Identificadores de código (clases, funciones, campos): en inglés, exactamente como figuran en `design.md`.

## Jerarquía normativa

Ante una discrepancia entre documentos, rige este orden:

1. Requisitos verificables: `openspec/specs/*/spec.md` (vigentes) y los specs delta del cambio activo, `openspec/changes/ide-v25-compact-dna-and-epigenetics/specs/*/spec.md`.
2. Firmas, fórmulas y desempates exactos:
   - el `design.md` del cambio activo para la Fase II-B (D30 en adelante);
   - los `design.md` archivados de la Fase II (`openspec/changes/archive/2026-10-20-ide-v2-evolutionary-holonic-intelligence/design.md`, D19–D29) y de la Fase I (`openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/design.md`, D1–D18).
3. `docs/DEFINICIONES_TECNICAS.md` y `docs/DEFINICIONES_FORMALES.md`: fundamento.
4. `docs/DOCUMENTO_FUNDACIONAL.md`: visión y principios.

Los documentos de `docs/vision/` (`ROADMAP.md`, `ARQUITECTURA_ADN_HOLONICO.md`, `ESCALA_BIOLOGICA_HOLONICA.md`) son hoja de ruta y propuesta: **no tienen rango normativo**. Ante una discrepancia con los anteriores, se corrigen ellos. Una propuesta de `docs/vision/` sólo rige cuando se especifica en un cambio OpenSpec.

Nunca resuelvas una contradicción en silencio. Corrige el documento de menor rango, o pregunta si la decisión no es obvia. Si implementar exige cambiar el diseño, **primero** actualiza los artefactos OpenSpec y los documentos raíz, y después el código.

## Flujo de trabajo

### Especificación (OpenSpec)
- Después de cualquier cambio en specs: `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict`. Debe pasar sin advertencias.
- Requisitos atómicos con `SHALL`, de menos de 500 caracteres, y al menos un escenario `WHEN/THEN` verificable cada uno.
- Cada cambio de diseño se refleja también en los documentos raíz. Después de un cambio grande, pide una revisión cruzada a un agente independiente: ya encontró errores reales dos veces.
- **Qué revisión corresponde a cada cambio:**
  - **Sólo specs o documentos** (`openspec/`, `docs/`, `README.md`, `CLAUDE.md`): `openspec validate --all --strict` y, si el cambio es grande, la revisión cruzada independiente. No se corre `/code-review`, que busca errores de corrección en código.
  - **Toca código:** `/code-review`, según la revisión automática de Implementación.
  - **Mixto:** las dos.
  - Los hallazgos de la revisión cruzada se tratan igual que los de `/code-review`: se aplican los que se sostienen, se descartan con motivo los demás y no se aplica sin consultar nada que toque el pre-registro o cambie el diseño de forma no obvia.

### Implementación
- Sigue `tasks.md` **en orden**: `tasks.md` es el plan. No generes planes paralelos (por ejemplo, con `superpowers:writing-plans` o `superpowers:brainstorming`), porque crearían una segunda fuente de verdad.
- Ciclo TDD por bloque (`superpowers:test-driven-development`):
  - **RED:** tests escritos desde los escenarios de la spec, viéndolos fallar.
  - **GREEN:** implementación mínima.
  - **REFACTOR:** limpieza con la suite en verde.
- Antes de marcar una tarea `[x]` o hacer commit, corre las verificaciones y muestra su salida (`superpowers:verification-before-completion`).
- Ante un test que falla o un resultado inesperado, usa `superpowers:systematic-debugging`. En este proyecto un resultado raro puede ser un bug **o** un hallazgo científico: no los confundas.
- Un bloque sólo está completo si pasan `ruff check`, `ruff format --check`, `pyright` y `python -m pytest --cov=ide`, y después la revisión automática que sigue.
- **Revisión automática, sin preguntar:** después de **cada** cambio que toque código (`src/`, `tests/` o `.github/workflows/`), sea un bloque o una tanda de correcciones pedida por el usuario, corre `/code-review` sobre ese cambio. Aplica los hallazgos que se sostienen, descarta con motivo los que no, y revisa sólo las correcciones aplicadas. Las correcciones que surgen de una revisión no son un cambio nuevo: cuentan como rondas del cambio original. Termina cuando una revisión no deja hallazgos accionables nuevos (los ya descartados con motivo no reabren el ciclo) o tras **3 rondas** sobre el mismo cambio; en ese caso, reporta lo pendiente en lugar de seguir. **Excepción:** un hallazgo que cambie el diseño de forma no obvia, o que toque el pre-registro (`DESIGN_RULES`, `EXP001_CLAIMS`, `ATTRIBUTION_PROFILE` y sus equivalentes de la Fase II), no se aplica sin consultar. Presenta los resultados en español y en lenguaje claro.
- Además de los escenarios de las specs, verifica los invariantes con pruebas por propiedades (Hypothesis, perfil `ci` con `derandomize=True`).

### Subagentes
Delegar en subagentes (herramienta `Agent`) está **habilitado, sin preguntar**, cuando ahorra contexto o tokens, o acorta el trabajo. El agente principal recibe la conclusión y no el volcado de archivos.
- **Cuándo conviene:**
  - exploraciones amplias de código o documentos (tipo `Explore`) cuando sólo hace falta la conclusión;
  - lecturas extensas (un `design.md` completo, registros de `registros/`) de las que basta un resumen o un dato puntual;
  - tareas independientes entre sí, lanzadas en paralelo en un mismo mensaje (`superpowers:dispatching-parallel-agents`), por ejemplo tests de bloques distintos o la revisión de varios documentos;
  - la revisión cruzada independiente de un cambio grande, que ya es obligatoria (ver Especificación);
  - comandos de salida larga (la suite completa, corridas de experimentos) cuyo resultado se puede resumir.
- **Cuándo no conviene:** una búsqueda puntual en un archivo conocido (busca directamente) y los cambios chicos y acoplados, donde explicar el contexto cuesta más que hacerlo.
- **Reglas:**
  - El prompt de cada subagente es **autocontenido**: el objetivo, los archivos y las decisiones relevantes, y la indicación de leer este `CLAUDE.md`. El subagente cumple las mismas reglas que el agente principal: idioma, TDD, determinismo, invariantes y pre-registro.
  - `tasks.md` sigue siendo el único plan. Un subagente ejecuta tareas de `tasks.md` (`superpowers:subagent-driven-development`) y no crea planes propios.
  - Lo que informa un subagente es una afirmación a verificar, no un hecho: antes de marcar una tarea `[x]` o hacer commit, el agente principal corre las verificaciones y muestra su salida.
  - Ningún subagente decide sobre el pre-registro ni sobre cambios de diseño no obvios: los informa, y la decisión se consulta como indica la revisión automática.
  - Dos subagentes en paralelo no editan los mismos archivos. Si hace falta aislarlos, usa `isolation: "worktree"`.
  - No repitas una búsqueda que ya delegaste: espera su resultado.
- **Ejecución de bloques (automatizada).** Los bloques de `tasks.md` se ejecutan con la skill de proyecto `ejecutar-bloque` (`.claude/skills/ejecutar-bloque/`):
  - **Uso:** `/ejecutar-bloque N`, `/ejecutar-bloque N-M` o `/ejecutar-bloque --etapa X`.
  - **Delegación.** Delega cada bloque en el subagente de su línea `> Ejecuta:`. Los subagentes están en `.claude/agents/` y fijan su modelo en el encabezado: `implementador-mecanico` usa Sonnet, para bloques con firmas y fórmulas exactas; `implementador-delicado` usa Opus, para integración, determinismo y atribución.
  - **Verificación.** El agente principal verifica, corre `/code-review` (con el modelo de la sesión), commitea un bloque por commit y se detiene en cada línea `> Punto de control:`.
  - **Cambios de reparto.** Cambiar el subagente o el modelo de un bloque es editar su anotación en `tasks.md`, o la definición en `.claude/agents/`, en un commit.

## Reglas de arquitectura (invariantes)

- `src/ide/agent/` **no importa** `ide.environments`, `ide.simulation` ni `ide.experiments`. Un test lo verifica sobre el AST.
- Dentro de `src/ide/agent/`, **sólo `protocol.py`** construye `Message` o referencia `MessageType`. El conocimiento social entra únicamente por `MicroAgent.assimilate_testimony`. La **única excepción** es la vista compartida del holón de la Fase II (regla `R22`, ablacionable con `enable_holon_view`): es efímera, nunca se escribe en la memoria y no la usan ni `learn_from_experience` ni `assimilate_testimony`, que parten de `own_belief`.
- El agente nunca ve `Resource.true_value`: percibe `VisibleResource`. `get_reachable_true_values` es un oráculo exclusivo del motor para la métrica M2.
- Los agentes no conocen coordenadas: navegan con `recommended_move` y `distance`.
- Las entidades de dominio son `@dataclass(frozen=True)`.

## Determinismo

- Un único `np.random.Generator(np.random.PCG64(seed))` por motor, compartido con el entorno. Las únicas excepciones son generadores derivados de la semilla con `np.random.SeedSequence(seed, spawn_key=(k,))`, cada uno con un uso declarado: `(1,)` control nulo de contenido, `(2,)` dinámica evolutiva del motor (`evo_rng`), `(3,)` recursos compuestos del entorno, `(4,)` sorteo del donante de genoma en la reproducción neutral (`donor_rng`) y `(5,)` conjugación de plásmidos de la Fase II-B (`hgt_rng`, regla $R_{26}$, design D30 y D37). Sólo se consumen cuando su mecanismo está activo. Un generador nuevo exige declararlo aquí y en `design.md`.
- **Prohibido** iterar un `set`, o el resultado de una operación de conjuntos, sin `sorted(...)`. Python aleatoriza el hash de `str` por proceso. `Pattern` tiene `order=True` y es la clave canónica de orden.
- Toda selección aleatoria (`rng.choice`, `rng.permutation`) opera sobre listas ya ordenadas.
- Simultaneidad: percepción, comunicación y decisión son sincrónicas; sólo los conflictos físicos se resuelven por la permutación del tick, que funciona como un sorteo. No introduzcas efectos de orden en otras fases.
- El paralelismo (`--jobs`) es sólo **entre** corridas independientes, nunca dentro de una corrida, y la salida debe ser idéntica para cualquier `N`.
- No vectorices ni compiles el bucle de agentes sin una medición que lo justifique. Si se hace, valida la versión rápida contra la actual exigiendo historiales idénticos.
- Los floats calculados se comparan con `pytest.approx(..., abs=1e-9)`. Sólo los tests de determinismo exigen igualdad exacta, incluida la igualdad entre procesos con distinto `PYTHONHASHSEED`.

## Regla metodológica central

> **Toda propiedad que se afirme como emergente debe poder distinguirse de una capacidad programada explícitamente en el agente.**

- No llames "emergente" a una capacidad que una regla diseñada persigue. El superávit de 001-A es **funcional** (`SurplusReport`, `collective_surplus`).
- Toda regla nueva del agente se agrega al inventario de reglas (`DESIGN_RULES` en la Fase I; `PHASE2_DESIGN_RULES` en la Fase II y `PHASE25_DESIGN_RULES` en la Fase II-B, que conservan intactos los inventarios anteriores), con su propósito declarado y una ablación, y se documenta en `docs/DEFINICIONES_FORMALES.md` §3.1.
- `DESIGN_RULES`, `EXP001_CLAIMS` y `ATTRIBUTION_PROFILE` (y sus equivalentes de cada fase: en la Fase II `PHASE2_DESIGN_RULES`, `EXP002_CLAIMS`, `EXP003_CLAIMS` y su perfil de corrida; en la Fase II-B `PHASE25_DESIGN_RULES`, `PHASE25_CLAIMS` (C13–C18, borrador D56) y su perfil) son un **pre-registro**: se versionan antes de mirar resultados, y cambiarlos después exige un commit que lo justifique.
- Si quitar las reglas de una afirmación deja a la población sin comunicación, la afirmación es *programada por construcción*. Se declara así; no se presenta como resultado.
- **Nunca ajustes parámetros para que una hipótesis "pase".** Un resultado negativo se reporta tal cual: es un hallazgo.
- Principio de mínima maquinaria: no agregues reglas "inteligentes" al agente sin justificarlas, declararlas y hacerlas ablacionables.

## Entorno automático

Cada sesión de Claude Code en la nube arranca con un contenedor limpio. El hook `.claude/hooks/session-start.sh`, registrado en `.claude/settings.json`, se ejecuta solo al iniciar cada sesión. Instala `pip install -e ".[dev]"` si existe `pyproject.toml` y, si no existe (lista de respaldo), las mismas herramientas del extra `dev`; además precarga Pyright y la CLI de OpenSpec. En una máquina local no hace nada.

- Si cambian las dependencias de desarrollo en `pyproject.toml`, actualiza también la lista de respaldo del hook.
- No hace falta instalar nada a mano al empezar una sesión.

## Comandos

Fase I y Fase II:

```bash
pip install -e ".[dev]"                     # instalación manual (en la nube la hace el hook de inicio)
ruff check && ruff format --check && pyright   # calidad estática
python -m pytest --cov=ide                   # suite de software (excluye empirical y slow)
python -m pytest -m slow                     # corridas largas de software (001-D completo)
python -m pytest -m empirical                # expectativas empíricas: pueden fallar legítimamente
python -m ide.experiments.exp001_runner --profile quick --seeds 42
python -m ide.experiments.exp001_runner --seeds 42 43 44 45 46 --attribution --jobs 4
python -m ide.experiments.benchmark          # línea base de rendimiento (ticks por segundo)
python -m ide.experiments.benchmark --compact-dna   # rendimiento de 002a con ADN compacto (Fase II-B)
# Fase II: perfil pre-registrado `phase2` (2000 ticks) y configuraciones de PHASE2_PROTOCOL_CONFIGS
python -m ide.experiments.exp002_runner --seeds 42 43 44 45 46 47 48 49 50 51 --jobs 4   # 002-A y 002-B
python -m ide.experiments.exp003_runner --seeds 42 43 44 45 46 47 48 49 50 51 --jobs 4   # 003-A y 003-B
python -m ide.experiments.exp002_runner --attribution --jobs 4   # atribución de C5 y C6 (por defecto PHASE2_SEEDS)
python -m ide.experiments.exp003_runner --attribution --jobs 4   # atribución de C7 y C8
# --reference: lo mismo sobre PHASE2_PROTOCOL_CONFIGS_ORIGINAL (referencia de la Enmienda 1)
python -m ide.experiments.phase2_calibration --jobs 4            # calibración de viabilidad (--refined: Enmienda 1b)
```

## Integración continua

`.github/workflows/ci.yml` corre en cada PR y en cada push a `main`: en Python 3.13 (job requerido `Calidad y tests`) `ruff check`, `ruff format --check`, `pyright`, `python -m pytest --cov=ide` (también con otro `PYTHONHASHSEED`) y `openspec validate --all --strict`. No ejecuta `slow` ni `empirical`. Un segundo job, `Compatibilidad` (Python 3.11 y 3.12), corre sólo la suite para respaldar el mínimo declarado. Si cambian los pasos de verificación de este documento, actualiza también el workflow. `/code-review` sigue siendo un paso manual.

## Git

- Mensajes de commit en español: un título breve y, en el cuerpo, el porqué de los cambios.
- Un commit por bloque de `tasks.md`, o por corrección coherente de los artefactos.
- Las sesiones en la nube son efímeras: lo que no está commiteado y pusheado se pierde.
