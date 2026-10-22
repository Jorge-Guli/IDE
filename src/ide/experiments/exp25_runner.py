"""Protocolos de la Fase II-B (`25a`, `25b`, `25c` y `25d`, design D56) y su CLI reproducible.

Cada protocolo parte de su configuración en `PHASE25_PROTOCOL_CONFIGS` (condición `full`) y
compara las condiciones de `phase25_conditions`, todas con la misma semilla. Usa la
infraestructura de `phase2_cli.py` (`ProtocolSpec` y `run_protocol`). Antes de crear `--out`, la
CLI comprueba que la configuración de cada protocolo que va a correr respete sus rasgos
(`check_phase25_protocol`; en la atribución, `validate_phase25_attribution`); un problema de
configuración o de argumentos sale con código 2. Los archivos llevan el perfil en el nombre
(`exp25_{perfil}_...`) y registran el perfil, las semillas y las configuraciones corridas. Tres
modos:

- **Protocolos** (por defecto): corre cada protocolo con sus condiciones y semillas (por defecto
  `PHASE25_SEEDS` y el perfil `phase25`, del que sólo se usa `total_ticks`) y escribe
  `exp25_{perfil}_{protocolo}_{condición}.json` con el resumen de cada semilla
  (`Phase25ConditionSummary`). Con `--histories`, cada corrida escribe al terminar sus historiales
  genético y ecológico completos en `exp25_{perfil}_{protocolo}_{condición}_seed{s}_histories.json`,
  sin acumularlos; un `OSError` al escribirlos queda como `error` de esa corrida, no aborta el lote
  y la CLI devuelve 1. La consola sólo muestra demografía.
- **Prueba de humo** (`--smoke`, D56): `exp25_{perfil}_smoke.json` registra, por protocolo,
  condición y semilla, sólo la terminación (`finished` o `error`, con el tipo y el mensaje de la
  excepción, sin direcciones de memoria), la población final (hojas vivas) y la generación máxima;
  las configuraciones van como metadato del archivo. Sus motores corren sin la telemetría de
  evolución abierta (sólo con la comprobación de invariantes `_BirthInvariant`): no producen los
  historiales genético y ecológico ni calculan ninguna métrica de afirmación. Una corrida que
  falla no aborta las demás; la CLI devuelve 1 si alguna falló.
- **Atribución** (`--attribution`): `run_phase25_attribution` con las semillas (por defecto
  `PHASE25_SEEDS`) y los `rule_effects` exploratorios (`--rule-effect-seeds`, sólo en este modo; por
  defecto `PHASE25_RULE_EFFECT_SEEDS`); escribe el `Phase25Report` en
  `exp25_phase25_attribution.json` y una tabla en consola. Usa siempre el perfil pre-registrado:
  otro `--profile` es un error de argumentos.

Las corridas son independientes: se reparten en `--jobs` procesos (por defecto, los núcleos
detectados; D62.3 y precisión 55) y la salida es idéntica para cualquier `--jobs`. Las
configuraciones idénticas (p. ej., `stable` de `25d` y `full` de `25a`) corren una sola vez.

Uso: `python -m ide.experiments.exp25_runner [--profile P] [--seeds 42 43 ...] [--jobs N]
[--out results/] [--histories | --smoke | --attribution [--rule-effect-seeds 42 ...]]`.
"""

import argparse
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import median
from typing import Any

from ide.config import SimulationConfig
from ide.experiments import attribution
from ide.experiments.attribution import (
    PHASE25_ATTRIBUTION_PROFILE,
    PHASE25_CLAIMS,
    PHASE25_MIN_VALID_PAIRS,
    PHASE25_RULE_EFFECT_SEEDS,
    PHASE25_SEEDS,
    Phase25Report,
    claim_threshold_and_valid_seeds,
    final_demography,
    phase25_conditions,
    run_phase25_attribution,
)
from ide.experiments.exp001_runner import (
    PROFILES,
    default_jobs,
    map_in_order,
    non_negative_int,
    positive_int,
    report_to_dict,
    validate_seeds,
    write_json,
)
from ide.experiments.metrics import EcologyTickMetrics, GeneticTickMetrics
from ide.experiments.phase2_cli import ProtocolSpec, require_positive_ticks, run_protocol
from ide.simulation.engine import SimulationEngine
from ide.simulation.pipeline import TickFrame

