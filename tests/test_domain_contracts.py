"""Tests de `domain-contracts`: tipos inmutables, puerto de entorno y `SimulationConfig`."""

import dataclasses
import json
from dataclasses import FrozenInstanceError, fields

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.config import SimulationConfig
from ide.domain.ports import EnvironmentPort, EvolutionaryEnvironmentPort
from ide.domain.types import (
    ActionResult,
    AgentAction,
    AgentGenome,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    ExpressedPhenotype,
    HolonSnapshot,
    KnowledgeUnit,
    Message,
    MessageType,
    Observation,
    Pattern,
    Resource,
    StigmergicTrace,
    VisibleResource,
)
from ide.environments.grid2d import ToroidalGrid2D


def pat(name: str) -> Pattern:
    return Pattern((("id", name),))


def unit(pattern: Pattern, value: float = 1.0, conf: float = 0.5) -> KnowledgeUnit:
    return KnowledgeUnit(pattern, value, conf, 1, 0, True)


# --- Estructuras inmutables -------------------------------------------------------------------


def test_pattern_es_inmutable() -> None:
    p = pat("p_0")
    with pytest.raises(FrozenInstanceError):
        p.attributes = ()  # type: ignore[misc]
    assert p == pat("p_0")


def test_knowledge_unit_es_inmutable() -> None:
    k = unit(pat("p_0"))
    with pytest.raises(FrozenInstanceError):
        k.confidence = 0.9  # type: ignore[misc]
    assert k.confidence == 0.5


@pytest.mark.parametrize(
    "cls", [Resource, VisibleResource, Observation, Message, AgentAction, ActionResult]
)
def test_tipos_de_dominio_son_frozen(cls: type) -> None:
    assert cls.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_pattern_hashable_y_orden_canonico() -> None:
    p1, p0 = pat("p_1"), pat("p_0")
    assert sorted([p1, p0])[0] == p0
    d = {p1: 1, p0: 0}
    assert d[pat("p_0")] == 0
    assert p0.label == "id=p_0"
    assert len({p0, pat("p_0")}) == 1


def test_pattern_label_con_varios_atributos() -> None:
    p = Pattern((("color", "azul"), ("forma", "esfera")))
    assert p.label == "color=azul&forma=esfera"


# --- Message ----------------------------------------------------------------------------------


@pytest.mark.parametrize("tipo", [MessageType.QUERY_RESPONSE, MessageType.BROADCAST_BELIEF])
def test_mensaje_sin_creencia_es_invalido(tipo: MessageType) -> None:
    with pytest.raises(ValueError):
        Message(tipo, sender_id=1, recipient_id=2, pattern=pat("p_0"), belief=None)


def test_mensaje_con_creencia_de_otro_patron_es_invalido() -> None:
    with pytest.raises(ValueError):
        Message(MessageType.BROADCAST_BELIEF, 1, None, pat("p_0"), belief=unit(pat("p_1")))


def test_mensajes_validos() -> None:
    q = Message(MessageType.QUERY_PATTERN, 1, 2, pat("p_0"))
    assert q.belief is None
    r = Message(MessageType.QUERY_RESPONSE, 2, 1, pat("p_0"), unit(pat("p_0")))
    assert r.belief is not None


# --- VisibleResource ---------------------------------------------------------------------------


def test_campos_exactos_de_visible_resource() -> None:
    nombres = {f.name for f in fields(VisibleResource)}
    assert nombres == {"resource_id", "pattern", "recommended_move", "distance", "is_reachable_now"}
    assert "true_value" not in nombres


# --- EnvironmentPort ---------------------------------------------------------------------------

METODOS_PUERTO = [
    "get_active_agent_ids",
    "get_observation",
    "get_communication_neighbors",
    "execute_action",
    "remove_agents",
    "retire_pattern_resources",
    "invert_world_rules",
    "step_dynamics",
    "get_world_patterns",
    "get_reachable_true_values",
]


def test_environment_port_declara_los_diez_metodos() -> None:
    declarados = {n for n in vars(EnvironmentPort) if not n.startswith("_")}
    assert declarados == set(METODOS_PUERTO)


def test_environment_port_es_runtime_checkable() -> None:
    class Completo:
        pass

    for nombre in METODOS_PUERTO:
        setattr(Completo, nombre, lambda self, *a, **k: None)
    assert isinstance(Completo(), EnvironmentPort)
    assert not isinstance(object(), EnvironmentPort)


