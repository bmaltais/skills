# Triage guide

## Severity
| Severity | Typical evidence |
|---|---|
| High | Cloud account keys (Azure Storage, Log Analytics, Automation), Entra/Bot app client secrets, Cognitive/Search/API admin keys, private keys, SAS tokens, or **committed Terraform state** (it holds keys, passwords and directory data). Any of these at default HEAD of a public repo raise urgency. |
| Medium | Hard-coded VM/DB admin passwords in deployable configs, passwords reused across repos, read/telemetry API keys removed from HEAD but still in history, PII such as user lists from `azuread_users` state. |
| Low / informational | Upstream fork example values, chart defaults, local-dev `.env` defaults, documented placeholders. |

Report confidence separately from validity, for example "9/10 plausible key; validity untested". Never claim that a credential is live.

## Known false positives
- `index_key` in Terraform state is a `for_each`/`count` key, not a secret.
- Slack webhook `T00000000/B00000000/XXXXXXXX...` is a documented placeholder.
- All-zero GUIDs (`00000000-0000-0000-0000-000000000000`) for client, tenant or subscription IDs are placeholders.
- Values beginning `var.`, `local.`, `data.`, `module.`, `dependency.`, `get_env(`, `${`, `$(` are references.
- Key Vault secret *names* (e.g. `secret_name = "sql-admin-password"`) are not values.
- `.env` files that hold only tool version pins.

## Value shape hints (from `len`/chars in redacted output)
- 88 characters, base64 (`aA9#`, ends `==`): Azure Storage account key or Log Analytics shared key.
- 32 characters, uppercase hex (`A9`): Azure Cognitive Search admin/query key.
- 32 characters, lowercase hex (`a9`): Cognitive Services / APIM subscription key.
- 34 characters, mixed with symbols: Entra app client secret (legacy format); 40 characters with `~` is the new format.
- 36 characters, GUID: an ID, not a secret, unless the key is `client_secret` and the value is not all zeros.
- 40 characters, lowercase alphanumeric, key `apiKey`: Application Insights API key.

## Grouping
Collapse raw matches into 3-6 findings by root cause, such as "state files committed" or "app passwords in tfvars". Report each with:
- the repository and the main files
- the first commit and its date
- the distinct values by sid
- whether they are at HEAD, on other branch tips, or in history only
- the scanner count versus manual-only items
- a recommended action: rotate first, then investigate logs, then remove from history (this does not revoke the credential), then prevent recurrence with push protection and CI scanning.

## Coverage statement (always include)
Count the repos mirrored and scanned, the reachable versus patch-bearing commits, and the scan time. Also state the limitations: default rules and allowlists apply. Binary files, archives, unreachable objects, Actions logs, releases, wikis, issues, gists, packages and external forks are not covered. Credential validity was not tested.
