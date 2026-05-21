---
name: artyfacts
description: Manage your Artyfacts workspace — list, create, update, and search artifacts and sections via artyfacts-pp-cli. Invoke with /artyfacts <what you want to do>.
version: 2.0.0
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

# /artyfacts

Work with your Artyfacts workspace using `artyfacts-pp-cli`.

```
/artyfacts                                  # workspace overview
/artyfacts list my recent specs
/artyfacts create a feature spec for payments
/artyfacts search authentication
/artyfacts sync
/artyfacts show me stale artifacts
```

## Step 1 — always check auth first

```bash
artyfacts-pp-cli auth status
```

If not authenticated:
```bash
artyfacts-pp-cli auth login
```

## Step 2 — map intent to command

| User says | Command group |
|-----------|---------------|
| list / browse / show / find | `artifacts list`, `artifacts tree` |
| search / look for | `search-local` (or `artifacts list --search`) |
| create / write / make | `workflow create-with-sections` or `artifacts create` + `sections create` |
| update / change / rename / move / archive | `artifacts update`, `sections update` |
| delete / remove a section | `sections delete` |
| delete an artifact | no CLI command — use `curl -X DELETE $BASE_URL/artifacts/<id>` with the Bearer token |
| bulk archive / promote / transition | `artifacts bulk-status` — **status-only PATCH is not supported by the API**; see Known Limitations |
| sync / refresh / pull | `sync` |
| stats / insights / who wrote what | `artifacts stats` |
| stale / out of date | `artifacts stale` |
| org settings / conventions | `org context` |
| export / backup | `export` |
| import / restore | `import` |
| log in / get key / check auth | `auth login`, `auth status` |

**Valid artifact types:** `doc`, `spec`, `research`, `report`, `experiment`, `phase`, `runbook`, `folder`. Do not use `document` — it is rejected by the API.

**Default output flag:** use `--json` whenever you need to parse or display structured data. Use `--agent` for non-interactive multi-step flows.

**No arguments:** run `artifacts list --json`, `artifacts stats --json`, and `org context --json` to produce a workspace overview.

## Reference files

Load these when you need flag details, enumerations, or step-by-step examples:

- Read [references/commands.md](references/commands.md) — full flag reference for every command
- Read [references/global-flags.md](references/global-flags.md) — output, behavior, and delivery flags shared by all commands
- Read [references/workflows.md](references/workflows.md) — multi-step patterns: author content, bulk ops, backup, CI

## Known Limitations

- **Status updates:** `PATCH /artifacts/{id}` silently ignores `status` when sent with other fields, and rejects it outright when sent alone. `artifacts bulk-status` and `artifacts update --status` will both fail. There is no known working API endpoint for changing artifact status — treat status as read-only for now.
- **Artifact delete:** The CLI has no `artifacts delete` command. To delete, call `DELETE $BASE_URL/artifacts/<id>` directly with the Bearer token from `~/.config/artyfacts-pp-cli/config.toml`.

## Presenting results

- **Lists:** render as a table (id, title, type, status, updated_at).
- **Single artifact:** show metadata block then each section heading + body.
- **Stats:** prose summary ("23 artifacts: 8 specs, 6 docs, 5 reports…").
- **Create/update:** confirm what changed and show the artifact ID.
- **Errors:** show the message and suggest the fix (usually auth, sync, or a missing flag).
- After any create, offer the next logical step (add sections, mark active, sync).
