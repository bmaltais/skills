#!/usr/bin/env bash
# Run a Python script via uv, in a venv scoped to the owning skill's own folder.
# Touches no system Python and no system-wide uv install: if `uv` isn't already
# on PATH, it's installed once into "$skill_dir/.uv" and reused from there.
#
# Usage: run_python.sh <skill-dir> <script.py> [args...]
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "usage: run_python.sh <skill-dir> <script.py> [args...]" >&2
  exit 2
fi

skill_dir="$1"; shift
script="$1"; shift

local_uv_dir="$skill_dir/.uv"
venv_dir="$skill_dir/.venv"

if command -v uv >/dev/null 2>&1; then
  uv_bin="$(command -v uv)"
elif [ -x "$local_uv_dir/uv" ]; then
  uv_bin="$local_uv_dir/uv"
else
  curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="$local_uv_dir" sh >&2
  uv_bin="$local_uv_dir/uv"
fi

[ -d "$venv_dir" ] || "$uv_bin" venv "$venv_dir" --quiet

exec "$uv_bin" run --python "$venv_dir/bin/python" "$script" "$@"
