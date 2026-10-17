# Proposal: Fase II (v2.0) — Evolución Abierta, Herencia Dual y Arquitectura Holónica Recursiva

## Why

La ejecución de la Fase I (v1.0) demostró rigurosamente que una población de micro-agentes con memoria estrictamente acotada ($C_{\max} < |\mathcal{P}|$) e inmunidad epistémica distribuida logra superávit de decisión colectiva, memoria transaccional persistente ante ablación del $100\%$ de los descubridores originales y rechazo de desinformación ($C_3$ emergente con $p = 0.03125$). Sin embargo, también reveló un **techo estructural infranqueable**: en una población estática de agentes inmortales ($g=0$), donde las reglas comunicativas son fijas y ningún grupo de agentes puede consolidarse como unidad funcional de orden superior, la inteligencia colectiva queda confinada al Nivel 1 (vecindad efímera de un salto) y es clasificada por el marco de atribución como *programada por construcción* ($C_1, C_2, C_4$).

Para alcanzar una inteligencia distribuida genuinamente emergente y abierta (*open-ended evolution*), el sistema necesita incorporar los mecanismos de las **Grandes Transiciones Evolutivas** (Maynard Smith & Szathmáry) y la **Síntesis Evolutiva Extendida** (Simbiogénesis de Lynn Margulis, Causalidad Descendente de Denis Noble y Construcción de Nicho / Estigmergia): metabolismo energético con selección natural, reproducción diferencial con herencia genética y cultural vertical, e integración jerárquica recursiva ilimitada ($L = 0, 1, 2, \dots, K$) donde micro-agentes cooperativos formen holones (`CompositeAgent`) capaces de resolver problemas compuestos ($m > C_{\max}$), ortogonalizar sus memorias internas, reproducirse simbióticamente y componer nuevos niveles holónicos sin límite prefijado.

## What Changes

- **Metabolismo Energético y Selección Natural ($R_{12}$):**
  - Incorporación de energía interna $E_i(t) \in \mathbb{R}$, costo metabólico basal por tick $c_{\text{base}}(i) = c_{\text{fijo}} + c_{\text{mem}} \cdot C_{\max, i}^2$ (penalización cuadrática del cerebro individual que impide la hipertrofia solitaria y favorece la cooperación multicelular), costo por movimiento $c_{\text{move}}$ y costo por emisión comunicativa $c_{\text{msg}}$.
  - Muerte por agotamiento energético ($E_i(t) \le 0$) con liberación espacial inmediata, y reproducción diferencial ($E_i(t) \ge E_{\text{reprod}}$) con partición conservativa de energía ($\kappa_{\text{part}}$) sujeta a capacidad de carga ambiental $N_{\max}$.
- **Herencia Dual Intergeneracional ($g \to g+1$):**
  - **Herencia Genética con Mutación Acotada ($R_{13}$):** Nuevo dataclass inmutable `AgentGenome` que encapsula rasgos heredables ($\alpha, \gamma, \epsilon, \omega_{\text{bond}}, C_{\max}, r_{\text{perc}}, r_{\text{com}}$) con mutación gaussiana truncada / discreta controlada por un generador pseudoaleatorio dedicado (`evo_rng`) al reproducirse.
  - **Herencia Cultural Vertical ($R_{14}$):** Transferencia epigénica al nacer de hasta $\min(C_{\max, \text{hijo}}, |\mathcal{M}_{\text{padre}}|)$ creencias de mayor utilidad de la memoria materna/paterna con descuento intergeneracional $\gamma_{\text{gen}} \in [0, 1]$ e invariante `from_direct_experience = False` ($d=0, \tau = t_{\text{nac}}$).
