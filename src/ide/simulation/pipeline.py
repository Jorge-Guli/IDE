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
from typing import TYPE_CHECKING, NamedTuple, Protocol, cast, runtime_checkable

import numpy as np

from ide.agent.dna import internal_state_active, signals_active
from ide.agent.evolution import sos_mutation_active
from ide.agent.holon import CompositeAgent
from ide.config import SimulationConfig, genetic_policy_active, sporulation_active
from ide.domain.extensions import CompositeRule
from ide.domain.ports import EcologicalEnvironmentPort
from ide.domain.types import (
    CARCASS_PATTERN,
    ActionType,
    AgentAction,
    EventSignals,
    Message,
    Observation,
    Pattern,
    SocialPerception,
    integer_id,
)
from ide.experiments.metrics import TickMetrics

if TYPE_CHECKING:
    from ide.agent.micro_agent import MicroAgent
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

    Al final, `predated`: los objetivos de un ataque con éxito y `stolen > 0` del tick
    ($R_{37}$), que escribe la ejecución y lee el paso de muerte (precisiones 37 y 84).

    Después, los insumos de `EventSignals` ($R_{32}$, D58.5, precisión 87), que lee
    `EventsSystem` al final del tick: `start_energy`, la instantánea de energías al empezar el
    tick que toma la percepción social (D47.3); `ate`, quienes consumieron un recurso con valor
    experimentado positivo; y `received`, los que ganaron energía como objetivo de un `SHARE`.
    Los llenan sólo con la política genética efectivamente activa.

    Por último, `signals`: la máscara de símbolos emitidos en la Fase 3 por cada emisor con
    alguno ($R_{41}$, D60.3, precisión 97), que escribe `SignalEmissionSystem` y lee el
    metabolismo para cobrar `signal_cost` por símbolo. Sin $R_{41}$ queda vacío.

    Al final, `dormant` (R28, precisión E1 y E6): las endosporas que lo siguen siendo después de
    la germinación, es decir, las que estuvieron en endospora todo el tick. Lo calcula una vez
    `GerminationSystem`; sin $R_{28}$ efectiva queda vacío y nadie es "dormido". Quien esporula
    en la Fase 4 no está en él: actuó en el tick.
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
    predated: set[int] = field(default_factory=set[int])
    start_energy: dict[int, float] = field(default_factory=dict[int, float])
    ate: set[int] = field(default_factory=set[int])
    received: set[int] = field(default_factory=set[int])
    signals: dict[int, int] = field(default_factory=dict[int, int])
    dormant: frozenset[int] = frozenset()


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

    La marca `notifies_decisions` señala el sistema tras el cual se notifica `on_decisions`: el
    de decisión o, con $R_{41}$, el de emisión de señales, que lo sigue en la Fase 3 (decisión,
    emisión de señales, contexto de compuestos, `on_decisions` y estado interno; precisión 97).
    """

    name: str
    notifies_decisions: bool = False


def carcasses_active(config: SimulationConfig) -> bool:
    """R35 efectivamente activa: con `enable_carcasses` y evolución (D48.3, D52.3, precisión 78).

    Es la única definición de la condición; el motor la guarda en `engine.carcasses_active`.
    """
    return config.enable_evolution and config.enable_carcasses


def energy_transfer_active(config: SimulationConfig) -> bool:
    """R36 efectivamente activa: `enable_energy_transfer` con R32 efectiva (D52.3, precisión 83).

    `SHARE` sólo existe como conducta del ADN: sin la política genética la bandera es inerte, y
    sin evolución no hay energía que ceder. Es la única definición de la condición; el motor la
    guarda en `engine.energy_transfer_active`.
    """
    return (
        config.enable_evolution and genetic_policy_active(config) and config.enable_energy_transfer
    )


def predation_active(config: SimulationConfig) -> bool:
    """R37 efectivamente activa: `enable_predation` con R32 efectiva (D52.3, precisión 83).

    Sin evolución no hay energía que robar. Es la única definición de la condición; el motor la
    guarda en `engine.predation_active`.
    """
    return config.enable_evolution and genetic_policy_active(config) and config.enable_predation


def telomere_senescence_active(config: SimulationConfig) -> bool:
    """R29 efectivamente activa: `enable_telomere_senescence` con evolución (D30.3, D39).

    Es la única definición de la condición: con ella, `build_systems` agrega `SenescenceSystem`.
    Sin evolución la bandera es inerte: no hay metabolismo al que sumar la senescencia.
    """
    return config.enable_evolution and config.enable_telomere_senescence


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


class GerminationSystem(BaseSystem):
    """Germinación de la endospora (R28, D38): en la Fase 1, después de la percepción.

    Una endospora germina (`set_endospore(False)`) si su observación tiene algún recurso visible
    o, con $R_{19}$, su celda tiene un rastro con `sign_value > 0`. Germina antes de la
    percepción social y de la emisión, y actúa normalmente en ese tick (precisión E1). No consume
    generadores. Sólo está en la lista con $R_{28}$ efectivamente activa.
    """

    name = "germination"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, observations = engine.agents, frame.observations
        trails = engine.config.enable_stigmergy
        for aid in frame.order:
            agent = agents[aid]
            if not agent.is_endospore:
                continue
            if observations[aid].visible_resources or (
                trails and any(t.sign_value > 0 for t in engine._evo.get_cell_stigmergy(aid))
            ):
                agent.set_endospore(False)
        frame.dormant = frozenset(aid for aid in frame.order if agents[aid].is_endospore)


class SocialPerceptionSystem(BaseSystem):
    """Percepción social (R32, D47.3): una `SocialPerception` por agente en `frame.social`.

    Sólo está en la lista con la política genética efectivamente activa. Construye la
    percepción de los agentes que pueden decidir: con $R_{28}$ una endospora no se percibe
    socialmente, porque no decide (D38, precisión E1). Usa
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
        # Instantánea de energías: sólo se consulta, nunca se recorre para dar un orden. Es también
        # la energía al empezar el tick de `EventSignals.lost_energy` (precisión 87): nada cambia
        # la energía antes de la Fase 4.
        energy = {aid: agent.energy for aid, agent in agents.items()}
        frame.start_energy = energy
        crowding = engine.config.crowding_threshold
        dormant = frame.dormant
        for aid in frame.order:
            if aid in dormant:
                continue
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


