---
name: ejecutar-bloque
description: Ejecuta uno o más bloques del tasks.md del cambio OpenSpec activo con el ciclo completo del proyecto: delega la implementación en el subagente anotado en el bloque ("Ejecuta:"), verifica desde el agente principal, corre /code-review, marca las tareas, commitea y pushea un commit por bloque, y se detiene en los puntos de control. Úsala cuando el usuario pida implementar un bloque o una etapa (por ejemplo "/ejecutar-bloque 3" o "/ejecutar-bloque --etapa A").
---

# Ejecutar bloques de `tasks.md`

Esta skill es un **procedimiento**, no un plan: el plan es el `tasks.md` del cambio OpenSpec activo, que figura en el estado de `CLAUDE.md`. Todo lo que dice qué hacer, con qué subagente y dónde detenerse sale de ese archivo.

## Argumentos
- **`N`:** ejecuta sólo el bloque `N`.
- **`N-M`:** ejecuta los bloques de `N` a `M`, en orden.
- **`--etapa X`:** ejecuta los bloques de la etapa `X`, según la tabla de etapas del encabezado de `tasks.md`.
- **Sin argumento:** ejecuta el primer bloque con tareas pendientes `[ ]`.

En todos los casos, la ejecución se detiene en el primer punto de control que aparezca (paso 7).

## Antes de empezar
1. Lee `CLAUDE.md` y el `tasks.md` del cambio activo.
2. Comprueba que el bloque anterior al primero pedido esté completo (todas sus tareas `[x]`). Si no lo está, detenete e informalo: los bloques se ejecutan **en orden**.
3. Comprueba que el árbol de trabajo esté limpio (`git status`). Si hay cambios ajenos, detenete y consulta.

## Ciclo por bloque
1. **Leer el bloque.** Toma sus tareas, la línea `> Ejecuta: <subagente>` y, si la tiene, la línea `> Punto de control: ...`.
2. **Delegar.** Si la línea `> Ejecuta:` dice "agente principal", no delegues: haz el bloque vos mismo, siguiendo sus indicaciones. Por ejemplo, las corridas largas las corre el responsable del proyecto en su equipo, y vos registrás e interpretás. Si no, invoca la herramienta `Agent` con `subagent_type` igual al subagente anotado (`implementador-mecanico` o `implementador-delicado`). El modelo lo fija la definición del subagente en `.claude/agents/`. El prompt es autocontenido y lleva:
   - el número de bloque y la ruta del cambio activo;
   - las decisiones o aclaraciones que el usuario haya tomado en la conversación y afecten al bloque;
   - la indicación de que no commitee.
   - Lánzalo en primer plano (`run_in_background: false`), porque el resto del ciclo depende de su resultado.
3. **Revisar el informe.** Si el subagente informó ambigüedades o contradicciones del diseño, **no sigas**. Las triviales se resuelven corrigiendo primero el `design.md` y los specs, como pide `CLAUDE.md`. Las que tocan el pre-registro o cambian el diseño de forma no obvia se consultan al usuario.
4. **Verificar desde el agente principal.** Lo que informa el subagente es una afirmación a verificar (`superpowers:verification-before-completion`). Corre y muestra la salida de:
   - `ruff check`, `ruff format --check` y `pyright`;
   - `python -m pytest --cov=ide`, con cobertura de al menos 90 %;
   - lo que pida el bloque en su `[REFACTOR]`: por ejemplo `tests/test_performance_equivalence.py`, el benchmark, `python -m pytest -m slow` u `openspec validate --all --strict` si el bloque tocó specs.
   - Si algo falla, devuélvelo al mismo subagente (`SendMessage`) con la salida del error, o corrígelo si es trivial. Después, vuelve a verificar.
5. **Revisar el código.** Corre `/code-review` sobre el diff del bloque y aplica las reglas de `CLAUDE.md`:
   - aplica los hallazgos que se sostienen y descarta los demás con motivo;
   - revisa sólo las correcciones aplicadas;
   - corta tras 3 rondas;
   - lo que toque el pre-registro o cambie el diseño de forma no obvia se consulta.
   - Después de aplicar correcciones, repite el paso 4.
6. **Cerrar el bloque.**
   - Marca `[x]` las tareas del bloque en `tasks.md`, con una nota breve de la evidencia si corresponde.
   - Haz **un commit por bloque**, en español: un título breve y el porqué en el cuerpo, con las líneas de atribución del sistema.
   - Haz push a la rama de trabajo.
7. **Punto de control.** Si el bloque tiene la línea `> Punto de control: ...`, **detenete** aunque queden bloques pedidos. Muéstrale al usuario lo que esa línea pide revisar, con su evidencia, y espera su respuesta antes de seguir.

## Al terminar
Informa al usuario, en español y en lenguaje claro:
- los bloques cerrados, con su commit;
- la salida resumida de las verificaciones;
- los hallazgos de la revisión, aplicados y descartados con su motivo;
- lo que quedó pendiente o espera una decisión suya.
