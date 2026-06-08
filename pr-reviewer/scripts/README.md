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

The SKILL.md instructs the agent to prefer:

```bash
python3 /home/bernard/.grok/skills/pr-reviewer/scripts/post_review.py \
  --pr-url "..." \
  --review-file /tmp/review.md \
  --mode hybrid \
  --dry-run
```

After user says "yes, post it", re-run with `--confirm`.

## Design philosophy

- Parsing of the review text is done in Python (reliable regex + line walking) because the structured output contains code blocks and multi-line suggestions.
- All actual writes go through `gh` (so we inherit the user's authentication and never handle raw tokens unless explicitly requested).
- Dry-run is always safe and shows the agent (and user) exactly what would be posted.