class SignalPerceptionSystem(BaseSystem):
    """Percepción de las señales del tick anterior ($R_{41}$, D60.4, D60.5, precisiones 64 y 65).

    Va después de la germinación y de la percepción social, y antes de la emisión de mensajes.
    Recalcula `perceived_symbols` de cada agente, en orden de `agent_id`: la máscara pendiente
    de `engine.pending_signals` (el OR de los símbolos que emitieron en la Fase 3 del tick
    anterior los emisores de los que era vecino de comunicación), si sigue vivo y no es
    endospora; si no, 0. Con `comm_content_null`, cada máscara no vacía se reemplaza en ese
    orden por `int(null_rng.integers(1, 256))`: la señal conserva su presencia y pierde su
    contenido. Vacía `pending_signals`: nadie percibe una señal dos veces. Las señales no son
    `Message` ni creencias: no pasan por el protocolo ni por la memoria (D60.6). Sólo está en la
    lista con $R_{41}$ efectivamente activa, y sólo consume `null_rng` con el control nulo.
    """

    name = "signal_perception"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        pending, agents = engine.pending_signals, engine.agents
        null = engine.config.comm_content_null
        for aid in sorted(agents):
            agent = agents[aid]
            mask = 0 if agent.is_endospore else pending.get(aid, 0)
            if mask and null:
                mask = int(engine.null_rng.integers(1, 256))
            agent.set_perceived_symbols(mask)
        engine.pending_signals = {}


