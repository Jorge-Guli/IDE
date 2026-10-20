"""ADN compacto de codones de 32 bits y su transcripción en dos pasadas (R24, D32 y D33).

Módulo puro: sólo conoce `ide.domain`, `ide.config` y la biblioteca estándar (los codones son
`int` de Python, no `numpy.uint32`, D32). No importa
`micro_agent`, `holon`, `environments`, `simulation` ni `experiments`, y no ve coordenadas ni
`true_value`.
"""

import math
from typing import NamedTuple

from ide.config import FOUNDER_DNA_LENGTH, SimulationConfig
from ide.domain.extensions import integer_trait_bounds
from ide.domain.types import (
    AgentGenome,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    ExpressedPhenotype,
)

__all__ = [
    "FOUNDER_DNA_LENGTH",
    "Codon",
    "decode_codon",
    "encode_codon",
    "founder_dna",
    "phenotype_from_genome",
    "transcribe_phenotype",
]

# Modos del codón (D32).
_MODE_ADDITIVE = 0
_MODE_REPRESSOR = 1
_MODE_MULTIPLICATIVE = 2
_MODE_RESERVED = 3

# Destinos (D32): 0x00-0x08 modulan un rasgo; 0x09 emite un canal.
_TRAIT_COUNT = 9
_TARGET_EMIT_TF = 0x09

# Promotores (D32).
_PROM_SOLITARY_L0 = 0x01
_PROM_IN_HOLON_LAST = 0x0A
_PROM_ROLE_EXPLORER = 0x10
_PROM_ROLE_LIBRARIAN = 0x11
_PROM_ROLE_NERVE = 0x12
_PROM_STRESS = 0x18
_PROM_SURPLUS = 0x19
_PROM_TF_FIRST = 0x80
_PROM_TF_LAST = 0xBF

# Escalas k de los destinos 0x00-0x08 (D32).
_SCALES = (0.40, 0.40, 0.35, 0.50, 3.0, 2.0, 2.0, 250.0, 0.50)

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


def founder_dna(config: SimulationConfig) -> CompactDNA:
    """ADN fundador neutro: un codón `ALWAYS_BASAL` aditivo de carga 0 por cada rasgo (D32)."""
    del config  # el fundador no depende de la configuración; se conserva la firma de D32
    return CompactDNA(chromosome=tuple(encode_codon(0x00, t) for t in range(_TRAIT_COUNT)))


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
    """Cotas `(lo, hi)` de los destinos 0x00-0x08 (D33); las enteras, como en `mutate_genome`."""
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
    )


def transcribe_phenotype(
    dna: CompactDNA, context: EpigeneticContext, config: SimulationConfig
) -> ExpressedPhenotype:
    """Transcripción pura en dos pasadas del ADN al fenotipo expresado (D33).

    Recorre `chromosome + plasmids` en orden; `crispr_memory` no se transcribe. Las bases salen
    de `config`, que debe ser la configuración base de la población.
    """
    codons = [decode_codon(c) for c in dna.chromosome + dna.plasmids]
    # Pasada 1: promotores de contexto y factores de transcripción.
    active = [
        c.promoter < _PROM_TF_FIRST and _promoter_active(c.promoter, context, config)
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
    active = [
        is_active
        or (
            _PROM_TF_FIRST <= codon.promoter <= _PROM_TF_LAST
            and act[codon.promoter - _PROM_TF_FIRST] > rep[codon.promoter - _PROM_TF_FIRST]
        )
        for codon, is_active in zip(codons, active, strict=True)
    ]
    # Expresión de cada rasgo, acumulando en el orden de recorrido.
    additive = [0.0] * _TRAIT_COUNT
    repressor = [1.0] * _TRAIT_COUNT
    multiplier = [1.0] * _TRAIT_COUNT
    expressed = 0
    for codon, is_active in zip(codons, active, strict=True):
        if not is_active or codon.target >= _TRAIT_COUNT or codon.mode == _MODE_RESERVED:
            continue
        expressed += 1
        if codon.mode == _MODE_ADDITIVE:
            additive[codon.target] += codon.delta
        elif codon.mode == _MODE_REPRESSOR:
            repressor[codon.target] *= 1.0 - abs(codon.delta)
        else:
            multiplier[codon.target] *= 1.0 + codon.delta
    bases = _trait_bases(config)
    bounds = _trait_bounds(config)
    values: list[float] = []
    for t in range(_TRAIT_COUNT):
        x = bases[t] * multiplier[t] + _SCALES[t] * repressor[t] * additive[t]
        lo, hi = bounds[t]
        if 4 <= t <= 7:  # rasgos enteros: floor(x + 0.5), no `round`
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
    )


def phenotype_from_genome(genome: AgentGenome, config: SimulationConfig) -> ExpressedPhenotype:
    """Fenotipo de un agente sin ADN: R28 y R29 operan sobre el genoma plano (D33.7)."""
    return ExpressedPhenotype(
        genome, config.telomere_base_lifespan, config.spore_energy_threshold, 0
    )
