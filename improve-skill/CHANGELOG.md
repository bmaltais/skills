# improve-skill Optimization Log

## Session 2026-07-04 — Step 2

### Edits Applied
- [op: insert_before, Step 7 Edit principles] Added **Quality audit — writing-great-skills** sub-section: before committing each edit, audit the changed section for no-ops, duplication, sediment, and leading-word opportunities; a passing audit is part of the Step 8 gate. Reasoning: user explicitly instructed to refer to writing-great-skills when improving skills. Support count: 1 explicit instruction.
- [op: delete, Step 9] Removed "What to record each session" numbered list — direct duplication of the format block immediately above it. Support count: 1 (caught by writing-great-skills audit).
- [op: delete, Step 4] Removed "After merging, you should have a compact set of non-overlapping edits." — no-op sentence describing the result rather than instructing an action. Support count: 1 (caught by writing-great-skills audit).

### Deferred Edits (waiting for more signal)
- [P2] Step 9 "How to use history in future sessions" subsection partially duplicates Step 1. Could be deleted from Step 9 entirely since Step 1 already covers it. One occurrence — wait for friction signal.

### Observed Regressions from Previous Edits
- None. Step 1 edit (skillpack sync) worked as intended — sync ran at end of session.

### Meta Notes
- Writing-great-skills audit found real duplication and a no-op on first application — it's a strong quality gate. Encoding it in Step 7 before Gate (Step 8) is the right placement: catch problems before they're accepted.
- Strategy this round: deletion > addition. Removed more than was added (2 deletes, 1 add).
- Convergence: Step 2. Edits are improving skill quality (not just adding coverage). Good signal.

---

## Session 2026-07-04 — Step 1

### Edits Applied
- [op: insert_after, Step 9 longitudinal note] Added **Step 9.5 — Sync Skills (Mandatory)**: run `skillpack sync` after persisting the changelog. Reasoning: user explicitly said "make sure to run skillpack sync after editing the skills — you should take note of that". Without this step, skill edits stay siloed in the local agent directory. Support count: 1 explicit user instruction.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- N/A — first session

### Meta Notes
- First optimization step. Single, clear, mandatory addition. Skill is otherwise solid.
- Convergence: N/A (baseline)

---

## Session 2026-07-04 — Step 1 (improve-skill self-improvement)

### Edits Applied
- [op: replace] Removed `### Quality audit — writing-great-skills` subsection from Step 7 and promoted it to `## Step 7.5 — Quality Audit (Mandatory)` — a first-class numbered step with an explicit `read` tool call on `writing-great-skills/SKILL.md`, exhaustive scope ("every changed section"), and a completion criterion ("Do not proceed to Step 8 until this is done"). Reasoning: in this session the audit was run mentally without loading the doc, causing 4 issues to be missed and requiring a correction round-trip. Root cause: buried subsection framing made it skippable. Support count: 1 user correction ("did you run write-better-skills...?"). 

### Deferred Edits
- (none)

### Observed Regressions from Previous Edits
- N/A — first changelog entry for improve-skill itself.

### Meta Notes
- The skill is well-structured overall. Single failure mode: audit enforcement. One targeted edit, no other friction.
- Convergence: N/A (first entry).

---

## Session 2026-07-05 — Step 1 (self-application)

### Edits Applied
- [op: append] Added note to `implement` skill: "Read every file before editing it. Use `read` to inspect, `edit` to change. If `edit` fails with 'oldText not found', re-read the file first." Reasoning: observed 2× edit failures in this session where oldText didn't match because files weren't read first. Support count: 2 session signals.

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- None.

### Meta Notes
- First time improve-skill was used as a meta-skill in a real session. The `implement` skill was the target of improvement, not improve-skill itself.
- Convergence: N/A (new skill being optimized).

---

## Session 2026-07-05 — Step 1 (self-application, continued)

### Edits Applied
- None (this session only observed failures, no direct edits to improve-skill itself).

### Observed Failure Signals in Session
1. Edit validation failure: tried to edit `repo.go` without reading first → oldText didn't match
2. Edit validation failure: tried to edit `repo.go` PlainClone section without reading exact content → oldText didn't match
3. Syntax error: used `fmt.Errorf` with multiline string in Go → should have used simpler formatting
4. Test failure: `IsTransportAuthError` test failed because `errors.Is` wasn't used → existing codebase pattern