# --- SimulationConfig --------------------------------------------------------------------------


def test_config_por_defecto_es_valida() -> None:
    cfg = SimulationConfig()
    assert (cfg.seed, cfg.num_agents, cfg.memory_capacity, cfg.num_world_patterns) == (
        42,
        80,
        3,
        12,
    )


def test_capacidad_igual_a_patrones_es_invalida() -> None:
    with pytest.raises(ValueError, match="memory_capacity"):
        SimulationConfig(num_world_patterns=8, memory_capacity=8)


def test_capacidad_igual_a_patrones_se_permite_sin_restriccion() -> None:
    cfg = SimulationConfig(
        num_world_patterns=8,
        memory_capacity=8,
        max_genome_memory_capacity=8,  # D20: la cota del genoma no puede quedar bajo la capacidad
        enforce_memory_constraint=False,
    )
    assert cfg.memory_capacity == 8


def test_capacidad_nula_es_invalida_aun_sin_restriccion() -> None:
    with pytest.raises(ValueError, match="memory_capacity"):
        SimulationConfig(memory_capacity=0, enforce_memory_constraint=False)


@pytest.mark.parametrize(
    "campo",
    [
        "initial_direct_confidence",
        "alpha_learning",
        "beta_reinforce",
        "beta_punish",
        "gamma_social_discount",
        "eta_consensus",
        "eta_doubt",
        "min_confidence",
        "decision_conf_threshold",
        "epsilon_explore",
        "epsilon_recheck",
    ],
)
@pytest.mark.parametrize("valor", [-0.01, 1.5])
def test_coeficientes_fuera_de_rango(campo: str, valor: float) -> None:
    with pytest.raises(ValueError, match=campo):
        SimulationConfig(**{campo: valor})


@pytest.mark.parametrize(
    "campo",
    [
        "num_agents",
        "resources_per_pattern",
        "grid_width",
        "grid_height",
        "num_world_patterns",
    ],
)
def test_enteros_minimos(campo: str) -> None:
    # num_world_patterns necesita memory_capacity compatible; se relaja la restricción.
    with pytest.raises(ValueError, match=campo):
        SimulationConfig(**{campo: 0}, enforce_memory_constraint=False)


def test_num_world_patterns_minimo_dos() -> None:
    with pytest.raises(ValueError, match="num_world_patterns"):
        SimulationConfig(num_world_patterns=1, enforce_memory_constraint=False)


@pytest.mark.parametrize(
    "campo",
    [
        "perception_radius",
        "comm_radius",
        "lambda_decay",
        "passive_conf_decay",
        "max_broadcast_per_tick",
        "max_queries_per_tick",
        "seed",
    ],
)
def test_valores_negativos(campo: str) -> None:
    with pytest.raises(ValueError, match=campo):
        SimulationConfig(**{campo: -1})


def test_semilla_cero_es_valida() -> None:
    assert SimulationConfig(seed=0).seed == 0


def test_min_confidence_menor_que_umbral() -> None:
    with pytest.raises(ValueError, match="min_confidence"):
        SimulationConfig(min_confidence=0.4, decision_conf_threshold=0.35)
    with pytest.raises(ValueError, match="min_confidence"):
        SimulationConfig(min_confidence=0.35, decision_conf_threshold=0.35)


def test_radio_que_da_la_vuelta_al_toro() -> None:
    with pytest.raises(ValueError, match="radius"):
        SimulationConfig(grid_width=4, grid_height=4, perception_radius=2)
    with pytest.raises(ValueError, match="radius"):
        SimulationConfig(grid_width=40, grid_height=4, comm_radius=2)


def test_radio_maximo_permitido() -> None:
    cfg = SimulationConfig(grid_width=5, grid_height=5, perception_radius=2, comm_radius=2)
    assert cfg.perception_radius == 2


def test_politicas_de_contrato_por_defecto() -> None:
    cfg = SimulationConfig()
    assert cfg.epsilon_recheck == 0.0
    assert cfg.tau_policy == "validation"
    assert cfg.anti_echo_enabled is True
    assert cfg.enable_navigation is True
    assert cfg.comm_content_null is False
    assert cfg.update_scheme == "synchronous"
    assert cfg.enable_specialization is False


