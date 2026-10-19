"""Tests de `evolutionary-dynamics` del lado del agente: genoma, metabolismo y herencia (R13, R14).

La demografía del motor (muerte, reproducción por tick, modo neutral) se prueba en el bloque 5.
"""

import ast
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.evolution import (
    compute_metabolic_cost,
    genome_from_config,
    transfer_cultural_heritage,
)
from ide.agent.memory import BoundedMemory
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.extensions import mutate_genome
from ide.domain.types import AgentGenome, KnowledgeUnit, Pattern

AGENT_DIR = Path(__file__).resolve().parents[1] / "src" / "ide" / "agent"
CFG = SimulationConfig()
INHERIT = replace(CFG, enable_cultural_inheritance=True)


def pat(i: int) -> Pattern:
    return Pattern((("id", f"p_{i}"),))


def ku(
    i: int, conf: float = 0.9, value: float = 1.0, tau: int = 0, n: int = 1, direct: bool = True
) -> KnowledgeUnit:
    return KnowledgeUnit(pat(i), value, conf, n, tau, direct)


def rng(seed: int = 0) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))


def memory_with(*units: KnowledgeUnit, capacity: int = 3) -> BoundedMemory:
    memory = BoundedMemory(capacity)
    for unit in units:
        memory.upsert(unit, 0)
    return memory


# --- Genoma fundador ---------------------------------------------------------------------------


def test_genome_from_config_toma_los_rasgos_de_la_configuracion() -> None:
    cfg = replace(
        CFG,
        alpha_learning=0.3,
        gamma_social_discount=0.6,
        epsilon_explore=0.2,
        initial_bond_affinity=0.9,
        memory_capacity=4,
        perception_radius=3,
        comm_radius=1,
    )
    assert genome_from_config(cfg) == AgentGenome(0.3, 0.6, 0.2, 0.9, 4, 3, 1)


def test_genome_from_config_por_defecto_coincide_con_agent_genome() -> None:
    assert genome_from_config(CFG) == AgentGenome()


# --- Metabolismo (R20, R21) --------------------------------------------------------------------


def test_penalizacion_cuadratica_del_cerebro_individual() -> None:
    cfg = replace(
        CFG, metabolic_base_cost=0.02, memory_capacity_cost=0.005, sensory_radius_cost=0.0
    )
    small, big = AgentGenome(memory_capacity=3), AgentGenome(memory_capacity=6)
    assert compute_metabolic_cost(small, cfg) == pytest.approx(0.065, abs=1e-9)
    assert compute_metabolic_cost(big, cfg) == pytest.approx(0.200, abs=1e-9)


def test_costo_sensorial_cuadratico_en_ambos_radios() -> None:
    cfg = replace(CFG, metabolic_base_cost=0.0, memory_capacity_cost=0.0, sensory_radius_cost=0.01)
    genome = AgentGenome(perception_radius=3, comm_radius=2)
    assert compute_metabolic_cost(genome, cfg) == pytest.approx(0.01 * (9 + 4), abs=1e-9)


def test_costo_metabolico_por_defecto() -> None:
    expected = 0.01 + 0.002 * 9 + 0.0005 * (4 + 4)
    assert compute_metabolic_cost(AgentGenome(), CFG) == pytest.approx(expected, abs=1e-9)


# --- Herencia cultural vertical (R14) ----------------------------------------------------------


def test_transferencia_descuenta_la_confianza_sin_tocar_el_resto() -> None:
    parent = memory_with(ku(1, conf=0.8, n=5, tau=40))
    cfg = replace(INHERIT, inheritance_discount=0.5)
    assert transfer_cultural_heritage(parent, 3, 50, cfg) == (ku(1, conf=0.4, n=5, tau=40),)


@pytest.mark.parametrize(
    "overrides",
    [{"enable_cultural_inheritance": False}, {"inheritance_discount": 0.0}],
)
def test_ablacion_de_la_herencia_cultural(overrides: dict[str, object]) -> None:
    parent = memory_with(ku(1), ku(2))
    cfg = replace(INHERIT, **overrides)  # type: ignore[arg-type]
    assert transfer_cultural_heritage(parent, 3, 0, cfg) == ()


def test_transferencia_por_utilidad_descendente_y_hasta_la_capacidad_del_hijo() -> None:
    parent = memory_with(ku(3, conf=0.5), ku(1, conf=0.9), ku(2, conf=0.7))
    out = transfer_cultural_heritage(parent, 2, 0, INHERIT)
    assert [u.pattern for u in out] == [pat(1), pat(2)]


