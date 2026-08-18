# github-pr-workflow Optimization Log

## Session 2026-08-04 — Step 8

### Edits Applied
- [op: insert_after] `SKILL.md` § "1. Branch Creation" — added a check for when reusing an existing branch instead of creating a new one: `git fetch origin && git merge-base HEAD origin/<base>` before the first commit of the session. — reasoning: this session continued work on a branch created in an earlier session; a companion skill (`eslz-module-upgrade`) had already checked the branch against `origin/main` once, but without fetching first, so the check silently passed against a stale local ref. By the time this skill's push/PR steps ran, the branch's actual base had already moved (a prior PR with the same content had merged under a different commit SHA). Section 1's existing `git fetch origin` only runs on the new-branch path (before `git checkout -b`); nothing in this skill re-verifies freshness when the branch already exists, which is exactly the case a resumed multi-turn session hits.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — the fetch+rebase-before-push guidance from Steps 3 and 7 (auto-committing docs workflow, bot-authored `action_required` commits) wasn't triggered this session; this is a distinct scenario (branch reused across sessions, not a bot commit mid-session).

### Meta Notes
- This finding surfaced from a user correction ("did you make sure you updated the code against master/main?") during a session that also exercised `eslz-module-upgrade`; the root cause was fixed in that skill's own staleness check (missing `git fetch` prefix), but this skill had an independent, unaddressed version of the same gap for anyone invoking it standalone on a reused branch — worth fixing here too rather than assuming the other skill's fix covers every entry path.

## Session 2026-08-03 — Step 7

