# Especificación de Definiciones Formales — Proyecto IDE (v2.0)

Este documento establece de manera rigurosa y sin ambigüedades qué significa cada concepto dentro del sistema de **Inteligencia Distribuida Emergente (IDE)** antes de escribir código. Toda implementación debe respetar estas definiciones.

> **Novedades en la Versión 2.0:** Esta versión conserva íntegramente las definiciones y métricas verificadas de la **Fase I (Experimento 001)** y extiende la ontología matemática hacia la **Fase II (Experimentos 002–003)**:
> 1. **Metabolismo, muerte y reproducción intergeneracional ($g \to g+1$).**
> 2. **Herencia Dual:** herencia genética con mutación sobre $\Theta_i$ y capacidades $\mathcal{G}_i$ + herencia cultural vertical de creencias $\mathcal{M}_{\text{padre}} \to \mathcal{M}_{\text{hijo}}$.
> 3. **Arquitectura Holónica / Jerarquía Recursiva ($L \in \mathbb{N}_0$):** formalización del **Holón** (`AgentNode`) mediante el patrón recursivo *Composite*, donde tanto un agente elemental ($L=0$) como una coalición de coaliciones de nivel arbitrario ($L = 1, 2, \dots, K$, sin tope de niveles codificado) exponen la misma interfaz estructural (`node_id`, `holon_level`, `leaf_agents`, `effective_capacity`, `collective_memory`). Percibir, decidir y actuar siguen siendo operaciones de las hojas ($L = 0$); los holones se forman y disuelven con los operadores `BOND` y `SPLIT`.

> **Relación con los demás documentos.** La visión está en el [Documento Fundacional](DOCUMENTO_FUNDACIONAL.md) y la arquitectura en las [Definiciones Técnicas](DEFINICIONES_TECNICAS.md). Los requisitos vigentes de la Fase I están en [`openspec/specs/`](openspec/specs/), y sus valores numéricos, firmas y reglas de desempate exactos, en el diseño archivado [`design.md`](openspec/changes/archive/2026-10-17-ide-emergent-distributed-intelligence/design.md) (Decisiones D1–D18). Para la Fase II rige [`openspec/changes/ide-v2-evolutionary-holonic-intelligence/design.md`](openspec/changes/ide-v2-evolutionary-holonic-intelligence/design.md) (Decisiones D19–D29), que es la fuente única de sus fórmulas, nombres, valores por defecto y desempates: §6–§8 lo resumen y, ante una discrepancia, rige el design. Los valores que aparecen aquí como "ej." son ilustrativos.

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
- **Condición de resolución (física del entorno):** cuando la hoja $a$ ejecuta `INTERACT` sobre un recurso compuesto, sea $\mathcal{K}_{\text{eff}}$ el conjunto de patrones $\rho$ para los que alguna hoja en alcance local de $a$ dentro de su holón raíz $U$ (§7.2), o sólo $a$ si no pertenece a un holón, sostiene como creencia propia (`own_belief`: su memoria o su caché efímero del tick, que incluye lo que obtuvo de sus vecinos) una creencia con $\hat{v} > 0$ y $c \ge c_{\text{umbral}}$. El intento tiene éxito si y sólo si $\Sigma_k \subseteq \mathcal{K}_{\text{eff}}$. Esta condición se aplica aunque la vista compartida del holón ($R_{22}$, §7.2) esté apagada: es una propiedad declarada del entorno diseñado ("el recurso se libera si el grupo local conoce los fragmentos"), como `true_value`, y no un canal de conocimiento hacia el agente. Por eso no tiene regla en el inventario (§3.1): el agente no la recibe, la aprende.
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

**Presupuestos de diseño (Fase I: $R_1 \dots R_{11}$; Fase II añade $R_{12} \dots R_{23}$).** Sea $\mathcal{R}$ el conjunto de reglas diseñadas del agente, cada una con un **propósito declarado**. Las reglas $R_1$ y $R_2$ son nucleares: no se ablacionan (en la Fase II, también $R_{20}$).

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

Ningún parámetro de este perfil se cambia a la vista de los resultados. Si la población se extingue o no llega a varias generaciones, eso se reporta como resultado. Antes de implementar los runners se corre una prueba de humo que sólo comprueba que la corrida termina y registra la generación máxima, sin calcular ni mirar las métricas de las afirmaciones.

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
3. **Mensajes:** $m_i(t)$ es la cantidad de mensajes que emitió en las Fases 1 y 2; $c_{\text{msg}}$ = `message_cost` ($0.001$).
4. **Coordinación ($R_{23}$):** $c_{\text{coord\_share}}(i, t) = c_{\text{coord}}(U)/|U|$ si $a_i$ es hoja del holón raíz $U$ (§7.2), y $0$ si no pertenece a ningún holón. Se cobra en la Fase 5.

