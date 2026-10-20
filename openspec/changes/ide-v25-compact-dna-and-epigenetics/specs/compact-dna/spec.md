# Spec Delta: Compact DNA

## Purpose

Proveer el genotipo compacto de las hojas ($L = 0$) de la Fase II-B: codones de 32 bits con promotor, destino, modo, canal y carga; un ADN fundador neutro; la transcripción pura en dos pasadas con una red regulatoria de un solo nivel, que produce el fenotipo expresado según el contexto epigenético ($R_{24}$); los operadores de mutación del ADN; las operaciones sobre plásmidos y memoria CRISPR ($R_{26}$, $R_{27}$); la conducta codificada en el ADN ($R_{32}$): destinos de conducta, promotores sensoriales, la evaluación pura de impulsos y el fundador conductual neutro; y la recombinación pura de cromosomas ($R_{38}$). Todo vive en `src/ide/agent/dna.py`, según design D32, D33, D35, D37, D46 y D51.

## ADDED Requirements

### Requirement: Decodificación de los Campos del Codón
`decode_codon(codon) -> Codon` SHALL devolver un `NamedTuple` con `promoter = (c >> 24) & 0xFF`, `target = (c >> 16) & 0xFF`, `mode = (c >> 14) & 0x3`, `channel = (c >> 8) & 0x3F` y `delta = (p - 256 if p >= 128 else p) / 128.0` con `p = c & 0xFF`, usando enteros de Python y no `numpy.uint32`.

#### Scenario: Campos de un codón regulado y represor
- **WHEN** se invoca `decode_codon(0x80044580)`
- **THEN** devuelve `promoter == 0x80`, `target == 0x04`, `mode == 1`, `channel == 5` y `delta == -1.0` (con tolerancia `1e-9`).

#### Scenario: Extremo superior de la carga
- **WHEN** se invoca `decode_codon(encode_codon(0x00, 0x00, payload=127))`
- **THEN** `delta` vale `0.9921875` (con tolerancia `1e-9`).

### Requirement: Codificación Inversa del Codón con Validación de Rango
`encode_codon(promoter, target, mode=0, channel=0, payload=0) -> int` SHALL ser la inversa de `decode_codon`, con `promoter` y `target` en $[0, 255]$, `mode` en $[0, 3]$, `channel` en $[0, 63]$ y `payload` en $[-128, 127]$, y SHALL lanzar `ValueError` si algún argumento está fuera de rango.

#### Scenario: Ida y vuelta
- **WHEN** se invoca `encode_codon(0x80, 0x04, 1, 5, -128)`
- **THEN** devuelve `0x80044580`, y `decode_codon` de ese valor recupera `promoter == 0x80`, `target == 0x04`, `mode == 1` y `channel == 5`.

#### Scenario: Argumentos fuera de rango
- **WHEN** se invoca `encode_codon` con `payload=128`, con `mode=4`, con `channel=64` o con `promoter=256`
- **THEN** cada invocación lanza `ValueError`.

### Requirement: Promotores de Contexto Holónico
La transcripción SHALL considerar activo el promotor `0x00` (`ALWAYS_BASAL`) siempre, el `0x01` (`SOLITARY_L0`) si y sólo si `context.holon_level == 0`, y cada promotor `0x02`–`0x0A` (`IN_HOLON_Lk`, con $k = \text{prom} - 1$) si y sólo si `context.holon_level >= k`.

#### Scenario: Activación según el nivel del holón
- **WHEN** se transcribe con `EpigeneticContext(holon_level=2)` un ADN con codones aditivos sobre el destino `0x00` y promotores `0x00`, `0x01`, `0x03` y `0x04`
- **THEN** sólo los codones con promotor `0x00` y `0x03` modulan el rasgo; los de `0x01` (exige nivel 0) y `0x04` (exige nivel 3) quedan inactivos.

### Requirement: Promotores de Rol y de Energía
La transcripción SHALL considerar activos los promotores `0x10`, `0x11` y `0x12` si y sólo si `context.role` es `EXPLORER`, `LIBRARIAN` o `NERVE`, respectivamente; el `0x18` si y sólo si `context.energy_ratio < config.stress_energy_ratio`; y el `0x19` si y sólo si `context.energy_ratio >= config.surplus_energy_ratio`.

#### Scenario: Umbrales de energía con desigualdades exactas
- **WHEN** con `stress_energy_ratio = 0.35` y `surplus_energy_ratio = 0.85` se transcribe un ADN con un codón aditivo de promotor `0x18` y otro de promotor `0x19`, primero con `energy_ratio = 0.35` y después con `energy_ratio = 0.85`
- **THEN** con `0.35` ninguno de los dos está activo (`0.35` no es menor que `0.35`), y con `0.85` sólo está activo el de promotor `0x19`.

#### Scenario: Promotor de rol
- **WHEN** se transcribe un codón aditivo de promotor `0x11` con `role = EpigeneticRole.LIBRARIAN` y después con `role = EpigeneticRole.NERVE`
- **THEN** el codón está activo sólo en el primer contexto.

### Requirement: Promotores Reservados Inertes
Los promotores `0x0B`–`0x0F`, `0x13`–`0x17`, `0x1A`–`0x1F`, `0x28`–`0x7F` y `0xC0`–`0xFF` SHALL quedar reservados y nunca activarse en ningún contexto, ni en la transcripción del fenotipo ni en `evaluate_drives`; los promotores sensoriales `0x20`–`0x27` SHALL quedar inactivos en la transcripción del fenotipo, porque sólo actúan en la evaluación de impulsos (design D46.2).

