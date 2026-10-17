# Especificación de Definiciones Formales — Proyecto IDE (v2.0)

Este documento establece de manera rigurosa y sin ambigüedades qué significa cada concepto dentro del sistema de **Inteligencia Distribuida Emergente (IDE)** antes de escribir código. Toda implementación debe respetar estas definiciones.

> **Novedades en la Versión 2.0:** Esta versión conserva íntegramente las definiciones y métricas verificadas de la **Fase I (Experimento 001)** y extiende la ontología matemática hacia la **Fase II (Experimentos 002–003)**:
> 1. **Metabolismo, muerte y reproducción intergeneracional ($g \to g+1$).**
> 2. **Herencia Dual:** herencia genética con mutación sobre $\Theta_i$ y capacidades $\mathcal{G}_i$ + herencia cultural vertical de creencias $\mathcal{M}_{\text{padre}} \to \mathcal{M}_{\text{hijo}}$.
> 3. **Arquitectura Holónica / Jerarquía Recursiva Ilimitada ($L \in \mathbb{N}_0$):** formalización del **Holón** (`AgentNode`) mediante el patrón recursivo *Composite*, donde tanto un agente elemental ($L=0$) como una coalición de coaliciones de nivel arbitrario ($L = 1, 2, \dots, K$, sin tope codificado) obedecen la misma interfaz matemática de percepción, memoria distribuida, decisión, fusión (`BOND`) y fisión (`SPLIT`).

> **Relación con los demás documentos.** La visión está en el [Documento Fundacional](DOCUMENTO_FUNDACIONAL.md) y la arquitectura en las [Definiciones Técnicas](DEFINICIONES_TECNICAS.md). Los valores numéricos, firmas y reglas de desempate exactos de la Fase I son normativos en [`design.md`](openspec/changes/ide-emergent-distributed-intelligence/design.md); los valores que aparecen aquí como "ej." son ilustrativos.

---

## 1. Definiciones Ontológicas (Qué existe en el sistema)

### 1.1. Tiempo ($t$) y Generaciones ($g$)
El sistema evoluciona en pasos de tiempo discretos (ticks):
$$t \in \{0, 1, 2, \dots, T\}$$
En cada paso $t$, todos los agentes (o nodos holónicos activos) perciben, se comunican, deciden, actúan, metabolizan y aprenden de forma local (ver §2 y §6), sin un coordinador que dirija sus estrategias. El tick es un reloj de simulación, no una entidad cognitiva. Dentro de un tick, la percepción, la comunicación y la decisión son **simultáneas**; los conflictos físicos (dos agentes que intentan consumir el mismo recurso) se resuelven por sorteo. Ninguna de las dos idealizaciones, reloj sincrónico o actualización secuencial, es más realista que la otra: una comunidad real es asíncrona. Por eso ninguna propiedad emergente puede depender del esquema de actualización (criterio E5, §3.1).

Además del tiempo de reloj $t$, cada agente posee un **índice generacional** $g_i \in \mathbb{N}_0$:
- La población fundadora en $t=0$ tiene $g_i = 0$.
- Todo agente nacido por reproducción de un progenitor $p$ en el instante $t > 0$ recibe $g_{\text{hijo}} = g_p + 1$ (o $1 + \max(g_{p_1}, g_{p_2})$ en reproducción biparental).

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
Para crear una presión selectiva real hacia la autoorganización en niveles jerárquicos superiores ($L = 1, 2, \dots, K$), el entorno en Fase II introduce **Recursos Compuestos** $r^{(m)}$ de **orden de complejidad $m \in \mathbb{N}$**:
$$r^{(m)} = \left(\Sigma_r = \{\rho_1, \rho_2, \dots, \rho_m\}, \; v_{\text{éxito}}(r^{(m)}), \; v_{\text{fallo}}(r^{(m)})\right), \quad \Sigma_r \subseteq \mathcal{P}_{\text{mundo}}$$
- **Condición de desbloqueo epistémico:** Un nodo holónico $u$ (agente individual o meta-agente compuesto) sólo puede extraer con éxito el retorno $v_{\text{éxito}}(r^{(m)}) > 0$ si su memoria colectiva interna $\mathcal{M}_{\text{holón}}(u)$ conoce **simultáneamente y de forma válida** los $m$ patrones constituyentes $\rho_1, \dots, \rho_m$. En caso contrario, sufre la penalización $v_{\text{fallo}}(r^{(m)}) < 0$.
- **Imposibilidad individual para $m > C_{\max}$:** Dado que un agente elemental ($L=0$) jamás puede almacenar más de $C_{\max}$ creencias en su memoria interna, **ningún individuo aislado puede resolver de manera autónoma y determinista un recurso compuesto de orden $m > C_{\max}$**.
- **Escalamiento superlineal del retorno:** El valor energético de los recursos compuestos escala con su orden $m$:
  $$v_{\text{éxito}}(r^{(m)}) = v_0 \cdot m^{\kappa_{\text{comp}}}, \quad \text{con } \kappa_{\text{comp}} > 1$$
  Esto hace energéticamente rentable que agentes de nivel $L=0$ se unan en meta-agentes de nivel $L=1$ (para resolver órdenes $m \le |u_{L=1}| \cdot C_{\max}$), y que meta-agentes de nivel $L=1$ se unan a su vez en niveles $L=2, 3, \dots, K$ para desbloquear recursos de orden $m$ arbitrariamente alto.

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

