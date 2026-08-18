---
name: github-pr-force-merge
description: 'Force-merge a GitHub pull request blocked by branch protection or a repository ruleset (e.g. required code-owner review, required approving reviews), by temporarily disabling only the blocking ruleset(s), merging with admin bypass, then restoring enforcement. Use when the user says "force merge", "expedite", "bypass review", "merge anyway", or gives a GitHub PR URL/number and asks to merge it despite it being blocked. Always re-enables any ruleset it disabled — never leaves protections off.'
argument-hint: '<PR_URL_or_number> [owner/repo] [merge_method]'
---

# GitHub PR Force Merge

Merge a blocked GitHub PR by bypassing branch protection, restoring it afterward. Mirrors `azure-devops-pr-expedite` but for GitHub repos (classic branch protection + repository rulesets).

## Preferred approach — run the script

Run [force-merge-pr.sh](./scripts/force-merge-pr.sh):

```bash
./scripts/force-merge-pr.sh <PR_URL_or_number> [owner/repo] [merge_method]
```

- Accepts a full PR URL (`https://github.com/OWNER/REPO/pull/N`) or just the number with `owner/repo` as the 2nd arg.
- `merge_method` defaults to `squash` (`merge` | `squash` | `rebase`).
- First tries a plain `gh pr merge --admin` (handles classic branch-protection required reviews, which admin bypass alone can satisfy).
- If that fails with a **repository ruleset violation** (e.g. `require_code_owner_review`, which admin bypass does NOT skip when `current_user_can_bypass: never`), it:
  1. Lists rulesets via `gh api repos/OWNER/REPO/rulesets`, finds `active` ones with `target: branch` whose `conditions.ref_name.include` matches the PR's base branch.
  2. Disables only those rulesets (`enforcement=disabled`), saving their IDs to `/tmp/gh-force-merge-<owner>-<repo>-<PR>-rulesets.txt`.
  3. Retries `gh pr merge --admin`.
  4. Restores `enforcement=active` on every disabled ruleset via an EXIT/INT/TERM trap — runs even if the merge itself fails.

If the script was interrupted and rulesets are still disabled, run the emergency restore, [restore-rulesets.sh](./scripts/restore-rulesets.sh):

```bash
./scripts/restore-rulesets.sh <owner/repo> <PR_number>
```

## When to use

- User says: "force merge PR #N", "expedite this PR", "bypass the review requirement and merge", "merge anyway"
- The PR is open, checks are green (or user accepts the risk), but `mergeable_state` is `blocked` due to missing approvals or a required code-owner review.

## Prerequisites

- `gh auth status` must show an **active** account with `repo` and `workflow` scopes.
- That account must have **admin** permission on the repo (check: `gh api repos/OWNER/REPO --jq '.permissions'`) — required both to use `--admin` merge bypass and to toggle ruleset enforcement.
- Prefer the `gh` CLI account, not the MCP GitHub tool — the MCP GitHub merge tool may run under different/invalid credentials and 404 even when `gh` itself works. If the MCP `merge_pull_request` tool 404s, fall back to `gh pr merge` directly.

## Manual steps (if the script can't be run)

1. **Check PR status**
   ```bash
   gh pr view <PR_NUM> --repo OWNER/REPO --json state,mergeable,mergeStateStatus,baseRefName
   ```

2. **Try the simple path first**
   ```bash
   gh pr merge <PR_NUM> --repo OWNER/REPO --squash --admin
   ```
   If this succeeds, stop — classic branch protection was the only blocker and admin bypass handled it.

3. **If it fails with "Repository rule violations found" / "Waiting on code owner review"**, a repository ruleset (not classic protection) is blocking it. List rulesets:
   ```bash
   gh api repos/OWNER/REPO/rulesets
   ```
   Inspect each to find the one targeting the base branch:
   ```bash
   gh api repos/OWNER/REPO/rulesets/<ID>
   # look for: target: "branch", enforcement: "active",
   # conditions.ref_name.include containing "refs/heads/<base>"
   ```

4. **Disable it, note the ID**
   ```bash
   gh api -X PUT repos/OWNER/REPO/rulesets/<ID> -f enforcement=disabled
   ```

5. **Retry the merge**
   ```bash
   gh pr merge <PR_NUM> --repo OWNER/REPO --squash --admin
   ```

6. **Always restore enforcement immediately after**, success or failure:
   ```bash
   gh api -X PUT repos/OWNER/REPO/rulesets/<ID> -f enforcement=active
   ```

## Key facts learned

- `mergeable_state: "blocked"` with all check runs green almost always means a **review requirement** (classic protection's `required_pull_request_reviews` and/or a repository ruleset's `require_code_owner_review`), not a failing CI check.
- Classic branch protection (`enforce_admins: false`) can be bypassed by `gh pr merge --admin` alone.
- Repository **rulesets** are a separate, newer mechanism. Check `current_user_can_bypass` in the ruleset detail — if `"never"`, no bypass flag will work; the ruleset itself must be toggled to `enforcement=disabled` for the merge, then back to `active`.
- Never leave a ruleset or branch protection disabled after the merge — always restore in a `trap`, not just at the end of a linear script.
