# Especificación de Definiciones Formales — Proyecto IDE (v2.0)

Este documento establece de manera rigurosa y sin ambigüedades qué significa cada concepto dentro del sistema de **Inteligencia Distribuida Emergente (IDE)** antes de escribir código. Toda implementación debe respetar estas definiciones.

> **Novedades en la Versión 2.0:** Esta versión conserva íntegramente las definiciones y métricas verificadas de la **Fase I (Experimento 001)** y extiende la ontología matemática hacia la **Fase II (Experimentos 002–003)**:
> 1. **Metabolismo, muerte y reproducción intergeneracional ($g \to g+1$).**
> 2. **Herencia Dual:** herencia genética con mutación sobre $\Theta_i$ y capacidades $\mathcal{G}_i$ + herencia cultural vertical de creencias $\mathcal{M}_{\text{padre}} \to \mathcal{M}_{\text{hijo}}$.
> 3. **Arquitectura Holónica / Jerarquía Recursiva ($L \in \mathbb{N}_0$):** formalización del **Holón** (`AgentNode`) mediante el patrón recursivo *Composite*, donde tanto un agente elemental ($L=0$) como una coalición de coaliciones de nivel arbitrario ($L = 1, 2, \dots, K$, sin tope de niveles codificado) exponen la misma interfaz estructural (`node_id`, `holon_level`, `leaf_agents`, `effective_capacity`, `collective_memory`). Percibir, decidir y actuar siguen siendo operaciones de las hojas ($L = 0$); los holones se forman y disuelven con los operadores `BOND` y `SPLIT`.

> **Estado (2026-10-21).** Fase I (Experimento 001): implementada, verificada y archivada. Fase II (Experimentos 002 y 003): implementada, corrida y archivada; sus resultados, negativos para C5–C8, están en [RESULTADOS.md](RESULTADOS.md). La Fase II-B (v2.5) está en implementación en el cambio activo [`openspec/changes/ide-v25-compact-dna-and-epigenetics/`](../openspec/changes/ide-v25-compact-dna-and-epigenetics/): su etapa A ($R_{24}$) está completa, y el 2026-10-20 se **reformuló** (design D43–D56) con conducta codificada en el ADN, ecología con interacciones y métricas de evolución abierta, y el 2026-10-21 se **amplió** (design D57–D63) con estado interno persistente, plasticidad en vida, señales evolucionables y un entorno cambiante. Su pre-registro vigente es el **borrador D56**, reabierto con la ampliación y pendiente de aprobación en la tarea 0.5; el pre-registro D42 quedó sustituido y sus afirmaciones C9–C12 se retiraron sin medir. Se refleja en este documento: su inventario $R_{24}$–$R_{41}$ y sus afirmaciones C13–C20 en §3.1, y su modelo genético, conductual y ecológico en §9. Para sus valores rige el `design.md` de ese cambio (Decisiones D30–D63 y sus "Precisiones"; D43–D63 prevalecen donde contradicen a las anteriores), que es la fuente única de sus fórmulas, nombres, valores por defecto y desempates.

> **Relación con los demás documentos.** La visión está en el [Documento Fundacional](DOCUMENTO_FUNDACIONAL.md) y la arquitectura en las [Definiciones Técnicas](DEFINICIONES_TECNICAS.md). Los requisitos vigentes de la Fase I están en [`openspec/specs/`](../openspec/specs/), y sus valores numéricos, firmas y reglas de desempate exactos, en el diseño archivado [`design.md`](../openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/design.md) (Decisiones D1–D18). Los requisitos vigentes de la Fase II también están sincronizados en [`openspec/specs/`](../openspec/specs/), y para sus valores rige el diseño archivado [`openspec/changes/archive/2026-10-20-ide-v2-evolutionary-holonic-intelligence/design.md`](../openspec/changes/archive/2026-10-20-ide-v2-evolutionary-holonic-intelligence/design.md) (Decisiones D19–D29), que es la fuente única de sus fórmulas, nombres, valores por defecto y desempates: §6–§8 lo resumen y, ante una discrepancia, rige el design. Los valores que aparecen aquí como "ej." son ilustrativos.

> **Numeración de experimentos (v2).** 001 memoria (completado), 002 evolución y herencia, 003 holones y composición, 004 especialización, 005 shock ambiental (cambio del mundo), 006 protocolo emergente. Correspondencia con la numeración v1, que todavía aparece en documentos y docstrings anteriores: v1 002 (confianza por emisor) no tiene experimento asignado en v2; v1 003 (especialización) → v2 004; v1 004 (cambio del mundo) → v2 005; v1 005 (recursos compuestos) → v2 003; v1 006 (evolución) → v2 002; v1 007 (protocolo) → v2 006.

---

## 1. Definiciones Ontológicas (Qué existe en el sistema)

### 1.1. Tiempo ($t$) y Generaciones ($g$)
El sistema evoluciona en pasos de tiempo discretos (ticks):
$$t \in \{0, 1, 2, \dots, T\}$$
En cada paso $t$, todos los agentes (o nodos holónicos activos) perciben, se comunican, deciden, actúan, metabolizan y aprenden de forma local (ver §2 y §6), sin un coordinador que dirija sus estrategias. El tick es un reloj de simulación, no una entidad cognitiva. Dentro de un tick, la percepción, la comunicación y la decisión son **simultáneas**; los conflictos físicos (dos agentes que intentan consumir el mismo recurso) se resuelven por sorteo. Ninguna de las dos idealizaciones, reloj sincrónico o actualización secuencial, es más realista que la otra: una comunidad real es asíncrona. Por eso ninguna propiedad emergente puede depender del esquema de actualización (criterio E5, §3.1).

Además del tiempo de reloj $t$, cada agente posee un **índice generacional** $g_i \in \mathbb{N}_0$:
- La población fundadora en $t=0$ tiene $g_i = 0$.
- Todo agente nacido por reproducción de un progenitor $p$ en el instante $t > 0$ recibe $g_{\text{hijo}} = g_p + 1$. (La reproducción biparental está fuera del alcance de la Fase II actual.)

---

### 1.2. Espacio y Entorno ($\mathcal{E}$)
El **Entorno** es el contenedor abstracto donde habitan los agentes y existen los recursos. Para garantizar que el sistema pueda escalar de una grilla 2D a espacios continuos, grafos complejos o entornos 3D, el entorno se define únicamente por **tres relaciones espaciales**:

1. **Conjunto de Ubicaciones ($\mathcal{L}$):** Donde puede estar un agente o un recurso.
   - *En Grilla 2D Toroidal:* $\mathcal{L} = \{0, \dots, W-1\} \times \{0, \dots, H-1\}$, donde las coordenadas hacen *wrap-around* ($\pmod W, \pmod H$).
   - *En Grafo Espacial (futuro):* $\mathcal{L} = V$ (nodos de un grafo $G=(V, E)$).
   - *En Espacio Continuo (futuro):* $\mathcal{L} = \mathbb{R}^d$.
2. **Vecindad de Percepción ($\mathcal{N}_{\text{perc}}(l, r_{\text{perc}})$):** El conjunto de ubicaciones que un agente situado en $l \in \mathcal{L}$ con radio perceptual $r_{\text{perc}}$ puede observar directamente.
3. **Vecindad de Comunicación ($\mathcal{N}_{\text{com}}(l, r_{\text{com}})$):** El conjunto de agentes con los que un agente situado en $l \in \mathcal{L}$ con alcance $r_{\text{com}}$ puede intercambiar mensajes en el instante $t$.

> **Regla de Oro de Escalabilidad:** Ningún agente conoce las coordenadas globales del mapa ni su tamaño total. El agente sólo recibe lo que hay dentro de $\mathcal{N}_{\text{perc}}$ y $\mathcal{N}_{\text{com}}$.

---

### 1.3. Recurso ($r$), Recursos Compuestos y Regla del Mundo ($F$)
Un **Recurso** es una entidad presente en el entorno con la que un agente o meta-agente puede interactuar (consumir/recolectar o evitar).

#### 1.3.1. Recursos Elementales (Orden $m = 1$)
Cada recurso elemental $r$ posee dos partes (en el Experimento 001, $v(r) \in \{+1.0, -1.0\}$):
1. **Rasgos Observables ($\mathbf{x}_r$):** Un conjunto de atributos discretos visibles antes de interactuar con él.
   - Ejemplo: $\mathbf{x}_r = (\text{color}, \text{forma}, \text{textura})$.
2. **Consecuencia Real ($v(r) \in \mathbb{R}$):** El efecto real sobre el agente (ej. $+1.0$ si es nutritivo, $-1.0$ si es venenoso).
   - **Restricción:** $v(r)$ es **invisible** a simple vista. El agente sólo descubre $v(r)$ de manera directa si interactúa con el recurso (pagando el costo o recibiendo el beneficio), o de manera indirecta si otro agente se lo comunica.

La **Regla del Mundo** $F(\mathbf{x}_r) \to v(r)$ es el conjunto de leyes que asocia patrones observables con sus consecuencias. Existen $N$ patrones elementales distintos en el entorno:
$$\mathcal{P}_{\text{mundo}} = \{P_1, P_2, \dots, P_N\}$$
Resolver el entorno elemental significa conocer la consecuencia asociada a los $N$ patrones.

#### 1.3.2. Recursos Compuestos Graduados (Orden $m \ge 2$, Fase II)
Para crear una presión selectiva hacia la cooperación en niveles jerárquicos superiores ($L \ge 1$), el entorno de Fase II puede incluir **Recursos Compuestos** (`CompositeRule`, design D27) de un **único orden $m$** = `composite_order` ($m \ge 2$, por defecto $2$). Sea $B = \lfloor N/2 \rfloor$ el número de patrones benéficos $p_0, \dots, p_{B-1}$; la configuración exige $m \le B$ (si no, `SimulationConfig` lanza `ValueError`). Para cada $k \in \{0, \dots, n_{\text{comp}} - 1\}$, con $n_{\text{comp}}$ = `num_composite_patterns` (por defecto $0$: sin compuestos), el patrón compuesto $\rho^{c}_k$ exige el conjunto ordenado
$$\Sigma_k = \{p_{(k + j) \bmod B} : j = 0, \dots, m - 1\} \subseteq \mathcal{P}_{\text{mundo}}$$
y cada uno se instancia en `composite_resources_per_pattern` recursos físicos ubicados y repuestos con un generador dedicado.
- **Valor superlineal:** el valor del recurso compuesto es
  $$v(\rho^{c}_k) = m^{\kappa_{\text{comp}}}, \qquad \kappa_{\text{comp}} = \texttt{composite\_reward\_exponent} \;(1.5 \text{ por defecto})$$
  sin factor de escala adicional; en la energía se multiplica por $\eta_E$ (§6.1). Las creencias siguen viviendo en $\hat{v} \in [-1, 1]$: el valor superlineal sólo se refleja en la energía. Los órdenes posibles en un mundo dado son los $m$ con $2 \le m \le N/2$.
- **Condición de resolución (física del entorno):** cuando la hoja $a$ ejecuta `INTERACT` sobre un recurso compuesto, sea $\mathcal{K}_{\text{eff}}$ el conjunto de patrones $\rho$ para los que alguna hoja en alcance local de $a$ dentro de su holón raíz $U$ (§7.2), o sólo $a$ si no pertenece a un holón, sostiene como creencia propia (`own_belief`: su memoria o su caché efímero del tick, que incluye lo que obtuvo de sus vecinos) una creencia con $\hat{v} > 0$ y $c \ge c_{\text{umbral}}$. El intento tiene éxito si y sólo si $\Sigma_k \subseteq \mathcal{K}_{\text{eff}}$. $\mathcal{K}_{\text{eff}}$ y el alcance local se evalúan con el estado al empezar la Fase 4 (posiciones y creencias tras la decisión), para que el orden de ejecución de la Fase 4 no altere el resultado. Esta condición se aplica aunque la vista compartida del holón ($R_{22}$, §7.2) esté apagada: es una propiedad declarada del entorno diseñado ("el recurso se libera si el grupo local conoce los fragmentos"), como `true_value`, y no un canal de conocimiento hacia el agente. Por eso no tiene regla en el inventario (§3.1): el agente no la recibe, la aprende.
  - **Éxito:** el agente aprende el patrón compuesto con valor experimentado $+1.0$ (§2.1) y se incrementa el contador M12; si $U$ es un holón compuesto, registra superávit en el tick (§7.2). Con evolución activa, la ganancia $\eta_E \cdot m^{\kappa_{\text{comp}}}$ se reparte en partes iguales entre las hojas de $U$ en alcance local ($R_{23}$, §7.2); con `holon_energy_sharing=False`, o fuera de un holón, va entera a $a$. El éxito no convierte a $a$ en descubridor directo (que sólo rastrea patrones elementales) ni deposita rastro estigmérgico.
  - **Fracaso:** el agente aprende el patrón compuesto con valor experimentado $r = -$`composite_failure_penalty` ($\in [-1, 0]$; penalización por defecto $0.20$) y no se registra éxito. Con evolución activa, ese valor le cuesta energía sólo a $a$ (§6.1).
- **Límite individual para $m > C_{\max}$:** un agente sin holón sólo cuenta con su memoria ($\le C_{\max}$ creencias) y con lo que obtuvo en el caché efímero de ese tick. Sin holón ni consultas en el tick, no puede resolver un recurso compuesto de orden $m > C_{\max}$.
- **Aprendizaje por experiencia:** el motor **no** le entrega al agente ningún patrón compuesto ni lee la estructura de `CompositeRule` para informarlo. Para el agente, un recurso compuesto es un recurso más, con su propio patrón $\rho^{c}_k$: lo percibe como `VisibleResource`, lo explora con $\epsilon$ como a cualquier patrón desconocido, lo consulta y lo difunde con el protocolo, y aprende su valor por experiencia directa. Sólo el motor conoce `CompositeRule`, y sólo para resolver la interacción en la Fase 4. El valor que aprende el agente **no es estacionario**: el mismo recurso paga o castiga según lo que sepa su grupo local en ese tick. Es una propiedad declarada del entorno, no un defecto: un individuo solo tenderá a aprender que $\rho^{c}_k$ es dañino, y si los holones superan esa trampa es parte de lo que se mide.
- **M2:** por objetividad, los recursos compuestos **no entran** en M2, que se calcula sólo sobre recursos elementales (§8).
- **Alcance frente al shock ambiental (decisión del 2026-10-19):** el valor $m^{\kappa_{\text{comp}}}$ de un recurso compuesto es fijo. `invert_world_rules` sólo invierte los patrones elementales del mundo, de modo que un compuesto sigue pagando aunque alguno de sus fragmentos requeridos haya pasado a ser dañino. Combinar recursos compuestos con el shock ambiental (Experimento 005) queda **fuera del alcance** de los Experimentos 002 y 003; si el 005 lo necesita, se decide en su propio cambio, con su propio pre-registro.

---

### 1.4. Unidad de Conocimiento / Creencia ($k$)
El conocimiento no es texto libre; es una estructura de datos atómica llamada **Creencia** (*Belief*).

Una creencia $k$ se define formalmente como una tupla de 6 elementos:
$$k = (\rho, \hat{v}, c, n, \tau, d)$$

Donde:
- **$\rho$ (Patrón / Condición):** El rasgo o combinación de rasgos observables a los que aplica la regla (ej. `Color == Azul` o `Color == Rojo AND Forma == Círculo`).
- **$\hat{v} \in \mathbb{R}$ (Predicción de Valor):** El efecto esperado al interactuar con un recurso que cumple $\rho$ (ej. $+1.0$ benéfico, $-1.0$ dañino).
- **$c \in [0, 1]$ (Confianza Epistémica):** Grado de certidumbre que el agente asigna a esta creencia ($0 = \text{nula}$, $1 = \text{certeza total}$).
- **$n \in \mathbb{N}$ (Evidencia Acumulada):** Cantidad de observaciones o confirmaciones que respaldan la creencia.
- **$\tau \in \mathbb{N}$ (Última Validación):** Paso temporal $t$ de la última vez que esta creencia fue confirmada por experiencia directa o por el consenso de un emisor con evidencia directa, o adoptada. Ni la duda social (§2.3, Escenario C) ni el consenso entre rumores actualizan $\tau$: un rumor no valida a otro rumor.
- **$d \in \{0, 1\}$ (Origen Empírico):** $d = 1$ si el propio agente experimentó directamente el patrón; $d = 0$ si la creencia proviene sólo de testimonios (horizontales o heredados verticalmente de un progenitor). Es la base de la protección anti-cámara de eco (§2.3).

---

### 1.5. Memoria Limitada del Agente ($\mathcal{M}_i$)
Cada agente elemental $a_i$ posee una memoria local $\mathcal{M}_i$ compuesta por una lista de creencias:
$$\mathcal{M}_i(t) = \{k_1, k_2, \dots, k_m\}, \quad \text{con } m \le C_{\max, i}$$

- **$C_{\max, i}$ (Capacidad de Memoria Individual):** Número máximo de creencias que el agente $a_i$ puede almacenar simultáneamente (en Fase I es constante $C_{\max}$ para todos; en Fase II puede mutar entre generaciones, sujeto a un costo metabólico cuadrático en $C_{\max, i}$, regla $R_{21}$, §6.1).
- **Restricción Crítica del Proyecto:**
  $$C_{\max, i} \ll N$$
  Donde $N$ es la cantidad total de patrones del mundo $\mathcal{P}_{\text{mundo}}$.
  *Ejemplo:* Si en el mundo existen $N = 12$ tipos de recursos distintos, y cada agente tiene capacidad $C_{\max} = 3$, ningún agente elemental puede almacenar más del $25\%$ del conocimiento del mundo.

---

### 1.6. Agente Mínimo ($a_i$, Nivel $L = 0$)
Un agente elemental (hoja de la jerarquía holónica, $L=0$) es una unidad autónoma caracterizada en el instante $t$ por:
$$a_i(t) = \langle \text{id}_i, l_i(t), E_i(t), \mathcal{M}_i(t), \Theta_i, \mathcal{G}_i, \mathcal{H}_i \rangle$$

1. **Identificador ($\text{id}_i$):** Único para trazabilidad de métricas y genealogía (no usado para privilegios jerárquicos).
2. **Ubicación actual ($l_i(t) \in \mathcal{L}$):** Posición en el entorno.
3. **Estado Interno / Energía ($E_i(t) \in \mathbb{R}$):** Nivel de energía metabólica acumulada. Si un agente consume recursos beneficiosos, $E_i$ sube; si consume recursos dañinos o paga costos metabólicos, $E_i$ baja. *En el Experimento 001 (Fase I) $E_i$ no se modela: no afecta la supervivencia ni la decisión, y el desempeño se mide sólo con la calidad de las decisiones (M2). En la Fase II (§6), $E_i(t)$ gobierna la supervivencia (el agente muere si $E_i \le 0$ tras el cobro metabólico) y la reproducción ($E_i \ge E_{\text{reprod}}$); no tiene tope superior.*
4. **Memoria Local ($\mathcal{M}_i(t)$):** Sujeta a $|\mathcal{M}_i(t)| \le C_{\max, i}$.
5. **Parámetros Cognitivos Locales ($\Theta_i$):** Tasas de aprendizaje ($\alpha_i$), factor de descuento de confianza social ($\gamma_i$), tasa de exploración ($\epsilon_i$), propensión a cooperar/fusionarse ($\omega_{\text{bond}, i}$).
6. **Capacidades Físicas ($\mathcal{G}_i$):** Tupla $(C_{\max, i}, r_{\text{perc}, i}, r_{\text{com}, i})$. En Fase I son homogéneas para toda la población; en Fase II forman parte del genoma heredable (`AgentGenome`) con costo metabólico cuadrático ($R_{21}$, §6.1).
7. **Registro de Linaje ($\mathcal{H}_i$):** Par $(\text{parent\_id}_i, g_i)$ que registra el progenitor (`None` en los fundadores) y el número de generación $g_i \in \mathbb{N}_0$. (El design de Fase II no almacena el tick de nacimiento $t_{\text{nac}, i}$ en el agente.)

---

## 2. Dinámica Cognitiva y Reglas de Interacción (Fase I Base)

En cada ciclo $t$, cada agente ejecuta procesos estrictamente locales en este orden: **(1)** percibir, **(2)** comunicarse (consultar, responder, difundir y revalidar), **(3)** decidir, **(4)** actuar y aprender por experiencia directa, y **(5)** olvidar (decaimiento pasivo). En Fase II, la Fase 5 del motor añade el cobro de coordinación y metabolismo, la causalidad descendente, la reconfiguración holónica (`SPLIT`/`BOND`), la muerte y la reproducción (§6 y §7; design D21–D26). La comunicación ocurre **antes** de decidir para que la consulta en vivo (§2.4) pueda informar la decisión del mismo tick. Las subsecciones siguientes describen cada regla, no el orden.

### 2.1. Aprendizaje Individual (Por Experiencia Directa)
Cuando el agente $a_i$ interactúa directamente con un recurso $r$ de patrón $\rho$ y recibe la consecuencia real $v$:

1. **Si $\rho$ NO está en $\mathcal{M}_i$:**
   Crea una nueva creencia con alta confianza inicial (porque la vivió en carne propia):
   $$k_{\text{nuevo}} = (\rho, \hat{v} = v, c = c_{\text{directa}}, n = 1, \tau = t, d = 1)$$
   *(donde típicamente $c_{\text{directa}} \approx 0.85$).*
2. **Si $\rho$ YA está en $\mathcal{M}_i$:**
   Actualiza el valor predicho y ajusta la confianza según si la experiencia confirmó o contradijo su creencia previa:
   - Actualización de valor:
     $$\hat{v}_{\text{nuevo}} = (1 - \alpha) \hat{v}_{\text{prev}} + \alpha v$$
   - Si el signo/magnitud de $v$ coincide con $\hat{v}_{\text{prev}}$ (Confirmación):
     $$c_{\text{nuevo}} = \min\left(1.0, \; c_{\text{prev}} + \beta_{\text{refuerzo}} (1 - c_{\text{prev}})\right)$$
   - Si $v$ contradice a $\hat{v}_{\text{prev}}$ (Refutación empírica), sea $c' = c_{\text{prev}} - \beta_{\text{castigo}}$:
     - Si $c' < c_{\text{umbral}}$, la creencia se **reinicia** al valor experimentado: $k = (\rho, v, c_{\text{directa}}, 1, t, 1)$.
     - Si no, conserva temporalmente su signo con confianza $c'$ y magnitud $\max(0.05, |(1-\alpha)\hat{v}_{\text{prev}} + \alpha v|)$.
     *(La experiencia directa tiene prioridad para destruir creencias falsas).*
   - En todos los casos la creencia resultante tiene $d = 1$.

---

### 2.2. Política de Gestión de Memoria (Olvido y Reemplazo)
¿Qué ocurre si $|\mathcal{M}_i| = C_{\max}$ y el agente necesita guardar una creencia nueva $k_{\text{nueva}}$?

Cada creencia $k \in \mathcal{M}_i$ tiene un **Índice de Retención (Utilidad Epistémica)**:
$$U(k, t) = c \cdot \text{relevancia}(|\hat{v}|) \cdot e^{-\lambda (t - \tau)}, \qquad \text{relevancia}(x) = \max(x, 0.1)$$
(El piso $0.1$ evita que una creencia de valor predicho cercano a cero tenga utilidad nula.)
- Creencias con mayor confianza ($c$), que advierten de grandes peligros o grandes beneficios ($|\hat{v}|$ alto) y que han sido usadas o validadas recientemente ($t - \tau$ bajo) tienen mayor $U(k, t)$.
- Si $U(k_{\text{nueva}}, t) > \min_{k \in \mathcal{M}_i} U(k, t)$ (estrictamente), reemplaza a la creencia de menor utilidad; los empates se resuelven por menor $\tau$ y, de persistir, por el orden canónico de $\rho$.
- La experiencia directa (§2.1) siempre se retiene, aunque su utilidad no supere el mínimo (prioridad empírica).
- Además, en cada paso de tiempo sin validación, la confianza sufre un decaimiento pasivo leve ($\delta_{\text{olvido}}$) para evitar que datos obsoletos o falsos no verificados ocupen memoria eternamente. Si la confianza cae por debajo de $c_{\min}$, la creencia se olvida.