- **$C_{\max, i}$ (Capacidad de Memoria Individual):** Número máximo de creencias que el agente $a_i$ puede almacenar simultáneamente (en Fase I es constante $C_{\max}$ para todos; en Fase II puede evolucionar sujeto a un costo metabólico cuadrático por slot).
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
3. **Estado Interno / Energía ($E_i(t) \in \mathbb{R}_{\ge 0}$):** Nivel de energía metabólica acumulada. Si un agente consume recursos beneficiosos, $E_i$ sube; si consume recursos dañinos o paga costos metabólicos, $E_i$ baja. *En el Experimento 001 (Fase I) $E_i$ no se modela: no afecta la supervivencia ni la decisión, y el desempeño se mide sólo con la calidad de las decisiones (M2). En la Fase II (§6), $E_i(t)$ gobierna la supervivencia ($E_i > 0$) y la reproducción ($E_i \ge E_{\text{reprod}}$).*
4. **Memoria Local ($\mathcal{M}_i(t)$):** Sujeta a $|\mathcal{M}_i(t)| \le C_{\max, i}$.
5. **Parámetros Cognitivos Locales ($\Theta_i$):** Tasas de aprendizaje ($\alpha_i$), factor de descuento de confianza social ($\gamma_i$), tasa de exploración ($\epsilon_i$), propensión a cooperar/fusionarse ($\omega_{\text{bond}, i}$).
6. **Capacidades Físicas ($\mathcal{G}_i$):** Tupla $(C_{\max, i}, r_{\text{perc}, i}, r_{\text{com}, i})$. En Fase I son homogéneas para toda la población; en Fase II forman parte del genoma heredable con costo metabólico proporcional.
7. **Registro de Linaje ($\mathcal{H}_i$):** Tupla $(\text{parent\_id}_i, g_i, t_{\text{nac}, i})$ que registra el progenitor, el número de generación $g_i \in \mathbb{N}_0$ y el tick de nacimiento.

---

## 2. Dinámica Cognitiva y Reglas de Interacción (Fase I Base)

En cada ciclo $t$, cada agente ejecuta procesos estrictamente locales en este orden: **(1)** percibir, **(2)** comunicarse (consultar, responder, difundir y revalidar), **(3)** decidir, **(4)** actuar y aprender por experiencia directa, y **(5)** olvidar (decaimiento pasivo). En Fase II se añaden **(6)** metabolismo/reproducción y **(7)** reconfiguración holónica (`BOND`/`SPLIT`). La comunicación ocurre **antes** de decidir para que la consulta en vivo (§2.4) pueda informar la decisión del mismo tick. Las subsecciones siguientes describen cada regla, no el orden.

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
donde $\varphi$ es el **factor de confianza en el emisor**. En el Exp 001, $\varphi = \gamma$ para todo emisor, así que el recorte nunca actúa y $c_{\text{recibida}} = \gamma \cdot c_{\text{ext}}$. Una estrategia de confianza por emisor (Exp 002) puede asignar otro $\varphi$, incluso mayor que 1; el recorte mantiene la confianza en $[0, 1]$. En las fórmulas siguientes, $\gamma c_{\text{ext}}$ abrevia $c_{\text{recibida}}$.
*(Un rumor nunca tiene la misma fuerza inicial que haberlo vivido directamente; cada salto de boca en boca sin verificación empírica atenúa la confianza).*

#### Escenario B: Consenso ($\rho \in \mathcal{M}_j$ y $\text{sign}(\hat{v}_j) == \text{sign}(\hat{v}_{\text{ext}})$)
Ambos agentes coinciden. El receptor promedia la estimación ponderada por confianza:
$$\hat{v}_j \leftarrow \frac{c_j \hat{v}_j + (\gamma c_{\text{ext}}) \hat{v}_{\text{ext}}}{c_j + \gamma c_{\text{ext}}}$$
y refuerza moderadamente su confianza:
$$c^{*} = c_j + \eta_{\text{consenso}} \cdot \gamma c_{\text{ext}} (1 - c_j)$$
- Si el emisor tiene evidencia directa ($d_{\text{ext}} = 1$): $c_j \leftarrow \min(1.0, c^{*})$.
- Si el emisor sólo transmite un rumor ($d_{\text{ext}} = 0$): $c_j \leftarrow \min\left(\max(c_j, \gamma c_{\text{ext}}),\; c^{*}\right)$, y $\tau_j$ **no** se actualiza.

*(Protección anti-cámara de eco: sin la segunda regla, dos agentes que sólo tienen el mismo rumor podrían rebotárselo hasta $c \to 1$ sin ninguna evidencia física; y si el rebote refrescara $\tau$, quedarían exentos del olvido para siempre. La cota $\max(c_j, \gamma c_{\text{ext}})$ sólo impide que la confianza de la población crezca si $\varphi \le 1$.)*

> **Riesgo declarado (Exp 002).** Con $\varphi > 1$, la cota deja de proteger: dos portadores del mismo rumor que se asignan $\varphi > 1$ se lo rebotan hasta $c \to 1$ sin ninguna evidencia física, aunque $\tau$ siga sin refrescarse. Una estrategia de confianza que asigne $\varphi > 1$ equivale a una ablación parcial de R6 y debe declararse como tal en el diseño de ese experimento.

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

