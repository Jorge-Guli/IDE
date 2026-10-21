"""Tests de la senescencia telomérica ($R_{29}$) y de la mutación SOS ($R_{30}$) (bloque 16).

Cubren `compute_senescence_cost` (design D39), la edad (`tick - birth_tick`) y la longevidad
expresada con y sin ADN, el cobro de la senescencia también a las endosporas, el registro de
`last_stress_tick` después de la muerte (siempre, aunque $R_{30}$ esté apagada, precisión 7), las
tres escalas de SOS decididas con el estado del progenitor antes de partir la energía, por hoja en
la reproducción holónica ($R_{17}$), la escala 1.0 con la regla apagada, la inercia sin evolución
(D30.3), que la Fase II no cambia en un bit y el determinismo entre procesos.
"""

import copy
import os
import subprocess
import sys
import textwrap
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.dna import encode_codon, founder_dna
from ide.agent.evolution import compute_senescence_cost, compute_sos_scale
from ide.agent.holon import CompositeAgent
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.types import CompactDNA
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
from ide.simulation.engine import SimulationEngine
from ide.simulation.pipeline import (
    DeathSystem,
    ExpressionSystem,
    MetabolismSystem,
    SenescenceSystem,
    StressSystem,
    TickFrame,
    build_systems,
    sos_mutation_active,
    telomere_senescence_active,
)

ROOT = Path(__file__).resolve().parents[1]


def cfg(**overrides: Any) -> SimulationConfig:
    """Configuración chica con evolución, sin costos ni reproducción salvo lo que se pida."""
    base = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=6,
        resources_per_pattern=3,
        enable_evolution=True,
        metabolic_base_cost=0.0,
        memory_capacity_cost=0.0,
        sensory_radius_cost=0.0,
        move_cost=0.0,
        message_cost=0.0,
        dna_codon_cost=0.0,
        holon_coord_cost=0.0,
        reproduction_threshold=100.0,
    )
    return replace(base, **overrides)


def set_energy(engine: SimulationEngine, aid: int, energy: float) -> None:
    agent = engine.agents[aid]
    agent.apply_energy_delta(energy - agent.energy)


def energies(engine: SimulationEngine) -> dict[int, float]:
    return {aid: engine.agents[aid].energy for aid in sorted(engine.agents)}


def names(config: SimulationConfig) -> list[str]:
    return [system.name for system in build_systems(config)]


def make_holon(engine: SimulationEngine, ids: list[int]) -> CompositeAgent:
    """Agrupa en un holón raíz nuevo los nodos raíz de las hojas `ids`."""
    children = tuple(engine.root_nodes.pop(engine.agent_to_root[aid]) for aid in ids)
    holon = CompositeAgent(engine.next_holon_id, children, engine.next_tick, True)
    engine.next_holon_id -= 1
    engine.root_nodes[holon.node_id] = holon
    for leaf in holon.leaf_agents:
        engine.agent_to_root[leaf.agent_id] = holon.node_id
    return holon


def spy_scales(monkeypatch: pytest.MonkeyPatch) -> dict[int, float]:
    """Registra, por progenitor, la `mutation_scale` con que el motor pide cada hijo."""
    scales: dict[int, float] = {}
    original = MicroAgent.create_offspring

    def spy(self: MicroAgent, *args: Any, **kwargs: Any) -> MicroAgent:
        scales[self.agent_id] = kwargs.get("mutation_scale", 1.0)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(MicroAgent, "create_offspring", spy)
    return scales


# --- compute_senescence_cost (D39) --------------------------------------------------------------


def test_senescencia_de_un_agente_viejo() -> None:
    config = cfg(enable_telomere_senescence=True, senescence_cost_rate=1e-5)
    # Escenario del spec: nacido en el tick 100, paga el metabolismo del tick 800.
    assert compute_senescence_cost(800 - 100, 600, config) == pytest.approx(0.1, abs=1e-9)


def test_senescencia_dentro_de_la_longevidad() -> None:
    config = cfg(enable_telomere_senescence=True, senescence_cost_rate=1e-5)
    assert compute_senescence_cost(600, 600, config) == 0.0
    assert compute_senescence_cost(0, 600, config) == 0.0