#### Scenario: Codones con promotor reservado o sensorial en el fenotipo
- **WHEN** se agregan al ADN fundador codones aditivos con `payload = 64` sobre el destino `0x00` y promotores `0x0B`, `0x13`, `0x1A`, `0x20` (sensorial), `0x27` (sensorial), `0x28`, `0x7F` y `0xC0`, y se transcriben en contextos con todos los niveles, roles y energías
- **THEN** el `alpha_learning` expresado es siempre igual a la base.

#### Scenario: Promotores reservados en la evaluación de impulsos
- **WHEN** se evalúa con `evaluate_drives` un ADN con codones `encode_codon(p, 0x43, 0, 0, 64)` para `p` en `0x0B`, `0x1A`, `0x28`, `0x7F` y `0xC0`, con todos los campos de `SensorySignals` en `True`
- **THEN** el impulso de `WANDER` vale `0.0`.

### Requirement: Destinos de Rasgo con Base, Escala y Cotas
Los destinos `0x00`–`0x08` SHALL modular, con escalas $k$ de 0.40, 0.40, 0.35, 0.50, 3.0, 2.0, 2.0, 250 y 0.50, los rasgos $\alpha$, $\gamma$, $\epsilon$, $\omega_{\text{bond}}$, $C_{\max}$, $r_{\text{perc}}$, $r_{\text{com}}$, $T_{\max}$ y $E_{\text{espora}}$, con bases `alpha_learning`, `gamma_social_discount`, `epsilon_explore`, `initial_bond_affinity`, `memory_capacity`, `perception_radius`, `comm_radius`, `telomere_base_lifespan` y `spore_energy_threshold`.

#### Scenario: Codón aditivo sobre el destino de alfa
- **WHEN** con `alpha_learning = 0.40` se transcribe el ADN fundador más un codón `encode_codon(0x00, 0x00, 0, 0, 64)` ($\delta = 0.5$)
- **THEN** el `alpha_learning` expresado vale `0.40 + 0.40 * 0.5 = 0.60` (con tolerancia `1e-9`).

### Requirement: Destinos de Rasgo de Compromiso, Recombinación y Comunicación
Los destinos `0x0A`, `0x0B` y `0x0C` SHALL modular, como rasgos reales con escala $k = 0.60$, el compromiso simbiótico ($R_{31}$), la propensión a recombinar ($R_{38}$) y la propensión a comunicar ($R_{32}$), con bases `symbiotic_commitment_base`, `recombination_base` y `comm_propensity_base`, con la misma fórmula, el mismo recorrido y las mismas pasadas que los destinos `0x00`–`0x08` (design D46.7).

#### Scenario: Codones sobre los rasgos de la reformulación
- **WHEN** con `symbiotic_commitment_base = 0.0`, `recombination_base = 0.0` y `comm_propensity_base = 1.0` se transcribe el ADN fundador más `encode_codon(0x00, 0x0A, 0, 0, 64)`, `encode_codon(0x00, 0x0B, 0, 0, 32)` y `encode_codon(0x00, 0x0C, 0, 0, -64)`
- **THEN** `symbiotic_commitment == 0.30`, `recombination_propensity == 0.15` y `comm_propensity == 0.70` (con tolerancia `1e-9`).

#### Scenario: Un solo codón alcanza el umbral de 0.5
- **WHEN** con `recombination_base = 0.0` se transcribe el ADN fundador más `encode_codon(0x00, 0x0B, 0, 0, 108)` ($\delta = 0.84375$)
- **THEN** `recombination_propensity == 0.50625` (con tolerancia `1e-9`), que es $\ge 0.5$, mientras que con $k = 0.50$ el máximo de un codón sería $0.5 \cdot 0.9921875 < 0.5$.

### Requirement: Cotas de los Rasgos Expresados
La transcripción SHALL acotar $\alpha$ a $[0.01, 1]$; $\gamma$, $\epsilon$, $\omega_{\text{bond}}$ y los rasgos de `0x0A`–`0x0C` a $[0, 1]$; $C_{\max}$ a $[1, C^{\text{tope}}]$; los radios a $[1, r^{\text{tope}}]$; $T_{\max}$ a [`telomere_min_lifespan`, `telomere_max_lifespan`]; y $E_{\text{espora}}$ a [0, `reproduction_threshold`], con $C^{\text{tope}}$ y $r^{\text{tope}}$ iguales a las cotas de `mutate_genome` en la Fase II.

#### Scenario: Saturación de la propensión a comunicar
- **WHEN** con `comm_propensity_base = 1.0` se transcribe el ADN fundador más `encode_codon(0x00, 0x0C, 0, 0, 127)`
- **THEN** $x = 1.0 + 0.60 \cdot 0.9921875 = 1.5953125$ y `comm_propensity` vale `1.0` (con tolerancia `1e-9`).

#### Scenario: Saturación en la cota inferior
- **WHEN** con `alpha_learning = 0.40` se transcribe el ADN fundador más tres codones `encode_codon(0x00, 0x00, 0, 0, -128)`
- **THEN** $x = 0.40 - 0.40 \cdot 3 = -0.80$ y el `alpha_learning` expresado vale `0.01` (con tolerancia `1e-9`).

#### Scenario: Cota superior de la capacidad de memoria
- **WHEN** con `memory_capacity = 3`, `max_genome_memory_capacity = 6`, `num_world_patterns = 12` y `enforce_memory_constraint=True` se transcriben cuatro codones aditivos con $\delta = 0.5$ sobre el destino `0x04`
- **THEN** $x = 3 + 3 \cdot 2 = 9$ y la capacidad expresada vale `6`.

