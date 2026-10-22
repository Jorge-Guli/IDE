"""Configuración reproducible e inmutable de una simulación."""

from dataclasses import asdict, dataclass
from typing import Any

# Longitud del ADN fundador (D32): un codón por cada rasgo 0x00-0x08. `ide.agent.dna` reutiliza
# este valor; vive aquí porque la configuración lo necesita y no puede importar del agente.
FOUNDER_DNA_LENGTH = 9
# Longitud del ADN fundador con la política genética (D46.5): los 9 codones de rasgo más los cuatro
# codones conductuales neutros. `ide.agent.dna.founder_dna_length` debe coincidir con este valor.
FOUNDER_DNA_LENGTH_GENETIC = FOUNDER_DNA_LENGTH + 4
# Tolerancia de los umbrales de energía (precisión 93): `1.5 * 2.2` vale `3.3000000000000003`, y
# una energía de 3.3 debe alcanzar la alta fidelidad de R30. Vive aquí para que el estrés tenga
# una sola definición, compartida por `ide.agent.dna`, `ide.agent.micro_agent` y la evolución.
ENERGY_THRESHOLD_TOLERANCE = 1e-9

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
    "dna_point_mutation_rate",
    "dna_duplication_rate",
    "dna_deletion_rate",
    "dna_excision_rate",
    "hgt_rate",
    "spore_cost_fraction",
    "sos_high_fidelity_factor",
    "lock_coord_discount",
    "comm_propensity_base",
    "symbiotic_commitment_base",
    "recombination_base",
    "share_fraction",
    "share_efficiency",
    "predation_efficiency",
    "plasticity_rate_base",
    "world_shift_fraction",
)
_MIN_ONE_FIELDS = (
    "num_agents",
    "resources_per_pattern",
    "grid_width",
    "grid_height",
    "max_population",
    "composite_resources_per_pattern",
    "max_plasmids",
    "crispr_eval_ticks",
    "crispr_memory_size",
    "sos_window",
    "telomere_min_lifespan",
    "crowding_threshold",
    "resource_regen_delay",
    "num_regions",
    "carcass_lifetime",
    "activity_threshold",
)
_POSITIVE_FIELDS = (
    "initial_energy",
    "reproduction_threshold",
    "energy_gain_scale",
    "composite_reward_exponent",
    "stress_energy_ratio",
    "surplus_energy_ratio",
    "hgt_energy_ratio",
    "sos_hypermutation_factor",
    "sos_high_fidelity_energy_ratio",
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
    "dna_codon_cost",
    "crispr_toxicity_threshold",
    "senescence_cost_rate",
    "spore_energy_threshold",
    "attack_power",
    "attack_cost",
    "season_length",
    "signal_cost",
    "world_shift_period",
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
    epsilon_recheck: float = 0.0  # contrato Exp 005 (Decisión 12)
    tau_policy: str = "validation"  # contrato Exp 005: "validation" | "evidence_age"
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

    # --- Fase II-B: ADN compacto y expresión condicional (R24) ---
    enable_compact_dna: bool = False
    dna_codon_cost: float = 0.0002  # c_dna por codón (cromosoma + plásmidos + CRISPR) y por tick
    dna_point_mutation_rate: float = (
        0.05  # probabilidad por codón de invertir un bit al reproducirse
    )
    dna_duplication_rate: float = 0.02
    dna_deletion_rate: float = 0.02
    dna_min_length: int = 1
    dna_max_length: int = 32
    stress_energy_ratio: float = 0.35  # promotor 0x18 y estrés de R30
    surplus_energy_ratio: float = 0.85  # promotor 0x19
    # --- R25 ---
    enable_epigenetic_roles: bool = False
    # --- R26 y R27 ---
    enable_plasmid_hgt: bool = False
    dna_excision_rate: float = 0.02  # copia de un codón del cromosoma a un plásmido al reproducirse
    max_plasmids: int = 4
    hgt_rate: float = 0.05  # probabilidad por tick de que un donante elegible conjugue
    hgt_energy_ratio: float = (
        0.85  # el donante necesita E >= hgt_energy_ratio * reproduction_threshold
    )
    enable_crispr_immunity: bool = False
    crispr_eval_ticks: int = 20
    crispr_toxicity_threshold: float = 0.20
    crispr_memory_size: int = 4
    # --- R28 ---
    enable_sporulation: bool = False
    spore_energy_threshold: float = 0.30
    spore_cost_fraction: float = 0.05  # costo de la endospora = fracción de metabolic_base_cost
    # --- R29 ---
    enable_telomere_senescence: bool = False
    telomere_base_lifespan: int = 600
    telomere_min_lifespan: int = 150
    telomere_max_lifespan: int = 1200
    senescence_cost_rate: float = 1e-5  # costo extra = rate * (edad - T_max)^2
    # --- R30 ---
    enable_sos_mutation: bool = False
    sos_window: int = 50
    sos_hypermutation_factor: float = 4.0
    sos_high_fidelity_factor: float = 0.25
    sos_high_fidelity_energy_ratio: float = 1.5
    # --- R31 ---
    enable_symbiotic_ratchet: bool = False
    lock_coord_discount: float = 0.5  # `lock_composite_threshold` se eliminó (D50.3 y D52.4)

    # --- Fase II-B reformulada (D52) ---
    # R32: conducta en el ADN
    enable_genetic_policy: bool = False
    comm_propensity_base: float = 1.0
    crowding_threshold: int = 3
    # R31 reformulada
    symbiotic_commitment_base: float = 0.0
    # R33 y R34
    enable_resource_depletion: bool = False
    resource_regen_delay: int = 20
    enable_heterogeneity: bool = False
    num_regions: int = 3
    season_length: int = 0  # 0 = sin estaciones
    winter_regen_factor: float = 3.0
    # R35
    enable_carcasses: bool = False
    carcass_value: float = 0.6
    carcass_lifetime: int = 50
    # R36 y R37
    enable_energy_transfer: bool = False
    share_fraction: float = 0.25
    share_efficiency: float = 0.9
    enable_predation: bool = False
    attack_power: float = 0.5
    predation_efficiency: float = 0.6
    attack_cost: float = 0.01
    # R38
    enable_recombination: bool = False
    recombination_base: float = 0.0
    # Telemetría de evolución abierta (D53): nacimientos portadores (precisión 43)
    activity_threshold: int = 10

    # --- Ampliación (D57-D63): estado interno, plasticidad, señales y entorno cambiante ---
    enable_internal_state: bool = False  # R39
    enable_plasticity: bool = False  # R40
    plasticity_rate_base: float = 0.0
    enable_signals: bool = False  # R41
    signal_cost: float = 0.002
    world_shift_period: int = 0  # 0 = sin cambios del entorno (D62.1)
    world_shift_fraction: float = 0.5

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
        self._validate_phase25()

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

    def _validate_phase25(self) -> None:
        # Los rangos de D31 se validan siempre con las tuplas de campos de `__post_init__`.
        if not self.stress_energy_ratio < self.surplus_energy_ratio:
            raise ValueError(
                f"stress_energy_ratio ({self.stress_energy_ratio}) debe ser menor que "
                f"surplus_energy_ratio ({self.surplus_energy_ratio})"
            )
        if not 1 <= self.dna_min_length <= FOUNDER_DNA_LENGTH:
            raise ValueError(
                f"dna_min_length debe estar en [1, {FOUNDER_DNA_LENGTH}], "
                f"recibido {self.dna_min_length}"
            )
        if self.dna_max_length < FOUNDER_DNA_LENGTH:
            raise ValueError(
                f"dna_max_length debe ser >= {FOUNDER_DNA_LENGTH}, recibido {self.dna_max_length}"
            )
        if not (
            self.telomere_min_lifespan <= self.telomere_base_lifespan <= self.telomere_max_lifespan
        ):
            raise ValueError(
                f"telomere_min_lifespan ({self.telomere_min_lifespan}) <= "
                f"telomere_base_lifespan ({self.telomere_base_lifespan}) <= "
                f"telomere_max_lifespan ({self.telomere_max_lifespan}) no se cumple"
            )
        self._validate_phase25_reformulation()
        if self.enable_compact_dna:
            self._validate_compact_dna()

    def _validate_phase25_reformulation(self) -> None:
        # Los rangos de D52.2 y D63.1 se validan siempre con las tuplas de `__post_init__`.
        if not self.winter_regen_factor >= 1:  # `not >=` también rechaza NaN
            raise ValueError(
                f"winter_regen_factor debe ser >= 1, recibido {self.winter_regen_factor}"
            )
        if not 0.0 < self.carcass_value <= 1.0:  # `not` también rechaza NaN
            raise ValueError(f"carcass_value debe estar en (0, 1], recibido {self.carcass_value}")
        if self.enable_heterogeneity and self.num_regions > self.grid_width:
            raise ValueError(
                f"num_regions ({self.num_regions}) debe ser <= grid_width ({self.grid_width})"
            )

    def _validate_compact_dna(self) -> None:
        if not self.enable_evolution:
            raise ValueError("enable_compact_dna exige enable_evolution=True")
        if self.perception_radius < 1:
            raise ValueError(
                f"perception_radius debe ser >= 1 con enable_compact_dna, "
                f"recibido {self.perception_radius}"
            )
        if self.comm_radius < 1:
            raise ValueError(
                f"comm_radius debe ser >= 1 con enable_compact_dna, recibido {self.comm_radius}"
            )
        # R32 efectiva (precisión 31): el fundador conductual debe caber en las cotas (D46.5).
        # `dna_min_length <= 13` ya lo garantiza la cota de D31 (`dna_min_length <= 9`).
        if self.enable_genetic_policy and self.dna_max_length < FOUNDER_DNA_LENGTH_GENETIC:
            raise ValueError(
                f"dna_max_length ({self.dna_max_length}) debe ser >= "
                f"{FOUNDER_DNA_LENGTH_GENETIC} con enable_genetic_policy"
            )
        if not 0.01 <= self.alpha_learning <= 1.0:
            raise ValueError(
                f"alpha_learning debe estar en [0.01, 1] con enable_compact_dna, "
                f"recibido {self.alpha_learning}"
            )
        # Las cotas de D31 para C_max y los radios ya las garantizan las validaciones previas:
        # `2 * max(r) < min(grid)` equivale a `r <= (min(grid) - 1) // 2`;
        # `max_genome_memory_capacity >= memory_capacity` y, con `enforce_memory_constraint`,
        # `memory_capacity < num_world_patterns`.
        if self.spore_energy_threshold > self.reproduction_threshold:
            raise ValueError(
                f"spore_energy_threshold ({self.spore_energy_threshold}) debe ser <= "
                f"reproduction_threshold ({self.reproduction_threshold}) con enable_compact_dna"
            )

    def to_dict(self) -> dict[str, Any]:
        """Diccionario con todos los campos, serializable a JSON."""
        return asdict(self)


def genetic_policy_active(config: SimulationConfig) -> bool:
    """R32 efectivamente activa: con `enable_compact_dna` y `enable_genetic_policy` (prec. 31).

    Es la única definición de la condición: la usan `dna.py` (R39, D57.3) y `pipeline.py`, y el
    motor la guarda en `engine.genetic_policy_active`. Sin ADN, `enable_genetic_policy` es
    inerte: no hay percepción social, la puerta de comunicación no actúa y la política es la
    escrita a mano.
    """
    return config.enable_compact_dna and config.enable_genetic_policy


def sporulation_active(config: SimulationConfig) -> bool:
    """R28 efectivamente activa: `enable_sporulation` con evolución (precisión 30, D38, D50.2).

    Es la única definición de la condición: con ella la política factibiliza `SPORULATE` y el
    motor agrega la germinación y aplica la física y el costo de la endospora. Sin evolución la
    bandera es inerte. La entrada exige además la política genética (`SPORULATE` sólo existe
    como conducta del ADN): sin ella nadie entra nunca en endospora, aunque esta condición valga.
    """
    return config.enable_evolution and config.enable_sporulation


def epigenetic_roles_active(config: SimulationConfig) -> bool:
    """R25 efectivamente activa: `enable_epigenetic_roles` con ADN y holones (D30.3, D36).

    Es la única definición de la condición: la usan `assign_epigenetic_roles`, `build_systems`
    (que agrega la asignación de roles de la Fase 5) y la impronta de la reproducción holónica,
    que el motor lee de `engine.epigenetic_roles_active`. Sin ADN o sin holones la bandera es
    inerte: todas las hojas conservan `NONE`.
    """
    return (
        config.enable_compact_dna
        and config.enable_holonic_hierarchy
        and config.enable_epigenetic_roles
    )


def symbiotic_ratchet_active(config: SimulationConfig) -> bool:
    """R31 efectivamente activa: `enable_symbiotic_ratchet` con ADN y holones (D50.3, D52.3).

    Es la única definición de la condición: la usan el sello (`should_lock_holon`) y, a través de
    `is_effectively_locked`, la protección contra `SPLIT` (`should_split_holon`) y el descuento de
    coordinación del motor. Sin ADN la bandera es inerte aunque
    `symbiotic_commitment_base >= 0.5` (precisión 32): el compromiso es siempre un rasgo
    heredable, nunca un decreto de la configuración.
    """
    return (
        config.enable_compact_dna
        and config.enable_holonic_hierarchy
        and config.enable_symbiotic_ratchet
    )


def recombination_active(config: SimulationConfig) -> bool:
    """R38 efectivamente activa: `enable_recombination` con ADN y evolución (D51, D52.3).

    Es la única definición de la condición: con ella la reproducción individual (R12, también la
    neutral) busca pareja y cruza los cromosomas con `evo_rng`; el motor la guarda en
    `engine.recombination_active`. Sin ADN o sin evolución la bandera es inerte y no se extrae
    nada. La reproducción holónica (R17) nunca recombina.
    """
    return config.enable_compact_dna and config.enable_evolution and config.enable_recombination


def stress_energy_limit(config: SimulationConfig) -> float:
    """Límite de energía del estrés (D39, precisión 93): hay estrés si `energy` es menor.

    Vale `stress_energy_ratio * reproduction_threshold - ENERGY_THRESHOLD_TOLERANCE`. Es la única
    definición del umbral: la usan el promotor `0x18`, la banda de expresión del agente y el
    registro del estrés de R30, de modo que en el umbral exacto no hay estrés en ninguno.
    """
    return config.stress_energy_ratio * config.reproduction_threshold - ENERGY_THRESHOLD_TOLERANCE


def is_stress_energy_ratio(energy_ratio: float, config: SimulationConfig) -> bool:
    """Estrés expresado como `E / reproduction_threshold` (promotor `0x18`, precisión 93).

    Compara `energy_ratio * reproduction_threshold` con `stress_energy_limit`; NaN no es estrés.
    """
    return energy_ratio * config.reproduction_threshold < stress_energy_limit(config)
