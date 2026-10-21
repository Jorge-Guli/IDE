"""Motor por sistemas (design D44): marco del tick, sistemas ordenados y observadores.

`SimulationEngine.step()` crea un `TickFrame`, ejecuta en orden los sistemas de
`build_systems(config)`, avisa a los observadores (`TickObserver`) después del sistema de
decisión (`DecisionSystem`) y al final del tick, e incrementa `next_tick`. Cada sistema es una
fase (o parte de una fase) del orden de D53.1 con la precisión 70; un mecanismo que vive en su
propio sistema no aparece en la lista con su bandera apagada, así que con las banderas por
defecto la lista se reduce a la de la Fase I.

Este módulo es la descomposición interna del motor: sus sistemas leen y escriben el estado de
`SimulationEngine` y usan sus métodos auxiliares, que siguen en `engine.py` (los comparten las
perturbaciones y la Fase 5). Por eso desactiva `reportPrivateUsage` de Pyright. El oráculo de M2
(`get_reachable_true_values`) no se usa aquí: lo consulta sólo `TickMetricsObserver`, en
`engine.py` (precisión 72). Ningún sistema calcula métricas: el estado del tick que leen los
observadores (los compuestos alcanzables, M2 y las métricas) vive en el `TickFrame`.
"""

# pyright: reportPrivateUsage=false

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

import numpy as np

from ide.agent.holon import CompositeAgent
from ide.config import SimulationConfig
from ide.domain.ports import EcologicalEnvironmentPort
from ide.domain.types import (
    CARCASS_PATTERN,
    ActionType,
    AgentAction,
    Message,
    Observation,
    Pattern,
    SocialPerception,
)
from ide.experiments.metrics import TickMetrics

if TYPE_CHECKING:
    from ide.simulation.engine import SimulationEngine

# Contexto de una resolución compuesta, fijado al empezar la Fase 4 (D27):
# (éxito, hojas que reciben la ganancia, holón raíz o None).
CompositeContext = tuple[bool, list[int], CompositeAgent | None]

# Nombre del sistema de decisión. `step()` no reconoce ese sistema por el nombre sino por la marca
# `notifies_decisions`: los nombres los fija la implementación y no son contrato (precisión 20).
DECISION_SYSTEM = "decision"


@dataclass
class TickFrame:
    """Estado mutable de un tick (D44.1); no es una entidad de dominio.

    Los conjuntos (`moved`, `surplus`) se recorren siempre con `sorted(...)` (precisión 39).
    `social` guarda la `SocialPerception` de cada agente (D47.3); sólo la llena
    `SocialPerceptionSystem`, con la política genética efectivamente activa, y sin ella queda
    vacío, de modo que la decisión recibe `None`.
    `attacks` y `events` los llenan los sistemas de las interacciones y de la ecología (D49, D53);
    sin esas reglas quedan vacíos.

    Después de los campos de D44.1 van los del estado del tick que leen los observadores
    (precisión 73): `composite_reachable` (por agente con algún compuesto alcanzable, sus
    `resource_id` y patrones, D25.3), lo escribe `DecisionSystem`; `decision_opportunities` y
    `correct_decisions` (M2), `TickMetricsObserver` en `on_decisions`; `world_patterns`, `step()`
    una sola vez, al terminar los sistemas; y `tick_metrics`, `TickMetricsObserver` en
    `on_tick_end`.
    """

    tick: int
    order: list[int] = field(default_factory=list[int])
    reach: dict[int, list[int]] = field(default_factory=dict[int, list[int]])
    observations: dict[int, Observation] = field(default_factory=dict[int, Observation])
    social: dict[int, SocialPerception] = field(default_factory=dict[int, SocialPerception])
    emitted: list[Message] = field(default_factory=list[Message])
    responses: list[Message] = field(default_factory=list[Message])
    actions: dict[int, AgentAction] = field(default_factory=dict[int, AgentAction])
    composite_intents: dict[int, Pattern] = field(default_factory=dict[int, Pattern])
    composite_contexts: dict[int, CompositeContext] = field(
        default_factory=dict[int, CompositeContext]
    )
    moved: set[int] = field(default_factory=set[int])
    attacks: dict[int, int] = field(default_factory=dict[int, int])
    surplus: set[int] = field(default_factory=set[int])
    births: int = 0
    deaths: int = 0
    messages_sent: int = 0
    events: Counter[str] = field(default_factory=Counter[str])
    composite_reachable: dict[int, dict[int, Pattern]] = field(
        default_factory=dict[int, dict[int, Pattern]]
    )
    decision_opportunities: int = 0
    correct_decisions: int = 0
    world_patterns: dict[Pattern, float] = field(default_factory=dict[Pattern, float])
    tick_metrics: TickMetrics | None = None


