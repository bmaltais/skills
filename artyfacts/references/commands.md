# Command Reference

Full flag listing for every `artyfacts-pp-cli` command.
Global flags (--json, --agent, --select, etc.) apply to all commands — see global-flags.md.

---

## artifacts list

List artifacts, optionally filtered.

```bash
artyfacts-pp-cli artifacts list [flags]
```

| Flag | Type | Description |
|------|------|-------------|
| `--type` | string | Filter by type: `doc`, `spec`, `research`, `report`, `experiment`, `phase`, `runbook`, `folder` |
| `--parent-id` | string | Filter by parent folder ID |
| `--is-root` | bool | Only return root-level artifacts (no parent) |
| `--limit` | int | Max results (default 50) |
| `--search` | string | Full-text search across titles, summaries, and section bodies (live API) |

---

## artifacts get

Get a specific artifact with all its sections.

```bash
artyfacts-pp-cli artifacts get <artifact_id> [flags]
```

No command-specific flags. Returns artifact metadata + full sections array.

---

## artifacts create

Create a new artifact envelope. Use `workflow create-with-sections` when you also have content.

```bash
artyfacts-pp-cli artifacts create [flags]
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--title` | string | yes | Artifact title |
| `--type` | string | yes | `doc`, `spec`, `research`, `report`, `experiment`, `phase`, `runbook`, `folder` |
| `--summary` | string | yes | Brief description (max 500 chars) |
| `--status` | string | | Initial status: `draft`, `active`, `final`, `superseded`, `archived` |
| `--tags` | string | | Comma-separated tags |
| `--parent-id` | string | | Parent folder ID |
| `--stdin` | bool | | Read request body as JSON from stdin |

---

## artifacts update

Update artifact metadata. Only the flags you pass are changed.

```bash
artyfacts-pp-cli artifacts update <artifact_id> [flags]
```

| Flag | Type | Description |
|------|------|-------------|
| `--title` | string | New title |
| `--summary` | string | New summary |
| `--status` | string | `draft`, `active`, `final`, `superseded`, `archived` |
| `--tags` | string | New tags — replaces existing tags entirely |
| `--visibility` | string | `private`, `team`, `organization`, `public` |
| `--retention` | string | `ephemeral`, `7d`, `30d`, `90d`, `1y`, `permanent` |
| `--parent-id` | string | Move to a different parent folder |
| `--stdin` | bool | Read request body as JSON from stdin |

---

## artifacts stale

Compare local store timestamps against the live API. Shows artifacts updated by other agents or users since the last `sync`.

```bash
artyfacts-pp-cli artifacts stale [flags]
```

| Flag | Type | Description |
|------|------|-------------|
| `--db` | string | Custom SQLite database path |

Requires a prior `sync`. Use to find candidates for re-sync.

---

## artifacts stats

Aggregate the local store for workspace statistics. Requires a prior `sync`.

```bash
artyfacts-pp-cli artifacts stats [flags]
```

| Flag | Type | Description |
|------|------|-------------|
| `--by-agent` | bool | Section and artifact counts per `agent_name` |
| `--by-type` | bool | Artifact counts per type |
| `--by-status` | bool | Artifact counts per status |
| `--db` | string | Custom SQLite database path |

Omitting all `--by-*` flags returns a combined summary.

---

## artifacts tree

Render the folder hierarchy as an ASCII tree. Requires a prior `sync`.

```bash
artyfacts-pp-cli artifacts tree [folder-id] [flags]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--depth` | int | 5 | Maximum nesting depth |
| `--db` | string | | Custom SQLite database path |

Pass an optional `folder-id` to root the tree at a specific folder.

---

## artifacts bulk-status

Batch-transition artifact statuses. Updates both local store and live API.

```bash
artyfacts-pp-cli artifacts bulk-status [flags]
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--status` | string | yes | New status to set: `draft`, `active`, `final`, `superseded`, `archived` |
| `--filter-status` | string | | Only act on artifacts with this current status |
| `--filter-type` | string | | Only act on artifacts of this type |
| `--dry-run` | bool | | Preview changes without applying |
| `--db` | string | | Custom SQLite database path |

Always run with `--dry-run` first to preview scope.

---

## sections list

```bash
artyfacts-pp-cli sections list <artifact_id> [flags]
```

No command-specific flags. Returns sections ordered by position.

---

## sections get

```bash
artyfacts-pp-cli sections get <artifact_id> <section_id> [flags]
```

No command-specific flags.

---

## sections create

```bash
artyfacts-pp-cli sections create <artifact_id> [flags]
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--id` | string | yes | Section ID — lowercase slug (e.g. `overview`, `api-schema`) |
| `--heading` | string | yes | Section heading |
| `--type` | string | yes | Content type: `document/markdown`, `code/python`, `code/javascript`, `data/json`, `data/yaml`, `image/png` |
| `--body` | string | | Section content text |
| `--position` | int | | Display order (0-indexed) |
| `--agent-name` | string | | Author name shown in the UI |
| `--stdin` | bool | | Read request body as JSON from stdin |

---

## sections update

```bash
artyfacts-pp-cli sections update <artifact_id> <section_id> [flags]
```

| Flag | Type | Description |
|------|------|-------------|
| `--body` | string | New section content |
| `--heading` | string | New section heading |
| `--is-streaming` | bool | Signal edit-in-progress state (true = writing, false = done) |
| `--agent-name` | string | Author name |
| `--stdin` | bool | Read request body as JSON from stdin |

