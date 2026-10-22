"""Jerarquía holónica recursiva sin límite de niveles (Exp 003 v2, design D23 a D26).

Patrón *Composite*: un `MicroAgent` es el nodo de nivel 0 y un `CompositeAgent` agrupa dos o
más nodos de cualquier nivel. Ninguna función recibe el entorno: las distancias y los pares
adyacentes llegan ya calculados por el motor. El motor decide también cuándo invocar BOND
(`enable_holonic_hierarchy`) y R17 (`enable_holon_reproduction`); `should_split_holon` y
`apply_downward_causation` respetan su propia bandera porque la decisión es parte de la regla.

Fase II-B: `assign_epigenetic_roles` ($R_{25}$, D36 y D50.1) calcula la señal posicional de las
hojas y `should_lock_holon` ($R_{31}$, D50.3) decide el sello por compromiso simbiótico; los dos
respetan su condición efectiva (`epigenetic_roles_active` y `symbiotic_ratchet_active`).
"""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Protocol, runtime_checkable

from ide.agent.epistemology import is_known
from ide.agent.micro_agent import MicroAgent
from ide.config import SimulationConfig, epigenetic_roles_active, symbiotic_ratchet_active
from ide.domain.extensions import compute_epistemic_synergy
from ide.domain.types import EpigeneticRole, KnowledgeUnit, Pattern

# Compromiso simbiótico expresado medio de las hojas a partir del cual un holón raíz se suelda
# (R31, D50.3).
LOCK_COMMITMENT_THRESHOLD = 0.5


@runtime_checkable
class AgentNode(Protocol):
    """Nodo del bosque holónico: un `MicroAgent` (L = 0) o un `CompositeAgent` (L >= 1)."""

    @property
    def node_id(self) -> int: ...
    @property
    def holon_level(self) -> int: ...
    @property
    def leaf_agents(self) -> tuple[MicroAgent, ...]: ...
    @property
    def effective_capacity(self) -> int: ...
    def collective_memory(self) -> dict[Pattern, KnowledgeUnit]: ...


def best_beliefs(
    beliefs_by_leaf: Mapping[int, Mapping[Pattern, KnowledgeUnit]],
) -> dict[Pattern, KnowledgeUnit]:
    """Por patrón, la creencia de máx (c, τ, -agent_id) entre las hojas dadas, por patrón.

    Es la regla de selección de la memoria colectiva (D23) y de la vista del holón (D25.2).
    """
    best: dict[Pattern, tuple[tuple[float, int, int], KnowledgeUnit]] = {}
    for agent_id, beliefs in beliefs_by_leaf.items():
        for pattern, unit in beliefs.items():
            key = (unit.confidence, unit.last_updated_tick, -agent_id)
            current = best.get(pattern)
            if current is None or key > current[0]:
                best[pattern] = (key, unit)
    return {pattern: best[pattern][1] for pattern in sorted(best)}


def _mean_bond_affinity(node: AgentNode) -> float:
    leaves = node.leaf_agents
    return sum(leaf.genome.bond_affinity for leaf in leaves) / len(leaves)


