---
name: go-k8s-cli
description: "Scaffold, build, and debug a Go CLI that talks to Kubernetes via client-go. Use when: creating a new Go CLI for Kubernetes, wiring up Cobra commands, applying/deleting Kubernetes resources from Go, waiting for pod readiness, streaming logs, or running kubectl-exec from Go code. Trigger on phrases like 'build a go cli for k8s', 'scaffold a kubernetes go tool', 'create/update/delete k8s resources from go', 'stream pod logs in go', 'wait for pod ready in go', 'kubectl exec from go'."
argument-hint: "scaffold | apply | wait | logs | exec | troubleshoot"
---

# Go + Kubernetes CLI Skill

End-to-end reference for scaffolding a Go CLI that manages Kubernetes resources using `k8s.io/client-go` and `github.com/spf13/cobra`.

---

## Environment Setup

### Go via snap (Ubuntu/Debian)
snap-installed Go lives at `/snap/bin/go` but `/snap/bin` is often **not** in PATH inside non-interactive shells or VS Code terminals.

```bash
export PATH="$PATH:/snap/bin"
go version   # verify before running any go commands
```

Add to `~/.bashrc` or `~/.profile` to make permanent.

---

## Module Scaffold

```bash
go mod init github.com/<org>/<repo>
```

Required dependencies for a k8s CLI:

```
k8s.io/client-go          # Kubernetes API client
k8s.io/api                # Kubernetes API types (Pod, StatefulSet, etc.)
k8s.io/apimachinery       # ObjectMeta, runtime types, apierrors
github.com/spf13/cobra    # CLI framework
gopkg.in/yaml.v3          # Config file parsing
```

```bash
go get k8s.io/client-go@v0.29.3 k8s.io/api@v0.29.3 k8s.io/apimachinery@v0.29.3
go get github.com/spf13/cobra@v1.8.1 gopkg.in/yaml.v3@v3.0.1
go mod tidy
```

### First build is slow
First `go build ./...` on a fresh module compiles all k8s dependencies — this takes **2–4 minutes**. Use a 300s+ timeout or run async. Subsequent builds are cached and fast.

---

## kubeconfig / REST client

```go
// internal/k8s/client.go
func buildRestConfig(kubeconfigPath string) (*rest.Config, error) {
    if kubeconfigPath == "" {
        kubeconfigPath = os.Getenv("KUBECONFIG")
    }
    if kubeconfigPath != "" {
        return clientcmd.BuildConfigFromFlags("", kubeconfigPath)
    }
    // Default rules: ~/.kube/config → in-cluster
    loadingRules := clientcmd.NewDefaultClientConfigLoadingRules()
    cfg, err := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(
        loadingRules, &clientcmd.ConfigOverrides{},
    ).ClientConfig()
    if err == nil {
        return cfg, nil
    }
    return rest.InClusterConfig()
}
```

Expose both `*kubernetes.Clientset` and `*rest.Config` when you need `kubectl exec`:

```go
func NewClientWithConfig(path string) (*kubernetes.Clientset, *rest.Config, error) {
    cfg, err := buildRestConfig(path)
    if err != nil { return nil, nil, err }
    cs, err := kubernetes.NewForConfig(cfg)
    return cs, cfg, err
}
```

---

## Apply / Upsert Pattern

For create-or-update without server-side apply:

```go
_, err := cs.CoreV1().ConfigMaps(ns).Get(ctx, name, metav1.GetOptions{})
if apierrors.IsNotFound(err) {
    _, err = cs.CoreV1().ConfigMaps(ns).Create(ctx, obj, metav1.CreateOptions{})
} else if err == nil {
    _, err = cs.CoreV1().ConfigMaps(ns).Update(ctx, obj, metav1.UpdateOptions{})
}
```

---

## Secrets — NEVER pre-encode Data values

`corev1.Secret.Data` is `map[string][]byte`. Kubernetes handles base64 encoding at the wire level. **Store raw bytes only:**

```go
// CORRECT
secret.Data = map[string][]byte{
    "authkey": []byte(authKeyPlaintext),
}

// WRONG — double-encodes; the key will be base64(base64(value)) on disk
secret.Data = map[string][]byte{
    "authkey": []byte(base64.StdEncoding.EncodeToString([]byte(authKeyPlaintext))),
}
```

Use `secret.StringData` (type `map[string]string`) if you prefer to work with strings — k8s auto-converts to `Data` on write.

---

## client-go Type Placement Cheat Sheet

Common mistake: importing the wrong package for a type.

