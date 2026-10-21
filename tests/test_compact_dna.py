"""Tests del ADN compacto: codón, ADN fundador y transcripción (bloque 2, D32 y D33)."""

import ast
import dataclasses
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent import dna as dna_module
from ide.agent.dna import (
    BEHAVIOR_TARGETS,
    FOUNDER_DNA_LENGTH,
    Codon,
    decode_codon,
    encode_codon,
    evaluate_drives,
    expressible_codons,
    founder_dna,
    founder_dna_length,
    mutate_dna,
    phenotype_from_genome,
    recombine_dna,
    transcribe_phenotype,
)
from ide.agent.evolution import genome_from_config
from ide.config import FOUNDER_DNA_LENGTH_GENETIC, SimulationConfig
from ide.domain.extensions import integer_trait_bounds
from ide.domain.types import (
    Behavior,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    SensorySignals,
)

ROOT = Path(__file__).resolve().parent.parent
DNA_PATH = ROOT / "src" / "ide" / "agent" / "dna.py"

ALWAYS = 0x00
ALPHA, GAMMA, EPS, BOND, CAP, PERC, COM, LIFE, SPORE, EMIT = range(10)


def make_config(**overrides: object) -> SimulationConfig:
    params: dict[str, object] = {"enable_evolution": True, "enable_compact_dna": True}
    params.update(overrides)
    return SimulationConfig(**params)  # type: ignore[arg-type]


def with_codons(config: SimulationConfig, *codons: int) -> CompactDNA:
    base = founder_dna(config)
    return CompactDNA(chromosome=base.chromosome + tuple(codons))


def alpha_of(dna: CompactDNA, ctx: EpigeneticContext, config: SimulationConfig) -> float:
    return transcribe_phenotype(dna, ctx, config).genome.alpha_learning


CTX0 = EpigeneticContext()


# (a) codón ---------------------------------------------------------------------------------


def test_decode_codon_regulado_y_represor() -> None:
    codon = decode_codon(0x80044580)
    assert isinstance(codon, Codon)
    assert codon.promoter == 0x80
    assert codon.target == 0x04
    assert codon.mode == 1
    assert codon.channel == 5
    assert codon.delta == pytest.approx(-1.0, abs=1e-9)


def test_delta_extremos() -> None:
    assert decode_codon(encode_codon(0, 0, payload=127)).delta == pytest.approx(0.9921875, abs=1e-9)
    assert decode_codon(encode_codon(0, 0, payload=-128)).delta == pytest.approx(-1.0, abs=1e-9)
    assert decode_codon(encode_codon(0, 0, payload=0)).delta == 0.0


def test_encode_ida_y_vuelta() -> None:
    value = encode_codon(0x80, 0x04, 1, 5, -128)
    assert value == 0x80044580
    assert type(value) is int
    decoded = decode_codon(value)
    assert (decoded.promoter, decoded.target, decoded.mode, decoded.channel) == (0x80, 4, 1, 5)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"payload": 128},
        {"payload": -129},
        {"mode": 4},
        {"mode": -1},
        {"channel": 64},
        {"channel": -1},
        {"promoter": 256},
        {"promoter": -1},
        {"target": 256},
        {"target": -1},
    ],
)
def test_encode_fuera_de_rango(kwargs: dict[str, int]) -> None:
    args = {"promoter": 0, "target": 0}
    args.update(kwargs)
    with pytest.raises(ValueError):
        encode_codon(**args)


@given(
    st.integers(0, 255),
    st.integers(0, 255),
    st.integers(0, 3),
    st.integers(0, 63),
    st.integers(-128, 127),
)
def test_propiedad_ida_y_vuelta(
    promoter: int, target: int, mode: int, channel: int, p: int
) -> None:
    decoded = decode_codon(encode_codon(promoter, target, mode, channel, p))
    assert (decoded.promoter, decoded.target, decoded.mode, decoded.channel) == (
        promoter,
        target,
        mode,
        channel,
    )
    assert decoded.delta == p / 128.0


# (b) ADN fundador --------------------------------------------------------------------------


def test_founder_dna_longitud_y_contenido() -> None:
    config = make_config()
    dna = founder_dna(config)
    assert FOUNDER_DNA_LENGTH == 9
    assert len(dna.chromosome) == 9
    assert dna.chromosome == tuple(encode_codon(0x00, t) for t in range(9))
    assert dna.plasmids == () and dna.crispr_memory == ()


def test_founder_dna_reexporta_la_constante_de_config() -> None:
    import ide.config

    assert dna_module.FOUNDER_DNA_LENGTH is ide.config.FOUNDER_DNA_LENGTH


CONTEXTS = (
    EpigeneticContext(),
    EpigeneticContext(3, EpigeneticRole.NERVE, 0.1),
    EpigeneticContext(0, EpigeneticRole.EXPLORER, 2.0),
)


@pytest.mark.parametrize("ctx", CONTEXTS)
def test_fundador_neutro(ctx: EpigeneticContext) -> None:
    config = make_config()
    phenotype = transcribe_phenotype(founder_dna(config), ctx, config)
    assert phenotype.genome == genome_from_config(config)
    assert phenotype.lifespan == config.telomere_base_lifespan
    assert phenotype.spore_threshold == config.spore_energy_threshold
    assert phenotype.expressed_codons == 9


@st.composite
def valid_configs(draw: st.DrawFn) -> SimulationConfig:
    """Configuraciones válidas con ADN: varía cotas de memoria, cuadrícula, vida y espora."""
    grid = draw(st.integers(5, 30))
    capacity = draw(st.integers(1, 6))
    max_capacity = draw(st.integers(capacity, 10))
    patterns = draw(st.integers(capacity + 1, 16))
    radius_max = (grid - 1) // 2
    life_min = draw(st.integers(1, 300))
    life_base = draw(st.integers(life_min, 800))
    life_max = draw(st.integers(life_base, 1500))
    reproduction = draw(st.floats(0.2, 3.0))
    return make_config(
        alpha_learning=draw(st.floats(0.01, 1.0)),
        gamma_social_discount=draw(st.floats(0.0, 1.0)),
        epsilon_explore=draw(st.floats(0.0, 1.0)),
        initial_bond_affinity=draw(st.floats(0.0, 1.0)),
        memory_capacity=capacity,
        max_genome_memory_capacity=max_capacity,
        num_world_patterns=patterns,
        enforce_memory_constraint=draw(st.booleans()),
        perception_radius=draw(st.integers(1, radius_max)),
        comm_radius=draw(st.integers(1, radius_max)),
        grid_width=grid,
        grid_height=draw(st.integers(grid, 30)),
        telomere_min_lifespan=life_min,
        telomere_base_lifespan=life_base,
        telomere_max_lifespan=life_max,
        reproduction_threshold=reproduction,
        spore_energy_threshold=draw(st.floats(0.0, 1.0)) * reproduction,
    )


@given(
    config=valid_configs(),
    level=st.integers(0, 12),
    role=st.sampled_from(list(EpigeneticRole)),
    energy=st.floats(0.0, 3.0),
)
def test_propiedad_fundador_neutro(
    config: SimulationConfig, level: int, role: EpigeneticRole, energy: float
) -> None:
    phenotype = transcribe_phenotype(
        founder_dna(config), EpigeneticContext(level, role, energy), config
    )
    assert phenotype.genome == genome_from_config(config)
    assert phenotype.lifespan == config.telomere_base_lifespan
    assert phenotype.spore_threshold == config.spore_energy_threshold


# (c) promotores ----------------------------------------------------------------------------


def test_promotores_por_nivel_de_holon() -> None:
    config = make_config()
    dna = with_codons(
        config,
        encode_codon(0x00, ALPHA, 0, 0, 64),
        encode_codon(0x01, ALPHA, 0, 0, 64),
        encode_codon(0x03, ALPHA, 0, 0, 64),
        encode_codon(0x04, ALPHA, 0, 0, 64),
    )
    # Nivel 2: activos 0x00 y 0x03 (k = 2); 0x01 exige nivel 0 y 0x04 exige nivel 3.
    value = alpha_of(dna, EpigeneticContext(holon_level=2), config)
    assert value == pytest.approx(0.40 + 0.40 * (0.5 + 0.5), abs=1e-9)


@pytest.mark.parametrize(
    ("level", "promoter", "active"),
    [
        (0, 0x01, True),
        (1, 0x01, False),
        (0, 0x02, False),
        (1, 0x02, True),
        (5, 0x06, True),
        (4, 0x06, False),
        (9, 0x0A, True),
        (8, 0x0A, False),
    ],
)
def test_promotor_in_holon(level: int, promoter: int, active: bool) -> None:
    config = make_config()
    dna = with_codons(config, encode_codon(promoter, ALPHA, 0, 0, 64))
    value = alpha_of(dna, EpigeneticContext(holon_level=level), config)
    assert value == pytest.approx(0.60 if active else 0.40, abs=1e-9)


def test_umbrales_de_energia_exactos() -> None:
    config = make_config(stress_energy_ratio=0.35, surplus_energy_ratio=0.85)
    dna = with_codons(
        config,
        encode_codon(0x18, ALPHA, 0, 0, 64),
        encode_codon(0x19, GAMMA, 0, 0, 64),
    )
    at_stress = transcribe_phenotype(dna, EpigeneticContext(energy_ratio=0.35), config)
    assert at_stress.genome.alpha_learning == pytest.approx(0.40, abs=1e-9)
    assert at_stress.genome.gamma_social_discount == config.gamma_social_discount
    at_surplus = transcribe_phenotype(dna, EpigeneticContext(energy_ratio=0.85), config)
    assert at_surplus.genome.alpha_learning == pytest.approx(0.40, abs=1e-9)
    assert at_surplus.genome.gamma_social_discount == pytest.approx(
        min(1.0, config.gamma_social_discount + 0.40 * 0.5), abs=1e-9
    )
    below = transcribe_phenotype(dna, EpigeneticContext(energy_ratio=0.349), config)
    assert below.genome.alpha_learning == pytest.approx(0.60, abs=1e-9)


