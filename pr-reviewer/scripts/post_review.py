#!/usr/bin/env python3
"""
post_review.py — Robust helper for posting Copilot Reviewer output to GitHub PRs.

This script is the preferred way for the pr-reviewer skill to post feedback.

Features:
- Parses the exact **Summary** / 🔴 Critical / 🟡 Suggestions / ✅ Positive format.
- Supports three modes: top-level comment, inline review comments, or hybrid.
- Uses `gh` under the hood (via subprocess) so it benefits from gh auth.
- Can use explicit token from `gh auth token` when needed.
- Safe dry-run mode.
- Extracts file:line references and suggested fixes into proper GitHub review comments.

Usage from the skill:
    python3 /home/bernard/.grok/skills/pr-reviewer/scripts/post_review.py \
        --pr-url https://github.com/owner/repo/pull/123 \
        --review-file /tmp/review.md \
        --mode hybrid \
        --confirm   # or let the skill handle confirmation first

    # Or pipe the review:
    cat review.md | python3 ... --pr-url ... --mode comment --stdin
"""

import argparse
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import List, Dict, Optional, Tuple


FINDING_RE = re.compile(
    r"^\s*-\s+`(?P<path>[^:`]+):(?P<line>\d+)`\s*[–-]\s*(?P<desc>.+?)(?:\s*Suggested fix:)?$",
    re.IGNORECASE | re.MULTILINE,
)


def run_gh(args: List[str], input_data: Optional[str] = None, check: bool = True) -> str:
    """Run a gh command and return stdout."""
    cmd = ["gh"] + args
    try:
        result = subprocess.run(
            cmd,
            input=input_data.encode() if input_data else None,
            capture_output=True,
            check=check,
        )
        return result.stdout.decode().strip()
    except subprocess.CalledProcessError as e:
        print(f"gh command failed: {' '.join(cmd)}", file=sys.stderr)
        print(e.stderr.decode(), file=sys.stderr)
        if check:
            raise
        return ""


def parse_pr_identifiers(pr_ref: str) -> Tuple[str, str, str]:
    """Return (owner, repo, number) for a PR reference. Does not require git or network."""
    # Use the shell helper if available for consistency
    try:
        out = subprocess.check_output(
            ["bash", "-c", f"source /home/bernard/.grok/skills/pr-reviewer/scripts/github.sh && parse_pr_url '{pr_ref}'"],
            text=True,
        ).strip()
        owner, repo, number = out.split()
        return owner, repo, number
    except Exception:
        pass

    # Fallback simple parser (supports URL and owner/repo#N forms)
    m = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_ref)
    if not m:
        m = re.search(r"([^/]+)/([^#]+)#(\d+)", pr_ref)
    if not m:
        raise ValueError(f"Could not parse PR: {pr_ref}")
    return m.groups()


def get_pr_info(pr_ref: str) -> Tuple[str, str, str, Optional[str]]:
    """Return (owner, repo, number, head_sha). head_sha may be None if fetch fails.
    head_sha is only needed for inline/hybrid modes; top-level comments work without it.
    Uses robust --repo syntax internally.
    """
    owner, repo, number = parse_pr_identifiers(pr_ref)

    head_sha: Optional[str] = None
    try:
        # Use --repo form (more reliable than owner/repo#N, works outside any git checkout)
        head_sha = run_gh(
            ["pr", "view", "--repo", f"{owner}/{repo}", number, "--json", "headRefOid", "--jq", ".headRefOid"],
            check=False,  # best effort; many comment-only flows don't need it
        )
    except Exception:
        head_sha = None

    return owner, repo, number, head_sha


def get_head_sha_for_review(owner: str, repo: str, number: str) -> str:
    """Fetch head SHA; raises a clear error if unavailable (required for inline comments)."""
    try:
        sha = run_gh(
            ["pr", "view", "--repo", f"{owner}/{repo}", number, "--json", "headRefOid", "--jq", ".headRefOid"]
        )
        if not sha:
            raise RuntimeError("Empty head SHA returned")
        return sha
    except Exception as e:
        raise RuntimeError(
            f"Could not determine head commit SHA for {owner}/{repo}#{number}. "
            "Inline/hybrid mode requires it for anchoring comments to the exact commit. "
            f"Details: {e}"
        ) from e


