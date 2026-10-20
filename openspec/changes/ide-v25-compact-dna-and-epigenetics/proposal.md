# Proposal: Fase II-B (v2.5) — ADN Compacto de 32 bits, Conducta Evolucionable y Ecología

> **Reformulada el 2026-10-20** (ver la sección "Reformulación del 2026-10-20" al final y design D43–D56). Lo que sigue hasta esa sección es la propuesta original, aprobada el mismo día; donde la reformulación la contradice, rige la reformulación.

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
  - **El codón.** Cada codón es un entero de 32 bits: `PROM` (8 bits), `TARGET` (8 bits), `REG_MODE` (8 bits, dividido en `MODE` de 2 bits y `CHANNEL` de 6) y `PAYLOAD` (8 bits con signo).
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
- `compact-dna`: codón de 32 bits, ADN fundador, transcripción en dos pasadas, fenotipo expresado, operadores de mutación del ADN, plásmidos y memoria CRISPR ($R_{24}$, $R_{26}$, $R_{27}$); con la reformulación, también los destinos de conducta, los promotores sensoriales, la evaluación de impulsos y la recombinación ($R_{32}$, $R_{38}$).

### Modified Capabilities
- `domain-contracts`: tipos de la Fase II-B, tipos de conducta y percepción social, y banderas e hiperparámetros con retrocompatibilidad por defecto.
- `bounded-memory`: cambio de capacidad en vida (`resize`), con desalojo por menor utilidad.
- `micro-agent`: ADN, fenotipo expresado, configuración base, rol epigenético, edad, estado de endospora, descendencia con ADN, puerto de política y política genética.
- `evolutionary-dynamics`: costo del ADN, senescencia ($R_{29}$), endospora como conducta ($R_{28}$), mutación SOS ($R_{30}$), costo de los ataques y recombinación al nacer.
- `holonic-hierarchy`: señal posicional ($R_{25}$) y compromiso simbiótico ($R_{31}$).
- `spatial-environments`: recursos agotables, heterogeneidad, cadáveres y agentes visibles ($R_{33}$–$R_{35}$).
- `simulation-engine`: motor por sistemas y observadores, Fase 0 de expresión, percepción social, interacciones entre agentes, conjugación con `hgt_rng` y evaluación CRISPR.
- `experimental-suite`: `GeneticTickMetrics` y `EcologyTickMetrics` con métricas de evolución abierta, compuerta de viabilidad y protocolos `25a`, `25b` y `25c`.
- `emergence-attribution`: `PHASE25_DESIGN_RULES` ($R_{24}$–$R_{38}$), `PHASE25_CLAIMS` (C13–C18), corrección de Holm y tamaño de efecto mínimo.

## Decisiones P4–P7 (resueltas el 2026-10-20; ver el registro al final de esta sección)

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

## Resolución de P4–P7 (2026-10-20, decisión del responsable del proyecto)

- **P4.** Se aprueba el pre-registro de D42 tal como está:
  - el inventario $R_{24}$–$R_{31}$;
  - las afirmaciones C9–C12;
  - las configuraciones de `002c`, `002d`, `002e` y `003c`;
  - el perfil `phase2` con las semillas 42–51, las reglas inactivas y E4;
  - los valores por defecto de D31.
- **P5.** El diagnóstico de la tarea 0.1 confirmó el "Tapón de Matusalén" en las 20 semillas (`docs/RESULTADOS.md`). Se mantienen $R_{29}$ y C10.
- **P6.** Se aprueban los sesgos declarados de $R_{24}$, $R_{28}$ y $R_{31}$.
- **P7.** El Exp 004 se medirá con $R_{25}$ ablacionada. Lo que muestre la Fase II-B con $R_{25}$ activa no cuenta como evidencia de especialización.

## Decisiones tomadas (2026-10-20, tras la revisión cruzada independiente)

Son parte del pre-registro que se aprueba completo en la tarea 0.2. Ya están incorporadas al design:
- **C11.** Mide la población **activa** final, sin endosporas (`final_active_population`). La prueba de humo de `002e` no registra la población, y `002e` no se recalibra después de ella.
- **E4 en `002d`.** Es interpretable sólo si el control nulo termina con población viva en al menos 8 de 10 semillas, según la demografía. En los otros tres protocolos, E4 es no interpretable de antemano.
- **CRISPR ($R_{27}$).** El balance del ensayo descuenta la energía cedida a los hijos durante la ventana, para no purgar plásmidos por el solo hecho de reproducirse.
- **Diagnóstico de la tarea 0.1.** La hipótesis del "Tapón de Matusalén" se confirma si, en al menos 8 de 10 semillas de cada protocolo, más de la mitad de los agentes vivos en el tick 2000 nació antes del tick 1000.

## Impact

