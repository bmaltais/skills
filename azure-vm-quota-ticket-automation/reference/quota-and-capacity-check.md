# Live quota headroom and capacity-restriction check

`azqt` does not query live Azure quota or SKU-restriction state itself — this check uses the `az` CLI directly. Run it after Step 6 (`Confirm complete requests only`) and before presenting the pre-submission approval table, for every distinct subscription/region/quota_family combination in `confirmed_requests.json`. Both `az` calls below return data for *every* quota family in a subscription/region in one response, so run each one only once per distinct subscription/region pair — cache and reuse it across every quota_family that shares that pair instead of re-invoking `az` per family.

## Current quota headroom

```text
az vm list-usage --location <region> --subscription <subscription_id> -o json
```

Cache the result keyed by `(subscription_id, region)`. For each `quota_family` in that subscription/region, find the cached entry whose `name.value` equals it. `currentValue` is usage, `limit` is the quota ceiling; free quota is `limit - currentValue`.

## Capacity restriction ("high in demand" / portal troubleshoot message)

Run this once per distinct **subscription/region** pair, not once per subscription/region/quota_family — the SKU list for a region is identical no matter which family you're about to check, so a second family in the same subscription/region must reuse the first call's result instead of re-invoking `az`.

**Do not use `az vm list-skus`** — measured against a real ticket's subscription/region, it took over 60 seconds because it paginates the entire global SKU catalog (all resource types, all regions) client-side before filtering, regardless of `--location`/`--resource-type`/`--query` flags. Call the same ARM endpoint directly with `az rest`, which lets the API filter server-side by `location` and returns in a few seconds:

```text
az rest --method get --url "https://management.azure.com/subscriptions/<subscription_id>/providers/Microsoft.Compute/skus?api-version=2021-07-01&\$filter=location%20eq%20%27<region>%27" \
  --query "value[?resourceType=='virtualMachines'].{name:name, family:family, restrictions:restrictions}" -o json
```

(The `$filter` OData expression only reliably supports the single `location eq '<region>'` clause on this endpoint — adding `and resourceType eq '...'` to it silently breaks server-side filtering and returns the full unfiltered multi-region catalog instead, so keep the `resourceType` filter in the `--query` clause, not in `$filter`.)

Cache that trimmed result keyed by `(subscription_id, region)` for the rest of the run. Then, for each `quota_family` you need in that subscription/region, look it up in the cached result instead of re-querying: the family is capacity-restricted for that subscription/region if no entry's `family` equals it, or a matching entry has a `restrictions` item with `reasonCode: NotAvailableForSubscription` whose `type` is `Location` (blocks the whole region) **or** `Zone` (blocks the listed zones — in practice Azure reports true regional capacity restrictions as a `Zone`-type restriction covering every zone in the region rather than a `Location`-type entry, so treat either as restricted; do not require an exact `type: Location` match). This is what the Azure portal surfaces as "vCPUs are high in demand in \<region\>... select troubleshoot." A sufficient numeric quota limit does not mean the SKU is actually deployable.

## Applying the result

| Restricted? | Free quota covers the ask? | Action |
| --- | --- | --- |
| No | Yes | Drop the line item — exclude its candidate(s), no ticket needed. |
| No | No | Submit at the natural computed ask. |
| Yes | Yes or No | Submit at `max(natural_ask, current_limit + 1)` — a request at or below the current limit will not trigger Azure's capacity/troubleshoot review; only exceeding it does. |

Always present current limit, restriction status, and the final requested quota together in the approval table so the user can see why a number was bumped or a line item dropped.

## Checking or closing an existing ticket

A user may later ask to check, or close, a ticket by its human-readable `supportTicketId` (e.g. `2608070040004479`) rather than the tool's own `azqt-<hash>` resource name, and `azqt` has no lookup-by-ticket-number command. Resolve it once per session by listing tickets across the candidate subscriptions and matching `properties.supportTicketId`:

```text
az rest --method get --url "https://management.azure.com/subscriptions/<sub>/providers/Microsoft.Support/supportTickets?api-version=2020-04-01"
```

To judge whether an existing ticket's request is still needed, re-run the current-quota-headroom and capacity-restriction checks above for its `quotaChangeRequests` region/family; it's satisfied when the family is unrestricted and the live limit already meets or exceeds the requested amount.

Closing a satisfied ticket: the status-update API (`PATCH .../supportTickets/{name}?api-version=2020-04-01` with `{"status": "closed"}`) fails with `UpdateOperationDenied` whenever an engineer is actively assigned — expect this on nearly every real ticket, not as an error to debug. When denied, request closure instead by adding a communication:

```text
az rest --method put --url ".../supportTickets/{name}/communications/{communicationName}?api-version=2020-04-01" --body '{"properties": {"subject": "...", "body": "<reason, and whether follow-up is needed>", "sender": "<contact email>"}}'
```

This call returns 202 Accepted with no body and the new communication is not immediately visible on a follow-up list call — don't re-send on an empty-looking result; wait a moment and re-check before assuming failure.
