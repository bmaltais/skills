# Workflows

Multi-step patterns for common operations.

---

## Author a new artifact with content

The fastest path when you have content ready to write.

**Step 1** — write the payload to a temp file:

```yaml
# /tmp/artyfacts-payload.yaml
title: "Feature Spec: User Authentication"
type: spec
summary: "Technical specification for the user auth system."
status: draft
sections:
  - id: overview
    heading: "Overview"
    type: document/markdown
    body: |
      This spec covers the user authentication system...

  - id: requirements
    heading: "Requirements"
    type: document/markdown
    body: |
      ## Functional Requirements
      - Users must be able to sign in with email + password
      ...

  - id: schema
    heading: "Data Schema"
    type: data/json
    body: |
      {
        "user": {
          "id": "uuid",
          "email": "string",
          "created_at": "timestamp"
        }
      }
```

**Step 2** — create it:

```bash
artyfacts-pp-cli workflow create-with-sections \
  --sections-file /tmp/artyfacts-payload.yaml \
  --json
```

The command sets `is_streaming=true` during writes and flips it to `false` on completion — no manual stream management needed.

---

## Add a section to an existing artifact

```bash
artyfacts-pp-cli sections create <artifact_id> \
  --id implementation \
  --heading "Implementation Notes" \
  --type document/markdown \
  --body "..." \
  --json
```

For long body content, write to a temp file and pipe it:

```bash
echo '{"id":"impl","heading":"Implementation","type":"document/markdown","body":"..."}' \
  | artyfacts-pp-cli sections create <artifact_id> --stdin --json
```

---

## Update a section's content

```bash
artyfacts-pp-cli sections update <artifact_id> <section_id> \
  --body "Updated content here." \
  --json
```

To signal live editing in the UI (optional):
```bash
artyfacts-pp-cli sections stream-start <artifact_id> <section_id>
artyfacts-pp-cli sections update <artifact_id> <section_id> --body "..."
artyfacts-pp-cli sections stream-end <artifact_id> <section_id>
```

---

## Find then update an artifact

```bash
# 1. Find candidates
artyfacts-pp-cli search-local "authentication" --json
# or
artyfacts-pp-cli artifacts list --type spec --json

# 2. Read the current state
artyfacts-pp-cli artifacts get <artifact_id> --json

# 3. Update metadata
artyfacts-pp-cli artifacts update <artifact_id> \
  --status active \
  --json

# 4. Update a section
artyfacts-pp-cli sections update <artifact_id> <section_id> \
  --body "New content." \
  --json
```

---

## Promote all drafts to active

Preview first:
```bash
artyfacts-pp-cli artifacts bulk-status \
  --status active \
  --filter-status draft \
  --dry-run
```

Apply:
```bash
artyfacts-pp-cli artifacts bulk-status \
  --status active \
  --filter-status draft \
  --yes
```

Scope to a type:
```bash
artyfacts-pp-cli artifacts bulk-status \
  --status active \
  --filter-status draft \
  --filter-type spec \
  --yes
```

---

## Archive superseded docs

```bash
artyfacts-pp-cli artifacts bulk-status \
  --status archived \
  --filter-status superseded \
  --filter-type doc \
  --dry-run

# Then without --dry-run when ready
```

---

## Sync then search

```bash
# Incremental sync (only changed artifacts)
artyfacts-pp-cli sync

# Full refresh when the store seems stale
artyfacts-pp-cli sync --full

# Then search offline — zero network calls
artyfacts-pp-cli search-local "payments" --limit 10 --json
```

---

## Workspace health check

```bash
artyfacts-pp-cli doctor
artyfacts-pp-cli auth status
artyfacts-pp-cli artifacts stale --json
artyfacts-pp-cli artifacts stats --json
```

---

## Export a full backup

```bash
# JSONL (recommended — streaming, no memory pressure)
artyfacts-pp-cli export artifacts --format jsonl --output ~/backup-artifacts.jsonl

# JSON array
artyfacts-pp-cli export artifacts --format json --output ~/backup-artifacts.json
```

---

## Import from a backup

```bash
# Dry-run first
artyfacts-pp-cli import artifacts --input ~/backup-artifacts.jsonl --dry-run

# Apply
artyfacts-pp-cli import artifacts --input ~/backup-artifacts.jsonl
```

---

## CI: generate and publish a report artifact

```bash
# 1. Generate your content and write the payload
cat > /tmp/report.yaml << 'EOF'
title: "Build Report — 2026-05-11"
type: report
summary: "Automated CI build report."
status: active
sections:
  - id: summary
    heading: "Summary"
    type: document/markdown
    body: |
      Build passed. 142 tests, 0 failures.
  - id: details
    heading: "Details"
    type: data/json
    body: '{"tests":142,"failures":0,"duration_s":47}'
EOF

# 2. Create it
artyfacts-pp-cli workflow create-with-sections \
  --sections-file /tmp/report.yaml \
  --agent \
  --json
```

---

## Save a profile for repeated use

```bash
# Save an agent-mode profile
artyfacts-pp-cli profile save ci-mode --agent --yes --no-input

# Use it
artyfacts-pp-cli artifacts list --profile ci-mode
```
