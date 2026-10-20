# Spec Delta: Compact DNA

## Purpose

Proveer el genotipo compacto de las hojas ($L = 0$) de la Fase II-B: codones de 32 bits con promotor, destino, modo, canal y carga; un ADN fundador neutro; la transcripción pura en dos pasadas con una red regulatoria de un solo nivel, que produce el fenotipo expresado según el contexto epigenético ($R_{24}$); los operadores de mutación del ADN; y las operaciones sobre plásmidos y memoria CRISPR ($R_{26}$, $R_{27}$). Todo vive en `src/ide/agent/dna.py`, según design D32, D33, D35 y D37.

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
Los promotores `0x0B`–`0x0F`, `0x13`–`0x17`, `0x1A`–`0x7F` y `0xC0`–`0xFF` SHALL quedar reservados y nunca activarse en ningún contexto, incluidos los promotores espaciales o ecológicos `0x20`–`0x7F` de la Fase III.

#### Scenario: Codones con promotor reservado
- **WHEN** se agregan al ADN fundador codones aditivos con `payload = 64` sobre el destino `0x00` y promotores `0x0B`, `0x13`, `0x20`, `0x7F` y `0xC0`, y se transcriben en contextos con todos los niveles, roles y energías
- **THEN** el `alpha_learning` expresado es siempre igual a la base.

### Requirement: Destinos de Rasgo con Base, Escala y Cotas
Los destinos `0x00`–`0x08` SHALL modular, con escalas $k$ de 0.40, 0.40, 0.35, 0.50, 3.0, 2.0, 2.0, 250 y 0.50, los rasgos $\alpha$, $\gamma$, $\epsilon$, $\omega_{\text{bond}}$, $C_{\max}$, $r_{\text{perc}}$, $r_{\text{com}}$, $T_{\max}$ y $E_{\text{espora}}$, con bases `alpha_learning`, `gamma_social_discount`, `epsilon_explore`, `initial_bond_affinity`, `memory_capacity`, `perception_radius`, `comm_radius`, `telomere_base_lifespan` y `spore_energy_threshold`.

#### Scenario: Codón aditivo sobre el destino de alfa
- **WHEN** con `alpha_learning = 0.40` se transcribe el ADN fundador más un codón `encode_codon(0x00, 0x00, 0, 0, 64)` ($\delta = 0.5$)
- **THEN** el `alpha_learning` expresado vale `0.40 + 0.40 * 0.5 = 0.60` (con tolerancia `1e-9`).

### Requirement: Cotas de los Rasgos Expresados
La transcripción SHALL acotar $\alpha$ a $[0.01, 1]$; $\gamma$, $\epsilon$ y $\omega_{\text{bond}}$ a $[0, 1]$; $C_{\max}$ a $[1, C^{\text{tope}}]$; los radios a $[1, r^{\text{tope}}]$; $T_{\max}$ a [`telomere_min_lifespan`, `telomere_max_lifespan`]; y $E_{\text{espora}}$ a [0, `reproduction_threshold`], con $C^{\text{tope}}$ y $r^{\text{tope}}$ iguales a las cotas de `mutate_genome` en la Fase II.

#### Scenario: Saturación en la cota inferior
- **WHEN** con `alpha_learning = 0.40` se transcribe el ADN fundador más tres codones `encode_codon(0x00, 0x00, 0, 0, -128)`
- **THEN** $x = 0.40 - 0.40 \cdot 3 = -0.80$ y el `alpha_learning` expresado vale `0.01` (con tolerancia `1e-9`).

#### Scenario: Cota superior de la capacidad de memoria
- **WHEN** con `memory_capacity = 3`, `max_genome_memory_capacity = 6`, `num_world_patterns = 12` y `enforce_memory_constraint=True` se transcriben cuatro codones aditivos con $\delta = 0.5$ sobre el destino `0x04`
- **THEN** $x = 3 + 3 \cdot 2 = 9$ y la capacidad expresada vale `6`.

### Requirement: Destinos Reservados Inertes
El destino `0x09` (`EMIT_TF`) SHALL usarse sólo para emitir el canal `channel` y no modular ningún rasgo, y los destinos `0x0A`–`0xFF` (operadores lógicos y órganos de la Fase IV) SHALL quedar reservados e inertes.

#### Scenario: Codones con destino reservado
- **WHEN** se agregan al ADN fundador codones `ALWAYS_BASAL` aditivos con `payload = 127` y destinos `0x0A`, `0x80` y `0xFF`
- **THEN** el fenotipo expresado es igual al del ADN fundador, incluido `expressed_codons == 9`.

### Requirement: ADN Fundador Neutro
`founder_dna(config) -> CompactDNA` SHALL devolver `CompactDNA(chromosome=tuple(encode_codon(0x00, t) for t in range(0x00, 0x09)))` y `FOUNDER_DNA_LENGTH` SHALL valer 9, de modo que `transcribe_phenotype(founder_dna(c), ctx, c).genome == genome_from_config(c)` para todo contexto y toda configuración válida con `enable_compact_dna=True`.