def test_senescencia_con_la_regla_apagada() -> None:
    config = cfg(enable_telomere_senescence=False, senescence_cost_rate=1e-5)
    assert compute_senescence_cost(700, 600, config) == 0.0


@given(
    age=st.integers(0, 5000),
    lifespan=st.integers(1, 1200),
    rate=st.floats(0.0, 1e-3, allow_nan=False),
)
def test_senescencia_cuadratica_y_no_negativa(age: int, lifespan: int, rate: float) -> None:
    config = cfg(enable_telomere_senescence=True, senescence_cost_rate=rate)
    cost = compute_senescence_cost(age, lifespan, config)
    assert cost >= 0.0
    expected = rate * (age - lifespan) ** 2 if age > lifespan else 0.0
    assert cost == pytest.approx(expected, abs=1e-9)


# --- Edad y longevidad expresada en el motor ----------------------------------------------------


def senescent_config(**overrides: Any) -> SimulationConfig:
    defaults: dict[str, Any] = {
        "enable_telomere_senescence": True,
        "senescence_cost_rate": 1e-5,
        "telomere_min_lifespan": 1,
        "telomere_base_lifespan": 5,
    }
    return cfg(**{**defaults, **overrides})


def test_sistema_de_senescencia_solo_con_evolucion_y_su_bandera() -> None:
    on = senescent_config()
    assert telomere_senescence_active(on)
    order = names(on)
    assert "senescence" in order
    # (iii) del orden de D53.1: después del resto del metabolismo y antes de la muerte.
    assert order.index("metabolism") + 1 == order.index("senescence")
    assert order.index("senescence") + 1 == order.index("death")
    off = replace(on, enable_telomere_senescence=False)
    assert not telomere_senescence_active(off)
    assert names(off) == [n for n in order if n != "senescence"]
    # Sin evolución, la bandera es inerte (D30.3): no lanza error y no agrega el sistema.
    inert = replace(on, enable_evolution=False)
    assert not telomere_senescence_active(inert)
    assert names(inert) == names(replace(inert, enable_telomere_senescence=False))


def test_edad_desde_el_nacimiento_sin_adn() -> None:
    engine = SimulationEngine(senescent_config())
    agent = engine.agents[0]
    assert agent.dna is None and agent.birth_tick == 0
    # Sin ADN, la longevidad es `telomere_base_lifespan` (D33.7).
    assert agent.phenotype.lifespan == 5
    before = energies(engine)
    SenescenceSystem().run(engine, TickFrame(15))  # edad 15, exceso 10
    for aid, energy in energies(engine).items():
        assert before[aid] - energy == pytest.approx(1e-5 * 10**2, abs=1e-9)


def test_hijo_cuenta_la_edad_desde_su_nacimiento() -> None:
    engine = SimulationEngine(senescent_config())
    parent = engine.agents[0]
    child = parent.create_offspring(engine.next_agent_id, 12, engine.evo_rng)
    engine.agents[child.agent_id] = child
    assert child.birth_tick == 12 and child.phenotype.lifespan == 5
    before = child.energy
    SenescenceSystem().run(engine, TickFrame(20))  # edad 8, exceso 3
    assert before - child.energy == pytest.approx(1e-5 * 9, abs=1e-9)
    before = child.energy
    SenescenceSystem().run(engine, TickFrame(17))  # edad 5: dentro de la longevidad
    assert child.energy == before


def test_longevidad_expresada_por_el_destino_0x07_con_adn() -> None:
    config = cfg(
        enable_compact_dna=True,
        enable_telomere_senescence=True,
        senescence_cost_rate=1e-5,
        telomere_min_lifespan=1,
        telomere_base_lifespan=300,
    )
    engine = SimulationEngine(config)
    shorter = (*founder_dna(config).chromosome, encode_codon(0x00, 0x07, 0, 0, -64))
    engine.agents[0].set_dna(CompactDNA(chromosome=shorter))
    ExpressionSystem().run(engine, TickFrame(185))
    # x = 300 + 250 * (-0.5) = 175 (D33.4, escala del destino 0x07).
    assert engine.agents[0].phenotype.lifespan == 175
    assert engine.agents[1].phenotype.lifespan == 300
    before = energies(engine)
    SenescenceSystem().run(engine, TickFrame(185))
    after = energies(engine)
    assert before[0] - after[0] == pytest.approx(1e-5 * (185 - 175) ** 2, abs=1e-9)
    assert after[1] == before[1]  # edad 185 <= 300