class EmissionSystem(BaseSystem):
    """Emisión de mensajes sobre la observación de la Fase 1, con la puerta de D46.6.

    La puerta vive en `protocol.py` (`agent.communicates`): este sistema no la conoce.
    """

    name = "emission"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, tick = engine.agents, frame.tick
        observations, emitted = frame.observations, frame.emitted
        dormant = frame.dormant
        for aid in frame.order:
            if aid in dormant:
                continue  # R28 (D38): una endospora no emite
            emitted += agents[aid].perceive_and_emit_messages(observations[aid], tick)


class StigmergyAssimilationSystem(BaseSystem):
    """Rastros de la celda como testimonios del emisor sintético (R19, D27.3)."""

    name = "stigmergy_assimilation"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        engine._assimilate_stigmergy(frame.tick, frame.dormant)


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
        for aid, inbox in engine._route(frame.emitted, neighbors, order, frame.dormant).items():
            responses += agents[aid].process_incoming_messages(inbox, tick)
        for aid, inbox in engine._route(responses, neighbors, order, frame.dormant).items():
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

    def __init__(self, notifies_decisions: bool = True) -> None:
        # Con $R_{41}$ la marca pasa a `SignalEmissionSystem`, que la sigue en la Fase 3.
        self.notifies_decisions = notifies_decisions

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, tick, rng = engine.agents, frame.tick, engine.rng
        rules = engine._composite_rules
        actions, intents = frame.actions, frame.composite_intents
        reachable = frame.composite_reachable
        social = frame.social
        dormant = frame.dormant
        for aid in frame.order:
            observation = frame.observations[aid]
            agent, perception = agents[aid], social.get(aid)
            if aid in dormant:
                # R28 (D38): `IDLE` sin decidir, sin consumir el generador y sin compuestos.
                actions[aid] = AgentAction(ActionType.IDLE)
                continue
            # Sin percepción social se conserva la llamada de la Fase I (`social` es `None`):
            # hay tests de la Fase II que parchean `decide_action` con sólo tres parámetros.
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


class SignalEmissionSystem(BaseSystem):
    """Emisión de señales en la Fase 3 ($R_{41}$, D60.2-D60.4, precisión 97).

    Va inmediatamente después de la decisión y lleva la marca `notifies_decisions`: la Fase 3 es
    decisión, emisión de señales, contexto de compuestos (que corre dentro de la decisión y es
    independiente de la emisión), `on_decisions` y estado interno. Cada agente que decidió con
    la política genética emite los símbolos `emitted` de la evaluación registrada de su
    decisión, a la vez que actúa: `SIGNAL` no ocupa la acción. Una endospora no registra su
    decisión, así que no emite. Escribe `frame.signals` (emisor -> máscara, que el metabolismo
    cobra a `signal_cost` por símbolo), suma el evento `signals_emitted` y deja en
    `engine.pending_signals`, por receptor, el OR de las máscaras de los emisores de cuya
    observación del tick era vecino de comunicación (`neighbor_ids`), para la Fase 1 del tick
    siguiente: nadie percibe una señal del mismo tick. Sólo está en la lista con $R_{41}$
    efectivamente activa; no consume generadores ni depende del orden.
    """

    name = "signal_emission"
    notifies_decisions = True

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, tick, observations = engine.agents, frame.tick, frame.observations
        emitted = frame.signals
        pending: dict[int, int] = {}
        symbols = 0
        for aid in sorted(frame.actions):
            evaluation = agents[aid].decision_evaluation(tick)
            if evaluation is None or not evaluation.emitted:
                continue
            mask = evaluation.emitted
            emitted[aid] = mask
            symbols += mask.bit_count()
            for receiver in observations[aid].neighbor_ids:
                pending[receiver] = pending.get(receiver, 0) | mask
        engine.pending_signals = pending
        if symbols:
            frame.events["signals_emitted"] += symbols  # D63.3, precisiones 20 y 85


