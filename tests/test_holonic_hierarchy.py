"""Tests de `holonic-hierarchy`: AgentNode, CompositeAgent y operadores R15-R18 (D23-D26)."""

from collections.abc import Callable, Iterator
from dataclasses import replace
from itertools import count

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ide.agent.evolution import genome_from_config
from ide.agent.holon import (
    AgentNode,
    CompositeAgent,
    apply_downward_causation,
    assign_epigenetic_roles,
    evaluate_bond_candidates,
    prune_dead_leaves,
    reproduce_holon,
    should_lock_holon,
    should_split_holon,
)
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig, epigenetic_roles_active, symbiotic_ratchet_active
from ide.domain.types import EpigeneticRole, KnowledgeUnit, Pattern

CFG = SimulationConfig()


def pat(i: int) -> Pattern:
    return Pattern((("id", f"p_{i}"),))


def ku(i: int, conf: float = 0.9, tau: int = 0, value: float = 1.0) -> KnowledgeUnit:
    return KnowledgeUnit(pat(i), value, conf, 1, tau, True)


def leaf(
    aid: int,
    *units: KnowledgeUnit,
    capacity: int = 3,
    bond: float = 0.6,
    energy: float = 1.5,
) -> MicroAgent:
    genome = replace(genome_from_config(CFG), memory_capacity=capacity, bond_affinity=bond)
    agent = MicroAgent.from_lineage(aid, CFG, genome, energy, 0, None)
    for unit in units:
        agent.memory.upsert(unit, unit.last_updated_tick)
    return agent


def holon(node_id: int, *children: AgentNode, tick: int = 0) -> CompositeAgent:
    return CompositeAgent(node_id, children, tick, True)


def ids(node: AgentNode) -> list[int]:
    return [a.agent_id for a in node.leaf_agents]


def rng(seed: int = 0) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))


# --- (a) Protocolo AgentNode y composición recursiva ------------------------------------------


def test_composicion_multinivel_arbitraria() -> None:
    a = [leaf(i) for i in range(6)]
    h1, h2 = holon(-2, a[0], a[1]), holon(-3, a[2], a[3])
    s1 = holon(-4, h1, h2)
    m1 = holon(-5, s1, a[4])
    top = holon(-6, m1, a[5])
    assert [n.holon_level for n in (a[0], h1, s1, m1, top)] == [0, 1, 2, 3, 4]
    assert len(m1.leaf_agents) == 5
    assert all(isinstance(n, AgentNode) for n in (*a, h1, h2, s1, m1, top))


def test_hojas_ordenadas_por_agent_id_y_propiedades_agregadas() -> None:
    a3 = leaf(3, capacity=2, bond=0.2, energy=1.0)
    a1 = leaf(1, capacity=4, bond=0.4, energy=2.0)
    a7 = leaf(7, capacity=3, bond=0.9, energy=0.5)
    u = holon(-2, holon(-3, a7, a3), a1)
    assert ids(u) == [1, 3, 7]
    assert u.children[0].node_id == -3 and u.children[1] is a1
    assert u.effective_capacity == 9
    assert u.total_energy == pytest.approx(3.5, abs=1e-9)
    assert u.mean_bond_affinity == pytest.approx(0.5, abs=1e-9)


def test_estado_inicial_del_holon() -> None:
    u = CompositeAgent(-2, (leaf(0), leaf(1)), 17, False)
    assert u.node_id == -2
    assert (u.created_tick, u.formation_tick) == (17, 17)
    assert (u.ticks_without_surplus, u.cooperative_completions) == (0, 0)
    assert u.formed_by_bond is False
    assert u.formation_knowledge == ()


# --- (b) Holones degenerados -------------------------------------------------------------------


def test_rechazo_de_holon_con_menos_de_dos_hijos() -> None:
    with pytest.raises(ValueError):
        CompositeAgent(-2, (leaf(0),), 0, True)
    with pytest.raises(ValueError):
        CompositeAgent(-2, (), 0, True)


def test_rechazo_de_hojas_duplicadas() -> None:
    a0, a1, a2 = leaf(0), leaf(1), leaf(2)
    with pytest.raises(ValueError):
        holon(-3, holon(-2, a0, a1), holon(-4, a1, a2))
    with pytest.raises(ValueError):
        holon(-2, a0, a0)


