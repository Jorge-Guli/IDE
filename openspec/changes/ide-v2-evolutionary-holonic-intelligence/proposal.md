# Proposal: Fase II (v2.0) — Evolución Abierta, Herencia Dual y Arquitectura Holónica Recursiva

## Why

La Fase I (v1.0) construyó y verificó una población de micro-agentes con memoria estrictamente acotada ($C_{\max} < |\mathcal{P}|$) y un marco de atribución (001-D) que separa lo programado de lo emergente. Sus resultados, registrados en `RESULTADOS.md` (perfil `quick`, semillas 42–46), son honestos y mayormente negativos para la emergencia:
- **C1 (acceso) y C2 (superávit de decisión):** `PROGRAMMED`, por construcción. La comunicación da acceso y mejores decisiones (p = 0.03125 frente a la población aislada), pero ése es el propósito de las reglas que la producen.
- **C3 (inmunidad a la falsedad):** `PROGRAMMED`. La población completa extingue el rumor en las 5 semillas, pero sin los filtros epistémicos diseñados (R3, R4, R6, R7) la contención no supera a la población aislada (E3: p = 0.5).
- **C4 (persistencia extra-individual):** `NOT_OBSERVED`. Tras eliminar a los descubridores, el conocimiento social sobrevive sólo en 2 de 5 semillas (001-D, perfil `quick`).

Estos resultados muestran un **techo estructural**: en una población estática de agentes inmortales ($g=0$), con reglas comunicativas fijas y sin unidades funcionales de orden superior, toda capacidad colectiva observada se explica por las reglas diseñadas y el conocimiento no sobrevive a sus portadores. La Fase II pregunta si mecanismos de otro tipo (selección, herencia y composición) cambian ese cuadro, y somete cada uno al mismo marco de atribución.

Para investigar si una inteligencia distribuida abierta (*open-ended evolution*) es alcanzable, el sistema incorpora los mecanismos de las **Grandes Transiciones Evolutivas** (Maynard Smith & Szathmáry) y la **Síntesis Evolutiva Extendida** (Simbiogénesis de Lynn Margulis, Causalidad Descendente de Denis Noble y Construcción de Nicho / Estigmergia): metabolismo energético con selección natural, reproducción diferencial con herencia genética y cultural vertical, e integración jerárquica recursiva ilimitada ($L = 0, 1, 2, \dots, K$) donde micro-agentes cooperativos formen holones (`CompositeAgent`) capaces de resolver problemas compuestos ($m > C_{\max}$), ortogonalizar sus memorias internas, reproducirse simbióticamente y componer nuevos niveles holónicos sin límite prefijado.

## What Changes

- **Metabolismo Energético y Selección Natural ($R_{12}$):**
  - Incorporación de energía interna $E_i(t) \in \mathbb{R}$, costo metabólico basal por tick $c_{\text{base}}(i) = c_{\text{fijo}} + c_{\text{mem}} \cdot C_{\max, i}^2 + c_{\text{sens}} \cdot (r_{\text{perc}, i}^2 + r_{\text{com}, i}^2)$ (penalización cuadrática del cerebro y de los sentidos individuales: es una decisión de diseño que encarece la hipertrofia solitaria y, por lo tanto, **sesga a favor de la cooperación**; se declara como tal), costo por movimiento $c_{\text{move}}$ y costo por emisión comunicativa $c_{\text{msg}}$.
  - Muerte por agotamiento energético ($E_i(t) \le 0$) con liberación espacial inmediata, y reproducción diferencial ($E_i(t) \ge E_{\text{reprod}}$) con partición conservativa de energía ($\kappa_{\text{part}}$) sujeta a capacidad de carga ambiental $N_{\max}$.
- **Herencia Dual Intergeneracional ($g \to g+1$):**
  - **Herencia Genética con Mutación Acotada ($R_{13}$):** Nuevo dataclass inmutable `AgentGenome` que encapsula rasgos heredables ($\alpha, \gamma, \epsilon, \omega_{\text{bond}}, C_{\max}, r_{\text{perc}}, r_{\text{com}}$) con mutación gaussiana truncada / discreta controlada por un generador pseudoaleatorio dedicado (`evo_rng`) al reproducirse.
  - **Herencia Cultural Vertical ($R_{14}$):** Al nacer, el hijo recibe como testimonio parental (por `assimilate_testimony`, la única puerta del conocimiento social) hasta $\min(C_{\max, \text{hijo}}, |\mathcal{M}_{\text{padre}}|)$ creencias de mayor utilidad del progenitor, con descuento intergeneracional $\gamma_{\text{gen}} \in [0, 1]$ además del descuento social $\gamma$: la creencia heredada tiene confianza $\gamma \cdot \gamma_{\text{gen}} \cdot c$, $n = 1$, $\tau = t_{\text{nac}}$ y `from_direct_experience = False`.