> Esta sección es de la propuesta original. La reformulación la amplía y la corrige en "Impacto adicional" (al final): en particular, el test de firmas canónicas de la Fase I se amplía con parámetros opcionales.

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
- **Tests:** suites nuevas `tests/test_compact_dna.py` y `tests/test_exp25.py`, más la ampliación de las existentes, sin modificar ningún test de las Fases I y II.
- **Dependencias:** ninguna nueva.

## Reformulación del 2026-10-20

### Por qué
Con la etapa A terminada (bloques 1 a 5), una lectura del código y de los resultados de las Fases I y II mostró que el plan original repetía el experimento de la Fase II a mayor costo:
- **La conducta era código fijo.** El ADN sólo ajustaba los 7 parámetros de una política escrita a mano, así que la evolución no podía producir conductas nuevas.
- **Las capacidades se otorgaban por decreto.** Castas, esporulación y estabilidad del holón las producía una regla, y por eso C9–C12 eran programadas por construcción.
- **El entorno no tenía física entre agentes.** Sin escasez ni interacciones no hay competencia ni coevolución.
- **El motor era monolítico** y **la medición sólo preguntaba si una hipótesis pasaba**, con 10 semillas y la viabilidad descubierta tarde.

El responsable del proyecto decidió que cada entregable acerque el proyecto a su objetivo de fondo, que la vida digital pueda surgir, evolucionar y complejizarse. Por eso la Fase II-B corrige esas cuestiones de base y conserva el concepto de ADN, que se mejora.

### Qué cambia
- **Principio:** la regla da la capacidad y el ADN decide su uso (design D43).
- **Arquitectura:** motor por sistemas y observadores (D44) y puerto de política (D45), sin cambio de conducta, con los hashes dorados como test de aceptación.
- **Conducta en el ADN ($R_{32}$, D46, D47):** destinos de conducta, promotores sensoriales y una política genética cuyo ADN fundador reproduce exactamente la política escrita a mano. El ADN también decide si el agente comunica.
- **Ecología (D48, D49):** recursos agotables ($R_{33}$), heterogeneidad espacial y estacional ($R_{34}$), cadáveres ($R_{35}$), transferencia de energía ($R_{36}$) y depredación ($R_{37}$).
- **ADN mejorado:** recombinación ($R_{38}$, D51) y tres rasgos nuevos (compromiso simbiótico, propensión a recombinar y propensión a comunicar).
- **Reglas reformuladas (D50):** $R_{25}$ pasa a ser una señal posicional; $R_{28}$, una conducta disponible; $R_{31}$, un sello que depende del compromiso expresado.
- **Medición (D53–D56):** métricas de evolución abierta (actividad de Bedau–Packard, divergencia de la conducta, regulación expresada), compuerta de viabilidad antes de cualquier afirmación, 30 semillas, corrección de Holm y tamaño de efecto mínimo.
- **Pre-registro:** D42 queda sustituido por el borrador D56. C9–C12 se retiran sin medir. Las afirmaciones nuevas, C13–C18, son pruebas genuinas contra la deriva neutral o contra la ablación de un mecanismo ecológico.

### Qué no cambia
- D30–D35 (etapa A, implementada), $R_{26}$, $R_{27}$, $R_{29}$ y $R_{30}$.
- La compatibilidad bit a bit con las Fases I y II con las banderas por defecto.
- Las invariantes de arquitectura y determinismo de `CLAUDE.md`. La reformulación no agrega generadores.

### Decisión P8 (pendiente, tarea 0.5)
Aprobar o corregir el borrador D56 antes del bloque 6:
- el inventario $R_{24}$–$R_{38}$;
- los protocolos `25a`, `25b` y `25c` y sus condiciones;
- las afirmaciones C13–C18, sus métricas y sus $\delta_{\min}$;
- la prueba de signo con Holm, el perfil `phase25` de 5000 ticks y las semillas 42–71;
- la compuerta de viabilidad de D55;
- los valores por defecto de D52.

### Impacto adicional
- **Código nuevo:** `src/ide/agent/policy.py`, `src/ide/simulation/pipeline.py` y `src/ide/experiments/phase25_viability.py`, además de los módulos de la propuesta original.
- **Código modificado además del original:** `src/ide/agent/protocol.py`, `src/ide/domain/ports.py` y `src/ide/environments/grid2d.py`.
- **Tests:** algunos tests de los bloques 1 a 5 cambian donde la reformulación lo declara (destinos `0x0A`–`0x0C`, conteo de `expressed_codons` y `lock_composite_threshold`). Ningún test de conducta de las Fases I y II cambia. La excepción es el test de firmas públicas canónicas de la Fase I, que se amplía con los parámetros opcionales `policy` y `social` (design, precisión 22).
- **Alcance:** la fase pasa de 7 a 18 bloques pendientes. Es del tamaño de la Fase II completa.
