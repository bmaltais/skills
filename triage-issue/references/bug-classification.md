# Bug Classification Reference

Three mutually exclusive bug types. Classify exactly one; justify with evidence.

---

## 1. Regression

> "It worked before and something broke it."

### Detection Signals
- User says "this used to work", "worked in version X", "broke after update"
- A passing test now fails with no change to the test
- `git log --follow` shows the file changed recently near the failure date
- `git bisect` identifies a specific commit as the breakage point
- CI history shows green → red transition without spec changes

### Confirming Questions
- "When did it last work correctly?"
- "Did anything change recently — dependency update, config, deploy?"
- "Is there a version or commit where this still works?"

### Git Commands
```bash
# Trace full history of a specific file (including renames)
git log --follow -p -- path/to/file.ts

# Find commits that mention the symptom or affected function
git log --grep="<keyword>" --oneline

# Binary-search for the breaking commit
git bisect start
git bisect bad                    # current commit is broken
git bisect good <last-known-good-sha>
# Git checks out midpoints; run your repro, mark good/bad
git bisect good   # or: git bisect bad
# Repeat until bisect identifies the culprit commit
git bisect reset  # restore HEAD when done

# Inspect the identified commit
git show <sha> --stat
```

### Confirmation Criteria
Classification is **regression** when:
- `git bisect` or `git log` identifies a specific commit introducing the failure, AND
- The behavior was previously correct (test, docs, or user testimony confirms prior state)

---

## 2. Missing Feature

> "The spec says it should work, but it never did."

### Detection Signals
- Behaviour has never worked in any version (`git log` shows no prior implementation)
- Feature is documented or spec'd but code path does not exist
- No tests were ever written for this path (coverage gap)
- User says "I expected X to work" with no "it used to" qualifier

### Confirming Questions
- "Has this ever worked in any version of the system?"
- "Is this behaviour documented or specified anywhere?"
- "Is there an existing test that covers this path?"

### Git Commands
```bash
# Check whether any code for this feature was ever committed
git log --all --grep="<feature name>" --oneline

# Search across full history for a function or keyword
git log -S "<function_name>" --oneline   # pickaxe: commits that added/removed this string

# Confirm no prior implementation exists
git log --all --follow -- path/to/expected/module.ts
```

### Confirmation Criteria
Classification is **missing feature** when:
- No prior implementation found in git history, AND
- A spec, README, or design doc describes the expected behaviour, AND
- `git log -S` finds no prior attempt at implementation

---

## 3. Design Flaw

> "It works exactly as designed, but the design is wrong."

### Detection Signals
- Code behaves consistently but the behaviour itself is harmful or incorrect
- Tests pass but test the wrong thing
- The feature "works" but causes downstream failures (data corruption, cascading errors)
- User says "it does X, but it should do Y" and X is clearly intentional in the code
- Architecture review reveals a structural decision that cannot be patched locally

### Confirming Questions
- "Is the code doing exactly what someone intended?"
- "Would a fix require changing the interface contract, not just the implementation?"
- "Would patching this symptom just move the problem somewhere else?"

### Git Commands
```bash
# Find the original design decision — look at the commit that introduced the structure
git log --follow -p -- path/to/core/file.ts | head -200

# Check if the design was discussed in commit messages
git log --grep="design\|architect\|decision\|chose" --oneline

# Look for the point the abstraction was introduced
git log -S "<key_abstraction_name>" --oneline
```

### Confirmation Criteria
Classification is **design flaw** when:
- Code behaves consistently with its implementation intent (not a bug in execution), AND
- The intended behaviour itself is incorrect or harmful, AND
- Fixing it requires changing an interface, contract, or core assumption — not just patching a line

---

## Classification Decision Tree

```
Is there git evidence it worked before?
├── YES → REGRESSION (confirm with bisect)
└── NO → Was it ever implemented?
         ├── NO  → MISSING FEATURE (confirm with git log -S)
         └── YES → Does it work as intended, but the intent is wrong?
                   ├── YES → DESIGN FLAW
                   └── NO  → Re-examine: likely REGRESSION with subtle evidence
```

---

## Output Format

Always include in the GitHub issue:

```
**Bug Classification:** [Regression | Missing Feature | Design Flaw]

**Justification:** <1-2 sentences citing specific git evidence or code path observation>

**Key Evidence:**
- `git bisect` identified commit abc1234 as the regression point
- Function `handleAuth()` has no implementation path for expired tokens (missing feature)
- `parseDate()` intentionally truncates timezone (design flaw — confirmed in commit ef56789)
```
