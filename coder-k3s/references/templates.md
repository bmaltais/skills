# Coder Workspace Templates

## Available Templates

| Template | Description | Startup Time |
|----------|-------------|--------------|
| `ai-workspace` | aider + claude-code + LiteLLM pre-configured | ~5min (first), ~5s (restart) |
| `minimal-ubuntu` | code-server only, user installs the rest | ~90s (first), ~5s (restart) |

Template source files: `/home/bernard/coder/workspace-template/` and `/home/bernard/coder/workspace-template-minimal/`

---

## Template Structure

```hcl
terraform {
  required_providers {
    coder      = { source = "coder/coder" }
    kubernetes = { source = "hashicorp/kubernetes" }
  }
}

provider "kubernetes" {}  # uses in-cluster config

data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}
```

### Per-owner namespace pattern
```hcl
locals {
  namespace = "coder-${data.coder_workspace_owner.me.name}"
}

resource "kubernetes_namespace" "workspace" {
  metadata { name = local.namespace }
}
```
> Always create the namespace resource — Coder does NOT create it automatically.
> All other resources must `depends_on = [kubernetes_namespace.workspace]`.

### Node scheduling
```hcl
node_selector = var.use_gpu ? { "role" = "agent-runner" } : { "role" = "apps" }
# agent-runner → desktop-4m9dse4 (RTX 3090)
# apps         → mini1 or mini2
```

### Persistent home
```hcl
resource "kubernetes_persistent_volume_claim" "workspace" {
  metadata {
    name      = "home-${data.coder_workspace.me.name}"
    namespace = local.namespace
  }
  spec {
    access_modes = ["ReadWriteOnce"]
    resources { requests = { storage = "${var.disk_size}Gi" } }
  }
  wait_until_bound = false
}
```

---

## Startup Script Pattern

### Critical ordering rule
Always start `code-server` **before** `apt-get install`. apt can take 3-10 minutes; code-server must be up for the health check to pass.

```bash
startup_script = <<-EOT
  set -e

  # 1. Install code-server FIRST (cached on PVC after first run)
  if [ ! -f /home/coder/.local/bin/code-server ]; then
    curl -fsSL https://code-server.dev/install.sh | sh -s -- --method=standalone --prefix=/home/coder/.local
  fi
  export PATH="/home/coder/.local/bin:$PATH"
  # Redirect output to detach from the startup script's pipes.
  # Without this, Coder warns "output pipes were not closed after 10s" and
  # may terminate code-server when the script exits.
  code-server --bind-addr [::]:13337 --auth none --disable-telemetry /home/coder > /tmp/code-server.log 2>&1 &

  # 2. Remove broken git PPA from base image BEFORE apt-get update
  sudo find /etc/apt/sources.list.d/ -name "*git*" | sudo xargs rm -f 2>/dev/null || true
  sudo grep -rl 'git-core\|launchpadcontent.net/git' /etc/apt/sources.list.d/ | sudo xargs rm -f 2>/dev/null || true
  sudo apt-get update -qq 2>/dev/null || true

  # 3. Install tools (runs in background while code-server is already up)
  sudo apt-get install -y -qq curl git vim tmux htop jq ...
EOT
```

### Why `--bind-addr [::]:13337`
The Coder server connects to workspace pods via their Tailscale IPv6 address (e.g., `fd7a:115c:a1e0:...`).
Binding to `0.0.0.0:13337` only covers IPv4 — this causes 502 Bad Gateway.
`[::]:13337` covers both IPv4 and IPv6 on Linux (dual-stack).

### code-server PVC caching
`code-server` installs into `~/.local` which is the `/home/coder` PVC mount.
After the first workspace start, the binary is already there — subsequent starts skip the download and launch in ~2 seconds.

---

## code-server App Resource

```hcl
resource "coder_app" "code-server" {
  agent_id     = coder_agent.main.id
  slug         = "code-server"
  display_name = "VS Code"
  url          = "http://localhost:13337/?folder=/home/coder"
  icon         = "/icon/code.svg"
  subdomain    = false
  share        = "owner"

  healthcheck {
    url       = "http://localhost:13337/healthz"
    interval  = 5
    threshold = 6
  }
}
```

---

## Push Workflow

```bash
# 1. Edit template locally
vim /home/bernard/coder/workspace-template/main.tf

# 2. Copy to mini1
scp -r /home/bernard/coder/workspace-template bernard@mini1:/tmp/

# 3. Authenticate CLI if token expired
ssh bernard@mini1 "coder login http://100.101.186.51:31557 --token <token>"

# 4. Push
ssh bernard@mini1 "coder templates push ai-workspace --directory /tmp/workspace-template/ --yes"

# 5. Update existing workspaces
ssh bernard@mini1 "coder update <owner>/<workspace>"
```

> Use `coder templates push` (not `create`) for updates. `create` is deprecated.

---

## LiteLLM Integration

Inside any workspace pod, LiteLLM is reachable at:
```bash
export OPENAI_API_BASE=http://litellm.default.svc:4000/v1
export OPENAI_API_KEY=EMPTY

# Use with aider
aider --model openai/reasoning

# Use with claude-code
claude --api-url http://litellm.default.svc:4000/v1
```

Add to startup_script to pre-configure:
```bash
echo 'export OPENAI_API_BASE=http://litellm.default.svc:4000/v1' >> /home/coder/.bashrc
echo 'export OPENAI_API_KEY=EMPTY' >> /home/coder/.bashrc
```

---

## Known Deprecation Warnings (non-breaking)

- `kubernetes_namespace` → use `kubernetes_namespace_v1`
- `kubernetes_persistent_volume_claim` → use `kubernetes_persistent_volume_claim_v1`
- `kubernetes_pod` → use `kubernetes_pod_v1`
- `coder templates create` → use `coder templates push`

These are warnings only — templates work fine with the deprecated resources.
