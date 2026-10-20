# Design: Fase II-B (v2.5) — ADN Compacto de 32 bits, Conducta Evolucionable y Ecología

> **Reformulación del 2026-10-20 (D43–D56).** Con la etapa A completa (bloques 1 a 5, D30–D35 implementadas), el responsable del proyecto decidió que la Fase II-B corrija las cuestiones de base que hacían de la Fase II un experimento sin salida, en lugar de agregar mecanismos sobre la misma arquitectura. Las decisiones D43–D56, al final de la sección de decisiones, **prevalecen** sobre D30–D42 donde las contradicen, y cada decisión afectada lo indica en su encabezado. El pre-registro D42 queda **sustituido** por el borrador D56, que se aprueba en la tarea 0.5 antes de seguir con el bloque 6. Ninguna afirmación de D42 se midió.

## Context

La Fase II quedó implementada, corrida y archivada (`openspec/changes/archive/2026-10-20-ide-v2-evolutionary-holonic-intelligence/`, decisiones D19–D29). Sus requisitos vigentes están en `openspec/specs/`. Sus resultados, en `docs/RESULTADOS.md`, son negativos para C5–C8 y dejan cuatro preguntas exploratorias abiertas:
- el genoma congelado rinde más que la evolución;
- los recursos compuestos casi no se resuelven;
- la redundancia de los holones crece;
- con abundancia casi no hay recambio generacional, por una causa no verificada.

Esta fase implementa, como cambio opcional y ablacionable, la propuesta de [`docs/vision/ARQUITECTURA_ADN_HOLONICO.md`](../../../docs/vision/ARQUITECTURA_ADN_HOLONICO.md). Respecto de la propuesta, corrige:
- **El direccionamiento de factores de transcripción.** La propuesta prometía 128 canales con 6 bits; quedan 64 canales, porque 6 bits sólo alcanzan para 64.
- **La profundidad de la red regulatoria.** Con dos pasadas hay un solo nivel de regulación, no "múltiples etapas".
- **Los rangos de promotores y destinos sin significado.** Quedan declarados reservados e inertes.
- **El inventario.** Telómeros y SOS se separan en dos reglas ($R_{29}$ y $R_{30}$), y el trinquete pasa a $R_{31}$.
- **El campo `z_layer` y el estado de endospora del contexto epigenético.** No entran: el primero es de la Fase III y el segundo lo maneja el motor.

**Fuentes normativas.**
- **Fases I y II:** los specs vigentes y los `design.md` archivados (D1–D18 y D19–D29).
- **Fase II-B:** este documento es la **fuente única** de firmas, fórmulas, valores por defecto y desempates. Sus decisiones continúan la numeración, desde D30.
- **Documentos raíz:** `docs/DEFINICIONES_FORMALES.md` y `docs/DEFINICIONES_TECNICAS.md` incorporan estas decisiones en la tarea 0.3, al aprobarse el pre-registro.

**Restricciones heredadas que esta fase no puede romper:**
- los hashes SHA-256 dorados de `tests/test_performance_equivalence.py`;
- las auditorías AST de `tests/test_micro_agent.py` y `tests/test_simulation_engine.py`: `src/ide/agent/` no importa `environments`, `simulation` ni `experiments`, y sólo `protocol.py` construye `Message`;
- los 14 campos de `TickMetrics` y los campos de `EvolutionaryTickMetrics`;
- `DESIGN_RULES`, `PHASE2_DESIGN_RULES`, `ALL_DESIGN_RULES` y el pre-registro de la Fase II, que no se modifican;
- la igualdad de historiales entre procesos con distinto `PYTHONHASHSEED`.

**Diagnóstico que motiva la reformulación (2026-10-20).** Una lectura del código de las Fases I y II (`engine.py`, `micro_agent.py`, `ports.py`) y de sus resultados identificó cinco problemas de base. Mientras no se corrijan, cualquier mecanismo nuevo repite el experimento de la Fase II a mayor costo:
1. **La conducta es código fijo.** `MicroAgent.decide_action` es una política escrita a mano. El genoma, plano o compacto, sólo ajusta sus parámetros, así que la evolución no puede producir una conducta nueva.
2. **Las capacidades se otorgan por decreto.** Las reglas diseñadas producen directamente lo que se quiere observar (castas, esporulación, estabilidad del holón), y por eso toda afirmación sale programada por construcción.
3. **El entorno es un problema de clasificación.** Los recursos reaparecen al instante y los agentes no interactúan físicamente entre sí: no hay escasez, competencia ni coevolución.
4. **El motor es monolítico.** `step()` concentra todos los mecanismos detrás de banderas y llama directamente a la memoria del agente; las métricas se calculan dentro del bucle.
5. **La medición sólo pregunta si una hipótesis pasa.** No hay métricas de evolución abierta, la potencia estadística es baja (10 semillas) y la viabilidad demográfica se descubre tarde, cuando el control nulo ya se extinguió.

---

## Goals / Non-Goals

**Goals:**
- Representar el genotipo de cada hoja ($L = 0$) como un `CompactDNA` de codones de 32 bits, con expresión condicional al contexto (nivel holónico, rol, energía) y una red regulatoria de un nivel ($R_{24}$).
- Cobrar el costo cuadrático $R_{21}$ sobre el fenotipo **expresado**, más un costo lineal por codón.
- **Principio de la reformulación (D43): la regla da la capacidad y el ADN decide su uso.** Ninguna regla nueva produce por sí sola la conducta que se quiere observar.
- **Conducta codificada en el ADN ($R_{32}$, D45–D47):** un puerto de política, la política escrita a mano como caso particular y una política genética cuyos impulsos de conducta los expresan codones con promotores de contexto, sensoriales y regulados. El ADN fundador reproduce exactamente la política escrita a mano.
- **Ecología con interacciones físicas (D48, D49):** recursos agotables ($R_{33}$), heterogeneidad espacial y estacional ($R_{34}$), cadáveres ($R_{35}$), transferencia de energía ($R_{36}$) y depredación ($R_{37}$).
- **Mecanismos del ADN:** señal posicional epigenética ($R_{25}$), plásmidos ($R_{26}$), inmunidad CRISPR ($R_{27}$), endospora como conducta disponible ($R_{28}$), senescencia ($R_{29}$), mutación SOS ($R_{30}$), compromiso simbiótico expresado ($R_{31}$) y recombinación ($R_{38}$), cada uno con su bandera y su ablación.
- **Motor por sistemas (D44):** un pipeline ordenado de sistemas y observadores de telemetría, con los hashes dorados como test de aceptación.
- **Medición de evolución abierta (D53) y pre-registro con potencia (D55, D56):** métricas de actividad evolutiva, compuerta de viabilidad antes de cualquier afirmación, 30 semillas, corrección de Holm y tamaño de efecto mínimo.
- Compatibilidad bit a bit con las Fases I y II cuando las banderas nuevas están en su valor por defecto.

**Non-Goals:**
- **Operadores lógicos y órganos de sandbox de la Fase IV** (modo `AST_PIPE` y destinos `0x0D`–`0x3F` y `0x48`–`0xFF`): quedan reservados e **inertes**.
- **Promotores espaciales de la Fase III** (`0x28`–`0x7F`): reservados e inertes. Los promotores sensoriales `0x20`–`0x27` se especifican en D46.
- **ADN propio de los holones.** Un `CompositeAgent` no tiene ADN: su genética es la de sus hojas.
- **Comunicación nueva.** El ADN y los plásmidos **no transportan creencias**: el conocimiento social sigue entrando sólo por `assimilate_testimony`. El ADN sólo decide **si** el agente comunica (D46.6).
- **Programas en el ADN** (máquina virtual tipo Avida), **espacio 3D**, **interfaz web** y **aceleración en GPU**: son de la Fase III.
- **Recalibración del perfil a la vista de las afirmaciones.** La única calibración permitida es la compuerta de viabilidad de D55, declarada de antemano y sólo demográfica.

---

## Decisions (Numeradas D30 a D56, continuando D1–D29)

### Decisión 30: Alcance, Compatibilidad y Generadores
> **Ampliada por D43 y D52:** las banderas nuevas de la reformulación también valen `False` por defecto y siguen la misma regla de dependencias inertes. La reformulación no agrega generadores.

1. **Banderas inactivas por defecto.** Todas las banderas nuevas valen `False`: `enable_compact_dna`, `enable_epigenetic_roles`, `enable_plasmid_hgt`, `enable_crispr_immunity`, `enable_sporulation`, `enable_telomere_senescence`, `enable_sos_mutation` y `enable_symbiotic_ratchet`.
2. **Comportamiento con las banderas por defecto.** El motor, el agente, la memoria, la grilla, `TickMetrics`, `EvolutionaryTickMetrics` y todos los generadores se comportan exactamente como en la Fase II. Ninguna rama nueva consume un generador, ni cambia un valor o un orden de iteración.
3. **Dependencias inertes, no inválidas.** $R_{25}$, $R_{26}$ y $R_{27}$ sólo actúan con `enable_compact_dna=True`; $R_{25}$ y $R_{31}$, sólo con `enable_holonic_hierarchy=True`; $R_{27}$, sólo con $R_{26}$ activa; $R_{28}$, $R_{29}$ y $R_{30}$, sólo con `enable_evolution=True`. Con su requisito apagado, la bandera es **inerte**: no lanza `ValueError`. Así, ablacionar $R_{24}$ en una configuración con $R_{25}$ activa es válido, y deja inerte a $R_{25}$, igual que ablacionar $R_{15}$ dejaba inertes $R_{16}$–$R_{18}$ en la Fase II.
4. **Generador nuevo `hgt_rng`.**
   - Se declara `self.hgt_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(config.seed, spawn_key=(5,))))`.
   - Su único uso es el sorteo de la conjugación de plásmidos (D37). Sólo se consume con `enable_compact_dna=True` y `enable_plasmid_hgt=True`.
   - Va aparte para que activar $R_{26}$ no desplace la secuencia de `evo_rng`.
   - Se declara también en `CLAUDE.md`.
5. **Uso de `evo_rng`.** La mutación del ADN (D35) usa `evo_rng`, igual que `mutate_genome`. Con `enable_compact_dna=True`, la secuencia de `evo_rng` difiere de la de la Fase II: es esperable, porque el operador es otro.
6. **Telemetría separada.** La telemetría de esta fase vive en `engine.genetic_history: list[GeneticTickMetrics]` (D41). No se agregan campos a `TickMetrics` ni a `EvolutionaryTickMetrics`.

### Decisión 31: Contratos de Dominio y Configuración
En `src/ide/domain/types.py`, sin tocar los tipos existentes:

```python
class EpigeneticRole(Enum):
    NONE = "NONE"
    EXPLORER = "EXPLORER"    # casta periférica (menor grado interno en el holón)
    LIBRARIAN = "LIBRARIAN"  # casta de conocimiento propio único
    NERVE = "NERVE"          # casta de enlace (mayor grado interno)

@dataclass(frozen=True)
class CompactDNA:
    chromosome: tuple[int, ...]        # codones de 32 bits, herencia vertical
    plasmids: tuple[int, ...] = ()     # a lo sumo `max_plasmids` codones, herencia vertical y horizontal (R26)
    crispr_memory: tuple[int, ...] = ()  # firmas de plásmidos rechazados, FIFO de `crispr_memory_size` (R27)
    # __post_init__: ValueError si algún codón no está en [0, 2**32 - 1], si `chromosome` está vacío,
    # o si `plasmids` o `crispr_memory` tienen codones repetidos.

@dataclass(frozen=True)
class EpigeneticContext:
    holon_level: int = 0                  # nivel del nodo raíz que contiene a la hoja; 0 si está sola
    role: EpigeneticRole = EpigeneticRole.NONE
    energy_ratio: float = 1.0             # E_i / reproduction_threshold

@dataclass(frozen=True)
class ExpressedPhenotype:
    genome: AgentGenome           # los 7 rasgos expresados
    lifespan: int                 # T_max expresada (R29)
    spore_threshold: float        # E_espora expresada (R28)
    expressed_codons: int         # codones que modulan un rasgo en este contexto (telemetría)
```

La longitud de `chromosome` no se valida en el tipo: las cotas `dna_min_length` y `dna_max_length` son de la configuración y las aplica la mutación (D35).

En `src/ide/config.py`, `SimulationConfig` incorpora al final:

```python
    # --- Fase II-B: ADN compacto y expresión condicional (R24) ---
    enable_compact_dna: bool = False
    dna_codon_cost: float = 0.0002          # c_dna por codón (cromosoma + plásmidos + CRISPR) y por tick
    dna_point_mutation_rate: float = 0.05   # probabilidad por codón de invertir un bit al reproducirse
    dna_duplication_rate: float = 0.02
    dna_deletion_rate: float = 0.02
    dna_min_length: int = 1
    dna_max_length: int = 32
    stress_energy_ratio: float = 0.35       # promotor 0x18 y estrés de R30
    surplus_energy_ratio: float = 0.85      # promotor 0x19
    # --- R25 ---
    enable_epigenetic_roles: bool = False
    # --- R26 y R27 ---
    enable_plasmid_hgt: bool = False
    dna_excision_rate: float = 0.02         # copia de un codón del cromosoma a un plásmido al reproducirse
    max_plasmids: int = 4
    hgt_rate: float = 0.05                  # probabilidad por tick de que un donante elegible conjugue
    hgt_energy_ratio: float = 0.85          # el donante necesita E >= hgt_energy_ratio * reproduction_threshold
    enable_crispr_immunity: bool = False
    crispr_eval_ticks: int = 20
    crispr_toxicity_threshold: float = 0.20
    crispr_memory_size: int = 4
    # --- R28 ---
    enable_sporulation: bool = False
    spore_energy_threshold: float = 0.30
    spore_cost_fraction: float = 0.05       # costo de la endospora = fracción de metabolic_base_cost
    # --- R29 ---
    enable_telomere_senescence: bool = False
    telomere_base_lifespan: int = 600
    telomere_min_lifespan: int = 150
    telomere_max_lifespan: int = 1200
    senescence_cost_rate: float = 1e-5      # costo extra = rate * (edad - T_max)^2
    # --- R30 ---
    enable_sos_mutation: bool = False
    sos_window: int = 50
    sos_hypermutation_factor: float = 4.0
    sos_high_fidelity_factor: float = 0.25
    sos_high_fidelity_energy_ratio: float = 1.5
    # --- R31 ---
    enable_symbiotic_ratchet: bool = False
    lock_composite_threshold: int = 3
    lock_coord_discount: float = 0.5
```

> **Campo eliminado por D52.4:** `lock_composite_threshold` y su validación `lock_composite_threshold >= 1` salen de la configuración con la reformulación (D50.3).

**Validación en `__post_init__`.** Siempre se aplica, aunque la bandera esté apagada, porque son rangos de parámetros:
- **En $[0, 1]$:** `dna_point_mutation_rate`, `dna_duplication_rate`, `dna_deletion_rate`, `dna_excision_rate`, `hgt_rate`, `spore_cost_fraction`, `sos_high_fidelity_factor`, `lock_coord_discount`.
- **No negativos:** `dna_codon_cost`, `crispr_toxicity_threshold`, `senescence_cost_rate`, `spore_energy_threshold`.
- **Estrictamente positivos:** `stress_energy_ratio`, `surplus_energy_ratio`, `hgt_energy_ratio`, `sos_hypermutation_factor`, `sos_high_fidelity_energy_ratio`.
- **Enteros mínimos:** `dna_min_length >= 1`, `dna_max_length >= FOUNDER_DNA_LENGTH` (9, D32), `dna_min_length <= FOUNDER_DNA_LENGTH`, `max_plasmids >= 1`, `crispr_eval_ticks >= 1`, `crispr_memory_size >= 1`, `sos_window >= 1`, `lock_composite_threshold >= 1`, `telomere_min_lifespan >= 1`, `telomere_min_lifespan <= telomere_base_lifespan <= telomere_max_lifespan`.
- **Orden:** `stress_energy_ratio < surplus_energy_ratio`.