def test_tau_policy_desconocida() -> None:
    with pytest.raises(ValueError, match="tau_policy"):
        SimulationConfig(tau_policy="siempre")
    assert SimulationConfig(tau_policy="evidence_age").tau_policy == "evidence_age"


def test_update_scheme_desconocido() -> None:
    with pytest.raises(ValueError, match="update_scheme"):
        SimulationConfig(update_scheme="continuo")
    assert SimulationConfig(update_scheme="asynchronous").update_scheme == "asynchronous"


def test_config_es_inmutable_y_replace_revalida() -> None:
    cfg = SimulationConfig()
    with pytest.raises(FrozenInstanceError):
        cfg.seed = 1  # type: ignore[misc]
    assert dataclasses.replace(cfg, seed=7).seed == 7
    with pytest.raises(ValueError, match="gamma_social_discount"):
        dataclasses.replace(cfg, gamma_social_discount=2.0)


def test_to_dict_ida_y_vuelta_por_json() -> None:
    cfg = SimulationConfig(seed=7, comm_content_null=True, tau_policy="evidence_age")
    assert SimulationConfig(**json.loads(json.dumps(cfg.to_dict()))) == cfg
    assert set(cfg.to_dict()) == {f.name for f in fields(SimulationConfig)}


def test_consulta_con_creencia_es_invalida() -> None:
    with pytest.raises(ValueError, match="QUERY_PATTERN"):
        Message(MessageType.QUERY_PATTERN, 1, 2, pat("p_0"), belief=unit(pat("p_0")))


# --- Fase II: tipos inmutables, sub-puerto y configuración -------------------------------------


@pytest.mark.parametrize("cls", [AgentGenome, StigmergicTrace, HolonSnapshot])
def test_tipos_de_fase_ii_son_frozen(cls: type) -> None:
    assert cls.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_agent_genome_por_defecto_coincide_con_la_configuracion() -> None:
    genome, config = AgentGenome(), SimulationConfig()
    assert genome.alpha_learning == config.alpha_learning
    assert genome.gamma_social_discount == config.gamma_social_discount
    assert genome.epsilon_explore == config.epsilon_explore
    assert genome.bond_affinity == config.initial_bond_affinity
    assert genome.memory_capacity == config.memory_capacity
    assert genome.perception_radius == config.perception_radius
    assert genome.comm_radius == config.comm_radius
    with pytest.raises(FrozenInstanceError):
        genome.alpha_learning = 0.1  # type: ignore[misc]


def test_campos_de_los_tipos_de_fase_ii() -> None:
    assert [f.name for f in fields(StigmergicTrace)] == [
        "pattern",
        "sign_value",
        "intensity",
        "last_updated_tick",
    ]
    assert [f.name for f in fields(HolonSnapshot)] == [
        "node_id",
        "holon_level",
        "child_node_ids",
        "leaf_agent_ids",
        "effective_capacity",
        "collective_known_patterns",
    ]


def test_visible_resource_conserva_sus_campos_de_fase_i() -> None:
    assert {f.name for f in fields(VisibleResource)} == {
        "resource_id",
        "pattern",
        "recommended_move",
        "distance",
        "is_reachable_now",
    }


def test_environment_port_conserva_sus_diez_metodos() -> None:
    declarados = {n for n in vars(EnvironmentPort) if not n.startswith("_")}
    assert len(declarados) == 10


def test_evolutionary_port_extiende_a_environment_port() -> None:
    nuevos = {
        "spawn_agent_near",
        "set_agent_radii",
        "get_agent_distance",
        "get_composite_rules",
        "deposit_stigmergy",
        "get_cell_stigmergy",
        "get_active_stigmergy_cells",
    }
    assert issubclass(EvolutionaryEnvironmentPort, EnvironmentPort)
    assert nuevos <= {n for n in vars(EvolutionaryEnvironmentPort) if not n.startswith("_")}
    assert not isinstance(object(), EvolutionaryEnvironmentPort)


def test_config_por_defecto_apaga_los_mecanismos_de_fase_ii() -> None:
    cfg = SimulationConfig()
    for flag in (
        "enable_evolution",
        "enable_cultural_inheritance",
        "enable_holonic_hierarchy",
        "enable_holon_reproduction",
        "enable_downward_causation",
        "enable_stigmergy",
    ):
        assert getattr(cfg, flag) is False
    assert cfg.num_composite_patterns == 0
    assert cfg.reproduction_mode == "energy"
    assert cfg.enable_holon_splitting and cfg.enable_holon_view and cfg.holon_energy_sharing
    assert SimulationConfig(**json.loads(json.dumps(cfg.to_dict()))) == cfg


