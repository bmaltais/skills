#!/usr/bin/env bash
# file-size-guard: fail when a staged source file exceeds the token limit.
# Tokens ~= bytes / 4. Reads the git index, never the working tree.
#
#   check-file-size.sh          check staged files (pre-commit)
#   check-file-size.sh --all    check every tracked file in the index (audit)
#
# Env: FILE_SIZE_GUARD_LIMIT (default 5000)
# Extra ignores: one glob per line in .file-size-guard-ignore at the repo root.

set -euo pipefail

LIMIT="${FILE_SIZE_GUARD_LIMIT:-5000}"
cd "$(git rev-parse --show-toplevel)"

SOURCE_EXT='ts|tsx|js|jsx|mjs|cjs|vue|svelte|astro|py|rb|go|rs|java|kt|kts|swift|c|h|cc|cpp|hpp|cs|php|scala|ex|exs|lua|sh|bash|zsh|dart|zig|qml'

# Paths that are not agent-authored: deps, build output, codegen, lockfiles, tests.
DEFAULT_IGNORE=(
  'node_modules/*' '*/node_modules/*' 'vendor/*' '*/vendor/*'
  'dist/*' '*/dist/*' 'build/*' '*/build/*' '.next/*' '*/.next/*'
  '*.min.*' '*.gen.*' '*.generated.*' '*_generated.*' '*.pb.go' '*_pb2.py'
  '*.d.ts' '*.lock' '*-lock.*' 'migrations/*' '*/migrations/*'
  '*.test.*' '*.spec.*' '*_test.*' 'test_*' '__tests__/*' '*/__tests__/*'
  'tests/*' '*/tests/*' '__snapshots__/*' '*/__snapshots__/*'
)

IGNORE=("${DEFAULT_IGNORE[@]}")
if [[ -f .file-size-guard-ignore ]]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    IGNORE+=("$line")
  done < .file-size-guard-ignore
fi

is_ignored() {
  local path="$1" glob
  for glob in "${IGNORE[@]}"; do
    # shellcheck disable=SC2254
    case "$path" in $glob) return 0 ;; esac
  done
  return 1
}

if [[ "${1:-}" == "--all" ]]; then
  list() { git ls-files -z; }
else
  list() { git diff --cached --name-only --diff-filter=ACM -z; }
fi

offenders=()
while IFS= read -r -d '' path; do
  [[ "$path" =~ \.($SOURCE_EXT)$ ]] || continue
  is_ignored "$path" && continue
  bytes=$(git cat-file -s ":$path" 2>/dev/null) || continue
  tokens=$((bytes / 4))
  (( tokens > LIMIT )) && offenders+=("$path|$tokens")
done < <(list)

(( ${#offenders[@]} == 0 )) && exit 0

{
  echo "file-size-guard: source files over the ${LIMIT}-token limit (tokens ~= bytes/4):"
  for o in "${offenders[@]}"; do
    echo "  ${o%%|*}  (~${o##*|} tokens)"
  done
  cat <<MSG

Split each file before committing:
  1. Start with a leaf: a cluster of functions nothing else in the file calls. Move it
     to its own file, named for what it does.
  2. If types/interfaces/constants dominate the size, move them to a sibling types file.
  3. If the file mixes concerns across its public API, split along that surface and
     re-export from the original path, or update the callers.
  4. Keep the new files focused; a grab-bag like utils2 just moves the problem.

Then re-stage the new files and commit again.
Generated or non-authored file? Add its path or glob to .file-size-guard-ignore.
MSG
} >&2
exit 1