@runtime_checkable
class EngineSystem(Protocol):
    """Una fase del tick: lee y escribe el motor y el marco, sin calcular métricas."""

    name: str
    # `step()` invoca `on_decisions` inmediatamente después del único sistema que la tiene.
    notifies_decisions: bool

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None: ...


@runtime_checkable
class TickObserver(Protocol):
    """Telemetría fuera del bucle: observa el tick sin cambiar el estado del motor."""

    def on_decisions(self, engine: "SimulationEngine", frame: TickFrame) -> None: ...

    def on_tick_end(self, engine: "SimulationEngine", frame: TickFrame) -> None: ...


class BaseSystem:
    """Base de los sistemas del motor: sin marca de `on_decisions` salvo que la redefinan.

    La marca `notifies_decisions` señala el sistema tras el cual se notifica `on_decisions`. Hoy
    es el de decisión; el bloque de señales ($R_{41}$) puede partir la Fase 3 (decisión,
    emisión de señales, contexto de compuestos, `on_decisions` y estado interno) moviendo la
    marca al sistema que corresponda.
    """

    name: str
    notifies_decisions: bool = False


def carcasses_active(config: SimulationConfig) -> bool:
    """R35 efectivamente activa: con `enable_carcasses` y evolución (D48.3, D52.3, precisión 78).

    Es la única definición de la condición; el motor la guarda en `engine.carcasses_active`.
    """
    return config.enable_evolution and config.enable_carcasses


def genetic_policy_active(config: SimulationConfig) -> bool:
    """R32 efectivamente activa: con `enable_compact_dna` y `enable_genetic_policy` (prec. 31).

    Es la única definición de la condición; el motor la guarda en `engine.genetic_policy_active`.
    Sin ADN, `enable_genetic_policy` es inerte: no hay percepción social, la puerta de
    comunicación no actúa y la política es la escrita a mano.
    """
    return config.enable_compact_dna and config.enable_genetic_policy


def validate_systems(systems: tuple[EngineSystem, ...]) -> tuple[EngineSystem, ...]:
    """Devuelve `systems` si exactamente uno tiene la marca `notifies_decisions`.

    Raises:
        ValueError: si ningún sistema o más de uno tiene la marca.
    """
    marked = [system.name for system in systems if system.notifies_decisions]
    if len(marked) != 1:
        raise ValueError(
            f"exactamente un sistema debe marcar notifies_decisions; marcados: {marked}"
        )
    return systems


# --- Comienzo del tick ---------------------------------------------------------------------------


class WorldShiftSystem(BaseSystem):
    """Cambio del entorno (D62.1, precisión 56): antes de la Fase 0 de los ticks múltiplos.

    En cada tick `t > 0` con `t % world_shift_period == 0` invierte la fracción
    `world_shift_fraction` de las reglas del mundo con el generador principal. Es una
    manipulación experimental del entorno, no una regla del agente; sólo está en la lista con
    `world_shift_period > 0`.
    """

    name = "world_shift"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        config = engine.config
        if frame.tick > 0 and frame.tick % config.world_shift_period == 0:
            engine.env.invert_world_rules(config.world_shift_fraction, engine.rng)


# --- Fase 0 --------------------------------------------------------------------------------------


class ExpressionSystem(BaseSystem):
    """Fase 0 (R24, D34.4): expresión del fenotipo, antes de la permutación y del alcance."""

    name = "expression"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        engine._express_phenotypes(frame.tick)


# --- Fase 1 --------------------------------------------------------------------------------------


class ScheduleSystem(BaseSystem):
    """Permutación del tick: el sorteo que resuelve los conflictos físicos de la Fase 4."""

    name = "schedule"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        frame.order = cast(
            list[int],
            engine.rng.permutation(np.array(sorted(engine.agents), dtype=np.int64)).tolist(),  # pyright: ignore[reportUnknownMemberType]
        )


