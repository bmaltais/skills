---
name: eslz-l2-module-installation
description: >-
  Install, wire, and validate a new Terraform CAF module or test resource into an ESLZ L2 blueprint.
  Use this whenever the user asks to add, deploy, wire, scaffold, or test a new module or resource in
  an ESLZ L2 folder, especially when they provide a GitHub module URL, a Terraform registry link, or ask
  for an L2 test resource. Trigger on phrases like "deploy an L2 resource", "add this module to L2",
  "wire this CAF module into ESLZ", "install this in L2", "create an L2 test resource", or "add this
  terraform module to the project blueprint". This skill is for integrating modules into an existing ESLZ
  L2 structure, not for writing a brand new standalone Terraform module from scratch.
categories: [software-development]
agents: [copilot]
license: MIT
metadata:
  source: custom
  scope: global
---

# ESLZ L2 Module Installation Workflow

Use this workflow to add a reusable Terraform module or test resource to an existing ESLZ L2 blueprint.
Prefer the smallest change set that matches the repo's current patterns.

## Goals

- Fit the new resource into the existing L2 module structure instead of creating one-off Terraform in the environment folder.
- Reuse upstream CAF modules where possible.
- Add only the supporting resources required for the target module to plan successfully.
- Validate with non-destructive commands only.

## Hard rules

- Never run `terraform apply`, `terragrunt apply`, `terraform destroy`, or `terragrunt destroy` unless the user explicitly asks and local policy allows it.
- Prefer `terragrunt init` and `terragrunt plan` for environment validation.
- Do not guess upstream versions. Check tags and pin to the latest stable release unless the repo already standardizes on another version.
- Fix compatibility issues at the source pin or wrapper layer, not by weakening the target environment.
- Preserve existing naming, variable, and Terragrunt patterns already used by the repo.
- If the target resource supports private endpoints and the upstream module exposes private endpoint configuration, default to private endpoint deployment and disable public network access unless the user explicitly asks for a public endpoint.
- In environments where Azure Policy creates private DNS records on private endpoint detection, do not configure Terraform-managed private DNS zone association for those private endpoints unless the user explicitly confirms that local DNS wiring is required.

## Step 1: Identify the target integration points

Inspect the current repo before editing.

Read these first when present:

- `modules/L2_blueprint_project/*.tf`
- `modules/L2_blueprint_project/variables.tf`
- `modules/L2_blueprint_project/locals.tf`
- `modules/L2_blueprint_project/L1-remote-base-state.tf`
- `<landing-zone>/<env>/L2_blueprint_project/terragrunt.hcl`
- `<landing-zone>/<env>/L2_blueprint_project/config/*.tfvars`

Look for these patterns:

- Active wrapper files like `containerGroups.tf`
- Dormant or legacy examples like files ending in `_`
- Existing variable naming style such as `containerGroup`, `pim_rbac`, `storageaccountsV2`
- L1 remote state outputs already available for reuse such as `resource_groups_all`, `subnets`, `private_dns_zone_ids`

## Step 2: Inspect the upstream module and its dependencies

When the user provides a GitHub module repo or URL:

1. Read the upstream README and examples.
2. Check upstream tags and pin the latest release.
3. Confirm whether the repo's provider versions are compatible with that release.
4. Identify prerequisite resources the module needs.

Common examples:

- Synapse needs an ADLS Gen2 filesystem.
- Private endpoint capable modules may need `subnets` and `private_dns_zone_ids`.
- Modules that generate or store secrets may depend on an existing Key Vault layout from L1.
- Synapse private-only deployments require checking upstream support for managed VNet and system-assigned identity before disabling public network access.

When private endpoints are supported, inspect the module's ESLZ example tfvars first and mirror that input shape instead of inventing a custom private endpoint structure.

If the upstream module is not sufficient by itself, add a thin local wrapper resource for the missing prerequisite instead of forking the upstream module.

## Step 3: Decide what files to add or update

In a typical L2 installation, update these layers:

1. `modules/L2_blueprint_project/*.tf`
2. Environment config files under `config/*.tfvars`
3. Environment README if the new resource needs operator guidance

Prefer this shape:

- One wrapper file per new capability in `modules/L2_blueprint_project/`
- One variable near the wrapper file if the repo already follows that pattern
- One or more focused tfvars files in the target environment

Do not put resource implementation directly in the environment folder unless the repo already uses that pattern.

## Step 4: Implement the wrapper cleanly

For a typical module wrapper in `modules/L2_blueprint_project/<feature>.tf`:

1. Declare a variable with a permissive shape if the repo already uses `type = any`.
2. Use `for_each` for multiple instances.
3. Pass through shared L2 values:
   - `env`
   - `group`
   - `project`
   - `location`
   - `tags`
   - `resource_groups` from L1 outputs
   - `subnets` where needed
   - `private_dns_zone_ids` where needed
4. Add `depends_on` only when a real graph dependency is not otherwise expressible.

Example wrapper shape:

```hcl
variable "example_feature" {
  description = "Example feature definitions keyed by user-defined suffix"
  type        = any
  default     = {}
}

module "example_feature" {
  source   = "github.com/example/module.git?ref=v1.2.3"
  for_each = var.example_feature

  userDefinedString = each.key
  env               = var.env
  group             = var.group
  project           = var.project
  location          = var.location
  resource_groups   = local.resource_groups_all
  tags              = var.tags
}
```

## Step 5: Add supporting local resources only when required