__all__ = [
    "PHASE25_SPECS",
    "Phase25ConditionHistories",
    "Phase25ConditionSummary",
    "Phase25ProtocolReport",
    "build_arg_parser",
    "main",
    "run_phase25_condition",
    "run_phase25_condition_histories",
    "run_phase25_protocol",
]

_PROTOCOLS = ("25a", "25b", "25c", "25d")
_NAME = "exp25"


@dataclass(frozen=True)
class Phase25ConditionSummary:
    """Resumen de una condición (spec "Resumen por Condición de los Protocolos 25a a 25d")."""

    final_accuracy: float  # M2 acumulada del último tick
    final_agents: int  # hojas vivas al final
    final_active_agents: int  # hojas vivas que no están en endospora
    max_generation: int  # máximo de la corrida
    last_genetic: GeneticTickMetrics | None  # último registro de `genetic_history`
    last_ecology: EcologyTickMetrics | None  # último registro de `ecology_history`


@dataclass(frozen=True)
class Phase25ConditionHistories:
    """Historiales genético y ecológico completos de una corrida, un registro por tick."""

    genetic_history: tuple[GeneticTickMetrics, ...]
    ecology_history: tuple[EcologyTickMetrics, ...]


@dataclass(frozen=True)
class Phase25ProtocolReport:
    protocol: str  # "25a" | "25b" | "25c" | "25d"
    seed: int
    total_ticks: int
    conditions: dict[str, Phase25ConditionSummary]  # en el orden de `phase25_conditions`


def run_phase25_condition_histories(
    config: SimulationConfig, total_ticks: int
) -> tuple[Phase25ConditionSummary, Phase25ConditionHistories]:
    """Corre una condición durante `total_ticks`: su resumen y sus historiales."""
    require_positive_ticks(total_ticks)
    engine = SimulationEngine(config)
    history = engine.run(total_ticks)
    final_agents, final_active_agents, max_generation = final_demography(engine)
    genetic, ecology = engine.genetic_history, engine.ecology_history
    summary = Phase25ConditionSummary(
        final_accuracy=history[-1].cumulative_decision_accuracy,
        final_agents=final_agents,
        final_active_agents=final_active_agents,
        max_generation=max_generation,
        last_genetic=genetic[-1] if genetic else None,
        last_ecology=ecology[-1] if ecology else None,
    )
    return summary, Phase25ConditionHistories(tuple(genetic), tuple(ecology))


def run_phase25_condition(config: SimulationConfig, total_ticks: int) -> Phase25ConditionSummary:
    """Corre una condición durante `total_ticks` y la resume."""
    return run_phase25_condition_histories(config, total_ticks)[0]


def _spec(key: str) -> ProtocolSpec:
    def conditions(config: SimulationConfig) -> dict[str, SimulationConfig]:
        return phase25_conditions(key, config)

    def assemble(
        seed: int, total_ticks: int, runs: Mapping[str, Phase25ConditionSummary]
    ) -> Phase25ProtocolReport:
        return Phase25ProtocolReport(key, seed, total_ticks, dict(runs))

    def headline(report: Phase25ProtocolReport) -> str:
        """Sólo demografía: nunca las métricas de las afirmaciones."""
        return "; ".join(
            f"{key} {name}: población {s.final_agents} (hojas activas {s.final_active_agents}), "
            f"generación máxima {s.max_generation}"
            for name, s in report.conditions.items()
        )

    def validate(config: SimulationConfig) -> None:
        """La configuración `full` respeta los rasgos de su protocolo (D56); si no, `ValueError`."""
        attribution.check_phase25_protocol(key, config)

    return ProtocolSpec(key, conditions, run_phase25_condition, assemble, headline, validate)


PHASE25_SPECS: tuple[ProtocolSpec, ...] = tuple(_spec(key) for key in _PROTOCOLS)
_SPECS_BY_KEY = {spec.key: spec for spec in PHASE25_SPECS}


