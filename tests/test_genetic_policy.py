"""Tests de la política genética, la percepción social y la puerta de comunicación (bloque 10).

Cubren `GeneticPolicy.decide` (factibilidad, orden de prueba y extracciones de `rng`, D46.1 y
D46.4, precisiones 24 y 25), las `SensorySignals` construidas desde la observación, las creencias
y `social` (D47.4), la percepción social del motor (D47.3), la puerta de comunicación de
`protocol.py` (D46.6), el caché de impulsos (D46.8), el contexto de la última expresión
(precisión 23), la política de los fundadores (D45.4) y la aceptación de D46.5: con el ADN
fundador, sin mutación y sin costo por codón, `002a` y `003a` dan los mismos historiales con y sin
la política genética.
"""

import itertools
from dataclasses import astuple, replace
from typing import Any, cast

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.dna import BEHAVIOR_TARGETS, behavior_terms, encode_codon, evaluate_drives
from ide.agent.micro_agent import MicroAgent
from ide.agent.policy import GeneticPolicy, HandwrittenPolicy, sensory_signals
from ide.config import SimulationConfig
from ide.domain.types import (
    CARCASS_PATTERN,
    ActionType,
    AgentAction,
    Behavior,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    KnowledgeUnit,
    Message,
    MessageType,
    Observation,
    Pattern,
    SensorySignals,
    SocialPerception,
    VisibleAgent,
    VisibleResource,
)
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
from ide.simulation.engine import SimulationEngine
from ide.simulation.pipeline import (
    DECISION_SYSTEM,
    PerceptionSystem,
    SocialPerceptionSystem,
    TickFrame,
    build_systems,
    genetic_policy_active,
)

GCFG = SimulationConfig(enable_evolution=True, enable_compact_dna=True, enable_genetic_policy=True)
MOVES = ((0, 1), (0, -1), (1, 0), (-1, 0))
IDLE = AgentAction(ActionType.IDLE)
_FOUNDER_TRAITS = tuple(encode_codon(0x00, t) for t in range(9))


def pat(i: int) -> Pattern:
    return Pattern((("id", f"p_{i}"),))


def rng(seed: int = 0) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))


def state(g: np.random.Generator) -> Any:
    return g.bit_generator.state


def behavior_codon(behavior: Behavior, payload: int, promoter: int = 0x00, mode: int = 0) -> int:
    target = BEHAVIOR_TARGETS[list(Behavior).index(behavior)]
    return encode_codon(promoter, target, mode, 0, payload)


def genetic_agent(
    drives: dict[Behavior, int], config: SimulationConfig = GCFG, extra: tuple[int, ...] = ()
) -> MicroAgent:
    """Agente con la política genética y un ADN con los impulsos dados (carga / 128)."""
    agent = MicroAgent(1, config, policy=GeneticPolicy())
    behaviors = tuple(behavior_codon(b, p) for b, p in drives.items())
    agent.set_dna(CompactDNA(chromosome=_FOUNDER_TRAITS + behaviors + extra))
    return agent


def know(agent: MicroAgent, i: int, value: float = 1.0, confidence: float = 0.8) -> None:
    agent.memory.upsert(KnowledgeUnit(pat(i), value, confidence, 1, 0, True), 0, force=True)


def res(rid: int, i: int, distance: int, move: Any = (1, 0)) -> VisibleResource:
    return VisibleResource(rid, pat(i), None if distance == 0 else move, distance, distance == 0)


def obs(
    resources: tuple[VisibleResource, ...] = (),
    moves: tuple[Any, ...] = MOVES,
    neighbors: tuple[int, ...] = (),
) -> Observation:
    return Observation(1, 0, resources, moves, neighbors)


def decide_twin(
    agent: MicroAgent,
    o: Observation,
    social: SocialPerception | None = None,
    seed: int = 3,
    tick: int = 0,
) -> tuple[AgentAction, np.random.Generator]:
    """Decide en `tick`; un agente decide una sola vez por tick (precisión 88)."""
    g = rng(seed)
    return GeneticPolicy().decide(agent, o, social, tick, g), g


# --- (a) GeneticPolicy.decide ------------------------------------------------------------------


def test_caminar_antes_que_consumir() -> None:
    agent = genetic_agent({Behavior.WANDER: 64, Behavior.CONSUME: 32})
    know(agent, 0)
    action, g = decide_twin(agent, obs((res(3, 0, 0),)))
    ref = rng(3)
    assert action == AgentAction(ActionType.MOVE, MOVES[int(ref.integers(len(MOVES)))])
    assert state(g) == state(ref)