**Validación con `enable_compact_dna=True`:**
- **Requisitos.** Exige `enable_evolution=True`, `perception_radius >= 1` y `comm_radius >= 1`.
- **Bases dentro de sus cotas.** Cada base de rasgo debe estar dentro de las cotas de D33, para que el ADN fundador exprese exactamente la base:
  - `alpha_learning` en $[0.01, 1]$;
  - `memory_capacity` menor o igual que la cota de $C_{\max}$;
  - los radios menores o iguales que la cota de radio;
  - `spore_energy_threshold <= reproduction_threshold`.
- **Mensaje de error.** El `ValueError` menciona el campo.

### Decisión 32: El Codón de 32 bits y el ADN Fundador
Un codón es un `int` en $[0, 2^{32} - 1]$. Se usan enteros de Python, no `numpy.uint32`, para que la igualdad, el `repr` y el hash no dependan del dtype.

```text
 31          24 23          16 15  14 13      8 7            0
+--------------+--------------+------+---------+--------------+
|   PROMOTER   |    TARGET    | MODE | CHANNEL |   PAYLOAD    |
+--------------+--------------+------+---------+--------------+
```

**Campos del codón** (en `src/ide/agent/dna.py`):
- `decode_codon(codon) -> Codon`, con `Codon` como `NamedTuple` de `promoter`, `target`, `mode`, `channel` y `delta`.
- Las fórmulas exactas son:
  - `promoter = (c >> 24) & 0xFF`;
  - `target = (c >> 16) & 0xFF`;
  - `mode = (c >> 14) & 0x3`;
  - `channel = (c >> 8) & 0x3F`;
  - `p = c & 0xFF` y `delta = (p - 256 if p >= 128 else p) / 128.0`, así que `delta` va de −1.0 a +0.9921875.
- `encode_codon(promoter, target, mode=0, channel=0, payload=0) -> int` es la inversa, con `payload` en $[-128, 127]$. Lanza `ValueError` fuera de rango.

**Modos:**
- `0` = `ADDITIVE`;
- `1` = `REPRESSOR`;
- `2` = `MULTIPLICATIVE`;
- `3` = `RESERVED`: el `AST_PIPE` de la Fase IV, inerte en v2.5.

**Promotores (`PROM`).** Un promotor se dice **activo** en un contexto:

| Valor | Nombre | Activo si |
| :---: | :--- | :--- |
| `0x00` | `ALWAYS_BASAL` | siempre |
| `0x01` | `SOLITARY_L0` | `context.holon_level == 0` |
| `0x02`–`0x0A` | `IN_HOLON_Lk`, con $k = \text{prom} - 1$ | `context.holon_level >= k` |
| `0x10` | `ROLE_EXPLORER` | `context.role is EpigeneticRole.EXPLORER` |
| `0x11` | `ROLE_LIBRARIAN` | `context.role is EpigeneticRole.LIBRARIAN` |
| `0x12` | `ROLE_NERVE` | `context.role is EpigeneticRole.NERVE` |
| `0x18` | `STRESS_LOW_ENERGY` | `context.energy_ratio < config.stress_energy_ratio` |
| `0x19` | `SURPLUS_HIGH_ENERGY` | `context.energy_ratio >= config.surplus_energy_ratio` |
| `0x80`–`0xBF` | `TF_0`–`TF_63` | en la pasada 2, si el canal `prom - 0x80` está encendido (D33) |
| resto | reservados | nunca (`0x0B`–`0x0F`, `0x13`–`0x17`, `0x1A`–`0x7F` y `0xC0`–`0xFF`) |

**Destinos (`TARGET`):**

| Valor | Rasgo | Base $b$ | Escala $k$ | Cotas | Tipo |
| :---: | :--- | :--- | ---: | :--- | :--- |
| `0x00` | $\alpha$ | `alpha_learning` | 0.40 | $[0.01, 1]$ | real |
| `0x01` | $\gamma$ | `gamma_social_discount` | 0.40 | $[0, 1]$ | real |
| `0x02` | $\epsilon$ | `epsilon_explore` | 0.35 | $[0, 1]$ | real |
| `0x03` | $\omega_{\text{bond}}$ | `initial_bond_affinity` | 0.50 | $[0, 1]$ | real |
| `0x04` | $C_{\max}$ | `memory_capacity` | 3.0 | $[1, C^{\text{tope}}]$ | entero |
| `0x05` | $r_{\text{perc}}$ | `perception_radius` | 2.0 | $[1, r^{\text{tope}}]$ | entero |
| `0x06` | $r_{\text{com}}$ | `comm_radius` | 2.0 | $[1, r^{\text{tope}}]$ | entero |
| `0x07` | $T_{\max}$ | `telomere_base_lifespan` | 250 | $[$`telomere_min_lifespan`$,$ `telomere_max_lifespan`$]$ | entero |
| `0x08` | $E_{\text{espora}}$ | `spore_energy_threshold` | 0.50 | $[0,$ `reproduction_threshold`$]$ | real |
| `0x09` | `EMIT_TF` | — | — | — | emite el canal `channel` |
| `0x0A`–`0xFF` | reservados | — | — | — | inertes |

Las cotas de los rasgos enteros son las mismas que usa `mutate_genome` en la Fase II:
- $C^{\text{tope}}$ es `max_genome_memory_capacity`, acotado además por `num_world_patterns - 1` cuando `enforce_memory_constraint=True`;
- $r^{\text{tope}} = (\min(\text{grid\_width}, \text{grid\_height}) - 1) // 2$.

**ADN fundador.**
- `founder_dna(config) -> CompactDNA` devuelve `CompactDNA(chromosome=tuple(encode_codon(0x00, t) for t in range(0x00, 0x09)))`: un codón `ALWAYS_BASAL`, `ADDITIVE`, de canal 0 y `payload` 0 por cada rasgo `0x00`–`0x08`.
- `FOUNDER_DNA_LENGTH = 9`.
- Expresa exactamente la base en cualquier contexto (D33): `transcribe_phenotype(founder_dna(c), ctx, c).genome == genome_from_config(c)`, para todo contexto y toda configuración válida con `enable_compact_dna=True`.

### Decisión 33: Transcripción en Dos Pasadas y Fenotipo Expresado
`transcribe_phenotype(dna: CompactDNA, context: EpigeneticContext, config: SimulationConfig) -> ExpressedPhenotype` es una función **pura**. Los codones se recorren en el orden `chromosome + plasmids`; `crispr_memory` no se transcribe.

1. **Pasada 1 (contexto).** Son activos los codones con promotor menor que `0x80` cuyo promotor está activo según D32.
2. **Factores de transcripción.** Entre los activos de la pasada 1, cada codón con `target == 0x09` y `mode != 3` suma 1 a `act[channel]` si `mode` es 0 o 2, y a `rep[channel]` si `mode` es 1. El canal $c$ está **encendido** si y sólo si `act[c] > rep[c]`.
3. **Pasada 2 (regulados).** Son activos los codones con promotor en `0x80`–`0xBF` cuyo canal `promoter - 0x80` está encendido. Sus `EMIT_TF` **no** encienden canales: la red tiene un solo nivel de regulación, y se declara así.
4. **Expresión de cada rasgo.** Para cada destino $T$ entre `0x00` y `0x08`, sea $A_T$ el conjunto de codones activos (pasadas 1 y 2) con ese destino:
   - $S = \sum_{a \in A_T,\ \text{mode}=0} \delta_a$;
   - $\rho = \prod_{a \in A_T,\ \text{mode}=1} (1 - |\delta_a|)$;
   - $\mu = \prod_{a \in A_T,\ \text{mode}=2} (1 + \delta_a)$;
   - los codones con modo 3 se ignoran;
   - $x_T = b_T \cdot \mu + k_T \cdot \rho \cdot S$.
   - Un rasgo real vale `min(hi, max(lo, x))`. Un rasgo entero vale `min(hi, max(lo, math.floor(x + 0.5)))`; no se usa `round`, que redondea al par. Con $A_T$ vacío, $x_T = b_T$.
   - El represor atenúa sólo la parte aditiva, no la multiplicativa: se declara.
   - Los productos y la suma se acumulan en el orden de recorrido, para que el resultado en coma flotante sea determinista.
5. **Salida.**
   - `genome = AgentGenome(alpha_learning, gamma_social_discount, epsilon_explore, bond_affinity, memory_capacity, perception_radius, comm_radius)` con los valores de `0x00`–`0x06`;
   - `lifespan` es el valor de `0x07` y `spore_threshold` el de `0x08`;
   - `expressed_codons` es la cantidad de codones activos con destino en `0x00`–`0x08` y modo distinto de 3.
6. **Bases.** Las bases $b_T$ se toman siempre de la **configuración base** de la población (D34), nunca de la configuración fenotípica del agente, para que la expresión no se acumule de un tick a otro.
7. **Equivalente sin ADN.** `phenotype_from_genome(genome, config) -> ExpressedPhenotype` devuelve `ExpressedPhenotype(genome, config.telomere_base_lifespan, config.spore_energy_threshold, 0)`. Es el fenotipo de un agente sin ADN (`enable_compact_dna=False`), con el que $R_{28}$ y $R_{29}$ funcionan también sobre el genoma plano.

### Decisión 34: Expresión en Vida, Costo y Nacimiento (R24)
1. **Estado del agente.** `MicroAgent` incorpora:
   - `dna: CompactDNA | None`, que vale `None` sin ADN;
   - `phenotype: ExpressedPhenotype`;
   - `base_config: SimulationConfig`: la configuración de la población. Un fundador recibe la del motor, y un descendiente la `base_config` de su progenitor;
   - `epigenetic_role: EpigeneticRole`, que vale `NONE` al nacer;
   - `birth_tick: int`, que vale 0 en los fundadores;
   - `is_endospore: bool`, que vale `False`;
   - `last_stress_tick: int | None`, que vale `None`.
   - Métodos nuevos: `express(context: EpigeneticContext, tick: int) -> bool`, `set_epigenetic_role(role)`, `set_dna(dna)` y `set_endospore(flag)`.
   - `genome` sigue existiendo y devuelve el genoma **expresado**: con ADN, `phenotype.genome`.
2. **`express`.**
   - Con `dna is None`, no hace nada y devuelve `False`.
   - Con ADN, calcula el fenotipo con `transcribe_phenotype(dna, context, base_config)`. Si `genome` cambió:
     - reemplaza `_genome`;
     - reemplaza `_config` por la configuración fenotípica, con el mismo `replace` de los 6 campos que `from_lineage`;
     - llama a `memory.resize(genome.memory_capacity, tick)`.
   - Devuelve `True` si cambió algún radio, para que el motor actualice el entorno.
   - **Caché.** Puede memoizar por `(min(context.holon_level, 9), context.role, banda)`, con `banda` ∈ {estrés, normal, superávit} según los umbrales de D32. El caché se invalida cuando cambia el ADN. Es una optimización: un test exige que coincida con la transcripción directa.
3. **Achicar la memoria (`BoundedMemory.resize(capacity, tick)`).**
   - Con `capacity < 1`, lanza `ValueError`.
   - Fija la capacidad y, mientras `len(memory) > capacity`, elimina la unidad de menor utilidad con el mismo criterio y desempate que el desalojo ($R_2$, incluida la penalización $R_{18}$).
   - Agrandar la capacidad no borra nada.
   - El olvido forzado por un cambio de fenotipo es parte declarada de $R_{24}$.
4. **Fase 0 del tick (`_express_phenotypes`).**
   - Corre sólo con `enable_compact_dna=True`, al empezar `step()` y antes de calcular la permutación y el alcance local.
   - Para cada `aid` en `sorted(self.agents)` arma el contexto:
     - `holon_level` es el de `self.root_nodes[self.agent_to_root[aid]]`, o 0 si la hoja es su propia raíz;
     - `role` es `agent.epigenetic_role`;
     - `energy_ratio = agent.energy / config.reproduction_threshold`.
   - Llama a `agent.express(context, tick)`. Si devuelve `True`, llama a `env.set_agent_radii(aid, r_perc, r_com)`.
   - No consume generadores, y cada agente se expresa sobre el estado de fin del tick anterior: no hay efectos de orden.
5. **Costo metabólico con ADN.** Al cobrar el metabolismo (D21 de la Fase II), el costo basal es:
   - `compute_metabolic_cost(agent.genome, config)`, sobre el genoma **expresado** en la Fase 0 del tick;
   - más `compute_dna_cost(agent.dna, config) = config.dna_codon_cost * (len(chromosome) + len(plasmids) + len(crispr_memory))`;
   - más la senescencia de D39.
   - Sin ADN, `compute_dna_cost` vale 0.
6. **Nacimiento.**
   - El hijo nace con su ADN mutado (D35) y se expresa en el acto con `EpigeneticContext(0, EpigeneticRole.NONE, energía_del_hijo / reproduction_threshold)`.
   - `spawn_agent_near` recibe los radios de ese fenotipo de nacimiento.
   - El hijo nace con `birth_tick = tick`, `is_endospore = False` y `last_stress_tick = None`.
   - Desde el tick siguiente, la Fase 0 lo expresa con su contexto real.
7. **Reproducción neutral ($R_{12}$ ablacionada).** El donante sorteado con `donor_rng` aporta su **ADN** en lugar de su genoma. La secuencia de `donor_rng` no cambia.

### Decisión 35: Operadores de Mutación del ADN
`mutate_dna(dna: CompactDNA, config: SimulationConfig, rng: np.random.Generator, scale: float = 1.0) -> CompactDNA`, en `src/ide/agent/dna.py`:
0. **Puerta de $R_{13}$.** Si `config.mutation_rate == 0.0` y `config.discrete_mutation_prob == 0.0` (la ablación pre-registrada de $R_{13}$), devuelve `dna` sin consumir `rng`. Así, la ablación de $R_{13}$ congela también el ADN sin modificar el pre-registro de la Fase II.
   - Las probabilidades efectivas son $p_x = \min(1, \text{scale} \cdot \text{config.dna\_}x\text{\_rate})$.
1. **Mutación puntual del cromosoma.**
   - Si el cromosoma no está vacío, extrae `u = rng.random(len(chromosome))`.
   - Para cada índice $i$, en orden, con `u[i] < p_point`, extrae `bit = int(rng.integers(0, 32))` y aplica `codon ^= 1 << bit`.
2. **Mutación puntual de los plásmidos.** Igual, sobre `plasmids`, sólo si no está vacío. Si un plásmido mutado coincide con otro, se elimina el duplicado posterior. También se descarta el plásmido mutado que coincida con un codón de `crispr_memory` (punto 12).
3. **Duplicación.**
   - Extrae `u = float(rng.random())`.
   - Si `u < p_dup` y `len(chromosome) < dna_max_length`, extrae `i = int(rng.integers(len(chromosome)))` e inserta una copia del codón `i` en la posición `i + 1`.