### Edits Applied
- [op: replace] `references/ci-status-gotchas.md` "`action_required` on a bot-authored commit (403 on approve)" — the documented fix said a repo maintainer "must click **Approve and run workflows** in the Actions tab UI," with no CLI path. Replaced with `gh run rerun <RUN_ID>` as the first thing to try (re-triggering the run re-evaluates it under the rerunning user's own permissions rather than the bot's, and needs no UI interaction), keeping the manual UI click only as a fallback if the rerun itself comes back `action_required` again — reasoning: hit the exact documented 403 this session (Copilot's review pushed a fix commit directly to the PR branch, its CI runs came back `action_required`), but instead of stopping to tell the user it needed manual approval, `gh run rerun` on the affected run IDs succeeded immediately and CI went green with zero human/UI interaction. The previous guidance wasn't wrong (the 403 and its cause are correctly diagnosed) but its prescribed fix was overly conservative — a working CLI-only path existed and wasn't documented.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — every other documented flow this session (branch-reuse check not applicable since this was a fresh PR, `--body-file` for the PR body, `gh pr comment` to request an `@copilot` review, JSON-based CI polling with no pager hang, reading bot review responses via `issues/N/comments`) held with zero friction.

### Meta Notes
- Convergence note (7th entry): this is the first edit to a previously-applied fix that wasn't a regression — the old guidance was correct but incomplete (right diagnosis, suboptimal prescribed remedy). Distinct from Step 3's true regression (a fix that stopped working outright). Worth watching whether other "tell the user, needs manual step" gotchas in this skill have a similar undocumented CLI shortcut that just hasn't been tried yet.

## Session 2026-08-03 — skill-contracts pass (branch-level disclosure)

### Edits Applied
- [op: replace] `SKILL.md` frontmatter `description` — had no trigger phrasing (`check_skill.py` warned "model-invoked description lists no trigger — it may never fire"); rewritten to lead with "Use when the user wants to create a branch, open or update a pull request, request an automated PR review, check or poll CI status, auto-fix a failing CI run, or merge a PR."
- [op: replace] `SKILL.md` — every "With git + curl:" block (Sections 3, 4, 5, 6, plus the Owner/Repo extraction and the full `git + curl` column of the commands table) moved verbatim to a new `references/git-curl-fallback.md`, mirrored section-by-section. Reasoning: the prior structural pass (below) disclosed conditional *gotchas*, but left the entire `gh`-vs-`git+curl` **branch** duplicated inline after every step — the exact case `writing-great-skills.md` calls out ("branching is the cleanest disclosure test: inline what every branch needs, push behind a pointer what only some branches reach"). `AUTH="git"` is the rare branch (machines without `gh`); it doesn't need to sit in the primary path every `gh`-CLI session reads. `SKILL.md` body dropped from 400 to ~214 lines; `check_skill.py` sprawl warning shrank from 400 to 214 (still over the 150 heuristic, but no longer carrying a second full copy of every command).
- [op: remove] `SKILL.md` § "7. Complete Workflow Example" — deleted. Every line was either a repeat of a command already shown in Sections 1-3 or a bare `# ... (see Section N)` comment; pure duplication/no-op per the pruning rules, no unique content.
- [op: replace] `SKILL.md` § "Useful PR Commands Reference" — the Projects (classic) GraphQL-bug callout (was an inline blockquote under the table) moved to `references/ci-status-gotchas.md` alongside the other `gh` CLI environment quirks; table now links there instead of repeating the workaround inline.
- [op: replace] `SKILL.md` § "2. Making Commits" — the inline Conventional Commits type table and the `-F`-over-`-m` shell-escaping tip were replaced with a pointer to `references/conventional-commits.md`. That file already existed with the fuller version of this same content but was never linked from `SKILL.md` — an orphaned reference file (dead weight, unreachable by any context pointer). Moved the escaping tip into it (as a gotcha section) instead of keeping two copies.
- [op: replace] `SKILL.md` § "3. Pushing and Creating a PR" → "Create the PR" — added a pointer to `templates/pr-body-feature.md` and `templates/pr-body-bugfix.md` for `--body-file` content. Both templates existed in the skill folder already but had no reference anywhere in `SKILL.md` — same orphaned-file problem as the Conventional Commits reference.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — this is a structural/contract pass (`skill-contracts` methodology run against the skill, not a new field session), not a new-session field report. All prior field-observed content (pager fix, `action_required` handling, auto-commit rebase, Projects-classic bug, log-reading, CI failure patterns, PR-reuse check, `-F`/`--body-file` shell-escaping fixes) is preserved unchanged in meaning, only relocated or pointed to.

### Meta Notes
- `python3 ~/.claude/skills/skill-contracts/scripts/check_skill.py github-pr-workflow` (adapted path: `/home/bernard/.copilot/skills/skill-contracts/scripts/check_skill.py`) went from 2 warnings (no-trigger description, 400-line sprawl) to 1 (sprawl, now 214 lines) and 0 errors. The remaining sprawl warning is the six ordered `gh`-CLI steps themselves (Sections 1-6) — legitimate primary-tier content per the information hierarchy, not reference bloat; further cuts would mean fragmenting 3-5 line step-specific tips into more reference files, trading legibility for a lower line count without removing anything actually redundant.
- Found and fixed two **orphaned reference files** (`references/conventional-commits.md`, `templates/pr-body-feature.md`, `templates/pr-body-bugfix.md`) that existed on disk but had zero inbound links from `SKILL.md` — unreachable by any context pointer, so no agent run would ever have found them. Worth checking for this class of bug (files present, never linked) whenever a skill folder accumulates `references/`/`templates/` content over multiple sessions.

## Session 2026-08-03 — Structural review (writing-great-skills pass)

### Edits Applied
- [op: replace] `SKILL.md` § "4. Monitoring CI Status" — the four inline gotcha callouts (pager alternate-buffer hang, workflow-file `action_required`, bot-commit 403 on approve, auto-commit-workflow rebase-before-push) were conditional branches, not the mainline check — moved verbatim to a new `references/ci-status-gotchas.md`, replaced in `SKILL.md` with one pointer sentence. Reasoning: none of these fire on every PR; per the information-hierarchy rule ("disclose what only some branches need, inline what every path needs") they belonged behind a context pointer, not sitting in the primary path every session reads.
- [op: replace] `SKILL.md` § "5. Auto-Fixing CI Failures" → Step 1 (git+curl) — removed the "download logs as zip, extract, read" block; it duplicated `references/ci-troubleshooting.md`'s "Reading CI Logs" section almost verbatim (same commands, single source of truth violation). Replaced with a pointer to that file. Kept the unique "list workflow runs" snippet (needed to obtain `RUN_ID`) inline since it isn't documented elsewhere.
- [op: replace] `references/ci-troubleshooting.md` — fixed `$GH_OWNER/$GH_REPO` to match the `$OWNER/$REPO` convention used everywhere else in `SKILL.md` and this reference set (was an unexplained naming drift between the two files).
- [op: replace] `references/ci-troubleshooting.md` § "Re-running After Fix" — this section repeated the exact git add/commit/push + re-check commands already given as `SKILL.md` § 5 Steps 2-3. Collapsed to a one-line pointer back to those steps instead of restating them.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — this pass is a structural/information-hierarchy review, not a new-session field report; no new failure signal, only de-duplication and progressive disclosure of existing content. All prior field-observed content (pager fix, `action_required` handling, auto-commit rebase, log-reading, CI failure patterns) is preserved unchanged in meaning, only relocated or pointed-to.

### Meta Notes
- This session applied the `writing-great-skills` framework directly: content itself wasn't wrong (6 prior sessions converged on zero new friction), but `SKILL.md` had grown to 445 lines with two clear violations — sprawl (conditional-branch-only gotchas sitting in the mainline CI-status step) and duplication (the same log-download commands stated in both `SKILL.md` and `ci-troubleshooting.md`, with a variable-name drift as a symptom of there being two sources of truth). Net effect: `SKILL.md` down to 414 lines, no information lost, one new reference file for the CI-status-checking branch cases.

## Session 2026-08-03 — Step 6

### Edits Applied
- (none) — this session re-exercised every fix from Steps 1-5 (JSON-based CI polling with no pager hang, `--body-file` for the PR body, `gh pr comment` to request an automated `@copilot` review, fetch+rebase before each follow-up push since the docs workflow auto-commits, and the bot-authored-commit `action_required` 403 requiring manual "Approve and run workflows" in the UI) and all held with zero regressions and zero new friction. Per the skill's own guardrails ("quality over quantity... do not invent improvements to appear productive"), no edit is proposed this round.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- Convergence note (6th entry): first fully clean session for this skill — zero new failure signals of any kind. The skill appears converged for the standard create → monitor → auto-fix → (blocked on required review) flow; future friction, if any, is more likely to come from adjacent process gaps (e.g. how to read an automated bot reviewer's response, which this session found via `issues/N/comments` without any wasted round trip) than from the documented CLI mechanics.

