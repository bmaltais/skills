# pr-reviewer Optimization Log

## Session 2026-06-08 — Step 1

(This is a mirror of the canonical training log under ~/.pi/agent/skills/pr-reviewer/ for the skill source tree. See that file for the full entry.)

### Edits Applied
- [op: replace] Fixed `post_top_level_comment` in scripts/post_review.py (both source and agent copies) to use the robust `gh pr comment --repo OWNER/REPO NUMBER` form instead of the fragile `OWNER/REPO#NUMBER` positional syntax. Added explanatory comment. This was the sole P0 edit.

See ~/.pi/agent/skills/pr-reviewer/CHANGELOG.md for complete signals, reasoning, gate validation, and meta notes. This is Step 1 (no prior history).

The primary recommended Python posting helper now matches the claims in SKILL.md, the behavior of github.sh:post_pr_comment, and get_pr_info.

## Session 2026-06-08 — Step 2 (mirror)

**Primary change:** Made posting the default behavior for plain `/pr-reviewer <pr>` invocations (opt-out via `--no-post`).

- Updated frontmatter, Command/flag handling, Workflow, Posting Feedback section (constraints + flow now labeled "default behavior"), Execution Rules, Updated Workflow Notes, and Examples in both .grok and .pi copies of SKILL.md.
- Synced equivalent update to scripts/README.md (Usage section) under both locations.
- Full analysis, signals (including recurrence from Step 1's decision to defer SKILL.md changes), reasoning, deferred items, meta notes, and gate validation are recorded in the canonical ~/.pi/agent/skills/pr-reviewer/CHANGELOG.md.

This resolves the repeated user expectation mismatch for the core "review + post" contract of the skill. The improve-skill invocation that triggered this pass was clean (no friction signals for improve-skill itself).
