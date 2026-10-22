"""Tests de `simulation-engine`: pipeline de 5 fases, determinismo y perturbaciones."""

import ast
import builtins
import copy
import hashlib
import os
import subprocess
import sys
import textwrap
from collections.abc import Callable
from dataclasses import astuple, replace
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from ide.agent.dna import encode_codon, founder_dna, mutate_dna, transcribe_phenotype
from ide.agent.evolution import compute_dna_cost, compute_metabolic_cost
from ide.agent.holon import CompositeAgent, composite_nodes
from ide.agent.memory import BoundedMemory
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig
from ide.domain.extensions import AgentCapabilities, integer_trait_bounds
from ide.domain.types import (
    ActionResult,
    ActionType,
    AgentAction,
    AgentGenome,
    CompactDNA,
    EpigeneticContext,
    EpigeneticRole,
    KnowledgeUnit,
    Message,
    Observation,
    Pattern,
    Resource,
)
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS, ablate
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


def test_oraculo_de_verdad_nadie_fuera_del_motor_lo_referencia() -> None:
    """Ningún módulo de `src/ide` salvo el motor referencia `get_reachable_true_values`.

    Cuenta atributos, nombres, cadenas (`getattr`) e importaciones; las definiciones del
    puerto y del entorno no son referencias.
    """
    nombre = "get_reachable_true_values"
    src = Path(__file__).resolve().parents[1] / "src" / "ide"
    nodos = [
        (path.relative_to(src).as_posix(), node)
        for path in src.rglob("*.py")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
    ]
    # Control del recorrido: si el AST no se leyera, el conjunto vacío pasaría sin detectar nada.
    definen = {ruta for ruta, n in nodos if isinstance(n, ast.FunctionDef) and n.name == nombre}
    assert "domain/ports.py" in definen
    referencian = {
        ruta
        for ruta, node in nodos
        if (isinstance(node, ast.Attribute) and node.attr == nombre)
        or (isinstance(node, ast.Name) and node.id == nombre)
        or (isinstance(node, ast.Constant) and node.value == nombre)
        or (isinstance(node, ast.alias) and node.name == nombre)
    }
    assert referencian <= {"simulation/engine.py"}


# --- Fase II: generadores, vista del holón, compuestos y Fase 5 (bloque 5) ---------------------

COMP2 = Pattern((("id", "c_0"), ("order", "2")))
COMP3 = Pattern((("id", "c_0"), ("order", "3")))
IDLE = AgentAction(ActionType.IDLE)


def quiet(**overrides: Any) -> SimulationConfig:
    """Configuración chica sin costos energéticos ni reproducción, salvo que se pidan."""
    costs: dict[str, Any] = {
        "metabolic_base_cost": 0.0,
        "memory_capacity_cost": 0.0,
        "sensory_radius_cost": 0.0,
        "move_cost": 0.0,
        "message_cost": 0.0,
        "holon_coord_cost": 0.0,
        "reproduction_threshold": 100.0,
    }
    return small_config(**{**costs, **overrides})


def act(
    monkeypatch: pytest.MonkeyPatch,
    engine: SimulationEngine,
    actions: dict[int, AgentAction] | None = None,
) -> None:
    """Fija la acción de cada agente actual: la de `actions` o `IDLE`."""
    actions = actions or {}
    for aid, agent in engine.agents.items():
        action = actions.get(aid, IDLE)
        monkeypatch.setattr(agent, "decide_action", lambda *_args, a=action: a)


def make_holon(engine: SimulationEngine, ids: list[int]) -> CompositeAgent:
    """Agrupa en un holón raíz nuevo los nodos raíz de las hojas `ids`."""
    children = tuple(engine.root_nodes.pop(engine.agent_to_root[aid]) for aid in ids)
    holon = CompositeAgent(engine.next_holon_id, children, engine.next_tick, True)
    engine.next_holon_id -= 1
    engine.root_nodes[holon.node_id] = holon
    for leaf in holon.leaf_agents:
        engine.agent_to_root[leaf.agent_id] = holon.node_id
    return holon


def replace_agent(
    engine: SimulationEngine,
    aid: int,
    genome: AgentGenome,
    energy: float = 1.5,
    generation: int = 0,
) -> MicroAgent:
    """Sustituye un agente fundador por uno con genoma y linaje dados, en la misma celda."""
    agent = MicroAgent.from_lineage(aid, engine.config, genome, energy, generation, None)
    engine.agents[aid] = agent
    engine.root_nodes[aid] = agent
    return agent


def shifted(cell: Cell, dx: int = 1, side: int = 10) -> Cell:
    return ((cell[0] + dx) % side, cell[1])


def test_generadores_derivados_de_la_semilla() -> None:
    engine = SimulationEngine(small_config(seed=9))
    for key, generator in ((2, engine.evo_rng), (4, engine.donor_rng)):
        ref = np.random.Generator(np.random.PCG64(np.random.SeedSequence(9, spawn_key=(key,))))
        assert generator.bit_generator.state == ref.bit_generator.state


def test_un_nacimiento_consume_evo_rng_y_no_el_generador_principal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = quiet(enable_evolution=True, reproduction_threshold=5.0)
    a, b = SimulationEngine(config), SimulationEngine(config)
    fresh = copy.deepcopy(b.evo_rng.bit_generator.state)
    a.agents[0].apply_energy_delta(10.0)
    a.step()
    b.step()
    assert len(a.agents) == len(b.agents) + 1
    assert a.rng.bit_generator.state == b.rng.bit_generator.state
    assert a.evo_rng.bit_generator.state != fresh
    assert b.evo_rng.bit_generator.state == fresh


def test_evolucion_sin_nacimientos_ni_muertes_conserva_la_secuencia_de_fase_i() -> None:
    base = small_config(seed=3)
    evo = replace(base, enable_evolution=True, initial_energy=100.0, reproduction_threshold=1e9)
    a, b = SimulationEngine(base), SimulationEngine(evo)
    a.run(30)
    b.run(30)
    assert _state(a) == _state(b)


def test_estado_holonico_inicial() -> None:
    engine = SimulationEngine(small_config())
    assert engine.root_nodes == engine.agents
    assert engine.agent_to_root == {aid: aid for aid in engine.agents}
    assert engine.next_holon_id == -2
    assert engine.next_agent_id == 10
    assert engine.composite_completions == 0
    assert engine.evolutionary_history == []


def _holon_view_setup(**overrides: Any) -> SimulationEngine:
    """Agentes 1 y 2 en un holón, junto a un recurso de ρ_1 que sólo el agente 2 conoce."""
    config = small_config(
        num_agents=3,
        resources_per_pattern=1,
        max_broadcast_per_tick=0,
        enable_holonic_hierarchy=True,
        **overrides,
    )
    engine = SimulationEngine(config)
    grid = grid_of(engine)
    cell, _ = first_resource_of(grid, pat(1))
    walk_to(grid, 1, shifted(cell))
    walk_to(grid, 2, shifted(cell))
    engine.agents[2].memory.upsert(direct(pat(1), 1.0), 0)
    make_holon(engine, [1, 2])
    return engine


def _queried(calls: list[tuple[Any, ...]]) -> list[Pattern]:
    return [m.pattern for m in calls[0][-1] if m.msg_type.name == "QUERY_PATTERN"]


