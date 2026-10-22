"""Observadores de la telemetría de evolución abierta de la Fase II-B (D44.2, D53.2, D53.3).

`GeneticMetricsObserver` produce `engine.genetic_history` y `EcologyMetricsObserver`
`engine.ecology_history`, un registro por tick con cualquier combinación de banderas. No guardan
estado entre llamadas (precisión 73): lo que leen de las decisiones lo escriben en el
`TickFrame` en `on_decisions` (precisión 126: la decisión registrada de un receptor de la
conjugación ya no existe en `on_tick_end`), y lo que cruza ticks lo acumula el colector del motor
(`engine.genetic_collector`). No consumen generadores, no cambian el estado del motor ni de los
agentes y no consultan el oráculo de M2 (precisión 72): las oportunidades y los aciertos de M2
del tick los toman del marco, donde los dejó `TickMetricsObserver`.
"""

from typing import TYPE_CHECKING

from ide.agent.dna import BEHAVIORS
from ide.agent.policy import behavior_feasibility
from ide.domain.ports import EcologicalEnvironmentPort
from ide.experiments.metrics import (
    BEHAVIOR_SLOTS,
    DecisionEcology,
    DecisionRecord,
    ecology_tick_metrics,
    first_feasible_slot,
    summarize_decisions,
)
from ide.simulation.pipeline import TickFrame

if TYPE_CHECKING:
    from ide.simulation.engine import SimulationEngine


def tick_decisions(engine: "SimulationEngine", frame: TickFrame) -> list[int]:
    """Las decisiones del tick (precisión 5): las hojas vivas que no estaban en endospora en la
    Fase 3, incluidas las que terminan en `IDLE`, ascendentes.

    Se leen en `on_decisions`, antes de la Fase 4, que es donde `SPORULATE` cambia el estado. Una
    endospora puesta a mano sin $R_{28}$ decide (precisión 100) pero no cuenta.
    """
    agents = engine.agents
    return sorted(aid for aid in frame.active_order if not agents[aid].is_endospore)


class GeneticMetricsObserver:
    """Produce `GeneticTickMetrics` (D53.2, D63.2) en `engine.genetic_history`.

    En `on_decisions` resume las decisiones del tick: para cada decisión tomada con la política
    genética, compara la primera conducta factible según el ADN del agente (con la evaluación
    registrada de su decisión) con la del ADN fundador, sobre las mismas señales y
    factibilidades, con `EXPLORE` factible si hay recursos alcanzables desconocidos y sin
    extraer de ningún generador; y lee los símbolos emitidos (`frame.signals`). En `on_tick_end`
    arma el registro con el estado de las hojas vivas al final del tick.
    """

    def on_decisions(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, tick = engine.agents, frame.tick
        founder = engine.genetic_collector.founder_drives
        records: list[DecisionRecord] = []
        for aid in tick_decisions(engine, frame):
            agent = agents[aid]
            emitted = frame.signals.get(aid, 0)
            evaluation = agent.decision_evaluation(tick)
            if evaluation is None:  # no decidió con la política genética
                records.append(DecisionRecord(emitted, None, False))
                continue
            signals, feasible = behavior_feasibility(
                agent, frame.observations[aid], frame.social.get(aid)
            )
            own = first_feasible_slot(evaluation.drives, feasible)
            records.append(
                DecisionRecord(emitted, signals, own != first_feasible_slot(founder, feasible))
            )
        frame.decision_genetics = summarize_decisions(records)

    def on_tick_end(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        engine.genetic_history.append(
            engine.genetic_collector.record_tick(
                frame.tick,
                engine.agents,
                engine.root_nodes,
                frame.events,
                frame.born,
                frame.death_ages,
                frame.plasmid_receptions,
                frame.decision_genetics,
            )
        )


class EcologyMetricsObserver:
    """Produce `EcologyTickMetrics` (D53.3, D63.3, D63.4) en `engine.ecology_history`.

    En `on_decisions` cuenta las decisiones del tick y su conducta (`decision_behavior`, sólo con
    la política genética); en `on_tick_end` copia los eventos del tick (precisión 20), los
    recursos presentes (`get_resource_count`, precisión 18; 0 con un entorno sin el puerto
    ecológico, precisión 133) y M2 del tick.
    """

    def on_decisions(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        agents, tick = engine.agents, frame.tick
        decisions = tick_decisions(engine, frame)
        counts = [0] * len(BEHAVIORS)
        for aid in decisions:
            behavior = agents[aid].decision_behavior(tick)
            if behavior is not None:
                counts[BEHAVIOR_SLOTS[behavior]] += 1
        frame.decision_ecology = DecisionEcology(len(decisions), tuple(counts))

    def on_tick_end(self, engine: "SimulationEngine", frame: TickFrame) -> None:
        env = engine.env
        resources = env.get_resource_count() if isinstance(env, EcologicalEnvironmentPort) else 0
        decisions = frame.decision_ecology or DecisionEcology(0, (0,) * len(BEHAVIORS))
        engine.ecology_history.append(
            ecology_tick_metrics(
                frame.tick,
                resources,
                frame.events,
                decisions,
                frame.decision_opportunities,
                frame.correct_decisions,
            )
        )
