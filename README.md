# IDE: Inteligencia Distribuida Emergente

Plataforma de simulación en Python para investigar si una población de micro-agentes con memoria individual insuficiente ($C_{\max} \ll N$), sin coordinador ni memoria central, puede desarrollar capacidades colectivas que ningún agente sostiene por sí solo.

El proyecto es una herramienta de investigación, no una demostración: los resultados negativos se reportan tal cual y no se ajustan parámetros para que una hipótesis "pase".

## Instalación

Requiere Python 3.11 o superior.

```bash
pip install -e ".[dev]"
```

## Ejecución

```bash
# Calidad estática y suite de software (excluye los marcadores empirical y slow)
ruff check && ruff format --check && pyright
python -m pytest --cov=ide
OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict   # specs

# Corridas largas de software (001-D completo) y expectativas empíricas
python -m pytest -m slow
python -m pytest -m empirical          # pueden fallar legítimamente

# Experimento 001 (protocolos 001-A, 001-B y 001-C)
python -m ide.experiments.exp001_runner --profile quick --seeds 42
python -m ide.experiments.exp001_runner --seeds 42 43 44 45 46 --out results/ --jobs 4

# Atribución de emergencia (001-D): fuerza el perfil pre-registrado (`quick`);
# siempre usa `quick`, ignora `--profile` e imprime una nota, para no romper el pre-registro
python -m ide.experiments.exp001_runner --seeds 42 43 44 45 46 --attribution --jobs 4

# Línea base de rendimiento (ticks por segundo)
python -m ide.experiments.benchmark
```

El paralelismo (`--jobs`) es sólo entre corridas independientes: el diseño exige salida idéntica para cualquier número de procesos y para cualquier `PYTHONHASHSEED`. La suite lo comprueba con `--jobs 1` frente a `--jobs 2` y con `PYTHONHASHSEED` 0 frente a 1 (perfil `quick`). No se comparan historiales entre versiones distintas de Python o de NumPy: el determinismo vale dentro de un mismo entorno.

## Estructura

```
src/ide/
├── domain/        tipos inmutables, puertos y extensiones de la hoja de ruta
├── agent/         MicroAgent, memoria acotada, epistemología y protocolo de mensajes
├── environments/  grilla 2D toroidal (ToroidalGrid2D)
├── simulation/    SimulationEngine y control nulo de contenido
├── experiments/   métricas, protocolos 001-A/B/C, atribución 001-D, CLI y benchmark
└── config.py      SimulationConfig (todos los parámetros, validados)
tests/             escenarios de las specs y pruebas por propiedades (Hypothesis)
openspec/          especificación verificable (specs, diseño y plan de tareas)
RESULTADOS.md      registro de resultados empíricos, positivos o negativos
```

Reglas de arquitectura verificadas por tests: `ide.agent` no importa `environments`, `simulation` ni `experiments`; sólo `protocol.py` construye `Message`; el agente nunca ve `Resource.true_value`.

## Regla de atribución

> **Toda propiedad que se afirme como emergente debe poder distinguirse de una capacidad programada explícitamente en el agente.**

Cada regla del agente se declara en el inventario `DESIGN_RULES` con su propósito y una ablación. El módulo de atribución (001-D) compara, para cada afirmación de `EXP001_CLAIMS`, la población completa contra la población aislada, la población sin las reglas diseñadas para esa afirmación y un control nulo de contenido. Si quitar esas reglas deja a la población sin comunicación, la afirmación es *programada por construcción* y se declara así, no como resultado. `DESIGN_RULES`, `EXP001_CLAIMS` y `ATTRIBUTION_PROFILE` son un pre-registro: se versionan antes de mirar resultados.

Los resultados vigentes están en [`RESULTADOS.md`](RESULTADOS.md).

## Documentos de fundamento

Orden de jerarquía normativa ante cualquier discrepancia:

1. Requisitos verificables: los vigentes de la Fase I en [`openspec/specs/`](openspec/specs/), más los specs delta del cambio en curso de la Fase II en [`openspec/changes/ide-v2-evolutionary-holonic-intelligence/specs/`](openspec/changes/ide-v2-evolutionary-holonic-intelligence/specs).
2. Firmas, fórmulas, desempates y checklist de aceptación: el [`design.md` de la Fase I](openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/design.md) (archivado, Decisiones D1–D18) y el [`design.md` de la Fase II](openspec/changes/ide-v2-evolutionary-holonic-intelligence/design.md) (D19–D29).
3. [`DEFINICIONES_TECNICAS.md`](DEFINICIONES_TECNICAS.md) y [`DEFINICIONES_FORMALES.md`](DEFINICIONES_FORMALES.md): fundamento.
4. [`DOCUMENTO_FUNDACIONAL.md`](DOCUMENTO_FUNDACIONAL.md): visión y principios.

El plan de la Fase I está completo ([`tasks.md` archivado](openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/tasks.md)). El plan de la Fase II es [`tasks.md`](openspec/changes/ide-v2-evolutionary-holonic-intelligence/tasks.md); tiene decisiones abiertas que bloquean parte de su implementación (ver su `proposal.md`). Las convenciones de desarrollo están en [`CLAUDE.md`](CLAUDE.md).

## Integración continua

`.github/workflows/ci.yml` corre en cada PR y en cada push a `main`. En Python 3.13 (job requerido `Calidad y tests`) ejecuta: `ruff check`, `ruff format --check`, `pyright`, la suite con cobertura, una segunda pasada de la suite con otro `PYTHONHASHSEED` y `openspec validate --all --strict`. No ejecuta `slow` ni `empirical`. Un segundo job, `Compatibilidad` (Python 3.11 y 3.12), corre sólo la suite para respaldar el mínimo declarado.