> **Advertencia de atribución.** El meta-agente efímero de nivel 0 es una consecuencia **directa y buscada** de la consulta en vivo: la regla existe para producirlo. Observarlo valida el mecanismo, pero no constituye emergencia (§3.1). El protocolo de mensajes (`QUERY`, `RESPONSE`, `BROADCAST`) tiene semántica predefinida; su des-programación progresiva es un eje del programa de investigación ([Documento Fundacional](DOCUMENTO_FUNDACIONAL.md) §8).

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
| **Adaptación Evolutiva Intergeneracional (Fase II)** | Incremento estadísticamente significativo de la eficiencia metabólica y precisión cognitiva de la generación $g_k$ respecto de la generación fundadora $g_0$ ($k \ge 3$), medido en condiciones ambientales idénticas. |
| **Holón / Meta-Agente de Nivel $L$ (Fase II)** | Unidad autónoma compuesta recursivamente por sub-nodos de nivel $\le L-1$ que comparte un pozo metabólico común, fusiona sus memorias para alcanzar capacidad epistémica efectiva $C_{\text{eff}}(u) \le |u| \cdot C_{\max}$ y coordina su acción física para resolver recursos compuestos de orden $m > C_{\max}$. |

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
| $R_{12}$ | II | Selección metabólica y reproducción ($\S6.1$) | Presión selectiva diferencial |
| $R_{13}$ | II | Mutación genética de $\Theta_i, \mathcal{G}_i$ ($\S6.2$) | Variación heredable de capacidades |
| $R_{14}$ | II | Herencia cultural vertical $\mathcal{M}_{\text{padre}} \to \mathcal{M}_{\text{hijo}}$ ($\S6.3$) | Transferir conocimiento entre generaciones |
| $R_{15}$ | II | Operador de Fusión Holónica `BOND` ($\S7.3$) | Formar meta-agentes de nivel $L \ge 1$ |
| $R_{16}$ | II | Operador de Fisión Holónica `SPLIT` ($\S7.3$) | Disolver coaliciones ineficientes |
| $R_{17}$ | II | Endosimbiosis reproductiva holónica ($\S7.4$, Margulis) | Reproducir un Holón exitoso como unidad ya ensamblada |
| $R_{18}$ | II | Causalidad descendente y particionamiento intra-holón ($\S7.5$, Noble) | Inhibir redundancia epistémica entre miembros de un Holón |
| $R_{19}$ | II | Construcción de nicho / estigmergia espacial ($\S7.6$) | Externalizar memoria sobre las celdas del entorno |

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

**Consecuencia para el Experimento 001.** Las afirmaciones de acceso (C1), superávit de decisión (C2) y persistencia extra-individual (C4) tienen $R_8, R_9 \in R_C$; quitar ambas reglas aísla la población, así que son **programadas por construcción**. No es una predicción: es lo que establece la regla mientras el canal transmita creencias con semántica de fábrica. "Por construcción" es una marca (`by_construction`: E3 no se prueba); el estado sigue el orden de la clasificación, así que si falla E2 es `NOT_OBSERVED` aunque la afirmación sea por construcción (le ocurrió a C4 en la corrida pre-registrada; ver `RESULTADOS.md`). La inmunidad colectiva a la falsedad (C3) tiene $R_C = \{R_3, R_4, R_6, R_7\}$ (los filtros epistémicos y el olvido) y es la única con una prueba empírica genuina: ¿la contención del rumor sobrevive sólo con transmisión y aprendizaje directo? El resultado está abierto. Además se mide el aporte de cada regla, apagándolas de a una. Las candidatas genuinas a emergencia en este nivel son las propiedades que ninguna regla persigue, por ejemplo transiciones abruptas de la cobertura accesible o de la persistencia al variar la densidad de agentes o el radio de comunicación. Los saltos conceptuales vendrán de la evolución intergeneracional y jerarquía holónica (Experimentos 002–003) y de la des-programación del protocolo (Experimento 007).

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
- *Trampa de evitación:* un agente que cree que un patrón benéfico es dañino no lo prueba, así que no puede refutarlo empíricamente. Si la creencia falsa es un rumor, su corrección depende de la duda social, del olvido y de la exploración, y es un fenómeno a medir en el Experimento 001. Si en cambio es evidencia directa que quedó obsoleta porque el mundo cambió (Experimento 004), la población puede quedar bloqueada, porque el consenso entre testigos directos refresca $\tau$. Para ese caso se compararán dos mecanismos: $\tau$ como edad de la evidencia más reciente y la re-verificación escéptica con probabilidad $\epsilon_{\text{recheck}}(1-c)$.

### M7. Eficiencia y Costo de Comunicación ($Cost_{\text{com}}(t)$)
Cantidad media de mensajes transmitidos por agente por paso de tiempo ($\frac{\text{Mensajes}(t)}{M}$). La eficiencia se resume como ganancia de precisión por mensaje: $\Delta_{\text{col}} / \overline{Cost_{\text{com}}}$ (indefinida si no hubo mensajes).

---

## 5. Contratos de Software (Interfaces Desacopladas)

