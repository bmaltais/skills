# ESLZ Documentation Template

## Naming convention

`ESLZ/<variable_name>.tfvars`

## Template

```hcl
# ESLZ/managed_identities.tfvars
#
# Managed Identities — create User Assigned Managed Identities with optional
# role assignments at arbitrary scopes.
#
# Each key becomes part of the auto-generated name: ${prefix}-${key}-uami
# Override with `name` for a custom name.

managed_identities = {
  # Minimal — identity only, no roles
  devops = {}

  # Full-featured — custom name, specific RG, roles at different scopes
  app1 = {
    name           = "custom-app1-uami"
    resource_group = "Network"              # any key from var.resourceGroups
    tags           = { purpose = "workload" }
    roles = [
      { role = "Contributor" },             # defaults to subscription scope
      { role = "Storage Blob Data Reader", scope = "/subscriptions/.../resourceGroups/storage-rg" }
    ]
  }
}
```

## Rules

- Header comment explains the feature and when to use it.
- At least two examples: one minimal (fewest options) and one full-featured.
- Inline comments for every non-obvious field.
- Note which resource groups / scopes are valid.
- If `ESLZ/` does not exist, create the directory.
- Run `terraform fmt` on the new file to ensure canonical formatting.
