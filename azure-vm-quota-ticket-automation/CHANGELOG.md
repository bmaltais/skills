# azure-vm-quota-ticket-automation Optimization Log

## Session 2026-08-06 — Step 1

### Edits Applied
- [op: insert_after] `reference/extraction-guidance.md`: added a default-quota rule — when `RequestedQuota` is unstated but the candidate's vCPU count is known (informal size or resolved SKU), default to `max(vcpu_count, 10)` instead of leaving it for clarification. Reasoning: this session's run against `example-quota-info.txt` had to ask the identical `RequestedQuota` question for all 11 extracted candidates (none of which stated a quota), a large, avoidable clarification round. User-supplied rule (skipped Steps 2–5 per explicit instruction).
- [op: replace] `reference/clarifying-question-templates.md`: `RequestedQuota` question now scoped to "only ask when the candidate has no known vCPU count," pointing back to the extraction-guidance default rather than restating it. Reasoning: keep the default in a single source of truth.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none) — first entry for this skill.

### Meta Notes
- Skill is repo-local (`/home/bernard/github/tickets/.copilot/skills/`), not installed via skillpack — `skillpack sync` does not apply; changes are versioned directly in this repo.
- Convergence: n/a (first recorded session).

## Session 2026-08-07 — Step 2

### Edits Applied
- [op: replace] `SKILL.md` Step 7: added a hard approval gate — the agent must present the full `confirmed_requests.json` contents, grouped by the ticket each will produce, and get explicit user approval before ever calling `submit-tickets`. Reasoning: agent was about to call `submit-tickets` for 11 candidates across 4 tickets without first showing the user the exact payload for sign-off; user corrected this ("never submit a ticket without clearly producing an output of what you are about to ask for my approval").

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- Same session also surfaced a missed extraction (an entire `AAFC-CMG` section, including a subscription-less `Prod` subsection) — this points at a possible gap in the Step 3 extraction pass on documents with more than two workload sections, but no clear rule change is warranted yet from a single occurrence; watch for recurrence before editing `extraction-guidance.md`.

## Session 2026-08-07 — Step 3

### Edits Applied
- [op: replace] `reference/extraction-guidance.md`: fixed the `RequestedQuota` default rule — the 10-vCPU minimum is a floor on the *quota-family group total* (all candidates sharing subscription+region+quota_family, i.e. one ticket line item), not on each individual candidate. Each candidate defaults to its own known vCPU count; only the shortfall (if the group sums to under 10) gets added to one candidate so the group total reaches 10.
- [op: replace] `reference/clarifying-question-templates.md`: updated the `RequestedQuota` cross-reference to point at the corrected per-group floor instead of the removed per-candidate `max(vcpu_count, 10)` formula.

### Reasoning
- The original per-candidate `max(vcpu_count, 10)` wording was fine for groups with exactly one candidate (e.g. Archibus, where each subscription/quota-family combination had only one VM) but silently inflated any group with multiple candidates: P2P PROD's 5-VM DASv6 group summed to 50 instead of its actual 24 vCPU total, and AAFC-CMG's 2-VM DASv6 groups summed to 20 instead of 10. User caught this by asking "why 50 instead of 30... why 20 instead of 10" and then corrected the rule directly: "we can't request... less than 10 VCPU... it is just that the minimum is 10" — confirming the floor is per quota-family group, not per VM.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- Step 1's `max(vcpu_count, 10)` default (per-candidate) is the regression this step fixes.

### Meta Notes
- Confirmed via `PayloadMapper.build_payload` that only the *group* total (`total_requested_quota` per line item) reaches the actual Azure payload as `NewLimit`; how the total is split across candidates in `confirmed_requests.json` is bookkeeping only and has no effect on the submitted ticket.

## Session 2026-08-07 — Step 4

