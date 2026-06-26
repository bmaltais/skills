---
name: implement
description: Pick up a GitHub issue tagged ready-for-agent and implement it. Reads the agent brief, explores the codebase, writes the fix or feature, verifies all acceptance criteria, and opens a linked PR. Use when the user says "pick up an issue", "work on a ready-for-agent issue", "implement issue #N", "fix issue #N", "/implement", or wants to action a pre-triaged issue.
---

# Implement

Pick up a `ready-for-agent` issue from the tracker, implement it against the agent brief, verify every acceptance criterion, and ship a PR.

The **agent brief comment** is the contract. The original issue body is background. If they conflict, the brief wins.

## Invocation

```
/implement          — list ready-for-agent issues and let maintainer pick
/implement #N       — go straight to issue N
```

## Phase 1 — Discover

If no issue number was given, query the tracker:

```
gh issue list --label ready-for-agent --state open --json number,title,createdAt
```

Show issues oldest-first. Let the maintainer pick. If exactly one issue exists, confirm and proceed.

## Phase 2 — Brief

Fetch the full issue:

```
gh issue view N --comments --json number,title,body,labels,comments,createdAt,author
```

Find the agent brief comment — it will contain the heading `## Agent Brief`. This is the contract.

Extract:
- **Category** (`bug` or `enhancement`)
- **Summary** — one-line description of the goal
- **Current behavior** — what the system does now
- **Desired behavior** — what it should do after
- **Key interfaces** — types, functions, config shapes to look for or modify
- **Acceptance criteria** — the checklist; these are your definition of done
- **Out of scope** — do not touch these

If no agent brief comment exists, use the issue body. Flag this to the maintainer: brief-less issues are harder to implement correctly.

## Phase 3 — Explore

Use the key interfaces from the brief to orient codebase exploration. Do not read everything — find the seam.

For each key interface named in the brief:
1. `grep` for the type/function name to locate the relevant files
2. Read the implementation and callers
3. Understand what would need to change to reach the desired behavior

For large codebases (>20 relevant files), spawn an exploration sub-agent:

```
Agent(
  prompt = "Explore the codebase for: <summary>. Key interfaces: <list>. Return: affected files, relevant types/functions, your understanding of what needs to change.",
  subagent_type = "Explore"
)
```

Do not start implementing until exploration is complete.

## Phase 4 — Plan

Before writing code, map each acceptance criterion to a concrete implementation step. State the plan in one short paragraph or bullet list — this is for your own orientation, not a user-facing document. Identify any risks or ambiguities and surface them to the maintainer now, before making changes.

If the brief is under-specified for any criterion, ask one targeted question. Do not ask more than needed — if you can make a reasonable judgment call, make it and document it in the PR body.

## Phase 5 — Implement

### Branch

Create a branch before touching any files. **Always branch from `main` explicitly** — if the current HEAD is not `main`, branching without specifying the base silently inherits ancestor commits that will appear in the PR diff:

```
git checkout main
git pull
git checkout -b fix/issue-N-short-title    # for bugs
git checkout -b feat/issue-N-short-title   # for enhancements
```

Never commit directly to main.

**Pre-push diff check (mandatory):** Before running `git push`, confirm the PR will contain only your intended commits:

```
git log --oneline main...HEAD
```

If any commits appear that you did not author in this session, stop. Rebase off the stale ancestor before pushing:

**Multi-account auth check:** In multi-account environments, verify the correct GitHub account is active before pushing — a wrong active account silently causes a 403:

```
gh auth status
```

If the wrong account is active, switch before pushing: `gh auth switch --user <account>`

```
git rebase --onto main <last-unwanted-commit> HEAD
```

### Write the code

- Implement what the brief's **desired behavior** describes
- Respect the **out of scope** list — do not touch adjacent things
- Follow the project's existing conventions (formatting, naming, test style)
- Run the project's type checker and linter as you go; fix errors immediately
- **Prefer compound tools over sequential pairs** — use `read_and_patch` instead of `read` → `edit`, `create_and_run` instead of `write` → `bash`, `bash_and_run` instead of `bash` → `bash`. Check the compound tool table in system prompt before reaching for basic tools.
- **Use `patch-verify` for literal replacements when it is installed** — if `patch-verify` is on `$PATH` (check with `command -v patch-verify`), use it via terminal instead of the `edit` tool for any single-file literal string replacement. It validates uniqueness, shows a diff, and is the canonical tool for this repo. Using `replace_string_in_file` or `multi_replace_string_in_file` when `patch-verify` is available is a missed-use anti-pattern.
- **After any full-file write or large rewrite**, run the build immediately before proceeding — catches unused imports, syntax errors, and type mismatches while context is fresh
- **When adding side-effects to a widely-called function** (e.g. Load, Init, New), run the full test suite immediately — these functions are exercised by tests using fake environments (temp HOME, mock FS) and side-effects like auto-detection or network calls will break them
- **Never use `sed`, `awk`, or bash string manipulation to modify source code** — always use the `edit` tool (or `write` for full rewrites). `sed` is acceptable for querying (grep, line counts) but not for code changes: it cannot validate replacements were unique, risks partial matches, and produces cascading errors (renamed functions clashing, orphaned references)
- **Patch boundaries must respect structural blocks** — when using `read_and_patch` or `edit`, ensure `old_str` captures complete structural units (matching braces, full if/for/switch blocks). Never end `old_str` in the middle of a block where the replacement might drop a closing `}`, an adjacent statement, or a loop terminator. If inserting lines inside a block, include the block's closing brace in both `old_str` and `new_str` to prevent structural damage.

