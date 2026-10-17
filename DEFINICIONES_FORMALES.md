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
- **Condición de resolución:** cuando la hoja $a$ ejecuta `INTERACT` sobre un recurso compuesto, sea $\mathcal{K}_{\text{eff}}$ el conjunto de patrones $\rho$ para los que alguna hoja en alcance local de $a$ dentro de su holón raíz $U$ (§7.2), o sólo $a$ si no pertenece a un holón, sostiene (en memoria o en su caché efímero del tick) una creencia con $\hat{v} > 0$ y $c \ge c_{\text{umbral}}$. El intento tiene éxito si y sólo si $\Sigma_k \subseteq \mathcal{K}_{\text{eff}}$. El éxito incrementa el contador M12 y, con evolución activa, reparte $\eta_E \cdot m^{\kappa_{\text{comp}}}$ en partes iguales entre las hojas localmente conectadas de $U$. El fracaso no registra éxito y, con evolución activa, cuesta energía sólo a $a$: su valor experimentado es $r = -$`composite_failure_penalty` ($\in [-1, 0]$; penalización por defecto $0.20$; §6.1).
- **Límite individual para $m > C_{\max}$:** un agente sin holón sólo cuenta con su memoria ($\le C_{\max}$ creencias) y con lo que obtuvo en el caché efímero de ese tick. Sin holón ni consultas en el tick, no puede resolver un recurso compuesto de orden $m > C_{\max}$.
- **Pendiente (decisión abierta P2):** cómo llega el agente a conocer el patrón compuesto para decidir interactuar con él (inyección de un patrón "desbloqueado" por el motor, que funciona como oráculo parcial, o aprendizaje por experiencia). Por objetividad, los recursos compuestos **no entran** en M2, que se calcula sólo sobre recursos elementales (§8).

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

- **$C_{\max, i}$ (Capacidad de Memoria Individual):** Número máximo de creencias que el agente $a_i$ puede almacenar simultáneamente (en Fase I es constante $C_{\max}$ para todos; en Fase II puede mutar entre generaciones, sujeto a un costo metabólico cuadrático en $C_{\max, i}$, §6.1).
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
6. **Capacidades Físicas ($\mathcal{G}_i$):** Tupla $(C_{\max, i}, r_{\text{perc}, i}, r_{\text{com}, i})$. En Fase I son homogéneas para toda la población; en Fase II forman parte del genoma heredable (`AgentGenome`) con costo metabólico cuadrático (§6.1).
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
| **Adaptación Evolutiva Intergeneracional (Fase II)** | Diferencia de precisión acumulada (M2) entre una población con mutación genética activa y otra idéntica con el genoma congelado (protocolo 002-A, `adaptation_gain` = `evolved_accuracy` − `frozen_genome_accuracy`), con las mismas condiciones iniciales. |
| **Holón / Meta-Agente de Nivel $L$ (Fase II)** | Nodo `CompositeAgent` formado por la regla `BOND` (R15) a partir de $\ge 2$ sub-nodos de nivel $\le L-1$ con hojas disjuntas. Sus hojas reparten el costo de coordinación y las ganancias de los recursos compuestos que resuelven, y su capacidad efectiva es $C_{\text{eff}}(U) = \sum_{\ell \in \text{leaves}(U)} C_{\max, \ell}$ (§7). |

### 3.1. Atribución de Emergencia

**Regla central:** *toda propiedad que se afirme como emergente debe poder distinguirse de una capacidad programada explícitamente en el agente.*

**Presupuestos de diseño (Fase I: $R_1 \dots R_{11}$; Fase II añade $R_{12} \dots R_{19}$).** Sea $\mathcal{R}$ el conjunto de reglas diseñadas del agente, cada una con un **propósito declarado**. Las reglas $R_1$ y $R_2$ son nucleares: no se ablacionan.

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

**Inventario de Fase II (`PHASE2_DESIGN_RULES`, design D29).** Cada regla lleva su propósito declarado (la capacidad que se diseñó para producir) y su ablación (los parámetros de `SimulationConfig` que la desactivan). `DESIGN_RULES` conserva sólo $R_1 \dots R_{11}$; `ALL_DESIGN_RULES = DESIGN_RULES + PHASE2_DESIGN_RULES`.