def test_reasignar_hijos_valida_y_recalcula() -> None:
    a = [leaf(i) for i in range(3)]
    u = holon(-2, holon(-3, a[0], a[1]), a[2])
    assert u.holon_level == 2
    u.children = (a[1], a[2])
    assert (u.holon_level, ids(u)) == (1, [1, 2])
    with pytest.raises(ValueError):
        u.children = (a[2],)


# --- (c) Memoria colectiva ---------------------------------------------------------------------


def test_superacion_holonica_de_la_barrera_de_capacidad_individual() -> None:
    leaves = [leaf(j, *(ku(3 * j + i) for i in range(3))) for j in range(3)]
    u = holon(-2, *leaves)
    assert all(len(lf.memory) == 3 for lf in leaves)
    assert len(u.collective_memory()) == 9
    assert list(u.collective_memory()) == sorted(u.collective_memory())


def test_memoria_colectiva_con_desempate_determinista() -> None:
    a1 = leaf(1, ku(0, conf=0.5), ku(1, conf=0.7, tau=3), ku(2, conf=0.6, tau=2))
    a2 = leaf(2, ku(0, conf=0.8), ku(1, conf=0.7, tau=5), ku(2, conf=0.6, tau=2, value=-1.0))
    u = holon(-2, a2, a1)
    memory = u.collective_memory()
    assert memory[pat(0)] == a2.memory.get(pat(0))  # mayor confianza
    assert memory[pat(1)] == a2.memory.get(pat(1))  # empate: mayor τ
    assert memory[pat(2)] == a1.memory.get(pat(2))  # empate total: menor agent_id


def test_memoria_colectiva_restringida_a_hojas_permitidas() -> None:
    a1, a2, a3 = leaf(1, ku(0)), leaf(2, ku(1)), leaf(3, ku(2))
    u = holon(-2, holon(-3, a1, a2), a3)
    assert sorted(u.collective_memory({1, 3})) == [pat(0), pat(2)]
    assert u.collective_memory(set()) == {}


# --- (d) BOND (R15) ----------------------------------------------------------------------------


def test_fusion_entre_especialistas_complementarios() -> None:
    cfg = replace(CFG, holon_bond_threshold=0.5)
    a, b = leaf(1, ku(0), ku(1), bond=0.8), leaf(2, ku(2), bond=0.8)
    assert evaluate_bond_candidates([a, b], [(1, 2)], cfg) == [(1, 2)]


def test_rechazo_de_fusion_entre_clones_redundantes() -> None:
    cfg = replace(CFG, holon_bond_threshold=0.3)
    a, b = leaf(1, ku(0), ku(1), bond=1.0), leaf(2, ku(0), ku(1), bond=1.0)
    assert evaluate_bond_candidates([a, b], [(1, 2)], cfg) == []


def test_bond_solo_entre_pares_adyacentes() -> None:
    a, b = leaf(1, ku(0), bond=1.0), leaf(2, ku(1), bond=1.0)
    assert evaluate_bond_candidates([a, b], [], CFG) == []


def test_bond_normaliza_y_deduplica_los_pares() -> None:
    a, b = leaf(1, ku(0), bond=1.0), leaf(2, ku(1), bond=1.0)
    assert evaluate_bond_candidates([a, b], [(2, 1), (1, 2), (1, 1)], CFG) == [(1, 2)]


def test_bond_respeta_el_maximo_de_hojas() -> None:
    cfg = replace(CFG, max_holon_leaves=2)
    u = holon(-2, leaf(1, ku(0), bond=1.0), leaf(2, ku(1), bond=1.0))
    c = leaf(3, ku(2), bond=1.0)
    assert evaluate_bond_candidates([u, c], [(-2, 3)], cfg) == []
    assert evaluate_bond_candidates([u, c], [(-2, 3)], replace(cfg, max_holon_leaves=3)) == [
        (-2, 3)
    ]


def test_bond_solo_cuenta_creencias_confiables() -> None:
    # p_1 bajo el umbral de decisión: los conjuntos válidos son {p_0} y {p_0}, clones.
    a = leaf(1, ku(0), ku(1, conf=0.2), bond=1.0)
    b = leaf(2, ku(0), bond=1.0)
    assert evaluate_bond_candidates([a, b], [(1, 2)], replace(CFG, holon_bond_threshold=0.1)) == []


