# ITSG-33 PBMM Control Assessment Hints

Per-control guidance for `itsg-33-assess`. Each entry tells the LLM what to look for, which files to read, and what Pass / Fail / Not Assessable looks like for that control.

**Profile:** PBMM (Protected B / Medium Integrity / Medium Availability)  
**Source:** ITSG-33 Annex 3A — cyber.gc.ca

---

## How to read an entry

- **File patterns** — glob patterns the skill uses for targeted reads. Read files matching these patterns first.
- **Pass signals** — concrete artifacts or config patterns that indicate the control is satisfied.
- **Fail signals** — concrete artifacts or config patterns that indicate a gap.
- **Not Assessable** — when to report Not Assessable instead of Pass or Fail.

---

## AC — Access Control

### AC-2 — Account Management
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/rbac*.yaml`, `**/role*.yaml`, `**/serviceaccount*.yaml`, `**/values*.yaml`  
**Pass signals:** Service accounts explicitly defined with minimal scopes; no default service account tokens auto-mounted (`automountServiceAccountToken: false`); IaC creates named service principals with scoped permissions; stale accounts not present.  
**Fail signals:** `automountServiceAccountToken` absent or true on pod specs; service accounts with no explicit role binding at all; default service accounts used for workloads.  
**Not Assessable:** No Terraform, K8s manifests, or Helm values files found in repo.
**Note:** This control is about whether accounts are explicitly defined and provisioned deliberately — not about how much privilege they hold. Over-broad privilege on an otherwise well-defined, named account is AC-3's and AC-6's concern; don't fail AC-2 for it.

---

### AC-3 — Access Enforcement
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/rbac*.yaml`, `**/role*.yaml`, `**/clusterrole*.yaml`, `**/policy*.yaml`, `**/opa*.yaml`, `**/kyverno*.yaml`  
**Pass signals:** RBAC roles with explicit `rules` arrays (not wildcard); OPA Gatekeeper or Kyverno policies enforcing access constraints; IAM policies in Terraform with explicit `allow` actions (no `*`).  
**Fail signals:** A Role or ClusterRole's own `rules:` block, as defined in this repo's manifests, contains wildcard (`*`) verbs or resources; IAM policies with `"Action": "*"`; no admission controller policies found.  
**Not Assessable:** No RBAC manifests, IAM Terraform resources, or admission controller configs found.
**Note:** This control is about whether an access enforcement *mechanism* exists and is granular (explicit, non-wildcard rules) — not about whether privilege is minimized overall. A properly-scoped Role can make this control Pass even if a separate, broader grant elsewhere makes AC-6 Fail; the two controls assess different properties of the same RBAC surface and are not required to agree. A `ClusterRoleBinding`/`RoleBinding` that grants a broad *built-in* role (e.g. `cluster-admin`) by `roleRef` name is not itself a wildcard `rules:` block — that binding's breadth is AC-6's concern (excessive privilege grant), not evidence against AC-3's mechanism check. Only wildcard verbs/resources actually written in a `rules:` block in this repo count as an AC-3 Fail signal; do not infer wildcard content from a referenced role's well-known name.

---

### AC-4 — Information Flow Enforcement
**Severity:** P2  
**File patterns:** `**/networkpolicy*.yaml`, `**/*.tf`, `**/ingress*.yaml`, `**/egress*.yaml`, `**/firewall*.tf`, `**/security_group*.tf`  
**Pass signals:** Kubernetes NetworkPolicy resources with explicit ingress/egress rules; default-deny-all NetworkPolicy present; Terraform security groups with explicit allow rules and implicit deny; WAF rules configured.  
**Fail signals:** No NetworkPolicy resources in a multi-service K8s deployment; security groups with `0.0.0.0/0` ingress on non-public ports; no egress restrictions.  
**Not Assessable:** Repo contains no K8s manifests and no Terraform network resources.

---

### AC-5 — Separation of Duties
**Severity:** P2  
**File patterns:** `.github/workflows/*.yaml`, `.github/CODEOWNERS`, `**/*.tf`, `**/rbac*.yaml`  
**Pass signals:** CODEOWNERS file requiring separate approvers for sensitive paths; GitHub Actions workflows require environment protection rules with required reviewers; IaC pipeline has separate plan and apply stages with approval gate; no single identity has both write and approve permissions.  
**Fail signals:** Single identity or service account can both propose and approve changes; no CODEOWNERS; workflows deploy without approval gate; cluster-admin used for both operational and deployment tasks.  
**Not Assessable:** No CI/CD pipeline files or RBAC manifests found.
**Note:** This control is about whether propose/approve duties are split across distinct roles or identities — not about whether any one role holds broad privilege. A read-only audit role and a separate deploy-approval gate satisfy this control's Pass signals on their own; a different, overly-broad grant elsewhere (AC-6's concern) does not override or negate them. Weigh AC-5 only on its own separation-of-duties evidence, not on RBAC breadth found elsewhere in the same manifests.

---