def run_phase25_protocol(
    key: str, config: SimulationConfig, total_ticks: int
) -> Phase25ProtocolReport:
    """Corre todas las condiciones del protocolo `key` con la semilla de `config`."""
    spec = _SPECS_BY_KEY.get(key)
    if spec is None:
        raise ValueError(f"protocolo desconocido de la Fase II-B: {key}")
    return run_protocol(spec, config, total_ticks)


# --- Unidades de trabajo -----------------------------------------------------------------------

# Destino de un historial: (ruta, encabezado con perfil, protocolo, condición, semilla, ticks y
# configuración). Una corrida compartida por varias condiciones escribe un archivo por cada una.
_HistoryTarget = tuple[str, dict[str, Any]]
_Task = tuple[SimulationConfig, int, tuple[_HistoryTarget, ...]]  # (config, ticks, historiales)


_ADDRESS = re.compile(r"0x[0-9a-fA-F]+")


def _error_record(error: BaseException) -> dict[str, str]:
    """Tipo y mensaje de una excepción, deterministas: sin direcciones de memoria (`0x...`)."""
    return {"type": type(error).__name__, "message": _ADDRESS.sub("0x?", str(error))}


def _run_task(task: _Task) -> tuple[Phase25ConditionSummary, dict[str, str] | None]:
    """Corre una configuración y escribe sus historiales al terminar: no viajan ni se acumulan.

    Un `OSError` al escribirlos no aborta el lote: se devuelve como error de la corrida, junto
    con su resumen.
    """
    config, total_ticks, targets = task
    summary, histories = run_phase25_condition_histories(config, total_ticks)
    if targets:
        data = report_to_dict(histories)
        try:
            for path, header in targets:
                write_json(Path(path), {**header, **data})
        except OSError as error:
            return summary, _error_record(error)
    return summary, None


class _BirthInvariant:
    """Invariante del motor de la precisión 68, sin telemetría: todo nacimiento contado se anota.

    Es la comprobación que hace `GeneticMetricsObserver` al cerrar el tick, sin producir ningún
    registro; si falla, la corrida termina en error.
    """

    def on_decisions(self, engine: SimulationEngine, frame: TickFrame) -> None:
        pass

    def on_tick_end(self, engine: SimulationEngine, frame: TickFrame) -> None:
        if len(frame.born) != frame.births:
            raise RuntimeError(
                f"nacimientos sin anotar en el tick {frame.tick}: el motor contó {frame.births} "
                f"y se anotaron {len(frame.born)}"
            )


def _smoke_engine(config: SimulationConfig) -> SimulationEngine:
    """Motor de la prueba de humo (D56): sin telemetría de evolución abierta.

    `telemetry_observers` sólo tiene `_BirthInvariant`, así que no se producen `genetic_history`
    ni `ecology_history`, de donde salen las métricas de C13-C20, pero se conserva la comprobación
    de invariantes. La telemetría no consume generadores ni cambia el estado del motor, así que
    la demografía es la misma que con ella.
    """
    engine = SimulationEngine(config)
    engine.telemetry_observers = [_BirthInvariant()]
    return engine


def _smoke_task(task: tuple[SimulationConfig, int]) -> dict[str, Any]:
    """Terminación, población final y generación máxima de una corrida (D56).

    Una excepción se registra (tipo y mensaje) y no se propaga.
    """
    config, total_ticks = task
    try:
        engine = _smoke_engine(config)
        engine.run(total_ticks)
    except Exception as error:  # se registra la falla y siguen las demás corridas (D56)
        return {
            "termination": "error",
            "error": _error_record(error),
            "final_agents": None,
            "max_generation": None,
        }
    final_agents, _, max_generation = final_demography(engine)
    return {
        "termination": "finished",
        "error": None,
        "final_agents": final_agents,
        "max_generation": max_generation,
    }