def test_costo_basal_con_adn_y_senescencia() -> None:
    """Escenario del spec: 0.01 + 0.045 + 0.0018 + 0.001 = 0.0578."""
    config = cfg(
        enable_compact_dna=True,
        enable_telomere_senescence=True,
        metabolic_base_cost=0.01,
        memory_capacity_cost=0.005,
        dna_codon_cost=0.0002,
        senescence_cost_rate=1e-5,
        memory_capacity=3,
        telomere_min_lifespan=1,
        telomere_base_lifespan=5,
    )
    engine = SimulationEngine(config)
    dna = engine.agents[0].dna
    assert dna is not None and len(dna.chromosome) == 9
    before = energies(engine)
    frame = TickFrame(15)
    MetabolismSystem().run(engine, frame)
    SenescenceSystem().run(engine, frame)
    for aid, energy in energies(engine).items():
        assert before[aid] - energy == pytest.approx(0.0578, abs=1e-9)


def test_senescencia_tambien_en_las_endosporas() -> None:
    """Sólo la parte de R29 (0.001) del escenario del spec "Endospora senescente".

    El costo reducido de la endospora (`spore_cost_fraction * metabolic_base_cost`, 0.0005) en
    lugar del basal es del bloque 17 (D38, precisión 90): lo cubre el test de abajo.
    """
    engine = SimulationEngine(senescent_config(enable_sporulation=True))
    engine.agents[2].set_endospore(True)
    before = energies(engine)
    SenescenceSystem().run(engine, TickFrame(15))
    assert before[2] - engine.agents[2].energy == pytest.approx(0.001, abs=1e-9)


def test_endospora_senescente_paga_su_costo_mas_la_senescencia() -> None:
    """Escenario completo del spec: 0.0005 + 0.001 = 0.0015 en el tick."""
    config = senescent_config(
        enable_sporulation=True, metabolic_base_cost=0.01, spore_cost_fraction=0.05
    )
    engine = SimulationEngine(config)
    engine.agents[2].set_endospore(True)
    before = engine.agents[2].energy
    frame = TickFrame(15)
    MetabolismSystem().run(engine, frame)
    SenescenceSystem().run(engine, frame)
    assert before - engine.agents[2].energy == pytest.approx(0.0015, abs=1e-9)


def test_senescencia_no_consume_generadores() -> None:
    engine = SimulationEngine(senescent_config())
    states = [
        copy.deepcopy(g.bit_generator.state)
        for g in (engine.rng, engine.evo_rng, engine.donor_rng, engine.null_rng)
    ]
    SenescenceSystem().run(engine, TickFrame(40))
    assert states == [
        g.bit_generator.state
        for g in (engine.rng, engine.evo_rng, engine.donor_rng, engine.null_rng)
    ]


def test_la_senescencia_puede_matar_en_el_mismo_tick() -> None:
    """El costo se cobra antes de la muerte (D53.1, paso iii): quien queda en E <= 0 muere."""
    config = senescent_config(senescence_cost_rate=1.0, initial_energy=1.0)
    engine = SimulationEngine(config)
    engine.next_tick = 7  # edad 7, exceso 2: costo 4 > energía 1
    engine.step()
    assert engine.agents == {}
    assert engine.evolutionary_history[-1].deaths_this_tick == config.num_agents


# --- Registro del estrés (D39, precisión 7) -----------------------------------------------------


def stress_config(**overrides: Any) -> SimulationConfig:
    defaults: dict[str, Any] = {
        "reproduction_threshold": 2.2,
        "stress_energy_ratio": 0.35,
        "enable_sos_mutation": True,
    }
    return cfg(**{**defaults, **overrides})