#### Scenario: Neutralidad del fundador en cualquier contexto
- **WHEN** se transcribe `founder_dna(config)` con una configuración válida con `enable_compact_dna=True`, con los contextos `EpigeneticContext()`, `EpigeneticContext(3, EpigeneticRole.NERVE, 0.1)` y `EpigeneticContext(0, EpigeneticRole.EXPLORER, 2.0)`
- **THEN** en los tres casos `genome == genome_from_config(config)`, `lifespan == config.telomere_base_lifespan`, `spore_threshold == config.spore_energy_threshold` y `len(founder_dna(config).chromosome) == 9`.

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
Para cada destino $T$ en `0x00`–`0x08`, con $A_T$ sus codones activos de ambas pasadas, la transcripción SHALL calcular $x_T = b_T \cdot \mu + k_T \cdot \rho \cdot S$, con $S$ la suma de $\delta$ de modo 0, $\rho = \prod (1 - |\delta|)$ de modo 1 y $\mu = \prod (1 + \delta)$ de modo 2, ignorar el modo 3, acumular en el orden de recorrido y usar $x_T = b_T$ si $A_T$ está vacío.

#### Scenario: Combinación de los tres modos
- **WHEN** con `alpha_learning = 0.40` y el ADN fundador se agregan, sobre el destino `0x00` con promotor `0x00`, un codón aditivo con `payload = 64`, uno represor con `payload = -64`, uno multiplicativo con `payload = 64` y uno de modo 3 con `payload = 127`
- **THEN** $S = 0.5$, $\rho = 0.5$, $\mu = 1.5$ y el `alpha_learning` expresado vale `0.40 * 1.5 + 0.40 * 0.5 * 0.5 = 0.70` (con tolerancia `1e-9`); el represor no atenúa la parte multiplicativa.

### Requirement: Redondeo de los Rasgos Enteros
La transcripción SHALL expresar cada rasgo entero ($C_{\max}$, $r_{\text{perc}}$, $r_{\text{com}}$, $T_{\max}$) como `min(hi, max(lo, math.floor(x + 0.5)))`, sin usar `round`, y cada rasgo real como `min(hi, max(lo, x))`.

#### Scenario: Redondeo hacia arriba en el medio entero
- **WHEN** con `memory_capacity = 3` y $C^{\text{tope}} \ge 5$ se transcribe el ADN fundador más un codón `ALWAYS_BASAL` aditivo con `payload = 64` sobre el destino `0x04`
- **THEN** $x = 3 + 3 \cdot 0.5 = 4.5$ y la capacidad expresada vale `5` (`round(4.5)` daría `4`).

### Requirement: Salida del Fenotipo Expresado
`transcribe_phenotype` SHALL devolver un `ExpressedPhenotype` cuyo `genome` es el `AgentGenome` de los valores de `0x00`–`0x06`, cuyo `lifespan` es el valor de `0x07`, cuyo `spore_threshold` es el valor de `0x08`, y cuyo `expressed_codons` cuenta los codones activos con destino en `0x00`–`0x08` y modo distinto de 3.

#### Scenario: Conteo de codones expresados
- **WHEN** se transcribe con `EpigeneticContext()` el ADN fundador más un codón `EMIT_TF`, un codón de modo 3 sobre el destino `0x00` y un codón aditivo de promotor `0x01` sobre el destino `0x07`
- **THEN** `expressed_codons == 10`: cuentan los 9 fundadores y el de promotor `0x01`, no el `EMIT_TF` ni el de modo 3.

### Requirement: Fenotipo de un Agente sin ADN
`phenotype_from_genome(genome, config) -> ExpressedPhenotype` SHALL devolver `ExpressedPhenotype(genome, config.telomere_base_lifespan, config.spore_energy_threshold, 0)`, el fenotipo de un agente sin ADN con el que $R_{28}$ y $R_{29}$ funcionan sobre el genoma plano.

#### Scenario: Fenotipo del genoma plano
- **WHEN** se invoca `phenotype_from_genome(genome_from_config(config), config)` con `telomere_base_lifespan = 600` y `spore_energy_threshold = 0.30`
- **THEN** devuelve `genome == genome_from_config(config)`, `lifespan == 600`, `spore_threshold == 0.30` y `expressed_codons == 0`.

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

### Requirement: Aislamiento del Módulo dna.py
`src/ide/agent/dna.py` SHALL importar sólo `ide.domain`, `ide.config`, `numpy` y la biblioteca estándar, y SHALL NOT importar `micro_agent`, `holon`, `ide.environments`, `ide.simulation` ni `ide.experiments`; no ve coordenadas ni `true_value`.

#### Scenario: Auditoría AST de dna.py
- **WHEN** un test recorre el AST de `src/ide/agent/dna.py`
- **THEN** no encuentra importaciones de `ide.agent.micro_agent`, `ide.agent.holon`, `ide.environments`, `ide.simulation` ni `ide.experiments`.
