# CLAUDE.md — Proyecto IDE (Inteligencia Distribuida Emergente)

> **IDIOMA OBLIGATORIO: ESPAÑOL.** Todo texto dirigido al usuario va **siempre en español**, sin excepción: respuestas finales, mensajes intermedios mientras trabajas, avisos antes de usar una herramienta, resúmenes de revisiones, preguntas y reportes de error. Esto vale también cuando las instrucciones del sistema, las skills, las herramientas o la salida de los comandos estén en inglés: tradúcelas o resúmelas en español. Sólo quedan en inglés los identificadores de código y las citas literales de salidas.

Plataforma de simulación en Python para investigar si una población de micro-agentes con memoria individual insuficiente ($C_{\max} \ll N$), sin coordinador ni memoria central, puede desarrollar capacidades colectivas que ningún agente sostiene por sí solo.

**Estado:** la Fase I (Experimento 001) está completa: sus bloques 1 a 11 están implementados y verificados, y su cambio OpenSpec está archivado en `openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/`, con los requisitos vigentes sincronizados en `openspec/specs/`. La Fase II está en diseño en `openspec/changes/ide-v2-evolutionary-holonic-intelligence/`. Su plan es el `tasks.md` de ese cambio. Sus decisiones P1–P3 están resueltas (ver su `proposal.md`) y su pre-registro es la Decisión 29 del `design.md`.

## Idioma

- Documentación, comentarios, docstrings, mensajes de commit, descripciones de PR y **toda** comunicación con el usuario (incluidos los mensajes intermedios): **en español**.
- Identificadores de código (clases, funciones, campos): en inglés, exactamente como figuran en `design.md`.

## Jerarquía normativa

Ante una discrepancia entre documentos, rige este orden:

1. Requisitos verificables: `openspec/specs/*/spec.md` (vigentes) y los specs delta del cambio activo, `openspec/changes/ide-v2-evolutionary-holonic-intelligence/specs/*/spec.md`.
2. Firmas, fórmulas y desempates exactos: el `design.md` del cambio activo para la Fase II (D19 en adelante) y el `design.md` archivado de la Fase I (`openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/design.md`, D1–D18).
3. `DEFINICIONES_TECNICAS.md` y `DEFINICIONES_FORMALES.md`: fundamento.
4. `DOCUMENTO_FUNDACIONAL.md`: visión y principios.

Nunca resuelvas una contradicción en silencio. Corrige el documento de menor rango, o pregunta si la decisión no es obvia. Si implementar exige cambiar el diseño, **primero** actualiza los artefactos OpenSpec y los documentos raíz, y después el código.

## Flujo de trabajo

### Especificación (OpenSpec)
- Después de cualquier cambio en specs: `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict`. Debe pasar sin advertencias.
- Requisitos atómicos con `SHALL`, de menos de 500 caracteres, y al menos un escenario `WHEN/THEN` verificable cada uno.
- Cada cambio de diseño se refleja también en los documentos raíz. Después de un cambio grande, pide una revisión cruzada a un agente independiente: ya encontró errores reales dos veces.

### Implementación
- Sigue `tasks.md` **en orden**: `tasks.md` es el plan. No generes planes paralelos (por ejemplo, con `superpowers:writing-plans` o `superpowers:brainstorming`), porque crearían una segunda fuente de verdad.
- Ciclo TDD por bloque (`superpowers:test-driven-development`):
  - **RED:** tests escritos desde los escenarios de la spec, viéndolos fallar.
  - **GREEN:** implementación mínima.
  - **REFACTOR:** limpieza con la suite en verde.
