"""Tests del puerto de política (design D45): `PolicyPort`, `HandwrittenPolicy` y la delegación."""

import ast
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.epistemology import is_known
from ide.agent.micro_agent import MicroAgent
from ide.agent.policy import HandwrittenPolicy, PolicyPort
from ide.config import SimulationConfig
from ide.domain.types import (
    ActionType,
    AgentAction,
    KnowledgeUnit,
    Observation,
    Pattern,
    VisibleResource,
)

POLICY_PATH = Path(__file__).resolve().parents[1] / "src" / "ide" / "agent" / "policy.py"
CFG = SimulationConfig()
MOVES = ((0, 1), (0, -1), (1, 0), (-1, 0))


def pat(i: int) -> Pattern:
    return Pattern((("id", f"p_{i}"),))


def rng(seed: int = 0) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))


def legacy_decide(agent: MicroAgent, obs: Observation, rng: np.random.Generator) -> AgentAction:
    """Referencia: cuerpo literal de `decide_action` en e0e494e (previo al bloque 7).

    Sólo cambia `self` por `agent` (y `self._config` por `agent.config`).
    """
    navigate = agent.config.enable_navigation
    beneficial: list[tuple[float, int]] = []  # (-v̂·c, resource_id): `min` elige el mejor
    unknown: list[VisibleResource] = []
    goals: list[VisibleResource] = []
    for res in obs.visible_resources:
        if not (res.is_reachable_now or navigate):
            continue
        belief = agent.get_effective_belief(res.pattern)
        if not is_known(belief, agent.config):
            if res.is_reachable_now:
                unknown.append(res)
        elif belief.predicted_value > 0:
            if res.is_reachable_now:
                beneficial.append((-belief.predicted_value * belief.confidence, res.resource_id))
            else:
                goals.append(res)

    if beneficial:
        return AgentAction(ActionType.INTERACT, min(beneficial)[1])
    if unknown and rng.random() < agent.config.epsilon_explore:
        target = min(unknown, key=lambda r: r.resource_id)
        return AgentAction(ActionType.INTERACT, target.resource_id)
    if goals:
        goal = min(goals, key=lambda r: (r.distance, r.resource_id))
        return AgentAction(ActionType.MOVE, goal.recommended_move)
    if not obs.available_moves:
        return AgentAction(ActionType.IDLE)
    return AgentAction(
        ActionType.MOVE, obs.available_moves[int(rng.integers(len(obs.available_moves)))]
    )


@dataclass
class RecordingPolicy:
    calls: list[tuple[object, ...]] = field(default_factory=list)

    def decide(
        self,
        agent: MicroAgent,
        obs: Observation,
        social: object | None,
        tick: int,
        rng: np.random.Generator,
    ) -> AgentAction:
        self.calls.append((agent, obs, social, tick, rng))
        return AgentAction(ActionType.IDLE)


class IdlePolicy:
    def decide(
        self,
        agent: MicroAgent,
        obs: Observation,
        social: object | None,
        tick: int,
        rng: np.random.Generator,
    ) -> AgentAction:
        return AgentAction(ActionType.IDLE)


def an_obs(resources: tuple[VisibleResource, ...] = ()) -> Observation:
    return Observation(1, 0, resources, MOVES, ())


def test_politica_de_prueba_conforme_al_puerto() -> None:
    policy: PolicyPort = IdlePolicy()
    a = MicroAgent(1, CFG, policy=policy)
    assert a.decide_action(an_obs(), 3, rng()) == AgentAction(ActionType.IDLE)


def test_delegacion_con_y_sin_social() -> None:
    policy = RecordingPolicy()
    a = MicroAgent(1, CFG, policy=policy)
    o, g, social = an_obs(), rng(), object()
    a.decide_action(o, 5, g)
    a.decide_action(o, 6, g, social)
    assert policy.calls[0] == (a, o, None, 5, g)
    assert policy.calls[1] == (a, o, social, 6, g)


