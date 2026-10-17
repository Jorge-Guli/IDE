"""Tests de `simulation-engine`: pipeline de 5 fases, determinismo y perturbaciones."""

import copy
import os
import subprocess
import sys
import textwrap
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.extensions import AgentCapabilities
from ide.domain.types import (
    ActionResult,
    ActionType,
    AgentAction,
    KnowledgeUnit,
    Message,
    Observation,
    Pattern,
    Resource,
)
from ide.environments.grid2d import ToroidalGrid2D
from ide.simulation import engine as engine_module
from ide.simulation.engine import SimulationEngine

Cell = tuple[int, int]
ROOT = Path(__file__).resolve().parents[1]


def pat(i: int) -> Pattern:
    return Pattern((("id", f"p_{i}"),))


def small_config(**overrides: Any) -> SimulationConfig:
    base = SimulationConfig(grid_width=10, grid_height=10, num_agents=10, resources_per_pattern=4)
    return replace(base, **overrides)


def grid_of(engine: SimulationEngine) -> ToroidalGrid2D:
    return cast(ToroidalGrid2D, engine.env)


def resources_of(grid: ToroidalGrid2D) -> list[tuple[Cell, Resource]]:
    found = [
        (cell, r)
        for cell in sorted(grid.cell_resources)
        for r in grid.cell_resources[cell].values()
    ]
    return sorted(found, key=lambda item: item[1].resource_id)