| Regla | Descripción (`name`) | Propósito declarado (`purpose`) | Ablación (`ablation`) |
| :--- | :--- | :--- | :--- |
| $R_{12}$ | Reproducción diferencial por umbral energético (§6.1) | Que los agentes con más energía dejen más descendencia (selección). | `(("reproduction_threshold", 1e9),)` |
| $R_{13}$ | Mutación genética acotada (§6.2) | Variación heredable sobre la que actúa la selección. | `(("mutation_rate", 0.0), ("discrete_mutation_prob", 0.0))` |
| $R_{14}$ | Herencia cultural vertical (§6.3) | Transmitir conocimiento de padres a hijos. | `(("enable_cultural_inheritance", False), ("inheritance_discount", 0.0))` |
| $R_{15}$ | Fusión holónica (BOND) (§7.3) | Asociar nodos complementarios en unidades de nivel superior. | `(("enable_holonic_hierarchy", False),)` |
| $R_{16}$ | Fisión holónica (SPLIT) (§7.3) | Disolver holones sin superávit. | `(("enable_holon_splitting", False),)` |
| $R_{17}$ | Reproducción de holón completo (§7.4) | Transmitir la estructura simbiótica a la descendencia. | `(("enable_holon_reproduction", False),)` |
| $R_{18}$ | Causalidad descendente intra-holón (§7.5) | Reducir la redundancia de memoria entre hojas de un holón (ortogonalización). | `(("enable_downward_causation", False), ("redundancy_penalty", 1.0))` |
| $R_{19}$ | Estigmergia (§7.6) | Externalizar conocimiento en el entorno. | `(("enable_stigmergy", False), ("stigmergy_deposit_rate", 0.0))` |

> **Pendiente de aprobación (decisión abierta P3).** El inventario $R_{12} \dots R_{19}$, las afirmaciones C5–C8 y sus variantes de comparación son **pre-registro** y todavía no están aprobados: lo que figura aquí es la propuesta del design D29, que debe revisarse y versionarse antes de mirar cualquier resultado. Además, hay mecanismos diseñados que aún **no tienen regla** en el inventario: el metabolismo y la muerte por agotamiento (§6.1), el costo de coordinación del holón (§7.2), el pozo de energía compartido (reparto de ganancias compuestas y de costos entre hojas, §7.2) y la vista compartida del holón (decisión abierta P1, §7.2). Mientras no se declaren con propósito y ablación, ninguna afirmación que dependa de ellos puede clasificarse como emergente.

**Afirmación pre-registrada.** Una afirmación $C$ consiste en una métrica poblacional $m_C$, su dirección de mejora y el conjunto $R_C \subseteq \mathcal{R}$ de reglas cuyo propósito declarado la produce. Se declara antes de ejecutar el experimento, junto con el perfil de corrida. *Principio conservador acotado:* toda afirmación sobre **disponibilidad o transmisión** de conocimiento incluye en $R_C$ las reglas de comunicación $R_8$ y $R_9$; una afirmación sobre **cómo se procesa** lo transmitido incluye las reglas diseñadas para ese procesamiento.

**Variantes.** Para cada semilla se mide $m_C$ en: la población **completa**; la **aislada** (sin comunicación); la población **sin $R_C$** (todas las reglas de $R_C$ desactivadas a la vez); y el **control nulo** (mismas reglas de emisión, recepción y ruteo, pero cada creencia entregada llega con $\hat{v}$ reemplazado por $\pm 1$ al azar, extraído de un generador propio). El control no fija el volumen de mensajes, que depende de las creencias; cada variante reporta el suyo.

**Criterios.** Con $n \ge 5$ semillas y una prueba de signo unilateral con $\alpha = 0.05$:
- **E1 Localidad:** $m_C$ es poblacional y ningún agente la computa ni la recibe.
- **E2 Superávit:** la población completa supera a la aislada.
- **E3 Independencia del propósito:** la población sin $R_C$ sigue superando a la aislada ($R_C = \emptyset$ lo cumple trivialmente).
- **E4 Dependencia del contenido:** la población completa supera al control nulo.
- **E5 Robustez al esquema de actualización:** bajo un esquema asíncrono (los agentes se activan de a uno, en orden aleatorio, viendo el mundo ya modificado por los anteriores), la afirmación vuelve a cumplir E2 y E3. Hay patrones que aparecen con actualización sincrónica y desaparecen con la asíncrona (Huberman y Glance, 1993): son artefactos del reloj, no de la población.

