# Quota-request extraction guidance

Use this guide to turn a `Quota_Request_Document` into candidate records. Read the **entire** file as UTF-8 text before extracting. This is a transcription task: retain supported facts, retain uncertainty, and never invent a quota, region, subscription, contact, or quota family.

## Stop before any ticket action

1. **Unreadable or empty document.** If the file is empty or cannot be read and decoded as UTF-8 text, report the specific reason, log an `extraction-error` event, and stop. Do not call `map-sku`, create `confirmed_requests.json`, call `submit-tickets`, or contact Azure.
2. **Zero candidates.** After successfully reading the document, if it contains neither a specific formal VM SKU nor an informal description containing both vCPU and memory, report that zero `Candidate_Quota_Request` objects were found, log the stop outcome, and stop before ticket submission.

`references/azure-support-email.txt` is the zero-candidate example. It is a case-closure notice that mentions generic “VM SKUs,” quota increases, subscriptions, and regions, but it does not request a particular SKU or vCPU-and-memory size. Generic category terms are not candidate occurrences.

## Candidate extraction

Create one `Candidate_Quota_Request` for each formal Azure VM SKU occurrence or each informal size occurrence with both a vCPU count and memory amount (for example, `2 vcpu 8gb ram` or `8vcpu 32gb`). Assign a unique candidate ID and record every surrounding fact the document establishes:

- `SubscriptionId`, `Region`, VM SKU name, informal size description, and `Environment_Label`;
- `Justification`, `CurrentQuota`, `RequestedQuota`, and `SeverityLevel`; and
- `ContactName`, `ContactEmail`, and `ContactPhone` after applying the signature rules below.

Leave unsupported facts missing. Do not borrow a subscription from a different section, infer a region from a workload name, derive requested quota or severity from prose, or map a VM size to a quota family during extraction. `azqt map-sku` performs the family lookup later.

When the document does not state `RequestedQuota` for a candidate with a known vCPU count (from its informal size or a resolved SKU), default it rather than asking a clarifying question. The 10-vCPU minimum is a floor on each *quota-family group* (every candidate sharing a subscription, region, and resolved quota family — the group `azqt submit-tickets` later turns into one ticket line item), not on each individual candidate: set every such candidate's `RequestedQuota` to its own known vCPU count, then, only if the group's candidates sum to less than 10, add the shortfall to one candidate in the group so the group's total reaches exactly 10. A group whose candidates already sum to 10 or more needs no adjustment. Only ask the clarifying question when no vCPU count is known for the candidate.

Set the initial completeness state as follows: `Complete` only when every Azure Support API-required field is present and unambiguous; `Incomplete` when any required field is absent; and `Ambiguous` when the document supports more than one value for a required field. Clarification and SKU mapping may later change that state.

## Occurrences are not general deduplication

Treat each written SKU-or-size occurrence as a separate candidate. Never merge, sum, or suppress equal-looking text merely because its values match. The sole same-occurrence exception is when two occurrences have **both** the same associated environment label **and** the same associated subscription ID. Sharing only one of those associations—or neither—still produces separate candidates.

Worked examples below illustrate the rules only — a bundled example file can drift out of sync with its description over time. Always extract from the literal text of the document you were actually given, never from what a worked example here claims that file contains.

### Worked example: `references/example-quota-info.txt`

| Section and surrounding association | Written size occurrences | Required handling |
| --- | --- | --- |
| Archibus `Prod` with subscription `64080835-75bb-4085-aa73-e802ad5f3a04` | `2 vcpu 8gb ram`; `8 vcpu 64gb ram` | Create one candidate for each occurrence, retaining Prod and that subscription. |
| Archibus `QA` with no subscription | `2 vcpu 8gb ram`; `8 vcpu 64gb ram` | Create one candidate for each occurrence. Keep QA, but leave subscription missing; do not borrow it from Prod or DEV. |
| Archibus `DEV` with subscription `27b10a82-5946-4e08-96bf-ecb447fe907d` | `2 vcpu 8gb ram`; `8 vcpu 64gb ram` | Create one candidate for each occurrence, retaining DEV and that subscription. |
| P2P `PROD` with no subscription | `2vcpu 8gb ram`; `2vcpu 8gb ram`; `8vcpu 32gb`; `4vcpu 16gb`; `8vcpu 32gb` | Create five candidates. Repeated `2/8` and `8/32` values remain separate because the missing subscription prevents the permitted same-occurrence association. |

The example does not establish a region, requested quota, severity, or clear per-candidate justification for those size lines. Preserve those fields as missing so they are clarified rather than guessed.

## Contact signature blocks and association

A `Contact_Signature_Block` is a contiguous closing identification block, normally after a sign-off, that identifies a person and contains an email address or phone number. It can include a title, organization, working hours, or adjacent closing details. A greeting recipient, subscription owner named in body text, or support-routing address in request prose is not a signature block by itself.

First identify **all** signature blocks, then associate contacts per candidate. The association applies even when other candidate fields are incomplete.

### No signature blocks

Set `ContactName`, `ContactEmail`, and `ContactPhone` to missing for every candidate. Do not use an opening greeting, subscription-owner reference, or non-signature address as a substitute.

### Exactly one signature block

Associate that block’s name, email, and phone with every candidate, regardless of where the occurrence appears. In `references/azure-support-email.txt`, the closing after `Regards,` distinguishes the support engineer’s signature from the opening `Hello Maxime/Graham` greeting and from the body’s subscription IDs. The file has no candidates, but a candidate in that document would use this one closing signature.

### More than one signature block

For each SKU-or-size occurrence, define its section as the contiguous text range bounded by the nearest preceding signature block (or document start) and the nearest following signature block (or document end). Associate only the contact from the signature block applicable to that bounded section:

- an occurrence before the first signature block uses that following block;
- an occurrence after the final signature block uses the final preceding block; and
- where a section is bounded by signature blocks on both sides, use the block the section unambiguously identifies as its contact. If the applicable block cannot be determined, leave all three contact fields missing rather than choosing arbitrarily.

In `references/example-quota-info.txt`, the Archibus and P2P size lines occur before the bilingual closing contact blocks. Their section ends at the first such closing block, so the later French closing must not overwrite their contact association. Preserve only the name, email, and phone actually extractable from the applicable block; if no personal name can be established, leave `ContactName` missing even when email and phone are present.

## Before handing candidates to the CLI

1. Confirm that the whole document was read and neither stop condition applies.
2. Confirm that every formal SKU and every informal vCPU-and-memory occurrence was considered.
3. Confirm that repeated values were retained unless both environment and subscription establish the limited same-occurrence case.
4. Confirm that every copied field is supported by nearby text and every unknown field remains missing.
5. Confirm that all signature blocks were found and the zero/one/many association rule was applied per candidate.
6. Assign unique IDs and `Complete`, `Incomplete`, or `Ambiguous` states, then log each candidate as `candidate-extracted`.

Only after this phase, send each candidate with a formal SKU or informal size to `azqt map-sku`. Never infer the compute quota family during extraction.