### Requirement: Destinos Reservados Inertes
El destino `0x09` (`EMIT_TF`) SHALL usarse sólo para emitir el canal `channel`, sin modular rasgos ni impulsos, y los destinos `0x0D`–`0x3F` y `0x48`–`0xFF` (operadores lógicos y órganos de la Fase IV) SHALL quedar reservados e inertes, en la transcripción del fenotipo y en `evaluate_drives`; `0x0A`–`0x0C` son destinos de rasgo y `0x40`–`0x47`, de conducta (design D46).

#### Scenario: Codones con destino reservado
- **WHEN** con `enable_genetic_policy=False` se agregan al ADN fundador codones `ALWAYS_BASAL` aditivos con `payload = 127` y destinos `0x0D`, `0x3F`, `0x48`, `0x80` y `0xFF`
- **THEN** el fenotipo expresado es igual al del ADN fundador, incluido `expressed_codons == 9`, y `evaluate_drives` devuelve los ocho impulsos en `0.0`.

### Requirement: ADN Fundador Neutro
`founder_dna(config) -> CompactDNA` SHALL devolver un cromosoma con los 9 codones `tuple(encode_codon(0x00, t) for t in range(0x00, 0x09))`, sin plásmidos ni firmas, y con `enable_genetic_policy=True` SHALL agregarle al final, en este orden, `encode_codon(0x00, 0x40, 0, 0, 127)`, `encode_codon(0x00, 0x41, 0, 0, 96)`, `encode_codon(0x00, 0x42, 0, 0, 64)` y `encode_codon(0x00, 0x43, 0, 0, 32)` (design D32 y D46.5).

#### Scenario: Fundador sin política genética
- **WHEN** se invoca `founder_dna(config)` con `enable_compact_dna=True` y `enable_genetic_policy=False`
- **THEN** `chromosome == tuple(encode_codon(0x00, t) for t in range(9))`, `plasmids == ()` y `crispr_memory == ()`.

#### Scenario: Fundador con política genética
- **WHEN** se invoca `founder_dna(config)` con `enable_compact_dna=True` y `enable_genetic_policy=True`
- **THEN** el cromosoma tiene 13 codones: los 9 del fundador sin política genética seguidos de los cuatro codones de conducta, en el orden `0x40`, `0x41`, `0x42` y `0x43`.

### Requirement: Longitud del ADN Fundador
`founder_dna_length(config) -> int` SHALL valer 13 con `enable_genetic_policy=True` y 9 sin ella, igual a `len(founder_dna(config).chromosome)`, y la constante `FOUNDER_DNA_LENGTH` SHALL conservar el valor 9, que es el que usa la validación de `dna_min_length` y `dna_max_length` (design D31 y D46.5).

#### Scenario: Longitud con y sin política genética
- **WHEN** se invoca `founder_dna_length` con `enable_genetic_policy=False` y con `enable_genetic_policy=True`
- **THEN** devuelve `9` y `13`, respectivamente, y `FOUNDER_DNA_LENGTH == 9` en ambos casos.

### Requirement: Neutralidad Fenotípica del ADN Fundador
Para todo contexto y toda configuración válida con `enable_compact_dna=True`, con o sin política genética, `transcribe_phenotype(founder_dna(c), ctx, c)` SHALL expresar exactamente las bases: `genome == genome_from_config(c)`, `lifespan == c.telomere_base_lifespan`, `spore_threshold == c.spore_energy_threshold` y los rasgos de `0x0A`–`0x0C` iguales a sus bases.

#### Scenario: Neutralidad del fundador en cualquier contexto
- **WHEN** se transcribe `founder_dna(config)` con una configuración válida con `enable_compact_dna=True`, con `enable_genetic_policy` en `False` y en `True`, y con los contextos `EpigeneticContext()`, `EpigeneticContext(3, EpigeneticRole.NERVE, 0.1)` y `EpigeneticContext(0, EpigeneticRole.EXPLORER, 2.0)`
- **THEN** en todos los casos `genome == genome_from_config(config)`, `lifespan == config.telomere_base_lifespan`, `spore_threshold == config.spore_energy_threshold`, `symbiotic_commitment == config.symbiotic_commitment_base`, `recombination_propensity == config.recombination_base`, `comm_propensity == config.comm_propensity_base` y `expressed_codons == 9`.

### Requirement: Impulsos del Fundador Conductual
Con `enable_genetic_policy=True`, `evaluate_drives(founder_dna(c), ctx, signals, c)` SHALL devolver `(0.9921875, 0.75, 0.5, 0.25, 0.0, 0.0, 0.0, 0.0)` para todo contexto y todas las señales, de modo que el orden de prueba de la política genética del fundador sea `CONSUME`, `EXPLORE`, `NAVIGATE` y `WANDER`, el de `HandwrittenPolicy` (design D46.5).

#### Scenario: Impulsos fundadores independientes del contexto y de las señales
- **WHEN** se evalúa `founder_dna(config)` con `enable_genetic_policy=True` en los contextos `EpigeneticContext()` y `EpigeneticContext(3, EpigeneticRole.NERVE, 0.1)`, con todos los campos de `SensorySignals` en `False` y después en `True`
- **THEN** los cuatro resultados son `(0.9921875, 0.75, 0.5, 0.25, 0.0, 0.0, 0.0, 0.0)` (con tolerancia `1e-9`).

### Requirement: Transcripción Pura sobre Cromosoma y Plásmidos
`transcribe_phenotype(dna, context, config) -> ExpressedPhenotype` SHALL ser una función pura que recorre los codones en el orden `chromosome + plasmids` y no transcribe `crispr_memory`.

#### Scenario: Plásmido transcrito y firma CRISPR ignorada
- **WHEN** con `alpha_learning = 0.40` el codón `encode_codon(0x00, 0x00, 0, 0, 64)` está primero sólo en `plasmids` y después sólo en `crispr_memory` de un ADN cuyo cromosoma es el fundador
- **THEN** el `alpha_learning` expresado vale `0.60` en el primer caso y `0.40` en el segundo (con tolerancia `1e-9`).

