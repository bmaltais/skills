# Coder on k3s — Troubleshooting

## 502 Bad Gateway — "connection was refused"

### Symptom
```
Failed to proxy request to application: dial context: connect tcp [fd7a:...]:13337: connection was refused
```

### Cause A: code-server not running
Check:
```bash
kubectl exec -n coder-<owner> workspace-<name> -- ss -tlnp | grep 13337
kubectl exec -n coder-<owner> workspace-<name> -- tail -30 /tmp/coder-startup-script.log
```

Fix: ensure startup_script installs and starts code-server **before** `apt-get install`.

### Cause B: code-server bound to IPv4 only (`0.0.0.0`)
Coder connects via Tailscale IPv6 (`fd7a:115c:...`). Binding to `0.0.0.0` misses IPv6.

Fix:
```bash
code-server --bind-addr [::]:13337 ...
```

### Cause C: startup script still running
The apt install phase takes 3-10 minutes. If code-server starts after apt, the health check times out.

Fix: move code-server start to the top of the startup_script, before any apt commands.

---

## Workspace namespace not found

### Symptom
```
Error: namespaces "coder-bmaltais" not found
```

### Cause
Coder does NOT auto-create the workspace namespace. The template must do it.

### Fix
Add to template:
```hcl
resource "kubernetes_namespace" "workspace" {
  metadata { name = local.namespace }
}

# And add depends_on to all other resources:
resource "kubernetes_persistent_volume_claim" "workspace" {
  depends_on = [kubernetes_namespace.workspace]
  ...
}
resource "kubernetes_pod" "workspace" {
  depends_on = [kubernetes_namespace.workspace]
  ...
}
```

---

## CLI version mismatch

### Symptom
```
WARN: Your client version (2.21.3) does not match the server version (2.33.2)
```

### Fix
```bash
ssh bernard@mini1 "curl -fsSL https://coder.com/install.sh | sh -s -- --version 2.33.2"
ssh bernard@mini1 "coder version"
```

---

## `coder login` requires browser / hangs

### Symptom
`coder login` opens a browser auth flow — unusable from SSH.

### Fix
Get a token from the UI: **Settings → Tokens → + New token**, then:
```bash
ssh bernard@mini1 "coder login http://100.101.186.51:31557 --token <token>"
```

Do NOT escape the token with `\$` — pass it literally.

---

## `--token` flag not getting argument

### Symptom
```
flag needs an argument: --token
```

### Cause
Shell escaping: `--token \$CODER_TOKEN` expands to empty string.

### Fix
```bash
# WRONG:
ssh bernard@mini1 "coder login http://... --token \$TOKEN"

# RIGHT (token literal):
ssh bernard@mini1 "coder login http://... --token abc123xyz"

# RIGHT (env var set before command):
ssh bernard@mini1 "TOKEN=abc123xyz coder login http://... --token \$TOKEN"
```

---

## Startup script "output pipes were not closed" warning

### Symptom
```
WARNING: script exited successfully, but output pipes were not closed after 10s.
This usually means a child process was started with references to stdout or stderr.
```

### Cause
A background process (e.g. `code-server`) was launched with `&` but without redirecting its stdout/stderr. Coder waits for all file descriptors referencing the script's pipes to close. Since the background process inherited them, Coder times out and may terminate that process.

### Fix
Redirect the background process output away from the script's pipes:
```bash
# WRONG — inherits startup script's stdout/stderr pipes:
code-server --bind-addr [::]:13337 --auth none /home/coder &

# RIGHT — detached from pipes, logs go to a file:
code-server --bind-addr [::]:13337 --auth none /home/coder > /tmp/code-server.log 2>&1 &
```

The log is then readable inside the pod:
```bash
kubectl exec -n coder-<owner> workspace-<name> -- tail -f /tmp/code-server.log
```

---

## apt-get fails with 503 on git package

### Symptom
```
E: Failed to fetch https://ppa.launchpadcontent.net/git-core/ppa/ubuntu/...  503 Service Unavailable
```

### Cause
`codercom/enterprise-base:ubuntu` includes `/etc/apt/sources.list.d/git-core-ubuntu-ppa-noble.sources` which points to a broken PPA.

### Fix
Remove the file before `apt-get update`:
```bash
sudo find /etc/apt/sources.list.d/ -name "*git*" | sudo xargs rm -f 2>/dev/null || true
sudo grep -rl 'git-core\|launchpadcontent.net/git' /etc/apt/sources.list.d/ | sudo xargs rm -f 2>/dev/null || true
sudo apt-get update -qq
```

Note: the file is `git-core-ubuntu-ppa-noble.sources` (deb822 format, not `.list`).

---

## Workspace pod stuck in Pending

```bash
kubectl describe pod workspace-<name> -n coder-<owner>
```

Common causes:
- **No node matches nodeSelector**: check `role=apps` or `role=agent-runner` label exists
  ```bash
  kubectl get nodes --show-labels | grep role
  ```
- **PVC unbound**: check storage class supports `ReadWriteOnce` on that node
  ```bash
  kubectl get pvc -n coder-<owner>
  ```
- **Resource limits too high**: reduce cpu/memory in template parameters

---

## CODER_ACCESS_URL connection refused (workspace agent can't connect)

### Symptom
Workspace pod starts but agent never connects. Logs show repeated connection refused to the access URL.

### Cause
`CODER_ACCESS_URL` is set to the ClusterIP service — pods can't reach themselves via ClusterIP in some CNI configurations.

### Fix
Use NodePort (accessible from all pods via node IP):
```yaml
CODER_ACCESS_URL: "http://100.101.186.51:31557"  # Tailscale IP + NodePort
```

Never use `http://coder.coder.svc` as the access URL.

---

## Check all workspace logs at once

```bash
# Startup script
kubectl exec -n coder-<owner> workspace-<name> -- cat /tmp/coder-startup-script.log

# Agent init log  
kubectl exec -n coder-<owner> workspace-<name> -- cat /tmp/coder-agent-init.log

# Running processes
kubectl exec -n coder-<owner> workspace-<name> -- ps aux

# Port listeners
kubectl exec -n coder-<owner> workspace-<name> -- ss -tlnp
```
