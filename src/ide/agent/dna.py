"""ADN compacto de codones de 32 bits, su transcripción en dos pasadas y los impulsos (R24, R32).

Cubre D32 y D33 (codón y fenotipo), D46 (conducta en el ADN: promotores sensoriales, impulsos y
fundador conductual), D51.2 (recombinación) y la precisión 42 (codones expresables).

Módulo puro: sólo conoce `ide.domain`, `ide.config`, `numpy` (sólo para tipar el generador) y la
biblioteca estándar (los codones son `int` de Python, no `numpy.uint32`, D32). No importa
`micro_agent`, `holon`, `environments`, `simulation` ni `experiments`, y no ve coordenadas ni
`true_value`.
"""

import math
from typing import NamedTuple

import numpy as np

from ide.config import FOUNDER_DNA_LENGTH, SimulationConfig
from ide.domain.extensions import integer_trait_bounds
from ide.domain.types import (
    AgentGenome,
    Behavior,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    ExpressedPhenotype,
    SensorySignals,
)

__all__ = [
    "BEHAVIOR_TARGETS",
    "FOUNDER_DNA_LENGTH",
    "Codon",
    "decode_codon",
    "encode_codon",
    "evaluate_drives",
    "expressible_codons",
    "founder_dna",
    "founder_dna_length",
    "mutate_dna",
    "phenotype_from_genome",
    "recombine_dna",
    "transcribe_phenotype",
]

# Modos del codón (D32).
_MODE_ADDITIVE = 0
_MODE_REPRESSOR = 1
_MODE_MULTIPLICATIVE = 2
_MODE_RESERVED = 3

# Destinos (D32, D46.7): 0x00-0x08 y 0x0A-0x0C modulan un rasgo; 0x09 emite un canal.
_FOUNDER_TRAITS = 9  # un codón fundador por cada rasgo 0x00-0x08
_TARGET_EMIT_TF = 0x09
_TRAIT_TARGETS = (*range(0x00, 0x09), 0x0A, 0x0B, 0x0C)
_TRAIT_SLOT = {target: slot for slot, target in enumerate(_TRAIT_TARGETS)}
_TRAIT_COUNT = len(_TRAIT_TARGETS)
_INTEGER_SLOTS = range(4, 8)  # memory_capacity, perception_radius, comm_radius, lifespan

# Conductas (D46.1): un destino por `Behavior`, en el orden del enumerado.
BEHAVIOR_TARGETS = (0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47)
assert len(BEHAVIOR_TARGETS) == len(Behavior), "BEHAVIOR_TARGETS debe tener un destino por Behavior"
_BEHAVIOR_SLOT = {target: slot for slot, target in enumerate(BEHAVIOR_TARGETS)}
_BEHAVIOR_COUNT = len(Behavior)

# Destinos de otras decisiones, necesarios sólo para `expressible_codons` (D61, precisión 54):
# `0x0F` rasgo de plasticidad, `0x0D`/`0x0E` estado y `0x48` señal.
_TARGET_PLASTICITY_RATE = 0x0F
_TARGET_SET_STATE = 0x0D
_TARGET_CLEAR_STATE = 0x0E
_TARGET_SIGNAL = 0x48
_SENSING_TARGETS = frozenset(
    (_TARGET_SET_STATE, _TARGET_CLEAR_STATE, _TARGET_SIGNAL, *BEHAVIOR_TARGETS)
)
_FUNCTIONAL_TARGETS = _SENSING_TARGETS | {_TARGET_PLASTICITY_RATE, *_TRAIT_TARGETS}
_CHANNEL_MASK = 0x3F00  # bits 8-13 del codón
# Destinos donde `channel` no tiene efecto (D61); en estado y señal elige un bit y no se enmascara.
_CHANNEL_FREE_TARGETS = frozenset((*_TRAIT_TARGETS, _TARGET_PLASTICITY_RATE, *BEHAVIOR_TARGETS))

