---
agents: null
categories:
    - software-development
description: Practical, provider-agnostic guide to naming Terraform resources, local blocks, and modules at scale. Use when designing new modules, reviewing naming consistency, establishing team naming standards, or asking "what should I name this resource?".
license: MIT - copilot - claude
metadata:
    github-path: terraform-naming-conventions
    github-ref: refs/tags/v1.0.0
    github-repo: https://github.com/bmaltais/skills
    github-tree-sha: 400cf93acccc059b6580bee8b81e4f0368e3aa7f
    scope: global
    source: custom
name: terraform-naming-conventions
tags:
    - terraform
    - naming
    - conventions
    - iac
version: 1.0.0
---
# Terraform Resource Naming Conventions

A practical, provider-agnostic guide to naming Terraform resources and local blocks at scale.

## When to Use This Skill

Use this guidance when you:
- Design new Terraform modules or configurations
- Review naming consistency across resources
- Establish naming standards for a team or platform
- Refactor resource names and need a decision framework
- Ask: "What should I name this resource?" or "What's the best practice for naming?"

## Core Principle

**Separate Terraform identifiers from real resource names.**

Terraform needs TWO distinct naming schemes:

1. **Terraform block names** (internal, code references) — simple, stable, semantic
2. **Actual cloud resource names** (visible to ops, billing, monitoring) — unique, contextual, predictable

---

## 1. Terraform Block Names (Internal References)

The name in the resource declaration:

```hcl
resource "azurerm_storage_account" "this" {}
resource "aws_vpc" "main" {}
resource "google_compute_instance" "primary" {}
```

### Best Practices

✅ **Use simple, stable names:**
- `this` (default/primary resource)
- `main` (primary instance)
- `default` (standard configuration)
- `primary` (first in a set)

✅ **Optimize for code readability**, not uniqueness

✅ **Use semantic meaning** — convey intent, not environment or region

❌ **Never encode:**
- Environment (prod, dev, test)
- Region (eus, weu, cus)
- Instance numbers
- Workload names

### Why This Matters

- These names appear in **every reference** throughout your code
- Renaming them causes **Terraform state churn** and requires migrations
- They are **not visible** outside Terraform
- Simple names are **easy to refactor**

### Examples

✅ Good:
```hcl
resource "azurerm_virtual_network" "this" {}
resource "azurerm_subnet" "internal" {}
resource "aws_load_balancer" "main" {}
```

❌ Bad:
```hcl
resource "azurerm_virtual_network" "prod_eastus_vnet_01" {}
resource "azurerm_subnet" "app_subnet_prod" {}
resource "aws_load_balancer" "nlb-us-east-primary" {}
```

---

## 2. Actual Cloud Resource Names (Name Attributes)

The **real name** of the resource in the cloud provider:

```hcl
name = "${var.org}-${var.app}-${var.env}-${var.region}-${var.component}"
```

This is **where uniqueness, context, and environment live** — because cloud providers enforce it and operations need it to find resources.

### Structure: Proven Pattern

```
<org>-<system>-<env>-<region>-<component>-<instance>
```

Example:
```
ssc-ipam-prod-eus-vnet
ssc-ipam-prod-eus-subnet-app
ssc-ipam-prod-eus-nsg-app
```

### Ordering Rules

1. **Organization/platform first** — identifies the tenant/business unit
2. **System/application second** — identifies the workload
3. **Environment third** — prod, dev, test, uat
4. **Region fourth** — geographic location
5. **Component fifth** — resource type or function
6. **Instance number last** — only if multiple instances needed

**Key rule:** Pick one order and never deviate.

### Be Explicit and Predictable

✅ Good (someone can tell: *what*, *where*, *who owns it*):
```
ssc-ipam-prod-eus-sql-01
contoso-erp-dev-weu-app-gateway
acme-ai-uat-cus-storage
```

❌ Bad (ambiguous):
```
vnet01
network-prod
ipam-main
db-server
```

---

## 3. Abbreviations: Standards Over Freedom

Abbreviations must be **widely understood**, **documented**, and **used consistently**.

### Acceptable Abbreviations