@pytest.mark.parametrize(
    ("overrides", "campo"),
    [
        ({"initial_energy": 0.0}, "initial_energy"),
        ({"reproduction_threshold": 0.0}, "reproduction_threshold"),
        ({"energy_gain_scale": 0.0}, "energy_gain_scale"),
        ({"composite_reward_exponent": 0.0}, "composite_reward_exponent"),
        ({"offspring_energy_share": 1.0}, "offspring_energy_share"),
        ({"offspring_energy_share": 0.0}, "offspring_energy_share"),
        ({"inheritance_discount": 1.5}, "inheritance_discount"),
        ({"discrete_mutation_prob": -0.1}, "discrete_mutation_prob"),
        ({"initial_bond_affinity": 1.1}, "initial_bond_affinity"),
        ({"holon_bond_threshold": 2.0}, "holon_bond_threshold"),
        ({"stigmergy_deposit_rate": 1.5}, "stigmergy_deposit_rate"),
        ({"stigmergy_decay": -0.5}, "stigmergy_decay"),
        ({"redundancy_penalty": 0.0}, "redundancy_penalty"),
        ({"redundancy_penalty": 1.5}, "redundancy_penalty"),
        ({"metabolic_base_cost": -0.01}, "metabolic_base_cost"),
        ({"mutation_rate": -0.01}, "mutation_rate"),
        ({"holon_coord_cost": -1.0}, "holon_coord_cost"),
        ({"composite_failure_penalty": 1.5}, "composite_failure_penalty"),
        ({"composite_failure_penalty": -0.1}, "composite_failure_penalty"),
        ({"num_composite_patterns": -1}, "num_composite_patterns"),
        ({"max_population": 0}, "max_population"),
        ({"max_genome_memory_capacity": 2}, "max_genome_memory_capacity"),
        ({"max_holon_leaves": 1}, "max_holon_leaves"),
        ({"holon_split_patience": 0}, "holon_split_patience"),
        ({"composite_order": 1}, "composite_order"),
        ({"composite_resources_per_pattern": 0}, "composite_resources_per_pattern"),
        ({"reproduction_mode": "random"}, "reproduction_mode"),
        (
            {"num_world_patterns": 6, "num_composite_patterns": 1, "composite_order": 4},
            "composite_order",
        ),
    ],
)
def test_config_rechaza_hiperparametros_de_fase_ii_invalidos(
    overrides: dict[str, object], campo: str
) -> None:
    with pytest.raises(ValueError, match=campo):
        SimulationConfig(**overrides)  # type: ignore[arg-type]


def test_config_orden_compuesto_sin_compuestos_no_se_valida() -> None:
    SimulationConfig(num_world_patterns=6, num_composite_patterns=0, composite_order=4)
    SimulationConfig(num_world_patterns=8, num_composite_patterns=1, composite_order=4)


def test_config_acepta_los_bordes_validos_de_fase_ii() -> None:
    SimulationConfig(redundancy_penalty=1.0, composite_failure_penalty=1.0, mutation_rate=0.0)


@pytest.mark.parametrize(
    "campo",
    [
        "initial_energy",
        "energy_gain_scale",
        "composite_failure_penalty",
        "redundancy_penalty",
        "offspring_energy_share",
        "mutation_rate",
        "move_cost",
    ],
)
def test_config_rechaza_nan_en_hiperparametros_de_fase_ii(campo: str) -> None:
    with pytest.raises(ValueError, match=campo):
        SimulationConfig(**{campo: float("nan")})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "overrides",
    [
        {"stigmergy_deposit_rate": 0.04},
        {"stigmergy_deposit_rate": 0.05},  # 0.05 * 0.85 < 0.05: sólo sobreviviría con c = 1
        {"stigmergy_deposit_rate": 0.3, "min_confidence": 0.3},
        {"stigmergy_deposit_rate": 0.5, "initial_direct_confidence": 0.09},
    ],
)
def test_config_rechaza_estigmergia_que_solo_borraria_rastros(overrides: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="stigmergy_deposit_rate"):
        SimulationConfig(enable_stigmergy=True, **overrides)  # type: ignore[arg-type]