### Requirement: Factores de Transcripción de la Pasada 1
La transcripción SHALL activar en la pasada 1 los codones con promotor menor que `0x80` cuyo promotor está activo, y entre ellos cada codón con `target == 0x09` y `mode != 3` SHALL sumar 1 a `act[channel]` si `mode` es 0 o 2, y a `rep[channel]` si `mode` es 1; el canal $c$ queda encendido si y sólo si `act[c] > rep[c]`.

#### Scenario: Activador neutralizado por un represor
- **WHEN** el ADN contiene `encode_codon(0x00, 0x09, 0, 3)`, `encode_codon(0x00, 0x09, 1, 3)` y un codón aditivo de promotor `0x83` sobre el destino `0x00`
- **THEN** `act[3] == rep[3] == 1`, el canal 3 queda apagado y el codón de promotor `0x83` no modula el rasgo.

#### Scenario: Canal encendido
- **WHEN** el ADN contiene `encode_codon(0x00, 0x09, 2, 3)` y un codón `encode_codon(0x83, 0x00, 0, 0, 64)`, con `alpha_learning = 0.40` y el ADN fundador
- **THEN** el canal 3 queda encendido y el `alpha_learning` expresado vale `0.60` (con tolerancia `1e-9`).

### Requirement: Red Regulatoria de un Solo Nivel
En la pasada 2, la transcripción SHALL activar los codones con promotor en `0x80`–`0xBF` cuyo canal `promoter - 0x80` quedó encendido en la pasada 1, y sus codones `EMIT_TF` SHALL NOT encender canales: la red tiene un solo nivel de regulación.

#### Scenario: Cascada de dos niveles no propagada
- **WHEN** el canal 3 está encendido en la pasada 1, el ADN contiene `encode_codon(0x83, 0x09, 0, 4)` y un codón aditivo de promotor `0x84` sobre el destino `0x00`, y ningún codón de la pasada 1 emite el canal 4
- **THEN** el canal 4 queda apagado y el codón de promotor `0x84` no modula el rasgo.

### Requirement: Fórmula de Expresión de un Rasgo
Para cada destino de rasgo $T$ en `0x00`–`0x08` y `0x0A`–`0x0C`, con $A_T$ sus codones activos de ambas pasadas, la transcripción SHALL calcular $x_T = b_T \cdot \mu + k_T \cdot \rho \cdot S$, con $S$ la suma de $\delta$ de modo 0, $\rho = \prod (1 - |\delta|)$ de modo 1 y $\mu = \prod (1 + \delta)$ de modo 2, ignorar el modo 3, acumular en el orden de recorrido y usar $x_T = b_T$ si $A_T$ está vacío.

#### Scenario: Combinación de los tres modos
- **WHEN** con `alpha_learning = 0.40` y el ADN fundador se agregan, sobre el destino `0x00` con promotor `0x00`, un codón aditivo con `payload = 64`, uno represor con `payload = -64`, uno multiplicativo con `payload = 64` y uno de modo 3 con `payload = 127`
- **THEN** $S = 0.5$, $\rho = 0.5$, $\mu = 1.5$ y el `alpha_learning` expresado vale `0.40 * 1.5 + 0.40 * 0.5 * 0.5 = 0.70` (con tolerancia `1e-9`); el represor no atenúa la parte multiplicativa.

### Requirement: Redondeo de los Rasgos Enteros
La transcripción SHALL expresar cada rasgo entero ($C_{\max}$, $r_{\text{perc}}$, $r_{\text{com}}$, $T_{\max}$) como `min(hi, max(lo, math.floor(x + 0.5)))`, sin usar `round`, y cada rasgo real como `min(hi, max(lo, x))`.

#### Scenario: Redondeo hacia arriba en el medio entero
- **WHEN** con `memory_capacity = 3` y $C^{\text{tope}} \ge 5$ se transcribe el ADN fundador más un codón `ALWAYS_BASAL` aditivo con `payload = 64` sobre el destino `0x04`
- **THEN** $x = 3 + 3 \cdot 0.5 = 4.5$ y la capacidad expresada vale `5` (`round(4.5)` daría `4`).

### Requirement: Salida del Fenotipo Expresado
`transcribe_phenotype` SHALL devolver un `ExpressedPhenotype` cuyo `genome` es el `AgentGenome` de `0x00`–`0x06`; `lifespan`, el valor de `0x07`; `spore_threshold`, el de `0x08`; `symbiotic_commitment`, `recombination_propensity` y `comm_propensity`, los de `0x0A`, `0x0B` y `0x0C`; y cuyo `expressed_codons` cuenta los codones activos con destino en `0x00`–`0x08` o `0x0A`–`0x0C` y modo distinto de 3 (design D33 y D46.7).

#### Scenario: Conteo de codones expresados
- **WHEN** se transcribe con `EpigeneticContext()` el ADN fundador sin política genética más un codón `EMIT_TF`, un codón de modo 3 sobre el destino `0x00`, un codón aditivo de promotor `0x01` sobre el destino `0x07`, un codón `ALWAYS_BASAL` aditivo sobre el destino `0x0C` y otro sobre el destino de conducta `0x40`
- **THEN** `expressed_codons == 11`: cuentan los 9 fundadores, el de promotor `0x01` y el de `0x0C`, no el `EMIT_TF`, ni el de modo 3, ni el de conducta.

#### Scenario: Codones de conducta del fundador fuera del conteo
- **WHEN** se transcribe `founder_dna(config)` con `enable_genetic_policy=True`
- **THEN** `expressed_codons == 9`, aunque el cromosoma tenga 13 codones activos.

