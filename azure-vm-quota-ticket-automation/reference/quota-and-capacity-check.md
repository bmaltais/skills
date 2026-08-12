# Live quota headroom and capacity-restriction check

`azqt` does not query live Azure quota or SKU-restriction state itself — this check uses the `az` CLI directly. Run it after Step 6 (`Confirm complete requests only`) and before presenting the pre-submission approval table, for every distinct subscription/region/quota_family combination in `confirmed_requests.json`.

## Current quota headroom

```text
az vm list-usage --location <region> --subscription <subscription_id> -o json
```

Find the entry whose `name.value` equals the target `quota_family`. `currentValue` is usage, `limit` is the quota ceiling; free quota is `limit - currentValue`.

## Capacity restriction ("high in demand" / portal troubleshoot message)

```text
az vm list-skus --location <region> --subscription <subscription_id> --resource-type virtualMachines -o json
```

If no SKU with the target `quota_family` appears in this location-scoped result, or an entry has a `restrictions` item with `reasonCode: NotAvailableForSubscription` and `type: Location` covering the region, the family is capacity-restricted for that subscription in that region — this is what the Azure portal surfaces as "vCPUs are high in demand in \<region\>... select troubleshoot." A sufficient numeric quota limit does not mean the SKU is actually deployable.

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