- Antes de marcar una tarea `[x]` o hacer commit, corre las verificaciones y muestra su salida (`superpowers:verification-before-completion`).
- Ante un test que falla o un resultado inesperado, usa `superpowers:systematic-debugging`. En este proyecto un resultado raro puede ser un bug **o** un hallazgo científico: no los confundas.
- Un bloque sólo está completo si pasan `ruff check`, `ruff format --check`, `pyright` y `python -m pytest --cov=ide`, y después la revisión automática que sigue.
- **Revisión automática, sin preguntar:** después de **cada** cambio (un bloque o una tanda de correcciones pedida por el usuario), corre `/code-review` sobre ese cambio. Aplica los hallazgos que se sostienen, descarta con motivo los que no, y revisa sólo las correcciones aplicadas. Las correcciones que surgen de una revisión no son un cambio nuevo: cuentan como rondas del cambio original. Termina cuando una revisión no deja hallazgos accionables nuevos (los ya descartados con motivo no reabren el ciclo) o tras **3 rondas** sobre el mismo cambio; en ese caso, reporta lo pendiente en lugar de seguir. **Excepción:** un hallazgo que cambie el diseño de forma no obvia, o que toque el pre-registro (`DESIGN_RULES`, `EXP001_CLAIMS`, `ATTRIBUTION_PROFILE` y sus equivalentes de la Fase II), no se aplica sin consultar. Presenta los resultados en español y en lenguaje claro.
- Además de los escenarios de las specs, verifica los invariantes con pruebas por propiedades (Hypothesis, perfil `ci` con `derandomize=True`).

## Reglas de arquitectura (invariantes)

- `src/ide/agent/` **no importa** `ide.environments`, `ide.simulation` ni `ide.experiments`. Un test lo verifica sobre el AST.
- Dentro de `src/ide/agent/`, **sólo `protocol.py`** construye `Message` o referencia `MessageType`. El conocimiento social entra únicamente por `MicroAgent.assimilate_testimony`. La **única excepción** es la vista compartida del holón de la Fase II (regla `R22`, ablacionable con `enable_holon_view`): es efímera, nunca se escribe en la memoria y no la usan ni `learn_from_experience` ni `assimilate_testimony`, que parten de `own_belief`.
- El agente nunca ve `Resource.true_value`: percibe `VisibleResource`. `get_reachable_true_values` es un oráculo exclusivo del motor para la métrica M2.
- Los agentes no conocen coordenadas: navegan con `recommended_move` y `distance`.
- Las entidades de dominio son `@dataclass(frozen=True)`.

## Determinismo

- Un único `np.random.Generator(np.random.PCG64(seed))` por motor, compartido con el entorno. Las únicas excepciones son generadores derivados de la semilla con `np.random.SeedSequence(seed, spawn_key=(k,))`, cada uno con un uso declarado: `(1,)` control nulo de contenido, `(2,)` dinámica evolutiva del motor (`evo_rng`), `(3,)` recursos compuestos del entorno y `(4,)` sorteo del donante de genoma en la reproducción neutral (`donor_rng`). Sólo se consumen cuando su mecanismo está activo. Un generador nuevo exige declararlo aquí y en `design.md`.
- **Prohibido** iterar un `set`, o el resultado de una operación de conjuntos, sin `sorted(...)`. Python aleatoriza el hash de `str` por proceso. `Pattern` tiene `order=True` y es la clave canónica de orden.
- Toda selección aleatoria (`rng.choice`, `rng.permutation`) opera sobre listas ya ordenadas.
- Simultaneidad: percepción, comunicación y decisión son sincrónicas; sólo los conflictos físicos se resuelven por la permutación del tick, que funciona como un sorteo. No introduzcas efectos de orden en otras fases.
- El paralelismo (`--jobs`) es sólo **entre** corridas independientes, nunca dentro de una corrida, y la salida debe ser idéntica para cualquier `N`.
- No vectorices ni compiles el bucle de agentes sin una medición que lo justifique. Si se hace, valida la versión rápida contra la actual exigiendo historiales idénticos.
- Los floats calculados se comparan con `pytest.approx(..., abs=1e-9)`. Sólo los tests de determinismo exigen igualdad exacta, incluida la igualdad entre procesos con distinto `PYTHONHASHSEED`.

