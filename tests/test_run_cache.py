"""Tests del caché persistente de corridas (precisión 140 del design de la Fase II-B).

Un lote largo (`exp25_runner --smoke`, protocolos, `--attribution` y la compuerta de viabilidad)
se reanuda tras un corte: cada corrida guarda su resultado en un archivo propio apenas termina y,
al relanzar el mismo comando, las corridas guardadas se cargan del disco. La salida (JSON y
consola) es byte a byte la de una corrida de una vez, para cualquier `--jobs`.
"""

import dataclasses
import json
import multiprocessing
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from ide.config import SimulationConfig
from ide.experiments import attribution, exp25_runner, phase25_viability, run_cache
from ide.experiments.attribution import (
    PHASE25_CLAIMS,
    PHASE25_PROTOCOL_CONFIGS,
    Phase25RunRecord,
    run_phase25_attribution,
)
from ide.experiments.exp001_runner import PROFILES, Profile
from ide.experiments.exp25_runner import main
from ide.experiments.run_cache import CACHE_FORMAT_VERSION, RunCache, run_key

SMALL = {"grid_width": 10, "grid_height": 10, "num_agents": 12}
TINY_TICKS = 12

requires_fork = pytest.mark.skipif(
    multiprocessing.get_start_method() != "fork",
    reason="los parches del test sólo llegan a los procesos hijos con fork",
)


@pytest.fixture
def tiny(monkeypatch: pytest.MonkeyPatch) -> str:
    """Perfil corto y protocolos chicos, sin tocar el pre-registro versionado."""
    monkeypatch.setitem(PROFILES, "tiny", Profile(TINY_TICKS, 4, 8, 4))
    small = {
        key: dataclasses.replace(config, **SMALL)
        for key, config in PHASE25_PROTOCOL_CONFIGS.items()
    }
    monkeypatch.setattr(attribution, "PHASE25_PROTOCOL_CONFIGS", small)
    return "tiny"


def snapshot(directory: Path) -> dict[str, bytes]:
    """Contenido de los archivos de salida (sin el caché)."""
    return {p.name: p.read_bytes() for p in sorted(directory.iterdir()) if p.is_file()}


def cache_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.json"))


