"""Tests del bloque 27: contratos y generador de la sombra neutral (design D65, D66, D73.6).

Cubren la bandera `enable_neutral_shadow`, el estado `shadow_dna` y `shadow_internal_state` del
agente, el generador `shadow_rng` (`spawn_key=(6,)`), la condición efectiva de la sombra y la
sombra de los fundadores. La herencia, la mutación y la conjugación llegan en el bloque 28.
"""

import dataclasses
from dataclasses import fields, replace
from typing import Any

import numpy as np
import pytest

from ide.agent.dna import encode_codon, founder_dna
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig, neutral_shadow_active
from ide.domain.types import CompactDNA
from ide.experiments.attribution import PHASE25_PROTOCOL_CONFIGS
from ide.simulation.engine import SimulationEngine


def cfg(**overrides: Any) -> SimulationConfig:
    base = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=8,
        resources_per_pattern=4,
        enable_evolution=True,
        enable_compact_dna=True,
        enable_neutral_shadow=True,
    )
    return replace(base, **overrides)


def fresh_shadow_rng(seed: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed, spawn_key=(6,))))


# --- bandera (D65.1) -------------------------------------------------------------------------


def test_bandera_es_el_ultimo_campo_con_default_false() -> None:
    names = [f.name for f in fields(SimulationConfig)]
    assert names[-1] == "enable_neutral_shadow"
    assert names[-2] == "world_shift_fraction"
    assert SimulationConfig().enable_neutral_shadow is False


def test_bandera_sin_validacion_propia() -> None:
    assert SimulationConfig(enable_neutral_shadow=True).enable_neutral_shadow is True


@pytest.mark.parametrize(
    ("evolution", "dna", "shadow", "expected"),
    [
        (True, True, True, True),
        (True, True, False, False),
        (False, False, True, False),
        (True, False, True, False),
    ],
)
def test_sombra_efectiva(evolution: bool, dna: bool, shadow: bool, expected: bool) -> None:
    config = SimulationConfig(
        enable_evolution=evolution, enable_compact_dna=dna, enable_neutral_shadow=shadow
    )
    assert neutral_shadow_active(config) is expected


# --- estado del agente (D65.2) ---------------------------------------------------------------


def test_agente_sin_sombra_por_defecto() -> None:
    agent = MicroAgent(0, SimulationConfig(enable_evolution=True, enable_compact_dna=True))
    assert agent.shadow_dna is None
    assert agent.shadow_internal_state == 0


def test_set_shadow_dna_y_estado() -> None:
    config = SimulationConfig(enable_evolution=True, enable_compact_dna=True)
    agent = MicroAgent(0, config)
    dna = CompactDNA(chromosome=(encode_codon(0x00, 1),))
    agent.set_shadow_dna(dna)
    agent.set_shadow_internal_state(255)
    assert agent.shadow_dna == dna
    assert agent.shadow_internal_state == 255
    agent.set_shadow_internal_state(0)
    assert agent.shadow_internal_state == 0


@pytest.mark.parametrize("state", [-1, 256, 1000])
def test_set_shadow_internal_state_fuera_de_rango(state: int) -> None:
    agent = MicroAgent(0, SimulationConfig(enable_evolution=True, enable_compact_dna=True))
    with pytest.raises(ValueError, match="shadow_internal_state"):
        agent.set_shadow_internal_state(state)
    assert agent.shadow_internal_state == 0


@pytest.mark.parametrize("state", [3.5, True, np.int64(7)])
def test_set_shadow_internal_state_exige_int(state: object) -> None:
    agent = MicroAgent(0, SimulationConfig(enable_evolution=True, enable_compact_dna=True))
    with pytest.raises(TypeError, match="shadow_internal_state"):
        agent.set_shadow_internal_state(state)  # type: ignore[arg-type]
    assert agent.shadow_internal_state == 0


def test_create_offspring_no_toca_la_sombra() -> None:
    config = SimulationConfig(enable_compact_dna=True, enable_evolution=True)
    parent = MicroAgent(0, config)
    shadow = CompactDNA(chromosome=(encode_codon(0x00, 2),))
    parent.set_shadow_dna(shadow)
    parent.set_shadow_internal_state(7)
    child = parent.create_offspring(1, 5, np.random.default_rng(1))
    assert child.shadow_dna is None
    assert child.shadow_internal_state == 0
    assert parent.shadow_dna == shadow
    assert parent.shadow_internal_state == 7