class LocalReachSystem(BaseSystem):
    """Alcance local de las hojas de cada holón (D24.1); nadie se mueve antes de la Fase 4."""

    name = "local_reach"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        frame.reach = engine._local_reach()


class HolonViewSystem(BaseSystem):
    """Vista del holón (R22, D25.2): desde la memoria (tiempo 1) o desde lo propio (tiempo 2)."""

    def __init__(self, name: str, from_memory: bool) -> None:
        self.name = name
        self.from_memory = from_memory

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        engine._sync_holon_view(frame.reach, from_memory=self.from_memory)


class PerceptionSystem(BaseSystem):
    """Percepción: la observación de cada agente, sobre la misma instantánea para todos.

    Ni la observación ni la emisión consumen generadores ni cambian el entorno, así que
    separarlas en dos recorridos con el mismo orden no altera nada; entre ellas van la
    germinación ($R_{28}$) y la percepción social (D53.1, precisión 70).
    """

    name = "perception"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        env, tick, observations = engine.env, frame.tick, frame.observations
        for aid in frame.order:
            observations[aid] = env.get_observation(aid, tick)


class SocialPerceptionSystem(BaseSystem):
    """Percepción social (R32, D47.3): una `SocialPerception` por agente en `frame.social`.

    Sólo está en la lista con la política genética efectivamente activa. Usa
    `get_visible_agents` y la instantánea de energías al empezar el sistema, antes de cualquier
    acción del tick (percepción sincrónica):
    - "activo" excluye a las endosporas;
    - `adjacent` son los activos a distancia <= 1, ascendentes, y `weakest_adjacent` el de menor
      `(energía, agent_id)`; `weaker_adjacent` dice si su energía es menor que la propia;
    - `flee_move` es el de la entrada del activo más cercano con energía estrictamente mayor que
      la propia, con desempate por `(distance, agent_id)`, el orden de `get_visible_agents`;
    - `crowded` vale si hay al menos `crowding_threshold` activos visibles;
    - `carcass_visible`, si algún recurso visible de la observación tiene `CARCASS_PATTERN`.
    No consume generadores ni cambia el entorno.
    """

    name = "social_perception"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        env = cast(EcologicalEnvironmentPort, engine.env)
        agents, social, observations = engine.agents, frame.social, frame.observations
        energy = {aid: agents[aid].energy for aid in sorted(agents)}
        crowding = engine.config.crowding_threshold
        for aid in frame.order:
            own = energy[aid]
            active = [v for v in env.get_visible_agents(aid) if not agents[v.agent_id].is_endospore]
            adjacent = tuple(sorted(v.agent_id for v in active if v.distance <= 1))
            weakest = min(adjacent, key=lambda other: (energy[other], other)) if adjacent else None
            flee = next((v.flee_move for v in active if energy[v.agent_id] > own), None)
            social[aid] = SocialPerception(
                adjacent=adjacent,
                weakest_adjacent=weakest,
                weaker_adjacent=weakest is not None and energy[weakest] < own,
                flee_move=flee,
                crowded=len(active) >= crowding,
                carcass_visible=any(
                    res.pattern == CARCASS_PATTERN for res in observations[aid].visible_resources
                ),
            )


class EmissionSystem(BaseSystem):
    """Emisión de mensajes sobre la observación de la Fase 1, con la puerta de D46.6.

    La puerta vive en `protocol.py` (`agent.communicates`): este sistema no la conoce.
    """

    name = "emission"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, tick = engine.agents, frame.tick
        observations, emitted = frame.observations, frame.emitted
        for aid in frame.order:
            emitted += agents[aid].perceive_and_emit_messages(observations[aid], tick)


class StigmergyAssimilationSystem(BaseSystem):
    """Rastros de la celda como testimonios del emisor sintético (R19, D27.3)."""

    name = "stigmergy_assimilation"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        engine._assimilate_stigmergy(frame.tick)


# --- Fase 2 --------------------------------------------------------------------------------------


