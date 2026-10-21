"""Tests de las interacciones entre agentes: transferencia y depredación (bloque 12).

Cubren `SHARE` ($R_{36}$, D49.1, precisiones 11 y 12), `ATTACK` ($R_{37}$, D49.2): éxito sólo
contra un objetivo más débil al ejecutarse, robo acotado, eficiencia, costo por intento en el
metabolismo y muerte con cadáver; los conflictos resueltos por la permutación del tick; que M2
juzga la decisión cualquiera sea la conducta (D49.4, precisión 21); los eventos del tick en
`frame.events` (precisión 20); la conservación (D49.5: ninguna interacción crea energía); la
inercia de las reglas apagadas (D52.3) y el determinismo entre procesos.
"""

import os
import subprocess
import sys
import textwrap
from dataclasses import astuple, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.dna import BEHAVIOR_TARGETS, encode_codon, founder_dna
from ide.config import SimulationConfig
from ide.domain.types import (
    CARCASS_PATTERN,
    ActionType,
    AgentAction,
    Behavior,
    CompactDNA,
)
from ide.environments.grid2d import ToroidalGrid2D
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
from ide.simulation.engine import SimulationEngine
from ide.simulation.pipeline import (
    BaseSystem,
    ExecutionSystem,
    MetabolismSystem,
    ScheduleSystem,
    TickFrame,
    energy_transfer_active,
    predation_active,
)

ROOT = Path(__file__).resolve().parents[1]
IDLE = AgentAction(ActionType.IDLE)
# Claves válidas de `frame.events`: los campos contadores de `EcologyTickMetrics` (precisión 20).
ECOLOGY_COUNTERS = {
    "shares",
    "attacks",
    "successful_attacks",
    "predation_deaths",
    "starvation_deaths",
    "carcasses_deposited",
    "carcasses_eaten",
    "sporulations",
    "recombinations",
}


def cfg(**overrides: Any) -> SimulationConfig:
    """Configuración chica con la política genética, R36 y R37, sin costos ni reproducción."""
    base = SimulationConfig(
        grid_width=10,
        grid_height=10,
        num_agents=14,
        resources_per_pattern=4,
        enable_evolution=True,
        enable_compact_dna=True,
        enable_genetic_policy=True,
        enable_energy_transfer=True,
        enable_predation=True,
        metabolic_base_cost=0.0,
        memory_capacity_cost=0.0,
        sensory_radius_cost=0.0,
        move_cost=0.0,
        message_cost=0.0,
        dna_codon_cost=0.0,
        attack_cost=0.0,
        reproduction_threshold=100.0,
    )
    return replace(base, **overrides)


def grid_of(engine: SimulationEngine) -> ToroidalGrid2D:
    return cast(ToroidalGrid2D, engine.env)


class FixedOrder(BaseSystem):
    """Reemplaza la permutación del tick: primero `order` y después el resto, ascendente."""

    name = "schedule"

    def __init__(self, order: list[int]) -> None:
        self.order = order

    def run(self, engine: SimulationEngine, frame: TickFrame) -> None:
        rest = [aid for aid in sorted(engine.agents) if aid not in self.order]
        frame.order = [*self.order, *rest]


def fix_order(engine: SimulationEngine, order: list[int]) -> None:
    engine.systems = tuple(
        FixedOrder(order) if isinstance(system, ScheduleSystem) else system
        for system in engine.systems
    )


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


def set_energy(engine: SimulationEngine, aid: int, energy: float) -> None:
    agent = engine.agents[aid]
    agent.apply_energy_delta(energy - agent.energy)


class Spy:
    """Registra, al final del tick, los eventos, los ataques y M2 del marco."""

    def __init__(self) -> None:
        self.events: list[dict[str, int]] = []
        self.attacks: list[dict[int, int]] = []
        self.deaths: list[int] = []
        self.m2: list[tuple[int, int]] = []

    def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.m2.append((frame.decision_opportunities, frame.correct_decisions))

    def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
        self.events.append(dict(frame.events))
        self.attacks.append(dict(frame.attacks))
        self.deaths.append(frame.deaths)