# --- CLI ---------------------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fase II-B: protocolos 25a, 25b, 25c y 25d (design D56)"
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default=PHASE25_ATTRIBUTION_PROFILE,
        help=(
            "sólo se usa `total_ticks` del perfil; --attribution sólo admite el pre-registrado "
            f"({PHASE25_ATTRIBUTION_PROFILE})"
        ),
    )
    parser.add_argument("--seeds", type=non_negative_int, nargs="+", default=list(PHASE25_SEEDS))
    parser.add_argument(
        "--rule-effect-seeds",
        type=non_negative_int,
        nargs="*",
        default=None,
        help=(
            "sólo con --attribution: semillas de los rule_effects exploratorios (por defecto, "
            "PHASE25_RULE_EFFECT_SEEDS; sin valores, ninguna)"
        ),
    )
    parser.add_argument("--out", type=Path, default=Path("results/"))
    parser.add_argument(
        "--jobs", type=positive_int, default=default_jobs(), help="por defecto, los núcleos"
    )
    parser.add_argument(
        "--histories",
        action="store_true",
        help="sólo en el modo protocolos: escribe los historiales genético y ecológico",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--smoke",
        action="store_true",
        help="prueba de humo (D56): sólo terminación, generación máxima y población final",
    )
    mode.add_argument(
        "--attribution",
        action="store_true",
        help="atribución de C13-C20 con el perfil pre-registrado",
    )
    return parser


def _validate_configs(configs: Mapping[str, SimulationConfig]) -> None:
    """Los cuatro protocolos que se corren tienen su configuración y respetan sus rasgos (D56).

    Si no, `ValueError`. La atribución valida lo suyo con `validate_phase25_attribution`.
    """
    missing = [key for key in _PROTOCOLS if key not in configs]
    if missing:
        raise ValueError(f"faltan las configuraciones de los protocolos {missing}")
    for spec in PHASE25_SPECS:
        spec.validate(configs[spec.key])


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    seeds: list[int] = args.seeds
    out: Path = args.out
    jobs: int = args.jobs
    profile: str = args.profile
    # Opciones que no aplican al modo elegido: error de argumentos, antes de crear --out.
    if args.rule_effect_seeds is not None and not args.attribution:
        parser.error("--rule-effect-seeds sólo se usa con --attribution")
    if args.attribution and profile != PHASE25_ATTRIBUTION_PROFILE:
        parser.error(
            f"--attribution usa siempre el perfil pre-registrado {PHASE25_ATTRIBUTION_PROFILE}"
        )
    if args.histories and (args.smoke or args.attribution):
        parser.error("--histories sólo se usa en el modo protocolos")
    rule_effect_seeds: list[int] = (
        list(PHASE25_RULE_EFFECT_SEEDS)
        if args.rule_effect_seeds is None
        else args.rule_effect_seeds
    )
    try:
        validate_seeds(seeds)
    except ValueError as error:
        parser.error(f"--seeds: {error}")
    if rule_effect_seeds:
        try:
            validate_seeds(rule_effect_seeds)
        except ValueError as error:
            parser.error(f"--rule-effect-seeds: {error}")
    configs = attribution.PHASE25_PROTOCOL_CONFIGS  # se lee aquí: los tests lo reemplazan
    # (protocolo, condición, semilla) -> configuración, en orden fijo.
    planned: dict[tuple[str, str, int], SimulationConfig] = {}
    run_configs: dict[str, SimulationConfig] = {}  # las configuraciones validadas que se corren
    try:  # antes de crear --out: una configuración que no respeta su protocolo falla ya
        if args.attribution:
            run_configs = attribution.validate_phase25_attribution(
                seeds, PHASE25_CLAIMS, configs, rule_effect_seeds
            )
        else:
            _validate_configs(configs)
            run_configs = {key: configs[key] for key in _PROTOCOLS}
            planned = {
                (protocol, name, seed): config
                for protocol in _PROTOCOLS
                for seed in seeds
                for name, config in phase25_conditions(
                    protocol, replace(configs[protocol], seed=seed)
                ).items()
            }
    except ValueError as error:
        parser.error(f"configuración inválida: {error}")
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        parser.error(f"--out no es un directorio utilizable ({out}): {error}")
    if args.attribution:
        return _main_attribution(seeds, rule_effect_seeds, out, jobs, run_configs)
    total_ticks = PROFILES[profile].total_ticks
    if args.smoke:
        return _main_smoke(planned, profile, total_ticks, seeds, out, jobs, run_configs)
    return _main_protocols(planned, profile, total_ticks, seeds, out, jobs, args.histories)


