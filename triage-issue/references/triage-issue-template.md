# Triage Issue Template

GitHub issue format for bugs that have been triaged with root cause analysis and a TDD fix plan.

---

## Title Convention

```
[BUG] <verb phrase describing the broken behaviour>
```

**Good:**
- `[BUG] Auth token refresh silently fails when expiry window < 60s`
- `[BUG] CSV export omits rows where currency field is null`
- `[BUG] Pagination resets to page 1 on every re-render`

**Avoid:**
- `[BUG] Login broken` — too vague
- `[BUG] Fix the thing` — describes action, not symptom

---

## Issue Body Template

Copy this template verbatim. Fill every section — leave no section empty.

```markdown
## Problem Description

**Symptom:**
<One or two sentences: what the user observes going wrong>

**Reproduction Steps:**
1. <Step 1>
2. <Step 2>
3. <Observe: ...>

**Environment:**
- OS / Platform: <e.g. macOS 14, Ubuntu 22.04, Node 20>
- Version / Commit: <e.g. v2.3.1 or git sha>
- Relevant config: <env vars, feature flags, or "none">

---

## Root Cause

**Fault location:** `<path/to/file.ts>` — `<FunctionName>()` around line <N>

**Why it happens:**
<2-4 sentences: what the code does, why that produces the symptom, what invariant is violated>

**Supporting evidence:**
- `git log --follow`: <what the history showed>
- Commit `<sha>`: <what this commit changed that matters>
- Code path: `entryPoint()` → `middleLayer()` → `<FaultLocation>()`

---

## Bug Classification

**Type:** [Regression | Missing Feature | Design Flaw]

**Justification:**
<1-2 sentences citing the specific evidence — a bisect result, a missing code path, or the design intent>

---

## TDD Fix Plan

Ordered RED-GREEN cycles. Complete each cycle fully before starting the next.

### Cycle 1 — <short name for what this cycle proves>

**RED — Failing test to write:**
```
<describe the test: what it calls, what it asserts, why it fails now>
```

**Implementation step:**
<What to change in the code to make this test pass — specific, not "fix the bug">

**GREEN state:**
<The test passes. What observable behaviour is now correct?>

---

### Cycle 2 — <short name>

**RED — Failing test to write:**
```
<describe the test>
```

**Implementation step:**
<What to change>

**GREEN state:**
<What is now correct?>

---

<!-- Add Cycle 3, 4, ... as needed -->

---

## Acceptance Criteria

One criterion per TDD cycle's final GREEN state. Each must be independently verifiable.

- [ ] <Criterion matching Cycle 1 GREEN state>
- [ ] <Criterion matching Cycle 2 GREEN state>
<!-- One bullet per cycle -->

---

## Out of Scope

This issue covers **diagnosis only**. The following are explicitly excluded:
- Implementing the fix (tracked separately; assign to tdd skill or engineer)
- Refactoring unrelated code
- Updating documentation (follow-on task after fix is verified)
```

---

## `gh issue create` CLI Example

Use this exact pattern to create the issue from the command line:

```bash
gh issue create \
  --title "[BUG] Auth token refresh silently fails when expiry window < 60s" \
  --body "$(cat <<'EOF'
## Problem Description

**Symptom:**
Token refresh returns HTTP 200 but the new token is identical to the expired one
when the expiry window is under 60 seconds.

**Reproduction Steps:**
1. Set token TTL to 45 seconds in config
2. Wait for token to expire
3. Trigger any authenticated API call
4. Observe: response succeeds but subsequent calls fail with 401

**Environment:**
- Platform: Node 20 / Express 4.18
- Version: v3.1.2
- Config: TOKEN_TTL=45

---

## Root Cause

**Fault location:** `src/auth/refresh.ts` — `refreshToken()` around line 87

**Why it happens:**
The clock-skew guard uses `>` instead of `>=` when comparing expiry to the
current timestamp, so tokens expiring in exactly 60s are treated as still valid
and the cached (expired) token is returned without a network call.

**Supporting evidence:**
- `git bisect` identified commit a3f9c12 (2026-02-14) as the regression point
- Commit a3f9c12 changed the comparison operator from `>=` to `>` in the skew guard
- Code path: `apiClient()` → `getValidToken()` → `refreshToken()`

---

## Bug Classification

**Type:** Regression

**Justification:**
git bisect confirmed that commit a3f9c12 introduced the operator change.
Token refresh functioned correctly in all prior versions.

---

## TDD Fix Plan

### Cycle 1 — Operator fix in clock-skew guard

**RED — Failing test to write:**
\`\`\`
test("refreshToken() issues a new token when expiry window is exactly 60s", () => {
  mockTokenExpiry(Date.now() + 60_000);
  const token = refreshToken();
  expect(token).not.toBe(cachedToken);
});
\`\`\`

**Implementation step:**
Change `expiry > Date.now() + SKEW_BUFFER` to `expiry >= Date.now() + SKEW_BUFFER`
in `refreshToken()` at line 87.

**GREEN state:**
Test passes. Tokens expiring within the 60s window are correctly refreshed.

---

### Cycle 2 — Edge case: expiry window < 60s

**RED — Failing test to write:**
\`\`\`
test("refreshToken() issues a new token when expiry window is 45s", () => {
  mockTokenExpiry(Date.now() + 45_000);
  const token = refreshToken();
  expect(token).not.toBe(cachedToken);
});
\`\`\`

**Implementation step:**
No additional code change needed — covered by Cycle 1 fix. Confirm the test
passes with the same operator fix.

**GREEN state:**
Test passes. All sub-60s expiry windows correctly trigger refresh.

---

## Acceptance Criteria

- [ ] `refreshToken()` issues a new token when expiry window is exactly 60 seconds
- [ ] `refreshToken()` issues a new token when expiry window is less than 60 seconds

---

## Out of Scope

This issue covers **diagnosis only**. Implementation is a separate task.
EOF
)"
```

---

## Field Reference

| Field | Required | Notes |
|---|---|---|
| Title | Yes | `[BUG]` prefix, verb phrase, ≤72 chars |
| Problem Description | Yes | Symptom + steps + environment |
| Root Cause | Yes | Fault location + why + evidence |
| Bug Classification | Yes | One type + justification |
| TDD Fix Plan | Yes | ≥2 RED-GREEN cycles |
| Acceptance Criteria | Yes | One bullet per cycle GREEN state |
| Out of Scope | Yes | Keeps issue boundary explicit |

---

## Labels and Metadata (Optional)

Add these flags to the `gh issue create` command if the repo uses them:

```bash
  --label "bug,needs-triage"          # or "bug,regression" after classification
  --assignee "@me"                    # if you are picking this up immediately
  --milestone "v3.2.0"               # if a milestone is known
  --project "Engineering Backlog"    # if project boards are in use
```
