# pr-reviewer helpers

This directory contains the official helpers for the `/pr-reviewer` skill.

## Files

- `github.sh` — Bash library. Source it to get:
  - `get_github_token` (wraps `gh auth token`)
  - `parse_pr_url`
  - `get_pr_head_sha`
  - `post_pr_comment`
  - `post_pr_review`
  - `ensure_github_token`

- `post_review.py` — **Main recommended tool** for posting.
  - Parses the exact structured review format produced by the Copilot Reviewer persona.
  - Supports `--mode comment|inline|hybrid`
  - `--dry-run` for safe previews
  - `--confirm` to actually post
  - Automatically uses `gh auth token` + the shell helpers

## Usage inside the skill

The SKILL.md instructs the agent that plain `/pr-reviewer <pr>` (or equivalent) means **review + post by default**.

The agent should:

1. Output the exact structured review (starting with **Summary**).
2. Write the review to a temp file.
3. Run the helper with `--dry-run` (the result is shown for transparency).
4. Because the command itself signals posting intent, immediately re-run the same command with `--confirm` (unless the user used `--no-post` or objects after the dry-run preview).

Example (default top-level comment):

```bash
python3 /home/bernard/.grok/skills/pr-reviewer/scripts/post_review.py \
  --pr-url "https://github.com/OWNER/REPO/pull/123" \
  --review-file /tmp/copilot-review.md \
  --mode comment \
  --dry-run

# then
python3 ... --confirm
```

Use `--mode hybrid` (or `--inline`) only when the user explicitly requests line-anchored comments. Use `--no-post` / `--review-only` to produce the review text without writing to the PR.

## Design philosophy

- Parsing of the review text is done in Python (reliable regex + line walking) because the structured output contains code blocks and multi-line suggestions.
- All actual writes go through `gh` (so we inherit the user's authentication and never handle raw tokens unless explicitly requested).
- Dry-run is always safe and shows the agent (and user) exactly what would be posted.