def test_config_acepta_tasas_de_estigmergia_coherentes() -> None:
    # borde exacto: 0.1 * 0.5 == 0.05
    SimulationConfig(
        enable_stigmergy=True, stigmergy_deposit_rate=0.1, initial_direct_confidence=0.5
    )
    SimulationConfig(enable_stigmergy=True, stigmergy_deposit_rate=0.0)  # nunca deposita
    SimulationConfig(enable_stigmergy=False, stigmergy_deposit_rate=0.04)  # apagada: no aplica
    SimulationConfig(enable_stigmergy=False, stigmergy_deposit_rate=0.0)  # ablación de R19


@given(
    rate=st.floats(0.0, 1.0),
    first=st.floats(0.0, 1.0),
    minimum=st.floats(0.0, 0.3),
    enabled=st.booleans(),
)
def test_config_de_estigmergia_aceptada_deja_el_rastro_de_una_creencia_directa_nueva(
    rate: float, first: float, minimum: float, enabled: bool
) -> None:
    """Se rechaza sii, con la estigmergia activa y tasa positiva, el entorno real no guarda el
    rastro de una creencia directa nueva (confianza `initial_direct_confidence`)."""
    probe = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=1,
        min_confidence=minimum,
        stigmergy_deposit_rate=rate,
    )
    grid = ToroidalGrid2D(probe, np.random.Generator(np.random.PCG64(0)))
    grid.deposit_stigmergy(0, pat("p_0"), 1.0, first, 0)
    stored = grid.get_active_stigmergy_cells() == 1
    kwargs = {
        "enable_stigmergy": enabled,
        "stigmergy_deposit_rate": rate,
        "initial_direct_confidence": first,
        "min_confidence": minimum,
    }
    if enabled and rate > 0 and not stored:
        with pytest.raises(ValueError, match="stigmergy_deposit_rate"):
            SimulationConfig(**kwargs)  # type: ignore[arg-type]
    else:
        SimulationConfig(**kwargs)  # type: ignore[arg-type]


# --- Fase II-B: ADN compacto, contexto epigenético y configuración (D30, D31) ------------------

_PHASE25_FLAGS = (
    "enable_compact_dna",
    "enable_epigenetic_roles",
    "enable_plasmid_hgt",
    "enable_crispr_immunity",
    "enable_sporulation",
    "enable_telomere_senescence",
    "enable_sos_mutation",
    "enable_symbiotic_ratchet",
)


def test_epigenetic_role_miembros_y_valores() -> None:
    assert [m.name for m in EpigeneticRole] == ["NONE", "EXPLORER", "LIBRARIAN", "NERVE"]
    assert all(m.value == m.name for m in EpigeneticRole)
    assert EpigeneticRole.NERVE.value == "NERVE"