**Programada por construcción.** Si quitar $R_C$ deja a la población sin ningún canal de emisión, la población sin $R_C$ *es* la aislada, y E3 deja de ser una prueba para ser una tautología. La afirmación se declara entonces *programada por construcción*, sin presentarlo como resultado empírico.

**Clasificación.** *No observada* si falla E2; *programada* si cumple E2 y además es programada por construcción o falla E3; *artefacto de actividad* si cumple E2 y E3 y falla E4; si cumple E1–E4: *emergente pendiente de robustez* mientras E5 no pueda evaluarse, *artefacto del reloj* si falla E5 y **emergente** si la cumple. Con menos de 5 semillas el estado es *evidencia insuficiente*.

**Consecuencia para el Experimento 001.** Las afirmaciones de acceso (C1), superávit de decisión (C2) y persistencia extra-individual (C4) tienen $R_8, R_9 \in R_C$; quitar ambas reglas aísla la población, así que son **programadas por construcción**. No es una predicción: es lo que establece la regla mientras el canal transmita creencias con semántica de fábrica. "Por construcción" es una marca (`by_construction`: E3 no se prueba); el estado sigue el orden de la clasificación, así que si falla E2 es `NOT_OBSERVED` aunque la afirmación sea por construcción (le ocurrió a C4 en la corrida pre-registrada; ver `RESULTADOS.md`). La inmunidad colectiva a la falsedad (C3) tiene $R_C = \{R_3, R_4, R_6, R_7\}$ (los filtros epistémicos y el olvido) y es la única con una prueba empírica genuina: ¿la contención del rumor sobrevive sólo con transmisión y aprendizaje directo? El resultado está abierto. Además se mide el aporte de cada regla, apagándolas de a una. Las candidatas genuinas a emergencia en este nivel son las propiedades que ninguna regla persigue, por ejemplo transiciones abruptas de la cobertura accesible o de la persistencia al variar la densidad de agentes o el radio de comunicación. Las preguntas siguientes se plantean con la evolución intergeneracional y la jerarquía holónica (Experimentos 002–003) y con la des-programación del protocolo (Experimento 006), sometidas al mismo criterio.

**Afirmaciones propuestas de Fase II (C5–C8, design D29; pendientes de P3).** Se evalúan con el mismo marco (E1–E5 y la clasificación anterior):

| Afirmación | Protocolo | Métrica $m_C$ (mayor es mejor) | $R_C$ propuesto |
| :--- | :---: | :--- | :--- |
| C5: aceleración cultural intergeneracional | 002-B | `cultural_accuracy` | $\{R_{14}\}$ |
| C6: adaptación evolutiva de linajes | 002-A | `evolved_accuracy` | $\{R_{12}, R_{13}\}$ |
| C7: superávit cooperativo sobre recursos compuestos | 003-A | `holonic_composite_completions` | $\{R_{15}, R_{17}\}$ |
| C8: ortogonalización intra-holón | 003-B | `downward_causation_coverage_gain` | $\{R_{18}\}$ |

Para C5–C8, la variante **aislada** desactiva además los canales colectivos de Fase II (`comm_enabled=False`, `enable_cultural_inheritance=False`, `enable_holonic_hierarchy=False`, `enable_stigmergy=False`), y el **control nulo** aplica el reemplazo de $\hat{v}$ también a la herencia cultural ($R_{14}$), a la estigmergia ($R_{19}$) y a la vista compartida del holón. *Advertencia de atribución:* $R_{18}$ está diseñada para ortogonalizar, de modo que la ortogonalización que produzca es **programada**, no espontánea (el nombre provisional del design, "Ortogonalización espontánea intra-holón", no se usa aquí por esa razón). Lo mismo vale, con sus propósitos, para C5 frente a $R_{14}$ y para C7 frente a $R_{15}$ y $R_{17}$. En su forma actual, C7 y C8 podrían quedar clasificadas como emergentes aunque una regla diseñada las persiga: es uno de los puntos que P3 debe resolver antes de versionar el pre-registro.

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
5. **`ExperimentRunner` y `MetricsCollector`:** Ejecuta los protocolos con semillas reproducibles (`seed`) y calcula las métricas M1–M7 (Fase I) y M8–M12 (Fase II).
6. **Atribución:** Inventario de reglas con propósito declarado, ablaciones, control nulo, registro pre-declarado de afirmaciones y clasificación según §3.1.

