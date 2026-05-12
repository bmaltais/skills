---
agents:
    - copilot
categories:
    - software-development
description: |
    Generate, validate, and explain Azure resource names and tags following the SSC (Shared Services Canada) / GC Naming and Tagging Standard for Azure v2.1. Use this skill whenever the user wants to name an Azure resource, generate a compliant name, check if a name is valid, ask about naming rules or suffix codes, or get tagging guidance. Trigger on phrases like "name this resource", "what should I call my azure", "is this name valid", "generate a resource group name", "what suffix for", "what tags do I need", "check this azure name", "help me name", "what device type", "naming convention", "SSC naming standard". DO NOT trigger for general Azure questions unrelated to naming or tagging.
license: MIT
metadata:
    github-path: ssc-azure-naming
    github-ref: refs/tags/v1.0.0
    github-repo: https://github.com/bmaltais/skills
    github-tree-sha: ad7ff2ef6e42d8fa1211f67fd271a72c0ef3b707
    scope: global
    source: custom
name: ssc-azure-naming
---
# SSC Azure Naming & Tagging Assistant (v2.1)

You are a naming expert for the Shared Services Canada (SSC) / Government of Canada
Azure naming and tagging standard. Work through the steps below based on what the
user needs.

---

## STEP 1 — Detect intent

Determine what the user is asking for:

- **generate** — create a new compliant resource name
- **validate** — check whether an existing name is compliant
- **explain** — describe a rule, field, suffix, or device type code
- **tag** — provide tagging guidance for a resource

If the intent is unclear, ask one focused question to clarify.

---

## STEP 2 — Collect required inputs (generate / validate)

For **generate**, identify or ask for:

| Field | Size | Values |
|---|---|---|
| `<dept code>` | 2 chars | `Sc`=SSC; extend as needed per dept |
| `<environment>` | 1 char | `P`=Production, `D`=Development, `Q`=QA, `S`=Sandbox |
| `<csp region>` | 1 char | `C/c`=Azure Canada Central, `D/d`=Azure Canada East, `G/g`=AWS Ca-central-1, `K/k`=GCP Montreal, `Z/z`=Azure Stack SSC Central (Barrie), `Y/y`=Azure Stack SSC East (Montreal), `M/m`=GCP multi-region |
| `<device type>` | 3 chars | **Optional** as of v2.1 — see Device Type Table below |
| `<userDefined>` | variable | Mandatory free-form string; `-` or `_` allowed as subfield delimiter |
| Resource type | — | Required to select the correct pattern and suffix |

For **validate**, ask for the existing name and resource type if not provided.

---

## STEP 3 — Apply the naming structure

### Full naming structure

```
<dept(2)><env(1)><region(1)>[<deviceType(3)>]-<userDefined>[-<suffix>]
```

**Example:** `ScPcCNR-Core-MRZ-vnet`
→ SSC (`Sc`) + Production (`P`) + Azure Canada Central (`c`) + Cloud Network Resource (`CNR`) + user string `Core-MRZ` + suffix `vnet`

**Key structural rules:**
- The 4-char GC prefix (`<dept><env><region>`) has **no internal delimiter**
- Device type (3 chars) attaches **directly to the prefix** with no delimiter
- A **hyphen `-`** separates the prefix+deviceType from the user defined string
- The suffix is appended with a **hyphen `-`**
- **VMs have no suffix** — child objects inherit the VM name + new suffix
- **Entra ID objects use underscore `_`** as field delimiter, not hyphen

---

## STEP 4 — Resource-specific patterns

Use the table below to determine the correct pattern. `<prefix>` = `<dept><env><region>`.

### General / Governance Objects

| Resource Type | Pattern | Scope | Max Len | Notes |
|---|---|---|---|---|
| Management Group | `<prefix>-<owner>-<userDefined>` | Tenant | 90 | No suffix required; spaces allowed |
| Subscription | `<prefix>-<owner>-<userDefined>` | Tenant | 90 | No suffix; spaces allowed; use `m` for multi-region |
| Resource Group | `<prefix>-<owner>-<userDefined>-rg` | Subscription | 90 | Cannot be renamed after creation |

### Compute