### AC-6 — Least Privilege
**Severity:** P1  
**File patterns:** `**/clusterrole*.yaml`, `**/role*.yaml`, `**/clusterrolebinding*.yaml`, `**/rolebinding*.yaml`, `**/*.tf`, `**/values*.yaml`  
**Pass signals:** No ClusterRoleBinding to `cluster-admin` for non-system subjects; RBAC roles are namespace-scoped (Role, not ClusterRole) where possible; workload identity used instead of static credentials; IAM roles follow least-privilege (specific actions, not `*`); PIM/JIT referenced for elevated access.  
**Fail signals:** ClusterRoleBinding granting `cluster-admin` to non-system service accounts or users; static credentials (keys, passwords) in Terraform or values files; IAM roles with `"Action": "*"` or equivalent; overly broad namespace-level roles.  
**Not Assessable:** No RBAC or IAM config found.

---

### AC-7 — Unsuccessful Login Attempts
**Severity:** P2  
**File patterns:** `**/*.tf`, `**/ingress*.yaml`, `**/middleware*.yaml`, `**/*.json`, `**/*.yaml`, `**/nginx*.conf`, `**/app*.yaml`  
**Pass signals:** Rate limiting configured on auth endpoints (ingress annotations, middleware, WAF rules); account lockout policy visible in IdP Terraform config (e.g., Azure AD, Entra ID conditional access); exponential backoff in auth code.  
**Fail signals:** No rate limiting on authentication endpoints; no lockout policy in IdP config.  
**Not Assessable:** No auth endpoint config, IdP Terraform, or ingress middleware found.

---

### AC-8 — System Use Notification
**Severity:** P3  
**File patterns:** `**/*.html`, `**/*.yaml`, `**/*.json`, `**/config*.yaml`, `**/login*.html`  
**Pass signals:** Login banner or warning notice configured in app config, IdP settings, or login page; banner includes acceptable use language.  
**Fail signals:** No login banner configured; IdP Terraform has no notification/banner setting.  
**Not Assessable:** No login page, IdP config, or app config files found.

---

### AC-11 — Session Lock
**Severity:** P2  
**File patterns:** `**/*.yaml`, `**/*.json`, `**/*.tf`, `**/session*.yaml`, `**/app*.yaml`  
**Pass signals:** Session timeout configured (idle timeout ≤ 15 minutes for PBMM); IdP Terraform has session lifetime settings; app config specifies inactivity timeout.  
**Fail signals:** Session timeout absent or set to > 15 minutes; no session management config found.  
**Not Assessable:** No session config, IdP settings, or app config found.

---

### AC-12 — Session Termination
**Severity:** P2  
**File patterns:** `**/*.yaml`, `**/*.tf`, `**/*.json`, `**/session*.yaml`  
**Pass signals:** Session revocation on logout configured; IdP Terraform includes token lifetime and refresh token expiry; service mesh session termination on connection close.  
**Fail signals:** No logout/revocation mechanism in config; tokens with no expiry configured.  
**Not Assessable:** No session or token config found.

---

### AC-17 — Remote Access
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/bastion*.tf`, `**/vpn*.tf`, `**/*.yaml`, `.github/workflows/*.yaml`  
**Pass signals:** Remote access only via bastion or VPN (no direct SSH/RDP to workload nodes); SSH keys managed via IaC (no hardcoded keys); MFA enforced for remote access in IdP config; session recording configured.  
**Fail signals:** Direct SSH exposed on workload VMs (port 22 open to 0.0.0.0/0); hardcoded SSH keys in Terraform; no VPN or bastion config.  
**Not Assessable:** No network/VM Terraform or remote access config found.

---

### AC-19 — Access Control for Mobile Devices
**Severity:** P3  
**File patterns:** `**/*.tf`, `**/conditional_access*.tf`, `**/policy*.yaml`  
**Pass signals:** Conditional access policies in Terraform requiring managed/compliant devices; MDM compliance required for access to protected resources.  
**Fail signals:** No device compliance conditions in IdP/conditional access Terraform.  
**Not Assessable:** No IdP Terraform or conditional access policy files found.

---

## AU — Audit and Accountability

### AU-2 — Auditable Events
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/logging*.yaml`, `**/audit*.yaml`, `**/fluent*.yaml`, `**/vector*.yaml`, `**/logstash*.yaml`, `**/app*.yaml`  
**Pass signals:** Audit logging explicitly enabled in platform config (K8s audit policy, cloud audit logs in Terraform); log config captures authentication events, privilege changes, resource creation/deletion, and policy changes; structured logging in app config.  
**Fail signals:** No audit logging config; K8s audit policy absent; cloud provider audit logs not enabled in Terraform; app logs only to stdout with no event classification.  
**Not Assessable:** No logging config, Terraform log resources, or app config found.

---

