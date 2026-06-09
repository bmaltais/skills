---
name: coder-k3s
description: 'Deploy, configure, manage, and troubleshoot Coder self-hosted dev environments on a k3s Kubernetes cluster. Use when: installing Coder on k3s, creating or updating workspace templates, debugging 502 Bad Gateway errors, fixing code-server connectivity, managing Coder CLI authentication, pushing Terraform workspace templates, configuring PostgreSQL backend, debugging workspace pod failures, setting up per-user namespaces, or integrating Coder workspaces with LiteLLM / GPU nodes.'
argument-hint: 'install | template | workspace | troubleshoot | auth'
---

# Coder on k3s

End-to-end skill for running Coder (self-hosted dev environments) on a k3s cluster over Tailscale.

## Cluster Context

- **Coder server**: `<CODER_SERVER_HOST>` (NodePort 31557), namespace `coder`
- **Access URL**: `http://<CODER_SERVER_IP>:31557` (Tailscale direct) or SSH tunnel → `http://localhost:8081`
- **SSH tunnel**: `ssh -L 8081:<CODER_SERVER_IP>:31557 <USER>@<CODER_SERVER_HOST> -N`
- **PostgreSQL**: `coder-db` pod in `coder` namespace on `<CODER_SERVER_HOST>`
- **Helm values**: `~/coder/helm-values.yaml`
- **Templates dir**: `~/coder/workspace-template/` (ai-workspace), `~/coder/workspace-template-minimal/` (minimal-ubuntu)

## When to Use

- Installing or upgrading Coder via Helm
- Authenticating the `coder` CLI (token-based, non-interactive)
- Creating or pushing workspace templates
- Debugging workspace pod failures (502, connection refused, bad gateway)
- Configuring GPU vs CPU node scheduling in templates
- Setting up per-user namespace isolation
- Integrating workspaces with LiteLLM or other cluster services

---

## Install & Upgrade

See [./references/install.md](./references/install.md) for full procedure.

Quick upgrade:
```bash
helm upgrade coder coder-v2/coder -n coder -f ~/coder/helm-values.yaml
```

---

## CLI Authentication

Coder CLI requires a session token — browser auth doesn't work over SSH.

```bash
# 1. Open UI → Settings → Tokens → + New token
# 2. Run:
ssh <USER>@<CODER_SERVER_HOST> "coder login http://<CODER_SERVER_IP>:31557 --token <token>"
```

Verify:
```bash
ssh <USER>@<CODER_SERVER_HOST> "coder list"
```

---

## Template Management

See [./references/templates.md](./references/templates.md) for authoring guide.

### Push an update
```bash
scp -r ~/coder/workspace-template <USER>@<CODER_SERVER_HOST>:/tmp/
ssh <USER>@<CODER_SERVER_HOST> "coder templates push ai-workspace --directory /tmp/workspace-template/ --yes"
```

### Update existing workspace to new template version
```bash
ssh <USER>@<CODER_SERVER_HOST> "coder update <owner>/<workspace>"
```

### List templates
```bash
ssh <USER>@<CODER_SERVER_HOST> "coder templates list"
```

---

## Workspace Storage — What Persists vs What Doesn't

Each workspace has a PVC mounted at `/home/coder`. Only this directory survives a workspace stop/start.

| Location | Persists? | Notes |
|---|---|---|
| `/home/coder/**` | ✅ Yes | PVC — survives pod deletion |
| `~/.local`, `~/.config`, `~/.bashrc` | ✅ Yes | Inside `/home/coder` |
| System packages (`apt install`) | ❌ No | Container filesystem — gone on stop |
| `/usr/local/**`, `/opt/**` | ❌ No | Ephemeral container layer |

### Making installed tools persist

**Option 1 — Install to home dir** (immediate, no template change):
```bash
# Example: install a binary to ~/.local/bin (persists)
curl -fsSL https://example.com/install.sh | INSTALL_DIR=/home/coder/.local/bin bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

**Option 2 — Add to startup_script** (reinstalls on every start, reproducible):
```hcl
startup_script = <<-EOT
  # Pixi package manager — install once, cached on PVC
  if [ ! -f /home/coder/.pixi/bin/pixi ]; then
    curl -fsSL https://pixi.sh/install.sh | bash
  fi
  echo 'export PATH="/home/coder/.pixi/bin:$PATH"' >> /home/coder/.bashrc
  
  # System tools reinstalled on every start (fast with apt cache)
  sudo apt-get install -y -qq curl git vim python3-pip
EOT
```

**Option 3 — Custom Docker image** (fastest startup, most reproducible):
Replace `codercom/enterprise-base:ubuntu` with a custom image that has your tools pre-baked.

---

## Workspace Operations

```bash
# List all workspaces
ssh <USER>@<CODER_SERVER_HOST> "coder list"

# Create workspace from template
ssh <USER>@<CODER_SERVER_HOST> "coder create --template=ai-workspace --org=coder myworkspace"

# Delete workspace
ssh <USER>@<CODER_SERVER_HOST> "coder delete <owner>/<workspace> --yes"

# Get workspace pod
kubectl get pods -A | grep coder- | grep -v '^coder '

# Exec into workspace pod
kubectl exec -n coder-<owner> workspace-<name> -- bash
```

### restart vs update — important distinction

| Command | Template version used | When to use |
|---------|----------------------|-------------|
| `coder restart <ws> --yes` | Same version as currently running | Bounce the pod (no template change) |
| `coder update <ws>` | Latest published template version | After pushing a template fix — **does NOT accept `--yes`** |

After pushing a template fix with `coder templates push`, always use `coder update` (not `coder restart`) to pick up the change:
```bash
# Push fix
scp -r ~/coder/workspace-template-minimal <USER>@<CODER_SERVER_HOST>:/tmp/
ssh <USER>@<CODER_SERVER_HOST> "coder templates push minimal-ubuntu --directory /tmp/workspace-template-minimal/ --yes"

# Apply to a running workspace (no --yes flag available)
ssh <USER>@<CODER_SERVER_HOST> "coder update <owner>/<workspace>"
```

Monitor until healthy:
```bash
ssh <USER>@<CODER_SERVER_HOST> "coder logs <owner>/<workspace> --follow"
# Confirm: HEALTHY: true
ssh <USER>@<CODER_SERVER_HOST> "coder list"
```

---

## Troubleshooting

See [./references/troubleshoot.md](./references/troubleshoot.md) for all known issues.

Quick checks:
```bash
# Check startup script log
kubectl exec -n coder-<owner> workspace-<name> -- tail -50 /tmp/coder-startup-script.log

# Check if code-server is listening
kubectl exec -n coder-<owner> workspace-<name> -- ss -tlnp | grep 13337

# Check coder server logs
kubectl logs -n coder -l app.kubernetes.io/name=coder --tail=50
```