def spied(engine: SimulationEngine) -> Spy:
    spy = Spy()
    engine.observers.append(spy)
    return spy


def share(target: int) -> AgentAction:
    return AgentAction(ActionType.SHARE, target)


def attack(target: int) -> AgentAction:
    return AgentAction(ActionType.ATTACK, target)


# --- Condiciones efectivas (D52.3) -------------------------------------------------------------


def test_r36_y_r37_inertes_sin_evolucion() -> None:
    """La validación ya exige evolución con ADN; la condición la exige igual, como R28."""
    flags = {
        "enable_compact_dna": True,
        "enable_genetic_policy": True,
        "enable_energy_transfer": True,
        "enable_predation": True,
    }
    on = cast(SimulationConfig, SimpleNamespace(enable_evolution=True, **flags))
    off = cast(SimulationConfig, SimpleNamespace(enable_evolution=False, **flags))
    assert energy_transfer_active(on) and predation_active(on)
    assert not energy_transfer_active(off) and not predation_active(off)


def test_condiciones_efectivas_de_r36_y_r37() -> None:
    assert energy_transfer_active(cfg()) and predation_active(cfg())
    assert not energy_transfer_active(cfg(enable_energy_transfer=False))
    assert not predation_active(cfg(enable_predation=False))
    # Sin la política genética (R32), las dos reglas son inertes.
    assert not energy_transfer_active(cfg(enable_genetic_policy=False))
    assert not predation_active(cfg(enable_genetic_policy=False))
    without_dna = cfg(enable_compact_dna=False)
    assert not energy_transfer_active(without_dna) and not predation_active(without_dna)


# --- (a) SHARE (D49.1) ---------------------------------------------------------------------------


def test_cesion_con_perdida(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(share_fraction=0.25, share_efficiency=0.9))
    set_energy(engine, 1, 2.0)
    set_energy(engine, 3, 0.5)
    act(monkeypatch, engine, {1: share(3)})
    spy = spied(engine)
    engine.step()
    assert engine.agents[1].energy == pytest.approx(1.5, abs=1e-9)
    assert engine.agents[3].energy == pytest.approx(0.95, abs=1e-9)
    assert spy.events == [{"shares": 1}]


def test_cesion_a_una_endospora_sin_efecto(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg())
    set_energy(engine, 1, 2.0)
    set_energy(engine, 3, 0.5)
    engine.agents[3].set_endospore(True)
    act(monkeypatch, engine, {1: share(3)})
    spy = spied(engine)
    engine.step()
    assert engine.agents[1].energy == pytest.approx(2.0, abs=1e-9)
    assert engine.agents[3].energy == pytest.approx(0.5, abs=1e-9)
    assert spy.events == [{}]


@pytest.mark.parametrize("donor_energy", [0.0, -0.2])
def test_donante_sin_energia_no_cede(donor_energy: float) -> None:
    engine = SimulationEngine(cfg())
    set_energy(engine, 1, donor_energy)
    set_energy(engine, 3, 0.5)
    before = {aid: agent.energy for aid, agent in engine.agents.items()}
    # Sólo la Fase 4: el donante sin energía moriría en la Fase 5.
    actions = {aid: IDLE for aid in engine.agents}
    actions[1] = share(3)
    frame = TickFrame(0, order=sorted(engine.agents), actions=actions)
    ExecutionSystem().run(engine, frame)
    assert {aid: agent.energy for aid, agent in engine.agents.items()} == before
    assert "shares" not in frame.events


def test_donante_vaciado_antes_en_la_misma_fase(monkeypatch: pytest.MonkeyPatch) -> None:
    """El donante con energía 0.3 al decidir es robado antes de ceder: su SHARE no hace nada."""
    engine = SimulationEngine(cfg(attack_power=0.5, predation_efficiency=0.6))
    set_energy(engine, 5, 1.0)
    set_energy(engine, 1, 0.3)
    set_energy(engine, 3, 0.5)
    act(monkeypatch, engine, {5: attack(1), 1: share(3)})
    fix_order(engine, [5, 1])
    spy = spied(engine)
    engine.step()
    assert 1 not in engine.agents  # quedó con energía 0.0 y murió en la Fase 5
    assert engine.agents[3].energy == pytest.approx(0.5, abs=1e-9)
    assert engine.agents[5].energy == pytest.approx(1.18, abs=1e-9)
    assert spy.events == [
        {"attacks": 1, "successful_attacks": 1, "predation_deaths": 1},
    ]


