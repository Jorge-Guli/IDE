"""Tests de `micro-agent`: aislamiento, protocolo, caché efímero, comunicación y decisión."""

import ast
import inspect
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.epistemology import is_known
from ide.agent.evolution import genome_from_config
from ide.agent.micro_agent import MicroAgent
from ide.agent.protocol import BeliefExchangeProtocol
from ide.config import SimulationConfig
from ide.domain.extensions import AgentCapabilities, mutate_genome
from ide.domain.types import (
    ActionType,
    AgentAction,
    AgentGenome,
    KnowledgeUnit,
    Message,
    MessageType,
    Observation,
    Pattern,
    VisibleResource,
)

AGENT_DIR = Path(__file__).resolve().parents[1] / "src" / "ide" / "agent"
CFG = SimulationConfig()
MOVES = ((0, 1), (0, -1), (1, 0), (-1, 0))


def pat(i: int) -> Pattern:
    return Pattern((("id", f"p_{i}"),))


def ku(i: int, value: float = 1.0, conf: float = 0.9, tau: int = 0) -> KnowledgeUnit:
    return KnowledgeUnit(pat(i), value, conf, 1, tau, True)


def vis(rid: int, i: int, distance: int = 0, move: object = None) -> VisibleResource:
    return VisibleResource(rid, pat(i), move, distance, distance == 0)


def obs(
    resources: tuple[VisibleResource, ...] = (),
    neighbors: tuple[int, ...] = (),
    moves: tuple[object, ...] = MOVES,
    agent_id: int = 1,
) -> Observation:
    return Observation(agent_id, 0, resources, moves, neighbors)


def agent(agent_id: int = 1, **overrides: object) -> MicroAgent:
    return MicroAgent(agent_id, replace(CFG, **overrides))  # type: ignore[arg-type]


def rng(seed: int = 0) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))


# --- Auditorías sobre el AST -------------------------------------------------------------------


def agent_modules() -> list[Path]:
    # Recursivo: un subpaquete de `agent/` también queda bajo las auditorías.
    return sorted(AGENT_DIR.rglob("*.py"))


def test_auditoria_de_importaciones() -> None:
    forbidden = ("environments", "simulation", "experiments", "grid2d")
    for path in agent_modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [alias.name for alias in node.names]
            for name in names:
                assert not any(word in name for word in forbidden), (
                    f"{path.relative_to(AGENT_DIR)}: {name}"
                )


def test_auditoria_del_protocolo() -> None:
    for path in agent_modules():
        if path == AGENT_DIR / "protocol.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                func = node.func
                called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
                assert called != "Message", f"{path.relative_to(AGENT_DIR)} construye Message"
            if isinstance(node, ast.Name):
                assert node.id != "MessageType", (
                    f"{path.relative_to(AGENT_DIR)} referencia MessageType"
                )
            if isinstance(node, ast.Attribute):
                assert node.attr != "MessageType", (
                    f"{path.relative_to(AGENT_DIR)} referencia MessageType"
                )
            if isinstance(node, ast.ImportFrom):
                imported = [alias.name for alias in node.names]
                assert "MessageType" not in imported, (
                    f"{path.relative_to(AGENT_DIR)} importa MessageType"
                )


def test_auditoria_sin_alias_de_nombres_vigilados() -> None:
    # Un alias (`import ... as x`) burlaría las auditorías por nombre.
    watched = {"Message", "MessageType", "merge_social_belief", "types", "epistemology"}
    for path in agent_modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import | ast.ImportFrom):
                for alias in node.names:
                    leaf = alias.name.rsplit(".", 1)[-1]
                    assert alias.asname is None or leaf not in watched, (
                        f"{path.relative_to(AGENT_DIR)}: {alias.name}"
                    )


def references_by_scope(tree: ast.AST, name: str) -> list[str]:
    """Ruta completa de ámbitos (`<module>/Clase/función`) de cada referencia a `name`."""
    found: list[str] = []

    def visit(node: ast.AST, path: tuple[str, ...]) -> None:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            path = (*path, node.name)
        elif isinstance(node, ast.Lambda):
            path = (*path, "<lambda>")
        if (isinstance(node, ast.Name) and node.id == name) or (
            isinstance(node, ast.Attribute) and node.attr == name
        ):
            found.append("/".join(path))
        for child in ast.iter_child_nodes(node):
            visit(child, path)

    visit(tree, ("<module>",))
    return found


def test_asimilacion_social_solo_por_assimilate_testimony() -> None:
    # Fuera de `epistemology.py`, `merge_social_belief` sólo aparece en el método
    # `assimilate_testimony` de la clase de nivel superior `MicroAgent` de `micro_agent.py`.
    for path in agent_modules():
        if path == AGENT_DIR / "epistemology.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for scope in references_by_scope(tree, "merge_social_belief"):
            assert path == AGENT_DIR / "micro_agent.py", f"{path.relative_to(AGENT_DIR)}:{scope}"
            assert scope == "<module>/MicroAgent/assimilate_testimony", (
                f"{path.relative_to(AGENT_DIR)}:{scope}"
            )