---

## sections stream-start / stream-end

Signal streaming state on a section (shows a live-edit indicator in the UI).

```bash
artyfacts-pp-cli sections stream-start <artifact_id> <section_id>
artyfacts-pp-cli sections stream-end   <artifact_id> <section_id>
```

No flags. `stream-start` sets `is_streaming=true`; `stream-end` sets it to `false`.
`workflow create-with-sections` handles these automatically.

---

## sections delete

```bash
artyfacts-pp-cli sections delete <artifact_id> <section_id> [flags]
```

No command-specific flags. Permanent — cannot be undone.

---

## sync

Pull all artifacts and sections into the local SQLite store.
Default path: `~/.local/share/artyfacts-pp-cli/store.db`

```bash
artyfacts-pp-cli sync [flags]
```

| Flag | Type | Description |
|------|------|-------------|
| `--full` | bool | Force complete refresh (ignore incremental state) |
| `--type` | string | Only sync artifacts of this type |
| `--db` | string | Custom SQLite database path |

Incremental by default — only fetches artifacts updated since last sync.

---

## search-local

Full-text search across artifact titles, summaries, and section bodies using SQLite FTS5. Zero network calls.

```bash
artyfacts-pp-cli search-local "<query>" [flags]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--limit` | int | 20 | Max results |
| `--db` | string | | Custom SQLite database path |

Requires a prior `sync`. If results are empty, run `sync` first then retry.

---

## org / org context

Get organization details, agent conventions, and preferred workflows.

```bash
artyfacts-pp-cli org context [flags]
artyfacts-pp-cli org          # shortcut
```

No command-specific flags.

---

## workflow create-with-sections

Create an artifact and add all sections in one step.
Sets `is_streaming=true` during writes, then `false` on completion.

```bash
artyfacts-pp-cli workflow create-with-sections [flags]
```

| Flag | Type | Description |
|------|------|-------------|
| `--sections-file` | string | YAML or JSON file with artifact metadata and sections (preferred for multi-section content) |
| `--title` | string | Artifact title (inline, single-section only) |
| `--type` | string | Artifact type |
| `--summary` | string | Brief description |
| `--status` | string | Initial status |
| `--parent-id` | string | Parent folder ID |
| `--agent-name` | string | Default agent name for all sections |

**Sections file format (YAML):**
```yaml
title: "Artifact Title"
type: spec           # doc | spec | research | report | experiment | phase | runbook | folder
summary: "Brief description (max 500 chars)"
status: draft        # draft | active | final | superseded | archived
sections:
  - id: overview          # lowercase slug
    heading: "Overview"
    type: document/markdown
    body: |
      Content here.
  - id: schema
    heading: "Schema"
    type: data/json
    body: '{"key":"value"}'
  - id: implementation
    heading: "Implementation"
    type: code/python
    body: |
      def example():
          pass
```

Section content types: `document/markdown`, `code/python`, `code/javascript`, `data/json`, `data/yaml`, `image/png`

---

## export

Export API data to JSONL or JSON.

```bash
artyfacts-pp-cli export <resource> [id] [flags]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | string | `jsonl` | `jsonl` (streaming, one object per line) or `json` (array) |
| `--output`, `-o` | string | stdout | Output file path |
| `--limit` | int | 0 (unlimited) | Maximum records to export |
| `--no-cache` | bool | | Bypass response cache |

`<resource>` is the API resource name (e.g. `artifacts`). JSONL recommended for large datasets.

---

## import

Import records from a JSONL file by issuing POST requests for each record.

```bash
artyfacts-pp-cli import <resource> [flags]
```

| Flag | Type | Description |
|------|------|-------------|
| `--input`, `-i` | string | Input JSONL file path (use `-` for stdin) |
| `--dry-run` | bool | Preview without sending requests |
| `--batch-size` | int | Records per batch (default 1) |

Failed records are logged to stderr but do not stop the import.

---

## auth

| Command | Description |
|---------|-------------|
| `auth login` | Run device authorization flow — opens browser, polls for approval, saves key automatically |
| `auth login --no-browser` | Same flow but prints URL only (for headless/SSH) |
| `auth status` | Show whether credentials are configured and which source is active |
| `auth set-token <token>` | Save an API token manually |
| `auth logout` | Clear saved credentials (env vars are unaffected) |
| `auth get-key` | Explain how to obtain an API key |

---

## profile

Named sets of flags for reuse across invocations.

```bash
artyfacts-pp-cli profile save <name>     # capture current invocation's flags
artyfacts-pp-cli profile list            # list all saved profiles
artyfacts-pp-cli profile show <name>     # show a profile's values as JSON
artyfacts-pp-cli profile use <name>      # print what a profile will apply
artyfacts-pp-cli profile delete <name>   # remove a profile
```

Apply a saved profile: `--profile <name>` on any command. Explicit flags override profile values.

---

## Utility commands

| Command | Description |
|---------|-------------|
| `doctor` | Check CLI health: auth, connectivity, store status |
| `which <capability>` | Find the command that implements a described capability |
| `api` | Browse all API endpoints by interface name |
| `version` | Print version |
| `agent-context` | Emit structured JSON describing this CLI for agents |
| `feedback` | Record feedback about this CLI |
