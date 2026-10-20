"""Línea base de rendimiento: ticks por segundo con la configuración base del Exp 001.

Uso: `python -m ide.experiments.benchmark [--ticks 300] [--out benchmark.json] [--compact-dna]`.

Sin opciones, la configuración es la base del Exp 001, sin cambios (`mode = "exp001"`).

Con `--compact-dna` mide el protocolo `002a` de la Fase II (`PHASE2_PROTOCOL_CONFIGS`) con
`enable_compact_dna` (R24), para registrar el costo de la Fase 0 de expresión
(`mode = "002a+compact_dna"`). Por defecto escribe en `benchmark_compact_dna.json`, para no pisar
la línea base. No usa la base del Exp 001 con evolución porque esa población se extingue antes de
los 300 ticks y la medición sería la de un mundo vacío.
"""

import argparse
import json
import platform
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

from ide.config import SimulationConfig
from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS
from ide.simulation.engine import SimulationEngine

BENCHMARK_TICKS = 300
BENCHMARK_REPETITIONS = 3


def measure_ticks_per_second(config: SimulationConfig, ticks: int) -> float:
    """Ticks por segundo de una corrida nueva; la construcción del motor no se cronometra."""
    engine = SimulationEngine(config)
    start = time.perf_counter()
    engine.run(ticks)
    return ticks / (time.perf_counter() - start)


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"se esperaba un entero, recibido {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"debe ser >= 1, recibido {value}")
    return value


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Línea base de rendimiento del motor IDE")
    parser.add_argument("--ticks", type=_positive_int, default=BENCHMARK_TICKS)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="archivo de salida (por defecto, benchmark.json o benchmark_compact_dna.json)",
    )
    parser.add_argument(
        "--compact-dna",
        action="store_true",
        help="mide el protocolo 002a de la Fase II con enable_compact_dna (R24)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ticks: int = args.ticks
    config = SimulationConfig()
    mode = "exp001"
    default_out = Path("benchmark.json")
    if args.compact_dna:
        config = replace(PHASE2_PROTOCOL_CONFIGS["002a"], enable_compact_dna=True)
        mode = "002a+compact_dna"
        default_out = Path("benchmark_compact_dna.json")
    out: Path = default_out if args.out is None else args.out
    rates = [measure_ticks_per_second(config, ticks) for _ in range(BENCHMARK_REPETITIONS)]
    report = {
        "median_ticks_per_second": statistics.median(rates),
        "mode": mode,
        "ticks_per_second": rates,
        "ticks": ticks,
        "repetitions": BENCHMARK_REPETITIONS,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "config": config.to_dict(),
    }
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Mediana: {report['median_ticks_per_second']:.1f} ticks/s ({out})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