def test_cesion_a_un_objetivo_inexistente_sin_efecto(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg())
    before = {aid: agent.energy for aid, agent in engine.agents.items()}
    act(monkeypatch, engine, {1: share(999)})
    spy = spied(engine)
    engine.step()
    assert {aid: agent.energy for aid, agent in engine.agents.items()} == before
    assert spy.events == [{}]


def test_cesion_nula_no_cuenta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con `share_fraction = 0` la cesión no transfiere energía: no cuenta en `shares` (C18)."""
    engine = SimulationEngine(cfg(share_fraction=0.0))
    set_energy(engine, 1, 2.0)
    act(monkeypatch, engine, {1: share(3)})
    before = {aid: agent.energy for aid, agent in engine.agents.items()}
    spy = spied(engine)
    engine.step()
    assert {aid: agent.energy for aid, agent in engine.agents.items()} == before
    assert spy.events == [{}]


def test_endospora_no_cede_ni_ataca(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hasta el bloque 17, una endospora que decidió SHARE o ATTACK actúa como IDLE (prec. 82)."""
    engine = SimulationEngine(cfg(attack_cost=0.3))
    set_energy(engine, 1, 2.0)
    set_energy(engine, 4, 2.0)
    for aid in (1, 4):
        engine.agents[aid].set_endospore(True)
    act(monkeypatch, engine, {1: share(3), 4: attack(6)})
    before = {aid: agent.energy for aid, agent in engine.agents.items()}
    spy = spied(engine)
    engine.step()
    assert {aid: agent.energy for aid, agent in engine.agents.items()} == before
    assert spy.attacks == [{}]
    assert spy.events == [{}]


def test_cesion_inerte_sin_r36(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(enable_energy_transfer=False))
    set_energy(engine, 1, 2.0)
    act(monkeypatch, engine, {1: share(3)})
    before = {aid: agent.energy for aid, agent in engine.agents.items()}
    spy = spied(engine)
    engine.step()
    assert {aid: agent.energy for aid, agent in engine.agents.items()} == before
    assert spy.events == [{}]


# --- (b) ATTACK (D49.2) ----------------------------------------------------------------------


def test_robo_acotado_y_muerte_por_depredacion(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(attack_power=0.5, predation_efficiency=0.6))
    set_energy(engine, 4, 1.2)
    set_energy(engine, 6, 0.3)
    act(monkeypatch, engine, {4: attack(6)})
    spy = spied(engine)
    engine.step()
    assert engine.agents[4].energy == pytest.approx(1.38, abs=1e-9)
    assert 6 not in engine.agents
    assert spy.attacks == [{4: 1}]
    assert spy.deaths == [1]
    assert spy.events == [{"attacks": 1, "successful_attacks": 1, "predation_deaths": 1}]


def test_robo_sin_muerte(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(attack_power=0.5, predation_efficiency=0.6))
    set_energy(engine, 4, 2.0)
    set_energy(engine, 6, 1.0)
    act(monkeypatch, engine, {4: attack(6)})
    engine.step()
    assert engine.agents[4].energy == pytest.approx(2.3, abs=1e-9)
    assert engine.agents[6].energy == pytest.approx(0.5, abs=1e-9)


def test_objetivo_igual_de_fuerte(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg())
    set_energy(engine, 4, 0.8)
    set_energy(engine, 6, 0.8)
    act(monkeypatch, engine, {4: attack(6)})
    spy = spied(engine)
    engine.step()
    assert engine.agents[4].energy == pytest.approx(0.8, abs=1e-9)
    assert engine.agents[6].energy == pytest.approx(0.8, abs=1e-9)
    assert spy.attacks == [{4: 1}]
    assert spy.events == [{"attacks": 1}]