def test_promotor_de_rol() -> None:
    config = make_config()
    dna = with_codons(config, encode_codon(0x11, ALPHA, 0, 0, 64))
    librarian = alpha_of(dna, EpigeneticContext(role=EpigeneticRole.LIBRARIAN), config)
    nerve = alpha_of(dna, EpigeneticContext(role=EpigeneticRole.NERVE), config)
    assert librarian == pytest.approx(0.60, abs=1e-9)
    assert nerve == pytest.approx(0.40, abs=1e-9)
    explorer_dna = with_codons(config, encode_codon(0x10, ALPHA, 0, 0, 64))
    assert alpha_of(
        explorer_dna, EpigeneticContext(role=EpigeneticRole.EXPLORER), config
    ) == pytest.approx(0.60, abs=1e-9)
    nerve_dna = with_codons(config, encode_codon(0x12, ALPHA, 0, 0, 64))
    assert alpha_of(
        nerve_dna, EpigeneticContext(role=EpigeneticRole.NERVE), config
    ) == pytest.approx(0.60, abs=1e-9)


def test_promotores_reservados_nunca_se_activan() -> None:
    config = make_config()
    reserved = (0x0B, 0x0F, 0x13, 0x17, 0x1A, 0x20, 0x7F, 0xC0, 0xFF)
    dna = with_codons(config, *(encode_codon(p, ALPHA, 0, 0, 64) for p in reserved))
    for level in (0, 1, 5, 12):
        for role in EpigeneticRole:
            for energy in (0.0, 0.5, 2.0):
                ctx = EpigeneticContext(level, role, energy)
                assert alpha_of(dna, ctx, config) == pytest.approx(0.40, abs=1e-9)


# (d) fórmula -------------------------------------------------------------------------------


def test_codon_aditivo_sobre_alfa() -> None:
    config = make_config(alpha_learning=0.40)
    dna = with_codons(config, encode_codon(0x00, ALPHA, 0, 0, 64))
    assert alpha_of(dna, CTX0, config) == pytest.approx(0.60, abs=1e-9)


def test_saturacion_en_cota_inferior() -> None:
    config = make_config(alpha_learning=0.40)
    dna = with_codons(config, *(encode_codon(0x00, ALPHA, 0, 0, -128) for _ in range(3)))
    assert alpha_of(dna, CTX0, config) == pytest.approx(0.01, abs=1e-9)


def test_cota_superior_de_capacidad() -> None:
    config = make_config(
        memory_capacity=3,
        max_genome_memory_capacity=6,
        num_world_patterns=12,
        enforce_memory_constraint=True,
    )
    dna = with_codons(config, *(encode_codon(0x00, CAP, 0, 0, 64) for _ in range(4)))
    assert transcribe_phenotype(dna, CTX0, config).genome.memory_capacity == 6


def test_cota_de_capacidad_por_patrones_del_mundo() -> None:
    config = make_config(
        memory_capacity=3,
        max_genome_memory_capacity=20,
        num_world_patterns=6,
        enforce_memory_constraint=True,
    )
    dna = with_codons(config, *(encode_codon(0x00, CAP, 0, 0, 64) for _ in range(4)))
    assert transcribe_phenotype(dna, CTX0, config).genome.memory_capacity == 5


def test_cota_de_radios() -> None:
    config = make_config(grid_width=20, grid_height=12, perception_radius=2, comm_radius=2)
    dna = with_codons(
        config,
        *(encode_codon(0x00, PERC, 0, 0, 127) for _ in range(10)),
        *(encode_codon(0x00, COM, 0, 0, -128) for _ in range(10)),
    )
    genome = transcribe_phenotype(dna, CTX0, config).genome
    assert genome.perception_radius == (12 - 1) // 2
    assert genome.comm_radius == 1


def test_cotas_de_vida_y_espora() -> None:
    config = make_config(
        telomere_min_lifespan=150,
        telomere_max_lifespan=1200,
        telomere_base_lifespan=600,
        reproduction_threshold=1.0,
        spore_energy_threshold=0.30,
    )
    high = with_codons(
        config,
        *(encode_codon(0x00, LIFE, 0, 0, 127) for _ in range(10)),
        *(encode_codon(0x00, SPORE, 0, 0, 127) for _ in range(10)),
    )
    phenotype = transcribe_phenotype(high, CTX0, config)
    assert phenotype.lifespan == 1200
    assert phenotype.spore_threshold == pytest.approx(1.0, abs=1e-9)
    low = with_codons(
        config,
        *(encode_codon(0x00, LIFE, 0, 0, -128) for _ in range(10)),
        *(encode_codon(0x00, SPORE, 0, 0, -128) for _ in range(10)),
    )
    phenotype = transcribe_phenotype(low, CTX0, config)
    assert phenotype.lifespan == 150
    assert phenotype.spore_threshold == pytest.approx(0.0, abs=1e-9)


def test_combinacion_de_los_tres_modos() -> None:
    config = make_config(alpha_learning=0.40)
    dna = with_codons(
        config,
        encode_codon(0x00, ALPHA, 0, 0, 64),
        encode_codon(0x00, ALPHA, 1, 0, -64),
        encode_codon(0x00, ALPHA, 2, 0, 64),
        encode_codon(0x00, ALPHA, 3, 0, 127),
    )
    assert alpha_of(dna, CTX0, config) == pytest.approx(0.40 * 1.5 + 0.40 * 0.5 * 0.5, abs=1e-9)


def test_redondeo_floor_x_mas_medio() -> None:
    config = make_config(memory_capacity=3, max_genome_memory_capacity=6, num_world_patterns=12)
    dna = with_codons(config, encode_codon(0x00, CAP, 0, 0, 64))
    assert transcribe_phenotype(dna, CTX0, config).genome.memory_capacity == 5  # round(4.5) == 4


# (e) red regulatoria -----------------------------------------------------------------------


def test_activador_neutralizado_por_represor() -> None:
    config = make_config(alpha_learning=0.40)
    dna = with_codons(
        config,
        encode_codon(0x00, EMIT, 0, 3),
        encode_codon(0x00, EMIT, 1, 3),
        encode_codon(0x83, ALPHA, 0, 0, 64),
    )
    assert alpha_of(dna, CTX0, config) == pytest.approx(0.40, abs=1e-9)


def test_canal_encendido() -> None:
    config = make_config(alpha_learning=0.40)
    dna = with_codons(
        config,
        encode_codon(0x00, EMIT, 2, 3),
        encode_codon(0x83, ALPHA, 0, 0, 64),
    )
    phenotype = transcribe_phenotype(dna, CTX0, config)
    assert phenotype.genome.alpha_learning == pytest.approx(0.60, abs=1e-9)
    assert phenotype.expressed_codons == 10


def test_canal_con_mas_represores_queda_apagado() -> None:
    config = make_config()
    dna = with_codons(
        config,
        encode_codon(0x00, EMIT, 0, 3),
        encode_codon(0x00, EMIT, 1, 3),
        encode_codon(0x00, EMIT, 1, 3),
        encode_codon(0x83, ALPHA, 0, 0, 64),
    )
    assert alpha_of(dna, CTX0, config) == pytest.approx(0.40, abs=1e-9)


def test_cascada_de_dos_niveles_no_se_propaga() -> None:
    config = make_config()
    dna = with_codons(
        config,
        encode_codon(0x00, EMIT, 0, 3),
        encode_codon(0x83, EMIT, 0, 4),
        encode_codon(0x84, ALPHA, 0, 0, 64),
    )
    assert alpha_of(dna, CTX0, config) == pytest.approx(0.40, abs=1e-9)


def test_pasada_2_exige_promotor_de_la_pasada_1_activo() -> None:
    config = make_config()
    # El emisor tiene promotor 0x01 (exige nivel 0): en nivel 2 el canal no se enciende.
    dna = with_codons(
        config,
        encode_codon(0x01, EMIT, 0, 3),
        encode_codon(0x83, ALPHA, 0, 0, 64),
    )
    assert alpha_of(dna, EpigeneticContext(holon_level=0), config) == pytest.approx(0.60, abs=1e-9)
    assert alpha_of(dna, EpigeneticContext(holon_level=2), config) == pytest.approx(0.40, abs=1e-9)


def test_emit_tf_de_modo_3_no_cuenta() -> None:
    config = make_config()
    dna = with_codons(
        config,
        encode_codon(0x00, EMIT, 3, 3),
        encode_codon(0x83, ALPHA, 0, 0, 64),
    )
    assert alpha_of(dna, CTX0, config) == pytest.approx(0.40, abs=1e-9)


def test_promotor_tf_fuera_de_rango_de_canales_es_inerte() -> None:
    config = make_config()
    dna = with_codons(config, encode_codon(0xC0, ALPHA, 0, 0, 64))
    assert alpha_of(dna, CTX0, config) == pytest.approx(0.40, abs=1e-9)


# (f) destinos reservados, plásmidos y CRISPR ----------------------------------------------


def test_destinos_reservados_inertes() -> None:
    config = make_config()
    dna = with_codons(config, *(encode_codon(0x00, t, 0, 0, 127) for t in (0x10, 0x80, 0xFF)))
    phenotype = transcribe_phenotype(dna, CTX0, config)
    reference = transcribe_phenotype(founder_dna(config), CTX0, config)
    assert phenotype == reference
    assert phenotype.expressed_codons == 9


def test_emit_tf_no_modula_rasgos() -> None:
    config = make_config()
    dna = with_codons(config, encode_codon(0x00, EMIT, 0, 5))
    phenotype = transcribe_phenotype(dna, CTX0, config)
    assert phenotype.genome == genome_from_config(config)


