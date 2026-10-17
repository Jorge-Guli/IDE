# Especificación de Definiciones Formales — Proyecto IDE (v0.2)

Este documento establece de manera rigurosa y sin ambigüedades qué significa cada concepto dentro del sistema de **Inteligencia Distribuida Emergente (IDE)** antes de escribir código. Toda implementación debe respetar estas definiciones.

> **Relación con los demás documentos.** La visión está en el [Documento Fundacional](DOCUMENTO_FUNDACIONAL.md) y la arquitectura en las [Definiciones Técnicas](DEFINICIONES_TECNICAS.md). Los valores numéricos, firmas y reglas de desempate exactos son normativos en [`design.md`](openspec/changes/ide-emergent-distributed-intelligence/design.md); los valores que aparecen aquí como "ej." son ilustrativos.

---

## 1. Definiciones Ontológicas (Qué existe en el sistema)

### 1.1. Tiempo ($t$)
El sistema evoluciona en pasos de tiempo discretos (ticks):
$$t \in \{0, 1, 2, \dots, T\}$$
En cada paso $t$, todos los agentes perciben, se comunican, deciden, actúan y aprenden de forma local (ver §2), sin un coordinador que dirija sus estrategias. El tick es un reloj de simulación, no una entidad cognitiva.

---

### 1.2. Espacio y Entorno ($\mathcal{E}$)
El **Entorno** es el contenedor abstracto donde habitan los agentes y existen los recursos. Para garantizar que el sistema pueda escalar de una grilla 2D a espacios continuos, grafos complejos o entornos 3D, el entorno se define únicamente por **tres relaciones espaciales**:

1. **Conjunto de Ubicaciones ($\mathcal{L}$):** Donde puede estar un agente o un recurso.
   - *En Grilla 2D Toroidal:* $\mathcal{L} = \{0, \dots, W-1\} \times \{0, \dots, H-1\}$, donde las coordenadas hacen *wrap-around* ($\pmod W, \pmod H$).
   - *En Grafo Espacial (futuro):* $\mathcal{L} = V$ (nodos de un grafo $G=(V, E)$).
   - *En Espacio Continuo (futuro):* $\mathcal{L} = \mathbb{R}^d$.
2. **Vecindad de Percepción ($\mathcal{N}_{\text{perc}}(l)$):** El conjunto de ubicaciones que un agente situado en $l \in \mathcal{L}$ puede observar directamente.
3. **Vecindad de Comunicación ($\mathcal{N}_{\text{com}}(l)$):** El conjunto de agentes con los que un agente situado en $l \in \mathcal{L}$ puede intercambiar mensajes en el instante $t$.

> **Regla de Oro de Escalabilidad:** Ningún agente conoce las coordenadas globales del mapa ni su tamaño total. El agente sólo recibe lo que hay dentro de $\mathcal{N}_{\text{perc}}$ y $\mathcal{N}_{\text{com}}$.

---

### 1.3. Recurso ($r$) y Regla del Mundo ($F$)
Un **Recurso** es una entidad presente en el entorno con la que un agente puede interactuar (consumir/recolectar o evitar).

Cada recurso $r$ posee dos partes (en el Experimento 001, $v(r) \in \{+1.0, -1.0\}$; los recursos neutrales quedan para experimentos posteriores):
1. **Rasgos Observables ($\mathbf{x}_r$):** Un conjunto de atributos discretos visibles antes de interactuar con él.
   - Ejemplo: $\mathbf{x}_r = (\text{color}, \text{forma}, \text{textura})$.
2. **Consecuencia Real ($v(r) \in \mathbb{R}$):** El efecto real sobre el agente (ej. $+10$ si es nutritivo, $-15$ si es venenoso, $0$ si es inerte).
   - **Restricción:** $v(r)$ es **invisible** a simple vista. El agente sólo descubre $v(r)$ de manera directa si interactúa con el recurso (pagando el costo o recibiendo el beneficio), o de manera indirecta si otro agente se lo comunica.