- **Verify stdlib APIs before writing:** When you plan to use a Go standard library type, field, or method that you have not read in codebase files during this session, run `go doc <pkg> <Symbol>` to confirm it exists before writing. Do not rely on training-data memory — struct field availability is especially unreliable (e.g. `http.Transport` has `ReadBufferSize`/`WriteBufferSize`; `http.Server` does not). Memory errors here cost a write → build-fail → revert cycle.

- **Go unexport refactor (bulk rename exported → unexported functions):** Use `vscode_renameSymbol` per function, or make each rename individually in the edit tool. After unexporting, run `go build ./...` immediately. Do not attempt bulk sed renames. Also update every `_test.go` file in the same package:
  1. For each test file that calls unexported functions, change its package declaration from `package X_test` to `package X` and remove the self-import (`"github.com/.../X"`).
  2. Before doing this, audit whether any test file that stays as `package X_test` uses a helper function (e.g. `writeFile`, `emptyState`) that was defined in a file you just moved to `package X`. If so, either move the helper into a new `_test.go` file that stays in `package X_test`, or duplicate it. Failing to do this produces "undefined: writeFile" compile errors only in the external-package tests.
  3. After the package declaration change, also scan for type and constant references like `skill.MyType{...}` and `skill.SomeConst` — these are not function calls and will be missed if you only look for function-call patterns.

### Tests

If the brief is a bug fix and a correct seam exists — write a failing test first, then fix it (red-green). If it is an enhancement, write tests that verify the new behavior described in the acceptance criteria.

**Code-path coverage rule:** Every new branching code path (new `if`, new function, new parse/decode step) needs at least one test that exercises it directly — not just an end-to-end test that happens to pass through it. If you add a function that parses a health response, test the parsing. If you add a fallback path, test both the happy path and the fallback. End-to-end tests verify behavior; unit tests pin each new code path against regressions.

If no correct seam exists, document the gap in the PR body.

**Test isolation (mandatory before writing any new test OR modifying existing tests):** Before writing the first test, scan 2–3 existing `*_test.go` files in the same package for environment isolation patterns, then apply the same pattern to every new test:
- `t.Setenv("HOME", t.TempDir())` — isolates config/state that resolves via `os.UserHomeDir()`
- `t.TempDir()` for writable directories — auto-cleaned after the test
- Any `os.Setenv` / mock FS setup the existing tests use

**Filesystem-state convention check:** When your new production code checks filesystem state (e.g. `os.Stat`, file existence, directory contents) on a field that tests populate with `t.TempDir()`, ask: *what does an empty temp dir imply about the production invariant?* If existing tests use bare empty dirs but production always has a populated directory, your check will fire falsely in tests. Identify the sentinel that distinguishes populated vs empty (e.g. a `.git` subdirectory for git clones) and guard the check accordingly — or update the test helper to match the production state.

If any existing test in the package uses `t.Setenv("HOME", ...)`, all new tests in that file must use it too — even if the code path under test does not *currently* write to HOME. This prevents surprises when the implementation evolves.

**When modifying existing tests** (e.g. removing a struct field they assert on): check whether the test function already has HOME isolation. If it doesn't, and the constructor it calls reads from disk (config files, state files), **add isolation now** — your change may expose a latent dependency on real disk state that was previously masked.

**Red-phase gate (mandatory for bug fixes):** After writing the test, run it against the *unfixed* code before implementing the fix. The test MUST fail. If it passes before the fix, it does not exercise the broken code path — rewrite the test until it is genuinely red, or explicitly document in the PR body why no behavioral test is achievable (e.g. test requires external state that cannot be reproduced in a unit test). A test that cannot catch a regression is worse than no test — it creates false confidence.

### Verification loop

After implementing, work through the acceptance criteria checklist one by one. For each:
- State what you did to satisfy it
- Run the relevant command or test to confirm it passes
- If it fails, fix before proceeding

**CLI flag checklist (mandatory when the brief adds flags):**
- For every flag named in the brief, verify it exists on **every command** the brief mentions it on.
- For flags described as optional-value (e.g. `--llm [<agent>]`), test both forms: flag alone (`--flag`) and flag with value (`--flag value`). In cobra, a `String` flag always requires a value — use `flag.NoOptDefVal` to allow bare `--flag`.
- Run `<binary> <command> --help` for each affected command and confirm the flag appears.

Do not open a PR until all acceptance criteria are met.

