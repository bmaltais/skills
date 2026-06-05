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

**The final step in every plan must be:** `Run /simplify on all changes before committing`

When tracking progress with `manage_todo_list`, include this as an explicit todo item. It must appear in the list and be marked `completed` before any `git add`.

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

```
git rebase --onto main <last-unwanted-commit> HEAD
```

### Write the code

- Implement what the brief's **desired behavior** describes
- Respect the **out of scope** list — do not touch adjacent things
- Follow the project's existing conventions (formatting, naming, test style)
- Run the project's type checker and linter as you go; fix errors immediately
- **After any full-file write or large rewrite**, run the build immediately before proceeding — catches unused imports, syntax errors, and type mismatches while context is fresh
- **When adding side-effects to a widely-called function** (e.g. Load, Init, New), run the full test suite immediately — these functions are exercised by tests using fake environments (temp HOME, mock FS) and side-effects like auto-detection or network calls will break them
- **Never use `sed`, `awk`, or bash string manipulation to modify source code** — always use the `edit` tool (or `write` for full rewrites). `sed` is acceptable for querying (grep, line counts) but not for code changes: it cannot validate replacements were unique, risks partial matches, and produces cascading errors (renamed functions clashing, orphaned references)
- **Patch boundaries must respect structural blocks** — when using `read_and_patch` or `edit`, ensure `old_str` captures complete structural units (matching braces, full if/for/switch blocks). Never end `old_str` in the middle of a block where the replacement might drop a closing `}`, an adjacent statement, or a loop terminator. If inserting lines inside a block, include the block's closing brace in both `old_str` and `new_str` to prevent structural damage.

- **Go unexport refactor (bulk rename exported → unexported functions):** Use `vscode_renameSymbol` per function, or make each rename individually in the edit tool. After unexporting, run `go build ./...` immediately. Do not attempt bulk sed renames. Also update every `_test.go` file in the same package:
  1. For each test file that calls unexported functions, change its package declaration from `package X_test` to `package X` and remove the self-import (`"github.com/.../X"`).
  2. Before doing this, audit whether any test file that stays as `package X_test` uses a helper function (e.g. `writeFile`, `emptyState`) that was defined in a file you just moved to `package X`. If so, either move the helper into a new `_test.go` file that stays in `package X_test`, or duplicate it. Failing to do this produces "undefined: writeFile" compile errors only in the external-package tests.
  3. After the package declaration change, also scan for type and constant references like `skill.MyType{...}` and `skill.SomeConst` — these are not function calls and will be missed if you only look for function-call patterns.

### Tests

If the brief is a bug fix and a correct seam exists — write a failing test first, then fix it (red-green). If it is an enhancement, write tests that verify the new behavior described in the acceptance criteria.

If no correct seam exists, document the gap in the PR body.

**Test isolation (mandatory before writing any new test OR modifying existing tests):** Before writing the first test, scan 2–3 existing `*_test.go` files in the same package for environment isolation patterns, then apply the same pattern to every new test:
- `t.Setenv("HOME", t.TempDir())` — isolates config/state that resolves via `os.UserHomeDir()`
- `t.TempDir()` for writable directories — auto-cleaned after the test
- Any `os.Setenv` / mock FS setup the existing tests use

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

### Simplify before committing (mandatory)

Before running `git commit`, invoke the simplify skill on the uncommitted changes. **This means actually executing the simplify workflow** — spawning the 3 parallel review agents (code reuse, code quality, efficiency) as defined in the simplify SKILL.md. A personal glance at the diff does NOT count as running simplify.

```
/simplify
```

The simplify skill will:
1. Collect the git diff
2. Spawn 3 specialized review agents concurrently
3. Aggregate findings and apply high-confidence fixes

Apply all fixes the simplify skill proposes. Only then commit. This catches code-quality issues before they become PR review comments.

**Anti-pattern:** Do not substitute your own judgment ("the code looks clean") for the actual skill invocation. The 3 agents catch issues the implementing agent is blind to (reuse opportunities against the broader codebase, efficiency patterns, quality issues).

#### Fallback: environments without sub-agents (e.g. pi)

If the runtime does not support spawning sub-agents, perform a **structured inline review** — three separate passes over the full `git diff`, each with a forced checklist. This is NOT the same as glancing at the diff and saying "looks clean."

**Pass 1 — Code Reuse** (run `grep`/`rg` to answer each question):
- [ ] Does any new function duplicate logic already present elsewhere in the repo? Search for key verbs/nouns from the new code.
- [ ] Are there existing helpers (error formatting, HTTP client setup, config loading) that the new code should call instead of re-implementing?
- [ ] If >50% of a block matches an existing function, extract or call the existing one.

**Pass 2 — Code Quality:**
- [ ] Any magic numbers or strings that should be constants?
- [ ] Any exported symbols missing doc comments (Go) or equivalent?
- [ ] Any error paths that swallow context (e.g. returning generic message when the original error is available)?
- [ ] Dead code or unused imports? Run the language's lint tool (`go vet`, `eslint`, etc.).

**Pass 3 — Efficiency:**
- [ ] Any network/IO calls inside a loop?
- [ ] Any unbounded allocations (e.g. appending in a loop without pre-sizing when length is known)?
- [ ] Any blocking calls that could be concurrent?

For each pass, **show your grep commands and their results** — this forces actual codebase inspection rather than imagination. Report findings with file:line references. Apply high-confidence fixes before committing. If all three passes produce zero findings, state that explicitly with evidence (the grep outputs).

## Phase 6 — Ship

**GATE — simplify must run before any `git add`.**
If `/simplify` was not already invoked in this session (i.e., the 3 parallel review agents were not actually spawned and their output collected), run it now and apply all high-confidence fixes before proceeding. A self-assessment ("looks clean") does NOT satisfy this gate. Do not skip this even for small changes. In environments without sub-agents, the structured 3-pass inline review (see "Fallback" above) satisfies this gate — but only if grep commands were actually executed and results shown.

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
- ALWAYS include `Closes #N` in the PR body
- ALWAYS remove `ready-for-agent` from the issue when the PR is open
- ALWAYS run type checker and linter before pushing — fix errors, never suppress
- ALWAYS surface ambiguities in Phase 4, not mid-implementation
- ALWAYS run `/simplify` as the final step of Phase 4's plan before any `git add` — it must be a tracked todo item, not a reminder
- NEVER commit without `/simplify` having run in the same session

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