| Type | Correct package | Wrong assumption |
|---|---|---|
| `PodLogOptions` | `corev1 "k8s.io/api/core/v1"` | `metav1` |
| `PodExecOptions` | `corev1 "k8s.io/api/core/v1"` | `metav1` |
| `ObjectMeta` | `metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"` | `corev1` |
| `GetOptions`, `ListOptions` | `metav1` | `corev1` |
| `DeleteOptions` | `metav1` | `corev1` |
| `LabelSelector` | `metav1` | `corev1` |
| `ResourceRequirements` (PVC) | `corev1` | `metav1` |

---

## Streaming Pod Logs

```go
import corev1 "k8s.io/api/core/v1"

req := cs.CoreV1().Pods(ns).GetLogs(podName, &corev1.PodLogOptions{
    Container: "mycontainer",
    Follow:    true,
})
stream, err := req.Stream(ctx)
if err != nil { return err }
defer stream.Close()
io.Copy(os.Stdout, stream)
```

---

## Wait for Pod Ready

```go
import "k8s.io/apimachinery/pkg/util/wait"

err := wait.PollUntilContextTimeout(ctx, 3*time.Second, 5*time.Minute, false,
    func(ctx context.Context) (bool, error) {
        pod, err := cs.CoreV1().Pods(ns).Get(ctx, podName, metav1.GetOptions{})
        if apierrors.IsNotFound(err) { return false, nil }
        if err != nil { return false, err }
        if pod.Status.Phase != corev1.PodRunning { return false, nil }
        for _, cs := range pod.Status.ContainerStatuses {
            if !cs.Ready { return false, nil }
        }
        return true, nil
    },
)
```

---

## kubectl exec from Go (SPDY)

```go
import (
    corev1 "k8s.io/api/core/v1"
    "k8s.io/client-go/kubernetes/scheme"
    "k8s.io/client-go/tools/remotecommand"
)

req := cs.CoreV1().RESTClient().Post().
    Resource("pods").Name(podName).Namespace(ns).
    SubResource("exec").
    VersionedParams(&corev1.PodExecOptions{
        Container: "mycontainer",
        Command:   []string{"tailscale", "ip", "-4"},
        Stdout: true, Stderr: true,
    }, scheme.ParameterCodec)

exec, _ := remotecommand.NewSPDYExecutor(restCfg, "POST", req.URL())
var stdout, stderr bytes.Buffer
exec.StreamWithContext(ctx, remotecommand.StreamOptions{
    Stdout: &stdout, Stderr: &stderr,
})
```

---

## SSH Command Passthrough (remote command after `--`)

To allow `mytool ssh <name> -- ls -la` style invocations, use `MinimumNArgs(1)` and `FParseErrWhitelist` so Cobra doesn't reject flags meant for the remote command:

```go
var sshCmd = &cobra.Command{
    Use:  "ssh <name> [-- remote command...]",
    Args: cobra.MinimumNArgs(1),
    RunE: runSSH,
    FParseErrWhitelist: cobra.FParseErrWhitelist{UnknownFlags: true},
}

func runSSH(_ *cobra.Command, args []string) error {
    name := args[0]
    remoteCmd := args[1:] // everything after the name

    sshArgs := []string{"-o", "StrictHostKeyChecking=accept-new", user + "@" + host}
    sshArgs = append(sshArgs, remoteCmd...)
    cmd := exec.Command("ssh", sshArgs...)
    // ...
}
```

---



Place scripts alongside the Go package that embeds them:

```
internal/k8s/
    embed.go          ← //go:embed directive lives here
    scripts/
        init.sh
```

```go
// embed.go
package k8s

import "embed"

//go:embed scripts/init.sh
var scripts embed.FS

func initScript() (string, error) {
    data, _ := scripts.ReadFile("scripts/init.sh")
    return string(data), nil
}
```

---

## Label Conventions for Managed Resources

```go
map[string]string{
    "app.kubernetes.io/managed-by": "mytool",
    "mytool.io/name":               name,
}
```

List with label selector:

```go
cs.AppsV1().StatefulSets(ns).List(ctx, metav1.ListOptions{
    LabelSelector: "app.kubernetes.io/managed-by=mytool",
})
```

---

## Cobra Skeleton

```go
// cmd/root.go
var (
    namespace  string
    kubeconfig string
)

var rootCmd = &cobra.Command{Use: "mytool", Short: "..."}

func Execute() { rootCmd.Execute() }

func init() {
    rootCmd.PersistentFlags().StringVar(&namespace, "namespace", "", "k8s namespace")
    rootCmd.PersistentFlags().StringVar(&kubeconfig, "kubeconfig", "", "path to kubeconfig")
    rootCmd.AddCommand(startCmd, stopCmd, deleteCmd, listCmd, logsCmd, sshCmd)
}
```