| Resource Type | Pattern | Scope | Max Len | Notes |
|---|---|---|---|---|
| Virtual Machine (Windows) | `<prefix>[<devType>]-<userDefined>` | RG | **15** | No suffix; 15-char limit for NetBIOS/DNS |
| Virtual Machine (Linux) | `<prefix>[<devType>]-<userDefined>` | RG | 64 | No suffix |
| VM OS Disk | `<vm-name>-osdisk<#>` | RG | 80 | Child of VM; inherits VM name |
| VM Data Disk | `<vm-name>-datadisk<#>` | RG | 80 | Child of VM |
| Availability Set | `<vm-name>-[<userDefined>-]as` | RG | 80 | Drop instance `##` for clusters |
| Function App | `<prefix>[<devType>]-<userDefined>-fn` | Global | 60 | Alphanumeric and hyphen |
| Key Vault | `<prefix>[<devType>]-<userDefined>-kv` | Global | **3–24** | Alphanumeric and hyphen only |
| App Service | `<prefix>[<devType>]-<userDefined>-asv` | Global | 60 | |
| App Service Plan | `<prefix>[<devType>]-<userDefined>-asp` | RG | 80 | |

### Storage

> Storage objects require **globally unique lowercase alphanumeric** strings. No hyphens allowed in storage account names.

| Resource Type | Pattern | Scope | Max Len | Notes |
|---|---|---|---|---|
| Storage Account (data/disks) | `(tolower)<prefix><userDefined>[<random>]` | Global | **3–24** | Lowercase alnum only; no hyphens; use random suffix for uniqueness |
| Data Lake Store | `(tolower)<prefix><userDefined>` | Global | 3–24 | Same restrictions as storage account |
| Container (in storage) | `<stg-account-name>-<userDefined>` | Storage Acct | 3–63 | Lowercase; alphanumeric and hyphen |
| Queue | `<stg-account-name>-<userDefined>` | Storage Acct | 3–63 | Lowercase |
| Table | `<stg-account-name><userDefined>` | Storage Acct | 3–63 | Alphanumeric; no hyphen |
| File Share | `<stg-account-name>-<userDefined>` | Storage Acct | 3–63 | Lowercase |

### Networking

> Networking objects typically do **not** need DNS entries, so resource suffixes are mandatory.
> Use `CNR` (Cloud Network Resource) as the device type for network infrastructure.
> Child objects (NIC, PIP, etc.) inherit the parent object name with the suffix swapped.

| Resource Type | Pattern | Scope | Max Len | Notes |
|---|---|---|---|---|
| Virtual Network (VNet) | `<prefix>CNR-<userDefined>-vnet` | RG | 64 | No IP addresses in name |
| Subnet | `<vnet-name-no-suffix>-<userDefined>-snet` | VNet | 80 | Drop `-vnet` from parent; `GatewaySubnet` and `AzureFirewallSubnet` are reserved Azure names |
| Route Table | `<vnet-or-snet-name>-rt` | RG | 80 | Scope depends on assignment |
| Route | `<userDefined>-route` | RG | 80 | Defined by network team |
| Network Security Group | `<parent-name>-nsg` | RG | 80 | Parent is VM name or subnet name |
| NSG Rule | `<action>-<description>` | NSG | 80 | e.g., `Allow-RDP`, `Deny-InboundMRZ` |
| Network Interface (NIC) | `<parent-name>-nic<#>` | RG | 80 | Parent is VM/LB/FW name |
| Public IP Address | `<parent-name>-pip<#>` | RG | 80 | Exception to suffix rule; number appended |
| Azure Firewall | `<prefix>FWL-<userDefined>-azfw` | RG | 80 | |
| Azure Bastion | `<prefix>BST-<userDefined>-bstn` | RG | 80 | |
| VNet Gateway | `<vnet-name>-[<userDefined>-]vng` | RG | 80 | User string optional |
| Local Network Gateway | `<vnet-name>-[<userDefined>-]lng` | RG | 80 | |
| Connection | `<vnet-name>-[<userDefined>-]con` | VNet | 80 | |
| VNet Peering | `<source-vnet>-<dest-vnet>-gwp` | VNet | 80 | No user defined field |
| Load Balancer | `<prefix>ADC-<userDefined>-lb` | RG | 80 | |
| LB Frontend Interface | `<lb-name-no-suffix>-lbr<#>` | RG | 80 | Drop `-lb` from parent |
| LB Backend Pool | `<lb-name-no-suffix>-lbbp` | RG | 80 | |
| LB Health Probe | `<lb-name-no-suffix>-<userDefined>-lbhp` | RG | 80 | User string required |
| Application Gateway | `<prefix>[<devType>]-<userDefined>-agw` | RG | 80 | |
| Traffic Manager | `<prefix>-<userDefined>-tm` | RG | 63 | Alphanumeric and hyphen |
| Network Watcher | `<prefix>CNR-<userDefined>-nw` | RG | 80 | |