Antes de implementar, la arquitectura en Python se compromete a separar estrictamente estos componentes (detalle en las [Definiciones Técnicas](DEFINICIONES_TECNICAS.md)):

1. **`KnowledgeUnit` (Estructura de Datos Pura):** Representa la creencia $k = (\rho, \hat{v}, c, n, \tau, d)$. Inmutable; las actualizaciones son funciones puras que devuelven una creencia nueva.
2. **`BoundedMemory` (Módulo de Memoria):** Contiene hasta $C_{\max}$ unidades `KnowledgeUnit`. Ejecuta inserción, búsqueda por patrón, decaimiento temporal y reemplazo por menor utilidad $U(k, t)$.
3. **`AgentNode` / `MicroAgent` / `CompositeAgent` (Jerarquía Cognitiva Local):** `MicroAgent` ($L=0$) contiene `BoundedMemory` y las reglas de aprendizaje directo, asimilación social (Escenarios A, B, C) y toma de decisiones. `CompositeAgent` ($L \ge 1$) agrupa recursivamente nodos `AgentNode` de niveles inferiores sin límite de profundidad. **Ninguno importa ni conoce ninguna clase de Grilla 2D.** La semántica del protocolo de mensajes vive aislada en un módulo reemplazable, para poder des-programarla.
4. **`Environment` (Interfaz Abstracta del Mundo):**
   - Implementación 1: `ToroidalGrid2D` (Experimento 001, con soporte de recursos compuestos en Fase II).
   - Implementaciones futuras: `SpatialGraph`, `ContinuousSpace2D`.
5. **`ExperimentRunner` y `MetricsCollector`:** Ejecuta los protocolos con semillas reproducibles (`seed`) y calcula las métricas M1–M7 (Fase I) y M8–M12 (Fase II).
6. **Atribución:** Inventario de reglas con propósito declarado, ablaciones, control nulo, registro pre-declarado de afirmaciones y clasificación según §3.1.

---

## 6. Dinámica Evolutiva Intergeneracional (Fase II — Experimento 002)

En la Fase I, la población $M$ es estática e inmortal. En la Fase II, los agentes están sujetos a **metabolismo energético, muerte por agotamiento y reproducción diferencial con herencia dual**.

### 6.1. Metabolismo Energético, Muerte y Reproducción ($R_{12}$)
Cada agente elemental $a_i$ mantiene una reserva energética $E_i(t) \in [0, E_{\max}]$, inicializada en $E_i(0) = E_0$. En cada paso $t$, su energía evoluciona según:
$$E_i(t+1) = \min\left(E_{\max},\; E_i(t) + \Delta E_{\text{interacción}, i}(t) - c_{\text{basal}}(\mathcal{G}_i) - c_{\text{acción}, i}(t)\right)$$

Donde:
1. **Retorno de interacción ($\Delta E_{\text{interacción}, i}(t)$):** Si el agente interactúa con un recurso $r$, recibe $\Delta E = s_E \cdot v(r)$ (donde $s_E > 0$ es el factor de escala energética; consumir recursos benéficos recarga energía y consumir venenos la drena drásticamente).
2. **Costo metabólico basal dependiente del genoma ($c_{\text{basal}}(\mathcal{G}_i)$):** Mantener un hardware más potente cuesta más energía por tick, impidiendo que la evolución infle trivialmente todas las capacidades al infinito:
   $$c_{\text{basal}}(\mathcal{G}_i) = c_0 + c_{\text{mem}} \cdot C_{\max, i}^2 + c_{\text{perc}} \cdot r_{\text{perc}, i}^2 + c_{\text{com}} \cdot r_{\text{com}, i}^2$$
   *(El costo cuadrático en $C_{\max, i}$ preserva la restricción fundamental $C_{\max, i} \ll N$: un agente que intente evolucionar un cerebro gigante muere de inanición antes de amortizarlo, forzando a que el escalamiento cognitivo ocurra por agregación en Meta-Agentes y no por hipertrofia individual).*
3. **Condición de Muerte:** Si al finalizar el tick $E_i(t+1) \le 0$, el agente $a_i$ muere y es retirado del entorno.
4. **Condición de Reproducción:** Si $E_i(t+1) \ge E_{\text{reprod}}$ (y la población total no supera la capacidad de carga ambiental $M_{\max}$), el agente $a_i$ se reproduce generando un descendiente $a_{\text{hijo}}$ en una celda vecina libre (o en la misma celda):
   - El progenitor transfiere una fracción $\phi_E \in (0, 1)$ (ej. $\phi_E = 0.5$) de su energía al hijo y paga un costo de gestación $c_{\text{gest}}$:
     $$E_{\text{hijo}}(t+1) = \phi_E (E_i(t+1) - c_{\text{gest}}), \qquad E_i(t+1) \leftarrow (1 - \phi_E)(E_i(t+1) - c_{\text{gest}})$$
   - El linaje del hijo se registra como $\mathcal{H}_{\text{hijo}} = (\text{id}_i, g_i + 1, t + 1)$.

---

### 6.2. Herencia Genética y Mutación Acotada ($R_{13}$)
El descendiente hereda los hiperparámetros cognitivos $\Theta_i = (\alpha_i, \gamma_i, \epsilon_i, \omega_{\text{bond}, i})$ y las capacidades discretas $\mathcal{G}_i = (C_{\max, i}, r_{\text{perc}, i}, r_{\text{com}, i})$ del progenitor con mutación estocástica controlada:

1. **Parámetros continuos ($\theta \in \Theta_i$, con dominio $[\theta_{\min}, \theta_{\max}]$):**
   $$\theta_{\text{hijo}} = \text{clip}\left(\theta_{\text{padre}} + \xi, \; \theta_{\min}, \; \theta_{\max}\right), \quad \xi \sim \begin{cases} \mathcal{N}(0, \sigma_{\text{mut}}^2) & \text{con prob. } p_{\text{mut}} \\ 0 & \text{con prob. } 1 - p_{\text{mut}} \end{cases}$$
2. **Capacidades discretas ($g \in \mathcal{G}_i$, con dominio entero $[g_{\min}, g_{\max}]$ y $C_{\max} \le C_{\text{límite}} < N$):**
   $$g_{\text{hijo}} = \text{clip}\left(g_{\text{padre}} + \delta_g, \; g_{\min}, \; g_{\max}\right), \quad \delta_g \in \{-1, 0, +1\} \text{ con prob. } \left(\tfrac{p_{\text{mut,cap}}}{2}, 1 - p_{\text{mut,cap}}, \tfrac{p_{\text{mut,cap}}}{2}\right)$$

---

### 6.3. Herencia Cultural Vertical ($\mathcal{M}_{\text{padre}} \to \mathcal{M}_{\text{hijo}}$, $R_{14}$)
Para resolver el cuello de botella descubierto en el Experimento 001 (donde la regla anti-cámara de eco $R_6$ causaba la extinción del conocimiento social tras purgar a los descubridores originales en C4), la reproducción incorpora **transmisión cultural intergeneracional**:

Al nacer en el instante $t$, el hijo recibe hasta $K_{\text{herencia}} \le C_{\max, \text{hijo}}$ creencias seleccionadas entre las de mayor utilidad epistémica $U(k, t)$ de la memoria de su progenitor $\mathcal{M}_{\text{padre}}(t)$ que superen $c_{\text{umbral}}$. Para cada creencia transferida $k_{\text{padre}} = (\rho, \hat{v}, c, n, \tau, d)$:
$$k_{\text{hijo}} = \left(\rho, \; \hat{v}, \; c_{\text{hijo}} = \gamma_{\text{gen}} \cdot c, \; n = 1, \; \tau = t, \; d = 0\right)$$
donde $\gamma_{\text{gen}} \in (0, 1]$ (ej. $\gamma_{\text{gen}} = 0.85$) es el **factor de retención cultural intergeneracional**.
- **Invariante de honestidad epistémica:** Toda creencia heredada verticalmente nace con $d = 0$ (`from_direct_experience = False`), porque el hijo no experimentó físicamente el recurso: lo recibió por tradición familiar. Sin embargo, al inicializarse con $\tau = t$ en el nacimiento del hijo, la tradición sobrevive al cambio de generación y le otorga al descendiente una ventaja de arranque para validar empíricamente los recursos benéficos (momento en que pasará a $d = 1$) y evitar los venenosos sin pagar el costo letal del ensayo y error desde cero.

---

## 7. Arquitectura Holónica y Jerarquía Recursiva Ilimitada (Fase II — Experimento 003)

Para que conjuntos de agentes puedan operar como un agente más capaz ($L=1$), y conjuntos de estos meta-agentes puedan volver a operar en conjunto ($L=2, 3, \dots, K$) **sin ningún límite fijo de niveles**, definimos formalmente la **Jerarquía Holónica Recursiva**.

### 7.1. Definición Inductiva de un Holón (`AgentNode`) de Nivel Arbitrario $L \in \mathbb{N}_0$
Todo participante activo del sistema es un **Holón** (o nodo agéntico) $u$. El conjunto de todos los holones posibles $\mathcal{U}$ se define inductivamente:

1. **Caso Base (Nivel $L = 0$, Agente Elemental):**
   Todo `MicroAgent` $a_i$ es un holón hoja con:
   $$\text{children}(a_i) = \emptyset, \qquad L(a_i) = 0, \qquad |a_i| = 1$$
   donde $L(u)$ es el **nivel jerárquico** y $|u|$ es la **masa** (cantidad total de agentes elementales de nivel $0$ contenidos en el subárbol de $u$).

2. **Paso Inductivo (Nivel $L \ge 1$, Meta-Agente Compuesto):**
   Dado un conjunto finito de $k \ge 2$ holones activos disjuntos $\{u_1, u_2, \dots, u_k\} \subset \mathcal{U}$ (que pueden ser del mismo o de distinto nivel), su acoplamiento forma un nuevo holón compuesto $U = \text{Composite}(u_1, \dots, u_k)$ con:
   $$\text{children}(U) = \{u_1, \dots, u_k\}$$
   $$L(U) = 1 + \max_{u_j \in \text{children}(U)} L(u_j)$$
   $$|U| = \sum_{u_j \in \text{children}(U)} |u_j|$$
   $$\text{leaves}(U) = \bigcup_{u_j \in \text{children}(U)} \text{leaves}(u_j)$$