def test_auditoria_de_ambitos_registra_cada_ambito() -> None:
    source = (
        "x = merge_social_belief\n"
        "f = lambda b: merge_social_belief(b)\n"
        "class A:\n    y = merge_social_belief\n"
        "def assimilate_testimony(a, b):\n    return merge_social_belief(b)\n"
        "class Outer:\n    class MicroAgent:\n"
        "        def assimilate_testimony(self, b):\n            return merge_social_belief(b)\n"
        "def Helper():\n    def assimilate_testimony():\n        return merge_social_belief\n"
        "class MicroAgent:\n    def assimilate_testimony(self, b):\n"
        "        return merge_social_belief(b)\n"
    )
    assert references_by_scope(ast.parse(source), "merge_social_belief") == [
        "<module>",
        "<module>/<lambda>",
        "<module>/A",
        "<module>/assimilate_testimony",
        "<module>/Outer/MicroAgent/assimilate_testimony",
        "<module>/Helper/assimilate_testimony",
        "<module>/MicroAgent/assimilate_testimony",
    ]


def test_protocolo_no_escribe_la_memoria_directamente() -> None:
    # El protocolo sólo modifica al agente a través de `assimilate_testimony`.
    forbidden = {"upsert", "remove", "decay_step", "learn_from_experience", "decay_memory"}
    tree = ast.parse((AGENT_DIR / "protocol.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden, f"protocol.py usa {node.attr}"
            assert not node.attr.startswith("_"), f"protocol.py accede a {node.attr}"


def imported_modules(path: Path) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            # También los nombres: `from . import micro_agent` no deja rastro en `module`.
            names += [node.module or ""] + [alias.name for alias in node.names]
    return names


def test_evolution_no_importa_micro_agent() -> None:
    # Sin ciclo: `micro_agent.py` importa `evolution.py`, nunca al revés (D20, regla 5).
    names = imported_modules(AGENT_DIR / "evolution.py")
    assert not any("micro_agent" in name for name in names), names


def test_ningun_modulo_del_agente_referencia_nullify_belief() -> None:
    # El control nulo de contenido lo aplica sólo el motor (D20, regla 4).
    for path in agent_modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            name = getattr(node, "id", None) or getattr(node, "attr", None)
            if isinstance(node, ast.alias):
                name = node.name
            assert name != "nullify_belief", path.relative_to(AGENT_DIR)


# --- Interfaz ----------------------------------------------------------------------------------


def test_firmas_publicas_canonicas() -> None:
    expected = {
        "__init__": ["self", "agent_id", "config", "trust_strategy", "protocol"],
        "perceive_and_emit_messages": ["self", "obs", "tick"],
        "process_incoming_messages": ["self", "messages", "tick"],
        "decide_action": ["self", "obs", "tick", "rng"],
        "learn_from_experience": ["self", "pattern", "real_value", "tick"],
        "decay_memory": ["self", "tick"],
        "get_effective_belief": ["self", "pattern"],
        "assimilate_testimony": ["self", "belief", "sender_id", "tick"],
    }
    for name, params in expected.items():
        assert list(inspect.signature(getattr(MicroAgent, name)).parameters) == params, name
    init = inspect.signature(MicroAgent.__init__).parameters
    assert init["trust_strategy"].default is None
    assert init["protocol"].default is None


def test_propiedades_de_solo_lectura() -> None:
    a = agent(7)
    assert a.agent_id == 7
    assert a.config == CFG
    assert a.capabilities == AgentCapabilities()
    assert len(a.memory) == 0
    for name in ("agent_id", "config", "memory", "capabilities"):
        assert isinstance(inspect.getattr_static(MicroAgent, name), property)


def test_capacidad_de_memoria_desde_la_configuracion() -> None:
    a = agent(memory_capacity=2)
    for i in range(3):
        a.learn_from_experience(pat(i), 1.0, 0)
    assert len(a.memory) == 2


class SilentProtocol(BeliefExchangeProtocol):
    def emit(self, agent: MicroAgent, obs: Observation, tick: int) -> list[Message]:
        return []


def test_protocolo_inyectado() -> None:
    a = MicroAgent(1, CFG, protocol=SilentProtocol())
    a.memory.upsert(ku(0), 0)
    assert a.perceive_and_emit_messages(obs((vis(10, 5),), neighbors=(2, 3)), 0) == []


# --- Caché efímero -----------------------------------------------------------------------------


def full_agent() -> MicroAgent:
    a = agent()
    for i in range(CFG.memory_capacity):
        a.memory.upsert(ku(i, conf=1.0, tau=0), 0)
    return a


def test_creencia_solo_en_cache_vive_un_tick() -> None:
    a = full_agent()
    merged = a.assimilate_testimony(ku(9, value=-1.0, conf=0.5), sender_id=2, tick=0)
    assert pat(9) not in a.memory
    assert a.get_effective_belief(pat(9)) == merged
    a.perceive_and_emit_messages(obs(), 1)
    assert a.get_effective_belief(pat(9)) is None


def test_memoria_tiene_prioridad_sobre_el_cache() -> None:
    a = full_agent()
    a.assimilate_testimony(ku(9, conf=0.5), sender_id=2, tick=0)
    a.learn_from_experience(pat(9), -1.0, 0)
    belief = a.get_effective_belief(pat(9))
    assert belief is not None
    assert belief == a.memory.get(pat(9))


# --- Asimilación social ------------------------------------------------------------------------


@dataclass(frozen=True)
class RecordingTrust:
    factor: float
    calls: list[tuple[int, int, float]]

    def compute_sender_trust(self, receiver_id: int, sender_id: int, base_gamma: float) -> float:
        self.calls.append((receiver_id, sender_id, base_gamma))
        return self.factor


def test_asimilacion_con_trust_strategy() -> None:
    trust = RecordingTrust(0.5, [])
    a = MicroAgent(4, CFG, trust_strategy=trust)
    merged = a.assimilate_testimony(ku(0, conf=0.8), sender_id=9, tick=3)
    assert trust.calls == [(4, 9, CFG.gamma_social_discount)]
    assert merged.confidence == pytest.approx(0.4, abs=1e-9)
    assert a.memory.get(pat(0)) == merged


def test_asimilacion_parte_de_la_creencia_efectiva() -> None:
    a = full_agent()
    first = a.assimilate_testimony(ku(9, conf=0.4), sender_id=2, tick=0)
    second = a.assimilate_testimony(ku(9, conf=0.4), sender_id=3, tick=0)
    assert first.evidence_count == 1
    assert second.evidence_count == 2


# --- Emisión -----------------------------------------------------------------------------------


def test_consulta_por_recurso_desconocido() -> None:
    messages = agent().perceive_and_emit_messages(obs((vis(10, 5),), neighbors=(2, 3)), 0)
    assert Message(MessageType.QUERY_PATTERN, 1, None, pat(5)) in messages


def test_sin_vecinos_no_hay_mensajes() -> None:
    a = agent()
    a.memory.upsert(ku(0), 0)
    assert a.perceive_and_emit_messages(obs((vis(10, 5),)), 0) == []


def test_consultas_limite_y_orden() -> None:
    a = agent(max_queries_per_tick=2, max_broadcast_per_tick=0)
    a.memory.upsert(ku(1, conf=0.9), 0)  # conocido: no se consulta
    a.memory.upsert(ku(4, conf=0.2), 0)  # confianza baja: se consulta
    resources = (
        vis(30, 1, 0),
        vis(20, 7, 1, (1, 0)),
        vis(21, 4, 1, (1, 0)),
        vis(22, 7, 1, (0, 1)),
        vis(10, 3, 2, (0, 1)),
    )
    messages = a.perceive_and_emit_messages(obs(resources, neighbors=(2,)), 0)
    assert [m.pattern for m in messages] == [pat(4), pat(7)]
    assert all(m.msg_type is MessageType.QUERY_PATTERN for m in messages)
    assert all(m.recipient_id is None and m.belief is None for m in messages)


def test_consultas_usan_la_distancia_minima_del_patron() -> None:
    # No depende de que el entorno entregue los recursos ordenados por distancia.
    a = agent(max_queries_per_tick=1, max_broadcast_per_tick=0)
    resources = (vis(1, 7, 3, (1, 0)), vis(2, 3, 2, (1, 0)), vis(3, 7, 1, (0, 1)))
    messages = a.perceive_and_emit_messages(obs(resources, neighbors=(2,)), 0)
    assert [m.pattern for m in messages] == [pat(7)]


def test_consultas_deshabilitadas() -> None:
    a = agent(max_queries_per_tick=0)
    assert a.perceive_and_emit_messages(obs((vis(10, 5),), neighbors=(2,)), 0) == []


def test_solo_se_difunde_conocimiento_confiable() -> None:
    a = agent(max_broadcast_per_tick=2)
    strong, weak = ku(0, conf=0.9), ku(1, conf=0.2)
    a.memory.upsert(strong, 0)
    a.memory.upsert(weak, 0)
    messages = a.perceive_and_emit_messages(obs(neighbors=(2,)), 0)
    assert messages == [Message(MessageType.BROADCAST_BELIEF, 1, None, pat(0), strong)]


def test_difusion_por_utilidad_y_luego_patron() -> None:
    a = agent(max_broadcast_per_tick=2, max_queries_per_tick=2)
    for unit in (ku(2, conf=0.6), ku(0, conf=0.6), ku(1, conf=0.9)):
        a.memory.upsert(unit, 0)
    messages = a.perceive_and_emit_messages(obs((vis(10, 5),), neighbors=(2,)), 0)
    assert [m.msg_type for m in messages] == [
        MessageType.QUERY_PATTERN,
        MessageType.BROADCAST_BELIEF,
        MessageType.BROADCAST_BELIEF,
    ]
    assert [m.pattern for m in messages[1:]] == [pat(1), pat(0)]


def test_no_se_responde_desde_el_cache() -> None:
    a = full_agent()
    cached = a.assimilate_testimony(ku(9, conf=0.9), sender_id=2, tick=0)
    assert pat(9) not in a.memory
    assert cached.confidence >= CFG.decision_conf_threshold
    query = Message(MessageType.QUERY_PATTERN, 3, None, pat(9))
    assert a.process_incoming_messages([query], 0) == []


# --- Recepción ---------------------------------------------------------------------------------


def test_vecino_informado_responde() -> None:
    a = agent(2)
    k = ku(5, value=-1.0, conf=0.85)
    a.memory.upsert(k, 0)
    out = a.process_incoming_messages([Message(MessageType.QUERY_PATTERN, 1, None, pat(5))], 0)
    assert out == [Message(MessageType.QUERY_RESPONSE, 2, 1, pat(5), k)]


def test_no_responde_sin_confianza_suficiente() -> None:
    a = agent(2)
    a.memory.upsert(ku(5, conf=0.2), 0)
    out = a.process_incoming_messages([Message(MessageType.QUERY_PATTERN, 1, None, pat(5))], 0)
    assert out == []


def test_respuesta_independiente_del_orden_de_la_bandeja() -> None:
    query = Message(MessageType.QUERY_PATTERN, 1, None, pat(5))
    rumor = Message(MessageType.BROADCAST_BELIEF, 3, None, pat(5), ku(5, conf=1.0))
    outputs = []
    for inbox in ([rumor, query], [query, rumor]):
        a = agent(2)
        a.memory.upsert(ku(5, conf=0.6), 0)
        outputs.append((a.process_incoming_messages(inbox, 1), a.get_effective_belief(pat(5))))
    assert outputs[0] == outputs[1]
    assert outputs[0][0] == [Message(MessageType.QUERY_RESPONSE, 2, 1, pat(5), ku(5, conf=0.6))]


def test_testimonio_previo_no_suprime_una_respuesta() -> None:
    # Un broadcast que desplaza a ρ5 de la memoria llena no impide responder por ρ5.
    a = agent(2)
    for i in (5, 6, 7):
        a.memory.upsert(ku(i, conf=0.4), 0)
    rumor = Message(MessageType.BROADCAST_BELIEF, 3, None, pat(9), ku(9, conf=1.0))
    out = a.process_incoming_messages(
        [rumor, Message(MessageType.QUERY_PATTERN, 1, None, pat(5))], 0
    )
    assert pat(5) not in a.memory
    assert out == [Message(MessageType.QUERY_RESPONSE, 2, 1, pat(5), ku(5, conf=0.4))]


def test_ignora_mensajes_propios_y_ajenos() -> None:
    a = agent(2)
    a.memory.upsert(ku(5), 0)
    messages = [
        Message(MessageType.QUERY_PATTERN, 2, None, pat(5)),
        Message(MessageType.BROADCAST_BELIEF, 2, None, pat(6), ku(6)),
        Message(MessageType.QUERY_RESPONSE, 3, 4, pat(7), ku(7)),
    ]
    assert a.process_incoming_messages(messages, 0) == []
    assert a.get_effective_belief(pat(6)) is None
    assert a.get_effective_belief(pat(7)) is None


def test_asimilacion_de_mensajes_en_orden() -> None:
    a = agent(1)
    messages = [
        Message(MessageType.BROADCAST_BELIEF, 2, None, pat(5), ku(5, conf=0.8)),
        Message(MessageType.QUERY_RESPONSE, 3, 1, pat(5), ku(5, conf=0.8)),
    ]
    assert a.process_incoming_messages(messages, 4) == []
    belief = a.get_effective_belief(pat(5))
    assert belief is not None
    assert belief.evidence_count == 2
    assert belief.confidence == pytest.approx(0.6 + 0.15 * 0.6 * 0.4, abs=1e-9)


def test_respuesta_permite_evitar_un_recurso_danino() -> None:
    a = agent(1, epsilon_explore=1.0)
    response = Message(MessageType.QUERY_RESPONSE, 2, 1, pat(5), ku(5, value=-1.0, conf=0.85))
    a.process_incoming_messages([response], 0)
    belief = a.get_effective_belief(pat(5))
    assert belief is not None
    assert belief.confidence == pytest.approx(0.6375, abs=1e-9)
    action = a.decide_action(obs((vis(10, 5),)), 0, rng())
    assert action.action_type is not ActionType.INTERACT


# --- Decisión ----------------------------------------------------------------------------------


def test_consumo_de_benefico_conocido() -> None:
    a = agent()
    a.memory.upsert(ku(1, conf=0.70), 0)
    assert a.decide_action(obs((vis(10, 1),)), 0, rng()) == AgentAction(ActionType.INTERACT, 10)


def test_consumo_del_mayor_valor_esperado_con_desempate() -> None:
    a = agent()
    a.memory.upsert(ku(1, value=0.5, conf=0.8), 0)
    a.memory.upsert(ku(2, value=1.0, conf=0.8), 0)
    resources = (vis(10, 1), vis(12, 2), vis(11, 2))
    assert a.decide_action(obs(resources), 0, rng()).target == 11


def test_exploracion_garantizada() -> None:
    a = agent(epsilon_explore=1.0)
    resources = (vis(12, 4), vis(10, 3))
    assert a.decide_action(obs(resources), 0, rng()) == AgentAction(ActionType.INTERACT, 10)


def test_exploracion_extrae_un_unico_random() -> None:
    a = agent(epsilon_explore=1.0)
    generator, reference = rng(5), rng(5)
    a.decide_action(obs((vis(10, 3),)), 0, generator)
    reference.random()
    assert generator.bit_generator.state == reference.bit_generator.state


def test_exploracion_deshabilitada() -> None:
    a = agent(epsilon_explore=0.0)
    action = a.decide_action(obs((vis(10, 3),)), 0, rng())
    assert action.action_type is not ActionType.INTERACT


def test_exploracion_no_considera_creencias_debiles_conocidas() -> None:
    # Una creencia con c < umbral cuenta como no conocida: es candidata a exploración.
    a = agent(epsilon_explore=1.0)
    a.memory.upsert(ku(3, value=-1.0, conf=0.2), 0)
    assert a.decide_action(obs((vis(10, 3),)), 0, rng()).target == 10


def test_evitacion_de_unica_opcion_toxica() -> None:
    a = agent(epsilon_explore=1.0)
    a.memory.upsert(ku(2, value=-1.0, conf=0.70), 0)
    action = a.decide_action(obs((vis(10, 2),)), 0, rng())
    assert action.action_type is ActionType.MOVE
    assert action.target in MOVES


def test_navegacion_por_recommended_move() -> None:
    a = agent()
    a.memory.upsert(ku(1, conf=0.80), 0)
    action = a.decide_action(obs((vis(10, 1, 2, (1, 0)),)), 0, rng())
    assert action == AgentAction(ActionType.MOVE, (1, 0))


def test_navegacion_al_benefico_mas_cercano() -> None:
    a = agent()
    a.memory.upsert(ku(1, conf=0.80), 0)
    a.memory.upsert(ku(2, value=-1.0, conf=0.80), 0)
    resources = (vis(5, 2, 1, (0, 1)), vis(11, 1, 2, (1, 0)), vis(9, 1, 2, (-1, 0)))
    assert a.decide_action(obs(resources), 0, rng()).target == (-1, 0)


def test_ablacion_de_la_navegacion() -> None:
    a = agent(enable_navigation=False)
    a.memory.upsert(ku(1, conf=0.80), 0)
    action = a.decide_action(obs((vis(10, 1, 2, (1, 0)),)), 0, rng(11))
    reference = rng(11)
    assert action == AgentAction(ActionType.MOVE, MOVES[int(reference.integers(len(MOVES)))])


class SpyAgent(MicroAgent):
    def __init__(self, config: SimulationConfig) -> None:
        super().__init__(1, config)
        self.looked_up: list[Pattern] = []

    def get_effective_belief(self, pattern: Pattern) -> KnowledgeUnit | None:
        self.looked_up.append(pattern)
        return super().get_effective_belief(pattern)


def test_sin_navegacion_no_consulta_recursos_lejanos() -> None:
    a = SpyAgent(replace(CFG, enable_navigation=False, epsilon_explore=0.0))
    a.memory.upsert(ku(1, conf=0.8), 0)
    action = a.decide_action(obs((vis(10, 3), vis(11, 1, 2, (1, 0)))), 0, rng(4))
    assert a.looked_up == [pat(3)]
    reference = rng(4)
    reference.random()
    assert action == AgentAction(ActionType.MOVE, MOVES[int(reference.integers(len(MOVES)))])


def test_caminata_aleatoria() -> None:
    a = agent()
    action = a.decide_action(obs(), 0, rng(3))
    reference = rng(3)
    assert action == AgentAction(ActionType.MOVE, MOVES[int(reference.integers(len(MOVES)))])


def test_sin_movimientos_posibles_idle() -> None:
    assert agent().decide_action(obs(moves=()), 0, rng()) == AgentAction(ActionType.IDLE)


# --- Aprendizaje y olvido ----------------------------------------------------------------------


def test_aprendizaje_con_memoria_llena() -> None:
    a = full_agent()
    a.learn_from_experience(pat(9), -0.3, 5)
    belief = a.memory.get(pat(9))
    assert belief is not None
    assert belief.from_direct_experience is True
    assert len(a.memory) == CFG.memory_capacity


def test_aprendizaje_parte_del_cache() -> None:
    a = full_agent()
    a.assimilate_testimony(ku(9, conf=0.8), sender_id=2, tick=0)
    a.learn_from_experience(pat(9), 1.0, 1)
    belief = a.memory.get(pat(9))
    assert belief is not None
    assert belief.evidence_count == 2
    assert belief.confidence == pytest.approx(0.6 + 0.3 * 0.4, abs=1e-9)


def test_decaimiento_de_memoria() -> None:
    a = agent()
    a.memory.upsert(ku(0, conf=0.5, tau=0), 0)
    a.memory.upsert(ku(1, conf=CFG.min_confidence, tau=0), 0)
    a.decay_memory(1)
    unit = a.memory.get(pat(0))
    assert unit is not None
    assert unit.confidence == pytest.approx(0.5 - CFG.passive_conf_decay, abs=1e-9)
    assert pat(1) not in a.memory


# --- Propiedades -------------------------------------------------------------------------------

memory_beliefs = st.lists(
    st.tuples(
        st.integers(0, 5),
        st.floats(-1.0, 1.0, allow_nan=False),
        st.floats(0.0, 1.0, allow_nan=False),
    ),
    max_size=3,
)
visible = st.lists(
    st.tuples(st.integers(0, 5), st.integers(0, 3), st.sampled_from(MOVES)), max_size=8
).map(
    lambda items: tuple(
        sorted(
            (vis(rid, i, d, None if d == 0 else move) for rid, (i, d, move) in enumerate(items)),
            key=lambda r: (r.distance, r.resource_id),
        )
    )
)


def loaded_agent(beliefs: list[tuple[int, float, float]], **overrides: object) -> MicroAgent:
    a = agent(**overrides)
    for i, value, conf in beliefs:
        a.memory.upsert(ku(i, value=value, conf=conf), 0)
    return a


@given(memory_beliefs, visible, st.floats(0.0, 1.0), st.integers(0, 2**32 - 1))
def test_propiedad_nunca_consume_un_danino_conocido(
    beliefs: list[tuple[int, float, float]],
    resources: tuple[VisibleResource, ...],
    epsilon: float,
    seed: int,
) -> None:
    a = loaded_agent(beliefs, epsilon_explore=epsilon)
    action = a.decide_action(obs(resources), 0, rng(seed))
    if action.action_type is ActionType.INTERACT:
        target = next(r for r in resources if r.resource_id == action.target)
        assert target.is_reachable_now
        belief = a.get_effective_belief(target.pattern)
        assert not (
            belief is not None
            and belief.confidence >= CFG.decision_conf_threshold
            and belief.predicted_value < 0
        )
    elif action.action_type is ActionType.MOVE:
        assert action.target in MOVES


@given(memory_beliefs, visible, st.integers(0, 2**32 - 1))
def test_propiedad_decision_determinista(
    beliefs: list[tuple[int, float, float]], resources: tuple[VisibleResource, ...], seed: int
) -> None:
    first = loaded_agent(beliefs).decide_action(obs(resources), 0, rng(seed))
    second = loaded_agent(beliefs).decide_action(obs(resources), 0, rng(seed))
    assert first == second


@given(memory_beliefs, visible, st.integers(0, 3), st.integers(0, 3))
def test_propiedad_emision_acotada_y_ordenada(
    beliefs: list[tuple[int, float, float]],
    resources: tuple[VisibleResource, ...],
    max_queries: int,
    max_broadcast: int,
) -> None:
    a = loaded_agent(
        beliefs, max_queries_per_tick=max_queries, max_broadcast_per_tick=max_broadcast
    )
    messages = a.perceive_and_emit_messages(obs(resources, neighbors=(2,)), 0)
    queries = [m for m in messages if m.msg_type is MessageType.QUERY_PATTERN]
    broadcasts = [m for m in messages if m.msg_type is MessageType.BROADCAST_BELIEF]
    assert messages == queries + broadcasts
    assert len(queries) <= max_queries and len(broadcasts) <= max_broadcast
    assert len({m.pattern for m in queries}) == len(queries)
    assert {m.pattern for m in queries} <= {r.pattern for r in resources}
    for m in broadcasts:
        assert m.belief is not None and m.belief.confidence >= CFG.decision_conf_threshold
        assert a.memory.get(m.pattern) == m.belief

    # Consultas (spec "Emisión de Consultas en Vivo"): sólo patrones no conocidos; si hubo
    # lugar se consultaron todos; y ningún desconocido omitido precede a uno consultado en
    # (distancia mínima del patrón, pattern).
    def rank(pattern: Pattern) -> tuple[int, Pattern]:
        return (min(r.distance for r in resources if r.pattern == pattern), pattern)

    queried = [m.pattern for m in queries]
    unknown = {r.pattern for r in resources} - {
        r.pattern for r in resources if is_known(a.get_effective_belief(r.pattern), CFG)
    }
    assert set(queried) <= unknown
    assert [rank(q) for q in queried] == sorted(rank(q) for q in queried)
    if len(queried) < max_queries:
        assert set(queried) == unknown
    for omitted in sorted(unknown - set(queried)):
        assert all(rank(omitted) > rank(q) for q in queried)

    # Broadcasts (spec "Difusión Espontánea Priorizada"): utilidad no creciente; si hubo lugar
    # se difundieron todas las confiables; y ninguna omitida supera a una difundida.
    def utility(unit: KnowledgeUnit) -> float:
        return a.memory.compute_utility(unit, 0)

    sent = [m.belief for m in broadcasts if m.belief is not None]
    reliable = [u for u in a.memory.all_units() if u.confidence >= CFG.decision_conf_threshold]
    assert len({u.pattern for u in sent}) == len(sent)
    assert all((-utility(x), x.pattern) < (-utility(y), y.pattern) for x, y in pairwise(sent))
    if len(sent) < max_broadcast:
        assert sorted(u.pattern for u in sent) == sorted(u.pattern for u in reliable)
    for omitted in (u for u in reliable if u not in sent):
        assert all((-utility(omitted), omitted.pattern) > (-utility(x), x.pattern) for x in sent)


# --- Fase II: nodo holónico de nivel cero, energía y linaje ------------------------------------


def test_nodo_de_nivel_cero_y_estado_de_linaje() -> None:
    a = MicroAgent(7, CFG)
    assert a.node_id == 7
    assert a.holon_level == 0
    assert a.leaf_agents == (a,)
    assert a.generation == 0
    assert a.parent_id is None
    assert a.energy == CFG.initial_energy
    assert a.genome == genome_from_config(CFG)
    assert a.config is CFG  # sin `replace`: idéntico a la Fase I
    for name in (
        "energy",
        "generation",
        "parent_id",
        "genome",
        "node_id",
        "holon_level",
        "leaf_agents",
        "effective_capacity",
    ):
        assert isinstance(inspect.getattr_static(MicroAgent, name), property), name


def test_capacidad_efectiva_y_memoria_colectiva_de_una_hoja() -> None:
    a = agent(memory_capacity=2)
    a.memory.upsert(ku(3), 0)
    a.memory.upsert(ku(1, conf=0.4), 0)
    assert a.effective_capacity == 2
    assert a.collective_memory() == {pat(1): ku(1, conf=0.4), pat(3): ku(3)}
    assert list(a.collective_memory()) == [pat(1), pat(3)]


def test_apply_energy_delta_suma_y_resta() -> None:
    a = agent()
    a.apply_energy_delta(0.45)
    assert a.energy == pytest.approx(CFG.initial_energy + 0.45, abs=1e-9)
    a.apply_energy_delta(-2.5)
    assert a.energy == pytest.approx(CFG.initial_energy - 2.05, abs=1e-9)


def test_from_lineage_expresa_el_genoma_en_la_configuracion() -> None:
    genome = AgentGenome(0.2, 0.5, 0.3, 0.9, 5, 1, 3)
    trust, protocol = RecordingTrust(0.5, []), SilentProtocol()
    child = MicroAgent.from_lineage(
        11, CFG, genome, 0.8, 3, 4, trust_strategy=trust, protocol=protocol
    )
    assert (child.agent_id, child.energy, child.generation, child.parent_id) == (11, 0.8, 3, 4)
    assert child.genome == genome
    assert child.config == replace(
        CFG,
        alpha_learning=0.2,
        gamma_social_discount=0.5,
        epsilon_explore=0.3,
        memory_capacity=5,
        perception_radius=1,
        comm_radius=3,
    )
    assert child.memory.capacity == 5 and child.effective_capacity == 5
    assert child.perceive_and_emit_messages(obs((vis(10, 5),), neighbors=(2,)), 0) == []
    child.assimilate_testimony(ku(0, conf=0.8), sender_id=2, tick=0)
    assert trust.calls == [(11, 2, 0.5)]


def test_creacion_de_descendiente_con_conservacion_de_energia() -> None:
    parent = MicroAgent.from_lineage(5, CFG, genome_from_config(CFG), 2.0, 1, None)
    parent.memory.upsert(ku(0), 0)
    child = parent.create_offspring(child_id=99, tick=25, rng=rng())
    assert parent.energy == pytest.approx(1.0, abs=1e-9)
    assert (child.agent_id, child.parent_id, child.generation) == (99, 5, 2)
    assert child.energy == pytest.approx(1.0, abs=1e-9)
    assert len(child.memory) == 0


def test_particion_exacta_de_energia_y_linaje() -> None:
    parent = MicroAgent.from_lineage(4, CFG, genome_from_config(CFG), 2.4, 2, 1)
    child = parent.create_offspring(child_id=30, tick=0, rng=rng())
    assert (child.parent_id, child.generation) == (4, 3)
    assert child.energy == pytest.approx(1.2, abs=1e-9)
    assert parent.energy == pytest.approx(1.2, abs=1e-9)
    assert parent.energy + child.energy == pytest.approx(2.4, abs=1e-12)


def test_descendiente_hereda_estrategia_de_confianza_y_protocolo() -> None:
    trust = RecordingTrust(0.5, [])
    parent = MicroAgent(1, CFG, trust_strategy=trust, protocol=SilentProtocol())
    child = parent.create_offspring(child_id=2, tick=0, rng=rng())
    assert child.perceive_and_emit_messages(obs((vis(10, 5),), neighbors=(3,)), 0) == []
    child.assimilate_testimony(ku(0), sender_id=1, tick=0)
    assert trust.calls == [(2, 1, child.config.gamma_social_discount)]


def test_clonacion_exacta_bajo_ablacion_de_mutacion() -> None:
    cfg = replace(CFG, mutation_rate=0.0, discrete_mutation_prob=0.0)
    parent = MicroAgent(1, cfg)
    generator, reference = rng(3), rng(3)
    child = parent.create_offspring(child_id=2, tick=0, rng=generator)
    assert child.genome == parent.genome
    assert generator.bit_generator.state == reference.bit_generator.state


def test_descendiente_muta_con_mutate_genome() -> None:
    cfg = replace(CFG, mutation_rate=0.2, discrete_mutation_prob=1.0)
    parent = MicroAgent(1, cfg)
    child = parent.create_offspring(child_id=2, tick=0, rng=rng(8))
    assert child.genome == mutate_genome(parent.genome, cfg, rng(8))
    assert child.config.memory_capacity == child.genome.memory_capacity


def test_descendiente_toma_el_genoma_del_donante() -> None:
    cfg = replace(CFG, mutation_rate=0.0, discrete_mutation_prob=0.0)
    donor = AgentGenome(memory_capacity=5, bond_affinity=0.1)
    child = MicroAgent(1, cfg).create_offspring(2, 0, rng(), genome_source=donor)
    assert child.genome == donor
    assert child.memory.capacity == 5


# --- Fase II: creencia propia y vista del holón (R22) -------------------------------------------


def test_own_belief_es_memoria_y_luego_cache_propio() -> None:
    a = full_agent()
    cached = a.assimilate_testimony(ku(9, conf=0.5), sender_id=2, tick=0)
    assert a.own_belief(pat(9)) == cached
    assert a.own_belief(pat(0)) == a.memory.get(pat(0))
    assert a.own_belief(pat(8)) is None


def test_vista_del_holon_sobrevive_a_la_percepcion_y_se_borra_con_clear() -> None:
    a = agent()
    view = ku(4, value=-1.0, conf=0.9)
    a.inject_ephemeral_belief(view)
    assert a.get_effective_belief(pat(4)) == view
    assert a.own_belief(pat(4)) is None
    a.perceive_and_emit_messages(obs(), 1)
    assert a.get_effective_belief(pat(4)) == view
    a.clear_holon_beliefs()
    assert a.get_effective_belief(pat(4)) is None


def test_creencia_propia_tiene_prioridad_sobre_la_vista_del_holon() -> None:
    a = full_agent()
    a.inject_ephemeral_belief(ku(0, value=-1.0, conf=0.95))
    a.inject_ephemeral_belief(ku(9, value=-1.0, conf=0.95))
    cached = a.assimilate_testimony(ku(9, conf=0.6), sender_id=2, tick=0)
    assert a.get_effective_belief(pat(0)) == a.memory.get(pat(0))
    assert a.get_effective_belief(pat(9)) == cached


def test_la_vista_del_holon_no_contamina_el_aprendizaje_propio() -> None:
    a, reference = agent(), agent()
    a.inject_ephemeral_belief(ku(0, value=-1.0, conf=0.9))
    a.learn_from_experience(pat(0), 1.0, 3)
    reference.learn_from_experience(pat(0), 1.0, 3)
    assert a.memory.get(pat(0)) == reference.memory.get(pat(0))
    assert a.own_belief(pat(0)) == reference.own_belief(pat(0))


def test_la_vista_del_holon_no_entra_en_la_asimilacion_social() -> None:
    a, reference = agent(), agent()
    a.inject_ephemeral_belief(ku(0, value=1.0, conf=0.9))
    merged = a.assimilate_testimony(ku(0, value=1.0, conf=0.8), sender_id=2, tick=0)
    assert merged == reference.assimilate_testimony(ku(0, value=1.0, conf=0.8), 2, 0)
    assert merged.evidence_count == 1


def test_la_vista_del_holon_guia_la_decision_y_evita_la_consulta() -> None:
    a = agent(max_broadcast_per_tick=0)
    a.inject_ephemeral_belief(ku(5, conf=0.9))
    assert a.perceive_and_emit_messages(obs((vis(10, 5),), neighbors=(2,)), 0) == []
    assert a.decide_action(obs((vis(10, 5),)), 0, rng()) == AgentAction(ActionType.INTERACT, 10)


def test_no_se_responde_ni_difunde_desde_la_vista_del_holon() -> None:
    a = agent(2, max_broadcast_per_tick=3)
    a.inject_ephemeral_belief(ku(5, conf=0.9))
    query = Message(MessageType.QUERY_PATTERN, 1, None, pat(5))
    assert a.process_incoming_messages([query], 0) == []
    assert a.perceive_and_emit_messages(obs(neighbors=(1,)), 0) == []
