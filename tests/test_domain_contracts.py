"""Tests de `domain-contracts`: tipos inmutables, puerto de entorno y `SimulationConfig`."""

import dataclasses
import json
from dataclasses import FrozenInstanceError, fields

import pytest

from ide.config import SimulationConfig
from ide.domain.ports import EnvironmentPort
from ide.domain.types import (
    ActionResult,
    AgentAction,
    KnowledgeUnit,
    Message,
    MessageType,
    Observation,
    Pattern,
    Resource,
    VisibleResource,
)


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
    cfg = SimulationConfig(num_world_patterns=8, memory_capacity=8, enforce_memory_constraint=False)
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
    ],
)
def test_valores_negativos(campo: str) -> None:
    with pytest.raises(ValueError, match=campo):
        SimulationConfig(**{campo: -1})


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