4. **Deleción.**
   - Extrae `u = float(rng.random())`.
   - Si `u < p_del` y `len(chromosome) > dna_min_length`, extrae `i = int(rng.integers(len(chromosome)))` y elimina el codón `i`.
5. **Escisión a plásmido.** Sólo con `enable_plasmid_hgt=True`:
   - Extrae `u = float(rng.random())`.
   - Si `u < p_exc`, extrae `i = int(rng.integers(len(chromosome)))`.
   - Si el codón `i` no está ya en `plasmids` ni en `crispr_memory`, lo agrega al final de `plasmids`. Si se pasa de `max_plasmids`, descarta el primero (FIFO).
6. **Lo que no muta.** `crispr_memory` se hereda sin mutar.

Los pasos 3 a 5 consumen siempre su extracción `u`. La extracción del índice sólo ocurre si el operador se aplica. La secuencia depende del estado, pero es determinista.

**Genoma plano con SOS ($R_{30}$).** Sin ADN, la escala se aplica a `mutate_genome` con una configuración escalada: `replace(config, mutation_rate=scale * mutation_rate, discrete_mutation_prob=min(1.0, scale * discrete_mutation_prob))`. Con `scale == 1.0` se pasa la configuración intacta, y la Fase II no cambia ni en un bit.

`MicroAgent.create_offspring(child_id, tick, rng, genome_source=None, dna_source=None, mutation_scale=1.0)`:
- **Con ADN:** muta `dna_source` o, si es `None`, el ADN propio con `mutate_dna(..., self.base_config, rng, mutation_scale)`.
- **Sin ADN:** conserva el comportamiento de la Fase II, con la escala de arriba.
- **Lo que hereda el hijo:** `plasmids` y `crispr_memory` vienen dentro del ADN. Los ensayos CRISPR pendientes (D37) **no** se heredan.

### Decisión 36: Roles Epigenéticos e Impronta (R25)
> **Reinterpretada por D50.1:** la asignación no cambia, pero $R_{25}$ pasa a ser una **señal posicional**. Ningún codón del ADN fundador la usa: la especialización que aparezca es la que la selección construya sobre esa señal.

`assign_epigenetic_roles(holon: CompositeAgent, local_reach: Mapping[int, Sequence[int]], config: SimulationConfig) -> dict[int, EpigeneticRole]`, en `holon.py`:
- **Contrato de `local_reach`.** Es el mismo de D25.1 de la Fase II, con la misma validación: lanza `ValueError` también con la regla apagada.
- **Regla apagada.** Con `enable_epigenetic_roles=False` o `enable_compact_dna=False`, devuelve `NONE` para todas las hojas.
- **Regla activa.** Sea $K(\ell)$ el conjunto de patrones de la memoria de $\ell$ con `confidence >= decision_conf_threshold`, `unique(ℓ)` $= |K(\ell) \setminus \bigcup_{\ell' \neq \ell} K(\ell')|$ sobre las hojas del holón, y `deg(ℓ)` $= |\text{loc}(\ell) \setminus \{\ell\}|$.
  1. `LIBRARIAN` es la hoja que maximiza `(unique(ℓ), |K(ℓ)|, -agent_id)`.
  2. `EXPLORER` es, entre las restantes, la que maximiza `(-deg(ℓ), -agent_id)`.
  3. `NERVE` es, si quedan hojas, la que maximiza `(deg(ℓ), -agent_id)` entre las restantes.
  4. Las demás quedan en `NONE`.
- **Función pura.** Lee las memorias de las hojas, como $R_{18}$, y no conoce coordenadas.

**Cuándo asigna el motor.**
- Asigna en la Fase 5, después de $R_{18}$, a cada `CompositeAgent` raíz en orden de `node_id` cuyo conjunto de hojas **cambió** desde su última asignación. El motor guarda `self._role_leaf_sets: dict[int, frozenset[int]]`, que va de cada raíz al conjunto de hojas que tenía al asignar.
- Las hojas que son su propia raíz vuelven a `NONE`.
- Las entradas de raíces que ya no existen se descartan.
- Los roles se escriben con `set_epigenetic_role` después de calcularlos todos.

**Impronta.** En la reproducción holónica ($R_{17}$), cada hoja hija recibe el rol de su progenitora, y el motor registra el conjunto de hojas de la réplica como ya asignado. La réplica conserva la impronta hasta que su composición cambie. Sin $R_{17}$, la impronta no actúa: un hijo individual nace solo, con `NONE`.

### Decisión 37: Plásmidos y Conjugación (R26) e Inmunidad CRISPR (R27)
**Conjugación (`_conjugate`).** Corre en la Fase 5, después de la reproducción, con `enable_compact_dna` y `enable_plasmid_hgt` activas:
1. **Donantes.** Son las hojas, en orden de `agent_id`, que cumplen: no son endospora, tienen `plasmids` no vacío y tienen `energy >= hgt_energy_ratio * reproduction_threshold`. El conjunto se fija **al empezar** el paso.
2. **Sorteo por donante.** Para cada donante, en orden:
   - `u = float(hgt_rng.random())`. Si `u >= hgt_rate`, el donante no conjuga.
   - Si conjuga, sus candidatos son `sorted(b for b in agentes vivos al empezar el paso if b != donante and not endospora and env.get_agent_distance(donante, b) <= 1)`.
   - Si hay candidatos: `receptor = candidatos[int(hgt_rng.integers(len(candidatos)))]` y `codón = plasmids_del_donante_al_empezar[int(hgt_rng.integers(len(plasmids)))]`.
   - Se registra el par `(receptor, codón)`.
3. **Aplicación.** Las transferencias se aplican después de sortearlas todas. Si hay dos o más, se aplican en el orden de `hgt_rng.permutation(len(transferencias))` sobre la lista registrada: con FIFO, la llegada de varios plásmidos al mismo receptor es un conflicto, y se resuelve por sorteo, como los conflictos físicos, no por `agent_id`. Cada una se aplica con `receive_plasmid(dna, codon, config) -> CompactDNA | None`:
   - Con $R_{27}$ activa y el codón en `crispr_memory`, devuelve `None`: la transferencia se **bloquea** y cuenta como rechazo.
   - Si el codón ya está en `plasmids`, devuelve el mismo ADN sin cambios.
   - Si no, lo agrega al final, con FIFO a `max_plasmids`.
   - Si el ADN cambió, el motor lo guarda con `set_dna`. Con $R_{27}$ activa, abre un ensayo `trials[codón] = (tick, energía actual, 0.0)` en el receptor. El tercer valor acumula la energía cedida a los hijos durante la ventana: cada `create_offspring` del receptor suma la energía del hijo a todos sus ensayos abiertos.

**Ensayo CRISPR (`_evaluate_crispr`).** Corre después de la conjugación, con `enable_crispr_immunity` activa. Para cada agente en orden de `agent_id`, y para cada ensayo en orden de codón:
- **Ensayo vencido** (`tick - t0 >= crispr_eval_ticks`):
  - Si el codón sigue en `plasmids` y el balance $\Delta E = \text{energy} - e_0 + \text{cedida} < -$`crispr_toxicity_threshold`, se purga con `purge_plasmid(dna, codon, config) -> CompactDNA`: lo quita de `plasmids` y lo agrega a `crispr_memory`, con FIFO a `crispr_memory_size`.
  - En cualquier caso, el ensayo se cierra.
- **Plásmido perdido.** Si el plásmido se perdió por FIFO antes del vencimiento, el ensayo se cierra al vencer, sin purga.

**Por qué se descuenta lo cedido (decisión del 2026-10-20).** Reproducirse cede `offspring_energy_share` de una energía de al menos `reproduction_threshold`, una caída de 1.1 o más con los valores por defecto. Sin descontarla, todo receptor que se reproduce dentro de la ventana purgaría el plásmido, sin relación con su efecto, y $R_{27}$ castigaría a los agentes exitosos.

**Lo que no hacen los plásmidos.** Transportan codones, no creencias. Son un canal genético, no epistémico: no pasan por `assimilate_testimony` ni por el control nulo de contenido. El control nulo de E4 no los altera, y así se declara.

### Decisión 38: Esporulación (R28)
> **Entrada sustituida por D50.2:** se entra en endospora sólo cuando la política genética elige la conducta `SPORULATE`. La regla de umbral de abajo queda sin efecto; la germinación, la física y el costo de la endospora se mantienen.

- **Entrada.** Con `enable_evolution` y `enable_sporulation` activas, en la Fase 5, después de la muerte y antes de la reproducción, en orden de `agent_id`, una hoja que no es endospora entra en endospora (`set_endospore(True)`) si cumple tres condiciones:
  - `energy <= phenotype.spore_threshold`;
  - su observación de la Fase 1 de ese tick no tiene recursos visibles;
  - con $R_{19}$ activa, su celda no tiene ningún rastro con `sign_value > 0`.
  - La entrada se evalúa antes de la reproducción (D41), así que los recién nacidos del tick no entran en ella.
- **Germinación.** En la Fase 1, inmediatamente después de `get_observation`, una endospora germina (`set_endospore(False)`) si su observación tiene algún recurso visible o, con $R_{19}$, su celda tiene un rastro positivo. Germina antes de emitir, y actúa normalmente en ese tick.
- **Física de la endospora:**
  - no llama a `perceive_and_emit_messages`, ni asimila estigmergia;
  - no envía ni recibe mensajes: se excluye del ruteo como emisora y como destinataria;
  - su acción de la Fase 3 es `IDLE` sin llamar a `decide_action`, así que no consume `self.rng`, y no suma oportunidad de decisión en M2;
  - no se reproduce, ni dona o recibe plásmidos;
  - sigue en su holón y su memoria decae normalmente.
- **Costo.** Paga `spore_cost_fraction * metabolic_base_cost`, más la senescencia de D39, en lugar del costo basal, el de ADN, el de movimiento y el de mensajes.
- **Sesgo declarado.** $R_{28}$ está diseñada para que poblaciones que la Fase II extinguía sobrevivan. La supervivencia que produzca es programada.

### Decisión 39: Senescencia Telomérica (R29) y Mutación SOS (R30)
**Senescencia.** `compute_senescence_cost(age: int, lifespan: int, config: SimulationConfig) -> float`, en `evolution.py`, devuelve `config.senescence_cost_rate * (age - lifespan) ** 2` si `config.enable_telomere_senescence` y `age > lifespan`, y `0.0` en otro caso. Con `enable_evolution` y `enable_telomere_senescence` activas, al cobrar el metabolismo:
- La edad es `age = tick - birth_tick`.
- Si `age > phenotype.lifespan`, el costo suma `senescence_cost_rate * (age - lifespan) ** 2`.
- Se cobra también a las endosporas.
- Con ADN, `lifespan` se expresa por el destino `0x07`. Sin ADN, vale `telomere_base_lifespan`.

**SOS.**
- **Registro del estrés.** Siempre, después del cobro metabólico y de la muerte, cada sobreviviente con `energy < stress_energy_ratio * reproduction_threshold` registra `last_stress_tick = tick`. No consume generadores.
- **Escala de mutación.** Con `enable_sos_mutation` activa, al reproducirse, la escala se decide con el estado del progenitor **antes** de partir la energía:
  - `sos_hypermutation_factor`, si `last_stress_tick is not None` y `tick - last_stress_tick <= sos_window`;
  - si no, `sos_high_fidelity_factor`, si `energy >= sos_high_fidelity_energy_ratio * reproduction_threshold`;
  - si no, 1.0.
  - La reproducción holónica aplica la regla a cada hoja.
- **Regla apagada.** Con la regla apagada, la escala es 1.0.

### Decisión 40: Trinquete Simbiótico (R31)
> **Condición de sellado sustituida por D50.3:** un holón se suelda cuando sus hojas expresan compromiso simbiótico, no por reproducirse ni por contar compuestos. Los efectos de un holón soldado se mantienen. `lock_composite_threshold` se elimina de la configuración.

- **Atributo.** `CompositeAgent` incorpora `is_locked: bool = False`.
- **Cuándo se suelda un holón.** Con `enable_holonic_hierarchy` y `enable_symbiotic_ratchet` activas, un holón **raíz** queda soldado en dos casos:
  - (a) al reproducirse por $R_{17}$: se sueldan el progenitor y su réplica;
  - (b) en el paso de coordinación de la Fase 5, si `cooperative_completions >= lock_composite_threshold`. El sello se aplica **antes** de cobrar el costo de coordinación y de evaluar `SPLIT`, así que el descuento y la protección rigen desde ese mismo tick.
- **Efectos de un holón soldado:**
  - `should_split_holon` devuelve `False`, por paciencia y por energía;
  - su costo de coordinación se multiplica por `lock_coord_discount`.
- **Lo que no impide.** La poda por muerte sigue actuando: si sobreviven dos o más hojas, el holón conserva el sello; con una sola, colapsa como en la Fase II. Un holón soldado puede fusionarse por `BOND` en un nivel superior, y conserva su sello si después queda expuesto como raíz.
- **Sesgo declarado.** La estabilidad que produzca $R_{31}$ es por decreto, no un hallazgo.

### Decisión 41: Orden de la Fase 5, Telemetría y Protocolos
> **Sustituida por D44 (pipeline), D53 (orden completo y telemetría) y D56 (protocolos).** Se conserva como antecedente.

**Orden completo del tick con la Fase II-B:**
- Fase 0: expresión.
- Fases 1 a 4: como en la Fase II, con la germinación y la exclusión de las endosporas de D38.
- Fase 5:
  - (i) `decay_memory`;
  - (ii) coordinación, con el sello y el descuento de $R_{31}$, `SPLIT` y `BOND`;
  - (iii) metabolismo, con el costo del ADN, la senescencia y la endospora;
  - (iv) muerte, registro del estrés y entrada en endospora;
  - (v) reproducción, con SOS, ADN e impronta;
  - (vi) conjugación ($R_{26}$) y ensayo CRISPR ($R_{27}$);
  - (vii) $R_{18}$ y asignación de roles ($R_{25}$);
  - (viii) `env.step_dynamics`;
  - (ix) métricas.
- Sin las banderas nuevas, el orden se reduce exactamente al de la Fase II.

**`GeneticTickMetrics`.** Es un `@dataclass(frozen=True)` nuevo en `metrics.py`, que se registra en cada tick en `engine.genetic_history`. Sus campos:
- `tick`;
- `mean_chromosome_length`, `mean_expressed_codons` y `mean_plasmids`, que valen 0.0 sin ADN;
- `endospores` y `senescent_agents` (con `age > lifespan`);
- `mean_age` y `max_age`;
- `explorers`, `librarians` y `nerves`;
- `locked_holons`;
- `hgt_transfers`, `crispr_rejections` y `crispr_purges`, que cuentan los eventos del tick.

**Protocolos (`src/ide/experiments/exp25_runner.py`).** Usan la infraestructura de `phase2_cli.py` (`ProtocolSpec`), y su resumen por condición incluye `final_accuracy`, `composite_completions`, `final_agents`, `final_active_agents` (hojas vivas que no están en endospora), `max_generation` y el resumen genético del último tick. Condiciones de comparación de cada protocolo:
- `002c`: `dna` (base), `flat_genome` (sin $R_{24}$), `frozen_dna` (sin $R_{13}$) y `drift` (sin $R_{12}$);
- `002d`: `telomeres` (base) y `no_telomeres` (sin $R_{29}$);
- `002e`: `sporulation` (base) y `no_sporulation` (sin $R_{28}$);
- `003c`: `roles` (base), `no_roles` (sin $R_{25}$) y `unlocked` (sin $R_{31}$).