def walk_to(grid: ToroidalGrid2D, agent_id: int, target: Cell) -> None:
    """Lleva al agente a `target` con `MOVE`, que no consume el generador."""
    width, height = grid.config.grid_width, grid.config.grid_height
    while grid.get_agent_position(agent_id) != target:
        x, y = grid.get_agent_position(agent_id)
        dx = ((target[0] - x + width // 2) % width) - width // 2
        dy = ((target[1] - y + height // 2) % height) - height // 2
        grid.execute_action(
            agent_id, AgentAction(ActionType.MOVE, (int(np.sign(dx)), int(np.sign(dy)))), 0
        )


def first_resource_of(grid: ToroidalGrid2D, pattern: Pattern) -> tuple[Cell, Resource]:
    return next((cell, r) for cell, r in resources_of(grid) if r.pattern == pattern)


def direct(pattern: Pattern, value: float, conf: float = 0.9) -> KnowledgeUnit:
    return KnowledgeUnit(pattern, value, conf, 1, 0, True)


def record_calls(
    monkeypatch: pytest.MonkeyPatch, target: object, name: str
) -> list[tuple[Any, ...]]:
    """Envuelve `target.name` y registra los argumentos y el resultado de cada llamada."""
    calls: list[tuple[Any, ...]] = []
    original: Callable[..., Any] = getattr(target, name)

    def wrapper(*args: Any) -> Any:
        result = original(*args)
        calls.append((*args, result))
        return result

    monkeypatch.setattr(target, name, wrapper)
    return calls


# --- Construcción ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"enable_specialization": True},
        {"epsilon_recheck": 0.1},
        {"tau_policy": "evidence_age"},
        {"update_scheme": "asynchronous"},
    ],
)
def test_mecanismos_fuera_de_alcance_lanzan_not_implemented(overrides: dict[str, Any]) -> None:
    with pytest.raises(NotImplementedError):
        SimulationEngine(replace(SimulationConfig(), **overrides))


def test_construccion_crea_un_agente_por_activo_con_la_grilla_por_defecto() -> None:
    engine = SimulationEngine(small_config())
    assert isinstance(engine.env, ToroidalGrid2D)
    assert sorted(engine.agents) == engine.env.get_active_agent_ids() == list(range(10))
    assert all(isinstance(a, MicroAgent) and a.agent_id == i for i, a in engine.agents.items())
    assert engine.next_tick == 0 and engine.history == []


def test_la_grilla_comparte_el_generador_del_motor() -> None:
    config = small_config(seed=5)
    engine = SimulationEngine(config)
    rng = np.random.Generator(np.random.PCG64(5))
    ToroidalGrid2D(config, rng)
    assert engine.rng.bit_generator.state == rng.bit_generator.state


# --- Orden y simultaneidad ---------------------------------------------------------------------


def test_todas_las_fases_usan_la_permutacion_del_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(small_config())
    observed = record_calls(monkeypatch, engine.env, "get_observation")
    executed = record_calls(monkeypatch, engine.env, "execute_action")
    for _ in range(3):
        observed.clear()
        executed.clear()
        expected = [int(a) for a in copy.deepcopy(engine.rng).permutation(sorted(engine.agents))]
        engine.step()
        assert [call[0] for call in observed] == expected
        assert [call[0] for call in executed] == expected


def test_orden_independiente_del_hash() -> None:
    script = textwrap.dedent(
        """
        from ide.config import SimulationConfig
        from ide.environments.grid2d import ToroidalGrid2D
        from ide.simulation.engine import SimulationEngine

        order = []
        original = ToroidalGrid2D.get_observation

        def spy(self, agent_id, tick):
            order.append((tick, agent_id))
            return original(self, agent_id, tick)

        ToroidalGrid2D.get_observation = spy
        engine = SimulationEngine(SimulationConfig(seed=11, num_agents=20))
        engine.run(5)
        print(order)
        print(engine.history[-1])
        """
    )
    outputs = []
    for hash_seed in ("0", "1"):
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
    assert outputs[0] == outputs[1]
    assert outputs[0].strip()


def _contested_setup(seed: int) -> tuple[SimulationEngine, Resource]:
    """Agentes 3 y 8 en la celda de un recurso benéfico que ambos conocen."""
    engine = SimulationEngine(small_config(seed=seed, comm_enabled=False))
    grid = grid_of(engine)
    cell, resource = first_resource_of(grid, pat(1))
    for aid in (3, 8):
        walk_to(grid, aid, cell)
        engine.agents[aid].memory.upsert(direct(pat(1), 1.0), 0, force=True)
    return engine, resource


@pytest.mark.parametrize("seed", range(6))
def test_sorteo_de_un_recurso_disputado(monkeypatch: pytest.MonkeyPatch, seed: int) -> None:
    engine, resource = _contested_setup(seed)
    executed = record_calls(monkeypatch, engine.env, "execute_action")
    engine.step()
    by_agent = {call[0]: (call[1], call[3]) for call in executed}
    # Decisiones sobre la misma instantánea: ambos intentan consumir el mismo recurso.
    for aid in (3, 8):
        assert by_agent[aid][0] == AgentAction(ActionType.INTERACT, resource.resource_id)
    order = [call[0] for call in executed]
    winner, loser = (3, 8) if order.index(3) < order.index(8) else (8, 3)
    assert by_agent[winner][1] == ActionResult(ActionType.INTERACT, pat(1), 1.0)
    assert by_agent[loser][1] == ActionResult(ActionType.INTERACT, None, None)
    assert winner in engine.direct_discoverers[pat(1)]
    assert loser not in engine.direct_discoverers[pat(1)]


def test_existe_una_semilla_donde_8_precede_a_3() -> None:
    """Garantiza que el sorteo parametrizado cubre el escenario literal de la spec."""
    winners = set()
    for seed in range(6):
        engine, _ = _contested_setup(seed)
        perm = [int(a) for a in copy.deepcopy(engine.rng).permutation(sorted(engine.agents))]
        winners.add(8 if perm.index(8) < perm.index(3) else 3)
    assert winners == {3, 8}


# --- Intercambio social ------------------------------------------------------------------------


def test_consulta_resuelta_en_el_mismo_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(small_config(max_broadcast_per_tick=0))
    grid = grid_of(engine)
    cell, _ = first_resource_of(grid, pat(5))
    walk_to(grid, 1, cell)
    walk_to(grid, 2, cell)
    engine.agents[2].memory.upsert(direct(pat(5), -1.0, 0.85), 0, force=True)
    seen: list[KnowledgeUnit | None] = []
    agent = engine.agents[1]
    original = agent.decide_action

    def spy(obs: Any, tick: int, rng: np.random.Generator) -> AgentAction:
        seen.append(agent.get_effective_belief(pat(5)))
        return original(obs, tick, rng)

    monkeypatch.setattr(agent, "decide_action", spy)
    engine.step()
    belief = seen[0]
    assert belief is not None
    assert belief.predicted_value == -1.0
    assert belief.confidence == pytest.approx(0.75 * 0.85, abs=1e-9)
    assert belief.from_direct_experience is False


def test_un_mensaje_cuenta_una_vez(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(small_config())
    emitted: list[Message] = []
    responses: list[Message] = []
    for agent in engine.agents.values():
        for name, store in (
            ("perceive_and_emit_messages", emitted),
            ("process_incoming_messages", responses),
        ):
            original = getattr(agent, name)

            def wrapper(*args: Any, _orig: Any = original, _store: list[Message] = store) -> Any:
                out = _orig(*args)
                _store.extend(out)
                return out

            monkeypatch.setattr(agent, name, wrapper)
    for _ in range(30):
        emitted.clear()
        responses.clear()
        metrics = engine.step()
        assert metrics.messages_sent == len(emitted) + len(responses)
    assert any(m.messages_sent > 0 for m in engine.history)


def test_modo_aislado_sin_creencias_sociales() -> None:
    engine = SimulationEngine(replace(SimulationConfig(), comm_enabled=False))
    history = engine.run(100)
    assert len(history) == 100
    assert all(m.messages_sent == 0 and m.messages_per_agent == 0.0 for m in history)
    for agent in engine.agents.values():
        assert all(u.from_direct_experience for u in agent.memory.all_units())


def test_registro_de_descubridores_directos(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(small_config())
    executed = record_calls(monkeypatch, engine.env, "execute_action")
    found = 0
    for _ in range(40):
        executed.clear()
        engine.step()
        for aid, _action, _tick, result in executed:
            if result.experienced_value is None:
                continue
            found += 1
            assert aid in engine.direct_discoverers[result.interacted_pattern]
            unit = engine.agents[aid].memory.get(result.interacted_pattern)
            assert unit is not None and unit.from_direct_experience
            assert unit.last_updated_tick == engine.next_tick - 1
    assert found > 0


def test_capabilities_invariantes_durante_100_ticks() -> None:
    engine = SimulationEngine(SimulationConfig())
    engine.run(100)
    assert all(a.capabilities == AgentCapabilities() for a in engine.agents.values())


def test_memoria_acotada_en_todo_tick() -> None:
    engine = SimulationEngine(SimulationConfig())
    for _ in range(60):
        engine.step()
        assert all(len(a.memory) <= 3 for a in engine.agents.values())


# --- Reproducibilidad --------------------------------------------------------------------------


def _state(engine: SimulationEngine) -> tuple[Any, ...]:
    grid = grid_of(engine)
    positions = [grid.get_agent_position(a) for a in sorted(engine.agents)]
    memories = [engine.agents[a].memory.all_units() for a in sorted(engine.agents)]
    return engine.history, positions, memories


def test_reproducibilidad_bit_a_bit_200_ticks() -> None:
    a = SimulationEngine(SimulationConfig(seed=42))
    b = SimulationEngine(SimulationConfig(seed=42))
    a.run(200)
    b.run(200)
    assert a.next_tick == b.next_tick == 200
    assert _state(a) == _state(b)


@settings(max_examples=20)
@given(st.integers(min_value=0, max_value=2**32 - 1))
def test_determinismo_de_un_motor_pequeno(seed: int) -> None:
    config = small_config(seed=seed, num_agents=6)
    a, b = SimulationEngine(config), SimulationEngine(config)
    a.run(15)
    b.run(15)
    assert _state(a) == _state(b)


def test_run_devuelve_la_historia_completa() -> None:
    engine = SimulationEngine(small_config())
    first = engine.run(3)
    second = engine.run(2)
    assert [m.tick for m in first] == [0, 1, 2]
    assert [m.tick for m in second] == [3, 4]
    assert [m.tick for m in engine.history] == [0, 1, 2, 3, 4]


# --- Perturbaciones ----------------------------------------------------------------------------


def test_inject_false_belief_en_el_25_por_ciento() -> None:
    engine = SimulationEngine(SimulationConfig())
    engine.run(10)
    ids = engine.inject_false_belief(pat(0), -1.0, 0.95, 0.25)
    assert len(ids) == 20 and ids == sorted(set(ids))
    for aid in ids:
        unit = engine.agents[aid].memory.get(pat(0))
        assert unit == KnowledgeUnit(pat(0), -1.0, 0.95, 1, 10, False)


def test_ablate_population_del_50_por_ciento() -> None:
    engine = SimulationEngine(SimulationConfig())
    removed = engine.ablate_population(0.50)
    assert len(removed) == 40 and removed == sorted(set(removed))
    assert len(engine.agents) == 40
    assert engine.env.get_active_agent_ids() == sorted(engine.agents)
    assert not set(removed) & set(engine.agents)


@pytest.mark.parametrize("fraction", [-0.1, 1.5, float("nan"), float("inf"), float("-inf")])
def test_fraccion_invalida_no_consume_el_generador(fraction: float) -> None:
    engine = SimulationEngine(small_config())
    state = engine.rng.bit_generator.state
    with pytest.raises(ValueError, match="fraction"):
        engine.ablate_population(fraction)
    with pytest.raises(ValueError, match="fraction"):
        engine.inject_false_belief(pat(0), -1.0, 0.9, fraction)
    assert engine.rng.bit_generator.state == state
    assert sorted(engine.agents) == list(range(10))
    assert all(len(a.memory) == 0 for a in engine.agents.values())


@pytest.mark.parametrize(
    "overrides",
    [{"comm_enabled": False}, {"max_queries_per_tick": 0}, {"comm_content_null": True}],
)
def test_sin_canal_veraz_la_cobertura_accesible_es_la_individual(
    monkeypatch: pytest.MonkeyPatch, overrides: dict[str, Any]
) -> None:
    engine = SimulationEngine(small_config(**overrides))
    recorded = record_calls(monkeypatch, engine.collector, "record_tick")
    history = engine.run(40)
    assert any(m.individual_coverage_mean > 0 for m in history)
    for metrics in history:
        assert metrics.accessible_coverage_mean == pytest.approx(
            metrics.individual_coverage_mean, abs=1e-9
        )
    # Contrato de `record_tick`: el mapa de vecinos llega vacío por agente.
    assert all(not any(call[3].values()) for call in recorded)
    snap = engine.snapshot()
    assert snap.accessible_coverage_mean == pytest.approx(snap.individual_coverage_mean, abs=1e-9)


def test_con_canal_veraz_la_cobertura_accesible_supera_a_la_individual() -> None:
    engine = SimulationEngine(small_config())
    history = engine.run(40)
    assert any(m.accessible_coverage_mean > m.individual_coverage_mean for m in history)


def test_snapshot_sin_efectos_secundarios() -> None:
    engine = SimulationEngine(SimulationConfig())
    engine.run(50)
    cumulative = engine.history[-1].cumulative_decision_accuracy
    engine.ablate_population(0.5)
    rng_state = engine.rng.bit_generator.state
    first, second = engine.snapshot(), engine.snapshot()
    assert first == second
    assert first.active_agents == 40
    assert len(engine.history) == 50 and engine.next_tick == 50
    assert engine.rng.bit_generator.state == rng_state
    after = engine.step()
    assert after.tick == 50 and engine.history[-2].cumulative_decision_accuracy == cumulative


def test_ablate_discoverers_preserva_al_portador_social() -> None:
    engine = SimulationEngine(small_config())
    grid = grid_of(engine)
    cell, _ = first_resource_of(grid, pat(1))
    walk_to(grid, 1, cell)
    neighbor = next(
        ((cell[0] + dx) % 10, (cell[1] + dy) % 10)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if (dx, dy) != (0, 0)
        and not grid.cell_resources[((cell[0] + dx) % 10, (cell[1] + dy) % 10)]
    )
    walk_to(grid, 2, neighbor)
    engine.agents[1].memory.upsert(direct(pat(1), 1.0), 0, force=True)
    engine.step()
    assert 1 in engine.direct_discoverers[pat(1)]
    assert 2 not in engine.direct_discoverers[pat(1)]
    carried = engine.agents[2].memory.get(pat(1))
    assert carried is not None and not carried.from_direct_experience

    removed = engine.ablate_discoverers(pat(1))
    assert 1 in removed and 2 not in removed
    assert removed == sorted(engine.direct_discoverers[pat(1)])
    assert 1 not in engine.agents and 1 not in grid.get_active_agent_ids()
    assert all(r.pattern != pat(1) for _, r in resources_of(grid))
    assert engine.agents[2].memory.get(pat(1)) == carried
    engine.run(5)  # el estímulo retirado no se repone
    assert all(r.pattern != pat(1) for _, r in resources_of(grid))


def test_ruteo_con_los_vecinos_de_la_observacion(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(small_config())
    engine.run(20)  # creencias que difundir
    target, other = 0, 1
    original = engine.env.get_observation

    def redirect(agent_id: int, tick: int) -> Observation:
        obs = original(agent_id, tick)
        return replace(obs, neighbor_ids=(other,) if agent_id == target else (target,))

    monkeypatch.setattr(engine.env, "get_observation", redirect)
    emitted: list[Message] = []
    inboxes: dict[int, list[Message]] = {}
    for aid, agent in engine.agents.items():
        emit, process = agent.perceive_and_emit_messages, agent.process_incoming_messages

        def emit_spy(obs: Observation, tick: int, _e: Any = emit) -> Any:
            out = _e(obs, tick)
            emitted.extend(out)
            return out

        def spy(messages: list[Message], tick: int, _aid: int = aid, _p: Any = process) -> Any:
            inboxes.setdefault(_aid, list(messages))  # sólo la primera pasada
            return _p(messages, tick)

        monkeypatch.setattr(agent, "perceive_and_emit_messages", emit_spy)
        monkeypatch.setattr(agent, "process_incoming_messages", spy)
    metrics = engine.step()
    assert metrics.messages_sent > 0
    receivers = sorted(aid for aid, inbox in inboxes.items() if inbox)
    assert set(receivers) <= {target, other}
    # El agente 0 recibe, en orden de emisión, todos los mensajes de los demás emisores, y el
    # agente 1 todos los del agente 0 (los emitidos en la fase 1 no llevan `recipient_id`).
    assert all(m.recipient_id is None for m in emitted)
    assert inboxes[target] == [m for m in emitted if m.sender_id != target]
    assert inboxes[other] == [m for m in emitted if m.sender_id == target]
    assert inboxes[target]


def test_ablate_discoverers_sin_retirar_el_estimulo() -> None:
    engine = SimulationEngine(small_config())
    engine.run(30)
    pattern = next(p for p in sorted(engine.direct_discoverers) if engine.direct_discoverers[p])
    removed = engine.ablate_discoverers(pattern, retire_stimulus=False)
    assert removed and not set(removed) & set(engine.agents)
    assert any(r.pattern == pattern for _, r in resources_of(grid_of(engine)))


# --- Control nulo de contenido -----------------------------------------------------------------


def test_determinismo_del_control_nulo() -> None:
    config = SimulationConfig(seed=42, comm_content_null=True)
    a, b = SimulationEngine(config), SimulationEngine(config)
    a.run(100)
    b.run(100)
    assert a.history == b.history


def test_control_nulo_una_extraccion_por_entrega(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(small_config(comm_content_null=True))
    calls = record_calls(monkeypatch, engine_module, "nullify_belief")
    deliveries = 0
    for agent in engine.agents.values():
        original = agent.process_incoming_messages

        def wrapper(messages: list[Message], tick: int, _orig: Any = original) -> list[Message]:
            nonlocal deliveries
            deliveries += sum(1 for m in messages if m.belief is not None)
            return _orig(messages, tick)

        monkeypatch.setattr(agent, "process_incoming_messages", wrapper)
    engine.run(30)
    assert deliveries > 0 and len(calls) == deliveries
    assert all(call[-1].predicted_value in (1.0, -1.0) for call in calls)
    expected = np.random.Generator(np.random.PCG64(np.random.SeedSequence(42, spawn_key=(1,))))
    expected.random(deliveries)
    assert engine.null_rng.bit_generator.state == expected.bit_generator.state


def test_el_control_no_desplaza_el_generador_principal() -> None:
    plain = SimulationEngine(SimulationConfig(seed=42))
    null = SimulationEngine(SimulationConfig(seed=42, comm_content_null=True))
    a, b = plain.step(), null.step()
    assert plain.rng.bit_generator.state == null.rng.bit_generator.state
    # Bajo el control nulo no hay canal de consulta veraz: la cobertura accesible es la individual.
    assert b.accessible_coverage_mean == pytest.approx(b.individual_coverage_mean, abs=1e-9)
    assert replace(a, accessible_coverage_mean=0.0) == replace(b, accessible_coverage_mean=0.0)
