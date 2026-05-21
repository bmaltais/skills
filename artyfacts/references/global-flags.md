# Global Flags

Every `artyfacts-pp-cli` command accepts these flags. They don't need to be repeated in each command's docs.

---

## Output format

| Flag | Description |
|------|-------------|
| `--json` | Output as JSON. Use whenever you need to parse or display structured data. |
| `--plain` | Tab-separated plain text. Good for piping to other tools. |
| `--csv` | CSV output (table and array responses). |
| `--quiet` | Bare output — one value per line. Good for scripting. |
| `--compact` | Return only key fields: `id`, `name`, `status`, `timestamps`. Reduces token usage in agent flows. |
| `--select <fields>` | Comma-separated fields to include in output, e.g. `--select id,title,status`. Applied after the response is received. |
| `--human-friendly` | Enable colored output and rich formatting. Not useful for parsing. |
| `--no-color` | Disable colored output. |

**Recommended defaults:**
- Parsing/display → `--json`
- Agent pipelines → `--agent` (sets `--json --compact --no-input --no-color --yes`)
- Minimal IDs for a list → `--json --select id,title`

---

## Agent / automation

| Flag | Description |
|------|-------------|
| `--agent` | Set all agent-friendly defaults at once: `--json --compact --no-input --no-color --yes`. Use in non-interactive multi-step flows. |
| `--no-input` | Disable all interactive prompts. Required for CI. |
| `--yes` | Skip confirmation prompts. Use with destructive or write operations in scripts. |
| `--dry-run` | Show the request that would be sent without executing it. Safe for any command. |

---

## Data source

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--data-source` | `auto`, `live`, `local` | `auto` | `auto` = live API with local fallback; `live` = API only, no local cache; `local` = synced SQLite only, no network calls |

Use `--data-source local` when offline or for speed. Use `--data-source live` to bypass stale local data.

---

## Output delivery

| Flag | Description |
|------|-------------|
| `--deliver <sink>` | Route output to a sink instead of stdout. Values: `stdout` (default), `file:<path>`, `webhook:<url>` |

Examples:
```bash
# Write output to a file
artyfacts-pp-cli artifacts list --json --deliver file:/tmp/artifacts.json

# POST output to a webhook
artyfacts-pp-cli artifacts stats --json --deliver webhook:https://example.com/hook
```

---

## Request behavior

| Flag | Default | Description |
|------|---------|-------------|
| `--timeout` | `30s` | Request timeout. Increase for large syncs or slow connections: `--timeout 120s` |
| `--rate-limit` | `2` | Max requests per second (0 to disable). Lower if you hit API rate limits. |
| `--no-cache` | | Bypass the response cache for fresh data. |

---

## Config and profiles

| Flag | Description |
|------|-------------|
| `--config <path>` | Custom config file path. Default: `~/.config/artyfacts-pp-cli/config.toml` |
| `--profile <name>` | Apply a saved profile's flag values. Explicit flags override profile values. |

---

## Write-safety flags

| Flag | Description |
|------|-------------|
| `--idempotent` | Treat already-existing create results as a successful no-op (don't error on 409 conflicts). |
| `--ignore-missing` | Treat missing delete targets as a successful no-op (don't error on 404). |