def test_empate_resuelto_por_la_posicion_en_la_tabla() -> None:
    agent = genetic_agent({Behavior.WANDER: 64, Behavior.CONSUME: 64})
    know(agent, 0)
    action, g = decide_twin(agent, obs((res(3, 0, 0),)))
    assert action == AgentAction(ActionType.INTERACT, 3)
    assert state(g) == state(rng(3))


def test_impulsos_no_positivos_o_conductas_no_factibles() -> None:
    agent = genetic_agent({Behavior.SHARE: 64, Behavior.CONSUME: -32})
    know(agent, 0)
    social = SocialPerception(adjacent=(3,), weakest_adjacent=3)
    action, g = decide_twin(agent, obs((res(3, 0, 0),)), social)
    assert action == IDLE
    assert state(g) == state(rng(3))


def test_consumo_del_mejor_recurso_con_desempate_por_id() -> None:
    agent = genetic_agent({Behavior.CONSUME: 64})
    know(agent, 0, 0.5, 0.8)
    know(agent, 1, 0.8, 0.5)  # mismo v̂·c que el patrón 0
    know(agent, 2, 0.9, 0.9)
    action, _ = decide_twin(agent, obs((res(7, 0, 0), res(5, 1, 0), res(9, 2, 1))))
    assert action == AgentAction(ActionType.INTERACT, 5)


def test_exploracion_sin_candidatos_no_consume_el_generador() -> None:
    agent = genetic_agent({Behavior.EXPLORE: 64})
    action, g = decide_twin(agent, obs((res(4, 0, 2),)))  # desconocido pero no alcanzable
    assert action == IDLE
    assert state(g) == state(rng(3))


@pytest.mark.parametrize("epsilon", [0.0, 1.0])
def test_exploracion_con_candidato_extrae_una_vez(epsilon: float) -> None:
    agent = genetic_agent({Behavior.EXPLORE: 64}, replace(GCFG, epsilon_explore=epsilon))
    action, g = decide_twin(agent, obs((res(8, 0, 0), res(4, 1, 0))))
    ref = rng(3)
    ref.random()
    assert state(g) == state(ref)
    assert action == (AgentAction(ActionType.INTERACT, 4) if epsilon == 1.0 else IDLE)


@pytest.mark.parametrize("navigate", [False, True])
def test_navegacion(navigate: bool) -> None:
    agent = genetic_agent({Behavior.NAVIGATE: 64}, replace(GCFG, enable_navigation=navigate))
    know(agent, 0)
    o = obs((res(6, 0, 3, (0, 1)), res(2, 0, 2, (1, 1)), res(1, 0, 2, (-1, 0))))
    action, g = decide_twin(agent, o)
    assert action == (AgentAction(ActionType.MOVE, (-1, 0)) if navigate else IDLE)
    assert state(g) == state(rng(3))


def test_caminata_sin_movimientos_no_es_factible() -> None:
    agent = genetic_agent({Behavior.WANDER: 64})
    action, g = decide_twin(agent, obs(moves=()))
    assert action == IDLE
    assert state(g) == state(rng(3))


@pytest.mark.parametrize("weaker", [True, False])
def test_ataque_al_vecino_mas_debil(weaker: bool) -> None:
    agent = genetic_agent({Behavior.ATTACK: 64}, replace(GCFG, enable_predation=True))
    social = SocialPerception(adjacent=(3, 8), weakest_adjacent=8, weaker_adjacent=weaker)
    action, _ = decide_twin(agent, obs(), social)
    assert action == (AgentAction(ActionType.ATTACK, 8) if weaker else IDLE)


def test_ataque_sin_r37_no_es_factible() -> None:
    agent = genetic_agent({Behavior.ATTACK: 64})
    social = SocialPerception(adjacent=(3,), weakest_adjacent=3, weaker_adjacent=True)
    assert decide_twin(agent, obs(), social)[0] == IDLE


def test_esporulacion_por_debajo_del_umbral_expresado() -> None:
    config = replace(GCFG, enable_sporulation=True, spore_energy_threshold=GCFG.initial_energy)
    agent = genetic_agent({Behavior.SPORULATE: 64}, config)
    assert agent.energy == agent.phenotype.spore_threshold
    assert decide_twin(agent, obs())[0] == AgentAction(ActionType.SPORULATE)
    agent.apply_energy_delta(0.1)
    assert decide_twin(agent, obs(), tick=1)[0] == IDLE


def test_esporulacion_sin_r28_no_es_factible() -> None:
    config = replace(GCFG, spore_energy_threshold=GCFG.initial_energy)
    agent = genetic_agent({Behavior.SPORULATE: 64}, config)
    assert decide_twin(agent, obs())[0] == IDLE