- **Arquitectura Holónica y Jerarquía Recursiva Ilimitada ($L = 0, 1, 2, \dots, K$):**
  - **Protocolo `AgentNode` y clase `CompositeAgent` (Patrón *Composite*):** Tanto `MicroAgent` ($L=0$) como `CompositeAgent` ($L \ge 1$) implementan `AgentNode`. Un `CompositeAgent` agrupa un conjunto arbitrario de nodos hijos (`MicroAgent` o `CompositeAgent` de niveles inferiores), definiendo recursivamente su nivel $L(U) = 1 + \max_{c \in \text{children}(U)} L(c)$, su masa $|U| = \sum_c |c|$ y su memoria colectiva $\mathcal{M}_{\text{holon}}(U) = \bigcup_{\ell \in \text{leaves}(U)} \mathcal{M}_\ell$ sin límite de profundidad jerárquica.
  - **Fusión Simbiótica `BOND` ($R_{15}$) y Fisión `SPLIT` ($R_{16}$):** Operadores dinámicos en la Fase 5 del motor que ensamblan pares de nodos co-localizados cuya complementariedad epistémica de Jaccard y propensión $\omega_{\text{bond}}$ superan el umbral $\theta_{\text{sinergia}}$, y disuelven holones cuyo costo metabólico de coordinación $c_{\text{coord}}(U) = c_{\text{enlace}} \cdot |U| \cdot L(U)$ excede su superávit cooperativo o cuya energía agregada cae por debajo del umbral de viabilidad.
- **Pilares de la Síntesis Evolutiva Extendida:**
  - **Endosimbiosis Reproductiva Holónica ($R_{17}$, Margulis):** Reproducción directa de un `CompositeAgent` exitoso ($E_{\text{holon}}(U) \ge |U| \cdot E_{\text{reprod}}$) como unidad simbiótica ya ensamblada (`reproduce_holon`), clonando con mutación cada hoja y replicando la topología arbórea en un holón hijo $U_{\text{hijo}}$.
  - **Causalidad Descendente y Particionamiento Epigenético Intra-Holón ($R_{18}$, Noble):** Modulación descendente de la función de utilidad de memoria $U(k, t)$ de las hojas de un holón mediante el factor de penalización por redundancia $\psi_{\text{red}} \in (0, 1]$ cuando otro miembro del mismo holón ya posee el patrón $\rho$ con mayor confianza, induciendo ortogonalización espontánea de memorias ($\mathcal{M}_i \cap \mathcal{M}_j \to \emptyset$) y maximizando la capacidad efectiva $C_{\text{eff}}(U)$.
  - **Construcción de Nicho y Estigmergia Espacial ($R_{19}$):** Depósito y lectura de rastros epistémicos `StigmergicTrace` en las celdas de `ToroidalGrid2D` con decaimiento ambiental $\delta_{\text{suelo}}$ por tick.
- **Recursos Compuestos Graduados y Nuevos Protocolos Experimentales (002 y 003):**
  - Recursos compuestos (`CompositeRule`) de orden $m \in \{2, 3, \dots\}$ que exigen que el nodo consumidor (individuo u holón) conozca simultáneamente los $m$ patrones constituyentes para liberar un retorno energético superlineal $v_0 \cdot m^{\kappa_{\text{comp}}}$, proveyendo la presión selectiva ecológica para escalar a niveles $L=1, 2, \dots, K$.
  - Nuevas métricas poblacionales y multinivel `M8` a `M12` en `EvolutionaryTickMetrics`, extensión del catálogo de atribución a `R12`–`R19` y afirmaciones `C5`–`C8`, y runners reproducibles `exp002_runner.py` y `exp003_runner.py`.
- **Compatibilidad Regresiva Absoluta con Fase I:**
  - Todas las banderas de Fase II tienen valor por defecto `False` en `SimulationConfig`. Cuando están desactivadas, el motor, la grilla, los tipos de dominio, `TickMetrics` y el generador `rng` se comportan bit a bit igual que en la Fase I, preservando los 379 tests existentes y los hashes SHA-256 dorados.

## Capabilities

### New Capabilities
- `evolutionary-dynamics`: Metabolismo energético ($E_i(t)$), costo cuadrático de capacidad cerebral ($C_{\max}^2$), muerte por inanición, reproducción diferencial ($R_{12}$), genoma mutable `AgentGenome` ($R_{13}$) y herencia cultural vertical con descuento intergeneracional ($R_{14}$).
- `holonic-hierarchy`: Protocolo `AgentNode`, clase recursiva `CompositeAgent` para niveles arbitrarios $L = 0 \dots K$, memoria colectiva distribuida $\mathcal{M}_{\text{holon}}(U)$, operadores de fusión `BOND` ($R_{15}$) y fisión `SPLIT` ($R_{16}$), reproducción simbiótica de holones ($R_{17}$) y causalidad descendente intra-holón ($R_{18}$).