def test_plasmido_se_transcribe_y_crispr_no() -> None:
    config = make_config(alpha_learning=0.40)
    codon = encode_codon(0x00, ALPHA, 0, 0, 64)
    founder = founder_dna(config)
    with_plasmid = CompactDNA(chromosome=founder.chromosome, plasmids=(codon,))
    with_crispr = CompactDNA(chromosome=founder.chromosome, crispr_memory=(codon,))
    assert alpha_of(with_plasmid, CTX0, config) == pytest.approx(0.60, abs=1e-9)
    assert alpha_of(with_crispr, CTX0, config) == pytest.approx(0.40, abs=1e-9)


def test_orden_cromosoma_mas_plasmidos_en_el_producto() -> None:
    config = make_config(alpha_learning=0.40)
    mult = encode_codon(0x00, ALPHA, 2, 0, 64)
    founder = founder_dna(config)
    dna = CompactDNA(chromosome=(*founder.chromosome, mult), plasmids=(mult ^ 0x1,))
    # El plásmido es un codón distinto con delta 65/128; el producto cubre ambos.
    expected = 0.40 * 1.5 * (1 + 65 / 128)
    assert alpha_of(dna, CTX0, config) == pytest.approx(expected, abs=1e-9)


# (g) fenotipo sin ADN y conteo -------------------------------------------------------------


def test_phenotype_from_genome() -> None:
    config = make_config(telomere_base_lifespan=600, spore_energy_threshold=0.30)
    genome = genome_from_config(config)
    phenotype = phenotype_from_genome(genome, config)
    assert phenotype.genome == genome
    assert phenotype.lifespan == 600
    assert phenotype.spore_threshold == 0.30
    assert phenotype.expressed_codons == 0


def test_conteo_de_codones_expresados() -> None:
    config = make_config()
    dna = with_codons(
        config,
        encode_codon(0x00, EMIT, 0, 3),
        encode_codon(0x00, ALPHA, 3, 0, 100),
        encode_codon(0x01, LIFE, 0, 0, 64),
    )
    phenotype = transcribe_phenotype(dna, CTX0, config)
    assert phenotype.expressed_codons == 10
    assert phenotype.lifespan == min(config.telomere_max_lifespan, int(600 + 250 * 0.5 + 0.5))


def test_transcripcion_pura_no_muta_el_adn() -> None:
    config = make_config()
    dna = with_codons(config, encode_codon(0x00, ALPHA, 0, 0, 64))
    first = transcribe_phenotype(dna, CTX0, config)
    second = transcribe_phenotype(dna, CTX0, config)
    assert first == second


# Propiedades -------------------------------------------------------------------------------


@given(
    config=valid_configs(),
    codons=st.lists(st.integers(0, 2**32 - 1), min_size=1, max_size=40),
    plasmids=st.lists(st.integers(0, 2**32 - 1), max_size=4, unique=True),
    level=st.integers(0, 12),
    role=st.sampled_from(list(EpigeneticRole)),
    energy=st.floats(0.0, 3.0),
)
def test_propiedad_cotas(
    config: SimulationConfig,
    codons: list[int],
    plasmids: list[int],
    level: int,
    role: EpigeneticRole,
    energy: float,
) -> None:
    dna = CompactDNA(chromosome=tuple(codons), plasmids=tuple(plasmids))
    phenotype = transcribe_phenotype(dna, EpigeneticContext(level, role, energy), config)
    genome = phenotype.genome
    capacity_hi, radius_hi = integer_trait_bounds(config)
    assert 0.01 <= genome.alpha_learning <= 1.0
    assert 0.0 <= genome.gamma_social_discount <= 1.0
    assert 0.0 <= genome.epsilon_explore <= 1.0
    assert 0.0 <= genome.bond_affinity <= 1.0
    assert 1 <= genome.memory_capacity <= capacity_hi
    assert 1 <= genome.perception_radius <= radius_hi
    assert 1 <= genome.comm_radius <= radius_hi
    assert config.telomere_min_lifespan <= phenotype.lifespan <= config.telomere_max_lifespan
    assert 0.0 <= phenotype.spore_threshold <= config.reproduction_threshold
    assert 0 <= phenotype.expressed_codons <= len(codons) + len(plasmids)
    assert type(genome.memory_capacity) is int
    assert type(phenotype.lifespan) is int


def test_independencia_de_pythonhashseed() -> None:
    script = (
        "from ide.agent.dna import *\n"
        "from ide.config import SimulationConfig\n"
        "from ide.domain.types import *\n"
        "c = SimulationConfig(enable_evolution=True, enable_compact_dna=True)\n"
        "cod = [encode_codon(0x00, 0x09, 0, 3), encode_codon(0x83, 0x00, 0, 0, 64),\n"
        "       encode_codon(0x00, 0x04, 2, 0, 90), encode_codon(0x02, 0x07, 0, 0, -50)]\n"
        "d = CompactDNA(chromosome=founder_dna(c).chromosome + tuple(cod), plasmids=(77,))\n"
        "for lvl in (0, 1, 4):\n"
        "    for role in EpigeneticRole:\n"
        "        print(transcribe_phenotype(d, EpigeneticContext(lvl, role, 0.2), c))\n"
    )
    outputs: list[str] = []
    for hash_seed in ("0", "1", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        done = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            check=True,
            cwd=ROOT,
        )
        outputs.append(done.stdout)
    assert outputs[0] and outputs[0] == outputs[1] == outputs[2]


# Auditoría AST -----------------------------------------------------------------------------


FORBIDDEN_MODULES = (
    "ide.agent.micro_agent",
    "ide.agent.holon",
    "ide.environments",
    "ide.simulation",
    "ide.experiments",
)
ALLOWED_PREFIXES = ("ide.domain", "ide.config", "numpy")


