"""Configuración reproducible e inmutable de una simulación."""

from dataclasses import asdict, dataclass
from typing import Any

_TAU_POLICIES = ("validation", "evidence_age")
_UPDATE_SCHEMES = ("synchronous", "asynchronous")
_REPRODUCTION_MODES = ("energy", "neutral")

_UNIT_INTERVAL_FIELDS = (
    "initial_direct_confidence",
    "alpha_learning",
    "beta_reinforce",
    "beta_punish",
    "gamma_social_discount",
    "eta_consensus",
    "eta_doubt",
    "min_confidence",
    "decision_conf_threshold",
    "epsilon_explore",
    "epsilon_recheck",
    "discrete_mutation_prob",
    "initial_bond_affinity",
    "holon_bond_threshold",
    "inheritance_discount",
    "stigmergy_deposit_rate",
    "stigmergy_decay",
)
_MIN_ONE_FIELDS = (
    "num_agents",
    "resources_per_pattern",
    "grid_width",
    "grid_height",
    "max_population",
    "composite_resources_per_pattern",
)
_POSITIVE_FIELDS = (
    "initial_energy",
    "reproduction_threshold",
    "energy_gain_scale",
    "composite_reward_exponent",
)
_NON_NEGATIVE_FIELDS = (
    "seed",  # PCG64 no acepta semillas negativas
    "perception_radius",
    "comm_radius",
    "lambda_decay",
    "passive_conf_decay",
    "max_broadcast_per_tick",
    "max_queries_per_tick",
    "metabolic_base_cost",
    "memory_capacity_cost",
    "sensory_radius_cost",
    "move_cost",
    "message_cost",
    "mutation_rate",
    "holon_coord_cost",
    "holon_min_energy_per_leaf",
    "composite_failure_penalty",
    "num_composite_patterns",
)


