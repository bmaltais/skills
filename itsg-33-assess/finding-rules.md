# Finding Rules

Reference for `itsg-33-assess` Step 4c (Reason). Every family subagent applies these rules
after reading a control's matched files and its **Pass signals** / **Fail signals** entries in
[`controls.md`](controls.md). If the control has a **Note** field in `controls.md`, read it
first — it exists specifically to disambiguate the control from a commonly-conflated sibling
control, and it takes precedence over the rules below whenever the two would otherwise
conflict.

- **Signal lists are alternatives, not a checklist.** Pass signals and Fail signals are each
  an *OR* list of examples, not a set of requirements that must all be satisfied. One clear,
  concrete positive signal is enough for Pass; you do not need every listed pass signal to be
  present. Likewise, one clear negative signal is enough for Fail.
- **Fail requires a concrete artifact, not just an unverified gap.** Only report Fail when
  you observe a specific anti-pattern in a matched file (e.g., a `cluster-admin` binding, a
  hardcoded credential, unsanitized query concatenation), or a narrow case where this control
  exists specifically to assess whether a foundational capability is present at all and that
  capability is entirely absent (see the cascading rule below for how to tell foundational
  controls apart from the dependent controls that build on them — this is a narrow exception,
  not a general license to fail any missing nice-to-have). Do not report Fail merely because a
  *particular* pass signal can't be verified from repo contents alone (e.g., GitHub
  branch-protection settings, an IdP's MFA policy, image-signing enforcement) when nothing in
  the repo actively contradicts it — that is a **Not Assessable**, not a Fail.
- **Pass equally requires a concrete positive artifact, not just the absence of a Fail
  pattern.** The inverse of the rule above holds just as strongly: don't award Pass merely
  because you didn't find the specific anti-pattern from the Fail-signal list. If the
  capability this control assesses was never actually implemented anywhere in the repo — no
  bastion/VPN config, no monitoring/alerting config, and so on — that is **Not Assessable**,
  not Pass, even though nothing looks actively broken. Reserve Pass for when you can point to a
  specific artifact that positively implements what the control asks for.
- **A satisfied core Pass signal outweighs an unmet optional item on the Fail-signal list.**
  Fail-signal lists often mix two different things: "the practice doesn't exist at all" and
  "an additional layer or enhancement of an already-working practice is missing" (e.g., a
  scanner that runs on every PR and blocks merge, but doesn't *also* run on a schedule or
  *also* cover IaC specifically). When a clear, concrete Pass signal is satisfied by the core
  mechanism, don't let an unmet optional completeness item flip the finding to Fail — only do
  that when the Fail-list item describes an active defect in the *same* mechanism you were
  about to credit (e.g., the scanner exists but doesn't block merge, or runs with
  `continue-on-error: true`). Ask whether the missing item is a defect in what's there, or an
  unimplemented extra layer on top of something that already works.
- **An entirely unattempted specialized practice is Not Assessable, not Fail.** Some controls
  assess a specialized or supplementary practice (e.g., software license scanning, image
  signing, pre-commit secret scanning) that plenty of otherwise well-secured systems simply
  haven't adopted, as distinct from a baseline capability every system in scope is expected to
  have. If the repo shows no attempt at the practice at all — not even a partial or
  misconfigured one — prefer Not Assessable over Fail. Reserve Fail for this class of control
  when there's a broken or half-implemented attempt (e.g., an admission controller present but
  not enforcing any policy, or a license-scan step that exists but is disabled).
- **A broad pattern match (e.g. `**/*.tf`) is not itself a positive or negative signal.**
  Many controls list catch-all patterns like `**/*.tf` so the relevant resource can be found
  if present. Matching a file under that pattern does not, on its own, satisfy Step 4b's
  "files matched" gate for *this control's subject matter* — read the file's content and ask
  whether it actually relates to what this control assesses. A Terraform file that has nothing
  to do with logging does not make AU-4 Fail; it means the log-storage resource AU-4 cares
  about was never introduced (see the cascading rule below).
- **Cascading Not Assessable within a family.** Within a control family, some controls assess
  whether a foundational capability exists *at all*, while others assess a property of a
  pipeline that presupposes that capability exists. In the AU family specifically: AU-2
  (auditable events), AU-3 (audit record content), and AU-12 (audit generation) together
  assess whether any audit logging exists at all — if no audit logging pipeline is configured
  anywhere in the repo (no K8s audit policy, no cloud audit log resource, no structured
  app-level security event logging), mark all three **Fail**, since "there is no audit trail at
  all" is itself the finding for each of them. AU-4 (storage capacity), AU-5 (failure
  alerting), AU-8 (time stamps), AU-9 (protection of audit info), and AU-11 (retention) assess
  *properties* of that pipeline — if the foundational pipeline is entirely absent, mark these
  **Not Assessable**, since there is nothing to evaluate the property of. Do not fail a
  dependent control for a property of something that doesn't exist, and do not excuse a
  foundational control to Not Assessable just because no dedicated logging file type is
  present. The same foundational-vs-dependent shape can recur in other families — ask whether
  the control is asking "does this capability exist" (foundational) or "how good/complete is
  the existing thing" (dependent) before assuming absence of one implies the same verdict for
  the other.
- **Don't re-litigate one control's finding inside another — and expect legitimate
  disagreement between controls that share evidence.** If an issue is already the precise
  subject of a more specific control (e.g., overly-broad IAM/RBAC privilege is AC-6's
  concern), don't also fail a different control (e.g., AC-2, which is about whether accounts
  are explicitly defined and tokens aren't auto-mounted) for the same underlying fact unless
  that control's own signals are about something distinct. At the same time, two controls
  reading the *same* files can correctly land on different findings, because they assess
  different properties of the same evidence: a namespace-scoped Role with an explicit,
  non-wildcard verb list can make an access-enforcement-mechanism control Pass (the mechanism
  exists and is granular) even while a separate, overly-broad cluster-wide binding elsewhere in
  the same manifest set makes a least-privilege control Fail (a grant elsewhere violates
  minimality) — mechanism existence/granularity and privilege minimality are distinct
  questions, and are not required to agree. Read what each control is actually named and scoped
  to assess, not just whether a fail-signal keyword string appears in a matched file.
- **Don't confuse artifacts with similar names.** A resource that shares a keyword with a
  control's subject (e.g., a *backup* retention period vs. an *audit log* retention period) is
  only evidence for that control if it is actually the same kind of artifact — check what the
  resource actually stores before citing it.
- **Don't infer compliance transitively from an adjacent service's tier or feature flag.** A
  managed service's SKU, plan level, or an available-but-unconfigured feature (e.g., a key
  vault's "Premium" tier that *supports* HSM-backed or FIPS-validated keys) is not itself
  evidence that the control's actual mechanism is provisioned or in use for this system. Only
  credit Pass when the configuration you read shows the mechanism itself is enabled and applied
  — e.g., a resource or setting that actually selects the FIPS-validated key type, not merely a
  tier capable of offering it. The same caution applies to any control where the pass signal is
  a specific configured behavior: a plan that could support it is not the same as evidence it is
  turned on.
