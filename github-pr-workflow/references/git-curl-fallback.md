# Git + curl Fallback Commands

The full `git` + `curl` command set for machines without `gh` installed — reached only when the Quick Auth Detection block in `SKILL.md` sets `AUTH="git"`. Mirrors `SKILL.md` one-for-one: same section numbers, same order, same intent. Sections 1 and 2 (branch creation, commits) aren't listed here because they're pure `git` and already identical in both paths.

## Extracting Owner/Repo from the Git Remote

Every command below needs `owner/repo`. Extract it once, from the git remote:

```bash
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
echo "Owner: $OWNER, Repo: $REPO"
```

## Section 3 — Creating a PR

```bash
BRANCH=$(git branch --show-current)

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{
    \"title\": \"feat: add JWT-based user authentication\",
    \"body\": \"## Summary\nAdds login and register API endpoints.\n\nCloses #42\",
    \"head\": \"$BRANCH\",
    \"base\": \"main\"
  }"
```

The response JSON includes the PR `number` — save it for later commands. To create as a draft, add `"draft": true` to the JSON body.

Requesting an automated review (e.g. `@copilot`):

```bash
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/<PR_NUMBER>/comments \
  -d '{"body":"@copilot perform a multiple axis and in-depth review of the PR"}'
```

## Section 4 — Monitoring CI Status

```bash
# Get the latest commit SHA on the current branch
SHA=$(git rev-parse HEAD)

# Query the combined status
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Overall: {data['state']}\")
for s in data.get('statuses', []):
    print(f\"  {s['context']}: {s['state']} - {s.get('description', '')}\")"

# Also check GitHub Actions check runs (separate endpoint)
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/check-runs \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for cr in data.get('check_runs', []):
    print(f\"  {cr['name']}: {cr['status']} / {cr['conclusion'] or 'pending'}\")"
```

Poll until complete — check every 30 seconds, up to 10 minutes:

```bash
SHA=$(git rev-parse HEAD)
for i in $(seq 1 20); do
  STATUS=$(curl -s \
    -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
  echo "Check $i: $STATUS"
  if [ "$STATUS" = "success" ] || [ "$STATUS" = "failure" ] || [ "$STATUS" = "error" ]; then
    break
  fi
  sleep 30
done
```

## Section 5 — Auto-Fixing CI Failures

```bash
BRANCH=$(git branch --show-current)

# List workflow runs on this branch
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/runs?branch=$BRANCH&per_page=5" \
  | python3 -c "
import sys, json
runs = json.load(sys.stdin)['workflow_runs']
for r in runs:
    print(f\"Run {r['id']}: {r['name']} - {r['conclusion'] or r['status']}\")"
```

Once you have a `RUN_ID`, see [`ci-troubleshooting.md`](ci-troubleshooting.md) for the log-download command and the failure-pattern table.

## Section 6 — Merging

```bash
PR_NUMBER=<number>

# Merge the PR via API (squash)
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d "{
    \"merge_method\": \"squash\",
    \"commit_title\": \"feat: add user authentication (#$PR_NUMBER)\"
  }"

# Delete the remote branch after merge
BRANCH=$(git branch --show-current)
git push origin --delete $BRANCH

# Switch back to main locally
git checkout main && git pull origin main
git branch -d $BRANCH
```

Merge methods: `"merge"` (merge commit), `"squash"`, `"rebase"`.

### Enable Auto-Merge

`gh pr merge --auto` covers this on the `gh` path. Without `gh`, auto-merge needs the GraphQL API — REST has no equivalent:

```bash
PR_NODE_ID=$(curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'])")

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/graphql \
  -d "{\"query\": \"mutation { enablePullRequestAutoMerge(input: {pullRequestId: \\\"$PR_NODE_ID\\\", mergeMethod: SQUASH}) { clientMutationId } }\"}"
```

## Other PR Actions

| Action | git + curl |
|--------|-----------|
| List my PRs | `curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$OWNER/$REPO/pulls?state=open"` |
| View PR diff | `git diff main...HEAD` (local) or `curl -H "Accept: application/vnd.github.diff" -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/repos/$OWNER/$REPO/pulls/N` |
| Add comment | `curl -X POST -H "Authorization: token $GITHUB_TOKEN" .../issues/N/comments -d '{"body":"..."}'` |
| Request review | `curl -X POST -H "Authorization: token $GITHUB_TOKEN" .../pulls/N/requested_reviewers -d '{"reviewers":["user"]}'` |
| Update title/body | `curl -X PATCH -H "Authorization: token $GITHUB_TOKEN" .../pulls/N -d '{"title":"...","body":"..."}'` |
| Close PR | `curl -X PATCH -H "Authorization: token $GITHUB_TOKEN" .../pulls/N -d '{"state":"closed"}'` |
| Check out someone's PR | `git fetch origin pull/N/head:pr-N && git checkout pr-N` |