*(El costo cuadrático es una **decisión de diseño declarada**, la regla $R_{21}$: encarece la hipertrofia individual de $C_{\max, i}$ y de los radios, preserva la restricción $C_{\max, i} \ll N$ y, por lo tanto, sesga a favor de la cooperación. No es un resultado. Su ablación anula $c_{\text{mem}}$ y $c_{\text{sens}}$. El resto del balance (costo fijo, de movimiento y de emisión, la muerte con $E \le 0$ y la capacidad de carga) es la física metabólica $R_{20}$, nuclear: sin ella no hay selección.)*

- **Muerte:** si al cobrar el metabolismo en la Fase 5 resulta $E_i(t+1) \le 0$, el agente muere en ese mismo tick: se retira del motor y del entorno y se poda de cualquier árbol holónico (`prune_dead_leaves`, §7.3).
- **Reproducción individual diferencial ($R_{12}$, `reproduction_mode="energy"`, valor por defecto):** en la Fase 5, después de la reproducción holónica (§7.4), cada agente sobreviviente, en orden ascendente de `agent_id`, que todavía no se haya reproducido en el tick, con $E_i \ge E_{\text{reprod}}$ = `reproduction_threshold` ($2.20$) y con cupo ($|\mathcal{A}| < N_{\max}$, donde $N_{\max}$ = `max_population` $= 160$ es la capacidad de carga y $\mathcal{A}$ la población activa) engendra **un** hijo. No hay costo de gestación: la energía se parte de forma conservativa con $\kappa_{\text{part}}$ = `offspring_energy_share` ($0 < \kappa_{\text{part}} < 1$, por defecto $0.50$):
  $$E_{\text{hijo}} = \kappa_{\text{part}} \cdot E_i, \qquad E_i \leftarrow (1 - \kappa_{\text{part}}) \cdot E_i$$
- **Reproducción neutral (`reproduction_mode="neutral"`, ablación de $R_{12}$ y control de deriva de C6; design D26, caso 3):** quita el vínculo entre éxito y herencia sin cambiar **la regla** demográfica. Los mismos agentes que en el modo `"energy"` (no reproducidos, con $E_i \ge E_{\text{reprod}}$, en orden de `agent_id`, respetando el cupo) se reproducen exactamente igual: misma partición de energía, misma ubicación junto a ellos, mismo `parent_id`, misma generación y misma herencia cultural. Sólo cambia el **genoma** del hijo: antes de cada nacimiento se sortea un donante con `donors[int(donor_rng.integers(len(donors)))]` (generador propio, `spawn_key=(4,)`), donde `donors` es la lista ordenada por `agent_id` de los agentes vivos al empezar la fase de reproducción del tick, y el hijo recibe `mutate_genome(donante.genome, ...)` en vez del genoma de su progenitor. En un tick dado, con el mismo estado de partida, quién se reproduce, la partición de energía y las posiciones son las mismas que en el modo `"energy"`; sólo se rompe la herencia de los rasgos de los exitosos. A partir de ahí las dos corridas divergen, porque los hijos tienen genomas distintos, y ésa es la diferencia que mide `selection_gain`: no es un control de demografía idéntica a lo largo de la corrida. La reproducción holónica ($R_{17}$, §7.4) no cambia. Comparar contra este control separa el efecto de la selección del de la deriva genética (`selection_gain`, §8).
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
   donde $\mathcal{K}(\ell)$ son los patrones de la memoria de $\ell$ con $c \ge c_{\text{umbral}}$ y $\mathcal{K}_{\text{loc}}(U)$ es la unión de $\mathcal{K}(\ell)$ sobre la **componente conexa más grande** del grafo de alcance local entre las hojas de $U$ (empate entre componentes del mismo tamaño: la de menor `agent_id` mínimo). Con superávit, el contador `ticks_without_surplus` vuelve a $0$; sin superávit, aumenta en $1$.

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
  donde $c$ es la confianza de su creencia sobre $\rho$ después de aprender (§2.1). Si la celda ya tiene un rastro de $\rho$ de un tick anterior, el nuevo lo reemplaza; si es del mismo tick, se conserva el de mayor $(I, s)$, así los depósitos simultáneos dan el mismo resultado en cualquier orden. Un depósito con $I < c_{\min}$ (`min_confidence`) reemplaza y se purga en el acto: borra el rastro de $\rho$ de un tick anterior y no deja ninguno; frente a un rastro del mismo tick no cambia nada, porque la regla del mayor $(I, s)$ se aplica antes y ese rastro tiene mayor intensidad, de modo que ningún rastro existe bajo el umbral con el que el decaimiento lo purgaría.
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
- **003-B** (`run_protocol_003b_orthogonalization`, `OrthogonalizationReport`): dos condiciones con $R_{18}$ apagada, `with_view` = `config` y `without_view` = `ablate(config, ["R22"])` (holones formados por la misma `BOND`, sin vista compartida). Reporta `mean_acquired_coverage` y `mean_acquired_coverage_without_view` (medias de M13 por par tick-holón elegible de cada condición, o `None`), `coverage_advantage` (con vista − sin vista, o `None`), las reducciones de redundancia medias de ambas condiciones (descriptivas), `holon_ticks` y `holon_ticks_without_view` (la exposición de cada condición), `max_holon_level` y el pico de conteos por nivel.