### Decisión 42: Pre-Registro de la Fase II-B (APROBADO el 2026-10-20, decisión P4; SUSTITUIDO por D56)
> **Sustituido por el borrador D56 (reformulación del 2026-10-20), antes de medir ninguna afirmación.** Las afirmaciones C9–C12 se **retiran sin medir**: eran programadas por construcción y no acercaban el proyecto a su objetivo. El diagnóstico de la tarea 0.1 se conserva como antecedente de $R_{29}$. El texto de abajo se conserva como registro.

Esta decisión es **pre-registro**. El responsable del proyecto la aprobó el 2026-10-20 (tarea 0.2), sin cambios respecto del borrador y con las decisiones del 2026-10-20 ya incorporadas. Se aprobó **antes** de implementar y de mirar cualquier resultado: el único dato previo es el diagnóstico demográfico de la tarea 0.1, que no mide ninguna afirmación. Cambiarla exige un commit que lo justifique.

**Inventario `PHASE25_DESIGN_RULES`** (en `attribution.py`; `ALL_DESIGN_RULES` no cambia):

| Regla | `name` | `purpose` (capacidad que se diseñó para producir) | `ablation` |
| :--- | :--- | :--- | :--- |
| `R24` | ADN compacto y expresión condicional | Rasgos codificados en codones de 32 bits, expresados según el contexto, con costo cuadrático sólo sobre lo expresado. Sesgo declarado: abarata la complejidad latente. | `(("enable_compact_dna", False),)` |
| `R25` | Roles epigenéticos intra-holón | Especializar hojas con el mismo ADN en castas según su posición y su conocimiento en el holón. La especialización que produzca es programada. | `(("enable_epigenetic_roles", False),)` |
| `R26` | Conjugación de plásmidos | Transferir codones entre vecinos en vida. | `(("enable_plasmid_hgt", False),)` |
| `R27` | Inmunidad CRISPR | Purgar plásmidos con balance energético negativo y bloquear su reingreso. | `(("enable_crispr_immunity", False),)` |
| `R28` | Esporulación | Reducir el gasto en hambruna sin estímulos. Sesgo declarado: rescata poblaciones. | `(("enable_sporulation", False),)` |
| `R29` | Senescencia telomérica | Garantizar el recambio generacional limitando la vida. | `(("enable_telomere_senescence", False),)` |
| `R30` | Mutación SOS | Aumentar la variación bajo estrés y reducirla en abundancia. | `(("enable_sos_mutation", False),)` |
| `R31` | Trinquete simbiótico | Volver indisolubles los holones consolidados. Sesgo declarado: estabilidad por decreto. | `(("enable_symbiotic_ratchet", False),)` |

- `PHASE25_ALL_RULES = ALL_DESIGN_RULES + PHASE25_DESIGN_RULES`.
- `ablate()` busca las reglas en un índice que incluye las dos tuplas, sin modificar `ALL_DESIGN_RULES`.

**Configuraciones `PHASE25_PROTOCOL_CONFIGS`**, sobre `PHASE2_PROTOCOL_CONFIGS` (`resources_per_pattern = 20`):
- `"002c"`: `"002a"` con `enable_compact_dna`, `enable_plasmid_hgt`, `enable_crispr_immunity` y `enable_sos_mutation`.
- `"002d"`: `"002c"` con `enable_telomere_senescence=True` y `resources_per_pattern=40`.
- `"002e"`: `"002c"` con `enable_sporulation=True` y `resources_per_pattern=10`.
- `"003c"`: `"003a"` con `enable_compact_dna`, `enable_epigenetic_roles`, `enable_symbiotic_ratchet`, `enable_plasmid_hgt`, `enable_crispr_immunity` y `enable_sos_mutation`.

**Afirmaciones `PHASE25_CLAIMS`**, con el criterio de la Fase II (por construcción si el canal no es vacío y está contenido en $R_C$):

| Afirmación | Protocolo | Métrica (↑) | $R_C$ | Canal | Variante `isolated` | Clasificación esperable |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `C9` Adaptación con genoma regulado | `002c` | `evolved_accuracy` | `("R24",)` | `("R24",)` | `ablate(config, ["R24"])`: genoma plano, todo lo demás igual | Programada por construcción |
| `C10` Adaptación con recambio en abundancia | `002d` | `evolved_accuracy` | `("R29",)` | `("R29",)` | `ablate(config, ["R29"])` | Programada por construcción |
| `C11` Supervivencia activa en el desierto | `002e` | `final_active_population` | `("R28",)` | `("R28",)` | `ablate(config, ["R28"])` | Programada por construcción. Cuenta sólo hojas activas: una endospora no es población activa (decisión del 2026-10-20) |
| `C12` Superávit cooperativo con castas | `003c` | `holonic_composite_completions` | `("R25",)` | `("R25",)` | `ablate(config, ["R25"])` | Programada por construcción; potencia baja, porque en la Fase II los compuestos fueron 0 a 2 por corrida |

- **Variantes.** `isolated`, `null_content` y `rule_effects` (una por regla ablacionable de `PHASE25_ALL_RULES`, salvo las inactivas), como en D29.
- **Reglas inactivas (`PHASE25_INACTIVE_RULES`):**
  - `"002c"`: `R14`–`R19`, `R22`, `R23`, `R25`, `R28`, `R29` y `R31`;
  - `"002d"`: las de `"002c"` salvo `R29`;
  - `"002e"`: las de `"002c"` salvo `R28`;
  - `"003c"`: `R14`, `R18`, `R19`, `R28` y `R29`.
  - Un test las contrasta con las configuraciones, como en la Fase II.
- **E4.** Por la demografía de la calibración de la Fase II (el control nulo se extingue con 20 y con 10), E4 se declara **no interpretable** de antemano para `002c`, `002e` y `003c`. Para `002d` la calibración de la Fase II no basta, porque no tenía ADN ni senescencia y usó otras semillas. Por eso, E4 de C10 es interpretable **sólo si** la variante `null_content` termina con población viva en al menos 8 de las 10 semillas, según `ClaimEvaluation.demography`; si no, se informa como no interpretable. La condición se evalúa sobre la demografía, sin mirar la métrica de C10 (decisión del 2026-10-20).
- **Perfil.** `phase2`, con 2000 ticks y `PHASE2_SEEDS` (42–51). `run_phase25_attribution(seeds=PHASE2_SEEDS, claims=PHASE25_CLAIMS, jobs=1, configs=None)` devuelve `AttributionReport(profile="phase2", rules=PHASE25_ALL_RULES, ...)`.
- **Implementación de la atribución.** La maquinaria de la Fase II no reconoce los protocolos nuevos:
  - `is_phase2_claim` mira `PHASE2_PROTOCOL_CONFIGS`;
  - `_metric` y `_RUN_KIND` no conocen las métricas ni los protocolos;
  - E4 se deriva de la abundancia del entorno.
  - Por eso la atribución de la Fase II-B se declara explícitamente:
    - `is_phase25_claim(claim)` vale `claim.protocol in PHASE25_PROTOCOL_CONFIGS`, y esas afirmaciones usan el camino de variantes de la Fase II (`isolated` por su canal, criterio "por construcción" ampliado y `rule_effects` sobre `PHASE25_ALL_RULES`, salvo `PHASE25_INACTIVE_RULES`);
    - `PHASE25_CLAIM_CHANNELS` define los canales;
    - `PHASE25_METRIC_FIELDS` (precisión 9) mapea cada métrica a su campo;
    - `PHASE25_E4_INTERPRETABLE: dict[str, bool]` fija E4 por protocolo, sin derivarlo de la abundancia (`False` en `002c`, `002e` y `003c`). Para `002d` vale `True`, pero condicionado a la regla demográfica de arriba.
  - El camino de la Fase II no cambia: un test exige que los reportes de C5–C8 sean idénticos a los de antes del cambio.
- **Prueba de humo.** Antes de los runners, como en D29: registra si la corrida termina, la generación máxima y, salvo en `002e`, la población final, sin calcular ni mirar las métricas de las afirmaciones.
  - En `002e` **no** registra la población, porque la población activa final es la métrica de C11.
  - Si un protocolo resulta inviable, se reporta como resultado: no hay calibración sin una decisión nueva.
  - `002e` no se recalibra en ningún caso después de la prueba de humo (decisión del 2026-10-20).
- **Diagnóstico previo (decisión P5, tarea 0.1).** Antes de aprobar C10, se mide la demografía de la Fase II con `resources_per_pattern = 40`:
  - muertes por tick, edad al morir y nacimientos por tick;
  - con `PHASE2_PROTOCOL_CONFIGS_ORIGINAL["002a"]` y `["003a"]`, y las semillas de calibración 0 a 9;
  - sin calcular métricas de afirmaciones.
  - **Criterio, fijado antes de correrlo (decisión del 2026-10-20):** la hipótesis del "Tapón de Matusalén" se considera **confirmada** si, en al menos 8 de las 10 semillas de cada protocolo, más de la mitad de los agentes vivos en el tick 2000 nació antes del tick 1000. Si no, se considera **refutada**, y la tarea 0.2 decide si $R_{29}$ y C10 se mantienen.

### Precisiones (2026-10-20, surgidas de la redacción de los specs)
Cierran huecos de D34–D41 sin cambiar su intención. Las precisiones 9 (mapeo de métricas) y 13 (dependencia de P5) forman parte de cómo se mide el pre-registro (D42), y se aprueban con él en la tarea 0.2. Las demás no lo tocan.
1. **Fundadores (D34.1).** `MicroAgent.__init__` fija `base_config = config`.
   - Con `config.enable_compact_dna=True`, asigna `dna = founder_dna(config)` y `phenotype = transcribe_phenotype(dna, EpigeneticContext(0, EpigeneticRole.NONE, config.initial_energy / config.reproduction_threshold), config)`, cuyo `genome` es `genome_from_config(config)` (D32).
   - Si no, asigna `dna = None` y `phenotype = phenotype_from_genome(genome_from_config(config), config)`.
   - `from_lineage` recibe además `dna` y `base_config`. Con `dna`, `genome` puede ser `None`: se toma el genoma expresado en el contexto de nacimiento, y si se da, debe coincidir con él. Sin `dna`, `genome` es obligatorio.
2. **Actualización del fenotipo en `express` (D34.2).** `express` reemplaza **siempre** `phenotype` por el fenotipo transcripto, aunque sólo cambien `lifespan`, `spore_threshold` o `expressed_codons`. El reemplazo de `_genome` y de `_config` y el `resize` de la memoria ocurren sólo si cambió `genome`.
3. **Expresión al nacer (D34.6).** La hace `create_offspring`, en el agente, no el motor. El motor sólo lee los radios del hijo para `spawn_agent_near`.
4. **Ensayos CRISPR (D37).**
   - **Dónde viven.** En `MicroAgent`, con `plasmid_trials -> dict[int, tuple[int, float, float]]` (una copia, ordenada por codón; tick de apertura, energía de ingreso y energía cedida), `open_plasmid_trial(codon, tick)` y `close_plasmid_trial(codon)`. `create_offspring` suma la energía del hijo a la cedida de todos los ensayos abiertos.
   - **Apertura.** `open_plasmid_trial` no reabre un ensayo ya abierto para ese codón: conserva el original.
   - **Cierre.** Un ensayo sólo se cierra al vencer. Si al vencer el plásmido ya no está, se cierra sin purga.
   - **Herencia.** Los ensayos no se heredan (D35).
5. **Conteo de eventos de conjugación (D37 y D41).**
   - `hgt_transfers` cuenta las transferencias que **cambiaron** el ADN del receptor.
   - `crispr_rejections` cuenta las bloqueadas por `crispr_memory`.
   - Un codón ya presente no cuenta en ninguno de los dos.
   - `crispr_purges` cuenta las purgas del paso de ensayo.
6. **Endospora dentro de un holón (D38).** Sigue pagando su alícuota del costo de coordinación ($R_{23}$), que se cobra en el paso (ii) de la Fase 5 y es distinto del costo basal. Lo que reemplaza la endospora es el costo basal, el del ADN, el de movimiento y el de mensajes.
7. **Registro del estrés (D39).** "Siempre" quiere decir "aunque `enable_sos_mutation=False`". El registro ocurre en el paso de metabolismo, así que sólo existe con `enable_evolution=True`.
8. **Descuento del trinquete (D40).** El costo de coordinación se cobra sólo a los holones raíz, como en la Fase II. El descuento se aplica si la **raíz** está soldada: un sub-holón soldado dentro de una raíz sin soldar no da descuento.
9. **Mapeo de métrica a campo (D41 y D42).** `PHASE25_METRIC_FIELDS = {"evolved_accuracy": "final_accuracy", "final_active_population": "final_active_agents", "holonic_composite_completions": "composite_completions"}`, como `_PHASE2_METRIC_FIELDS`.
10. **`genetic_history` (D41).** Se registra en **cada** tick, con cualquier combinación de banderas, como `evolutionary_history`.
    - Los promedios son sobre las hojas vivas al final del tick.
    - `mean_age` es `float` y `max_age` es `int`.
    - Con la población vacía, los promedios valen `0.0` y los máximos `0`.
    - Sin ADN, las medias genéticas valen `0.0`.
    - La edad se define siempre, por `birth_tick`.
11. **Roles (D36).** Una raíz sin entrada en `_role_leaf_sets` cuenta como cambiada. En la impronta, cada hoja hija recibe el rol de la hoja progenitora de la que nació, según la correspondencia `offspring[progenitora.agent_id]` de `reproduce_holon`.
12. **Plásmido mutado (D35, paso 2).** Después de la mutación puntual de los plásmidos, se descartan, en orden, los codones repetidos (se queda el primero) y los que estén en `crispr_memory`.
13. **Dependencia de P5.** C10 y $R_{29}$ quedan sujetos al diagnóstico de la tarea 0.1. Si se descartan, la tarea 0.2 retoca D42 y los specs de `emergence-attribution` y `experimental-suite` (`002d`).
14. **Endosporas y reproducción (D38).**
    - Un holón con alguna hoja en endospora no se reproduce por $R_{17}$.
    - En la reproducción neutral, los donantes de genoma son los agentes vivos que no están en endospora al empezar la fase de reproducción.
    - Una endospora se expresa igual en la Fase 0. Es inocuo, porque paga un costo fijo, y evita un caso especial.

---

## Reformulación del 2026-10-20 (D43–D56)

### Decisión 43: Principio, Alcance y Estado de las Decisiones Anteriores
1. **Principio.** *La regla da la capacidad y el ADN decide su uso.* Cada regla nueva o reformulada pone a disposición del agente una capacidad física o sensorial; ningún codón del ADN fundador la usa, salvo para reproducir la conducta de la Fase II (D46.5). Lo que la población haga con esa capacidad lo produce la selección, y se mide contra la reproducción neutral (precisión 44).
2. **Lo que se conserva sin cambios:** D30–D35 (implementadas en la etapa A), D37 ($R_{26}$ y $R_{27}$) y D39 ($R_{29}$ y $R_{30}$).
3. **Lo que se reinterpreta o sustituye:**
   - D36 ($R_{25}$): misma asignación, reinterpretada como señal (D50.1);
   - D38 ($R_{28}$): la entrada en endospora pasa a ser una conducta (D50.2);
   - D40 ($R_{31}$): el sello depende de un rasgo expresado (D50.3);
   - D41: sustituida por D44, D53 y D56;
   - D42: sustituida por el borrador D56. C9–C12 se retiran sin medir.