def test_express_y_decide_action_indiferentes_a_la_sombra() -> None:
    config = cfg(enable_neutral_shadow=False, enable_genetic_policy=True)
    engine = SimulationEngine(config)
    other = SimulationEngine(config)
    arbitrary = CompactDNA(chromosome=(encode_codon(0x00, 3), encode_codon(0x00, 4)))
    for agent in other.agents.values():
        agent.set_shadow_dna(arbitrary)
        agent.set_shadow_internal_state(200)
    engine.run(10)
    other.run(10)
    assert engine.history == other.history
    assert engine.genetic_history == other.genetic_history
    assert engine.evolutionary_history == other.evolutionary_history
    assert engine.ecology_history == other.ecology_history
    for name in ("rng", "null_rng", "evo_rng", "donor_rng", "hgt_rng"):
        assert getattr(engine, name).bit_generator.state == getattr(other, name).bit_generator.state


# --- generador (D66) -------------------------------------------------------------------------


def test_shadow_rng_declarado_con_spawn_key_6() -> None:
    engine = SimulationEngine(cfg(seed=17, enable_neutral_shadow=False))
    assert engine.shadow_rng.bit_generator.state == fresh_shadow_rng(17).bit_generator.state


@pytest.mark.parametrize("protocol", ["25a", "25b", "25c", "25d"])
def test_shadow_rng_sin_consumo_con_sombra_apagada(protocol: str) -> None:
    config = replace(PHASE25_PROTOCOL_CONFIGS[protocol], seed=42, enable_neutral_shadow=False)
    engine = SimulationEngine(config)
    engine.run(50)
    assert engine.shadow_rng.bit_generator.state == fresh_shadow_rng(42).bit_generator.state


@pytest.mark.parametrize("protocol", ["25a", "25b", "25c", "25d"])
def test_shadow_rng_sin_consumo_con_sombra_efectiva_en_este_bloque(protocol: str) -> None:
    # El bloque 27 no tiene todavía ningún uso de `shadow_rng` (herencia y conjugación: bloque 28).
    config = replace(PHASE25_PROTOCOL_CONFIGS[protocol], seed=42, enable_neutral_shadow=True)
    engine = SimulationEngine(config)
    engine.run(20)
    assert engine.shadow_rng.bit_generator.state == fresh_shadow_rng(42).bit_generator.state


def test_generadores_del_motor_incluyen_shadow_rng() -> None:
    engine = SimulationEngine(cfg())
    names = {name for name, value in vars(engine).items() if isinstance(value, np.random.Generator)}
    assert names == {"rng", "null_rng", "evo_rng", "donor_rng", "hgt_rng", "shadow_rng"}


# --- sombra inerte (D65.1) -------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [{"enable_compact_dna": False}, {"enable_compact_dna": False, "enable_evolution": False}],
)
def test_sombra_inerte_sin_adn_o_sin_evolucion(overrides: dict[str, bool]) -> None:
    on = SimulationEngine(cfg(**overrides))
    off = SimulationEngine(cfg(enable_neutral_shadow=False, **overrides))
    assert all(a.shadow_dna is None for a in on.agents.values())
    assert all(a.shadow_internal_state == 0 for a in on.agents.values())
    on.run(10)
    off.run(10)
    assert on.history == off.history
    assert on.shadow_rng.bit_generator.state == fresh_shadow_rng(on.config.seed).bit_generator.state


# --- fundadores (D65.3) ----------------------------------------------------------------------


@pytest.mark.parametrize("protocol", ["25a", "25b", "25c", "25d"])
def test_fundadores_con_sombra_igual_al_adn(protocol: str) -> None:
    config = replace(PHASE25_PROTOCOL_CONFIGS[protocol], enable_neutral_shadow=True)
    engine = SimulationEngine(config)
    assert engine.agents
    for agent in engine.agents.values():
        assert agent.shadow_dna == agent.dna == founder_dna(config)
        assert agent.shadow_internal_state == 0
    assert (
        engine.shadow_rng.bit_generator.state == fresh_shadow_rng(config.seed).bit_generator.state
    )


def test_fundadores_sin_sombra_apagada() -> None:
    engine = SimulationEngine(cfg(enable_neutral_shadow=False))
    assert all(a.shadow_dna is None for a in engine.agents.values())


def test_config_de_protocolos_no_activa_la_sombra() -> None:
    assert all(not c.enable_neutral_shadow for c in PHASE25_PROTOCOL_CONFIGS.values())


def test_to_dict_y_replace_conservan_la_bandera() -> None:
    config = cfg()
    assert config.to_dict()["enable_neutral_shadow"] is True
    assert dataclasses.replace(config, enable_neutral_shadow=False).enable_neutral_shadow is False