class CompositeAgent:
    """Holón de nivel L >= 1. Sus propiedades derivadas se recalculan desde `children`.

    `node_id` lo asigna el motor (negativo, D23). `formation_knowledge` lo completa el motor
    porque exige conocer la verdad del mundo; este módulo nunca lo calcula.
    """

    def __init__(
        self,
        node_id: int,
        children: tuple[AgentNode, ...],
        created_tick: int,
        formed_by_bond: bool,
    ) -> None:
        self.node_id = node_id
        self.children = children
        self.created_tick = created_tick
        self.formation_tick = created_tick
        self.ticks_without_surplus = 0
        self.cooperative_completions = 0
        self.formed_by_bond = formed_by_bond
        self.formation_knowledge: tuple[tuple[int, frozenset[Pattern]], ...] = ()
        # Sello de R31 (D40, D50.3): permanente; lo pone el motor con `should_lock_holon`.
        self.is_locked = False

    @property
    def children(self) -> tuple[AgentNode, ...]:
        return self._children

    @children.setter
    def children(self, children: tuple[AgentNode, ...]) -> None:
        if len(children) < 2:
            raise ValueError(f"un holón exige al menos 2 hijos, recibidos {len(children)}")
        leaf_ids = [leaf.agent_id for child in children for leaf in child.leaf_agents]
        if len(leaf_ids) != len(set(leaf_ids)):
            raise ValueError(f"hojas repetidas entre los hijos del holón: {sorted(leaf_ids)}")
        self._children = tuple(children)

    @property
    def holon_level(self) -> int:
        return 1 + max(child.holon_level for child in self._children)

    @property
    def leaf_agents(self) -> tuple[MicroAgent, ...]:
        leaves = (leaf for child in self._children for leaf in child.leaf_agents)
        return tuple(sorted(leaves, key=lambda leaf: leaf.agent_id))

    @property
    def effective_capacity(self) -> int:
        return sum(leaf.memory.capacity for leaf in self.leaf_agents)

    @property
    def total_energy(self) -> float:
        return sum(leaf.energy for leaf in self.leaf_agents)

    @property
    def mean_bond_affinity(self) -> float:
        return _mean_bond_affinity(self)

    def collective_memory(
        self, allowed_leaf_ids: set[int] | None = None
    ) -> dict[Pattern, KnowledgeUnit]:
        """Unión de las memorias de las hojas: por patrón, máx (c, τ, -agent_id)."""
        return best_beliefs(
            {
                leaf.agent_id: leaf.collective_memory()
                for leaf in self.leaf_agents
                if allowed_leaf_ids is None or leaf.agent_id in allowed_leaf_ids
            }
        )


def composite_nodes(node: AgentNode) -> list[CompositeAgent]:
    """Nodos compuestos del subárbol de `node` (incluido él), en preorden."""
    if not isinstance(node, CompositeAgent):
        return []
    return [node, *(c for child in node.children for c in composite_nodes(child))]


def prune_dead_leaves(node: AgentNode, alive_ids: set[int]) -> AgentNode | None:
    """Poda recursiva: un sub-holón con una sola hoja viva colapsa a ella; sin hojas, `None`.

    Modifica en el lugar los holones que sobreviven con dos o más hijos.
    """
    if not isinstance(node, CompositeAgent):
        return node if node.node_id in alive_ids else None
    surviving = [
        pruned
        for child in node.children
        if (pruned := prune_dead_leaves(child, alive_ids)) is not None
    ]
    if not surviving:
        return None
    if len(surviving) == 1:
        return surviving[0]
    node.children = tuple(surviving)
    return node


def evaluate_bond_candidates(
    roots: Sequence[AgentNode], adjacent_pairs: Sequence[tuple[int, int]], config: SimulationConfig
) -> list[tuple[int, int]]:
    """Pares de nodos raíz a fusionar por BOND (R15, D24.3), en orden de selección.

    `adjacent_pairs` son los pares de `node_id` con alguna hoja de cada nodo a distancia <= 1. Los
    candidatos con puntaje >= `holon_bond_threshold` se eligen por (-puntaje, a, b), sin que un
    nodo participe en dos fusiones del mismo tick.
    """
    by_id = {root.node_id: root for root in roots}
    known: dict[int, frozenset[Pattern]] = {}

    def valid_patterns(node_id: int) -> frozenset[Pattern]:
        if node_id not in known:
            memory = by_id[node_id].collective_memory()
            known[node_id] = frozenset(p for p, u in memory.items() if is_known(u, config))
        return known[node_id]

    candidates: list[tuple[float, int, int]] = []
    for a, b in sorted({(min(pair), max(pair)) for pair in adjacent_pairs if pair[0] != pair[1]}):
        node_a, node_b = by_id[a], by_id[b]
        if len(node_a.leaf_agents) + len(node_b.leaf_agents) > config.max_holon_leaves:
            continue
        affinity = (_mean_bond_affinity(node_a) + _mean_bond_affinity(node_b)) / 2
        score = compute_epistemic_synergy(valid_patterns(a), valid_patterns(b), affinity)
        if score >= config.holon_bond_threshold:
            candidates.append((-score, a, b))

    selected: list[tuple[int, int]] = []
    used: set[int] = set()
    for _, a, b in sorted(candidates):
        if a not in used and b not in used:
            selected.append((a, b))
            used.update((a, b))
    return selected


