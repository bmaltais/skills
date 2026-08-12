# `azqt` CLI reference

This is the complete command and JSON contract for the **current bundled source** in `tools/azqt/src/azqt/cli.py`. All six documented subcommands are implemented; an agent must use this reference rather than run `--help` during a skill run.

## Universal invocation and result contract

Run every command from any working directory in this exact form:

```text
uv run --project <skill_dir>/tools/azqt azqt <subcommand> ...
```

Replace `<skill_dir>` with the absolute path to this skill folder. The only parser-provided flags not repeated in every command form are `-h` and `--help`; they print help and exit, but are not needed and must not be used mid-run. No command has a `--version` flag or any undocumented global option.

On a completed handler, stdout contains exactly one JSON object, serialized on one line. The command-specific objects and their fields are specified below. A handler error writes plain-text diagnostics to stderr, exits 1, and emits no success object. Parser errors (for example, a missing required flag or an invalid `int`/`float` value) likewise exit non-zero before an output object. A business outcome inside a valid JSON result is not necessarily a process failure: `submit-tickets` can exit 0 with failed groups, while `finish-run` deliberately exits 1 after printing its summary whenever its tally contains failed groups, excluded candidates, or a persisted early-stop reason.

A run ID is the 32-character lowercase hexadecimal value returned by `init-run`. Commands that resolve a log (`map-sku`, `log-event`, `submit-tickets`, and `finish-run`) require that run's audit-log file to exist in the current state directory; an invalid ID or unavailable log is a handler error. `validate` requires `--run` syntactically but does not inspect the ID or log.

## `init-run`

```text
uv run --project <skill_dir>/tools/azqt azqt init-run --document <path>
```

| Flag | Required | Meaning |
| --- | --- | --- |
| `--document <path>` | Yes | Path recorded as the quota-request document. Source does not read or validate the document at this step. |

On success, stdout is exactly one object with this schema:

```json
{"run_id":"<32 lowercase hexadecimal characters>","log_path":"<native path string>"}
```

It creates a JSONL audit log and appends a `run-start` event. The optional `AZQT_STATE_DIR` environment variable changes the state directory for the current implementation; otherwise the tool uses an OS temporary-directory location.

## `map-sku`

Choose exactly one input form:

```text
uv run --project <skill_dir>/tools/azqt azqt map-sku --run <run_id> [--candidate-id <id>] --sku "<formal SKU>"
uv run --project <skill_dir>/tools/azqt azqt map-sku --run <run_id> [--candidate-id <id>] --vcpu <integer> --memory-gib <number>
uv run --project <skill_dir>/tools/azqt azqt map-sku --run <run_id> --input <candidates.json path>
```

| Flag | Required | Meaning and constraint |
| --- | --- | --- |
| `--run <run_id>` | Yes | Existing run ID; one `sku-resolution` event is appended per result. |
| `--candidate-id <id>` | No | ID for a direct `--sku` or size invocation; defaults to `single`. |
| `--sku <text>` | One input form | Formal VM SKU; cannot be combined with `--vcpu` or `--memory-gib`. |
| `--vcpu <integer>` | Size input form | Must be supplied with `--memory-gib`. |
| `--memory-gib <number>` | Size input form | Must be supplied with `--vcpu`; parsed as a float. |
| `--input <path>` | Batch input form | JSON array path; cannot be combined with direct SKU or size flags. Each item's exact field names (`vm_sku_name`, `informal_size_description`) are in "Agent-authored JSON schemas from the design" below — do not guess a field name (`sku_name` and similar variants are not read).

SKU matching is case- and whitespace-insensitive. If both a batch item’s non-blank SKU and informal size are present, the SKU takes precedence. A direct `--sku` may be an empty/whitespace string, in which case the resolver reports an incomplete result rather than an argument error.

