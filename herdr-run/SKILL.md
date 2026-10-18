---
name: herdr-run
description: Run a long or user-visible command (install, build, server, test run) in a herdr pane the user can watch, and get its tail and exit status back. Use when HERDR_ENV=1.
---

`herdr-run "<command>"` runs the command in one reused herdr pane, waits, prints the last 40 lines, then `exit=<code>`, and exits with the command's status.

| Flag | Effect |
|---|---|
| `--timeout MS` | Wait at most MS (default 600000). On timeout it prints the pane id and exits 124; the command keeps running. |
| `--lines N` | Print the last N lines. |
| `--fresh` | Open a new pane instead of reusing the remembered one. |

Servers and other long-lived processes: use `--fresh` for each, a short `--timeout`, and tell the user which pane they run in.

Quick read-only commands go through Bash directly.

If `herdr-run` is missing, `scripts/build.sh` in this folder builds it into `~/.local/bin`. The Rust source is in `scripts/herdr-run`.
