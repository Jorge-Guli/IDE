# Quality Tooling Specification

## Purpose
Verificar de forma automática y objetiva la calidad del código: estilo y errores comunes, tipado estático estricto, invariantes por pruebas basadas en propiedades, cobertura y una línea base de rendimiento medida desde el primer motor, sin alterar la semántica del modelo.

## Requirements

### Requirement: Calidad Estática
El proyecto SHALL configurar en `pyproject.toml` Ruff (lint y formato) y Pyright en modo estricto sobre `src/`, y SHALL pasar `ruff check`, `ruff format --check` y `pyright` sin errores antes de marcar un bloque de `tasks.md` como completo.

#### Scenario: Error de tipos detectado antes de los tests
- **WHEN** una función de `src/ide/` devuelve un valor cuyo tipo no coincide con su anotación
- **THEN** `pyright` termina con código distinto de 0 y nombra el archivo y la línea.

### Requirement: Pruebas por Propiedades Reproducibles
La suite SHALL verificar con Hypothesis los invariantes de memoria, epistemología, grilla y determinismo de `design.md`, usando un perfil `ci` con `derandomize=True` registrado en `tests/conftest.py`, de modo que dos corridas de la suite generen los mismos casos.

#### Scenario: Invariante de capacidad
- **WHEN** Hypothesis genera secuencias arbitrarias de `upsert` y `decay_step` sobre `BoundedMemory(capacity=c)` con `c` entre 1 y 5
- **THEN** en ningún paso `len(memory)` supera `c`.

#### Scenario: Rangos epistémicos
- **WHEN** Hypothesis genera creencias y valores reales válidos arbitrarios para `update_from_direct_experience` y `merge_social_belief`
- **THEN** toda creencia resultante tiene `predicted_value` en `[-1, 1]` y `confidence` en `[0, 1]`.

### Requirement: Cobertura Reportada
La suite SHALL ejecutarse con `python -m pytest --cov=ide` y reportar la cobertura por módulo, para identificar reglas de los escenarios que quedaron sin probar.

#### Scenario: Reporte de cobertura
- **WHEN** se ejecuta `python -m pytest --cov=ide`
- **THEN** la salida incluye una fila de cobertura por cada módulo de `src/ide/`.

### Requirement: Línea Base de Rendimiento
`python -m ide.experiments.benchmark` SHALL ejecutar 3 repeticiones de 300 ticks con la configuración base del Exp 001 y escribir `benchmark.json` con la mediana de ticks por segundo, la versión de Python y la plataforma, sin afectar los resultados de ninguna simulación.

#### Scenario: Medición registrada
- **WHEN** se ejecuta el benchmark
- **THEN** `benchmark.json` contiene `median_ticks_per_second > 0`, `python_version`, `platform` y `repetitions == 3`.
