"""Separación entre software e hipótesis (`experimental-suite`): la corrida por defecto."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect(*args: str) -> set[str]:
    # Sin PYTEST_ADDOPTS heredado: debe ser exactamente `python -m pytest` con la config del repo.
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"}
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *args],
        cwd=ROOT, capture_output=True, text=True, check=False, env=env,
    )  # fmt: skip
    assert done.returncode == 0, done.stdout + done.stderr
    return {line for line in done.stdout.splitlines() if "::" in line}


def test_corrida_por_defecto_excluye_empirical_y_slow() -> None:
    """Escenario "Corrida por defecto": `python -m pytest` no ejecuta `empirical` ni `slow`."""
    default = collect()
    assert default
    for marker in ("empirical", "slow"):
        marked = collect("-m", marker)
        assert marked  # existen tests con ese marcador...
        assert not default & marked  # ...y la corrida por defecto no los recolecta