---

### 2.3. Comunicación Local y Epistemología Social (Revalidación)
Cuando dos agentes $a_i$ (emisor) y $a_j$ (receptor) están dentro de su vecindad de comunicación ($a_j \in \mathcal{N}_{\text{com}}(l_i)$):

El emisor $a_i$ transmite una creencia $k_{\text{ext}} = (\rho, \hat{v}_{\text{ext}}, c_{\text{ext}}, n_{\text{ext}}, \tau, d_{\text{ext}})$ seleccionada de su memoria: la de mayor utilidad $U$ entre las que alcanzan o superan $c_{\text{umbral}}$ (difusión espontánea), o la que le fue consultada (§2.4).

El receptor $a_j$ evalúa $k_{\text{ext}}$ bajo tres escenarios posibles:

#### Escenario A: Patrón desconocido ($\rho \notin \mathcal{M}_j$)
El receptor no sabe nada sobre $\rho$. Adopta la creencia pero aplicando un **descuento por testimonio indirecto** ($\gamma \in (0, 1]$, donde $\gamma = 1$ sólo se usa para ablacionar la regla; ej. $\gamma = 0.75$):
$$c_{\text{recibida}} = \max\left(0,\; \min\left(1,\; \varphi \cdot c_{\text{ext}}\right)\right)$$
donde $\varphi$ es el **factor de confianza en el emisor**. En el Exp 001, $\varphi = \gamma$ para todo emisor, así que el recorte nunca actúa y $c_{\text{recibida}} = \gamma \cdot c_{\text{ext}}$. Una estrategia de confianza por emisor (extensión de confianza por emisor, contrato `TrustStrategyPort`, sin experimento asignado en v2) puede asignar otro $\varphi$, incluso mayor que 1; el recorte mantiene la confianza en $[0, 1]$. En las fórmulas siguientes, $\gamma c_{\text{ext}}$ abrevia $c_{\text{recibida}}$.
*(Un rumor nunca tiene la misma fuerza inicial que haberlo vivido directamente; cada salto de boca en boca sin verificación empírica atenúa la confianza).*

#### Escenario B: Consenso ($\rho \in \mathcal{M}_j$ y $\text{sign}(\hat{v}_j) == \text{sign}(\hat{v}_{\text{ext}})$)
Ambos agentes coinciden. El receptor promedia la estimación ponderada por confianza:
$$\hat{v}_j \leftarrow \frac{c_j \hat{v}_j + (\gamma c_{\text{ext}}) \hat{v}_{\text{ext}}}{c_j + \gamma c_{\text{ext}}}$$
y refuerza moderadamente su confianza:
$$c^{*} = c_j + \eta_{\text{consenso}} \cdot \gamma c_{\text{ext}} (1 - c_j)$$
- Si el emisor tiene evidencia directa ($d_{\text{ext}} = 1$): $c_j \leftarrow \min(1.0, c^{*})$.
- Si el emisor sólo transmite un rumor ($d_{\text{ext}} = 0$): $c_j \leftarrow \min\left(\max(c_j, \gamma c_{\text{ext}}),\; c^{*}\right)$, y $\tau_j$ **no** se actualiza.

*(Protección anti-cámara de eco: sin la segunda regla, dos agentes que sólo tienen el mismo rumor podrían rebotárselo hasta $c \to 1$ sin ninguna evidencia física; y si el rebote refrescara $\tau$, quedarían exentos del olvido para siempre. La cota $\max(c_j, \gamma c_{\text{ext}})$ sólo impide que la confianza de la población crezca si $\varphi \le 1$.)*

> **Riesgo declarado (extensión de confianza por emisor).** Con $\varphi > 1$, la cota deja de proteger: dos portadores del mismo rumor que se asignan $\varphi > 1$ se lo rebotan hasta $c \to 1$ sin ninguna evidencia física, aunque $\tau$ siga sin refrescarse. Una estrategia de confianza que asigne $\varphi > 1$ equivale a una ablación parcial de R6 y debe declararse como tal en el diseño de ese experimento.

Las fórmulas de los tres escenarios suponen que $k_j$ y $k_{\text{ext}}$ se refieren al mismo patrón $\rho$; fusionar creencias sobre patrones distintos es un error.

#### Escenario C: Conflicto Epistémico ($\rho \in \mathcal{M}_j$ y $\text{sign}(\hat{v}_j) \neq \text{sign}(\hat{v}_{\text{ext}})$)
El vecino afirma que el recurso es bueno, pero el receptor cree que es malo (o viceversa).
- **Sustitución:** si la creencia propia es un rumor ($d_j = 0$) y el testimonio es claramente más fuerte ($\gamma c_{\text{ext}} > 1.2\, c_j$), el receptor la reemplaza por la del emisor:
  $$k_j \leftarrow \left(\rho, \hat{v}_{\text{ext}}, \max(c_{\min}, \gamma c_{\text{ext}} - 0.5\, c_j), 1, t, 0\right)$$
- **Resistencia:** en cualquier otro caso conserva su valor y reduce su certeza por la duda, con resistencia $r = 2$ si su creencia es empírica ($d_j = 1$) y $r = 1$ si no:
  $$c_j \leftarrow \max\left(0,\; c_j - \frac{\eta_{\text{duda}}\, \gamma c_{\text{ext}}}{r}\right)$$
  La duda no actualiza $\tau$.

---

### 2.4. Cómo Funciona la Memoria Colectiva en Tiempo Real (Consulta y Acción)
Si un agente $a_i$ se encuentra frente a un recurso $r$ con patrón $\rho$, ¿cómo toma la decisión si su memoria individual es $C_{\max} \ll N$ y **no recuerda** $\rho$ en ese instante?

Existen **dos mecanismos complementarios**, ambos **diseñados** (reglas R9 y R8 de §3.1), que producen el acceso colectivo al conocimiento:

1. **Difusión Continua y Recambio Adaptativo:**
   Los agentes intercambian creencias constantemente al cruzarse. Las creencias verdaderas son revalidadas una y otra vez por distintos agentes que interactúan con el entorno, manteniendo su confianza $c$ alta en la población, mientras que las falsas chocan con la experiencia empírica y se extinguen.
2. **Consulta Local en Vivo (*Collective Query / Micro-Grupos*):**
   Cuando el agente $a_i$ observa un recurso con patrón $\rho \notin \mathcal{M}_i$, puede emitir una **consulta local** (`QUERY(ρ)`) a sus vecinos inmediatos en $\mathcal{N}_{\text{com}}(l_i)$.
   - Si algún vecino $a_k \in \mathcal{N}_{\text{com}}(l_i)$ posee $\rho$ en su memoria $\mathcal{M}_k$, responde inmediatamente con su creencia $k$, tal como la sostenía antes de procesar los demás mensajes del tick: en el esquema sincrónico, el orden en que llegan los mensajes no altera la respuesta.
   - De este modo, un grupo de $G$ agentes cercanos con memorias disjuntas de tamaño $C_{\max}$ actúa efectivamente como un **meta-agente efímero con memoria combinada de hasta $G \times C_{\max}$**, sin que ningún individuo haya ampliado su hardware interno.

> **Advertencia de atribución.** El meta-agente efímero de nivel 0 es una consecuencia **directa y buscada** de la consulta en vivo: la regla existe para producirlo. Observarlo valida el mecanismo, pero no constituye emergencia (§3.1). El protocolo de mensajes (`QUERY`, `RESPONSE`, `BROADCAST`) tiene semántica predefinida; su des-programación progresiva es un eje del programa de investigación ([Documento Fundacional](DOCUMENTO_FUNDACIONAL.md) §7, "Eje transversal"; el criterio epistemológico está en su §9).

---

## 3. Definiciones Operacionales de Fenómenos Colectivos

Para que el proyecto tenga rigor científico, no usaremos palabras vagas. Cada fenómeno se define operacionalmente así. Que un fenómeno colectivo aparezca **no** lo convierte en emergente: eso lo decide el criterio de atribución (§3.1).

| Concepto | Definición Operacional Exacta |
| :--- | :--- |
| **Conocimiento Individual** | Conjunto de patrones $\rho$ en $\mathcal{M}_i(t)$ cuyo signo predicho $\text{sign}(\hat{v})$ coincide con la realidad $\text{sign}(F(\rho))$ y cuya confianza supera el umbral de decisión ($c \ge c_{\text{umbral}}$). |
| **Conocimiento Colectivo (Poblacional)** | Unión de los conocimientos válidos presentes en al menos un agente activo ($p_{\min} = 1/M$). |
| **Conocimiento Accesible** | Para un agente, unión de su conocimiento individual y el de sus vecinos de comunicación a $d = 1$ salto en el instante $t$. Es lo que puede usar para decidir mediante una consulta en vivo. |
| **Superávit Cognitivo Colectivo ($\Delta_{\text{col}}$)** | Diferencia entre el rendimiento (precisión $Acc$, M2) de la población conectada y el de una población idéntica sin comunicación, con las mismas condiciones iniciales: $\Delta_{\text{col}} = Acc_{\text{col}} - Acc_{\text{iso}}$. Un $\Delta_{\text{col}} > 0$ consistente entre semillas demuestra que la población supera el límite de sus partes; si ese superávit es emergente o programado lo decide §3.1. La cota teórica individual $C_{\max}/N$ se usa en cambio para la cobertura (M1). |
| **Epistemología Distribuida (Inmunidad a Falsedad)** | Capacidad de la red para hacer que la prevalencia de una creencia falsa inyectada ($F(\rho) \neq \hat{v}_{\text{falso}}$) tienda a $0$ cuando $t \to \infty$ sin intervención externa. |
| **Memoria Colectiva Persistente** | Condición en la cual una creencia verdadera descubierta en $t_0$ por un subconjunto de agentes $S_0$ sigue activa en la población en $t_1 \gg t_0$ después de que el $100\%$ de los agentes originales de $S_0$ han sido eliminados o han olvidado el dato. |
| **Adaptación Evolutiva Intergeneracional (Fase II)** | Diferencia de precisión acumulada (M2) entre una población con mutación genética activa y otra idéntica con el genoma congelado (protocolo 002-A, `adaptation_gain` = `evolved_accuracy` − `frozen_genome_accuracy`), con las mismas condiciones iniciales. La parte atribuible a la selección se separa de la deriva con el control de reproducción neutral (`selection_gain` = `evolved_accuracy` − `drift_accuracy`, §6.1 y §8). |
| **Holón / Meta-Agente de Nivel $L$ (Fase II)** | Nodo `CompositeAgent` formado por la regla `BOND` ($R_{15}$) a partir de $\ge 2$ sub-nodos de nivel $\le L-1$ con hojas disjuntas. Sus hojas reparten el costo de coordinación y las ganancias de los recursos compuestos que resuelven ($R_{23}$), ven el conocimiento de las hojas cercanas del holón ($R_{22}$), y su capacidad efectiva es $C_{\text{eff}}(U) = \sum_{\ell \in \text{leaves}(U)} C_{\max, \ell}$ (§7). |

### 3.1. Atribución de Emergencia

**Regla central:** *toda propiedad que se afirme como emergente debe poder distinguirse de una capacidad programada explícitamente en el agente.*

**Presupuestos de diseño (Fase I: $R_1 \dots R_{11}$; Fase II añade $R_{12} \dots R_{23}$; Fase II-B añade $R_{24} \dots R_{41}$).** Sea $\mathcal{R}$ el conjunto de reglas diseñadas del agente, cada una con un **propósito declarado**. Las reglas $R_1$ y $R_2$ son nucleares: no se ablacionan (en la Fase II, también $R_{20}$).

| Regla | Fase | Descripción | Propósito declarado |
| :--- | :---: | :--- | :--- |
| $R_1$ | I | Aprendizaje por experiencia directa (§2.1) | Aprender del entorno |
| $R_2$ | I | Memoria acotada con reemplazo por utilidad (§2.2) | Restricción experimental $C_{\max} < N$ |
| $R_3$ | I | Olvido pasivo $\delta$ (§2.2) | Eliminar lo no revalidado |
| $R_4$ | I | Descuento por testimonio $\gamma$ (§2.3 A) | Atenuar rumores |
| $R_5$ | I | Refuerzo por consenso $\eta_{\text{consenso}}$ (§2.3 B) | Consolidar acuerdos |
| $R_6$ | I | Protección anti-cámara de eco (§2.3 B) | Impedir certeza sin evidencia |
| $R_7$ | I | Duda ante contradicción $\eta_{\text{duda}}$ (§2.3 C) | Filtrar testimonios falsos |
| $R_8$ | I | Consulta en vivo (§2.4) | Acceder a memoria ajena (meta-agente) |
| $R_9$ | I | Difusión espontánea (§2.4) | Transmitir conocimiento |
| $R_{10}$ | I | Exploración $\epsilon$ | Descubrir lo desconocido |
| $R_{11}$ | I | Navegación hacia benéficos conocidos | Buscar alimento |

**Inventario de Fase II (`PHASE2_DESIGN_RULES`, design D29, pre-registro versionado).** Cada regla lleva su propósito declarado (la capacidad que se diseñó para producir) y su ablación (los parámetros de `SimulationConfig` que la desactivan; `()` marca una regla nuclear, como $R_1$ y $R_2$). `DESIGN_RULES` conserva sólo $R_1 \dots R_{11}$; `ALL_DESIGN_RULES = DESIGN_RULES + PHASE2_DESIGN_RULES`, y `ablate()` opera sobre cualquier regla ablacionable de `ALL_DESIGN_RULES`.

| Regla | Descripción (`name`) | Propósito declarado (`purpose`) | Ablación (`ablation`) |
| :--- | :--- | :--- | :--- |
| $R_{12}$ | Reproducción diferencial por energía (§6.1) | Que los agentes con más energía dejen más descendencia (selección). | `(("reproduction_mode", "neutral"),)`: misma demografía, genoma del hijo tomado de un donante al azar (§6.1, reproducción neutral). Es también el control de deriva de C6. |
| $R_{13}$ | Mutación genética acotada (§6.2) | Variación heredable sobre la que actúa la selección. | `(("mutation_rate", 0.0), ("discrete_mutation_prob", 0.0))` |
| $R_{14}$ | Herencia cultural vertical (§6.3) | Transmitir conocimiento de padres a hijos. | `(("enable_cultural_inheritance", False), ("inheritance_discount", 0.0))` |
| $R_{15}$ | Fusión holónica (BOND) (§7.3) | Asociar nodos complementarios en unidades de nivel superior. | `(("enable_holonic_hierarchy", False),)`. Apagarla deja inertes $R_{16}$, $R_{17}$, $R_{18}$, $R_{22}$ y $R_{23}$. |
| $R_{16}$ | Fisión holónica (SPLIT) (§7.3) | Disolver holones sin superávit. | `(("enable_holon_splitting", False),)` |
| $R_{17}$ | Reproducción de holón completo (§7.4) | Transmitir la estructura simbiótica a la descendencia. | `(("enable_holon_reproduction", False),)` |
| $R_{18}$ | Causalidad descendente intra-holón (§7.5) | Reducir la redundancia de memoria entre hojas de un holón (ortogonalización). | `(("enable_downward_causation", False), ("redundancy_penalty", 1.0))` |
| $R_{19}$ | Estigmergia (§7.6) | Externalizar conocimiento en el entorno. | `(("enable_stigmergy", False), ("stigmergy_deposit_rate", 0.0))` |
| $R_{20}$ | Física metabólica (§6.1) | Vida y muerte por energía: costo basal fijo, de movimiento y de emisión, muerte con $E \le 0$ y capacidad de carga. Sin ella no hay selección. | `()` (nuclear) |
| $R_{21}$ | Costo cuadrático de cerebro y sentidos (§6.1) | Encarecer la hipertrofia individual ($C_{\max}^2$, radios²). Sesga a favor de cooperar; se declara como sesgo. | `(("memory_capacity_cost", 0.0), ("sensory_radius_cost", 0.0))` |
| $R_{22}$ | Vista compartida del holón (§7.2) | Dar a cada hoja acceso efímero al conocimiento de las hojas cercanas de su holón. | `(("enable_holon_view", False),)` |
| $R_{23}$ | Coordinación y reparto energético del holón (§7.2) | Que pertenecer a un holón tenga un costo y un beneficio energético compartido. | `(("holon_coord_cost", 0.0), ("holon_energy_sharing", False))` |

**Física del entorno sin regla.** Cómo paga un recurso compuesto (éxito si el grupo local conoce los fragmentos, fracaso si no; §1.3.2) es una propiedad del entorno diseñado, como `true_value`: el agente no la recibe, la aprende. Por eso no figura en el inventario.

**Afirmación pre-registrada.** Una afirmación $C$ consiste en una métrica poblacional $m_C$, su dirección de mejora y el conjunto $R_C \subseteq \mathcal{R}$ de reglas cuyo propósito declarado la produce. Se declara antes de ejecutar el experimento, junto con el perfil de corrida. *Principio conservador acotado:* toda afirmación sobre **disponibilidad o transmisión** de conocimiento incluye en $R_C$ las reglas de comunicación $R_8$ y $R_9$; una afirmación sobre **cómo se procesa** lo transmitido incluye las reglas diseñadas para ese procesamiento.

**Variantes.** Para cada semilla se mide $m_C$ en: la población **completa**; la **aislada** (sin comunicación); la población **sin $R_C$** (todas las reglas de $R_C$ desactivadas a la vez); y el **control nulo** (mismas reglas de emisión, recepción y ruteo, pero cada creencia entregada llega con $\hat{v}$ reemplazado por $\pm 1$ al azar, extraído de un generador propio). El control no fija el volumen de mensajes, que depende de las creencias; cada variante reporta el suyo. (En la Fase II, la variante aislada de cada afirmación se define aparte; ver "Variantes de Fase II".)

**Criterios.** Con $n \ge 5$ semillas y una prueba de signo unilateral con $\alpha = 0.05$:
- **E1 Localidad:** $m_C$ es poblacional y ningún agente la computa ni la recibe.
- **E2 Superávit:** la población completa supera a la aislada.
- **E3 Independencia del propósito:** la población sin $R_C$ sigue superando a la aislada ($R_C = \emptyset$ lo cumple trivialmente).
- **E4 Dependencia del contenido:** la población completa supera al control nulo.
- **E5 Robustez al esquema de actualización:** bajo un esquema asíncrono (los agentes se activan de a uno, en orden aleatorio, viendo el mundo ya modificado por los anteriores), la afirmación vuelve a cumplir E2 y E3. Hay patrones que aparecen con actualización sincrónica y desaparecen con la asíncrona (Huberman y Glance, 1993): son artefactos del reloj, no de la población.

**Programada por construcción.** Si quitar $R_C$ deja a la población sin ningún canal de emisión, la población sin $R_C$ *es* la aislada, y E3 deja de ser una prueba para ser una tautología. La afirmación se declara entonces *programada por construcción*, sin presentarlo como resultado empírico.

**Criterio ampliado para la Fase II.** Cada afirmación de Fase II declara además su **canal**: las reglas sin las cuales el mecanismo que se pone a prueba no existe (`PHASE2_CLAIM_CHANNELS`). Una afirmación de Fase II es *programada por construcción* si su canal no es vacío y está contenido en $R_C$: quitar $R_C$ elimina el mecanismo que se pone a prueba, y E3 sería una tautología. Para las afirmaciones de Fase I el criterio no cambia.

**Clasificación.** *No observada* si falla E2; *programada* si cumple E2 y además es programada por construcción o falla E3; *artefacto de actividad* si cumple E2 y E3 y falla E4; si cumple E1–E4: *emergente pendiente de robustez* mientras E5 no pueda evaluarse, *artefacto del reloj* si falla E5 y **emergente** si la cumple. Con menos de 5 semillas el estado es *evidencia insuficiente*.

**Consecuencia para el Experimento 001.** Las afirmaciones de acceso (C1), superávit de decisión (C2) y persistencia extra-individual (C4) tienen $R_8, R_9 \in R_C$; quitar ambas reglas aísla la población, así que son **programadas por construcción**. No es una predicción: es lo que establece la regla mientras el canal transmita creencias con semántica de fábrica. "Por construcción" es una marca (`by_construction`: E3 no se prueba); el estado sigue el orden de la clasificación, así que si falla E2 es `NOT_OBSERVED` aunque la afirmación sea por construcción (le ocurrió a C4 en la corrida pre-registrada; ver `RESULTADOS.md`). La inmunidad colectiva a la falsedad (C3) tiene $R_C = \{R_3, R_4, R_6, R_7\}$ (los filtros epistémicos y el olvido) y es la única con una prueba empírica genuina: ¿la contención del rumor sobrevive sólo con transmisión y aprendizaje directo? El resultado está abierto. Además se mide el aporte de cada regla, apagándolas de a una. Las candidatas genuinas a emergencia en este nivel son las propiedades que ninguna regla persigue, por ejemplo transiciones abruptas de la cobertura accesible o de la persistencia al variar la densidad de agentes o el radio de comunicación. Las preguntas siguientes se plantean con la evolución intergeneracional y la jerarquía holónica (Experimentos 002–003) y con la des-programación del protocolo (Experimento 006), sometidas al mismo criterio.

**Afirmaciones pre-registradas de Fase II (`EXP002_CLAIMS` y `EXP003_CLAIMS`, design D29).** Se evalúan con el mismo marco (E1–E5 y la clasificación anterior), con el criterio ampliado de "por construcción":

| Afirmación | Protocolo | Métrica $m_C$ (dirección) | $R_C$ | Canal | Variante **aislada** | Clasificación esperable |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- |
| C5: aceleración cultural intergeneracional | 002-B | `cultural_accuracy` (mayor es mejor) | $\{R_{14}\}$ | $(R_{14})$ | `ablate(config, ["R14"])`: sin herencia, con comunicación horizontal | Programada por construcción. |
| C6: adaptación evolutiva por selección | 002-A | `evolved_accuracy` (mayor es mejor) | $\{R_{12}, R_{13}\}$ | $(R_{12})$ | `ablate(config, ["R12"])`: el control de deriva (reproducción neutral) | Programada por construcción: adaptarse por selección es el propósito de $R_{12}$ y $R_{13}$. |
| C7: superávit cooperativo sobre recursos compuestos | 003-A | `holonic_composite_completions` (mayor es mejor) | $\{R_{15}, R_{17}\}$ | $(R_{15})$ | `ablate(config, ["R15"])`: sin holones, con comunicación | Programada por construcción: el entorno impide por diseño que un individuo con $C_{\max} < m$ y sin ayuda resuelva el recurso. |
| C8: cobertura colectiva adquirida sin causalidad descendente | 003-B | `mean_acquired_coverage` (mayor es mejor) | $\{R_{22}\}$ | $(R_{22})$ | `ablate(config, ["R22"])`: holones formados por la misma regla `BOND`, sin la vista compartida | Programada por construcción: saber más patrones correctos es una afirmación sobre **disponibilidad** de conocimiento, y por el principio conservador ([Documento Fundacional](DOCUMENTO_FUNDACIONAL.md) §9, punto 5) se atribuye a la regla que da acceso a ese conocimiento, $R_{22}$. |