def parse_review_text(text: str) -> List[Dict]:
    """
    Parse the Copilot Reviewer structured output into a list of findings.

    Looks for lines containing `path:line` inside the Critical / Suggestions sections.
    """
    findings = []
    current_severity = None

    # Normalize dashes
    text = text.replace("–", "-").replace("—", "-")

    # First pass: find the last seen severity header before each potential bullet
    lines = text.splitlines()

    for idx, line in enumerate(lines):
        # Update current section
        low = line.lower()
        if "🔴" in line or "critical issues" in low:
            current_severity = "critical"
            continue
        if "🟡" in line or "suggestions" in low:
            current_severity = "suggestion"
            continue
        if "✅" in line or "positive notes" in low:
            current_severity = None
            continue

        if not current_severity:
            continue

        # Match the file:line pattern
        m = re.search(r"`([^:`]+):(\d+)`\s*-\s*(.+)", line)
        if m:
            path, lineno, desc = m.groups()
            desc = desc.strip()

            # Collect the next few lines as suggestion/context (until next bullet or header)
            suggestion_lines = []
            for j in range(idx + 1, min(idx + 12, len(lines))):
                l = lines[j]
                if re.search(r"`[^:`]+:\d+`", l) and l.strip().startswith("-"):
                    break
                if l.strip().startswith("**") and ("Critical" in l or "Suggestion" in l or "Positive" in l):
                    break
                suggestion_lines.append(l.rstrip())

            suggestion = "\n".join(suggestion_lines).strip()

            findings.append({
                "severity": current_severity,
                "path": path.strip(),
                "line": int(lineno),
                "description": desc,
                "suggestion": suggestion,
            })

    return findings


def _split_description_and_suggestion(text: str) -> Tuple[str, str]:
    """Split a bullet body into description and suggested fix."""
    if "Suggested fix" in text:
        parts = re.split(r"Suggested fix[:\s]*", text, maxsplit=1, flags=re.IGNORECASE)
        return parts[0].strip(), (parts[1] if len(parts) > 1 else "").strip()
    return text.strip(), ""


def build_github_comments(findings: List[Dict]) -> List[Dict]:
    """Convert our findings into GitHub review comment objects (for the /reviews API)."""
    comments = []
    for f in findings:
        body = f"**{f['severity'].upper()}**: {f['description']}\n\n"
        if f["suggestion"]:
            body += f"**Suggested fix**:\n{f['suggestion']}\n"

        comments.append(
            {
                "path": f["path"],
                "line": f["line"],
                "side": "RIGHT",
                "body": body.strip(),
            }
        )
    return comments


def build_top_level_body(review_text: str, findings: List[Dict]) -> str:
    """Create a nice top-level comment body from the full review."""
    # Keep the original review format but add a small header
    header = "**Copilot Reviewer** — automated review\n\n"
    return header + review_text.strip()


def post_top_level_comment(owner: str, repo: str, number: str, body: str, dry_run: bool = False) -> str:
    if dry_run:
        print("=== DRY RUN: Would post top-level comment ===")
        print(body[:500] + "..." if len(body) > 500 else body)
        return "dry-run"

    return run_gh(["pr", "comment", f"{owner}/{repo}#{number}", "--body", body])


def post_review_with_comments(
    owner: str,
    repo: str,
    number: str,
    head_sha: str,
    review_body: str,
    comments: List[Dict],
    dry_run: bool = False,
) -> str:
    payload = {
        "commit_id": head_sha,
        "body": review_body,
        "event": "COMMENT",
        "comments": comments,
    }

    if dry_run:
        print("=== DRY RUN: Would submit review ===")
        print(json.dumps(payload, indent=2))
        return "dry-run"

    return run_gh(
        ["api", f"repos/{owner}/{repo}/pulls/{number}/reviews", "--method", "POST", "--input", "-"],
        input_data=json.dumps(payload),
    )