### Automation / Identity

| Resource Type | Pattern | Scope | Max Len | Notes |
|---|---|---|---|---|
| Service Principal / Run As | `<prefix>-<owner>-<userDefined>-spn` | Subscription | 50 | |
| Container Registry | `<prefix><devType>-<userDefined>-registry` | Global | 50 | Alphanumeric only (under review) |

### Microsoft Entra ID (Azure AD)

> Entra ID objects use **underscore `_`** as field delimiter (not hyphen).
> Use best-fit environment (`P`=prod for shared groups, primary region `c`=Canada Central).

| Resource Type | Pattern | Scope | Max Len | Notes |
|---|---|---|---|---|
| Azure Account | `<identifier>.<first>.<last>@tenant.onmicrosoft.com` | Tenant | — | identifier: Admin, Dev, Ops, Srv, Test, B2B |
| Azure AD Group | `<dept><env><region>_<GroupType>_<UserDefined>` | Tenant | 50 | Underscore delimiter; `GroupType` default is `APP` |
| IAM Group | `Subscription-<UserDefined>` | Tenant | 50 | For role assignment groups |
| App Registration | `SSC-SPC-<UserDefined>` | Tenant | 50 | Spaces allowed; bilingual dept acronym |
| Enterprise Application | `SSC-SPC-<UserDefined>` | Tenant | 50 | Spaces allowed |
| User Managed Identity | `<dept><env><region>_<userDefined>` | Tenant | 128 | Supports tags; follow IAM naming if possible |
| System Managed Identity | `<Azure Resource Name>` | — | — | Name matches parent resource automatically |

---

## STEP 5 — Device type lookup

The 3-character SACM device type is **optional** as of v2.1, but retained for VMs and for backward compatibility with BCA Terraform templates.

### Generic Cloud Device Types

| Code | Use for |
|---|---|
| `CNR` | Cloud Network Resource — VNets, NICs, NSGs, route tables, gateways |
| `CSA` | Cloud Storage Account |
| `CSV` | Cloud Secret Vault (Key Vault) |
| `CCR` | Cloud Container Registry |
| `CPS` | Cloud Platform Service (generic PaaS without a better match) |
| `CLD` | Generic Cloud Entity / Object |
| `FWL` | Firewall |
| `ADC` | Application Delivery Controller (Load Balancer, F5, etc.) |
| `BST` | Bastion Host |

### Server Device Types (SACM Functional)

First char `S` = Server. Second char = OS. Third char = function.

**Windows servers (second char `W`):**

| Code | Function |
|---|---|
| `SWA` | Domain Services (Active Directory, DNS, DHCP) |
| `SWB` | Database (Oracle, MS-SQL, etc.) |
| `SWC` | Web Server (Apache, IIS — HTTP/HTTPS only) |
| `SWD` | Application Server (WebLogic, WebSphere, SAP, PeopleSoft, etc.) |
| `SWE` | Management Server (vCenter, SCOM, SCCM, Puppet, etc.) |
| `SWF` | File and Print Server |
| `SWG` | Cluster |
| `SWH` | Messaging |
| `SWJ` | Jump Server |

**Linux servers (second char `L`):**

| Code | Function |
|---|---|
| `SLA` | Domain Services |
| `SLB` | Database |
| `SLC` | Web Server |

**Other servers:**

| Code | Use for |
|---|---|
| `SRV` | Generic server (no specific OS/function) |
| `SAx` | Appliance-based server (not OS-specific) |
| `SXx` | Hypervisor |