def test_bond_pondera_por_la_media_de_las_afinidades_de_los_nodos() -> None:
    # ω̄(U) = 0.3, ω̄(c) = 0.9: score = 1.0 · 0.6 (la media por hojas daría 0.5).
    # Los umbrales dejan margen para no depender del redondeo.
    u = holon(-2, leaf(1, ku(0), bond=0.2), leaf(2, ku(0), bond=0.4))
    c = leaf(3, ku(1), bond=0.9)
    assert evaluate_bond_candidates([u, c], [(-2, 3)], replace(CFG, holon_bond_threshold=0.55)) == [
        (-2, 3)
    ]
    assert (
        evaluate_bond_candidates([u, c], [(-2, 3)], replace(CFG, holon_bond_threshold=0.65)) == []
    )


def test_bond_emparejamiento_codicioso_sin_solapamiento() -> None:
    # score(1,2) = 1.0, score(2,3) = 1.0, score(1,3) = 0.5, score(3,4) = 1.0.
    a1 = leaf(1, ku(0), bond=1.0)
    a2 = leaf(2, ku(1), bond=1.0)
    a3 = leaf(3, ku(0), ku(2), bond=1.0)
    a4 = leaf(4, ku(5), bond=1.0)
    pairs = [(2, 3), (1, 3), (1, 2), (3, 4)]
    assert evaluate_bond_candidates([a1, a2, a3, a4], pairs, CFG) == [(1, 2), (3, 4)]


# --- (e) SPLIT (R16) ---------------------------------------------------------------------------


def test_fision_por_paciencia_agotada() -> None:
    u = holon(-2, leaf(1), leaf(2))
    u.ticks_without_surplus = CFG.holon_split_patience - 1
    assert should_split_holon(u, CFG) is False
    u.ticks_without_surplus = CFG.holon_split_patience
    assert should_split_holon(u, CFG) is True


def test_fision_por_energia_minima() -> None:
    cfg = replace(CFG, holon_min_energy_per_leaf=0.5)
    assert should_split_holon(holon(-2, leaf(1, energy=0.6), leaf(2, energy=0.5)), cfg) is False
    assert should_split_holon(holon(-2, leaf(1, energy=0.6), leaf(2, energy=0.3)), cfg) is True


def test_sin_fision_si_esta_deshabilitada() -> None:
    u = holon(-2, leaf(1, energy=0.0), leaf(2, energy=0.0))
    u.ticks_without_surplus = 10**6
    assert should_split_holon(u, replace(CFG, enable_holon_splitting=False)) is False


# --- (f) Causalidad descendente (R18) ---------------------------------------------------------

R18 = replace(CFG, enable_downward_causation=True, redundancy_penalty=0.2)


def test_desalojo_preferente_de_creencia_redundante_dentro_del_holon() -> None:
    a1 = leaf(1, ku(0, conf=0.9))
    a2 = leaf(2, ku(0, conf=0.9), ku(1, conf=0.5), capacity=2)
    u = holon(-2, a1, a2)
    assert len(u.collective_memory()) == 2
    apply_downward_causation(u, {1: [1, 2], 2: [1, 2]}, R18)
    assert a2.memory.compute_utility(ku(0, conf=0.9), 0) == pytest.approx(0.18, abs=1e-9)
    assert a1.memory.compute_utility(ku(0, conf=0.9), 0) == pytest.approx(0.9, abs=1e-9)
    a2.memory.upsert(ku(2, conf=0.6), 0)
    assert sorted(lf.pattern for lf in a2.memory.all_units()) == [pat(1), pat(2)]
    assert len(u.collective_memory()) == 3


def test_causalidad_descendente_de_alcance_local() -> None:
    a1 = leaf(1, ku(0, conf=0.9))
    a2 = leaf(2, ku(0, conf=0.5))
    a3 = leaf(3, ku(0, conf=0.5))
    u = holon(-2, holon(-3, a1, a2), a3)
    apply_downward_causation(u, {1: [1, 2], 2: [1, 2], 3: [3]}, R18)
    utilities = [lf.memory.compute_utility(ku(0, conf=0.5), 0) for lf in (a1, a2, a3)]
    assert utilities == [
        pytest.approx(0.5, abs=1e-9),
        pytest.approx(0.1, abs=1e-9),
        pytest.approx(0.5, abs=1e-9),  # fuera del alcance de la titular: no es redundante
    ]