def main():
    parser = argparse.ArgumentParser(description="Post Copilot Reviewer output to a GitHub PR.")
    parser.add_argument("--pr-url", required=True, help="PR URL or owner/repo#123")
    parser.add_argument("--review-file", help="Path to file containing the full review text")
    parser.add_argument("--stdin", action="store_true", help="Read review from stdin")
    parser.add_argument(
        "--mode",
        choices=["comment", "inline", "hybrid"],
        default="comment",
        help="comment = top-level only, inline = review with line comments, hybrid = both",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without posting")
    parser.add_argument("--confirm", action="store_true", help="Actually post (the skill should ask first)")

    args = parser.parse_args()

    # Best-effort early auth check with actionable guidance.
    # The actual gh calls will surface real errors, but this helps users quickly.
    try:
        token = run_gh(["auth", "token"], check=False)
        if not token:
            print(
                "WARNING: No GitHub token available via 'gh auth token'.\n"
                "         Run one of:\n"
                "           gh auth login\n"
                "           gh auth refresh -s repo\n"
                "         Then re-run this command.",
                file=sys.stderr,
            )
    except Exception:
        pass

    # Get review text
    if args.review_file:
        review_text = Path(args.review_file).read_text()
    elif args.stdin:
        review_text = sys.stdin.read()
    else:
        parser.error("Provide --review-file or --stdin")

    findings = parse_review_text(review_text)
    print(f"Parsed {len(findings)} findings (critical + suggestions)")

    criticals = [f for f in findings if f["severity"] == "critical"]
    suggestions = [f for f in findings if f["severity"] == "suggestion"]

    # Parse PR identifiers (owner/repo/number) — this is cheap and works offline.
    # head_sha is optional for pure top-level comments.
    owner = repo = number = head_sha = None
    try:
        owner, repo, number, head_sha = get_pr_info(args.pr_url)
        sha_display = head_sha[:8] if head_sha else "unavailable (ok for comment mode)"
        print(f"Target: {owner}/{repo}#{number} (head: {sha_display})")
    except Exception as e:
        print(f"Could not parse PR identifiers from {args.pr_url}: {e}")
        # Without identifiers we can't post anything useful.
        if not args.dry_run:
            print("ERROR: A valid --pr-url (or owner/repo#N) is required to post.", file=sys.stderr)
            sys.exit(1)
        owner = repo = number = None  # will trigger dry-run prints below

    # For inline/hybrid we *must* have a head SHA (to anchor comments to the diff).
    needs_sha = args.mode in ("inline", "hybrid")
    if needs_sha and owner and repo and number and not head_sha:
        if args.dry_run:
            print("Note: head SHA not available in this environment (inline comments will be simulated).")
        else:
            try:
                head_sha = get_head_sha_for_review(owner, repo, number)
            except RuntimeError as e:
                print(f"ERROR: {e}", file=sys.stderr)
                sys.exit(1)

    if args.dry_run or not args.confirm:
        print("Running in dry-run / preview mode (no writes will be performed).")
        args.dry_run = True

    # Always build the full top-level body from the original review
    top_body = build_top_level_body(review_text, findings)

    posted_urls = []

    if args.mode in ("comment", "hybrid"):
        if owner and repo and number:
            result = post_top_level_comment(owner, repo, number, top_body, dry_run=args.dry_run)
            print(f"Top-level comment result: {result}")
            posted_urls.append(f"https://github.com/{owner}/{repo}/pull/{number}")
        else:
            print("DRY-RUN: Would post the following as top-level comment:")
            print(top_body[:800] + ("..." if len(top_body) > 800 else ""))

    if args.mode in ("inline", "hybrid"):
        gh_comments = build_github_comments(criticals + suggestions)
        if not gh_comments:
            print("No file:line findings found — skipping inline comments.")
        else:
            if owner and repo and number and head_sha:
                # Put a short summary in the review body for the inline case
                short_body = f"**Copilot Reviewer** — see inline comments for details.\n\n{len(criticals)} critical, {len(suggestions)} suggestions."
                result = post_review_with_comments(
                    owner, repo, number, head_sha, short_body, gh_comments, dry_run=args.dry_run
                )
                print(f"Review with {len(gh_comments)} inline comments submitted: {result}")
                posted_urls.append(f"https://github.com/{owner}/{repo}/pull/{number}")
            else:
                print(f"DRY-RUN: Would create a review with {len(gh_comments)} inline comments on the following lines:")
                for c in gh_comments:
                    print(f"  {c['path']}:{c['line']}")

    if posted_urls and not args.dry_run:
        print("\nPosted to:")
        for u in set(posted_urls):
            print(f"  {u}")

    if args.dry_run:
        print("\n(This was a dry run. Re-run with --confirm after user approval.)")


if __name__ == "__main__":
    main()
