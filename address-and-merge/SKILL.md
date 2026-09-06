---
name: address-and-merge
description: Address the review feedback on an open PR, then squash-merge it and delete the branch. Use when the user says "address the feedback on PR N", "fix the review comments", "merge PR N", or "address and merge".
---

# Address and Merge

**Product:** a merged PR and a clean repo. Concretely — every unresolved review
thread on the PR ends in either a code change or a stated reason it needs none;
those changes land as one commit; the PR is squash-merged; both branches are
gone and the repo sits on an up-to-date default branch.

Derived from the PR's review threads. No threads fetched, no work to do — the
run halts rather than guessing what "the feedback" meant.

```
/address-and-merge          — detect the current branch's open PR
/address-and-merge #N       — go straight to PR N
```

## Phase 0 — Preconditions

```bash
gh auth status
git status --porcelain     # must be empty
```

Uncommitted work is the dangerous one: Phase 5 commits everything the fixes
touch, and pre-existing edits ride along invisibly. Stop and tell the user;
let them stash or commit.

## Phase 1 — Identify the PR

```bash
gh pr view [N] --json number,state,headRefName,baseRefName
```

With no `N`, this resolves the current branch's PR. Halt if there is no PR, or
if `state` is not `OPEN`.

```bash
git checkout <headRefName> && git pull
```

## Phase 2 — Fetch unresolved feedback

Two endpoints, two comment types. `gh pr view --comments` returns only
conversation-level comments — inline review comments (where automated reviewers
like Copilot live) come from the API, and only GraphQL carries the resolved
flag, so already-handled threads can be skipped.

```bash
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

# 1. Inline review threads, unresolved only
gh api graphql -f query='
query($owner:String!,$name:String!,$pr:Int!){
  repository(owner:$owner,name:$name){ pullRequest(number:$pr){
    reviewThreads(first:100){ nodes{
      isResolved
      comments(first:1){ nodes{ path line body author{login} } } } } } } }' \
  -F owner=${REPO%/*} -F name=${REPO#*/} -F pr=<N> \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[]
        | select(.isResolved | not) | .comments.nodes[0]'

# 2. Conversation-level comments
gh pr view <N> --json comments --jq '.comments[] | {author: .author.login, body: .body}'
```

Write the resulting list down before editing anything — it is the checklist
Phase 3 closes against. Nothing unresolved in either stream: skip to Phase 6.

## Phase 3 — Address each item

For each item on the checklist:

1. **Locate** — `path` + `line` for inline threads; grep the named symbol for
   conversation comments.
2. **Read the surrounding code** before editing. Ambiguous comment: take the
   most reasonable reading and record it in the commit message.
3. **Apply the fix** with the edit tool, so the change is reviewable as a diff.

Some comments are wrong, or already handled by other code. Those close with a
written reason, not a change — but they still close explicitly.

**Completion criterion:** every item on the Phase 2 checklist is marked either
*fixed* (with the file it touched) or *declined* (with the reason). A tally that
is short of the fetched list means Phase 3 is not done.

## Phase 4 — Verify

Find the project's canonical commands first — `Makefile`, `AGENTS.md`,
`CLAUDE.md`, `README.md`, or the `scripts` block of `package.json`. Use those.
Absent any of them, fall back to the language default (Go:
`go build ./... && go test ./... && go vet ./...`; Node: `npm test`; Python:
`pytest`).

**Postcondition:** the chosen command exits 0. A failure is fixed, never
suppressed or skipped.

## Phase 5 — Commit and push

One commit for all review fixes, naming the PR and summarising what changed:

```bash
git add <changed files>
git commit -m "fix: address PR #70 review feedback (NoOptDefVal constant, errCount on merge error)"
git push
```

Push as a new commit on top of the reviewed history, so reviewers can diff what
changed since their review.

## Phase 6 — Merge and clean up

```bash
gh pr merge <N> --squash --delete-branch
```

Squash keeps the default branch linear; `--delete-branch` removes the remote
branch and switches back before deleting the local one.

"Pull Request is not mergeable" right after a push is usually GitHub's API
lagging. Check, then retry once:

```bash
gh pr view <N> --json mergeable,mergeStateStatus,state
sleep 5 && gh pr merge <N> --squash --delete-branch
```

If the local branch survives, delete it with `git branch -D <branch>` — after a
squash the branch tip is not an ancestor of main, so `-d` refuses and `-D` is
the safe correct call.

**Postcondition** — all four must hold:

```bash
gh pr view <N> --json state --jq '.state'      # MERGED
git rev-parse --abbrev-ref HEAD                # the base branch
git branch --list <branch>                     # empty
git ls-remote --heads origin <branch>          # empty
```

## Phase 7 — Report

```
PR #N merged ✓  (<count> comments addressed, <count> declined)
Branch <branch> deleted (remote + local) ✓
Now on <base> @ <short SHA>
```