## Session 2026-08-03 — Step 5

### Edits Applied
- [op: insert_after] `SKILL.md` § "3. Pushing and Creating a PR" → "Create the PR" — added a new "Requesting an Automated Review" subsection: post a `gh pr comment` (or REST equivalent) tagging the repo's AI reviewer (e.g. `@copilot`) immediately after opening the PR, rather than waiting for the user to ask — reasoning: this session completed the full create → monitor CI → (blocked on required review) flow, then the user had to send a separate follow-up message asking to add a review-request comment. Nothing in the PR-creation step suggested this as a normal part of finishing a PR.
- [op: insert_after] `SKILL.md` § "2. Making Commits" — added a guard to run `git status` and check for pre-existing unrelated changes/deletions before `git add -A`, restoring anything out of scope with `git checkout -- <path>` — reasoning: this session's `git status` surfaced `.devcontainer/*` files already deleted from the working tree, unrelated to and predating the task; staged and committed only the intended files after manually checking and restoring the unrelated deletion. Encoding this catch (a success this session, not a failure) so it isn't left to chance in future sessions that skip the manual check.
- [op: insert_after] `SKILL.md` § "4. Monitoring CI Status" (gh) → `action_required` note — added a caveat that a commit authored by a bot/app identity (the Copilot coding agent pushed a fix commit after the review request this same session) can 403 on `gh api .../actions/runs/{id}/approve` ("This run is not from a fork pull request or queued by the Actions bot"), unlike the already-documented workflow-file-change case which the endpoint does cover — reasoning: hit this immediately after applying the Requesting an Automated Review edit above, in the very same session: Copilot's review produced a real fix commit, its CI runs came back `action_required`, and the documented approve command failed with a 403 the existing note gave no indication of. Resolution requires a human clicking "Approve and run workflows" in the Actions UI — the skill now says so instead of implying the API call always works.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — Steps 1-4's fixes (`--body-file`/heredoc, `-F` commit messages, JSON-based CI polling, `action_required` approval loop recurring on the docs-workflow auto-commit, branch-reuse check) all held with zero regressions this session; the auto-commit + `action_required` sequence recurred exactly as documented and resolved on the first try for the workflow-file-change case.