# Promotores (D32).
_PROM_SOLITARY_L0 = 0x01
_PROM_IN_HOLON_LAST = 0x0A
_PROM_ROLE_EXPLORER = 0x10
_PROM_ROLE_LIBRARIAN = 0x11
_PROM_ROLE_NERVE = 0x12
_PROM_STRESS = 0x18
_PROM_SURPLUS = 0x19
_PROM_SENSE_FIRST = 0x20  # sensoriales 0x20-0x27 (D46.2): sólo actúan en los impulsos
_PROM_SENSE_LAST = 0x27
_PROM_TF_FIRST = 0x80
_PROM_TF_LAST = 0xBF

# Escalas k de los destinos de rasgo (D32 y D46.7), en el orden de `_TRAIT_TARGETS`.
_SCALES = (0.40, 0.40, 0.35, 0.50, 3.0, 2.0, 2.0, 250.0, 0.50, 0.60, 0.60, 0.60)

_ROLE_PROMOTERS = {
    _PROM_ROLE_EXPLORER: EpigeneticRole.EXPLORER,
    _PROM_ROLE_LIBRARIAN: EpigeneticRole.LIBRARIAN,
    _PROM_ROLE_NERVE: EpigeneticRole.NERVE,
}


class Codon(NamedTuple):
    """Campos decodificados de un codón de 32 bits."""

    promoter: int
    target: int
    mode: int
    channel: int
    delta: float  # carga con signo en [-1.0, 0.9921875]


def decode_codon(codon: int) -> Codon:
    """Decodifica los campos de un codón con enteros de Python (D32)."""
    payload = codon & 0xFF
    return Codon(
        promoter=(codon >> 24) & 0xFF,
        target=(codon >> 16) & 0xFF,
        mode=(codon >> 14) & 0x3,
        channel=(codon >> 8) & 0x3F,
        delta=(payload - 256 if payload >= 128 else payload) / 128.0,
    )


def encode_codon(
    promoter: int, target: int, mode: int = 0, channel: int = 0, payload: int = 0
) -> int:
    """Inversa de `decode_codon`. Lanza `ValueError` si algún argumento está fuera de rango."""
    if not 0 <= promoter <= 255:
        raise ValueError(f"promoter debe estar en [0, 255], recibido {promoter}")
    if not 0 <= target <= 255:
        raise ValueError(f"target debe estar en [0, 255], recibido {target}")
    if not 0 <= mode <= 3:
        raise ValueError(f"mode debe estar en [0, 3], recibido {mode}")
    if not 0 <= channel <= 63:
        raise ValueError(f"channel debe estar en [0, 63], recibido {channel}")
    if not -128 <= payload <= 127:
        raise ValueError(f"payload debe estar en [-128, 127], recibido {payload}")
    return (promoter << 24) | (target << 16) | (mode << 14) | (channel << 8) | (payload & 0xFF)


# Codones conductuales del fundador (D46.5): impulsos 0.9921875, 0.75, 0.5 y 0.25, cuyo orden de
# prueba reproduce a `HandwrittenPolicy`.
_FOUNDER_BEHAVIOR_CODONS = (
    encode_codon(0x00, 0x40, 0, 0, 127),
    encode_codon(0x00, 0x41, 0, 0, 96),
    encode_codon(0x00, 0x42, 0, 0, 64),
    encode_codon(0x00, 0x43, 0, 0, 32),
)


def founder_dna(config: SimulationConfig) -> CompactDNA:
    """ADN fundador neutro (D32 y D46.5).

    Un codón `ALWAYS_BASAL` aditivo de carga 0 por cada rasgo 0x00-0x08 y, con la política
    genética, cuatro codones conductuales que reproducen a `HandwrittenPolicy`.
    """
    chromosome = tuple(encode_codon(0x00, t) for t in range(_FOUNDER_TRAITS))
    if config.enable_genetic_policy:
        chromosome += _FOUNDER_BEHAVIOR_CODONS
    return CompactDNA(chromosome=chromosome)


def founder_dna_length(config: SimulationConfig) -> int:
    """Longitud del cromosoma fundador: 13 con la política genética y 9 sin ella (D46.5)."""
    if config.enable_genetic_policy:
        return FOUNDER_DNA_LENGTH + len(_FOUNDER_BEHAVIOR_CODONS)
    return FOUNDER_DNA_LENGTH


