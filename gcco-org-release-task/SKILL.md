---
name: gcco-org-release-task
description: Create an Azure DevOps Task to track updating a GCCO org (in AZDO-OrgMGMT-163ENT) to a new release. Use this whenever the user updates a terragrunt.hcl `local.release` value for an org and wants to log the change as a work item. Trigger on phrases like "create a task for this org update", "log this release update", "create a work item for this org", "track this update in DevOps", "create a DevOps task", "log that I updated the org", or when the user says they updated an org's release and want to record it.
categories: [software-development]
agents: [copilot]
metadata:
  source: custom
  scope: global
---

# GCCO Org Release Task Creator

Creates an Azure DevOps Task in the `Activities` project to track updating a GCCO org to a new release — mirroring task #4413 (the reference for DND-AICentre / release 20260310.0).

**Script**: `scripts/create_release_task.sh` — always use this script. Do not hand-craft individual `az` commands.

## Step 1 — Gather context

Extract these from the open file and conversation. Ask for anything missing.

| Variable | Source |
|---|---|
| `ORG_NAME` | Folder name in `organizations/` (e.g. `DND-AICentre`) — from the open file path |
| `RELEASE` | `local.release` in the org's `terragrunt.hcl` (e.g. `20260310.0`) |
| `ESLZ_VERSION` | Default `r3.2` for release `20260310.0` — ask the user only if different |
| `PARENT_ID` | Default `3121` — ask only if the user wants a different parent story |
| `CLOSE_TASK` | Default **yes** (work already done) — add `--no-close` flag only if user says otherwise |

## Step 2 — Run the script

```bash
SKILL_DIR="/home/bernard/.copilot/skills/gcco-org-release-task"
bash "$SKILL_DIR/scripts/create_release_task.sh" \
  "{ORG_NAME}" "{RELEASE}" "{ESLZ_VERSION}" "{PARENT_ID}"
# Append --no-close if the task should stay open
```

The script:
1. Detects the current sprint automatically
2. Creates the task with the correct area, iteration, description, priority, and assignee
3. Links it to the parent story
4. Closes it (unless `--no-close` is passed)
5. Prints the task URL

## Step 3 — Report back

After the script completes, show the user the task ID and URL printed by the script.

---

## Reference — Task #4413 (DND-AICentre)

| Field | Value |
|---|---|
| Title | Update DND-AICentre to release 20260310.0 |
| Type | Task |
| Area | `Activities\Projects\GCCO Releases` |
| Iteration | `Activities\Projects\FY 2025-2026\Q3\Sprint (10-15 10-28)` |
| Description | In preparation for the project update to ESLZ r3.2 we need to update the ADO Org release to release 20260310.0. |
| Priority | 2 |
| Assigned To | admin.bernard.maltais@ent.cloud-nuage.canada.ca |
| Parent | 3121 (OrgMGMT Fix) |
| State | Closed |
