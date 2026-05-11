# tests/upgrade_compat.tftest.hcl
#
# Substitution tokens (replace before committing):
#   __RESOURCE_TYPE__  — snake_case resource name, e.g. linux_virtual_machine
#   __PROVIDER_NAME__  — provider name, e.g. azurerm, azuread
#   __PROVIDER_SOURCE__ — registry source, e.g. hashicorp/azurerm
#
# Purpose: verify that the current module variable interface is backward-compatible
# with the previous release. Add one `run` block per breaking-change scenario caught
# during upgrade (naming changes, removed args, restructured blocks).

mock_provider "__PROVIDER_NAME__" {
  source = "__PROVIDER_SOURCE__"
}

# ── Naming convention: verify auto-generated name follows expected formula ─────
run "naming_convention" {
  command = plan

  variables {
    env               = "Dev"
    userDefinedString = "test"
    __RESOURCE_TYPE__ = {
      instance1 = {
        resource_group = "Project"
        # minimal valid config — add required fields for this resource type
      }
    }
  }

  # Replace with the actual output name and expected value for this module
  # assert {
  #   condition     = module.__RESOURCE_TYPE__["instance1"].name == "DevXXX-test"
  #   error_message = "Name does not follow expected convention"
  # }
}

# ── Default values: plan succeeds with minimal config (no optional args) ───────
run "default_values" {
  command = plan

  variables {
    env               = "Dev"
    userDefinedString = "defaults"
    __RESOURCE_TYPE__ = {
      minimal = {
        resource_group = "Project"
        # add the minimum required fields for this resource type only
      }
    }
  }
}

# ── Upgrade compat: old tfvars format still produces a valid plan ──────────────
# Add one run block per argument that changed shape, was renamed, or became optional.
# run "legacy_arg_format_still_accepted" {
#   command = plan
#   variables {
#     env               = "Dev"
#     userDefinedString = "compat"
#     __RESOURCE_TYPE__ = {
#       old_format = {
#         resource_group = "Project"
#         old_arg        = "value"   # arg that was renamed or restructured
#       }
#     }
#   }
# }