def should_split_holon(holon: CompositeAgent, config: SimulationConfig) -> bool:
    """SPLIT (R16, D24.2): paciencia sin superávit agotada o energía bajo el mínimo por hoja.

    Con $R_{31}$ efectivamente activa, un holón soldado nunca se parte (D40, D50.3).
    """
    if not config.enable_holon_splitting:
        return False
    if holon.is_locked and symbiotic_ratchet_active(config):
        return False
    starving = holon.total_energy < len(holon.leaf_agents) * config.holon_min_energy_per_leaf
    return holon.ticks_without_surplus >= config.holon_split_patience or starving


def should_lock_holon(holon: CompositeAgent, config: SimulationConfig) -> bool:
    """Sello de R31 (D50.3): el holón no soldado se suelda si sus hojas se comprometen.

    Devuelve `True` si y sólo si $R_{31}$ está efectivamente activa, el holón no está soldado y
    la media del `symbiotic_commitment` expresado de todas sus hojas es >= 0.5. El motor lo
    evalúa sólo sobre las raíces, en el paso de coordinación de la Fase 5 y antes de cobrar el
    costo y de evaluar `SPLIT` (precisión 19). No modifica el holón.
    """
    if holon.is_locked or not symbiotic_ratchet_active(config):
        return False
    leaves = holon.leaf_agents
    mean = sum(leaf.phenotype.symbiotic_commitment for leaf in leaves) / len(leaves)
    return mean >= LOCK_COMMITMENT_THRESHOLD


def _validated_reach(
    holon: CompositeAgent, local_reach: Mapping[int, Sequence[int]]
) -> dict[int, list[int]]:
    """Valida `local_reach` (contrato de D25.1) y devuelve, por hoja, sus cercanas con ella.

    Raises:
        ValueError: si `local_reach` no tiene exactamente una clave por hoja o da, para alguna
            hoja, agentes que no son hojas del holón.
    """
    leaf_ids = {leaf.agent_id for leaf in holon.leaf_agents}
    if set(local_reach.keys()) != leaf_ids:
        raise ValueError(
            f"local_reach debe tener exactamente una clave por hoja: {sorted(leaf_ids)}"
        )
    nearby_ids: dict[int, list[int]] = {}
    for aid in sorted(leaf_ids):
        if not set(local_reach[aid]) <= leaf_ids:
            raise ValueError(f"local_reach debe dar, para la hoja {aid}, sólo hojas del holón")
        nearby_ids[aid] = sorted({*local_reach[aid], aid})
    return nearby_ids


def assign_epigenetic_roles(
    holon: CompositeAgent, local_reach: Mapping[int, Sequence[int]], config: SimulationConfig
) -> dict[int, EpigeneticRole]:
    """Señal posicional de R25 (D36, D50.1): un rol por hoja, ordenado por `agent_id`.

    `local_reach` sigue el contrato de D25.1 y se valida aun con la regla apagada. Con $R_{25}$
    inerte, todas las hojas reciben `NONE`. Con la regla activa, con K los patrones de
    la memoria de la hoja con `confidence >= decision_conf_threshold`, `unique` lo que sólo ella
    sabe en el holón y `deg` sus cercanas sin contarse a sí misma:
    1. `LIBRARIAN` maximiza `(unique, |K|, -agent_id)`;
    2. `EXPLORER` maximiza, entre las restantes, `(-deg, -agent_id)`;
    3. `NERVE` maximiza, si quedan hojas, `(deg, -agent_id)` entre las restantes;
    4. las demás quedan en `NONE`.
    Es pura: lee las memorias como R18, no conoce coordenadas y no escribe roles.
    """
    nearby_ids = _validated_reach(holon, local_reach)
    leaves = holon.leaf_agents
    roles = {leaf.agent_id: EpigeneticRole.NONE for leaf in leaves}
    if not epigenetic_roles_active(config):
        return roles
    threshold = config.decision_conf_threshold
    known = {
        leaf.agent_id: frozenset(
            u.pattern for u in leaf.memory.all_units() if u.confidence >= threshold
        )
        for leaf in leaves
    }
    holders = Counter(pattern for patterns in known.values() for pattern in patterns)
    unique = {
        aid: sum(1 for pattern in patterns if holders[pattern] == 1)
        for aid, patterns in known.items()
    }
    degree = {aid: len(nearby) - 1 for aid, nearby in nearby_ids.items()}  # sin la propia hoja
    remaining = sorted(roles)
    librarian = max(remaining, key=lambda aid: (unique[aid], len(known[aid]), -aid))
    remaining.remove(librarian)
    explorer = max(remaining, key=lambda aid: (-degree[aid], -aid))
    remaining.remove(explorer)
    roles[librarian] = EpigeneticRole.LIBRARIAN
    roles[explorer] = EpigeneticRole.EXPLORER
    if remaining:
        roles[max(remaining, key=lambda aid: (degree[aid], -aid))] = EpigeneticRole.NERVE
    return roles