---

## 6. Dinámica Evolutiva Intergeneracional (Fase II — Experimento 002)

En la Fase I, la población es estática e inmortal. En la Fase II, con `enable_evolution=True`, los agentes están sujetos a **metabolismo energético, muerte por agotamiento y reproducción diferencial con herencia dual**. Con los valores por defecto (todas las banderas de Fase II en `False`), el sistema se comporta bit a bit como en la Fase I. Esta sección resume las decisiones D21, D22 y D26 del design de Fase II, que rige ante cualquier discrepancia. Toda operación estocástica de esta sección usa el generador dedicado `evo_rng` (`SeedSequence(seed, spawn_key=(2,))`), nunca el generador del motor.

### 6.1. Metabolismo Energético, Muerte y Reproducción ($R_{12}$)
Cada agente elemental $a_i$ mantiene una energía $E_i(t) \in \mathbb{R}$, inicializada en $E_0$ = `initial_energy` ($1.50$), **sin tope superior**. Su costo basal por tick depende del genoma y es cuadrático en la capacidad de memoria y en los radios:
$$c_{\text{base}}(i) = c_{\text{fijo}} + c_{\text{mem}} \cdot C_{\max, i}^2 + c_{\text{sens}} \cdot \left(r_{\text{perc}, i}^2 + r_{\text{com}, i}^2\right)$$
con $c_{\text{fijo}}$ = `metabolic_base_cost` ($0.01$), $c_{\text{mem}}$ = `memory_capacity_cost` ($0.002$) y un **único** coeficiente sensorial $c_{\text{sens}}$ = `sensory_radius_cost` ($0.0005$) para ambos radios. El balance del tick es:
$$E_i(t+1) = E_i(t) + \eta_E \cdot r_i(t) - c_{\text{base}}(i) - c_{\text{move}} \cdot \mathbb{I}(\text{mov}_i(t)) - c_{\text{msg}} \cdot m_i(t) - c_{\text{coord\_share}}(i, t)$$
donde:
1. **Retorno de interacción:** $\eta_E$ = `energy_gain_scale` ($0.45$) y $r_i(t)$ es el valor real experimentado: $v(r)$ de un recurso elemental; $-$`composite_failure_penalty` en un intento compuesto fallido; o la fracción que le toca de un recurso compuesto resuelto por su holón (§1.3.2). Se acredita en la Fase 4.
2. **Movimiento:** $\mathbb{I}(\text{mov}_i(t)) = 1$ si el agente ejecutó un `MOVE` válido; $c_{\text{move}}$ = `move_cost` ($0.005$).
3. **Mensajes:** $m_i(t)$ es la cantidad de mensajes que emitió en las Fases 1 y 2; $c_{\text{msg}}$ = `message_cost` ($0.001$).
4. **Coordinación:** $c_{\text{coord\_share}}(i, t) = c_{\text{coord}}(U)/|U|$ si $a_i$ es hoja del holón raíz $U$ (§7.2), y $0$ si no pertenece a ningún holón. Se cobra en la Fase 5.

*(El costo cuadrático es una **decisión de diseño declarada**: encarece la hipertrofia individual de $C_{\max, i}$ y de los radios, preserva la restricción $C_{\max, i} \ll N$ y, por lo tanto, sesga a favor de la cooperación. No es un resultado.)*