La **Regla del Mundo** $F(\mathbf{x}_r) \to v(r)$ es el conjunto de leyes que asocia patrones observables con sus consecuencias. Supongamos que existen $N$ tipos o patrones distintos en el entorno:
$$\mathcal{P}_{\text{mundo}} = \{P_1, P_2, \dots, P_N\}$$
Resolver el entorno significa conocer la consecuencia asociada a los $N$ patrones.

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
- **$d \in \{0, 1\}$ (Origen Empírico):** $d = 1$ si el propio agente experimentó directamente el patrón; $d = 0$ si la creencia proviene sólo de testimonios. Es la base de la protección anti-cámara de eco (§2.3).

---

### 1.5. Memoria Limitada del Agente ($\mathcal{M}_i$)
Cada agente $a_i$ posee una memoria local $\mathcal{M}_i$ compuesta por una lista de creencias:
$$\mathcal{M}_i(t) = \{k_1, k_2, \dots, k_m\}, \quad \text{con } m \le C_{\max}$$

- **$C_{\max}$ (Capacidad de Memoria Individual):** Número máximo de creencias que un agente puede almacenar simultáneamente.
- **Restricción Crítica del Experimento 001:**
  $$C_{\max} \ll N$$
  Donde $N$ es la cantidad total de patrones del mundo $\mathcal{P}_{\text{mundo}}$.
  *Ejemplo:* Si en el mundo existen $N = 12$ tipos de recursos distintos, y cada agente tiene capacidad $C_{\max} = 3$, ningún agente puede almacenar más del $25\%$ del conocimiento del mundo.

---

### 1.6. Agente Mínimo ($a_i$)
Un agente es una unidad autónoma caracterizada en el instante $t$ por:
$$a_i(t) = \langle \text{id}_i, l_i(t), E_i(t), \mathcal{M}_i(t), \Theta_i \rangle$$

1. **Identificador ($\text{id}_i$):** Único para trazabilidad de métricas (no usado para jerarquías).
2. **Ubicación actual ($l_i(t) \in \mathcal{L}$):** Posición en el entorno.
3. **Estado Interno ($E_i(t)$):** Nivel de energía/salud o utilidad acumulada. Si un agente consume recursos beneficiosos, $E_i$ sube; si consume recursos dañinos, $E_i$ baja. *En el Experimento 001 $E_i$ no se modela: no afecta la supervivencia ni la decisión, y el desempeño se mide sólo con la calidad de las decisiones (M2).*
4. **Memoria Local ($\mathcal{M}_i(t)$):** Sujeta a $|\mathcal{M}_i(t)| \le C_{\max}$.
5. **Parámetros Locales ($\Theta_i$):** Tasas de aprendizaje ($\alpha$), factor de descuento de confianza social ($\gamma$), tasa de exploración ($\epsilon$).

---

## 2. Dinámica Cognitiva y Reglas de Interacción

En cada ciclo $t$, cada agente ejecuta procesos estrictamente locales en este orden: **(1)** percibir, **(2)** comunicarse (consultar, responder, difundir y revalidar), **(3)** decidir, **(4)** actuar y aprender por experiencia directa, y **(5)** olvidar (decaimiento pasivo). La comunicación ocurre **antes** de decidir para que la consulta en vivo (§2.4) pueda informar la decisión del mismo tick. Las subsecciones siguientes describen cada regla, no el orden.

### 2.1. Aprendizaje Individual (Por Experiencia Directa)
Cuando el agente $a_i$ interactúa directamente con un recurso $r$ de patrón $\rho$ y recibe la consecuencia real $v$:

1. **Si $\rho$ NO está en $\mathcal{M}_i$:**
   Crea una nueva creencia con alta confianza inicial (porque la vivió en carne propia):
   $$k_{\text{nuevo}} = (\rho, \hat{v} = v, c = c_{\text{directa}}, n = 1, \tau = t)$$
   *(donde típicamente $c_{\text{directa}} \approx 0.8$).*
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
El receptor no sabe nada sobre $\rho$. Adopta la creencia pero aplicando un **descuento por testimonio indirecto** ($\gamma \in (0, 1)$, ej. $\gamma = 0.7$):
$$c_{\text{recibida}} = \gamma \cdot c_{\text{ext}}$$
*(Un rumor nunca tiene la misma fuerza inicial que haberlo vivido directamente; cada salto de boca en boca sin verificación empírica atenúa la confianza).*

#### Escenario B: Consenso ($\rho \in \mathcal{M}_j$ y $\text{sign}(\hat{v}_j) == \text{sign}(\hat{v}_{\text{ext}})$)
Ambos agentes coinciden. El receptor promedia la estimación ponderada por confianza:
$$\hat{v}_j \leftarrow \frac{c_j \hat{v}_j + (\gamma c_{\text{ext}}) \hat{v}_{\text{ext}}}{c_j + \gamma c_{\text{ext}}}$$
y refuerza moderadamente su confianza:
$$c^{*} = c_j + \eta_{\text{consenso}} \cdot \gamma c_{\text{ext}} (1 - c_j)$$
- Si el emisor tiene evidencia directa ($d_{\text{ext}} = 1$): $c_j \leftarrow \min(1.0, c^{*})$.
- Si el emisor sólo transmite un rumor ($d_{\text{ext}} = 0$): $c_j \leftarrow \min\left(\max(c_j, \gamma c_{\text{ext}}),\; c^{*}\right)$, y $\tau_j$ **no** se actualiza.

*(Protección anti-cámara de eco: sin la segunda regla, dos agentes que sólo tienen el mismo rumor podrían rebotárselo hasta $c \to 1$ sin ninguna evidencia física; y si el rebote refrescara $\tau$, quedarían exentos del olvido para siempre.)*

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

Existen **dos mecanismos complementarios** que producen la emergencia colectiva:

1. **Difusión Continua y Recambio Adaptativo:**
   Los agentes intercambian creencias constantemente al cruzarse. Las creencias verdaderas son revalidadas una y otra vez por distintos agentes que interactúan con el entorno, manteniendo su confianza $c$ alta en la población, mientras que las falsas chocan con la experiencia empírica y se extinguen.
2. **Consulta Local en Vivo (*Collective Query / Micro-Grupos*):**
   Cuando el agente $a_i$ observa un recurso con patrón $\rho \notin \mathcal{M}_i$, puede emitir una **consulta local** (`QUERY(ρ)`) a sus vecinos inmediatos en $\mathcal{N}_{\text{com}}(l_i)$.
   - Si algún vecino $a_k \in \mathcal{N}_{\text{com}}(l_i)$ posee $\rho$ en su memoria $\mathcal{M}_k$, responde inmediatamente con su creencia $k$.
   - De este modo, un grupo de $G$ agentes cercanos con memorias disjuntas de tamaño $C_{\max}$ actúa efectivamente como un **meta-agente con memoria combinada de hasta $G \times C_{\max}$**, sin que ningún individuo haya ampliado su hardware interno.

---

## 3. Definiciones Operacionales de Fenómenos Emergentes

Para que el proyecto tenga rigor científico, no usaremos palabras vagas. Cada fenómeno se define operacionalmente así:

| Concepto | Definición Operacional Exacta |
| :--- | :--- |
| **Conocimiento Individual** | Conjunto de patrones $\rho$ en $\mathcal{M}_i(t)$ cuyo signo predicho $\text{sign}(\hat{v})$ coincide con la realidad $\text{sign}(F(\rho))$ y cuya confianza supera el umbral de decisión ($c \ge c_{\text{umbral}}$). |
| **Conocimiento Colectivo (Poblacional)** | Unión de los conocimientos válidos presentes en al menos un agente activo ($p_{\min} = 1/M$). |
| **Conocimiento Accesible** | Para un agente, unión de su conocimiento individual y el de sus vecinos de comunicación a $d = 1$ salto en el instante $t$. Es lo que puede usar para decidir mediante una consulta en vivo. |
| **Superávit Cognitivo Emergente ($\Delta_{\text{emerg}}$)** | Diferencia entre el rendimiento (precisión $Acc$, M2) de la población conectada y el de una población idéntica sin comunicación, con las mismas condiciones iniciales: $\Delta_{\text{emerg}} = Acc_{\text{col}} - Acc_{\text{iso}}$. Un $\Delta_{\text{emerg}} > 0$ consistente entre semillas demuestra que la población supera el límite de sus partes. La cota teórica individual $C_{\max}/N$ se usa en cambio para la cobertura (M1). |
| **Epistemología Distribuida (Inmunidad a Falsedad)** | Capacidad de la red para hacer que la prevalencia de una creencia falsa inyectada ($F(\rho) \neq \hat{v}_{\text{falso}}$) tienda a $0$ cuando $t \to \infty$ sin intervención externa. |
| **Memoria Colectiva Persistente** | Condición en la cual una creencia verdadera descubierta en $t_0$ por un subconjunto de agentes $S_0$ sigue activa en la población en $t_1 \gg t_0$ después de que el $100\%$ de los agentes originales de $S_0$ han sido eliminados o han olvidado el dato. |

---

## 4. Definición Matemática de las Métricas (Experimento 001)

Sea $\mathcal{A}$ la población de $M$ agentes, $\mathcal{P}_{\text{mundo}}$ el conjunto de $N$ reglas del entorno y $C_{\max} < N$ el límite de memoria individual.

### M1. Cobertura Epistémica Individual vs. Colectiva
- **Cobertura Individual Media ($Cov_{\text{ind}}(t)$):** Fracción de las $N$ reglas del mundo que un agente promedio conoce correctamente en el paso $t$. Por restricción de hardware, siempre se cumple:
  $$Cov_{\text{ind}}(t) \le \frac{C_{\max}}{N} < 1.0$$
- **Cobertura Colectiva ($Cov_{\text{col}}(t)$):** Fracción de las $N$ reglas del mundo que están correctamente representadas en la población en el paso $t$.
- **Cobertura Accesible Media ($Cov_{\text{acc}}(t)$):** Fracción media, sobre agentes, de las $N$ reglas que cada agente conoce válidamente o puede obtener de un vecino a 1 salto. Sin comunicación, $Cov_{\text{acc}} = Cov_{\text{ind}}$.
  - *Advertencia:* $Cov_{\text{col}} \to 1$ **no** demuestra emergencia, porque una población aislada de $M$ agentes también la alcanza cuando $M \cdot C_{\max} \ge N$ (80 × 3 ≫ 12).
  - *Éxito del Experimento:* $Cov_{\text{acc}}^{\text{col}}(t) > Cov_{\text{acc}}^{\text{iso}}(t)$, con $Cov_{\text{ind}}(t) \le \frac{C_{\max}}{N}$ en ambos modos.

### M2. Precisión de Decisión Colectiva ($Acc_{\text{col}}(t)$) vs. Aislada ($Acc_{\text{iso}}(t)$)
En una ventana de tiempo $\Delta t$, sea $D_{\text{totales}}$ el número de oportunidades de decisión (un agente con al menos un recurso en su celda) y $D_{\text{correctas}}$ las acertadas: consumir un recurso benéfico, o no consumir nada cuando todos los recursos de la celda son dañinos. Ignorar una celda con algún recurso benéfico, o consumir uno dañino, es incorrecto. Se juzga la intención en el momento de decidir, aunque otro agente consuma antes el recurso:
$$Acc(t) = \frac{D_{\text{correctas}}}{D_{\text{totales}}}$$
- Se compara la población con comunicación activa ($Acc_{\text{col}}$) contra una población idéntica con comunicación desactivada ($Acc_{\text{iso}}$).
- **Criterio de Emergencia:** la precisión acumulada final cumple $Acc_{\text{col}}(T) > Acc_{\text{iso}}(T)$ de forma estadísticamente significativa sobre varias semillas independientes (cada semilla corre ambos modos con idénticas condiciones iniciales). Una versión más exigente, a evaluar como análisis secundario, es $Acc_{\text{col}}(T) > \sup_t Acc_{\text{iso}}(t)$.

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
  2. **Tiempo de Recuperación ($T_{\text{rec}}$):** Pasos necesarios para que la media móvil de $Acc$ (ventana de 20 ticks) regrese al $90\%$ de su media en los 20 ticks previos al daño.