4. **Lo que se agrega:** el motor por sistemas (D44), el puerto de política (D45), la conducta en el ADN ($R_{32}$, D46), la percepción social y las acciones nuevas (D47), la ecología ($R_{33}$–$R_{35}$, D48), las interacciones ($R_{36}$, $R_{37}$, D49), la recombinación ($R_{38}$, D51), la configuración (D52), la telemetría de evolución abierta (D53), el rendimiento (D54), la compuerta de viabilidad (D55) y el pre-registro (D56).
5. **Compatibilidad.** Con todas las banderas nuevas en su valor por defecto, las Fases I y II y la etapa A de la Fase II-B se comportan bit a bit como antes: los hashes dorados de la Fase I, las huellas de la Fase II y los tests de los bloques 1 a 5 no cambian, salvo los que la propia reformulación modifica de forma explícita (D46.7, D50.3 y D52.4). Ningún test de conducta de las Fases I y II cambia. La única excepción es el test de firmas públicas canónicas de la Fase I (`test_firmas_publicas_canonicas`), que se amplía con los parámetros opcionales `policy=None` y `social=None` (precisión 22); es un cambio aditivo de firma, sin cambio de conducta.
6. **Generadores.** La reformulación no agrega generadores. Las extracciones nuevas usan el generador principal (la conducta en la Fase 3 y la ubicación de recursos en el entorno) o `evo_rng` (la recombinación al nacer), siempre detrás de su bandera.

### Decisión 44: Motor por Sistemas y Observadores
1. **Sistemas.** `src/ide/simulation/pipeline.py` define:
   ```python
   class EngineSystem(Protocol):
       name: str
       def run(self, engine: "SimulationEngine", frame: "TickFrame") -> None: ...

   class TickObserver(Protocol):
       def on_decisions(self, engine: "SimulationEngine", frame: "TickFrame") -> None: ...
       def on_tick_end(self, engine: "SimulationEngine", frame: "TickFrame") -> None: ...

   @dataclass
   class TickFrame:  # estado mutable de un tick; no es una entidad de dominio
       tick: int
       order: list[int]
       reach: dict[int, list[int]]
       observations: dict[int, Observation]
       social: dict[int, SocialPerception]
       emitted: list[Message]
       responses: list[Message]
       actions: dict[int, AgentAction]
       composite_intents: dict[int, Pattern]
       composite_contexts: dict[int, tuple[bool, list[int], CompositeAgent | None]]
       moved: set[int]
       attacks: dict[int, int]       # intentos de ataque por agente, para el costo (D49)
       surplus: set[int]
       births: int
       deaths: int
       messages_sent: int
       events: Counter[str]          # eventos ecológicos y genéticos del tick (D53)
   ```
   - `build_systems(config) -> tuple[EngineSystem, ...]` arma la lista ordenada de D53. Un mecanismo que vive en su propio sistema no aparece en la lista con su bandera apagada.
   - `SimulationEngine.step()` crea el `TickFrame`, ejecuta los sistemas en orden, llama a `on_decisions` de cada observador después del sistema de decisión y a `on_tick_end` al final, e incrementa `next_tick`.
2. **Observadores.** La telemetría sale del bucle:
   - `TickMetricsObserver` produce `TickMetrics` (M1–M7) y juzga M2 en `on_decisions`, con el oráculo `get_reachable_true_values` consultado **antes** de ejecutar las acciones, como hoy;
   - `EvolutionaryMetricsObserver`, `GeneticMetricsObserver` y `EcologyMetricsObserver` producen sus historiales (D53).
   - La API pública del motor no cambia: `history`, `evolutionary_history`, `agents`, `root_nodes`, `step()`, `run()`, `snapshot()` y las perturbaciones.
3. **Acceso al agente.** Los sistemas no llaman a `agent.memory` directamente salvo en los puntos que hoy lo hacen ($R_{18}$, $R_{19}$, el superávit de conocimiento y las perturbaciones). La lista se fija en un test AST sobre `pipeline.py` y `engine.py`, para que no crezca.
4. **Aceptación.** El refactor no cambia ningún comportamiento:
   - los hashes SHA-256 dorados de `tests/test_performance_equivalence.py` son idénticos;
   - las huellas de la Fase II y los historiales de `002a` y `003a` con y sin ADN (bloque 5) son idénticos;
   - el consumo de cada generador sigue la misma secuencia;
   - el benchmark no empeora más de un 10 % en ticks por segundo (D54).

### Decisión 45: Puerto de Política y Política Escrita a Mano
1. **Puerto.** `src/ide/agent/policy.py` define:
   ```python
   class PolicyPort(Protocol):
       def decide(self, agent: "MicroAgent", obs: Observation, social: SocialPerception | None,
                  tick: int, rng: np.random.Generator) -> AgentAction: ...
   ```
2. **`HandwrittenPolicy`.** Es la lógica actual de `MicroAgent.decide_action`, movida sin cambios: consumir el recurso alcanzable de mayor $\hat{v} \cdot c$, explorar con probabilidad $\epsilon$, navegar hacia un objetivo conocido o caminar al azar, con los mismos desempates y las mismas extracciones de `rng`. Ignora `social`.
3. **`MicroAgent`.** Recibe `policy: PolicyPort | None` en el constructor (por defecto `HandwrittenPolicy()`), lo propaga a sus descendientes en `create_offspring`, y `decide_action(obs, tick, rng, social=None)` delega en él. La firma vieja de `decide_action` sigue siendo válida.
4. **Selección.** El motor construye los fundadores con `GeneticPolicy()` si `enable_compact_dna` y `enable_genetic_policy` están activas, y con `HandwrittenPolicy()` en otro caso.
5. **Aislamiento.** `policy.py` vive en `src/ide/agent/` y cumple sus invariantes: no importa `environments`, `simulation` ni `experiments`, y no construye `Message`.

### Decisión 46: Conducta Codificada en el ADN (R32)
1. **Conductas.** `Behavior` es un `Enum` en `domain/types.py`, con un destino de codón por conducta. El orden de la tabla es el orden de desempate.

   | Destino | `Behavior` | Acción | Factible si |
   | :---: | :--- | :--- | :--- |
   | `0x40` | `CONSUME` | `INTERACT` sobre el recurso alcanzable conocido y benéfico de mayor $\hat{v} \cdot c$ (desempate por menor `resource_id`) | existe alguno |
   | `0x41` | `EXPLORE` | `INTERACT` sobre el recurso alcanzable desconocido de menor `resource_id` | existe alguno **y** `rng.random() < epsilon_explore` expresado; la extracción ocurre sólo si existe alguno |
   | `0x42` | `NAVIGATE` | `MOVE` con el `recommended_move` del objetivo conocido benéfico no alcanzable más cercano (desempate por `resource_id`) | `enable_navigation` y existe alguno |
   | `0x43` | `WANDER` | `MOVE` a `available_moves[int(rng.integers(len(available_moves)))]` | hay movimientos disponibles |
   | `0x44` | `SHARE` | `SHARE` sobre `social.weakest_adjacent` | $R_{36}$ activa, `social.adjacent` no vacío y energía propia $> 0$ |
   | `0x45` | `ATTACK` | `ATTACK` sobre `social.weakest_adjacent` | $R_{37}$ activa y `social.weaker_adjacent` |
   | `0x46` | `FLEE` | `MOVE` con `social.flee_move` | `social.flee_move is not None` |
   | `0x47` | `SPORULATE` | `SPORULATE` | $R_{28}$ activa y `energy <= phenotype.spore_threshold` |

   Las definiciones de "conocido", "benéfico" y "alcanzable" son las de `HandwrittenPolicy`, con `get_effective_belief`.
2. **Promotores sensoriales.** Los promotores `0x20`–`0x27` leen un `SensorySignals` (D47) del tick:

   | Promotor | Nombre | Activo si |
   | :---: | :--- | :--- |
   | `0x20` | `SENSE_KNOWN_GOOD` | algún recurso visible es conocido y benéfico |
   | `0x21` | `SENSE_UNKNOWN` | algún recurso visible es desconocido |
   | `0x22` | `SENSE_NO_RESOURCE` | no hay recursos visibles |
   | `0x23` | `SENSE_NEIGHBOR_ADJACENT` | `social.adjacent` no está vacío |
   | `0x24` | `SENSE_WEAKER_ADJACENT` | `social.weaker_adjacent` |
   | `0x25` | `SENSE_STRONGER_NEAR` | `social.flee_move is not None` |
   | `0x26` | `SENSE_CROWDED` | `social.crowded` |
   | `0x27` | `SENSE_CARCASS` | `social.carcass_visible` |

   En la transcripción del fenotipo de la Fase 0 (D33) los promotores sensoriales están **inactivos**: los rasgos no dependen de la percepción inmediata. Sólo actúan en la evaluación de impulsos.
3. **Evaluación de impulsos.** `evaluate_drives(dna, context, signals, config) -> tuple[float, ...]`, en `dna.py`, es pura y devuelve un impulso por conducta, en el orden de la tabla:
   - repite las dos pasadas de D33, con la activación de pasada 1 extendida a los promotores sensoriales;
   - para cada destino de conducta $B$, con $A_B$ sus codones activos de modo distinto de 3: $S_B$ la suma de $\delta$ de modo 0, $\rho_B$ el producto de $(1 - |\delta|)$ de modo 1 y $\mu_B$ el producto de $(1 + \delta)$ de modo 2;
   - el impulso es $d_B = \mu_B \cdot \rho_B \cdot S_B$, sin cotas, y vale 0 con $A_B$ vacío;
   - acumula en el orden de recorrido, como D33.
   - **Cambio respecto de D32:** los destinos `0x40`–`0x47` dejan de ser reservados. En la transcripción del fenotipo siguen siendo inertes y no cuentan en `expressed_codons`.
4. **Decisión.** `GeneticPolicy.decide`:
   - calcula `signals` y los impulsos;
   - recorre las conductas con $d_B > 0$ en orden de $(-d_B, \text{posición en la tabla})$;
   - devuelve la acción de la primera conducta factible;
   - si ninguna lo es, devuelve `IDLE`.
   - Una endospora no decide (D38).
5. **Fundador conductual neutro.** Con `enable_genetic_policy=True`, `founder_dna(config)` agrega al cromosoma de D32 cuatro codones `ALWAYS_BASAL` aditivos, en este orden: `encode_codon(0x00, 0x40, 0, 0, 127)`, `encode_codon(0x00, 0x41, 0, 0, 96)`, `encode_codon(0x00, 0x42, 0, 0, 64)` y `encode_codon(0x00, 0x43, 0, 0, 32)`. Los impulsos fundadores son 0.9921875, 0.75, 0.5 y 0.25, y el orden de prueba reproduce exactamente `HandwrittenPolicy`, incluidas las extracciones de `rng`.
   - **Test de aceptación:** con el ADN fundador, sin mutación y con `dna_codon_cost = 0.0`, las corridas de `002a` y `003a` con `enable_genetic_policy=True` producen historiales idénticos a los de `enable_genetic_policy=False`. El costo por codón se anula porque el fundador conductual tiene 13 codones y no 9: con el costo por defecto pagaría más energía por tick, y los historiales divergirían por el metabolismo, no por la conducta.
   - `founder_dna_length(config)` vale 13 con la política genética y 9 sin ella. `FOUNDER_DNA_LENGTH = 9` se conserva para la validación de D31.
6. **Propensión a comunicar.** Con la política genética, el rasgo expresado `comm_propensity` (destino `0x0C`, D46.7) decide si el agente comunica en el tick:
   - con `comm_propensity >= 0.5`, emite y responde consultas como en la Fase I;
   - con `comm_propensity < 0.5`, no emite ni responde, pero sigue recibiendo y asimilando testimonios.
   - La puerta vive en `protocol.py` (`agent.communicates`), sin consumir generadores. Con la política escrita a mano, `communicates` vale siempre `True`.
7. **Rasgos nuevos.** La transcripción del fenotipo (D33) agrega tres destinos de rasgo real:

   | Destino | Rasgo | Base $b$ | Escala $k$ | Cotas |
   | :---: | :--- | :--- | ---: | :--- |
   | `0x0A` | compromiso simbiótico ($R_{31}$) | `symbiotic_commitment_base` | 0.60 | $[0, 1]$ |
   | `0x0B` | propensión a recombinar ($R_{38}$) | `recombination_base` | 0.60 | $[0, 1]$ |
   | `0x0C` | propensión a comunicar ($R_{32}$) | `comm_propensity_base` | 0.60 | $[0, 1]$ |

   La escala 0.60 (y no 0.50) hace que un solo codón aditivo con `payload >= 107` ($\delta \approx 0.836$) lleve un rasgo de base 0 al umbral de 0.5: con 0.50, el máximo de un codón es $0.5 \cdot 0.9921875 < 0.5$, y comunicar, soldarse o recombinar exigiría dos mutaciones coordinadas, cada una neutral por separado (revisión cruzada, hallazgo 7).

   `ExpressedPhenotype` agrega `symbiotic_commitment`, `recombination_propensity` y `comm_propensity`, con valores por defecto `0.0`, `0.0` y `1.0` (las bases por defecto de D52.1; el agente siempre los recibe transcriptos desde su configuración), y `expressed_codons` pasa a contar los destinos `0x00`–`0x08` y `0x0A`–`0x0C`. El ADN fundador no tiene codones sobre ellos: expresa las bases. `phenotype_from_genome` también devuelve las bases.
8. **Caché.** `MicroAgent` puede memoizar los impulsos por `(clave de contexto de D34.2, signals)`, invalidando al cambiar el ADN. Un test exige que coincida con la evaluación directa.

### Decisión 47: Percepción Social, Señales y Acciones Nuevas
1. **Tipos nuevos** en `domain/types.py`, todos `@dataclass(frozen=True)`:
   ```python
   class Behavior(Enum): CONSUME, EXPLORE, NAVIGATE, WANDER, SHARE, ATTACK, FLEE, SPORULATE

   @dataclass(frozen=True)
   class VisibleAgent:
       agent_id: int
       distance: int               # Chebyshev toroidal
       recommended_move: Any       # hacia el agente; None si distance == 0
       flee_move: Any              # el movimiento de Moore que maximiza la distancia; desempate por orden de MOORE_MOVES

   @dataclass(frozen=True)
   class SocialPerception:
       adjacent: tuple[int, ...] = ()            # agentes activos a distancia <= 1, ascendentes
       weakest_adjacent: int | None = None       # de `adjacent`, el de menor (energía, agent_id)
       weaker_adjacent: bool = False             # su energía es menor que la propia
       flee_move: Any = None                     # huida del más cercano con más energía que la propia
       crowded: bool = False                     # agentes activos visibles >= crowding_threshold
       carcass_visible: bool = False             # algún recurso visible es un cadáver (R35)

   @dataclass(frozen=True)
   class SensorySignals:
       known_good: bool; unknown: bool; no_resource: bool; neighbor_adjacent: bool
       weaker_adjacent: bool; stronger_near: bool; crowded: bool; carcass: bool
   ```
   `ActionType` agrega `SHARE`, `ATTACK` y `SPORULATE`. `AgentAction.target` es el `agent_id` en `SHARE` y `ATTACK`, y `None` en `SPORULATE`.