class InternalStateSystem(BaseSystem):
    """Aplicación del estado interno al terminar la Fase 3 ($R_{39}$, D58.3).

    A cada agente que decidió le aplica el estado siguiente de la evaluación registrada de su
    decisión del tick (`MicroAgent.apply_internal_state`), `(internal_state | set_mask) &
    ~clear_mask`, después de la decisión y de `on_decisions`: la decisión del tick usó el estado
    anterior, y la evaluación del tick siguiente lee el nuevo. Un agente que no decidió con la
    política genética conserva su estado, y una endospora también, porque no registra su
    decisión: el estado se conserva en endospora (D58.1). Sólo está en la lista con $R_{39}$
    efectivamente activa; no consume generadores ni depende del orden.
    """

    name = "internal_state"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, tick = engine.agents, frame.tick
        for aid in sorted(frame.actions):
            agents[aid].apply_internal_state(tick)


# --- Fase 4 --------------------------------------------------------------------------------------


def _interaction_target(
    engine: "SimulationEngine", actor_id: int, target: object
) -> "MicroAgent | None":
    """El objetivo de un `SHARE` o un `ATTACK` si sigue vivo, no es endospora y sigue adyacente.

    "Sigue vivo" es "sigue en `engine.agents`": nadie muere en la Fase 4 (precisión 12).
    "Adyacente" es a distancia <= 1 del actor al ejecutarse, la misma noción que
    `SocialPerception.adjacent` (precisión 86): el motor la consulta al entorno, y el agente
    sigue sin conocer coordenadas. Si el objetivo o el actor se movieron antes en la permutación
    del tick y quedaron a distancia mayor, devuelve `None`.
    """
    target_id = integer_id(target)
    if target_id is None:
        return None
    agent = engine.agents.get(target_id)
    if agent is None or agent.is_endospore:
        return None
    if engine._evo.get_agent_distance(actor_id, target_id) > 1:
        return None
    return agent


def _execute_share(
    engine: "SimulationEngine", donor_id: int, target: object, frame: TickFrame
) -> None:
    """`SHARE` ($R_{36}$, D49.1, precisiones 11, 12 y 86) con las energías vigentes al ejecutarse.

    Si el donante tiene energía > 0 y el objetivo es otro agente, sigue vivo, no es endospora y
    sigue adyacente, el donante pierde
    `amount = share_fraction * energía` y el receptor gana `share_efficiency * amount`; si no, no
    ocurre nada. Cuenta el evento `shares` sólo si transfiere energía, `amount > 0` (precisión
    85; métrica de C18).
    """
    donor, receiver = engine.agents[donor_id], _interaction_target(engine, donor_id, target)
    if receiver is None or receiver is donor or donor.energy <= 0:
        return
    config = engine.config
    amount = config.share_fraction * donor.energy
    donor.apply_energy_delta(-amount)
    received = config.share_efficiency * amount
    receiver.apply_energy_delta(received)
    if amount > 0:
        frame.events["shares"] += 1
    if received > 0:
        frame.received.add(receiver.agent_id)  # evento `received_energy` (D58.5, precisión 87)


def _execute_attack(
    engine: "SimulationEngine", attacker_id: int, target: object, frame: TickFrame
) -> None:
    """`ATTACK` ($R_{37}$, D49.2, precisión 12) con las energías vigentes al ejecutarse.

    El intento se cuenta siempre en `frame.attacks` (su costo lo cobra el metabolismo) y en el
    evento `attacks`, también si el objetivo ya no está adyacente (precisión 86). Tiene éxito si el
    objetivo sigue vivo, no es endospora, sigue adyacente y es estrictamente más débil que el
    atacante; entonces `stolen = min(attack_power, max(0, energía_del_objetivo))`
    pasa del objetivo al atacante con la eficiencia `predation_efficiency`. Un ataque con éxito y
    `stolen > 0` deja al objetivo en `frame.predated`, que el paso de muerte usa para separar las
    muertes por depredación de las de hambre (precisiones 37 y 84).
    """
    frame.attacks[attacker_id] = frame.attacks.get(attacker_id, 0) + 1
    frame.events["attacks"] += 1
    attacker = engine.agents[attacker_id]
    victim = _interaction_target(engine, attacker_id, target)
    if victim is None or attacker.energy <= victim.energy:
        return
    config = engine.config
    stolen = min(config.attack_power, max(0.0, victim.energy))
    victim.apply_energy_delta(-stolen)
    attacker.apply_energy_delta(config.predation_efficiency * stolen)
    frame.events["successful_attacks"] += 1
    if stolen > 0:
        frame.predated.add(victim.agent_id)