### Edits Applied
- [op: insert_after] reference/azqt-cli-reference.md: added an Authentication note under submit-tickets documenting both supported credential shapes (service-principal env vars, or ARM_USE_CLI=true with a delegated az CLI login) and that missing credentials fail fast. Reasoning: the reference doc had zero mention of auth requirements, forcing two separate full source-dives into auth.py this session (once for the original SP-only flow, once after the user added ARM_USE_CLI support) before submit-tickets could be run.
- [op: replace] reference/azqt-cli-reference.md: map-sku's --input row now cross-references the exact batch JSON field names (vm_sku_name, informal_size_description) instead of leaving them undocumented at the flag table. Reasoning: a guessed field name (sku_name) silently produced four all-null resolutions since the real schema is documented far below under a differently-named heading, requiring a second attempt after re-reading the file.
- [op: insert_after] reference/azqt-cli-reference.md: added a Troubleshooting note under submit-tickets describing the 'not uniquely available' classification-resolution failure class and the direct-API-query diagnostic technique (query the same Support endpoints with the run's own token) instead of guessing a replacement display name. Reasoning: submit-tickets failed this session on a stale hardcoded Azure Support classification display name; diagnosing it required inventing this technique from scratch, worth capturing for reuse.

### Deferred Edits (waiting for more signal)
- [P3] Extraction pass missing an entire workload section (AAFC-CMG) on a multi-section document — single occurrence so far (also flagged in Step 2's meta notes); still deferred pending a second occurrence before editing extraction-guidance.md's occurrence-scanning rule.

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- Reordered this CHANGELOG to chronological order (Step 1 -> 2 -> 3) to match append_changelog.py's append-at-end convention; previous entries had been manually inserted newest-first.
- This is the third documentation-gap edit found via direct source reading rather than the reference doc itself (auth requirements, batch-input field names, and now the classification-troubleshooting path) -- the reference doc may be due for a fuller pass checked against current tool source rather than relying on incremental per-session patches.

## Session 2026-08-07 — Step 5

### Edits Applied
- [op: code fix] tools/azqt/src/azqt/azure/ticket_client.py `_poll_operation`: when a poll response has no operation-state field (no top-level 'status', no 'properties.provisioningState'), try treating the payload as the final SupportTicketDetails resource itself before declaring failure. Reasoning: Azure sometimes completes the LRO by returning the ticket resource directly at the operation URL rather than a generic status wrapper; the tool mis-reported two real, successfully-created tickets (Archibus DEV, P2P PROD) as 'failed' with 'operation status poll did not include an operation status' across two separate submit-tickets calls this session, discovered only by manually GETting the ticket resource directly. Added tests test_202_poll_returning_the_final_ticket_resource_directly_succeeds and test_poll_response_with_neither_operation_state_nor_ticket_data_fails (117 total tests passing).
- [op: insert_after] reference/azqt-cli-reference.md map-sku section: added a rule that a new table.json SKU's quota_family must be verified against a live subscription's Microsoft.Compute resourceSkus/usages API, never guessed from the SKU name's spelling pattern. Reasoning: this session's table.json (added by the user in an earlier session) had standardDASv6Family/standardEASv6Family for the AMD v6 'as' SKUs, but Azure's real family names are standardDav6Family/standardEav6Family (the 's' is dropped for v6 but kept for v7's standardDasv7Family) -- the wrong names still let two real government-subscription tickets get created successfully with an incorrect VMFamily, since Azure doesn't validate that field against the real catalog at creation time.
- [op: insert_after] reference/azqt-cli-reference.md submit-tickets Troubleshooting: added a note that a failed result mentioning a support plan (e.g. 'Your support plan type is Free...') is a real per-subscription account limitation requiring a plan upgrade or manual Portal submission, not a payload/tool defect worth retrying or debugging further.

### Deferred Edits (waiting for more signal)
- [P3] Extraction pass missing an entire workload section (AAFC-CMG) on a multi-section document -- still only a single occurrence (last flagged in Step 2), no recurrence this session; remains deferred.

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- This is the second session in a row where the highest-value edit was found only by directly querying live Azure APIs rather than trusting documentation, table.json data, or the tool's own prior success -- worth remembering as a general debugging pattern for this skill: verify against the real API before trusting a plausible-looking static value.
- Convergence: the azqt-cli-reference.md Troubleshooting section is proving to be a sticking, cumulative pattern (2 notes added across 2 sessions, neither reverted) -- prefer continuing to grow it over adding new top-level sections. The failure classes keep shifting (extraction, then default-value math, then live-API data-correctness) rather than repeating, suggesting broad coverage is still being built out; keep the learning rate as-is rather than decreasing it yet.

## Session 2026-08-11 — Step 6

### Edits Applied
- [op: insert_after] SKILL.md: inserted a new Step 7 (renumbering the rest to nine total) requiring a live quota-headroom and SKU capacity-restriction check for every subscription/region/quota_family combination before the approval gate, plus a new reference/quota-and-capacity-check.md documenting the exact `az vm list-usage` / `az vm list-skus` commands and the drop-vs-bump decision table. Reasoning: this session had to be told twice, mid-run, to (1) check whether existing quota already covered the ask and (2) check whether a family was capacity-restricted in the target region (Azure's 'high in demand... troubleshoot' case) -- neither check existed anywhere in the skill, forcing two full ad-hoc detours (six `az vm list-usage` calls, then `az vm list-skus` plus two web-doc fetches) that a documented step would have made routine.
- [op: insert_after] SKILL.md new Step 7: encoded the user-supplied business rule that a capacity-restricted family must be requested at current-limit+1 (not just the natural computed ask), since a request at or below the existing limit will not trigger Azure's capacity review even though the family is undeployable. Reasoning: user explicitly corrected the agent's prior recommendation ('I recommend not submitting any tickets... already covered') with this rule after the restriction check surfaced the conflict between 'quota looks sufficient' and 'SKU is actually blocked'.
- [op: insert_after] reference/extraction-guidance.md: added a one-line caveat that worked examples illustrate the rules only and may drift out of sync with the bundled example file they describe -- always extract from the literal text of the actual document, never from a worked-example table's claims. Reasoning: this session's `example-quota-info.txt` worked-example table incorrectly claimed the QA subsection had no subscription, that region was unestablished, and that multiple bilingual signature blocks existed -- all three contradicted the actual current file content and required independent re-verification.
- [op: replace] reference/clarifying-question-templates.md: the ambiguous quota-family template now instructs surfacing a document-stated SKU/family preference (e.g. 'prefer AMD v6 skus') as the recommended option in the disambiguation question, instead of a bare alternatives list. Reasoning: this session found and applied that pattern ad hoc for a real document that stated exactly such a preference, and the user confirmed both recommended picks in one round -- worth encoding as reusable technique.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- Discovered this session: a separate, more advanced copy of this same skill+tool bundle already exists at /home/bernard/github/tickets/.copilot/skills/azure-vm-quota-ticket-automation (repo-local, per the 2026-08-06 meta note not managed by skillpack for this skill) whose tools/azqt already implements this exact quota-headroom check natively in the CLI (azure/quota_usage.py, a 'skipped' submit-tickets status) -- but the installed copy actually used this session has none of that code. The two copies have diverged: the installed SKILL.md/tool lacks a capability the repo-local one already has. This session's fix is agent-side (raw `az` calls) since porting the repo-local CLI feature into the installed tool is a larger, separate engineering task -- flagged here for a future dedicated session rather than attempted under the learning-rate cap.
- Convergence: five sessions in, failure classes keep shifting across categories (extraction correctness, requested-quota math, live-API data accuracy, auth/troubleshooting docs, and now pre-submission quota/capacity checks) rather than repeating within one category -- broad coverage is still being built out, keep the learning rate as-is.

## Session 2026-08-12 — Step 7

### Edits Applied
- [op: insert_after] reference/quota-and-capacity-check.md: added a 'Checking or closing an existing ticket' section covering (1) resolving a human-readable supportTicketId to its azqt-<hash> resource name by listing supportTickets across candidate subscriptions since azqt has no lookup-by-number command, (2) reusing the existing quota/restriction checks to judge whether an existing ticket's request is still needed, and (3) the closure procedure: PATCH status=closed first, but expect UpdateOperationDenied whenever an engineer is assigned (routine, not a bug), then request closure via a Communications API PUT instead, noting it returns 202 with no body and is not immediately visible on a follow-up list call. Reasoning: this session hit the identical UpdateOperationDenied -> communications-based closure sequence 4 times in a row across 4 different tickets, and the async-no-body gotcha caused one accidental duplicate communication send when a too-fast verification read came back empty.
- [op: insert_after] SKILL.md: added a one-line pointer after Step 9 directing an out-of-run request to check/close an existing ticket by supportTicketId to the new quota-and-capacity-check.md section, since azqt itself has no ticket-lookup or ticket-management commands. Reasoning: this whole post-submission lifecycle (check status, decide if still needed, request closure) is a distinct, recurring request pattern not covered anywhere in the original 9-step extraction-to-submission flow.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- (none)

### Meta Notes
- This is the first session to exercise post-submission ticket lifecycle (checking/closing existing tickets) rather than the extraction-to-submission flow -- a new capability area, not a fix to the existing 9 steps.
- Convergence: 7 sessions in. Failure classes have now covered extraction correctness, requested-quota math, live-API data accuracy, auth/troubleshooting docs, pre-submission quota/capacity checks, and now post-submission ticket lifecycle -- each session keeps finding a genuinely new category rather than repeating a prior one, so the skill is still broadening coverage rather than converging; keep the learning rate as-is.
