"""Tests del motor por sistemas y observadores (bloque 6, design D44, D53.1 y D54).

Cubren `EngineSystem`, `TickObserver`, `TickFrame` y `build_systems` (orden de las fases y
ausencia de los sistemas de los mecanismos apagados), la telemetría producida por observadores
con M2 juzgado en `on_decisions`, la auditoría AST de los accesos a `agent.memory` (D44.3) y la
aceptación del refactor (D44.4): historiales de `002a` y `003a` con ADN idénticos a los del motor
previo al refactor. Los hashes dorados de la Fase I (`tests/test_performance_equivalence.py`) y
las huellas de la Fase II sin ADN (`tests/test_simulation_engine.py`) completan la aceptación.
"""

import ast
import hashlib
from dataclasses import astuple, fields, is_dataclass, replace
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from ide.config import SimulationConfig
from ide.domain.types import ActionResult, ActionType, AgentAction
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS, ablate
from ide.simulation.engine import (
    EvolutionaryMetricsObserver,
    SimulationEngine,
    TickMetricsObserver,
)
from ide.simulation.pipeline import (
    DECISION_SYSTEM,
    DecisionSystem,
    EngineSystem,
    TickFrame,
    TickObserver,
    build_systems,
    validate_systems,
)

SRC = Path(__file__).resolve().parents[1] / "src" / "ide"
IDLE = AgentAction(ActionType.IDLE)

# Sistemas de cada mecanismo de las Fases I, II y II-B (etapa A) que existen en el bloque 6, con la
# condición que los activa. Un mecanismo apagado no aparece en `build_systems` (D44.1).
MECHANISM_SYSTEMS: dict[str, tuple[str, ...]] = {
    "enable_compact_dna": ("expression",),
    "enable_holonic_hierarchy": (
        "local_reach",
        "holon_coordination",
        "downward_causation",
    ),
    "enable_stigmergy": ("stigmergy_assimilation",),
    "comm_enabled": ("social_exchange",),
    "enable_evolution": ("metabolism", "death", "reproduction"),
}

# Orden de D53.1 reducido a la Fase II más la Fase 0 de la etapa A.
PHASE2_ORDER = (
    "expression",  # Fase 0
    "schedule",  # Fase 1: permutación del tick
    "local_reach",
    "holon_view_memory",
    "perception",
    "emission",
    "stigmergy_assimilation",
    "social_exchange",  # Fase 2
    "holon_view_own",
    DECISION_SYSTEM,  # Fase 3 (y contexto de los compuestos)
    "execution",  # Fase 4
    "memory_decay",  # Fase 5 (i)
    "holon_coordination",  # (ii)
    "metabolism",  # (iii)
    "death",  # (iv)
    "reproduction",  # (v)
    "downward_causation",  # (vii)
    "environment_dynamics",  # (viii)
)


def full_phase2_config() -> SimulationConfig:
    """Todas las banderas de las Fases II y II-B (etapa A) que tienen sistema propio."""
    return replace(
        PHASE2_PROTOCOL_CONFIGS["003a"],
        enable_stigmergy=True,
        enable_compact_dna=True,
        enable_holon_view=True,
    )


def names(config: SimulationConfig) -> list[str]:
    return [system.name for system in build_systems(config)]


def grid_of(engine: SimulationEngine) -> ToroidalGrid2D:
    return cast(ToroidalGrid2D, engine.env)


