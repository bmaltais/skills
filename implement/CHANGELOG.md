# implement Optimization Log

## Session 2026-06-15 — Step 9

### Edits Applied
- (none — zero friction)

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — mandatory documentation update step (from Step 7) was exercised and worked: README.md and skillpack/SKILL.md were updated as part of issue #104 without user prompting.
- The `git status` pre-staging check (from Step 8) was used and correct.

### Meta Notes
- Two issues implemented (#104 large refactor, #98 trivial data-only change). Both PRs merged with zero review comments.
- Simplify 3-pass inline review caught the applyMerge duplication independently — no user correction needed.
- Convergence: strong. Skill is performing well. Learning rate staying low.

## Session 2026-06-07 — Step 8

### Edits Applied
- [op: insert_before "git add"] Added mandatory "pre-staging path check" — run `git status` first and use exact paths shown. Reasoning: `git add go/cmd/model-shelf/main.go` failed because CWD was inside `go/` subdirectory; git resolved as `go/go/...`. Required retry. Support count: 1, but fully generalizable to any project where git root ≠ module root.

### Deferred Edits (waiting for more signal)
- [P3] Brief-less issues: 3rd consecutive session with no agent brief comments. Skill handling (flag + proceed with body) continues to produce correct implementations. No skill gap. Keeping at P3 indefinitely — the handling works.

### Observed Regressions from Previous Edits
- (none) — Step 7's documentation update and compound-tool rules were not exercised this session (no enhancements, no read→edit patterns). No regression.

### Meta Notes
- Multi-issue PR deferred concern (from Step 3): 4+ sessions, zero problems. Dropping permanently.
- Session was low-friction except for one git add retry. The new mandatory `git status` check is the only edit worth making.
- Convergence: stable. One mechanical failure (path prefix), one correct fix. Skill is mature. Learning rate staying low.

## Session 2026-06-06 — Step 7

### Edits Applied
- [op: insert_after "Write the code" conventions list] Added compound tool preference rule — reasoning: user corrected read→edit pattern (should be read_and_patch) for second time across sessions. Support count: 2 (Step 1 deferred + this session).
- [op: insert_after verification loop, before simplify] Added "Documentation update (mandatory for enhancements)" section — reasoning: user explicitly called out README and skill file not being updated, noted it's been recurring across multiple PRs. Support count: 2 (explicit user corrections).

### Deferred Edits (waiting for more signal)
- [P3] Brief-less issue handling: agent proceeded without surfacing warning. Still correct given explicit user intent. Carried from Step 6.

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- The documentation gap was the dominant failure this session. User framed it as systematic ("how long has it been") — indicating multiple prior PRs shipped features without doc updates.
- Compound tool issue now promoted from P2→applied after second occurrence. Clear and unambiguous.
- Convergence: slight regression (user had to correct twice), but root causes are now addressed with clear mandatory steps. Skill should be back to low-friction next session.
- Strategy: both edits add mandatory steps. Skill is getting longer — next session should watch for whether the added steps cause slowdown or get skipped.

### Edits Applied
- (none — no P0/P1 issues observed)

### Deferred Edits (waiting for more signal)
- [P3] Brief-less issue warning: agent proceeded without surfacing "no agent brief found" to user. Correct call given user's explicit intent, but skill says to always flag. Watch for case where missing brief causes wrong implementation.

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- Session implemented 3 issues (#45, #46, #47) in one PR. Clean execution: bug fix correct first try, install.sh and README updates straightforward.
- Shell environment issue (`sudo` alias intercepting `cd`) caused repeated tool failures — not skill-addressable, agent adapted.
- 5 review comments on PR addressed cleanly in one pass, merged successfully.
- Convergence: stable. Four consecutive low-friction sessions. Skill is mature. Learning rate should remain low.

## Session 2026-06-05 — Step 5

### Edits Applied
- [op: append to concurrency review checklist] Added item 5: "For fields that change on every cycle, will updating them trigger expensive side-effects?" — reasoning: UptimeSeconds always changes on every poll, was marked as metricsChanged, causing EventHealthChange broadcast every 15s. Support count: 1, but clear and generalizable pattern.

### Deferred Edits (waiting for more signal)
- [P3] Multi-issue PRs: still no friction observed across 3 sessions. Dropping — clearly not a problem.

### Observed Regressions from Previous Edits
- (none) — The concurrency review checklist (Step 4) was relevant to this session's failure #2 (incomplete merge-back), but the agent didn't fully execute the checklist. This is an execution gap, not a skill gap.

### Meta Notes
- Session combined 3 issues into one PR. Clean except for 2 review comments, both in gossip polling code.
- The concurrency review checklist from Step 4 partially helped (merge-back issue is covered by item 3) but agent didn't trace all new fields through it. Reinforcing with more text unlikely to help — this is attention/discipline.
- Convergence: stable. 2 substantive review comments is low. The new item 5 addresses a distinct category (frequency-triggered side-effects) not previously covered.

## Session 2026-06-05 — Step 4

### Edits Applied
- [op: insert_after "Verification loop"] Added "Shared-state / concurrency review" checklist — reasoning: 2 review comments (self-disk race, missing event broadcast) traced to same root cause: stale copy overwrites and incomplete side-effect triggering. Support count: 2.
- [op: append to Pass 2 checklist] Added fallback/recovery error-swallowing check — reasoning: `loadFromMeshConfig` silently discarded parse errors and fell through to legacy config, re-introducing the bug it was supposed to fix. Support count: 1.
- [op: insert_after "Tests" first paragraph] Added "Code-path coverage rule" — reasoning: DiskFreeGB health parsing had no direct test; only end-to-end display test. Reviewer caught it. Promotes deferred P3 from Step 2. Support count: 2 (this session + deferred signal).

### Deferred Edits (waiting for more signal)
- [P3] Multi-issue PRs: still no friction observed. Keep watching.

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- Session had 4 review comments — all valid logic/coverage issues. The 3-pass simplify caught formatting/reuse but not concurrency semantics. Concurrency review is a distinct concern that the simplify pass doesn't cover well.
- Convergence: slight regression this session (4 review comments vs 0 in previous 3 sessions). Root cause: new territory (concurrent gossip state) exposed gaps in verification. Edits applied should prevent recurrence.
- Deferred "Go test stdout capture pattern" dropped — no signal in 3 sessions, clearly one-off.

## Session 2026-06-05 — Step 3

### Edits Applied
- (none — no P0/P1 issues observed)

### Deferred Edits (waiting for more signal)
- [P3] Multi-issue PRs: skill assumes single issue per invocation. Two-bug PR worked fine here but isn't explicitly documented. Wait for signal where combining causes problems.
- [P3] Go test stdout capture pattern: use `os.Pipe()` + `io.ReadAll(r)`, not `strings.Builder.ReadFrom`. Carried from Step 2.

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- Session combined two issues (#35, #36) into a single branch/PR. Efficient, no friction.
- Missing import caught immediately by existing "build after write" guard — guard is working.
- Convergence: stable. Three consecutive low-friction sessions. Skill is mature.

## Session 2026-06-05 — Step 2

### Edits Applied
- (none — no P0/P1 issues observed)

### Deferred Edits (waiting for more signal)
- [P3] Go test stdout capture pattern: use `os.Pipe()` + `io.ReadAll(r)`, not `strings.Builder.ReadFrom`. Single occurrence — wait for repeat before encoding in skill.
- [P2 carried] Compound tool usage reminder — still waiting for repeat signal.

### Observed Regressions from Previous Edits
- (none — Step 1's test-isolation edit was not exercised this session)

### Meta Notes
- Session was clean: implementation first-try, one stdlib knowledge error caught by existing "build after write" guard.
- Convergence: skill is working well. Low friction session. Learning rate should stay low.

## Session 2026-06-05 — Step 1

### Edits Applied
- [op: replace] Extended test isolation rule to cover "modifying existing tests" — reasoning: removing `d.nodes` field caused join_test.go to fail because it loaded real mesh.json from host disk. The rule previously only said "new tests". Support count: 1 (but clear causal chain).

### Deferred Edits (waiting for more signal)
- [P2] Compound tool usage reminder in "Write the code" section — user pointed out read→edit should be read_and_patch. Already in system prompt tool table; adding to implement skill may be duplicative. Wait for repeat.

### Observed Regressions from Previous Edits
- (none — first optimization step)

### Meta Notes
- Added simplify fallback for no-subagent environments earlier in session (separate invocation)
- Skill is fairly mature — prefer surgical edits over broad additions

## Session 2026-06-15 — Step 10

### Edits Applied
- [op: insert_after compound-tools rule] Added `patch-verify` specific rule — reasoning: agent used `replace_string_in_file` for all literal replacements throughout the session despite `patch-verify` being installed and GA. User explicitly flagged. Support count: pervasive (every file edit in session).

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — pre-staging `git status` check (Step 8) used correctly; documentation update step (Step 7) applied correctly (README updated in same PR).

### Meta Notes
- Session was otherwise clean: all 9 AC verified first-try, no PR review comments.
- The `patch-verify` miss is the only gap. Root cause: skill names generic compound tool preference but not repo-specific registered tools.
- Convergence: stable, one new rule added. Skill is mature.

## Session 2026-06-15 — Step 10

### Edits Applied
- [op: insert_before red-phase gate] Added Go flag test convention: flags before positionals in `flag`-based CLI tests. Reasoning: 8 test cases had to be mass-fixed because flags were placed after positionals — `flag` package silently stopped parsing. Support: 8 fixes in one shot.
- [op: replace] README.md doc update note — added "re-read file immediately before editing if modified earlier in session". Reasoning: README had duplicate row from a prior write in same session; multi_replace matched it twice. Support: 1.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — previous edits (compound-tool rule, documentation update step, `git status` pre-staging check) all fired correctly this session with zero user corrections.

### Meta Notes
- Two PRs shipped (#20, #21), both merged with zero review comments.
- Step 9 regression confirmed: documentation update step worked as intended — README and overlays updated without prompting.
- Convergence: strong. Skill is performing well. The flag-ordering note is the only new mechanical gap identified across many sessions.

---

## Session 2026-06-25 — Step 10

### Edits Applied
- [op: insert_after, Phase 5 Branch section] Added multi-account auth check (`gh auth status`) before `git push` — reasoning: push failed 403 because wrong GitHub account was active (`bernardmaltais` vs `bmaltais`); would have been caught by a pre-push `gh auth status` check. Support: 1.
- [op: insert_after, Test isolation section] Added filesystem-state convention check — reasoning: `os.Stat` check in ReconcilePlan against `CachePath`-derived paths broke 11 existing tests because tests use empty `t.TempDir()` as `CachePath`. The rule prompts asking "what does an empty field value mean in tests vs production?" before writing state-dependent checks. Support: 1.

### Deferred Edits
(none)

### Observed Regressions from Previous Edits
(none observed — documentation update step, red-phase gate, and code-path coverage rules all worked as intended this session)

### Meta Notes
- Both edits are small additions reinforcing existing sections (pre-push and test isolation). No deletions.
- The test-infrastructure failure (11 regressions) was the highest-friction event; it required a redesign iteration and test updates. The auth failure was resolved in one command.
- Convergence: slight increase in friction vs. previous session (which had zero). Two targeted edits applied; learning rate remains conservative.
