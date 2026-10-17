"""Configuración reproducible e inmutable de una simulación."""

from dataclasses import asdict, dataclass
from typing import Any

_TAU_POLICIES = ("validation", "evidence_age")
_UPDATE_SCHEMES = ("synchronous", "asynchronous")

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
)
_MIN_ONE_FIELDS = (
    "num_agents",
    "resources_per_pattern",
    "grid_width",
    "grid_height",
)
_NON_NEGATIVE_FIELDS = (
    "seed",  # PCG64 no acepta semillas negativas
    "perception_radius",
    "comm_radius",
    "lambda_decay",
    "passive_conf_decay",
    "max_broadcast_per_tick",
    "max_queries_per_tick",
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
            if getattr(self, name) < 0:
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

    def to_dict(self) -> dict[str, Any]:
        """Diccionario con todos los campos, serializable a JSON."""
        return asdict(self)