def test_causalidad_descendente_empate_conserva_la_hoja_de_menor_id() -> None:
    a4, a9 = leaf(4, ku(0, conf=0.7)), leaf(9, ku(0, conf=0.7))
    apply_downward_causation(holon(-2, a9, a4), {4: [4, 9], 9: [4, 9]}, R18)
    assert a4.memory.compute_utility(ku(0), 0) == pytest.approx(0.9, abs=1e-9)
    assert a9.memory.compute_utility(ku(0), 0) == pytest.approx(0.18, abs=1e-9)


def test_causalidad_descendente_incluye_siempre_a_la_propia_hoja() -> None:
    a1, a2 = leaf(1, ku(0, conf=0.9)), leaf(2, ku(0, conf=0.5))
    apply_downward_causation(holon(-2, a1, a2), {1: [2], 2: [1]}, R18)
    assert a1.memory.compute_utility(ku(0), 0) == pytest.approx(0.9, abs=1e-9)
    assert a2.memory.compute_utility(ku(0), 0) == pytest.approx(0.18, abs=1e-9)


def test_causalidad_descendente_valida_el_alcance_local() -> None:
    u = holon(-2, leaf(1, ku(0)), leaf(2, ku(0, conf=0.5)))
    with pytest.raises(ValueError, match="local_reach"):
        apply_downward_causation(u, {1: [1, 2]}, R18)  # falta la hoja 2
    with pytest.raises(ValueError, match="local_reach"):
        apply_downward_causation(u, {1: [1, 2], 2: [2, 7]}, R18)  # 7 no es hoja del holón
    with pytest.raises(ValueError, match="local_reach"):
        apply_downward_causation(u, {1: [1], 2: [2], 99: [1]}, R18)  # clave sobrante
    with pytest.raises(ValueError, match="local_reach"):  # también con la regla apagada
        apply_downward_causation(u, {1: [1, 2]}, replace(R18, enable_downward_causation=False))


def test_causalidad_descendente_apagada_limpia_la_penalizacion() -> None:
    a1, a2 = leaf(1, ku(0, conf=0.9)), leaf(2, ku(0, conf=0.5))
    u = holon(-2, a1, a2)
    reach = {1: [1, 2], 2: [1, 2]}
    apply_downward_causation(u, reach, R18)
    apply_downward_causation(u, reach, replace(R18, enable_downward_causation=False))
    assert a2.memory.compute_utility(ku(0), 0) == pytest.approx(0.9, abs=1e-9)


# --- (g) Reproducción del holón (R17) ---------------------------------------------------------


def node_ids_from(start: int) -> Callable[[], int]:
    counter: Iterator[int] = count(start, -1)
    return lambda: next(counter)


def shape(node: AgentNode) -> object:
    if isinstance(node, CompositeAgent):
        return tuple(shape(c) for c in node.children)
    return "hoja"


def test_reproduccion_de_un_holon_preservando_su_topologia() -> None:
    cfg = replace(CFG, mutation_rate=0.0, discrete_mutation_prob=0.0)
    parents = [
        MicroAgent.from_lineage(i, cfg, genome_from_config(cfg), 2.5, 0, None) for i in (1, 2, 3)
    ]
    u = CompositeAgent(
        -2, (CompositeAgent(-3, (parents[2], parents[0]), 4, True), parents[1]), 9, True
    )
    generator = rng()
    offspring = {p.agent_id: p.create_offspring(10 + p.agent_id, 30, generator) for p in parents}
    child = reproduce_holon(u, offspring, node_ids_from(-20), 30)
    assert shape(child) == shape(u) == (("hoja", "hoja"), "hoja")
    assert child.holon_level == 2
    assert ids(child) == [11, 12, 13]
    assert all(lf.parent_id == lf.agent_id - 10 for lf in child.leaf_agents)
    inner = child.children[0]
    assert isinstance(inner, CompositeAgent)
    assert (child.node_id, inner.node_id) == (-20, -21)
    assert [lf.agent_id for lf in inner.children if isinstance(lf, MicroAgent)] == [13, 11]
    for node in (child, inner):
        assert node.formed_by_bond is False
        assert (node.created_tick, node.formation_tick) == (30, 30)
        assert node.formation_knowledge == ()
    assert ids(u) == [1, 2, 3]  # el holón parental no cambia


