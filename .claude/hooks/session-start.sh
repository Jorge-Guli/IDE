#!/bin/bash
# Instala las dependencias del proyecto al iniciar una sesión de Claude Code en la nube.
# Es idempotente: puede ejecutarse varias veces sin efectos secundarios.
set -euo pipefail

# Sólo en sesiones remotas (en la nube); en una máquina local no hace nada.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

if [ -f pyproject.toml ]; then
  # Con pyproject.toml: paquete editable con el extra de desarrollo.
  python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore -e ".[dev]"
else
  # Sin pyproject.toml (lista de respaldo): se instalan las mismas
  # herramientas del extra `dev`; mantener alineada con pyproject.toml.
  python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore \
    "numpy>=1.26" "pytest>=8.0" "pytest-cov>=5.0" "hypothesis>=6.100" \
    "ruff>=0.6" "pyright>=1.1.380" "py-spy>=0.3" "line_profiler>=4.1"
fi

# Pyright descarga su motor en la primera ejecución; se hace aquí para que quede cacheado.
pyright --version >/dev/null

# Precarga la CLI de OpenSpec, que valida los artefactos de especificación.
OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest --version >/dev/null 2>&1 || true