class SocialExchangeSystem(BaseSystem):
    """Intercambio social en dos pasadas (Decisión 18)."""

    name = "social_exchange"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, tick, order = engine.agents, frame.tick, frame.order
        # Nadie se mueve entre las fases 1 y 2: los vecinos de la observación son los del ruteo,
        # sin volver a recorrer la vecindad (Decisión 18).
        neighbors = {aid: frame.observations[aid].neighbor_ids for aid in order}
        responses = frame.responses
        for aid, inbox in engine._route(frame.emitted, neighbors, order).items():
            responses += agents[aid].process_incoming_messages(inbox, tick)
        for aid, inbox in engine._route(responses, neighbors, order).items():
            if agents[aid].process_incoming_messages(inbox, tick):
                raise RuntimeError("la segunda pasada no debe generar respuestas")
        frame.messages_sent = len(frame.emitted) + len(responses)


# --- Fase 3 --------------------------------------------------------------------------------------


class DecisionSystem(BaseSystem):
    """Decisión sobre la observación de la Fase 1 y contexto de los compuestos (D27).

    Registra, una sola vez por tick, los recursos compuestos alcanzables de cada agente
    (`composite_reachable`, D25.3) y la intención compuesta de quien decide `INTERACT` sobre uno
    de ellos, y fija el contexto de su resolución con el estado al empezar la Fase 4, de modo que
    la permutación no la altera. M2 lo juzga `TickMetricsObserver` en `on_decisions`,
    inmediatamente después de este sistema, sobre esos mismos compuestos.
    """

    name = DECISION_SYSTEM
    notifies_decisions = True

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, tick, rng = engine.agents, frame.tick, engine.rng
        rules = engine._composite_rules
        actions, intents = frame.actions, frame.composite_intents
        reachable = frame.composite_reachable
        social = frame.social
        for aid in frame.order:
            observation = frame.observations[aid]
            agent, perception = agents[aid], social.get(aid)
            # Sin percepción social se conserva la llamada de la Fase I (`social` es `None`).
            if perception is None:
                action = agent.decide_action(observation, tick, rng)
            else:
                action = agent.decide_action(observation, tick, rng, perception)
            actions[aid] = action
            if not rules:
                continue
            composite = {
                res.resource_id: res.pattern
                for res in observation.visible_resources
                if res.is_reachable_now and res.pattern in rules
            }
            if composite:
                reachable[aid] = composite
                target = action.target
                if action.action_type is ActionType.INTERACT and target in composite:
                    intents[aid] = composite[cast(int, target)]
        frame.composite_contexts = {
            aid: engine._composite_context(aid, rules[pattern], frame.reach)
            for aid, pattern in intents.items()
        }


# --- Fase 4 --------------------------------------------------------------------------------------


class ExecutionSystem(BaseSystem):
    """Ejecución en el orden de la permutación, aprendizaje directo, energía y estigmergia."""

    name = "execution"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        config, env, agents, tick = engine.config, engine.env, engine.agents, frame.tick
        rules = engine._composite_rules
        actions, contexts = frame.actions, frame.composite_contexts
        moved, surplus = frame.moved, frame.surplus
        evolution = config.enable_evolution
        deposit = config.enable_stigmergy and config.stigmergy_deposit_rate > 0
        carcasses = engine.carcasses_active
        events = frame.events
        for aid in frame.order:
            result = env.execute_action(aid, actions[aid], tick)
            if result.action_type is ActionType.MOVE:
                moved.add(aid)
            pattern, value = result.interacted_pattern, result.experienced_value
            if value is None or pattern is None:
                continue
            if pattern in rules:
                rule = rules[pattern]
                engine._resolve_composite(aid, pattern, rule, contexts[aid], tick, surplus)
                continue
            if carcasses and pattern == CARCASS_PATTERN:
                events["carcasses_eaten"] += 1  # R35: sigue el camino de un recurso elemental
            agent = agents[aid]
            agent.learn_from_experience(pattern, value, tick)
            engine.direct_discoverers[pattern].add(aid)
            if evolution:
                agent.apply_energy_delta(config.energy_gain_scale * value)
            if deposit:
                learned = agent.memory.get(pattern)
                if learned is not None:  # siempre presente: la experiencia se fuerza en memoria
                    engine._evo.deposit_stigmergy(aid, pattern, value, learned.confidence, tick)


# --- Fase 5 --------------------------------------------------------------------------------------