2. **Puerto de entorno.** `EcologicalEnvironmentPort(EvolutionaryEnvironmentPort)` agrega:
   - `get_visible_agents(agent_id) -> tuple[VisibleAgent, ...]`: los agentes dentro del radio de percepción del observador, ordenados por `(distance, agent_id)`, sin él mismo;
   - `deposit_carcass(agent_id, value, tick) -> None` (D48.3);
   - `get_resource_count() -> int`, para la telemetría.
   - Los agentes siguen sin conocer coordenadas: sólo reciben distancias y movimientos.
3. **Construcción de `SocialPerception`.** La hace el motor en la Fase 1, con `enable_genetic_policy` activa, sobre la instantánea de energías al empezar el tick (percepción sincrónica):
   - "activo" excluye a las endosporas;
   - `flee_move` es el de la entrada de `get_visible_agents` del agente activo más cercano con energía estrictamente mayor que la propia, con desempate por `(distance, agent_id)`;
   - `carcass_visible` mira si algún `VisibleResource` tiene el patrón de cadáver de D48.3.
   - Sin la política genética, el motor no la construye y pasa `None`.
4. **Construcción de `SensorySignals`.** La hace `GeneticPolicy` a partir de la observación, de sus creencias efectivas y de `social`.

### Decisión 48: Ecología del Entorno (R33, R34, R35)
1. **Recursos agotables ($R_{33}$, `enable_resource_depletion`).**
   - Un recurso elemental consumido no reaparece en el tick siguiente, sino `resource_regen_delay` ticks después: se agenda con `due = tick + delay`.
   - `step_dynamics(tick)` repone, en orden de `(due, orden de consumo)`, los agendados con `due <= tick`, cada uno en una celda sorteada con el generador del entorno, como hoy.
   - Con la regla apagada, la reposición es la de la Fase II, sin cambios.
   - Los recursos compuestos no cambian.
2. **Heterogeneidad ($R_{34}$, `enable_heterogeneity`).**
   - **Regiones.** La grilla se divide en `num_regions` franjas verticales de ancho `grid_width // num_regions` (la última absorbe el resto). El patrón elemental de índice $i$ tiene como región propia $i \bmod$ `num_regions`. Sus recursos, al inicio y al reponerse, se ubican en una celda sorteada dentro de su región: `x = x0 + int(rng.integers(ancho))` y `y = int(rng.integers(grid_height))`.
   - **Estaciones.** Con `season_length > 0`, la estación es `(tick // season_length) % 2`; en la estación 1 (invierno), el retardo de $R_{33}$ se multiplica por `winter_regen_factor` y se redondea con `floor(x + 0.5)`. Sin $R_{33}$, las estaciones son inertes.
3. **Cadáveres ($R_{35}$, `enable_carcasses`, sólo con `enable_evolution`).**
   - Al morir un agente, por hambre o por depredación, el motor llama a `env.deposit_carcass(agent_id, carcass_value, tick)` **antes** de quitarlo del entorno. El entorno coloca en su celda un recurso de patrón `CARCASS_PATTERN = Pattern((("id", "carcass"),))` y valor `carcass_value`.
   - El cadáver se consume con `INTERACT`, como cualquier recurso; da `energy_gain_scale * carcass_value` y se aprende por experiencia directa.
   - No se repone. Se retira solo `carcass_lifetime` ticks después de depositado, en `step_dynamics`.
   - `CARCASS_PATTERN` no forma parte de `get_world_patterns()`: las métricas de cobertura y la exactitud de las Fases I y II no lo ven. Sí lo ve el oráculo de M2, porque es un recurso alcanzable.

### Decisión 49: Interacciones entre Agentes (R36, R37)
Se ejecutan en la Fase 4, en el orden de la permutación del tick, junto con las demás acciones. Las aplica el motor, porque el entorno no conoce la energía.
1. **Transferencia ($R_{36}$, `enable_energy_transfer`).** `SHARE` sobre `target`:
   - si el objetivo sigue vivo y no es endospora, `amount = share_fraction * energía_del_donante`;
   - el donante pierde `amount` y el receptor gana `share_efficiency * amount`;
   - si no, no ocurre nada.
2. **Depredación ($R_{37}$, `enable_predation`).** `ATTACK` sobre `target`:
   - el intento se cuenta en `frame.attacks` y cuesta `attack_cost` en el metabolismo, haya éxito o no;
   - tiene éxito si el objetivo sigue vivo, no es endospora y la energía del atacante es estrictamente mayor que la del objetivo **en el momento de ejecutarse**;
   - con éxito, `stolen = min(attack_power, max(0, energía_del_objetivo))`: el objetivo pierde `stolen` y el atacante gana `predation_efficiency * stolen`.
   - Un objetivo que queda con energía $\le 0$ muere en el paso de muerte de la Fase 5, y con $R_{35}$ deja un cadáver.
3. **`SPORULATE`.** Pone al agente en endospora al ejecutarse (D50.2).
4. **M2.** M2 sigue juzgando las decisiones con recursos elementales alcanzables, como hoy, cualquiera sea la conducta elegida (precisión 21).
5. **Cotas.** `share_efficiency <= 1` y `predation_efficiency <= 1`: ninguna interacción crea energía.

### Decisión 50: Reformulación de R25, R28 y R31
1. **$R_{25}$, señal posicional.** La asignación de D36 no cambia. Su propósito pasa a ser "proveer una señal de posición y de conocimiento dentro del holón". Como el ADN fundador no tiene codones con promotores de rol, cualquier diferencia de expresión entre roles la construye la selección.
2. **$R_{28}$, endospora como conducta.**
   - Se entra en endospora sólo con la conducta `SPORULATE` (D46), que exige `enable_genetic_policy`, `enable_evolution` y `enable_sporulation`, y `energy <= phenotype.spore_threshold`.
   - La regla de umbral de D38 (entrada automática en la Fase 5) se elimina.
   - La germinación, la física de la endospora y su costo de D38 y de las precisiones 6 y 14 se mantienen.
   - Sin la política genética, $R_{28}$ es inerte.
3. **$R_{31}$, compromiso simbiótico.**
   - En el paso de coordinación de la Fase 5, un holón raíz no soldado queda soldado si la media del `symbiotic_commitment` expresado de sus hojas es $\ge 0.5$. El sello es permanente, como en D40.
   - Las condiciones (a) y (b) de D40 se eliminan, y con ellas `lock_composite_threshold`.
   - Los efectos (sin `SPLIT` y con descuento de coordinación), la poda y la fusión de D40 y de la precisión 8 se mantienen.
   - Con `symbiotic_commitment_base = 0.0`, ningún holón fundador se suelda: el compromiso tiene que evolucionar.

### Decisión 51: Recombinación (R38)
Con `enable_compact_dna`, `enable_evolution` y `enable_recombination` activas, en la reproducción individual ($R_{12}$, no en $R_{17}$):
1. **Parejas.** El progenitor busca pareja si su `recombination_propensity` expresada es $\ge 0.5$. Las candidatas son, ordenadas por `agent_id`, las hojas vivas, no endosporas, con ADN, a distancia $\le 1$ y con `recombination_propensity >= 0.5`. Sin candidatas, la reproducción es asexual.
2. **Sorteo y cruce.** Con candidatas, con `evo_rng` y en este orden:
   - `pareja = candidatas[int(evo_rng.integers(len(candidatas)))]`;
   - `a = int(evo_rng.integers(1, len(cromosoma_progenitor) + 1))`;
   - `b = int(evo_rng.integers(0, len(cromosoma_pareja)))`;
   - el cromosoma recombinado es `progenitor[:a] + pareja[b:]`, truncado a `dna_max_length`; si queda más corto que `dna_min_length`, se usa el del progenitor.
   - Los plásmidos y `crispr_memory` son los del progenitor.
3. **Mutación.** El ADN recombinado se muta después con `mutate_dna` (D35), como cualquier hijo.
4. **Energía.** La pareja no cede energía: la recombinación es un intercambio de material genético, no de recursos.
5. **`recombine_dna(parent, partner, a, b, config) -> CompactDNA`** es una función pura en `dna.py`; el sorteo lo hace el motor.

### Decisión 52: Configuración de la Reformulación
1. **Campos nuevos** al final de `SimulationConfig`:
   ```python
       # --- R32: conducta en el ADN ---
       enable_genetic_policy: bool = False
       comm_propensity_base: float = 1.0
       crowding_threshold: int = 3
       # --- R31 reformulada ---
       symbiotic_commitment_base: float = 0.0
       # --- R33 y R34 ---
       enable_resource_depletion: bool = False
       resource_regen_delay: int = 20
       enable_heterogeneity: bool = False
       num_regions: int = 3
       season_length: int = 0               # 0 = sin estaciones
       winter_regen_factor: float = 3.0
       # --- R35 ---
       enable_carcasses: bool = False
       carcass_value: float = 0.6
       carcass_lifetime: int = 50
       # --- R36 y R37 ---
       enable_energy_transfer: bool = False
       share_fraction: float = 0.25
       share_efficiency: float = 0.9
       enable_predation: bool = False
       attack_power: float = 0.5
       predation_efficiency: float = 0.6
       attack_cost: float = 0.01
       # --- R38 ---
       enable_recombination: bool = False
       recombination_base: float = 0.0
       # --- Telemetría de evolución abierta (D53) ---
       activity_threshold: int = 500
   ```
2. **Validación siempre activa:**
   - en $[0, 1]$: `comm_propensity_base`, `symbiotic_commitment_base`, `recombination_base`, `share_fraction`, `share_efficiency`, `predation_efficiency`;
   - en $(0, 1]$: `carcass_value`;
   - no negativos: `attack_power`, `attack_cost`;
   - $\ge 1$: `crowding_threshold`, `resource_regen_delay`, `num_regions`, `carcass_lifetime`, `activity_threshold`, `winter_regen_factor`;
   - $\ge 0$: `season_length`;
   - `num_regions <= grid_width`.
3. **Dependencias inertes** (D30.3): $R_{31}$, $R_{32}$ y $R_{38}$ exigen `enable_compact_dna`; $R_{28}$, $R_{36}$ y $R_{37}$ exigen $R_{32}$, porque sólo actúan como conductas; $R_{35}$ y $R_{38}$ exigen `enable_evolution`; las estaciones de $R_{34}$ exigen $R_{33}$. Con el requisito apagado, la bandera es inerte y no lanza error.
4. **Campo eliminado.** `lock_composite_threshold` se elimina (D50.3); sus tests de validación se retiran en el bloque que implementa D50.
5. **Valores por defecto propuestos.** Se aprueban con el pre-registro en la tarea 0.5. La compuerta de viabilidad (D55) sólo puede cambiar `resources_per_pattern` y `resource_regen_delay`.

### Decisión 53: Orden del Tick y Telemetría de Evolución Abierta
1. **Orden de los sistemas** (`build_systems`):
   - **Fase 0:** expresión del fenotipo (D34.4).
   - **Fase 1:** percepción, germinación (D38), percepción social (D47.3), emisión con la puerta de comunicación (D46.6), estigmergia y vista del holón (tiempo 1).
   - **Fase 2:** intercambio social en dos pasadas y vista del holón (tiempo 2).
   - **Fase 3:** decisión con la política de cada agente; contexto de los compuestos. Observadores: `on_decisions`.
   - **Fase 4:** ejecución en el orden de la permutación (movimientos, interacciones con recursos, `SHARE`, `ATTACK` y `SPORULATE`), aprendizaje directo, energía y estigmergia.
   - **Fase 5:** (i) `decay_memory`; (ii) coordinación, sello de $R_{31}$, `SPLIT` y `BOND`; (iii) metabolismo, con ADN, senescencia, endospora y el costo de los ataques; (iv) muerte, cadáveres ($R_{35}$) y registro del estrés; (v) reproducción, con SOS, recombinación, ADN e impronta; (vi) conjugación y ensayo CRISPR; (vii) $R_{18}$ y roles; (viii) `env.step_dynamics`, con la reposición de $R_{33}$, $R_{34}$ y el retiro de cadáveres. Observadores: `on_tick_end`.
   - Sin las banderas nuevas, el orden se reduce exactamente al de la Fase II.
2. **`GeneticTickMetrics`** (sustituye a la de D41; se registra en cada tick en `engine.genetic_history`). Conserva todos los campos de D41 y de la precisión 10, incluido `locked_holons`, y agrega:
   - `distinct_genotypes`: cantidad de cromosomas distintos entre las hojas vivas;
   - `mean_functional_codons`: media de codones con destino de rasgo (`0x00`–`0x08`, `0x0A`–`0x0C`) o de conducta (`0x40`–`0x47`) y modo distinto de 3, cualquiera sea su promotor;
   - `regulated_expression_fraction`: definida en la precisión 42 (codones activos con promotor condicional en el protocolo);
   - `policy_divergence`: entre las decisiones del tick con la política genética, la fracción en que la primera conducta factible según el ADN del agente difiere de la del ADN fundador, evaluadas sobre las mismas señales y factibilidades, con `EXPLORE` tomada como factible si hay recursos desconocidos alcanzables, sin extraer de `rng`;
   - `communicating_fraction`: fracción de hojas vivas no endosporas con `comm_propensity >= 0.5`;
   - `new_activity` y `cumulative_new_activity` (actividad evolutiva de Bedau–Packard): para cada codón distinto $c$, la actividad $a_c(t) = \sum_{s \le t}$ (hojas vivas que portan $c$ en el cromosoma o en los plásmidos en el tick $s$). `new_activity` cuenta los codones cuya actividad cruzó `activity_threshold` en el tick, y `cumulative_new_activity` es su suma acumulada.
   - al final y en este orden, `mean_active_functional_codons` (precisión 42), `cumulative_births` y `new_activity_per_birth` (precisión 43).
   - Los valores de la población vacía siguen la precisión 10.
3. **`EcologyTickMetrics`** (nueva, en `engine.ecology_history`, registrada en cada tick): `tick`, `resources_available`, `shares`, `attacks`, `successful_attacks`, `predation_deaths` (muertes del tick de agentes atacados con éxito en ese tick), `starvation_deaths`, `carcasses_deposited`, `carcasses_eaten`, `sporulations`, `recombinations`, `share_rate` (`shares` dividido por las decisiones del tick; 0.0 sin decisiones) y `behavior_counts` (tupla con la cantidad de decisiones de cada `Behavior` en el tick, en el orden de la tabla de D46).
4. **Sin efecto en las métricas anteriores.** `TickMetrics` y `EvolutionaryTickMetrics` no cambian.

### Decisión 54: Rendimiento
1. **Línea base.** Antes del refactor (bloque 6) se registra el benchmark (`python -m ide.experiments.benchmark` y `--compact-dna`).
2. **Criterio del refactor.** Después de los bloques 6 y 7, el benchmark no puede empeorar más de un 10 %.
3. **Perfil largo.** Antes de la compuerta de viabilidad se mide el costo de un tick con todas las reglas de D56 activas. Si una corrida del perfil `phase25` supera los 5 minutos, se puede optimizar el bucle con la regla de `CLAUDE.md`: medición previa e historiales idénticos entre la versión rápida y la actual.