- **Muerte:** si al cobrar el metabolismo en la Fase 5 resulta $E_i(t+1) \le 0$, el agente muere en ese mismo tick: se retira del motor y del entorno y se poda de cualquier árbol holónico (`prune_dead_leaves`, §7.3).
- **Reproducción individual:** en la Fase 5, después de la reproducción holónica (§7.4), cada agente sobreviviente, en orden ascendente de `agent_id`, que todavía no se haya reproducido en el tick, con $E_i \ge E_{\text{reprod}}$ = `reproduction_threshold` ($2.20$) y con cupo ($|\mathcal{A}| < N_{\max}$, donde $N_{\max}$ = `max_population` $= 160$ es la capacidad de carga y $\mathcal{A}$ la población activa) engendra **un** hijo. No hay costo de gestación: la energía se parte de forma conservativa con $\kappa_{\text{part}}$ = `offspring_energy_share` ($0 < \kappa_{\text{part}} < 1$, por defecto $0.50$):
  $$E_{\text{hijo}} = \kappa_{\text{part}} \cdot E_i, \qquad E_i \leftarrow (1 - \kappa_{\text{part}}) \cdot E_i$$
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
   - $r_{\text{perc}}, r_{\text{com}}$: $g_{\min} = 1$ y $g_{\max} = \lfloor (\min(W, H) - 1)/2 \rfloor$, el mayor radio que admite la grilla. Si $g_{\max} < g_{\min}$, el rasgo conserva el valor parental.
   - Las extracciones aleatorias se consumen siempre, aunque el recorte anule el salto, para que la secuencia del generador no dependa del valor del rasgo.
3. **Ablación:** si $\sigma_{\text{mut}} = 0$ y $p_{\text{disc}} = 0$, el hijo es un clon exacto y no se consume el generador.
4. **Fenotipo:** los radios mutados son efectivos: el entorno usa los radios individuales del agente para su percepción y su vecindad de comunicación.

---

### 6.3. Herencia Cultural Vertical ($\mathcal{M}_{\text{padre}} \to \mathcal{M}_{\text{hijo}}$, $R_{14}$)
*Motivación:* en el Experimento 001 la persistencia extra-individual (C4) no se observó: el conocimiento social no sobrevivió a sus portadores (`RESULTADOS.md`). La herencia cultural es una regla **diseñada** para transmitir conocimiento entre generaciones; si lo logra, cumple su propósito declarado.

Con `enable_cultural_inheritance=True` y $\gamma_{\text{gen}}$ = `inheritance_discount` $> 0$ (por defecto $0.65$), al nacer el hijo en el tick $t$:
1. Se ordena la memoria del progenitor por utilidad descendente $U(k, t)$ del progenitor (§2.2, incluida la penalización por redundancia de $R_{18}$ si está activa), con desempate por el orden canónico de $\rho$, y se toman hasta $\min(C_{\max, \text{hijo}}, |\mathcal{M}_{\text{padre}}|)$ creencias.
2. De ellas se conservan las que cumplen $\gamma_{\text{gen}} \cdot c \ge c_{\min}$, y cada una se convierte en un testimonio parental $k' = (\rho, \hat{v}, \gamma_{\text{gen}} \cdot c, n, \tau, d)$.
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

3. **Identificadores:** las hojas conservan su `agent_id` $\ge 0$; cada holón compuesto recibe un `node_id` **negativo** de un contador monótono decreciente que empieza en $-1$, de modo que los identificadores de holones y de agentes nunca colisionan.

> **Profundidad sin tope codificado, pero acotada por la masa:** el código no fija un nivel máximo: un holón de nivel $L$ puede volver a fusionarse en uno de nivel $L+1$. Pero `BOND` exige $|U| \le$ `max_holon_leaves` ($8$ por defecto), y cada nivel nuevo agrega al menos una hoja, así que $L(U) \le$ `max_holon_leaves` $- 1$. Que se formen niveles $L \ge 2$ es una pregunta empírica (protocolo 003-B), no una propiedad garantizada.

---

### 7.2. Propiedades Colectivas de un Holón de Nivel $L \ge 1$
Un holón compuesto $U$ tiene las siguientes propiedades, derivadas de sus hojas:

1. **Alcance local intra-holón:** dos hojas $\ell_a, \ell_b$ de $U$ están en alcance local en el tick $t$ si su distancia de Chebyshev toroidal cumple $d(\ell_a, \ell_b) \le \max(r_{\text{com}, a}, r_{\text{com}, b}) + 1$. Todo lo que una hoja obtiene de su holón (vista compartida, resolución de compuestos, causalidad descendente) se limita a las hojas en su alcance local: no hay "telepatía holónica".