- **Observación exploratoria (C6).** Qué rasgos evolucionan (`final_mean_memory_capacity`, `final_mean_bond_affinity` del reporte de 002-A) se registra como **observación exploratoria**, no como afirmación.
- **C8 y $R_{18}$.** $R_{18}$ está diseñada para ortogonalizar (§7.5): con ella activa, la ortogonalización sería **programada**. Por eso C8 se mide con $R_{18}$ apagada y pregunta si un holón gana cobertura colectiva (patrones correctos *distintos*, por miembro) desde que se formó, **sin** $R_{18}$ (M13, §8). Quitar $R_{18}$ no la vuelve genuina: la cobertura que gane un holón con la vista es disponibilidad de conocimiento, y C8 se declara programada por construcción por $R_{22}$. El efecto de $R_{18}$ se mide aparte, como cualquier regla, con su ablación (`rule_effects`).
- **C8 y el sesgo de `BOND`.** `BOND` ($R_{15}$) ya junta memorias distintas al fusionar, así que la redundancia baja de un holón recién formado no es un logro del holón. Ese sesgo se cancela por dos vías: M13 mide el **cambio** desde la formación ($\text{red}_0$ − redundancia actual), y la variante aislada forma sus holones con la misma regla `BOND` y sólo quita la vista compartida ($R_{22}$). No son *los mismos* holones, porque la vista cambia la energía y con ella qué holones se forman y cuánto duran; por eso M13 se promedia por par (tick, holón) y el reporte muestra la exposición de cada condición. Cancelar ese sesgo no basta para llamar emergente a C8.
- **Sin prueba genuina pre-registrada en la Fase II.** Con el criterio ampliado, C5, C6, C7 y C8 salen programadas por construcción: sus cuatro afirmaciones verifican que mecanismos diseñados funcionan. **La Fase II no tiene ninguna prueba genuina pre-registrada**, y se declara así, como resultado del diseño.
- **Observaciones exploratorias de 003-B** (no son afirmaciones y no se clasifican). En las dos condiciones de 003-B se registran la cobertura colectiva adquirida (M13), la reducción de redundancia y la exposición a holones. **Mecanismo hipotético, declarado de antemano:** con la vista, una hoja deja de consultar lo que ya saben sus compañeros (§7.2), no lo duplica y conserva capacidad para patrones propios. No se pre-registra ningún veredicto esperado. E4 compara contra el control nulo, que anula el contenido de **todos** los canales (horizontal, herencia, estigmergia y vista), así que pone a prueba si importa el contenido de toda la comunicación, no sólo el de la vista.
- **Semillas sin medición.** Si a cualquiera de las dos variantes de una comparación (E2 o E4) le falta la media de M13 en una semilla, esa comparación cuenta como empate (la prueba de signo la descarta) y el reporte la lista. Con menos de `MIN_SEEDS` semillas medidas en E2, C8 es `INSUFFICIENT_EVIDENCE`. Un efecto de regla sin semillas medidas vale `None`, nunca `0.0`.

**Variantes de Fase II.**
- **Aislada:** la indicada en la tabla.
- **Sin $R_C$:** `ablate(config, R_C)`, sólo si $R_C$ no es vacío y la afirmación no es por construcción (con lo anterior, no se corre para ninguna de C5–C8).
- **Control nulo:** `comm_content_null=True`; el motor aplica el reemplazo de $\hat{v}$ por $\pm 1$ al ruteo horizontal, a la herencia cultural ($R_{14}$), a la estigmergia ($R_{19}$) y a la vista del holón ($R_{22}$).
- **Efecto de cada regla:** una variante sin cada regla ablacionable de `ALL_DESIGN_RULES`, **salvo las inactivas** en el protocolo de la afirmación: para ellas quitar la regla no cambia nada, y un efecto 0 se leería como "no influye". Las inactivas se declaran en `PHASE2_INACTIVE_RULES` y no reciben variante ni efecto:
  - `"002a"`: $R_{14}$, $R_{15}$, $R_{16}$, $R_{17}$, $R_{18}$, $R_{19}$, $R_{22}$, $R_{23}$ (sin herencia cultural, sin holones, sin estigmergia).
  - `"002b"`: $R_{15}$, $R_{16}$, $R_{17}$, $R_{18}$, $R_{19}$, $R_{22}$, $R_{23}$.
  - `"003a"` y `"003b"`: $R_{14}$, $R_{18}$, $R_{19}$.

Para C1–C4 las variantes no cambian, y cuando todas las afirmaciones evaluadas son de Fase I el reporte de atribución sigue usando sólo `DESIGN_RULES` (si no, `ALL_DESIGN_RULES`).

**Perfil pre-registrado de la Fase II.** `PHASE2_ATTRIBUTION_PROFILE = "phase2"`, con 2000 ticks (`total_ticks`, el único campo del perfil que usan los protocolos 002 y 003), y `PHASE2_SEEDS` = semillas 42 a 51 (10 semillas: la prueba de signo unilateral puede llegar a $p = 1/1024$). Las configuraciones de cada protocolo quedan congeladas en `PHASE2_PROTOCOL_CONFIGS`, sobre los valores por defecto de `SimulationConfig`:
- `"002a"`: `enable_evolution=True`.
- `"002b"`: `enable_evolution=True`, `enable_cultural_inheritance=True`.
- `"003a"` y `"003b"`: `enable_evolution=True`, `enable_holonic_hierarchy=True`, `enable_holon_reproduction=True`, `num_composite_patterns=3`, `composite_order=4` ($> C_{\max} = 3$). En `"003b"`, `enable_downward_causation=False` es parte de la condición base de C8.

Ningún parámetro de este perfil se cambia a la vista de los resultados de las afirmaciones. La única excepción es la Enmienda 1, que se apoya sólo en la demografía de la prueba de humo y de una calibración declarada de antemano. Si la población se extingue o no llega a varias generaciones, eso se reporta como resultado. Antes de implementar los runners se corre una prueba de humo que sólo comprueba que la corrida termina y registra la generación máxima, sin calcular ni mirar las métricas de las afirmaciones.

**Enmienda 1 del perfil (2026-10-19, decisión del responsable del proyecto).** La prueba de humo (registrada en `RESULTADOS.md`, commit `58bf283`) mostró que con estas configuraciones la población no pasa de la generación 1 en ninguna de las 40 corridas: el perfil es inviable para medir C5 a C8, que dependen de la sucesión generacional o de los holones. Se calibra **una** variable del entorno con un procedimiento declarado antes de ejecutarlo y ciego a las afirmaciones (`src/ide/experiments/phase2_calibration.py`):
- **Parámetro:** `resources_per_pattern` (abundancia del entorno; no toca ninguna regla $R_{12}$–$R_{23}$). **Efecto declarado sobre C7:** los recursos compuestos siguen fijos (`composite_resources_per_pattern`), así que más recursos elementales cambian la escasez relativa de los compuestos, de la que depende `holonic_composite_completions`. No es un sesgo de selección, porque todas las condiciones comparten el valor, pero el parámetro no es neutral para C7.
- **Grilla cerrada**, en orden ascendente: 10, 20, 40 y 80. Se elige el menor valor viable, el mismo para los cuatro protocolos, y la evaluación se detiene ahí. Si ningún valor es viable, no se elige nada ni se amplía la grilla sin una decisión nueva.
- **Semillas de calibración** 0 a 9, distintas de las de medición (`PHASE2_SEEDS`).
- **Criterio.** Una corrida es viable si al final de los 2000 ticks la población sigue viva y llegó al menos a la generación 5. Un valor es viable si al menos 8 de las 10 semillas son viables en **cada condición de comparación** (`calibration_conditions`): las condiciones de cada runner, derivadas de sus `ProtocolSpec` (002-A: `evolved`, `frozen_genome` sin $R_{13}$ y `drift` sin $R_{12}$; 002-B: `cultural` y `tabula_rasa` sin $R_{14}$; 003-A: `holonic` e `individual` sin $R_{15}$; 003-B: `with_view` y `without_view` sin $R_{22}$), más el control nulo de cada protocolo (`null_content`, la variante de E4 en la atribución). Las configuraciones idénticas, como las bases de 003-A y 003-B, corren una sola vez. Exigir la viabilidad sólo a la base dejaría a esa condición en el borde de la supervivencia, y una variante algo más débil podría extinguirse antes y perder en las métricas acumuladas por pura demografía, a favor de la afirmación (hallazgo de la revisión cruzada). Las variantes de `rule_effects` no entran en el criterio: su registro demográfico (abajo) permite auditarlas.
- **Ceguera.** La calibración sólo registra población final y generación máxima: nunca calcula ni mira las métricas de las afirmaciones.
- **Antecedente.** Una primera corrida, con el criterio limitado a la base (commit `02c6a56`), terminó, pero su salida no se leyó antes de ampliar el criterio. Su JSON y su salida de consola se commitean sin leer junto con el criterio ampliado (`registros/phase2_calibration_antecedente.json` y `registros/phase2_calibration_antecedente_consola.txt`), se registra en `RESULTADOS.md` como antecedente y no se usa para elegir el valor.
- **Registro demográfico.** Para distinguir una diferencia por extinción de una diferencia de mecanismo, los reportes de 002 y 003 registran por condición la población final y la generación máxima (`condition_demography`, D28), y la atribución hace lo mismo por variante y semilla (`ClaimEvaluation.demography`, vacío en Fase I).
- **Enmienda 1b (2026-10-19, decisión del responsable del proyecto, antes de correrla).** Con la grilla original ningún valor fue viable (`RESULTADOS.md`): con 20 se extingue el control nulo y con 40 y 80 casi no hay recambio generacional. Se evalúa, con el mismo criterio, las mismas semillas y el mismo procedimiento, la grilla refinada 25, 30, 35 (`CALIBRATION_REFINED_GRID`, `python -m ide.experiments.phase2_calibration --refined`, que escribe `phase2_calibration_refinada.json`), en orden ascendente y con parada en el primer valor viable. **Salida fijada de antemano:** si tampoco hay un valor viable, se usa `resources_per_pattern = 20` (todas las condiciones de los runners son viables) y la comparación E4 de C5 a C8 se declara **no interpretable**, porque con 20 se extingue el control nulo. No cambia ninguna clasificación: las cuatro afirmaciones son programadas por construcción, y en la clasificación de la Decisión 13 su estado se decide antes de E4; el p de E4 se informa con esa advertencia. Las variantes de `rule_effects` no entran en el criterio y con 20 también podrían extinguirse: su `ClaimEvaluation.demography` se revisa antes de interpretar cada efecto, y un efecto con la variante extinguida se informa como no interpretable.
- **Resultado de la grilla refinada y salida de respaldo (2026-10-19).** La grilla refinada de la Enmienda 1b se corrió en el equipo del responsable del proyecto, sobre el código de `d60ffa6` (`--refined`, salida en `registros/phase2_calibration_refinada_consola.txt`), y **ningún valor es viable**: con 25 todas las condiciones de los runners son viables en al menos 8 de 10 semillas, pero el control nulo de 003 sólo en 5 de 10; con 30 y 35 las condiciones de 002 y 003-A `individual` casi no llegan a la generación 5. Por la regla fijada de antemano en la Enmienda 1b, `PHASE2_PROTOCOL_CONFIGS` toma `resources_per_pattern = 20` (`PHASE2_RESOURCES_PER_PATTERN`) sobre `PHASE2_PROTOCOL_CONFIGS_ORIGINAL`. Con 20 todas las condiciones de los runners son viables en al menos 9 de 10 semillas de calibración, pero el valor **no cumple el criterio**: el control nulo se extingue en 8 o 9 de 10. Por eso la comparación E4 de C5 a C8 se declara **no interpretable** (`ClaimEvaluation.e4_interpretable = False` cuando la configuración base usa la abundancia del perfil; no cambia ninguna clasificación, porque las cuatro son programadas por construcción y su estado se decide antes de E4), y cada efecto de `rule_effects` se interpreta sólo después de revisar su `ClaimEvaluation.demography`. La extinción del control nulo es una observación demográfica de la calibración, no una medición de las afirmaciones.
- **Incorporación.** El valor elegido (la salida de respaldo de la Enmienda 1b, 20) se incorpora a `PHASE2_PROTOCOL_CONFIGS` en un commit que lo justifica, antes de correr los protocolos con `PHASE2_SEEDS`. Las configuraciones originales quedan en `PHASE2_PROTOCOL_CONFIGS_ORIGINAL`: su inviabilidad queda registrada como resultado, y los protocolos y la atribución también se corren con ellas como referencia (`--reference` en la CLI de los runners, que escribe `expNNN_reference_*.json`, y `run_phase2_attribution(configs=PHASE2_PROTOCOL_CONFIGS_ORIGINAL)`).

**Inventario de la Fase II-B (`PHASE25_DESIGN_RULES`, design D56, borrador de pre-registro pendiente de aprobación en la tarea 0.5, reabierto el 2026-10-21 para agregar $R_{39}$–$R_{41}$ de la ampliación D57–D63).** Sustituye al inventario $R_{24}$–$R_{31}$ del pre-registro D42, aprobado el 2026-10-20 y reemplazado por la reformulación del mismo día antes de medir ninguna afirmación. Se agrega en `attribution.py` sin tocar `DESIGN_RULES`, `PHASE2_DESIGN_RULES` ni `ALL_DESIGN_RULES`. `PHASE25_ALL_RULES = ALL_DESIGN_RULES + PHASE25_DESIGN_RULES`, y `ablate()` busca las reglas en las dos tuplas. El modelo de cada regla está en §9. De la etapa A sólo está implementada $R_{24}$.

**Principio de la reformulación (design D43):** *la regla da la capacidad y el ADN decide su uso.* Cada regla nueva o reformulada pone a disposición del agente una capacidad física o sensorial, y ningún codón del ADN fundador la usa, salvo para reproducir la conducta de la Fase II (§9.10). Lo que la población haga con esa capacidad lo produce la selección, y se mide contra la reproducción neutral. Por eso el propósito declarado de $R_{25}$, $R_{28}$, $R_{31}$, $R_{36}$–$R_{41}$ es *permitir* algo, no producirlo. La ampliación (D57) sigue el mismo principio: el ADN fundador no usa el estado interno, la plasticidad ni las señales, así que sigue reproduciendo la política escrita a mano.

| Regla | Descripción (`name`) | Propósito declarado (`purpose`) | Ablación (`ablation`) |
| :--- | :--- | :--- | :--- |
| $R_{24}$ | ADN compacto y expresión condicional (§9.1–§9.4) | Rasgos en codones de 32 bits expresados según el contexto, con costo sobre lo expresado. **Sesgo declarado:** abarata la complejidad latente. | `(("enable_compact_dna", False),)`. Apagarla deja inertes $R_{25}$–$R_{27}$, $R_{31}$, $R_{32}$ y $R_{38}$, y con $R_{32}$ también $R_{28}$, $R_{36}$, $R_{37}$ y $R_{39}$–$R_{41}$. |
| $R_{25}$ | Señal posicional epigenética (§9.5) | Proveer una señal de posición y conocimiento dentro del holón; su uso lo decide el ADN. | `(("enable_epigenetic_roles", False),)` |
| $R_{26}$ | Conjugación de plásmidos (§9.6) | Transferir codones entre vecinos en vida. | `(("enable_plasmid_hgt", False),)`. Apagarla deja inerte $R_{27}$. |
| $R_{27}$ | Inmunidad CRISPR (§9.6) | Purgar plásmidos con balance energético negativo y bloquear su reingreso. | `(("enable_crispr_immunity", False),)` |
| $R_{28}$ | Endospora disponible (§9.7) | Permitir un estado de bajo gasto; su uso lo decide el ADN. | `(("enable_sporulation", False),)` |
| $R_{29}$ | Senescencia telomérica (§9.8) | Limitar la vida con una longevidad expresada. **Sesgo declarado:** fuerza recambio. | `(("enable_telomere_senescence", False),)` |
| $R_{30}$ | Mutación SOS (§9.8) | Aumentar la variación bajo estrés y reducirla en abundancia. | `(("enable_sos_mutation", False),)` |
| $R_{31}$ | Compromiso simbiótico (§9.9) | Permitir que un holón se vuelva indisoluble si sus hojas lo expresan. | `(("enable_symbiotic_ratchet", False),)` |
| $R_{32}$ | Conducta codificada en el ADN (§9.10) | Que la política de acción y la decisión de comunicar se expresen desde el ADN. | `(("enable_genetic_policy", False),)`. Apagarla deja inertes $R_{28}$, $R_{36}$ y $R_{37}$, que sólo actúan como conductas, y $R_{39}$–$R_{41}$, que sólo actúan en la evaluación de conducta. |
| $R_{33}$ | Recursos agotables (§9.11) | Escasez real: los recursos tardan en reponerse. | `(("enable_resource_depletion", False),)`. Apagarla deja inertes las estaciones de $R_{34}$. |
| $R_{34}$ | Heterogeneidad espacial y estacional (§9.11) | Nichos por región y abundancia variable en el tiempo. | `(("enable_heterogeneity", False),)` |
| $R_{35}$ | Cadáveres (§9.11) | Cerrar el ciclo de energía: los muertos son recurso. | `(("enable_carcasses", False),)` |
| $R_{36}$ | Transferencia de energía (§9.12) | Permitir ceder energía a un vecino; su uso lo decide el ADN. | `(("enable_energy_transfer", False),)` |
| $R_{37}$ | Depredación (§9.12) | Permitir robar energía a un vecino más débil; su uso lo decide el ADN. | `(("enable_predation", False),)` |
| $R_{38}$ | Recombinación (§9.13) | Permitir el cruce de cromosomas con una pareja; su uso lo decide el ADN. | `(("enable_recombination", False),)` |
| $R_{39}$ | Estado interno persistente (§9.15) | Permitir que el ADN escriba y lea bits de estado que persisten entre ticks; su uso lo decide el ADN. | `(("enable_internal_state", False),)` |
| $R_{40}$ | Plasticidad en vida (§9.16) | Permitir codones cuya fuerza se ajusta en vida con una regla de refuerzo mínima; qué y cuánto se aprende lo decide el ADN. | `(("enable_plasticity", False),)` |
| $R_{41}$ | Señales evolucionables (§9.17) | Permitir emitir y percibir símbolos sin significado de fábrica; su uso y su significado los construye la evolución. | `(("enable_signals", False),)` |

- **Dependencias inertes, no inválidas (design D30.3, D52.3 y precisiones 31 y 32 de la reformulación).** $R_{25}$, $R_{26}$, $R_{27}$, $R_{31}$, $R_{32}$ y $R_{38}$ sólo actúan con $R_{24}$ (así el compromiso de $R_{31}$ siempre es un rasgo heredable, nunca un decreto de la configuración); $R_{25}$ y $R_{31}$, sólo con $R_{15}$; $R_{27}$, sólo con $R_{26}$; $R_{28}$, $R_{36}$, $R_{37}$ y $R_{39}$–$R_{41}$, sólo con $R_{32}$ efectivamente activa (D57.3); $R_{28}$, $R_{29}$, $R_{30}$, $R_{35}$ y $R_{38}$, sólo con `enable_evolution=True`; las estaciones de $R_{34}$, sólo con $R_{33}$. Con su requisito apagado la bandera es inerte y no lanza `ValueError`, igual que $R_{16}$–$R_{18}$ sin $R_{15}$.
- **Reglas reformuladas (design D50).** $R_{25}$ conserva la asignación de roles, pero el rol pasa a ser sólo una señal que ningún codón fundador lee. $R_{28}$ deja de entrar en endospora por umbral: se entra sólo con la conducta `SPORULATE`. $R_{31}$ deja de soldar por reproducción o por compuestos resueltos: suelda cuando las hojas expresan compromiso. El borrador D56 ya no declara los sesgos que D42 les atribuía ("especialización programada", "rescata poblaciones" y "estabilidad por decreto"): con la reformulación, ninguna de las tres produce por sí sola esa capacidad. Conservan su sesgo declarado $R_{24}$ y $R_{29}$.
- **Lo que no son.** El ADN y los plásmidos **no transportan creencias**: el conocimiento social sigue entrando sólo por `assimilate_testimony`. El ADN sólo decide **si** el agente comunica (§9.10). Por eso el control nulo de E4 no los altera, y así se declara. Las señales de $R_{41}$ tampoco son `Message` ni creencias: no pasan por `protocol.py` ni por `assimilate_testimony` y nunca se escriben en la memoria; son un canal sensorial, como ver a un vecino (D60.6). El control nulo les quita el contenido y les conserva la presencia (§9.17).
- **Ablación de $R_{12}$ con ADN (precisión 41).** Con `enable_compact_dna` activa, `ablate(config, ["R12"])` cambia también la reproducción holónica $R_{17}$: cada hoja hija recibe el ADN de un donante sorteado con `donor_rng`, en el orden de `leaf_agents`, en lugar del de su hoja progenitora. Sin ADN, $R_{17}$ hereda como en la Fase II. Es un cambio de un camino ya implementado en la etapa A (ADN, reproducción neutral y $R_{17}$ a la vez) que ningún test existente ejerce (design D43.5).
- **$R_{29}$.** Su motivación, el "Tapón de Matusalén", quedó confirmada por el diagnóstico previo de la tarea 0.1 en las 10 semillas de los dos protocolos ([RESULTADOS.md](RESULTADOS.md)).

**Afirmaciones C9–C12 (design D42): retiradas sin medir.** El pre-registro D42 proponía cuatro afirmaciones, todas programadas por construcción: C9, adaptación con genoma regulado (`002c`, $R_C = \{R_{24}\}$); C10, adaptación con recambio en abundancia (`002d`, $\{R_{29}\}$); C11, supervivencia activa en el desierto (`002e`, $\{R_{28}\}$); y C12, superávit cooperativo con castas (`003c`, $\{R_{25}\}$). La reformulación del 2026-10-20 las **retiró antes de medir ninguna**: verificaban que mecanismos diseñados funcionan y no acercaban el proyecto a su objetivo. Sus protocolos (`002c`, `002d`, `002e` y `003c`), sus configuraciones y su perfil (`phase2`, semillas 42–51) se retiran con ellas. El texto completo se conserva como registro en el design (D42).

**Afirmaciones de la Fase II-B reformulada (`PHASE25_CLAIMS`, design D56, borrador pendiente de aprobación en la tarea 0.5, reabierto el 2026-10-21 con C19 y C20).** C13–C19 son **pruebas genuinas**: ninguna regla persigue la métrica, y la comparación es contra la reproducción neutral (la ablación de $R_{12}$), contra la ablación de un mecanismo ecológico o, en C19, contra un entorno estable. C20 es funcional (abajo). La reproducción neutral **no es deriva pura**: conserva sesgos residuales, declarados abajo. Cada métrica es la media de la ventana final, los últimos $\max(1, \lceil 0.1 \cdot T \rceil)$ ticks, de su campo de `GeneticTickMetrics` o `EcologyTickMetrics` (§9.14), salvo C16, que usa el último tick.

| Afirmación | Protocolo | Métrica $m_C$ (mayor es mejor) | Comparación | $R_C$ | Canal | $\delta_{\min}$ (propuesto) |
| :--- | :---: | :--- | :--- | :--- | :--- | ---: |
| C13: la regulación génica evoluciona | `25a` | `mean_conditional_codons` (precisión 42) | `full` frente a `drift` | $\{R_{12}\}$ | $()$ | 1.0 |
| C14: la conducta evoluciona | `25a` | `policy_divergence` | `full` frente a `drift` | $\{R_{12}\}$ | $()$ | 0.05 |
| C15: la comunicación evoluciona desde cero | `25c` | `communicating_fraction` | `full` frente a `drift` | $\{R_{12}\}$ | $()$ | 0.10 |
| C16: actividad evolutiva por encima de la reproducción neutral | `25a` | `new_activity_per_birth` (último tick, precisión 43) | `full` frente a `drift` | $\{R_{12}\}$ | $()$ | relativo: $\max(0.001,\ 0.25 \cdot \text{mediana de drift})$ |
| C17: la depredación aumenta la complejidad genética | `25a` | `mean_expressible_nonattack_codons` (precisión 42) | `full` frente a `no_predation` | $\{R_{37}\}$ | $()$ | 1.0 |
| C18: la cooperación material evoluciona en los holones | `25b` | `share_rate` | `full` frente a `drift` | $\{R_{12}\}$ | $()$ | 0.01 |
| C19: la memoria y el aprendizaje evolucionan cuando el entorno cambia | `25d` | `mean_learning_codons` (§9.14, D63.2) | `full` frente a `stable` | $()$ | $()$ | 1.0 |