## Regla metodológica central

> **Toda propiedad que se afirme como emergente debe poder distinguirse de una capacidad programada explícitamente en el agente.**

- No llames "emergente" a una capacidad que una regla diseñada persigue. El superávit de 001-A es **funcional** (`SurplusReport`, `collective_surplus`).
- Toda regla nueva del agente se agrega al inventario de reglas (`DESIGN_RULES` en la Fase I; `PHASE2_DESIGN_RULES` en la Fase II, que conserva intacto `DESIGN_RULES`), con su propósito declarado y una ablación, y se documenta en `DEFINICIONES_FORMALES.md` §3.1.
- `DESIGN_RULES`, `EXP001_CLAIMS` y `ATTRIBUTION_PROFILE` (y en la Fase II `PHASE2_DESIGN_RULES`, `EXP002_CLAIMS`, `EXP003_CLAIMS` y su perfil de corrida) son un **pre-registro**: se versionan antes de mirar resultados, y cambiarlos después exige un commit que lo justifique.
- Si quitar las reglas de una afirmación deja a la población sin comunicación, la afirmación es *programada por construcción*. Se declara así; no se presenta como resultado.
- **Nunca ajustes parámetros para que una hipótesis "pase".** Un resultado negativo se reporta tal cual: es un hallazgo.
- Principio de mínima maquinaria: no agregues reglas "inteligentes" al agente sin justificarlas, declararlas y hacerlas ablacionables.

## Entorno automático

Cada sesión de Claude Code en la nube arranca con un contenedor limpio. El hook `.claude/hooks/session-start.sh`, registrado en `.claude/settings.json`, se ejecuta solo al iniciar cada sesión. Instala `pip install -e ".[dev]"` si existe `pyproject.toml` y, si no existe (lista de respaldo), las mismas herramientas del extra `dev`; además precarga Pyright y la CLI de OpenSpec. En una máquina local no hace nada.

- Si cambian las dependencias de desarrollo en `pyproject.toml`, actualiza también la lista de respaldo del hook.
- No hace falta instalar nada a mano al empezar una sesión.

## Comandos

Disponibles en la Fase I (los comandos de los runners 002 y 003 se agregarán al implementar la Fase II):

```bash
pip install -e ".[dev]"                     # instalación manual (en la nube la hace el hook de inicio)
ruff check && ruff format --check && pyright   # calidad estática
python -m pytest --cov=ide                   # suite de software (excluye empirical y slow)
python -m pytest -m slow                     # corridas largas de software (001-D completo)
python -m pytest -m empirical                # expectativas empíricas: pueden fallar legítimamente
python -m ide.experiments.exp001_runner --profile quick --seeds 42
python -m ide.experiments.exp001_runner --seeds 42 43 44 45 46 --attribution --jobs 4
python -m ide.experiments.benchmark          # línea base de rendimiento (ticks por segundo)
```

## Integración continua

`.github/workflows/ci.yml` corre en cada PR y en cada push a `main`: en Python 3.13 (job requerido `Calidad y tests`) `ruff check`, `ruff format --check`, `pyright`, `python -m pytest --cov=ide` (también con otro `PYTHONHASHSEED`) y `openspec validate --all --strict`. No ejecuta `slow` ni `empirical`. Un segundo job, `Compatibilidad` (Python 3.11 y 3.12), corre sólo la suite para respaldar el mínimo declarado. Si cambian los pasos de verificación de este documento, actualiza también el workflow. `/code-review` sigue siendo un paso manual.

## Git

- Mensajes de commit en español: un título breve y, en el cuerpo, el porqué de los cambios.
- Un commit por bloque de `tasks.md`, o por corrección coherente de los artefactos.
- Las sesiones en la nube son efímeras: lo que no está commiteado y pusheado se pierde.