- **Arquitectura Holónica y Jerarquía Recursiva Ilimitada ($L = 0, 1, 2, \dots, K$):**
  - **Protocolo `AgentNode` y clase `CompositeAgent` (Patrón *Composite*):** Tanto `MicroAgent` ($L=0$) como `CompositeAgent` ($L \ge 1$) implementan `AgentNode`. Un `CompositeAgent` agrupa un conjunto arbitrario de nodos hijos (`MicroAgent` o `CompositeAgent` de niveles inferiores), definiendo recursivamente su nivel $L(U) = 1 + \max_{c \in \text{children}(U)} L(c)$, su masa $|U| = \sum_c |c|$ y su memoria colectiva $\mathcal{M}_{\text{holon}}(U) = \bigcup_{\ell \in \text{leaves}(U)} \mathcal{M}_\ell$ sin límite de profundidad jerárquica.
  - **Fusión Simbiótica `BOND` ($R_{15}$) y Fisión `SPLIT` ($R_{16}$):** Operadores dinámicos en la Fase 5 del motor que ensamblan pares de nodos co-localizados cuya complementariedad epistémica de Jaccard y propensión $\omega_{\text{bond}}$ superan el umbral $\theta_{\text{sinergia}}$, y disuelven holones cuyo costo metabólico de coordinación $c_{\text{coord}}(U) = c_{\text{enlace}} \cdot |U| \cdot L(U)$ excede su superávit cooperativo o cuya energía agregada cae por debajo del umbral de viabilidad.
- **Mecanismos declarados además (design D29):** física metabólica nuclear ($R_{20}$), costo cuadrático de cerebro y sentidos ($R_{21}$), vista compartida del holón ($R_{22}$) y coordinación y reparto energético del holón ($R_{23}$).
- **Pilares de la Síntesis Evolutiva Extendida:**
  - **Endosimbiosis Reproductiva Holónica ($R_{17}$, Margulis):** Reproducción directa de un `CompositeAgent` exitoso ($E_{\text{holon}}(U) \ge |U| \cdot E_{\text{reprod}}$) como unidad simbiótica ya ensamblada (`reproduce_holon`), clonando con mutación cada hoja y replicando la topología arbórea en un holón hijo $U_{\text{hijo}}$.
  - **Causalidad Descendente y Particionamiento Epigenético Intra-Holón ($R_{18}$, Noble):** Modulación descendente de la función de utilidad de memoria $U(k, t)$ de las hojas de un holón mediante el factor multiplicativo de redundancia $\psi_{\text{red}} \in (0, 1]$ cuando otro miembro del holón en alcance local ya posee el patrón $\rho$ con mayor confianza. Esta regla está **diseñada para ortogonalizar** las memorias ($\mathcal{M}_i \cap \mathcal{M}_j \to \emptyset$). Por eso la ortogonalización que produzca es, por definición, programada, no espontánea.
  - **Construcción de Nicho y Estigmergia Espacial ($R_{19}$):** Depósito y lectura de rastros epistémicos `StigmergicTrace` en las celdas de `ToroidalGrid2D` con decaimiento ambiental $\delta_{\text{suelo}}$ por tick.
- **Recursos Compuestos Graduados y Nuevos Protocolos Experimentales (002 y 003):**
  - Recursos compuestos (`CompositeRule`, que ya existe como contrato en `domain/extensions.py`) de orden $m \in \{2, 3, \dots\}$ que exigen que el nodo consumidor (individuo u holón) conozca simultáneamente los $m$ patrones constituyentes para liberar un retorno energético superlineal $m^{\kappa_{\text{comp}}}$ (escalado por $\eta_E$), proveyendo la presión selectiva ecológica para escalar a niveles $L=1, 2, \dots, K$.
  - Nuevas métricas poblacionales y multinivel `M8` a `M13` en `EvolutionaryTickMetrics`, extensión del catálogo de atribución a `R12`–`R23` y afirmaciones `C5`–`C8`, y runners reproducibles `exp002_runner.py` y `exp003_runner.py`.