@dataclass(frozen=True)
class SimulationConfig:
    """Parámetros de una corrida. Las variantes se construyen con `dataclasses.replace`."""

    seed: int = 42
    grid_width: int = 40
    grid_height: int = 40
    num_agents: int = 80
    num_world_patterns: int = 12
    resources_per_pattern: int = 8
    memory_capacity: int = 3
    perception_radius: int = 2
    comm_radius: int = 2
    comm_enabled: bool = True
    initial_direct_confidence: float = 0.85
    alpha_learning: float = 0.40
    beta_reinforce: float = 0.30
    beta_punish: float = 0.60
    gamma_social_discount: float = 0.75
    eta_consensus: float = 0.15
    eta_doubt: float = 0.20
    lambda_decay: float = 0.005
    passive_conf_decay: float = 0.002
    min_confidence: float = 0.05
    decision_conf_threshold: float = 0.35
    epsilon_explore: float = 0.15
    max_broadcast_per_tick: int = 1
    max_queries_per_tick: int = 2
    enable_specialization: bool = False
    epsilon_recheck: float = 0.0  # contrato Exp 004 (Decisión 12)
    tau_policy: str = "validation"  # contrato Exp 004: "validation" | "evidence_age"
    anti_echo_enabled: bool = True  # ablación de R6 (Decisión 13)
    enable_navigation: bool = True  # ablación de R11 (Decisión 13)
    comm_content_null: bool = False  # control nulo E4 (Decisión 13)
    update_scheme: str = "synchronous"  # Decisión 15: "synchronous" | "asynchronous"
    enforce_memory_constraint: bool = True

    # --- Fase II: metabolismo, evolución y herencia dual (R12, R13, R14) ---
    enable_evolution: bool = False
    initial_energy: float = 1.50
    reproduction_threshold: float = 2.20
    reproduction_mode: str = "energy"  # "energy" (R12) | "neutral" (ablación de R12)
    offspring_energy_share: float = 0.50
    max_population: int = 160
    metabolic_base_cost: float = 0.01
    memory_capacity_cost: float = 0.002
    sensory_radius_cost: float = 0.0005
    move_cost: float = 0.005
    message_cost: float = 0.001
    energy_gain_scale: float = 0.45
    mutation_rate: float = 0.05
    discrete_mutation_prob: float = 0.10
    max_genome_memory_capacity: int = 6
    initial_bond_affinity: float = 0.60
    enable_cultural_inheritance: bool = False
    inheritance_discount: float = 0.65

    # --- Fase II: jerarquía holónica, endosimbiosis y causalidad descendente (R15-R18) ---
    enable_holonic_hierarchy: bool = False
    holon_bond_threshold: float = 0.35
    max_holon_leaves: int = 8
    holon_coord_cost: float = 0.002
    enable_holon_splitting: bool = True
    enable_holon_view: bool = True  # R22; sólo actúa con enable_holonic_hierarchy=True
    holon_energy_sharing: bool = True  # parte de R23; sólo actúa con enable_holonic_hierarchy=True
    holon_split_patience: int = 25
    holon_min_energy_per_leaf: float = 0.30
    enable_holon_reproduction: bool = False
    enable_downward_causation: bool = False
    redundancy_penalty: float = 0.25

    # --- Fase II: recursos compuestos y estigmergia espacial (R19) ---
    num_composite_patterns: int = 0
    composite_order: int = 2
    composite_resources_per_pattern: int = 4
    composite_reward_exponent: float = 1.50
    composite_failure_penalty: float = 0.20
    enable_stigmergy: bool = False
    stigmergy_deposit_rate: float = 0.50
    stigmergy_decay: float = 0.02

    def __post_init__(self) -> None:
        if self.memory_capacity < 1:
            raise ValueError(f"memory_capacity debe ser >= 1, recibido {self.memory_capacity}")
        if self.num_world_patterns < 2:
            raise ValueError(
                f"num_world_patterns debe ser >= 2, recibido {self.num_world_patterns}"
            )
        if self.enforce_memory_constraint and self.memory_capacity >= self.num_world_patterns:
            raise ValueError(
                f"memory_capacity ({self.memory_capacity}) debe ser menor que "
                f"num_world_patterns ({self.num_world_patterns}) con enforce_memory_constraint"
            )
        for name in _MIN_ONE_FIELDS:
            if getattr(self, name) < 1:
                raise ValueError(f"{name} debe ser >= 1, recibido {getattr(self, name)}")
        for name in _NON_NEGATIVE_FIELDS:
            if not getattr(self, name) >= 0:  # `not >=` también rechaza NaN
                raise ValueError(f"{name} no puede ser negativo, recibido {getattr(self, name)}")
        if 2 * max(self.perception_radius, self.comm_radius) >= min(
            self.grid_width, self.grid_height
        ):
            raise ValueError(
                "perception_radius/comm_radius: 2 * max(radius) debe ser menor que "
                "min(grid_width, grid_height)"
            )
        for name in _UNIT_INTERVAL_FIELDS:
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} debe estar en [0, 1], recibido {getattr(self, name)}")
        if self.min_confidence >= self.decision_conf_threshold:
            raise ValueError(
                f"min_confidence ({self.min_confidence}) debe ser menor que "
                f"decision_conf_threshold ({self.decision_conf_threshold})"
            )
        if self.tau_policy not in _TAU_POLICIES:
            raise ValueError(
                f"tau_policy debe ser uno de {_TAU_POLICIES}, recibido {self.tau_policy!r}"
            )
        if self.update_scheme not in _UPDATE_SCHEMES:
            raise ValueError(
                f"update_scheme debe ser uno de {_UPDATE_SCHEMES}, recibido {self.update_scheme!r}"
            )

        self._validate_phase2()

    def _validate_phase2(self) -> None:
        for name in _POSITIVE_FIELDS:
            if not getattr(self, name) > 0.0:  # `not >` también rechaza NaN
                raise ValueError(f"{name} debe ser > 0, recibido {getattr(self, name)}")
        if not 0.0 < self.offspring_energy_share < 1.0:
            raise ValueError(
                f"offspring_energy_share debe estar en (0, 1), recibido "
                f"{self.offspring_energy_share}"
            )
        if not 0.0 < self.redundancy_penalty <= 1.0:
            raise ValueError(
                f"redundancy_penalty debe estar en (0, 1], recibido {self.redundancy_penalty}"
            )
        if not self.composite_failure_penalty <= 1.0:
            raise ValueError(
                f"composite_failure_penalty debe ser <= 1, recibido "
                f"{self.composite_failure_penalty}"
            )
        if self.max_genome_memory_capacity < self.memory_capacity:
            raise ValueError(
                f"max_genome_memory_capacity ({self.max_genome_memory_capacity}) debe ser >= "
                f"memory_capacity ({self.memory_capacity})"
            )
        if self.max_holon_leaves < 2:
            raise ValueError(f"max_holon_leaves debe ser >= 2, recibido {self.max_holon_leaves}")
        if self.holon_split_patience < 1:
            raise ValueError(
                f"holon_split_patience debe ser >= 1, recibido {self.holon_split_patience}"
            )
        if self.composite_order < 2:
            raise ValueError(f"composite_order debe ser >= 2, recibido {self.composite_order}")
        if self.reproduction_mode not in _REPRODUCTION_MODES:
            raise ValueError(
                f"reproduction_mode debe ser uno de {_REPRODUCTION_MODES}, "
                f"recibido {self.reproduction_mode!r}"
            )
        if (
            self.enable_stigmergy
            and self.stigmergy_deposit_rate > 0
            and self.stigmergy_deposit_rate * self.initial_direct_confidence < self.min_confidence
        ):
            # Ni una creencia directa nueva dejaría un rastro: la estigmergia casi sólo borraría
            # rastros (D20 y D27). Es una cota de cordura, no una garantía para todo depósito.
            raise ValueError(
                f"stigmergy_deposit_rate ({self.stigmergy_deposit_rate}) por "
                f"initial_direct_confidence ({self.initial_direct_confidence}) debe ser >= "
                f"min_confidence ({self.min_confidence}) con enable_stigmergy"
            )
        if self.num_composite_patterns > 0 and self.composite_order > self.num_world_patterns // 2:
            raise ValueError(
                f"composite_order ({self.composite_order}) debe ser <= num_world_patterns // 2 "
                f"({self.num_world_patterns // 2}) cuando num_composite_patterns > 0"
            )

    def to_dict(self) -> dict[str, Any]:
        """Diccionario con todos los campos, serializable a JSON."""
        return asdict(self)