def test_transferencia_desempata_por_patron() -> None:
    parent = memory_with(ku(2, conf=0.6), ku(0, conf=0.6), ku(1, conf=0.6))
    out = transfer_cultural_heritage(parent, 3, 0, INHERIT)
    assert [u.pattern for u in out] == [pat(0), pat(1), pat(2)]


def test_transferencia_usa_la_utilidad_penalizada_del_padre() -> None:
    # R18 afecta también el orden de la herencia cultural (D25, punto 1).
    parent = memory_with(ku(0, conf=0.9), ku(1, conf=0.5))
    parent.set_redundant_patterns(frozenset({pat(0)}), penalty=0.2)
    out = transfer_cultural_heritage(parent, 1, 0, INHERIT)
    assert [u.pattern for u in out] == [pat(1)]


def test_transferencia_filtra_lo_que_quedaria_bajo_c_min_despues_de_truncar() -> None:
    # γ · γ_gen · c = 0.75 · 0.65 · 0.1 = 0.04875 < 0.05: no se transfiere, y el cupo
    # del hijo no se rellena con la creencia siguiente.
    parent = memory_with(ku(0, conf=0.9), ku(1, conf=0.1, value=1.0, tau=5), ku(2, conf=0.08))
    out = transfer_cultural_heritage(parent, 2, 5, INHERIT)
    assert [u.pattern for u in out] == [pat(0)]


def test_transferencia_en_el_umbral_exacto_se_conserva() -> None:
    cfg = replace(INHERIT, gamma_social_discount=0.5, inheritance_discount=0.5, min_confidence=0.2)
    parent = memory_with(ku(0, conf=0.8))
    assert len(transfer_cultural_heritage(parent, 3, 0, cfg)) == 1


def test_transferencia_no_modifica_la_memoria_del_padre() -> None:
    parent = memory_with(ku(0), ku(1, conf=0.4))
    before = parent.all_units()
    transfer_cultural_heritage(parent, 3, 0, INHERIT)
    assert parent.all_units() == before


def test_transferencia_epigenica_por_la_puerta_social() -> None:
    # Escenario del spec: el motor entrega la herencia por `assimilate_testimony`.
    cfg = replace(INHERIT, inheritance_discount=0.5, mutation_rate=0.0, discrete_mutation_prob=0.0)
    parent = MicroAgent(4, cfg)
    parent.memory.upsert(ku(1, conf=0.80, n=5, tau=30), 30)
    child = parent.create_offspring(child_id=9, tick=50, rng=rng())
    for belief in transfer_cultural_heritage(
        parent.memory, child.memory.capacity, 50, child.config
    ):
        child.assimilate_testimony(belief, sender_id=parent.agent_id, tick=50)
    inherited = child.memory.get(pat(1))
    assert inherited is not None
    assert inherited.predicted_value == 1.0
    assert inherited.confidence == pytest.approx(0.30, abs=1e-9)
    assert inherited.evidence_count == 1
    assert inherited.last_updated_tick == 50
    assert inherited.from_direct_experience is False


# --- Auditorías sobre el AST -------------------------------------------------------------------


def imported_modules(path: Path) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    return names


def test_evolution_no_importa_micro_agent() -> None:
    # Sin ciclo: `micro_agent.py` importa `evolution.py`, nunca al revés (D20, regla 5).
    names = imported_modules(AGENT_DIR / "evolution.py")
    assert not any("micro_agent" in name for name in names), names


