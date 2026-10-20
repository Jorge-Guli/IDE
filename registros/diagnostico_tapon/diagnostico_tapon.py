"""Diagnóstico demográfico del "Tapón de Matusalén" (Fase II-B, tarea 0.1, design D42).

Corre las configuraciones de la Fase II con abundancia (`resources_per_pattern = 40`) y las
semillas de calibración 0 a 9, y registra **sólo demografía**: nacimientos, muertes, edad al
morir y la proporción de vivos al final que nació antes del tick 1000. No calcula ninguna
métrica de afirmación (ni precisión, ni compuestos, ni cobertura).

Criterio fijado de antemano (design D42, decisión del 2026-10-20): la hipótesis se confirma si,
en al menos 8 de las 10 semillas de cada protocolo, más de la mitad de los agentes vivos en el
tick 2000 nació antes del tick 1000.

Uso: `python registros/diagnostico_tapon/diagnostico_tapon.py [--jobs 4] [--ticks 2000]`.
"""

import argparse
import json
import statistics
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

from ide.experiments.attribution import PHASE2_PROTOCOL_CONFIGS_ORIGINAL
from ide.simulation.engine import SimulationEngine

PROTOCOLS = ("002a", "003a")
SEEDS = tuple(range(10))
RESOURCES_PER_PATTERN = 40
CUTOFF_TICK = 1000
MIN_VIABLE_SEEDS = 8


def run_one(job: tuple[str, int, int]) -> dict[str, object]:
    protocol, seed, ticks = job
    config = replace(
        PHASE2_PROTOCOL_CONFIGS_ORIGINAL[protocol],
        resources_per_pattern=RESOURCES_PER_PATTERN,
        seed=seed,
    )
    engine = SimulationEngine(config)
    birth: dict[int, int] = {aid: 0 for aid in engine.agents}
    ages_at_death: list[int] = []
    deaths_by_tick: list[int] = []
    births_by_tick: list[int] = []
    alive = set(engine.agents)
    for tick in range(ticks):
        engine.step()
        now = set(engine.agents)
        born = sorted(now - alive)
        dead = sorted(alive - now)
        for aid in born:
            birth[aid] = tick
        ages_at_death.extend(tick - birth[aid] for aid in dead)
        births_by_tick.append(len(born))
        deaths_by_tick.append(len(dead))
        alive = now
    final = sorted(alive)
    old = sum(1 for aid in final if birth[aid] < CUTOFF_TICK)
    second_half = deaths_by_tick[CUTOFF_TICK:]
    return {
        "protocol": protocol,
        "seed": seed,
        "final_agents": len(final),
        "final_born_before_cutoff": old,
        "old_fraction": old / len(final) if final else None,
        "total_births": sum(births_by_tick),
        "total_deaths": sum(deaths_by_tick),
        "mean_deaths_per_tick_second_half": (
            sum(second_half) / len(second_half) if second_half else None
        ),
        "mean_births_per_tick_second_half": (
            sum(births_by_tick[CUTOFF_TICK:]) / len(second_half) if second_half else None
        ),
        "median_age_at_death": statistics.median(ages_at_death) if ages_at_death else None,
        "deaths_recorded": len(ages_at_death),
    }


def _fmt(value: object) -> str:
    return "-" if value is None else f"{value:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--ticks", type=int, default=2000)
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).with_name("diagnostico_tapon.json")
    )
    args = parser.parse_args()
    jobs = [(p, s, args.ticks) for p in PROTOCOLS for s in SEEDS]
    with Pool(args.jobs) as pool:
        runs = pool.map(run_one, jobs)
    verdicts = {}
    for protocol in PROTOCOLS:
        rows = [r for r in runs if r["protocol"] == protocol]
        aged = sum(1 for r in rows if r["old_fraction"] is not None and r["old_fraction"] > 0.5)
        verdicts[protocol] = {"aged_seeds": aged, "confirmed": aged >= MIN_VIABLE_SEEDS}
        for r in rows:
            frac = r["old_fraction"]
            print(
                f"{protocol} semilla {r['seed']}: vivos {r['final_agents']}, "
                f"nacidos antes del tick {CUTOFF_TICK} {r['final_born_before_cutoff']} "
                f"({'-' if frac is None else f'{frac:.2f}'}), nacimientos {r['total_births']}, "
                f"muertes {r['total_deaths']}, muertes/tick 2a mitad "
                f"{_fmt(r['mean_deaths_per_tick_second_half'])}, mediana de edad al morir "
                f"{r['median_age_at_death']}"
            )
        print(
            f"{protocol}: semillas envejecidas {aged}/10 -> confirmada: {aged >= MIN_VIABLE_SEEDS}"
        )
    confirmed = all(v["confirmed"] for v in verdicts.values())
    print(f"Hipótesis del Tapón de Matusalén: {'CONFIRMADA' if confirmed else 'REFUTADA'}")
    report = {
        "criterion": "confirmada si, en >= 8 de 10 semillas de cada protocolo, más de la mitad "
        "de los vivos en el tick final nació antes del tick 1000",
        "resources_per_pattern": RESOURCES_PER_PATTERN,
        "ticks": args.ticks,
        "seeds": list(SEEDS),
        "verdicts": verdicts,
        "confirmed": confirmed,
        "runs": runs,
    }
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