**Shared-state / concurrency review (mandatory when touching structs accessed under a mutex or across goroutines):**
Before pushing, trace the data flow of every modified shared field:
1. Where is it written? (identify all write sites — including copies made before/after locks)
2. Where is it read? (is the read seeing the latest write, or a stale copy?)
3. If a snapshot copy is made, are updates applied *before* the copy or *after*? (after = stale copy overwrites the update on merge-back)
4. Are side-effects (persistence, event broadcast) triggered for *all* change paths, or only some?
5. For fields that change on **every** cycle (timestamps, counters, uptime), will updating them trigger expensive side-effects (event broadcast, network push, disk persist)? If so, update locally without broadcasting — only broadcast when the *delta* crosses a meaningful threshold.

This catches ordering bugs where a field is updated in the locked struct but not reflected in the working copy (or vice versa).

### Documentation update (mandatory for enhancements)

After the verification loop passes, check whether user-facing documentation needs updating:

1. **README.md** — does the new feature add CLI flags, API fields, config options, or change behavior described in the README? If yes, update it.
2. **Skill files** (e.g. `skills/*/SKILL.md`) — does the feature change what agents should know about (new commands, new JSON fields, new decision logic)? If yes, update.
3. **CONTEXT.md** — does the feature add new domain terms or change existing definitions? If yes, update.

Do NOT ship a feature PR without updating the docs that describe the feature. This includes JSON output examples, config file examples, and CLI help text shown in documentation.

## Phase 6 — Ship

```
git add <specific files>
git commit -m "<type>: <summary from brief>"
git push -u origin <branch>
gh pr create \
  --title "<summary from brief>" \
  --body "$(cat <<'EOF'
## Summary
<one-paragraph description of what changed and why>

## Acceptance criteria
- [x] criterion 1
- [x] criterion 2

## Notes
<any judgment calls made, gaps documented, or out-of-scope items noticed>

Closes #N
EOF
)"
```

**Heredoc quoting (mandatory):** The body uses a single-quoted delimiter (`<<'EOF'`), which already disables all shell expansion. Write backticks and `$` **literally** — do NOT backslash-escape them. Escaping (`\``) injects literal backslashes into the PR body, so every code span renders as `\`text\`` on GitHub.

**PR group check (mandatory when issue has a `pr-group` label or references sub-issues):**
If the implemented issue bundles multiple sub-issues (e.g. `#245` covering `#237` and `#242`), add a `Closes #N` line for **each** sub-issue in the PR body. GitHub only auto-closes issues that appear explicitly with `Closes`/`Fixes`/`Resolves` — the umbrella issue body is not scanned. Scan the issue body for `#NNN` patterns to identify sub-issues:

```bash
gh issue view N --json body --jq '.body' | grep -oE '#[0-9]+'
```

Return the PR URL to the maintainer.

## Phase 7 — Handoff

After the PR is open, remove the `ready-for-agent` label from the issue — it is now in-flight, not queued:

```
gh issue edit N --remove-label ready-for-agent
```

Do not close the issue — the PR's `Closes #N` will close it automatically on merge.

## Phase 8 — Address Review Feedback

When the user asks to address feedback on an open PR, fetch **both** comment types:

```bash
# 1. Inline review comments (line-level, from automated reviewers and humans)
gh api repos/{owner}/{repo}/pulls/{N}/comments \
  --jq '.[] | {path: .path, line: .line, body: .body}'

# 2. Conversation-level comments (general PR discussion)
gh pr view N --comments --json comments
```

> **Important:** `gh pr view N --comments` does NOT return inline review comments.
> It only returns top-level issue comments. Always use the `gh api` call above
> for line-level feedback (e.g. Copilot automated reviews).

Work through each inline comment:
1. Locate the flagged code using `path` + `line` from the comment
2. Apply the fix in the branch (never force-push over a merged review)
3. Run `go build ./... && go test ./... && go vet ./...` (or equivalent) after all fixes
4. Commit with `fix: address PR #N review feedback` and push

## Key Invariants

- NEVER implement from the issue body alone — find the agent brief comment first
- NEVER commit directly to main or master
- NEVER open a PR before all acceptance criteria are verified
- NEVER touch anything listed under **Out of scope**
- ALWAYS include `Closes #N` for every issue closed by the PR — umbrella issue AND all sub-issues (GitHub only auto-closes issues explicitly listed)
- ALWAYS remove `ready-for-agent` from the issue when the PR is open
- ALWAYS run type checker and linter before pushing — fix errors, never suppress
- ALWAYS surface ambiguities in Phase 4, not mid-implementation

## Vocabulary

**User says (route here):**
- "pick up an issue", "work on a ready-for-agent issue", "/implement"
- "implement issue #N", "fix issue #N", "action issue #N"
- "start work on #N", "take on #N", "pick up #N"
- "what's ready for me to work on?"

**Does NOT handle:**
- Triaging or classifying issues → `/triage`
- Diagnosing hard bugs before they reach `ready-for-agent` → `/diagnose`
- Writing agent briefs → `/triage` (produces the brief as part of moving to `ready-for-agent`)
- Reviewing the PR after it's open → `/review`
- Shipping unrelated local changes → `/ship`