def test_objetivo_mas_fuerte(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg())
    set_energy(engine, 4, 0.5)
    set_energy(engine, 6, 0.8)
    act(monkeypatch, engine, {4: attack(6)})
    spy = spied(engine)
    engine.step()
    assert engine.agents[4].energy == pytest.approx(0.5, abs=1e-9)
    assert engine.agents[6].energy == pytest.approx(0.8, abs=1e-9)
    assert spy.events == [{"attacks": 1}]


def test_objetivo_ya_sin_energia(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(attack_power=0.5, predation_efficiency=0.6))
    set_energy(engine, 4, 1.2)
    set_energy(engine, 6, 0.3)
    set_energy(engine, 8, 0.5)
    act(monkeypatch, engine, {4: attack(6), 8: attack(6)})
    fix_order(engine, [4, 8])
    spy = spied(engine)
    engine.step()
    assert engine.agents[8].energy == pytest.approx(0.5, abs=1e-9)  # stolen = 0
    assert spy.attacks == [{4: 1, 8: 1}]
    assert spy.events == [{"attacks": 2, "successful_attacks": 2, "predation_deaths": 1}]


def test_muerte_tras_un_ataque_con_exito_sin_robo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Precisión 37: un ataque con éxito y `stolen = 0` no hace depredación; muere de hambre."""
    engine = SimulationEngine(cfg())
    set_energy(engine, 6, 0.0)
    set_energy(engine, 8, 0.5)
    act(monkeypatch, engine, {8: attack(6)})
    spy = spied(engine)
    engine.step()
    assert 6 not in engine.agents
    assert engine.agents[8].energy == pytest.approx(0.5, abs=1e-9)
    assert spy.events == [{"attacks": 1, "successful_attacks": 1, "starvation_deaths": 1}]


def test_ataque_a_una_endospora_paga_el_costo(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(attack_cost=0.01))
    set_energy(engine, 4, 1.5)
    set_energy(engine, 6, 0.2)
    engine.agents[6].set_endospore(True)
    act(monkeypatch, engine, {4: attack(6)})
    spy = spied(engine)
    engine.step()
    assert engine.agents[6].energy == pytest.approx(0.2, abs=1e-9)
    assert engine.agents[4].energy == pytest.approx(1.49, abs=1e-9)
    assert spy.events == [{"attacks": 1}]


def test_ataque_fallido_con_costo_en_el_metabolismo(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(attack_cost=0.01, metabolic_base_cost=0.01))
    set_energy(engine, 4, 0.5)
    set_energy(engine, 6, 0.8)
    act(monkeypatch, engine, {4: attack(6)})
    before = {aid: agent.energy for aid, agent in engine.agents.items()}
    engine.step()
    assert before[4] - engine.agents[4].energy == pytest.approx(0.02, abs=1e-9)
    assert before[6] - engine.agents[6].energy == pytest.approx(0.01, abs=1e-9)


def test_el_metabolismo_cobra_cada_intento_de_frame_attacks() -> None:
    """El costo es por intento registrado en `frame.attacks` (D49.2), vía `MetabolismSystem`."""
    engine = SimulationEngine(cfg(attack_cost=0.01))
    set_energy(engine, 4, 0.5)
    set_energy(engine, 5, 0.5)
    before = {aid: agent.energy for aid, agent in engine.agents.items()}
    frame = TickFrame(0, order=sorted(engine.agents), attacks={4: 2, 5: 1})
    MetabolismSystem().run(engine, frame)
    assert engine.agents[4].energy == pytest.approx(0.48, abs=1e-9)
    assert engine.agents[5].energy == pytest.approx(0.49, abs=1e-9)
    assert all(engine.agents[aid].energy == before[aid] for aid in before if aid not in (4, 5))


def test_muerte_por_depredacion_deja_cadaver(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(enable_carcasses=True, carcass_value=0.6))
    grid = grid_of(engine)
    set_energy(engine, 4, 1.2)
    set_energy(engine, 6, 0.3)
    set_energy(engine, 7, 0.0)  # muere por hambre
    cell = grid.get_agent_position(6)
    act(monkeypatch, engine, {4: attack(6)})
    spy = spied(engine)
    engine.step()
    assert 6 not in engine.agents and 7 not in engine.agents
    carcasses = [r for r in grid.cell_resources[cell].values() if r.pattern == CARCASS_PATTERN]
    assert len(carcasses) >= 1
    assert spy.events == [
        {
            "attacks": 1,
            "successful_attacks": 1,
            "predation_deaths": 1,
            "starvation_deaths": 1,
            "carcasses_deposited": 2,
        }
    ]


def test_robado_que_muere_en_el_metabolismo_cuenta_como_depredacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Precisión 37: atacado con éxito y `stolen > 0` en el tick, aunque lo remate el costo."""
    engine = SimulationEngine(cfg(attack_power=0.2, metabolic_base_cost=0.2))
    set_energy(engine, 4, 1.2)
    set_energy(engine, 6, 0.3)
    act(monkeypatch, engine, {4: attack(6)})
    spy = spied(engine)
    engine.step()
    assert 6 not in engine.agents
    assert spy.events[0]["predation_deaths"] == 1
    assert "starvation_deaths" not in spy.events[0]