**Adding a new SKU to `skumapping/table.json`:** never derive its `quota_family` from the SKU name's own spelling pattern — verify it against a live subscription's actual catalog first (`GET .../providers/Microsoft.Compute/locations/<region>/usages` or `.../skus`, filtered to the target SKU). Family names are not always a simple transform of the SKU name: for example the AMD "as" D/E-series drops the "s" for v6 (`Standard_D2as_v6` → `standardDav6Family`) but keeps it for v7 (`Standard_D2as_v7` → `standardDasv7Family`). A plausible-looking guessed name can still create a ticket successfully (Azure doesn't validate `VMFamily` against the real catalog at creation time) while requesting a family that doesn't exist, silently defeating the request.

Successful stdout has this schema:

```json
{
  "resolutions": [
    {
      "candidate_id": "string",
      "quota_family": "string or null",
      "matched_input": "string or null",
      "ambiguous_candidates": ["string"],
      "unmatched": false
    }
  ]
}
```

A resolved item has a non-null `quota_family`, an empty `ambiguous_candidates` list, and `unmatched: false`. An ambiguous informal size has `quota_family: null`, a non-empty `ambiguous_candidates` list, and `unmatched: false`. An unmatched SKU or size has `quota_family: null`, an empty list, and `unmatched: true`. A record with neither usable input has `quota_family: null`, an empty list, and `unmatched: false`.

## `validate`

```text
uv run --project <skill_dir>/tools/azqt azqt validate --run <run_id> --field <field-name> --value "<value>" [--candidate-id <id>]
```

| Flag | Required | Meaning |
| --- | --- | --- |
| `--run <run_id>` | Yes syntactically | Required by the parser but not read or validated by the current validation handler. |
| `--field <field-name>` | Yes | One of the source-supported field names below. |
| `--value <value>` | Yes | Text value to validate. |
| `--candidate-id <id>` | No | Accepted by the parser but not used by the current validation handler. |

The source supports `ContactEmail`, `SubscriptionId`, `RequestedQuota`, and `SeverityLevel`. It accepts severity values only as lowercase `minimal`, `moderate`, or `critical`. It detects refusal phrases before ordinary validation: `unknown`, `n/a`, `don't know`, `won't provide`, and `not available`.

Normal output schemas are:

```json
{"valid":true,"reason":"valid"}
{"valid":false,"reason":"<validation failure or unsupported field>"}
{"valid":false,"reason":"matched refusal phrase '<phrase>'","refusal":true}
```

`Region`, `ContactName`, and `Compute_Quota_Family` are currently unsupported and yield `valid: false` with an `unsupported field` reason unless the value matches a refusal phrase.

## `log-event`

```text
uv run --project <skill_dir>/tools/azqt azqt log-event --run <run_id> --type <event-type> --data <json-object-or-@file>
```

| Flag | Required | Meaning |
| --- | --- | --- |
| `--run <run_id>` | Yes | Existing run ID. |
| `--type <event-type>` | Yes | Exactly one of `candidate-extracted`, `clarification-answer-applied`, `candidate-excluded`, or `extraction-error`. |
| `--data <json-object-or-@file>` | Yes | An inline JSON object, or `@<path>` to a UTF-8 file containing one JSON object. Arrays and scalar JSON values are rejected. |

On a valid event payload, stdout has this schema:

```json
{"ok":true,"write_failed":false}
```

`ok` is `false` and `write_failed` is `true` only when the append-only audit write fails after event parsing. Malformed JSON, a non-object payload, unsupported type, unreadable `@file`, or invalid run ID is a command failure with stderr output and exit 1, not a JSON result. Audit serialization redacts values under `client_secret`, `certificate`, and `access_token` keys.

## `submit-tickets`

```text
uv run --project <skill_dir>/tools/azqt azqt submit-tickets --run <run_id> --input <confirmed_requests.json path>
```

| Flag | Required | Meaning |
| --- | --- | --- |
| `--run <run_id>` | Yes | Run ID from `init-run`; used to find the audit log and to resolve cached Azure Support classifications. |
| `--input <path>` | Yes | UTF-8 JSON file containing the `confirmed_requests.json` array. |

**Authentication:** before it will contact Azure, `submit-tickets` requires one of two credential shapes in the process environment: a service principal (`AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and either `AZURE_CLIENT_SECRET` or `AZURE_CLIENT_CERTIFICATE`/`AZURE_CLIENT_CERTIFICATE_THUMBPRINT`), or `ARM_USE_CLI=true` with an already-logged-in `az` CLI session (a delegated user token — no app registration needed). Missing credentials fail fast with a plain-text configuration error before any group is submitted.

The command reads the request array and groups it into one Azure Support ticket per exact `subscription_id`, since Azure Support tickets are always scoped to a single subscription. Within a subscription's ticket, requests are further sub-grouped into line items by exact `quota_family` plus case-insensitive `region`; each line item becomes one `quotaChangeRequests` entry (with its own summed limit) on that subscription's ticket, so a single ticket can request quota across multiple regions and/or quota families for the same subscription. Group, sub-group, and member ordering, and each line item's first member's region spelling, are retained. The CLI—not the caller—owns grouping, Azure Support payload construction, authentication, submission, asynchronous-operation polling, retries, audit events, and per-ticket outcome reporting. An empty input array succeeds without contacting Azure and returns `{"results":[]}`.

For each non-empty run, the CLI obtains an Azure AD access token, resolves the Azure Support quota service and Compute VM Cores classification, maps each subscription's ticket, and submits every successfully mapped ticket. A mapping error or ticket-create/poll failure is isolated to that subscription's ticket; other tickets continue. A token-renewal failure marks all remaining submit-ready tickets as failed and stops further ticket creation.

On success, stdout is exactly one object with this schema:

```json
{
  "results": [
    {
      "group_key": {
        "subscription_id": "string",
        "line_items": [
          {"region": "string", "quota_family": "string"}
        ]
      },
      "status": "created or failed",
      "ticket_number": "string or null",
      "ticket_status": "string or null",
      "error": "string or null"
    }
  ]
}
```

Each result corresponds to one ticket (one subscription), and `group_key.line_items` lists every distinct region/quota_family combination folded into that ticket. A `created` result has `ticket_number` and `ticket_status` and has `error: null`; a `failed` result has `ticket_number: null`, `ticket_status: null`, and an error message. Per-ticket mapping, ticket, polling, retry, and mid-run token-renewal failures are returned as `failed` results, and the command still exits 0. Input read/JSON/shape errors, invalid group-key fields, initial Azure AD authentication failure, or Azure Support classification-resolution failure produce plain-text stderr and exit 1 before the results object is emitted.

Azure Support tickets cannot span multiple subscriptions—this is a real Azure Support API constraint, not a tool limitation—so requests for different subscriptions always produce separate tickets even in a single `submit-tickets` call.

**Troubleshooting a classification-resolution failure:** if `submit-tickets` exits 1 with an error that a service or problem-classification name was "not uniquely available," the tool's hardcoded display-name constant may no longer match Azure's live catalog (Azure periodically renames these). Do not guess a replacement string — query the same endpoints directly with the run's own access token (`GET providers/Microsoft.Support/services` and `.../problemClassifications`, matching this source's `api-version`) to see the current catalog before proposing a fix.

**A `failed` result whose error mentions a support plan** (for example "Your support plan type is Free... you need access to our high tier-support plans") is a real, per-subscription account limitation, not a payload or tool defect — the Support API requires at least a paid plan on that specific subscription. Retrying will not help; report it to the user as needing a support-plan upgrade (or manual submission through the Azure Portal) for that subscription, and move on to the other groups.

## `finish-run`

```text
uv run --project <skill_dir>/tools/azqt azqt finish-run --run <run_id>
```

| Flag | Required | Meaning in current source |
| --- | --- | --- |
| `--run <run_id>` | Yes | Run ID from `init-run`; it is validated and used to locate the existing audit log. |

`finish-run` reads and validates the persisted JSONL audit log only; it does not contact Azure or resubmit requests. On a readable, valid log, stdout is exactly one object with this schema:

```json
{
  "created": 0,
  "failed": 0,
  "excluded": 0,
  "groups_failed": [{"<failed-group event-data field>": "<value>"}],
  "candidates_excluded": [{"<candidate-excluded event-data field>": "<value>"}],
  "stopped_early": false,
  "stop_reasons": [{"<extraction-error event-data field>": "<value>"}]
}
```

`created` is the number of `support-ticket-received` events, not a count of distinct tickets by name. `excluded` is the number of `candidate-excluded` events, and `candidates_excluded` contains each such event's `data` object in audit-log order. `stopped_early` is true when an `extraction-error` event is present, with those event data objects in `stop_reasons`; it covers unreadable, empty, or zero-candidate stop paths. A ticket is initially failed by a `quota-request-group-excluded` event or a `submission-outcome` event whose `outcome` is `failure` or `timeout`. Ticket identity is the event data's `subscription_id` plus the order-independent set of `{region, quota_family}` pairs in its `line_items` list, when `subscription_id` is a string and every `line_items` entry has string `region` and `quota_family`; malformed identities are kept distinct per event. Any ticket with a matching `support-ticket-received` event is removed from the failed tally. `failed` is the count of remaining tickets, and `groups_failed` contains their retained failure event-data objects.

After calculating that summary, the command attempts to append one `run-end` event with only `created`, `failed`, and `excluded` in its data when no prior `run-end` event exists. A later `finish-run` invocation does not add another `run-end` event. This append is best-effort: a write failure is not included in stdout and does not change the computed summary or exit code.

The command exits 1 when `failed`, `excluded`, or `stopped_early` is nonzero/true; otherwise it exits 0. This expected non-zero result still includes the summary JSON. An invalid or missing run ID, missing or unreadable audit log, malformed JSONL, or an audit entry that is not an object with string `event_type` and object `data` is a handler failure: it writes a plain-text error to stderr, exits 1, and emits no summary JSON.

## Agent-authored JSON schemas from the design

The following schemas are reproduced verbatim from `design.md`. `candidates.json` is read by the implemented batch `map-sku` path, and `confirmed_requests.json` is read by the implemented `submit-tickets` path.

```jsonc
// candidates.json (agent-authored, passed to `azqt map-sku --input`)
[{
  "candidate_id": "c1",
  "vm_sku_name": null,
  "informal_size_description": {"vcpu": 8, "memory_gib": 64}
}]

// confirmed_requests.json (agent-authored, passed to `azqt submit-tickets --input`)
[{
  "candidate_id": "c1",
  "subscription_id": "64080835-75bb-4085-aa73-e802ad5f3a04",
  "region": "canadacentral",
  "quota_family": "standardDSv5Family",
  "requested_quota": 8,
  "justification": "Archibus Prod workload scale-out",
  "contact_name": "Maxime Seguin",
  "contact_email": "maxime.seguin@ssc-spc.gc.ca",
  "contact_phone": "613-327-9514",
  "country": "CAN",
  "preferred_time_zone": "Eastern Standard Time",
  "preferred_support_language": "en-us",
  "severity_level": "moderate"
}]
```

Azure's `ContactProfile` requires `firstName`, `lastName`, `country`, `preferredTimeZone`, and `preferredSupportLanguage` in addition to the contact email — none of these are optional. `contact_name` must contain both a first and last name (split on the first whitespace); `country` is the ISO 3166-1 alpha-3 code; `preferred_time_zone` is a Windows time zone name (e.g. `"Eastern Standard Time"`); `preferred_support_language` is a standard language-country code (e.g. `"en-us"`, `"fr-fr"`). Missing or single-word values fail with a `MappingError` before any group is submitted.