def _promoter_active(promoter: int, context: EpigeneticContext, config: SimulationConfig) -> bool:
    """Promotores de la pasada 1 (menores que 0x80). Los reservados nunca se activan."""
    if promoter == 0x00:
        return True
    if promoter == _PROM_SOLITARY_L0:
        return context.holon_level == 0
    if promoter <= _PROM_IN_HOLON_LAST:  # 0x02-0x0A: IN_HOLON_Lk con k = promoter - 1
        return context.holon_level >= promoter - 1
    role = _ROLE_PROMOTERS.get(promoter)
    if role is not None:
        return context.role is role
    if promoter == _PROM_STRESS:
        return context.energy_ratio < config.stress_energy_ratio
    if promoter == _PROM_SURPLUS:
        return context.energy_ratio >= config.surplus_energy_ratio
    return False


def _trait_bounds(config: SimulationConfig) -> tuple[tuple[float, float], ...]:
    """Cotas `(lo, hi)` de los destinos de rasgo (D33, D46.7); las enteras, como `mutate_genome`."""
    capacity_hi, radius_hi = integer_trait_bounds(config)
    return (
        (0.01, 1.0),
        (0.0, 1.0),
        (0.0, 1.0),
        (0.0, 1.0),
        (1, capacity_hi),
        (1, radius_hi),
        (1, radius_hi),
        (config.telomere_min_lifespan, config.telomere_max_lifespan),
        (0.0, config.reproduction_threshold),
        (0.0, 1.0),
        (0.0, 1.0),
        (0.0, 1.0),
    )


def _trait_bases(config: SimulationConfig) -> tuple[float, ...]:
    return (
        config.alpha_learning,
        config.gamma_social_discount,
        config.epsilon_explore,
        config.initial_bond_affinity,
        config.memory_capacity,
        config.perception_radius,
        config.comm_radius,
        config.telomere_base_lifespan,
        config.spore_energy_threshold,
        config.symbiotic_commitment_base,
        config.recombination_base,
        config.comm_propensity_base,
    )


def _sensory_values(signals: SensorySignals) -> tuple[bool, ...]:
    """Valores de los promotores sensoriales `0x20`-`0x27` (D46.2), en el orden de los campos."""
    return (
        signals.known_good,
        signals.unknown,
        signals.no_resource,
        signals.neighbor_adjacent,
        signals.weaker_adjacent,
        signals.stronger_near,
        signals.crowded,
        signals.carcass,
    )


def _active_codons(
    codons: list[Codon],
    context: EpigeneticContext,
    config: SimulationConfig,
    sensors: tuple[bool, ...] | None,
) -> list[bool]:
    """Las dos pasadas de D33: qué codones están activos.

    Con `sensors=None` (transcripción del fenotipo) los promotores sensoriales están inactivos;
    con `sensors` (evaluación de impulsos, D46.2) se activan según el valor que leen.
    """
    # Pasada 1: promotores de contexto, sensoriales y factores de transcripción.
    active = [
        c.promoter < _PROM_TF_FIRST
        and (
            _promoter_active(c.promoter, context, config)
            or (
                sensors is not None
                and _PROM_SENSE_FIRST <= c.promoter <= _PROM_SENSE_LAST
                and sensors[c.promoter - _PROM_SENSE_FIRST]
            )
        )
        for c in codons
    ]
    act = [0] * 64
    rep = [0] * 64
    for codon, is_active in zip(codons, active, strict=True):
        if is_active and codon.target == _TARGET_EMIT_TF and codon.mode != _MODE_RESERVED:
            if codon.mode == _MODE_REPRESSOR:
                rep[codon.channel] += 1
            else:
                act[codon.channel] += 1
    # Pasada 2: codones regulados; sus EMIT_TF no encienden canales (un solo nivel).
    return [
        is_active
        or (
            _PROM_TF_FIRST <= codon.promoter <= _PROM_TF_LAST
            and act[codon.promoter - _PROM_TF_FIRST] > rep[codon.promoter - _PROM_TF_FIRST]
        )
        for codon, is_active in zip(codons, active, strict=True)
    ]


class _Accumulated(NamedTuple):
    """Acumulación de D33 por destino: suma aditiva, producto represor y multiplicativo."""

    additive: list[float]  # S
    repressor: list[float]  # rho
    multiplier: list[float]  # mu
    hits: list[int]  # codones activos acumulados (0 = destino sin codones)