### Meta Notes
- Convergence note (5th entry): both findings this round were about *finishing* a PR well (requesting review, keeping the diff scoped) rather than a CLI/mechanics failure — a third flavor of gap alongside "shell-escaping quirks" (Steps 1-2) and "workflow-judgment" (Step 4). The documented CLI-mechanics fixes continue to hold across sessions with zero regressions, suggesting that layer has converged; remaining friction is shifting toward "what does a complete, well-scoped PR handoff look like" rather than command reliability.

## Session 2026-08-03 — Step 4

### Edits Applied
- [op: insert_after] `SKILL.md` § "1. Branch Creation" — added a check for an already-open, unmerged PR from earlier in the same session before branching; commit related follow-up work to that PR's existing branch instead of opening a new one, unless the user explicitly asks for a separate PR — reasoning: this session branched and opened a second PR for a change (a release-on-merge workflow) that the user considered part of the same in-flight PR, requiring the new PR to be closed and its commit cherry-picked onto the original branch after an explicit correction ("I wanted you to add this to the existing PR... not create a new one"). The skill's branch-creation step had no check for existing session-scoped PRs at all.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — this session re-exercised the Step 3 JSON-polling fix (clean, no pager hang), the `--body-file`/heredoc convention (clean), the `action_required` approval flow (clean, recurred on two separate pushes as documented), the bot-commit fetch+rebase guidance (not triggered this time — no auto-commit on the second push), and the Projects-classic `gh pr edit` GraphQL bug fallback (hit again, `gh api --method PATCH` fallback worked immediately). All five prior fixes held.

### Meta Notes
- Convergence note (4th entry): this is the first friction in this skill that isn't a `gh` CLI/shell-escaping rough edge — it's a workflow-judgment gap (when to branch vs. reuse) rather than a command reliability issue. Every previously-applied fix (Steps 1-3) held with zero regressions this round, suggesting the CLI-mechanics layer of this skill has converged; future friction is more likely to be this kind of process/judgment gap than a new escaping or pager quirk.

## Session 2026-08-03 — Step 3

### Edits Applied
- [op: replace] `SKILL.md` § "4. Monitoring CI Status" (gh) — the Step 2 fix (`PAGER=cat GH_PAGER=cat gh pr checks`) regressed: this session hit the exact same alternate-screen-buffer hang, twice (plain and `--watch`), with the PAGER prefix already applied. Replaced the guidance: keep the PAGER-prefixed one-shot command as a first try, but added an explicit, unconditional fallback to `gh run list --json ... | cat` and `gh pr view --json state,mergeable,mergeStateStatus,statusCheckRollup | cat` — both JSON-output commands that never invoke a pager — as the reliable path the moment the first hangs. Poll the `gh pr view` command in a loop instead of `--watch`.
- [op: insert_after] `SKILL.md` § "4. Monitoring CI Status" (gh) — added guidance for repos with an auto-committing workflow (e.g. a docs-generation job with `git-push: "true"`): expect the remote branch to gain a bot commit shortly after your push, which will reject a second push as non-fast-forward — always `git fetch` + `git rebase origin/<branch>` before pushing a follow-up fix — reasoning: hit this exactly once this session (a `terraform-docs` auto-push workflow), losing a push attempt to a rejection before fetch+rebase resolved it; no prior coverage anywhere in the skill for a bot being a co-writer on the branch.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- **Yes** — the Step 2 edit (`PAGER=cat GH_PAGER=cat` prefix) was not sufficient this session; the same alternate-buffer hang recurred despite the fix being in place and applied correctly. This is the reason for this session's replace (not just an append) — the previous fix is demoted from "the fix" to "try first," with a mandatory fallback now given equal footing.

### Meta Notes
- Convergence note (3rd entry): this is the first *regression* observed for this skill — a previously-applied fix didn't hold across environments. Rather than layer a third pager-flag variant on top, this round switched strategy entirely to a pager-free JSON-output path, which is more robust by construction (no TTY/pager behavior to fight). Worth checking in a future session whether the JSON fallback itself ever needs a fallback, or whether this closes the pattern for good. The bot-commit/rebase finding is unrelated churn — a genuinely new gap, not a regression.

## Session 2026-07-31 — Step 2

