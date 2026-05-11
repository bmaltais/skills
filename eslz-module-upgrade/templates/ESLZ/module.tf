# ESLZ/__RESOURCE_TYPE__.tf
#
# This is the file callers copy into their L2 blueprint.
# It declares one variable block per module input and a module block that
# iterates over the map passed in by the caller.
#
# Substitution tokens (replace before committing):
#   __RESOURCE_TYPE__  — snake_case resource name, e.g. linux_virtual_machine
#   __ORG__            — GitHub org, e.g. canada-ca-terraform-modules
#   __NEXT_VERSION__   — next semver tag, e.g. v2.1.0
#
# How to determine __NEXT_VERSION__:
#   git tag --sort=-v:refname | head -1   → current latest tag
#   Increment: patch (+0.0.1) for bug-fix-only PRs, minor (+0.1.0) for new args

# ── Standard variables consumed by nearly every module ─────────────────────────

variable "__RESOURCE_TYPE__" {
  description = "Map of __RESOURCE_TYPE__ configuration objects, keyed by instance name"
  type        = any
  default     = {}
}

variable "resource_groups" {
  description = "Map of resource group objects (must include at least the RG the resource is deployed into)"
  type        = any
  default     = {}
}

variable "env" {
  description = "Environment prefix used in resource naming (e.g. Dev, Prod, Staging)"
  type        = string
  default     = null
}

variable "userDefinedString" {
  description = "User-defined suffix appended to the auto-generated resource name"
  type        = string
  default     = null
}

# ── Add / remove variable blocks to match the module's actual inputs ───────────
# Examples of other common inputs:
#
# variable "subnets" {
#   description = "Map of subnet objects used for NIC or private endpoint placement"
#   type        = any
#   default     = {}
# }
#
# variable "key_vault" {
#   description = "Key Vault object used to store generated secrets or retrieve CMK keys"
#   type        = any
#   default     = null
# }
#
# variable "law" {
#   description = "Log Analytics Workspace object for diagnostic settings"
#   type        = any
#   default     = null
# }

# ── Module block ───────────────────────────────────────────────────────────────

module "__RESOURCE_TYPE__" {
  source   = "github.com/__ORG__/terraform-azurerm-caf-__RESOURCE_TYPE__?ref=__NEXT_VERSION__"
  for_each = var.__RESOURCE_TYPE__

  # Pass all module-level variables through
  resource_groups   = var.resource_groups
  env               = var.env
  userDefinedString = var.userDefinedString

  # Add any other module inputs here, matching the variables declared above

  # The per-instance config object — always last
  __RESOURCE_TYPE__ = each.value
}
