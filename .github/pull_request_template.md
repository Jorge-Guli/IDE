## Resumen

<!-- Qué cambia y por qué, en dos o tres líneas. Si implementa bloques de tasks.md, indica cuáles. -->

### Bloques de `tasks.md`

<!-- Ejemplo: "Bloque 7: grilla 2D toroidal (7.1 y 7.2)". Borra esta sección si no aplica. -->

## Cambios de diseño

<!--
Todo cambio de diseño se refleja primero en los artefactos OpenSpec (specs y design.md)
y en los documentos raíz, y después en el código. Lista cada cambio y dónde quedó
documentado. Escribe "Ninguno" si no hay.
-->

- [ ] Si hubo un cambio grande de especificación, un agente independiente hizo la revisión cruzada

## Decisiones pendientes o aceptadas

<!-- Contradicciones resueltas, hallazgos descartados con su motivo, riesgos declarados. -->

## Verificación

- [ ] Ciclo TDD por bloque: tests escritos desde los escenarios de la spec y vistos fallar (RED), implementación mínima (GREEN) y limpieza con la suite en verde (REFACTOR)
- [ ] `ruff check` y `ruff format --check` sin errores
- [ ] `pyright` (estricto) sin errores
- [ ] `python -m pytest --cov=ide` en verde
- [ ] `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict` sin advertencias, si cambiaron specs
- [ ] Los invariantes nuevos o modificados se verifican también con pruebas por propiedades (Hypothesis, perfil `ci` con `derandomize=True`)
- [ ] `/code-review` corrido sobre el cambio, con sus hallazgos aplicados o descartados con motivo

<details>
<summary>Salida de las verificaciones</summary>

<!-- Pega aquí la salida final de cada verificación marcada arriba: ruff check, ruff format --check, pyright, pytest con la cobertura total y, si cambiaron specs, openspec validate. -->

```text

```

</details>

## Arquitectura y determinismo

- [ ] `src/ide/agent/` no importa `ide.environments`, `ide.simulation` ni `ide.experiments`; sólo `protocol.py` construye `Message` o referencia `MessageType`; el conocimiento social entra únicamente por `MicroAgent.assimilate_testimony`
- [ ] El agente no ve `Resource.true_value` ni coordenadas; las entidades de dominio son `@dataclass(frozen=True)`
- [ ] Ningún `set` (ni resultado de operaciones de conjuntos) se itera sin `sorted(...)`, y toda selección aleatoria opera sobre listas ordenadas
- [ ] Un único `np.random.Generator(np.random.PCG64(seed))` por motor, compartido con el entorno; los únicos generadores adicionales son los derivados declarados en CLAUDE.md (`SeedSequence(seed, spawn_key=(k,))`); sin efectos de orden fuera de los conflictos físicos; salida idéntica para cualquier `--jobs`

## Reglas metodológicas

- [ ] Nada se presenta como emergente si una regla diseñada lo persigue; si quitar las reglas de una afirmación deja a la población sin comunicación, se declara *programada por construcción*
- [ ] No se ajustaron parámetros para que una hipótesis "pase"; los resultados negativos se reportan tal cual
- [ ] Toda regla nueva del agente está en `DESIGN_RULES`, con propósito declarado y ablación, y en `DEFINICIONES_FORMALES.md` §3.1
- [ ] El pre-registro (`DESIGN_RULES`, `EXP001_CLAIMS`, `ATTRIBUTION_PROFILE` y, en la Fase II, `PHASE2_DESIGN_RULES`, `EXP002_CLAIMS`, `EXP003_CLAIMS` y su perfil) se versionó antes de mirar resultados; si cambió después, un commit lo justifica