# Acciones sin recompensa de R40 (D59.4): no cambian la energía del agente en la Fase 4.
_UNREWARDED = frozenset((ActionType.MOVE, ActionType.IDLE, ActionType.SPORULATE))


class ExecutionSystem(BaseSystem):
    """Ejecución en el orden de la permutación, aprendizaje directo, energía y estigmergia.

    Con $R_{36}$ y $R_{37}$ efectivamente activas, el motor ejecuta `SHARE` y `ATTACK` en ese mismo
    recorrido, sobre las energías vigentes al ejecutar cada una (D49): la permutación del tick es
    la única fuente de orden. Sin ellas, la grilla las ejecuta como `IDLE`, como en la Fase II.
    `SPORULATE` (R28 efectiva) pone al agente en endospora y cuenta el evento `sporulations`: es la
    única entrada (D50.2). Con $R_{28}$ una endospora no decide, así que su acción es `IDLE`; una
    puesta a mano que decidió `SHARE` o `ATTACK` no tiene efecto ni paga el intento.

    Con $R_{40}$ efectivamente activa, inmediatamente después de ejecutar la acción de cada
    agente aplica la regla de aprendizaje (`MicroAgent.reinforce`, D59.4) con la recompensa $r$:
    el cambio de la energía del agente durante su propia acción (consumir un recurso, un cadáver
    o un compuesto, ceder o robar energía), y 0 en `MOVE`, `IDLE` y `SPORULATE`. Lo que le hacen
    otros agentes ocurre en sus turnos y los costos de la Fase 5 después, así que no cuentan. Suma
    las actualizaciones al evento `plastic_updates` (D63.3, precisión 62). No consume generadores.
    """

    name = "execution"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, actions, tick = engine.agents, frame.actions, frame.tick
        config = engine.config
        flags = _ExecutionFlags(
            rules=engine._composite_rules,
            ate=frame.ate if engine.genetic_policy_active else None,
            transfer=engine.energy_transfer_active,
            predation=engine.predation_active,
            carcasses=engine.carcasses_active,
            evolution=config.enable_evolution,
            deposit=config.enable_stigmergy and config.stigmergy_deposit_rate > 0,
            sporulation=engine.sporulation_active,
        )
        learning = engine.plasticity_active
        updates = 0
        for aid in frame.order:
            action = actions[aid]
            if not learning or action.action_type in _UNREWARDED:
                _execute_action(engine, frame, flags, aid, action)
                continue
            # R40 (D59.4): la recompensa es el cambio de la energía durante la propia acción.
            learner = agents[aid]
            before = learner.energy
            _execute_action(engine, frame, flags, aid, action)
            updates += learner.reinforce(tick, learner.energy - before)
        if updates:
            frame.events["plastic_updates"] += updates  # D63.3, precisiones 20, 62 y 85


class _ExecutionFlags(NamedTuple):
    """Condiciones de la ejecución, calculadas una vez por tick en `ExecutionSystem.run`."""

    rules: dict[Pattern, CompositeRule]  # reglas de los recursos compuestos (D25)
    ate: set[int] | None  # evento `ate` (D58.5, precisión 87): sólo con R32 efectiva
    transfer: bool  # R36 efectivamente activa
    predation: bool  # R37 efectivamente activa
    carcasses: bool  # R35 efectivamente activa
    evolution: bool  # la energía del recurso se suma al agente
    deposit: bool  # depósito estigmérgico (R19)
    sporulation: bool  # R28 efectivamente activa: `SPORULATE` pone al agente en endospora


