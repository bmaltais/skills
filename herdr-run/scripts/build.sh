#!/usr/bin/env bash
# Build herdr-run and install it to ~/.local/bin. Build output stays outside the skill folder.
set -euo pipefail
cd "$(dirname "$0")/herdr-run"
export CARGO_TARGET_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/herdr-run-target"
cargo build --release -q
install -m755 "$CARGO_TARGET_DIR/release/herdr-run" "$HOME/.local/bin/herdr-run"