### Modified Capabilities
- `domain-contracts`: Incorporación en `SimulationConfig` de los hiperparámetros y banderas de Fase II (con defaults retrocompatibles `False`), nuevos tipos inmutables (`AgentGenome`, `CompositeRule`, `StigmergicTrace`, `HolonSnapshot`) y sub-puerto `EvolutionaryEnvironmentPort` (preservando intactos los 10 métodos de `EnvironmentPort` y los 5 campos de `VisibleResource`).
- `roadmap-extensions`: Evolución de `AgentCapabilities` y estrategias de similitud/sinergia para integrarse con `AgentGenome` y con la evaluación de fusión holónica.
- `bounded-memory`: Soporte opcional de penalización por redundancia intra-holón ($\psi_{\text{red}}$, $R_{18}$) en el cálculo de utilidad $U(k, t)$ y desalojo, manteniendo intacto el comportamiento por defecto ($\psi_{\text{red}} = 1.0$).
- `micro-agent`: Implementación del protocolo `AgentNode` ($L=0$), estado energético y de linaje (`energy`, `generation`, `parent_id`, `genome`), consumo de parámetros desde `genome` cuando la evolución está activa y método `create_offspring` de herencia dual.
- `spatial-environments`: Implementación de `EvolutionaryEnvironmentPort` en `ToroidalGrid2D` con soporte para inserción de descendientes (`spawn_agent_near`), recursos compuestos (`CompositeRule` de orden $m \ge 2$) y rastros estigmérgicos por celda (`StigmergicTrace`, $R_{19}$).
- `simulation-engine`: Extensión de la Fase 4 (resolución cooperativa de recursos compuestos por holones y depósito estigmérgico) y Fase 5 (metabolismo, causalidad descendente, `BOND`, `SPLIT`, muerte y reproducción individual/holónica usando `evo_rng` dedicado).
- `experimental-suite`: Nuevas métricas `M8` a `M12` en `EvolutionaryTickMetrics`, runners `exp002_runner.py` (Protocolos `002-A` y `002-B`) y `exp003_runner.py` (Protocolos `003-A` y `003-B`).
- `emergence-attribution`: Extensión del pre-registro con `PHASE2_DESIGN_RULES` (`R12`–`R19`), `ALL_DESIGN_RULES` y las afirmaciones de emergencia evolutiva y holónica `C5`–`C8` (`EXP002_CLAIMS` y `EXP003_CLAIMS`).

## Impact

- **Código afectado:**
  - `src/ide/config.py` (nuevos campos validados de Fase II con valores por defecto `False` que no alteran `SimulationConfig()` base en comportamiento).
  - `src/ide/domain/types.py`, `src/ide/domain/ports.py`, `src/ide/domain/extensions.py`.
  - `src/ide/agent/memory.py`, `src/ide/agent/micro_agent.py`, y nuevos módulos `src/ide/agent/evolution.py` y `src/ide/agent/holon.py`.
  - `src/ide/environments/grid2d.py`.
  - `src/ide/simulation/engine.py`.
  - `src/ide/experiments/metrics.py`, `src/ide/experiments/attribution.py`, y nuevos runners `src/ide/experiments/exp002_runner.py` y `src/ide/experiments/exp003_runner.py`.
- **Tests:** Nuevas suites de pruebas unitarias y basadas en propiedades (`tests/test_evolutionary_dynamics.py`, `tests/test_holonic_hierarchy.py`, `tests/test_exp002_exp003.py`) más ampliación de las suites existentes sin romper ninguno de los 379 tests de Fase I.
- **Dependencias:** Ninguna dependencia externa nueva (se mantiene el stack puro `numpy`, `pytest`, `hypothesis`, `ruff`, `pyright`).
