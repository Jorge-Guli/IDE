# Proposal: Fase II-B (v2.5) — ADN Compacto de 32 bits, Regulación Génica, Epigenética, Plásmidos y Senescencia

## Why

La Fase II (archivada en `openspec/changes/archive/2026-10-20-ide-v2-evolutionary-holonic-intelligence/`) implementó metabolismo, selección, herencia dual, holones recursivos y estigmergia, y corrió su pre-registro (D29). Sus resultados, en `docs/RESULTADOS.md`, son negativos:
- **Afirmaciones.** Las cuatro afirmaciones C5–C8 dieron `NOT_OBSERVED`. Ningún mecanismo diseñado (herencia cultural, selección, holones, vista compartida) mostró el beneficio funcional que se le atribuía.
- **Control nulo.** E4 no es interpretable, porque el control nulo se extingue con `resources_per_pattern = 20`.
- **Observaciones exploratorias, que quedaron como preguntas abiertas:**
  - El genoma congelado rinde más que la evolución en las 10 semillas, y la capacidad de memoria media baja de 3 a 1.9. Una hipótesis no verificada es que el costo cuadrático $R_{21}$ seleccione memorias chicas a costa de la precisión.
  - Los recursos compuestos casi no se resuelven: 0.6 por corrida.
  - La redundancia de los holones crece.
  - Con abundancia (`resources_per_pattern` ≥ 30), la población llega al tope pero casi no hay recambio generacional. La causa no se verificó: la mortalidad no se midió.

En la Fase II, el genoma es un vector plano de 7 escalares (`AgentGenome`): genotipo y fenotipo coinciden y no hay regulación. Un agente paga el costo cuadrático de todo su genoma en cualquier contexto. Esta fase reemplaza esa representación, de forma opcional y ablacionable, por un **ADN compacto en las hojas** ($L = 0$). Ese ADN es una secuencia de codones de 32 bits, con promotores condicionales y una red regulatoria de un nivel. Sobre él se agregan seis mecanismos de la visión de [`docs/vision/ARQUITECTURA_ADN_HOLONICO.md`](../../../docs/vision/ARQUITECTURA_ADN_HOLONICO.md): diferenciación epigenética, plásmidos con inmunidad, esporulación, senescencia, mutación por estrés y trinquete simbiótico. Cada uno es una regla declarada con su propósito y su ablación.

**Lo que esta fase no promete.** Todas sus reglas son maquinaria diseñada. Por la regla metodológica central, cualquier capacidad que persiga una de ellas es **programada**, no emergente:
- la especialización bajo $R_{25}$;
- la supervivencia en el desierto bajo $R_{28}$;
- el recambio generacional bajo $R_{29}$.

El pre-registro propuesto (design D42) declara sus cuatro afirmaciones como programadas por construcción, igual que en la Fase II. El valor científico de la fase está en responder, con controles, si un genoma regulado cambia lo que la Fase II no pudo mostrar. Un resultado negativo se reporta tal cual.

## What Changes

- **ADN compacto y expresión condicional ($R_{24}$):** nuevos tipos inmutables `CompactDNA`, `EpigeneticRole`, `EpigeneticContext` y `ExpressedPhenotype`.
  - **El codón.** Cada codón es un entero de 32 bits con cuatro campos de 8 bits: `PROM | TARGET | REG_MODE | PAYLOAD`.
  - **La transcripción.** `transcribe_phenotype` es pura y trabaja en dos pasadas. La primera evalúa los promotores de contexto y los factores de transcripción; la segunda, los promotores regulados. El resultado es el fenotipo expresado: los 7 rasgos de `AgentGenome`, más la longevidad y el umbral de esporulación.
  - **El costo.** El costo cuadrático se cobra sobre el fenotipo **expresado**. Cada codón paga además un costo lineal $c_{\text{dna}}$.
  - **La expresión en vida.** Ocurre en una nueva Fase 0 del tick. Puede cambiar $C_{\max}$, que achica la memoria por desalojo, y los radios.
  - **El fundador.** El ADN fundador es neutro: expresa exactamente `genome_from_config`.
- **Operadores genéticos.** La mutación del ADN reemplaza a `mutate_genome` cuando el ADN está activo:
  - mutación de un bit del codón (SNP);
  - duplicación y deleción de codones;
  - escisión de un codón del cromosoma a un plásmido.
  - Usa `evo_rng` y respeta la ablación pre-registrada de $R_{13}$.
- **Mecanismos nuevos, cada uno con su bandera (por defecto `False`) y su ablación:**
  - $R_{25}$: roles epigenéticos intra-holón (`EXPLORER`, `LIBRARIAN`, `NERVE`) con impronta en la reproducción holónica.
  - $R_{26}$: conjugación de plásmidos entre vecinos, con un generador nuevo `hgt_rng` (`spawn_key=(5,)`).
  - $R_{27}$: inmunidad tipo CRISPR contra plásmidos con balance energético negativo.
  - $R_{28}$: esporulación ante hambruna sin estímulos.
  - $R_{29}$: senescencia telomérica.
  - $R_{30}$: mutación adaptativa por estrés (SOS).
  - $R_{31}$: trinquete simbiótico. Un holón consolidado no se disuelve por `SPLIT` y paga menos coordinación.