def test_sistema_de_estres_solo_con_sos_efectiva() -> None:
    """El registro sólo existe con R30 efectivamente activa: nadie más lo lee (precisión 7)."""
    on = stress_config()
    order = names(on)
    assert order.index("death") + 1 == order.index("stress")
    assert order.index("stress") + 1 == order.index("reproduction")
    off = replace(on, enable_sos_mutation=False)
    assert names(off) == [n for n in order if n != "stress"]
    assert "stress" not in names(PHASE2_PROTOCOL_CONFIGS["002a"])


def test_record_stress_fija_last_stress_tick() -> None:
    """Escenario "Setters del estado nuevo" del spec micro-agent, en su parte de R30."""
    agent = MicroAgent(0, cfg())
    assert agent.last_stress_tick is None
    agent.record_stress(30)
    assert agent.last_stress_tick == 30


def test_registro_del_ultimo_tick_de_estres() -> None:
    engine = SimulationEngine(stress_config())
    set_energy(engine, 0, 0.70)
    set_energy(engine, 1, 0.80)
    StressSystem().run(engine, TickFrame(30))
    assert engine.agents[0].last_stress_tick == 30  # 0.70 < 0.77
    assert engine.agents[1].last_stress_tick is None
    # Un estrés posterior reemplaza al anterior; sin estrés se conserva.
    set_energy(engine, 1, 2.0)
    StressSystem().run(engine, TickFrame(31))
    assert engine.agents[0].last_stress_tick == 31
    assert engine.agents[1].last_stress_tick is None


def test_umbral_de_estres_con_tolerancia() -> None:
    """En el umbral exacto no hay estrés: `energy < umbral - 1e-9` (precisión 93)."""
    engine = SimulationEngine(stress_config())
    set_energy(engine, 0, 0.77)
    set_energy(engine, 1, 0.77 - 1e-6)
    StressSystem().run(engine, TickFrame(5))
    assert engine.agents[0].last_stress_tick is None
    assert engine.agents[1].last_stress_tick == 5


def test_sin_sos_no_se_registra_el_estres() -> None:
    config = stress_config(enable_sos_mutation=False)
    assert not sos_mutation_active(config)
    engine = SimulationEngine(config)
    set_energy(engine, 3, 0.1)
    engine.step()
    assert all(a.last_stress_tick is None for a in engine.agents.values())


def test_registro_del_estres_solo_de_sobrevivientes_y_sin_generadores() -> None:
    engine = SimulationEngine(stress_config())
    set_energy(engine, 0, 0.0)  # muere
    set_energy(engine, 1, 0.5)
    states = [
        copy.deepcopy(g.bit_generator.state)
        for g in (engine.rng, engine.evo_rng, engine.donor_rng, engine.null_rng)
    ]
    frame = TickFrame(4)
    DeathSystem().run(engine, frame)
    StressSystem().run(engine, frame)
    assert 0 not in engine.agents and frame.deaths == 1
    assert engine.agents[1].last_stress_tick == 4
    assert states == [
        g.bit_generator.state
        for g in (engine.rng, engine.evo_rng, engine.donor_rng, engine.null_rng)
    ]


def test_el_registro_ocurre_en_el_tick_y_el_hijo_nace_sin_estres() -> None:
    config = stress_config(initial_energy=1.0)
    engine = SimulationEngine(config)
    set_energy(engine, 0, 0.5)
    set_energy(engine, 1, 5.0)
    engine.step()
    assert engine.agents[0].last_stress_tick == 0
    children = [a for a in engine.agents.values() if a.parent_id == 1]
    assert len(children) == 1 and children[0].last_stress_tick is None


# --- Escala de mutación SOS (R30) --------------------------------------------------------------


def sos_config(**overrides: Any) -> SimulationConfig:
    defaults: dict[str, Any] = {
        "enable_sos_mutation": True,
        "sos_window": 50,
        "reproduction_threshold": 2.2,
        "sos_high_fidelity_energy_ratio": 1.5,
        "initial_energy": 1.0,
    }
    return cfg(**{**defaults, **overrides})


