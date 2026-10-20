# Design: Fase II-B (v2.5) — ADN Compacto de 32 bits, Regulación Génica, Epigenética, Plásmidos y Senescencia

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

---

## Goals / Non-Goals

**Goals:**
- Representar el genotipo de cada hoja ($L = 0$) como un `CompactDNA` de codones de 32 bits, con expresión condicional al contexto (nivel holónico, rol, energía) y una red regulatoria de un nivel ($R_{24}$).
- Cobrar el costo cuadrático $R_{21}$ sobre el fenotipo **expresado**, más un costo lineal por codón.
- Implementar, cada uno con su bandera y su ablación: roles epigenéticos ($R_{25}$), plásmidos ($R_{26}$), inmunidad CRISPR ($R_{27}$), esporulación ($R_{28}$), senescencia ($R_{29}$), mutación SOS ($R_{30}$) y trinquete simbiótico ($R_{31}$).
- Proveer telemetría genética, cuatro protocolos y su atribución, con un pre-registro que se apruebe antes de mirar resultados (D42).
- Compatibilidad bit a bit con las Fases I y II cuando las banderas nuevas están en su valor por defecto.

**Non-Goals:**
- **Operadores lógicos y órganos de sandbox de la Fase IV** (destinos `0x0A`–`0xFF`, modo `AST_PIPE`): quedan reservados e **inertes**.
- **Promotores espaciales o ecológicos de la Fase III** (`0x20`–`0x7F`): reservados e inertes.
- **ADN propio de los holones.** Un `CompositeAgent` no tiene ADN: su genética es la de sus hojas.
- **Comunicación nueva.** El ADN y los plásmidos **no transportan creencias**: el conocimiento social sigue entrando sólo por `assimilate_testimony`.
- **Recalibración del perfil.** No se recalibra a la vista de las afirmaciones (D42).

---

## Decisions (Numeradas D30 a D42, continuando D1–D29)

### Decisión 30: Alcance, Compatibilidad y Generadores
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
2. **Mutación puntual de los plásmidos.** Igual, sobre `plasmids`, sólo si no está vacío. Si un plásmido mutado coincide con otro, se elimina el duplicado posterior.
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
**Senescencia.** Con `enable_evolution` y `enable_telomere_senescence` activas, al cobrar el metabolismo:
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
- **Atributo.** `CompositeAgent` incorpora `is_locked: bool = False`.
- **Cuándo se suelda un holón.** Con `enable_holonic_hierarchy` y `enable_symbiotic_ratchet` activas, un holón **raíz** queda soldado en dos casos:
  - (a) al reproducirse por $R_{17}$: se sueldan el progenitor y su réplica;
  - (b) en el paso de coordinación de la Fase 5, antes de evaluar `SPLIT`, si `cooperative_completions >= lock_composite_threshold`.
- **Efectos de un holón soldado:**
  - `should_split_holon` devuelve `False`, por paciencia y por energía;
  - su costo de coordinación se multiplica por `lock_coord_discount`.
- **Lo que no impide.** La poda por muerte sigue actuando: si sobreviven dos o más hojas, el holón conserva el sello; con una sola, colapsa como en la Fase II. Un holón soldado puede fusionarse por `BOND` en un nivel superior, y conserva su sello si después queda expuesto como raíz.
- **Sesgo declarado.** La estabilidad que produzca $R_{31}$ es por decreto, no un hallazgo.

### Decisión 41: Orden de la Fase 5, Telemetría y Protocolos
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

### Decisión 42: Pre-Registro de la Fase II-B (BORRADOR — requiere aprobación, decisión P4)
Esta decisión es un **borrador de pre-registro**. Se aprueba o se corrige en la tarea 0.2, **antes** de implementar los runners y de mirar cualquier resultado. Una vez aprobada, cambiarla exige un commit que lo justifique.

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
   - `from_lineage` recibe además `dna` y `base_config`.
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

## Arquitectura de Módulos y Árbol de Archivos

