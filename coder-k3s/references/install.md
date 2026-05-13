# Coder on k3s — Install & Upgrade

## Prerequisites

```bash
helm repo add coder-v2 https://helm.coder.com/v2
helm repo update
kubectl create namespace coder
```

## PostgreSQL Backend

Deploy before Coder:

```yaml
# /home/bernard/coder/postgres.yaml
# - Deployment: coder-db, namespace: coder
# - nodeSelector: role=apps  (pins to mini1)
# - hostPath: /opt/coder-db on mini1
# - credentials: coder / coderpass
# - Service: ClusterIP, port 5432, name coder-db
```

```bash
kubectl apply -f /home/bernard/coder/postgres.yaml
```

## Helm Values (helm-values.yaml)

Key settings:
```yaml
coder:
  env:
    - name: CODER_ACCESS_URL
      value: "http://100.101.186.51:31557"   # Tailscale IP of mini1, NodePort
    - name: CODER_PG_CONNECTION_URL
      value: "postgres://coder:coderpass@coder-db.coder.svc:5432/coder?sslmode=disable"
  service:
    type: NodePort
    nodePort: 31557
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: role
                operator: In
                values: ["apps"]
```

> **CODER_ACCESS_URL must use NodePort (not ClusterIP).**
> ClusterIP is not reachable from the pod itself — this causes "connection refused" on workspace agent connect.

## Install

```bash
helm upgrade --install coder coder-v2/coder \
  --namespace coder \
  --version 2.33.2 \
  -f /home/bernard/coder/helm-values.yaml

kubectl rollout status deployment/coder -n coder --timeout=120s
```

## RBAC (workspace creation)

Coder needs cluster-admin to create workspace namespaces and pods:

```bash
kubectl apply -f /home/bernard/coder/rbac.yaml
```

## First-time Admin User

```bash
ssh bernard@mini1 "coder login http://100.101.186.51:31557 \
  --first-user-username bmaltais \
  --first-user-email admin@example.com \
  --first-user-password <password>"
```

## Verify

```bash
kubectl get pods -n coder -o wide
# coder pod     → mini1 (role=apps)
# coder-db pod  → mini1 (role=apps)

curl -s http://100.101.186.51:31557/api/v2/buildinfo | jq .version
# Should return: "2.33.2"
```

## Upgrade

```bash
helm repo update
helm upgrade coder coder-v2/coder \
  --namespace coder \
  --version <new-version> \
  -f /home/bernard/coder/helm-values.yaml
```

After upgrade, update the CLI on mini1:
```bash
ssh bernard@mini1 "curl -fsSL https://coder.com/install.sh | sh -s -- --version <new-version>"
ssh bernard@mini1 "coder version"
```
