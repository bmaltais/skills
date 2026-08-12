---
name: azure-vm-quota-ticket-automation
description: Extract Azure VM quota requests from free text, clarify missing details, and use the bundled azqt CLI to map, audit, submit, and report requests. Use when the user shares a document, email, or chat log containing Azure VM quota asks (SKUs, vCPU/memory sizes, subscription IDs) and wants Azure Support quota-increase tickets extracted, clarified, and filed.
---

# Azure VM quota ticket automation

Use the bundled CLI only in this form:

```text
uv run --project <skill_dir>/tools/azqt azqt <subcommand> ...
```

Replace `<skill_dir>` with this skill folder's absolute path. Before using a subcommand, consult `reference/azqt-cli-reference.md` for its exact flags, input files, stdout schema, and exit behavior; do not run `--help` mid-run. Keep the `run_id` returned in step 1 and provide it to every later CLI call.

Follow these nine steps in order.

1. **Start the run.** Call `azqt init-run --document <path>` first. Retain the returned `run_id` and `log_path`. If the command fails without its documented JSON result, report its stderr error and stop.

2. **Read or stop.** Read the complete document as UTF-8 text. Apply the stop conditions in `reference/extraction-guidance.md`. If it is empty or unreadable, report the specific reason, record an `extraction-error` event with `azqt log-event`, and stop without mapping, submission, or Azure contact. If a readable document contains zero candidate occurrences, report that zero candidates were found, record an `extraction-error` event with an explicit `zero candidates` reason, and stop before submission.

3. **Extract and audit candidates.** Follow `reference/extraction-guidance.md` exactly. Create candidates from VM SKU or vCPU-and-memory occurrences using its occurrence/no-deduplication rule, preserve only text-supported surrounding fields, set each initial completeness state, and apply its zero/one/many signature-block contact-association rules. Assign a unique candidate ID and log every candidate through `azqt log-event --type candidate-extracted`, including its ID, extracted fields, and completeness state.

4. **Map SKU or size deterministically.** Create `candidates.json` in the schema from `reference/azqt-cli-reference.md`, then call `azqt map-sku --run <run_id> --input <candidates.json path>`. Use each returned resolution. Never infer or guess a compute quota family yourself. Treat an `unmatched` resolution or a non-empty `ambiguous_candidates` list as an unresolved quota-family field; retain the returned candidates for clarification.

5. **Clarify in batches and audit updates.** Use `reference/clarifying-question-templates.md` after mapping. For every incomplete or ambiguous candidate, form one consolidated question set per clarification round containing every unresolved field across all candidates; each question identifies the candidate ID and field. Before accepting every answer, run `azqt validate --run <run_id> --field <field> --value <answer> --candidate-id <id>` and apply the template's stated handling for unsupported fields, recognized regions, contact names, and quota-family selections. Log every accepted field change through `azqt log-event --type clarification-answer-applied`, recording the candidate ID, field, previous value, and new value. Track rounds independently per candidate field, and ask follow-ups only for unresolved fields. After three total rounds, exclude that candidate and record `candidate-excluded` with the reason. If validation flags `refusal: true`, immediately exclude that candidate and log the refusal reason; do not ask further questions for it.

6. **Confirm complete requests only.** Promote a candidate to `Confirmed_Quota_Request` only when every required Azure Support API field, including its unambiguous quota family, is present and valid. Write only promoted candidates to `confirmed_requests.json`, following the verbatim schema in `reference/azqt-cli-reference.md`. Do not place incomplete, ambiguous, refused, or round-exhausted candidates in this file or submit them.

7. **Check live quota headroom and capacity restrictions before requesting.** `azqt` does not itself query live Azure state — follow `reference/quota-and-capacity-check.md` to check, for every distinct subscription/region/quota_family combination in `confirmed_requests.json`, its current quota usage/limit and whether the family is capacity-restricted (Azure's "high in demand... troubleshoot" case, which blocks deployment regardless of the numeric limit). Drop a line item only when it is not capacity-restricted and existing free quota already covers it, logging `candidate-excluded` with that reason. When a family is capacity-restricted, request at least current limit + 1 even if the natural computed ask is smaller — a request at or below the current limit will not trigger Azure's capacity review.

8. **Get explicit approval, then submit all confirmed requests.** Before calling `submit-tickets`, present the full contents of `confirmed_requests.json` to the user grouped by the ticket they will produce (subscription, its region/quota-family line items, requested quota, contact, and justification) and wait for explicit approval. Never call `submit-tickets` without first showing this output. Once approved, call `azqt submit-tickets --run <run_id> --input <confirmed_requests.json path>` once with all confirmed requests. The CLI—not the agent—groups requests into one Azure Support ticket per subscription (Azure Support tickets are always subscription-scoped), with each distinct region/quota-family combination for that subscription becoming its own line item on that same ticket, builds Azure payloads, authenticates, creates/polls tickets, retries failures, and audits each ticket. Interpret every item in the returned `results` array: record the group key (subscription and its line items), ticket number, and ticket status for `created`; record the group key and error for `failed`. A successful command exit does not itself mean every ticket was created. Requests for different subscriptions always produce separate tickets, since Azure does not support quota tickets that span subscriptions.

9. **Finish and report.** Call `azqt finish-run --run <run_id>` and use its persisted-audit-log summary as authoritative. Present the result in prose: each created ticket with its subscription, the region/quota-family line items it covers, ticket number, and status; each failed ticket with its subscription, line items, and reason; each excluded candidate with its determined subscription, region, SKU or size, and exclusion reason when available; and the `created`, `failed`, and `excluded` counts. A non-zero `finish-run` exit that still returns summary JSON means the run is incomplete or partially failed because it has failed tickets, excluded candidates, or a persisted early-stop reason; report that outcome rather than treating it as a command crash. If it emits no summary JSON, surface the stderr error rather than guessing a result.

If the user later asks to check, or close, an existing ticket by its `supportTicketId`, follow `reference/quota-and-capacity-check.md`'s "Checking or closing an existing ticket" section rather than `azqt`, which has no lookup-by-ticket-number or ticket-management commands.

Keep Service Principal credentials, client secrets, certificates, and access tokens out of document data, generated JSON files, CLI arguments, audit-event data, and user-facing output.
