# IDE: Inteligencia Distribuida Emergente

Plataforma de simulación en Python para investigar si una población de micro-agentes con memoria individual insuficiente ($C_{\max} \ll N$), sin coordinador ni memoria central, puede desarrollar capacidades colectivas que ningún agente sostiene por sí solo.

El proyecto es una herramienta de investigación, no una demostración: los resultados negativos se reportan tal cual y no se ajustan parámetros para que una hipótesis "pase".

## Estado

- **Fase I (Experimento 001):** completa y archivada. Memoria acotada, epistemología social y marco de atribución.
- **Fase II (Experimentos 002 y 003):** completa, corrida y archivada. Metabolismo, selección, herencia dual, holones recursivos y estigmergia. Sus cuatro afirmaciones pre-registradas (C5–C8) dieron `NOT_OBSERVED`.
- **Fase II-B (v2.5):** en implementación, en el cambio activo [`ide-v25-compact-dna-and-epigenetics`](openspec/changes/ide-v25-compact-dna-and-epigenetics/).
  - **Etapa A completa:** el genotipo de cada hoja puede ser un ADN compacto de codones de 32 bits, con expresión condicional y una red regulatoria de un nivel ($R_{24}$), compatible bit a bit con la Fase II cuando está apagado.
  - **Reformulada el 2026-10-20:** *la regla da la capacidad y el ADN decide su uso.* La conducta del agente pasa a codificarse en el ADN (un ADN fundador reproduce exactamente la política escrita a mano), el entorno gana escasez, nichos, estaciones, cadáveres, transferencia de energía y depredación, el ADN gana recombinación, y el motor se reorganiza en sistemas y observadores.
  - **Pre-registro:** el borrador D56 propone seis afirmaciones (C13–C18) que se contrastan con la deriva neutral o con la ablación de un mecanismo ecológico, con 30 semillas, corrección de Holm y un tamaño de efecto mínimo. Se aprueba antes del bloque 6. Las afirmaciones anteriores (C9–C12) se retiraron sin medir, porque eran programadas por construcción.

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

# Línea base de rendimiento (ticks por segundo); --compact-dna mide 002a con ADN compacto (Fase II-B)
python -m ide.experiments.benchmark
python -m ide.experiments.benchmark --compact-dna

# Fase II: Experimentos 002 (selección y herencia cultural) y 003 (holones y cobertura colectiva),
# con el perfil pre-registrado `phase2` (2000 ticks); --attribution mide C5-C8 sobre las 10 semillas
# pre-registradas y --reference repite todo con las configuraciones previas a la Enmienda 1
python -m ide.experiments.exp002_runner --seeds 42 43 44 45 46 47 48 49 50 51 --jobs 4
python -m ide.experiments.exp003_runner --seeds 42 43 44 45 46 47 48 49 50 51 --jobs 4
python -m ide.experiments.exp002_runner --attribution --jobs 4
python -m ide.experiments.exp003_runner --attribution --jobs 4