- **C20, funcional y no genuina (D56 reabierto).** C20: *la memoria y la plasticidad aceleran la recuperación tras un cambio del entorno* (`25d`, métrica `post_shift_accuracy`, `full` frente a `no_learning`, $R_C$ y canal $\{R_{39}, R_{40}\}$, $\delta_{\min} = 0.02$). `post_shift_accuracy` es la suma de `correct_decisions` dividida por la suma de `decision_opportunities` (§9.14, D63.4) en los 200 ticks que siguen a cada cambio del entorno, sobre todos los cambios de la corrida (0.0 sin oportunidades). Como su canal coincide con su $R_C$, es **programada por construcción**: verifica que la capacidad sirve, como C1 y C2 de la Fase I, y **no entra en la corrección de Holm**. Su estado (precisión 53) es `OBSERVED` si el p-valor **crudo** de la prueba de signo sobre los pares válidos es menor que 0.05 y la mediana de las diferencias es al menos $\delta_{\min}$, y `NOT_OBSERVED` si no; no recorre la escalera E1–E5.

- **Protocolos (`PHASE25_PROTOCOL_CONFIGS`),** con `(resources_per_pattern, resource_regen_delay)` fijados por la compuerta de viabilidad:
  - en todos, `dna_max_length = 64` (D62.2);
  - `"25a"`, ecología individual: `PHASE2_PROTOCOL_CONFIGS["002a"]` con $R_{24}$, $R_{32}$, $R_{26}$–$R_{30}$, $R_{33}$, $R_{34}$ (`season_length = 500`), $R_{35}$–$R_{38}$ y $R_{39}$–$R_{41}$ activas;
  - `"25b"`, ecología holónica: `PHASE2_PROTOCOL_CONFIGS["003a"]` con las banderas de `"25a"` más $R_{25}$ y $R_{31}$;
  - `"25c"`, comunicación desde cero: `"25a"` con `comm_propensity_base = 0.0`;
  - `"25d"`, entorno cambiante: `"25a"` con `world_shift_period = 1000` y `world_shift_fraction = 0.5` (§9.18).
- **Condiciones de comparación:** `full` (la configuración del protocolo), `drift` (`ablate(config, ["R12"])`, **reproducción neutral**; con ADN, también la reproducción holónica $R_{17}$ es neutral, precisión 41, así que `drift` quita la selección también en `25b`), `no_predation` (sólo `"25a"`, `ablate(config, ["R37"])`), `stable` (sólo `"25d"`, la configuración con `world_shift_period = 0`), `no_learning` (sólo `"25d"`, `ablate(config, ["R39", "R40"])`) y `null_content` (el control nulo de contenido, para E4).
- **Clasificación y canal vacío (precisión 33).** Con canal vacío, ninguna es programada por construcción. En la Fase II, C6 medía `evolved_accuracy`, que es justamente lo que persigue la selección por energía de $R_{12}$ (comer bien da energía, y la energía da descendencia): por eso su canal era $R_{12}$. Las métricas de C13–C19 no son lo que ninguna regla selecciona ni produce: si crecen por encima de la reproducción neutral, es porque la selección las construyó como medio, no como fin.
- **Sesgos residuales de la reproducción neutral (precisión 44).** En `drift` siguen actuando mecanismos selectivos o dependientes de la energía:
  - la supervivencia: los donantes son los vivos que no están en endospora al empezar la reproducción;
  - la conjugación de $R_{26}$, que sólo hacen los donantes con energía suficiente, así que los codones de plásmidos se siguen propagando por energía;
  - la purga de plásmidos de $R_{27}$ y la escala de mutación de $R_{30}$, que depende de la energía del progenitor;
  - en `25b`, que un holón se reproduzca por $R_{17}$ depende de su energía total, y la réplica hereda la topología y los roles del holón progenitor;
  - la decisión de recombinar ($R_{38}$) la toma el fenotipo del agente que se reproduce, no el del donante.
  - **Expectativa declarada (no verificable de antemano):** estos sesgos acercan `drift` a `full`, así que se espera que sean conservadores. Para C14 hay un argumento más: la selección purificadora en `full` reduce `policy_divergence`. Las pruebas unilaterales detectan sólo selección positiva neta.
- **Reglas inactivas (`PHASE25_INACTIVE_RULES`), sin variante ni efecto:** `"25a"` y `"25c"`: $R_{14}$–$R_{19}$, $R_{22}$, $R_{23}$, $R_{25}$ y $R_{31}$ (sin herencia cultural, holones ni estigmergia, como `002a`); `"25b"`: $R_{14}$, $R_{18}$ y $R_{19}$, como `003a`; `"25d"`: las de `"25a"` (precisión 51).
- **Pares válidos (precisiones 45, 47 y 48).** Un par (semilla) es válido si las dos condiciones terminan con al menos una hoja activa; los demás se excluyen, sus semillas se informan en `excluded_seeds` y su cantidad en `excluded_pairs`. Si quedan menos de 20 pares válidos, la afirmación es `NOT_OBSERVED` con `evaluable = False`, y sigue contando en la corrección de Holm con el p-valor de la prueba de signo sobre sus pares válidos (1.0 si no queda ninguna diferencia distinta de cero).
- **Prueba y corrección.** Prueba de signo unilateral sobre las diferencias de los pares válidos, descartando empates, con corrección de Holm–Bonferroni sobre las afirmaciones genuinas C13–C19 ($m = 7$) y $\alpha = 0.05$. C20 se informa aparte, sin corregir.
- **Umbral de efecto.** `Phase25Claim` agrega `delta_relative` (0.0 por defecto). El umbral es $\max(\delta_{\min},\ \text{delta\_relative} \cdot \text{mediana de la condición de comparación})$, sobre los pares válidos. Sólo C16 usa `delta_relative = 0.25`, con $\delta_{\min} = 0.001$, porque la escala de su cociente se desconoce antes de correr.
- **Estado.** `OBSERVED` (un miembro nuevo de `ClaimStatus` que sólo usan estas afirmaciones) si el p-valor ajustado es menor que $\alpha$ **y** la mediana de las diferencias pareadas es al menos el umbral de efecto; `NOT_OBSERVED` en otro caso. La mediana se toma sobre **todas** las diferencias de los pares válidos, incluidas las nulas; la prueba de signo, en cambio, descarta los empates. Estas afirmaciones **no** recorren la escalera E1–E5: se evalúan sólo con la comparación pre-registrada, la corrección de Holm y el umbral de efecto, y E4 se informa aparte. Se informan siempre el p-valor crudo, el ajustado, la mediana y la demografía: por semilla y condición, `final_agents`, `final_active_agents`, `max_generation`, `cumulative_births`, `cumulative_deaths` y `mean_age_at_death`, como covariables (precisión 49: `cumulative_births` y `cumulative_deaths` suman, desde el tick 0, `births` y `deaths` de `evolutionary_history`, con los nacimientos individuales y holónicos y las muertes por hambre y por depredación; las perturbaciones no cuentan).
- **E4.** Se informa contra `null_content`, con `PHASE25_SEEDS` y la misma regla de pares válidos que las afirmaciones (precisiones 38 y 45): un control nulo extinguido no cuenta como un 0.0 a favor de `full`. Es interpretable en un protocolo sólo si, con la configuración elegida por la compuerta, su condición `null_content` fue viable en al menos 9 de las 10 semillas de viabilidad; si no, se declara no interpretable sin mirar la métrica. El control nulo aleatoriza el contenido de las creencias en todos los canales epistémicos, como en la Fase II, y no altera el ADN, los plásmidos, la política ni la puerta de comunicación.
- **Efectos de regla.** `rule_effects` (una variante por regla de `PHASE25_ALL_RULES`, salvo las inactivas del protocolo) son **exploratorios**: se miden sólo con las semillas 42–51 y no entran en la corrección de Holm.
- **Perfil.** `phase25`, con 5000 ticks y `PHASE25_SEEDS` = semillas 42 a 71 (30 semillas). `PHASE2_SEEDS` no cambia.
- **Compuerta de viabilidad (design D55), antes de cualquier afirmación.** Sólo demográfica, con las semillas 0 a 9 (`PHASE25_VIABILITY_SEEDS`). Cada corrida dura el perfil `phase25` (5000 ticks). Una corrida es viable si termina con al menos una hoja viva **que no esté en endospora** y con `max_generation >= 20`; una configuración es viable si, para cada protocolo y cada una de sus condiciones `full`, `drift`, `no_predation`, `stable` y `no_learning`, lo son al menos 9 de las 10 semillas (con 9 de 10 por condición, la estimación puntual es de unos 24 pares válidos de 30, por encima de los 20 que exige la evaluación; no es una garantía: con 10 semillas, 9 de 10 es compatible con una supervivencia real menor, y alguna afirmación podría quedar no evaluable). `null_content` se corre y se registra, pero no decide la viabilidad: sólo si E4 es interpretable. Se recorre en orden, de menos a más abundancia (menos recursos por patrón y, a igual cantidad, mayor retardo), la grilla declarada de `(resources_per_pattern, resource_regen_delay)`: `(20, 20)`, `(20, 10)`, `(30, 20)`, `(30, 10)`, `(40, 40)` y `(40, 20)`, y se elige la primera viable. Si ninguna lo es, se reporta como resultado y decide el responsable del proyecto; no se prueba nada fuera de la grilla sin una enmienda.
- **Prueba de humo.** Después de la compuerta y antes de los runners: registra por protocolo, condición y semilla sólo la terminación, la generación máxima y la población final, sin calcular ni mirar las métricas de las afirmaciones.
- **Experimento 004 (decisión P7).** Con $R_{25}$ como señal, la especialización que aparezca es evolucionada sobre una señal diseñada. El Exp 004 (especialización) se sigue midiendo con $R_{25}$ ablacionada, y lo que muestre la Fase II-B con $R_{25}$ activa no cuenta como evidencia de especialización.

---

## 4. Definición Matemática de las Métricas (Fase I: Experimento 001)

Sea $\mathcal{A}$ la población de $M$ agentes, $\mathcal{P}_{\text{mundo}}$ el conjunto de $N$ reglas del entorno y $C_{\max} < N$ el límite de memoria individual.

### M1. Cobertura Epistémica Individual vs. Colectiva
- **Cobertura Individual Media ($Cov_{\text{ind}}(t)$):** Fracción de las $N$ reglas del mundo que un agente promedio conoce correctamente en el paso $t$. Por restricción de hardware, siempre se cumple:
  $$Cov_{\text{ind}}(t) \le \frac{C_{\max}}{N} < 1.0$$
- **Cobertura Colectiva ($Cov_{\text{col}}(t)$):** Fracción de las $N$ reglas del mundo que están correctamente representadas en la población en el paso $t$.
- **Cobertura Accesible Media ($Cov_{\text{acc}}(t)$):** Fracción media, sobre agentes, de las $N$ reglas que cada agente conoce válidamente o puede obtener de un vecino a 1 salto. Sin un canal de consulta veraz (sin comunicación, sin consultas en vivo o bajo el control nulo de contenido), $Cov_{\text{acc}} = Cov_{\text{ind}}$: "accesible" significa obtenible mediante una consulta que transmite el contenido real.
  - *Advertencia:* $Cov_{\text{col}} \to 1$ **no** demuestra emergencia, porque una población aislada de $M$ agentes también la alcanza cuando $M \cdot C_{\max} \ge N$ (80 × 3 ≫ 12).
  - *Éxito del Experimento:* $Cov_{\text{acc}}^{\text{col}}(t) > Cov_{\text{acc}}^{\text{iso}}(t)$, con $Cov_{\text{ind}}(t) \le \frac{C_{\max}}{N}$ en ambos modos.

### M2. Precisión de Decisión Colectiva ($Acc_{\text{col}}(t)$) vs. Aislada ($Acc_{\text{iso}}(t)$)
En una ventana de tiempo $\Delta t$, sea $D_{\text{totales}}$ el número de oportunidades de decisión (un agente con al menos un recurso en su celda) y $D_{\text{correctas}}$ las acertadas: consumir un recurso benéfico, o no consumir nada cuando todos los recursos de la celda son dañinos. Ignorar una celda con algún recurso benéfico, o consumir uno dañino, es incorrecto. Se juzga la intención en el momento de decidir, aunque otro agente consuma antes el recurso:
$$Acc(t) = \frac{D_{\text{correctas}}}{D_{\text{totales}}}$$
- Se compara la población con comunicación activa ($Acc_{\text{col}}$) contra una población idéntica con comunicación desactivada ($Acc_{\text{iso}}$).
- **Criterio de superávit (E2 de §3.1):** la precisión acumulada final cumple $Acc_{\text{col}}(T) > Acc_{\text{iso}}(T)$ de forma estadísticamente significativa sobre varias semillas independientes (cada semilla corre ambos modos con idénticas condiciones iniciales). Una versión más exigente, a evaluar como análisis secundario, es $Acc_{\text{col}}(T) > \sup_t Acc_{\text{iso}}(t)$.

### M3. Velocidad de Propagación ($T_{\text{prop}}(\theta)$)
Sea $P_{\rho^*}(t)$ la prevalencia de $\rho^*$ (fracción de agentes que lo conocen válidamente), $t_0$ el primer tick con $P_{\rho^*}(t_0) > 0$ y $P_{\max} = \max_t P_{\rho^*}(t)$. Entonces $T_{\text{prop}}(\theta) = \min\{t - t_0 : P_{\rho^*}(t) \ge \theta P_{\max}\}$, y se reportan $t_{50}$ y $t_{90}$.
*(Se normaliza por el pico porque la prevalencia absoluta de un patrón está limitada, en promedio, por $C_{\max}/N$, y un umbral absoluto podría no alcanzarse nunca.)*

### M4. Persistencia Extra-Individual ($Pers(\rho^*)$)
Una vez que el conocimiento sobre $\rho^*$ se ha difundido, en el instante $t_{\text{purge}}$ se eliminan **todos** los agentes que alguna vez tuvieron contacto directo con el recurso físico $\rho^*$ **y** se retira $\rho^*$ del mapa de forma definitiva, para impedir re-descubrimientos.
- Se mide durante cuántos pasos $\Delta t$ la población conserva la regla correcta sólo por transmisión social (hasta que su prevalencia válida llega a 0). Como ningún sobreviviente tiene evidencia directa, la regla anti-eco impide que la confianza se recupere, así que se espera una extinción gradual: lo que se mide es su duración.

### M5. Resiliencia ante Daño / Ablación ($Res(\kappa)$)
Con el sistema en estado estacionario ($t_{\text{est}}$), se destruye instantáneamente una fracción aleatoria $\kappa \in \{0.1, 0.3, 0.5, 0.7\}$ de los agentes.
- Se mide:
  1. **Retención Inmediata:** $\frac{Cov_{\text{col}}(t_{\text{est}}^+)}{Cov_{\text{col}}(t_{\text{est}}^-)}$
  2. **Tiempo de Recuperación ($T_{\text{rec}}$):** Pasos necesarios para que la media móvil de $Acc$ (ventana de 20 ticks) regrese al $90\%$ de su media en los 20 ticks previos al daño. Si esa media previa es 0, no hay referencia y $T_{\text{rec}}$ no es medible (se reporta como ausente, no como recuperación inmediata).

### M6. Tasa de Rechazo de Falsedad ($FalseDecay(t)$)
En $t_{\text{inject}}$, se inyecta en una fracción $q$ de agentes ($q = 25\%$) una creencia falsa plantada como rumor: $k_{\text{falsa}} = (\rho_x, \hat{v}_{\text{erróneo}}, c = 0.95, n = 1, t_{\text{inject}}, d = 0)$.
- Se mide la curva de prevalencia $P_{\text{falsa}}(t)$ (porcentaje de agentes que sostienen la creencia falsa en $t > t_{\text{inject}}$).
- *Éxito epistemológico:* $P_{\text{falsa}}(t) \to 0$ conforme los agentes contrastan el rumor con la realidad del entorno.
- *Trampa de evitación:* un agente que cree que un patrón benéfico es dañino no lo prueba, así que no puede refutarlo empíricamente. Si la creencia falsa es un rumor, su corrección depende de la duda social, del olvido y de la exploración, y es un fenómeno a medir en el Experimento 001. Si en cambio es evidencia directa que quedó obsoleta porque el mundo cambió (Experimento 005, shock ambiental), la población puede quedar bloqueada, porque el consenso entre testigos directos refresca $\tau$. Para ese caso se compararán dos mecanismos: $\tau$ como edad de la evidencia más reciente y la re-verificación escéptica con probabilidad $\epsilon_{\text{recheck}}(1-c)$.

### M7. Eficiencia y Costo de Comunicación ($Cost_{\text{com}}(t)$)
Cantidad media de mensajes transmitidos por agente por paso de tiempo ($\frac{\text{Mensajes}(t)}{M}$). La eficiencia se resume como ganancia de precisión por mensaje: $\Delta_{\text{col}} / \overline{Cost_{\text{com}}}$ (indefinida si no hubo mensajes).

---

## 5. Contratos de Software (Interfaces Desacopladas)

Antes de implementar, la arquitectura en Python se compromete a separar estrictamente estos componentes (detalle en las [Definiciones Técnicas](DEFINICIONES_TECNICAS.md)):

1. **`KnowledgeUnit` (Estructura de Datos Pura):** Representa la creencia $k = (\rho, \hat{v}, c, n, \tau, d)$. Inmutable; las actualizaciones son funciones puras que devuelven una creencia nueva.
2. **`BoundedMemory` (Módulo de Memoria):** Contiene hasta $C_{\max}$ unidades `KnowledgeUnit`. Ejecuta inserción, búsqueda por patrón, decaimiento temporal y reemplazo por menor utilidad $U(k, t)$.
3. **`AgentNode` / `MicroAgent` / `CompositeAgent` (Jerarquía Cognitiva Local):** `MicroAgent` ($L=0$) contiene `BoundedMemory` y las reglas de aprendizaje directo, asimilación social (Escenarios A, B, C) y toma de decisiones. `CompositeAgent` ($L \ge 1$) agrupa recursivamente nodos `AgentNode` de niveles inferiores, sin tope de niveles codificado (la masa máxima `max_holon_leaves` acota la profundidad, §7.1). **Ninguno importa ni conoce ninguna clase de Grilla 2D.** La semántica del protocolo de mensajes vive aislada en un módulo reemplazable, para poder des-programarla.
4. **`Environment` (Interfaz Abstracta del Mundo):**
   - Implementación 1: `ToroidalGrid2D` (Experimento 001, con soporte de recursos compuestos en Fase II).
   - Implementaciones futuras: `SpatialGraph`, `ContinuousSpace2D`.
5. **`ExperimentRunner` y `MetricsCollector`:** Ejecuta los protocolos con semillas reproducibles (`seed`) y calcula las métricas M1–M7 (Fase I) y M8–M13 (Fase II).
6. **Atribución:** Inventario de reglas con propósito declarado, ablaciones, control nulo, registro pre-declarado de afirmaciones y clasificación según §3.1.

---

## 6. Dinámica Evolutiva Intergeneracional (Fase II — Experimento 002)

En la Fase I, la población es estática e inmortal. En la Fase II, con `enable_evolution=True`, los agentes están sujetos a **metabolismo energético, muerte por agotamiento y reproducción diferencial con herencia dual**. Con los valores por defecto (todas las banderas de Fase II en `False`), el sistema se comporta bit a bit como en la Fase I. Esta sección resume las decisiones D21, D22 y D26 del design de Fase II, que rige ante cualquier discrepancia. Toda operación estocástica de esta sección usa el generador dedicado `evo_rng` (`SeedSequence(seed, spawn_key=(2,))`), nunca el generador del motor. Las reglas que intervienen son $R_{20}$ (física metabólica, nuclear), $R_{21}$ (costo cuadrático), $R_{12}$ (reproducción diferencial), $R_{13}$ (mutación) y $R_{14}$ (herencia cultural).

### 6.1. Metabolismo Energético ($R_{20}$, $R_{21}$), Muerte y Reproducción ($R_{12}$)
Cada agente elemental $a_i$ mantiene una energía $E_i(t) \in \mathbb{R}$, inicializada en $E_0$ = `initial_energy` ($1.50$), **sin tope superior**. Su costo basal por tick depende del genoma y es cuadrático en la capacidad de memoria y en los radios (el término fijo es parte de $R_{20}$; los términos cuadráticos son $R_{21}$):
$$c_{\text{base}}(i) = c_{\text{fijo}} + c_{\text{mem}} \cdot C_{\max, i}^2 + c_{\text{sens}} \cdot \left(r_{\text{perc}, i}^2 + r_{\text{com}, i}^2\right)$$
con $c_{\text{fijo}}$ = `metabolic_base_cost` ($0.01$), $c_{\text{mem}}$ = `memory_capacity_cost` ($0.002$) y un **único** coeficiente sensorial $c_{\text{sens}}$ = `sensory_radius_cost` ($0.0005$) para ambos radios. El balance del tick es:
$$E_i(t+1) = E_i(t) + \eta_E \cdot r_i(t) - c_{\text{base}}(i) - c_{\text{move}} \cdot \mathbb{I}(\text{mov}_i(t)) - c_{\text{msg}} \cdot m_i(t) - c_{\text{coord\_share}}(i, t)$$
donde:
1. **Retorno de interacción:** $\eta_E$ = `energy_gain_scale` ($0.45$) y $r_i(t)$ es el valor real experimentado: $v(r)$ de un recurso elemental; $-$`composite_failure_penalty` en un intento compuesto fallido; o la fracción que le toca de un recurso compuesto resuelto por su holón (§1.3.2). Se acredita en la Fase 4.
2. **Movimiento:** $\mathbb{I}(\text{mov}_i(t)) = 1$ si el agente ejecutó un `MOVE` válido; $c_{\text{move}}$ = `move_cost` ($0.005$).
3. **Mensajes:** $m_i(t)$ es la cantidad de mensajes que emitió en las Fases 1 y 2; $c_{\text{msg}}$ = `message_cost` ($0.001$). Sin comunicación (`comm_enabled=False`) no se envía ninguno y $m_i(t) = 0$.
4. **Coordinación ($R_{23}$):** $c_{\text{coord\_share}}(i, t) = c_{\text{coord}}(U)/|U|$ si $a_i$ es hoja del holón raíz $U$ (§7.2), y $0$ si no pertenece a ningún holón. Se cobra en la Fase 5.

*(El costo cuadrático es una **decisión de diseño declarada**, la regla $R_{21}$: encarece la hipertrofia individual de $C_{\max, i}$ y de los radios, preserva la restricción $C_{\max, i} \ll N$ y, por lo tanto, sesga a favor de la cooperación. No es un resultado. Su ablación anula $c_{\text{mem}}$ y $c_{\text{sens}}$. El resto del balance (costo fijo, de movimiento y de emisión, la muerte con $E \le 0$ y la capacidad de carga) es la física metabólica $R_{20}$, nuclear: sin ella no hay selección.)*

- **Muerte:** si al cobrar el metabolismo en la Fase 5 resulta $E_i(t+1) \le 0$, el agente muere en ese mismo tick: se retira del motor y del entorno y se poda de cualquier árbol holónico (`prune_dead_leaves`, §7.3).
- **Reproducción individual diferencial ($R_{12}$, `reproduction_mode="energy"`, valor por defecto):** en la Fase 5, después de la reproducción holónica (§7.4), cada agente sobreviviente, en orden ascendente de `agent_id`, que todavía no se haya reproducido en el tick, con $E_i \ge E_{\text{reprod}}$ = `reproduction_threshold` ($2.20$) y con cupo ($|\mathcal{A}| < N_{\max}$, donde $N_{\max}$ = `max_population` $= 160$ es la capacidad de carga y $\mathcal{A}$ la población activa) engendra **un** hijo. No hay costo de gestación: la energía se parte de forma conservativa con $\kappa_{\text{part}}$ = `offspring_energy_share` ($0 < \kappa_{\text{part}} < 1$, por defecto $0.50$):
  $$E_{\text{hijo}} = \kappa_{\text{part}} \cdot E_i, \qquad E_i \leftarrow (1 - \kappa_{\text{part}}) \cdot E_i$$