> **Propiedad de Escalamiento Ilimitado:** Como un holón $U$ de nivel $L$ implementa exactamente la misma interfaz matemática que un holón de nivel $0$, dos o más holones de nivel $L=1$ pueden unirse en un holón de nivel $L=2$, dos de nivel $L=2$ en uno de nivel $L=3$, y así sucesivamente hasta cualquier nivel $K \in \mathbb{N}$ que la riqueza energética del entorno sea capaz de sostener.

---

### 7.2. Propiedades Colectivas Emergentes de un Holón de Nivel $L \ge 1$
Un holón compuesto $U$ de cualquier nivel $L \ge 1$ opera como una unidad cohesiva con las siguientes propiedades derivadas recursivamente de sus hijos $\text{children}(U) = \{u_1, \dots, u_k\}$:

1. **Memoria Distribuida Integrada ($\mathcal{M}_{\text{holón}}(U)$):**
   Ningún nodo padre duplica ni almacena en un "servidor central" las creencias de sus miembros; en cambio, la memoria efectiva de $U$ es la proyección agregada recursiva de las memorias de sus sub-nodos:
   $$\mathcal{M}_{\text{holón}}(U) = \bigoplus_{u_j \in \text{children}(U)} \mathcal{M}_{\text{holón}}(u_j)$$
   donde el operador de agregación epistémica $\bigoplus$ combina creencias sobre un mismo patrón $\rho$ ponderando por confianza (aplicando la regla de consenso §2.3 B) y conserva la unión de los patrones disjuntos.
   - **Capacidad Epistémica Efectiva:**
     $$C_{\text{eff}}(U) = \left|\mathcal{M}_{\text{holón}}(U)\right| \le \sum_{a_i \in \text{leaves}(U)} C_{\max, i}$$
     Un holón de masa $|U|$ con memorias internas diversificadas puede alcanzar $C_{\text{eff}}(U) \ge N$, cubriendo el $100\%$ de las leyes del mundo y desbloqueando recursos compuestos de orden $m \le C_{\text{eff}}(U)$ que eran inalcanzables para sus partes por separado.

2. **Campo Perceptual Unificado ($\mathcal{O}(U, t)$):**
   El campo visual del holón $U$ es la unión de las observaciones de sus sub-nodos inmediatos:
   $$\mathcal{O}(U, t) = \bigcup_{u_j \in \text{children}(U)} \mathcal{O}(u_j, t)$$

3. **Pozo Metabólico y Costo de Coordinación Jerárquica ($c_{\text{coord}}(U)$):**
   La energía total del holón es $E(U, t) = \sum_{u_j \in \text{children}(U)} E(u_j, t)$. Todo retorno energético obtenido por $U$ (incluyendo el desbloqueo de recursos compuestos $r^{(m)}$) se distribuye entre sus hojas proporcionalmente a su contribución epistémica o de forma equitativa, pero mantener la estructura jerárquica de nivel $L(U)$ exige pagar por tick un **costo metabólico de coordinación**:
   $$c_{\text{coord}}(U) = c_{\text{enlace}} \cdot |\text{children}(U)| \cdot (1 + \alpha_{\text{nivel}} \cdot L(U))$$
   - *Equilibrio termodinámico:* Si el entorno sólo contiene recursos simples ($m=1$), el costo $c_{\text{coord}}(U) > 0$ hace que los niveles altos sean deficitarios y se disuelvan (`SPLIT`). Si el entorno contiene recursos compuestos ricos ($m > C_{\max}$), el superávit energético $v_{\text{éxito}}(r^{(m)}) \gg c_{\text{coord}}(U)$ selecciona y estabiliza niveles jerárquicos cada vez más profundos ($L = 1, 2, \dots, K$).

---

### 7.3. Operadores Dinámicos de Fusión (`BOND`, $R_{15}$) y Fisión (`SPLIT`, $R_{16}$)

La jerarquía no está fija al inicio de la simulación: todos los agentes comienzan en $L=0$ y la topología arbórea emerge y se reconfigura dinámicamente en cada tick $t$.

#### 1. Fusión Holónica (`BOND(u_a, u_b) -> U_nuevo`)
Dos holones raíces activos $u_a$ y $u_b$ (de cualquier nivel $L(u_a), L(u_b) \in \mathbb{N}_0$) situados dentro de su vecindad de comunicación mutua se fusionan en un nuevo holón padre $U = \text{Composite}(u_a, u_b)$ de nivel $L(U) = 1 + \max(L(u_a), L(u_b))$ si y sólo si se cumplen tres condiciones locales:
1. **Viabilidad energética:** $E(u_a, t) \ge E_{\text{min\_bond}}$ y $E(u_b, t) \ge E_{\text{min\_bond}}$.
2. **Complementariedad Epistémica (Sinergia de Memoria):** El índice de disimilitud de Jaccard entre sus conjuntos de patrones conocidos supera un umbral mínimo $\theta_{\text{sinergia}}$:
   $$\text{Sinergia}(u_a, u_b) = 1 - \frac{|\text{Patrones}(u_a) \cap \text{Patrones}(u_b)|}{|\text{Patrones}(u_a) \cup \text{Patrones}(u_b)|} \ge \theta_{\text{sinergia}}$$
   *(Evita fusionar clones con memorias redundantes que pagarían costo de coordinación sin ampliar su capacidad epistémica combinada $C_{\text{eff}}$).*
