# Runtime & Orchestration

## Resource Limits

Always set CPU and memory limits to prevent resource exhaustion.

```yaml
# Docker Compose
services:
  app:
    image: myapp:latest
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

```yaml
# Kubernetes
spec:
  containers:
  - name: myapp
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

- Set both requests (guaranteed) and limits (ceiling)
- Monitor actual usage to tune appropriately
- Limits prevent noisy-neighbor problems

---

## Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8080/health || exit 1
```

- **Liveness**: Is the app alive? Restart if not.
- **Readiness**: Can it serve traffic? Remove from LB if not.
- Design checks that are lightweight and fast
- Use `--start-period` to allow for application warm-up

---

## Logging

- Write to `STDOUT`/`STDERR` — never to files inside the container
- Use structured logging (JSON) for parsing by aggregators
- Integrate with Fluentd, Logstash, or Loki for centralization
- Set up log rotation and retention policies

```dockerfile
# Application should log to stdout
CMD ["node", "dist/main.js"]
# NOT: CMD ["node", "dist/main.js >> /var/log/app.log"]
```

---

## Persistent Storage

```yaml
services:
  database:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

- **Never** store persistent data in container's writable layer
- Use named volumes or cloud-native storage (EBS, Azure Disk, GCE PD)
- Implement backup strategies for all persistent volumes
- Prefer named volumes over bind mounts for portability

---

## Networking

```yaml
services:
  web:
    networks:
      - frontend
      - backend
  api:
    networks:
      - backend
  db:
    networks:
      - backend

networks:
  frontend:
  backend:
    internal: true  # No external access
```

- Create separate networks per application tier
- Use `internal: true` for backend networks (no external access)
- Use service discovery (DNS) provided by orchestrator
- Implement network policies in Kubernetes for pod-to-pod control

---

## Orchestration Patterns

### Rolling Updates (Zero Downtime)

```yaml
# Kubernetes
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

### Scaling

```yaml
# Docker Compose
services:
  app:
    deploy:
      replicas: 3
```

### Key Orchestration Features
- **Auto-scaling**: Scale based on CPU/memory/custom metrics
- **Self-healing**: Restart failed containers automatically
- **Service discovery**: Built-in DNS for inter-service communication
- **Rolling updates**: Zero-downtime deployments with automatic rollback