### Decisión 55: Compuerta de Viabilidad (antes de cualquier afirmación)
1. **Qué mide.** Sólo demografía: si la corrida termina con población viva y la generación máxima. No calcula ninguna métrica de afirmación.
2. **Semillas.** `PHASE25_VIABILITY_SEEDS = tuple(range(0, 10))`, disjuntas de `PHASE25_SEEDS`.
3. **Criterio.** Cada corrida dura el perfil `phase25` (5000 ticks). Una corrida es viable si termina con al menos una hoja viva **que no esté en endospora** y `max_generation >= 20`. Una configuración es viable si, para **cada** protocolo de D56 y **cada** una de sus condiciones `full`, `drift` y `no_predation`, al menos 8 de las 10 semillas son viables. La condición `null_content` se corre y se registra, pero **no** decide la viabilidad: sólo decide si E4 es interpretable (D56).
4. **Grilla declarada**, en orden de preferencia (menos abundancia primero: menos recursos por patrón y, a igual cantidad, mayor retardo), sobre `(resources_per_pattern, resource_regen_delay)`: `(20, 20)`, `(20, 10)`, `(30, 20)`, `(30, 10)`, `(40, 40)` y `(40, 20)`. Se elige la **primera** viable, y se detiene al encontrarla.
5. **Sin viables.** Si ninguna lo es, se reporta como resultado y decide el responsable del proyecto. No se prueba nada fuera de la grilla sin una enmienda.
6. **Registro.** La salida completa va a `registros/` y a `docs/RESULTADOS.md` antes de la prueba de humo.

### Decisión 56: Pre-Registro de la Fase II-B Reformulada (BORRADOR, se aprueba en la tarea 0.5)
Esta decisión es **pre-registro**. Se aprueba antes de implementar los bloques nuevos y antes de mirar cualquier resultado. Cambiarla después exige un commit que lo justifique.

**Inventario `PHASE25_DESIGN_RULES`** (`R24`–`R38`; `ALL_DESIGN_RULES` no cambia):

| Regla | `name` | `purpose` | `ablation` |
| :--- | :--- | :--- | :--- |
| `R24` | ADN compacto y expresión condicional | Rasgos en codones de 32 bits expresados según el contexto, con costo sobre lo expresado. Sesgo declarado: abarata la complejidad latente. | `(("enable_compact_dna", False),)` |
| `R25` | Señal posicional epigenética | Proveer una señal de posición y conocimiento dentro del holón; su uso lo decide el ADN. | `(("enable_epigenetic_roles", False),)` |
| `R26` | Conjugación de plásmidos | Transferir codones entre vecinos en vida. | `(("enable_plasmid_hgt", False),)` |
| `R27` | Inmunidad CRISPR | Purgar plásmidos con balance energético negativo y bloquear su reingreso. | `(("enable_crispr_immunity", False),)` |
| `R28` | Endospora disponible | Permitir un estado de bajo gasto; su uso lo decide el ADN. | `(("enable_sporulation", False),)` |
| `R29` | Senescencia telomérica | Limitar la vida con una longevidad expresada. Sesgo declarado: fuerza recambio. | `(("enable_telomere_senescence", False),)` |
| `R30` | Mutación SOS | Aumentar la variación bajo estrés y reducirla en abundancia. | `(("enable_sos_mutation", False),)` |
| `R31` | Compromiso simbiótico | Permitir que un holón se vuelva indisoluble si sus hojas lo expresan. | `(("enable_symbiotic_ratchet", False),)` |
| `R32` | Conducta codificada en el ADN | Que la política de acción y la decisión de comunicar se expresen desde el ADN. | `(("enable_genetic_policy", False),)` |
| `R33` | Recursos agotables | Escasez real: los recursos tardan en reponerse. | `(("enable_resource_depletion", False),)` |
| `R34` | Heterogeneidad espacial y estacional | Nichos por región y abundancia variable en el tiempo. | `(("enable_heterogeneity", False),)` |
| `R35` | Cadáveres | Cerrar el ciclo de energía: los muertos son recurso. | `(("enable_carcasses", False),)` |
| `R36` | Transferencia de energía | Permitir ceder energía a un vecino; su uso lo decide el ADN. | `(("enable_energy_transfer", False),)` |
| `R37` | Depredación | Permitir robar energía a un vecino más débil; su uso lo decide el ADN. | `(("enable_predation", False),)` |
| `R38` | Recombinación | Permitir el cruce de cromosomas con una pareja; su uso lo decide el ADN. | `(("enable_recombination", False),)` |

- `PHASE25_ALL_RULES = ALL_DESIGN_RULES + PHASE25_DESIGN_RULES`, y `ablate()` busca en las dos tuplas.

**Protocolos `PHASE25_PROTOCOL_CONFIGS`**, con `(resources_per_pattern, resource_regen_delay)` fijados por la compuerta de viabilidad (D55):
- `"25a"` (ecología individual): `PHASE2_PROTOCOL_CONFIGS["002a"]` con `enable_compact_dna`, `enable_genetic_policy`, `enable_plasmid_hgt`, `enable_crispr_immunity`, `enable_sporulation`, `enable_telomere_senescence`, `enable_sos_mutation`, `enable_resource_depletion`, `enable_heterogeneity` (`season_length = 500`), `enable_carcasses`, `enable_energy_transfer`, `enable_predation` y `enable_recombination` en `True`.
- `"25b"` (ecología holónica): `PHASE2_PROTOCOL_CONFIGS["003a"]` con las banderas de `"25a"` más `enable_epigenetic_roles` y `enable_symbiotic_ratchet`.
- `"25c"` (comunicación desde cero): `"25a"` con `comm_propensity_base = 0.0`.

**Condiciones de comparación:**
- `full`: la configuración del protocolo;
- `drift`: `ablate(config, ["R12"])`, **reproducción neutral**. Con `enable_compact_dna` activa, la reproducción holónica ($R_{17}$) también es neutral: cada hoja hija recibe el ADN de un donante sorteado con `donor_rng`, en el orden de las hojas del holón (precisión 41). Así `drift` quita la selección también en `25b`.
- `no_predation` (sólo `"25a"`): `ablate(config, ["R37"])`;
- `null_content`: el control nulo de contenido, para E4.

**Afirmaciones `PHASE25_CLAIMS`.** Son **pruebas genuinas**: ninguna regla persigue la métrica, y la comparación es contra la reproducción neutral o contra la ablación de un mecanismo ecológico. La reproducción neutral **no es deriva pura**: conserva sesgos residuales que se declaran en la precisión 44. Cada métrica es la media de la ventana final (el último 10 % de los ticks) de su campo de `GeneticTickMetrics` o `EcologyTickMetrics`.

| Afirmación | Protocolo | Métrica (↑) | Comparación | $R_C$ | Canal | $\delta_{\min}$ (propuesto) |
| :--- | :--- | :--- | :--- | :--- | :--- | ---: |
| `C13` La regulación génica evoluciona | `25a` | `regulated_expression_fraction` (precisión 42) | `full` frente a `drift` | `("R12",)` | `()` | 0.05 |
| `C14` La conducta evoluciona | `25a` | `policy_divergence` | `full` frente a `drift` | `("R12",)` | `()` | 0.05 |
| `C15` La comunicación evoluciona desde cero | `25c` | `communicating_fraction` | `full` frente a `drift` | `("R12",)` | `()` | 0.10 |
| `C16` Actividad evolutiva por encima de la reproducción neutral | `25a` | `new_activity_per_birth` (último tick, precisión 43) | `full` frente a `drift` | `("R12",)` | `()` | 0.01 |
| `C17` La depredación aumenta la complejidad genética | `25a` | `mean_active_functional_codons` (precisión 42) | `full` frente a `no_predation` | `("R37",)` | `()` | 1.0 |
| `C18` La cooperación material evoluciona en los holones | `25b` | `share_rate` | `full` frente a `drift` | `("R12",)` | `()` | 0.01 |

- **Clasificación.** Con canal vacío, ninguna es programada por construcción.
- **Pares válidos (precisión 45).** Se excluye el par de una semilla si alguna de sus dos condiciones termina sin hojas activas. Si quedan menos de 20 pares válidos, la afirmación es `NOT_OBSERVED` con `evaluable = False`, y sigue contando en la corrección de Holm.
- **Prueba.** Prueba de signo unilateral sobre las diferencias de los pares válidos, descartando empates.
- **Corrección.** Holm–Bonferroni sobre `C13`–`C18` con $\alpha = 0.05$.
- **Estado.** `OBSERVED` si el p-valor ajustado es menor que $\alpha$ **y** la mediana de las diferencias pareadas es al menos $\delta_{\min}$; `NOT_OBSERVED` en otro caso. Se informan siempre el p-valor crudo, el ajustado, la mediana y la demografía.
- **E4.** Se informa contra `null_content`. Es interpretable en un protocolo sólo si, con la configuración elegida por la compuerta, su condición `null_content` fue viable en al menos 8 de las 10 semillas de viabilidad; si no, se declara no interpretable sin mirar la métrica.
- **Efectos de regla.** `rule_effects` (una variante por regla de `PHASE25_ALL_RULES`, salvo las inactivas del protocolo) son **exploratorios**: se miden sólo con las semillas 42–51 y no entran en la corrección de Holm.

**Perfil.**
- `phase25`: 5000 ticks.
- `PHASE25_SEEDS = tuple(range(42, 72))`, 30 semillas.
- `PHASE2_SEEDS` no cambia.

**Prueba de humo.** Después de la compuerta y antes de los runners. Registra, por protocolo, condición y semilla, sólo la terminación, la generación máxima y la población final, sin calcular ni mirar las métricas de las afirmaciones.


### Precisiones de la reformulación (2026-10-20, surgidas de la redacción de los specs)
Cierran huecos de D53–D56 sin cambiar su intención. Forman parte del borrador que se aprueba en la tarea 0.5.
1. **Estado `OBSERVED`.** `ClaimStatus` agrega el miembro `OBSERVED = "OBSERVED"`, que sólo usan las afirmaciones de D56. Los estados de las Fases I y II no cambian.
2. **Reglas inactivas (`PHASE25_INACTIVE_RULES`).** `"25a"` y `"25c"`: `R14`–`R19`, `R22`, `R23`, `R25` y `R31` (sin herencia cultural, holones ni estigmergia, como `002a`). `"25b"`: `R14`, `R18` y `R19`, como `003a`. Un test las contrasta con las configuraciones.
3. **Tipos y función de la atribución.**
   - `Phase25Claim` (`frozen`): `claim_id`, `statement`, `protocol`, `metric`, `comparison` (`"drift"` o `"no_predation"`), `rule_ids`, `channel` y `delta_min`.
   - `Phase25ClaimEvaluation` (`frozen`): `claim_id`, `status`, `p_value`, `p_adjusted`, `median_difference`, `values`, `comparison_values`, `demography`, `e4_p_value` y `e4_interpretable`.
   - `Phase25Report` (`frozen`): `profile = "phase25"`, `rules = PHASE25_ALL_RULES`, `evaluations` y `rule_effects` (exploratorios).
   - `run_phase25_attribution(seeds=PHASE25_SEEDS, claims=PHASE25_CLAIMS, jobs=1, configs=None, rule_effect_seeds=PHASE25_RULE_EFFECT_SEEDS) -> Phase25Report`, con `PHASE25_RULE_EFFECT_SEEDS = tuple(range(42, 52))` y `PROFILES["phase25"]`.
4. **Ventana final.** Son los últimos `max(1, math.ceil(0.1 * total_ticks))` ticks.
5. **Denominadores.** Las "decisiones del tick" son las de las hojas vivas que no estaban en endospora en la Fase 3, incluidas las que terminan en `IDLE`.
   - `policy_divergence` y `share_rate` valen 0.0 sin decisiones; `policy_divergence` sólo cuenta las tomadas con la política genética.
   - En `regulated_expression_fraction`, una hoja sin codones activos aporta 0.0.
6. **Actividad de Bedau–Packard.** Un codón "cruza" el umbral en el tick $t$ si $a_c(t-1) < $ `activity_threshold` $\le a_c(t)$. Una hoja aporta 1 por codón distinto que porta, aunque lo porte en el cromosoma y en un plásmido, o varias veces.
7. **`GeneticTickMetrics`.** Conserva todos los campos de D41, incluido `locked_holons`, y agrega los de D53.2.
8. **Resumen del runner.** Por condición: `final_accuracy`, `final_agents`, `final_active_agents`, `max_generation` y el último registro de `genetic_history` y de `ecology_history`. La CLI usa por defecto `PHASE25_SEEDS`.
9. **Control nulo.** `null_content` aleatoriza el contenido de las creencias en todos los canales epistémicos, como en la Fase II (mensajes, estigmergia, herencia cultural y vista del holón). No altera el ADN, los plásmidos, la política ni la puerta de comunicación.
10. **Benchmark.** El criterio del 10 % de D54.2 se aplica a las dos variantes, con y sin `--compact-dna`.
11. **Donante sin energía (D49.1).** `SHARE` es factible sólo si la energía del agente es estrictamente positiva. Al ejecutarse, si la energía del donante es $\le 0$, no ocurre nada.
12. **"Sigue vivo" en la Fase 4 (D49).** Nadie muere en la Fase 4: "sigue vivo" quiere decir "sigue en `engine.agents`". Un objetivo con energía $\le 0$ puede ser atacado, y rinde `stolen = 0`.
13. **Parejas de la recombinación (D51.1).** El progenitor no es candidato de sí mismo. Las candidatas se fijan al empezar el paso de reproducción, entre las hojas vivas en ese momento: los nacidos en el mismo paso no cuentan.
14. **Recombinación en la deriva (D51 y D34.7).** Con la reproducción neutral, el primer cromosoma del cruce es el ADN del donante sorteado con `donor_rng`. La búsqueda de pareja y la propensión son las del agente que se reproduce. El orden de extracciones es: el donante con `donor_rng`, el cruce con `evo_rng` (D51.2) y la mutación con `evo_rng`. Así, `drift` sólo quita la selección y conserva la recombinación.
15. **Índice del patrón (D48.2).** Es el $i$ del nombre `p_i` con que el entorno crea el patrón, no su posición en el orden de `Pattern`.
16. **Estación del retardo (D48.2).** Es la del tick en que se consume el recurso, cuando se agenda su `due`.
17. **Cadáveres (D48.3).**
    - Reciben `resource_id` del contador monótono del entorno.
    - Varios cadáveres del mismo tick se depositan en orden de `agent_id`.
    - Las perturbaciones (`ablate_population` y `ablate_discoverers`) no dejan cadáver: sólo el hambre y la depredación.
    - Comer un cadáver sigue el camino de cualquier recurso elemental: suma a `direct_discoverers` y, con $R_{19}$, deposita estigmergia.