**Environments:**
- `prod`, `dev`, `test`, `uat`, `staging`

**Regions (Azure example):**
- `eus` (East US)
- `weu` (West Europe)
- `cus` (Central US)

**Resource types:**
- `vnet` (virtual network)
- `subnet` (subnet)
- `nsg` (network security group)
- `sql` (SQL database)
- `stg` (storage)

### Create a Canonical List

If using abbreviations, maintain a **single source of truth**:

```hcl
# locals.tf
locals {
  regions = {
    "eastus"      = "eus"
    "westeurope"  = "weu"
    "centralus"   = "cus"
  }
  
  environments = {
    "production"  = "prod"
    "development" = "dev"
    "testing"     = "test"
  }
}
```

Enforce via documentation or linting.

---

## 4. Provider Constraints (Abstract Them Away)

Each cloud provider has naming rules:
- Length limits (Azure Storage: 24 chars max)
- Allowed characters (no underscores in some services)
- Global vs regional uniqueness
- Case sensitivity

**Solution: Compose names in a local block**

```hcl
locals {
  # Base name: consistent across all resources
  base_name = lower(join("-", [
    var.organization,
    var.application,
    var.environment,
    var.region
  ]))
  
  # Resource-specific names with length constraints
  storage_account_name = substr(
    replace("${local.base_name}stg", "-", ""),
    0, 24
  )
  
  vnet_name = "${local.base_name}-vnet"
}
```

**Use the locals everywhere**, not hardcoded names:

```hcl
resource "azurerm_storage_account" "this" {
  name = local.storage_account_name
}

resource "azurerm_virtual_network" "this" {
  name = local.vnet_name
}
```

Benefits:
- Single source of truth for naming
- Easy to change policy repo-wide
- Constraints are applied consistently
- Names are testable

---

## 5. Module Design: Never Hardcode Environment or Region

Modules must be **environment-agnostic** and **region-agnostic**.

✅ Good (reusable):
```hcl
# modules/network/variables.tf
variable "environment" {
  type = string
}

variable "region" {
  type = string
}

# modules/network/locals.tf
locals {
  base_name = "${var.organization}-${var.application}-${var.environment}-${var.region}"
}
```

❌ Bad (not reusable):
```hcl
# Hardcoded in module
name = "prod-eus-vnet"
```

Why:
- Breaks reusability across environments
- Encourages copy/paste modules
- Makes testing and staging harder
- Multiplies maintenance burden

---

## 6. Composition Over Conditionals

**Avoid conditional logic in names.**

❌ Don't do this:
```hcl
name = var.environment == "prod" ? "core-vnet" : "nonprod-vnet"
```

✅ Do this:
```hcl
name = "${local.base_name}-vnet"

# Then, if prod looks different in infrastructure, use a separate module or variable set
```

Why:
- Conditionals hide intent
- They cause drift between environments
- They're hard to debug across large estates
- Composition is self-documenting

---

## 7. Use Tags/Labels for Metadata — Not Names

**Names are for identity. Tags are for metadata.**

### Put in Tags:
- Cost center
- Owner/team
- Data classification
- Compliance scope
- Environment (as metadata, not primary identifier)

### Keep in Names:
- Identity (unique identifier in the system)
- Uniqueness (what makes this different)
- Operational clarity (can ops find and understand it?)

Example:

```hcl
resource "azurerm_virtual_network" "this" {
  name = "${local.base_name}-vnet"  # Identity and uniqueness
  
  tags = {
    environment     = var.environment          # Metadata
    cost_center     = var.cost_center          # Metadata
    owner           = var.owner_team           # Metadata
    data_class      = "internal"               # Metadata
  }
}
```

---

## 8. Enforce Naming Conventions

Best practices are only useful if enforced.

### Recommended Tools

- **`terraform validate`** — built-in validation
- **`terraform fmt`** — enforce code style
- **`tflint`** — custom linting rules
- **`terraform-compliance` or OPA/Sentinel** — policy as code
- **Pre-commit hooks** — catch violations before commit

### Example TFLint Rule

To enforce use of `local.base_name`:

```hcl
# .tflint.hcl
rule "custom_naming_convention" {
  enabled = true
}
```