def _accumulate(codons: list[Codon], active: list[bool], slots: dict[int, int]) -> _Accumulated:
    """Acumula en el orden de recorrido los codones activos de modo distinto de 3 por destino.

    `slots` asigna a cada destino su posición. Es la regla común de la transcripción del fenotipo
    y de la evaluación de impulsos (el bloque 14 agregará aquí el modo plástico).
    """
    n = len(slots)
    acc = _Accumulated([0.0] * n, [1.0] * n, [1.0] * n, [0] * n)
    for codon, is_active in zip(codons, active, strict=True):
        slot = slots.get(codon.target)
        if not is_active or slot is None or codon.mode == _MODE_RESERVED:
            continue
        acc.hits[slot] += 1
        if codon.mode == _MODE_ADDITIVE:
            acc.additive[slot] += codon.delta
        elif codon.mode == _MODE_REPRESSOR:
            acc.repressor[slot] *= 1.0 - abs(codon.delta)
        else:
            acc.multiplier[slot] *= 1.0 + codon.delta
    return acc


def transcribe_phenotype(
    dna: CompactDNA, context: EpigeneticContext, config: SimulationConfig
) -> ExpressedPhenotype:
    """Transcripción pura en dos pasadas del ADN al fenotipo expresado (D33).

    Recorre `chromosome + plasmids` en orden; `crispr_memory` no se transcribe. Las bases salen
    de `config`, que debe ser la configuración base de la población. Los promotores sensoriales y
    los destinos de conducta están inactivos aquí: sólo actúan en `evaluate_drives` (D46.2).
    """
    codons = [decode_codon(c) for c in dna.chromosome + dna.plasmids]
    active = _active_codons(codons, context, config, None)
    acc = _accumulate(codons, active, _TRAIT_SLOT)
    additive, repressor, multiplier = acc.additive, acc.repressor, acc.multiplier
    expressed = sum(acc.hits)
    bases = _trait_bases(config)
    bounds = _trait_bounds(config)
    values: list[float] = []
    for t in range(_TRAIT_COUNT):
        x = bases[t] * multiplier[t] + _SCALES[t] * repressor[t] * additive[t]
        lo, hi = bounds[t]
        if t in _INTEGER_SLOTS:  # rasgos enteros: floor(x + 0.5), no `round`
            values.append(min(int(hi), max(int(lo), math.floor(x + 0.5))))
        else:
            values.append(min(hi, max(lo, x)))
    genome = AgentGenome(
        alpha_learning=values[0],
        gamma_social_discount=values[1],
        epsilon_explore=values[2],
        bond_affinity=values[3],
        memory_capacity=int(values[4]),
        perception_radius=int(values[5]),
        comm_radius=int(values[6]),
    )
    return ExpressedPhenotype(
        genome=genome,
        lifespan=int(values[7]),
        spore_threshold=values[8],
        expressed_codons=expressed,
        symbiotic_commitment=values[9],
        recombination_propensity=values[10],
        comm_propensity=values[11],
    )


def evaluate_drives(
    dna: CompactDNA,
    context: EpigeneticContext,
    signals: SensorySignals,
    config: SimulationConfig,
) -> tuple[float, ...]:
    """Impulsos puros por conducta, en el orden de `Behavior` (D46.3).

    Repite las dos pasadas de la transcripción con los promotores sensoriales activos según
    `signals`. Para cada destino de conducta $B$, con sus codones activos de modo distinto de 3,
    el impulso es `d_B = mu_B * rho_B * S_B` (suma aditiva, producto represor y
    producto multiplicativo, acumulados en el orden de recorrido), sin cotas; vale 0.0 sin codones.
    """
    codons = [decode_codon(c) for c in dna.chromosome + dna.plasmids]
    active = _active_codons(codons, context, config, _sensory_values(signals))
    acc = _accumulate(codons, active, _BEHAVIOR_SLOT)
    return tuple(
        acc.multiplier[b] * acc.repressor[b] * acc.additive[b] if acc.hits[b] else 0.0
        for b in range(_BEHAVIOR_COUNT)
    )