def _labels(planned: Mapping[tuple[str, str, int], SimulationConfig]) -> list[tuple[str, str]]:
    """(protocolo, condición) en el orden de los protocolos y de `phase25_conditions`."""
    return list(dict.fromkeys((protocol, name) for protocol, name, _ in planned))


def _prefix(profile: str) -> str:
    """Prefijo de los archivos: el experimento y el perfil, para no mezclar corridas."""
    return f"{_NAME}_{profile}"


def _main_protocols(
    planned: Mapping[tuple[str, str, int], SimulationConfig],
    profile: str,
    total_ticks: int,
    seeds: list[int],
    out: Path,
    jobs: int,
    histories: bool,
) -> int:
    prefix = _prefix(profile)
    # Una configuración idéntica corre una vez; con --histories escribe un archivo por etiqueta.
    targets: dict[SimulationConfig, list[_HistoryTarget]] = {}
    for (protocol, name, seed), config in planned.items():
        group = targets.setdefault(config, [])
        if histories:
            path = out / f"{prefix}_{protocol}_{name}_seed{seed}_histories.json"
            header = {
                "profile": profile,
                "protocol": protocol,
                "condition": name,
                "seed": seed,
                "total_ticks": total_ticks,
                "config": config.to_dict(),
            }
            group.append((str(path), header))
    tasks: list[_Task] = [(config, total_ticks, tuple(group)) for config, group in targets.items()]
    outcomes = dict(zip(targets, map_in_order(_run_task, tasks, jobs), strict=True))
    summaries = {config: summary for config, (summary, _) in outcomes.items()}
    failures = sum(error is not None for _, error in outcomes.values())

    for protocol, name in _labels(planned):
        runs = [
            {
                "seed": seed,
                "config": planned[(protocol, name, seed)].to_dict(),
                "summary": report_to_dict(outcomes[planned[(protocol, name, seed)]][0]),
                "error": outcomes[planned[(protocol, name, seed)]][1],
            }
            for seed in seeds
        ]
        write_json(
            out / f"{prefix}_{protocol}_{name}.json",
            {
                "protocol": protocol,
                "condition": name,
                "profile": profile,
                "total_ticks": total_ticks,
                "seeds": seeds,
                "runs": runs,
            },
        )
    for seed in seeds:
        lines: list[str] = []
        for spec in PHASE25_SPECS:
            by_condition = {
                name: summaries[config]
                for (protocol, name, s), config in planned.items()
                if protocol == spec.key and s == seed
            }
            lines.append(spec.headline(spec.assemble(seed, total_ticks, by_condition)))
        print(f"semilla {seed}: " + " | ".join(lines))
    if failures:
        print(
            f"Aviso: {failures} corridas no pudieron escribir sus historiales; el error está en "
            "el JSON de su condición."
        )
    return 1 if failures else 0


def _main_smoke(
    planned: Mapping[tuple[str, str, int], SimulationConfig],
    profile: str,
    total_ticks: int,
    seeds: list[int],
    out: Path,
    jobs: int,
    configs: Mapping[str, SimulationConfig],
) -> int:
    """Prueba de humo de D56: sólo terminación, generación máxima y población final.

    Devuelve 1 si alguna corrida falló (su tipo y mensaje quedan en el registro) y 0 si no.
    """
    tasks = list(dict.fromkeys((config, total_ticks) for config in planned.values()))
    results = dict(zip(tasks, map_in_order(_smoke_task, tasks, jobs), strict=True))
    runs: list[dict[str, Any]] = []
    failures = 0
    print(f"Prueba de humo de la Fase II-B: perfil {profile} ({total_ticks} ticks)")
    for protocol, name in _labels(planned):
        parts: list[str] = []
        for seed in seeds:
            result = results[(planned[(protocol, name, seed)], total_ticks)]
            runs.append({"protocol": protocol, "condition": name, "seed": seed, **result})
            if result["termination"] == "error":
                failures += 1
                error = result["error"]
                parts.append(f"semilla {seed} falló ({error['type']}: {error['message']})")
            else:
                parts.append(
                    f"semilla {seed} terminó, población {result['final_agents']}, "
                    f"generación {result['max_generation']}"
                )
        print(f"  {protocol} {name}: " + "; ".join(parts))
    write_json(
        out / f"{_prefix(profile)}_smoke.json",
        {
            "profile": profile,
            "total_ticks": total_ticks,
            "seeds": seeds,
            "configs": {key: configs[key].to_dict() for key in _PROTOCOLS},
            "runs": runs,
        },
    )
    if failures:
        print(f"Aviso: {failures} corridas fallaron; el registro guarda el tipo y el mensaje.")
    return 1 if failures else 0