### Edits Applied
- [op: insert_after] `SKILL.md` § "2. Making Commits" — added a tip to use `git commit -F <file>` instead of inline `-m "..."` when the message contains `!`, backticks, or `$` — reasoning: `git commit -m "feat!: ..."` (the Conventional Commits breaking-change marker, literally suggested one section above) triggered bash history expansion (`bash: unrecognized history modifier`), garbling the multi-line message and aborting the commit. Mirrors the skill's own existing `--body-file` fix for PR bodies — same root cause, same fix, different command.
- [op: replace] `SKILL.md` § "4. Monitoring CI Status" (gh) — prefixed `gh pr checks` / `--watch` examples with `PAGER=cat GH_PAGER=cat` — reasoning: `gh pr checks --watch` opened an alternate-screen pager this session, returning no usable output to the tool runner; happened twice (plain and `--watch`) before the workaround was found.
- [op: insert_after] `SKILL.md` § "4. Monitoring CI Status" (gh) — added a note that PRs which add/modify `.github/workflows/*` files can come back `action_required` (empty job list) even for the PR author with write access, with the `gh api .../actions/runs/{id}/approve` fix and a warning that it recurs on every push touching a workflow file — reasoning: hit this twice in the same PR (initial push and a follow-up push), with zero prior coverage in the CI-monitoring section.
- [op: replace] `SKILL.md` § "Useful PR Commands Reference" — broadened the existing Projects-classic GraphQL warning from `gh pr edit`-only to explicitly include `gh pr view` (with or without `--comments`), and added `gh api` REST fallbacks for reading reviews/comments (`.../pulls/N/reviews`, `.../pulls/N/comments`, `.../issues/N/comments`) — reasoning: `gh pr view --comments` failed with the exact same GraphQL `projectCards` error the skill already documented, but scoped only to `gh pr edit`; had to improvise the `gh api` REST fallback for reading comments from scratch.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — the Step 1 `--body-file` tip was used correctly and cleanly this session.

### Meta Notes
- Convergence note (2nd entry): PR body construction (fixed step 1) had zero friction this session — that edit stuck. New friction this round clustered around shell-escaping (commit `-m`) and `gh` CLI environment quirks (pager, Projects-classic scope, workflow-approval) rather than the documented git/PR mechanics, which continue to run clean. Worth watching whether "gh CLI has an undocumented rough edge" keeps recurring as its own pattern across future sessions.

## Session 2026-07-31 — Step 1

### Edits Applied
- [op: insert_after] `SKILL.md` § "3. Pushing and Creating a PR" → "Create the PR" (gh) — added a tip recommending `--body-file` with a heredoc over inline `--body "..."` for long or backtick-heavy descriptions, plus a one-liner to fix an already-malformed body via `gh api --method PATCH ... -f body=...` — reasoning: this session's `gh pr create --body "..."` had a stray `"` where a backtick was intended (typed directly inside an escaped shell string), silently corrupting part of the PR description; required a follow-up PATCH to fix. The skill's own example already relies on escaped backticks inline, which is exactly the fragile pattern that caused the bug.

### Deferred Edits (waiting for more signal)
- (none — first pass)

### Observed Regressions from Previous Edits
- (none — first optimization pass for this skill)

### Meta Notes
- First optimization pass. The rest of the documented flow (branch → commit → push → `gh pr create` → `gh pr checks`) executed clean first-try this session; only the body-construction step had friction. Keep future edits scoped to genuine reproducible friction rather than speculative hardening of steps that already ran clean.

## Session 2026-08-10 — Step 9

### Edits Applied
- [op: insert_after] SKILL.md § "Requesting an Automated Review" — added a guardrail against treating a reviewer-authored fix commit plus its own reviewer-authored test as independent verification of an external-system claim (an API constraint, a provider default). Reasoning: this session accepted a Copilot review fix that coupled export_policy_enabled to public_network_access_enabled based on a misread Azure API constraint (the real constraint is one-directional, not bidirectional), plus a Copilot-authored mock test asserting the wrong value as correct. Both merged and CI went green. Only a live terraform-module-upgrade-probe run (a separate skill, real deployed state) caught the resulting plan diff before it reached production. The review + its own test never independently verified the claim against primary docs.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- This is the first session where a fix authored by the requested automated reviewer was itself wrong and reached a green-CI, review-approved state before an unrelated downstream check (a live probe in a different skill/repo) caught it — worth watching whether future sessions show this as a recurring blind spot specific to accepting AI-reviewer-authored fixes at face value.