### Requirement: Fenotipo de un Agente sin ADN
`phenotype_from_genome(genome, config) -> ExpressedPhenotype` SHALL devolver un fenotipo con `genome`, `lifespan = config.telomere_base_lifespan`, `spore_threshold = config.spore_energy_threshold`, `expressed_codons = 0` y los rasgos `symbiotic_commitment`, `recombination_propensity` y `comm_propensity` iguales a `symbiotic_commitment_base`, `recombination_base` y `comm_propensity_base`: el fenotipo de un agente sin ADN (design D33.7 y D46.7).

#### Scenario: Fenotipo del genoma plano
- **WHEN** se invoca `phenotype_from_genome(genome_from_config(config), config)` con `telomere_base_lifespan = 600`, `spore_energy_threshold = 0.30`, `symbiotic_commitment_base = 0.2`, `recombination_base = 0.4` y `comm_propensity_base = 0.6`
- **THEN** devuelve `genome == genome_from_config(config)`, `lifespan == 600`, `spore_threshold == 0.30`, `expressed_codons == 0`, `symbiotic_commitment == 0.2`, `recombination_propensity == 0.4` y `comm_propensity == 0.6`.

### Requirement: Destinos de Conducta
Los destinos `0x40`–`0x47` SHALL corresponder, en ese orden, a las conductas `CONSUME`, `EXPLORE`, `NAVIGATE`, `WANDER`, `SHARE`, `ATTACK`, `FLEE` y `SPORULATE` de `Behavior`, según la tupla `BEHAVIOR_TARGETS` de `dna.py`; SHALL modular sólo los impulsos de `evaluate_drives`, y en el fenotipo SHALL quedar inertes y fuera de `expressed_codons` (design D46.1, D46.3 y precisión 26).

#### Scenario: Correspondencia entre conductas y destinos
- **WHEN** se inspecciona `BEHAVIOR_TARGETS`
- **THEN** vale `(0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47)`, en el orden de `list(Behavior)`.

#### Scenario: Codón de conducta inerte en el fenotipo y activo en los impulsos
- **WHEN** con `enable_genetic_policy=False` se agrega al ADN fundador `encode_codon(0x00, 0x46, 0, 0, 127)`
- **THEN** el fenotipo expresado es igual al del ADN fundador, con `expressed_codons == 9`, y `evaluate_drives` devuelve `0.9921875` en la posición 6 (`FLEE`) y `0.0` en las demás (con tolerancia `1e-9`).

### Requirement: Promotores Sensoriales
En la pasada 1 de `evaluate_drives`, los promotores `0x20`–`0x27` SHALL estar activos si y sólo si es verdadero, respectivamente, el campo `known_good`, `unknown`, `no_resource`, `neighbor_adjacent`, `weaker_adjacent`, `stronger_near`, `crowded` o `carcass` de `SensorySignals`; los demás promotores SHALL activarse como en la transcripción del fenotipo (design D46.2).

#### Scenario: Impulso condicionado a la ausencia de recursos
- **WHEN** se evalúa un ADN cuyo único codón de conducta es `encode_codon(0x22, 0x43, 0, 0, 64)`, primero con `no_resource=True` y después con `no_resource=False`, con las demás señales en `False`
- **THEN** el impulso de `WANDER` vale `0.5` en el primer caso y `0.0` en el segundo.

#### Scenario: Correspondencia de cada promotor sensorial
- **WHEN** para cada `p` en `0x20`–`0x27` se evalúa el codón `encode_codon(p, 0x40, 0, 0, 64)` con sólo el campo `p - 0x20` de `SensorySignals` (en el orden de sus campos) en `True`, y después con ese único campo en `False`
- **THEN** el impulso de `CONSUME` vale `0.5` en el primer caso y `0.0` en el segundo, para los ocho promotores.

### Requirement: Evaluación Pura de Impulsos
`evaluate_drives(dna, context, signals, config) -> tuple[float, ...]` SHALL ser pura y devolver 8 impulsos en el orden de `Behavior`: repite las dos pasadas de la transcripción sobre `chromosome + plasmids`, con los promotores sensoriales activos en la pasada 1, y para cada destino de conducta $B$ calcula $d_B = \mu_B \cdot \rho_B \cdot S_B$ sobre sus codones activos de modo distinto de 3, sin cotas, en el orden de recorrido, con $d_B = 0$ si no tiene ninguno.

#### Scenario: Combinación de los tres modos en un impulso
- **WHEN** se evalúa un ADN con codones `ALWAYS_BASAL` sobre el destino `0x44`: aditivos con `payload` 64 y 32, uno represor con `payload = -64`, uno multiplicativo con `payload = 64` y uno de modo 3 con `payload = 127`
- **THEN** $S = 0.75$, $\rho = 0.5$, $\mu = 1.5$ y el impulso de `SHARE` vale `1.5 * 0.5 * 0.75 = 0.5625` (con tolerancia `1e-9`).

#### Scenario: Impulso negativo sin cotas
- **WHEN** se evalúa un ADN con dos codones `encode_codon(0x00, 0x45, 0, 0, -128)`
- **THEN** el impulso de `ATTACK` vale `-2.0` (con tolerancia `1e-9`).

#### Scenario: Canal regulado encendido por un sensor
- **WHEN** se evalúa un ADN con `encode_codon(0x23, 0x09, 0, 2)` y `encode_codon(0x82, 0x46, 0, 0, 64)`, primero con `neighbor_adjacent=True` y después con `neighbor_adjacent=False`
- **THEN** el canal 2 se enciende sólo en el primer caso, y el impulso de `FLEE` vale `0.5` y `0.0`, respectivamente.