def phenotype_from_genome(genome: AgentGenome, config: SimulationConfig) -> ExpressedPhenotype:
    """Fenotipo de un agente sin ADN: R28 y R29 operan sobre el genoma plano (D33.7)."""
    return ExpressedPhenotype(
        genome,
        config.telomere_base_lifespan,
        config.spore_energy_threshold,
        0,
        symbiotic_commitment=config.symbiotic_commitment_base,
        recombination_propensity=config.recombination_base,
        comm_propensity=config.comm_propensity_base,
    )


def _admit_plasmid(plasmids: list[int], codon: int, crispr_memory: tuple[int, ...]) -> bool:
    """Regla de admisión de plásmidos (D35, pasos 2 y 5): sin repetidos ni vetados por CRISPR.

    Agrega `codon` al final de `plasmids` y devuelve `True` si se admite.
    """
    if codon in plasmids or codon in crispr_memory:
        return False
    plasmids.append(codon)
    return True


def _mutate_codons(
    codons: tuple[int, ...], p_point: float, rng: np.random.Generator
) -> tuple[int, ...]:
    """Mutación puntual (D35, pasos 1 y 2): un `random(n)` y un bit sorteado por codón elegido."""
    if not codons:
        return codons
    u = rng.random(len(codons))
    mutated: list[int] = []
    for codon, ui in zip(codons, u, strict=True):
        if ui < p_point:
            codon ^= 1 << int(rng.integers(0, 32))  # `int(...)`: el tipo exige int de Python
        mutated.append(codon)
    return tuple(mutated)


def mutate_dna(
    dna: CompactDNA, config: SimulationConfig, rng: np.random.Generator, scale: float = 1.0
) -> CompactDNA:
    """Operadores de mutación del ADN al reproducirse (D35 y D37).

    Orden exacto de extracciones de `rng`: mutación puntual del cromosoma, mutación puntual de los
    plásmidos, duplicación, deleción y, sólo con `enable_plasmid_hgt`, escisión a plásmido. Los
    pasos 3 a 5 consumen siempre su `u`; el índice se extrae sólo si el operador se aplica.
    `crispr_memory` se hereda sin mutar.
    """
    if not (scale >= 0.0 and math.isfinite(scale)):
        raise ValueError(f"scale debe ser finito y no negativo, recibido {scale}")
    if config.mutation_rate == 0.0 and config.discrete_mutation_prob == 0.0:
        return dna  # puerta de R13: la ablación congela también el ADN, sin consumir `rng`
    p_point = min(1.0, scale * config.dna_point_mutation_rate)
    p_dup = min(1.0, scale * config.dna_duplication_rate)
    p_del = min(1.0, scale * config.dna_deletion_rate)
    p_exc = min(1.0, scale * config.dna_excision_rate)

    chromosome = list(_mutate_codons(dna.chromosome, p_point, rng))
    # Plásmidos mutados: se descartan los repetidos (queda el primero) y los vetados por CRISPR.
    plasmids: list[int] = []
    for codon in _mutate_codons(dna.plasmids, p_point, rng):
        _admit_plasmid(plasmids, codon, dna.crispr_memory)

    if float(rng.random()) < p_dup and len(chromosome) < config.dna_max_length:
        i = int(rng.integers(len(chromosome)))
        chromosome.insert(i + 1, chromosome[i])
    if float(rng.random()) < p_del and len(chromosome) > config.dna_min_length:
        del chromosome[int(rng.integers(len(chromosome)))]
    if config.enable_plasmid_hgt and float(rng.random()) < p_exc:
        codon = chromosome[int(rng.integers(len(chromosome)))]
        if _admit_plasmid(plasmids, codon, dna.crispr_memory) and (
            len(plasmids) > config.max_plasmids
        ):
            del plasmids[0]  # FIFO
    return CompactDNA(
        chromosome=tuple(chromosome),
        plasmids=tuple(plasmids),
        crispr_memory=dna.crispr_memory,
    )