def apply_downward_causation(
    holon: CompositeAgent, local_reach: Mapping[int, Sequence[int]], config: SimulationConfig
) -> None:
    """Causalidad descendente (R18, D25.1): penaliza en cada hoja lo que otra cercana sabe mejor.

    `local_reach` tiene una clave por hoja: `local_reach[aid]` son las hojas del holón en
    alcance local de `aid`, que se toma como incluida aunque no figure en la lista. Con la
    regla apagada, limpia la penalización de todas las hojas.
    """
    leaves = holon.leaf_agents
    by_id = {leaf.agent_id: leaf for leaf in leaves}
    # Se valida aun con la regla apagada, para que la ablación no oculte un error del motor.
    nearby_ids = _validated_reach(holon, local_reach)
    if not config.enable_downward_causation:
        for leaf in leaves:
            leaf.memory.set_redundant_patterns(frozenset(), 1.0)
        return
    redundant_by_leaf: dict[int, frozenset[Pattern]] = {}
    for leaf in leaves:
        nearby = [by_id[aid] for aid in nearby_ids[leaf.agent_id]]
        redundant: set[Pattern] = set()
        for unit in leaf.memory.all_units():
            holders = [
                (held.confidence, -other.agent_id)
                for other in nearby
                if (held := other.memory.get(unit.pattern)) is not None
            ]
            if max(holders)[1] != -leaf.agent_id:
                redundant.add(unit.pattern)
        redundant_by_leaf[leaf.agent_id] = frozenset(redundant)
    # Se calcula todo antes de escribir: ninguna hoja lee una penalización del mismo paso.
    for leaf in leaves:
        leaf.memory.set_redundant_patterns(
            redundant_by_leaf[leaf.agent_id], config.redundancy_penalty
        )


def reproduce_holon(
    holon: CompositeAgent,
    offspring: Mapping[int, MicroAgent],
    node_id_source: Callable[[], int],
    tick: int,
) -> CompositeAgent:
    """Endosimbiosis (R17, D26): replica el árbol sustituyendo cada hoja por su hija.

    Los `node_id` nuevos se piden en preorden (primero el nodo, luego sus hijos en orden). Todos
    los nodos replicados nacen con `formed_by_bond = False` y `formation_tick = tick`.
    """
    leaf_ids = [leaf.agent_id for leaf in holon.leaf_agents]
    children_ids = [offspring[aid].agent_id for aid in leaf_ids if aid in offspring]
    if (
        len(children_ids) != len(leaf_ids)
        or len(set(children_ids)) != len(leaf_ids)
        or not set(children_ids).isdisjoint(leaf_ids)
    ):
        # Se valida antes de pedir IDs: un fallo no deja huecos en el contador del motor.
        raise ValueError(
            f"offspring debe asignar a cada hoja un hijo distinto y ajeno al holón: {leaf_ids}"
        )

    def replicate(node: CompositeAgent) -> CompositeAgent:
        node_id = node_id_source()
        children = tuple(
            replicate(child) if isinstance(child, CompositeAgent) else offspring[child.node_id]
            for child in node.children
        )
        return CompositeAgent(node_id, children, tick, False)

    return replicate(holon)