def run_cli(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = main(argv)
    return code, capsys.readouterr().out


class _Killed(BaseException):
    """Corte simulado del contenedor: no es `Exception`, así que nadie lo captura."""


def kill_after(monkeypatch: pytest.MonkeyPatch, stores: int) -> None:
    """El proceso "muere" justo después de guardar `stores` corridas en el caché."""
    original = RunCache.store
    done: list[str] = []

    def store(self: RunCache, key: str, result: Any) -> None:
        original(self, key, result)
        done.append(key)
        if len(done) >= stores:
            raise _Killed

    monkeypatch.setattr(RunCache, "store", store)


# --- Claves y archivos -------------------------------------------------------------------------


def test_claves_deterministas_y_distintas() -> None:
    config = dataclasses.replace(PHASE25_PROTOCOL_CONFIGS["25a"], **SMALL)
    key = run_key("exp25_smoke", config, 10)
    assert key == run_key("exp25_smoke", dataclasses.replace(config), 10)
    assert len(key) == 64 and all(c in "0123456789abcdef" for c in key)
    others = {
        run_key("exp25_smoke", dataclasses.replace(config, seed=config.seed + 1), 10),
        run_key("exp25_smoke", dataclasses.replace(config, num_agents=13), 10),
        run_key("exp25_smoke", dataclasses.replace(config, enable_predation=False), 10),
        run_key("exp25_smoke", config, 11),
        run_key("exp25_protocol", config, 10),
        run_key("exp25_smoke", config, 10, extra=["a"]),
        run_key("exp25_smoke", config, 10, extra=["b"]),
    }
    assert key not in others
    assert len(others) == 7


def test_clave_estable_entre_procesos() -> None:
    """La clave no depende de `PYTHONHASHSEED`: se calcula igual en otro intérprete."""
    import os
    import subprocess
    import sys

    code = (
        "import dataclasses\n"
        "from ide.experiments.attribution import PHASE25_PROTOCOL_CONFIGS\n"
        "from ide.experiments.run_cache import run_key\n"
        "c = dataclasses.replace(PHASE25_PROTOCOL_CONFIGS['25d'], seed=7)\n"
        "print(run_key('exp25_protocol', c, 12, extra=['x']))\n"
    )
    keys = set()
    for hashseed in ("0", "1"):
        env = {**os.environ, "PYTHONHASHSEED": hashseed}
        result = subprocess.run(
            [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
        )
        keys.add(result.stdout.strip())
    config = dataclasses.replace(PHASE25_PROTOCOL_CONFIGS["25d"], seed=7)
    assert keys == {run_key("exp25_protocol", config, 12, extra=["x"])}


def test_guardar_y_cargar(tmp_path: Path) -> None:
    cache = RunCache(tmp_path / "c")
    assert cache.load("a" * 64) is None  # sin directorio todavía
    cache.store("a" * 64, {"x": 1.5, "y": [1, 2], "z": None})
    assert cache.load("a" * 64) == {"x": 1.5, "y": [1, 2], "z": None}
    data = json.loads(cache.path("a" * 64).read_text())
    assert data["format"] == CACHE_FORMAT_VERSION and data["key"] == "a" * 64
    assert [p.name for p in (tmp_path / "c").iterdir()] == [f"{'a' * 64}.json"]  # sin temporales


@pytest.mark.parametrize(
    "content",
    [
        "",
        "{",
        "[1, 2]",
        '{"format": 999, "key": "KEY", "result": 1}',
        '{"format": FORMAT, "key": "otra", "result": 1}',
        '{"format": FORMAT, "key": "KEY"}',
        "\xff\xfe",
    ],
)
def test_archivo_corrupto_o_de_otra_version_se_ignora(tmp_path: Path, content: str) -> None:
    cache = RunCache(tmp_path)
    key = "b" * 64
    text = content.replace("FORMAT", str(CACHE_FORMAT_VERSION)).replace("KEY", key)
    cache.path(key).write_bytes(text.encode("latin-1"))
    assert cache.load(key) is None


# --- Prueba de humo ----------------------------------------------------------------------------


def smoke_argv(tiny: str, out: Path, jobs: str) -> list[str]:
    return ["--smoke", "--profile", tiny, "--seeds", "7", "--jobs", jobs, "--out", str(out)]


def test_humo_reanudado_es_identico(
    tmp_path: Path,
    tiny: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Correr parte, "matar", relanzar: la misma salida que una corrida de una vez sin caché."""
    once = tmp_path / "once"
    code, console = run_cli(smoke_argv(tiny, once, "1"), capsys)
    assert code == 0
    out, cache = tmp_path / "resumed", tmp_path / "cache"
    argv = [*smoke_argv(tiny, out, "1"), "--cache", str(cache)]
    with monkeypatch.context() as patch:
        kill_after(patch, 5)
        with pytest.raises(_Killed):
            main(argv)
    capsys.readouterr()
    assert len(cache_files(cache)) == 5
    assert not (out / f"exp25_{tiny}_smoke.json").exists()
    executed: list[SimulationConfig] = []
    original = exp25_runner._smoke_engine

    def counting(config: SimulationConfig) -> Any:
        executed.append(config)
        return original(config)

    monkeypatch.setattr(exp25_runner, "_smoke_engine", counting)
    resumed_code, resumed_console = run_cli(argv, capsys)
    assert (resumed_code, resumed_console) == (code, console)
    assert snapshot(out) == snapshot(once)
    total = len(cache_files(cache))
    assert len(executed) == total - 5  # las 5 guardadas no se corren de nuevo
    executed.clear()
    assert run_cli(argv, capsys) == (code, console)  # todo del caché: nada corre
    assert executed == []
    assert snapshot(out) == snapshot(once)


@requires_fork
def test_humo_con_cache_identico_para_cualquier_jobs(
    tmp_path: Path, tiny: str, capsys: pytest.CaptureFixture[str]
) -> None:
    reference = tmp_path / "ref"
    expected = run_cli(smoke_argv(tiny, reference, "1"), capsys)
    for jobs in ("1", "2"):
        out = tmp_path / f"jobs{jobs}"
        argv = [*smoke_argv(tiny, out, jobs), "--cache", str(tmp_path / f"cache{jobs}")]
        assert run_cli(argv, capsys) == expected  # caché vacío
        assert snapshot(out) == snapshot(reference)
        assert run_cli(argv, capsys) == expected  # todo del caché
        assert snapshot(out) == snapshot(reference)
    names = [p.name for p in cache_files(tmp_path / "cache1")]
    assert names == [p.name for p in cache_files(tmp_path / "cache2")]


def test_cache_por_defecto_dentro_de_out(
    tmp_path: Path, tiny: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--cache` sin directorio usa `--out/.cache_exp25`; sin `--cache` no hay caché."""
    out = tmp_path / "out"
    assert run_cli(smoke_argv(tiny, out, "1"), capsys)[0] == 0
    assert not (out / ".cache_exp25").exists()
    assert run_cli([*smoke_argv(tiny, out, "1"), "--cache"], capsys)[0] == 0
    assert cache_files(out / ".cache_exp25")


def test_humo_archivo_corrupto_se_recalcula(
    tmp_path: Path,
    tiny: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out, cache = tmp_path / "out", tmp_path / "cache"
    argv = [*smoke_argv(tiny, out, "1"), "--cache", str(cache)]
    expected = run_cli(argv, capsys)
    before = snapshot(out)
    files = cache_files(cache)
    files[0].write_text("{ corrupto")
    data = json.loads(files[1].read_text())
    files[1].write_text(json.dumps({**data, "format": CACHE_FORMAT_VERSION + 1}))
    data = json.loads(files[2].read_text())
    files[2].write_text(json.dumps({**data, "result": {"termination": "finished"}}))
    executed: list[SimulationConfig] = []
    original = exp25_runner._smoke_engine

    def counting(config: SimulationConfig) -> Any:
        executed.append(config)
        return original(config)

    monkeypatch.setattr(exp25_runner, "_smoke_engine", counting)
    assert run_cli(argv, capsys) == expected
    assert snapshot(out) == before
    assert len(executed) == 3  # sólo las tres dañadas
    assert json.loads(files[0].read_text())["format"] == CACHE_FORMAT_VERSION  # reescrita


def test_humo_no_cachea_corridas_fallidas(
    tmp_path: Path,
    tiny: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Una corrida que falla no se guarda: al relanzar se reintenta."""
    out, cache = tmp_path / "out", tmp_path / "cache"
    argv = [*smoke_argv(tiny, out, "1"), "--cache", str(cache)]
    original = exp25_runner._smoke_engine
    target = dataclasses.replace(attribution.PHASE25_PROTOCOL_CONFIGS["25b"], seed=7)  # `full`

    def failing(config: SimulationConfig) -> Any:
        if config == target:
            raise RuntimeError("falla transitoria")
        return original(config)

    with monkeypatch.context() as patch:
        patch.setattr(exp25_runner, "_smoke_engine", failing)
        assert run_cli(argv, capsys)[0] == 1
    failed = len(cache_files(cache))
    reference = tmp_path / "ref"
    expected = run_cli(smoke_argv(tiny, reference, "1"), capsys)
    assert run_cli(argv, capsys) == expected
    assert snapshot(out) == snapshot(reference)
    assert len(cache_files(cache)) == failed + 1


# --- Protocolos e historiales ------------------------------------------------------------------


def protocol_argv(tiny: str, out: Path, jobs: str, *extra: str) -> list[str]:
    return ["--profile", tiny, "--seeds", "7", "--jobs", jobs, "--out", str(out), *extra]


@pytest.mark.parametrize("histories", [False, True])
def test_protocolos_reanudados_son_identicos(
    tmp_path: Path,
    tiny: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    histories: bool,
) -> None:
    extra = ("--histories",) if histories else ()
    once = tmp_path / "once"
    expected = run_cli(protocol_argv(tiny, once, "1", *extra), capsys)
    assert expected[0] == 0
    out, cache = tmp_path / "out", tmp_path / "cache"
    argv = protocol_argv(tiny, out, "1", *extra, "--cache", str(cache))
    with monkeypatch.context() as patch:
        kill_after(patch, 4)
        with pytest.raises(_Killed):
            main(argv)
    capsys.readouterr()
    executed: list[SimulationConfig] = []
    original = exp25_runner.run_phase25_condition_histories

    def counting(config: SimulationConfig, total_ticks: int) -> Any:
        executed.append(config)
        return original(config, total_ticks)

    monkeypatch.setattr(exp25_runner, "run_phase25_condition_histories", counting)
    assert run_cli(argv, capsys) == expected
    assert snapshot(out) == snapshot(once)
    assert len(executed) == len(cache_files(cache)) - 4
    executed.clear()
    assert run_cli(argv, capsys) == expected
    assert executed == []
    assert snapshot(out) == snapshot(once)


def test_historial_faltante_o_truncado_se_recalcula(
    tmp_path: Path,
    tiny: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out, cache = tmp_path / "out", tmp_path / "cache"
    plain = protocol_argv(tiny, out, "1", "--cache", str(cache))
    argv = [*plain, "--histories"]
    expected = run_cli(argv, capsys)
    before = snapshot(out)
    truncated = out / f"exp25_{tiny}_25b_full_seed7_histories.json"
    truncated.write_bytes(truncated.read_bytes()[:100])
    (out / f"exp25_{tiny}_25c_drift_seed7_histories.json").unlink()
    executed: list[SimulationConfig] = []
    original = exp25_runner.run_phase25_condition_histories

    def counting(config: SimulationConfig, total_ticks: int) -> Any:
        executed.append(config)
        return original(config, total_ticks)

    monkeypatch.setattr(exp25_runner, "run_phase25_condition_histories", counting)
    assert run_cli(argv, capsys) == expected
    assert snapshot(out) == before
    assert len(executed) == 2
    # Un resumen guardado sin historiales no sirve para un lanzamiento con --histories.
    other = tmp_path / "other"
    executed.clear()
    first = run_cli(protocol_argv(tiny, other, "1", "--cache", str(tmp_path / "c2")), capsys)
    runs = len(executed)
    executed.clear()
    argv2 = protocol_argv(tiny, other, "1", "--cache", str(tmp_path / "c2"), "--histories")
    assert run_cli(argv2, capsys)[0] == first[0]
    assert len(executed) == runs


@requires_fork
def test_protocolos_con_cache_identicos_para_cualquier_jobs(
    tmp_path: Path, tiny: str, capsys: pytest.CaptureFixture[str]
) -> None:
    reference = tmp_path / "ref"
    expected = run_cli(protocol_argv(tiny, reference, "1", "--histories"), capsys)
    for jobs in ("1", "2"):
        out = tmp_path / f"jobs{jobs}"
        argv = protocol_argv(tiny, out, jobs, "--histories", "--cache", str(tmp_path / "c"))
        assert run_cli(argv, capsys) == expected
        assert snapshot(out) == snapshot(reference)


# --- Atribución --------------------------------------------------------------------------------


@pytest.fixture
def small_attribution(monkeypatch: pytest.MonkeyPatch) -> dict[str, SimulationConfig]:
    monkeypatch.setitem(PROFILES, "phase25", Profile(TINY_TICKS, 0, 1, 1))
    return {
        key: dataclasses.replace(config, **SMALL)
        for key, config in PHASE25_PROTOCOL_CONFIGS.items()
    }


def test_atribucion_desde_el_cache_da_el_mismo_reporte(
    tmp_path: Path,
    small_attribution: dict[str, SimulationConfig],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claims = [c for c in PHASE25_CLAIMS if c.protocol in ("25a", "25d")]
    kwargs: dict[str, Any] = {
        "seeds": (42, 43),
        "claims": claims,
        "configs": small_attribution,
        "rule_effect_seeds": (),
    }
    expected = run_phase25_attribution(**kwargs)
    cache = tmp_path / "cache"
    with monkeypatch.context() as patch:
        kill_after(patch, 3)
        with pytest.raises(_Killed):
            run_phase25_attribution(**kwargs, cache_dir=cache)
    executed: list[SimulationConfig] = []
    original = attribution._execute_phase25_run

    def counting(job: Any) -> Phase25RunRecord:
        executed.append(job[0])
        return original(job)

    monkeypatch.setattr(attribution, "_execute_phase25_run", counting)
    resumed = run_phase25_attribution(**kwargs, cache_dir=cache)
    assert repr(resumed) == repr(expected)
    assert resumed == expected
    assert len(executed) == len(cache_files(cache)) - 3
    executed.clear()
    again = run_phase25_attribution(**kwargs, cache_dir=cache)
    assert executed == []
    assert repr(again) == repr(expected)


def test_registro_de_atribucion_ida_y_vuelta(
    small_attribution: dict[str, SimulationConfig],
) -> None:
    config = dataclasses.replace(small_attribution["25d"], seed=3)
    metrics = tuple(sorted({c.metric for c in PHASE25_CLAIMS}))
    record = attribution._execute_phase25_run((config, TINY_TICKS, metrics))
    item = (config, TINY_TICKS, metrics)
    stored = json.loads(json.dumps(attribution._encode_phase25_record(item, record)))
    decoded = attribution._decode_phase25_record(item, stored)
    assert decoded == record
    assert repr(decoded) == repr(record)
    with pytest.raises((KeyError, TypeError, ValueError)):
        attribution._decode_phase25_record(item, {**stored, "metrics": {}})


@requires_fork
def test_cli_de_atribucion_con_cache(
    tmp_path: Path,
    tiny: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(PROFILES, "phase25", PROFILES[tiny])
    base = ["--attribution", "--seeds", "7", "--rule-effect-seeds"]
    reference = tmp_path / "ref"
    expected = run_cli([*base, "--jobs", "1", "--out", str(reference)], capsys)
    for jobs in ("1", "2"):
        out = tmp_path / f"jobs{jobs}"
        argv = [*base, "--jobs", jobs, "--out", str(out), "--cache", str(tmp_path / "c")]
        assert run_cli(argv, capsys) == expected
        assert snapshot(out) == snapshot(reference)


# --- Compuerta de viabilidad -------------------------------------------------------------------


def test_viabilidad_reanudada_es_identica(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_configs: Callable[..., Any] = attribution.phase25_protocol_configs

    def small_configs(*abundance: int) -> dict[str, SimulationConfig]:
        return {k: dataclasses.replace(c, **SMALL) for k, c in original_configs(*abundance).items()}

    monkeypatch.setattr(attribution, "phase25_protocol_configs", small_configs)
    grid = phase25_viability.VIABILITY_GRID[:2]
    kwargs: dict[str, Any] = {"total_ticks": 6, "jobs": 1, "seeds": (0, 1), "grid": grid}
    expected = phase25_viability.run_viability(**kwargs)
    cache = tmp_path / "cache"
    with monkeypatch.context() as patch:
        kill_after(patch, 7)
        with pytest.raises(_Killed):
            phase25_viability.run_viability(**kwargs, cache_dir=cache)
    executed: list[Any] = []
    original = phase25_viability.demography

    def counting(task: Any) -> Any:
        executed.append(task)
        return original(task)

    monkeypatch.setattr(phase25_viability, "demography", counting)
    resumed = phase25_viability.run_viability(**kwargs, cache_dir=cache)
    assert resumed == expected
    assert phase25_viability.report_to_json(resumed) == phase25_viability.report_to_json(expected)
    assert len(executed) == len(cache_files(cache)) - 7


@pytest.mark.parametrize(
    ("extra", "expected"),
    [([], None), (["--cache"], "OUT/.cache_viability"), (["--cache", "DIR"], "DIR")],
)
def test_cli_de_viabilidad_pasa_el_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra: list[str], expected: str | None
) -> None:
    received: list[Path | None] = []
    report = phase25_viability.ViabilityReport(6, (0,), (), None, None, ((1, 1),))

    def fake(*args: Any, cache_dir: Path | None = None, **kwargs: Any) -> Any:
        received.append(cache_dir)
        return report

    monkeypatch.setattr(phase25_viability, "run_viability", fake)
    monkeypatch.setattr(phase25_viability, "_print_configurations", lambda _: None)
    out = tmp_path / "v.json"
    argv = ["--ticks", "6", "--out", str(out)]
    argv += [e.replace("DIR", str(tmp_path / "d")) for e in extra]
    assert phase25_viability.main(argv) == 0
    paths = {"OUT": str(tmp_path), "DIR": str(tmp_path / "d")}
    want = None
    if expected is not None:
        want = Path(expected.replace("OUT", paths["OUT"]).replace("DIR", paths["DIR"]))
    assert received == [want]


def test_modulo_sin_generadores() -> None:
    """El caché no importa NumPy aleatorio ni crea generadores: no cambia ningún valor."""
    source = Path(run_cache.__file__).read_text(encoding="utf-8")
    assert "random" not in source