@pytest.mark.parametrize("cls", [CompactDNA, EpigeneticContext, ExpressedPhenotype])
def test_tipos_de_fase_iib_son_frozen(cls: type) -> None:
    assert cls.__dataclass_params__.frozen  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chromosome": ()},
        {"chromosome": (2**32,)},
        {"chromosome": (-1,)},
        {"chromosome": (1,), "plasmids": (3, 3)},
        {"chromosome": (1,), "crispr_memory": (5, 5)},
        {"chromosome": (1,), "plasmids": (2**32,)},
        {"chromosome": (1,), "crispr_memory": (-1,)},
    ],
)
def test_compact_dna_rechaza_construcciones_invalidas(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        CompactDNA(**kwargs)  # type: ignore[arg-type]


def test_compact_dna_acepta_bordes_y_repetidos_en_el_cromosoma() -> None:
    dna = CompactDNA(chromosome=(7, 7))
    assert dna.plasmids == () and dna.crispr_memory == ()
    CompactDNA(chromosome=(0, 2**32 - 1), plasmids=(0, 2**32 - 1), crispr_memory=(1, 2))
    with pytest.raises(FrozenInstanceError):
        dna.plasmids = (1,)  # type: ignore[misc]


def test_compact_dna_no_valida_longitudes() -> None:
    assert len(CompactDNA(chromosome=tuple(range(40))).chromosome) == 40
    assert len(CompactDNA(chromosome=(1,), plasmids=tuple(range(10))).plasmids) == 10


def test_campos_de_los_tipos_de_fase_iib() -> None:
    assert [f.name for f in fields(CompactDNA)] == ["chromosome", "plasmids", "crispr_memory"]
    assert [f.name for f in fields(EpigeneticContext)] == ["holon_level", "role", "energy_ratio"]
    assert [f.name for f in fields(ExpressedPhenotype)] == [
        "genome",
        "lifespan",
        "spore_threshold",
        "expressed_codons",
    ]


def test_epigenetic_context_por_defecto() -> None:
    ctx = EpigeneticContext()
    assert ctx.holon_level == 0
    assert ctx.role is EpigeneticRole.NONE
    assert ctx.energy_ratio == 1.0
    assert not hasattr(ctx, "z_layer")
    assert not any("spore" in f.name or "endospore" in f.name for f in fields(ctx))
    with pytest.raises(FrozenInstanceError):
        ctx.holon_level = 1  # type: ignore[misc]


def test_expressed_phenotype_inmutable() -> None:
    phen = ExpressedPhenotype(AgentGenome(), 600, 0.30, 9)
    assert (phen.lifespan, phen.spore_threshold, phen.expressed_codons) == (600, 0.30, 9)
    assert phen.genome == AgentGenome()
    with pytest.raises(FrozenInstanceError):
        phen.lifespan = 1  # type: ignore[misc]


def test_config_fase_iib_valores_por_defecto() -> None:
    cfg = SimulationConfig()
    for flag in _PHASE25_FLAGS:
        assert getattr(cfg, flag) is False
    expected: dict[str, object] = {
        "dna_codon_cost": 0.0002,
        "dna_point_mutation_rate": 0.05,
        "dna_duplication_rate": 0.02,
        "dna_deletion_rate": 0.02,
        "dna_min_length": 1,
        "dna_max_length": 32,
        "stress_energy_ratio": 0.35,
        "surplus_energy_ratio": 0.85,
        "dna_excision_rate": 0.02,
        "max_plasmids": 4,
        "hgt_rate": 0.05,
        "hgt_energy_ratio": 0.85,
        "crispr_eval_ticks": 20,
        "crispr_toxicity_threshold": 0.20,
        "crispr_memory_size": 4,
        "spore_energy_threshold": 0.30,
        "spore_cost_fraction": 0.05,
        "telomere_base_lifespan": 600,
        "telomere_min_lifespan": 150,
        "telomere_max_lifespan": 1200,
        "senescence_cost_rate": 1e-5,
        "sos_window": 50,
        "sos_hypermutation_factor": 4.0,
        "sos_high_fidelity_factor": 0.25,
        "sos_high_fidelity_energy_ratio": 1.5,
        "lock_composite_threshold": 3,
        "lock_coord_discount": 0.5,
    }
    for name, value in expected.items():
        assert getattr(cfg, name) == value, name
    assert SimulationConfig(**json.loads(json.dumps(cfg.to_dict()))) == cfg


def test_config_fase_iib_campos_al_final_en_orden() -> None:
    esperados = [
        "enable_compact_dna",
        "dna_codon_cost",
        "dna_point_mutation_rate",
        "dna_duplication_rate",
        "dna_deletion_rate",
        "dna_min_length",
        "dna_max_length",
        "stress_energy_ratio",
        "surplus_energy_ratio",
        "enable_epigenetic_roles",
        "enable_plasmid_hgt",
        "dna_excision_rate",
        "max_plasmids",
        "hgt_rate",
        "hgt_energy_ratio",
        "enable_crispr_immunity",
        "crispr_eval_ticks",
        "crispr_toxicity_threshold",
        "crispr_memory_size",
        "enable_sporulation",
        "spore_energy_threshold",
        "spore_cost_fraction",
        "enable_telomere_senescence",
        "telomere_base_lifespan",
        "telomere_min_lifespan",
        "telomere_max_lifespan",
        "senescence_cost_rate",
        "enable_sos_mutation",
        "sos_window",
        "sos_hypermutation_factor",
        "sos_high_fidelity_factor",
        "sos_high_fidelity_energy_ratio",
        "enable_symbiotic_ratchet",
        "lock_composite_threshold",
        "lock_coord_discount",
    ]
    names = [f.name for f in fields(SimulationConfig)]
    assert names[-len(esperados) :] == esperados
    assert names[-len(esperados) - 1] == "stigmergy_decay"


@pytest.mark.parametrize(
    "overrides",
    [
        {"hgt_rate": 1.5},
        {"lock_coord_discount": -0.1},
        {"dna_codon_cost": -0.001},
        {"dna_point_mutation_rate": 1.1},
        {"dna_point_mutation_rate": -0.1},
        {"dna_duplication_rate": 1.1},
        {"dna_deletion_rate": -0.1},
        {"dna_excision_rate": 2.0},
        {"spore_cost_fraction": 1.1},
        {"sos_high_fidelity_factor": -0.1},
        {"crispr_toxicity_threshold": -0.1},
        {"senescence_cost_rate": -1e-6},
        {"spore_energy_threshold": -0.1},
        {"stress_energy_ratio": 0.0},
        {"surplus_energy_ratio": 0.0},
        {"hgt_energy_ratio": 0.0},
        {"sos_hypermutation_factor": 0.0},
        {"sos_high_fidelity_energy_ratio": 0.0},
        {"stress_energy_ratio": 0.9, "surplus_energy_ratio": 0.85},
        {"stress_energy_ratio": 0.5, "surplus_energy_ratio": 0.5},
        {"dna_max_length": 8},
        {"dna_min_length": 10},
        {"dna_min_length": 0},
        {"max_plasmids": 0},
        {"crispr_eval_ticks": 0},
        {"crispr_memory_size": 0},
        {"sos_window": 0},
        {"lock_composite_threshold": 0},
        {"telomere_min_lifespan": 0},
        {"telomere_base_lifespan": 100},
        {"telomere_base_lifespan": 1300},
        {"telomere_max_lifespan": 500},
    ],
)
def test_config_fase_iib_validacion_siempre_activa(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError, match=next(iter(overrides))):
        SimulationConfig(**overrides)  # type: ignore[arg-type]


def test_config_fase_iib_acepta_bordes() -> None:
    SimulationConfig(
        dna_point_mutation_rate=0.0,
        hgt_rate=1.0,
        lock_coord_discount=1.0,
        dna_codon_cost=0.0,
        spore_energy_threshold=0.0,
        dna_min_length=9,
        dna_max_length=9,
        telomere_min_lifespan=600,
        telomere_max_lifespan=600,
    )


_DNA_ON: dict[str, object] = {"enable_evolution": True, "enable_compact_dna": True}


def test_config_adn_compacto_valido_por_defecto() -> None:
    cfg = SimulationConfig(**_DNA_ON)  # type: ignore[arg-type]
    assert cfg.enable_compact_dna


@pytest.mark.parametrize(
    ("overrides", "campo"),
    [
        ({"enable_evolution": False}, "enable_evolution"),
        ({"perception_radius": 0}, "perception_radius"),
        ({"comm_radius": 0}, "comm_radius"),
        ({"alpha_learning": 0.005}, "alpha_learning"),
        ({"memory_capacity": 5, "max_genome_memory_capacity": 4}, "max_genome_memory_capacity"),
        ({"spore_energy_threshold": 3.0, "reproduction_threshold": 2.2}, "spore_energy_threshold"),
    ],
)
def test_config_adn_compacto_rechaza_con_mensaje_del_campo(
    overrides: dict[str, object], campo: str
) -> None:
    kwargs = {**_DNA_ON, **overrides}
    with pytest.raises(ValueError, match=campo):
        SimulationConfig(**kwargs)  # type: ignore[arg-type]


def test_config_adn_compacto_radio_sobre_la_cota_de_expresion() -> None:
    # r_tope = (min(grid) - 1) // 2 = 4 con grilla 10: el borde es válido y 5 lo rechaza la
    # validación de la Fase I (`2 * max(r) < min(grid)`), que garantiza la cota de D31.
    cfg = SimulationConfig(grid_width=10, grid_height=10, perception_radius=4, **_DNA_ON)  # type: ignore[arg-type]
    assert cfg.perception_radius == 4
    for campo in ("perception_radius", "comm_radius"):
        with pytest.raises(ValueError, match=campo):
            SimulationConfig(grid_width=10, grid_height=10, **{campo: 5}, **_DNA_ON)  # type: ignore[arg-type]


def test_config_adn_compacto_capacidad_sobre_la_cota_de_expresion() -> None:
    # La cota de C_max la garantizan las validaciones de la Fase I y la Fase II.
    with pytest.raises(ValueError, match="memory_capacity"):
        SimulationConfig(
            num_world_patterns=12,
            memory_capacity=12,
            max_genome_memory_capacity=20,
            **_DNA_ON,  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="max_genome_memory_capacity"):
        SimulationConfig(memory_capacity=5, max_genome_memory_capacity=4, **_DNA_ON)  # type: ignore[arg-type]


def test_config_adn_compacto_bordes_de_las_bases() -> None:
    SimulationConfig(alpha_learning=0.01, **_DNA_ON)  # type: ignore[arg-type]
    SimulationConfig(alpha_learning=1.0, **_DNA_ON)  # type: ignore[arg-type]
    SimulationConfig(spore_energy_threshold=2.2, reproduction_threshold=2.2, **_DNA_ON)  # type: ignore[arg-type]
    SimulationConfig(
        memory_capacity=5,
        max_genome_memory_capacity=5,
        **_DNA_ON,  # type: ignore[arg-type]
    )


def test_config_sin_adn_no_valida_las_bases_de_expresion() -> None:
    SimulationConfig(alpha_learning=0.005)
    SimulationConfig(spore_energy_threshold=3.0, reproduction_threshold=2.2)


def test_config_dependencias_apagadas_dejan_banderas_inertes() -> None:
    SimulationConfig(
        enable_evolution=True,
        enable_holonic_hierarchy=True,
        enable_epigenetic_roles=True,
        enable_compact_dna=False,
    )
    SimulationConfig(enable_crispr_immunity=True, enable_sporulation=True)
    SimulationConfig(enable_epigenetic_roles=True, enable_plasmid_hgt=True)
    SimulationConfig(enable_symbiotic_ratchet=True)
    SimulationConfig(
        enable_telomere_senescence=True, enable_sos_mutation=True, enable_evolution=False
    )
    SimulationConfig(**{flag: True for flag in _PHASE25_FLAGS if flag != "enable_compact_dna"})  # type: ignore[arg-type]


# --- CompactDNA: tipos estrictos (D32) y propiedades -------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chromosome": [1, 2]},
        {"chromosome": (1,), "plasmids": [3]},
        {"chromosome": (1,), "crispr_memory": {5}},
        {"chromosome": (True,)},
        {"chromosome": (1.0,)},
        {"chromosome": (np.uint32(1),)},
        {"chromosome": (1,), "plasmids": (np.int64(3),)},
        {"chromosome": (1,), "crispr_memory": (False,)},
        {"chromosome": ("1",)},
    ],
)
def test_compact_dna_exige_tuplas_de_int_de_python(kwargs: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        CompactDNA(**kwargs)  # type: ignore[arg-type]


_codons = st.integers(min_value=0, max_value=2**32 - 1)
_out_of_range = st.one_of(st.integers(max_value=-1), st.integers(min_value=2**32))


@given(
    chromosome=st.lists(_codons, min_size=1, max_size=40),
    plasmids=st.lists(_codons, unique=True, max_size=10),
    crispr=st.lists(_codons, unique=True, max_size=10),
)
def test_compact_dna_acepta_toda_tupla_valida(
    chromosome: list[int], plasmids: list[int], crispr: list[int]
) -> None:
    dna = CompactDNA(tuple(chromosome), tuple(plasmids), tuple(crispr))
    assert dna.chromosome == tuple(chromosome)
    assert dna.plasmids == tuple(plasmids)
    assert dna.crispr_memory == tuple(crispr)


@given(
    codon=_out_of_range,
    where=st.sampled_from(["chromosome", "plasmids", "crispr_memory"]),
    prefix=st.lists(_codons, unique=True, max_size=5),
)
def test_compact_dna_rechaza_todo_codon_fuera_de_rango(
    codon: int, where: str, prefix: list[int]
) -> None:
    kwargs: dict[str, tuple[int, ...]] = {"chromosome": (1,)}
    kwargs[where] = (*prefix, codon) if where != "chromosome" else (1, codon)
    with pytest.raises(ValueError, match=where):
        CompactDNA(**kwargs)


@given(
    codon=_codons,
    where=st.sampled_from(["plasmids", "crispr_memory"]),
)
def test_compact_dna_rechaza_repetidos_en_plasmidos_y_crispr(codon: int, where: str) -> None:
    with pytest.raises(ValueError, match=where):
        CompactDNA(chromosome=(1,), **{where: (codon, codon)})