#### Scenario: Determinismo de la evaluación
- **WHEN** se evalúa dos veces el mismo ADN con el mismo contexto, las mismas señales y la misma configuración, también en procesos con distinto `PYTHONHASHSEED`
- **THEN** las dos tuplas son idénticas bit a bit.

### Requirement: Puerta de R13 en la Mutación del ADN
`mutate_dna(dna, config, rng, scale=1.0) -> CompactDNA` SHALL devolver `dna` sin consumir `rng` si `config.mutation_rate == 0.0` y `config.discrete_mutation_prob == 0.0`, de modo que la ablación pre-registrada de $R_{13}$ congela también el ADN.

#### Scenario: ADN congelado por la ablación de R13
- **WHEN** se invoca `mutate_dna` con `mutation_rate = 0.0`, `discrete_mutation_prob = 0.0` y tasas de ADN iguales a `1.0`
- **THEN** devuelve un ADN igual a `dna` y el estado de `rng` no cambia.

### Requirement: Probabilidades Efectivas Escaladas
`mutate_dna` SHALL usar como probabilidades efectivas $p_x = \min(1, \text{scale} \cdot \text{config.dna\_}x\text{\_rate})$ para la mutación puntual, la duplicación, la deleción y la escisión.

#### Scenario: Escala con tope en 1
- **WHEN** se invoca `mutate_dna` sobre el ADN fundador con `dna_duplication_rate = 0.5`, `scale = 4.0`, `dna_point_mutation_rate = 0.0`, `dna_deletion_rate = 0.0`, `enable_plasmid_hgt=False` y `dna_max_length = 32`
- **THEN** $p_{\text{dup}} = 1$ y el cromosoma resultante tiene 10 codones para cualquier semilla de `rng`.

### Requirement: Mutación Puntual del Cromosoma
`mutate_dna` SHALL extraer `u = rng.random(len(chromosome))` y, para cada índice $i$ en orden con `u[i] < p_point`, extraer `bit = int(rng.integers(0, 32))` y aplicar `codon ^= 1 << bit`.

#### Scenario: Inversión de un bit reproducible
- **WHEN** se invoca `mutate_dna` sobre el ADN fundador con `dna_point_mutation_rate = 1.0`, `dna_duplication_rate = 0.0` y `dna_deletion_rate = 0.0`, y se repiten las extracciones con un generador gemelo sembrado igual
- **THEN** cada codón del resultado difiere del original en exactamente el bit que indica el generador gemelo, y el resultado tiene 9 codones.

### Requirement: Mutación Puntual de los Plásmidos
Si `plasmids` no está vacío, `mutate_dna` SHALL aplicarle, después del cromosoma, la misma mutación puntual, y SHALL eliminar el duplicado posterior si un plásmido mutado coincide con otro y descartar el plásmido mutado que coincida con un codón de `crispr_memory`.

#### Scenario: Plásmidos vacíos sin consumo
- **WHEN** se invoca `mutate_dna` sobre el ADN fundador sin plásmidos con todas las tasas del ADN en `0.0` y `enable_plasmid_hgt=False`, y un generador gemelo extrae `random(9)`, `random()` y `random()`
- **THEN** ambos generadores terminan en el mismo estado: no se extrae ningún arreglo para `plasmids`.

#### Scenario: Colisión entre plásmidos
- **WHEN** la mutación puntual convierte el primer plásmido en un codón igual al segundo
- **THEN** el ADN resultante conserva una sola copia de ese codón en `plasmids`, en la posición del primero.

#### Scenario: Plásmido mutado vetado por CRISPR
- **WHEN** la mutación puntual convierte un plásmido en un codón que está en `crispr_memory`
- **THEN** ese codón no figura en `plasmids` del ADN resultante y `crispr_memory` no cambia.

### Requirement: Duplicación de un Codón con Cota Máxima
`mutate_dna` SHALL extraer siempre `u = float(rng.random())` y, si `u < p_dup` y `len(chromosome) < dna_max_length`, extraer `i = int(rng.integers(len(chromosome)))` e insertar una copia del codón `i` en la posición `i + 1`.

#### Scenario: Secuencia exacta de extracciones de la duplicación
- **WHEN** se invoca `mutate_dna` sobre el ADN fundador sin plásmidos con `dna_point_mutation_rate = 0.0`, `dna_duplication_rate = 1.0`, `dna_deletion_rate = 0.0` y `enable_plasmid_hgt=False`, y un generador gemelo extrae `random(9)`, `random()`, `integers(9)` y `random()`
- **THEN** el cromosoma resultante tiene 10 codones, el codón en la posición `i + 1` es copia del codón `i` extraído por el gemelo, y ambos generadores terminan en el mismo estado.

#### Scenario: Cromosoma en la longitud máxima
- **WHEN** `len(chromosome) == dna_max_length` y `dna_duplication_rate = 1.0`
- **THEN** la duplicación no se aplica, no se extrae índice y el cromosoma conserva su longitud tras la duplicación.

### Requirement: Deleción de un Codón con Cota Mínima
Después de la duplicación, `mutate_dna` SHALL extraer siempre `u = float(rng.random())` y, si `u < p_del` y `len(chromosome) > dna_min_length`, extraer `i = int(rng.integers(len(chromosome)))` y eliminar el codón `i`.

#### Scenario: Cromosoma en la longitud mínima
- **WHEN** `len(chromosome) == dna_min_length == 1`, `dna_duplication_rate = 0.0` y `dna_deletion_rate = 1.0`
- **THEN** el cromosoma resultante conserva su único codón y no se extrae índice de deleción.

