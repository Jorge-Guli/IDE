# Proposal: Plataforma de Inteligencia Distribuida Emergente (IDE)

## Why

Los sistemas actuales de inteligencia artificial concentran la cognición en modelos monolíticos de alto costo computacional, mientras que este proyecto busca investigar experimentalmente si capacidades cognitivas complejas, memoria colectiva y validación epistémica pueden emerger de una población de micro-agentes con memoria individual deliberadamente insuficiente ($C_{\max} \ll N$) operando sin servidor central ni memoria global. Se requiere construir la arquitectura fundacional desacoplada en Python y la suite experimental reproducible (empezando por el Experimento 001 y dejando los puntos de extensión listos para los Experimentos 002 a 007).

Como el agente ya incorpora mucha inteligencia de diseño (confianza, descuento del rumor, refuerzo, castigo, olvido, consultas, difusión), el proyecto adopta como regla metodológica central que **toda propiedad que se afirme como emergente debe poder distinguirse de una capacidad programada explícitamente en el agente**. Este cambio no elimina esas reglas, pero las declara, las vuelve ablacionables y agrega la maquinaria para clasificar cada afirmación. El Experimento 001 queda así planteado como **línea base funcional**: sus afirmaciones de acceso, superávit y persistencia son programadas por construcción, y la inmunidad colectiva a la falsedad es la única que se somete a una prueba empírica genuina de independencia respecto de las reglas diseñadas.

## What Changes

- Creación de la estructura de paquete Python (`pyproject.toml`, `src/ide/`, `tests/`) bajo arquitectura hexagonal estricta (separación total entre cognición del agente y topología del entorno).
- Implementación de contratos de dominio inmutables (`Pattern`, `KnowledgeUnit`, `Resource`, `VisibleResource`, `Observation`, `Message`, `AgentAction`, `ActionResult`) y el puerto abstracto `EnvironmentPort`, incluido un oráculo de verdad restringido a telemetría (`get_reachable_true_values`).
- Implementación del módulo de memoria acotada (`BoundedMemory`) con límite estricto $C_{\max}$, índice de utilidad epistémica $U(k, t)$ y decaimiento temporal pasivo.
- Implementación del motor epistemológico (funciones puras de `epistemology.py`) con reglas formales para aprendizaje por experiencia directa y revalidación social en tres escenarios (Desconocido con descuento $\gamma$, Consenso y Conflicto Epistémico).
- Implementación del agente autónomo (`MicroAgent`) agnóstico de coordenadas, con soporte para consultas colectivas en tiempo real (`QUERY_PATTERN` / `QUERY_RESPONSE`), difusión espontánea (`BROADCAST_BELIEF`) y toma de decisiones basada en umbral de confianza y exploración $\epsilon$. La semántica del protocolo queda aislada en `agent/protocol.py`, para poder des-programarla en experimentos posteriores.
- Implementación del entorno inicial `ToroidalGrid2D` con aritmética modular sin bordes, indexación espacial $O(1)$ por celda y ocultamiento estricto del valor real $v(r)$ antes de la interacción.
- Implementación del motor de simulación por pasos discretos (`SimulationEngine`) con pipeline determinista de 5 fases por tick, barajado de turnos mediante semilla (`np.random.Generator`) y reproducibilidad garantizada también entre procesos (independiente de `PYTHONHASHSEED`).
- Implementación del colector de métricas M1–M7 (`MetricsCollector`), incluida la cobertura accesible a un salto como medida del meta-agente, y el ejecutor automatizado de los protocolos experimentales:
  - **001-A:** Población comunicada vs. agentes aislados (superávit funcional).
  - **001-B:** Falsificación y Extinción de Creencias Falsas Inyectadas.
  - **001-C:** Resiliencia ante Daño Poblacional ($10\%, 30\%, 50\%, 70\%$) y Persistencia Extra-Individual.
  - **001-D:** Atribución de emergencia: ablación de las reglas de diseño, control nulo de contenido y clasificación de cada afirmación pre-registrada (`PROGRAMMED`, `EMERGENT`, etc.).
  - **Hooks de Extensión (002–006):** Puntos de extensión para estrategias de confianza social, especialización emergente, shock ambiental, inteligencia composicional y evolución (sólo contratos; su lógica queda fuera de este cambio).
