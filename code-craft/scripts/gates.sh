#!/usr/bin/env bash
# Detect and run this project's own quality gates.
# exit 0 = all passed | 1 = a gate failed | 3 = no gate found
# Usage: gates.sh [dir]   (default: current directory)
set -uo pipefail
cd "${1:-.}" || exit 1

ran=() failed=()

run() { # run <label> <cmd...>
  local label=$1; shift
  echo "== $label: $*"
  if "$@"; then ran+=("$label"); else ran+=("$label"); failed+=("$label"); fi
}

has() { command -v "$1" >/dev/null 2>&1; }
pkg() { grep -q "\"$1\" *:" package.json; } # ponytail: good enough; a dependency named "lint"/"test" would false-positive

if [ -f package.json ]; then
  runner=npm; [ -f pnpm-lock.yaml ] && runner=pnpm; [ -f yarn.lock ] && runner=yarn
  [ -f tsconfig.json ] && run tsc npx --no-install tsc --noEmit
  pkg lint && run lint "$runner" run lint
  pkg test && run test "$runner" run test
fi

if [ -f pyproject.toml ] || [ -f setup.py ] || compgen -G "*.py" >/dev/null; then
  has ruff && run ruff ruff check .
  { [ -f pyproject.toml ] && grep -q black pyproject.toml; } && has black && run black black --check .
  { [ -f pyproject.toml ] && grep -q mypy pyproject.toml; } && has mypy && run mypy mypy .
  has pytest && [ -n "$(find . -name 'test_*.py' -o -name '*_test.py' | head -1)" ] && run pytest pytest -q
fi

[ -f Cargo.toml ] && has cargo && { run clippy cargo clippy -- -D warnings; run cargo-test cargo test; }
[ -f go.mod ] && has go && { run vet go vet ./...; run go-test go test ./...; }

if [ ${#ran[@]} -eq 0 ]; then
  echo "NO GATES FOUND — no type-checker, linter, or test command detected. Report this explicitly."
  exit 3
fi
if [ ${#failed[@]} -gt 0 ]; then
  echo "FAILED: ${failed[*]}  (ran: ${ran[*]})"
  exit 1
fi
echo "PASSED: ${ran[*]}"