Or use a checklist in your SKILL or code review process:

- [ ] Resource block name is simple and stable (`this`, `main`, etc.)
- [ ] Actual `name` attribute uses composed `local.base_name`
- [ ] No hardcoded environment or region in module
- [ ] Abbreviations match the canonical list
- [ ] Names follow the org → app → env → region → component order

---

## 9. Document Once, Use Everywhere

A good naming standard:
- Fits on **one page** (or one skill)
- Includes 3–5 concrete examples per pattern
- Lists all allowed abbreviations
- Explains *why*, not just *what*
- Is referenced in code reviews and onboarding

**If it takes 10+ pages, it won't be followed.**

---

## Quick Reference: The Gold Standard

If you only remember these rules:

| Aspect | Rule |
|--------|------|
| **Terraform block names** | Simple, stable, semantic (`this`, `main`) |
| **Actual resource names** | Composed, predictable, unique (`org-app-env-region-component`) |
| **Module design** | Never hardcode environment or region |
| **Provider constraints** | Abstract via locals, not inline |
| **Tags vs names** | Names for identity, tags for metadata |
| **Ordering** | Org → app → env → region → component |
| **Abbreviations** | Document and enforce a canonical list |
| **Enforcement** | Use tflint, terraform validate, or code review checklist |
| **Consistency** | Pick one pattern, never deviate |

---

## Government & Compliance Naming: When to Use SSC Standard

If your Azure workload is **Government of Canada / SSC-governed** or subject to **regulatory naming constraints** (HIPAA, compliance frameworks, etc.):

⚠️ **Override the generic pattern in this skill with the applicable compliance standard.**

### SSC (Shared Services Canada) Azure Naming

SSC-governed workloads use a **rigid structure with fixed-width fields**:

```
<dept(2)><env(1)><region(1)>[<deviceType(3)>]-<userDefined>[-<suffix>]
```

Example: `ScPcCNR-Core-MRZ-vnet`

- **No hyphens in the 4-char prefix** (unlike the generic pattern in this skill)
- **Fixed widths**: dept=2 chars, env=1, region=1, device=3
- **Resource-specific rigid patterns** for each Azure resource type

**For SSC workloads:**
- Reference: **ssc-azure-naming** skill (Government of Canada / SSC standard)
- Module scaffold: **terraform-caf-azurerm-module** skill (implements SSC compliance)
- Build the generic `base_name` in this skill using the SSC pattern instead

**For commercial/non-regulated Azure workloads:**
- The pattern in this skill applies directly

---

## Examples by Use Case

### Single-Environment Module

```hcl
locals {
  base_name = "${var.organization}-${var.application}-${var.environment}"
}

resource "azurerm_virtual_network" "this" {
  name = "${local.base_name}-vnet"
}

resource "azurerm_subnet" "app" {
  name = "${local.base_name}-subnet-app"
}
```

### Multi-Region Deployment

```hcl
locals {
  base_name = "${var.organization}-${var.application}-${var.environment}-${var.region}"
}

resource "aws_vpc" "this" {
  tags = {
    Name = "${local.base_name}-vpc"
  }
}

resource "aws_subnet" "primary" {
  tags = {
    Name = "${local.base_name}-subnet-primary"
  }
}
```

### Constrained Naming (Azure Storage)

```hcl
locals {
  # Remove non-alphanumeric, enforce length
  storage_name = substr(
    replace("${var.org}${var.app}${var.env}", "-", ""),
    0, 24
  )
}

resource "azurerm_storage_account" "this" {
  name = local.storage_name
}
```

---

## Related Skills

- **terraform-validation-workflow** — validate naming via tflint and terraform validate
- **terraform-docs-workflow** — document variable and naming conventions
- **terraform-versioning-advisor** — ensure provider constraints are consistent with naming patterns
- **ssc-azure-naming** — Use if your workload is **Government of Canada / SSC-governed** or subject to regulatory constraints; provides rigid patterns that override the generic pattern in this skill
- **terraform-caf-azurerm-module** — Scaffold Terraform modules for Azure with built-in **SSC naming compliance**; use for government workloads
