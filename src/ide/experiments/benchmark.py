"""Línea base de rendimiento: ticks por segundo con la configuración base del Exp 001.

Uso: `python -m ide.experiments.benchmark [--ticks 300] [--out benchmark.json]`.
"""

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

from ide.config import SimulationConfig
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
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"debe ser >= 1, recibido {value}")
    return value


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Línea base de rendimiento del motor IDE")
    parser.add_argument("--ticks", type=_positive_int, default=BENCHMARK_TICKS)
    parser.add_argument("--out", type=Path, default=Path("benchmark.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ticks: int = args.ticks
    out: Path = args.out
    config = SimulationConfig()
    rates = [measure_ticks_per_second(config, ticks) for _ in range(BENCHMARK_REPETITIONS)]
    report = {
        "median_ticks_per_second": statistics.median(rates),
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