- **Inventario.** El documento de visión agrupaba telómeros y SOS en una sola regla ($R_{29}$). Se separan en $R_{29}$ y $R_{30}$, y el trinquete pasa a $R_{31}$: una regla, un propósito y una ablación.
- **Telemetría.** Nueva `GeneticTickMetrics` en `engine.genetic_history`, sin tocar `TickMetrics` ni `EvolutionaryTickMetrics`.
- **Protocolos.** Nuevos protocolos `002c`, `002d`, `002e` y `003c` en `exp25_runner.py`, con su atribución.
- **Compatibilidad.** Con las banderas en su valor por defecto, la Fase I es bit a bit idéntica: los hashes dorados no cambian. La Fase II se comporta exactamente igual.

## Capabilities

### New Capabilities
- `compact-dna`: codón de 32 bits, ADN fundador, transcripción en dos pasadas, fenotipo expresado, operadores de mutación del ADN, plásmidos y memoria CRISPR ($R_{24}$, $R_{26}$, $R_{27}$).

### Modified Capabilities
- `domain-contracts`: tipos de la Fase II-B y banderas e hiperparámetros con retrocompatibilidad por defecto.
- `bounded-memory`: cambio de capacidad en vida (`resize`), con desalojo por menor utilidad.
- `micro-agent`: ADN, fenotipo expresado, configuración base, rol epigenético, edad, estado de endospora y descendencia con ADN.
- `evolutionary-dynamics`: costo del ADN, senescencia ($R_{29}$), esporulación ($R_{28}$) y mutación SOS ($R_{30}$).
- `holonic-hierarchy`: asignación de roles ($R_{25}$) y trinquete simbiótico ($R_{31}$).
- `simulation-engine`: Fase 0 de expresión, orden de la Fase 5 extendida, conjugación con `hgt_rng` y evaluación CRISPR.
- `experimental-suite`: `GeneticTickMetrics` y protocolos `002c`, `002d`, `002e` y `003c`.
- `emergence-attribution`: `PHASE25_DESIGN_RULES` ($R_{24}$–$R_{31}$), `PHASE25_CLAIMS` (C9–C12) y su ejecución.

## Decisiones pendientes (requieren aprobación antes del bloque 1 de `tasks.md`)

- **P4, pre-registro de la Fase II-B (design D42).** Hay que aprobar o corregir:
  - el inventario $R_{24}$–$R_{31}$, con sus propósitos y ablaciones;
  - las afirmaciones C9–C12, todas propuestas como programadas por construcción;
  - las configuraciones de los protocolos `002c`, `002d`, `002e` y `003c`;
  - el perfil (`phase2`, semillas 42–51);
  - los valores por defecto de los hiperparámetros nuevos (D31).
  - Nada de esto se mira contra resultados: se fija antes.
- **P5, justificación de $R_{29}$.** El "Tapón de Matusalén" es una hipótesis **no verificada** (`docs/RESULTADOS.md`). Propuesta: antes de pre-registrar C10, correr un diagnóstico demográfico (tarea 0.1). Mide la mortalidad y la edad al morir con `resources_per_pattern = 40` y las semillas de calibración 0 a 9, sin mirar ninguna métrica de afirmación. Si el diagnóstico refuta la hipótesis, se decide si $R_{29}$ y C10 se mantienen.
- **P6, sesgos declarados.** Hay que aprobar que se declaren estos sesgos:
  - $R_{24}$ abarata por diseño la complejidad latente;
  - $R_{28}$ está diseñada para rescatar poblaciones que la Fase II extinguía;
  - $R_{31}$ estabiliza holones por decreto.
  - Ninguna de esas capacidades podrá presentarse como hallazgo.
- **P7, solapamiento con el Experimento 004.** $R_{25}$ asigna roles por una regla del holón, así que toda especialización que produzca es programada. Propuesta: el Exp 004 (especialización y división del trabajo) se mide con $R_{25}$ ablacionada, y lo que muestre la Fase II-B con $R_{25}$ activa no cuenta como evidencia para el 004.

## Impact

- **Código afectado:**
  - `src/ide/config.py`;
  - `src/ide/domain/types.py`;
  - `src/ide/agent/memory.py`, `src/ide/agent/micro_agent.py`, `src/ide/agent/evolution.py` y `src/ide/agent/holon.py`, más un módulo nuevo `src/ide/agent/dna.py`;
  - `src/ide/simulation/engine.py`;
  - `src/ide/experiments/metrics.py` y `src/ide/experiments/attribution.py`, más un runner nuevo `src/ide/experiments/exp25_runner.py`.
- **Invariantes:**
  - `src/ide/agent/` sigue sin importar `environments`, `simulation` ni `experiments`.
  - `dna.py` es puro: no ve coordenadas ni `true_value`.
  - El conocimiento social sigue entrando sólo por `assimilate_testimony`. El ADN no transporta creencias.
- **Determinismo.** Un generador derivado nuevo, `(5,)` `hgt_rng`, declarado en `CLAUDE.md` y en D30. Sólo se consume con $R_{26}$ activa.
- **Tests:** suites nuevas `tests/test_compact_dna.py`, `tests/test_genetic_ecology.py` y `tests/test_exp25.py`, más la ampliación de las existentes, sin modificar ningún test de las Fases I y II.
- **Dependencias:** ninguna nueva.