def test_reproduccion_exige_un_hijo_por_hoja_antes_de_pedir_ids() -> None:
    u = holon(-2, leaf(1), leaf(2))
    requested: list[int] = []

    def source() -> int:
        requested.append(-5)
        return -5

    with pytest.raises(ValueError, match="offspring"):
        reproduce_holon(u, {1: leaf(11)}, source, 0)
    with pytest.raises(ValueError, match="offspring"):
        reproduce_holon(u, {1: leaf(11), 2: leaf(11)}, source, 0)
    with pytest.raises(ValueError, match="offspring"):
        reproduce_holon(u, {1: leaf(2), 2: leaf(11)}, source, 0)  # hija = hoja parental
    assert requested == []


# --- (h) Poda recursiva de hojas muertas ------------------------------------------------------


def test_colapso_parcial_de_un_sub_holon_en_un_arbol_de_nivel_2() -> None:
    a1, a2, a3, a4 = (leaf(i) for i in (1, 2, 3, 4))
    h2 = holon(-3, a3, a4)
    s = holon(-4, holon(-2, a1, a2), h2)
    assert prune_dead_leaves(s, {2, 3, 4}) is s
    assert s.children == (a2, h2)
    assert len(s.leaf_agents) == 3
    assert s.holon_level == 2


def test_poda_de_un_sub_holon_entero() -> None:
    a = [leaf(i) for i in range(5)]
    s = holon(-4, holon(-2, a[0], a[1]), holon(-3, a[2], a[3]), a[4])
    assert prune_dead_leaves(s, {2, 3, 4}) is s
    assert ids(s) == [2, 3, 4]
    assert s.holon_level == 1 + 1


def test_poda_colapsa_al_unico_sobreviviente() -> None:
    a1, a2, a3 = leaf(1), leaf(2), leaf(3)
    s = holon(-3, holon(-2, a1, a2), a3)
    assert prune_dead_leaves(s, {2}) is a2


def test_poda_sin_sobrevivientes_devuelve_none() -> None:
    s = holon(-3, holon(-2, leaf(1), leaf(2)), leaf(3))
    assert prune_dead_leaves(s, {7}) is None


def test_poda_de_una_hoja_suelta() -> None:
    a = leaf(5)
    assert prune_dead_leaves(a, {5}) is a
    assert prune_dead_leaves(a, set()) is None


# --- Propiedades (Hypothesis) ------------------------------------------------------------------

# Un árbol es una hoja (su agent_id) o una lista de >= 2 subárboles.
_trees = st.recursive(
    st.just(None),
    lambda children: st.lists(children, min_size=2, max_size=3),
    max_leaves=10,
)


def build(tree: object, next_leaf: Iterator[int], next_node: Iterator[int]) -> AgentNode:
    if isinstance(tree, list):
        node_id = next(next_node)
        children = tuple(build(child, next_leaf, next_node) for child in tree)  # type: ignore[misc]
        return CompositeAgent(node_id, children, 0, True)
    aid = next(next_leaf)
    return leaf(aid, ku(aid % 4, conf=0.3 + 0.05 * aid, tau=aid % 3), capacity=1 + aid % 3)


def all_composites(node: AgentNode) -> list[CompositeAgent]:
    if not isinstance(node, CompositeAgent):
        return []
    return [node, *(c for child in node.children for c in all_composites(child))]


def depth(node: AgentNode) -> int:
    if not isinstance(node, CompositeAgent):
        return 0
    return 1 + max(depth(child) for child in node.children)


@given(_trees, st.permutations(range(10)))
def test_propiedad_invariantes_del_arbol(tree: object, order: list[int]) -> None:
    root = build(tree, iter(order), count(-2, -1))
    leaves = root.leaf_agents
    assert [a.agent_id for a in leaves] == sorted({a.agent_id for a in leaves})
    assert root.holon_level == depth(root)
    assert root.effective_capacity == sum(a.memory.capacity for a in leaves)
    memory = root.collective_memory()
    assert set(memory) == {u.pattern for a in leaves for u in a.memory.all_units()}
    for pattern, unit in memory.items():
        holders = [(a.memory.get(pattern), a.agent_id) for a in leaves if pattern in a.memory]
        best = max(holders, key=lambda h: (h[0].confidence, h[0].last_updated_tick, -h[1]))  # type: ignore[union-attr]
        assert unit == best[0]


