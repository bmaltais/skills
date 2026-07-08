# implement Optimization Log

## Session 2026-07-08 — Step 1

### Edits Applied
- [op: replace] Line "Commit your work to the current branch." replaced with an explicit instruction to branch off the target branch before committing, never commit directly to a shared branch (dev/master) — reasoning: session committed directly to `dev`, which had already been pushed upstream (via an out-of-band pull), requiring a `force-with-lease` push to strip it back off `origin/dev` and move the work to a new branch. High-cost failure, directly caused by the skill's literal wording.
- [op: append] Added a step to push the branch and open a PR against the target branch with `Closes #<ticket>` — reasoning: after committing, the skill ended with no PR step; user had to ask twice ("did you create the pr", "is the issue linked") before a PR was created and linked.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none — first optimization pass for this skill)

### Meta Notes
- Strategy: skill was minimal (5 lines) with a real gap at the end of its workflow (commit → nothing). Preferred extending the existing line + one appended step over restructuring.
- Convergence: too early to assess (first entry).

## Session 2026-07-08 — Step 2

### Edits Applied
- [op: replace] Line "Use /tdd where possible, at pre-agreed seams." replaced with a mandatory rule: every change ships with a test, use /tdd to find the seam even without prior agreement, and state explicitly when something is untestable — reasoning: this session shipped a GUI change with zero tests; the user had to explicitly ask ("did you implement tests... you should implement tests for all changes") before any were written. "Where possible" was read as optional and skipped by default.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none — step 1's branch/PR edits worked correctly this session: work went to a new branch and the PR flow was already established)

### Meta Notes
- Strategy: same as step 1 — reinforce an existing line rather than add a new section, since the gap was a weak qualifier ("where possible") rather than a missing step.
- Convergence: 2 sessions in, both edits triggered by direct user correction on distinct gaps (branching, testing) in the same short skill — skill was clearly undertrained at 5 lines; each pass is tightening a real gap, not churning previous edits.