### Other Network Device Types

| Code | Use for |
|---|---|
| `NSD` | Network Sniffer Device |
| `NMP` | Network Monitor Probe |
| `TAP` | Network TAP |
| `AGR` | Network TAP Aggregator |
| `IDS` | Intrusion Detection System |
| `IPS` | Intrusion Prevention System |
| `RTR` | Router |
| `APT` | Access Point |
| `NTP` | Network Time Server |
| `TCS` | Terminal Console Server |
| `QFC` | Storage SAN Switch |
| `QSN` | Storage Disk Array |
| `VDI` | Server-based Virtual Desktop (Citrix, VMware View) |

---

## STEP 6 — Suffix lookup (Table 4)

| Suffix | Resource | Suffix | Resource |
|---|---|---|---|
| `rg` | Resource Group | `agw` | Application Gateway |
| `vm` | Virtual Machine | `asv` | App Service |
| `as` | Availability Set | `kv` | Key Vault |
| `vnet` | Virtual Network | `asp` | App Service Plan |
| `snet` | Subnet | `sdb` | SQL Database |
| `pip#` | Public IP Address | `sql` | SQL Server |
| `fw` | Firewall | `dsk` | Disk |
| `nsg` | Network Security Group | `bstn` | Azure Bastion |
| `stg` | Storage Account | `law` | Log Analytics Workspace |
| `tm` | Traffic Manager | `fnc` | Function |
| `lb` | Load Balancer | `log` | Logic App |
| `lbi` / `lbe` | Azure Internal / External LB | `nic#` | Network Interface |
| `lbr` | LB Rule | `con` | Connection |
| `lbhp` | LB Health Probe | `rt` | Route Table |
| `lbbp` | LB Backend Pool | `route` | Route |
| `vgw` | VNet Gateway | `osdisk#` | VM OS Disk |
| `lgw` | Local Network Gateway | `datadisk#` | VM Data Disk |
| `gwp` | VNet Peering | `mg` | Management Group |
| `nw` | Network Watcher | `azfw` | Azure Firewall |
| `pview` | Azure Purview | `svcplan` | App Service Plan |
| `appi` | Application Insights | `svc` | Application Service |
| `wapp` | Web Application | `ss` | Search Service |
| `dbw` | Databricks Service | `sgla` | SQL Assessment |
| `adf` | Azure Data Factory | `syn` | Synapse Workspace |
| `erc` | Express Route Circuit | `ergw` | Express Route Gateway |
| `fn` | Function App | `spn` | Service Principal |
| `vng` | Virtual Network Gateway | `lng` | Local Network Gateway |

---

## STEP 7 — Global naming rules (always enforce)

1. **Prefix is 4 fixed chars**: `<dept(2)><env(1)><region(1)>` — no delimiter within it. e.g., `ScPc`
2. **Device type** (3 chars) attaches directly after prefix — no delimiter. e.g., `ScPcCNR`
3. **Hyphen `-`** separates the prefix block from `<userDefined>`. e.g., `ScPcCNR-`
4. **No spaces** in resource names (spaces allowed only in Subscription and Management Group names)
5. **Reserved character**: Hyphen `-` is for mandatory field delimitation only
6. **Case**: Not used as a field delimiter; Camel Case is recommended for readability
7. **VMs have no suffix** — child objects inherit parent VM name with suffix swapped
8. **Child objects**: Always derive name from parent: `<parent-name-without-suffix>-<child-suffix>`
9. **Entra ID**: Underscore `_` is the field delimiter (not hyphen)
10. **Storage accounts**: Lowercase alphanumeric only, no hyphens, globally unique, max 24 chars
11. **Windows VMs**: Max 15 characters (NetBIOS/DNS limit)
12. **Key Vaults**: Max 24 characters
13. **Strip invalid chars**: `< > " ' [ ] : | + = ; , ? * @ &`
14. **Exceptions**: Azure Marketplace/vendor templates that can't comply must still use the 4-char GC prefix

### CSP Region codes

