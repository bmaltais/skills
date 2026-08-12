# Clarifying-question templates

Use this guide after extraction and `azqt map-sku`. Clarification is candidate- and field-specific: do not ask a user to re-read the document, do not ask one question at a time, and never submit a candidate until it is confirmed.

## Build one batch per clarification round

At the start of a round, inspect **every** candidate that is `Incomplete` or `Ambiguous`. Build one consolidated question set containing each unresolved field across all candidates, including an ambiguous or unmatched compute quota family. Every question must identify both the candidate ID and the field it concerns.

Do not emit another question set until the user has had a chance to answer the entire current batch. An answer may resolve several questions, but apply every answer only to its corresponding candidate and field. A field omitted from the response remains unresolved and still counts as having consumed that round.

### Required field questions

Use only the fields that are missing or ambiguous for the specific candidate:

- `SubscriptionId`: “For candidate `<id>` (`<SKU or informal size>`), what Azure subscription GUID should receive this quota request?”
- `Region`: “For candidate `<id>` (`<SKU or informal size>`), what recognized Azure region identifier should be used?”
- `RequestedQuota`: only ask when the candidate has no known vCPU count (see extraction guidance's per-quota-family-group 10-vCPU floor): “For candidate `<id>` (`<SKU or informal size>`), what positive integer new quota limit is requested?”
- `SeverityLevel`: “For candidate `<id>`, choose the severity: `minimal`, `moderate`, or `critical`.”
- `ContactName`: “For candidate `<id>`, what is the non-empty contact name for the support ticket?”
- `ContactEmail`: “For candidate `<id>`, what is the contact email address for the support ticket?”

A single first-round message can be compact and still be complete, for example:

> I need the following details before any tickets can be submitted. Please answer each labeled item: (1) candidate `c-archibus-prod-2-8`: Region, RequestedQuota, SeverityLevel; (2) candidate `c-archibus-qa-2-8`: SubscriptionId, Region, RequestedQuota, SeverityLevel; (3) candidate `c-p2p-8-32-a`: SubscriptionId, Region, RequestedQuota, SeverityLevel, ContactName, ContactEmail.

## Ambiguous quota-family template

Never choose a family from an informal-size ratio yourself. If `map-sku` returns `quota_family: null` with `ambiguous_candidates`, present exactly the returned alternatives and allow a specific formal SKU as an alternative answer. If the source document states an explicit SKU/family preference (e.g. "prefer AMD v6 skus"), mark the matching alternative as the recommended option in the question instead of presenting a bare list — the user still confirms it, but doesn't have to repeat information already in the document.

> Candidate `<id>` has the informal size `<vCPU> vCPU / <memory> GiB`, which maps ambiguously to: `<ambiguous_candidates from map-sku>`. Please either select one of those quota families or provide the intended formal Azure VM SKU name. Do not provide a family outside that list unless you are providing a SKU for a new deterministic lookup.

For an unmatched input, say which SKU or size was unmatched and request the intended formal SKU name; do not manufacture a candidate list.

## Validate and apply answers

For every submitted answer, invoke `azqt validate` first, including answers for fields whose normal format validation is unsupported. This ensures the CLI's refusal detector can immediately exclude a candidate for **any** requested field. Accept an answer from deterministic validation only when the field is supported and the result is valid. The source currently validates:

| Field | Accepted value |
| --- | --- |
| `ContactEmail` | Valid email-address syntax |
| `SubscriptionId` | UUID/GUID syntax |
| `RequestedQuota` | Positive integer |
| `SeverityLevel` | Exactly `minimal`, `moderate`, or `critical` |

`azqt validate` detects these explicit refusal phrases case-insensitively within a natural-language answer: `unknown`, `n/a`, `don't know`, `won't provide`, and `not available`.

The current CLI returns `unsupported field` for `Region`, `ContactName`, and `Compute_Quota_Family`; this is an implementation limitation, not proof that a user’s answer is invalid. For those fields, apply the requirement-level rule while preserving the answer: Region must be a recognized Azure region identifier; ContactName must be non-empty and reasonably bounded; and a quota family must be one of the returned candidates unless the user supplied a new SKU that is then resolved by `map-sku`. Do not represent unsupported validation as successful CLI validation.

For every accepted answer, update only the identified field and log a `clarification-answer-applied` event containing the candidate ID, field name, previous value, and new value.

## Round limit, follow-up, and refusal

Track clarification rounds separately for each unresolved **candidate field**:

1. The initial batched question set is round 1.
2. After answers are applied, revalidate. Only unresolved, invalid, or omitted fields appear in the next batch; resolved fields never reappear.
3. The next two follow-up batches are rounds 2 and 3. If a field remains unresolved after the third total round, stop asking about that field, exclude the associated candidate, and log `candidate-excluded` with the precise reason.
4. If `azqt validate` returns `"refusal": true`, exclude the associated candidate immediately. Do not wait for another round, and log the refusal reason.

An invalid ordinary answer is not a refusal. Keep its field unresolved, count the round, and include only that field in the next batch. A missing answer is handled the same way.

### Follow-up template

> The following items are still unresolved. This is clarification round `<2 or 3>` for each listed field. Please answer only these items: (1) candidate `<id>`, `<field>`: `<format or selection required>`; (2) candidate `<id>`, `<field>`: `<format or selection required>`.

### Exclusion template

> Candidate `<id>` will not be submitted because `<field>` remained unresolved after three clarification rounds / the requested value was explicitly declined. The candidate and reason have been recorded.

## Promote only complete candidates

When every Azure Support API-required field and the compute quota family are present and unambiguous, set the candidate to `Complete` and promote it to a `Confirmed_Quota_Request`. Every other candidate stays out of `confirmed_requests.json` and out of Azure submission. This applies equally to candidates with missing extraction fields, invalid clarification answers, unresolved SKU mapping, and explicit refusals.