def recombine_dna(
    parent: CompactDNA, partner: CompactDNA, a: int, b: int, config: SimulationConfig
) -> CompactDNA:
    """Cruce de un punto de los cromosomas (R38, D51.2); el sorteo de `a` y `b` lo hace el motor.

    El cromosoma es `parent[:a] + partner[b:]`, truncado al prefijo `[:dna_max_length]` (precisión
    28); si queda más corto que `dna_min_length`, se usa el del progenitor. Los plásmidos y
    `crispr_memory` son los del progenitor.
    """
    chromosome = (parent.chromosome[:a] + partner.chromosome[b:])[: config.dna_max_length]
    if len(chromosome) < config.dna_min_length:
        chromosome = parent.chromosome
    return CompactDNA(
        chromosome=chromosome, plasmids=parent.plasmids, crispr_memory=parent.crispr_memory
    )


def _base_promoter_expressible(promoter: int, holonic: bool, roles: bool, senses: bool) -> bool:
    """Promotor menor que 0x80 expresable en el protocolo (precisión 42).

    `senses` indica que el destino del codón es de conducta, de estado o de señal: sólo sobre
    ellos actúan los promotores sensoriales, de eventos, de estado y de señales percibidas.
    """
    if promoter in (0x00, _PROM_SOLITARY_L0, _PROM_STRESS, _PROM_SURPLUS):
        return True
    if 0x02 <= promoter <= _PROM_IN_HOLON_LAST:
        return holonic
    if 0x10 <= promoter <= 0x12:
        return holonic and roles
    return senses and (0x20 <= promoter <= 0x2B or 0x30 <= promoter <= 0x3F)


def _base_promoter_constitutive(promoter: int, holonic: bool) -> bool:
    return promoter == 0x00 or (promoter == _PROM_SOLITARY_L0 and not holonic)


def expressible_codons(dna: CompactDNA, holonic: bool, roles: bool) -> tuple[tuple[int, bool], ...]:
    """Valores canónicos distintos de los codones funcionales expresables (precisión 42).

    Depende sólo del genotipo y del protocolo (`holonic` = holones activos, `roles` = roles
    epigenéticos activos). Cada valor, en orden ascendente, va con si su promotor es condicional.
    Un codón funcional tiene destino funcional (D61), modo distinto de 3 y promotor expresable;
    cuentan `chromosome + plasmids`, nunca `crispr_memory`. Los regulados `0x80`-`0xBF` son
    expresables si su canal tiene un emisor activador (`EMIT_TF` de modo 0 o 2) con promotor
    expresable menor que 0x80, y constitutivos si alguno de esos emisores lo es: aproximación
    declarada que no considera represores. El valor canónico enmascara `channel` sólo en los
    destinos de rasgo y de conducta, donde no tiene efecto. No recibe las banderas de $R_{39}$ a
    $R_{41}$ (límite declarado, precisión 60).
    """
    codons = [decode_codon(c) for c in dna.chromosome + dna.plasmids]
    emitters: dict[int, list[int]] = {}
    for codon in codons:
        if (
            codon.target == _TARGET_EMIT_TF
            and codon.mode in (_MODE_ADDITIVE, _MODE_MULTIPLICATIVE)
            and codon.promoter < _PROM_TF_FIRST
        ):
            emitters.setdefault(codon.channel, []).append(codon.promoter)
    found: dict[int, bool] = {}
    for raw, codon in zip(dna.chromosome + dna.plasmids, codons, strict=True):
        if codon.target not in _FUNCTIONAL_TARGETS or codon.mode == _MODE_RESERVED:
            continue
        senses = codon.target in _SENSING_TARGETS
        if codon.promoter < _PROM_TF_FIRST:
            if not _base_promoter_expressible(codon.promoter, holonic, roles, senses):
                continue
            conditional = not _base_promoter_constitutive(codon.promoter, holonic)
        elif codon.promoter <= _PROM_TF_LAST:
            sources = [
                p
                for p in emitters.get(codon.promoter - _PROM_TF_FIRST, ())
                if _base_promoter_expressible(p, holonic, roles, senses)
            ]
            if not sources:
                continue
            conditional = not any(_base_promoter_constitutive(p, holonic) for p in sources)
        else:
            continue
        value = raw & ~_CHANNEL_MASK if codon.target in _CHANNEL_FREE_TARGETS else raw
        found[value] = conditional
    return tuple((value, found[value]) for value in sorted(found))
