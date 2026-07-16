---
name: itsg-33-assess
description: >-
  Assess a local repo against ITSG-33 PBMM controls, producing evidence cards, a
  compliance report, and gap issues for failing controls. Use when the user wants
  an ITSG-33 or PBMM compliance assessment, or asks for a Security Assessment
  Report (SAR) package for this repo.
---

Assess the repo's code and IaC against ITSG-33 PBMM controls, producing evidence cards
and a rolled-up compliance report. Every run is **incremental** — re-assess only controls
whose relevant files changed; reuse cached findings for the rest.

## Branch: Init

**Trigger:** `security/itsg33.yaml` is absent.

1. **Prompt** for system name and system boundary description.
2. **Confirm** security profile — default PBMM; accept override.
3. **Detect** tracker mode from `git remote -v`:

   | Remote contains | `tracker` |
   |---|---|
   | `github.com` | `github` |
   | `dev.azure.com` | `azure-devops` |
   | neither | `local` |
4. **Write** `security/itsg33.yaml`:
   ```yaml
   profile: PBMM
   system_name: <value>
   system_boundary: <value>
   tracker: <github | azure-devops | local>
   ```
   For `tracker: azure-devops` only, also write `ado_org`, `ado_project`, `ado_repo`, parsed
   from the remote URL:
   - HTTPS form: `https://[<user>@]dev.azure.com/<org>/<project>/_git/<repo>`
   - SSH form: `git@ssh.dev.azure.com:v3/<org>/<project>/<repo>`

   ```yaml
   ado_org: https://dev.azure.com/<org>
   ado_project: <project>
   ado_repo: <repo>
   ```

   Completion: file exists, all four base fields are populated, and (for `tracker:
   azure-devops`) `ado_org`/`ado_project`/`ado_repo` are also populated.
5. **Create** folder structure:
   - `security/evidence/` — one `.md` per assessed control
   - `security/gaps/` — local gap files (used when `tracker: local`)
   Completion: both directories exist.
6. Continue directly into the **Assess branch** — no separate invocation needed.

---

## Branch: Assess

**Trigger:** Every run (including immediately after Init).

### Step 1 — Read config

Read `security/itsg33.yaml`. Accept `--profile <value>` argument as a run-time override
of `profile`. Completion: active profile and tracker mode are known.

### Step 2 — Fingerprint tech stack

Detect which file patterns are present in the repo:

| Signal | Pattern |
|--------|---------|
| Terraform | `**/*.tf` |
| Kubernetes manifests | `**/*.yaml`, `**/*.yml` (k8s heuristic: contains `apiVersion:` and `kind:`) |
| Helm values | `**/values*.yaml` |
| Dockerfile | `**/Dockerfile*` |
| GitHub Actions | `.github/workflows/*.yaml` |
| Go module | `go.mod` |
| Node | `package.json` |
| Python | `requirements*.txt`, `pyproject.toml` |

Completion: list of detected signal families recorded (e.g., `[terraform, kubernetes, github-actions]`).

### Step 3 — Load control catalogue

Load [`controls.md`](controls.md) via this context pointer. Completion: all control entries are loaded and available for Step 4.

### Step 4 — Dispatch family subagents

Partition `controls.md` by control family prefix: **AC, AU, IA, SC, CM, SI, SA, CP, RA**. In a
single message, dispatch one subagent per family (Task/Agent tool, parallel calls) — every
family gets a subagent every run, even if none of its controls changed since the last run.

Each subagent's dispatch prompt must include:
- The active `profile`, `system_name`, `system_boundary`, and tracker mode (from Step 1)
- The detected signal list from Step 2
- A pointer to `controls.md`, with an instruction to process only entries whose control ID
  starts with its assigned family prefix
- A pointer to `evidence-card.md` (the template to use when writing evidence cards)
- A pointer to `finding-rules.md` (the rules for weighing Pass/Fail/Not Assessable signals in Step 4c)
- The subagent contract below (steps 4a-4e)

**Subagent contract (per family)**

For each control in the assigned family, in order:

**4a. Cache check**
Read `security/assessment-state.yaml`. For each file listed under this control's
`files_read`, hash the current content and compare to the stored hash. If all hashes match,
this control is cached: set `"cached": true` on its fragment entry (Step 4's write-up below),
and do not rewrite its evidence card. `merge-state.py` (Step 5) is the sole authority for a
cached control's `finding`, `confidence`, and `files_read` in `assessment-state.yaml` — it
always uses the values already stored there, discarding whatever you write for these fields
on a cached control, so you do not need to reproduce them precisely; carrying forward your
best-available copy is enough. The remaining fragment fields (`risk_summary`,
`implementation_approach`, `evidence_artefacts`, `client_responsibility`) are never read for a
cached control either, since its evidence card is not rewritten — but `write-fragment.py` still
requires every field to be present, so do not omit them. Use a short placeholder string such as
`"(cached — see evidence card)"` for the three string fields, and a placeholder list such as
`["(cached)"]` for `evidence_artefacts` (any list is accepted; an empty list `[]` also works).
Skip to next control.

**4b. Read relevant files**
Glob the control's **File patterns** against the repo. If no files match any pattern →
finding is **Not Assessable**; record `reason: no matching files`; skip to 4d.

**4c. Reason**
Read the matched files. Apply the control's **Pass signals** and **Fail signals** from
`controls.md`, weighing them per the rules in [`finding-rules.md`](finding-rules.md) (load via
this context pointer).

Derive:
- `finding`: Pass / Fail / Not Assessable
- `confidence`: plain-English note explaining what was found or not found
- `risk_summary`: one-to-two sentence attacker-perspective statement (from controls.md risk context)
- `implementation_approach`: narrative of how the system implements (or fails to implement) the control, citing specific files and config constructs
- `evidence_artefacts`: bulleted list of relative file paths with a note on what each demonstrates
- `client_responsibility`: what application teams must do to maintain their side of this control
- `files_read`: map of `<relative path>` → SHA-256 of file content (used for cache check in 4a and stored in the fragment file)

**4d. Record finding**
Completion criterion: every control in the assigned family has a finding (Pass / Fail /
Not Assessable / cached) and a confidence note.

**4e. Write evidence card**
For each control with a finding (including cached, per 4a's no-rewrite rule), write/update
`security/evidence/<control-id>.md` using the template at [`evidence-card.md`](evidence-card.md)
(load via this context pointer). Populate all fields from the finding recorded in 4c/4d.
Completion: one `.md` file per control in the assigned family exists in `security/evidence/`.

*(End of per-control loop.)*

Write the family's results as JSON to a scratch input file
`security/.assessment-fragments/<family>.input.json`:
```json
{
  "family": "<family>",
  "controls": {
    "<control-id>": {
      "finding": "<Pass | Fail | Not Assessable>",
      "confidence": "<string>",
      "risk_summary": "<string>",
      "implementation_approach": "<string>",
      "evidence_artefacts": ["<relative path>", "..."],
      "client_responsibility": "<string>",
      "files_read": {"<relative path>": "<sha256>"},
      "cached": true
    }
  }
}
```
(Omit `"cached"` entirely for a control that was freshly assessed this run — only set it to
`true` for a cache hit per Step 4a.)

Then run:
```bash
python3 skills/itsg-33-assess/scripts/write-fragment.py <family> \
  security/.assessment-fragments/<family>.input.json \
  security/.assessment-fragments/<family>.json
```

If this exits non-zero, its stderr names exactly what is wrong (missing field, invalid finding
value, malformed JSON, invalid `files_read` hash). Fix the input file and re-run the script — up
to 2 attempts. If it still fails after 2 attempts, this counts as the "malformed output" case in
the failure handling below.

Completion: every control in the assigned family appears exactly once in
`security/.assessment-fragments/<family>.json`, and the script exited 0.

**Failure handling:** If a subagent errors, exhausts its 2 write-fragment.py
retry attempts without a clean exit, or produces a fragment missing/duplicating a control, the
orchestrator retries that one family's subagent once. If the
retry also fails, abort the entire run: report which family failed and why, leave
`security/assessment-state.yaml` and `security/evidence/` untouched, and leave
`security/.assessment-fragments/` in place for debugging. Do not proceed to Step 5.

### Step 5 — Merge state

Once all 9 fragments exist in `security/.assessment-fragments/`:

1. Run:
   ```bash
   python3 skills/itsg-33-assess/scripts/merge-state.py \
     security/.assessment-fragments \
     security/assessment-state.yaml \
     security/assessment-state.yaml \
     <profile>
   ```
   (`<profile>` is the profile from Step 1, e.g. `PBMM`.) This script is the sole writer of
   `security/assessment-state.yaml`, including the PBMM plausibility check (a synthetic
   `PLAUSIBILITY-WARNING` control appended when every SC and every IA control comes back Not
   Assessable) — nothing is hand-edited into this file afterward. For any control a fragment
   marks `"cached": true`, it
   uses the `finding`/`confidence`/`files_read` already stored in the pre-run
   `security/assessment-state.yaml` verbatim, discarding whatever the fragment wrote for those
   fields. For every other control, it takes `finding`/`confidence`/`files_read` directly from
   the fragment.

   If this exits non-zero, its stderr names exactly what is wrong: no fragment files found, a
   control present in more than one fragment, a control (cached or not) missing a required
   field, a control marked cached with no prior entry to carry forward, or a fragment/existing-
   state file that isn't valid JSON. Treat this as a "malformed output" case
   per Step 4's failure handling — if the cause clearly traces to one family's fragment, retry
   that family's subagent once and re-run this step; otherwise abort the entire run, report why,
   and leave `security/.assessment-fragments/` in place for debugging.

2. Confirm every control in `controls.md` appears in the merged `security/assessment-state.yaml`
   exactly once. (`merge-state.py` only guards against a control appearing in *more than one*
   fragment; a control missing from *every* fragment is not something the script can detect,
   since it doesn't know the full control catalogue — check this against `controls.md`
   directly.) A control missing from all fragments is treated as a subagent failure per Step 4's
   failure handling: retry that family once, then re-run this step.

3. Delete `security/.assessment-fragments/`.

Completion: `security/assessment-state.yaml` contains an entry for every control in
`controls.md`; the fragment directory no longer exists.

### Step 6 — Create gap issues

For each **Fail** finding, create a gap issue only if no open gap already exists for
that control.

**GitHub mode** (`tracker: github`):
```bash
bash skills/itsg-33-assess/scripts/gh-list-tagged-issues.sh itsg-33:gap
```
- Skip creation if a returned issue's title matches `[itsg-33:gap] <Control ID> — <Control Name>`.
- Otherwise, write the issue body (control ID, finding, confidence note, recommended action,
  link to evidence card) to a scratch file, then:
```bash
bash skills/itsg-33-assess/scripts/gh-create-issue.sh \
  "[itsg-33:gap] <Control ID> — <Control Name>" \
  "itsg-33:gap,<P1|P2|P3>" \
  <body-file>
```

**Azure DevOps mode** (`tracker: azure-devops`):
```bash
bash skills/itsg-33-assess/scripts/ado-list-tagged-items.sh "<ado_org>" "<ado_project>" itsg-33:gap
```
- Skip creation if a returned item's title matches `[itsg-33:gap] <Control ID> — <Control Name>`.
- Otherwise, write the description as simple HTML (`<p>`, `<ul>`, `<code>` — `System.Description`
  is a rich-text HTML field, not Markdown) with the same fields, then:
```bash
bash skills/itsg-33-assess/scripts/ado-create-work-item.sh \
  "<ado_org>" "<ado_project>" Issue \
  "[itsg-33:gap] <Control ID> — <Control Name>" \
  "itsg-33:gap; <P1|P2|P3>" \
  <description-file>
```

**Local mode** (`tracker: local`):
- Write `security/gaps/<control-id>.md` with the same fields.
- Skip if the file already exists.

If either script exits non-zero, its stderr names exactly what went wrong; report this to the
user rather than retrying silently.

Completion: every Fail finding has a gap issue, work item, or gap file; no duplicates created.

### Step 7 — Regenerate assessment report (Markdown)

Write/overwrite `security/assessment-report.md` following the structure at
[`report-template.md`](report-template.md) (load via this context pointer).

Completion: file written; POA&M includes one row per Fail finding; evidence cards index
links to every file in `security/evidence/`.

### Step 8 — Regenerate assessment report (HTML)

Write/overwrite `security/assessment-report.html` as a **self-contained** file (inline CSS,
no external resources), using the same structure as [`report-template.md`](report-template.md).
Include:

- Summary dashboard as stat tiles (Pass count in green, Fail in red, Not Assessable in grey)
- Control family breakdown as a simple table
- Top 3 gaps highlighted
- POA&M table with sortable columns (use plain `<table>` with `<th>` — no JS required)
- Evidence cards index as a linked list (links to the `.md` files)

Completion: `security/assessment-report.html` exists; opening it in a browser renders
correctly with no external requests.