2. **Memoria colectiva ($\mathcal{M}_{\text{holón}}(U)$):** ninguna estructura central almacena creencias; la memoria colectiva es una vista calculada sobre las memorias de las hojas (opcionalmente restringida a un subconjunto de hojas, por ejemplo las de alcance local). Para cada patrón $\rho$ conocido por alguna hoja, conserva la creencia que maximiza
   $$\left(c_\ell(\rho), \; \tau_\ell(\rho), \; -\text{id}_\ell\right)$$
   es decir, la de mayor confianza, luego la más reciente y luego la de la hoja de menor `agent_id`. No hay promedio ni consenso entre hojas.
   - **Capacidad efectiva:** $C_{\text{eff}}(U) = \sum_{\ell \in \text{leaves}(U)} C_{\max, \ell}$ (`effective_capacity`), y siempre $|\mathcal{M}_{\text{holón}}(U)| \le C_{\text{eff}}(U)$. Cada hoja conserva su límite $C_{\max, \ell}$. La ganancia de cobertura del holón sobre sus hojas se mide con M11 (§8).
   - **Vista compartida del holón (decisión abierta P1):** el design describe una variante en la que, en las Fases 1 y 2, cada hoja recibe en un caché efímero propio del holón las creencias de las hojas en su alcance local, que sólo usan la decisión y el protocolo de emisión (nunca el aprendizaje directo ni la asimilación de testimonios). Ese canal no pasa por `assimilate_testimony`, en contra del invariante vigente, y no se implementa hasta resolver P1.

3. **Energía y costo de coordinación:** la energía del holón es $E(U, t) = \sum_{\ell \in \text{leaves}(U)} E_\ell(t)$ (`total_energy`). Las ganancias de un recurso compuesto resuelto se reparten en partes iguales entre las hojas en alcance local de la hoja que lo resolvió (§1.3.2). Mantener el holón cuesta por tick
   $$c_{\text{coord}}(U) = c_{\text{enlace}} \cdot |U| \cdot L(U), \qquad c_{\text{enlace}} = \texttt{holon\_coord\_cost} \; (0.002)$$
   que se cobra **sólo a los holones raíz** (los sub-holones no pagan aparte, porque $L(U)$ ya pondera la profundidad) y, con evolución activa, se descuenta en partes iguales, $c_{\text{coord}}(U)/|U|$, de cada hoja (§6.1).
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

- **Atribución:** $R_{18}$ está **diseñada para ortogonalizar** las memorias de las hojas ($\mathcal{M}_i \cap \mathcal{M}_j \to \emptyset$) y acercar $|\mathcal{M}_{\text{holón}}(U)|$ a $C_{\text{eff}}(U)$. La ortogonalización que produzca es, por definición, **programada**, no espontánea. Lo que se pone a prueba (protocolo 003-B) es cuánto aumenta la cobertura holónica (M11) frente a holones sin la regla.
- *Fuera del alcance de la Fase II actual:* la modulación de la tasa de exploración $\epsilon_{\text{eff}}$ de las hojas por parte del holón.

---

### 7.6. Estigmergia Espacial ($R_{19}$)
Con `enable_stigmergy=True`, los agentes pueden **externalizar conocimiento en el entorno** dejando en su celda un **rastro estigmérgico** (`StigmergicTrace`) por patrón:
$$\mathcal{S}(l, \rho) = \left(\rho, \; s, \; I, \; \tau_{\text{rastro}}\right), \qquad s \in \{-1, 0, +1\}, \; I \in [0, 1]$$

- **Depósito (Fase 4):** tras una experiencia directa con un patrón **elemental** $\rho$ de valor real $v$, si $s_{\text{dep}}$ = `stigmergy_deposit_rate` $> 0$ (por defecto $0.50$), el agente deposita en su celda el rastro
  $$\left(\rho, \; s = \text{sign}(v), \; I = \min(1, \; s_{\text{dep}} \cdot c), \; \tau_{\text{rastro}} = t\right)$$
  donde $c$ es la confianza de su creencia sobre $\rho$ después de aprender (§2.1). Si la celda ya tiene un rastro de $\rho$, se conserva el de mayor $(I, \tau_{\text{rastro}}, s)$; así, los depósitos simultáneos del mismo tick dan el mismo resultado en cualquier orden.