# --- Atribución --------------------------------------------------------------------------------


def _demography_line(condition: str, records: Mapping[int, Mapping[str, float]]) -> str:
    seeds = sorted(records)
    active = sum(records[s]["final_active_agents"] >= 1 for s in seeds)
    generation = median([records[s]["max_generation"] for s in seeds]) if seeds else 0.0
    parents = median([records[s]["effective_parents"] for s in seeds]) if seeds else 0.0
    return (
        f"    {condition}: con hojas activas {active}/{len(seeds)}, generación máxima mediana "
        f"{generation:g}, progenitores efectivos medianos {parents:.2f}"
    )


def _main_attribution(
    seeds: list[int],
    rule_effect_seeds: list[int],
    out: Path,
    jobs: int,
    configs: Mapping[str, SimulationConfig],
) -> int:
    """Atribución de C13-C20 (D56): JSON del `Phase25Report` y tabla en consola."""
    print(f"Atribución de la Fase II-B con el perfil pre-registrado {PHASE25_ATTRIBUTION_PROFILE}")
    if len(seeds) < PHASE25_MIN_VALID_PAIRS:
        print(
            f"Aviso: con menos de {PHASE25_MIN_VALID_PAIRS} semillas ninguna afirmación es "
            "evaluable; todos los estados serán NOT_OBSERVED."
        )
    report: Phase25Report = run_phase25_attribution(
        seeds=seeds,
        claims=PHASE25_CLAIMS,
        jobs=jobs,
        configs=configs,
        rule_effect_seeds=rule_effect_seeds,
    )
    claims = {c.claim_id: c for c in PHASE25_CLAIMS}
    thresholds: dict[str, float] = {}
    valid_pairs: dict[str, int] = {}
    for e in report.evaluations:  # la misma cuenta con la que la atribución decide el estado
        threshold, valid = claim_threshold_and_valid_seeds(
            claims[e.claim_id], e.comparison_values, seeds, e.excluded_seeds
        )
        thresholds[e.claim_id], valid_pairs[e.claim_id] = threshold, len(valid)
    data = report_to_dict(report)
    data["seeds"] = seeds
    data["rule_effect_seeds"] = rule_effect_seeds
    data["thresholds"] = thresholds
    data["valid_pairs"] = valid_pairs
    data["configs"] = {key: configs[key].to_dict() for key in sorted(configs)}
    write_json(out / f"{_prefix(PHASE25_ATTRIBUTION_PROFILE)}_attribution.json", data)

    def fmt(value: float | None) -> str:
        return "—" if value is None else f"{value:.5f}"

    print(
        f"{'Afirmación':<11}{'Estado':<14}{'p crudo':>9}{'p ajustado':>12}{'Mediana':>11}"
        f"{'Umbral':>11}{'Pares válidos':>15}{'Evaluable':>11}{'E4 interpretable':>18}"
        f"{'p E4':>9}"
    )
    for e in report.evaluations:
        print(
            f"{e.claim_id:<11}{e.status.value:<14}{fmt(e.p_value):>9}{fmt(e.p_adjusted):>12}"
            f"{e.median_difference:>11.5f}{thresholds[e.claim_id]:>11.5f}"
            f"{valid_pairs[e.claim_id]:>15}{('sí' if e.evaluable else 'no'):>11}"
            f"{('sí' if e.e4_interpretable else 'no'):>18}{fmt(e.e4_p_value):>9}"
        )
        for condition, records in e.demography.items():
            print(_demography_line(condition, records))
    print(
        "Los rule_effects son exploratorios (semillas "
        f"{rule_effect_seeds if rule_effect_seeds else 'ninguna'}) y están en el JSON."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
