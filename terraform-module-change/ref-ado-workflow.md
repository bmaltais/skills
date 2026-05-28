# ADO Work Item Workflow

## Step 2b — Post plan comment (before writing any code)

Set work item to **Active** and post the implementation plan as a discussion comment.

```bash
source ~/dotfiles/sp/163ent-devops.user

az boards work-item update \
  --id <WI_ID> \
  --state "Active" \
  --org https://dev.azure.com/Azure163ent-CloudOperations
```

```bash
SKILL_DIR="/home/bernard/.copilot/skills/azure-devops-work-item-comment"
cat <<'EOF' | bash "$SKILL_DIR/scripts/add_comment.sh" <WI_ID>
<h2>Implementation Plan — <feature></h2>
<h3>Goal</h3><p>...</p>
<h3>Design Decisions</h3><ul><li>...</li></ul>
<h3>File Layout</h3><ul><li>...</li></ul>
<h3>Test Plan</h3><ol><li>...</li></ol>
<h3>Example Usage</h3><pre>...</pre>
EOF
```

The plan comment must include: Goal, Design decisions, File layout, Test plan,
Example usage snippet.

Do **not** proceed to Step 3 until the plan comment is posted successfully.

---

## Step 7 (completion) — Post completion comment

After updating RELEASE_NOTES.md, post a completion comment. Do this proactively
(do not wait for the user to ask), including for follow-on changes made later in
the same session.

```bash
SKILL_DIR="/home/bernard/.copilot/skills/azure-devops-work-item-comment"
echo "<p>Implementation complete: ...</p>" | bash "$SKILL_DIR/scripts/add_comment.sh" <WI_ID>
```

Include: what changed, key design decisions (and rejected alternatives), test count,
and the release note entry.

If the implementation required a design pivot, explain: original approach, what
changed, and why — do not leave stale plan comments as the last record of intent.