### Requirement: Escisión de un Codón a Plásmido
Sólo con `enable_plasmid_hgt=True`, después de la deleción, `mutate_dna` SHALL extraer `u = float(rng.random())` y, si `u < p_exc`, extraer `i = int(rng.integers(len(chromosome)))` y agregar el codón `i` al final de `plasmids` si no está ya en `plasmids` ni en `crispr_memory`, descartando el primero si se supera `max_plasmids`.

#### Scenario: Escisión con FIFO
- **WHEN** se invoca `mutate_dna` con `enable_plasmid_hgt=True`, `dna_excision_rate = 1.0`, `max_plasmids = 2`, tasas de las demás mutaciones en `0.0` y `plasmids` con dos codones que no están en el cromosoma
- **THEN** `plasmids` termina con el segundo plásmido original seguido del codón escindido.

#### Scenario: Escisión de un codón vetado
- **WHEN** el codón sorteado para la escisión está en `crispr_memory`
- **THEN** `plasmids` no cambia.

#### Scenario: Sin escisión con R26 apagada
- **WHEN** se invoca `mutate_dna` con `enable_plasmid_hgt=False` y `dna_excision_rate = 1.0`
- **THEN** no se extrae la `u` de la escisión y `plasmids` no cambia.

### Requirement: Memoria CRISPR Heredada sin Mutar
`mutate_dna` SHALL devolver `crispr_memory` sin cambios, y la secuencia de extracciones SHALL ser determinista: los pasos de duplicación, deleción y escisión consumen siempre su `u` y extraen el índice sólo si el operador se aplica.

#### Scenario: Firmas intactas con tasas máximas
- **WHEN** se invoca `mutate_dna` con todas las tasas del ADN en `1.0` sobre un ADN con `crispr_memory = (7, 9)`
- **THEN** el resultado tiene `crispr_memory == (7, 9)`.

### Requirement: Recepción de un Plásmido
`receive_plasmid(dna, codon, config) -> CompactDNA | None` SHALL devolver `None` si `enable_crispr_immunity=True` y `codon` está en `crispr_memory`; el mismo ADN si `codon` ya está en `plasmids`; y si no, el ADN con `codon` agregado al final de `plasmids`, descartando el primero si se supera `max_plasmids`.

#### Scenario: Bloqueo, duplicado y FIFO
- **WHEN** con `max_plasmids = 2` y `enable_crispr_immunity=True` un ADN con `plasmids = (1, 2)` y `crispr_memory = (5,)` recibe los codones `5`, `2` y `3`
- **THEN** con `5` devuelve `None`, con `2` devuelve el mismo ADN, y con `3` devuelve un ADN con `plasmids == (2, 3)`.

### Requirement: Purga de un Plásmido
`purge_plasmid(dna, codon, config) -> CompactDNA` SHALL quitar `codon` de `plasmids` y agregarlo al final de `crispr_memory`, descartando la firma más antigua si se supera `crispr_memory_size`.

#### Scenario: Purga con FIFO de firmas
- **WHEN** con `crispr_memory_size = 2` se purga el codón `4` de un ADN con `plasmids = (4, 6)` y `crispr_memory = (1, 2)`
- **THEN** el resultado tiene `plasmids == (6,)` y `crispr_memory == (2, 4)`.

### Requirement: Recombinación Pura de Cromosomas
`recombine_dna(parent, partner, a, b, config) -> CompactDNA` SHALL ser una función pura, sin generador, que devuelve un ADN con cromosoma `(parent.chromosome[:a] + partner.chromosome[b:])[:dna_max_length]` (truncado por prefijo, precisión 28), o el cromosoma de `parent` si el recombinado queda más corto que `dna_min_length`, y con `plasmids` y `crispr_memory` de `parent`; los cortes `a` y `b` los sortea el motor (design D51.2, D51.5).

#### Scenario: Cruce simple
- **WHEN** se invoca `recombine_dna` con `parent.chromosome == (1, 2, 3)`, `parent.plasmids == (8,)`, `parent.crispr_memory == (9,)`, `partner.chromosome == (4, 5, 6)`, `partner.plasmids == (7,)`, `a = 2` y `b = 1`
- **THEN** el resultado tiene `chromosome == (1, 2, 5, 6)`, `plasmids == (8,)` y `crispr_memory == (9,)`.

#### Scenario: Truncado a la longitud máxima
- **WHEN** con `dna_max_length = 12` se recombinan dos cromosomas de 9 codones con `a = 9` y `b = 0`
- **THEN** el cromosoma resultante tiene 12 codones: los 9 del progenitor seguidos de los 3 primeros de la pareja.

#### Scenario: Recombinado más corto que el mínimo
- **WHEN** con `dna_min_length = 5` se invoca `recombine_dna` con `parent.chromosome == (1, 2, 3, 4, 5, 6)`, `partner.chromosome == (7, 8, 9)`, `a = 1` y `b = 1`
- **THEN** el recombinado `(1, 8, 9)` tiene menos de 5 codones y el resultado tiene `chromosome == (1, 2, 3, 4, 5, 6)`.

### Requirement: Codones Funcionales Expresables
`expressible_codons(dna, holonic, roles) -> tuple[tuple[int, bool], ...]` SHALL ser pura, sin contexto, señales ni generador, y devolver en orden ascendente y sin repetidos los valores canónicos de los codones de `chromosome + plasmids` con destino de rasgo (`0x00`–`0x08`, `0x0A`–`0x0C`) o de conducta (`0x40`–`0x47`), modo distinto de 3 y promotor expresable, cada uno con si su promotor es condicional (design precisión 42).

#### Scenario: ADN fundador
- **WHEN** se invoca `expressible_codons(founder_dna(config), False, False)` con `enable_genetic_policy=False`
- **THEN** devuelve `tuple((encode_codon(0x00, t), False) for t in range(0x00, 0x09))`.

