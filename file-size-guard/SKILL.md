---
name: file-size-guard
description: Install a pre-commit hook that blocks staged source files over ~5000 tokens. Use when the user wants file-size limits, smaller files for agents, less context bloat, or a deterministic check, or when /retro finds large files.
---

# File size guard

A deterministic cap on source file size, enforced by the commit hook. An `AGENTS.md` line is only a pointer; the hook is the rule.

[check-file-size.sh](check-file-size.sh) is the complete check: staged-index reads, `bytes/4` tokens, source-extension allowlist, default ignores (lockfiles, codegen, `.d.ts`, tests, build output), and the split-guidance failure message. Copy it verbatim; edit only to change the limit or ignores.

## Steps

### 1. Pick the runner

Find what the repo already uses: Husky (`.husky/`), lefthook (`lefthook.yml`), pre-commit (`.pre-commit-config.yaml`), nano-staged / lint-staged config, or a bare `.git/hooks/pre-commit`. Use that one. With none, use a native `core.hooksPath` directory (`.githooks/`) so the hook is versioned.

Done when you can name the runner and its config file.

### 2. Install the script

Copy `check-file-size.sh` to `scripts/check-file-size.sh` (or the repo's scripts directory) and `chmod +x` it.

Done when it runs from the repo root.

### 3. Audit existing files

Run `scripts/check-file-size.sh --all`. Every offender would block its next edit. Show the list to the user and ask, per file: split now, or grandfather it in `.file-size-guard-ignore` (one glob per line, `#` comments).

Done when `--all` exits 0, or the user has decided on every listed file.

### 4. Wire it in

Add one command to the runner, as the pre-commit stage, running `scripts/check-file-size.sh`. Keep any existing entries; skip the edit if the command is already present, so reinstalling changes nothing. The script reads the index itself, so wire it as a whole-repo command, not a per-file one.

Done when the runner config contains the command exactly once.

### 5. Prove it blocks

Stage a throwaway source file of 20001+ bytes, run `git commit`, and confirm the commit is rejected with the split message. Unstage and delete the file. Then stage a small source file and confirm the hook passes.

Done when you have seen one rejection and one pass.

### 6. Point at it

Add one line to `AGENTS.md` / `CLAUDE.md`, if either exists:

```markdown
- Source files stay under ~5000 tokens (bytes/4); the pre-commit hook enforces it. Split before finishing.
```

## Tuning

- Limit: set `FILE_SIZE_GUARD_LIMIT` in the hook command (`FILE_SIZE_GUARD_LIMIT=3000 scripts/check-file-size.sh`).
- Languages: extend `SOURCE_EXT` in the script.
- Ignores: `.file-size-guard-ignore` for repo-specific paths, `DEFAULT_IGNORE` for universal ones.