### Root Causes
1. Not reading files before editing (basic practice, should be explicit in skill)
2. Not following existing codebase patterns (errors.Is vs direct comparison)
3. Overcomplicating error formatting (multiline fmt.Errorf is tricky in Go)

### Meta Notes
- The `implement` skill was the target of improvement, not improve-skill.
- The failures were execution issues, not skill gaps in improve-skill.
- Convergence: N/A (new skill being optimized).

---

## Session 2026-07-07 — Step 3

### Edits Applied
- (to azure-devops-work-item-comment, not improve-skill itself)
  [op: append] 3 rows added to "What does NOT work" — `--project` flag, relation-type friendly name, WIQL JSON bare list
  [op: insert] Project-confirmation rule before work item creation

### Deferred Edits (waiting for more signal)
- (none)

### Observed Regressions from Previous Edits
- None.

### Meta Notes
- Session had no improve-skill-specific failures. All 4 edits went to azure-devops-work-item-comment.
- Deferred-edit from Step 2 (Step 9 "How to use history" subsection duplication) still unconfirmed — no friction observed.
- Convergence: improve-skill itself appears stable. Target was a different skill.

## Session 2026-08-11 — Step 4

### Edits Applied
- [op: replace] Step 2 Failure/Success Signal tables (2 markdown tables, 9 rows, 18 lines with illustrative example phrases) compressed into two compact prose lines listing just the signal taxonomy — reasoning: skill-contracts review (check_skill.py) flagged sprawl (205 body lines, over the 150 threshold); the per-signal example quotes ("you forgot", "that's wrong") were no-ops (the model already recognizes what a user correction sounds like without a literal quoted example), while the category names are the load-bearing taxonomy and were preserved verbatim. Support: skill-contracts mechanical check.
- [op: replace] Step 7 'Only patch gaps in the skill — do not duplicate existing content' bullet — dropped the trailing negation clause; it restated the same meaning as the leading positive clause with no new information. Support: writing-great-skills no-op test (self-applied per Step 7.5).
- [op: replace] Step 6 'Group edits by owning skill before applying — this makes Step 6 coherent per-skill' — fixed a stale self-reference bug: grouping happens IN Step 6 to prepare for applying in Step 7, so the sentence should (and now does) say 'makes Step 7 coherent per-skill'.
- [op: replace] Step 5's Learning rate cap + Guardrails 'Multiple skills may need edits' bullet — the 'cap applies per-skill, not globally' clarification lived only in Guardrails (read once, at the end, easy to miss when actually executing Step 5), while Step 5 itself just said 'at most 4 edits per session' with no scope qualifier — genuine ambiguity, not just duplication. Moved the clarification into Step 5's own Learning rate cap sentence (co-location: the caveat belongs with the rule it qualifies) and trimmed the now-redundant Guardrails bullet to a one-line pointer back to Steps 5-6.

### Deferred Edits (waiting for more signal)
- [P2] Sprawl warning is reduced (205 -> 192 body lines) but not eliminated (still over the 150 threshold). Remaining length is a legitimately dense 10-step linear sequence (Steps 1-10 plus 7.5/9.5) with no branches to disclose behind a pointer and no evidence of premature completion to justify a sequence split (the one prior failure needing a split, Step 7.5, was about a buried/skippable subsection, not lookahead-induced rushing, and was already fixed by promoting it to a first-class step). Revisit only if a future session shows the length itself causing a miss.

### Observed Regressions from Previous Edits
- (none) — this is the first skill-contracts-driven review of improve-skill; no prior edit from this angle to regress.

### Meta Notes
- First review driven by an external contract (skill-contracts) rather than an observed in-session failure, mirroring the same review just done on eslz-module-upgrade in the same session. The mechanical check caught one thing (sprawl); the rest came from applying the contract's own vocabulary (single source of truth, co-location, no-op) by hand, which also surfaced one genuine bug (Step 6's stale self-reference) unrelated to either contract or friction signals — worth remembering that a contract review is also just a good occasion for a plain proofread.
- Convergence: this skill was already well-aligned with skill-contracts before this review (it already has 'The artifact', 'Preconditions', and a strong Step 8 Gate with a command-based postcondition) — unsurprising since both skills share an author/lineage. Diminishing returns expected on future contract-driven passes; friction-driven passes (the skill's own normal mode) remain the primary lever.