def test_donante_sin_energia() -> None:
    agent = genetic_agent({Behavior.SHARE: 64}, replace(GCFG, enable_energy_transfer=True))
    social = SocialPerception(adjacent=(3,), weakest_adjacent=3)
    assert decide_twin(agent, obs(), social)[0] == AgentAction(ActionType.SHARE, 3)
    agent.apply_energy_delta(-agent.energy)
    assert agent.energy == 0.0
    assert decide_twin(agent, obs(), social, tick=1)[0] == IDLE


def test_huida() -> None:
    agent = genetic_agent({Behavior.FLEE: 64, Behavior.WANDER: 32})
    action, g = decide_twin(agent, obs(), SocialPerception(flee_move=(1, 0)))
    assert action == AgentAction(ActionType.MOVE, (1, 0))
    assert state(g) == state(rng(3))


def test_sin_percepcion_social_las_conductas_sociales_no_son_factibles() -> None:
    config = replace(GCFG, enable_energy_transfer=True, enable_predation=True)
    agent = genetic_agent({Behavior.SHARE: 64, Behavior.ATTACK: 64, Behavior.FLEE: 64}, config)
    o = obs()
    assert sensory_signals(agent, o, None) == sensory_signals(agent, o, SocialPerception())
    action, g = decide_twin(agent, o, None)
    assert action == IDLE
    assert state(g) == state(rng(3))


def test_sin_impulsos_devuelve_idle() -> None:
    agent = genetic_agent({})
    know(agent, 0)
    action, g = decide_twin(agent, obs((res(3, 0, 0),)))
    assert action == IDLE
    assert state(g) == state(rng(3))


def test_la_politica_genetica_exige_adn() -> None:
    agent = MicroAgent(1, SimulationConfig(), policy=GeneticPolicy())
    with pytest.raises(ValueError, match="ADN"):
        agent.decide_action(obs(), 0, rng())


# --- (b) SensorySignals --------------------------------------------------------------------------


def test_senales_desde_la_observacion_las_creencias_y_lo_social() -> None:
    agent = genetic_agent({})
    know(agent, 0, 1.0, 0.80)
    social = SocialPerception(adjacent=(4,), weakest_adjacent=4, weaker_adjacent=True, crowded=True)
    signals = sensory_signals(agent, obs((res(9, 0, 2),)), social)
    assert signals == SensorySignals(
        known_good=True,
        unknown=False,
        no_resource=False,
        neighbor_adjacent=True,
        weaker_adjacent=True,
        stronger_near=False,
        crowded=True,
        carcass=False,
        attacked=False,
        ate=False,
        lost_energy=False,
        received_energy=False,
    )


def test_senales_sin_recursos_y_con_desconocidos() -> None:
    agent = genetic_agent({})
    know(agent, 0, -1.0, 0.9)  # conocido y dañino: no es `known_good`
    know(agent, 1, 1.0, 0.1)  # confianza bajo el umbral: desconocido
    empty = sensory_signals(agent, obs(), SocialPerception(flee_move=(0, 1)))
    assert empty.no_resource and not empty.known_good and not empty.unknown
    assert empty.stronger_near
    signals = sensory_signals(
        agent, obs((res(1, 0, 0), res(2, 1, 3))), SocialPerception(carcass_visible=True)
    )
    assert (signals.known_good, signals.unknown, signals.no_resource) == (False, True, False)
    assert signals.carcass and not signals.stronger_near and not signals.neighbor_adjacent


def test_senales_con_la_vista_del_holon() -> None:
    agent = genetic_agent({})
    agent.inject_ephemeral_belief(KnowledgeUnit(pat(0), 1.0, 0.9, 1, 0, False))
    assert sensory_signals(agent, obs((res(1, 0, 4),)), None).known_good


# --- (c) percepción social del motor ---------------------------------------------------------


def genetic_engine(**overrides: Any) -> SimulationEngine:
    config = replace(
        PHASE2_PROTOCOL_CONFIGS["002a"],
        enable_compact_dna=True,
        enable_genetic_policy=True,
        **overrides,
    )
    return SimulationEngine(config)


def set_energy(agent: MicroAgent, value: float) -> None:
    agent.apply_energy_delta(value - agent.energy)


def social_frame(
    engine: SimulationEngine,
    visible: dict[int, tuple[VisibleAgent, ...]],
    monkeypatch: pytest.MonkeyPatch,
) -> TickFrame:
    """Corre percepción y percepción social con `get_visible_agents` fijado por agente."""
    grid = cast(ToroidalGrid2D, engine.env)
    monkeypatch.setattr(grid, "get_visible_agents", lambda aid: visible.get(aid, ()))
    frame = TickFrame(0)
    frame.order = sorted(engine.agents)
    PerceptionSystem().run(engine, frame)
    SocialPerceptionSystem().run(engine, frame)
    return frame