```text
src/ide/
├── config.py               # MODIFICADO: banderas e hiperparámetros de la Fase II-B (D31)
├── domain/types.py         # MODIFICADO: +EpigeneticRole, +CompactDNA, +EpigeneticContext, +ExpressedPhenotype
├── agent/
│   ├── dna.py              # NUEVO: codón, ADN fundador, transcripción, mutate_dna, receive_plasmid, purge_plasmid
│   ├── memory.py           # MODIFICADO: +resize
│   ├── evolution.py        # MODIFICADO: +compute_dna_cost, +compute_senescence_cost
│   ├── micro_agent.py      # MODIFICADO: ADN, fenotipo, base_config, rol, edad, endospora, express, create_offspring
│   └── holon.py            # MODIFICADO: +assign_epigenetic_roles, +is_locked, should_split_holon con R31
├── simulation/engine.py    # MODIFICADO: Fase 0, hgt_rng, Fase 5 extendida, endosporas
└── experiments/
    ├── metrics.py          # MODIFICADO: +GeneticTickMetrics
    ├── attribution.py      # MODIFICADO: +PHASE25_DESIGN_RULES, +PHASE25_CLAIMS, +run_phase25_attribution
    └── exp25_runner.py     # NUEVO: protocolos 002c, 002d, 002e y 003c + CLI
```

`dna.py` importa sólo `ide.domain`, `ide.config`, `numpy` y la biblioteca estándar. No importa `micro_agent.py` ni `holon.py`.

---

## Risks / Trade-offs

- **Romper los hashes dorados o la Fase II.** *Mitigación:* toda rama nueva queda detrás de su bandera. `hgt_rng` es aparte. Un test exige que, con las banderas por defecto, los historiales de los protocolos de la Fase II sean idénticos a los de antes del cambio.
- **Costo de la Fase 0.** Transcribir el ADN en cada tick encarece el bucle. *Mitigación:* el caché por contexto (D34.2), más un benchmark que lo mida en el bloque del motor. No se vectoriza sin medir (CLAUDE.md).
- **Olvido forzado oscilante.** Un agente cerca de un umbral de energía puede achicar y agrandar su memoria tick a tick. Es física declarada de $R_{24}$, no se suaviza, y la telemetría lo deja auditable.
- **Atribución con muchas reglas.** Ocho reglas nuevas hacen costosos `rule_effects` y difícil su lectura. *Mitigación:* cada protocolo activa sólo las reglas que necesita (D42), y las inactivas se excluyen.
- **Solapamiento con el Experimento 004 (decisión P7).** Con $R_{25}$ activa, la especialización es programada. El Exp 004 se mide con $R_{25}$ ablacionada.
- **JSON de la Fase II.** `config.to_dict()` incluye los campos nuevos, así que los JSON que regeneren los runners de la Fase II ya no son idénticos byte a byte a los de `registros/`. Lo que se garantiza es que los **historiales** y los valores medidos son idénticos. Para comparar un JSON regenerado con uno registrado, se comparan sin los campos de D31.
- **Viabilidad.** Como en la Fase II, el perfil puede resultar inviable, por ejemplo `002e` con 10 recursos. Se reporta como resultado.

---

## Definition of Done (Checklist de Cierre de la Fase II-B)

- [ ] `ruff check`, `ruff format --check` y `pyright` sin errores ni advertencias.
- [ ] `python -m pytest --cov=ide` en verde (cobertura $\ge 90\%$), con los hashes dorados de la Fase I intactos y los historiales de la Fase II sin cambios con las banderas por defecto. Pasa también con otro `PYTHONHASHSEED`.
- [ ] `python -m pytest -m slow` en verde.
- [ ] `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate --all --strict` sin advertencias.
- [ ] El pre-registro aprobado (D42) está commiteado antes del primer commit de `exp25_runner.py`.
- [ ] `/code-review` sin hallazgos accionables pendientes en cada bloque, según CLAUDE.md.
