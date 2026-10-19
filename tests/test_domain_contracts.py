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
        # 0.06 * 0.85 = 0.051 >= 0.05, pero tras un decaimiento (0.02) queda en 0.031
        {"stigmergy_deposit_rate": 0.06},
    ],
)
def test_config_rechaza_estigmergia_que_solo_borraria_rastros(overrides: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="stigmergy_deposit_rate"):
        SimulationConfig(enable_stigmergy=True, **overrides)  # type: ignore[arg-type]


def test_config_acepta_tasas_de_estigmergia_coherentes() -> None:
    # borde exacto, con valores binarios para que no haya redondeo: 0.25 * 0.5 - 0.0625 == 0.0625
    SimulationConfig(
        enable_stigmergy=True,
        stigmergy_deposit_rate=0.25,
        initial_direct_confidence=0.5,
        stigmergy_decay=0.0625,
        min_confidence=0.0625,
    )
    SimulationConfig(enable_stigmergy=True, stigmergy_deposit_rate=0.0)  # nunca deposita
    SimulationConfig(enable_stigmergy=False, stigmergy_deposit_rate=0.04)  # apagada: no aplica
    SimulationConfig(enable_stigmergy=False, stigmergy_deposit_rate=0.0)  # ablación de R19


@given(
    rate=st.floats(0.0, 1.0),
    first=st.floats(0.0, 1.0),
    minimum=st.floats(0.0, 0.3),
    decay=st.floats(0.0, 0.2),
    enabled=st.booleans(),
)
def test_config_de_estigmergia_aceptada_deja_un_rastro_que_resiste_un_decaimiento(
    rate: float, first: float, minimum: float, decay: float, enabled: bool
) -> None:
    """Se rechaza sii, con la estigmergia activa y tasa positiva, el rastro de una creencia
    directa nueva (confianza `initial_direct_confidence`) no sigue en el entorno real tras un
    decaimiento, es decir, cuando otro agente podría leerlo."""
    probe = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=1,
        min_confidence=minimum,
        stigmergy_deposit_rate=rate,
        stigmergy_decay=decay,
    )
    grid = ToroidalGrid2D(probe, np.random.Generator(np.random.PCG64(0)))
    grid.deposit_stigmergy(0, pat("p_0"), 1.0, first, 0)
    grid.step_dynamics(1)
    stored = grid.get_active_stigmergy_cells() == 1
    kwargs = {
        "enable_stigmergy": enabled,
        "stigmergy_deposit_rate": rate,
        "initial_direct_confidence": first,
        "min_confidence": minimum,
        "stigmergy_decay": decay,
    }
    if enabled and rate > 0 and not stored:
        with pytest.raises(ValueError, match="stigmergy_deposit_rate"):
            SimulationConfig(**kwargs)  # type: ignore[arg-type]
    else:
        SimulationConfig(**kwargs)  # type: ignore[arg-type]