3. **Acuerdo mutuo:** La propensión combinada $\frac{1}{2}(\omega_{\text{bond}}(u_a) + \omega_{\text{bond}}(u_b))$ supera un sorteo estocástico o la presencia de un recurso compuesto cercano de orden $m > \max(C_{\text{eff}}(u_a), C_{\text{eff}}(u_b))$ que sí es resoluble por la unión $C_{\text{eff}}(u_a \cup u_b) \ge m$.

#### 2. Fisión Holónica (`SPLIT(U) -> children(U)`)
Un holón compuesto $U$ de nivel $L \ge 1$ se disuelve liberando intactos a sus sub-nodos inmediatos $u_1, \dots, u_k \in \text{children}(U)$ (de nivel $\le L-1$) cuando ocurre cualquiera de las dos condiciones siguientes:
1. **Déficit de rendimiento cooperativo:** El balance energético neto medio del holón durante una ventana de $\Delta t_{\text{eval}}$ ticks cae por debajo de la suma de lo que sus miembros obtendrían por separado (el costo de coordinación $c_{\text{coord}}(U)$ no se amortiza).
2. **Dispersión espacial o pérdida de cohesión:** La distancia espacial entre los sub-nodos supera el radio de cohesión del holón, o todos sus miembros salvo uno han muerto.

---

### 7.4. Endosimbiosis Reproductiva Holónica y Selección Multinivel (Margulis & Wilson, $R_{17}$)
En lugar de reducir la evolución a la competencia individual entre genes sueltos, la Fase II incorpora la **simbiogénesis hereditaria**:
- Cuando un holón compuesto $U$ de nivel $L \ge 1$ acumula una reserva energética conjunta $E(U, t) \ge |U| \cdot E_{\text{reprod}}$ (gracias a haber desbloqueado recursos compuestos $r^{(m)}$ de alto valor), el holón puede reproducirse **como unidad simbiótica integrada** (`REPRODUCE_HOLON(U) -> U_hijo`):
  1. Se clona recursivamente la topología arbórea de $U$, instanciando un descendiente $a'_i$ por cada hoja $a_i \in \text{leaves}(U)$ (aplicando mutación genética $R_{13}$ y herencia cultural vertical $R_{14}$ a cada hoja) y preservando los enlaces jerárquicos en el nuevo holón hijo $U_{\text{hijo}}$ de nivel $L(U_{\text{hijo}}) = L(U)$.
  2. De este modo, **la alianza cooperativa misma se vuelve heredable**: la descendencia no necesita redescubrir desde cero cómo asociarse ni qué fragmentos del mundo memorizar cada miembro.
- **Ecuación de Selección Multinivel:** El cambio evolutivo responde a dos componentes: la selección *dentro* de los grupos y la selección *entre* holones. Como el retorno de los recursos compuestos $v_{\text{éxito}}(r^{(m)}) = v_0 m^{\kappa_{\text{comp}}}$ sólo es accesible para holones con alta sinergia interna y se reparte en el pozo común $E(U, t)$, la varianza de aptitud *entre* holones domina a la tentación egoísta individual.

---

### 7.5. Causalidad Descendente y Particionamiento Epigenético Intra-Holón (Denis Noble, $R_{18}$)
En un sistema biológico real, el organismo o nivel superior $L$ modula hacia abajo la expresión y el estado de sus partes de nivel $< L$ (*downward causation*). En IDE v2.0, todo holón compuesto $U$ ejerce **causalidad descendente** sobre sus sub-nodos mediante dos mecanismos locales:

1. **Inhibición de Redundancia Epistémica (Particionamiento de Memoria Intra-Holón):**
   Cuando un agente hoja $a_i \in \text{leaves}(U)$ evalúa la utilidad de retención $U_i(k, t)$ de una creencia sobre el patrón $\rho$ en su `BoundedMemory`, el holón aplica un **factor de descuento por redundancia fraterna** si otro compañero $a_j \in \text{leaves}(U) \setminus \{a_i\}$ ya retiene $\rho$ con mayor confianza ($c_j(\rho) > c_i(\rho) \ge c_{\text{umbral}}$):
   $$U_{\text{holón}}(k, t \mid U) = U(k, t) \cdot (1 - \psi_{\text{red}} \cdot \mathbb{I}[\exists a_j \in \text{leaves}(U) \setminus \{a_i\} : c_j(\rho) > c_i(\rho)])$$
   donde $\psi_{\text{red}} \in [0, 1)$ (ej. $\psi_{\text{red}} = 0.7$).
   - **Efecto emergente:** Sin aumentar $C_{\max}$ de ningún individuo, los miembros de un holón dejan de desperdiciar sus escasos slots recordando los mismos patrones que ya recuerda su compañero de simbiosis, forzando la **ortogonalización espontánea de sus memorias** ($\mathcal{M}_i \cap \mathcal{M}_j \to \emptyset$) y maximizando la capacidad epistémica efectiva del holón hacia su cota teórica $C_{\text{eff}}(U) \to \sum_{a_i \in \text{leaves}(U)} C_{\max, i}$.