def test_ataque_inerte_sin_r37(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(enable_predation=False, attack_cost=0.5))
    set_energy(engine, 4, 1.2)
    set_energy(engine, 6, 0.3)
    act(monkeypatch, engine, {4: attack(6)})
    spy = spied(engine)
    engine.step()
    assert engine.agents[4].energy == pytest.approx(1.2, abs=1e-9)
    assert engine.agents[6].energy == pytest.approx(0.3, abs=1e-9)
    assert spy.attacks == [{}]
    assert spy.events == [{}]


# --- (c) Conflictos resueltos por la permutación del tick ---------------------------------------


@pytest.mark.parametrize("target_first", [True, False])
def test_mas_debil_al_ejecutarse(monkeypatch: pytest.MonkeyPatch, target_first: bool) -> None:
    """El 1 (0.7) ataca al 2 (0.8), que cede al 3: sólo si cede antes, el ataque tiene éxito."""
    engine = SimulationEngine(cfg(share_fraction=0.25, share_efficiency=0.9, attack_power=0.5))
    set_energy(engine, 1, 0.7)
    set_energy(engine, 2, 0.8)
    set_energy(engine, 3, 0.5)
    act(monkeypatch, engine, {1: attack(2), 2: share(3)})
    fix_order(engine, [2, 1] if target_first else [1, 2])
    spy = spied(engine)
    engine.step()
    agents = engine.agents
    if target_first:
        # 2 cede 0.2 (queda 0.6) y luego 1 (0.7 > 0.6) le roba 0.5.
        assert agents[2].energy == pytest.approx(0.1, abs=1e-9)
        assert agents[1].energy == pytest.approx(0.7 + 0.6 * 0.5, abs=1e-9)
        assert spy.events == [{"shares": 1, "attacks": 1, "successful_attacks": 1}]
    else:
        # 1 (0.7) no es más fuerte que 2 (0.8): fracasa, y 2 cede 0.2.
        assert agents[2].energy == pytest.approx(0.6, abs=1e-9)
        assert agents[1].energy == pytest.approx(0.7, abs=1e-9)
        assert spy.events == [{"attacks": 1, "shares": 1}]
    assert agents[3].energy == pytest.approx(0.68, abs=1e-9)


@pytest.mark.parametrize("order", [[4, 5], [5, 4]])
def test_dos_depredadores_sobre_la_misma_presa(
    monkeypatch: pytest.MonkeyPatch, order: list[int]
) -> None:
    engine = SimulationEngine(cfg(attack_power=0.5, predation_efficiency=0.6))
    set_energy(engine, 4, 1.0)
    set_energy(engine, 5, 1.0)
    set_energy(engine, 6, 0.6)
    act(monkeypatch, engine, {4: attack(6), 5: attack(6)})
    fix_order(engine, order)
    engine.step()
    first, second = order
    assert engine.agents[first].energy == pytest.approx(1.0 + 0.6 * 0.5, abs=1e-9)
    assert engine.agents[second].energy == pytest.approx(1.0 + 0.6 * 0.1, abs=1e-9)
    assert 6 not in engine.agents