def test_politica_por_defecto_es_handwritten() -> None:
    a = MicroAgent(7, SimulationConfig())
    assert isinstance(a.policy, HandwrittenPolicy)
    a.learn_from_experience(pat(0), 1.0, 0)
    o = an_obs((VisibleResource(3, pat(0), None, 0, True),))
    g1, g2 = rng(4), rng(4)
    assert a.decide_action(o, 1, g1) == HandwrittenPolicy().decide(a, o, None, 1, g2)
    assert g1.bit_generator.state == g2.bit_generator.state


def test_herencia_de_la_politica() -> None:
    policy = RecordingPolicy()
    parent = MicroAgent(1, CFG, policy=policy)
    child = parent.create_offspring(2, 1, rng())
    assert child.policy is policy
    assert child.create_offspring(3, 2, rng()).policy is policy
    child.decide_action(an_obs(), 4, rng())
    assert policy.calls[-1][0] is child
    dna_cfg = replace(CFG, enable_evolution=True, enable_compact_dna=True)
    dna_parent = MicroAgent(1, dna_cfg, policy=policy)
    assert dna_parent.create_offspring(2, 1, rng()).policy is policy
    donor = dna_parent.dna
    assert donor is not None
    assert dna_parent.create_offspring(3, 1, rng(), dna_source=donor).policy is policy


def test_from_lineage_acepta_politica() -> None:
    policy = RecordingPolicy()
    a = MicroAgent(1, CFG)
    child = MicroAgent.from_lineage(2, CFG, a.genome, 1.0, 1, 1, policy=policy)
    assert child.policy is policy


@st.composite
def scenarios(draw: st.DrawFn) -> tuple[list[tuple[int, float, float]], Observation, int, bool]:
    n = draw(st.integers(0, 6))
    resources = []
    beliefs = []
    for rid in range(n):
        distance = draw(st.integers(0, 3))
        resources.append(
            VisibleResource(rid, pat(rid % 4), MOVES[rid % 4], distance, distance == 0)
        )
        if draw(st.booleans()):
            beliefs.append((rid % 4, draw(st.floats(-1, 1)), draw(st.floats(0.0, 1.0))))
    moves = draw(st.sampled_from([MOVES, ()]))
    o = Observation(1, 0, tuple(resources), moves, ())
    return beliefs, o, draw(st.integers(0, 50)), draw(st.booleans())


@given(scenarios(), st.booleans())
def test_handwritten_igual_a_la_fase_i(
    scenario: tuple[list[tuple[int, float, float]], Observation, int, bool], with_social: bool
) -> None:
    beliefs, o, seed, navigate = scenario
    a = MicroAgent(1, replace(CFG, enable_navigation=navigate))
    for i, value, conf in beliefs:
        a.assimilate_testimony(KnowledgeUnit(pat(i), value, conf, 1, 0, True), 2, 0)
    social = object() if with_social else None
    g1, g2, g3 = rng(seed), rng(seed), rng(seed)
    expected = legacy_decide(a, o, g1)
    assert HandwrittenPolicy().decide(a, o, social, 0, g2) == expected
    assert a.decide_action(o, 0, g3) == expected
    assert g1.bit_generator.state == g2.bit_generator.state == g3.bit_generator.state


def test_auditoria_ast_de_policy() -> None:
    tree = ast.parse(POLICY_PATH.read_text(encoding="utf-8"))
    forbidden = ("environments", "simulation", "experiments", "grid2d")
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "ide.agent.micro_agent":
            raise AssertionError("micro_agent sólo se importa bajo TYPE_CHECKING")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr != "true_value"
        if isinstance(node, ast.Name):
            assert node.id not in ("true_value", "coords", "position", "coordinates")
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""] + [alias.name for alias in node.names]
        assert not any(w in n for n in names for w in forbidden)
        assert "MessageType" not in names
        if isinstance(node, ast.Call):
            func = node.func
            called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            assert called != "Message"
        if isinstance(node, ast.Name):
            assert node.id not in ("Message", "MessageType")