If the upstream module depends on a prerequisite not exposed by another existing wrapper, create the smallest local resource needed.

Examples:

- Add `azurerm_storage_data_lake_gen2_filesystem` when a Synapse workspace needs a filesystem but the upstream storage module only returns the storage account.
- Derive a local map output structure that matches the upstream module input contract instead of inventing a brand new shape.

Prefer transforming local outputs into the exact format the upstream module expects.

## Step 6: Create the environment tfvars

Add focused tfvars files under the target environment `config/` directory.

Rules:

- Keep one concern per file when practical.
- Use realistic but minimal values.
- Follow existing environment naming and resource group keys such as `Project`, `Management`, `Keyvault`.
- Add short comments only where the wrapper introduces a local convention beyond the upstream module.
- If the resource supports private endpoints, configure them in tfvars by default using the upstream ESLZ example structure and disable public access.
- Reuse the landing zone's established private endpoint subnet convention, often `PEP`, unless the repo clearly uses another subnet for private endpoints.
- If local private DNS zone wiring is not yet present, still configure the private endpoints first and note whether DNS is expected from policy, core DNS integration, or additional L1 work.
- If Azure Policy owns private DNS record creation in the target subscription, set the PE input so the module skips Terraform-managed DNS zone association. Prefer the module's explicit skip mechanism, such as `private_dns_zone_id = null`, when the upstream example or module implementation supports it.
- For Synapse, if `public_network_access_enabled = false`, also configure the upstream inputs required to satisfy the Azure API for private-only workspaces, specifically managed VNet enablement and a system-assigned managed identity when supported by the module.

For test resources, make the sample intentionally minimal but still plannable.

## Step 7: Update operator-facing notes

If the environment already has a README, update it with:

- Which tfvars files control the new resource
- Any prerequisite relationship between those files
- A reminder to run `terragrunt plan` first

Keep this short.

## Step 8: Validate safely

Run validation in this order:

1. `terraform fmt` on the touched module and environment directories
2. Editor or language-server error check if available
3. `terragrunt init -upgrade -no-color` in the target L2 environment
4. `terragrunt plan -no-color`

If the plan fails:

1. Read the exact error.
2. Determine whether the problem is:
   - upstream module version mismatch
   - provider compatibility mismatch
   - wrong input shape
   - missing prerequisite resource
   - bad local assumptions about L1 outputs
3. Fix the root cause and re-run validation.

## Known good heuristics

- If a CAF module uses old azurerm arguments, check for a newer tag before changing local code.
- If the repo already contains a dormant file ending in `_`, treat it as a reference, not an authoritative implementation.
- If the environment plan succeeds after `init -upgrade`, prefer pinning the validated tag explicitly in the wrapper.
- When wiring maps for upstream modules, match their example tfvars layout exactly unless the repo has a stronger local convention.
- For PE-capable resources in private-only subscriptions, create the private endpoint blocks as part of the initial installation rather than leaving them as a follow-up hardening step.
- For storage-backed services, include every required private subresource endpoint, not just the most obvious one. For example, ADLS-backed storage commonly needs both `blob` and `dfs`.
- For Synapse, follow the module's ESLZ example subresource naming exactly, such as `sql`, `sqlOnDemand`, and `dev`, and avoid renaming those values.
- If a plan or apply fails on a private-only Synapse workspace with validation errors about public network access, managed VNet, or identity, treat that as a configuration requirement to fix in tfvars rather than an Azure transient error.
- If a private storage or Synapse deployment fails on name resolution during creation of downstream resources, verify whether the environment expects policy-driven private DNS and whether the PE config is still trying to manage DNS links directly.

## Policy-managed PE DNS checklist

Use this checklist before the first full `terragrunt plan` when private endpoints are involved:

1. Confirm whether the subscription or management group uses Azure Policy to create private DNS records for private endpoints.
2. If policy owns DNS, ensure the module input skips Terraform-managed DNS zone association for each private endpoint.
3. Reuse the expected PE subnet, usually `PEP`, unless the landing zone clearly documents another subnet.
4. Check whether downstream resources will resolve through policy-created records only after PE creation, and account for that during validation of dependent resources.
5. Report DNS ownership clearly as one of: explicitly managed in Terraform, policy-driven, or pending additional L1 or platform wiring.

## Report back to the user with

Always summarize:

1. What files were added or changed
2. Which upstream module versions were pinned
3. Whether `terragrunt plan` passed
4. What resources the plan would create
5. Any security or network caveats in the sample configuration
6. Whether DNS zone linkage for the private endpoints is explicitly configured, policy-driven, or still pending
7. Whether any service-specific private-only prerequisites were required, such as Synapse managed VNet or system-assigned identity

## Example trigger cases

Example 1:
Input: `deploy an L2 test resource based on https://github.com/canada-ca-terraform-modules/terraform-azurerm-caf-synapse-workspace`
Output: Add a Synapse wrapper, add any missing ADLS prerequisite wiring, create environment tfvars, pin latest compatible releases, and validate with `terragrunt plan`.

Example 2:
Input: `add this CAF module to the P6 dev L2 blueprint`
Output: Inspect the current L2 module layout, install a new wrapper file using existing conventions, add config tfvars, and run a non-destructive plan.

Example 3:
Input: `wire this terraform module into ESLZ L2`
Output: Determine module prerequisites, integrate them into `modules/L2_blueprint_project`, and validate in the target environment folder.