@given(_trees, st.permutations(range(10)), st.sets(st.integers(0, 9)))
def test_propiedad_poda(tree: object, order: list[int], alive: set[int]) -> None:
    root = build(tree, iter(order), count(-2, -1))
    before = {a.agent_id for a in root.leaf_agents}
    pruned = prune_dead_leaves(root, alive)
    survivors = before & alive
    if not survivors:
        assert pruned is None
        return
    assert pruned is not None
    assert {a.agent_id for a in pruned.leaf_agents} == survivors
    if len(survivors) == 1:
        assert isinstance(pruned, MicroAgent)
    for node in all_composites(pruned):
        assert len(node.children) >= 2


def shape_with_leaves(node: AgentNode) -> object:
    if isinstance(node, CompositeAgent):
        return tuple(shape_with_leaves(c) for c in node.children)
    return node.node_id


@given(_trees, st.permutations(range(10)))
def test_propiedad_reproduccion_replica_la_forma(tree: object, order: list[int]) -> None:
    root = build(tree, iter(order), count(-2, -1))
    if not isinstance(root, CompositeAgent):
        return
    offspring = {a.agent_id: leaf(100 + a.agent_id) for a in root.leaf_agents}
    child = reproduce_holon(root, offspring, node_ids_from(-50), 7)

    def relabel(shape: object) -> object:
        return tuple(relabel(s) for s in shape) if isinstance(shape, tuple) else 100 + shape  # type: ignore[operator]

    assert shape_with_leaves(child) == relabel(shape_with_leaves(root))
    composites = all_composites(child)
    assert [n.node_id for n in composites] == list(range(-50, -50 - len(composites), -1))
    assert all(not n.formed_by_bond and n.formation_tick == 7 for n in composites)


# --- Fase II-B: señal posicional (R25, design D36 y D50.1) ------------------------------------

ROLES = SimulationConfig(
    enable_evolution=True,
    enable_compact_dna=True,
    enable_holonic_hierarchy=True,
    enable_epigenetic_roles=True,
)
NONE, EXPLORER, LIBRARIAN, NERVE = (
    EpigeneticRole.NONE,
    EpigeneticRole.EXPLORER,
    EpigeneticRole.LIBRARIAN,
    EpigeneticRole.NERVE,
)


def full_reach(*aids: int) -> dict[int, list[int]]:
    return {aid: list(aids) for aid in aids}


def test_condicion_efectiva_de_r25() -> None:
    assert epigenetic_roles_active(ROLES)
    assert not epigenetic_roles_active(SimulationConfig())
    for flag in ("enable_compact_dna", "enable_holonic_hierarchy", "enable_epigenetic_roles"):
        assert not epigenetic_roles_active(replace(ROLES, **{flag: False}))


@pytest.mark.parametrize(
    "overrides", [{"enable_compact_dna": False}, {"enable_epigenetic_roles": False}]
)
def test_roles_con_la_regla_apagada(overrides: dict[str, bool]) -> None:
    u = holon(-2, leaf(1, ku(0)), leaf(2, ku(1)), leaf(3, ku(2)))
    roles = assign_epigenetic_roles(u, full_reach(1, 2, 3), replace(ROLES, **overrides))
    assert roles == {1: NONE, 2: NONE, 3: NONE}


def test_roles_validan_el_alcance_local_aun_con_la_regla_apagada() -> None:
    u = holon(-2, leaf(1, ku(0)), leaf(2, ku(1)))
    off = replace(ROLES, enable_epigenetic_roles=False)
    for config in (ROLES, off):
        with pytest.raises(ValueError, match="local_reach"):
            assign_epigenetic_roles(u, {1: [1, 2]}, config)  # falta la hoja 2
        with pytest.raises(ValueError, match="local_reach"):
            assign_epigenetic_roles(u, {1: [1], 2: [2, 7]}, config)  # 7 no es hoja del holón