- **Decaimiento:** al avanzar la dinámica del entorno en el tick $t$, cada rastro que no se actualizó en el tick ($\tau_{\text{rastro}} < t$) pierde $\delta_{\text{suelo}}$ = `stigmergy_decay` ($0.02$) de intensidad, $I \leftarrow I - \delta_{\text{suelo}}$, y se elimina si $I < c_{\min}$.
- **Lectura (Fase 1):** el motor lee los rastros de la celda del agente (no forman parte de su `Observation`) y convierte cada uno en el testimonio $(\rho, s, I, 1, \tau_{\text{rastro}}, 0)$, que entrega con `assimilate_testimony` y `sender_id` $= -1$ (bajo el control nulo, antes reemplaza el valor por $\pm 1$ al azar). Se procesa como cualquier testimonio (§2.3): recibe el descuento de confianza en el emisor del receptor ($\gamma$ por defecto) y, como $d = 0$, la protección anti-cámara de eco.
- Los rastros sobreviven a quien los depositó mientras no decaigan: el entorno funciona como una memoria externa compartida. Que esto sostenga conocimiento a través de generaciones es lo que se pone a prueba; $R_{19}$ está diseñada para externalizar conocimiento.

---

## 8. Métricas Formales de Evolución y Jerarquía Holónica (Fase II: M8–M12)

Además de las métricas M1–M7 (§4), la Fase II registra por tick, en `EvolutionaryTickMetrics` (design D28; `TickMetrics` conserva sus 14 campos de Fase I), cinco métricas. Sea $\mathcal{A}(t)$ la población activa y $\mathcal{U}_{\text{root}}(t)$ el conjunto de holones raíz compuestos ($L \ge 1$).

- **M2 en Fase II:** la precisión de decisión se calcula **sólo sobre recursos elementales**, exactamente como en la Fase I. Los recursos compuestos no entran en la verdad que juzga la decisión: si, quitándolos, una celda queda sin recursos, o si la acción del agente es `INTERACT` sobre un recurso compuesto, ese agente no suma oportunidad de decisión en el tick. El desempeño sobre compuestos lo mide M12. (Esta elección está ligada a la decisión abierta P2.)

### M8. Dinámica Generacional
Generación media (`mean_generation`) y máxima (`max_generation`) de $\mathcal{A}(t)$, nacimientos (`births_this_tick`) y muertes (`deaths_this_tick`) del tick, y energía media (`mean_energy`). Si $\mathcal{A}(t) = \emptyset$, valen $0.0$, $0$ y $0.0$.

### M9. Cobertura Heredada (`inherited_coverage_ratio`)
Sobre los agentes activos con $g \ge 1$, sea $V_{\text{total}}$ el número total de creencias válidas en sus memorias y $V_{\text{social}}$ las que tienen $d = 0$:
$$M9(t) = \frac{V_{\text{social}}}{V_{\text{total}}} \quad (0.0 \text{ si } V_{\text{total}} = 0)$$
*(Cuenta toda creencia de origen social, sea heredada o recibida por testimonio horizontal: no distingue entre ambos canales.)*

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

Además se registra `stigmergy_active_cells` (celdas con al menos un rastro estigmérgico), como telemetría sin número de métrica.

**Protocolos y reportes (design D28).** 002-A compara mutación activa contra genoma congelado (`AdaptationReport`, con `adaptation_gain` = `evolved_accuracy` − `frozen_genome_accuracy`); 002-B compara herencia cultural contra *tabula rasa* (`CulturalInheritanceReport`, con `cultural_accuracy_surplus` y los ticks de convergencia: el menor tick con oportunidades de decisión y precisión acumulada $\ge 0.70$, o ninguno); 003-A compara jerarquía holónica contra individualismo ante recursos compuestos (`HolonicTransitionReport`); 003-B compara holones con y sin causalidad descendente (`MultilevelScalingReport`, con `orthogonalization_advantage` = diferencia de M11).

> **Pendiente de la decisión P3 (no es una métrica numerada):** un indicador de deriva neutral frente a selección, que compare la evolución de la media y la varianza de cada rasgo del genoma con un control en el que la reproducción no dependa de la energía. Sin ese control, un cambio en los rasgos heredables (C6) no puede distinguirse de la deriva genética. El design actual no lo define.
