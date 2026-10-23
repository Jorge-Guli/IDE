"""Caché persistente de corridas independientes (precisión 140 del design de la Fase II-B).

Los lotes largos de la Fase II-B (`exp25_runner --smoke`, el modo protocolos, `--attribution` y la
compuerta de viabilidad) se reanudan tras un corte: cada corrida guarda su resultado, serializado
en JSON, en un archivo propio apenas termina, y al relanzar el mismo comando las corridas
guardadas se cargan del disco en lugar de correrse. El caché no cambia ningún valor ni consume
generadores: una corrida es una función pura de su configuración, sus ticks y lo que se mide.

- **Clave.** `run_key` es el sha256 del JSON canónico (claves ordenadas, sin espacios) de la versión
  del formato, la huella del código del paquete `ide` y de NumPy, el modo (qué se mide), la
  configuración completa (`SimulationConfig.to_dict()`, que incluye la semilla), los ticks y un
  extra del modo (p. ej., las métricas pedidas). No depende de `PYTHONHASHSEED`. Cambiar el código
  invalida el caché entero.
- **Archivo.** `{clave}.json` con `format`, `key` y `result`; se escribe en un temporal del mismo
  directorio y se publica con `os.replace` (atómico). Un archivo ilegible, de otra versión, de otra
  clave o que no se decodifica se ignora y la corrida se recalcula y se reescribe.
- **Fallas.** Una corrida que termina en error no se guarda (su codificador devuelve `None`): al
  relanzar se reintenta. Un `OSError` al guardar no aborta el lote: avisa por `stderr` y la
  corrida se recalculará al relanzar.

La reunión de resultados es en el orden de las corridas, así que la salida no depende de `--jobs`
ni de qué corridas vinieron del caché.
"""

import functools
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

import ide
from ide.config import SimulationConfig
from ide.experiments.exp001_runner import map_in_order

__all__ = [
    "CACHE_FORMAT_VERSION",
    "DEFAULT_CACHE_NAME",
    "CachingCall",
    "RunCache",
    "code_fingerprint",
    "map_with_cache",
    "run_key",
    "sha256_file",
]

CACHE_FORMAT_VERSION = 1
DEFAULT_CACHE_NAME = ".cache_exp25"  # subdirectorio de `--out` cuando `--cache` no da directorio

# Errores con los que un resultado guardado no se puede decodificar: se recalcula.
_DECODE_ERRORS = (KeyError, TypeError, ValueError, AttributeError)


@functools.cache
def code_fingerprint() -> str:
    """sha256 de las fuentes `.py` del paquete `ide`, en orden de ruta relativa."""
    root = Path(ide.__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py"), key=lambda p: p.relative_to(root).as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def run_key(kind: str, config: SimulationConfig, total_ticks: int, extra: Any = None) -> str:
    """Clave determinista de una corrida: sha256 del JSON canónico de todo lo que la define."""
    payload = {
        "format": CACHE_FORMAT_VERSION,
        "code": code_fingerprint(),
        "numpy": np.__version__,
        "kind": kind,
        "config": config.to_dict(),
        "total_ticks": total_ticks,
        "extra": extra,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class RunCache:
    """Directorio con un archivo JSON por corrida terminada."""

    directory: Path

    def path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def load(self, key: str) -> Any | None:
        """El resultado guardado de `key`, o `None` si falta, está dañado o es de otra versión."""
        try:
            data = json.loads(self.path(key).read_text(encoding="utf-8"))
        except (OSError, ValueError):  # `UnicodeDecodeError` y `JSONDecodeError` son `ValueError`
            return None
        if not isinstance(data, dict):
            return None
        entry = cast(dict[str, Any], data)
        if (
            entry.get("format") != CACHE_FORMAT_VERSION
            or entry.get("key") != key
            or "result" not in entry
        ):
            return None
        return entry["result"]

    def store(self, key: str, result: Any) -> None:
        """Escritura atómica: temporal en el mismo directorio y `os.replace`."""
        self.directory.mkdir(parents=True, exist_ok=True)
        text = json.dumps(
            {"format": CACHE_FORMAT_VERSION, "key": key, "result": result}, sort_keys=True
        )
        descriptor, temporary = tempfile.mkstemp(
            dir=self.directory, prefix=f".{key}.", suffix=".tmp"
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path(key))
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise


@dataclass(frozen=True)
class CachingCall:
    """Unidad de trabajo que, al terminar, guarda su resultado codificado en el caché.

    Se ejecuta en el proceso que corre la corrida, así que cada resultado queda en disco apenas
    termina, sin esperar al resto del lote. `function` y `encode` son funciones de módulo (se
    envían a los procesos de `--jobs`). `encode(item, result)` devuelve `None` para no guardar.
    """

    function: Callable[[Any], Any]
    encode: Callable[[Any, Any], Any]
    directory: Path

    def __call__(self, keyed: tuple[str, Any]) -> Any:
        key, item = keyed
        result = self.function(item)
        try:
            encoded = self.encode(item, result)
            if encoded is not None:
                RunCache(self.directory).store(key, encoded)
        except OSError as error:  # el caché es una ayuda: su falla no aborta el lote
            message = f"Aviso: no se pudo guardar la corrida {key} en el caché: {error}"
            print(message, file=sys.stderr)
        return result


def map_with_cache(
    function: Callable[[Any], Any],
    items: Sequence[Any],
    keys: Sequence[str],
    jobs: int,
    cache: RunCache,
    encode: Callable[[Any, Any], Any],
    decode: Callable[[Any, Any], Any],
    mapper: Callable[[Callable[[Any], Any], Sequence[Any], int], list[Any]] = map_in_order,
) -> list[Any]:
    """`mapper(function, items, jobs)` que carga del caché las corridas ya guardadas.

    `decode(item, stored)` reconstruye el resultado; si lanza `KeyError`, `TypeError`,
    `ValueError` o `AttributeError`, lo guardado no sirve y la corrida se recalcula. Las demás
    corridas se reparten con `mapper` y cada una se guarda al terminar. Devuelve los resultados en
    el orden de `items`.
    """
    if len(keys) != len(items):
        raise ValueError("cada corrida necesita su clave")
    results: dict[int, Any] = {}
    for index, (item, key) in enumerate(zip(items, keys, strict=True)):
        stored = cache.load(key)
        if stored is None:
            continue
        try:
            results[index] = decode(item, stored)
        except _DECODE_ERRORS:
            continue
    pending = [index for index in range(len(items)) if index not in results]
    call = CachingCall(function, encode, cache.directory)
    fresh = mapper(call, [(keys[index], items[index]) for index in pending], jobs)
    results.update(zip(pending, fresh, strict=True))
    return [results[index] for index in range(len(items))]
