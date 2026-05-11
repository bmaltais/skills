# ESLZ/__RESOURCE_TYPE__.tfvars
#
# Substitution tokens (replace before committing):
#   __RESOURCE_TYPE__  — snake_case resource name, e.g. linux_virtual_machine
#
# Rules:
#   - Existing entries: preserve verbatim, no reformatting
#   - New arguments: add below existing entries, commented out with description
#   - Every new argument the module exposes MUST have at least one commented example

__RESOURCE_TYPE__ = {
  example = {
    # ── Required ──────────────────────────────────────────────────────────────
    resource_group = "Project"

    # ── Common optional ───────────────────────────────────────────────────────
    # location = "canadacentral"

    # ── New arguments (add one commented block per new module input) ──────────
    # new_feature = {
    #   key = "value"  # description of what this controls
    # }
  }
}