def _execute_action(
    engine: "SimulationEngine",
    frame: TickFrame,
    flags: _ExecutionFlags,
    aid: int,
    action: AgentAction,
) -> None:
    """Ejecuta la acción de `aid` en la Fase 4: interacción, recurso, compuesto o movimiento.

    `SHARE` y `ATTACK` con $R_{36}$ y $R_{37}$ efectivamente activas los aplica el motor (una
    endospora no tiene efecto, precisión 82); lo demás lo ejecuta el entorno. Un recurso elemental
    o un cadáver enseña su valor experimentado, da energía con la evolución y deposita la
    estigmergia ($R_{19}$); un compuesto se resuelve con el contexto fijado al decidir (D27).
    """
    kind = action.action_type
    if kind is ActionType.SPORULATE and flags.sporulation:
        # R28 (D38, D50.2): la única entrada en endospora; el agente actúa como `IDLE`.
        engine.agents[aid].set_endospore(True)
        frame.events["sporulations"] += 1
        return
    sharing = flags.transfer and kind is ActionType.SHARE
    if sharing or (flags.predation and kind is ActionType.ATTACK):
        if not engine.agents[aid].is_endospore:  # sólo una endospora puesta a mano, sin R28 (E3)
            execute = _execute_share if sharing else _execute_attack
            execute(engine, aid, action.target, frame)
        return
    tick = frame.tick
    result = engine.env.execute_action(aid, action, tick)
    if result.action_type is ActionType.MOVE:
        frame.moved.add(aid)
    pattern, value = result.interacted_pattern, result.experienced_value
    if value is None or pattern is None:
        return
    ate = flags.ate
    if pattern in flags.rules:
        context = frame.composite_contexts[aid]
        engine._resolve_composite(aid, pattern, flags.rules[pattern], context, tick, frame.surplus)
        if ate is not None and context[0]:  # con éxito, aprende el valor 1.0
            ate.add(aid)
        return
    if ate is not None and value > 0:
        ate.add(aid)
    if flags.carcasses and pattern == CARCASS_PATTERN:
        frame.events["carcasses_eaten"] += 1  # R35: sigue el camino de un recurso elemental
    agent = engine.agents[aid]
    agent.learn_from_experience(pattern, value, tick)
    engine.direct_discoverers[pattern].add(aid)
    if flags.evolution:
        agent.apply_energy_delta(engine.config.energy_gain_scale * value)
    if flags.deposit:
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
    """(iii) Costo basal, del ADN, de movimiento, de mensajes, de los ataques y de las señales
    (R13, D21, D34.5, D49.2, D60.3): `attack_cost` por cada intento registrado en
    `frame.attacks`, con éxito o sin él, y `signal_cost` por cada símbolo de `frame.signals`."""

    name = "metabolism"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        # Sin comunicación ningún mensaje se envía: no hay costo de mensajes (D21).
        sent = Counter(msg.sender_id for msg in (*frame.emitted, *frame.responses))
        if not engine.config.comm_enabled:
            sent.clear()
        engine._metabolize(frame.moved, sent, frame.attacks, frame.signals, frame.dormant)


class SenescenceSystem(BaseSystem):
    """(iii) Senescencia telomérica (R29, D39): `compute_senescence_cost` a cada agente vivo.

    Completa el cobro metabólico del paso (iii), antes de la muerte, con la edad
    `tick - birth_tick` y la longevidad expresada (`phenotype.lifespan`), también a las
    endosporas. Sólo está en la lista con $R_{29}$ efectivamente activa.
    """

    name = "senescence"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        engine._charge_senescence(frame.tick)


class DeathSystem(BaseSystem):
    """(iv) Muerte de quien quedó con energía <= 0 tras el metabolismo (R13) y, con R35, el
    cadáver de cada muerto, depositado antes de quitarlo (D48.3, precisión 78).

    Cuenta además, siempre que haya muertes, las del tick por depredación (objetivos de un ataque
    con éxito y `stolen > 0` en el tick, `frame.predated`) y por hambre (las demás),
    excluyentes (precisiones 37, 84 y 85).
    """

    name = "death"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        dead = engine._remove_dead(frame.tick)
        frame.deaths = len(dead)
        if not dead:
            return
        events = frame.events
        if engine.carcasses_active:
            events["carcasses_deposited"] += len(dead)
        predated = frame.predated
        by_predation = sum(1 for aid in dead if aid in predated)
        if by_predation:
            events["predation_deaths"] += by_predation
        if by_predation < len(dead):
            events["starvation_deaths"] += len(dead) - by_predation