### M6. Tasa de Rechazo de Falsedad ($FalseDecay(t)$)
En $t_{\text{inject}}$, se inyecta en una fracción $q$ de agentes ($q = 25\%$) una creencia falsa plantada como rumor: $k_{\text{falsa}} = (\rho_x, \hat{v}_{\text{erróneo}}, c = 0.95, n = 1, t_{\text{inject}}, d = 0)$.
- Se mide la curva de prevalencia $P_{\text{falsa}}(t)$ (porcentaje de agentes que sostienen la creencia falsa en $t > t_{\text{inject}}$).
- *Éxito epistemológico:* $P_{\text{falsa}}(t) \to 0$ conforme los agentes contrastan el rumor con la realidad del entorno.
- *Trampa de evitación:* un agente que cree que un patrón benéfico es dañino no lo prueba, así que no puede refutarlo empíricamente. Si la creencia falsa es un rumor, su corrección depende de la duda social, del olvido y de la exploración, y es un fenómeno a medir en el Experimento 001. Si en cambio es evidencia directa que quedó obsoleta porque el mundo cambió (Experimento 004), la población puede quedar bloqueada, porque el consenso entre testigos directos refresca $\tau$. Para ese caso se compararán dos mecanismos: $\tau$ como edad de la evidencia más reciente y la re-verificación escéptica con probabilidad $\epsilon_{\text{recheck}}(1-c)$.

### M7. Eficiencia y Costo de Comunicación ($Cost_{\text{com}}(t)$)
Cantidad media de mensajes transmitidos por agente por paso de tiempo ($\frac{\text{Mensajes}(t)}{M}$), evaluando la ganancia de precisión por cada mensaje enviado.

---

## 5. Contratos de Software (Interfaces Desacopladas)

Antes de implementar, la arquitectura en Python se compromete a separar estrictamente estos 5 componentes (detalle en las [Definiciones Técnicas](DEFINICIONES_TECNICAS.md)):

1. **`KnowledgeUnit` (Estructura de Datos Pura):** Representa la creencia $k = (\rho, \hat{v}, c, n, \tau, d)$. Inmutable; las actualizaciones son funciones puras que devuelven una creencia nueva.
2. **`BoundedMemory` (Módulo de Memoria):** Contiene hasta $C_{\max}$ unidades `KnowledgeUnit`. Ejecuta inserción, búsqueda por patrón, decaimiento temporal y reemplazo por menor utilidad $U(k, t)$.
3. **`MicroAgent` (Cerebro Local):** Contiene `BoundedMemory` y las reglas de aprendizaje directo, asimilación social (Escenarios A, B, C) y toma de decisiones. **No importa ni conoce ninguna clase de Grilla 2D.**
4. **`Environment` (Interfaz Abstracta del Mundo):**
   - Implementación 1: `ToroidalGrid2D` (Experimento 001).
   - Implementaciones futuras: `SpatialGraph`, `ContinuousSpace2D`.
5. **`ExperimentRunner` y `MetricsCollector`:** Ejecuta los protocolos (base, falsificación, daño) con semillas reproducibles (`seed`) y calcula las métricas M1–M7.