def test_vecinos_adyacentes_y_huida(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = genetic_engine()
    for aid, energy in ((1, 1.0), (4, 0.6), (2, 1.5), (7, 2.0)):
        set_energy(engine.agents[aid], energy)
    visible = {
        1: (
            VisibleAgent(2, 1, (1, 0), (-1, 0)),
            VisibleAgent(4, 1, (0, 1), (0, -1)),
            VisibleAgent(7, 2, (1, 1), (-1, -1)),
        )
    }
    social = social_frame(engine, visible, monkeypatch).social
    assert set(social) == set(engine.agents)
    assert social[1] == SocialPerception(
        adjacent=(2, 4),
        weakest_adjacent=4,
        weaker_adjacent=True,
        flee_move=(-1, 0),
        crowded=True,  # tres activos visibles con crowding_threshold = 3
        carcass_visible=False,
    )
    assert social[3] == SocialPerception()


def test_huida_del_mas_cercano_con_mas_energia(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = genetic_engine()
    for aid, energy in ((1, 1.0), (2, 0.5), (5, 3.0), (6, 3.0), (8, 1.0)):
        set_energy(engine.agents[aid], energy)
    visible = {
        1: (
            VisibleAgent(2, 1, (1, 0), (-1, 0)),
            VisibleAgent(8, 1, (0, 1), (0, -1)),  # igual energía: no cuenta como más fuerte
            VisibleAgent(5, 2, (1, 1), (-1, -1)),
            VisibleAgent(6, 2, (-1, 1), (1, -1)),
        )
    }
    social = social_frame(engine, visible, monkeypatch).social[1]
    assert social.flee_move == (-1, -1)
    assert social.adjacent == (2, 8)
    assert social.weakest_adjacent == 2 and social.weaker_adjacent


def test_vecino_mas_debil_por_energia_e_id(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = genetic_engine()
    for aid, energy in ((1, 1.0), (3, 1.2), (6, 1.2)):
        set_energy(engine.agents[aid], energy)
    visible = {1: (VisibleAgent(6, 0, None, (1, 0)), VisibleAgent(3, 1, (1, 0), (-1, 0)))}
    social = social_frame(engine, visible, monkeypatch).social[1]
    assert social.adjacent == (3, 6)
    assert social.weakest_adjacent == 3
    assert social.weaker_adjacent is False  # 1.2 no es menor que 1.0
    assert social.flee_move == (1, 0)  # el agente 6, a distancia 0, es el más cercano
    assert social.crowded is False


def test_endospora_no_es_un_agente_activo(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = genetic_engine()
    set_energy(engine.agents[1], 1.0)
    set_energy(engine.agents[4], 3.0)
    engine.agents[4].set_endospore(True)
    visible = {1: (VisibleAgent(4, 1, (1, 0), (-1, 0)),)}
    social = social_frame(engine, visible, monkeypatch).social[1]
    assert social.adjacent == ()
    assert social.weakest_adjacent is None
    assert social.flee_move is None


def test_cadaver_visible(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = genetic_engine()
    grid = cast(ToroidalGrid2D, engine.env)
    plain = grid.get_observation(1, 0)
    carcass = VisibleResource(999, CARCASS_PATTERN, (1, 0), 2, False)
    monkeypatch.setattr(
        grid,
        "get_observation",
        lambda aid, tick: replace(plain, visible_resources=(carcass,)) if aid == 1 else plain,
    )
    social = social_frame(engine, {}, monkeypatch).social
    assert social[1].carcass_visible
    assert not social[2].carcass_visible


def test_percepcion_social_sin_generadores_ni_cambios(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = genetic_engine()
    grid = cast(ToroidalGrid2D, engine.env)
    before = [state(g) for g in (engine.rng, engine.null_rng, engine.evo_rng, engine.donor_rng)]
    positions = {aid: grid.get_agent_position(aid) for aid in engine.agents}
    frame = TickFrame(0)
    frame.order = sorted(engine.agents)
    PerceptionSystem().run(engine, frame)
    SocialPerceptionSystem().run(engine, frame)
    after = [state(g) for g in (engine.rng, engine.null_rng, engine.evo_rng, engine.donor_rng)]
    assert before == after
    assert positions == {aid: grid.get_agent_position(aid) for aid in engine.agents}
    assert len(frame.social) == len(engine.agents)


def test_percepcion_social_sobre_la_grilla_real() -> None:
    engine = genetic_engine()
    grid = cast(ToroidalGrid2D, engine.env)
    frame = TickFrame(0)
    frame.order = sorted(engine.agents)
    PerceptionSystem().run(engine, frame)
    SocialPerceptionSystem().run(engine, frame)
    threshold = engine.config.crowding_threshold
    for aid in sorted(engine.agents):
        visible = grid.get_visible_agents(aid)
        adjacent = tuple(sorted(v.agent_id for v in visible if v.distance <= 1))
        assert frame.social[aid].adjacent == adjacent
        assert frame.social[aid].crowded == (len(visible) >= threshold)


def test_genetic_policy_active_exige_adn() -> None:
    assert genetic_policy_active(GCFG)
    assert not genetic_policy_active(replace(GCFG, enable_compact_dna=False))
    assert not genetic_policy_active(replace(GCFG, enable_genetic_policy=False))


def test_sistema_de_percepcion_social_solo_con_la_politica_genetica() -> None:
    base = replace(PHASE2_PROTOCOL_CONFIGS["002a"], enable_compact_dna=True)
    names = [s.name for s in build_systems(replace(base, enable_genetic_policy=True))]
    assert names.index("perception") < names.index("social_perception")
    assert names.index("social_perception") < names.index("emission")
    assert names.index("emission") < names.index(DECISION_SYSTEM)
    for config in (base, replace(base, enable_compact_dna=False, enable_genetic_policy=True)):
        assert "social_perception" not in [s.name for s in build_systems(config)]


def record_decisions(
    engine: SimulationEngine, monkeypatch: pytest.MonkeyPatch
) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []
    for agent in engine.agents.values():
        original = agent.decide_action

        def spy(*args: Any, _original: Any = original) -> AgentAction:
            calls.append(args)
            return _original(*args)

        monkeypatch.setattr(agent, "decide_action", spy)
    return calls


def test_la_decision_recibe_la_percepcion_social(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = genetic_engine()
    calls = record_decisions(engine, monkeypatch)
    engine.step()
    assert calls
    assert all(len(args) == 4 and isinstance(args[3], SocialPerception) for args in calls)


@pytest.mark.parametrize("dna", [False, True])
def test_sin_la_politica_genetica_social_es_none(
    dna: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = replace(PHASE2_PROTOCOL_CONFIGS["002a"], enable_compact_dna=dna)
    if not dna:
        config = replace(config, enable_genetic_policy=True)  # R32 inerte sin ADN
    engine = SimulationEngine(config)
    calls = record_decisions(engine, monkeypatch)
    engine.step()
    assert calls
    assert all(len(args) == 3 for args in calls)  # la llamada de la Fase I: `social` es None


# --- Política de los fundadores (D45.4) ------------------------------------------------------


def test_fundadores_con_la_politica_genetica_y_herencia() -> None:
    engine = genetic_engine()
    assert all(isinstance(a.policy, GeneticPolicy) for a in engine.agents.values())
    engine.run(60)
    assert engine.next_agent_id > PHASE2_PROTOCOL_CONFIGS["002a"].num_agents  # hubo nacimientos
    assert all(isinstance(a.policy, GeneticPolicy) for a in engine.agents.values())


@pytest.mark.parametrize(
    ("dna", "genetic"), [(False, False), (False, True), (True, False)], ids=str
)
def test_fundadores_con_la_politica_escrita_a_mano(dna: bool, genetic: bool) -> None:
    config = replace(
        PHASE2_PROTOCOL_CONFIGS["002a"], enable_compact_dna=dna, enable_genetic_policy=genetic
    )
    engine = SimulationEngine(config)
    assert all(isinstance(a.policy, HandwrittenPolicy) for a in engine.agents.values())


def test_la_politica_genetica_exige_el_puerto_ecologico() -> None:
    class Evolutivo(ToroidalGrid2D):
        """Grilla de la Fase II sin las consultas ecológicas (`None` bloquea el protocolo)."""

        get_visible_agents = None  # pyright: ignore[reportAssignmentType, reportIncompatibleMethodOverride]

    config = replace(
        PHASE2_PROTOCOL_CONFIGS["002a"], enable_compact_dna=True, enable_genetic_policy=True
    )
    env = Evolutivo(config, rng(config.seed))
    with pytest.raises(TypeError, match="EcologicalEnvironmentPort"):
        SimulationEngine(config, env)
    # Sin ADN, R32 es inerte (precisión 31) y no exige el puerto ecológico.
    SimulationEngine(replace(config, enable_compact_dna=False), env)


# --- (d) puerta de comunicación ----------------------------------------------------------------


def communicating_agent(base: float, policy: Any) -> MicroAgent:
    config = replace(GCFG, comm_propensity_base=base)
    return MicroAgent(1, config, policy=policy)


def test_agente_que_no_comunica_pero_aprende() -> None:
    agent = communicating_agent(0.0, GeneticPolicy())
    know(agent, 0, 1.0, 0.9)
    assert agent.communicates is False
    o = obs((res(5, 3, 1),), neighbors=(2,))
    assert agent.perceive_and_emit_messages(o, 1) == []
    belief = KnowledgeUnit(pat(7), 0.9, 0.9, 1, 0, True)
    inbox = [
        Message(MessageType.QUERY_PATTERN, 2, None, pat(0)),
        Message(MessageType.BROADCAST_BELIEF, 2, None, pat(7), belief),
    ]
    assert agent.process_incoming_messages(inbox, 1) == []
    assimilated = agent.memory.get(pat(7))
    assert assimilated is not None and assimilated.predicted_value > 0


def test_agente_que_comunica_emite_y_responde() -> None:
    agent = communicating_agent(1.0, GeneticPolicy())
    know(agent, 0, 1.0, 0.9)
    assert agent.communicates is True
    o = obs((res(5, 3, 1),), neighbors=(2,))
    emitted = agent.perceive_and_emit_messages(o, 1)
    assert [m.msg_type for m in emitted] == [
        MessageType.QUERY_PATTERN,
        MessageType.BROADCAST_BELIEF,
    ]
    responses = agent.process_incoming_messages(
        [Message(MessageType.QUERY_PATTERN, 2, None, pat(0))], 1
    )
    assert [m.msg_type for m in responses] == [MessageType.QUERY_RESPONSE]


def test_umbral_exacto_y_politica_escrita_a_mano() -> None:
    assert communicating_agent(0.5, GeneticPolicy()).communicates is True
    assert communicating_agent(0.0, HandwrittenPolicy()).communicates is True
    assert communicating_agent(0.0, None).communicates is True


def test_la_puerta_sigue_al_fenotipo_expresado() -> None:
    # Un codón aditivo de carga 107 sobre 0x0C lleva la propensión de 0 a 0.6 * 0.836 > 0.5.
    agent = communicating_agent(0.0, GeneticPolicy())
    assert agent.communicates is False
    agent.set_dna(CompactDNA(chromosome=(*_FOUNDER_TRAITS, encode_codon(0x00, 0x0C, 0, 0, 107))))
    agent.express(agent.last_context, 1)
    assert agent.phenotype.comm_propensity >= 0.5
    assert agent.communicates is True


def test_la_puerta_en_el_motor_reduce_los_mensajes() -> None:
    silent = genetic_engine(comm_propensity_base=0.0)
    silent.run(3)
    assert all(m.messages_sent == 0 for m in silent.history)
    talkative = genetic_engine()
    talkative.run(3)
    assert sum(m.messages_sent for m in talkative.history) > 0


# --- (e) caché de impulsos y contexto de la última expresión ---------------------------------


def test_contexto_de_nacimiento_y_de_la_fase_0() -> None:
    config = replace(GCFG, reproduction_threshold=2.2)
    parent = MicroAgent(1, config, policy=GeneticPolicy())
    set_energy(parent, 1.1 / config.offspring_energy_share)
    child = parent.create_offspring(2, 5, rng())
    assert child.last_context == EpigeneticContext(
        0, EpigeneticRole.NONE, child.energy / config.reproduction_threshold
    )
    child.express(EpigeneticContext(2, EpigeneticRole.NERVE, 0.9), 41)
    assert child.last_context == EpigeneticContext(2, EpigeneticRole.NERVE, 0.9)


def test_contexto_de_nacimiento_del_escenario() -> None:
    config = replace(GCFG, reproduction_threshold=2.2)
    child = MicroAgent.from_lineage(
        2, config, None, 0.55, 1, 1, dna=CompactDNA(_FOUNDER_TRAITS), policy=GeneticPolicy()
    )
    assert child.last_context == EpigeneticContext(0, EpigeneticRole.NONE, 0.25)


def test_contexto_del_fundador() -> None:
    agent = MicroAgent(1, GCFG)
    assert agent.last_context == EpigeneticContext(
        0, EpigeneticRole.NONE, GCFG.initial_energy / GCFG.reproduction_threshold
    )


_CONTEXT_DNA = CompactDNA(
    chromosome=(
        *_FOUNDER_TRAITS,
        behavior_codon(Behavior.CONSUME, 64),
        behavior_codon(Behavior.CONSUME, -40, promoter=0x18),  # estrés
        behavior_codon(Behavior.EXPLORE, 50, promoter=0x20),  # SENSE_KNOWN_GOOD
        behavior_codon(Behavior.EXPLORE, 30, promoter=0x19, mode=2),  # superávit, multiplicativo
        behavior_codon(Behavior.WANDER, 20, promoter=0x12),  # rol NERVE
        behavior_codon(Behavior.FLEE, 70, promoter=0x25),  # SENSE_STRONGER_NEAR
        behavior_codon(Behavior.SHARE, 60, promoter=0x03),  # IN_HOLON_L2
        behavior_codon(Behavior.ATTACK, 90, promoter=0x26, mode=1),  # represor con gentío
        behavior_codon(Behavior.ATTACK, 80, promoter=0x23),  # vecino adyacente
        encode_codon(0x27, 0x09, 0, 5, 10),  # EMIT_TF del canal 5 con cadáver visible
        behavior_codon(Behavior.SPORULATE, 100, promoter=0x85),  # regulado por el canal 5
    )
)


def all_signals() -> list[SensorySignals]:
    combos = itertools.product((False, True), repeat=8)
    return [SensorySignals(*bits, False, False, False, False) for bits in combos]


def test_cache_de_impulsos_igual_a_la_evaluacion_directa() -> None:
    agent = genetic_agent({}, extra=())
    contexts = [
        EpigeneticContext(level, role, ratio)
        for level in (0, 2, 11)
        for role in (EpigeneticRole.NONE, EpigeneticRole.NERVE)
        for ratio in (0.1, 0.7, 1.4)
    ]
    signals = all_signals()[::7]
    for dna in (_CONTEXT_DNA, CompactDNA(_FOUNDER_TRAITS), _CONTEXT_DNA):
        agent.set_dna(dna)
        for tick, context in enumerate(contexts):
            agent.express(context, tick)
            for s in signals:
                expected = evaluate_drives(dna, context, s, agent.base_config)
                assert agent.evaluate_behavior(s).drives == expected
                assert (
                    agent.evaluate_behavior(s).drives == expected
                )  # segunda lectura, desde el caché


@given(
    st.integers(0, 12),
    st.sampled_from(list(EpigeneticRole)),
    st.floats(0.0, 3.0),
    st.sampled_from(all_signals()),
)
def test_cache_de_impulsos_por_propiedades(
    level: int, role: EpigeneticRole, ratio: float, signals: SensorySignals
) -> None:
    agent = genetic_agent({})
    agent.set_dna(_CONTEXT_DNA)
    agent.evaluate_behavior(signals)  # puebla el caché con el contexto previo
    context = EpigeneticContext(level, role, ratio)
    agent.express(context, 1)
    assert agent.evaluate_behavior(signals).drives == evaluate_drives(
        _CONTEXT_DNA, context, signals, agent.base_config
    )


# --- Equivalencia del fundador (D46.5) -------------------------------------------------------


@st.composite
def founder_scenarios(draw: st.DrawFn) -> tuple[Any, ...]:
    n = draw(st.integers(0, 6))
    resources = []
    beliefs = []
    for rid in range(n):
        distance = draw(st.integers(0, 3))
        resources.append(res(rid, rid % 4, distance, MOVES[rid % 4]))
        if draw(st.booleans()):
            beliefs.append((rid % 4, draw(st.floats(-1, 1)), draw(st.floats(0.0, 1.0))))
    moves = draw(st.sampled_from([MOVES, ()]))
    o = Observation(1, 0, tuple(resources), moves, ())
    social = draw(
        st.builds(
            SocialPerception,
            adjacent=st.just((2, 5)),
            weakest_adjacent=st.sampled_from([2, 5]),
            weaker_adjacent=st.booleans(),
            flee_move=st.sampled_from([None, (1, 0)]),
            crowded=st.booleans(),
            carcass_visible=st.booleans(),
        )
        | st.none()
    )
    epsilon = draw(st.sampled_from([0.0, 0.3, 1.0]))
    return beliefs, o, draw(st.integers(0, 50)), draw(st.booleans()), epsilon, social


@given(founder_scenarios())
def test_fundador_genetico_equivalente_a_la_politica_escrita(scenario: tuple[Any, ...]) -> None:
    beliefs, o, seed, navigate, epsilon, social = scenario
    config = replace(
        GCFG,
        enable_navigation=navigate,
        epsilon_explore=epsilon,
        enable_energy_transfer=True,
        enable_predation=True,
        enable_sporulation=True,
    )
    agent = MicroAgent(1, config, policy=GeneticPolicy())
    for i, value, conf in beliefs:
        agent.assimilate_testimony(KnowledgeUnit(pat(i), value, conf, 1, 0, True), 2, 0)
    g1, g2 = rng(seed), rng(seed)
    expected = HandwrittenPolicy().decide(agent, o, social, 0, g1)
    assert agent.decide_action(o, 0, g2, social) == expected
    assert state(g1) == state(g2)


# --- (f) aceptación de D46.5 ----------------------------------------------------------------


def acceptance_history(protocol: str, genetic: bool, ticks: int = 120) -> Any:
    config = replace(
        PHASE2_PROTOCOL_CONFIGS[protocol],
        enable_compact_dna=True,
        mutation_rate=0.0,
        discrete_mutation_prob=0.0,
        dna_codon_cost=0.0,
        enable_genetic_policy=genetic,
    )
    engine = SimulationEngine(config)
    engine.run(ticks)
    grid = cast(ToroidalGrid2D, engine.env)
    ids = sorted(engine.agents)
    return (
        engine.history,
        [astuple(m) for m in engine.evolutionary_history],
        [grid.get_agent_position(a) for a in ids],
        [engine.agents[a].memory.all_units() for a in ids],
        [engine.agents[a].genome for a in ids],
        [state(g) for g in (engine.rng, engine.null_rng, engine.evo_rng, engine.donor_rng)],
        engine.next_agent_id,
    )


@pytest.mark.parametrize("protocol", ["002a", "003a"])
def test_aceptacion_del_fundador_genetico(protocol: str) -> None:
    with_policy = acceptance_history(protocol, True)
    without = acceptance_history(protocol, False)
    assert len(with_policy[0]) == 120
    assert with_policy[6] > PHASE2_PROTOCOL_CONFIGS[protocol].num_agents  # hubo nacimientos
    assert with_policy == without


# --- Correcciones de la revisión del bloque 10 -------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        {"adjacent": (3,)},  # adyacentes sin el más débil
        {"adjacent": (3,), "weakest_adjacent": 4},  # el más débil no es adyacente
        {"weakest_adjacent": 3},  # el más débil sin adyacentes
        {"weaker_adjacent": True},  # más débil que uno mismo sin objetivo
        {"adjacent": (5, 3), "weakest_adjacent": 3},  # no ascendentes
        {"adjacent": (3, 3), "weakest_adjacent": 3},  # repetidos
    ],
)
def test_percepcion_social_incoherente_rechazada(fields: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        SocialPerception(**fields)


def test_percepcion_social_coherente_aceptada() -> None:
    social = SocialPerception(adjacent=(2, 5), weakest_adjacent=5, weaker_adjacent=True)
    assert social.weakest_adjacent == 5


def test_la_puerta_la_declara_la_politica() -> None:
    assert GeneticPolicy.gates_communication is True
    assert HandwrittenPolicy.gates_communication is False

    class Gated:  # una política propia que declara la puerta, sin ser `GeneticPolicy`
        gates_communication = True

        def decide(self, *_args: Any) -> AgentAction:
            return IDLE

    class Open:
        gates_communication = False

        def decide(self, *_args: Any) -> AgentAction:
            return IDLE

    config = replace(GCFG, comm_propensity_base=0.0)
    assert MicroAgent(1, config, policy=Gated()).communicates is False
    assert MicroAgent(1, config, policy=Open()).communicates is True


def test_una_sola_instancia_de_la_politica_genetica() -> None:
    engine = genetic_engine()
    policies = {id(agent.policy) for agent in engine.agents.values()}
    assert len(policies) == 1


def test_la_endospora_recibe_su_percepcion_social(monkeypatch: pytest.MonkeyPatch) -> None:
    # Que la endospora no decida ni se perciba queda para el bloque 17 (precisión 82).
    engine = genetic_engine()
    engine.agents[5].set_endospore(True)
    social = social_frame(engine, {}, monkeypatch).social
    assert set(social) == set(engine.agents)


def test_cache_de_impulsos_acotado_y_con_aciertos(monkeypatch: pytest.MonkeyPatch) -> None:
    import ide.agent.micro_agent as micro_agent

    calls: list[SensorySignals] = []

    # Desde el bloque 14, el caché guarda la evaluación sin los pesos (`behavior_terms`, D59.5).
    def counting(dna: CompactDNA, context: Any, signals: SensorySignals, *args: Any) -> Any:
        calls.append(signals)
        return behavior_terms(dna, context, signals, *args)

    monkeypatch.setattr(micro_agent, "behavior_terms", counting)
    monkeypatch.setattr(micro_agent, "EVALUATION_CACHE_LIMIT", 5)
    agent = genetic_agent({})
    agent.set_dna(_CONTEXT_DNA)
    few = all_signals()[:4]
    for _ in range(3):  # cuatro claves bajo el tope: sólo la primera vuelta evalúa
        for s in few:
            assert agent.evaluate_behavior(s).drives == evaluate_drives(
                _CONTEXT_DNA, agent.last_context, s, agent.base_config
            )
    assert calls == few
    many = all_signals()[:40]
    for s in many:  # más claves que el tope: el caché nunca lo supera y los valores no cambian
        assert agent.evaluate_behavior(s).drives == evaluate_drives(
            _CONTEXT_DNA, agent.last_context, s, agent.base_config
        )
        assert len(agent._evaluation_cache) <= 5  # pyright: ignore[reportPrivateUsage]


def test_tope_declarado_del_cache() -> None:
    from ide.agent.micro_agent import EVALUATION_CACHE_LIMIT

    assert EVALUATION_CACHE_LIMIT == 512