def test_las_tres_escalas() -> None:
    config = sos_config()
    assert compute_sos_scale(2.5, 100, 140, config) == 4.0
    assert compute_sos_scale(3.4, 80, 140, config) == 0.25
    assert compute_sos_scale(2.5, None, 140, config) == 1.0
    # Bordes: la ventana incluye `sos_window`; la alta fidelidad incluye la igualdad.
    assert compute_sos_scale(2.5, 90, 140, config) == 4.0
    assert compute_sos_scale(2.5, 89, 140, config) == 1.0
    assert compute_sos_scale(1.5 * 2.2, None, 140, config) == 0.25
    # 1.5 * 2.2 == 3.3000000000000003: el literal 3.3 alcanza la alta fidelidad (precisión 93).
    assert compute_sos_scale(3.3, None, 140, config) == 0.25
    assert compute_sos_scale(3.3 - 1e-6, None, 140, config) == 1.0
    # El estrés reciente prevalece sobre la energía alta.
    assert compute_sos_scale(10.0, 139, 140, config) == 4.0


def test_escala_uno_con_la_regla_apagada() -> None:
    config = sos_config(enable_sos_mutation=False)
    assert compute_sos_scale(2.5, 100, 140, config) == 1.0
    assert compute_sos_scale(3.4, None, 140, config) == 1.0


def test_condicion_efectiva_de_sos() -> None:
    assert sos_mutation_active(sos_config())
    assert not sos_mutation_active(sos_config(enable_sos_mutation=False))
    # Sin evolución, la bandera es inerte (D30.3).
    inert = replace(sos_config(), enable_evolution=False)
    assert not sos_mutation_active(inert)
    assert names(inert) == names(replace(inert, enable_sos_mutation=False))


def test_el_motor_decide_las_tres_escalas_antes_de_partir_la_energia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = SimulationEngine(sos_config())
    engine.next_tick = 140
    for aid, energy in ((0, 2.5), (1, 3.4), (2, 2.5)):
        set_energy(engine, aid, energy)
    engine.agents[0].record_stress(100)
    engine.agents[1].record_stress(80)
    scales = spy_scales(monkeypatch)
    births = engine._reproduce(140)  # pyright: ignore[reportPrivateUsage]
    assert births == 3
    # Con 3.4 el progenitor pasa a 1.7 al partir: la alta fidelidad se decide antes.
    assert scales == {0: 4.0, 1: 0.25, 2: 1.0}