class MemoryDecaySystem(BaseSystem):
    """(i) Decaimiento de la memoria, en el orden del tick."""

    name = "memory_decay"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, tick = engine.agents, frame.tick
        for aid in frame.order:
            agents[aid].decay_memory(tick)


class HolonCoordinationSystem(BaseSystem):
    """(ii) Costo de coordinación, superávit y `SPLIT` (D24.2), y luego `BOND` (D24.3)."""

    name = "holon_coordination"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        engine._coordinate_and_split(frame.tick, frame.surplus)
        engine._bond(frame.tick)


class MetabolismSystem(BaseSystem):
    """(iii) Costo basal, del ADN, de movimiento y de mensajes (R13, D21, D34.5)."""

    name = "metabolism"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        # Sin comunicación ningún mensaje se envía: no hay costo de mensajes (D21).
        sent = Counter(msg.sender_id for msg in (*frame.emitted, *frame.responses))
        if not engine.config.comm_enabled:
            sent.clear()
        engine._metabolize(frame.moved, sent)


class DeathSystem(BaseSystem):
    """(iv) Muerte de quien quedó con energía <= 0 tras el metabolismo (R13) y, con R35, el
    cadáver de cada muerto, depositado antes de quitarlo (D48.3, precisión 78)."""

    name = "death"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        dead = engine._remove_dead(frame.tick)
        frame.deaths = len(dead)
        if dead and engine.carcasses_active:
            frame.events["carcasses_deposited"] += len(dead)


class ReproductionSystem(BaseSystem):
    """(v) R17 y luego R12 (o su ablación neutral), con ADN e impronta cultural."""

    name = "reproduction"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        frame.births = engine._reproduce(frame.tick)


class DownwardCausationSystem(BaseSystem):
    """(vii) R18 sobre el bosque del final del tick."""

    name = "downward_causation"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        engine._apply_downward_causation()


class EnvironmentDynamicsSystem(BaseSystem):
    """(viii) Dinámica del entorno: reposición de recursos y decaimiento de los rastros."""

    name = "environment_dynamics"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        engine.env.step_dynamics(frame.tick)


def build_systems(config: SimulationConfig) -> tuple[EngineSystem, ...]:
    """Lista ordenada de sistemas del tick (D53.1) para `config`.

    Un mecanismo con sistema propio sólo aparece con su bandera activa; sin las banderas de la
    Fase II-B la lista se reduce exactamente al orden de la Fase II, y sin las de la Fase II al
    de la Fase I. Los bloques siguientes insertan sus sistemas en la posición que les fija D53.1
    (por ejemplo, la germinación y la percepción social en la Fase 1, la conjugación en la Fase 5
    (vi)), siempre detrás de su bandera.
    """
    holonic = config.enable_holonic_hierarchy
    view = holonic and config.enable_holon_view
    evolution = config.enable_evolution
    systems: list[EngineSystem] = []
    # Comienzo del tick: cambio del entorno (D62.1), antes de la Fase 0.
    if config.world_shift_period > 0:
        systems.append(WorldShiftSystem())
    # Fase 0.
    if config.enable_compact_dna:
        systems.append(ExpressionSystem())
    # Fase 1.
    systems.append(ScheduleSystem())
    if holonic:
        systems.append(LocalReachSystem())
    if view:
        systems.append(HolonViewSystem("holon_view_memory", from_memory=True))
    systems.append(PerceptionSystem())
    if genetic_policy_active(config):
        systems.append(SocialPerceptionSystem())
    systems.append(EmissionSystem())
    if config.enable_stigmergy:
        systems.append(StigmergyAssimilationSystem())
    # Fase 2.
    if config.comm_enabled:
        systems.append(SocialExchangeSystem())
    if view:
        systems.append(HolonViewSystem("holon_view_own", from_memory=False))
    # Fase 3 (los observadores reciben `on_decisions` después de este sistema).
    systems.append(DecisionSystem())
    # Fase 4.
    systems.append(ExecutionSystem())
    # Fase 5.
    systems.append(MemoryDecaySystem())
    if holonic:
        systems.append(HolonCoordinationSystem())
    if evolution:
        systems += (MetabolismSystem(), DeathSystem(), ReproductionSystem())
    if holonic:
        systems.append(DownwardCausationSystem())
    systems.append(EnvironmentDynamicsSystem())
    return validate_systems(tuple(systems))
