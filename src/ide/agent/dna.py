"""ADN compacto de codones de 32 bits, su transcripción en dos pasadas y la conducta (R24, R32).

Cubre D32 y D33 (codón y fenotipo), D46 (conducta en el ADN: promotores sensoriales, impulsos y
fundador conductual), D58 y D60.1 (evaluación de conducta con eventos y estado interno, R39),
D59 (modo plástico y tasa de plasticidad, R40), D51.2 (recombinación), la precisión 42 (codones
expresables) y las consultas por genotipo de la telemetría (precisiones 43 y 52, D53.2).

Módulo puro: sólo conoce `ide.domain`, `ide.config`, `numpy` (sólo para tipar el generador) y la
biblioteca estándar (los codones son `int` de Python, no `numpy.uint32`, D32). No importa
`micro_agent`, `holon`, `environments`, `simulation` ni `experiments`, y no ve coordenadas ni
`true_value`.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np

from ide.config import (
    FOUNDER_DNA_LENGTH,
    SimulationConfig,
    genetic_policy_active,
    is_stress_energy_ratio,
)
from ide.domain.extensions import integer_trait_bounds
from ide.domain.types import (
    AgentGenome,
    Behavior,
    BehaviorEvaluation,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    ExpressedPhenotype,
    SensorySignals,
)

__all__ = [
    "BEHAVIORS",
    "BEHAVIOR_TARGETS",
    "FOUNDER_DNA_LENGTH",
    "BehaviorTerms",
    "Codon",
    "CodonCensus",
    "apply_plastic_weights",
    "behavior_terms",
    "canonical_codon",
    "codon_census",
    "crispr_immunity_active",
    "decode_codon",
    "encode_codon",
    "evaluate_behavior",
    "evaluate_drives",
    "expressible_codons",
    "founder_dna",
    "founder_dna_length",
    "functional_codon_values",
    "internal_state_active",
    "is_functional_codon",
    "learning_codons",
    "mutate_dna",
    "phenotype_from_genome",
    "plasmid_hgt_active",
    "plasticity_active",
    "purge_plasmid",
    "receive_plasmid",
    "recombine_dna",
    "trait_or_behavior_codons",
    "transcribe_phenotype",
]

# Modos del codón (D32, D61). El modo 3 es plástico (D59.1): sólo actúa en la evaluación de
# conducta, sobre los destinos de conducta y con R40; en el fenotipo y en los demás destinos es
# inerte. La reserva de la Fase IV (`AST_PIPE`) es el destino reservado 0x3F, inerte.
_MODE_ADDITIVE = 0
_MODE_REPRESSOR = 1
_MODE_MULTIPLICATIVE = 2
_MODE_PLASTIC = 3

# Destinos (D32, D46.7, D59.3): 0x00-0x08, 0x0A-0x0C y 0x0F modulan un rasgo; 0x09 emite un canal.
_FOUNDER_TRAITS = 9  # un codón fundador por cada rasgo 0x00-0x08
_TARGET_EMIT_TF = 0x09
_TARGET_PLASTICITY_RATE = 0x0F
_TRAIT_TARGETS = (*range(0x00, 0x09), 0x0A, 0x0B, 0x0C, _TARGET_PLASTICITY_RATE)
_TRAIT_SLOT = {target: slot for slot, target in enumerate(_TRAIT_TARGETS)}
_TRAIT_COUNT = len(_TRAIT_TARGETS)
_INTEGER_SLOTS = range(4, 8)  # memory_capacity, perception_radius, comm_radius, lifespan

# Conductas (D46.1): el orden de la tabla, que es el de desempate y el de las posiciones de
# `drives` y `plastic`; única fuente de ese orden para la política y el agente.
BEHAVIORS: tuple[Behavior, ...] = tuple(Behavior)
# Un destino por `Behavior`, en el orden del enumerado.
BEHAVIOR_TARGETS = (0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47)
assert len(BEHAVIOR_TARGETS) == len(Behavior), "BEHAVIOR_TARGETS debe tener un destino por Behavior"
_BEHAVIOR_SLOT = {target: slot for slot, target in enumerate(BEHAVIOR_TARGETS)}
# Destino de `ATTACK` (D46.1): inerte en `no_predation` (precisión 42).
_ATTACK_TARGET = BEHAVIOR_TARGETS[BEHAVIORS.index(Behavior.ATTACK)]
_BEHAVIOR_COUNT = len(Behavior)

# Destinos de otras decisiones (D61): `0x0D`/`0x0E` estado interno (R39, D58.2) y `0x48` señal.
_TARGET_SET_STATE = 0x0D
_TARGET_CLEAR_STATE = 0x0E
_TARGET_SIGNAL = 0x48
_SENSING_TARGETS = frozenset(
    (_TARGET_SET_STATE, _TARGET_CLEAR_STATE, _TARGET_SIGNAL, *BEHAVIOR_TARGETS)
)
_FUNCTIONAL_TARGETS = _SENSING_TARGETS | set(_TRAIT_TARGETS)  # incluye 0x0F (precisión 54)
_CHANNEL_MASK = 0x3F00  # bits 8-13 del codón
# Destinos donde `channel` no tiene efecto (D61); en estado y señal elige un bit y no se enmascara.
_CHANNEL_FREE_TARGETS = frozenset((*_TRAIT_TARGETS, *BEHAVIOR_TARGETS))

# Promotores (D32).
_PROM_SOLITARY_L0 = 0x01
_PROM_IN_HOLON_LAST = 0x0A
_PROM_ROLE_EXPLORER = 0x10
_PROM_ROLE_LIBRARIAN = 0x11
_PROM_ROLE_NERVE = 0x12
_PROM_STRESS = 0x18
_PROM_SURPLUS = 0x19
# Promotores de la evaluación de conducta (D46.2, D58.4, D58.5, D60.4, D61), inactivos en el
# fenotipo: sensoriales 0x20-0x27, eventos del tick anterior 0x28-0x2B, reservados 0x2C-0x2F,
# estado interno 0x30-0x37 (`STATE_k`) y señales percibidas 0x38-0x3F (`HEARD_k`).
_PROM_SENSE_FIRST = 0x20
_PROM_SENSE_LAST = 0x3F
_PROM_STATE_FIRST = 0x30  # `STATE_0`; `STATE_k` es `0x30 + k` (D58.4)
_PROM_STATE_LAST = 0x37
_PROM_HEARD_FIRST = 0x38  # `HEARD_0`; `HEARD_k` es `0x38 + k` (D60.4)
_STATE_BITS = 8  # `internal_state` tiene 8 bits (D58.1)
_SYMBOL_BITS = 8  # ocho símbolos de señal, `channel & 0x07` (D60.2)
SYMBOL_MASK = (1 << _SYMBOL_BITS) - 1  # cota de la máscara de símbolos (precisión 105)
_NO_PLASTIC: tuple[tuple[int, ...], ...] = ((),) * len(Behavior)
_PROM_TF_FIRST = 0x80
_PROM_TF_LAST = 0xBF

# Escalas k de los destinos de rasgo (D32 y D46.7), en el orden de `_TRAIT_TARGETS`.
_SCALES = (0.40, 0.40, 0.35, 0.50, 3.0, 2.0, 2.0, 250.0, 0.50, 0.60, 0.60, 0.60, 0.60)

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
        return is_stress_energy_ratio(context.energy_ratio, config)  # precisión 93
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
        config.plasticity_rate_base,
    )


def internal_state_active(config: SimulationConfig) -> bool:
    """$R_{39}$ efectivamente activa: `enable_internal_state` con $R_{32}$ efectiva (D57.3).

    $R_{32}$ efectiva es `genetic_policy_active` de `ide.config` (precisión 31). Sin ella, los
    destinos `0x0D`/`0x0E` y los promotores `0x30`-`0x37` son inertes (D58.7).
    """
    return genetic_policy_active(config) and config.enable_internal_state


def plasticity_active(config: SimulationConfig) -> bool:
    """$R_{40}$ efectivamente activa: `enable_evolution`, $R_{32}$ efectiva y `enable_plasticity`.

    Es la única definición (D57.3, D59.6, precisión 95). Exige la evolución explícitamente, como
    $R_{36}$ y $R_{37}$ (precisión 83): sin ella la energía no cambia en la Fase 4 y la regla
    sería inerte en silencio (hoy la validación del ADN ya la exige). Sin la condición, el modo 3
    es inerte también en la conducta y los pesos no se actualizan.
    """
    return config.enable_evolution and genetic_policy_active(config) and config.enable_plasticity


def signals_active(config: SimulationConfig) -> bool:
    """$R_{41}$ efectivamente activa: `enable_signals` con $R_{32}$ efectiva (D57.3, D60.7).

    Es la única definición: la usan la evaluación de conducta y `build_systems`. Sin ella, el
    destino `0x48` y los promotores `0x38`-`0x3F` son inertes y no hay emisión ni costo.
    """
    return genetic_policy_active(config) and config.enable_signals


def plasmid_hgt_active(config: SimulationConfig) -> bool:
    """$R_{26}$ efectivamente activa: `enable_plasmid_hgt` con ADN (D30.3, D37).

    Es la única definición de la condición de la conjugación: la usan `build_systems` (que agrega
    `ConjugationSystem`), `crispr_immunity_active` y la escisión de `mutate_dna`; el motor no la
    guarda. Exige la evolución explícitamente, como $R_{36}$ y $R_{37}$ (precisión 83), aunque la
    validación del ADN ya la exige. Sin ella, `hgt_rng` no se consume (D30.4).
    """
    return config.enable_evolution and config.enable_compact_dna and config.enable_plasmid_hgt


def crispr_immunity_active(config: SimulationConfig) -> bool:
    """$R_{27}$ efectivamente activa: `enable_crispr_immunity` con $R_{26}$ efectiva (D30.3, D37).

    Es la única definición de la condición del ensayo CRISPR: la usan `build_systems` y el motor,
    que la guarda en `engine.crispr_immunity_active`. Sin $R_{26}$ no llegan plásmidos por
    conjugación, no se abren ensayos y la bandera es inerte.
    """
    return plasmid_hgt_active(config) and config.enable_crispr_immunity


def heard_symbols(dna: CompactDNA) -> int:
    """Máscara de los símbolos que el ADN puede oír: el bit $k$ vale 1 si algún codón de
    `chromosome + plasmids` tiene el promotor `HEARD_k` (`0x38 + k`).

    La evaluación de conducta sólo depende de `perceived` a través de esos promotores, así que
    `perceived & heard_symbols(dna)` da la misma evaluación que `perceived` (precisión 105). Pura,
    sin generador.
    """
    mask = 0
    for codon in dna.chromosome + dna.plasmids:
        promoter = decode_codon(codon).promoter
        if _PROM_HEARD_FIRST <= promoter < _PROM_HEARD_FIRST + _SYMBOL_BITS:
            mask |= 1 << (promoter - _PROM_HEARD_FIRST)
    return mask


def _bits(mask: int, count: int) -> tuple[bool, ...]:
    """Los `count` bits menos significativos de `mask`, del 0 en adelante."""
    return tuple(bool(mask >> k & 1) for k in range(count))


def _behavior_promoters(
    signals: SensorySignals, state: int | None, perceived: int | None
) -> tuple[bool, ...]:
    """Valores de los promotores `0x20`-`0x3F` en la evaluación de conducta, en orden.

    - `0x20`-`0x27`: los ocho campos sensoriales de `SensorySignals` (D46.2);
    - `0x28`-`0x2B`: los cuatro eventos del tick anterior (D58.5), también sin $R_{39}$ (D58.7);
    - `0x2C`-`0x2F`: reservados, siempre inactivos (D61);
    - `0x30`-`0x37`: los bits de `state`; `state=None` (sin $R_{39}$) los deja inactivos (D58.4);
    - `0x38`-`0x3F`: los bits de `perceived`, la máscara de símbolos percibidos;
      `perceived=None` (sin $R_{41}$) los deja inactivos (D60.4, D60.7).
    """
    state_bits = (False,) * _STATE_BITS if state is None else _bits(state, _STATE_BITS)
    heard_bits = (False,) * _SYMBOL_BITS if perceived is None else _bits(perceived, _SYMBOL_BITS)
    return (
        signals.known_good,
        signals.unknown,
        signals.no_resource,
        signals.neighbor_adjacent,
        signals.weaker_adjacent,
        signals.stronger_near,
        signals.crowded,
        signals.carcass,
        signals.attacked,
        signals.ate,
        signals.lost_energy,
        signals.received_energy,
        *(False,) * 4,
        *state_bits,
        *heard_bits,
    )


def _active_codons(
    codons: list[Codon],
    context: EpigeneticContext,
    config: SimulationConfig,
    sensors: tuple[bool, ...] | None,
) -> list[bool]:
    """Las dos pasadas de D33: qué codones están activos.

    Con `sensors=None` (transcripción del fenotipo) los promotores `0x20`-`0x3F` están inactivos;
    con `sensors` (evaluación de conducta, D46.2 y D58.6) se activan según el valor que leen,
    uno por promotor en ese rango (`_behavior_promoters`).
    """
    # Pasada 1: promotores de contexto, de conducta y factores de transcripción.
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
        if is_active and codon.target == _TARGET_EMIT_TF and codon.mode != _MODE_PLASTIC:
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

    additive: list[float]  # S (con la carga de los codones plásticos, sin sus pesos)
    repressor: list[float]  # rho
    multiplier: list[float]  # mu
    hits: list[int]  # codones activos acumulados (0 = destino sin codones)
    plastic: list[list[int]]  # posiciones de los codones plásticos activos, ascendentes


def _accumulate(
    codons: list[Codon], active: list[bool], slots: dict[int, int], plastic: bool = False
) -> _Accumulated:
    """Acumula en el orden de recorrido los codones activos de cada destino.

    `slots` asigna a cada destino su posición. Es la regla común de la transcripción del fenotipo
    y de la evaluación de conducta. El modo 3 se ignora, salvo con `plastic` (evaluación de
    conducta con $R_{40}$ efectivamente activa, D59.1): entonces su carga $\\delta$ suma a $S$
    como un aditivo y su posición en `chromosome + plasmids` queda en `plastic`; el peso
    aprendido se suma después (`apply_plastic_weights`, precisión 57).
    """
    n = len(slots)
    acc = _Accumulated([0.0] * n, [1.0] * n, [1.0] * n, [0] * n, [[] for _ in range(n)])
    for index, (codon, is_active) in enumerate(zip(codons, active, strict=True)):
        slot = slots.get(codon.target)
        if not is_active or slot is None:
            continue
        if codon.mode == _MODE_PLASTIC:
            if not plastic:
                continue
            acc.plastic[slot].append(index)
            acc.hits[slot] += 1
            acc.additive[slot] += codon.delta
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
    los destinos de conducta están inactivos aquí: sólo actúan en `evaluate_behavior` (D46.2), y
    el modo 3 es inerte (D59.1).
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
        plasticity_rate=values[12],
    )


def _majority_mask(codons: list[Codon], active: list[bool], target: int) -> int:
    """Máscara de 8 bits por la regla de canales de D33.2 sobre los codones activos de `target`.

    El bit `channel & 0x07` vale 1 si sus codones de modo 0 o 2 superan en número a los de modo
    1; el modo 3 y `payload` no cuentan. Es la regla del estado interno (D58.2, D58.3) y de la
    emisión de señales (D60.3).
    """
    act = [0] * _STATE_BITS
    rep = [0] * _STATE_BITS
    for codon, is_active in zip(codons, active, strict=True):
        if not is_active or codon.target != target or codon.mode == _MODE_PLASTIC:
            continue
        if codon.mode == _MODE_REPRESSOR:
            rep[codon.channel & 0x07] += 1
        else:
            act[codon.channel & 0x07] += 1
    return sum(1 << k for k in range(_STATE_BITS) if act[k] > rep[k])


@dataclass(frozen=True)
class BehaviorTerms:
    """Evaluación de conducta sin los pesos aprendidos (D59.5, precisión 57).

    Es lo que guarda el caché único de la evaluación del agente (precisión 88): por conducta,
    $S_B$ sin los pesos (con la carga de sus codones plásticos), $\\mu_B$ y $\\rho_B$, y los
    índices de sus codones plásticos activos (`base.plastic`). `base` es la evaluación con todos
    los pesos en 0. `apply_plastic_weights` suma los pesos vigentes. Sin codones plásticos
    activos, los pesos no tienen efecto y las tres tuplas quedan vacías.
    """

    base: BehaviorEvaluation
    additive: tuple[float, ...] = ()  # S_B sin los pesos
    repressor: tuple[float, ...] = ()  # rho_B
    multiplier: tuple[float, ...] = ()  # mu_B

    def __post_init__(self) -> None:
        """Las tuplas son vacías si y sólo si `base.plastic` no tiene codones plásticos."""
        plastic = any(self.base.plastic)
        sizes = {len(self.additive), len(self.repressor), len(self.multiplier)}
        if sizes != ({_BEHAVIOR_COUNT} if plastic else {0}):
            raise ValueError(
                "BehaviorTerms exige S, rho y mu por conducta si y sólo si hay codones plásticos"
            )


def behavior_terms(
    dna: CompactDNA,
    context: EpigeneticContext,
    signals: SensorySignals,
    config: SimulationConfig,
    state: int = 0,
    perceived: int = 0,
) -> BehaviorTerms:
    """Parte de `evaluate_behavior` que no depende de los pesos aprendidos (precisión 57).

    Repite las dos pasadas de la transcripción sobre `chromosome + plasmids`, con los promotores
    `0x20`-`0x3F` activos según `signals`, `state` y `perceived` (`_behavior_promoters`), y
    acumula por conducta los codones activos de modo distinto de 3 y, con $R_{40}$
    efectivamente activa, los de modo 3 (D59.1). Con $R_{41}$ efectivamente activa, la máscara
    `emitted` sale de la regla de mayoría por símbolo sobre `SIGNAL` (D60.3). Sin generador.
    """
    stateful = internal_state_active(config)
    signaling = signals_active(config)
    codons = [decode_codon(c) for c in dna.chromosome + dna.plasmids]
    promoters = _behavior_promoters(
        signals, state if stateful else None, perceived if signaling else None
    )
    active = _active_codons(codons, context, config, promoters)
    acc = _accumulate(codons, active, _BEHAVIOR_SLOT, plasticity_active(config))
    drives = tuple(
        acc.multiplier[b] * acc.repressor[b] * acc.additive[b] if acc.hits[b] else 0.0
        for b in range(_BEHAVIOR_COUNT)
    )
    if stateful:
        set_mask = _majority_mask(codons, active, _TARGET_SET_STATE)
        clear_mask = _majority_mask(codons, active, _TARGET_CLEAR_STATE)
    else:
        set_mask = clear_mask = 0
    emitted = _majority_mask(codons, active, _TARGET_SIGNAL) if signaling else 0
    if not any(acc.plastic):
        return BehaviorTerms(BehaviorEvaluation(drives, set_mask, clear_mask, emitted, _NO_PLASTIC))
    plastic = tuple(tuple(indices) for indices in acc.plastic)
    return BehaviorTerms(
        BehaviorEvaluation(drives, set_mask, clear_mask, emitted, plastic),
        tuple(acc.additive),
        tuple(acc.repressor),
        tuple(acc.multiplier),
    )


def apply_plastic_weights(
    terms: BehaviorTerms, plastic_weights: Mapping[int, float] | None
) -> BehaviorEvaluation:
    """Suma los pesos aprendidos a `terms` (D59.1, precisión 57).

    Para cada conducta $B$ con codones plásticos activos, $d_B = \\mu_B \\cdot \\rho_B \\cdot
    (S_B + \\sum_i w_i)$, con $w_i$ = `plastic_weights.get(i, 0.0)` sumados a $S_B$ en orden
    ascendente de posición. Sin codones plásticos o sin pesos devuelve `terms.base`, que es
    idéntica: sumar 0.0 a $S_B$ no la cambia. Las demás conductas conservan su impulso.
    """
    base = terms.base
    if not plastic_weights or not terms.additive:  # sin pesos o sin codones plásticos
        return base
    drives = list(base.drives)
    for b, indices in enumerate(base.plastic):
        if not indices:
            continue
        total = terms.additive[b]
        for index in indices:
            total += plastic_weights.get(index, 0.0)
        drives[b] = terms.multiplier[b] * terms.repressor[b] * total
    return BehaviorEvaluation(
        tuple(drives), base.set_mask, base.clear_mask, base.emitted, base.plastic
    )


def evaluate_behavior(
    dna: CompactDNA,
    context: EpigeneticContext,
    signals: SensorySignals,
    config: SimulationConfig,
    state: int = 0,
    perceived: int = 0,
    plastic_weights: Mapping[int, float] | None = None,
) -> BehaviorEvaluation:
    """Evaluación pura de la conducta del tick (D60.1), sin generador.

    Es `apply_plastic_weights(behavior_terms(...), plastic_weights)`, y devuelve:
    - `drives`: para cada destino de conducta $B$, $d_B = \\mu_B \\cdot \\rho_B \\cdot (S_B +
      \\sum_i w_i)$ sobre sus codones activos, acumulado en el orden de recorrido y sin cotas;
      0.0 sin codones (D46.3). Con $R_{40}$ efectivamente activa, un codón activo de modo 3 en la
      posición $i$ de `chromosome + plasmids` suma su carga a $S_B$ y su peso
      $w_i$ = `plastic_weights.get(i, 0.0)` después (D59.1, precisión 57); sin ella es inerte;
    - `set_mask` y `clear_mask`: la regla de mayoría por bit sobre `SET_STATE` (`0x0D`) y
      `CLEAR_STATE` (`0x0E`), sólo con $R_{39}$ efectivamente activa; si no, 0 (D58.3, D58.7).
      El estado siguiente lo aplica el motor al terminar la Fase 3;
    - `plastic`: por conducta, las posiciones ascendentes de sus codones de modo 3 activos, con
      $R_{40}$ efectivamente activa (D59.4); si no, ocho tuplas vacías;
    - `emitted`: la máscara de símbolos emitidos, por la regla de mayoría por símbolo sobre
      `SIGNAL` (`0x48`, símbolo `channel & 0x07`), sólo con $R_{41}$ efectivamente activa; si
      no, 0 (D60.3, D60.7). `SIGNAL` no es una conducta: no tiene impulso. Con $R_{41}$, los
      promotores `HEARD_k` (`0x38`-`0x3F`) leen el bit $k$ de `perceived` (D60.4).
    """
    terms = behavior_terms(dna, context, signals, config, state, perceived)
    return apply_plastic_weights(terms, plastic_weights)


def evaluate_drives(
    dna: CompactDNA,
    context: EpigeneticContext,
    signals: SensorySignals,
    config: SimulationConfig,
) -> tuple[float, ...]:
    """Impulsos por conducta, en el orden de `Behavior` (D46.3): envoltorio de D60.1.

    Devuelve exactamente `evaluate_behavior(dna, context, signals, config).drives`, con
    `state=0`, `perceived=0` y sin pesos aprendidos.
    """
    return evaluate_behavior(dna, context, signals, config).drives


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
        plasticity_rate=config.plasticity_rate_base,
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
    plásmidos, duplicación, deleción y, sólo con $R_{26}$ efectiva (`plasmid_hgt_active`),
    escisión a plásmido. Los pasos 3 a 5 consumen siempre su `u`; el índice se extrae sólo si el
    operador se aplica.
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
    if plasmid_hgt_active(config) and float(rng.random()) < p_exc:
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


def receive_plasmid(dna: CompactDNA, codon: int, config: SimulationConfig) -> CompactDNA | None:
    """Recepción de un plásmido por conjugación (R26 y R27, design D37), pura.

    Devuelve `None` si $R_{27}$ está efectivamente activa (`crispr_immunity_active`) y `codon`
    está en `crispr_memory`: la transferencia se bloquea. Devuelve el mismo `dna` (la misma
    instancia) si `codon` ya está en `plasmids`. Si no, devuelve un ADN con `codon` al final de
    `plasmids`, descartando el primero si se supera `max_plasmids` (FIFO).
    """
    if crispr_immunity_active(config) and codon in dna.crispr_memory:
        return None
    if codon in dna.plasmids:
        return dna
    plasmids = (*dna.plasmids, codon)
    if len(plasmids) > config.max_plasmids:
        plasmids = plasmids[len(plasmids) - config.max_plasmids :]  # FIFO
    return CompactDNA(chromosome=dna.chromosome, plasmids=plasmids, crispr_memory=dna.crispr_memory)


def purge_plasmid(dna: CompactDNA, codon: int, config: SimulationConfig) -> CompactDNA:
    """Purga CRISPR de un plásmido (R27, design D37), pura.

    Quita `codon` de `plasmids` y lo agrega al final de `crispr_memory`, descartando la firma
    más antigua si se supera `crispr_memory_size` (FIFO).

    Raises:
        ValueError: si `codon` no está en `plasmids`: el motor sólo purga un plásmido presente.
    """
    if codon not in dna.plasmids:
        raise ValueError(f"purge_plasmid: el codón {codon} no está en plasmids")
    plasmids = tuple(c for c in dna.plasmids if c != codon)
    memory = (*(c for c in dna.crispr_memory if c != codon), codon)
    if len(memory) > config.crispr_memory_size:
        memory = memory[len(memory) - config.crispr_memory_size :]  # FIFO
    return CompactDNA(chromosome=dna.chromosome, plasmids=plasmids, crispr_memory=memory)


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


def canonical_codon(codon: int) -> int:
    """Valor canónico de un codón (precisión 42, D61): `codon & ~0x3F00` en los destinos de rasgo
    y de conducta, donde `channel` no tiene efecto; el codón intacto en los demás destinos, donde
    `channel` elige un bit, un símbolo o un canal."""
    target = (codon >> 16) & 0xFF
    return codon & ~_CHANNEL_MASK if target in _CHANNEL_FREE_TARGETS else codon


def _expressible_entries(
    raws: tuple[int, ...], codons: list[Codon], holonic: bool, roles: bool
) -> list[tuple[int, Codon, bool]]:
    """Codones de destino funcional (D61) con promotor expresable en el protocolo, de cualquier
    modo, en el orden de `chromosome + plasmids` (`raws`, ya decodificados en `codons`):
    `(codón, decodificado, condicional)`.

    Es la regla de expresabilidad de la precisión 42 (ampliada por la 59), que comparten
    `expressible_codons` (sin el modo 3), `learning_codons` (con él, precisión 52) y
    `codon_census`.
    """
    emitters: dict[int, list[int]] = {}
    for codon in codons:
        if (
            codon.target == _TARGET_EMIT_TF
            and codon.mode in (_MODE_ADDITIVE, _MODE_MULTIPLICATIVE)
            and codon.promoter < _PROM_TF_FIRST
        ):
            emitters.setdefault(codon.channel, []).append(codon.promoter)
    entries: list[tuple[int, Codon, bool]] = []
    for raw, codon in zip(raws, codons, strict=True):
        if codon.target not in _FUNCTIONAL_TARGETS:
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
        entries.append((raw, codon, conditional))
    return entries


def _decoded(dna: CompactDNA) -> tuple[tuple[int, ...], list[Codon]]:
    """`chromosome + plasmids` y sus codones decodificados, una sola vez."""
    raws = dna.chromosome + dna.plasmids
    return raws, [decode_codon(c) for c in raws]


def _expressible_values(entries: list[tuple[int, Codon, bool]]) -> dict[int, bool]:
    """Valor canónico -> condicional de las entradas expresables de modo distinto de 3."""
    found: dict[int, bool] = {}
    for raw, codon, conditional in entries:
        if codon.mode != _MODE_PLASTIC:
            found[canonical_codon(raw)] = conditional
    return found


def _learning_values(entries: list[tuple[int, Codon, bool]], plastic: bool) -> set[int]:
    """Valores canónicos de memoria y aprendizaje de las entradas expresables (precisión 52)."""
    found: set[int] = set()
    for raw, codon, _ in entries:
        target, mode = codon.target, codon.mode
        if (
            (target in (_TARGET_SET_STATE, _TARGET_CLEAR_STATE) and mode != _MODE_PLASTIC)
            or (_PROM_STATE_FIRST <= codon.promoter <= _PROM_STATE_LAST)
            or (plastic and mode == _MODE_PLASTIC and target in _BEHAVIOR_SLOT)
        ):
            found.add(canonical_codon(raw))
    return found


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
    found = _expressible_values(_expressible_entries(*_decoded(dna), holonic, roles))
    return tuple((value, found[value]) for value in sorted(found))


def learning_codons(dna: CompactDNA, holonic: bool, roles: bool, plastic: bool) -> tuple[int, ...]:
    """Valores canónicos distintos de los codones de memoria y aprendizaje (C19, precisión 52).

    Son los de `chromosome + plasmids` con promotor expresable en el protocolo (la regla de
    `expressible_codons`) que cumplen alguna de estas condiciones: destino `0x0D` o `0x0E` y modo
    distinto de 3; promotor `0x30`-`0x37` sobre un destino de conducta, de estado o de señal
    (de cualquier modo); o modo 3 sobre un destino de conducta, sólo si `plastic` (la hoja tiene
    `plasticity_rate > 0` expresada según su `last_context`, precisiones 23 y 52). Ascendentes.
    """
    entries = _expressible_entries(*_decoded(dna), holonic, roles)
    return tuple(sorted(_learning_values(entries, plastic)))


class CodonCensus(NamedTuple):
    """Conteos por genotipo de la telemetría genética (D53.2, precisiones 42, 52 y 54).

    Son los de `expressible_codons` (`expressible`, sin `ATTACK` en `nonattack` y condicionales
    en `conditional`), `trait_or_behavior_codons` (`functional`) y `learning_codons` sin y con
    la condición del modo 3 (`learning`, `learning_plastic`).
    """

    expressible: int
    nonattack: int
    conditional: int
    functional: int
    learning: int
    learning_plastic: int


def codon_census(dna: CompactDNA, holonic: bool, roles: bool) -> CodonCensus:
    """`CodonCensus` de `dna` en el protocolo, decodificando `chromosome + plasmids` una vez.

    Da los mismos conteos que las funciones por separado, con la misma regla de expresabilidad.
    """
    raws, codons = _decoded(dna)
    entries = _expressible_entries(raws, codons, holonic, roles)
    values = _expressible_values(entries)
    return CodonCensus(
        expressible=len(values),
        nonattack=sum(1 for v in values if (v >> 16) & 0xFF != _ATTACK_TARGET),
        conditional=sum(1 for conditional in values.values() if conditional),
        functional=sum(1 for codon in codons if _is_trait_or_behavior(codon)),
        learning=len(_learning_values(entries, False)),
        learning_plastic=len(_learning_values(entries, True)),
    )


def is_functional_codon(codon: int) -> bool:
    """Si el codón es funcional para la actividad (precisión 43): destino funcional (D61: rasgo,
    estado, conducta o señal) y modo distinto de 3, cualquiera sea el promotor."""
    return ((codon >> 16) & 0xFF) in _FUNCTIONAL_TARGETS and (codon >> 14) & 0x3 != _MODE_PLASTIC


def functional_codon_values(dna: CompactDNA) -> frozenset[int]:
    """Valores canónicos de los codones funcionales de `chromosome + plasmids` (precisión 43).

    Funcional quiere decir destino funcional (D61: rasgo, estado, conducta o señal) y modo
    distinto de 3, cualquiera sea el promotor. Es lo que cuenta la actividad de Bedau-Packard por
    nacimientos portadores: un individuo aporta 1 por valor canónico aunque lo porte varias veces.
    """
    return frozenset(
        canonical_codon(raw) for raw in dna.chromosome + dna.plasmids if is_functional_codon(raw)
    )


def trait_or_behavior_codons(dna: CompactDNA) -> int:
    """Codones de `chromosome + plasmids` con destino de rasgo (`0x00`-`0x08`, `0x0A`-`0x0C`,
    `0x0F`) o de conducta (`0x40`-`0x47`) y modo distinto de 3, cualquiera sea su promotor y con
    repeticiones: el conteo de `mean_functional_codons` (D53.2, precisión 54)."""
    return sum(
        1 for raw in dna.chromosome + dna.plasmids if _is_trait_or_behavior(decode_codon(raw))
    )


def _is_trait_or_behavior(codon: Codon) -> bool:
    """Destino de rasgo o de conducta y modo distinto de 3 (precisión 54)."""
    return codon.target in _CHANNEL_FREE_TARGETS and codon.mode != _MODE_PLASTIC