def test_librarian_desempata_por_conocimiento_total_y_por_identificador() -> None:
    # unique(1) = 1, unique(2) = unique(3) = 2 y |K(2)| = |K(3)| = 4: gana la hoja 2.
    a1 = leaf(1, ku(0), ku(30), capacity=5)
    a2 = leaf(2, ku(0), ku(1), ku(10), ku(11), capacity=5)
    a3 = leaf(3, ku(0), ku(1), ku(20), ku(21), capacity=5)
    roles = assign_epigenetic_roles(holon(-2, a1, a2, a3), full_reach(1, 2, 3), ROLES)
    assert roles[2] is LIBRARIAN


def test_librarian_prefiere_mas_conocimiento_unico() -> None:
    a1 = leaf(1, ku(0), ku(1), ku(2), capacity=5)  # unique 1, |K| 3
    a2 = leaf(2, ku(1), ku(2), capacity=5)  # unique 0
    a3 = leaf(3, ku(5), ku(6), capacity=5)  # unique 2, |K| 2
    roles = assign_epigenetic_roles(holon(-2, a1, a2, a3), full_reach(1, 2, 3), ROLES)
    assert roles[3] is LIBRARIAN


def test_k_solo_cuenta_creencias_sobre_el_umbral_de_decision() -> None:
    low = ROLES.decision_conf_threshold - 0.01
    a1 = leaf(1, ku(0, conf=low), ku(1, conf=low), ku(2, conf=low), capacity=5)
    a2 = leaf(2, ku(5), capacity=5)
    roles = assign_epigenetic_roles(holon(-2, a1, a2), full_reach(1, 2), ROLES)
    assert roles == {1: EXPLORER, 2: LIBRARIAN}


def test_explorer_y_nerve_por_grado_interno() -> None:
    a1 = leaf(1, ku(0))  # único con conocimiento propio: LIBRARIAN
    others = [leaf(aid) for aid in (2, 3, 4)]
    reach = {1: [3], 2: [3], 3: [1, 2, 4], 4: [3]}  # grados de 2, 3 y 4: 1, 3 y 1
    roles = assign_epigenetic_roles(holon(-2, a1, *others), reach, ROLES)
    assert roles == {1: LIBRARIAN, 2: EXPLORER, 3: NERVE, 4: NONE}


def test_el_grado_no_cuenta_a_la_propia_hoja() -> None:
    a1 = leaf(1, ku(0))
    # La hoja 2 se lista a sí misma: su grado sigue siendo 1, igual que el de la hoja 3.
    reach = {1: [2, 3], 2: [1, 2], 3: [1]}
    roles = assign_epigenetic_roles(holon(-2, a1, leaf(2), leaf(3)), reach, ROLES)
    assert roles == {1: LIBRARIAN, 2: EXPLORER, 3: NERVE}


def test_holon_de_dos_hojas_sin_nerve() -> None:
    roles = assign_epigenetic_roles(holon(-2, leaf(5), leaf(9)), full_reach(5, 9), ROLES)
    assert sorted(roles.values(), key=lambda r: r.value) == [EXPLORER, LIBRARIAN]
    assert NERVE not in roles.values()


def test_asignacion_pura_sin_escribir_roles() -> None:
    a1, a2 = leaf(1, ku(0)), leaf(2)
    roles = assign_epigenetic_roles(holon(-2, a1, a2), full_reach(1, 2), ROLES)
    assert roles == {1: LIBRARIAN, 2: EXPLORER}
    assert a1.epigenetic_role is NONE and a2.epigenetic_role is NONE


@given(_trees, st.permutations(range(10)), st.data())
def test_propiedad_una_casta_de_cada_tipo(
    tree: object, order: list[int], data: st.DataObject
) -> None:
    root = build(tree, iter(order), count(-2, -1))
    if not isinstance(root, CompositeAgent):
        return
    aids = [a.agent_id for a in root.leaf_agents]
    reach = {aid: data.draw(st.lists(st.sampled_from(aids), max_size=4)) for aid in aids}
    roles = assign_epigenetic_roles(root, reach, ROLES)
    assert list(roles) == aids
    values = list(roles.values())
    assert values.count(LIBRARIAN) == 1 and values.count(EXPLORER) == 1
    assert values.count(NERVE) == (1 if len(aids) >= 3 else 0)
    shuffled = {aid: list(reversed(reach[aid])) for aid in reversed(aids)}
    assert assign_epigenetic_roles(root, shuffled, ROLES) == roles