def test_escala_uno_en_el_motor_con_la_regla_apagada(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(sos_config(enable_sos_mutation=False))
    for aid, energy in ((0, 2.5), (1, 3.4)):
        set_energy(engine, aid, energy)
    engine.agents[0].record_stress(139)
    scales = spy_scales(monkeypatch)
    engine._reproduce(140)  # pyright: ignore[reportPrivateUsage]
    assert scales == {0: 1.0, 1: 1.0}


def test_escala_por_hoja_en_la_reproduccion_holonica(monkeypatch: pytest.MonkeyPatch) -> None:
    config = sos_config(
        num_agents=4,
        enable_holonic_hierarchy=True,
        enable_holon_reproduction=True,
    )
    engine = SimulationEngine(config)
    engine.next_tick = 60
    make_holon(engine, [1, 2])
    set_energy(engine, 1, 1.5)  # registró estrés 10 ticks antes
    set_energy(engine, 2, 3.0)  # sin estrés, energía intermedia (2.2 <= 3.0 < 3.3)
    engine.agents[1].record_stress(50)
    scales = spy_scales(monkeypatch)
    births = engine._reproduce(60)  # pyright: ignore[reportPrivateUsage]
    assert births == 2
    assert scales == {1: config.sos_hypermutation_factor, 2: 1.0}


def test_la_escala_cambia_la_mutacion_del_adn() -> None:
    """Con `p_point = min(1, 4 * 0.25) = 1` muta cada codón; con escala 0 no muta ninguno."""
    config = sos_config(
        enable_compact_dna=True,
        dna_point_mutation_rate=0.25,
        dna_duplication_rate=0.0,
        dna_deletion_rate=0.0,
        sos_hypermutation_factor=4.0,
        sos_high_fidelity_factor=0.0,
    )
    engine = SimulationEngine(config)
    set_energy(engine, 0, 2.5)
    set_energy(engine, 1, 3.4)
    engine.agents[0].record_stress(139)
    engine._reproduce(140)  # pyright: ignore[reportPrivateUsage]
    parent_dna = founder_dna(config).chromosome
    child_of = {a.parent_id: a for a in engine.agents.values() if a.parent_id is not None}
    hyper_dna, faithful_dna = child_of[0].dna, child_of[1].dna
    assert hyper_dna is not None and faithful_dna is not None
    hyper, faithful = hyper_dna.chromosome, faithful_dna.chromosome
    assert all(c != p for c, p in zip(hyper, parent_dna, strict=True))
    assert faithful == parent_dna


# --- Compatibilidad con la Fase II y determinismo -----------------------------------------------


def run_state(config: SimulationConfig, ticks: int) -> tuple[Any, ...]:
    engine = SimulationEngine(config)
    engine.run(ticks)
    return (
        engine.history,
        engine.evolutionary_history,
        sorted(engine.agents),
        [engine.agents[a].energy for a in sorted(engine.agents)],
        [engine.agents[a].genome for a in sorted(engine.agents)],
        engine.rng.bit_generator.state,
        engine.evo_rng.bit_generator.state,
        engine.donor_rng.bit_generator.state,
    )


@pytest.mark.parametrize("protocol", ["002a", "003a"])
def test_fase_ii_bit_a_bit_con_reglas_que_no_actuan(protocol: str) -> None:
    """Con escalas 1.0 y sin agentes más viejos que su longevidad, nada cambia en un bit."""
    base = PHASE2_PROTOCOL_CONFIGS[protocol]
    neutral = replace(
        base,
        enable_sos_mutation=True,
        sos_hypermutation_factor=1.0,
        sos_high_fidelity_factor=1.0,
        enable_telomere_senescence=True,
        telomere_base_lifespan=1200,
        telomere_max_lifespan=1200,
    )
    assert run_state(base, 60) == run_state(neutral, 60)


def test_las_reglas_activas_cambian_la_corrida() -> None:
    """Sanidad: con escalas distintas de 1 y longevidad corta, la corrida difiere."""
    base = replace(PHASE2_PROTOCOL_CONFIGS["002a"], telomere_min_lifespan=1)
    active = replace(
        base,
        enable_sos_mutation=True,
        enable_telomere_senescence=True,
        telomere_base_lifespan=10,
        senescence_cost_rate=1e-3,
    )
    assert run_state(base, 60) != run_state(active, 60)


def test_historiales_iguales_entre_procesos_con_r29_y_r30() -> None:
    script = textwrap.dedent(
        """
        from dataclasses import replace
        from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
        from ide.simulation.engine import SimulationEngine

        config = replace(
            PHASE2_PROTOCOL_CONFIGS["003a"], enable_compact_dna=True,
            enable_telomere_senescence=True, telomere_min_lifespan=1,
            telomere_base_lifespan=15, senescence_cost_rate=1e-3,
            enable_sos_mutation=True,
        )
        engine = SimulationEngine(config)
        engine.run(40)
        print(engine.history)
        print(engine.evolutionary_history)
        print(sorted(engine.root_nodes), sorted(engine.agents))
        agents = [engine.agents[a] for a in sorted(engine.agents)]
        print([(a.energy, a.birth_tick, a.last_stress_tick, a.dna) for a in agents])
        print([a.memory.all_units() for a in agents])
        print(engine.rng.bit_generator.state, engine.evo_rng.bit_generator.state)
        print(engine.donor_rng.bit_generator.state)
        print(sum(1 for a in agents if a.last_stress_tick is not None))
        """
    )
    outputs = []
    for hash_seed in ("0", "123"):
        # El `src` de este árbol primero: la instalación editable puede apuntar a otro.
        path = os.pathsep.join(
            filter(None, [str(ROOT / "src"), str(ROOT), os.environ.get("PYTHONPATH")])
        )
        env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": path}
        done = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            check=True,
            cwd=ROOT,
        )
        outputs.append(done.stdout)
    assert outputs[0] == outputs[1]
    # La corrida tiene estrés registrado: la igualdad no es trivial.
    assert outputs[0].strip().splitlines()[-1] != "0"