#### Scenario: Duplicados, inertes y firmas fuera
- **WHEN** al ADN fundador se le agregan en el cromosoma una copia de `encode_codon(0x00, 0x00)`, un `EMIT_TF`, un codón de modo 3 sobre `0x01` y uno aditivo sobre `0x0D`, la misma copia en `plasmids` y una firma en `crispr_memory`
- **THEN** el resultado tiene los mismos 9 elementos que el del fundador.

### Requirement: Valor Canónico de los Codones Funcionales
Como el campo `channel` sólo tiene efecto en los `EMIT_TF`, `expressible_codons` SHALL comparar los codones funcionales por su valor canónico `codon & ~0x3F00` y devolver ese valor; dos codones que difieren sólo en `channel` SHALL contar una vez (design precisión 42).

#### Scenario: Sinónimos por el campo channel
- **WHEN** sin política genética se agregan al cromosoma fundador `encode_codon(0x18, 0x01, 0, 3, 10)` y `encode_codon(0x18, 0x01, 0, 9, 10)`, que difieren sólo en `channel`, y `encode_codon(0x00, 0x02, 0, 7)`
- **THEN** `expressible_codons(dna, False, False)` tiene 10 elementos: los 9 del fundador, entre ellos `(encode_codon(0x00, 0x02), False)`, y `(encode_codon(0x18, 0x01, 0, 0, 10), True)` una sola vez.

### Requirement: Promotores Expresables en el Protocolo
Para `expressible_codons`, un promotor SHALL ser expresable si es `0x00`, `0x01`, `0x18` o `0x19`; `0x02`–`0x0A` sólo con `holonic`; `0x10`–`0x12` sólo con `holonic` y `roles`; `0x20`–`0x27` sólo sobre destinos de conducta; y `0x80`–`0xBF` si hay en `chromosome + plasmids`, nunca en `crispr_memory`, un emisor activador de su canal con promotor expresable menor que `0x80`, donde los sensoriales cuentan sólo para codones de conducta. Los reservados SHALL NOT serlo (design precisión 42).

#### Scenario: Promotores según el protocolo
- **WHEN** un ADN tiene codones aditivos de promotor `0x02` sobre `0x00`, `0x20` sobre `0x01`, `0x20` sobre `0x40` y `0x0B` sobre `0x41`, y se invoca `expressible_codons` con `holonic=False` y con `holonic=True`
- **THEN** con `False` es expresable sólo el de `0x20` sobre `0x40`, y con `True` también el de `0x02`.

#### Scenario: Promotores de rol sin R25
- **WHEN** un ADN tiene un codón aditivo de promotor `0x11` sobre `0x00` y se invoca `expressible_codons` con `holonic=True`, primero con `roles=False` y después con `roles=True`
- **THEN** el codón es expresable sólo con `roles=True`.

#### Scenario: Canal encendido por un sensor
- **WHEN** un ADN tiene `encode_codon(0x20, 0x09, 0, 5)` (emisor sensorial del canal 5), un codón aditivo de promotor `0x85` sobre `0x40` y otro de promotor `0x85` sobre `0x00`
- **THEN** es expresable el de destino `0x40` y no el de destino `0x00`.

#### Scenario: Emisor sólo en la memoria CRISPR
- **WHEN** un ADN tiene en el cromosoma un codón aditivo de promotor `0x85` sobre `0x02`, y su único `EMIT_TF` de modo 0 y promotor `0x00` sobre el canal 5 está en `crispr_memory`
- **THEN** ese codón no es expresable.

#### Scenario: Canal sin emisor activador
- **WHEN** un ADN tiene un codón aditivo de promotor `0x85` sobre `0x02`, y su única emisión del canal 5 es un `EMIT_TF` de modo 1 con promotor `0x00`
- **THEN** ese codón no es expresable.

### Requirement: Promotores Condicionales y Aproximación de los Canales Regulados
Un promotor expresable SHALL ser condicional salvo que sea constitutivo: `0x00`, `0x01` con `holonic=False` y `0x80`–`0xBF` cuando algún emisor activador de su canal tiene promotor constitutivo. Esta última es una aproximación declarada: SHALL NOT considerar los represores del canal, que en la transcripción pueden apagarlo (design precisión 42).

#### Scenario: Canal con activador constitutivo y represor
- **WHEN** un ADN tiene un codón aditivo de promotor `0x85` sobre `0x02`, un `EMIT_TF` de modo 0 y promotor `0x00` sobre el canal 5 y dos `EMIT_TF` de modo 1 y promotor `0x00` sobre el mismo canal
- **THEN** el codón es expresable y no condicional, aunque en la transcripción el canal 5 quede apagado.

#### Scenario: Canal con activador condicional
- **WHEN** un ADN tiene un codón aditivo de promotor `0x85` sobre `0x02` y su único activador del canal 5 es un `EMIT_TF` de modo 0 con promotor `0x18`
- **THEN** el codón es expresable y condicional.

### Requirement: Aislamiento del Módulo dna.py
`src/ide/agent/dna.py` SHALL importar sólo `ide.domain`, `ide.config`, `numpy` y la biblioteca estándar, y SHALL NOT importar `micro_agent`, `policy`, `holon`, `ide.environments`, `ide.simulation` ni `ide.experiments`; no ve coordenadas ni `true_value`.

#### Scenario: Auditoría AST de dna.py
- **WHEN** un test recorre el AST de `src/ide/agent/dna.py`
- **THEN** no encuentra importaciones de `ide.agent.micro_agent`, `ide.agent.policy`, `ide.agent.holon`, `ide.environments`, `ide.simulation` ni `ide.experiments`.
