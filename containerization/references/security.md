# Container Security

## Non-Root User (Mandatory)

Every production Dockerfile must run as non-root.

```dockerfile
# Create dedicated user and group
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Set ownership
RUN chown -R appuser:appgroup /app

# Switch before CMD
USER appuser
```

**Why:** Root containers can escalate to host if runtime vulnerabilities exist. Non-root limits blast radius.

---

## Minimal Base Images

Fewer packages = fewer CVEs = smaller attack surface.

| Image               | Size   | Shell? | Package Mgr? |
| ------------------- | ------ | ------ | ------------ |
| `distroless`        | ~2MB   | No     | No           |
| `alpine`            | ~5MB   | Yes    | apk          |
| `debian-slim`       | ~80MB  | Yes    | apt          |
| `ubuntu`            | ~130MB | Yes    | apt          |

- Use `distroless` when no shell access is needed (pure Go, Java JRE)
- Use `alpine` for most workloads
- Only use full distros when specific glibc packages are required

---

## Binary Verification During Build

Verify downloaded binaries with GPG + SHA256 to prevent supply chain attacks.

```dockerfile
RUN apk add --no-cache unzip gnupg \
    && curl -Lo /tmp/hashicorp.asc https://keybase.io/hashicorp/pgp_keys.asc \
    && gpg --import /tmp/hashicorp.asc \
    && curl -Lo /tmp/terraform.zip https://releases.hashicorp.com/terraform/${VERSION}/terraform_${VERSION}_linux_amd64.zip \
    && curl -Lo /tmp/terraform_SHA256SUMS https://releases.hashicorp.com/terraform/${VERSION}/terraform_${VERSION}_SHA256SUMS \
    && curl -Lo /tmp/terraform_SHA256SUMS.sig https://releases.hashicorp.com/terraform/${VERSION}/terraform_${VERSION}_SHA256SUMS.sig \
    # Verify signature
    && gpg --trust-model always --verify /tmp/terraform_SHA256SUMS.sig /tmp/terraform_SHA256SUMS \
    # Verify checksum
    && cd /tmp && grep "terraform_${VERSION}_linux_amd64.zip" terraform_SHA256SUMS | sha256sum -c - \
    # Install
    && unzip /tmp/terraform.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/terraform \
    # Cleanup in same layer
    && rm -rf /tmp/*.zip /tmp/*SHA256SUMS* /tmp/hashicorp.asc /root/.gnupg \
    && apk del unzip gnupg
```

**Principles:**
- Two-layer verification: GPG (authenticity) + SHA256 (integrity)
- Build fails immediately if verification fails
- Use official vendor GPG keys, not third-party
- Clean up verification artifacts in the same layer

---

## No Secrets in Layers

**Anti-patterns (NEVER do):**
```dockerfile
COPY secrets.txt /app/          # persists in layer history
ENV API_KEY=sk-abc123           # visible in image inspect
RUN echo "password" > /app/.env # persists even if deleted later
```

**Correct approach:**
- Mount secrets at runtime (Docker Secrets, K8s Secrets, Vault)
- Use `--mount=type=secret` for build-time secrets (BuildKit)
- Application reads secrets from env vars or mounted files at startup

---

## Image Signing & Verification

```bash
# Sign with Cosign
cosign sign --key cosign.key myregistry.com/myapp:v1.0.0

# Verify before deploy
cosign verify --key cosign.pub myregistry.com/myapp:v1.0.0
```

- Sign all production images in CI/CD
- Enforce verification policies — reject unsigned images
- Use Docker Content Trust or Cosign

---

## Static Analysis (CI Integration)

```yaml
# GitHub Actions
- name: Lint Dockerfile
  run: docker run --rm -i hadolint/hadolint < Dockerfile

- name: Scan for vulnerabilities
  run: |
    docker build -t myapp .
    trivy image --severity HIGH,CRITICAL myapp
```

- **Hadolint**: Dockerfile linting (best practices, security rules)
- **Trivy/Snyk/Clair**: Image vulnerability scanning
- Fail CI on CRITICAL/HIGH findings

---

## Capability Restrictions

At runtime, drop all unnecessary Linux capabilities:

```bash
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myapp
```

- Default: drop ALL, then add only what's needed
- Use `--security-opt=no-new-privileges` to prevent privilege escalation
- Mount root filesystem read-only when possible: `--read-only`
- Use seccomp profiles for additional syscall restrictions
