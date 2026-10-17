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

## Decisiones pendientes o aceptadas

<!-- Contradicciones resueltas, hallazgos descartados con su motivo, riesgos declarados. -->

## Verificación

- [ ] `ruff check` y `ruff format --check` sin errores
- [ ] `pyright` (estricto) sin errores
- [ ] `python -m pytest --cov=ide` en verde (indica cantidad de tests y cobertura)
- [ ] `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict` sin advertencias, si cambiaron specs
- [ ] `/code-review` corrido sobre el cambio, con sus hallazgos aplicados o descartados con motivo
- [ ] Invariantes verificados también con pruebas por propiedades (Hypothesis), si se agregó lógica nueva

## Reglas metodológicas

- [ ] No se ajustaron parámetros para que una hipótesis "pase"; los resultados negativos se reportan tal cual
- [ ] Toda regla nueva del agente está en `DESIGN_RULES`, con propósito declarado y ablación, y en `DEFINICIONES_FORMALES.md` §3.1
- [ ] El pre-registro (`DESIGN_RULES`, `EXP001_CLAIMS`, `ATTRIBUTION_PROFILE`) no cambió, o el cambio está justificado en un commit propio