- **Compatibilidad Regresiva Absoluta con Fase I:**
  - Todas las banderas de activación de Fase II tienen valor por defecto `False` y `num_composite_patterns = 0` en `SimulationConfig` (`enable_holon_splitting`, `enable_holon_view` y `holon_energy_sharing` valen `True`, pero sólo modulan a `enable_holonic_hierarchy`). Con esos valores, el motor, la grilla, los tipos de dominio, `TickMetrics` y el generador `rng` se comportan bit a bit igual que en la Fase I, preservando los 397 tests existentes y los hashes SHA-256 dorados.

## Capabilities

### New Capabilities
- `evolutionary-dynamics`: Metabolismo energético ($E_i(t)$), costo cuadrático de capacidad cerebral ($C_{\max}^2$), muerte por inanición, reproducción diferencial ($R_{12}$), genoma mutable `AgentGenome` ($R_{13}$) y herencia cultural vertical con descuento intergeneracional ($R_{14}$).
- `holonic-hierarchy`: Protocolo `AgentNode`, clase recursiva `CompositeAgent` para niveles arbitrarios $L = 0 \dots K$, memoria colectiva distribuida $\mathcal{M}_{\text{holon}}(U)$, operadores de fusión `BOND` ($R_{15}$) y fisión `SPLIT` ($R_{16}$), reproducción simbiótica de holones ($R_{17}$) y causalidad descendente intra-holón ($R_{18}$).

### Modified Capabilities
- `domain-contracts`: Incorporación en `SimulationConfig` de los hiperparámetros y banderas de Fase II (con defaults retrocompatibles), nuevos tipos inmutables (`AgentGenome`, `StigmergicTrace`, `HolonSnapshot`; `CompositeRule` ya existe) y sub-puerto `EvolutionaryEnvironmentPort` (preservando intactos los 10 métodos de `EnvironmentPort` y los 5 campos de `VisibleResource`).
- `roadmap-extensions`: Evolución de `AgentCapabilities` y estrategias de similitud/sinergia para integrarse con `AgentGenome` y con la evaluación de fusión holónica.
- `bounded-memory`: Soporte opcional de penalización por redundancia intra-holón ($\psi_{\text{red}}$, $R_{18}$) en el cálculo de utilidad $U(k, t)$ y desalojo, manteniendo intacto el comportamiento por defecto ($\psi_{\text{red}} = 1.0$).
- `micro-agent`: Implementación del protocolo `AgentNode` ($L=0$), estado energético y de linaje (`energy`, `generation`, `parent_id`, `genome`), consumo de parámetros desde `genome` cuando la evolución está activa, método `create_offspring` (energía y genoma; la herencia cultural la entrega el motor por `assimilate_testimony`) y separación entre `own_belief` y la creencia efectiva (requisito `MODIFIED`).
- `spatial-environments`: Implementación de `EvolutionaryEnvironmentPort` en `ToroidalGrid2D` con soporte para inserción de descendientes (`spawn_agent_near`), recursos compuestos (`CompositeRule` de orden $m \ge 2$) y rastros estigmérgicos por celda (`StigmergicTrace`, $R_{19}$).
- `simulation-engine`: Extensión de la Fase 4 (resolución cooperativa de recursos compuestos por holones y depósito estigmérgico) y Fase 5 (metabolismo, causalidad descendente, `BOND`, `SPLIT`, muerte y reproducción individual/holónica usando `evo_rng` dedicado).
- `experimental-suite`: Nuevas métricas `M8` a `M13` en `EvolutionaryTickMetrics`, runners `exp002_runner.py` (Protocolos `002-A` y `002-B`) y `exp003_runner.py` (Protocolos `003-A` y `003-B`).
- `emergence-attribution`: Extensión del pre-registro con `PHASE2_DESIGN_RULES` (`R12`–`R23`), `ALL_DESIGN_RULES`, `PHASE2_CLAIM_CHANNELS`, el perfil `phase2` y las afirmaciones evolutivas y holónicas `C5`–`C8` (`EXP002_CLAIMS` y `EXP003_CLAIMS`).

## Decisiones tomadas (2026-10-18)