def test_el_holon_evita_consultas_sobre_lo_que_ya_sabe(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _holon_view_setup()
    emitted = record_calls(monkeypatch, engine.agents[1], "perceive_and_emit_messages")
    engine.step()
    assert pat(1) not in _queried(emitted)
    assert engine.agents[1].own_belief(pat(1)) is None


def test_ablacion_de_la_vista_del_holon(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _holon_view_setup(enable_holon_view=False)
    emitted = record_calls(monkeypatch, engine.agents[1], "perceive_and_emit_messages")
    engine.step()
    assert pat(1) in _queried(emitted)
    assert engine.agents[1]._holon_tick_beliefs == {}


def test_la_vista_del_tiempo_2_lee_lo_obtenido_en_la_fase_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _holon_view_setup()
    agent2 = engine.agents[2]
    learned = KnowledgeUnit(pat(3), 1.0, 0.8, 1, 0, False)
    original = agent2.process_incoming_messages

    def spy(messages: list[Message], tick: int) -> list[Message]:
        out = original(messages, tick)
        agent2._ephemeral_tick_beliefs[learned.pattern] = learned  # sólo en el caché del tick
        return out

    monkeypatch.setattr(agent2, "process_incoming_messages", spy)
    engine.step()
    assert engine.agents[1]._holon_tick_beliefs.get(pat(3)) == learned


def test_la_vista_no_incluye_hojas_fuera_de_alcance_local() -> None:
    engine = _holon_view_setup(comm_radius=0)
    grid = grid_of(engine)
    walk_to(grid, 2, shifted(grid.get_agent_position(1), 3))
    engine.step()
    assert pat(1) not in engine.agents[1]._holon_tick_beliefs


def test_el_control_nulo_alcanza_a_la_vista_del_holon(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _holon_view_setup(comm_content_null=True)
    calls = record_calls(monkeypatch, engine_module, "nullify_belief")
    engine.step()
    assert any(call[0].pattern == pat(1) for call in calls)
    assert engine.agents[1]._holon_tick_beliefs[pat(1)].predicted_value in (-1.0, 1.0)


def _composite_setup(
    monkeypatch: pytest.MonkeyPatch, **overrides: Any
) -> tuple[SimulationEngine, CompositeAgent, Resource]:
    """Holón (1, 2) en celdas vecinas que conoce los fragmentos de `c_0`; el 1 lo consume."""
    settings_: dict[str, Any] = {
        "num_agents": 3,
        "num_composite_patterns": 1,
        "enable_holonic_hierarchy": True,
        **overrides,
    }
    engine = SimulationEngine(quiet(**settings_))
    grid = grid_of(engine)
    cell, resource = first_resource_of(grid, COMP2)
    walk_to(grid, 1, cell)
    walk_to(grid, 2, shifted(cell))
    engine.agents[1].memory.upsert(direct(pat(0), 1.0), 0)
    engine.agents[2].memory.upsert(direct(pat(1), 1.0), 0)
    holon = make_holon(engine, [1, 2])
    act(monkeypatch, engine, {1: AgentAction(ActionType.INTERACT, resource.resource_id)})
    return engine, holon, resource


def test_holon_con_memorias_complementarias_resuelve_el_compuesto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, holon, _ = _composite_setup(monkeypatch, enable_stigmergy=True)
    engine.step()
    assert engine.composite_completions == 1
    assert engine.evolutionary_history[-1].composite_completions == 1
    assert COMP2 not in engine.direct_discoverers
    learned = engine.agents[1].memory.get(COMP2)
    assert learned is not None and learned.from_direct_experience
    assert learned.predicted_value > 0
    assert holon.cooperative_completions == 1
    assert holon.ticks_without_surplus == 0
    traces = grid_of(engine).cell_stigmergy.values()
    assert all(COMP2 not in cell for cell in traces)


def test_la_resolucion_compuesta_no_depende_del_orden_de_la_fase_4(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El agente 2 se aleja en la Fase 4; cuenta el alcance local al empezar la fase."""
    orders: set[bool] = set()
    for seed in range(8):
        with monkeypatch.context() as patch:
            engine, _, resource = _composite_setup(patch, seed=seed, comm_radius=0)
            act(
                patch,
                engine,
                {
                    1: AgentAction(ActionType.INTERACT, resource.resource_id),
                    2: AgentAction(ActionType.MOVE, (1, 0)),
                },
            )
            order = [int(a) for a in copy.deepcopy(engine.rng).permutation(sorted(engine.agents))]
            orders.add(order.index(2) < order.index(1))
            engine.step()
            assert engine.composite_completions == 1
    assert orders == {True, False}


def test_individuo_solitario_no_cubre_todos_los_fragmentos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = quiet(
        num_agents=1,
        memory_capacity=2,
        num_composite_patterns=1,
        composite_order=3,
        enable_evolution=True,
    )
    engine = SimulationEngine(config)
    grid = grid_of(engine)
    cell, resource = first_resource_of(grid, COMP3)
    walk_to(grid, 0, cell)
    agent = engine.agents[0]
    agent.memory.upsert(direct(pat(0), 1.0), 0)
    agent.memory.upsert(direct(pat(1), 1.0), 0)
    act(monkeypatch, engine, {0: AgentAction(ActionType.INTERACT, resource.resource_id)})
    engine.step()
    assert engine.composite_completions == 0
    learned = agent.memory.get(COMP3)
    assert learned is not None
    assert learned.predicted_value == pytest.approx(-config.composite_failure_penalty, abs=1e-9)
    expected = config.initial_energy - config.energy_gain_scale * config.composite_failure_penalty
    assert agent.energy == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize("sharing", [True, False])
def test_reparto_de_la_ganancia_compuesta(monkeypatch: pytest.MonkeyPatch, sharing: bool) -> None:
    engine, _, _ = _composite_setup(
        monkeypatch, enable_evolution=True, holon_energy_sharing=sharing
    )
    config = engine.config
    gain = config.energy_gain_scale * 2**config.composite_reward_exponent
    engine.step()
    first, second = (gain / 2, gain / 2) if sharing else (gain, 0.0)
    assert engine.agents[1].energy == pytest.approx(config.initial_energy + first, abs=1e-9)
    assert engine.agents[2].energy == pytest.approx(config.initial_energy + second, abs=1e-9)


@pytest.mark.parametrize(
    ("interact", "with_elemental", "expected"),
    [(True, True, 0), (False, False, 0), (False, True, 1)],
)
def test_m2_se_mide_solo_sobre_recursos_elementales(
    monkeypatch: pytest.MonkeyPatch, interact: bool, with_elemental: bool, expected: int
) -> None:
    engine, _, resource = _composite_setup(monkeypatch)
    if not interact:
        act(monkeypatch, engine)
    truth = {resource.resource_id: resource.true_value}
    if with_elemental:
        truth[10**6] = 1.0
    monkeypatch.setattr(
        engine.env, "get_reachable_true_values", lambda aid: dict(truth) if aid == 1 else {}
    )
    engine.step()
    assert engine.history[-1].decision_opportunities == expected


def test_penalizacion_cuadratica_del_cerebro_individual(monkeypatch: pytest.MonkeyPatch) -> None:
    config = small_config(
        num_agents=2,
        comm_enabled=False,
        enable_evolution=True,
        metabolic_base_cost=0.02,
        memory_capacity_cost=0.005,
        sensory_radius_cost=0.0,
        reproduction_threshold=100.0,
    )
    engine = SimulationEngine(config)
    replace_agent(engine, 1, replace(engine.agents[1].genome, memory_capacity=6))
    act(monkeypatch, engine)
    engine.step()
    assert engine.agents[0].energy == pytest.approx(1.5 - 0.065, abs=1e-9)
    assert engine.agents[1].energy == pytest.approx(1.5 - 0.200, abs=1e-9)


def test_metabolismo_cobra_movimiento_y_mensajes(monkeypatch: pytest.MonkeyPatch) -> None:
    config = small_config(
        num_agents=4,
        enable_evolution=True,
        move_cost=0.01,
        message_cost=0.003,
        reproduction_threshold=100.0,
    )
    engine = SimulationEngine(config)
    act(monkeypatch, engine, {0: AgentAction(ActionType.MOVE, (1, 0))})
    emitted = {
        a: record_calls(monkeypatch, engine.agents[a], "perceive_and_emit_messages")
        for a in engine.agents
    }
    answered = {
        a: record_calls(monkeypatch, engine.agents[a], "process_incoming_messages")
        for a in engine.agents
    }
    engine.step()
    total = 0
    for aid, agent in engine.agents.items():
        sent = len(emitted[aid][0][-1]) + sum(len(call[-1]) for call in answered[aid])
        total += sent
        cost = compute_metabolic_cost(agent.genome, config) + 0.003 * sent
        cost += 0.01 if aid == 0 else 0.0
        assert agent.energy == pytest.approx(config.initial_energy - cost, abs=1e-9)
    assert total > 0


@pytest.mark.parametrize(("index", "sign"), [(0, 1.0), (6, -1.0)])
def test_ganancia_por_recurso_elemental(
    monkeypatch: pytest.MonkeyPatch, index: int, sign: float
) -> None:
    engine = SimulationEngine(quiet(num_agents=1, enable_evolution=True))
    grid = grid_of(engine)
    cell, resource = first_resource_of(grid, pat(index))
    walk_to(grid, 0, cell)
    act(monkeypatch, engine, {0: AgentAction(ActionType.INTERACT, resource.resource_id)})
    engine.step()
    expected = 1.5 + sign * engine.config.energy_gain_scale
    assert engine.agents[0].energy == pytest.approx(expected, abs=1e-9)


def test_muerte_por_inanicion_en_el_mismo_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(quiet(num_agents=3, enable_evolution=True))
    engine.agents[1].apply_energy_delta(-1.5)
    act(monkeypatch, engine)
    engine.step()
    assert 1 not in engine.agents
    assert 1 not in engine.env.get_active_agent_ids()
    assert engine.evolutionary_history[-1].deaths_this_tick == 1
    assert engine.evolutionary_history[-1].active_agents == 2


def test_la_muerte_poda_el_holon(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(
        quiet(num_agents=3, enable_evolution=True, enable_holonic_hierarchy=True)
    )
    holon = make_holon(engine, [1, 2])
    engine.agents[1].apply_energy_delta(-1.5)
    act(monkeypatch, engine)
    engine.step()
    assert holon.node_id not in engine.root_nodes
    assert engine.root_nodes[2] is engine.agents[2]
    assert engine.agent_to_root == {0: 0, 2: 2}


def test_la_ablacion_poda_y_reinicia_el_estado_de_formacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = SimulationEngine(
        quiet(
            num_agents=4,
            comm_enabled=False,
            enable_holonic_hierarchy=True,
            holon_bond_threshold=1.0,
        )
    )
    engine.agents[0].memory.upsert(direct(pat(0), 1.0), 0)
    engine.agents[2].memory.upsert(direct(pat(1), 1.0), 0)
    engine.agents[2].memory.upsert(direct(pat(7), 1.0), 0)  # signo incorrecto: no cuenta
    holon = make_holon(engine, [0, 1, 2])
    act(monkeypatch, engine)
    engine.run(2)
    engine.direct_discoverers[pat(5)] = {1}
    assert engine.ablate_discoverers(pat(5), retire_stimulus=False) == [1]
    assert [leaf.agent_id for leaf in holon.leaf_agents] == [0, 2]
    assert holon.formation_tick == engine.next_tick == 2
    assert holon.formation_knowledge == ((0, frozenset({pat(0)})), (2, frozenset({pat(1)})))
    assert engine.agent_to_root == {0: holon.node_id, 2: holon.node_id, 3: 3}


def test_particion_exacta_de_energia_y_linaje(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(
        quiet(num_agents=6, enable_evolution=True, reproduction_threshold=2.0)
    )
    replace_agent(engine, 4, engine.agents[4].genome, energy=2.4, generation=2)
    act(monkeypatch, engine)
    engine.step()
    child = engine.agents[6]
    assert (child.parent_id, child.generation) == (4, 3)
    assert child.energy == pytest.approx(1.2, abs=1e-9)
    assert engine.agents[4].energy == pytest.approx(1.2, abs=1e-9)
    assert engine.root_nodes[6] is child and engine.agent_to_root[6] == 6
    assert grid_of(engine).get_agent_distance(4, 6) <= 1
    assert engine.next_agent_id == 7
    assert engine.evolutionary_history[-1].births_this_tick == 1


def test_respeto_estricto_de_la_capacidad_de_carga(monkeypatch: pytest.MonkeyPatch) -> None:
    config = quiet(
        num_agents=3, enable_evolution=True, reproduction_threshold=2.0, max_population=3
    )
    engine = SimulationEngine(config)
    engine.agents[0].apply_energy_delta(1.0)
    act(monkeypatch, engine)
    engine.step()
    assert sorted(engine.agents) == [0, 1, 2]
    assert engine.agents[0].energy == pytest.approx(2.5, abs=1e-9)


def test_reproduccion_holonica_y_un_evento_por_agente(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(
        quiet(
            num_agents=3,
            enable_evolution=True,
            enable_holonic_hierarchy=True,
            enable_holon_reproduction=True,
            holon_bond_threshold=1.0,
            reproduction_threshold=2.0,
        )
    )
    holon = make_holon(engine, [0, 1])
    for aid in (0, 1):
        engine.agents[aid].apply_energy_delta(10.0)
    act(monkeypatch, engine)
    engine.step()
    assert engine.evolutionary_history[-1].births_this_tick == 2
    assert sorted(engine.agents) == [0, 1, 2, 3, 4]
    child_holon = engine.root_nodes[engine.agent_to_root[3]]
    assert isinstance(child_holon, CompositeAgent) and child_holon is not holon
    assert [leaf.agent_id for leaf in child_holon.leaf_agents] == [3, 4]
    assert [leaf.parent_id for leaf in child_holon.leaf_agents] == [0, 1]
    assert not child_holon.formed_by_bond
    assert child_holon.formation_knowledge == ((3, frozenset()), (4, frozenset()))
    for aid in (0, 1):
        assert engine.agents[aid].energy == pytest.approx(11.5 / 2, abs=1e-9)


def test_sin_r17_las_hojas_se_reproducen_por_separado(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(
        quiet(
            num_agents=3,
            enable_evolution=True,
            enable_holonic_hierarchy=True,
            holon_bond_threshold=1.0,
            reproduction_threshold=2.0,
        )
    )
    holon = make_holon(engine, [0, 1])
    for aid in (0, 1):
        engine.agents[aid].apply_energy_delta(10.0)
    act(monkeypatch, engine)
    engine.step()
    assert engine.root_nodes[3] is engine.agents[3]
    assert engine.root_nodes[4] is engine.agents[4]
    assert engine.root_nodes[holon.node_id] is holon


def test_reproduccion_neutral_misma_demografia_genoma_del_donante(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def build(mode: str) -> SimulationEngine:
        config = quiet(
            num_agents=4,
            enable_evolution=True,
            reproduction_threshold=2.0,
            mutation_rate=0.0,
            discrete_mutation_prob=0.0,
            reproduction_mode=mode,
        )
        engine = SimulationEngine(config)
        for aid in range(4):
            replace_agent(engine, aid, AgentGenome(bond_affinity=0.1 * (aid + 1)))
        for aid in (0, 2):
            engine.agents[aid].apply_energy_delta(1.0)
        with monkeypatch.context() as patch:
            act(patch, engine)
            engine.step()
        return engine

    energy, neutral = build("energy"), build("neutral")
    donor_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(42, spawn_key=(4,))))
    for child_id, parent in ((4, 0), (5, 2)):
        a, b = energy.agents[child_id], neutral.agents[child_id]
        assert a.parent_id == b.parent_id == parent
        assert a.energy == pytest.approx(b.energy, abs=1e-9)
        assert grid_of(energy).get_agent_position(child_id) == grid_of(neutral).get_agent_position(
            child_id
        )
        assert a.genome == energy.agents[parent].genome
        donor = int(donor_rng.integers(4))
        assert b.genome == neutral.agents[donor].genome


def test_herencia_cultural_por_assimilate_testimony(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(
        quiet(
            num_agents=3,
            comm_enabled=False,
            enable_evolution=True,
            enable_cultural_inheritance=True,
            inheritance_discount=0.5,
            reproduction_threshold=2.0,
            mutation_rate=0.0,
            discrete_mutation_prob=0.0,
        )
    )
    engine.agents[0].apply_energy_delta(1.0)
    engine.agents[0].memory.upsert(KnowledgeUnit(pat(1), 1.0, 0.8, 5, 0, True), 0)
    act(monkeypatch, engine)
    calls = record_calls(monkeypatch, MicroAgent, "assimilate_testimony")
    engine.step()
    child = engine.agents[3]
    assert [(c[0].agent_id, c[2], c[3]) for c in calls] == [(3, 0, 0)]
    assert child.memory.get(pat(1)) == KnowledgeUnit(
        pat(1), 1.0, pytest.approx(0.30, abs=1e-9), 1, 0, False
    )


def test_el_control_nulo_alcanza_a_la_herencia_cultural(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(
        quiet(
            num_agents=3,
            comm_enabled=False,
            comm_content_null=True,
            enable_evolution=True,
            enable_cultural_inheritance=True,
            reproduction_threshold=2.0,
        )
    )
    engine.agents[0].apply_energy_delta(1.0)
    engine.agents[0].memory.upsert(KnowledgeUnit(pat(1), 0.6, 0.8, 5, 0, True), 0)
    act(monkeypatch, engine)
    calls = record_calls(monkeypatch, engine_module, "nullify_belief")
    engine.step()
    assert [call[0].pattern for call in calls] == [pat(1)]
    inherited = engine.agents[3].memory.get(pat(1))
    assert inherited is not None and inherited.predicted_value in (-1.0, 1.0)


def test_causalidad_descendente_y_limpieza_tras_split(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(
        quiet(
            num_agents=3,
            comm_enabled=False,
            enable_holonic_hierarchy=True,
            enable_downward_causation=True,
            holon_bond_threshold=1.0,
        )
    )
    grid = grid_of(engine)
    walk_to(grid, 2, grid.get_agent_position(1))
    weaker = KnowledgeUnit(pat(0), 1.0, 0.8, 1, 1, True)
    engine.agents[1].memory.upsert(KnowledgeUnit(pat(0), 1.0, 0.9, 1, 1, True), 0)
    engine.agents[2].memory.upsert(weaker, 0)
    holon = make_holon(engine, [1, 2])
    act(monkeypatch, engine)
    engine.run(2)
    memory = engine.agents[2].memory
    plain = BoundedMemory(memory.capacity, engine.config.lambda_decay)
    unit = memory.get(pat(0))
    assert unit is not None
    penalized = memory.compute_utility(unit, 2)
    assert penalized == pytest.approx(0.25 * plain.compute_utility(unit, 2), abs=1e-9)

    holon.ticks_without_surplus = engine.config.holon_split_patience - 1
    engine.step()
    assert holon.node_id not in engine.root_nodes
    assert engine.root_nodes[1] is engine.agents[1] and engine.root_nodes[2] is engine.agents[2]
    assert memory.get(pat(0)) is not None
    assert memory.compute_utility(unit, 3) == pytest.approx(
        plain.compute_utility(unit, 3), abs=1e-9
    )


def test_split_libera_a_los_hijos_sin_perder_memorias(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(
        quiet(
            num_agents=3,
            comm_enabled=False,
            enable_holonic_hierarchy=True,
            holon_bond_threshold=1.0,
        )
    )
    engine.agents[1].memory.upsert(direct(pat(0), 1.0), 0)
    holon = make_holon(engine, [1, 2])
    holon.ticks_without_surplus = engine.config.holon_split_patience - 1
    act(monkeypatch, engine)
    engine.step()
    assert holon.node_id not in engine.root_nodes
    assert engine.agent_to_root == {0: 0, 1: 1, 2: 2}
    assert engine.agents[1].memory.get(pat(0)) is not None


def test_bond_fusiona_especialistas_complementarios(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(
        quiet(
            num_agents=2,
            comm_enabled=False,
            enable_holonic_hierarchy=True,
            initial_bond_affinity=0.8,
            holon_bond_threshold=0.5,
        )
    )
    grid = grid_of(engine)
    walk_to(grid, 1, grid.get_agent_position(0))
    engine.agents[0].memory.upsert(direct(pat(0), 1.0), 0)
    engine.agents[1].memory.upsert(direct(pat(1), 1.0), 0)
    engine.agents[1].memory.upsert(direct(pat(7), 1.0), 0)  # signo incorrecto
    act(monkeypatch, engine)
    engine.step()
    assert list(engine.root_nodes) == [-2]
    holon = engine.root_nodes[-2]
    assert isinstance(holon, CompositeAgent)
    assert holon.children == (engine.agents[0], engine.agents[1])
    assert holon.formed_by_bond and holon.created_tick == 0
    assert holon.formation_knowledge == ((0, frozenset({pat(0)})), (1, frozenset({pat(1)})))
    assert engine.agent_to_root == {0: -2, 1: -2}
    assert engine.next_holon_id == -3


def test_estigmergia_deposita_y_se_asimila_al_tick_siguiente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = SimulationEngine(quiet(num_agents=1, enable_stigmergy=True))
    grid = grid_of(engine)
    cell, resource = first_resource_of(grid, pat(0))
    walk_to(grid, 0, cell)
    act(monkeypatch, engine, {0: AgentAction(ActionType.INTERACT, resource.resource_id)})
    engine.step()
    trace = grid.cell_stigmergy[cell][pat(0)]
    intensity = engine.config.stigmergy_deposit_rate * engine.config.initial_direct_confidence
    assert trace.intensity == pytest.approx(intensity, abs=1e-9)
    assert trace.sign_value == 1.0 and trace.last_updated_tick == 0
    act(monkeypatch, engine)
    calls = record_calls(monkeypatch, MicroAgent, "assimilate_testimony")
    engine.step()
    assert [(c[1].pattern, c[2]) for c in calls] == [(pat(0), -1)]
    assert calls[0][1].confidence == pytest.approx(intensity, abs=1e-9)


def test_historial_evolutivo_en_una_corrida_de_fase_i() -> None:
    engine = SimulationEngine(small_config())
    engine.run(5)
    assert [m.tick for m in engine.evolutionary_history] == list(range(5))
    assert all(m.births_this_tick == m.deaths_this_tick == 0 for m in engine.evolutionary_history)


def test_sucesion_generacional_y_formacion_de_holones() -> None:
    config = SimulationConfig(
        enable_evolution=True,
        enable_cultural_inheritance=True,
        enable_holonic_hierarchy=True,
        resources_per_pattern=40,
    )
    engine = SimulationEngine(config)
    engine.run(100)
    history = engine.evolutionary_history
    assert len(history) == 100
    assert all(m.active_agents <= config.max_population for m in history)
    assert any(m.births_this_tick > 0 for m in history)
    assert max(m.max_generation for m in history) >= 1


def _forest_is_consistent(engine: SimulationEngine) -> bool:
    leaves = sorted(
        leaf.agent_id for node in engine.root_nodes.values() for leaf in node.leaf_agents
    )
    index = {leaf.agent_id: nid for nid, n in engine.root_nodes.items() for leaf in n.leaf_agents}
    return leaves == sorted(engine.agents) and index == engine.agent_to_root


PHASE2_ALL = {
    "enable_evolution": True,
    "enable_cultural_inheritance": True,
    "enable_holonic_hierarchy": True,
    "enable_holon_reproduction": True,
    "enable_downward_causation": True,
    "enable_stigmergy": True,
    "num_composite_patterns": 2,
}


@settings(max_examples=10)
@given(st.integers(min_value=0, max_value=2**32 - 1))
def test_el_bosque_holonico_particiona_a_la_poblacion(seed: int) -> None:
    engine = SimulationEngine(small_config(seed=seed, resources_per_pattern=6, **PHASE2_ALL))
    for _ in range(40):
        engine.step()
        assert _forest_is_consistent(engine)
    engine.ablate_population(0.3)
    assert _forest_is_consistent(engine)


def test_determinismo_con_todas_las_banderas_de_fase_ii() -> None:
    config = small_config(seed=21, resources_per_pattern=6, **PHASE2_ALL)
    a, b = SimulationEngine(config), SimulationEngine(config)
    a.run(40)
    b.run(40)
    assert _state(a) == _state(b)
    assert a.evolutionary_history == b.evolutionary_history


def test_fase_ii_independiente_del_hash() -> None:
    script = textwrap.dedent(
        """
        from ide.config import SimulationConfig
        from ide.simulation.engine import SimulationEngine

        engine = SimulationEngine(
            SimulationConfig(
                seed=11, num_agents=30, resources_per_pattern=20, enable_evolution=True,
                enable_cultural_inheritance=True, enable_holonic_hierarchy=True,
                enable_holon_reproduction=True, enable_downward_causation=True,
                enable_stigmergy=True, num_composite_patterns=2,
            )
        )
        engine.run(30)
        print(engine.history[-1])
        print(engine.evolutionary_history[-1])
        print(sorted(engine.root_nodes), sorted(engine.agents))
        print([engine.agents[a].memory.all_units() for a in sorted(engine.agents)])
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


def test_fase_ii_exige_un_entorno_evolutivo() -> None:
    class PhaseOneOnly:
        def __init__(self, grid: ToroidalGrid2D) -> None:
            self._grid = grid

        def get_active_agent_ids(self) -> list[int]:
            return self._grid.get_active_agent_ids()

    config = small_config(enable_evolution=True)
    grid = ToroidalGrid2D(config, np.random.Generator(np.random.PCG64(0)))
    with pytest.raises(TypeError, match="EvolutionaryEnvironmentPort"):
        SimulationEngine(config, env=cast(Any, PhaseOneOnly(grid)))


def test_sin_comunicacion_no_se_cobran_mensajes() -> None:
    config = quiet(num_agents=6, comm_enabled=False, enable_evolution=True, message_cost=0.5)
    engine = SimulationEngine(config)
    walk_to(grid_of(engine), 1, grid_of(engine).get_agent_position(0))
    engine.agents[0].memory.upsert(direct(pat(0), 1.0), 0)  # tendría algo que difundir
    with pytest.MonkeyPatch.context() as patch:
        act(patch, engine)
        engine.step()
    assert engine.history[-1].messages_sent == 0
    assert all(a.energy == pytest.approx(1.5, abs=1e-9) for a in engine.agents.values())


def test_un_sub_holon_liberado_por_split_reinicia_su_paciencia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = SimulationEngine(
        quiet(
            num_agents=4,
            comm_enabled=False,
            enable_holonic_hierarchy=True,
            holon_bond_threshold=1.0,
        )
    )
    inner = make_holon(engine, [0, 1])
    inner.ticks_without_surplus = engine.config.holon_split_patience - 1
    outer = make_holon(engine, [0, 2])
    outer.ticks_without_surplus = engine.config.holon_split_patience - 1
    act(monkeypatch, engine)
    engine.step()
    assert outer.node_id not in engine.root_nodes
    assert engine.root_nodes[inner.node_id] is inner
    assert inner.ticks_without_surplus == 0
    engine.step()
    assert engine.root_nodes.get(inner.node_id) is inner


# --- Fase II-B: motor con ADN compacto, R24 (bloque 5 de la Fase II-B, design D34) ------------


def dna_config(**overrides: Any) -> SimulationConfig:
    """`quiet` con evolución y ADN compacto: sin costos ni reproducción, salvo que se pidan."""
    return quiet(**{"enable_evolution": True, "enable_compact_dna": True, **overrides})


def dna_with(payloads: dict[int, int], plasmids: tuple[int, ...] = ()) -> CompactDNA:
    """ADN fundador con cargas aditivas `ALWAYS_BASAL`: `payloads[destino] = carga` (D32)."""
    chromosome = tuple(encode_codon(0x00, t, 0, 0, payloads.get(t, 0)) for t in range(9))
    return CompactDNA(chromosome, plasmids)


# Con las bases de `small_config` (C_max = 3, r_perc = r_com = 2): +1 a la capacidad (k = 3),
# +1 a la percepción y -1 a la comunicación (k = 2), redondeados con floor(x + 0.5) (D33).
CAPACITY_UP = {4: 43}
PERCEPTION_UP = {5: 64}
COMM_DOWN = {6: -64}


def generator_states(engine: SimulationEngine) -> list[Any]:
    return [
        copy.deepcopy(g.bit_generator.state)
        for g in (engine.rng, engine.null_rng, engine.evo_rng, engine.donor_rng)
    ]


def test_fase_0_contexto_de_una_hoja_en_un_holon_de_nivel_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = dna_config(num_agents=6, enable_holonic_hierarchy=True, reproduction_threshold=2.2)
    engine = SimulationEngine(config)
    make_holon(engine, [4, 5])
    outer = make_holon(engine, [4, 3])
    assert outer.holon_level == 2
    engine.agents[4].set_epigenetic_role(EpigeneticRole.NERVE)
    engine.agents[4].apply_energy_delta(-0.4)
    calls = {aid: record_calls(monkeypatch, engine.agents[aid], "express") for aid in engine.agents}
    act(monkeypatch, engine)
    engine.step()
    (context, tick, _), *_ = calls[4]
    assert tick == 0
    assert (context.holon_level, context.role) == (2, EpigeneticRole.NERVE)
    assert context.energy_ratio == pytest.approx(0.5, abs=1e-9)
    for aid, level in ((0, 0), (3, 2), (5, 2)):
        (context, tick, _), *_ = calls[aid]
        assert (context.holon_level, context.role, tick) == (level, EpigeneticRole.NONE, 0)
        assert context.energy_ratio == pytest.approx(1.5 / 2.2, abs=1e-9)
    assert all(len(c) == 1 for c in calls.values())  # una expresión por agente y por tick


def test_fase_0_actualiza_los_radios_solo_si_cambian(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(dna_config(num_agents=3))
    engine.agents[1].set_dna(dna_with(CAPACITY_UP))
    engine.agents[2].set_dna(dna_with(PERCEPTION_UP))
    calls = record_calls(monkeypatch, engine.env, "set_agent_radii")
    engine._express_phenotypes(0)  # pyright: ignore[reportPrivateUsage]
    assert [call[:3] for call in calls] == [(2, 3, 2)]
    assert engine.agents[1].genome.memory_capacity == 4
    assert engine.agents[1].memory.capacity == 4
    assert engine.agents[2].genome.perception_radius == 3
    engine._express_phenotypes(1)  # pyright: ignore[reportPrivateUsage]
    assert len(calls) == 1  # sin cambios, no se vuelve a tocar el entorno


# Cargas que llevan los rasgos enteros a sus cotas (con k = 2 o 3, +-127 satura) o los cambian.
_payloads = st.one_of(st.sampled_from([-128, 127]), st.integers(min_value=-128, max_value=127))
# ADN de un agente: capacidad, percepción y comunicación (`ALWAYS_BASAL`), y una carga sobre la
# percepción que sólo se activa dentro de un holón (`IN_HOLON_L1`, promotor 0x02).
_agent_dna = st.tuples(st.fixed_dictionaries({4: _payloads, 5: _payloads, 6: _payloads}), _payloads)
# El segundo contexto puede volver al fenotipo fundador: radios por defecto.
_second_dna = st.one_of(st.just(({4: 0, 5: 0, 6: 0}, 0)), _agent_dna)


def _dna_in_holon(gene: tuple[dict[int, int], int]) -> CompactDNA:
    payloads, in_holon = gene
    chromosome = (*dna_with(payloads).chromosome, encode_codon(0x02, 0x05, 0, 0, in_holon))
    return CompactDNA(chromosome)


def _toroidal_distance(a: Cell, b: Cell, side: int = 10) -> int:
    return max(min(abs(a[i] - b[i]), side - abs(a[i] - b[i])) for i in range(2))


def _check_expressed_radii(engine: SimulationEngine) -> None:
    """La entrada de radios, la vecindad y la percepción de la grilla son las expresadas."""
    grid = grid_of(engine)
    config = engine.config
    capacity_hi, radius_hi = integer_trait_bounds(config)
    default = (config.perception_radius, config.comm_radius)
    stored = grid._agent_radii  # pyright: ignore[reportPrivateUsage]
    resources = resources_of(grid)
    for aid in sorted(engine.agents):
        agent = engine.agents[aid]
        genome = agent.genome
        expressed = (genome.perception_radius, genome.comm_radius)
        if expressed == default:
            assert aid not in stored  # la entrada vieja se borra al volver a los globales
        else:
            assert stored.get(aid) == expressed
        assert all(1 <= radius <= radius_hi for radius in expressed)
        assert 1 <= genome.memory_capacity <= capacity_hi
        assert agent.memory.capacity == genome.memory_capacity
        cell = grid.get_agent_position(aid)
        near = [
            b
            for b in sorted(engine.agents)
            if b != aid and grid.get_agent_distance(aid, b) <= genome.comm_radius
        ]
        assert grid.get_communication_neighbors(aid) == near
        seen = sorted(v.resource_id for v in grid.get_observation(aid, 0).visible_resources)
        assert seen == sorted(
            r.resource_id
            for where, r in resources
            if _toroidal_distance(where, cell) <= genome.perception_radius
        )


_FOUNDER_GENE: tuple[dict[int, int], int] = ({4: 0, 5: 0, 6: 0}, 0)


@settings(max_examples=25)
@example(  # radios a las cotas y luego de vuelta a los globales: borra la entrada de la grilla
    first=[({4: 127, 5: 127, 6: -128}, 0)] * 4, second=[_FOUNDER_GENE] * 4, bond=False
)
@example(  # mismo ADN, cambia sólo el nivel: la percepción de 0 y 1 sube dentro del holón
    first=[({4: -128, 5: 0, 6: 0}, 64)] * 4, second=[None] * 4, bond=True
)
@given(
    st.lists(_agent_dna, min_size=4, max_size=4),
    st.lists(st.one_of(st.none(), _second_dna), min_size=4, max_size=4),
    st.booleans(),
)
def test_fase_0_sin_generadores_y_radios_del_entorno_expresados(
    first: list[tuple[dict[int, int], int]],
    second: list[tuple[dict[int, int], int] | None],
    bond: bool,
) -> None:
    engine = SimulationEngine(dna_config(num_agents=4, enable_holonic_hierarchy=True))
    for aid, gene in enumerate(first):
        engine.agents[aid].set_dna(_dna_in_holon(gene))
    before = generator_states(engine)
    engine._express_phenotypes(0)  # pyright: ignore[reportPrivateUsage]
    assert generator_states(engine) == before
    _check_expressed_radii(engine)
    # Segundo contexto: cambia el ADN de algunos agentes y, quizás, el nivel de 0 y 1.
    for aid, gene in enumerate(second):
        if gene is not None:
            engine.agents[aid].set_dna(_dna_in_holon(gene))
    if bond:
        make_holon(engine, [0, 1])
    engine._express_phenotypes(1)  # pyright: ignore[reportPrivateUsage]
    assert generator_states(engine) == before
    _check_expressed_radii(engine)


def _order_engine() -> SimulationEngine:
    """Población con holones, memorias llenas y ADN que cambia capacidad, radios y nivel."""
    engine = SimulationEngine(dna_config(num_agents=5, enable_holonic_hierarchy=True))
    in_holon_perception = encode_codon(0x02, 0x05, 0, 0, 64)  # IN_HOLON_L1: +1 a la percepción
    dnas = {
        0: dna_with({4: -43, **PERCEPTION_UP}),
        1: CompactDNA((*dna_with({}).chromosome, in_holon_perception)),
        2: dna_with({**COMM_DOWN, 4: -43}),
        3: dna_with(CAPACITY_UP),
    }
    for aid, dna in dnas.items():
        engine.agents[aid].set_dna(dna)
    for aid in sorted(engine.agents):
        for i in range(3):
            engine.agents[aid].memory.upsert(direct(pat(i + aid), 1.0, 0.5 + 0.1 * i), 0)
    make_holon(engine, [1, 2])
    return engine


def _phase_0_state(engine: SimulationEngine) -> tuple[Any, ...]:
    ids = sorted(engine.agents)
    return (
        [engine.agents[a].phenotype for a in ids],
        [engine.agents[a].config for a in ids],
        [engine.agents[a].memory.all_units() for a in ids],
        sorted(grid_of(engine)._agent_radii.items()),  # pyright: ignore[reportPrivateUsage]
        generator_states(engine),
    )


def test_fase_0_independiente_del_orden_de_recorrido(monkeypatch: pytest.MonkeyPatch) -> None:
    ordered, reversed_ = _order_engine(), _order_engine()
    ordered._express_phenotypes(0)  # pyright: ignore[reportPrivateUsage]
    visited: list[int] = []
    with monkeypatch.context() as patch:

        def backwards(items: Any, **kwargs: Any) -> list[Any]:
            result = list(reversed(builtins.sorted(items, **kwargs)))
            visited.extend(result)
            return result

        # Sólo dentro de esta llamada, `sorted` del motor recorre en orden invertido.
        patch.setattr(engine_module, "sorted", backwards, raising=False)
        reversed_._express_phenotypes(0)  # pyright: ignore[reportPrivateUsage]
    assert visited == [4, 3, 2, 1, 0]
    assert _phase_0_state(reversed_) == _phase_0_state(ordered)
    assert ordered.agents[1].genome.perception_radius == 3  # el contexto de holón actuó
    assert ordered.agents[0].memory.capacity == 2  # el olvido forzado actuó


def test_sin_adn_no_corre_la_fase_0(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(quiet(num_agents=3, enable_evolution=True))

    def fail(_tick: int) -> None:
        raise AssertionError("la Fase 0 no corre con enable_compact_dna=False")

    monkeypatch.setattr(engine, "_express_phenotypes", fail)
    engine.run(3)
    assert len(engine.history) == 3


def test_fase_0_antes_de_la_observacion(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(dna_config(num_agents=3))
    grid = grid_of(engine)
    engine.agents[0].set_dna(dna_with(PERCEPTION_UP))
    seen: list[tuple[int, int] | None] = []
    original = grid.get_observation

    def observe(agent_id: int, tick: int) -> Observation:
        if agent_id == 0:
            seen.append(grid._agent_radii.get(0))  # pyright: ignore[reportPrivateUsage]
        return original(agent_id, tick)

    monkeypatch.setattr(grid, "get_observation", observe)
    act(monkeypatch, engine)
    engine.step()
    assert seen == [(3, 2)]


def test_costo_metabolico_del_genoma_expresado_mas_el_adn(monkeypatch: pytest.MonkeyPatch) -> None:
    config = dna_config(
        num_agents=3,
        comm_enabled=False,
        metabolic_base_cost=0.01,
        memory_capacity_cost=0.002,
        sensory_radius_cost=0.003,
        dna_codon_cost=0.01,
    )
    engine = SimulationEngine(config)
    neutral_plasmid = encode_codon(0x00, 0x03, 3)  # modo 3: no se transcribe
    engine.agents[1].set_dna(
        replace(dna_with({**CAPACITY_UP, **PERCEPTION_UP}, (neutral_plasmid,)), crispr_memory=(7,))
    )
    act(monkeypatch, engine)
    engine.step()
    expressed = engine.agents[1].genome
    assert (expressed.memory_capacity, expressed.perception_radius) == (4, 3)
    for aid, codons in ((0, 9), (1, 11), (2, 9)):
        agent = engine.agents[aid]
        assert agent.dna is not None
        assert compute_dna_cost(agent.dna, config) == pytest.approx(0.01 * codons, abs=1e-12)
        cost = compute_metabolic_cost(agent.genome, config) + 0.01 * codons
        assert agent.energy == pytest.approx(1.5 - cost, abs=1e-9)


def _birth_engine(**overrides: Any) -> SimulationEngine:
    config = dna_config(num_agents=4, reproduction_threshold=2.0, **overrides)
    engine = SimulationEngine(config)
    engine.agents[2].set_dna(dna_with({**PERCEPTION_UP, **COMM_DOWN}))
    return engine


def test_nacimiento_con_radios_del_fenotipo_de_nacimiento(monkeypatch: pytest.MonkeyPatch) -> None:
    frozen = {"dna_point_mutation_rate": 0.0, "dna_duplication_rate": 0.0}
    a = _birth_engine(dna_deletion_rate=0.0, **frozen)
    b = _birth_engine(dna_deletion_rate=0.0, **frozen)
    a.agents[2].apply_energy_delta(0.9)
    spawned = record_calls(monkeypatch, a.env, "spawn_agent_near")
    act(monkeypatch, a)
    act(monkeypatch, b)
    a.step()
    b.step()
    child = a.agents[4]
    assert child.dna == a.agents[2].dna  # tasas del ADN en cero: el ADN no cambia
    assert child.birth_tick == 0
    assert [call[:2] + call[3:5] for call in spawned] == [(4, 2, 3, 1)]
    expected = transcribe_phenotype(
        child.dna,
        EpigeneticContext(0, EpigeneticRole.NONE, child.energy / 2.0),
        a.config,
    )
    assert child.phenotype == expected
    assert a.rng.bit_generator.state == b.rng.bit_generator.state
    # Desde el tick siguiente, la Fase 0 lo expresa con su contexto real.
    energy = child.energy  # la Fase 0 lee el estado de fin del tick anterior
    calls = record_calls(monkeypatch, child, "express")
    act(monkeypatch, a)
    a.step()
    (context, tick, _), *_ = calls
    assert (context.holon_level, context.role, tick) == (0, EpigeneticRole.NONE, 1)
    assert context.energy_ratio == pytest.approx(energy / 2.0, abs=1e-9)


def test_nacimiento_muta_el_adn_con_evo_rng(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _birth_engine(dna_point_mutation_rate=0.5)
    parent = engine.agents[2]
    parent.apply_energy_delta(0.9)
    assert parent.dna is not None
    seed = engine.config.seed
    twin = np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed, spawn_key=(2,))))
    expected = mutate_dna(parent.dna, parent.base_config, twin)
    spawned = record_calls(monkeypatch, engine.env, "spawn_agent_near")
    act(monkeypatch, engine)
    engine.step()
    child = engine.agents[4]
    assert child.dna == expected != parent.dna
    genome = child.genome
    assert [call[3:5] for call in spawned] == [(genome.perception_radius, genome.comm_radius)]


def test_reproduccion_neutral_con_el_adn_del_donante(monkeypatch: pytest.MonkeyPatch) -> None:
    def build(mode: str) -> SimulationEngine:
        engine = SimulationEngine(
            dna_config(
                num_agents=4,
                reproduction_threshold=2.0,
                reproduction_mode=mode,
                dna_point_mutation_rate=0.0,
                dna_duplication_rate=0.0,
                dna_deletion_rate=0.0,
            )
        )
        for aid in range(4):
            engine.agents[aid].set_dna(dna_with({3: 16 * (aid + 1)}))  # afinidad distinta
        for aid in (0, 2):
            engine.agents[aid].apply_energy_delta(1.0)
        with monkeypatch.context() as patch:
            act(patch, engine)
            engine.step()
        return engine

    energy, neutral = build("energy"), build("neutral")
    seed = neutral.config.seed
    donor_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed, spawn_key=(4,))))
    for child_id, parent in ((4, 0), (5, 2)):
        a, b = energy.agents[child_id], neutral.agents[child_id]
        assert a.parent_id == b.parent_id == parent
        assert a.energy == pytest.approx(b.energy, abs=1e-9)
        assert a.dna == energy.agents[parent].dna
        donor = int(donor_rng.integers(4))
        assert b.dna == neutral.agents[donor].dna
    assert neutral.donor_rng.bit_generator.state == donor_rng.bit_generator.state


@pytest.mark.parametrize("dna_parent", [True, False])
def test_reproduccion_neutral_rechaza_una_poblacion_mixta(dna_parent: bool) -> None:
    engine = SimulationEngine(dna_config(num_agents=3, reproduction_mode="neutral"))
    founder = engine.agents[1]
    flat = MicroAgent.from_lineage(1, engine.config, founder.genome, 2.0, 0, None)
    assert flat.dna is None and engine.agents[0].dna is not None
    parent, donor = (engine.agents[0], flat) if dna_parent else (flat, engine.agents[0])
    before = generator_states(engine)
    with pytest.raises(ValueError, match="mixta"):
        engine._give_birth(parent, 0, donor)  # pyright: ignore[reportPrivateUsage]
    assert generator_states(engine) == before
    assert 3 not in engine.agents


def test_radios_del_entorno_iguales_a_los_expresados_en_cada_tick() -> None:
    config = small_config(
        seed=5,
        num_agents=20,
        resources_per_pattern=8,
        enable_evolution=True,
        enable_compact_dna=True,
        enable_holonic_hierarchy=True,
        enable_holon_reproduction=True,
        dna_point_mutation_rate=0.3,
    )
    engine = SimulationEngine(config)
    grid = grid_of(engine)
    default = (config.perception_radius, config.comm_radius)
    differed = False
    for _ in range(40):
        engine.step()
        for aid in sorted(engine.agents):
            genome = engine.agents[aid].genome
            expressed = (genome.perception_radius, genome.comm_radius)
            stored = grid._agent_radii.get(aid, default)  # pyright: ignore[reportPrivateUsage]
            assert stored == expressed
            differed = differed or expressed != default
    assert differed  # algún radio expresado se apartó del de la configuración


def test_determinismo_con_adn_compacto() -> None:
    config = small_config(seed=21, resources_per_pattern=6, enable_compact_dna=True, **PHASE2_ALL)
    a, b = SimulationEngine(config), SimulationEngine(config)
    a.run(40)
    b.run(40)
    assert _state(a) == _state(b)
    assert a.evolutionary_history == b.evolutionary_history
    dna_a = [a.agents[x].dna for x in sorted(a.agents)]
    assert dna_a == [b.agents[x].dna for x in sorted(b.agents)]
    assert any(dna != dna_a[0] for dna in dna_a)  # el ADN evolucionó durante la corrida


def test_adn_compacto_independiente_del_hash() -> None:
    script = textwrap.dedent(
        """
        from ide.config import SimulationConfig
        from ide.simulation.engine import SimulationEngine

        engine = SimulationEngine(
            SimulationConfig(
                seed=11, num_agents=30, resources_per_pattern=20, enable_evolution=True,
                enable_compact_dna=True, dna_point_mutation_rate=0.2,
                enable_cultural_inheritance=True, enable_holonic_hierarchy=True,
                enable_holon_reproduction=True, enable_downward_causation=True,
                enable_stigmergy=True, num_composite_patterns=2,
            )
        )
        engine.run(30)
        print(engine.history)
        print(engine.evolutionary_history)
        print(sorted(engine.root_nodes), sorted(engine.agents))
        print([engine.agents[a].dna for a in sorted(engine.agents)])
        print([engine.agents[a].phenotype for a in sorted(engine.agents)])
        print([engine.agents[a].memory.all_units() for a in sorted(engine.agents)])
        """
    )
    outputs = []
    for hash_seed in ("0", "123"):
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


# Configuraciones de la Fase II fijadas bit a bit: los protocolos `002a` y `003a` con sus
# ablaciones, y variantes válidas que ejercen el control nulo en el nacimiento (`null_rng`), la
# estigmergia y la reproducción neutral (R12) con holones.
PHASE2_CASES: dict[str, SimulationConfig] = {
    "002a": PHASE2_PROTOCOL_CONFIGS["002a"],
    "002a-R12": ablate(PHASE2_PROTOCOL_CONFIGS["002a"], ["R12"]),
    "002a-R13": ablate(PHASE2_PROTOCOL_CONFIGS["002a"], ["R13"]),
    "002b-null": replace(PHASE2_PROTOCOL_CONFIGS["002b"], comm_content_null=True),
    "003a": PHASE2_PROTOCOL_CONFIGS["003a"],
    "003a-R12": ablate(PHASE2_PROTOCOL_CONFIGS["003a"], ["R12"]),
    "003a-R15": ablate(PHASE2_PROTOCOL_CONFIGS["003a"], ["R15"]),
    "003a-stigmergy": replace(PHASE2_PROTOCOL_CONFIGS["003a"], enable_stigmergy=True),
}

# Huellas SHA-256 de `phase2_digest` tras 100 ticks, calculadas con el motor de la Fase II previo
# al bloque 5 de la Fase II-B (commit 20305df, en una copia aparte), nunca con el motor nuevo.
# Igual que las de `test_performance_equivalence.py`, exigen igualdad de bits en la plataforma de
# referencia (Linux x86-64, numpy 2.x), en Python 3.11 a 3.13.
PHASE2_GOLDEN = {
    "002a": "0713ae8104d511d78f2adc1bf103587475f201507f87ea9d43c58e4f61ae7c21",
    "002a-R12": "74cbe3f2b1127aac8b4fd5f50a50ea8ef5a50c2cff83821f32cfa704faa01f31",
    "002a-R13": "16ab387fe754cfeef939a818e7f83131cd08aa6f2eac9ed8538d128de5fed363",
    "002b-null": "a58b0acb02d989283e67b36f6fee133c6ceba5d59c5bc0ccb46429dfa8d42663",
    "003a": "d826324c494031926dff7b7208a3f0bc5c9e45bab8560c676937aa1d3fac70b0",
    "003a-R12": "1be881f85f7ab8b8407c988552fc9417e1303e9ad6e86b27ced402521fcd820d",
    "003a-R15": "807f11edd8071fd246204935c46ca11174709d4b302614147af323ad09e13761",
    "003a-stigmergy": "690c71362abc0841c454a52478a1f991f122604b7bbc14f2f956bd6125ae770e",
}


def _rounded(value: Any) -> Any:
    """Redondea a 9 decimales los floats de una tupla de métricas, recursivamente."""
    if isinstance(value, float):
        return round(value, 9) + 0.0  # `+ 0.0` normaliza `-0.0`
    if isinstance(value, tuple):
        return tuple(_rounded(v) for v in cast(tuple[Any, ...], value))
    return value


def phase2_digest(config: SimulationConfig, ticks: int = 100) -> str:
    """Historiales, posiciones, memorias, genomas, bosque, descubridores y generadores.

    Los floats de `evolutionary_history` se redondean a 9 decimales: desde Python 3.12, `sum()`
    de floats usa suma compensada y el último bit de esos promedios difiere entre versiones. El
    resto exige igualdad de bits. El motor también usa `sum()` en su dinámica (por ejemplo, la
    energía de un holón), así que la igualdad entre versiones sólo está verificada para estos
    casos, en Python 3.11, 3.12 y 3.13.
    """
    engine = SimulationEngine(config)
    engine.run(ticks)
    grid = grid_of(engine)
    ids = sorted(engine.agents)
    state = (
        engine.history,
        [_rounded(astuple(m)) for m in engine.evolutionary_history],
        [grid.get_agent_position(a) for a in ids],
        [engine.agents[a].memory.all_units() for a in ids],
        [engine.agents[a].genome for a in ids],
        [
            (nid, node.holon_level, tuple(leaf.agent_id for leaf in node.leaf_agents))
            for nid, node in sorted(engine.root_nodes.items())
        ],
        {p: sorted(found) for p, found in sorted(engine.direct_discoverers.items())},
        [
            g.bit_generator.state
            for g in (engine.rng, engine.null_rng, engine.evo_rng, engine.donor_rng)
        ],
    )
    return hashlib.sha256(repr(state).encode()).hexdigest()


@pytest.mark.parametrize("name", sorted(PHASE2_CASES))
def test_protocolos_de_fase_ii_identicos_con_las_banderas_por_defecto(name: str) -> None:
    assert phase2_digest(PHASE2_CASES[name]) == PHASE2_GOLDEN[name]


# --- Fase II-B: señal posicional (R25, design D36 y D50.1; bloque 18) -------------------------


def roles_config(**overrides: Any) -> SimulationConfig:
    """`dna_config` con holones y R25, sin BOND ni comunicación salvo que se pidan."""
    base: dict[str, Any] = {
        "enable_holonic_hierarchy": True,
        "enable_epigenetic_roles": True,
        "holon_bond_threshold": 1.0,
        "comm_enabled": False,
    }
    return dna_config(**{**base, **overrides})


def roles_of(engine: SimulationEngine) -> dict[int, EpigeneticRole]:
    return {aid: engine.agents[aid].epigenetic_role for aid in sorted(engine.agents)}


def count_assignments(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Espía `assign_epigenetic_roles` en el motor: registra el `node_id` de cada llamada."""
    calls: list[int] = []
    original = engine_module.assign_epigenetic_roles

    def spy(holon: CompositeAgent, *args: Any) -> dict[int, EpigeneticRole]:
        calls.append(holon.node_id)
        return original(holon, *args)

    monkeypatch.setattr(engine_module, "assign_epigenetic_roles", spy)
    return calls


R_NONE, R_EXPLORER, R_LIBRARIAN, R_NERVE = (
    EpigeneticRole.NONE,
    EpigeneticRole.EXPLORER,
    EpigeneticRole.LIBRARIAN,
    EpigeneticRole.NERVE,
)


def test_rol_sin_efecto_en_el_adn_fundador() -> None:
    config = roles_config()
    dna = founder_dna(config)
    phenotypes = {
        transcribe_phenotype(dna, EpigeneticContext(1, role, 0.6), config)
        for role in EpigeneticRole
    }
    assert len(phenotypes) == 1


def test_sistema_de_roles_solo_con_r25_efectiva() -> None:
    names = [s.name for s in SimulationEngine(roles_config()).systems]
    assert names.index("downward_causation") < names.index("epigenetic_roles")
    assert names.index("epigenetic_roles") < names.index("environment_dynamics")
    for flag in ("enable_compact_dna", "enable_epigenetic_roles", "enable_holonic_hierarchy"):
        config = (
            roles_config(**{flag: False})
            if flag != "enable_compact_dna"
            else quiet(
                enable_evolution=True, enable_holonic_hierarchy=True, enable_epigenetic_roles=True
            )
        )
        assert "epigenetic_roles" not in [s.name for s in SimulationEngine(config).systems]


def test_asignacion_por_el_motor_en_la_fase_5(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(roles_config(num_agents=4))
    engine.agents[1].memory.upsert(direct(pat(0), 1.0), 0)
    holon = make_holon(engine, [1, 2])
    act(monkeypatch, engine)
    engine.step()
    assert roles_of(engine) == {0: R_NONE, 1: R_LIBRARIAN, 2: R_EXPLORER, 3: R_NONE}
    assert engine._role_leaf_sets == {holon.node_id: frozenset({1, 2})}  # pyright: ignore[reportPrivateUsage]


def test_composicion_estable_no_reasigna(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(roles_config(num_agents=4))
    engine.agents[1].memory.upsert(direct(pat(0), 1.0), 0)
    holon = make_holon(engine, [1, 2])
    calls = count_assignments(monkeypatch)
    act(monkeypatch, engine)
    engine.step()
    assert calls == [holon.node_id]
    # La hoja 2 pasa a saber más que la 1: no importa mientras la composición no cambie.
    for i in range(1, 4):
        engine.agents[2].memory.upsert(direct(pat(i), 1.0), engine.next_tick)
    engine.run(10)
    assert calls == [holon.node_id]
    assert roles_of(engine)[1] is R_LIBRARIAN and roles_of(engine)[2] is R_EXPLORER


def test_composicion_nueva_reasigna(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(roles_config(num_agents=4))
    engine.agents[1].memory.upsert(direct(pat(0), 1.0), 0)
    first = make_holon(engine, [1, 2])
    calls = count_assignments(monkeypatch)
    act(monkeypatch, engine)
    engine.step()
    engine.agents[3].memory.upsert(direct(pat(5), 1.0), 1)
    engine.agents[3].memory.upsert(direct(pat(6), 1.0), 1)
    merged = make_holon(engine, [1, 3])  # como un BOND: raíz nueva con una hoja más
    engine.step()
    assert calls == [first.node_id, merged.node_id]
    assert engine._role_leaf_sets == {merged.node_id: frozenset({1, 2, 3})}  # pyright: ignore[reportPrivateUsage]
    assert roles_of(engine)[3] is R_LIBRARIAN


def test_poda_cambia_la_composicion_y_reasigna(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sin SPLIT: la energía negativa de la hoja 3 partiría el holón por hambre antes de la muerte.
    engine = SimulationEngine(roles_config(num_agents=4, enable_holon_splitting=False))
    engine.agents[3].memory.upsert(direct(pat(0), 1.0), 0)
    holon = make_holon(engine, [1, 2, 3])
    calls = count_assignments(monkeypatch)
    act(monkeypatch, engine)
    engine.step()
    assert roles_of(engine)[3] is R_LIBRARIAN
    engine.agents[3].apply_energy_delta(-100.0)  # muere en la Fase 5: el holón queda con 2
    engine.step()
    assert calls == [holon.node_id, holon.node_id]
    assert engine._role_leaf_sets == {holon.node_id: frozenset({1, 2})}  # pyright: ignore[reportPrivateUsage]
    assert {roles_of(engine)[1], roles_of(engine)[2]} == {R_LIBRARIAN, R_EXPLORER}


def test_split_devuelve_a_none_y_limpia_el_registro(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(roles_config(num_agents=4))
    engine.agents[1].memory.upsert(direct(pat(0), 1.0), 0)
    holon = make_holon(engine, [1, 2, 3])
    act(monkeypatch, engine)
    engine.step()
    assert set(roles_of(engine).values()) == {R_NONE, R_LIBRARIAN, R_EXPLORER, R_NERVE}
    holon.ticks_without_surplus = engine.config.holon_split_patience
    engine.step()
    assert holon.node_id not in engine.root_nodes
    assert set(roles_of(engine).values()) == {R_NONE}
    assert engine._role_leaf_sets == {}  # pyright: ignore[reportPrivateUsage]


def test_impronta_en_la_reproduccion_holonica(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(
        roles_config(num_agents=4, enable_holon_reproduction=True, reproduction_threshold=2.0)
    )
    engine.agents[1].memory.upsert(direct(pat(0), 1.0), 0)
    holon = make_holon(engine, [1, 2, 3])
    calls = count_assignments(monkeypatch)
    act(monkeypatch, engine)
    engine.step()
    parents = {aid: engine.agents[aid].epigenetic_role for aid in (1, 2, 3)}
    assert set(parents.values()) == {R_LIBRARIAN, R_EXPLORER, R_NERVE}
    for aid in (1, 2, 3):
        engine.agents[aid].apply_energy_delta(10.0)
    engine.step()
    replica = engine.root_nodes[engine.agent_to_root[4]]
    assert isinstance(replica, CompositeAgent) and replica is not holon
    for child in replica.leaf_agents:
        assert child.parent_id is not None
        assert child.epigenetic_role is parents[child.parent_id]
    leaf_sets = engine._role_leaf_sets  # pyright: ignore[reportPrivateUsage]
    assert leaf_sets[replica.node_id] == frozenset(c.agent_id for c in replica.leaf_agents)
    assert calls == [holon.node_id]  # la réplica no se recalculó
    act(monkeypatch, engine)  # los hijos también quedan quietos
    for child in replica.leaf_agents:
        child.memory.upsert(direct(pat(7), 1.0), engine.next_tick)
    engine.step()
    assert calls == [holon.node_id]
    assert all(c.epigenetic_role is parents[cast(int, c.parent_id)] for c in replica.leaf_agents)


def test_sin_r17_el_hijo_nace_solo_y_sin_rol(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(roles_config(num_agents=3, reproduction_threshold=2.0))
    engine.agents[1].memory.upsert(direct(pat(0), 1.0), 0)
    make_holon(engine, [1, 2])
    act(monkeypatch, engine)
    engine.step()
    assert engine.agents[1].epigenetic_role is R_LIBRARIAN
    engine.agents[1].apply_energy_delta(10.0)
    engine.step()
    child = engine.agents[3]
    assert child.parent_id == 1 and engine.root_nodes[3] is child
    assert child.epigenetic_role is R_NONE


def test_fase_0_lee_el_rol_asignado(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(roles_config(num_agents=3))
    engine.agents[1].memory.upsert(direct(pat(0), 1.0), 0)
    make_holon(engine, [1, 2])
    act(monkeypatch, engine)
    engine.step()
    seen: list[EpigeneticContext] = []
    original = engine.agents[1].express

    def spy(context: EpigeneticContext, tick: int) -> bool:
        seen.append(context)
        return original(context, tick)

    monkeypatch.setattr(engine.agents[1], "express", spy)
    engine.step()
    assert seen[0].role is R_LIBRARIAN and seen[0].holon_level == 1


# --- Fase II-B: compromiso simbiótico (R31, design D40 y D50.3; bloque 18) --------------------

COMMITTED = encode_codon(0x00, 0x0A, 0, 0, 127)  # 0.6 * 127 / 128 = 0.5953125 sobre base 0


def ratchet_config(**overrides: Any) -> SimulationConfig:
    """`dna_config` con holones y R31, sin BOND ni comunicación salvo que se pidan."""
    base: dict[str, Any] = {
        "enable_holonic_hierarchy": True,
        "enable_symbiotic_ratchet": True,
        "lock_coord_discount": 0.5,
        "holon_coord_cost": 0.01,
        "holon_bond_threshold": 1.0,
        "comm_enabled": False,
    }
    return dna_config(**{**base, **overrides})


def commit(engine: SimulationEngine, *aids: int) -> None:
    """Agrega al ADN de `aids` un codón que expresa compromiso simbiótico >= 0.5."""
    for aid in aids:
        agent = engine.agents[aid]
        assert agent.dna is not None
        agent.set_dna(CompactDNA((*agent.dna.chromosome, COMMITTED)))


def all_holons(engine: SimulationEngine) -> list[CompositeAgent]:
    return [c for nid in sorted(engine.root_nodes) for c in composite_nodes(engine.root_nodes[nid])]


def test_sello_antes_del_costo_y_de_split(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(ratchet_config(num_agents=3, symbiotic_commitment_base=0.5))
    holon = make_holon(engine, [1, 2])
    holon.ticks_without_surplus = engine.config.holon_split_patience  # se partiría este tick
    act(monkeypatch, engine)
    engine.step()
    assert engine.root_nodes[holon.node_id] is holon and holon.is_locked
    cost = engine.agents[0].energy - engine.agents[1].energy
    assert cost == pytest.approx(0.5 * 0.01 * 1, abs=1e-9)  # descuento desde el mismo tick


def test_sello_por_el_compromiso_expresado_del_adn(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(ratchet_config(num_agents=4))
    loose, tight = make_holon(engine, [0, 1]), make_holon(engine, [2, 3])
    commit(engine, 0, 2, 3)  # media de `loose`: 0.30; de `tight`: 0.595
    act(monkeypatch, engine)
    engine.step()
    assert engine.agents[2].phenotype.symbiotic_commitment == pytest.approx(0.5953125, abs=1e-9)
    assert not loose.is_locked and tight.is_locked


def test_sin_adn_no_hay_sello(monkeypatch: pytest.MonkeyPatch) -> None:
    config = quiet(
        num_agents=3,
        enable_evolution=True,
        enable_holonic_hierarchy=True,
        enable_symbiotic_ratchet=True,
        symbiotic_commitment_base=0.8,
        holon_bond_threshold=1.0,
        comm_enabled=False,
    )
    engine = SimulationEngine(config)
    holon = make_holon(engine, [1, 2])
    act(monkeypatch, engine)
    engine.step()
    assert not holon.is_locked
    holon.ticks_without_surplus = config.holon_split_patience
    engine.step()
    assert holon.node_id not in engine.root_nodes  # sin efectos: se parte como en la Fase II


def test_sello_permanente(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(ratchet_config(num_agents=3, symbiotic_commitment_base=0.0))
    holon = make_holon(engine, [1, 2])
    holon.is_locked = True  # sus hojas expresan compromiso 0.0
    act(monkeypatch, engine)
    engine.run(5)
    assert holon.is_locked and engine.root_nodes[holon.node_id] is holon


def test_holon_soldado_deficitario(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(ratchet_config(num_agents=4, holon_min_energy_per_leaf=10.0))
    holon = make_holon(engine, [1, 2, 3])
    holon.is_locked = True
    holon.ticks_without_surplus = engine.config.holon_split_patience
    act(monkeypatch, engine)
    engine.step()
    assert engine.root_nodes[holon.node_id] is holon
    total = sum(engine.agents[0].energy - engine.agents[a].energy for a in (1, 2, 3))
    assert total == pytest.approx(0.5 * 0.01 * 3 * 1, abs=1e-9)


def test_descuento_solo_en_la_raiz_soldada(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(ratchet_config(num_agents=5))
    inner = make_holon(engine, [0, 1])
    inner.is_locked = True
    make_holon(engine, [2, 3])
    root = make_holon(engine, [0, 2])
    assert root.holon_level == 2 and len(root.leaf_agents) == 4
    act(monkeypatch, engine)
    engine.step()
    assert not root.is_locked
    for aid in (0, 1, 2, 3):
        cost = engine.agents[4].energy - engine.agents[aid].energy
        assert cost == pytest.approx(0.01 * 2, abs=1e-9)  # total: 0.01 * 4 * 2, sin descuento
    root.is_locked = True
    before = {aid: engine.agents[aid].energy for aid in range(5)}
    engine.step()
    for aid in (0, 1, 2, 3):
        cost = (before[aid] - engine.agents[aid].energy) - (before[4] - engine.agents[4].energy)
        assert cost == pytest.approx(0.5 * 0.01 * 2, abs=1e-9)


def test_poda_de_un_holon_soldado_en_el_motor(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(ratchet_config(num_agents=4))
    holon = make_holon(engine, [1, 2, 3])
    holon.is_locked = True
    act(monkeypatch, engine)
    engine.agents[3].apply_energy_delta(-100.0)
    engine.step()
    assert engine.root_nodes[holon.node_id] is holon and holon.is_locked
    assert [leaf.agent_id for leaf in holon.leaf_agents] == [1, 2]
    engine.agents[2].apply_energy_delta(-100.0)
    engine.step()
    assert holon.node_id not in engine.root_nodes
    assert engine.root_nodes[1] is engine.agents[1]


def test_sello_conservado_tras_fusion_y_split(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(ratchet_config(num_agents=4))
    inner = make_holon(engine, [0, 1])
    inner.is_locked = True
    outer = make_holon(engine, [0, 2])
    outer.ticks_without_surplus = engine.config.holon_split_patience
    act(monkeypatch, engine)
    engine.step()
    assert outer.node_id not in engine.root_nodes and not outer.is_locked
    assert engine.root_nodes[inner.node_id] is inner and inner.is_locked


def test_fundadores_sin_compromiso_no_se_sueldan(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(
        ratchet_config(num_agents=3, enable_holon_reproduction=True, reproduction_threshold=2.0)
    )
    holon = make_holon(engine, [0, 1])
    holon.cooperative_completions = 5
    for aid in (0, 1):
        engine.agents[aid].apply_energy_delta(10.0)
    act(monkeypatch, engine)
    engine.step()
    replica = engine.root_nodes[engine.agent_to_root[3]]
    assert isinstance(replica, CompositeAgent) and replica is not holon
    engine.step()
    assert not holon.is_locked and not replica.is_locked


def _phase_ii_b_holonic(**overrides: Any) -> SimulationConfig:
    """`003a` con ADN, R25 y R31 (bloque 18)."""
    return replace(
        PHASE2_PROTOCOL_CONFIGS["003a"],
        enable_compact_dna=True,
        enable_epigenetic_roles=True,
        enable_symbiotic_ratchet=True,
        **overrides,
    )


def test_adn_fundador_sin_compromiso_ningun_holon_se_suelda() -> None:
    engine = SimulationEngine(_phase_ii_b_holonic(seed=5))
    assert engine.config.symbiotic_commitment_base == 0.0
    holons_seen = 0
    for _ in range(80):
        engine.step()
        holons = all_holons(engine)
        holons_seen += len(holons)
        assert not any(h.is_locked for h in holons)
    assert holons_seen > 0  # hubo holones que podrían haberse soldado


def test_r25_y_r31_independientes_del_hash() -> None:
    script = textwrap.dedent(
        """
        from dataclasses import replace
        from ide.agent.dna import encode_codon
        from ide.agent.holon import composite_nodes
        from ide.domain.types import CompactDNA
        from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
        from ide.simulation.engine import SimulationEngine

        config = replace(
            PHASE2_PROTOCOL_CONFIGS["003a"], seed=7, enable_compact_dna=True,
            enable_epigenetic_roles=True, enable_symbiotic_ratchet=True,
        )
        engine = SimulationEngine(config)
        codon = encode_codon(0x00, 0x0A, 0, 0, 127)
        for aid in sorted(engine.agents):
            dna = engine.agents[aid].dna
            engine.agents[aid].set_dna(CompactDNA((*dna.chromosome, codon)))
        engine.run(60)
        holons = [
            c for nid in sorted(engine.root_nodes) for c in composite_nodes(engine.root_nodes[nid])
        ]
        print(sum(h.is_locked for h in holons))
        print(sum(engine.agents[a].epigenetic_role.value != "NONE" for a in engine.agents))
        print(engine.history)
        print(engine.evolutionary_history)
        print(sorted(engine.root_nodes), sorted(engine._role_leaf_sets.items()))
        print([(h.node_id, h.is_locked) for h in holons])
        print([(a, engine.agents[a].epigenetic_role, engine.agents[a].energy)
               for a in sorted(engine.agents)])
        print([engine.agents[a].dna for a in sorted(engine.agents)])
        print(engine.rng.bit_generator.state, engine.evo_rng.bit_generator.state)
        """
    )
    outputs: list[str] = []
    for hash_seed in ("0", "123"):
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
    locked, with_role = (int(x) for x in outputs[0].splitlines()[:2])
    assert locked > 0 and with_role > 0  # se sueldan holones y se asignan roles de verdad