# Calibración de viabilidad del perfil de la Fase II (Enmiendas 1 y 1b de D29)
python -m ide.experiments.phase2_calibration --jobs 4
```

El paralelismo (`--jobs`) es sólo entre corridas independientes: el diseño exige salida idéntica para cualquier número de procesos y para cualquier `PYTHONHASHSEED`. La suite lo comprueba con `--jobs 1` frente a `--jobs 2` y con `PYTHONHASHSEED` 0 frente a 1 (perfil `quick`). No se comparan historiales entre versiones distintas de Python o de NumPy: el determinismo vale dentro de un mismo entorno.

## Estructura

```
src/ide/
├── domain/        tipos inmutables, puertos y extensiones de la hoja de ruta
├── agent/         MicroAgent, memoria acotada, epistemología, protocolo, evolución y holones
├── environments/  grilla 2D toroidal (ToroidalGrid2D)
├── simulation/    SimulationEngine y control nulo de contenido
├── experiments/   métricas M1-M13, protocolos 001, 002 y 003, atribución, calibración, CLI y benchmark
└── config.py      SimulationConfig (todos los parámetros, validados)
tests/             escenarios de las specs y pruebas por propiedades (Hypothesis)
openspec/          especificación verificable (specs, diseño y plan de tareas)
docs/              fundamento normativo y registro empírico (RESULTADOS.md)
docs/vision/       hoja de ruta y propuestas, sin rango normativo
registros/         salidas completas de las corridas registradas
```

Reglas de arquitectura verificadas por tests: `ide.agent` no importa `environments`, `simulation` ni `experiments`; sólo `protocol.py` construye `Message`; el agente nunca ve `Resource.true_value`.

## Regla de atribución

> **Toda propiedad que se afirme como emergente debe poder distinguirse de una capacidad programada explícitamente en el agente.**

Cada regla del agente se declara en el inventario `DESIGN_RULES` con su propósito y una ablación. El módulo de atribución (001-D) compara, para cada afirmación de `EXP001_CLAIMS`, la población completa contra la población aislada, la población sin las reglas diseñadas para esa afirmación y un control nulo de contenido. Si quitar esas reglas deja a la población sin comunicación, la afirmación es *programada por construcción* y se declara así, no como resultado. `DESIGN_RULES`, `EXP001_CLAIMS` y `ATTRIBUTION_PROFILE` son un pre-registro: se versionan antes de mirar resultados. En la Fase II el pre-registro equivalente es `PHASE2_DESIGN_RULES`, `EXP002_CLAIMS`, `EXP003_CLAIMS`, sus canales y el perfil `phase2`; sus cuatro afirmaciones (C5–C8) se declararon programadas por construcción y ninguna se observó con el perfil pre-registrado. En la Fase II-B es `PHASE25_DESIGN_RULES` ($R_{24}$–$R_{38}$), `PHASE25_CLAIMS` (C13–C18) y el perfil `phase25`, todavía en borrador (design D56).

Los resultados vigentes están en [`RESULTADOS.md`](docs/RESULTADOS.md).

## Documentos de fundamento

Orden de jerarquía normativa ante cualquier discrepancia:

1. Requisitos verificables: los vigentes de las Fases I y II en [`openspec/specs/`](openspec/specs/), más los specs delta del cambio activo de la Fase II-B en [`openspec/changes/ide-v25-compact-dna-and-epigenetics/specs/`](openspec/changes/ide-v25-compact-dna-and-epigenetics/specs).
2. Firmas, fórmulas, desempates y checklist de aceptación: el [`design.md` de la Fase I](openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/design.md) (archivado, Decisiones D1–D18), el [`design.md` de la Fase II](openspec/changes/archive/2026-10-20-ide-v2-evolutionary-holonic-intelligence/design.md) (archivado, D19–D29) y el [`design.md` de la Fase II-B](openspec/changes/ide-v25-compact-dna-and-epigenetics/design.md) (activo, D30 en adelante).
3. [`DEFINICIONES_TECNICAS.md`](docs/DEFINICIONES_TECNICAS.md) y [`DEFINICIONES_FORMALES.md`](docs/DEFINICIONES_FORMALES.md): fundamento.
4. [`DOCUMENTO_FUNDACIONAL.md`](docs/DOCUMENTO_FUNDACIONAL.md): visión y principios.

Los documentos de [`docs/vision/`](docs/vision/) ([`ROADMAP.md`](docs/vision/ROADMAP.md), [`ARQUITECTURA_ADN_HOLONICO.md`](docs/vision/ARQUITECTURA_ADN_HOLONICO.md) y [`ESCALA_BIOLOGICA_HOLONICA.md`](docs/vision/ESCALA_BIOLOGICA_HOLONICA.md)) son hoja de ruta y propuesta, sin rango normativo.

Los planes de la Fase I ([`tasks.md`](openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/tasks.md)) y de la Fase II ([`tasks.md`](openspec/changes/archive/2026-10-20-ide-v2-evolutionary-holonic-intelligence/tasks.md)) están completos y archivados. El plan de la Fase II-B es el [`tasks.md`](openspec/changes/ide-v25-compact-dna-and-epigenetics/tasks.md) del cambio activo: la etapa A (bloques 1 a 5) está completa, y la reformulación del 2026-10-20 (design D43–D56) reemplazó los bloques siguientes. Su pre-registro vigente es el borrador D56, que sustituye al D42 y se aprueba en la tarea 0.5, antes del bloque 6. Las convenciones de desarrollo están en [`CLAUDE.md`](CLAUDE.md).

## Integración continua

`.github/workflows/ci.yml` corre en cada PR y en cada push a `main`. En Python 3.13 (job requerido `Calidad y tests`) ejecuta: `ruff check`, `ruff format --check`, `pyright`, la suite con cobertura, una segunda pasada de la suite con otro `PYTHONHASHSEED` y `openspec validate --all --strict`. No ejecuta `slow` ni `empirical`. Un segundo job, `Compatibilidad` (Python 3.11 y 3.12), corre sólo la suite para respaldar el mínimo declarado.