# --- Fase II-B: compromiso simbiótico (R31, design D40 y D50.3) -------------------------------

RATCHET = SimulationConfig(
    enable_evolution=True,
    enable_compact_dna=True,
    enable_holonic_hierarchy=True,
    enable_symbiotic_ratchet=True,
    lock_coord_discount=0.5,
)


def committed(aid: int, commitment: float, energy: float = 1.5) -> MicroAgent:
    """Hoja sin ADN que expresa `commitment` como base de su configuración (D46.7)."""
    config = replace(CFG, symbiotic_commitment_base=commitment)
    agent = MicroAgent.from_lineage(aid, config, genome_from_config(config), energy, 0, None)
    assert agent.phenotype.symbiotic_commitment == commitment
    return agent


def test_condicion_efectiva_de_r31() -> None:
    assert symbiotic_ratchet_active(RATCHET)
    assert not symbiotic_ratchet_active(SimulationConfig())
    for flag in ("enable_compact_dna", "enable_holonic_hierarchy", "enable_symbiotic_ratchet"):
        assert not symbiotic_ratchet_active(replace(RATCHET, **{flag: False}))


def test_holon_nace_sin_soldar() -> None:
    assert holon(-2, leaf(1), leaf(2)).is_locked is False


def test_sello_por_compromiso_medio() -> None:
    assert should_lock_holon(holon(-2, committed(1, 0.25), committed(2, 0.75)), RATCHET)
    assert not should_lock_holon(holon(-2, committed(1, 0.25), committed(2, 0.5)), RATCHET)


def test_sello_promedia_todas_las_hojas_del_arbol() -> None:
    inner = holon(-3, committed(2, 0.9), committed(3, 0.9))
    assert should_lock_holon(holon(-2, committed(1, 0.0), inner), RATCHET)  # media 0.6
    inner = holon(-3, committed(2, 0.6), committed(3, 0.6))
    assert not should_lock_holon(holon(-2, committed(1, 0.0), inner), RATCHET)  # media 0.4


def test_sin_sello_con_r31_inerte() -> None:
    u = holon(-2, committed(1, 0.8), committed(2, 0.8))
    for flag in ("enable_compact_dna", "enable_holonic_hierarchy", "enable_symbiotic_ratchet"):
        assert not should_lock_holon(u, replace(RATCHET, **{flag: False}))


def test_un_holon_ya_soldado_no_se_vuelve_a_sellar() -> None:
    u = holon(-2, committed(1, 0.8), committed(2, 0.8))
    u.is_locked = True
    assert not should_lock_holon(u, RATCHET)  # el sello es permanente: no hay nada que decidir
    assert u.is_locked


def test_holon_soldado_deficitario_no_se_parte() -> None:
    cfg = replace(RATCHET, holon_min_energy_per_leaf=1.0)
    u = holon(-2, leaf(1, energy=0.0), leaf(2, energy=0.0), leaf(3, energy=0.0))
    u.ticks_without_surplus = cfg.holon_split_patience
    assert should_split_holon(u, cfg) is True
    u.is_locked = True
    assert should_split_holon(u, cfg) is False
    # Con R31 inerte el sello no tiene efecto (D30.3, precisión 32).
    assert should_split_holon(u, replace(cfg, enable_compact_dna=False)) is True
    assert should_split_holon(u, replace(cfg, enable_symbiotic_ratchet=False)) is True


def test_poda_de_un_holon_soldado() -> None:
    a1, a2, a3 = leaf(1), leaf(2), leaf(3)
    u = holon(-2, a1, a2, a3)
    u.is_locked = True
    pruned = prune_dead_leaves(u, {1, 2})
    assert pruned is u and u.is_locked and ids(u) == [1, 2]
    assert prune_dead_leaves(u, {1}) is a1  # colapsa como en la Fase II


def test_sello_conservado_al_quedar_expuesto_como_raiz() -> None:
    inner = holon(-3, leaf(1), leaf(2))
    inner.is_locked = True
    outer = holon(-4, inner, leaf(3))
    assert outer.is_locked is False
    assert outer.children[0] is inner and inner.is_locked  # tras un SPLIT de `outer`