def test_el_orden_es_el_de_la_permutacion_del_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin fijar el orden, el resultado es el que dicta la permutación sorteada del tick."""
    engine = SimulationEngine(cfg(attack_power=0.5, predation_efficiency=0.6))
    set_energy(engine, 4, 1.0)
    set_energy(engine, 5, 1.0)
    set_energy(engine, 6, 0.6)
    act(monkeypatch, engine, {4: attack(6), 5: attack(6)})
    orders: list[list[int]] = []

    class OrderSpy:
        def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
            orders.append(list(frame.order))

        def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
            pass

    engine.observers.append(OrderSpy())
    engine.step()
    first = 4 if orders[0].index(4) < orders[0].index(5) else 5
    second = 9 - first
    assert engine.agents[first].energy == pytest.approx(1.3, abs=1e-9)
    assert engine.agents[second].energy == pytest.approx(1.06, abs=1e-9)


# --- (d) M2 juzga la decisión cualquiera sea la conducta (D49.4, precisión 21) ------------------


def _m2_with_truth(
    monkeypatch: pytest.MonkeyPatch, action: AgentAction, truth: dict[int, float]
) -> tuple[int, int]:
    engine = SimulationEngine(cfg())
    grid = grid_of(engine)
    monkeypatch.setattr(
        grid, "get_reachable_true_values", lambda aid: dict(truth) if aid == 1 else {}
    )
    act(monkeypatch, engine, {1: action})
    spy = spied(engine)
    engine.step()
    return spy.m2[0]


@pytest.mark.parametrize("action", [attack(3), share(3)])
def test_m2_ataque_o_cesion_con_recurso_benefico(
    monkeypatch: pytest.MonkeyPatch, action: AgentAction
) -> None:
    assert _m2_with_truth(monkeypatch, action, {50: 1.0}) == (1, 0)


@pytest.mark.parametrize(
    "action",
    [AgentAction(ActionType.MOVE, (1, 0)), attack(3), share(3), AgentAction(ActionType.SPORULATE)],
)
def test_m2_conductas_nuevas_con_solo_recursos_daninos(
    monkeypatch: pytest.MonkeyPatch, action: AgentAction
) -> None:
    assert _m2_with_truth(monkeypatch, action, {50: -1.0, 51: -0.5}) == (1, 1)


def test_m2_cadaver_en_el_oraculo(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(enable_carcasses=True))
    grid = grid_of(engine)
    for pattern in sorted(grid.get_world_patterns()):
        grid.retire_pattern_resources(pattern)
    grid.deposit_carcass(3, 0.6, 0)
    cell = grid.get_agent_position(3)
    (carcass,) = grid.cell_resources[cell].values()
    assert carcass.pattern == CARCASS_PATTERN
    colocated = [aid for aid in engine.agents if grid.get_agent_position(aid) == cell]
    act(monkeypatch, engine, {3: AgentAction(ActionType.INTERACT, carcass.resource_id)})
    spy = spied(engine)
    engine.step()
    assert spy.m2[0] == (len(colocated), 1)


# --- (e) Eventos del tick ----------------------------------------------------------------------


def test_eventos_con_nombres_de_ecology_tick_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg(enable_carcasses=True))
    set_energy(engine, 1, 2.0)
    set_energy(engine, 4, 1.2)
    set_energy(engine, 6, 0.3)
    set_energy(engine, 9, 0.0)
    act(monkeypatch, engine, {1: share(3), 4: attack(6), 5: attack(1)})
    spy = spied(engine)
    engine.step()
    (events,) = spy.events
    assert set(events) <= ECOLOGY_COUNTERS
    assert events["shares"] == 1 and events["attacks"] == 2
    assert all(count > 0 for count in events.values())


def test_sin_interacciones_no_hay_eventos(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimulationEngine(cfg())
    act(monkeypatch, engine)
    spy = spied(engine)
    engine.run(3)
    assert spy.events == [{}, {}, {}]
    assert spy.attacks == [{}, {}, {}]


# --- Conservación (D49.5): ninguna interacción crea energía --------------------------------------


@st.composite
def interaction_scenarios(draw: st.DrawFn) -> tuple[Any, ...]:
    n = 6
    energies = draw(st.lists(st.floats(-1.0, 3.0), min_size=n, max_size=n))
    kinds = draw(st.lists(st.sampled_from(["idle", "share", "attack"]), min_size=n, max_size=n))
    targets = draw(st.lists(st.integers(0, n), min_size=n, max_size=n))
    order = draw(st.permutations(list(range(n))))
    endospores = draw(st.lists(st.booleans(), min_size=n, max_size=n))
    params = {
        "share_fraction": draw(st.floats(0.0, 1.0)),
        "share_efficiency": draw(st.floats(0.0, 1.0)),
        "attack_power": draw(st.floats(0.0, 5.0)),
        "predation_efficiency": draw(st.floats(0.0, 1.0)),
    }
    return energies, kinds, targets, order, endospores, params


@given(interaction_scenarios())
def test_ninguna_interaccion_crea_energia(scenario: tuple[Any, ...]) -> None:
    energies, kinds, targets, order, endospores, params = scenario
    engine = SimulationEngine(cfg(num_agents=6, **params))
    ids = sorted(engine.agents)
    actions: dict[int, AgentAction] = {}
    for i, aid in enumerate(ids):
        set_energy(engine, aid, energies[i])
        engine.agents[aid].set_endospore(endospores[i])
        target = ids[targets[i]] if targets[i] < len(ids) else 999
        actions[aid] = {"idle": IDLE, "share": share(target), "attack": attack(target)}[kinds[i]]
    frame = TickFrame(0, order=[ids[i] for i in order], actions=actions)
    initial = {aid: agent.energy for aid, agent in engine.agents.items()}
    ExecutionSystem().run(engine, frame)
    after = sum(agent.energy for agent in engine.agents.values())
    assert after <= sum(initial.values()) + 1e-9
    # Las transferencias no tocan a nadie más que al par: los ociosos conservan su energía.
    for i, aid in enumerate(ids):
        untouched = kinds[i] == "idle" and all(
            not (kinds[j] != "idle" and targets[j] == i) for j in range(len(ids))
        )
        if untouched:
            assert engine.agents[aid].energy == initial[aid]
    # Una endospora que decidió atacar actúa como IDLE y no registra el intento (precisión 82).
    attempts = sum(1 for i in range(len(ids)) if kinds[i] == "attack" and not endospores[i])
    assert sum(frame.attacks.values()) == attempts


# --- Inercia de las reglas apagadas y determinismo ---------------------------------------------


def interacting_dna(config: SimulationConfig, aid: int) -> CompactDNA:
    """ADN fundador más impulsos de SHARE o ATTACK que superan a CONSUME (según la paridad)."""
    behavior = Behavior.ATTACK if aid % 2 == 0 else Behavior.SHARE
    target = BEHAVIOR_TARGETS[list(Behavior).index(behavior)]
    extra = (encode_codon(0x00, target, 0, 0, 127), encode_codon(0x00, target, 0, 0, 127))
    return CompactDNA(chromosome=founder_dna(config).chromosome + extra)


def interacting_digest(config: SimulationConfig, ticks: int = 40) -> Any:
    engine = SimulationEngine(config)
    for aid in sorted(engine.agents):
        engine.agents[aid].set_dna(interacting_dna(config, aid))
    engine.run(ticks)
    grid = grid_of(engine)
    ids = sorted(engine.agents)
    return (
        engine.history,
        [astuple(m) for m in engine.evolutionary_history],
        [grid.get_agent_position(a) for a in ids],
        [engine.agents[a].energy for a in ids],
        [engine.agents[a].memory.all_units() for a in ids],
        [g.bit_generator.state for g in (engine.rng, engine.null_rng, engine.evo_rng)],
        engine.donor_rng.bit_generator.state,
    )


def phase25(**overrides: Any) -> SimulationConfig:
    return replace(
        PHASE2_PROTOCOL_CONFIGS["002a"],
        enable_compact_dna=True,
        enable_genetic_policy=True,
        **overrides,
    )


def test_ablacion_de_r36_y_r37_deja_sus_parametros_inertes() -> None:
    off = phase25(enable_energy_transfer=False, enable_predation=False)
    tuned = replace(
        off, share_fraction=0.9, share_efficiency=0.1, attack_power=3.0, attack_cost=0.4
    )
    assert interacting_digest(off) == interacting_digest(tuned)


def test_r36_y_r37_activas_cambian_la_corrida() -> None:
    off = phase25(enable_energy_transfer=False, enable_predation=False)
    on = replace(off, enable_energy_transfer=True, enable_predation=True)
    assert interacting_digest(off) != interacting_digest(on)


@pytest.mark.parametrize("name", ["002a", "003a"])
def test_r36_y_r37_inertes_sin_politica_genetica(name: str) -> None:
    config = PHASE2_PROTOCOL_CONFIGS[name]
    flagged = replace(config, enable_energy_transfer=True, enable_predation=True, attack_cost=0.3)
    engine_a, engine_b = SimulationEngine(config), SimulationEngine(flagged)
    engine_a.run(40)
    engine_b.run(40)
    assert engine_a.history == engine_b.history
    assert engine_a.evolutionary_history == engine_b.evolutionary_history


def test_interacciones_independientes_del_hash() -> None:
    script = textwrap.dedent(
        """
        from dataclasses import replace
        from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
        from tests.test_interactions import interacting_dna
        from ide.simulation.engine import SimulationEngine

        config = replace(
            PHASE2_PROTOCOL_CONFIGS["003a"], enable_compact_dna=True,
            enable_genetic_policy=True, enable_energy_transfer=True, enable_predation=True,
            enable_carcasses=True, carcass_lifetime=6,
        )
        engine = SimulationEngine(config)
        for aid in sorted(engine.agents):
            engine.agents[aid].set_dna(interacting_dna(config, aid))
        frames = []
        class Spy:
            def on_decisions(self, engine, frame):
                pass
            def on_tick_end(self, engine, frame):
                frames.append((sorted(frame.events.items()), sorted(frame.attacks.items())))
        engine.observers.append(Spy())
        engine.run(30)
        print(frames)
        print(engine.history)
        print(engine.evolutionary_history)
        print(sorted(engine.root_nodes), sorted(engine.agents))
        print([engine.agents[a].energy for a in sorted(engine.agents)])
        print([engine.agents[a].memory.all_units() for a in sorted(engine.agents)])
        print(engine.env.get_resource_count(), engine.rng.bit_generator.state)
        print(engine.evo_rng.bit_generator.state, engine.donor_rng.bit_generator.state)
        """
    )
    outputs = []
    for hash_seed in ("0", "123"):
        # El `src` de este árbol primero: la instalación editable puede apuntar a otro.
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
    # La corrida tiene interacciones de verdad: no es una igualdad trivial.
    assert "'attacks'" in outputs[0] and "'shares'" in outputs[0]


@pytest.mark.parametrize("target", [None, True, (1, 0), "3"])
def test_objetivo_que_no_es_un_agent_id(target: object) -> None:
    """Un objetivo que no es un `agent_id` entero no recibe ni pierde energía."""
    engine = SimulationEngine(cfg())
    set_energy(engine, 1, 2.0)
    before = {aid: agent.energy for aid, agent in engine.agents.items()}
    actions = {aid: IDLE for aid in engine.agents}
    actions[1] = AgentAction(ActionType.SHARE, target)
    actions[4] = AgentAction(ActionType.ATTACK, target)
    frame = TickFrame(0, order=sorted(engine.agents), actions=actions)
    ExecutionSystem().run(engine, frame)
    assert {aid: agent.energy for aid, agent in engine.agents.items()} == before
    assert dict(frame.events) == {"attacks": 1} and frame.attacks == {4: 1}