class StressSystem(BaseSystem):
    """(iv) Registro del estrés (D39, precisión 7 y 91): `last_stress_tick` de los sobrevivientes.

    Va después de la muerte y antes de la reproducción, y sólo está en la lista con $R_{30}$
    efectivamente activa, porque nadie más lo lee: en la Fase II no cuesta nada.
    """

    name = "stress"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        engine._record_stress(frame.tick)


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


class EventsSystem(BaseSystem):
    """Eventos del tick (D58.5, precisiones 64 y 87): un `EventSignals` por agente vivo.

    Corre al final de la Fase 5, después de la muerte y de todo lo que cambia la energía del tick,
    y antes de los observadores de `on_tick_end`. Escribe `agent.last_events`, que la política
    genética lee en el tick siguiente:
    - `attacked`: objetivo de un ataque con éxito y `stolen > 0` (`frame.predated`);
    - `ate`: consumió un recurso con valor experimentado positivo (`frame.ate`);
    - `lost_energy`: su energía al final del tick es menor que al empezar (`frame.start_energy`);
    - `received_energy`: objetivo de un `SHARE` del que ganó energía (`frame.received`).
    Un agente nacido en el tick no está en la instantánea y recibe `EventSignals()`, como al
    nacer. Sólo está en la lista con la política genética efectivamente activa, también sin
    $R_{39}$: los eventos son percepción, no memoria (D58.7). No consume generadores.
    """

    name = "events"

    def run(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        start, predated, ate, received = (
            frame.start_energy,
            frame.predated,
            frame.ate,
            frame.received,
        )
        for aid in sorted(engine.agents):
            agent = engine.agents[aid]
            before = start.get(aid)
            if before is None:  # nacido en el tick
                agent.set_last_events(EventSignals())
                continue
            agent.set_last_events(
                EventSignals(
                    attacked=aid in predated,
                    ate=aid in ate,
                    lost_energy=agent.energy < before,
                    received_energy=aid in received,
                )
            )


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
    signals = signals_active(config)
    if sporulation_active(config):
        systems.append(GerminationSystem())
    if genetic_policy_active(config):
        systems.append(SocialPerceptionSystem())
    if signals:  # R41: señales del tick anterior (D60.4), tras la germinación y lo social
        systems.append(SignalPerceptionSystem())
    systems.append(EmissionSystem())
    if config.enable_stigmergy:
        systems.append(StigmergyAssimilationSystem())
    # Fase 2.
    if config.comm_enabled:
        systems.append(SocialExchangeSystem())
    if view:
        systems.append(HolonViewSystem("holon_view_own", from_memory=False))
    # Fase 3: decisión y, con R41, emisión de señales (D60.3); los observadores reciben
    # `on_decisions` después del último de los dos; con R39, al terminarla, la aplicación del
    # estado interno (D58.3).
    systems.append(DecisionSystem(notifies_decisions=not signals))
    if signals:
        systems.append(SignalEmissionSystem())
    if internal_state_active(config):
        systems.append(InternalStateSystem())
    # Fase 4.
    systems.append(ExecutionSystem())
    # Fase 5.
    systems.append(MemoryDecaySystem())
    if holonic:
        systems.append(HolonCoordinationSystem())
    if evolution:
        systems.append(MetabolismSystem())
        if telomere_senescence_active(config):
            systems.append(SenescenceSystem())
        systems.append(DeathSystem())
        if sos_mutation_active(config):
            systems.append(StressSystem())
        systems.append(ReproductionSystem())
    if holonic:
        systems.append(DownwardCausationSystem())
    systems.append(EnvironmentDynamicsSystem())
    # Final de la Fase 5: eventos del tick para la política genética (D58.5, precisión 87).
    if genetic_policy_active(config):
        systems.append(EventsSystem())
    return validate_systems(tuple(systems))