---

## Tailscale in Kubernetes

> Full reference is in the **tailscale-k8s** skill. Key points for Go CLI authors:

- Use `--state=kube:<secret>` + `--statedir=<pvc-path>` — auth state and SSH host keys both need persistent storage
- Skip `--authkey` on restart (check `tailscale status` first) to avoid `-1` suffix
- Scale to 0 and wait for pod termination **before** calling `DELETE /api/v2/device/{id}`
- Never call the Tailscale API on `stop` — only on `delete`
- Pod ServiceAccount needs `get/create/update/patch` on secrets for `TS_KUBE_SECRET`

See the **tailscale-k8s** skill for RBAC code, volume setup, API implementation, and the full stop-vs-delete pattern.

---


## PVC-Mounted Home Directory Ownership

When a StatefulSet mounts a PVC at `/home/<user>`, the provisioner creates the directory as **root**. `sshd` will refuse to authenticate because it requires the home directory to be owned by the user:

```
Authentication refused: bad ownership or modes for directory /home/dev
```

Fix in your init script — `chown` the **mount point itself**, not just `.ssh`:

```bash
# Correct: fix home dir ownership before setting up .ssh
chown dev:dev /home/dev
chmod 750 /home/dev

mkdir -p /home/dev/.ssh
cp /etc/myapp/authorized_keys /home/dev/.ssh/authorized_keys
chmod 700 /home/dev/.ssh
chmod 600 /home/dev/.ssh/authorized_keys
chown -R dev:dev /home/dev/.ssh
```

---

## SSH Host Key Churn on Pod Restart

### sshd-based SSH
StatefulSet pods regenerate SSH host keys on every restart (unless stored on the PVC). This causes `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED` for clients. Options:

1. **Short-term**: `ssh-keygen -R <hostname>` to clear the cached key before reconnecting.
2. **Long-term**: Store host keys on the PVC so they survive restarts:
   ```bash
   # In init.sh — persist host keys to the PVC
   KEYDIR=/home/dev/.ssh/host_keys
   mkdir -p "$KEYDIR"
   for type in rsa ecdsa ed25519; do
       keyfile="$KEYDIR/ssh_host_${type}_key"
       [ -f "$keyfile" ] || ssh-keygen -t "$type" -f "$keyfile" -N ""
       ln -sf "$keyfile" "/etc/ssh/ssh_host_${type}_key"
   done
   ```

### Tailscale SSH
With Tailscale SSH (`tailscale up --ssh`), host keys are managed by `tailscaled` in its `--statedir`. Set `--statedir` to a PVC-backed path — see the **tailscale-k8s** skill.

---

## k3s kubeconfig

k3s does not populate `~/.kube/config` automatically. The config lives at `/etc/rancher/k3s/k3s.yaml` and is root-owned. Copy it for user access:

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
```

Without this, `client-go`'s default config loader falls through to in-cluster detection and fails with:
```
unable to load in-cluster configuration, KUBERNETES_SERVICE_HOST and KUBERNETES_SERVICE_PORT must be defined
```

---

## Common Pitfalls

| Pitfall | Fix |
|---|---|
| `PodLogOptions` undefined from `metav1` | Import `corev1 "k8s.io/api/core/v1"` instead |
| Secret value corrupted / auth fails | Never base64-encode `Data []byte` values; use raw bytes |
| `go build` times out on first run | Allow 3–5 min for first k8s dep compilation; use 300s+ timeout |
| `/snap/bin/go` not found | `export PATH="$PATH:/snap/bin"` before any `go` commands |
| headless Service `clusterIP` rejected on update | Service `clusterIP: None` is immutable — delete and recreate if needed |
| StatefulSet `volumeClaimTemplates` immutable | Delete and recreate StatefulSet to change PVC spec |
| Tailscale sidecar CrashLoopBackOff | Missing RBAC — see **tailscale-k8s** skill |
| sshd rejects pubkey: `bad ownership for /home/dev` | PVC provisioned as root — `chown user:user /home/dev && chmod 750 /home/dev` in init script |
| SSH `REMOTE HOST IDENTIFICATION HAS CHANGED` | Pod restarted, new host keys generated — persist keys to PVC (see SSH Host Key Churn section) |
| `kubectl` fails: no kubeconfig | k3s stores config at `/etc/rancher/k3s/k3s.yaml` — copy to `~/.kube/config` |
| Any Tailscale identity / SSH / stop-vs-delete issue | See **tailscale-k8s** skill |