- **Reproducción neutral (`reproduction_mode="neutral"`, ablación de $R_{12}$ y control de deriva de C6; design D26, caso 3):** quita el vínculo entre éxito y herencia sin cambiar **la regla** demográfica. Los mismos agentes que en el modo `"energy"` (no reproducidos, con $E_i \ge E_{\text{reprod}}$, en orden de `agent_id`, respetando el cupo) se reproducen exactamente igual: misma partición de energía, misma ubicación junto a ellos, mismo `parent_id`, misma generación y misma herencia cultural. Sólo cambia el **genoma** del hijo: antes de cada nacimiento se sortea un donante con `donors[int(donor_rng.integers(len(donors)))]` (generador propio, `spawn_key=(4,)`), donde `donors` es la lista ordenada por `agent_id` de los agentes vivos al empezar la fase de reproducción del tick, y el hijo recibe `mutate_genome(donante.genome, ...)` en vez del genoma de su progenitor. En un tick dado, con el mismo estado de partida, quién se reproduce, la partición de energía y las posiciones son las mismas que en el modo `"energy"`; sólo se rompe la herencia de los rasgos de los exitosos. A partir de ahí las dos corridas divergen, porque los hijos tienen genomas distintos, y ésa es la diferencia que mide `selection_gain`: no es un control de demografía idéntica a lo largo de la corrida. La reproducción holónica ($R_{17}$, §7.4) no cambia en la Fase II; con el ADN de la Fase II-B, también sortea un donante por hoja (precisión 41, §9.4). Comparar contra este control separa el efecto de la selección del de la deriva genética (`selection_gain`, §8).
- **A lo sumo un evento reproductivo por agente y por tick:** un agente que ya se reprodujo como hoja de un holón (§7.4) no vuelve a reproducirse individualmente en el mismo tick.
- **Linaje y ubicación:** el hijo recibe un `agent_id` nuevo de un contador monótono, `parent_id` $= \text{id}_i$ y $g_{\text{hijo}} = g_i + 1$. Se ubica en la celda menos ocupada de la vecindad de Moore del progenitor (incluida la propia), sorteando con `evo_rng` entre las empatadas.

*(No se usa la notación $\varphi$ para la energía: $\varphi$ es la confianza en el emisor, §2.3. Tampoco $\kappa$ sin subíndice, que en M5 es la fracción ablacionada. $N$ sigue siendo la cantidad de patrones del mundo.)*

---

### 6.2. Herencia Genética y Mutación Acotada ($R_{13}$)
El genoma heredable es `AgentGenome` $= (\alpha, \gamma, \epsilon, \omega_{\text{bond}}, C_{\max}, r_{\text{perc}}, r_{\text{com}})$: los cuatro rasgos continuos $\Theta_i$ y los tres enteros $\mathcal{G}_i$. El genoma fundador ($g = 0$) se toma de la configuración (`genome_from_config`). Al reproducirse, el hijo recibe el genoma parental mutado (`mutate_genome`):

1. **Rasgos continuos** $\theta \in \{\alpha, \gamma, \epsilon, \omega_{\text{bond}}\}$, si $\sigma_{\text{mut}}$ = `mutation_rate` $> 0$ (por defecto $0.05$): se aplica **siempre** ruido gaussiano a los cuatro, con recorte:
   $$\theta_{\text{hijo}} = \text{clip}\left(\theta_{\text{padre}} + \xi_\theta, \; \theta_{\min}, \; \theta_{\max}\right), \qquad \xi_\theta \sim \mathcal{N}(0, \sigma_{\text{mut}}^2)$$
   con $\alpha \in [0.01, 1]$ y $\gamma, \epsilon, \omega_{\text{bond}} \in [0, 1]$.
2. **Rasgos enteros** $g \in (C_{\max}, r_{\text{perc}}, r_{\text{com}})$, en ese orden, si $p_{\text{disc}}$ = `discrete_mutation_prob` $> 0$ (por defecto $0.10$): con probabilidad $p_{\text{disc}}$ el rasgo salta $\pm 1$ (equiprobable) y se recorta a sus cotas:
   $$g_{\text{hijo}} = \text{clip}\left(g_{\text{padre}} + \delta_g, \; g_{\min}, \; g_{\max}\right), \quad \delta_g \in \{-1, 0, +1\} \text{ con prob. } \left(\tfrac{p_{\text{disc}}}{2}, 1 - p_{\text{disc}}, \tfrac{p_{\text{disc}}}{2}\right)$$
   - $C_{\max}$: $g_{\min} = 1$ y $g_{\max}$ = `max_genome_memory_capacity` ($6$), acotado además por $N - 1$ cuando se impone la restricción de memoria (`enforce_memory_constraint=True`).
   - $r_{\text{perc}}, r_{\text{com}}$: $g_{\min} = 1$ y $g_{\max} = \lfloor (\min(W, H) - 1)/2 \rfloor$, el mayor radio que admite la grilla. Si $g_{\max} < g_{\min}$, el rasgo conserva el valor parental. La mutación no produce radio 0.
   - Las extracciones aleatorias se consumen siempre, aunque el recorte anule el salto, para que la secuencia del generador no dependa del valor del rasgo.
3. **Ablación:** si $\sigma_{\text{mut}} = 0$ y $p_{\text{disc}} = 0$, el hijo es un clon exacto y no se consume el generador.
4. **Fenotipo:** los radios mutados son efectivos: el entorno usa los radios individuales del agente para su percepción y su vecindad de comunicación.

---

### 6.3. Herencia Cultural Vertical ($\mathcal{M}_{\text{padre}} \to \mathcal{M}_{\text{hijo}}$, $R_{14}$)
*Motivación:* en el Experimento 001 la persistencia extra-individual (C4) no se observó: el conocimiento social no sobrevivió a sus portadores (`RESULTADOS.md`). La herencia cultural es una regla **diseñada** para transmitir conocimiento entre generaciones; si lo logra, cumple su propósito declarado.

Con `enable_cultural_inheritance=True` y $\gamma_{\text{gen}}$ = `inheritance_discount` $> 0$ (por defecto $0.65$), al nacer el hijo en el tick $t$:
1. Se ordena la memoria del progenitor por utilidad descendente $U(k, t)$ del progenitor (§2.2, incluida la penalización por redundancia de $R_{18}$ si está activa), con desempate por el orden canónico de $\rho$, y se toman hasta $\min(C_{\max, \text{hijo}}, |\mathcal{M}_{\text{padre}}|)$ creencias.
2. De ellas se conservan las que cumplen $\gamma \cdot \gamma_{\text{gen}} \cdot c \ge c_{\min}$ (con $\gamma$ = `gamma_social_discount`), y cada una se convierte en un testimonio parental $k' = (\rho, \hat{v}, \gamma_{\text{gen}} \cdot c, n, \tau, d)$.
3. **Entrega por la puerta única del conocimiento social:** el motor entrega cada testimonio, en ese orden, con `assimilate_testimony` y `sender_id` = id del progenitor (bajo el control nulo, antes reemplaza $\hat{v}$ por $\pm 1$ al azar). Como el hijo nace con memoria vacía, se aplica el Escenario A (§2.3), y la creencia heredada queda:
$$k_{\text{hijo}} = \left(\rho, \; \hat{v}, \; c_{\text{hijo}} = \varphi \cdot \gamma_{\text{gen}} \cdot c, \; n = 1, \; \tau = t_{\text{nac}}, \; d = 0\right)$$
   donde $\varphi$ es la confianza en el emisor (§2.3), que por defecto vale $\gamma$ = `gamma_social_discount`; es decir, $c_{\text{hijo}} = \gamma \cdot \gamma_{\text{gen}} \cdot c$.

- **Invariante de honestidad epistémica:** toda creencia heredada nace con $d = 0$ (`from_direct_experience = False`): el hijo no experimentó el recurso. Pasará a $d = 1$ sólo por experiencia directa (§2.1).
- **Ablación:** con `enable_cultural_inheritance=False` o $\gamma_{\text{gen}} = 0$, el recién nacido empieza con memoria vacía (*tabula rasa*).
- La herencia se entrega en el mismo tick del nacimiento, antes de procesar al siguiente progenitor.

---

## 7. Arquitectura Holónica y Jerarquía Recursiva (Fase II — Experimento 003)

Esta sección resume las decisiones D23 a D27 del design de Fase II. La jerarquía se activa con `enable_holonic_hierarchy=True`; sin ella no hay holones y cada agente es su propio nodo raíz.

### 7.1. Definición Inductiva de un Holón (`AgentNode`) de Nivel Arbitrario $L \in \mathbb{N}_0$
Todo participante activo del sistema es un **Holón** (o nodo agéntico) $u$, que expone la interfaz `AgentNode` (`node_id`, `holon_level`, `leaf_agents`, `effective_capacity`, `collective_memory`). El conjunto de holones $\mathcal{U}$ se define inductivamente:

1. **Caso Base (Nivel $L = 0$, Agente Elemental):**
   Todo `MicroAgent` $a_i$ es un holón hoja con:
   $$\text{children}(a_i) = \emptyset, \qquad L(a_i) = 0, \qquad |a_i| = 1$$
   donde $L(u)$ es el **nivel jerárquico** y $|u|$ es la **masa**: el número de hojas (agentes elementales) del subárbol de $u$.

2. **Paso Inductivo (Nivel $L \ge 1$, `CompositeAgent`):**
   Dados $k \ge 2$ holones activos con hojas disjuntas $\{u_1, \dots, u_k\} \subset \mathcal{U}$ (del mismo o de distinto nivel), el holón compuesto $U = \text{Composite}(u_1, \dots, u_k)$ cumple:
   $$\text{children}(U) = \{u_1, \dots, u_k\}, \qquad L(U) = 1 + \max_{u_j \in \text{children}(U)} L(u_j)$$
   $$\text{leaves}(U) = \bigcup_{u_j \in \text{children}(U)} \text{leaves}(u_j), \qquad |U| = |\text{leaves}(U)|$$
   Un holón con menos de 2 hijos o con hojas repetidas es inválido.

3. **Identificadores:** las hojas conservan su `agent_id` $\ge 0$; cada holón compuesto recibe un `node_id` **negativo** de un contador monótono decreciente que empieza en $-2$ ($-1$ es el emisor sintético de la estigmergia), de modo que los identificadores de holones y de agentes nunca colisionan.

> **Profundidad sin tope codificado, pero acotada por la masa:** el código no fija un nivel máximo: un holón de nivel $L$ puede volver a fusionarse en uno de nivel $L+1$. Pero `BOND` exige $|U| \le$ `max_holon_leaves` ($8$ por defecto), y cada nivel nuevo agrega al menos una hoja, así que $L(U) \le$ `max_holon_leaves` $- 1$. Que se formen niveles $L \ge 2$ es una pregunta empírica (se registra con M10 en los protocolos 003-A y 003-B), no una propiedad garantizada.

---

### 7.2. Propiedades Colectivas de un Holón de Nivel $L \ge 1$
Un holón compuesto $U$ tiene las siguientes propiedades, derivadas de sus hojas:

1. **Alcance local intra-holón:** dos hojas $\ell_a, \ell_b$ de $U$ están en alcance local en el tick $t$ si su distancia de Chebyshev toroidal cumple $d(\ell_a, \ell_b) \le \max(r_{\text{com}, a}, r_{\text{com}, b}) + 1$. Todo lo que una hoja obtiene de su holón (vista compartida, resolución de compuestos, causalidad descendente) se limita a las hojas en su alcance local: no hay "telepatía holónica".

2. **Memoria colectiva ($\mathcal{M}_{\text{holón}}(U)$):** ninguna estructura central almacena creencias; la memoria colectiva es una vista calculada sobre las memorias de las hojas (opcionalmente restringida a un subconjunto de hojas, por ejemplo las de alcance local). Para cada patrón $\rho$ conocido por alguna hoja, conserva la creencia que maximiza
   $$\left(c_\ell(\rho), \; \tau_\ell(\rho), \; -\text{id}_\ell\right)$$
   es decir, la de mayor confianza, luego la más reciente y luego la de la hoja de menor `agent_id`. No hay promedio ni consenso entre hojas.
   - **Capacidad efectiva:** $C_{\text{eff}}(U) = \sum_{\ell \in \text{leaves}(U)} C_{\max, \ell}$ (`effective_capacity`), y siempre $|\mathcal{M}_{\text{holón}}(U)| \le C_{\text{eff}}(U)$. Cada hoja conserva su límite $C_{\max, \ell}$. La ganancia de cobertura del holón sobre sus hojas se mide con M11 (§8).
   - **Vista compartida del holón ($R_{22}$, design D25):** es un canal de conocimiento social **efímero y declarado**: cada hoja ve en el tick lo que saben las hojas de su holón raíz en alcance local, sin copiarlo a su memoria. Es la **única excepción** a la regla de que el conocimiento social entra sólo por `assimilate_testimony`, y se justifica porque no persiste, no pasa por la fusión epistémica (§2.3) y se puede apagar con `enable_holon_view=False` (por defecto `True`; sólo actúa con `enable_holonic_hierarchy=True`). Sin ella, los holones siguen existiendo (`BOND`, `SPLIT`, energía y resolución compuesta), pero sus miembros no ven el conocimiento ajeno.
     - *Contenido:* para cada patrón, la creencia de mayor $(c, \tau, -\text{id})$ entre las hojas del holón raíz en alcance local de la hoja, sin contarla a ella. Bajo el control nulo, el motor reemplaza antes $\hat{v}$ por $\pm 1$ al azar.
     - *Separación entre creencia propia y vista:* la vista vive en un caché efímero aparte (`_holon_tick_beliefs`). La creencia efectiva que usa la decisión (y la decisión de consultar del protocolo) sigue el orden memoria → caché efímero propio → vista del holón. El aprendizaje directo (§2.1) y la asimilación de testimonios (§2.3) parten sólo de la creencia propia (`own_belief`: memoria → caché efímero propio), para que nunca se fusionen con la creencia de un compañero. Las respuestas a consultas y las difusiones salen sólo de la memoria propia: nadie retransmite la vista del holón. Con la vista vacía, el comportamiento coincide bit a bit con la Fase I.
     - *Sincronización en dos tiempos, sin efectos de orden:* el motor calcula primero la vista de todas las hojas y recién después la inyecta, en orden de `agent_id`. **Tiempo 1** (Fase 1, antes de emitir mensajes): lee las memorias de las hojas, de modo que el protocolo no gasta consultas en lo que el holón ya sabe. **Tiempo 2** (al final de la Fase 2, antes de decidir): lee la creencia propia de las hojas (memoria más caché del tick en curso), para que la decisión de la Fase 3 aproveche lo que cada hoja obtuvo de sus vecinos.

3. **Energía, costo de coordinación y reparto ($R_{23}$):** la energía del holón es $E(U, t) = \sum_{\ell \in \text{leaves}(U)} E_\ell(t)$ (`total_energy`). Con `holon_energy_sharing=True` (por defecto), las ganancias de un recurso compuesto resuelto se reparten en partes iguales entre las hojas de $U$ en alcance local (§1.3.2); con `holon_energy_sharing=False` van enteras a la hoja que lo resolvió. Mantener el holón cuesta por tick
   $$c_{\text{coord}}(U) = c_{\text{enlace}} \cdot |U| \cdot L(U), \qquad c_{\text{enlace}} = \texttt{holon\_coord\_cost} \; (0.002)$$
   que se cobra **sólo a los holones raíz** (los sub-holones no pagan aparte, porque $L(U)$ ya pondera la profundidad) y, con evolución activa, se descuenta en partes iguales, $c_{\text{coord}}(U)/|U|$, de cada hoja (§6.1). El costo de coordinación y el reparto de la ganancia compuesta forman la regla $R_{23}$, diseñada para que pertenecer a un holón tenga un costo y un beneficio energético compartido; su ablación es `holon_coord_cost=0` y `holon_energy_sharing=False`.
   - *Fuera del alcance de la Fase II actual:* un campo perceptual unificado del holón (cada hoja percibe con sus propios radios) y el reparto de ganancias proporcional a la contribución epistémica.
   - Se pone a prueba si, con recursos compuestos disponibles, las ganancias compuestas compensan el costo de coordinación y sostienen holones; sin compuestos, el costo de coordinación sólo resta energía. Ninguna de las dos cosas se presupone.

4. **Superávit del tick:** $U$ tuvo superávit en el tick $t$ si y sólo si (a) registró al menos una resolución compuesta exitosa en la Fase 4 de $t$, o (b)
   $$|\mathcal{K}_{\text{loc}}(U)| > \max_{\ell \in \text{leaves}(U)} |\mathcal{K}(\ell)|$$
   donde $\mathcal{K}(\ell)$ son los patrones de la memoria de $\ell$ con $c \ge c_{\text{umbral}}$ y $\mathcal{K}_{\text{loc}}(U)$ es la unión de $\mathcal{K}(\ell)$ sobre la **componente conexa más grande** del grafo de alcance local entre las hojas de $U$ (empate entre componentes del mismo tamaño: la de menor `agent_id` mínimo). Con superávit, el contador `ticks_without_surplus` vuelve a $0$; sin superávit, aumenta en $1$. Sólo se evalúa en los holones raíz: un sub-holón que pasa a raíz por `SPLIT` empieza con el contador en $0$.

---

### 7.3. Operadores de Fusión (`BOND`, $R_{15}$) y Fisión (`SPLIT`, $R_{16}$)

Todos los agentes comienzan en $L = 0$, cada uno como su propio nodo raíz. La topología arbórea no está fija: la **producen** las reglas diseñadas $R_{15}$ (`BOND`) y $R_{16}$ (`SPLIT`), que la reconfiguran en la Fase 5 de cada tick. Qué estructuras resultan (cuántos holones, de qué nivel y cuánto duran) es lo que se mide con M10.

#### 1. Fisión Holónica (`SPLIT`, $R_{16}$)
Para cada holón raíz $U$, en orden ascendente de `node_id`, después de cobrar $c_{\text{coord}}(U)$ y actualizar su contador de superávit (§7.2): si `enable_holon_splitting=True` (valor por defecto) y se cumple
$$\texttt{ticks\_without\_surplus}(U) \ge \texttt{holon\_split\_patience} \;(25) \quad \text{o} \quad E(U, t) < |U| \cdot \texttt{holon\_min\_energy\_per\_leaf} \;(0.30)$$
el holón se disuelve: deja de ser raíz y cada uno de sus hijos **directos** pasa a ser un nodo raíz (los sub-holones intermedios se conservan si $L(U) \ge 2$). Las memorias de las hojas no cambian.

#### 2. Fusión Holónica (`BOND`, $R_{15}$)
Dos nodos raíz $U_a, U_b$ ($a < b$, de cualquier nivel) son **candidatos** en el tick $t$ si:
1. **Masa acotada:** $|U_a| + |U_b| \le$ `max_holon_leaves`.
2. **Contigüidad física:** alguna hoja de $U_a$ y alguna de $U_b$ están a distancia de Chebyshev toroidal $\le 1$.

Su puntaje combina complementariedad epistémica y propensión a fusionarse:
$$\text{score}(U_a, U_b) = \frac{|\mathcal{K}_a \,\triangle\, \mathcal{K}_b|}{|\mathcal{K}_a \cup \mathcal{K}_b|} \cdot \frac{\bar{\omega}_{\text{bond}}(U_a) + \bar{\omega}_{\text{bond}}(U_b)}{2}$$
donde $\mathcal{K}_a, \mathcal{K}_b$ son los patrones con $c \ge c_{\text{umbral}}$ en las memorias colectivas de $U_a$ y $U_b$ (el primer factor, $\mathcal{S}_{\text{comp}}$, es la distancia de Jaccard, y vale $0$ si $\mathcal{K}_a \cup \mathcal{K}_b = \emptyset$), y $\bar{\omega}_{\text{bond}}(U)$ es la media de $\omega_{\text{bond}}$ sobre las hojas de $U$.

Los candidatos con $\text{score} \ge \theta_{\text{bond}}$ = `holon_bond_threshold` ($0.35$) se ordenan por $(-\text{score}, a, b)$ y se fusionan de forma voraz y sin solapamiento en el mismo tick: cada par elegido se reemplaza por un nuevo holón raíz $U = \text{Composite}(U_a, U_b)$ de nivel $1 + \max(L(U_a), L(U_b))$. **No hay condición de energía ni sorteo:** la fusión es determinista dada la configuración del tick. *(Fusionar clones con memorias idénticas da $\mathcal{S}_{\text{comp}} = 0$ y queda excluido.)*

#### 3. Poda por muerte o ablación (`prune_dead_leaves`)
Cuando mueren o se eliminan agentes (por metabolismo o por las perturbaciones de ablación), cada árbol se poda recursivamente: un sub-holón sin hojas sobrevivientes desaparece; uno con un único hijo sobreviviente colapsa en ese hijo; uno con $\ge 2$ conserva los sobrevivientes y recalcula hojas y nivel.

---

### 7.4. Reproducción de Holón Completo ($R_{17}$, inspirada en la endosimbiosis de Margulis)
Con `enable_holon_reproduction=True` y `enable_evolution=True`, en la Fase 5 y antes de la reproducción individual (§6.1), cada holón raíz $U$, en orden ascendente de `node_id`, se reproduce como unidad si:
- ninguna de sus hojas se reprodujo ya en el tick;
- $E(U, t) \ge |U| \cdot E_{\text{reprod}}$;
- hay cupo para todas sus hojas hijas: $|\mathcal{A}| + |U| \le N_{\max}$.

Entonces cada hoja $\ell$, en orden de `agent_id`, engendra una hoja hija con las mismas reglas que la reproducción individual (partición de energía $\kappa_{\text{part}}$, mutación $R_{13}$, ubicación junto a $\ell$, herencia cultural $R_{14}$ entregada por el motor), y se replica la topología arbórea de $U$ en un nuevo holón raíz $U_{\text{hijo}}$ con $L(U_{\text{hijo}}) = L(U)$. Todas las hojas de $U$ y sus hijas quedan marcadas como reproducidas en ese tick.

- $R_{17}$ está diseñada para transmitir la estructura simbiótica a la descendencia: que la descendencia nazca asociada es su propósito, no un resultado.
- Si la selección entre holones llega a pesar más que la selección dentro de ellos es una pregunta empírica que se pone a prueba; no se presupone.

---

### 7.5. Causalidad Descendente Intra-Holón ($R_{18}$, inspirada en Denis Noble)
Con `enable_downward_causation=True`, para cada holón raíz $U$ y cada hoja $\ell \in \text{leaves}(U)$, sea $\text{loc}(\ell)$ el conjunto de hojas de $U$ en alcance local de $\ell$ (incluida $\ell$). Para cada patrón $\rho \in \mathcal{M}_\ell$, la **especialista local** es
$$\ell^*(\rho) = \arg\max_{\ell' \in \text{loc}(\ell),\; \rho \in \mathcal{M}_{\ell'}} \left(c_{\ell'}(\rho), \; -\text{id}_{\ell'}\right)$$
(en empate de confianza, la hoja de menor `agent_id`). Los patrones redundantes de $\ell$ son $\text{Red}(\ell) = \{\rho \in \mathcal{M}_\ell \mid \ell \neq \ell^*(\rho)\}$, y la utilidad de retención de $\ell$ se modula con un **factor multiplicativo**:
$$U_{\text{red}}(k, t) = \begin{cases} U(k, t) \cdot \psi_{\text{red}} & \text{si } \rho_k \in \text{Red}(\ell) \\ U(k, t) & \text{si no} \end{cases} \qquad \psi_{\text{red}} = \texttt{redundancy\_penalty} \in (0, 1], \text{ por defecto } 0.25$$
donde $\psi_{\text{red}} = 1$ equivale a no tener efecto. La modulación afecta a todo uso de la utilidad: el desalojo (§2.2), el orden de difusión espontánea y el orden de la herencia cultural (§6.3). Para las hojas fuera de todo holón, o con la regla desactivada, $\text{Red}(\ell) = \emptyset$ y el factor es $1$.