def _imported_modules() -> list[str]:
    """Módulos importados por `dna.py` (nombre completo, con `from m import x` como `m`)."""
    modules: list[str] = []
    for node in ast.walk(ast.parse(DNA_PATH.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "dna.py no usa importaciones relativas"
            modules.append(node.module or "")
    return modules


def _is_module(name: str, prefix: str) -> bool:
    return name == prefix or name.startswith(prefix + ".")


def test_auditoria_ast_de_dna() -> None:
    modules = _imported_modules()
    assert modules
    for name in modules:
        assert not any(_is_module(name, bad) for bad in FORBIDDEN_MODULES), name
    # `from ide.agent import micro_agent` también está vetado.
    for node in ast.walk(ast.parse(DNA_PATH.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module == "ide.agent":
            assert not {a.name for a in node.names} & {"micro_agent", "holon"}


def test_lista_positiva_de_importaciones_de_dna() -> None:
    stdlib = sys.stdlib_module_names
    for name in _imported_modules():
        top = name.split(".")[0]
        assert top in stdlib or any(_is_module(name, p) for p in ALLOWED_PREFIXES), name


# --- Bloque 3: mutación del ADN (D35 y D37) ---------------------------------------------------

NO_DNA_RATES: dict[str, object] = {
    "dna_point_mutation_rate": 0.0,
    "dna_duplication_rate": 0.0,
    "dna_deletion_rate": 0.0,
    "dna_excision_rate": 0.0,
}


def _rates(**overrides: object) -> SimulationConfig:
    return make_config(**{**NO_DNA_RATES, **overrides})


def _twin(seed: int) -> tuple[np.random.Generator, np.random.Generator]:
    return np.random.default_rng(seed), np.random.default_rng(seed)


def _same_state(a: np.random.Generator, b: np.random.Generator) -> bool:
    return a.bit_generator.state == b.bit_generator.state


def test_mutate_dna_puerta_r13_no_consume_rng() -> None:
    config = make_config(
        mutation_rate=0.0,
        discrete_mutation_prob=0.0,
        dna_point_mutation_rate=1.0,
        dna_duplication_rate=1.0,
        dna_deletion_rate=1.0,
        dna_excision_rate=1.0,
        enable_plasmid_hgt=True,
    )
    dna = CompactDNA(chromosome=founder_dna(config).chromosome, plasmids=(5,))
    rng, twin = _twin(1)
    assert mutate_dna(dna, config, rng) == dna
    assert _same_state(rng, twin)


def test_mutate_dna_puerta_r13_abierta_con_una_sola_tasa() -> None:
    config = _rates(mutation_rate=0.0, discrete_mutation_prob=0.1, dna_point_mutation_rate=1.0)
    dna = founder_dna(config)
    assert mutate_dna(dna, config, np.random.default_rng(1)) != dna


def test_mutate_dna_puerta_r13_abierta_con_mutation_rate_solo() -> None:
    config = _rates(mutation_rate=0.1, discrete_mutation_prob=0.0, dna_point_mutation_rate=1.0)
    dna = founder_dna(config)
    assert mutate_dna(dna, config, np.random.default_rng(1)) != dna


@pytest.mark.parametrize("scale", [-1.0, float("nan"), float("inf"), float("-inf")])
def test_mutate_dna_rechaza_escala_invalida(scale: float) -> None:
    config = make_config()
    with pytest.raises(ValueError, match="scale"):
        mutate_dna(founder_dna(config), config, np.random.default_rng(0), scale)


def test_mutacion_puntual_invierte_un_bit_por_codon() -> None:
    config = _rates(dna_point_mutation_rate=1.0)
    dna = founder_dna(config)
    rng, twin = _twin(7)
    result = mutate_dna(dna, config, rng)
    twin.random(9)
    bits = [int(twin.integers(0, 32)) for _ in range(9)]
    twin.random()  # duplicación
    twin.random()  # deleción
    assert len(result.chromosome) == 9
    for old, new, bit in zip(dna.chromosome, result.chromosome, bits, strict=True):
        assert new == old ^ (1 << bit)
    assert _same_state(rng, twin)
    assert all(type(c) is int for c in result.chromosome)


def test_mutacion_puntual_secuencia_con_probabilidad_parcial() -> None:
    config = _rates(dna_point_mutation_rate=0.5)
    dna = founder_dna(config)
    rng, twin = _twin(11)
    result = mutate_dna(dna, config, rng)
    u = twin.random(9)
    expected = []
    for codon, ui in zip(dna.chromosome, u, strict=True):
        if ui < 0.5:
            codon ^= 1 << int(twin.integers(0, 32))
        expected.append(codon)
    twin.random()
    twin.random()
    assert result.chromosome == tuple(expected)
    assert _same_state(rng, twin)


def test_plasmidos_vacios_no_consumen_arreglo() -> None:
    config = _rates()
    rng, twin = _twin(3)
    result = mutate_dna(founder_dna(config), config, rng)
    twin.random(9)
    twin.random()
    twin.random()
    assert result == founder_dna(config)
    assert _same_state(rng, twin)


def test_mutacion_puntual_de_plasmidos_despues_del_cromosoma() -> None:
    config = _rates(dna_point_mutation_rate=1.0)
    dna = CompactDNA(chromosome=founder_dna(config).chromosome, plasmids=(100, 200))
    rng, twin = _twin(5)
    result = mutate_dna(dna, config, rng)
    twin.random(9)
    for _ in range(9):
        twin.integers(0, 32)
    twin.random(2)
    bits = [int(twin.integers(0, 32)) for _ in range(2)]
    twin.random()
    twin.random()
    assert result.plasmids == (100 ^ (1 << bits[0]), 200 ^ (1 << bits[1]))
    assert _same_state(rng, twin)


def test_colision_entre_plasmidos_conserva_el_primero() -> None:
    config = _rates(dna_point_mutation_rate=1.0)
    chromosome = founder_dna(config).chromosome
    dna = CompactDNA(chromosome=chromosome, plasmids=(2, 1))
    # Bits sorteados: 9 del cromosoma y luego 0 y 1: 2 ^ 1 == 3 y 1 ^ 2 == 3 coinciden.
    rng = _ScriptedRng(randoms=[[0.0] * 9, [0.0, 0.0], 0.9, 0.9], integers=_bits(*[0] * 9, 0, 1))
    result = mutate_dna(dna, config, rng)  # type: ignore[arg-type]
    rng.assert_exhausted()
    assert result.plasmids == (3,)


def test_plasmido_mutado_en_crispr_memory_se_descarta() -> None:
    config = _rates(dna_point_mutation_rate=1.0)
    dna = CompactDNA(chromosome=founder_dna(config).chromosome, plasmids=(2, 8), crispr_memory=(3,))
    rng = _ScriptedRng(randoms=[[0.0] * 9, [0.0, 0.0], 0.9, 0.9], integers=_bits(*[0] * 9, 0, 0))
    result = mutate_dna(dna, config, rng)  # type: ignore[arg-type]
    rng.assert_exhausted()
    # 2 ^ 1 == 3 (vetado, se descarta) y 8 ^ 1 == 9.
    assert result.plasmids == (9,)
    assert result.crispr_memory == (3,)


class _ScriptedRng:
    """Generador guionado: devuelve en orden las extracciones preparadas por el test.

    `integers` es una lista de `(argumentos_esperados, valor)`: se verifica cada llamada y, con
    `assert_exhausted()`, que el guion se consumió completo.
    """

    def __init__(self, randoms: list[object], integers: list[tuple[tuple[int, ...], int]]) -> None:
        self._randoms = list(randoms)
        self._integers = list(integers)

    def random(self, size: int | None = None) -> object:
        value = self._randoms.pop(0)
        if size is None:
            return value
        assert isinstance(value, list) and len(value) == size
        return np.array(value)

    def integers(self, *args: int) -> int:
        expected, value = self._integers.pop(0)
        assert args == expected
        return value

    def assert_exhausted(self) -> None:
        assert not self._randoms and not self._integers


def _bits(*values: int) -> list[tuple[tuple[int, ...], int]]:
    """Guion de sorteos de bit: `integers(0, 32)` devolviendo cada valor."""
    return [((0, 32), v) for v in values]


def test_duplicacion_secuencia_exacta() -> None:
    config = _rates(dna_duplication_rate=1.0)
    dna = founder_dna(config)
    rng, twin = _twin(13)
    result = mutate_dna(dna, config, rng)
    twin.random(9)
    twin.random()
    i = int(twin.integers(9))
    twin.random()
    assert len(result.chromosome) == 10
    assert result.chromosome[i + 1] == dna.chromosome[i]
    assert result.chromosome == (
        *dna.chromosome[: i + 1],
        dna.chromosome[i],
        *dna.chromosome[i + 1 :],
    )
    assert _same_state(rng, twin)


def test_duplicacion_con_codones_distintos_inserta_copia_en_i_mas_uno() -> None:
    config = _rates(dna_duplication_rate=1.0)
    chromosome = tuple(encode_codon(0x00, t, payload=t) for t in range(9))
    dna = CompactDNA(chromosome=chromosome)
    rng = _ScriptedRng(randoms=[[0.9] * 9, 0.0, 0.9], integers=[((9,), 4)])
    result = mutate_dna(dna, config, rng)  # type: ignore[arg-type]
    rng.assert_exhausted()
    assert result.chromosome == (*chromosome[:5], chromosome[4], *chromosome[5:])


def test_duplicacion_en_longitud_maxima_no_extrae_indice() -> None:
    config = _rates(dna_duplication_rate=1.0, dna_max_length=9)
    rng, twin = _twin(17)
    result = mutate_dna(founder_dna(config), config, rng)
    twin.random(9)
    twin.random()
    twin.random()
    assert len(result.chromosome) == 9
    assert _same_state(rng, twin)


def test_delecion_secuencia_exacta() -> None:
    config = _rates(dna_deletion_rate=1.0)
    chromosome = tuple(encode_codon(0x00, t, payload=t) for t in range(9))
    dna = CompactDNA(chromosome=chromosome)
    rng, twin = _twin(19)
    result = mutate_dna(dna, config, rng)
    twin.random(9)
    twin.random()
    twin.random()
    i = int(twin.integers(9))
    assert result.chromosome == chromosome[:i] + chromosome[i + 1 :]
    assert _same_state(rng, twin)


def test_delecion_en_longitud_minima_no_extrae_indice() -> None:
    config = _rates(dna_deletion_rate=1.0, dna_min_length=9)
    rng, twin = _twin(23)
    result = mutate_dna(founder_dna(config), config, rng)
    twin.random(9)
    twin.random()
    twin.random()
    assert len(result.chromosome) == 9
    assert _same_state(rng, twin)


def test_delecion_no_baja_de_un_codon() -> None:
    config = _rates(dna_deletion_rate=1.0, dna_min_length=1)
    dna = CompactDNA(chromosome=(encode_codon(0x00, 0),))
    rng, twin = _twin(29)
    result = mutate_dna(dna, config, rng)
    twin.random(1)
    twin.random()
    twin.random()
    assert result.chromosome == dna.chromosome
    assert _same_state(rng, twin)


def test_duplicacion_y_delecion_usan_el_largo_actual() -> None:
    config = _rates(dna_duplication_rate=1.0, dna_deletion_rate=1.0)
    dna = founder_dna(config)
    rng, twin = _twin(31)
    result = mutate_dna(dna, config, rng)
    twin.random(9)
    twin.random()
    twin.integers(9)
    twin.random()
    twin.integers(10)  # la deleción ve el cromosoma ya duplicado
    assert len(result.chromosome) == 9
    assert _same_state(rng, twin)


def test_escision_con_fifo() -> None:
    config = _rates(enable_plasmid_hgt=True, dna_excision_rate=1.0, max_plasmids=2)
    chromosome = tuple(encode_codon(0x00, t, payload=t) for t in range(9))
    dna = CompactDNA(chromosome=chromosome, plasmids=(1000, 2000))
    rng, twin = _twin(37)
    result = mutate_dna(dna, config, rng)
    twin.random(9)
    twin.random(2)
    twin.random()
    twin.random()
    twin.random()
    i = int(twin.integers(9))
    assert result.plasmids == (2000, chromosome[i])
    assert result.chromosome == chromosome
    assert _same_state(rng, twin)


def test_escision_de_codon_vetado_no_cambia_plasmidos() -> None:
    config = _rates(enable_plasmid_hgt=True, dna_excision_rate=1.0)
    chromosome = tuple(encode_codon(0x00, t, payload=t) for t in range(9))
    dna = CompactDNA(chromosome=chromosome, crispr_memory=chromosome)
    rng, twin = _twin(41)
    result = mutate_dna(dna, config, rng)
    assert result.plasmids == ()
    assert result.crispr_memory == chromosome
    twin.random(9)
    twin.random()
    twin.random()
    twin.random()
    twin.integers(9)
    assert _same_state(rng, twin)


def test_escision_de_codon_ya_presente_en_plasmidos_no_duplica() -> None:
    config = _rates(enable_plasmid_hgt=True, dna_excision_rate=1.0, max_plasmids=9)
    chromosome = tuple(encode_codon(0x00, t, payload=t) for t in range(9))
    dna = CompactDNA(chromosome=chromosome, plasmids=chromosome)
    result = mutate_dna(dna, config, np.random.default_rng(2))
    assert result.plasmids == chromosome


def test_sin_escision_con_r26_apagada() -> None:
    config = _rates(enable_plasmid_hgt=False, dna_excision_rate=1.0)
    rng, twin = _twin(43)
    result = mutate_dna(founder_dna(config), config, rng)
    twin.random(9)
    twin.random()
    twin.random()
    assert result.plasmids == ()
    assert _same_state(rng, twin)


def test_escala_con_tope_en_uno() -> None:
    config = _rates(dna_duplication_rate=0.5, dna_max_length=32)
    for seed in range(20):
        result = mutate_dna(founder_dna(config), config, np.random.default_rng(seed), scale=4.0)
        assert len(result.chromosome) == 10


def test_escala_multiplica_la_probabilidad() -> None:
    config = _rates(dna_point_mutation_rate=0.05)
    dna = founder_dna(config)
    rng, twin = _twin(47)
    result = mutate_dna(dna, config, rng, scale=2.0)
    u = twin.random(9)
    expected = []
    for codon, ui in zip(dna.chromosome, u, strict=True):
        if ui < 0.10:
            codon ^= 1 << int(twin.integers(0, 32))
        expected.append(codon)
    assert result.chromosome == tuple(expected)


def test_crispr_memory_sin_mutar_con_tasas_maximas() -> None:
    config = make_config(
        dna_point_mutation_rate=1.0,
        dna_duplication_rate=1.0,
        dna_deletion_rate=1.0,
        dna_excision_rate=1.0,
        enable_plasmid_hgt=True,
    )
    dna = CompactDNA(chromosome=founder_dna(config).chromosome, crispr_memory=(7, 9))
    assert mutate_dna(dna, config, np.random.default_rng(0)).crispr_memory == (7, 9)


def test_mutate_dna_devuelve_enteros_de_python() -> None:
    config = make_config(dna_point_mutation_rate=1.0, dna_duplication_rate=1.0)
    result = mutate_dna(founder_dna(config), config, np.random.default_rng(0))
    for codon in result.chromosome + result.plasmids:
        assert type(codon) is int


def test_mutate_dna_no_modifica_la_entrada() -> None:
    config = make_config(dna_point_mutation_rate=1.0)
    dna = founder_dna(config)
    snapshot = dna.chromosome
    mutate_dna(dna, config, np.random.default_rng(0))
    assert dna.chromosome == snapshot


def test_mutate_dna_es_determinista() -> None:
    config = make_config(dna_point_mutation_rate=0.5, dna_duplication_rate=0.5)
    dna = founder_dna(config)
    a = mutate_dna(dna, config, np.random.default_rng(99))
    b = mutate_dna(dna, config, np.random.default_rng(99))
    assert a == b


_CODONS = st.integers(0, 2**32 - 1)


def _near(codon: int, bit: int) -> int:
    return codon ^ (1 << bit)


@st.composite
def _dna_cases(draw: st.DrawFn) -> tuple[CompactDNA, SimulationConfig]:
    """ADN arbitrario y configuración, con vecinos a un bit entre cromosoma, plásmidos y vetos."""
    min_length = draw(st.integers(1, FOUNDER_DNA_LENGTH))
    max_length = draw(st.integers(FOUNDER_DNA_LENGTH, FOUNDER_DNA_LENGTH + 4))
    max_plasmids = draw(st.integers(1, 4))
    length = draw(st.integers(min_length, max_length))
    chromosome = tuple(draw(st.lists(_CODONS, min_size=length, max_size=length)))
    pool = [*chromosome, *draw(st.lists(_CODONS, max_size=4))]
    bit = st.integers(0, 31)

    def neighbor() -> int:
        return _near(draw(st.sampled_from(pool)), draw(bit))

    plasmids = tuple(
        dict.fromkeys(
            draw(st.lists(st.one_of(_CODONS, st.builds(neighbor)), max_size=max_plasmids))
        )
    )
    pool += plasmids
    vetoes = tuple(
        dict.fromkeys(
            c
            for c in draw(st.lists(st.one_of(_CODONS, st.builds(neighbor)), max_size=4))
            if c not in plasmids
        )
    )
    config = make_config(
        dna_point_mutation_rate=draw(st.sampled_from([0.0, 0.05, 0.5, 1.0])),
        dna_duplication_rate=draw(st.sampled_from([0.0, 0.3, 1.0])),
        dna_deletion_rate=draw(st.sampled_from([0.0, 0.3, 1.0])),
        dna_excision_rate=draw(st.sampled_from([0.0, 0.3, 1.0])),
        max_plasmids=max_plasmids,
        dna_min_length=min_length,
        dna_max_length=max_length,
        enable_plasmid_hgt=draw(st.booleans()),
    )
    return CompactDNA(chromosome, plasmids, vetoes), config


@given(
    case=_dna_cases(),
    seed=st.integers(0, 2**32 - 1),
    scale=st.sampled_from([0.0, 0.5, 1.0, 2.0, 10.0]),
)
def test_propiedad_adn_mutado_siempre_valido(
    case: tuple[CompactDNA, SimulationConfig], seed: int, scale: float
) -> None:
    dna, config = case
    rng = np.random.default_rng(seed)
    for _ in range(10):  # la mutación encadenada nunca rompe las cotas ni la validez del tipo
        new = mutate_dna(dna, config, rng, scale)  # CompactDNA valida en `__post_init__`
        assert config.dna_min_length <= len(new.chromosome) <= config.dna_max_length
        assert len(new.plasmids) <= config.max_plasmids
        assert new.crispr_memory == dna.crispr_memory
        assert not set(new.plasmids) & set(new.crispr_memory)  # el veto de CRISPR se sostiene
        assert len(set(new.plasmids)) == len(new.plasmids)
        assert all(type(c) is int for c in new.chromosome + new.plasmids)
        dna = new


# ===========================================================================================
# Bloque 9: ADN conductual (D46, D51.2 y precisión 42)
# ===========================================================================================

SYMB, RECOMB, COMM = 0x0A, 0x0B, 0x0C
CONSUME, EXPLORE, NAVIGATE, WANDER, SHARE, ATTACK, FLEE, SPORULATE = BEHAVIOR_TARGETS
SENSE_FIELDS = tuple(f.name for f in dataclasses.fields(SensorySignals))[:8]
ZERO_DRIVES = (0.0,) * 8


def signals(**true_fields: bool) -> SensorySignals:
    """`SensorySignals` con todos los campos en `False` salvo los indicados."""
    values = {f.name: False for f in dataclasses.fields(SensorySignals)}
    values.update(true_fields)
    return SensorySignals(**values)


def all_signals(value: bool) -> SensorySignals:
    return SensorySignals(**{f.name: value for f in dataclasses.fields(SensorySignals)})


def drives_of(
    *codons: int,
    sig: SensorySignals | None = None,
    ctx: EpigeneticContext = CTX0,
    plasmids: tuple[int, ...] = (),
    crispr: tuple[int, ...] = (),
    config: SimulationConfig | None = None,
) -> tuple[float, ...]:
    """Impulsos de un cromosoma que contiene sólo los codones dados (sin fundador)."""
    config = config or make_config()
    dna = CompactDNA(chromosome=tuple(codons), plasmids=plasmids, crispr_memory=crispr)
    return evaluate_drives(dna, ctx, sig or signals(), config)


# (a) destinos de rasgo 0x0A-0x0C ---------------------------------------------------------


def test_rasgos_de_la_reformulacion_con_sus_escalas() -> None:
    config = make_config(
        symbiotic_commitment_base=0.0, recombination_base=0.0, comm_propensity_base=1.0
    )
    dna = with_codons(
        config,
        encode_codon(0x00, SYMB, 0, 0, 64),
        encode_codon(0x00, RECOMB, 0, 0, 32),
        encode_codon(0x00, COMM, 0, 0, -64),
    )
    phenotype = transcribe_phenotype(dna, CTX0, config)
    assert phenotype.symbiotic_commitment == pytest.approx(0.30, abs=1e-9)
    assert phenotype.recombination_propensity == pytest.approx(0.15, abs=1e-9)
    assert phenotype.comm_propensity == pytest.approx(0.70, abs=1e-9)
    assert phenotype.expressed_codons == 12


def test_un_solo_codon_alcanza_el_umbral_de_0_5() -> None:
    config = make_config(recombination_base=0.0)
    dna = with_codons(config, encode_codon(0x00, RECOMB, 0, 0, 108))
    phenotype = transcribe_phenotype(dna, CTX0, config)
    assert phenotype.recombination_propensity == pytest.approx(0.50625, abs=1e-9)
    assert phenotype.recombination_propensity >= 0.5


def test_saturacion_de_la_propension_a_comunicar() -> None:
    config = make_config(comm_propensity_base=1.0)
    dna = with_codons(config, encode_codon(0x00, COMM, 0, 0, 127))
    assert transcribe_phenotype(dna, CTX0, config).comm_propensity == pytest.approx(1.0, abs=1e-9)


def test_saturacion_inferior_de_los_rasgos_nuevos() -> None:
    config = make_config(symbiotic_commitment_base=0.1)
    dna = with_codons(config, *(encode_codon(0x00, SYMB, 0, 0, -128) for _ in range(2)))
    assert transcribe_phenotype(dna, CTX0, config).symbiotic_commitment == 0.0


def test_rasgos_nuevos_con_modos_represor_y_multiplicativo() -> None:
    config = make_config(symbiotic_commitment_base=0.4)
    mult = with_codons(config, encode_codon(0x00, SYMB, 2, 0, 64))  # 0.4 * 1.5
    assert transcribe_phenotype(mult, CTX0, config).symbiotic_commitment == pytest.approx(
        0.6, abs=1e-9
    )
    rep = with_codons(
        config, encode_codon(0x00, SYMB, 1, 0, -64), encode_codon(0x00, SYMB, 0, 0, 64)
    )  # 0.4 + 0.6 * 0.5 * 0.5
    assert transcribe_phenotype(rep, CTX0, config).symbiotic_commitment == pytest.approx(
        0.55, abs=1e-9
    )


@pytest.mark.parametrize("ctx", CONTEXTS)
@pytest.mark.parametrize("policy", [False, True])
def test_fundador_expresa_las_bases_de_los_rasgos_nuevos(
    ctx: EpigeneticContext, policy: bool
) -> None:
    config = make_config(
        enable_genetic_policy=policy,
        symbiotic_commitment_base=0.2,
        recombination_base=0.4,
        comm_propensity_base=0.6,
    )
    phenotype = transcribe_phenotype(founder_dna(config), ctx, config)
    assert phenotype.symbiotic_commitment == 0.2
    assert phenotype.recombination_propensity == 0.4
    assert phenotype.comm_propensity == 0.6
    assert phenotype.expressed_codons == 9


def test_rasgos_nuevos_con_plasmido_y_promotor_de_contexto() -> None:
    config = make_config(comm_propensity_base=0.2)
    dna = CompactDNA(
        chromosome=founder_dna(config).chromosome,
        plasmids=(encode_codon(0x02, COMM, 0, 0, 64),),  # sólo con nivel >= 1
        crispr_memory=(encode_codon(0x00, COMM, 0, 0, 127),),
    )
    assert transcribe_phenotype(dna, CTX0, config).comm_propensity == pytest.approx(0.2, abs=1e-9)
    ctx = EpigeneticContext(1)
    assert transcribe_phenotype(dna, ctx, config).comm_propensity == pytest.approx(0.5, abs=1e-9)


def test_conteo_de_expressed_codons_con_los_destinos_nuevos() -> None:
    config = make_config()
    dna = with_codons(
        config,
        encode_codon(0x00, EMIT, 0, 3),
        encode_codon(0x00, ALPHA, 3, 0, 100),
        encode_codon(0x01, LIFE, 0, 0, 64),
        encode_codon(0x00, COMM, 0, 0, 64),
        encode_codon(0x00, CONSUME, 0, 0, 64),
    )
    # cuentan los 9 fundadores, el de promotor 0x01 y el de 0x0C; no el EMIT_TF, el de modo 3
    # ni el de conducta
    assert transcribe_phenotype(dna, CTX0, config).expressed_codons == 11


def test_phenotype_from_genome_devuelve_las_bases_nuevas() -> None:
    config = make_config(
        symbiotic_commitment_base=0.2, recombination_base=0.4, comm_propensity_base=0.6
    )
    phenotype = phenotype_from_genome(genome_from_config(config), config)
    assert phenotype.symbiotic_commitment == 0.2
    assert phenotype.recombination_propensity == 0.4
    assert phenotype.comm_propensity == 0.6
    assert phenotype.expressed_codons == 0


@pytest.mark.parametrize("target", [0x0D, 0x0E, 0x10, 0x3E, 0x3F, 0x48, 0x49, 0x80, 0xFF])
def test_destinos_de_otros_bloques_o_reservados_siguen_inertes_en_el_fenotipo(
    target: int,
) -> None:
    """Estado y señal no modulan ningún rasgo; `0x0F` es un rasgo desde el bloque 14 (D59.3)."""
    config = make_config()
    reference = transcribe_phenotype(founder_dna(config), CTX0, config)
    for mode in (0, 3):
        dna = with_codons(config, encode_codon(0x00, target, mode, 1, 127))
        assert transcribe_phenotype(dna, CTX0, config) == reference


# (b) promotores sensoriales ---------------------------------------------------------------


@pytest.mark.parametrize("promoter", range(0x20, 0x28))
def test_promotores_sensoriales_inactivos_en_el_fenotipo(promoter: int) -> None:
    config = make_config()
    dna = with_codons(config, encode_codon(promoter, ALPHA, 0, 0, 64))
    for ctx in CONTEXTS:
        assert alpha_of(dna, ctx, config) == pytest.approx(config.alpha_learning, abs=1e-9)


def test_promotor_sensorial_emisor_no_enciende_canales_en_el_fenotipo() -> None:
    config = make_config()
    dna = with_codons(config, encode_codon(0x22, EMIT, 0, 2), encode_codon(0x82, ALPHA, 0, 0, 64))
    assert alpha_of(dna, CTX0, config) == pytest.approx(config.alpha_learning, abs=1e-9)


@pytest.mark.parametrize("index", range(8))
def test_correspondencia_de_cada_promotor_sensorial(index: int) -> None:
    codon = encode_codon(0x20 + index, CONSUME, 0, 0, 64)
    on = drives_of(codon, sig=signals(**{SENSE_FIELDS[index]: True}))
    off = drives_of(codon, sig=signals())
    assert on[0] == pytest.approx(0.5, abs=1e-9)
    assert off[0] == 0.0
    # los demás campos no la encienden
    others = {name: True for name in SENSE_FIELDS if name != SENSE_FIELDS[index]}
    assert drives_of(codon, sig=signals(**others))[0] == 0.0


def test_orden_de_los_campos_sensoriales() -> None:
    assert SENSE_FIELDS == (
        "known_good",
        "unknown",
        "no_resource",
        "neighbor_adjacent",
        "weaker_adjacent",
        "stronger_near",
        "crowded",
        "carcass",
    )


def test_impulso_condicionado_a_la_ausencia_de_recursos() -> None:
    codon = encode_codon(0x22, WANDER, 0, 0, 64)
    assert drives_of(codon, sig=signals(no_resource=True))[3] == pytest.approx(0.5, abs=1e-9)
    assert drives_of(codon, sig=signals(no_resource=False))[3] == 0.0


# (c) evaluate_drives ----------------------------------------------------------------------


def test_correspondencia_de_conductas_y_destinos() -> None:
    assert BEHAVIOR_TARGETS == (0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47)
    assert len(BEHAVIOR_TARGETS) == len(list(Behavior))


def test_impulsos_nulos_sin_codones_de_conducta() -> None:
    config = make_config()
    assert evaluate_drives(founder_dna(config), CTX0, all_signals(True), config)[4:] == (
        0.0,
        0.0,
        0.0,
        0.0,
    )
    assert drives_of(encode_codon(0x00, ALPHA, 0, 0, 64)) == ZERO_DRIVES


def test_combinacion_de_los_tres_modos_en_un_impulso() -> None:
    drives = drives_of(
        encode_codon(0x00, SHARE, 0, 0, 64),
        encode_codon(0x00, SHARE, 0, 0, 32),
        encode_codon(0x00, SHARE, 1, 0, -64),
        encode_codon(0x00, SHARE, 2, 0, 64),
        encode_codon(0x00, SHARE, 3, 0, 127),  # el modo 3 es inerte
    )
    assert drives[4] == pytest.approx(1.5 * 0.5 * 0.75, abs=1e-9)  # mu * rho * S = 0.5625
    assert drives[:4] == (0.0, 0.0, 0.0, 0.0) and drives[5:] == (0.0, 0.0, 0.0)


def test_impulso_negativo_sin_cotas() -> None:
    two = encode_codon(0x00, ATTACK, 0, 0, -128)
    assert drives_of(two, two)[5] == pytest.approx(-2.0, abs=1e-9)


def test_solo_con_modulador_sin_aditivo_el_impulso_es_nulo() -> None:
    """Con $S_B = 0$ (sin codones aditivos), $\\mu_B$ y $\\rho_B$ no producen impulso."""
    assert drives_of(encode_codon(0x00, FLEE, 2, 0, 64))[6] == 0.0


def test_destinos_de_conducta_inertes_en_el_fenotipo() -> None:
    config = make_config(enable_genetic_policy=False)
    dna = with_codons(config, encode_codon(0x00, FLEE, 0, 0, 127))
    reference = transcribe_phenotype(founder_dna(config), CTX0, config)
    assert transcribe_phenotype(dna, CTX0, config) == reference
    assert reference.expressed_codons == 9
    drives = evaluate_drives(dna, CTX0, signals(), config)
    assert drives[6] == pytest.approx(0.9921875, abs=1e-9)
    assert drives[:6] == (0.0,) * 6 and drives[7] == 0.0


def test_los_rasgos_no_producen_impulsos() -> None:
    config = make_config()
    assert evaluate_drives(founder_dna(config), CTX0, signals(), config) == ZERO_DRIVES


def test_canal_regulado_encendido_por_un_sensor() -> None:
    codons = (encode_codon(0x23, EMIT, 0, 2), encode_codon(0x82, FLEE, 0, 0, 64))
    on = drives_of(*codons, sig=signals(neighbor_adjacent=True))
    off = drives_of(*codons, sig=signals(neighbor_adjacent=False))
    assert on[6] == pytest.approx(0.5, abs=1e-9)
    assert off[6] == 0.0


def test_la_red_de_dos_pasadas_tambien_rige_en_los_impulsos() -> None:
    # La pasada 2 no enciende canales: el EMIT_TF regulado de la cascada no activa el siguiente.
    cascade = (
        encode_codon(0x00, EMIT, 0, 1),
        encode_codon(0x81, EMIT, 0, 2),
        encode_codon(0x82, WANDER, 0, 0, 64),
    )
    assert drives_of(*cascade)[3] == 0.0
    # Un represor neutraliza al activador (act > rep).
    repressed = (
        encode_codon(0x00, EMIT, 0, 1),
        encode_codon(0x00, EMIT, 1, 1),
        encode_codon(0x81, WANDER, 0, 0, 64),
    )
    assert drives_of(*repressed)[3] == 0.0
    # Un EMIT_TF de modo 3 no cuenta.
    reserved = (encode_codon(0x00, EMIT, 3, 1), encode_codon(0x81, WANDER, 0, 0, 64))
    assert drives_of(*reserved)[3] == 0.0


def test_promotores_de_contexto_en_los_impulsos() -> None:
    codon = encode_codon(0x02, CONSUME, 0, 0, 64)  # nivel >= 1
    assert drives_of(codon, ctx=EpigeneticContext(0))[0] == 0.0
    assert drives_of(codon, ctx=EpigeneticContext(1))[0] == pytest.approx(0.5, abs=1e-9)
    stress = encode_codon(0x18, FLEE, 0, 0, 64)
    assert drives_of(stress, ctx=EpigeneticContext(energy_ratio=0.1))[6] == pytest.approx(
        0.5, abs=1e-9
    )
    assert drives_of(stress, ctx=EpigeneticContext(energy_ratio=1.0))[6] == 0.0


@pytest.mark.parametrize("promoter", [0x0B, 0x13, 0x1A, 0x2C, 0x2F, 0x40, 0x7F, 0xC0])
def test_promotores_reservados_inactivos_en_los_impulsos(promoter: int) -> None:
    assert drives_of(encode_codon(promoter, WANDER, 0, 0, 64), sig=all_signals(True)) == (
        ZERO_DRIVES
    )


def test_plasmidos_cuentan_y_crispr_no_en_los_impulsos() -> None:
    plasmid = encode_codon(0x00, WANDER, 0, 0, 64)
    assert drives_of(encode_codon(0x00, ALPHA), plasmids=(plasmid,))[3] == pytest.approx(
        0.5, abs=1e-9
    )
    assert drives_of(encode_codon(0x00, ALPHA), crispr=(plasmid,)) == ZERO_DRIVES


def test_impulsos_acumulan_en_el_orden_de_recorrido() -> None:
    a, b, c = (encode_codon(0x00, CONSUME, 0, 0, p) for p in (127, 3, -77))
    expected = ((0.0 + 127 / 128) + 3 / 128) + (-77 / 128)
    assert drives_of(a, b, c)[0] == expected  # igualdad exacta: mismo orden de sumas


# (d) fundador y su longitud ---------------------------------------------------------------


def test_fundador_con_politica_genetica() -> None:
    config = make_config(enable_genetic_policy=True)
    dna = founder_dna(config)
    behavioral = (
        encode_codon(0x00, 0x40, 0, 0, 127),
        encode_codon(0x00, 0x41, 0, 0, 96),
        encode_codon(0x00, 0x42, 0, 0, 64),
        encode_codon(0x00, 0x43, 0, 0, 32),
    )
    assert dna.chromosome == tuple(encode_codon(0x00, t) for t in range(9)) + behavioral
    assert dna.plasmids == () and dna.crispr_memory == ()
    assert len(dna.chromosome) == 13


def test_fundador_sin_politica_genetica_no_cambia() -> None:
    config = make_config(enable_genetic_policy=False)
    assert founder_dna(config).chromosome == tuple(encode_codon(0x00, t) for t in range(9))


def test_longitud_del_fundador_con_y_sin_politica() -> None:
    plain = make_config(enable_genetic_policy=False)
    genetic = make_config(enable_genetic_policy=True)
    assert founder_dna_length(plain) == 9 == FOUNDER_DNA_LENGTH
    assert founder_dna_length(genetic) == 13
    assert founder_dna_length(plain) == len(founder_dna(plain).chromosome)
    assert founder_dna_length(genetic) == len(founder_dna(genetic).chromosome)
    assert FOUNDER_DNA_LENGTH == 9
    # `config.py` no puede importar de `agent`: su constante debe coincidir con la función.
    assert founder_dna_length(genetic) == FOUNDER_DNA_LENGTH_GENETIC
    assert founder_dna_length(plain) == FOUNDER_DNA_LENGTH


@pytest.mark.parametrize("ctx", CONTEXTS)
@pytest.mark.parametrize("sig_value", [False, True])
def test_impulsos_del_fundador_independientes_del_contexto_y_las_senales(
    ctx: EpigeneticContext, sig_value: bool
) -> None:
    config = make_config(enable_genetic_policy=True)
    drives = evaluate_drives(founder_dna(config), ctx, all_signals(sig_value), config)
    assert drives == pytest.approx((0.9921875, 0.75, 0.5, 0.25, 0.0, 0.0, 0.0, 0.0), abs=1e-9)


def test_fundador_con_politica_es_fenotipicamente_neutro() -> None:
    config = make_config(enable_genetic_policy=True)
    for ctx in CONTEXTS:
        phenotype = transcribe_phenotype(founder_dna(config), ctx, config)
        assert phenotype.genome == genome_from_config(config)
        assert phenotype.expressed_codons == 9


# (e) recombine_dna ------------------------------------------------------------------------


def _chromosome(start: int, n: int) -> tuple[int, ...]:
    return tuple(encode_codon(0x00, 0x00, 0, 0, start + i) for i in range(n))


def test_recombine_dna_cruce_de_un_punto() -> None:
    config = make_config()
    parent = CompactDNA(_chromosome(0, 6), plasmids=(11,), crispr_memory=(22,))
    partner = CompactDNA(_chromosome(50, 5), plasmids=(33,), crispr_memory=(44,))
    child = recombine_dna(parent, partner, 2, 3, config)
    assert child.chromosome == parent.chromosome[:2] + partner.chromosome[3:]
    assert child.plasmids == (11,)
    assert child.crispr_memory == (22,)


def test_recombine_dna_conserva_el_prefijo_al_truncar() -> None:
    config = make_config(dna_max_length=9)
    parent = CompactDNA(_chromosome(0, 8))
    partner = CompactDNA(_chromosome(50, 8))
    child = recombine_dna(parent, partner, 8, 0, config)  # 8 + 8 = 16 > 9
    assert len(child.chromosome) == 9
    assert child.chromosome == (parent.chromosome + partner.chromosome)[:9]


def test_recombine_dna_usa_el_progenitor_si_queda_mas_corto_que_el_minimo() -> None:
    config = make_config(dna_min_length=6)
    parent = CompactDNA(_chromosome(0, 6), plasmids=(7,))
    partner = CompactDNA(_chromosome(50, 6))
    child = recombine_dna(parent, partner, 1, 5, config)  # 1 + 1 = 2 < 6
    assert child == parent
    child = recombine_dna(parent, partner, 3, 3, config)  # 3 + 3 = 6, no es más corto
    assert child.chromosome == parent.chromosome[:3] + partner.chromosome[3:]


def test_recombine_dna_con_a_completo_y_b_al_final_da_el_progenitor() -> None:
    config = make_config()
    parent = CompactDNA(_chromosome(0, 5))
    partner = CompactDNA(_chromosome(50, 5))
    assert recombine_dna(parent, partner, 5, 5, config).chromosome == parent.chromosome


def test_recombine_dna_es_pura() -> None:
    config = make_config()
    parent = CompactDNA(_chromosome(0, 4))
    partner = CompactDNA(_chromosome(50, 4))
    before = (parent, partner)
    recombine_dna(parent, partner, 2, 1, config)
    assert (parent, partner) == before


@given(
    cut_a=st.integers(1, 12),
    cut_b=st.integers(0, 11),
    n_parent=st.integers(1, 12),
    n_partner=st.integers(1, 12),
    min_length=st.integers(1, 9),
    max_length=st.integers(9, 20),
)
def test_propiedad_recombine_dna_respeta_las_cotas(
    cut_a: int, cut_b: int, n_parent: int, n_partner: int, min_length: int, max_length: int
) -> None:
    config = make_config(dna_min_length=min_length, dna_max_length=max_length)
    parent = CompactDNA(_chromosome(0, n_parent), plasmids=(5,), crispr_memory=(6,))
    partner = CompactDNA(_chromosome(50, n_partner))
    a = min(cut_a, n_parent)
    b = min(cut_b, n_partner - 1)
    child = recombine_dna(parent, partner, a, b, config)
    assert len(child.chromosome) >= 1
    assert child.plasmids == parent.plasmids and child.crispr_memory == parent.crispr_memory
    candidate = (parent.chromosome[:a] + partner.chromosome[b:])[:max_length]
    if len(candidate) >= min_length:
        assert child.chromosome == candidate
        assert len(child.chromosome) <= max_length
    else:
        assert child.chromosome == parent.chromosome


# (e2) expressible_codons ------------------------------------------------------------------


def exp(
    *codons: int,
    plasmids: tuple[int, ...] = (),
    crispr: tuple[int, ...] = (),
    holonic: bool = False,
    roles: bool = False,
) -> tuple[tuple[int, bool], ...]:
    dna = CompactDNA(chromosome=tuple(codons) or (0,), plasmids=plasmids, crispr_memory=crispr)
    return expressible_codons(dna, holonic, roles)


def test_expressible_codons_del_fundador() -> None:
    config = make_config()
    result = expressible_codons(founder_dna(config), False, False)
    assert result == tuple((encode_codon(0x00, t), False) for t in range(9))
    genetic = expressible_codons(founder_dna(make_config(enable_genetic_policy=True)), False, False)
    assert len(genetic) == 13
    assert all(conditional is False for _, conditional in genetic)


def test_expressible_codons_excluye_emit_tf_modo_3_y_destinos_reservados() -> None:
    result = exp(
        encode_codon(0x00, EMIT, 0, 3),
        encode_codon(0x00, ALPHA, 3, 0, 5),
        encode_codon(0x00, 0x10, 0, 0, 5),
        encode_codon(0x00, 0x3F, 0, 0, 5),
        encode_codon(0x00, 0x49, 0, 0, 5),
        encode_codon(0x00, ALPHA, 0, 0, 7),
    )
    assert result == ((encode_codon(0x00, ALPHA, 0, 0, 7), False),)


def test_expressible_codons_incluye_todos_los_destinos_funcionales() -> None:
    targets = (*range(0x00, 0x09), 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, *range(0x40, 0x49))
    codons = tuple(encode_codon(0x00, t, 0, 0, 1) for t in targets)
    assert exp(*codons) == tuple((c, False) for c in sorted(codons))


def test_expressible_codons_promotores_de_contexto_segun_el_protocolo() -> None:
    def one(
        promoter: int, holonic: bool = False, roles: bool = False
    ) -> tuple[tuple[int, bool], ...]:
        return exp(encode_codon(promoter, ALPHA, 0, 0, 9), holonic=holonic, roles=roles)

    def code(promoter: int) -> int:
        return encode_codon(promoter, ALPHA, 0, 0, 9)

    assert one(0x00) == ((code(0x00), False),)
    assert one(0x01) == ((code(0x01), False),)  # sin holones es constitutivo
    assert one(0x01, holonic=True) == ((code(0x01), True),)
    assert one(0x02) == ()
    assert one(0x0A) == ()
    assert one(0x02, holonic=True) == ((code(0x02), True),)
    assert one(0x0A, holonic=True) == ((code(0x0A), True),)
    assert one(0x10, holonic=True) == ()
    assert one(0x10, roles=True) == ()
    assert one(0x12, holonic=True, roles=True) == ((code(0x12), True),)
    assert one(0x18) == ((code(0x18), True),)
    assert one(0x19) == ((code(0x19), True),)
    for reserved in (0x0B, 0x0F, 0x13, 0x17, 0x1A, 0x1F, 0x2C, 0x2F, 0x40, 0x7F, 0xC0, 0xFF):
        assert one(reserved, holonic=True, roles=True) == ()


def test_expressible_codons_promotores_sensoriales_sobre_destinos_de_conducta() -> None:
    sensory = encode_codon(0x20, ALPHA, 0, 0, 9)
    assert exp(sensory, holonic=True, roles=True) == ()  # sobre un rasgo: no expresable
    behavior = encode_codon(0x20, CONSUME, 0, 0, 9)
    assert exp(behavior) == ((behavior, True),)
    for promoter in (0x27, 0x28, 0x2B, 0x30, 0x37, 0x38, 0x3F):
        assert exp(encode_codon(promoter, ATTACK, 0, 0, 9)) == (
            (encode_codon(promoter, ATTACK, 0, 0, 9), True),
        )
    for target in (0x0D, 0x0E, 0x48):  # estado y señal también admiten los promotores nuevos
        codon = encode_codon(0x30, target, 0, 2, 9)
        assert exp(codon) == ((codon, True),)
    assert exp(encode_codon(0x30, COMM, 0, 0, 9)) == ()


def test_expressible_codons_regulados_exigen_un_emisor_activador() -> None:
    reg = encode_codon(0x83, ALPHA, 0, 0, 9)
    assert exp(reg) == ()  # sin emisor
    assert exp(reg, encode_codon(0x00, EMIT, 0, 3)) == ((reg, False),)  # constitutivo
    assert exp(reg, encode_codon(0x00, EMIT, 2, 3)) == ((reg, False),)  # modo 2 también activa
    assert exp(reg, encode_codon(0x00, EMIT, 1, 3)) == ()  # un represor no activa
    assert exp(reg, encode_codon(0x00, EMIT, 3, 3)) == ()  # modo 3: inerte
    assert exp(reg, encode_codon(0x00, EMIT, 0, 4)) == ()  # otro canal
    assert exp(reg, encode_codon(0x18, EMIT, 0, 3)) == ((reg, True),)  # emisor condicional
    # emisor con promotor regulado (0x80-0xBF) o no expresable: no cuenta
    assert exp(reg, encode_codon(0x83, EMIT, 0, 3)) == ()
    assert exp(reg, encode_codon(0x02, EMIT, 0, 3)) == ()
    assert exp(reg, encode_codon(0x02, EMIT, 0, 3), holonic=True) == ((reg, True),)


def test_expressible_codons_regulado_constitutivo_si_algun_emisor_lo_es() -> None:
    reg = encode_codon(0x83, ALPHA, 0, 0, 9)
    result = exp(reg, encode_codon(0x18, EMIT, 0, 3), encode_codon(0x00, EMIT, 0, 3))
    assert result == ((reg, False),)
    # con holones, 0x01 deja de ser constitutivo
    result = exp(reg, encode_codon(0x01, EMIT, 0, 3), holonic=True)
    assert result == ((reg, True),)
    assert exp(reg, encode_codon(0x01, EMIT, 0, 3)) == ((reg, False),)


def test_expressible_codons_emisores_en_plasmidos_si_y_en_crispr_no() -> None:
    reg = encode_codon(0x83, ALPHA, 0, 0, 9)
    emitter = encode_codon(0x00, EMIT, 0, 3)
    assert exp(reg, plasmids=(emitter,)) == ((reg, False),)
    assert exp(reg, crispr=(emitter,)) == ()
    # los codones de crispr_memory tampoco son expresables por sí mismos
    assert exp(encode_codon(0x00, ALPHA, 0, 0, 9), crispr=(encode_codon(0x00, BOND, 0, 0, 9),)) == (
        (encode_codon(0x00, ALPHA, 0, 0, 9), False),
    )


def test_expressible_codons_sensores_emisores_en_conducta_estado_y_senal() -> None:
    sensor_emitter = encode_codon(0x23, EMIT, 0, 3)
    on_trait = encode_codon(0x83, ALPHA, 0, 0, 9)
    on_behavior = encode_codon(0x83, CONSUME, 0, 0, 9)
    assert exp(on_trait, sensor_emitter) == ()
    assert exp(on_behavior, sensor_emitter) == ((on_behavior, True),)
    on_state = encode_codon(0x83, 0x0D, 0, 1, 9)
    assert exp(on_state, sensor_emitter) == ((on_state, True),)
    # un emisor de eventos, de estado o de señal percibida cuenta igual (precisión 59)
    for promoter in (0x28, 0x30, 0x38):
        assert exp(on_behavior, encode_codon(promoter, EMIT, 0, 3)) == ((on_behavior, True),)


def test_expressible_codons_valores_canonicos_distintos() -> None:
    # `channel` sólo se enmascara en destinos de rasgo y de conducta
    a = encode_codon(0x00, ALPHA, 0, 0, 9)
    b = encode_codon(0x00, ALPHA, 0, 5, 9)
    c = encode_codon(0x00, CONSUME, 0, 7, 9)
    assert exp(a, b, a, c) == ((a, False), (c & ~0x3F00, False))
    d1, d2 = encode_codon(0x00, 0x0D, 0, 1, 9), encode_codon(0x00, 0x0D, 0, 2, 9)
    s1, s2 = encode_codon(0x00, 0x48, 0, 1, 9), encode_codon(0x00, 0x48, 0, 2, 9)
    assert exp(d1, d2, s1, s2) == tuple((c_, False) for c_ in sorted((d1, d2, s1, s2)))
    # mutar el payload sí cambia el valor
    assert len(exp(a, encode_codon(0x00, ALPHA, 0, 0, 10))) == 2


def test_expressible_codons_ascendentes_y_duplicados_no_suman() -> None:
    low, high = encode_codon(0x00, 0x00, 0, 0, 1), encode_codon(0x00, 0x08, 0, 0, 1)
    assert exp(high, low, high, low, low) == ((low, False), (high, False))
    # los plásmidos duplican valores del cromosoma sin sumar
    assert exp(high, low, plasmids=(low,)) == ((low, False), (high, False))


def test_expressible_codons_regulado_aproxima_sin_considerar_represores() -> None:
    """Aproximación declarada: un represor constitutivo no cambia el carácter del regulado."""
    reg = encode_codon(0x83, ALPHA, 0, 0, 9)
    result = exp(reg, encode_codon(0x18, EMIT, 0, 3), encode_codon(0x00, EMIT, 1, 3))
    assert result == ((reg, True),)


# (f) propiedades --------------------------------------------------------------------------


signal_strategy = st.builds(SensorySignals, *([st.booleans()] * 12))
context_strategy = st.builds(
    EpigeneticContext,
    st.integers(0, 12),
    st.sampled_from(list(EpigeneticRole)),
    st.floats(0.0, 3.0),
)


@given(
    config=valid_configs(),
    codons=st.lists(st.integers(0, 2**32 - 1), min_size=1, max_size=40),
    plasmids=st.lists(st.integers(0, 2**32 - 1), max_size=4, unique=True),
    ctx=context_strategy,
    sig=signal_strategy,
)
def test_propiedad_impulsos_deterministas_y_bien_formados(
    config: SimulationConfig,
    codons: list[int],
    plasmids: list[int],
    ctx: EpigeneticContext,
    sig: SensorySignals,
) -> None:
    dna = CompactDNA(chromosome=tuple(codons), plasmids=tuple(plasmids))
    first = evaluate_drives(dna, ctx, sig, config)
    assert first == evaluate_drives(dna, ctx, sig, config)
    assert len(first) == len(list(Behavior)) == 8
    assert all(type(d) is float and d == d for d in first)
    # los codones de crispr_memory nunca influyen
    with_crispr = CompactDNA(
        chromosome=dna.chromosome, plasmids=dna.plasmids, crispr_memory=(encode_codon(0, 0x40),)
    )
    assert evaluate_drives(with_crispr, ctx, sig, config) == first


@given(
    codons=st.lists(st.integers(0, 2**32 - 1), min_size=1, max_size=30),
    holonic=st.booleans(),
    roles=st.booleans(),
)
def test_propiedad_expressible_codons_bien_formado(
    codons: list[int], holonic: bool, roles: bool
) -> None:
    dna = CompactDNA(chromosome=tuple(codons))
    result = expressible_codons(dna, holonic, roles)
    assert result == expressible_codons(dna, holonic, roles)
    values = [value for value, _ in result]
    assert values == sorted(set(values))
    for value in values:
        assert decode_codon(value).mode != 3


def test_independencia_de_pythonhashseed_en_los_impulsos() -> None:
    script = (
        "from ide.agent.dna import *\n"
        "from ide.config import SimulationConfig\n"
        "from ide.domain.types import *\n"
        "c = SimulationConfig(enable_evolution=True, enable_compact_dna=True,\n"
        "                     enable_genetic_policy=True)\n"
        "cod = [encode_codon(0x23, 0x09, 0, 3), encode_codon(0x83, 0x46, 0, 0, 64),\n"
        "       encode_codon(0x22, 0x43, 2, 0, 90), encode_codon(0x02, 0x44, 0, 0, -50)]\n"
        "d = CompactDNA(chromosome=founder_dna(c).chromosome + tuple(cod), plasmids=(77,))\n"
        "s = SensorySignals(*([True] * 12))\n"
        "for lvl in (0, 1, 4):\n"
        "    for role in EpigeneticRole:\n"
        "        print(evaluate_drives(d, EpigeneticContext(lvl, role, 0.2), s, c))\n"
        "print(expressible_codons(d, True, True))\n"
    )
    outputs: list[str] = []
    for hash_seed in ("0", "1", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        done = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            check=True,
            cwd=ROOT,
        )
        outputs.append(done.stdout)
    assert outputs[0] and outputs[0] == outputs[1] == outputs[2]