def test_ningun_modulo_del_agente_referencia_nullify_belief() -> None:
    # El control nulo de contenido lo aplica sólo el motor (D20, regla 4).
    for path in sorted(AGENT_DIR.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            name = getattr(node, "id", None) or getattr(node, "attr", None)
            if isinstance(node, ast.alias):
                name = node.name
            assert name != "nullify_belief", path.relative_to(AGENT_DIR)


# --- Propiedades (Hypothesis) ------------------------------------------------------------------


@st.composite
def configs(draw: st.DrawFn) -> SimulationConfig:
    """Configuraciones válidas con grillas chicas, para ejercitar las cotas de la mutación."""
    width, height = draw(st.integers(1, 12)), draw(st.integers(1, 12))
    max_radius = (min(width, height) - 1) // 2
    enforce = draw(st.booleans())
    patterns = draw(st.integers(2, 8))
    capacity_hi = patterns - 1 if enforce else 8
    capacity = draw(st.integers(1, capacity_hi))
    return replace(
        CFG,
        grid_width=width,
        grid_height=height,
        num_world_patterns=patterns,
        enforce_memory_constraint=enforce,
        memory_capacity=capacity,
        max_genome_memory_capacity=draw(st.integers(capacity, 9)),
        perception_radius=draw(st.integers(0, max_radius)),
        comm_radius=draw(st.integers(0, max_radius)),
        alpha_learning=draw(st.floats(0.01, 1.0)),
        gamma_social_discount=draw(st.floats(0.0, 1.0)),
        epsilon_explore=draw(st.floats(0.0, 1.0)),
        initial_bond_affinity=draw(st.floats(0.0, 1.0)),
        mutation_rate=draw(st.sampled_from([0.0, 0.05, 0.2, 1.0])),
        discrete_mutation_prob=draw(st.sampled_from([0.0, 0.1, 0.5, 1.0])),
    )


@given(configs(), st.integers(0, 2**32 - 1), st.integers(1, 40))
def test_propiedad_mutacion_acotada_y_aceptada_por_la_configuracion(
    cfg: SimulationConfig, seed: int, generations: int
) -> None:
    generator = rng(seed)
    genome = genome_from_config(cfg)
    radius_hi = (min(cfg.grid_width, cfg.grid_height) - 1) // 2
    capacity_hi = cfg.max_genome_memory_capacity
    if cfg.enforce_memory_constraint:
        capacity_hi = min(capacity_hi, cfg.num_world_patterns - 1)
    for _ in range(generations):
        parent = genome
        genome = mutate_genome(genome, cfg, generator)
        assert 0.01 <= genome.alpha_learning <= 1.0
        for value in (genome.gamma_social_discount, genome.epsilon_explore, genome.bond_affinity):
            assert 0.0 <= value <= 1.0
        assert 1 <= genome.memory_capacity <= capacity_hi
        for child_r, parent_r in (
            (genome.perception_radius, parent.perception_radius),
            (genome.comm_radius, parent.comm_radius),
        ):
            assert abs(child_r - parent_r) <= 1
            assert child_r == parent_r or 1 <= child_r <= max(radius_hi, 1)
        # El fenotipo del hijo es una configuración válida (D22, `from_lineage`).
        replace(
            cfg,
            alpha_learning=genome.alpha_learning,
            gamma_social_discount=genome.gamma_social_discount,
            epsilon_explore=genome.epsilon_explore,
            memory_capacity=genome.memory_capacity,
            perception_radius=genome.perception_radius,
            comm_radius=genome.comm_radius,
        )


def test_mutacion_acotada_durante_500_eventos_reproductivos() -> None:
    cfg = replace(CFG, mutation_rate=0.2, discrete_mutation_prob=0.5)
    generator, genome = rng(11), genome_from_config(cfg)
    for _ in range(500):
        genome = mutate_genome(genome, cfg, generator)
        assert 1 <= genome.memory_capacity <= cfg.max_genome_memory_capacity
        assert genome.memory_capacity < cfg.num_world_patterns
        assert 1 <= genome.perception_radius <= 19 and 1 <= genome.comm_radius <= 19


_parent_units = st.lists(
    st.builds(
        lambda i, c, v, t: ku(i, conf=c, value=v, tau=t),
        st.integers(0, 7),
        st.floats(0.0, 1.0),
        st.floats(-1.0, 1.0),
        st.integers(0, 30),
    ),
    max_size=8,
)


@given(
    _parent_units,
    st.integers(1, 6),
    st.integers(1, 6),
    st.integers(0, 40),
    st.floats(0.0, 1.0),
    st.floats(0.0, 1.0),
)
def test_propiedad_transferencia_cultural(
    units: list[KnowledgeUnit],
    parent_capacity: int,
    child_capacity: int,
    tick: int,
    discount: float,
    gamma: float,
) -> None:
    cfg = replace(INHERIT, inheritance_discount=discount, gamma_social_discount=gamma)
    parent = BoundedMemory(parent_capacity)
    for unit in units:
        parent.upsert(unit, unit.last_updated_tick)
    before = parent.all_units()
    out = transfer_cultural_heritage(parent, child_capacity, tick, cfg)
    assert parent.all_units() == before
    ranked = sorted(before, key=lambda u: (-parent.compute_utility(u, tick), u.pattern))
    eligible = [
        u
        for u in ranked[:child_capacity]
        if discount > 0.0 and gamma * discount * u.confidence >= cfg.min_confidence
    ]
    assert out == tuple(replace(u, confidence=discount * u.confidence) for u in eligible)
    assert len(out) <= min(child_capacity, len(before))


def test_transferencia_rechaza_capacidad_negativa() -> None:
    with pytest.raises(ValueError, match="child_capacity"):
        transfer_cultural_heritage(memory_with(ku(0)), -1, 0, INHERIT)