- **Atribución:** $R_{18}$ está **diseñada para ortogonalizar** las memorias de las hojas ($\mathcal{M}_i \cap \mathcal{M}_j \to \emptyset$) y acercar $|\mathcal{M}_{\text{holón}}(U)|$ a $C_{\text{eff}}(U)$. La ortogonalización que produzca es, por definición, **programada**. Su efecto se mide como el de cualquier otra regla, con su ablación. La afirmación C8 (§3.1) pregunta otra cosa: si los holones ganan cobertura colectiva **sin** $R_{18}$; por eso el protocolo 003-B corre con la regla apagada y compara la cobertura colectiva adquirida (M13) de holones con vista compartida ($R_{22}$) y sin ella. Esa cobertura es disponibilidad de conocimiento, así que C8 se declara programada por construcción por $R_{22}$ (§3.1).
- *Fuera del alcance de la Fase II actual:* la modulación de la tasa de exploración $\epsilon_{\text{eff}}$ de las hojas por parte del holón.

---

### 7.6. Estigmergia Espacial ($R_{19}$)
Con `enable_stigmergy=True`, los agentes pueden **externalizar conocimiento en el entorno** dejando en su celda un **rastro estigmérgico** (`StigmergicTrace`) por patrón:
$$\mathcal{S}(l, \rho) = \left(\rho, \; s, \; I, \; \tau_{\text{rastro}}\right), \qquad s \in \{-1, 0, +1\}, \; I \in [0, 1]$$

- **Depósito (Fase 4):** tras una experiencia directa con un patrón **elemental** $\rho$ de valor real $v$, si $s_{\text{dep}}$ = `stigmergy_deposit_rate` $> 0$ (por defecto $0.50$), el agente deposita en su celda el rastro
  $$\left(\rho, \; s = \text{sign}(v), \; I = \min(1, \; s_{\text{dep}} \cdot c), \; \tau_{\text{rastro}} = t\right)$$
  donde $c$ es la confianza de su creencia sobre $\rho$ después de aprender (§2.1). Si la celda ya tiene un rastro de $\rho$ de un tick anterior, el nuevo lo reemplaza; si es del mismo tick, se conserva el de mayor $(I, s)$, así los depósitos simultáneos dan el mismo resultado en cualquier orden. Un depósito con $I < c_{\min}$ (`min_confidence`) reemplaza y se purga en el acto: borra el rastro de $\rho$ de un tick anterior y no deja ninguno; frente a un rastro del mismo tick no cambia nada, porque la regla del mayor $(I, s)$ se aplica antes y ese rastro tiene mayor intensidad, de modo que ningún rastro existe bajo el umbral con el que el decaimiento lo purgaría. Por eso, con la estigmergia activa y $s_{\text{dep}} > 0$, la configuración exige $s_{\text{dep}} \cdot c_0 \ge c_{\min}$, con $c_0$ = `initial_direct_confidence`: una creencia directa nueva debe dejar un rastro que sobreviva; si no, la estigmergia casi sólo borraría rastros. Es una cota de cordura, no una garantía para todo depósito: si la experiencia refuerza un rumor previo o refuta una creencia, $c$ puede quedar por debajo de $c_0$, y el depósito puede borrar el rastro anterior sin dejar uno (la experiencia más reciente prevalece).
- **Decaimiento:** al avanzar la dinámica del entorno en el tick $t$, cada rastro que no se actualizó en el tick ($\tau_{\text{rastro}} < t$) pierde $\delta_{\text{suelo}}$ = `stigmergy_decay` ($0.02$) de intensidad, $I \leftarrow I - \delta_{\text{suelo}}$, y se elimina si $I < c_{\min}$.
- **Lectura (Fase 1):** el motor lee los rastros de la celda del agente (no forman parte de su `Observation`) y convierte cada uno en el testimonio $(\rho, s, I, 1, \tau_{\text{rastro}}, 0)$, que entrega con `assimilate_testimony` y `sender_id` $= -1$ (bajo el control nulo, antes reemplaza el valor por $\pm 1$ al azar). Se procesa como cualquier testimonio (§2.3): recibe el descuento de confianza en el emisor del receptor ($\gamma$ por defecto) y, como $d = 0$, la protección anti-cámara de eco.
- Los rastros sobreviven a quien los depositó mientras no decaigan: el entorno funciona como una memoria externa compartida. Que esto sostenga conocimiento a través de generaciones es lo que se pone a prueba; $R_{19}$ está diseñada para externalizar conocimiento.

---

## 8. Métricas Formales de Evolución y Jerarquía Holónica (Fase II: M8–M13)

Además de las métricas M1–M7 (§4), la Fase II registra por tick, en `EvolutionaryTickMetrics` (design D28; `TickMetrics` conserva sus 14 campos de Fase I), seis métricas. Sea $\mathcal{A}(t)$ la población activa y $\mathcal{U}_{\text{root}}(t)$ el conjunto de holones raíz compuestos ($L \ge 1$).

- **Creencias válidas en M9 y M11:** una creencia es válida si su confianza cumple $c \ge c_{\text{umbral}}$ (`decision_conf_threshold`), **sin importar si su signo es correcto**: esas métricas describen qué se retiene, no si es verdad. **M13 es la excepción:** sólo cuenta creencias de signo correcto.

- **M2 en Fase II:** la precisión de decisión se calcula **sólo sobre recursos elementales**, exactamente como en la Fase I. Los recursos compuestos no entran en la verdad que juzga la decisión: si, quitándolos, una celda queda sin recursos, o si la acción del agente es `INTERACT` sobre un recurso compuesto, ese agente no suma oportunidad de decisión en el tick. El desempeño sobre compuestos lo mide M12.

### M8. Dinámica Generacional
Generación media (`mean_generation`) y máxima (`max_generation`) de $\mathcal{A}(t)$, nacimientos (`births_this_tick`) y muertes (`deaths_this_tick`) del tick, y energía media (`mean_energy`). Si $\mathcal{A}(t) = \emptyset$, valen $0.0$, $0$ y $0.0$.

### M9. Proporción Social de los Descendientes (`offspring_social_ratio`, descriptiva)
Sobre los agentes activos con $g \ge 1$, sea $V_{\text{total}}$ el número total de creencias válidas en sus memorias y $V_{\text{social}}$ las que tienen $d = 0$:
$$M9(t) = \frac{V_{\text{social}}}{V_{\text{total}}} \quad (0.0 \text{ si } V_{\text{total}} = 0)$$
Es **descriptiva**: cuenta toda creencia de origen social, sea heredada o recibida por testimonio horizontal, así que no mide sola la herencia. La contribución de la herencia cultural se mide comparando contra la ablación de $R_{14}$ en 002-B (`social_ratio_gain`).

### M10. Estructura Holónica por Nivel
- `holon_count_by_level`: pares $(L, \text{conteo})$ con el número de holones compuestos activos de cada nivel $L \ge 1$, ordenados por $L$.
- `max_holon_level`: $L_{\max}(t)$, el mayor nivel presente ($0$ si no hay holones compuestos).
- `mean_holon_size`: masa media $\overline{|U|}$ de los holones raíz compuestos ($0.0$ si no hay ninguno).

### M11. Ganancia de Cobertura Holónica (`holonic_coverage_gain`)
Para cada $U \in \mathcal{U}_{\text{root}}(t)$, sea $|\mathcal{K}(U)|$ el número de patrones válidos de $\mathcal{M}_{\text{holón}}(U)$ y $\overline{|\mathcal{K}_{\text{leaf}}(U)|}$ el promedio de patrones válidos en las memorias individuales de sus hojas:
$$G(U) = \frac{|\mathcal{K}(U)|}{\overline{|\mathcal{K}_{\text{leaf}}(U)|}} \quad (1.0 \text{ si el denominador es } 0), \qquad M11(t) = \frac{1}{|\mathcal{U}_{\text{root}}(t)|} \sum_{U} G(U)$$
y $M11(t) = 1.0$ si no hay holones raíz compuestos.

### M12. Recursos Compuestos Resueltos (`composite_completions`)
Contador **acumulado** de resoluciones compuestas exitosas desde el inicio de la corrida (§1.3.2).

### M13. Cobertura Colectiva Adquirida (`acquired_coverage`, métrica de C8) y Reducción de Redundancia (`redundancy_reduction`, descriptiva)
Miden qué ganó cada holón **desde que se formó**, para que el sesgo de `BOND` ($R_{15}$), que ya junta memorias distintas al fusionar, no cuente. La métrica de C8 es la **cobertura colectiva adquirida**: cuántos patrones correctos *distintos* ganó el holón, por miembro. Con memoria acotada, ésa es la ventaja funcional de no duplicar: una hoja que duplica lo que sabe un compañero desaloja algo propio. A diferencia de la redundancia, olvidar algo duplicado no suma y olvidar algo único resta, así que no premia saber menos.
- **Creencias que cuentan.** Para una hoja $\ell$, $K(\ell)$ es el conjunto de patrones **elementales** de su memoria con $c \ge c_{\text{umbral}}$ (`decision_conf_threshold`) **y signo correcto** ($\text{sign}(\hat{v}) = \text{sign}(v)$ del patrón en el mundo). El colector conoce la verdad del mundo, como para M1 y M2; el agente no.
- **Cobertura y redundancia.** $\text{cov}(U) = \left|\bigcup_{\ell \in \text{leaves}(U)} K(\ell)\right|$. Con $S(U) = \sum_{\ell} |K(\ell)|$, $\text{red}(U) = (S(U) - \text{cov}(U))/S(U)$ si $S(U) > 0$ y $0$ si no.
- **Estado de formación.** Al crear un `CompositeAgent`, el motor guarda en `formation_knowledge` el $K(\ell)$ de cada hoja, en pares `(agent_id, K)`, fija `formation_tick` $=$ `created_tick` y marca `formed_by_bond`; $\text{cov}_0(U)$ y $\text{red}_0(U)$ se calculan con esos $K$. **Cuando el holón pierde un miembro** (por muerte o por cualquier poda) y sigue siendo un holón, el motor **reinicia** su estado de formación: `formation_knowledge` pasa a ser el $K$ actual de las hojas que quedan y `formation_tick` $= t$. Es como si el holón se formara de nuevo, de modo que una muerte nunca cuenta como ganancia ni como pérdida. Un sub-holón que pasa a raíz por `SPLIT` conserva su propio estado de formación y su `formed_by_bond`.
- **Holones elegibles.** $\mathcal{U}_{\ge 1}(t)$ son los holones raíz con `formed_by_bond` y $t - \texttt{formation\_tick} \ge 1$. Los creados por $R_{17}$ no entran (tampoco sus sub-holones replicados): su composición la impone la reproducción, no una fusión entre nodos que ya sabían algo.
- **Valor del tick.**
$$M13(t) = \frac{1}{|\mathcal{U}_{\ge 1}(t)|} \sum_{U \in \mathcal{U}_{\ge 1}(t)} \frac{\text{cov}(U) - \text{cov}_0(U)}{|U|}$$
con $|U|$ las hojas vivas. Es positiva si el holón sabe más cosas distintas que al formarse. `redundancy_reduction` es la media de $\text{red}_0(U) - \text{red}(U)$ sobre los mismos holones. Si $\mathcal{U}_{\ge 1}(t) = \emptyset$, las dos valen `None`: no hay nada que medir y el tick no cuenta.
- **Media de una corrida.** Se promedia sobre los pares (tick, holón elegible). Así, una condición con menos holones no se acerca a 0 por tener menos exposición. Sin ningún par, la media es `None`.
- *Ejemplos:*
  - Un holón de dos hojas se forma con $K = \{\rho_0, \rho_1\}$ y $K = \{\rho_0\}$ ($\text{cov}_0 = 2$, $\text{red}_0 = 1/3$). Más tarde tienen $\{\rho_0, \rho_1\}$ y $\{\rho_2\}$ ($\text{cov} = 3$, $\text{red} = 0$): $M13 = (3 - 2)/2 = 1/2$ y `redundancy_reduction` $= 1/3$.
  - Si en un holón $\{\rho_0\}, \{\rho_0\}$ una hoja olvida $\rho_0$, la cobertura no cambia ($M13 = 0$), aunque la redundancia baje.
  - Un holón se forma con $A = \{\rho_0\}$, $B = \{\rho_1\}$ y $C = \{\rho_2\}$; luego $A$ aprende $\rho_1$ (lo duplica) y muere $B$ en el tick $t$. El holón reinicia su estado de formación al de $A$ y $C$ en $t$ (`formation_tick` $= t$), no es elegible en $t$, y en $t+1$, sin otros cambios, aporta $M13 = 0$: la muerte no suma ni resta.

Además se registra `stigmergy_active_cells` (celdas con al menos un rastro estigmérgico), como telemetría sin número de métrica.

**Protocolos y reportes (design D28).** Cada protocolo corre sus condiciones con la misma semilla; las precisiones (`*_accuracy`) son la precisión acumulada M2 del último tick.
- **002-A** (`run_protocol_002a_adaptation`, `AdaptationReport`): tres condiciones, la evolutiva (`evolved_accuracy`), el genoma congelado (ablación de $R_{13}$, `frozen_genome_accuracy`) y el **control de deriva** (ablación de $R_{12}$, reproducción neutral con mutación, `drift_accuracy`). Reporta `adaptation_gain` = `evolved_accuracy` − `frozen_genome_accuracy` y `selection_gain` = `evolved_accuracy` − `drift_accuracy`: sin el control de deriva, un cambio en los rasgos heredables no podría distinguirse de la deriva genética. Registra además, como observación exploratoria, los rasgos medios finales `final_mean_memory_capacity` y `final_mean_bond_affinity`, junto con la generación máxima, la energía media y los nacimientos y muertes totales.
- **002-B** (`run_protocol_002b_cultural_inheritance`, `CulturalInheritanceReport`): herencia cultural frente a *tabula rasa* (ablación de $R_{14}$), con `cultural_accuracy_surplus`, la M9 final de ambas condiciones y su diferencia `social_ratio_gain`, y los ticks de convergencia (el menor tick con oportunidades de decisión y precisión acumulada $\ge 0.70$, o ninguno).
- **003-A** (`run_protocol_003a_holonic_transition`, `HolonicTransitionReport`): jerarquía holónica frente a individuos (ablación de $R_{15}$) ante recursos compuestos de orden $m > C_{\max}$, con las completaciones compuestas de ambas condiciones y su diferencia, la precisión de ambas, `max_holon_level` y el pico de M11.
- **003-B** (`run_protocol_003b_orthogonalization`, `OrthogonalizationReport`): dos condiciones con $R_{18}$ apagada, `with_view` = `config` y `without_view` = `ablate(config, ["R22"])` (holones formados por la misma `BOND`, sin vista compartida). Reporta `mean_acquired_coverage` y `mean_acquired_coverage_without_view` (medias de M13 por par tick-holón elegible de cada condición, o `None`), `coverage_advantage` (con vista − sin vista, o `None`), las reducciones de redundancia medias de ambas condiciones (descriptivas), `holon_ticks` y `holon_ticks_without_view` (la exposición de cada condición), `max_holon_level` y el pico de conteos por nivel (para cada nivel, el mayor número de holones de ese nivel en un mismo tick).

---

## 9. Genética Compacta, Conducta Evolucionable y Ecología (Fase II-B — Protocolos 25a, 25b, 25c y 25d)

> **Estado.** La etapa A ($R_{24}$, §9.1–§9.4) está implementada y verificada. El resto está especificado y sin implementar. La Fase II-B se **reformuló el 2026-10-20** (design D43–D56) y se **amplió el 2026-10-21** (D57–D63, §9.15–§9.18): esta sección resume las decisiones D30 a D63 del `design.md` del cambio activo [`ide-v25-compact-dna-and-epigenetics`](../openspec/changes/ide-v25-compact-dna-and-epigenetics/design.md), que rige ante cualquier discrepancia. El pre-registro vigente es el borrador D56 (§3.1), pendiente de aprobación en la tarea 0.5.

Con todas las banderas nuevas en `False` (su valor por defecto), el sistema se comporta bit a bit como en la Fase II. El genotipo de cada hoja ($L = 0$) pasa a ser un **ADN compacto** de codones de 32 bits, cuya expresión depende del contexto. Un `CompositeAgent` no tiene ADN propio: su genética es la de sus hojas. El ADN **no transporta creencias**: es un canal genético, no epistémico.

**Principio (design D43): la regla da la capacidad y el ADN decide su uso.** Cada regla nueva o reformulada pone a disposición del agente una capacidad física o sensorial: una conducta posible, una señal que puede leer o un estado al que puede entrar. Ningún codón del ADN fundador la usa, salvo para reproducir la conducta de la Fase II (§9.10). Lo que la población haga con esa capacidad lo produce la selección, y se mide contra la reproducción neutral (§3.1). Es la respuesta a la conclusión de la Fase II, cuyas cuatro afirmaciones salieron programadas por construcción: una regla que produce directamente lo que se quiere observar no deja nada que medir.

### 9.1. El Codón de 32 bits
Un codón es un entero $c \in [0, 2^{32} - 1]$, con cinco campos:
$$\underbrace{c_{31..24}}_{\text{PROMOTER}} \;\Big|\; \underbrace{c_{23..16}}_{\text{TARGET}} \;\Big|\; \underbrace{c_{15..14}}_{\text{MODE}} \;\Big|\; \underbrace{c_{13..8}}_{\text{CHANNEL}} \;\Big|\; \underbrace{c_{7..0}}_{\text{PAYLOAD}}$$
- $\text{prom} = \lfloor c / 2^{24} \rfloor \bmod 2^8$, $\text{target} = \lfloor c / 2^{16} \rfloor \bmod 2^8$, $\text{mode} = \lfloor c / 2^{14} \rfloor \bmod 4$ y $\text{channel} = \lfloor c / 2^{8} \rfloor \bmod 64$.
- **Efecto con signo.** Con $p = c \bmod 2^8$, el payload en complemento a dos es $\tilde p = p - 256$ si $p \ge 128$ y $\tilde p = p$ si no, y
  $$\delta = \tilde p / 128 \in [-1, \; 0.9921875].$$
- **Modos:** $0$ `ADDITIVE`, $1$ `REPRESSOR`, $2$ `MULTIPLICATIVE`, $3$ `PLASTIC` (D59.1): **inerte** en la transcripción del fenotipo y, con $R_{40}$, plástico sobre los destinos de conducta (§9.16). Hasta la ampliación, el modo 3 era el `AST_PIPE` reservado de la Fase IV; esa reserva se mudó al destino `0x3F`, inerte.
- **Canales.** 6 bits direccionan 64 factores de transcripción ($\text{TF}_0 \dots \text{TF}_{63}$).

El ADN de una hoja es $D = (\text{chromosome}, \text{plasmids}, \text{crispr\_memory})$: un cromosoma no vacío de herencia vertical, a lo sumo `max_plasmids` plásmidos sin repetir (herencia vertical y horizontal, $R_{26}$) y una memoria CRISPR sin repetir de a lo sumo `crispr_memory_size` firmas ($R_{27}$).

### 9.2. Promotores y Destinos
Sea un contexto epigenético $\chi = (L, \text{rol}, e)$, con $L$ el nivel del holón raíz que contiene a la hoja (0 si está sola), $\text{rol} \in \{\texttt{NONE}, \texttt{EXPLORER}, \texttt{LIBRARIAN}, \texttt{NERVE}\}$ y $e = E_i / E_{\text{reprod}}$. Sea además $\sigma$ el vector de señales sensoriales del tick (`SensorySignals`, §9.10). Un promotor está **activo** según:

| Promotor | Nombre | Activo si |
| :---: | :--- | :--- |
| `0x00` | `ALWAYS_BASAL` | siempre |
| `0x01` | `SOLITARY_L0` | $L = 0$ |
| `0x02`–`0x0A` | `IN_HOLON_Lk`, $k = \text{prom} - 1$ | $L \ge k$ |
| `0x10`, `0x11`, `0x12` | `ROLE_EXPLORER`, `ROLE_LIBRARIAN`, `ROLE_NERVE` | el rol coincide |
| `0x18` | `STRESS_LOW_ENERGY` | $e <$ `stress_energy_ratio` |
| `0x19` | `SURPLUS_HIGH_ENERGY` | $e \ge$ `surplus_energy_ratio` |
| `0x20`–`0x27` | promotores sensoriales (§9.10) | la señal correspondiente de $\sigma$ es verdadera, **sólo** en la evaluación de conducta; en la transcripción del fenotipo están inactivos |
| `0x28`–`0x2B` | eventos del tick anterior (§9.15): `EVENT_ATTACKED`, `EVENT_ATE`, `EVENT_LOST_ENERGY`, `EVENT_RECEIVED_ENERGY` | el campo correspondiente de `last_events` es verdadero, sólo en la evaluación de conducta |
| `0x30`–`0x37` | `STATE_k`, $k = \text{prom} - \texttt{0x30}$ ($R_{39}$, §9.15) | el bit $k$ de `internal_state` vale 1, sólo en la evaluación de conducta |
| `0x38`–`0x3F` | `HEARD_k`, $k = \text{prom} - \texttt{0x38}$ ($R_{41}$, §9.17) | el bit $k$ de la máscara de símbolos percibidos vale 1, sólo en la evaluación de conducta |
| `0x80`–`0xBF` | $\text{TF}_{\text{prom} - \texttt{0x80}}$ | en la pasada 2, si ese canal está encendido (§9.3) |
| resto | reservados | **nunca** (`0x0B`–`0x0F`, `0x13`–`0x17`, `0x1A`–`0x1F`, `0x2C`–`0x2F`, `0x40`–`0x7F`, `0xC0`–`0xFF`; D61) |

Los promotores espaciales de la Fase III quedan dentro de los reservados inertes.

Los destinos `0x00`–`0x08`, `0x0A`–`0x0C` y `0x0F` son **rasgos**, con base $b_T$ tomada de la configuración base de la población, escala $k_T$ y cotas $[\text{lo}_T, \text{hi}_T]$:

| Destino | Rasgo | $b_T$ | $k_T$ | Cotas | Tipo |
| :---: | :--- | :--- | ---: | :--- | :--- |
| `0x00` | $\alpha$ | `alpha_learning` | 0.40 | $[0.01, 1]$ | real |
| `0x01` | $\gamma$ | `gamma_social_discount` | 0.40 | $[0, 1]$ | real |
| `0x02` | $\epsilon$ | `epsilon_explore` | 0.35 | $[0, 1]$ | real |
| `0x03` | $\omega_{\text{bond}}$ | `initial_bond_affinity` | 0.50 | $[0, 1]$ | real |
| `0x04` | $C_{\max}$ | `memory_capacity` | 3.0 | $[1, C^{\text{tope}}]$ | entero |
| `0x05` | $r_{\text{perc}}$ | `perception_radius` | 2.0 | $[1, r^{\text{tope}}]$ | entero |
| `0x06` | $r_{\text{com}}$ | `comm_radius` | 2.0 | $[1, r^{\text{tope}}]$ | entero |
| `0x07` | $T_{\max}$ | `telomere_base_lifespan` | 250 | $[T_{\min}, T_{\text{tope}}]$ (`telomere_min_lifespan`, `telomere_max_lifespan`) | entero |
| `0x08` | $E_{\text{espora}}$ | `spore_energy_threshold` | 0.50 | $[0, E_{\text{reprod}}]$ | real |
| `0x0A` | compromiso simbiótico $\kappa$ ($R_{31}$) | `symbiotic_commitment_base` | 0.60 | $[0, 1]$ | real |
| `0x0B` | propensión a recombinar $\pi_{\text{rec}}$ ($R_{38}$) | `recombination_base` | 0.60 | $[0, 1]$ | real |
| `0x0C` | propensión a comunicar $\pi_{\text{com}}$ ($R_{32}$) | `comm_propensity_base` | 0.60 | $[0, 1]$ | real |
| `0x0F` | tasa de plasticidad $\eta$ ($R_{40}$, §9.16) | `plasticity_rate_base` | 0.60 | $[0, 1]$ | real |