- Simultaneidad declarada (percepción, comunicación y decisión sincrónicas; conflictos resueltos por sorteo) y un criterio de robustez al esquema de actualización (E5), para que el reloj de la simulación no pueda producir falsos positivos de emergencia.
- Calidad verificable desde el día 0: Ruff, Pyright estricto, pruebas por propiedades con Hypothesis, cobertura, una línea base de rendimiento medida y paralelismo entre corridas (`--jobs`) que no altera los resultados.
- CLI multi-semilla con exportación JSON/CSV y separación entre la suite de software (`pytest`) y la verificación de expectativas empíricas (`python -m pytest -m empirical`), cuyos resultados negativos se reportan sin ajustar parámetros.

## Capabilities

### New Capabilities
- `domain-contracts`: Modelos de datos inmutables, configuración determinista (`SimulationConfig`) e interfaz abstracta `EnvironmentPort` que desacopla el cerebro del agente de la geometría del mundo.
- `bounded-memory`: Almacenamiento local limitado a $C_{\max}$ creencias con cálculo de utilidad epistémica $U(k, t)$, reemplazo determinista y decaimiento pasivo.
- `epistemic-engine`: Reglas matemáticas de actualización por experiencia directa y asimilación/revalidación social frente a acuerdo, rumor desconocido o contradicción.
- `micro-agent`: Ciclo cognitivo local de percepción, consulta a vecinos (`QUERY_PATTERN`), respuesta social, difusión y selección de acciones sin acceso a estado global.
- `spatial-environments`: Implementación de `ToroidalGrid2D` con índice espacial $O(1)$, vecindades configurables y contrato preparado para futuros entornos (`SpatialGraph`, `ContinuousSpace2D`).
- `simulation-engine`: Orquestador de ticks en 5 fases síncronas con aleatorización reproducible de orden de agentes e inyección controlada de perturbaciones.
- `experimental-suite`: Cálculo de métricas M1–M7, ejecución reproducible de los protocolos 001-A, 001-B y 001-C, exportación de resultados en JSON/CSV y CLI de ejecución.
- `emergence-attribution`: Inventario de reglas de diseño con propósito declarado, ablaciones, control nulo de contenido, registro pre-declarado de afirmaciones y clasificación automática emergente/programado (protocolo 001-D).
- `quality-tooling`: Calidad estática (Ruff, Pyright estricto), pruebas por propiedades reproducibles con Hypothesis, cobertura y línea base de rendimiento.
- `roadmap-extensions`: Contratos e interfaces de extensión para los Experimentos 002 (Revalidación Social y Reputación), 003 (Especialización Emergente), 004 (Reorganización ante Shock Ambiental), 005 (Inteligencia Composicional) y 006 (Evolución y Selección).

### Modified Capabilities
<!-- No hay capacidades previas modificadas; proyecto greenfield -->

## Impact

- **Código nuevo:** Creación completa de `src/ide/` y `tests/` (15 módulos de producción y suite de pruebas unitarias, de integración y de hipótesis con `pytest`).
- **Dependencias:** Python $\ge 3.11$, `numpy` (para RNG reproducible y agregaciones estadísticas) y `pytest` (desarrollo/testing).
- **Reglas Arquitectónicas Aplicadas:**
  - Prohibición estricta de importar `environments` dentro de `src/ide/agent/`.
  - Prohibición de exponer `Resource.true_value` en `Observation` antes de ejecutar `INTERACT`.
  - Determinismo bit a bit garantizado mediante instancia explícita de `np.random.Generator(np.random.PCG64(seed))` y prohibición de iterar conjuntos sin ordenar.
- **Fuera de alcance:** energía $E_i$ del agente, recursos neutrales, interfaz gráfica, la lógica de los Experimentos 002–007 (incluido el protocolo de comunicación aprendido) y el barrido de densidad en busca de transiciones abruptas.