### AU-3 — Content of Audit Records
**Severity:** P1  
**File patterns:** `**/audit*.yaml`, `**/logging*.yaml`, `**/*.tf`, `**/fluent*.yaml`, `**/app*.yaml`  
**Pass signals:** Log format includes: timestamp, event type, source identity, resource affected, outcome (success/failure); structured JSON log format configured; log fields explicitly enumerated in config.  
**Fail signals:** Log format lacks required fields (no identity field, no outcome field); unstructured text logging; no log schema defined; no audit logging pipeline exists anywhere in the repo (this control is foundational alongside AU-2/AU-12 — see SKILL.md's cascading-NA rule).  
**Not Assessable:** N/A for total absence of a pipeline (that's Fail — see above). Only use Not Assessable when an audit/logging pipeline already exists somewhere in the repo but its record-content format genuinely can't be determined from repo contents (rare).

---

### AU-4 — Audit Storage Capacity
**Severity:** P2  
**File patterns:** `**/*.tf`, `**/storage*.tf`, `**/log*.tf`, `**/retention*.yaml`  
**Pass signals:** Log storage resource provisioned in Terraform with explicit capacity or auto-scale; storage account or log analytics workspace sized for expected log volume; alerts configured for storage capacity thresholds.  
**Fail signals:** No log storage resource in Terraform; log destination not provisioned; no capacity planning evident.  
**Not Assessable:** No storage or log destination Terraform found.

---

### AU-5 — Response to Audit Processing Failures
**Severity:** P2  
**File patterns:** `**/*.tf`, `**/alert*.yaml`, `**/prometheus*.yaml`, `**/monitoring*.yaml`  
**Pass signals:** Alert configured for log pipeline failure or log sink unavailability; system continues operating but alerts on audit failure; metric or health check for log forwarder.  
**Fail signals:** No alerting on log pipeline or audit system failure; log forwarder has no health monitoring.  
**Not Assessable:** No alerting or monitoring config found.

---

### AU-8 — Time Stamps
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/ntp*.yaml`, `**/chrony*.yaml`, `**/daemonset*.yaml`, `**/app*.yaml`  
**Pass signals:** NTP configured for all nodes (NTP server in IaC, chrony/ntpd daemonset); timestamps in UTC; log timestamps include timezone offset; no system clock drift tolerance > 1 second.  
**Fail signals:** No NTP config; system time not synchronized; log timestamps in local time without offset.  
**Not Assessable:** No NTP, clock sync, or timestamp config found.

---

### AU-9 — Protection of Audit Information
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/rbac*.yaml`, `**/storage*.tf`, `**/policy*.yaml`  
**Pass signals:** Log storage RBAC restricts write/delete to log pipeline service account only; log storage has immutability policy (WORM) or retention lock in Terraform; no general workload identity can delete logs.  
**Fail signals:** Log storage accessible with broad IAM permissions; no immutability or retention lock; audit logs can be modified by non-audit identities.  
**Not Assessable:** No log storage Terraform or RBAC for log resources found.

---

### AU-11 — Audit Record Retention
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/retention*.yaml`, `**/policy*.yaml`  
**Pass signals:** Log retention explicitly set ≥ 2 years (PBMM requirement) in Terraform or retention policy; lifecycle policy archives logs after active period; retention policy applied to log storage resource.  
**Fail signals:** Retention period < 2 years or not set (defaults to shorter) **on a log or audit destination**; no lifecycle/retention policy on log storage.  
**Not Assessable:** No log retention config or log-destination storage Terraform found. This control is about retention of *audit/log* data specifically — a retention setting on an unrelated resource (e.g., a database or blob **backup** policy) is not evidence for this control; if the only retention-shaped resource in the repo is a backup policy rather than a log destination, this is Not Assessable, not Fail.

---

### AU-12 — Audit Generation
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/audit*.yaml`, `**/logging*.yaml`, `**/app*.yaml`, `.github/workflows/*.yaml`  
**Pass signals:** Audit logging enabled at platform level (K8s audit policy, cloud provider audit logs); app-level audit logging for security-relevant events (auth, permission changes, data access); CI/CD pipeline logs artefacts and approvals.  
**Fail signals:** K8s audit policy not configured; cloud audit logs disabled in Terraform; app has no audit logging for security events.  
**Not Assessable:** No audit policy, logging config, or app security event logging found.

---

## IA — Identification and Authentication

### IA-2 — Identification and Authentication (Organizational Users)
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/auth*.yaml`, `**/oidc*.yaml`, `**/dex*.yaml`, `**/values*.yaml`  
**Pass signals:** Centralized IdP configured (Entra ID, Okta, Dex in Terraform); MFA enforced via conditional access policy or IdP Terraform; no local user accounts without IdP federation; OIDC/SAML integration present.  
**Fail signals:** Local user accounts with static passwords; no MFA enforcement in IdP Terraform; basic auth enabled; no centralized identity provider configured.  
**Not Assessable:** No IdP Terraform, auth config, or OIDC integration found.

---

### IA-3 — Device Identification and Authentication
**Severity:** P2  
**File patterns:** `**/*.tf`, `**/cert*.yaml`, `**/mtls*.yaml`, `**/istio*.yaml`, `**/linkerd*.yaml`  
**Pass signals:** mTLS configured in service mesh (Istio PeerAuthentication STRICT mode, Linkerd mTLS); device certificates issued via cert-manager or Terraform PKI; no anonymous device connections to internal services.  
**Fail signals:** Service mesh in PERMISSIVE mode (mTLS optional); no device authentication for internal service calls; cert-manager absent.  
**Not Assessable:** No service mesh, PKI, or certificate config found.

---

### IA-4 — Identifier Management
**Severity:** P2  
**File patterns:** `**/*.tf`, `**/serviceaccount*.yaml`, `**/rbac*.yaml`  
**Pass signals:** Service accounts follow a naming convention (not default names); IaC creates named, purpose-specific identities; no shared service accounts across multiple workloads; accounts have descriptions/labels indicating purpose and owner.  
**Fail signals:** Default service accounts used; generic names (`sa`, `app`, `service`) without workload context; multiple workloads sharing one service account.  
**Not Assessable:** No service account or identity Terraform/manifests found.

---

### IA-5 — Authenticator Management
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/secret*.yaml`, `**/vault*.yaml`, `**/keyvault*.tf`, `**/*.yaml`, `**/*.env.example`  
**Pass signals:** Secrets managed via Vault, Azure Key Vault, or AWS Secrets Manager in Terraform; no hardcoded credentials in code or manifests; Kubernetes Secrets referenced from external secrets operator or sealed secrets; credential rotation configured.  
**Fail signals:** Hardcoded passwords, tokens, or keys in any file; Kubernetes Secrets with base64 values in repo (not sealed/external); no secrets management tooling referenced.  
**Not Assessable:** No files matching the patterns above exist in the repo at all, or the matched files are unrelated to credential handling (e.g., the only matches are CI workflow YAML or infrastructure with nothing that touches secrets, tokens, or passwords) — i.e., this system has no visible credential-handling surface to assess. If files exist that clearly *do* handle credentials (app config, Terraform provisioning a database/API, Kubernetes Secrets, etc.) but show no secrets-management construct and no credential-shaped strings, do not default to Not Assessable — escalate to **Fail**, since an application handling credentials with no secrets management story anywhere is itself the gap.

---

### IA-6 — Authenticator Feedback
**Severity:** P3  
**File patterns:** `**/*.html`, `**/*.yaml`, `**/login*.html`, `**/app*.yaml`  
**Pass signals:** Login forms mask password fields; no plaintext password echoed in error messages; IdP config shows no credential exposure in responses.  
**Fail signals:** Password visible in form; error messages include credential values; login page source reveals password in plaintext.  
**Not Assessable:** No login UI or auth form files found.

---

### IA-7 — Cryptographic Module Authentication
**Severity:** P2  
**File patterns:** `**/*.tf`, `**/crypto*.yaml`, `**/tls*.yaml`, `**/fips*.yaml`  
**Pass signals:** FIPS 140-2/140-3 validated crypto modules referenced; TLS 1.2 minimum enforced; no deprecated crypto algorithms (MD5, SHA-1, DES, RC4) in config; crypto library versions in dependency manifests are current.  
**Fail signals:** TLS 1.0 or 1.1 permitted; deprecated algorithms configured; non-FIPS crypto libraries used for sensitive operations.  
**Not Assessable:** No TLS config or crypto library references found.
**Note:** A managed service's SKU or plan tier (e.g., a key vault's "Premium" tier, which merely supports HSM-backed or FIPS-validated keys) is not evidence this control passes. Only credit Pass when the configuration itself shows the FIPS-validated module or TLS version is actually selected/enforced — not that the plan tier makes it available. Absent that, treat as Not Assessable rather than inferring compliance from the tier.

---

### IA-8 — Identification and Authentication (Non-Organizational Users)
**Severity:** P2  
**File patterns:** `**/*.tf`, `**/auth*.yaml`, `**/b2c*.tf`, `**/external*.yaml`  
**Pass signals:** External users authenticated via separate IdP or B2C tenant; no shared accounts between org and external users; external access scoped to specific resources only.  
**Fail signals:** Internal and external users share same identity store with no separation; no distinction between org and non-org user authentication paths.  
**Not Assessable:** No external user auth config found (acceptable if system has no external users — flag as Not Assessable with note).

---

### IA-9 — Service Identification and Authentication
**Severity:** P2  
**File patterns:** `**/istio*.yaml`, `**/linkerd*.yaml`, `**/*.tf`, `**/mtls*.yaml`, `**/serviceaccount*.yaml`  
**Pass signals:** Service-to-service authentication via mTLS (Istio, Linkerd); workload identity used (not static API keys); API gateway enforces service authentication; service accounts with RBAC scoped to specific operations.  
**Fail signals:** Services communicate without authentication; static API keys used for service-to-service calls; no service mesh or API gateway authentication.  
**Not Assessable:** No service mesh, API gateway, or service auth config found.

---

## SC — System and Communications Protection

### SC-2 — Application Partitioning
**Severity:** P1  
**File patterns:** `**/namespace*.yaml`, `**/*.tf`, `**/values*.yaml`, `**/networkpolicy*.yaml`  
**Pass signals:** Separate Kubernetes namespaces for different workloads/environments; NetworkPolicies enforce namespace isolation; no cross-namespace communication without explicit policy; Terraform uses separate resource groups or subscriptions per environment.  
**Fail signals:** All workloads in default namespace; no namespace isolation; no NetworkPolicy; dev and prod in same namespace.  
**Not Assessable:** No namespace or network isolation config found.

---

### SC-5 — Denial of Service Protection
**Severity:** P2  
**File patterns:** `**/ingress*.yaml`, `**/*.tf`, `**/hpa*.yaml`, `**/pdb*.yaml`, `**/limit*.yaml`, `**/quota*.yaml`  
**Pass signals:** Resource quotas and LimitRanges defined per namespace; HorizontalPodAutoscaler configured; PodDisruptionBudget defined; WAF or DDoS protection enabled in Terraform (Azure DDoS, Cloudflare, etc.); rate limiting on ingress.  
**Fail signals:** No resource quotas; no HPA; no DDoS protection in IaC; ingress has no rate limiting.  
**Not Assessable:** No K8s resource config or IaC network protection found.

---

### SC-7 — Boundary Protection
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/networkpolicy*.yaml`, `**/firewall*.tf`, `**/security_group*.tf`, `**/ingress*.yaml`  
**Pass signals:** All external traffic enters via a single ingress/gateway; default-deny NetworkPolicy in every namespace; firewall rules explicit (no 0.0.0.0/0 on non-public ports); private endpoints used for backend services; no direct internet access to workload pods.  
**Fail signals:** Pods with public IPs; security groups allowing 0.0.0.0/0 on non-HTTP ports; no default-deny NetworkPolicy; backend services accessible from internet.  
**Not Assessable:** No network Terraform or NetworkPolicy found.

---

### SC-8 — Transmission Confidentiality and Integrity
**Severity:** P1  
**File patterns:** `**/tls*.yaml`, `**/*.tf`, `**/ingress*.yaml`, `**/istio*.yaml`, `**/cert-manager*.yaml`  
**Pass signals:** TLS enforced on all ingress (cert-manager, managed cert); Istio/Linkerd mTLS STRICT between services; no HTTP-only services; minimum TLS 1.2 configured; HSTS header configured.  
**Fail signals:** HTTP (non-TLS) ingress; mTLS in PERMISSIVE mode; TLS 1.0/1.1 permitted; no cert-manager or managed certificate.  
**Not Assessable:** No TLS or ingress config found.

---

### SC-12 — Cryptographic Key Establishment and Management
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/keyvault*.tf`, `**/kms*.tf`, `**/vault*.yaml`, `**/secret*.tf`  
**Pass signals:** KMS, Azure Key Vault, or HashiCorp Vault used for key management in Terraform; no keys stored in code or config files; key rotation configured; separate keys per environment.  
**Fail signals:** Encryption keys hardcoded in Terraform variables or code; no key management service referenced; single key used across all environments.  
**Not Assessable:** No key management Terraform or Vault config found.

---

### SC-13 — Cryptographic Protection
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/crypto*.yaml`, `**/tls*.yaml`, `**/encryption*.yaml`  
**Pass signals:** Approved algorithms used (AES-256, RSA-2048+, ECDSA P-256+, SHA-256+); no deprecated algorithms (MD5, SHA-1, DES, RC4, 3DES) in config or dependency manifests; FIPS mode referenced where applicable.  
**Fail signals:** Deprecated algorithms in TLS config or crypto library usage; weak key sizes (RSA < 2048); MD5 or SHA-1 for data integrity.  
**Not Assessable:** No crypto config or relevant library references found.

---

### SC-17 — Public Key Infrastructure Certificates
**Severity:** P2  
**File patterns:** `**/cert-manager*.yaml`, `**/*.tf`, `**/certificate*.yaml`, `**/issuer*.yaml`  
**Pass signals:** cert-manager deployed with a trusted Issuer (Let's Encrypt, internal CA, Azure/AWS managed cert); certificates have defined expiry and auto-renewal; no self-signed certs in production ingress; CA trust chain configured.  
**Fail signals:** Self-signed certificates on production ingress; no cert-manager or managed cert; certificates without auto-renewal; expired certificate config.  
**Not Assessable:** No cert-manager, certificate, or PKI config found.

---

### SC-18 — Mobile Code
**Severity:** P3  
**File patterns:** `**/nginx*.conf`, `**/ingress*.yaml`, `**/*.yaml`, `**/headers*.yaml`, `**/*.html`  
**Pass signals:** Content Security Policy (CSP) header configured with `script-src` restricting inline scripts and external origins; no `unsafe-inline` or `unsafe-eval` in CSP; Subresource Integrity (SRI) used for external scripts.  
**Fail signals:** No CSP header; `script-src: *` or `unsafe-inline` present; external scripts loaded without SRI.  
**Not Assessable:** No web server config, ingress annotations, or HTML files found.

---

### SC-23 — Session Authenticity
**Severity:** P2  
**File patterns:** `**/*.yaml`, `**/*.tf`, `**/session*.yaml`, `**/app*.yaml`, `**/*.json`  
**Pass signals:** CSRF protection enabled (token, SameSite cookie, Origin check); session tokens are cryptographically random (not sequential); session cookies have Secure and HttpOnly flags; anti-replay mechanisms in API config.  
**Fail signals:** No CSRF protection; sequential or predictable session IDs; cookies without Secure/HttpOnly; no SameSite attribute.  
**Not Assessable:** No session, cookie, or API auth config found.

---

### SC-28 — Protection of Information at Rest
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/storage*.tf`, `**/disk*.tf`, `**/database*.tf`, `**/pvc*.yaml`  
**Pass signals:** All storage resources in Terraform have encryption enabled (e.g., `encryption_at_rest_enabled = true`, `sse_specification`, `disk_encryption_set_id`); KMS key specified; PersistentVolumeClaims use encrypted StorageClass; database encryption in Terraform.  
**Fail signals:** Storage resources with encryption disabled or not configured; no encryption setting on database Terraform; PVCs using unencrypted StorageClass.  
**Not Assessable:** No storage, database, or PVC Terraform/manifests found.

---

### SC-39 — Process Isolation
**Severity:** P2  
**File patterns:** `**/pod*.yaml`, `**/*.yaml`, `**/deployment*.yaml`, `**/daemonset*.yaml`, `**/values*.yaml`  
**Pass signals:** Container securityContext sets `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`; seccomp profile configured (`RuntimeDefault` or custom); AppArmor or SELinux profile referenced; no `privileged: true` containers.  
**Fail signals:** `privileged: true` in any container; `runAsNonRoot: false` or absent; `allowPrivilegeEscalation: true`; no seccomp profile.  
**Not Assessable:** No pod/container spec or values files found.

---

## CM — Configuration Management

### CM-2 — Baseline Configuration
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/values*.yaml`, `**/helm*.yaml`, `**/*.yaml`  
**Pass signals:** All infrastructure defined in IaC (no manual/undocumented resources); Terraform state referenced; Helm values files define all configurable parameters explicitly; version-pinned images and chart versions.  
**Fail signals:** Undeclared resources (IaC missing large portions of infrastructure); `latest` image tags; unpinned Helm chart versions; no IaC for core infrastructure.  
**Not Assessable:** No IaC or Helm config found.

---

### CM-3 — Configuration Change Control
**Severity:** P1  
**File patterns:** `.github/workflows/*.yaml`, `.github/CODEOWNERS`, `.github/branch_protection*.yaml`, `**/*.tf`  
**Pass signals:** Branch protection rules enforced (require PR, require reviews, no force push to main); CODEOWNERS file for sensitive paths; CI pipeline runs on all PRs; Terraform plan required before apply; change approval workflow visible in CI config.  
**Fail signals:** No branch protection; no CODEOWNERS; direct commits to main allowed; no CI gate on PRs; Terraform apply without plan or approval.  
**Not Assessable:** No CI/CD config or branch protection config found.

---

### CM-5 — Access Restrictions for Change
**Severity:** P1  
**File patterns:** `.github/CODEOWNERS`, `.github/workflows/*.yaml`, `**/*.tf`  
**Pass signals:** CODEOWNERS restricts who can approve changes to IaC, security configs, and pipeline definitions; separate identities for deploying vs. approving; pipeline service account cannot approve its own PRs.  
**Fail signals:** No CODEOWNERS; any team member can merge to main without review; pipeline identity has write access to approve PRs.  
**Not Assessable:** No CODEOWNERS or pipeline config found.

---

### CM-6 — Configuration Settings
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/values*.yaml`, `**/config*.yaml`, `**/hardening*.yaml`  
**Pass signals:** CIS benchmark hardening settings present (kernel params, OS settings in IaC); no insecure defaults (debug mode off, verbose error responses off, default credentials removed); explicit secure defaults in Helm values; no `allowPrivilegeEscalation`, no `hostNetwork`, no `hostPID`.  
**Fail signals:** Debug mode enabled in non-dev config; default passwords or keys present; `hostNetwork: true` or `hostPID: true` without justification; insecure TLS defaults not overridden.  
**Not Assessable:** No config, values, or IaC hardening files found.

---

### CM-7 — Least Functionality
**Severity:** P2  
**File patterns:** `**/Dockerfile`, `**/deployment*.yaml`, `**/*.yaml`, `**/*.tf`  
**Pass signals:** Minimal base images (distroless, alpine, scratch); only required ports exposed; unused services/features disabled in config; no unnecessary packages installed in Dockerfile; capabilities dropped (`drop: ["ALL"]` in securityContext).  
**Fail signals:** Full OS base images (`ubuntu:latest`, `debian:latest`) without justification; all capabilities retained; unnecessary ports exposed; debug tools (curl, wget, bash) in production image.  
**Not Assessable:** No Dockerfile or deployment manifests found.

---

### CM-8 — Information System Component Inventory
**Severity:** P2  
**File patterns:** `**/package.json`, `**/go.mod`, `**/go.sum`, `**/requirements.txt`, `**/Pipfile.lock`, `**/Gemfile.lock`, `**/pom.xml`, `**/build.gradle`, `**/Chart.yaml`, `**/*.tf`  
**Pass signals:** Dependency manifests present and locked (lockfiles exist); SBOM generation configured in CI; all third-party components version-pinned; Helm chart dependencies declared in `Chart.yaml`.  
**Fail signals:** Dependency manifests without lockfiles; no SBOM generation; floating version ranges (`^1.0`, `~2.0`) for security-sensitive dependencies.  
**Not Assessable:** No dependency manifests found.

---

### CM-10 — Software Usage Restrictions
**Severity:** P3  
**File patterns:** `.github/workflows/*.yaml`, `**/license*.yaml`, `**/.licensrc*`, `**/package.json`  
**Pass signals:** License scanning configured in CI (FOSSA, license-checker, trivy license scan); prohibited license types (GPL, AGPL) flagged; license policy file present.  
**Fail signals:** No license scanning in CI; copyleft licenses in dependency tree without documented approval.  
**Not Assessable:** No CI config or license scanning config found.

---

### CM-11 — User-Installed Software
**Severity:** P2  
**File patterns:** `**/admission*.yaml`, `**/kyverno*.yaml`, `**/opa*.yaml`, `**/*.tf`  
**Pass signals:** Admission controller policies restrict container images to approved registries; allowlist of approved image registries configured; no `latest` tags permitted by policy; image signing verification (Cosign, Notary) configured.  
**Fail signals:** No admission controller image restrictions; `latest` tag permitted; images from arbitrary public registries allowed without policy.  
**Not Assessable:** No admission controller or image policy config found.

---

## SI — System and Information Integrity

### SI-2 — Flaw Remediation
**Severity:** P1  
**File patterns:** `.github/workflows/*.yaml`, `**/dependabot.yaml`, `**/renovate.json`, `**/.trivyignore`, `**/trivy*.yaml`  
**Pass signals:** Dependabot or Renovate configured for automated dependency updates; vulnerability scanning (Trivy, Grype, Snyk) in CI pipeline; CI fails on HIGH/CRITICAL CVEs; scan results reviewed (ignore files document accepted risks with justification).  
**Fail signals:** No dependency update automation; no vulnerability scanning in CI; CI passes despite HIGH CVEs; no scan config found.  
**Not Assessable:** No CI config, dependency manifests, or scan config found.

---

### SI-3 — Malicious Code Protection
**Severity:** P1  
**File patterns:** `.github/workflows/*.yaml`, `**/admission*.yaml`, `**/kyverno*.yaml`, `**/*.tf`  
**Pass signals:** Container image scanning in CI before push (Trivy, Grype, Anchore); admission webhook rejects images with critical vulnerabilities; image signing enforced (Cosign); no unapproved base images.  
**Fail signals:** No image scanning in CI; no admission webhook for image vulnerability policy; unsigned images admitted without verification.  
**Not Assessable:** No CI config or admission webhook config found.

---

### SI-4 — Information System Monitoring
**Severity:** P1  
**File patterns:** `**/prometheus*.yaml`, `**/grafana*.yaml`, `**/alert*.yaml`, `**/*.tf`, `**/monitoring*.yaml`  
**Pass signals:** Prometheus rules or equivalent alerting config present; alerts for security-relevant events (auth failures, privilege escalation, resource exhaustion); Grafana dashboards or equivalent defined as code; SIEM integration configured.  
**Fail signals:** No alerting rules; no monitoring config; security events not alerted on; monitoring only covers availability, not security events.  
**Not Assessable:** No monitoring, alerting, or observability config found.

---

### SI-7 — Software, Firmware, and Information Integrity
**Severity:** P2  
**File patterns:** `.github/workflows/*.yaml`, `**/cosign*.yaml`, `**/admission*.yaml`, `**/policy*.yaml`  
**Pass signals:** Image signing configured (Cosign); admission controller verifies signatures before admitting images; CI signs artefacts after build; integrity check on Helm chart or IaC downloads (checksum verification).  
**Fail signals:** No image signing in CI; admission controller does not verify signatures; no artefact integrity verification.  
**Not Assessable:** No CI config, signing config, or admission controller found.

---

### SI-10 — Information Input Validation
**Severity:** P1  
**File patterns:** `**/*.go`, `**/*.py`, `**/*.js`, `**/*.ts`, `**/*.java`, `**/*.cs`, `**/handler*.go`, `**/controller*.go`, `**/routes*.py`  
**Pass signals:** Input validation present at API boundaries (schema validation, type checking, length limits, allowlisting); parameterized queries or ORM used (no string concatenation for SQL); HTML output encoded; file upload validation.  
**Fail signals:** User input passed directly to queries, commands, or templates without sanitization; string concatenation in SQL; no schema validation on API inputs; file uploads accepted without type/size validation.  
**Not Assessable:** No application source code (only IaC/config in repo).

---

### SI-11 — Error Handling
**Severity:** P2  
**File patterns:** `**/*.go`, `**/*.py`, `**/*.js`, `**/*.ts`, `**/*.java`, `**/error*.go`, `**/middleware*.go`  
**Pass signals:** Error responses return generic messages to clients (no stack traces, no internal paths, no database errors); detailed errors logged server-side only; error handling middleware present; HTTP 500 responses do not include exception details.  
**Fail signals:** Stack traces returned to HTTP clients; database error messages exposed in API responses; internal file paths in error messages; no error handling middleware.  
**Not Assessable:** No application source code found.

---

### SI-16 — Memory Protection
**Severity:** P2  
**File patterns:** `**/Dockerfile`, `**/*.yaml`, `**/deployment*.yaml`, `**/*.tf`  
**Pass signals:** Container securityContext includes `readOnlyRootFilesystem: true`; memory limits set on all containers; seccomp profile restricts syscalls; no `SYS_PTRACE` capability; Go/Rust used (memory-safe languages) or equivalent mitigations present.  
**Fail signals:** No memory limits on containers; `readOnlyRootFilesystem: false` or absent; `SYS_PTRACE` capability granted; no seccomp profile.  
**Not Assessable:** No container spec or Dockerfile found.

---

## SA — System and Services Acquisition (partial)

### SA-10 — Developer Configuration Management
**Severity:** P2  
**File patterns:** `.gitignore`, `.gitattributes`, `.github/workflows/*.yaml`, `**/pre-commit*.yaml`  
**Pass signals:** `.gitignore` prevents secrets/credentials from being committed; commit signing configured (GPG or SSH); pre-commit hooks configured (secret scanning, linting); branch naming conventions enforced in CI.  
**Fail signals:** No `.gitignore`; no secret scanning in pre-commit or CI; no commit signing; sensitive file patterns not gitignored.  
**Not Assessable:** No git config or CI workflow files found.

---

### SA-11 — Developer Security Testing
**Severity:** P1  
**File patterns:** `.github/workflows/*.yaml`, `**/sonar*.yaml`, `**/semgrep*.yaml`, `**/bandit*.yaml`, `**/gosec*.yaml`  
**Pass signals:** SAST tool configured in CI (Semgrep, SonarQube, Bandit, gosec, CodeQL); dependency vulnerability scan in CI; DAST configured for pre-production environment; security scan results block merge on HIGH/CRITICAL findings.  
**Fail signals:** No SAST in CI; no dependency scanning; security scans optional (don't block merge); no DAST config.  
**Not Assessable:** No CI config found.

---

### SA-15 — Development Process, Standards, and Tools
**Severity:** P3  
**File patterns:** `.github/workflows/*.yaml`, `**/Makefile`, `**/.pre-commit-config.yaml`, `**/linting*.yaml`  
**Pass signals:** CI pipeline defined and enforced for all branches; linting configured (language-appropriate linter in CI); code review required (branch protection); consistent toolchain versions pinned (`.tool-versions`, `go.toolchain`, `nvmrc`).  
**Fail signals:** No CI pipeline; no linting; inconsistent toolchain versions; no code review enforcement.  
**Not Assessable:** No CI config or build tooling found.

---

### SA-22 — Unsupported System Components
**Severity:** P1  
**File patterns:** `**/package.json`, `**/go.mod`, `**/requirements.txt`, `**/Dockerfile`, `.github/workflows/*.yaml`  
**Pass signals:** All dependencies on supported versions (no EOL runtimes, libraries, or base images); EOL detection in CI (endoflife.date check, Dependabot alerts); base image versions pinned to current supported tags.  
**Fail signals:** EOL Node.js, Python, Go, or Java version in Dockerfile or runtime config; dependencies on archived/unmaintained packages; no EOL detection in CI.  
**Not Assessable:** No dependency manifests or Dockerfile found.

---

## CP — Contingency Planning (partial)

### CP-9 — Information System Backup
**Severity:** P1  
**File patterns:** `**/*.tf`, `**/backup*.tf`, `**/retention*.tf`, `**/storage*.tf`  
**Pass signals:** Backup policy configured in Terraform for all stateful resources (databases, storage accounts, PVCs); backup schedule and retention period explicitly set; backup stored in separate region or account; backup monitoring/alerting configured.  
**Fail signals:** No backup config for stateful resources; backup retention not set; backups in same region/account as primary; no backup monitoring.  
**Not Assessable:** No stateful resource Terraform or backup config found.

---

### CP-10 — Information System Recovery and Reconstitution
**Severity:** P2  
**File patterns:** `**/*.tf`, `**/dr*.yaml`, `**/recovery*.yaml`, `.github/workflows/*.yaml`  
**Pass signals:** Disaster recovery config in Terraform (geo-redundant storage, failover group, cross-region replication); recovery scripts or runbooks exist as code; RTO/RPO targets referenced in config comments or documentation; DR test workflow in CI.  
**Fail signals:** No redundancy or failover in Terraform; no recovery scripts; single-region only with no failover config.  
**Not Assessable:** No DR, redundancy, or failover Terraform found.

---

## RA — Risk Assessment (partial)

### RA-5 — Vulnerability Scanning
**Severity:** P1  
**File patterns:** `.github/workflows/*.yaml`, `**/trivy*.yaml`, `**/grype*.yaml`, `**/.snyk`, `**/checkov*.yaml`  
**Pass signals:** Vulnerability scanner configured in CI (Trivy, Grype, Snyk, Checkov); scans run on every PR and scheduled (e.g., weekly); scan results block merge on HIGH/CRITICAL; IaC scanning configured (Checkov, tfsec); container image scanning configured.  
**Fail signals:** No vulnerability scanner in CI; scans do not block merge; no scheduled scans; IaC not scanned; no image scanning.  
**Not Assessable:** No CI config or scan tooling config found.