- La escala 0.60 de `0x0A`–`0x0C` (y no 0.50) hace que un solo codón aditivo con $\delta \ge 0.84$ lleve un rasgo de base 0 al umbral de 0.5; con 0.50, el máximo de un codón sería $0.5 \cdot 0.9921875 < 0.5$, y comunicar, soldarse o recombinar exigiría dos mutaciones coordinadas, cada una neutral por separado (design D46.7).
- `0x09` es `EMIT_TF`: emite el canal `channel` (§9.3).
- `0x40`–`0x47` son **destinos de conducta** (§9.10): en la transcripción del fenotipo son inertes y no cuentan como codones expresados; sólo actúan en la evaluación de impulsos.
- `0x0D` (`SET_STATE`) y `0x0E` (`CLEAR_STATE`) son **destinos de estado** ($R_{39}$, §9.15) y `0x48` (`SIGNAL`) es el **destino de señal** ($R_{41}$, §9.17): en ellos `channel & 0x07` elige el bit o el símbolo, el `payload` se ignora y sólo actúan en la evaluación de conducta.
- `0x10`–`0x3E` y `0x49`–`0xFF` son reservados e **inertes** (órganos y operadores lógicos de la Fase IV), y `0x3F` es el `AST_PIPE` reservado de la Fase IV, también inerte (D61).
- $C^{\text{tope}}$ y $r^{\text{tope}}$ son las cotas de `mutate_genome` de la Fase II (§6.2): `max_genome_memory_capacity`, acotado por $N - 1$ si `enforce_memory_constraint`, y $\lfloor(\min(W, H) - 1)/2\rfloor$.

### 9.3. Transcripción en Dos Pasadas
La transcripción $\Phi(D, \chi) \to$ fenotipo es una función **pura**. Recorre los codones en el orden `chromosome + plasmids`; la memoria CRISPR no se transcribe.
1. **Pasada 1 (contexto).** Son activos los codones con $\text{prom} < \texttt{0x80}$ cuyo promotor está activo en $\chi$. Los promotores sensoriales no se activan en esta transcripción: los rasgos no dependen de la percepción inmediata.
2. **Factores de transcripción.** Entre los activos de la pasada 1, cada codón con destino `EMIT_TF` y modo $\ne 3$ suma 1 a $\text{act}[\text{channel}]$ si su modo es 0 o 2, y a $\text{rep}[\text{channel}]$ si es 1. El canal $j$ está **encendido** si y sólo si
   $$\text{act}[j] > \text{rep}[j].$$
3. **Pasada 2 (regulados).** Son activos los codones con promotor en `0x80`–`0xBF` cuyo canal $\text{prom} - \texttt{0x80}$ está encendido. Sus `EMIT_TF` **no** encienden canales: la red regulatoria tiene **un solo nivel**, y se declara así.

La evaluación de conducta (§9.10) repite estas dos pasadas con la pasada 1 extendida a los promotores sensoriales, de eventos, de estado y de señales percibidas.

### 9.4. Fenotipo Expresado, Costo y ADN Fundador ($R_{24}$)
Para cada destino de rasgo $T$, sea $A_T$ el conjunto de codones activos (pasadas 1 y 2) con ese destino, y $\delta_a$ el efecto de cada uno:
$$S = \sum_{a \in A_T,\ \text{mode}=0} \delta_a, \qquad \rho = \prod_{a \in A_T,\ \text{mode}=1} (1 - |\delta_a|), \qquad \mu = \prod_{a \in A_T,\ \text{mode}=2} (1 + \delta_a),$$
$$x_T = b_T \cdot \mu + k_T \cdot \rho \cdot S.$$
- Los codones de modo 3 se ignoran. Con $A_T = \emptyset$, $x_T = b_T$.
- El represor atenúa sólo la parte aditiva, no la multiplicativa: se declara.
- **Cotas y redondeo.** Un rasgo real vale $\min(\text{hi}_T, \max(\text{lo}_T, x_T))$. Un rasgo entero vale $\min(\text{hi}_T, \max(\text{lo}_T, \lfloor x_T + 0.5 \rfloor))$; no se redondea al par.
- La suma y los productos se acumulan en el orden de recorrido, para que el resultado en coma flotante sea determinista.
- **Fenotipo.** Los destinos `0x00`–`0x06` forman el genoma expresado `AgentGenome`; `0x07` da la vida máxima $T_{\max}$, `0x08` el umbral de esporulación $E_{\text{espora}}$, `0x0A`–`0x0C` el compromiso simbiótico, la propensión a recombinar y la propensión a comunicar, y `0x0F` la tasa de plasticidad (`plasticity_rate`, 0.0 por defecto en `ExpressedPhenotype`). `expressed_codons` cuenta los codones activos con destino de rasgo (`0x00`–`0x08`, `0x0A`–`0x0C` y, desde la ampliación, `0x0F`, precisión 54) y modo $\ne 3$ (telemetría).
- **Bases fijas.** $b_T$ sale siempre de la configuración base de la población, nunca de la del agente, para que la expresión no se acumule de un tick a otro. Sin ADN, el fenotipo es el genoma plano con las bases de los demás rasgos.

**ADN fundador neutro.** El cromosoma fundador tiene $9$ codones (`FOUNDER_DNA_LENGTH`), uno `ALWAYS_BASAL`, `ADDITIVE`, de canal 0 y payload 0 por cada destino `0x00`–`0x08`, sin plásmidos ni memoria CRISPR. Como $\delta = 0$, expresa exactamente la base en todo contexto:
$$\Phi(D_0, \chi).\text{genome} = \texttt{genome\_from\_config}(\text{config}) \quad \forall \chi.$$
No tiene codones sobre `0x0A`–`0x0C`: expresa sus bases. Con la política genética ($R_{32}$) se le agregan cuatro codones de conducta (§9.10), y su longitud pasa a 13 (`founder_dna_length`); entonces la configuración exige `dna_min_length` $\le 13 \le$ `dna_max_length` (precisión 27).

**Expresión en vida.** Al empezar cada tick (Fase 0), cada hoja se expresa con su contexto del final del tick anterior. Si cambia el genoma expresado, cambian su configuración fenotípica y sus radios, y su memoria se ajusta a la nueva $C_{\max}$: si se achica, se desalojan las creencias de menor utilidad con el criterio de $R_2$ (§2.2, con la penalización de $R_{18}$). Ese **olvido forzado** es parte declarada de $R_{24}$. Al nacer, el hijo se expresa con $\chi = (0, \texttt{NONE}, E_{\text{hijo}} / E_{\text{reprod}})$.

**Costo.** El costo cuadrático de $R_{21}$ (§6.1) se cobra sobre el genoma **expresado**, más un costo lineal por codón:
$$c_{\text{base}}(i) = c_{\text{fijo}} + c_{\text{mem}} C_{\max, i}^2 + c_{\text{sens}}(r_{\text{perc}, i}^2 + r_{\text{com}, i}^2) + c_{\text{dna}} \cdot \left(|\text{chromosome}_i| + |\text{plasmids}_i| + |\text{crispr\_memory}_i|\right) + c_{\text{sen}}(i)$$
con $c_{\text{dna}}$ = `dna_codon_cost` y $c_{\text{sen}}$ la senescencia (§9.8). Sin ADN, el término de codones vale 0. Abaratar lo latente (los codones no expresados sólo pagan $c_{\text{dna}}$) es el **sesgo declarado** de $R_{24}$. Los intentos de ataque suman además su costo (§9.12).

**Operadores de mutación (`mutate_dna`).** Al reproducirse, con la escala $s$ de $R_{30}$ (1 si no actúa) y $p_x = \min(1, s \cdot \texttt{dna\_}x\texttt{\_rate})$, sobre `evo_rng` y en este orden:
0. **Puerta de $R_{13}$.** Si `mutation_rate` $= 0$ y `discrete_mutation_prob` $= 0$ (la ablación pre-registrada de $R_{13}$), el ADN se hereda intacto y no se consume el generador.
1. **Mutación puntual del cromosoma:** cada codón, con probabilidad $p_{\text{point}}$, invierte un bit uniforme de sus 32 ($c \leftarrow c \oplus 2^{b}$).
2. **Mutación puntual de los plásmidos:** igual; después se descartan los repetidos (queda el primero) y los que estén en la memoria CRISPR.
3. **Duplicación:** con probabilidad $p_{\text{dup}}$, si $|\text{chromosome}| <$ `dna_max_length`, un codón uniforme se copia en la posición siguiente.
4. **Deleción:** con probabilidad $p_{\text{del}}$, si $|\text{chromosome}| >$ `dna_min_length`, se elimina un codón uniforme.
5. **Escisión a plásmido** (sólo con $R_{26}$): con probabilidad $p_{\text{exc}}$, un codón uniforme del cromosoma se copia al final de los plásmidos, si no está ya en ellos ni en la memoria CRISPR, con descarte FIFO a `max_plasmids`.

La memoria CRISPR se hereda sin mutar. Los pasos 3 a 5 consumen siempre su extracción de decisión; el índice sólo se extrae si el operador se aplica. En la reproducción neutral ($R_{12}$ ablacionada), el donante sorteado aporta su ADN en lugar de su genoma. Con ADN, la reproducción holónica ($R_{17}$) también es neutral: para cada hoja progenitora, en el orden de `leaf_agents`, se sortea con `donor_rng` un donante entre los mismos donantes que la reproducción individual, y la hoja hija recibe su ADN, que después se muta; sin ADN, $R_{17}$ se comporta como en la Fase II (precisión 41). Con $R_{38}$, la mutación se aplica después de la recombinación (§9.13).

### 9.5. Señal Posicional Epigenética ($R_{25}$)
Para un holón raíz $U$, sea $K(\ell)$ el conjunto de patrones de la memoria de la hoja $\ell$ con $c \ge c_{\text{umbral}}$, $\text{unique}(\ell) = \left|K(\ell) \setminus \bigcup_{\ell' \ne \ell} K(\ell')\right|$ y $\deg(\ell) = |\text{loc}(\ell) \setminus \{\ell\}|$, con $\text{loc}$ el alcance local de §7.2. Con $R_{24}$ y $R_{25}$ activas:
1. `LIBRARIAN` es la hoja que maximiza $(\text{unique}(\ell), |K(\ell)|, -\text{id}_\ell)$;
2. `EXPLORER` es, entre las restantes, la que maximiza $(-\deg(\ell), -\text{id}_\ell)$;
3. `NERVE` es, si quedan, la que maximiza $(\deg(\ell), -\text{id}_\ell)$;
4. las demás quedan en `NONE`.

El rol se reasigna sólo cuando cambia el conjunto de hojas de la raíz, y una hoja que queda sola vuelve a `NONE`. **Impronta:** en la reproducción holónica ($R_{17}$), cada hoja hija recibe el rol de su progenitora, y la réplica lo conserva hasta que su composición cambie.

**Reformulación (design D50.1).** La asignación no cambia, pero el rol es sólo una **señal posicional**: actúa únicamente a través de los promotores `0x10`–`0x12`, y el ADN fundador no tiene ningún codón con esos promotores. Cualquier diferencia de expresión entre roles la construye la selección; no hay castas con efectos prefijados.

### 9.6. Plásmidos ($R_{26}$) e Inmunidad CRISPR ($R_{27}$)
- **Conjugación.** Son donantes las hojas que no están en endospora, tienen plásmidos y cumplen $E \ge$ `hgt_energy_ratio` $\cdot E_{\text{reprod}}$. Cada donante, con probabilidad `hgt_rate`, transfiere un plásmido uniforme a un receptor uniforme entre los vecinos a distancia $\le 1$ que no están en endospora. Las extracciones usan el generador dedicado `hgt_rng` (`spawn_key=(5,)`). Las transferencias se sortean todas antes de aplicarlas, y se aplican en el orden de una permutación de `hgt_rng`: varias llegadas al mismo receptor son un conflicto, y se resuelve por sorteo.
- **Recepción.** Un codón que ya está en los plásmidos no cambia nada. Uno nuevo se agrega con FIFO a `max_plasmids`. Con $R_{27}$, un codón que está en la memoria CRISPR se **bloquea**.
- **Ensayo CRISPR.** Con $R_{27}$, cada plásmido recibido abre un ensayo $(t_0, e_0, \text{cedida} = 0)$ en el receptor. Cada hijo que el receptor engendra durante la ventana suma su energía a la cedida de todos sus ensayos abiertos. Al vencer ($t - t_0 \ge$ `crispr_eval_ticks`), si el plásmido sigue presente y
  $$\Delta E = E(t) - e_0 + \text{cedida} < -\,\texttt{crispr\_toxicity\_threshold},$$
  se **purga**: sale de los plásmidos y entra en la memoria CRISPR, con FIFO a `crispr_memory_size`. Si el plásmido ya se perdió, el ensayo se cierra sin purga. Los ensayos no se heredan.
- **Por qué se descuenta lo cedido (decisión del 2026-10-20).** Reproducirse cede `offspring_energy_share` de una energía de al menos $E_{\text{reprod}}$. Sin el descuento, todo receptor que se reproduce en la ventana purgaría el plásmido sin relación con su efecto, y $R_{27}$ castigaría a los exitosos.

### 9.7. Endospora como Conducta ($R_{28}$)
**Entrada (design D50.2).** Una hoja entra en **endospora** sólo cuando su política genética elige la conducta `SPORULATE` (§9.10), que es factible con $R_{32}$, evolución y $R_{28}$ activas y $E_i \le E_{\text{espora}, i}$. La endospora empieza al ejecutarse la acción, en la Fase 4. La entrada automática por umbral de la versión anterior (D38) se eliminó, y sin la política genética $R_{28}$ es inerte. El ADN fundador no tiene codones sobre `0x47`: esporular tiene que evolucionar.

**Germinación y física.** Una endospora **germina** en la Fase 1 en cuanto ve un recurso o, con $R_{19}$, un rastro positivo en su celda, y actúa normalmente ese tick. Mientras es endospora no emite, no recibe mensajes, no decide (su acción es `IDLE`, sin consumir el generador ni sumar oportunidad en M2), no se reproduce, no conjuga ni recombina, no cuenta como vecino activo en la percepción social (así que no recibe `SHARE` ni sufre `ATTACK`), sigue en su holón y su memoria decae. Paga `spore_cost_fraction` $\cdot\, c_{\text{fijo}}$ más la senescencia, en lugar del costo basal, el de ADN, el de movimiento y el de mensajes; sigue pagando su alícuota de coordinación ($R_{23}$). La población **activa** excluye las endosporas.

### 9.8. Senescencia Telomérica ($R_{29}$) y Mutación SOS ($R_{30}$)
- **Edad.** $\text{age}_i(t) = t - t_{\text{nac}, i}$, con $t_{\text{nac}} = 0$ en los fundadores. La Fase II-B registra el tick de nacimiento en el agente (`birth_tick`).
- **Senescencia ($R_{29}$).** Con evolución y $R_{29}$ activas, el cobro metabólico suma
  $$c_{\text{sen}}(i) = \texttt{senescence\_cost\_rate} \cdot \max(0, \text{age}_i - T_{\max, i})^2,$$
  también a las endosporas. Con ADN, $T_{\max, i}$ se expresa por el destino `0x07`; sin ADN, vale `telomere_base_lifespan`. Motivación: el "Tapón de Matusalén" confirmado en la tarea 0.1 ([RESULTADOS.md](RESULTADOS.md)).
- **Registro del estrés.** Siempre que hay metabolismo (aunque $R_{30}$ esté apagada), cada sobreviviente con $E_i <$ `stress_energy_ratio` $\cdot E_{\text{reprod}}$ registra $t_{\text{estrés}, i} = t$.
- **SOS ($R_{30}$).** Al reproducirse, con el estado del progenitor antes de partir la energía, la escala de mutación es
  $$s = \begin{cases} \texttt{sos\_hypermutation\_factor} & \text{si } t - t_{\text{estrés}} \le \texttt{sos\_window}, \\ \texttt{sos\_high\_fidelity\_factor} & \text{si no, y } E \ge \texttt{sos\_high\_fidelity\_energy\_ratio} \cdot E_{\text{reprod}}, \\ 1 & \text{en otro caso.} \end{cases}$$
  Con ADN escala las probabilidades de `mutate_dna`; sin ADN escala `mutation_rate` y `discrete_mutation_prob` de `mutate_genome` (recortando la segunda a 1). Con $R_{30}$ apagada, $s = 1$.

### 9.9. Compromiso Simbiótico ($R_{31}$)
**Sello (design D50.3).** Con el ADN, la jerarquía y $R_{31}$ activas (sin ADN, $R_{31}$ es inerte aunque `symbiotic_commitment_base` $\ge 0.5$), en el paso de coordinación de la Fase 5, un holón raíz no soldado queda **soldado** si la media del compromiso simbiótico $\kappa$ expresado (destino `0x0A`) de sus hojas es $\ge 0.5$. El sello es permanente y se aplica antes de cobrar la coordinación y de evaluar `SPLIT`, así que rige desde ese mismo tick. Con `symbiotic_commitment_base = 0` (el valor por defecto), ningún holón fundador se suelda: el compromiso tiene que evolucionar. Las condiciones de sellado de la versión anterior (reproducirse por $R_{17}$ o alcanzar `lock_composite_threshold` compuestos resueltos) se eliminaron, y el parámetro con ellas.

**Efectos.** Un holón soldado no se disuelve por `SPLIT` (ni por paciencia ni por energía) y su costo de coordinación se multiplica por `lock_coord_discount`, sólo si es la raíz la soldada. La poda por muerte sigue actuando (con una sola hoja sobreviviente, colapsa), y un holón soldado puede fusionarse por `BOND` en un nivel superior.

### 9.10. Conducta Codificada en el ADN ($R_{32}$)
**Puerto de política (design D45).** La decisión de la Fase 3 pasa por un puerto `PolicyPort`. La política escrita a mano de la Fase I (§6 de [Definiciones Técnicas](DEFINICIONES_TECNICAS.md), "Toma de decisión") es `HandwrittenPolicy`, sin cambios. Con $R_{24}$ y $R_{32}$ activas, los fundadores usan `GeneticPolicy` y la propagan a sus descendientes.

**Conductas.** Cada conducta $B$ tiene un destino de codón. El orden de la tabla es el orden de desempate:

| Destino | Conducta | Acción | Factible si |
| :---: | :--- | :--- | :--- |
| `0x40` | `CONSUME` | `INTERACT` sobre el recurso alcanzable conocido y benéfico de mayor $\hat{v} \cdot c$ (desempate por menor `resource_id`) | existe alguno |
| `0x41` | `EXPLORE` | `INTERACT` sobre el recurso alcanzable desconocido de menor `resource_id` | existe alguno **y** `rng.random()` $< \epsilon$ expresado (la extracción ocurre sólo si existe alguno) |
| `0x42` | `NAVIGATE` | `MOVE` con el `recommended_move` del objetivo conocido benéfico no alcanzable más cercano | `enable_navigation` y existe alguno |
| `0x43` | `WANDER` | `MOVE` a un movimiento disponible uniforme | hay movimientos disponibles |
| `0x44` | `SHARE` | `SHARE` sobre el vecino adyacente de menor energía | $R_{36}$ activa, hay vecinos adyacentes y $E_i > 0$ |
| `0x45` | `ATTACK` | `ATTACK` sobre el vecino adyacente de menor energía | $R_{37}$ activa y ese vecino tiene menos energía que el agente |
| `0x46` | `FLEE` | `MOVE` que aleja del vecino visible más cercano con más energía | existe ese vecino |
| `0x47` | `SPORULATE` | `SPORULATE` | `enable_evolution` y `enable_sporulation` activas y $E_i \le E_{\text{espora}, i}$ |

**Promotores sensoriales.** Leen el vector $\sigma$ de señales del tick, que la política arma a partir de la observación, de sus creencias efectivas y de la percepción social. "Activo" excluye a las endosporas, y la percepción social es sincrónica: usa las energías del comienzo del tick.

| Promotor | Señal | Activo si |
| :---: | :--- | :--- |
| `0x20` | `SENSE_KNOWN_GOOD` | algún recurso visible es conocido y benéfico |
| `0x21` | `SENSE_UNKNOWN` | algún recurso visible es desconocido |
| `0x22` | `SENSE_NO_RESOURCE` | no hay recursos visibles |
| `0x23` | `SENSE_NEIGHBOR_ADJACENT` | hay un agente activo a distancia $\le 1$ |
| `0x24` | `SENSE_WEAKER_ADJACENT` | el adyacente de menor energía tiene menos que el agente |
| `0x25` | `SENSE_STRONGER_NEAR` | hay un agente activo visible con más energía que el agente |
| `0x26` | `SENSE_CROWDED` | los agentes activos visibles son al menos `crowding_threshold` |
| `0x27` | `SENSE_CARCASS` | algún recurso visible es un cadáver ($R_{35}$) |

**Impulsos.** La evaluación de conducta `evaluate_behavior` (D60.1; `evaluate_drives` se conserva y devuelve sólo sus impulsos) repite las dos pasadas de §9.3 con la pasada 1 extendida a los promotores sensoriales y, con la ampliación, a los de eventos, estado y señales percibidas (§9.15–§9.17). Además de los impulsos, devuelve las máscaras de escritura del estado, la de símbolos emitidos y los codones plásticos activos por conducta. Para cada conducta $B$, con $A_B$ sus codones activos de modo $\ne 3$ y, con $R_{40}$, $P_B$ sus codones activos de modo 3 (§9.16):
$$S_B = \sum_{a \in A_B,\ \text{mode}=0} \delta_a + \sum_{a \in P_B} (\delta_a + w_a), \qquad \rho_B = \prod_{a \in A_B,\ \text{mode}=1} (1 - |\delta_a|), \qquad \mu_B = \prod_{a \in A_B,\ \text{mode}=2} (1 + \delta_a),$$
$$d_B = \mu_B \cdot \rho_B \cdot S_B,$$
sin cotas, con $d_B = 0$ si $A_B \cup P_B = \emptyset$, y acumulado en el orden de recorrido. Sin $R_{40}$, $P_B = \emptyset$. A diferencia de un rasgo, un impulso no tiene base: sin un codón aditivo la conducta no se considera.

**Decisión.** `GeneticPolicy` recorre las conductas con $d_B > 0$ en orden de $(-d_B, \text{posición en la tabla})$ y devuelve la acción de la primera factible; si ninguna lo es, devuelve `IDLE`. La factibilidad se evalúa de a una, en el orden de prueba, y se detiene en la primera factible: el generador sólo se consume en `EXPLORE` y `WANDER` cuando el recorrido llega a ellas. Los impulsos se evalúan con el contexto de la última expresión del agente (`last_context`: el de la Fase 0 del tick, o el de nacimiento). Sin percepción social, las señales sociales son falsas y `SHARE`, `ATTACK` y `FLEE` no son factibles. Una endospora no decide.

**"Con la política genética"** quiere decir que $R_{32}$ está efectivamente activa: $R_{24}$ y `enable_genetic_policy`. Con `enable_genetic_policy` y sin ADN, $R_{32}$ es inerte: no hay percepción social, la puerta de comunicación no actúa y la política es la escrita a mano.

**Fundador conductual neutro.** Con $R_{32}$, el ADN fundador de §9.4 agrega cuatro codones `ALWAYS_BASAL` aditivos sobre `CONSUME`, `EXPLORE`, `NAVIGATE` y `WANDER`, con payloads 127, 96, 64 y 32. Sus impulsos son 0.9921875, 0.75, 0.5 y 0.25, y el orden de prueba reproduce **exactamente** la política escrita a mano, incluidas las extracciones del generador. Por eso, con el ADN fundador, sin mutación y sin costo por codón (`dna_codon_cost = 0`, porque el fundador conductual tiene 13 codones y no 9), las corridas con y sin $R_{32}$ producen historiales idénticos (test de aceptación). El fundador no tiene codones sobre `SHARE`, `ATTACK`, `FLEE` ni `SPORULATE`, ni promotores sensoriales: toda conducta nueva, y toda conducta condicionada a la percepción, tiene que evolucionar.

**Comunicación.** Con la política genética, el agente emite y responde consultas en el tick sólo si su propensión a comunicar expresada (destino `0x0C`) es $\pi_{\text{com}} \ge 0.5$; si no, no emite ni responde, pero sigue recibiendo y asimilando testimonios. La puerta vive en `protocol.py` y no consume generadores. Con la política escrita a mano, el agente siempre comunica. El ADN decide **si** se comunica, nunca **qué**: el contenido sigue siendo el de la Fase I, y el conocimiento social sigue entrando sólo por `assimilate_testimony`.