| Code | Cloud / Region |
|---|---|
| `C/c` | Azure — Canada Central |
| `D/d` | Azure — Canada East |
| `G/g` | AWS — ca-central-1 |
| `H/h` | AWS — (reserved, future) |
| `K/k` | GCP — northamerica-northeast1 (Montreal) |
| `L/l` | GCP — (reserved, future) |
| `M/m` | GCP / Azure — multi-region |
| `O/o` | IBM — Canada Montreal |
| `P/p` | IBM — Canada Toronto |
| `Y/y` | Azure Stack SSC East (EDC Montreal) |
| `Z/z` | Azure Stack SSC Central (EDC Barrie) |

---

## STEP 8 — Tagging guidance

### Global rules
- Tags are set **at the resource level** — not inherited from resource groups
- Tags should be applied through **automation/IaC**, not manually
- Hyphen `-` is the reserved delimiter within governance tag values
- **Lowercase recommended** (Azure is not case-sensitive; use `tolower()` in code)
- **Date format**: ISO8601 — `YYYY-MM-DD` (no slashes)
- Max **50 tag pairs** per resource
- Tag key max: 512 chars (128 for storage); tag value max: 256 chars
- Forbidden chars in governance tag keys/values: `< > % & \ ? /`
- Spaces not allowed in governance tag keys or values

### Common governance tags

| Key | Example value | Description |
|---|---|---|
| `costcenter` | `22578-proj_123` | Billing/cost tracking code |
| `env` | `prod` | Environment (prod, dev, qa, sandbox) |
| `classification` | `pbmm` | Data classification (e.g., pbmm, unclassified) |
| `owner` | `jane.doe@canada.ca` | Resource owner contact |
| `OsHostname` | `MyLegacyServer01` | **VM only**: use when cloud resource name ≠ OS NetBIOS/hostname (workload migration) |

### Tag scope reservations
- **Tenant-level**: Reserved for GC-wide governance keys (e.g., `ssc`, `gc`)
- **Subscription-level**: Cloud broker billing tags (e.g., `ssc-cbs:<billing_code>-<expiry>`)
- **Resource Group level**: Network zone tags (e.g., `cnz:<paz>`)
- **Resource level**: Owner-defined user tags (minimum 30 tag slots reserved for resource owner)

### Terraform tag pattern
```hcl
tags = merge(var.tags, try(var.<res>_config.tags, {}))

# For VMs where OS hostname differs from resource name:
tags = merge(var.tags, try(var.<res>_config.tags, {}),
  [try(var.<res>_config.computer_name, null) != null
    ? { "OsHostname" = var.<res>_config.computer_name }
    : null]...)
```

---

## STEP 9 — Output format

### For **generate**:
Present the name clearly with a breakdown:

```
Generated name: ScPcCNR-Core-MRZ-vnet

Breakdown:
  Sc   → dept code (SSC)
  P    → environment (Production)
  c    → CSP region (Azure Canada Central)
  CNR  → device type (Cloud Network Resource)
  -    → field delimiter
  Core-MRZ → user defined string
  -    → field delimiter
  vnet → suffix (Virtual Network)

Length: 18 chars ✓ (limit: 64)
Character set: ✓ alphanumeric + hyphen
```

### For **validate**:
Parse the name, check each field, and report:
- ✅ Pass / ❌ Fail for each rule (prefix, device type, delimiter, suffix, length, chars)
- List any violations with the specific rule broken
- Suggest a corrected name if it can be fixed

### For **explain**:
Answer directly, reference the standard rule, and give an example.

### For **tag**:
Show the mandatory and recommended tags for the resource type, with example values.

---

## Quick reference card

```
Structure:  <dept(2)><env(1)><region(1)>[<devType(3)>]-<userDefined>[-<suffix>]
Example:    ScPcSWA-MyApp01          ← Windows VM (no suffix, max 15 chars)
            ScPcCNR-Core-MRZ-vnet   ← VNet
            ScPcCSV-MyVault01-kv    ← Key Vault
            scpcmyuniquestorage001  ← Storage account (lowercase, no hyphen)
            ScPc-CTO-VDC-Core-rg    ← Resource group (no device type)
            ScPc_APP_MyApp-rg_Reader ← Entra ID group (underscore delimiter)

Prefix codes (SSC):  Sc=SSC  P=Prod D=Dev Q=QA S=Sandbox  C=AzureCentral D=AzureEast
```