2. **Modulación Epigenética de la Exploración ($\epsilon_{\text{eff}}$):**
   Si la cobertura efectiva del holón $C_{\text{eff}}(U)$ aún es insuficiente para desbloquear un recurso compuesto visible de orden $m$, el holón incrementa temporalmente la tasa de exploración efectiva $\epsilon_{\text{eff}}$ de sus sub-nodos periféricos; una vez cubiertos los $m$ patrones, la reduce para conservar energía y explotar el conocimiento adquirido.

---

### 7.6. Construcción de Nicho y Estigmergia Espacial ($R_{19}$)
Además de la memoria interna $\mathcal{M}_i$ y la transmisión oral/vertical, los agentes y holones pueden **modificar epistémicamente su entorno físico** depositando en su ubicación actual $l \in \mathcal{L}$ un **Rastro Estigmérgico** (*Stigmergic Trace*):
$$\mathcal{S}(l, t) = (\rho, \; \hat{v}_{\text{rastro}}, \; I(l, t)), \quad I(l, t) \in [0, 1]$$
- Cuando un agente o holón experimenta directamente ($d=1$) un recurso de alto impacto en $l$, deposita o refuerza un rastro con intensidad $I(l, t) = c_{\text{directa}}$, que decae pasivamente en el suelo a tasa $\delta_{\text{suelo}}$ por tick:
  $$I(l, t+1) = \max(0, \; I(l, t) - \delta_{\text{suelo}})$$
- Cualquier agente futuro (incluso de generaciones posteriores $g + k$) que transite por $l$ percibe $\mathcal{S}(l, t)$ en su `Observation` y puede asimilarlo como testimonio ambiental con factor de descuento $\gamma_{\text{suelo}}$. Así, el propio paisaje físico actúa como una **memoria externa compartida (construcción de nicho)** que sobrevive a la muerte de los individuos.

---

## 8. Métricas Formales de Evolución y Jerarquía Holónica (Fase II: M8–M12)

Además de las métricas M1–M7 (§4), la Fase II incorpora cinco métricas formales para cuantificar la adaptación intergeneracional y la emergencia de niveles jerárquicos:

### M8. Progreso Evolutivo Intergeneracional ($\Delta_{\text{evo}}(g)$)
Sea $\mathcal{A}_g$ el conjunto de agentes nacidos en la generación $g \in \{0, 1, \dots, G_{\max}\}$. Se mide la precisión media de decisión $\overline{Acc}(g)$, la longevidad media $\overline{L}_{\text{vida}}(g)$ y la tasa neta de recolección energética $\overline{\dot{E}}(g)$ por generación:
$$\Delta_{\text{evo}}(g) = \overline{Acc}(g) - \overline{Acc}(0)$$
- **Éxito evolutivo:** Pendiente generacional positiva ($\Delta_{\text{evo}}(g) > 0$ con prueba de signo sobre $n \ge 5$ semillas para $g \ge 3$).

### M9. Retención Cultural Transgeneracional ($Pers_{\text{gen}}(\rho^*)$)
Generalización evolutiva de M4: tras retirar el recurso físico $\rho^*$ en $t_{\text{purge}}$, se mide cuántas **generaciones completas** ($g - g(t_{\text{purge}})$) permanece viva la creencia verdadera sobre $\rho^*$ en una población donde el $100\%$ de la generación que coexistió con el estímulo físico ya ha muerto por recambio demográfico natural.

### M10. Deriva vs. Selección de Rasgos Heredables ($\Theta(t), \mathcal{G}(t)$)
Evolución temporal de la media y varianza poblacional de cada gen $(\alpha, \gamma, \epsilon, \omega_{\text{bond}}, C_{\max}, r_{\text{perc}}, r_{\text{com}})$, comparada contra un **control nulo de deriva genética neutral** (donde la reproducción ocurre al azar sin depender de la energía $E_i$). Permite demostrar mediante el criterio E4 que el cambio en los hiperparámetros es adaptación real y no deriva aleatoria.

### M11. Profundidad y Distribución Holónica ($L_{\max}(t), H_{\text{holón}}(t)$)
En cada tick $t$, sea $\mathcal{U}_{\text{root}}(t)$ el conjunto de holones raíces activos:
- **Profundidad Jerárquica Máxima:** $L_{\max}(t) = \max_{u \in \mathcal{U}_{\text{root}}(t)} L(u)$.
- **Fracción de Masa por Nivel ($f_L(t)$):** Proporción de agentes elementales que operan integrados dentro de holones de nivel $\ge L$.
- **Entropía Estructural Jerárquica ($H_{\text{holón}}(t)$):** Diversidad de niveles de organización coexistiendo simultáneamente en el ecosistema.

### M12. Tasa de Resolución Composicional por Orden ($CompRate(m, t)$)
Para cada orden de complejidad de recurso compuesto $m \in \{1, 2, \dots, m_{\max}\}$, fracción de interacciones exitosas sobre el total de intentos:
$$CompRate(m, t) = \frac{\text{Desbloqueos Exitosos de orden } m}{\text{Interacciones Totales con recursos de orden } m}$$
- **Predicción fundamental de la Fase II:** Para todo orden $m > C_{\max}$, $CompRate(m, t) \approx 0$ en poblaciones de nivel fijo $L=0$, mientras que $CompRate(m, t) \to 1$ a medida que la población emerge niveles holónicos $L = 1, 2, \dots, K$ cuya capacidad epistémica efectiva cumple $C_{\text{eff}}(U) \ge m$.