### 9.11. Ecología del Entorno ($R_{33}$, $R_{34}$, $R_{35}$)
- **Recursos agotables ($R_{33}$).** Un recurso elemental consumido en el tick $t$ no reaparece en el tick siguiente, sino en $t + $ `resource_regen_delay` (con el retardo de la estación del tick de consumo, si hay estaciones), en una celda sorteada con el generador del entorno; los agendados se reponen en orden de (vencimiento, orden de consumo). Los recursos compuestos no cambian.
- **Heterogeneidad ($R_{34}$).** La grilla se divide en `num_regions` franjas verticales de ancho $\lfloor W / \texttt{num\_regions} \rfloor$ (la última absorbe el resto). El patrón elemental $i$ (el $i$ de su nombre `p_i`, no su posición en el orden de `Pattern`) tiene como región propia $i \bmod$ `num_regions`, y sus recursos se ubican, al inicio y al reponerse, en una celda sorteada dentro de ella. Con `season_length` $> 0$, la estación es $\lfloor t / \texttt{season\_length} \rfloor \bmod 2$, y en la estación 1 (invierno) el retardo de $R_{33}$ se multiplica por `winter_regen_factor` y se redondea con $\lfloor x + 0.5 \rfloor$. Sin $R_{33}$, las estaciones son inertes.
- **Cadáveres ($R_{35}$, sólo con evolución).** Al morir un agente, por hambre o por depredación, el entorno deposita en su celda un recurso de patrón `CARCASS_PATTERN` y valor `carcass_value`. Se consume con `INTERACT` como cualquier recurso, da $\eta_E \cdot$ `carcass_value` y se aprende por experiencia directa. No se repone, y se retira solo `carcass_lifetime` ticks después de depositado. Varios cadáveres del mismo tick se depositan en orden de `agent_id`; las perturbaciones (`ablate_population`, `ablate_discoverers`) no dejan cadáver. Comerlo sigue el camino de cualquier recurso elemental (cuenta como descubrimiento directo y, con $R_{19}$, deposita estigmergia). No forma parte de los patrones del mundo, así que la cobertura no lo ve, pero es un recurso elemental alcanzable y entra en el oráculo de M2.

### 9.12. Interacciones entre Agentes ($R_{36}$, $R_{37}$)
Se ejecutan en la Fase 4, en el orden de la permutación del tick, junto con las demás acciones, y las aplica el motor. Ninguna crea energía: `share_efficiency` $\le 1$ y `predation_efficiency` $\le 1$.
"Sigue vivo" quiere decir "sigue en la población": nadie muere en la Fase 4.
- **Transferencia ($R_{36}$).** `SHARE` sobre un objetivo vivo que no es endospora, con el donante en $E > 0$: el donante pierde $a = $ `share_fraction` $\cdot E_{\text{donante}}$ y el receptor gana `share_efficiency` $\cdot\, a$. Si no, no ocurre nada.
- **Depredación ($R_{37}$).** Cada intento de `ATTACK` cuesta `attack_cost` en el metabolismo, haya éxito o no. Tiene éxito si el objetivo sigue vivo, no es endospora y el atacante tiene estrictamente más energía que él **al ejecutarse**. Con éxito, $s = \min(\texttt{attack\_power}, \max(0, E_{\text{objetivo}}))$: el objetivo pierde $s$ y el atacante gana `predation_efficiency` $\cdot\, s$ (un objetivo con $E \le 0$ rinde $s = 0$). Un objetivo que queda con $E \le 0$ muere en el paso de muerte de la Fase 5 y, con $R_{35}$, deja un cadáver.
- **M2 (precisión 21).** M2 juzga **decisiones**, no acciones: si un agente tiene recursos elementales alcanzables (incluidos los cadáveres) y elige `FLEE`, `SHARE`, `ATTACK` o `SPORULATE`, la decisión cuenta como oportunidad y se juzga como hoy, como una decisión que no es `INTERACT` sobre el mejor recurso.

### 9.13. Recombinación ($R_{38}$)
Con $R_{24}$, evolución y $R_{38}$ activas, en la reproducción individual ($R_{12}$, no en $R_{17}$):
1. **Parejas.** El progenitor busca pareja si su propensión a recombinar expresada (destino `0x0B`) es $\pi_{\text{rec}} \ge 0.5$. Las candidatas son, ordenadas por `agent_id`, las demás hojas vivas al empezar el paso de reproducción (los nacidos en el mismo paso no cuentan), no endosporas, con ADN, a distancia $\le 1$ y con $\pi_{\text{rec}} \ge 0.5$. Sin candidatas, la reproducción es asexual.
2. **Cruce de un punto.** Con `evo_rng` se sortean la pareja y los puntos de corte $a \in [1, |\text{cromosoma}_{\text{progenitor}}|]$ y $b \in [0, |\text{cromosoma}_{\text{pareja}}| - 1]$. El cromosoma recombinado es $\text{progenitor}[{:}a] \,\Vert\, \text{pareja}[b{:}]$, truncado a `dna_max_length` (se conserva el prefijo); si queda más corto que `dna_min_length`, se usa el del progenitor. Plásmidos y memoria CRISPR son los del progenitor.
3. **Después,** el ADN recombinado se muta con `mutate_dna` (§9.4), como el de cualquier hijo. La pareja no cede energía.

Con `recombination_base = 0` (el valor por defecto), ningún fundador recombina: la reproducción sexual tiene que evolucionar.

**En la reproducción neutral (`drift`).** Con la reproducción neutral, el primer cromosoma del cruce es el ADN del donante sorteado con `donor_rng`; la pareja y la propensión son las del agente que se reproduce. Las extracciones van en este orden: el donante (`donor_rng`), el cruce (`evo_rng`) y la mutación (`evo_rng`). Así, `drift` sólo quita la selección y conserva la recombinación.

### 9.14. Orden del Tick y Telemetría de Evolución Abierta
**Motor por sistemas (design D44).** El tick se ejecuta como un pipeline ordenado de sistemas, y la telemetría sale del bucle a observadores. El refactor no cambia ningún comportamiento: los hashes dorados de la Fase I y las huellas de la Fase II se conservan.

**Orden (design D53, con la ampliación D58–D62).**
- **Al empezar el tick, antes de la Fase 0**, con `world_shift_period > 0`, en cada tick $t > 0$ con $t \bmod$ `world_shift_period` $= 0$: cambio del entorno (§9.18, precisión 56), con el generador principal.
- **Fase 0:** expresión de todas las hojas (§9.4), sin consumir generadores ni introducir efectos de orden.
- **Fase 1:** percepción, germinación, percepción social, percepción de los símbolos emitidos en el tick anterior ($R_{41}$, con el control nulo si corresponde; §9.17), emisión con la puerta de comunicación, estigmergia y vista del holón (tiempo 1).
- **Fase 2:** intercambio social en dos pasadas y vista del holón (tiempo 2).
- **Fase 3:** decisión con la política de cada agente, evaluada con el estado interno, los eventos y los símbolos percibidos **anteriores**, y emisión de símbolos ($R_{41}$); contexto de los compuestos. Al terminar la fase se aplica el estado interno nuevo ($R_{39}$, §9.15).
- **Fase 4:** ejecución en el orden de la permutación (movimientos, recursos, `SHARE`, `ATTACK` y `SPORULATE`), aprendizaje directo, energía y estigmergia; con $R_{40}$, la actualización de los pesos plásticos inmediatamente después de la acción de cada agente (§9.16).
- **Fase 5:** (i) olvido; (ii) coordinación, sello de $R_{31}$, `SPLIT` y `BOND`; (iii) metabolismo, con ADN, senescencia, endospora, costo de los ataques y costo de los símbolos emitidos ($R_{41}$); (iv) muerte, cadáveres y registro del estrés; (v) reproducción, con SOS, recombinación, ADN e impronta; (vi) conjugación y ensayo CRISPR; (vii) $R_{18}$ y roles; (viii) dinámica del entorno, con la reposición de $R_{33}$ y $R_{34}$ y el retiro de cadáveres.
- **Al terminar el tick:** el motor calcula los eventos del tick (`EventSignals`, §9.15) y los guarda en cada agente para la evaluación del tick siguiente.
- Sin las banderas nuevas, el orden se reduce exactamente al de la Fase II.

**Telemetría genética (`GeneticTickMetrics`).** Además de la longitud media del cromosoma, los codones expresados y los plásmidos, las endosporas, los senescentes ($\text{age} > T_{\max}$), la edad media y máxima, el conteo de cada rol, los holones soldados y los eventos de conjugación, rechazo CRISPR y purga, registra las **métricas de evolución abierta**, sobre las hojas vivas al final del tick. Las "decisiones del tick" son las de las hojas vivas que no estaban en endospora en la Fase 3, incluidas las que terminan en `IDLE`:
- `distinct_genotypes`: cantidad de cromosomas distintos.
- `mean_functional_codons` (descriptiva): media de codones con destino de rasgo (`0x00`–`0x08`, `0x0A`–`0x0C` y, por la precisión 54, `0x0F`) o de conducta (`0x40`–`0x47`) y modo $\ne 3$, cualquiera sea su promotor.
- **Codones expresables de una hoja (precisión 42).** C13 y C17 se miden sobre el **genotipo** y el protocolo, no sobre el estado del tick: no dependen de quién decidió, de las endosporas ni de las señales del entorno. Con `holonic = enable_holonic_hierarchy` y `roles = enable_epigenetic_roles`:
  - un promotor es **expresable** si es `0x00`, `0x01`, `0x18` o `0x19`; `0x02`–`0x0A` sólo si `holonic`; `0x10`–`0x12` sólo si `holonic` y `roles`; `0x20`–`0x27` sólo sobre destinos de conducta; los de eventos, estado y señales percibidas (`0x28`–`0x2B`, `0x30`–`0x37` y `0x38`–`0x3F`, D61) sólo sobre destinos de conducta, de estado y de señal, y son siempre **condicionales**; y `0x80`–`0xBF` si su canal tiene en `chromosome + plasmids` (nunca en `crispr_memory`) algún emisor activador (`EMIT_TF` de modo 0 o 2) con promotor expresable menor que `0x80`. Los emisores con promotor sensorial (`0x20`–`0x27`) encienden canales sólo para codones de conducta, porque en la evaluación de conducta los sensores actúan y en la transcripción del fenotipo están inactivos;
  - un promotor es **condicional** si es expresable y no constitutivo. Son constitutivos `0x00`, `0x01` sin holones y `0x80`–`0xBF` cuando algún emisor activador de su canal es constitutivo; esto último es una aproximación declarada, que no considera los represores;
  - **valor canónico:** el campo `channel` (bits 8–13) no tiene efecto en los destinos de rasgo ni en los de conducta `0x40`–`0x47`, así que esos codones se comparan por `codon & ~0x3F00` y dos que difieren sólo en `channel` son sinónimos y cuentan una vez. En `SET_STATE`, `CLEAR_STATE` y `SIGNAL` el canal elige el bit o el símbolo, así que no se enmascara (D61);
  - **funcionales:** los codones con destino de rasgo (incluido `0x0F`, precisión 54) o de conducta y modo $\ne 3$ y, desde la ampliación, los de estado (`0x0D`, `0x0E`) y de señal (`0x48`) con modo $\ne 3$ (D61);
  - `expressible_codons(dna, holonic, roles)`, pura en `dna.py`, devuelve los **valores canónicos distintos**, ascendentes, de los codones **funcionales** de `chromosome + plasmids` con promotor expresable, cada uno con si su promotor es condicional.
- `mean_conditional_codons` (métrica de C13): media, sobre las hojas con ADN, de la cantidad de esos valores con promotor condicional. Mide el **numerador**: una fracción podría subir sólo porque la selección borra los 9 codones de rasgo fundadores, que tienen `payload` 0, no aportan nada y cuestan energía.
- `mean_expressible_nonattack_codons` (métrica de C17): media, sobre las hojas con ADN, de la cantidad de esos valores cuyo destino no es `0x45` (`ATTACK`). En `no_predation` esos codones son inertes, y un solo codón `ATTACK` alcanzaría $\delta_{\min}$ sin complejidad nueva.
- `mean_expressible_codons` (descriptiva): la misma media con todos los valores, también los de `ATTACK`. Duplicar un codón, mutar un bit sinónimo o acumular codones inertes no suma.
- `regulated_expression_fraction` (descriptiva): media, sobre las hojas con ADN, de la fracción de esos valores cuyo promotor es condicional. Una hoja sin codones expresables aporta 0.
- `policy_divergence` (C14): entre las decisiones del tick con la política genética, la fracción en que la primera conducta factible según el ADN del agente difiere de la del ADN fundador, evaluadas con las mismas señales y factibilidades (con `EXPLORE` tomada como factible si hay recursos desconocidos alcanzables, sin extraer del generador); 0 sin decisiones.
- `communicating_fraction` (C15): fracción de hojas activas con $\pi_{\text{com}} \ge 0.5$.
- **Actividad evolutiva de Bedau–Packard por nacimientos** (C16, precisión 43). Para cada valor canónico $c$ **ausente del cromosoma de `founder_dna(config)`** (los fundadores cruzan el umbral en las dos condiciones y sólo agregarían un término demográfico), $a_c(t)$ cuenta, desde el tick 0 hasta $t$, los individuos que **nacieron** portando $c$ en `chromosome + plasmids` más las recepciones por conjugación ($R_{26}$) que agregaron $c$:
  $$a_c(t) = \left|\{\, i \text{ nacido en } s \le t : c \in \text{chromosome}_i \cup \text{plasmids}_i \,\}\right| + \left|\{\, \text{recepciones en } s \le t \text{ que agregaron } c \,\}\right|.$$
  Sólo cuentan los valores canónicos de codones **funcionales** (no los `EMIT_TF`, ni los de modo 3, ni los reservados); los fundadores no son "nacidos", y una recepción cuenta sólo si el receptor no portaba $c$.
  No depende de cuánto vive cada portador: la versión anterior, tick a tick, premiaba la longevidad, porque una sola hoja que vivía 500 ticks hacía cruzar el umbral a su codón sin transmitirlo nunca. Un individuo aporta 1 por valor canónico aunque lo porte varias veces. Un codón cruza el umbral en $t$ si $a_c(t-1) <$ `activity_threshold` $\le a_c(t)$, con `activity_threshold` $= 10$ nacimientos portadores. `new_activity` cuenta los codones que lo cruzaron en el tick, y `cumulative_new_activity` es su suma acumulada. La métrica de C16 es `new_activity_per_birth` $=$ `cumulative_new_activity` / `cumulative_births` (0 sin nacimientos; `cumulative_births` suma, desde el tick 0, los `births` de `evolutionary_history`, individuales y holónicos), que normaliza la actividad por el aporte de variación, distinto entre `full` y `drift` (precisión 43). Un componente nuevo que persiste acumula actividad; uno que la deriva introduce y pierde enseguida, no.
- `mean_age_at_death` (covariable de la longevidad; precisión 49): media acumulada de `tick - birth_tick` de las muertes desde el tick 0 (0 sin muertes).

**Telemetría de la ampliación (D63.2), al final de `GeneticTickMetrics`:**
- `mean_internal_state_bits`: media de bits encendidos de `internal_state` en las hojas vivas;
- `mean_plasticity_rate`: media de la $\eta$ expresada;
- `mean_abs_plastic_weight`: media de $|w_i|$ sobre todos los pesos de las hojas vivas (0 sin pesos);
- `mean_learning_codons` (métrica de C19, precisión 52): media, sobre las hojas con ADN, de la cantidad de valores canónicos distintos (D61) de `chromosome + plasmids` con promotor expresable en el protocolo que cumplen alguna de estas condiciones: destino `0x0D` o `0x0E` con modo $\ne 3$; promotor `0x30`–`0x37` sobre un destino de conducta, de estado o de señal; o modo 3 sobre un destino de conducta, en una hoja con `plasticity_rate` $> 0$. No se limita a los codones funcionales de la precisión 42, que excluyen el modo 3;
- `signaling_rate`: fracción de las decisiones del tick cuyo agente emitió al menos un símbolo;
- `symbol_diversity`: cantidad de símbolos distintos emitidos en el tick;
- `max_signal_information` (descriptiva): el máximo, sobre los pares (símbolo $k$, campo $j$ de `SensorySignals` del emisor), de la información mutua en bits entre "emitió $k$" y "$j$ es verdadero" en las decisiones del tick (0 sin decisiones). Mide si los símbolos llevan información sobre lo que percibe el emisor.

**Telemetría ecológica (`EcologyTickMetrics`).** Recursos disponibles, cesiones, ataques y ataques exitosos, muertes por depredación y por hambre, cadáveres depositados y comidos, esporulaciones y recombinaciones del tick; `share_rate` (métrica de C18: cesiones sobre decisiones del tick, 0 sin decisiones) y `behavior_counts` (decisiones del tick por conducta, en el orden de la tabla de §9.10). La ampliación (D63.3 y D63.4) agrega `signals_emitted` (símbolos emitidos en el tick), `plastic_updates` (actualizaciones de pesos con $r \ne 0$) y `decision_opportunities` y `correct_decisions` (las oportunidades y los aciertos de M2 del tick, que usa C20). Ninguna telemetría consume generadores, y `TickMetrics` y `EvolutionaryTickMetrics` no cambian.

### 9.15. Estado Interno Persistente ($R_{39}$, design D58)
Con la política genética ($R_{32}$) y $R_{39}$ activas, cada hoja tiene un estado interno $s_i \in [0, 255]$ (`internal_state`, 8 bits), que vale 0 al nacer, no se hereda y se conserva en la endospora.
- **Escritura.** En la evaluación de conducta del tick, para cada bit $k$: `set` vale si los codones activos de `SET_STATE` (`0x0D`) con `channel & 0x07` $= k$ y modo 0 o 2 superan en número a los de modo 1, y `clear`, lo mismo con `CLEAR_STATE` (`0x0E`); es la regla de mayoría de los canales de §9.3. Si valen los dos, prevalece `clear`:
  $$s_i' = (s_i \mathbin{|} \text{set\_mask}) \mathbin{\&} \lnot\,\text{clear\_mask}.$$
  El estado nuevo se aplica al terminar la Fase 3: la decisión del tick usa siempre el estado anterior.
- **Lectura.** Los promotores `STATE_k` (`0x30`–`0x37`) están activos si el bit $k$ vale 1.
- **Eventos del tick anterior.** `EventSignals` tiene cuatro campos: `attacked` (fue objetivo de un ataque con éxito con `stolen` $> 0$), `ate` (consumió un recurso con valor experimentado positivo), `lost_energy` (terminó el tick con menos energía que al empezarlo) y `received_energy` (fue objetivo de un `SHARE` que lo alcanzó). El motor los calcula al terminar el tick y los guarda en `last_events`; un recién nacido arranca con todos en falso. Los promotores `0x28`–`0x2B` los leen. Son percepción, no memoria: siguen disponibles con $R_{32}$ aunque $R_{39}$ esté apagada.
- Los promotores de eventos y de estado sólo actúan en la evaluación de conducta: en la transcripción del fenotipo están inactivos.
- **Sin $R_{39}$,** los destinos `0x0D` y `0x0E` y los promotores `0x30`–`0x37` son inertes y `internal_state` queda en 0.

### 9.16. Plasticidad en Vida ($R_{40}$, design D59)
Con la política genética y $R_{40}$ activas, un codón activo de modo 3 sobre un destino de conducta suma a $S_B$ el efecto $\delta_{\text{ef}} = \delta + w_i$, con $w_i$ su **peso aprendido** (§9.10). Sobre cualquier otro destino, y en la transcripción del fenotipo, sigue inerte.
- **Pesos.** `plastic_weights` se indexa por la posición del codón en `chromosome + plasmids`. Empieza vacío (todos los pesos en 0) al nacer, **no se hereda** y se vacía cuando cambia el ADN del agente (por conjugación o purga), porque las posiciones cambian.
- **Tasa.** El destino `0x0F` expresa la tasa $\eta \in [0, 1]$, con base `plasticity_rate_base` $= 0$: al empezar nadie aprende, y aprender tiene que evolucionar.
- **Regla de aprendizaje, mínima y declarada.** En la Fase 4, inmediatamente después de ejecutar la acción del agente, con $r$ la recompensa y $E$ los codones elegibles:
  - $r$ es el cambio de energía del agente causado por esa acción (consumir un recurso o un cadáver, ceder energía o robarla); vale 0 en `MOVE`, `IDLE` y `SPORULATE`, y no incluye lo que le hagan otros agentes ni los costos de la Fase 5;
  - $E$ son los codones de modo 3 activos en la evaluación del tick con destino igual a la conducta elegida;
  - $$w_i \leftarrow \min\big(1, \max(-1,\ w_i + \eta \cdot r)\big) \quad \forall i \in E.$$
  Es una regla de refuerzo del tipo Rescorla–Wagner, sin predicción de valor ni exploración propia. Se declara como capacidad: **qué** se aprende (qué codones son plásticos) y **cuánto** ($\eta$) lo decide el ADN. Lo aprendido no se hereda, lo que permite medir el efecto Baldwin.
- **Caché.** Los impulsos se pueden memoizar sin los pesos, guardando la lista de codones plásticos por conducta; los pesos se suman después. Un test exige igualdad con la evaluación directa.
- **Sin $R_{40}$,** el modo 3 es inerte también en la conducta y los pesos no se actualizan.

### 9.17. Señales Evolucionables ($R_{41}$, design D60)
Con la política genética y $R_{41}$ activas:
- **`SIGNAL` no es una conducta.** El destino `0x48` no compite en la decisión ni ocupa la acción del tick: emitir y actuar ocurren a la vez. Su `channel & 0x07` elige el símbolo $k \in \{0, \dots, 7\}$.
- **Emisión.** En la evaluación de conducta de la Fase 3, el símbolo $k$ se emite si los codones activos de `SIGNAL` sobre $k$ con modo 0 o 2 superan en número a los de modo 1 (regla de §9.3). Cada símbolo emitido cuesta `signal_cost`, que se cobra en el metabolismo. Las endosporas no emiten.
- **Percepción.** Los símbolos emitidos en la Fase 3 del tick $t$ los perciben, en la Fase 1 del tick $t + 1$, los agentes que eran vecinos de comunicación del emisor en el tick $t$ (los de su observación) y siguen vivos y activos. La máscara percibida es el OR de las recibidas, y los promotores `HEARD_k` (`0x38`–`0x3F`) leen su bit $k$, sólo en la evaluación de conducta. La percepción es sincrónica: nadie percibe una señal del mismo tick.
- **Control nulo.** Con `comm_content_null`, la máscara percibida no vacía de cada receptor se reemplaza, en orden de `agent_id`, por `int(null_rng.integers(1, 256))`: la señal conserva su presencia y pierde su contenido, como los mensajes de E4.
- **Lo que no son.** Las señales no son `Message` ni creencias: no pasan por `protocol.py` ni por `assimilate_testimony` y nunca se escriben en la memoria. Son un canal sensorial, como ver a un vecino; su significado, si aparece, lo construye la evolución.
- **Sin $R_{41}$,** el destino `0x48` y los promotores `0x38`–`0x3F` son inertes y no hay emisión ni costo.

### 9.18. Entorno Cambiante y ADN de 64 Codones (design D62)
- **Cambios del entorno.** Con `world_shift_period` $> 0$, al empezar el tick, antes de la Fase 0, en cada tick $t > 0$ con $t \bmod$ `world_shift_period` $= 0$ (precisión 56), el motor invierte una fracción `world_shift_fraction` de las reglas del mundo (`invert_world_rules`, con el generador principal). No es una regla de diseño del agente: es una manipulación experimental del entorno, como las perturbaciones de la Fase I. Con 0 (el valor por defecto) no hay cambios.
- **ADN de 64 codones.** Los protocolos de §3.1 fijan `dna_max_length = 64`; el valor por defecto de la configuración sigue en 32, así que ningún historial existente cambia. Como cada codón cuesta $c_{\text{dna}}$, la selección decide si conviene crecer.
- **Generadores.** La ampliación no agrega generadores (D57.4): el control nulo de las señales usa `null_rng` y los cambios del entorno, el generador principal.
