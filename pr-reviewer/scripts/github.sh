#!/usr/bin/env bash
# github.sh — Reusable helpers for GitHub PR operations (pr-reviewer skill)
# Source this file or call the functions directly.
#
# Usage examples:
#   source /home/bernard/.grok/skills/pr-reviewer/scripts/github.sh
#   TOKEN=$(get_github_token)
#   read owner repo num <<< "$(parse_pr_url "https://github.com/foo/bar/pull/123")"
#   sha=$(get_pr_head_sha "$owner" "$repo" "$num")

set -euo pipefail

# Get a fresh GitHub token using the official gh CLI.
# This is more reliable than gh auth status in many environments.
get_github_token() {
    local token
    token=$(gh auth token 2>/dev/null || true)
    if [[ -z "$token" ]]; then
        echo "ERROR: Could not obtain GitHub token via 'gh auth token'." >&2
        echo "Please run: gh auth login   (or gh auth refresh -s repo)" >&2
        return 1
    fi
    echo "$token"
}

# Parse various PR reference formats into "owner repo number"
# Supports:
#   https://github.com/owner/repo/pull/123
#   https://github.com/owner/repo/pull/123/files
#   owner/repo#123
#   owner/repo/pull/123
parse_pr_url() {
    local input="$1"
    local owner repo number

    if [[ "$input" =~ ^https?://github\.com/([^/]+)/([^/]+)/pull/([0-9]+) ]]; then
        owner="${BASH_REMATCH[1]}"
        repo="${BASH_REMATCH[2]}"
        number="${BASH_REMATCH[3]}"
    elif [[ "$input" =~ ^([^/]+)/([^#]+)#([0-9]+)$ ]]; then
        owner="${BASH_REMATCH[1]}"
        repo="${BASH_REMATCH[2]}"
        number="${BASH_REMATCH[3]}"
    elif [[ "$input" =~ ^([^/]+)/([^/]+)/pull/([0-9]+)$ ]]; then
        owner="${BASH_REMATCH[1]}"
        repo="${BASH_REMATCH[2]}"
        number="${BASH_REMATCH[3]}"
    else
        echo "ERROR: Could not parse PR reference: $input" >&2
        echo "Expected formats: https://github.com/owner/repo/pull/123 or owner/repo#123" >&2
        return 1
    fi

    echo "$owner $repo $number"
}

# Get the head commit SHA for a PR (required for inline review comments).
# Uses --repo flag for robustness (works outside git checkouts and avoids
# "owner/repo#N" being misinterpreted as a branch name by gh).
get_pr_head_sha() {
    local owner="$1"
    local repo="$2"
    local number="$3"

    gh pr view --repo "$owner/$repo" "$number" \
        --json headRefOid \
        --jq .headRefOid
}

# Post a single top-level comment on the PR.
# The body can be a large multi-line string.
# Uses --repo + number for robustness (avoids # syntax issues and works
# reliably from any working directory, even without a local git checkout
# of the target repo).
post_pr_comment() {
    local owner="$1"
    local repo="$2"
    local number="$3"
    local body="$4"

    gh pr comment --repo "$owner/$repo" "$number" --body "$body"
}

# Create a full Pull Request Review (event: COMMENT) with optional inline comments.
# The comments_json should be a JSON array of objects with path, line, side, body.
post_pr_review() {
    local owner="$1"
    local repo="$2"
    local number="$3"
    local commit_sha="$4"
    local review_body="$5"
    local comments_json="$6"   # JSON array string or empty

    local payload
    payload=$(jq -n \
        --arg commit "$commit_sha" \
        --arg body "$review_body" \
        --argjson comments "${comments_json:-[]}" \
        '{
            commit_id: $commit,
            body: $body,
            event: "COMMENT",
            comments: $comments
        }')

    echo "$payload" | gh api "repos/$owner/$repo/pulls/$number/reviews" \
        --method POST \
        --input -
}

# Convenience wrapper: get token and export as GITHUB_TOKEN for tools that expect it.
ensure_github_token() {
    local token
    token=$(get_github_token) || return 1
    export GITHUB_TOKEN="$token"
    echo "GITHUB_TOKEN exported (length: ${#token})"
}