## Session 2026-08-11 — Step 10

### Edits Applied
- [op: insert_after] SKILL.md § "Requesting an Automated Review" — added a "Reading the Review's Feedback" pointer directing straight to `gh api` (not `gh pr view --comments`) for fetching reviewer findings, plus a one-line row in the "Useful PR Commands Reference" table. — reasoning: this session posted an @copilot review request, then called `gh pr view 1 --comments` to read its findings and hit the exact, already-documented Projects (classic) GraphQL error (references/ci-status-gotchas.md has covered this since Step 2) before falling back to the correct `gh api` commands. The primary workflow had a step for *requesting* a review but none for *reading* its response, so the natural first command an agent reaches for is the one guaranteed to fail in this class of repo. Kept the fix as a pointer to the existing reference (not a restatement) to avoid duplicating the already-documented `gh api` commands.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- Convergence note (10th entry): the underlying `gh api` fallback commands have been correct and unchanged since Step 2 (5+ sessions with zero regressions on that content) — this session's gap was pure discoverability (missing pointer in the primary path), not a wrong or missing command. Matches this skill's broader pattern: CLI-mechanics content converged long ago; remaining friction is in workflow sequencing/discoverability of already-correct reference material.

## Session 2026-08-12 — Step 11

### Edits Applied
- [op: insert_after] references/ci-status-gotchas.md "action_required on a bot-authored commit (403 on approve)" — added a note that this can cascade when the repo also has an auto-committing workflow: a successful gh run rerun can let that workflow push a NEW bot-authored commit (e.g. a terraform-docs regeneration triggered by content that actually changed), which lands with its own fresh pair of action_required runs needing another rerun round. Don't stop after one successful rerun — keep re-checking gh run list until all-green with no new commits on git fetch — reasoning: this session hit exactly this cascade twice on the same PR. Push 1: rebased onto two Copilot-bot-authored commits, pushed, both resulting runs came back action_required and 403'd on /approve, gh run rerun fixed them — but that success let terraform-docs push an actual new README commit, which itself triggered a second action_required pair needing a second gh run rerun round. Push 2 (a later, unrelated fix) repeated the identical two-round cascade. The existing 'bot-authored commit' section already documented gh run rerun as the fix but framed it as a single, complete action; nothing connected it to the sibling 'auto-committing workflow' section to warn that fixing one can trigger the other.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — the existing gh run rerun fix, the fetch+rebase-before-push guidance, and the bot-commit-verification-before-integrating practice (checking git show on each copilot-swe-agent[bot] commit before rebasing onto it) all held correctly this session; this edit only connects two already-correct sections rather than changing either one's content.

### Meta Notes
- Convergence note (11th entry): CLI-mechanics content for this skill has been stable across many sessions now (zero regressions this round on any previously-applied fix). This session's one finding is a cross-reference gap between two individually-correct sections rather than a wrong command — consistent with this skill's established pattern (per Step 10's note) that remaining friction is workflow sequencing/discoverability, not command reliability.

## Session 2026-08-18 — Step 12

### Edits Applied
- [op: insert_after] `SKILL.md` § "3. Pushing and Creating a PR" → "Create the PR" — added a check: `gh release list` + `ls .github/workflows/` to detect a repo with release history but no release-creating workflow (grep for `release create`/`softprops/action-gh-release`), flag to the user that releases are manual before assuming CI tags on merge, plus the backfill recipe (`gh release create <version> --notes-file <path> --target <base-branch>` + follow-up workflow PR) if only discovered post-merge — reasoning: this session merged a PR into a Terraform CAF module repo (`terraform-azurerm-caf-subnet`) via this skill's create-PR flow; the user later asked why no GitHub release was auto-created after merge. Investigation found the repo has release history (`v3.3.0` etc.) but zero release-producing CI (only PR-triggered fmt/test/docs workflows) — all prior tags were created manually. This skill's PR-creation flow had no step that surfaces that gap, so the missing automation was discovered only after merge instead of being flagged proactively.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- This session never reached this skill's own "6. Merging" section (the PR was merged externally, outside this session) — placing the check at PR-creation time (Section 3) instead of merge time (Section 6) means it fires regardless of who/what performs the actual merge.