18. **`get_resource_count` (D47.2).** Cuenta todos los recursos presentes en el tablero, incluidos los compuestos y los cadáveres.
19. **Momento del sello (D50.3 y D53.1).** El sello de $R_{31}$ se aplica en el paso de coordinación **antes** de cobrar el costo de coordinación y de evaluar `SPLIT`, como en D40: el descuento y la protección rigen desde ese mismo tick.
20. **Nombres de los eventos (D44.1).** Las claves de `frame.events` son los nombres de los campos contadores de `EcologyTickMetrics` (D53.3). Los nombres de los sistemas los fija la implementación y no son contrato.
21. **M2 con las conductas nuevas (D49.4).** M2 juzga **decisiones**, no acciones: si un agente tiene recursos elementales alcanzables y elige `FLEE`, `SHARE`, `ATTACK` o `SPORULATE`, la decisión cuenta como oportunidad y `judge_decision` la juzga como hoy (no es un `INTERACT` sobre el mejor recurso). Los cadáveres son recursos elementales alcanzables y entran en el oráculo de M2.
22. **Firmas públicas (D45.3).** `MicroAgent.__init__` agrega `policy: PolicyPort | None = None` al final, después de `protocol`, y `decide_action` agrega `social: SocialPerception | None = None` al final. El test de firmas canónicas de la Fase I se actualiza en el bloque 7 con esos parámetros opcionales, y ningún otro test de las Fases I y II cambia.
23. **Contexto de los impulsos (D46.4).** `MicroAgent` guarda el `EpigeneticContext` de su última expresión (`last_context`): el de la Fase 0 del tick o, en un recién nacido, el de su nacimiento. `GeneticPolicy` evalúa los impulsos con ese contexto.
24. **`GeneticPolicy` sin percepción social.** Con `social=None`, la política usa `SocialPerception()`, con sus valores por defecto: las señales sociales son falsas y `SHARE`, `ATTACK` y `FLEE` no son factibles.
25. **Factibilidad perezosa (D46.4).** La factibilidad se evalúa conducta por conducta, en el orden de prueba, y se detiene en la primera factible. Así, `rng` sólo se consume en `EXPLORE` y `WANDER` cuando el recorrido llega a ellas, como en `HandwrittenPolicy`.
26. **Valores de los enumerados (D47.1).** Los miembros de `Behavior` y los nuevos de `ActionType` usan como valor su nombre en texto, como `MessageType`. La correspondencia con los destinos de codón vive en `dna.py` (`BEHAVIOR_TARGETS`, en el orden de la tabla de D46.1).
27. **Longitud máxima con la política genética (D31 y D46.5).** Con `enable_compact_dna` y `enable_genetic_policy` activas, la validación exige `dna_max_length >= founder_dna_length(config)` (13) y `dna_min_length <= founder_dna_length(config)`.
28. **Truncado de la recombinación (D51.2).** "Truncado a `dna_max_length`" conserva el prefijo `[:dna_max_length]`.
29. **Importaciones de `policy.py` (D45.5).** Puede importar `micro_agent` sólo bajo `TYPE_CHECKING`, para anotar tipos, como `protocol.py`. `EcologicalEnvironmentPort` es `@runtime_checkable`, como los puertos anteriores.
30. **"$R_{28}$ activa" en `SPORULATE` (D46.1).** Quiere decir `enable_evolution` y `enable_sporulation` en la configuración del agente. La política genética ya está activa por construcción.
31. **"Con la política genética" (D46.6, D47.3, D53.2).** Quiere decir que $R_{32}$ está **efectivamente** activa: `enable_compact_dna` y `enable_genetic_policy` en `True`. Con `enable_genetic_policy=True` y sin ADN, $R_{32}$ es inerte: no hay percepción social, la puerta de comunicación no actúa y la política es la escrita a mano.
32. **$R_{31}$ sin ADN (D50.3 y D52.3).** Sin `enable_compact_dna`, $R_{31}$ es inerte: el sello no se evalúa, aunque `symbiotic_commitment_base >= 0.5`. Así el compromiso siempre es un rasgo heredable, nunca un decreto de la configuración.
33. **Canal vacío de C13–C18 frente a C6 (D56).** En la Fase II, C6 medía `evolved_accuracy`, que es justamente lo que persigue la selección por energía de $R_{12}$: comer bien da energía, y la energía da descendencia. Por eso su canal era $R_{12}$ y era programada por construcción. Las métricas de C13–C18 (regulación expresada, divergencia de la conducta, comunicación, actividad evolutiva, complejidad genética y cooperación material) no son lo que ninguna regla selecciona ni produce: si crecen por encima de la deriva, es porque la selección las construyó como medio, no como fin. Por eso su canal es vacío. Estas afirmaciones no recorren la escalera E1–E5 de la Fase I: se evalúan sólo con la comparación pre-registrada, la corrección de Holm y $\delta_{\min}$, y E4 se informa aparte.
34. **Política de los descendientes (D45.3).** `MicroAgent.from_lineage` recibe `policy` y lo propaga a su construcción. `create_offspring` le pasa la política del progenitor.
35. **Recombinación en la deriva (precisión 14).** En la reproducción neutral, el ADN del donante sorteado es la base completa del hijo, como en D34.7: con $R_{38}$, el primer cromosoma del cruce, los plásmidos y `crispr_memory` son los del donante.
36. **Contexto de `regulated_expression_fraction` (D53.2).** La fracción se calcula sobre la transcripción del fenotipo con el `last_context` de cada hoja (precisión 23).
37. **Muertes por depredación y por hambre (D53.3).** Son excluyentes. Una muerte del tick es por depredación si el agente fue objetivo, en ese tick, de un ataque con éxito y `stolen > 0`; si no, es por hambre.
38. **Semillas de E4 (D56).** `e4_p_value` se calcula con `PHASE25_SEEDS`, pareando `full` con `null_content` por semilla.
39. **Conjuntos del `TickFrame` (D44.1).** `moved`, `surplus` y cualquier otro `set` del marco se recorren siempre con `sorted(...)`, como exige `CLAUDE.md`.
40. **Oscilación de la endospora (D50.2).** Un agente puede entrar en endospora con `SPORULATE` y germinar al tick siguiente si ve un recurso, y alternar así. Es física declarada: el costo reducido de la endospora es una capacidad disponible, y su uso lo decide el ADN.
41. **Reproducción holónica neutral (D56, `drift`).** Con `reproduction_mode == "neutral"` y `enable_compact_dna` activa, `_reproduce` sortea, para cada hoja progenitora de una reproducción holónica ($R_{17}$) y en el orden de `leaf_agents`, un donante con `donor_rng` entre los mismos donantes que la reproducción individual. El hijo de esa hoja recibe el ADN del donante, que después se muta. Sin ADN, $R_{17}$ se comporta como en la Fase II, así que sus historiales no cambian.
42. **Codones activos y expresión regulada (C13 y C17).** Para cada hoja con ADN, sus **codones activos** son la unión, por posición en `chromosome + plasmids`, de:
    - los codones con destino de rasgo (`0x00`–`0x08`, `0x0A`–`0x0C`) y modo distinto de 3 activos en la transcripción del fenotipo con `last_context`;
    - los codones con destino de conducta (`0x40`–`0x47`) y modo distinto de 3 activos en la última evaluación de impulsos de la hoja (vacío si no decidió).
    - `mean_active_functional_codons` es la media, sobre las hojas con ADN, de la cantidad de **valores distintos** entre sus codones activos. Así, duplicar un codón o acumular codones inertes no suma complejidad.
    - `regulated_expression_fraction` es la media, sobre las hojas con ADN, de la fracción de sus codones activos cuyo promotor es **condicional en el protocolo**: `0x18`, `0x19`, `0x20`–`0x27` y `0x80`–`0xBF` siempre, y `0x01`–`0x0A` y `0x10`–`0x12` sólo si `enable_holonic_hierarchy` está activa (sin holones equivalen a `ALWAYS_BASAL` o nunca se activan). Una hoja sin codones activos aporta 0.0.
    - `mean_functional_codons` de D53.2 se conserva como descriptiva.
43. **Actividad por nacimiento (C16).** `GeneticTickMetrics` agrega `cumulative_births` y `new_activity_per_birth = cumulative_new_activity / cumulative_births` (0.0 sin nacimientos). Normaliza la actividad por el aporte de variación, que crece con los nacimientos y difiere entre `full` y `drift`.
44. **Sesgos residuales de la reproducción neutral (D56).** En `drift` siguen actuando: la selección por supervivencia (los donantes son los vivos al empezar la reproducción), la purga de plásmidos de $R_{27}$ y la escala de mutación de $R_{30}$, que depende de la energía del progenitor. Actúan igual en las dos condiciones, salvo la supervivencia. El sesgo esperable es **conservador**: la supervivencia en `drift` acerca su resultado al de `full`, y la selección purificadora en `full` reduce `policy_divergence` (C14). Por eso las pruebas unilaterales sólo detectan selección positiva neta.
45. **Pares válidos y demografía (D56).** Un par (semilla) es válido si las dos condiciones terminan con al menos una hoja activa. `Phase25ClaimEvaluation` agrega `excluded_pairs` y `evaluable`, y su `demography` contiene, por semilla y condición, `final_agents`, `final_active_agents`, `max_generation`, `cumulative_births` y `cumulative_deaths`, que se informan siempre como covariables.
46. **Codones de conducta activos (precisión 42).** `dna.py` define `active_codon_indices(dna, context, signals, config) -> tuple[int, ...]`, pura: los índices, en `chromosome + plasmids`, de los codones de destino de conducta y modo distinto de 3 activos en la evaluación de impulsos. `GeneticPolicy` guarda en el agente `last_behavior_codons` (esos índices) cada vez que decide. "La última evaluación" es la del tick actual: una hoja que no decidió en el tick (por ejemplo, una endospora) tiene `last_behavior_codons == ()`.
47. **Campos de la evaluación (precisión 45).** `Phase25ClaimEvaluation` agrega al final, en este orden, `excluded_seeds: tuple[int, ...]`, `excluded_pairs: int` (su longitud) y `evaluable: bool`.
48. **P-valor de una afirmación no evaluable.** Es el de la prueba de signo sobre sus pares válidos (1.0 si no queda ninguna diferencia distinta de cero), y entra así en la corrección de Holm.
49. **Nacimientos y muertes acumulados.** `cumulative_births` y `cumulative_deaths` son las sumas, desde el tick 0, de `births` y `deaths` de `evolutionary_history`: incluyen los nacimientos individuales y holónicos, y las muertes por hambre y por depredación. Las perturbaciones no cuentan, y los protocolos de D56 no tienen ninguna.

---

## Arquitectura de Módulos y Árbol de Archivos

```text
src/ide/
├── config.py               # MODIFICADO: banderas e hiperparámetros (D31 y D52); sin lock_composite_threshold
├── domain/
│   ├── types.py            # MODIFICADO: +EpigeneticRole, +CompactDNA, +EpigeneticContext, +ExpressedPhenotype (D31, D46.7),
│   │                       #   +Behavior, +VisibleAgent, +SocialPerception, +SensorySignals, ActionType ampliado (D47)
│   └── ports.py            # MODIFICADO: +EcologicalEnvironmentPort (D47.2)
├── agent/
│   ├── dna.py              # NUEVO: codón, ADN fundador, transcripción, mutate_dna, plásmidos,
│   │                       #   +evaluate_drives, +founder_dna_length, +recombine_dna (D46, D51)
│   ├── policy.py           # NUEVO: PolicyPort, HandwrittenPolicy, GeneticPolicy (D45, D46)
│   ├── protocol.py         # MODIFICADO: puerta de comunicación (D46.6)
│   ├── memory.py           # MODIFICADO: +resize
│   ├── evolution.py        # MODIFICADO: +compute_dna_cost, +compute_senescence_cost
│   ├── micro_agent.py      # MODIFICADO: ADN, fenotipo, base_config, rol, edad, endospora, express, política
│   └── holon.py            # MODIFICADO: +assign_epigenetic_roles, +is_locked, sello por compromiso (D50.3)
├── environments/grid2d.py  # MODIFICADO: EcologicalEnvironmentPort, R33, R34, R35 (D48)
├── simulation/
│   ├── pipeline.py         # NUEVO: EngineSystem, TickObserver, TickFrame, build_systems (D44)
│   └── engine.py           # MODIFICADO: pipeline, Fase 0, hgt_rng, percepción social, interacciones, endosporas
└── experiments/
    ├── metrics.py          # MODIFICADO: +GeneticTickMetrics, +EcologyTickMetrics, observadores (D53)
    ├── attribution.py      # MODIFICADO: +PHASE25_DESIGN_RULES, +PHASE25_CLAIMS, Holm y δ_min (D56)
    ├── phase25_viability.py # NUEVO: compuerta de viabilidad (D55)
    └── exp25_runner.py     # NUEVO: protocolos 25a, 25b y 25c + CLI
```

- `dna.py` importa sólo `ide.domain`, `ide.config`, `numpy` y la biblioteca estándar. No importa `micro_agent.py`, `policy.py` ni `holon.py`.
- `policy.py` importa `dna.py`, `epistemology.py` y `ide.domain`, y cumple las invariantes de `src/ide/agent/`.

---

## Risks / Trade-offs

- **Romper los hashes dorados o la Fase II.** *Mitigación:* toda rama nueva queda detrás de su bandera y la reformulación no agrega generadores. El refactor por sistemas (D44) y el puerto de política (D45) se aceptan sólo con los hashes dorados, las huellas de la Fase II y los historiales del bloque 5 idénticos.
- **Refactor grande del motor.** Mover el código a sistemas puede alterar el orden de consumo de un generador sin que un test unitario lo note. *Mitigación:* el test de aceptación de D44.4 compara historiales completos, no sólo métricas finales, y el refactor no cambia ninguna conducta.
- **Costo de la conducta genética.** Evaluar impulsos en cada decisión encarece el bucle. *Mitigación:* el caché de D46.8 y la medición de D54 antes de las corridas largas.
- **Colapso por depredación.** La depredación puede extinguir la población. *Mitigación:* la eficiencia menor que 1, el éxito sólo contra un objetivo más débil y la compuerta de viabilidad (D55) antes de cualquier afirmación.
- **Inviabilidad del fundador en un entorno escaso.** El fundador reproduce la conducta de la Fase II, que no se diseñó para la escasez. *Mitigación:* la grilla declarada de D55; si nada es viable, decide el responsable del proyecto.
- **Resultado modesto.** Lo más probable es que la complejidad crezca poco y se estanque. Es un resultado válido: las afirmaciones C13–C18 están planteadas para detectar evolución genuina, no para confirmarla.
- **Olvido forzado oscilante.** Un agente cerca de un umbral de energía puede achicar y agrandar su memoria tick a tick. Es física declarada de $R_{24}$, no se suaviza, y la telemetría lo deja auditable.
- **Atribución con muchas reglas.** Quince reglas hacen costosos los `rule_effects`. *Mitigación:* son exploratorios y se miden con 10 semillas (D56).
- **Solapamiento con el Experimento 004 (decisión P7).** Con $R_{25}$ como señal, la especialización que aparezca es evolucionada sobre una señal diseñada. El Exp 004 se sigue midiendo con $R_{25}$ ablacionada.
- **JSON de la Fase II.** `config.to_dict()` incluye los campos nuevos, así que los JSON que regeneren los runners de la Fase II ya no son idénticos byte a byte a los de `registros/`. Lo que se garantiza es que los **historiales** y los valores medidos son idénticos. Para comparar un JSON regenerado con uno registrado, se comparan sin los campos de D31 y D52.

---

## Definition of Done (Checklist de Cierre de la Fase II-B)

- [ ] `ruff check`, `ruff format --check` y `pyright` sin errores ni advertencias.
- [ ] `python -m pytest --cov=ide` en verde (cobertura $\ge 90\%$), con los hashes dorados de la Fase I intactos y los historiales de la Fase II sin cambios con las banderas por defecto. Pasa también con otro `PYTHONHASHSEED`.
- [ ] El refactor por sistemas y el puerto de política cumplen la aceptación de D44.4, y el ADN fundador con la política genética reproduce la política escrita a mano (D46.5).
- [ ] `python -m pytest -m slow` en verde.
- [ ] `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict` sin advertencias.
- [ ] El pre-registro D56, aprobado en la tarea 0.5, está commiteado antes del primer commit de `exp25_runner.py`, y la compuerta de viabilidad (D55) está registrada antes de la prueba de humo.
- [ ] `/code-review` sin hallazgos accionables pendientes en cada bloque, según CLAUDE.md.