- **P1, canal de conocimiento del holón → (a):** vista compartida efímera, declarada como única excepción a la regla de que el conocimiento social entra por `assimilate_testimony`, con regla propia y ablación ($R_{22}$, `enable_holon_view`). Design D25.
- **P2, conocimiento de recursos compuestos → (b):** el agente aprende el valor de cada patrón compuesto por experiencia, como cualquier otro patrón. El motor no le inyecta nada. Design D25 y D27.
- **P3, pre-registro de la Fase II:** design D29.
  - **Reglas.** Inventario `R12`–`R23`:
    - `R12` se ablaciona con reproducción neutral, que es también el control de deriva.
    - Reglas nuevas: `R20`, física metabólica nuclear; `R21`, costo cuadrático; `R22`, vista del holón; `R23`, coordinación y reparto energético.
  - **Afirmaciones.**
    - C5, C6 y C7 se declaran programadas por construcción, con un criterio ampliado: el canal de la afirmación está entre sus reglas responsables.
    - C8 pasa a ser "cobertura colectiva adquirida **sin** causalidad descendente": cuántos patrones correctos distintos gana un holón desde que se formó, por miembro, comparada con la misma regla de formación sin la vista compartida ($R_{22}$). Por el principio conservador, es una afirmación sobre disponibilidad de conocimiento y se declara **programada por construcción** por $R_{22}$. **La Fase II no tiene ninguna prueba genuina pre-registrada**, y eso se declara como resultado del diseño.
    - Qué rasgos evolucionan se registra como observación exploratoria.
  - **Perfil.** 10 semillas (42–51), 2000 ticks y configuraciones por protocolo congeladas.
  - **Métricas.** M9 pasa a ser descriptiva (proporción social de los descendientes), y la contribución de la herencia se mide contra la ablación de `R14`. Se agrega M13 (cobertura colectiva adquirida desde la formación, sobre creencias de signo correcto; la reducción de redundancia queda como dato descriptivo).
  - **Corrección del pre-registro (2026-10-18, antes de mirar resultados).** Tras la revisión del pre-registro se cambiaron, con aprobación:
    - C8, para que el sesgo de `BOND` no cuente: ahora mide el cambio desde la formación, contra la ablación de `R22`, en lugar de un control barajado.
    - M13: sólo cuenta creencias de signo correcto; sólo entran holones formados por `BOND`; el estado de formación se reinicia cuando el holón pierde un miembro; se promedia por par (tick, holón), y sin holones no hay medición (la semilla cuenta como empate).
    - El mecanismo hipotético (la vista suprime consultas a lo que el holón ya sabe) se declara de antemano, sin pre-registrar un veredicto esperado. E4 anula el contenido de todos los canales, así que pone a prueba si importa el contenido de toda la comunicación.
    - M13 mide cobertura colectiva adquirida en lugar de reducción de redundancia, que premiaba olvidar.
    - La reproducción neutral: conserva exactamente la demografía y sólo sortea el genoma.
    - Las reglas inactivas de cada protocolo se excluyen de `rule_effects`.

    Se retiró el generador derivado `(4,)`.

## Impact

- **Código afectado:**
  - `src/ide/config.py` (nuevos campos validados de Fase II con valores por defecto `False` que no alteran `SimulationConfig()` base en comportamiento).
  - `src/ide/domain/types.py`, `src/ide/domain/ports.py`, `src/ide/domain/extensions.py`.
  - `src/ide/agent/memory.py`, `src/ide/agent/micro_agent.py`, y nuevos módulos `src/ide/agent/evolution.py` y `src/ide/agent/holon.py`.
  - `src/ide/environments/grid2d.py`.
  - `src/ide/simulation/engine.py`.
  - `src/ide/experiments/metrics.py`, `src/ide/experiments/attribution.py`, y nuevos runners `src/ide/experiments/exp002_runner.py` y `src/ide/experiments/exp003_runner.py`.
- **Tests:** Nuevas suites de pruebas unitarias y basadas en propiedades (`tests/test_evolutionary_dynamics.py`, `tests/test_holonic_hierarchy.py`, `tests/test_exp002_exp003.py`) más ampliación de las suites existentes sin modificar ni romper ninguno de los 397 tests de Fase I.
- **Dependencias:** Ninguna dependencia externa nueva (se mantiene el stack puro `numpy`, `pytest`, `hypothesis`, `ruff`, `pyright`).
