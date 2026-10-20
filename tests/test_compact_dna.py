"""Tests del ADN compacto: codón, ADN fundador y transcripción (bloque 2, D32 y D33)."""

import ast
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
    FOUNDER_DNA_LENGTH,
    Codon,
    decode_codon,
    encode_codon,
    founder_dna,
    mutate_dna,
    phenotype_from_genome,
    transcribe_phenotype,
)
from ide.agent.evolution import genome_from_config
from ide.config import SimulationConfig
from ide.domain.extensions import integer_trait_bounds
from ide.domain.types import CompactDNA, EpigeneticContext, EpigeneticRole

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
    dna = with_codons(config, *(encode_codon(0x00, t, 0, 0, 127) for t in (0x0A, 0x80, 0xFF)))
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