def walk_to(grid: ToroidalGrid2D, agent_id: int, target: tuple[int, int]) -> None:
    """Lleva al agente a `target` con `MOVE`, que no consume el generador."""
    width, height = grid.config.grid_width, grid.config.grid_height
    while grid.get_agent_position(agent_id) != target:
        x, y = grid.get_agent_position(agent_id)
        dx = ((target[0] - x + width // 2) % width) - width // 2
        dy = ((target[1] - y + height // 2) % height) - height // 2
        grid.execute_action(
            agent_id, AgentAction(ActionType.MOVE, (int(np.sign(dx)), int(np.sign(dy)))), 0
        )


def fix_actions(
    monkeypatch: pytest.MonkeyPatch,
    engine: SimulationEngine,
    actions: dict[int, AgentAction] | None = None,
) -> None:
    """Fija la acción de cada agente: la de `actions` o `IDLE`."""
    actions = actions or {}
    for aid, agent in engine.agents.items():
        action = actions.get(aid, IDLE)
        monkeypatch.setattr(agent, "decide_action", lambda *_args, a=action: a)


# --- (a) EngineSystem, TickObserver, TickFrame y build_systems ---------------------------------


def test_tick_frame_tiene_los_campos_de_d44_y_es_mutable() -> None:
    assert is_dataclass(TickFrame)
    assert [f.name for f in fields(TickFrame)] == [
        "tick",
        "order",
        "reach",
        "observations",
        "social",
        "emitted",
        "responses",
        "actions",
        "composite_intents",
        "composite_contexts",
        "moved",
        "attacks",
        "surplus",
        "births",
        "deaths",
        "messages_sent",
        "events",
        # Estado del tick que leen los observadores (precisión 73).
        "composite_reachable",
        "decision_opportunities",
        "correct_decisions",
        "world_patterns",
        "tick_metrics",
    ]
    frame = TickFrame(7)
    assert frame.tick == 7
    assert frame.order == [] and frame.actions == {} and frame.moved == set()
    assert frame.births == frame.deaths == frame.messages_sent == 0
    assert frame.decision_opportunities == frame.correct_decisions == 0
    assert frame.composite_reachable == {} and frame.world_patterns == {}
    assert frame.tick_metrics is None
    assert sum(frame.events.values()) == 0
    frame.births += 1  # estado mutable de un tick, no una entidad de dominio
    assert frame.births == 1
    # Cada marco tiene sus propios contenedores.
    frame.order.append(3)
    assert TickFrame(8).order == []


def test_build_systems_devuelve_sistemas_con_nombre_unico() -> None:
    for config in (SimulationConfig(), full_phase2_config()):
        systems = build_systems(config)
        assert isinstance(systems, tuple)
        assert all(isinstance(s, EngineSystem) for s in systems)
        assert all(isinstance(s.name, str) and callable(s.run) for s in systems)
        assert len({s.name for s in systems}) == len(systems)
        assert names(config).count(DECISION_SYSTEM) == 1


def test_build_systems_sigue_el_orden_de_d53() -> None:
    order = names(full_phase2_config())
    known = [name for name in order if name in PHASE2_ORDER]
    assert known == list(PHASE2_ORDER)


def test_orden_de_la_fase_i_con_las_banderas_por_defecto() -> None:
    order = names(SimulationConfig())
    assert order == [
        "schedule",
        "perception",
        "emission",
        "social_exchange",
        DECISION_SYSTEM,
        "execution",
        "memory_decay",
        "environment_dynamics",
    ]


@pytest.mark.parametrize("flag", sorted(MECHANISM_SYSTEMS))
def test_mecanismo_apagado_fuera_de_la_lista(flag: str) -> None:
    full = full_phase2_config()
    overrides = {flag: False}
    if flag == "enable_evolution":
        overrides["enable_compact_dna"] = False  # el ADN exige evolución (D34)
    off = replace(full, **overrides)
    on_names, off_names = names(full), names(off)
    for system in MECHANISM_SYSTEMS[flag]:
        assert system in on_names
        assert system not in off_names
    # Los sistemas comunes conservan su orden relativo.
    assert [n for n in on_names if n in off_names] == off_names


def test_vista_del_holon_solo_con_la_jerarquia_y_su_bandera() -> None:
    full = full_phase2_config()
    for config in (
        replace(full, enable_holon_view=False),
        replace(full, enable_holonic_hierarchy=False),
    ):
        assert "holon_view_memory" not in names(config)
        assert "holon_view_own" not in names(config)
    assert {"holon_view_memory", "holon_view_own"} <= set(names(full))


def test_adn_agrega_la_fase_0_al_principio() -> None:
    base = PHASE2_PROTOCOL_CONFIGS["002a"]
    with_dna = names(replace(base, enable_compact_dna=True))
    assert with_dna[0] == "expression"
    assert with_dna[1:] == names(base)


def test_step_ejecuta_los_sistemas_de_build_systems_en_orden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = full_phase2_config()
    engine = SimulationEngine(config)
    assert [s.name for s in engine.systems] == names(config)
    calls: list[str] = []
    for system in engine.systems:
        original = system.run

        def wrapper(eng: Any, frame: Any, _orig: Any = original, _name: str = system.name) -> None:
            calls.append(_name)
            _orig(eng, frame)

        monkeypatch.setattr(system, "run", wrapper)
    engine.run(2)
    assert calls == names(config) * 2
    assert engine.next_tick == 2


def test_step_devuelve_la_metrica_registrada() -> None:
    engine = SimulationEngine(SimulationConfig(num_agents=10, resources_per_pattern=3))
    metrics = engine.step()
    assert metrics is engine.history[-1]
    assert metrics.tick == 0
    assert engine.next_tick == 1


# --- (b) Observadores y momento de M2 ----------------------------------------------------------


class RecordingObserver:
    """Observador de prueba: registra el momento de cada llamada."""

    def __init__(self, log: list[str]) -> None:
        self.log = log
        self.decisions: list[tuple[int, dict[int, AgentAction], dict[int, tuple[int, int]]]] = []
        self.ends: list[int] = []

    def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.log.append("on_decisions")
        grid = grid_of(engine)
        positions = {aid: grid.get_agent_position(aid) for aid in sorted(engine.agents)}
        self.decisions.append((frame.tick, dict(frame.actions), positions))

    def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.log.append("on_tick_end")
        self.ends.append(frame.tick)


def test_observadores_por_defecto() -> None:
    engine = SimulationEngine(SimulationConfig(num_agents=10, resources_per_pattern=3))
    assert isinstance(engine.metrics_observer, TickMetricsObserver)
    assert [type(o) for o in engine.observers] == [EvolutionaryMetricsObserver]
    assert all(isinstance(o, TickObserver) for o in (engine.metrics_observer, *engine.observers))


def test_step_devuelve_la_metrica_del_tick_sin_depender_de_la_lista_publica() -> None:
    engine = SimulationEngine(SimulationConfig(num_agents=10, resources_per_pattern=3))
    engine.observers.clear()
    first = engine.step()
    engine.history.clear()  # `step()` no lee el historial
    second = engine.step()
    assert (first.tick, second.tick) == (0, 1)
    assert engine.history == [second]
    assert engine.evolutionary_history == []


def test_solo_el_sistema_de_decision_tiene_la_marca() -> None:
    for config in (SimulationConfig(), full_phase2_config()):
        marked = [s for s in build_systems(config) if s.notifies_decisions]
        assert len(marked) == 1 and isinstance(marked[0], DecisionSystem)


@pytest.mark.parametrize("marks", [0, 2])
def test_validate_systems_exige_exactamente_una_marca(marks: int) -> None:
    systems = list(build_systems(SimulationConfig()))
    for system in systems:
        system.notifies_decisions = False
    for system in systems[:marks]:
        system.notifies_decisions = True
    with pytest.raises(ValueError, match="notifies_decisions"):
        validate_systems(tuple(systems))


def test_on_decisions_sigue_a_la_marca_y_no_al_nombre_ni_a_la_clase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = SimulationEngine(SimulationConfig(num_agents=10, resources_per_pattern=3))
    log: list[str] = []
    engine.observers.append(RecordingObserver(log))
    systems = list(engine.systems)
    index = next(i for i, s in enumerate(systems) if isinstance(s, DecisionSystem))
    decision, execution = systems[index], systems[index + 1]
    # La marca pasa a la ejecución, que además toma el nombre del sistema de decisión; la
    # decisión cambia de nombre. `on_decisions` debe seguir a la marca: después de ejecutar.
    monkeypatch.setattr(decision, "notifies_decisions", False)
    monkeypatch.setattr(decision, "name", "otro_nombre")
    monkeypatch.setattr(execution, "notifies_decisions", True)
    monkeypatch.setattr(execution, "name", DECISION_SYSTEM)
    original_execute = engine.env.execute_action

    def execute(agent_id: int, action: AgentAction, tick: int) -> ActionResult:
        log.append("execute")
        return original_execute(agent_id, action, tick)

    monkeypatch.setattr(engine.env, "execute_action", execute)
    engine.step()
    assert log[-2:] == ["on_decisions", "on_tick_end"]
    assert log.count("on_decisions") == 1 and log.index("execute") < log.index("on_decisions")


def test_tick_sin_metricas_no_desalinea_los_historiales(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(SimulationConfig(num_agents=10, resources_per_pattern=3))
    log: list[str] = []
    engine.observers.append(RecordingObserver(log))
    monkeypatch.setattr(engine.metrics_observer, "on_tick_end", lambda *_args: None)
    with pytest.raises(RuntimeError, match="TickMetrics"):
        engine.step()
    assert engine.next_tick == 0
    assert engine.history == [] and engine.evolutionary_history == []
    assert "on_tick_end" not in log


def test_momento_de_los_observadores(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(SimulationConfig(num_agents=10, resources_per_pattern=3))
    grid = grid_of(engine)
    log: list[str] = []
    observer = RecordingObserver(log)
    engine.observers.append(observer)
    before = {aid: grid.get_agent_position(aid) for aid in sorted(engine.agents)}
    # Todos se mueven: si on_decisions llegara tarde, vería posiciones nuevas.
    fix_actions(monkeypatch, engine, {aid: AgentAction(ActionType.MOVE, (1, 0)) for aid in before})
    original_execute = grid.execute_action
    original_dynamics = grid.step_dynamics

    def execute(agent_id: int, action: AgentAction, tick: int) -> ActionResult:
        log.append("execute")
        return original_execute(agent_id, action, tick)

    def dynamics(tick: int) -> None:
        log.append("step_dynamics")
        original_dynamics(tick)

    monkeypatch.setattr(grid, "execute_action", execute)
    monkeypatch.setattr(grid, "step_dynamics", dynamics)
    engine.step()
    assert log.count("on_decisions") == 1 and log.count("on_tick_end") == 1
    assert log.index("on_decisions") < log.index("execute")
    assert log[-2:] == ["step_dynamics", "on_tick_end"]
    tick, actions, positions = observer.decisions[0]
    assert tick == 0
    assert sorted(actions) == sorted(before)  # `frame.actions` completo
    assert positions == before  # ningún agente se movió todavía
    assert observer.ends == [0]


def test_m2_se_juzga_en_on_decisions_antes_de_ejecutar(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(SimulationConfig(num_agents=10, resources_per_pattern=3))
    grid = grid_of(engine)
    observer = engine.metrics_observer
    state = {"inside": False, "executed": False}
    original_judge = observer.on_decisions
    original_truth = grid.get_reachable_true_values
    original_execute = grid.execute_action

    def judge(eng: SimulationEngine, frame: TickFrame) -> None:
        state["inside"] = True
        original_judge(eng, frame)
        state["inside"] = False

    def truth(agent_id: int) -> dict[int, float]:
        assert state["inside"], "el oráculo de M2 sólo se consulta en on_decisions"
        assert not state["executed"], "M2 se juzga antes de ejecutar las acciones"
        return original_truth(agent_id)

    def execute(agent_id: int, action: AgentAction, tick: int) -> ActionResult:
        state["executed"] = True
        return original_execute(agent_id, action, tick)

    monkeypatch.setattr(observer, "on_decisions", judge)
    monkeypatch.setattr(grid, "get_reachable_true_values", truth)
    monkeypatch.setattr(grid, "execute_action", execute)
    engine.step()
    assert state["executed"]


def test_m2_sobre_la_verdad_previa_a_la_ejecucion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dos agentes deciden consumir el mismo recurso benéfico: M2 juzga a los dos."""
    config = SimulationConfig(
        grid_width=10, grid_height=10, num_agents=10, resources_per_pattern=1, comm_enabled=False
    )
    engine = SimulationEngine(config)
    grid = grid_of(engine)
    cell, resource = next(
        (cell, r)
        for cell in sorted(grid.cell_resources)
        for r in sorted(grid.cell_resources[cell].values(), key=lambda r: r.resource_id)
        if r.true_value > 0
    )
    walk_to(grid, 3, cell)
    walk_to(grid, 8, cell)
    eat = AgentAction(ActionType.INTERACT, resource.resource_id)
    fix_actions(monkeypatch, engine, {3: eat, 8: eat})
    # Sólo 3 y 8 tienen recursos alcanzables que cuenten como oportunidad.
    original_truth = grid.get_reachable_true_values
    monkeypatch.setattr(
        grid,
        "get_reachable_true_values",
        lambda aid: original_truth(aid) if aid in (3, 8) else {},
    )
    results: dict[int, ActionResult] = {}
    original_execute = grid.execute_action

    def execute(agent_id: int, action: AgentAction, tick: int) -> ActionResult:
        results[agent_id] = original_execute(agent_id, action, tick)
        return results[agent_id]

    monkeypatch.setattr(grid, "execute_action", execute)
    frames: list[TickFrame] = []

    class FrameSpy:
        def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
            frames.append(frame)

        def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
            """No hace nada al final del tick."""

    engine.observers.append(FrameSpy())
    metrics = engine.step()
    assert metrics.decision_opportunities == 2
    assert metrics.correct_decisions == 2
    # M2 queda en el marco del tick, escrito antes de los demás observadores.
    assert (frames[0].decision_opportunities, frames[0].correct_decisions) == (2, 2)
    # Uno de los dos lo consume; el otro llega tarde a un recurso agotado.
    outcomes = sorted(results[aid].experienced_value is None for aid in (3, 8))
    assert outcomes == [False, True]
    assert ActionResult(ActionType.INTERACT, None, None) in (results[3], results[8])


def test_telemetria_en_on_tick_end_con_historiales_por_observador() -> None:
    config = replace(PHASE2_PROTOCOL_CONFIGS["003a"], enable_stigmergy=True)
    engine = SimulationEngine(config)
    engine.run(3)
    assert [m.tick for m in engine.history] == [0, 1, 2]
    assert [m.tick for m in engine.evolutionary_history] == [0, 1, 2]


# --- (c) Auditoría AST de los accesos a `agent.memory` (D44.3) ---------------------------------

# Funciones del motor que acceden a `.memory`. Son los puntos que ya lo hacían antes del refactor:
# R18 (causalidad descendente), R19 (depósito estigmérgico tras el aprendizaje directo), el
# superávit de conocimiento del holón, la herencia cultural al nacer (R14) y la perturbación del
# rumor. La lista no puede crecer sin cambiar este test.
MEMORY_ACCESS = {
    "engine.py:SimulationEngine._apply_downward_causation",
    "engine.py:SimulationEngine._has_knowledge_surplus",
    "engine.py:SimulationEngine._give_birth",
    "engine.py:SimulationEngine.inject_false_belief",
    "pipeline.py:ExecutionSystem.run",
}


def _functions_using_memory(path: Path) -> set[str]:
    found: set[str] = set()

    def visit(node: ast.AST, scope: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, [*scope, child.name])
                continue
            if isinstance(child, ast.Attribute) and child.attr == "memory":
                found.add(f"{path.name}:{'.'.join(scope)}")
            visit(child, scope)

    visit(ast.parse(path.read_text(encoding="utf-8")), [])
    return found


def test_accesos_del_motor_a_la_memoria_del_agente() -> None:
    paths = [SRC / "simulation" / "pipeline.py", SRC / "simulation" / "engine.py"]
    assert all(path.exists() for path in paths)
    found = set[str]().union(*(_functions_using_memory(path) for path in paths))
    assert found == MEMORY_ACCESS


# --- (d) Aceptación de D44.4: historiales con ADN idénticos al motor previo -------------------


def _rounded(value: Any) -> Any:
    """Redondea a 9 decimales los floats de una tupla de métricas, recursivamente."""
    if isinstance(value, float):
        return round(value, 9) + 0.0  # `+ 0.0` normaliza `-0.0`
    if isinstance(value, tuple):
        return tuple(_rounded(v) for v in cast(tuple[Any, ...], value))
    return value


def dna_digest(config: SimulationConfig, ticks: int = 100) -> str:
    """Historiales, posiciones, memorias, genomas, ADN, fenotipos, bosque y generadores.

    Igual que la huella de la Fase II (`tests/test_simulation_engine.py`), redondea los floats de
    `evolutionary_history` a 9 decimales por la suma compensada de Python 3.12 en adelante.
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
        [engine.agents[a].dna for a in ids],
        [engine.agents[a].phenotype for a in ids],
        [
            (nid, node.holon_level, tuple(leaf.agent_id for leaf in node.leaf_agents))
            for nid, node in sorted(engine.root_nodes.items())
        ],
        {p: sorted(found) for p, found in sorted(engine.direct_discoverers.items())},
        [
            g.bit_generator.state
            for g in (engine.rng, engine.null_rng, engine.evo_rng, engine.donor_rng)
        ],
        engine.next_agent_id,
        engine.next_holon_id,
    )
    return hashlib.sha256(repr(state).encode()).hexdigest()


_P = PHASE2_PROTOCOL_CONFIGS
DNA_CASES: dict[str, SimulationConfig] = {
    "002a-dna": replace(_P["002a"], enable_compact_dna=True),
    "002a-dna-R12": replace(ablate(_P["002a"], ["R12"]), enable_compact_dna=True),
    "002b-dna-null": replace(_P["002b"], comm_content_null=True, enable_compact_dna=True),
    "003a-dna": replace(_P["003a"], enable_compact_dna=True),
    "003a-dna-aislado": replace(_P["003a"], enable_compact_dna=True, comm_enabled=False),
    "003a-dna-stigmergy": replace(
        _P["003a"], enable_compact_dna=True, enable_stigmergy=True, dna_point_mutation_rate=0.2
    ),
}

# Huellas SHA-256 de `dna_digest` tras 100 ticks, calculadas con el motor previo al refactor por
# sistemas (commit 93e66f1, bloque 5), con PYTHONHASHSEED 0 y 123, nunca con el motor nuevo.
# Exigen igualdad de bits en la plataforma de referencia (Linux x86-64, numpy 2.x).
DNA_GOLDEN = {
    "002a-dna": "6d3c7529cbb3e37066b45e49fd4e117403703cb051e2133cdfcc45aba26214d7",
    "002a-dna-R12": "3aaab7c352483a6f5535f262d337b186e2f4581d74ff0c2d1bd3a52d32a40b2f",
    "002b-dna-null": "8f50fdaf7d82eb80c139bd31fe0752f5582dc55e94bd42774c0c44b4cfcf00f3",
    "003a-dna": "a6107a946b2af5a0e7b650554e0b611edb6670d1c6532789decbeaa7b8715029",
    "003a-dna-aislado": "a5cebac2e68408bb05a4b06485aaade20b7c6759d72dfad872b05f3e0463dd2a",
    "003a-dna-stigmergy": "5e13e85f466649046cb5d5bbd9130e31ed1355982bb3e76258246f48adb92b56",
}


@pytest.mark.parametrize("name", sorted(DNA_CASES))
def test_historiales_con_adn_identicos_al_motor_previo(name: str) -> None:
    assert dna_digest(DNA_CASES[name]) == DNA_GOLDEN[name]
