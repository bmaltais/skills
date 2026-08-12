---
name: improve-skill
description: Use when a session showed friction — user corrections, tool failures, repeated attempts, skipped steps — and you want to patch the skill(s) responsible so it doesn't recur.
argument-hint: "What specific areas or issues should the skill be improved in to make it more effective?"
---

# Improve Skill

Systematically optimize skills using real session signals — treating the skill document as trainable state and the session as a rollout trajectory.

> Inspired by SkillOpt (Microsoft): the skill document is the "weights" of a frozen agent.
> Session outcomes are the loss signal. This skill performs one optimization step.

## The artifact

One optimization step produces: a small set of applied edit patches (each an `op`/`target`/`content`/`reasoning`/`support_count`) to the owning skill's `SKILL.md`, and one dated entry in that skill's `CHANGELOG.md` recording what changed and why. Derived only from signals actually observed this session — a session with no friction yields zero edits, never invented ones. An edit is acceptable only if it's generalizable (no session-specific values baked in), fixes a root cause rather than a symptom, and survives the Gate (Step 8) unchanged.

## Preconditions

- **The session shows real friction** — a correction, a tool failure, a repeated attempt, a skipped step. If Step 2's scan turns up none, stop and report that; do not invent edits to look productive.
- **Each edit resolves to a real, readable skill file.** Step 7 reads the owning skill before touching it — if Step 6 can't point at an actual `SKILL.md`, that's the halt condition, not a cue to guess.

## Step 1 — Load History (Resume State)

Before analyzing the session, check for existing optimization history:

1. For each skill that was active in the session, check `CHANGELOG.md` in that skill's own directory (sibling to its `SKILL.md`)
2. If it exists, load:
   - **Deferred edits** — items waiting for confirming signal
   - **Recent regressions** — edits that hurt previous sessions
   - **Meta notes** — strategy preferences (e.g., "prefer deletion")
   - **Step count** — to continue numbering

Use this history downstream: in Step 3 (Reflect), promote a deferred edit to P0/P1 if this session gave confirming signal, and propose a revert or revision if a past edit is now a known regression; in Step 5 (Select), don't re-propose an edit already applied or explicitly rejected; in Step 8 (Gate), check the change against known regressions. If no history exists, this is step 1 for that skill.

## Step 2 — Rollout Analysis (Forward Pass)

Scan the full session as a trajectory. Extract **every** observable outcome:

**Failure signals (high priority):** user correction, tool failure, wrong output (incorrect code, missed requirement, hallucinated API), repeated attempt (same operation tried 2+ times before succeeding), wasted round-trip (a clarifying question that revealed an unspoken requirement).

**Success signals (lower priority, still valuable):** clean first-try execution, user praise, efficient pattern (solved in fewer steps than expected), novel technique worth encoding for reuse.

List **all** signals. Don't filter yet. Note the count of each pattern (support count).

## Step 3 — Reflect (Backward Pass)

For each failure signal, perform root-cause analysis:

1. **What went wrong?** (the symptom)
2. **Why?** (the root cause — trace back to what the skill said or failed to say)
3. **What skill change would have prevented it?** (the proposed edit)
4. **Is this pattern systematic or a one-off?** (support count > 1 = systematic)

For each success signal:
1. **What worked?** (the pattern)
2. **Is it already in the skill?** (if yes, skip)
3. **Would encoding it help future sessions?** (if no, skip)

Produce structured **edit patches** — each with:
- `op`: append | insert_after | replace | delete
- `target`: what section/text it affects
- `content`: the new text
- `reasoning`: why this edit addresses the observed signal
- `support_count`: how many session signals support this edit

## Step 4 — Aggregate (Merge Similar Patches)

Group proposed edits that address the same underlying issue. Merge them:

- Combine edits that would affect the same section into one coherent change
- If two edits conflict, keep the one with higher support count
- Remove redundant edits (one already implies the other)

## Step 5 — Select (Gradient Clipping / Learning Rate)

Rank merged edits by **impact × frequency × confidence**:

| Priority | Criteria | Action |
|----------|----------|--------|
| P0 | High support count + clear root cause + reproducible | Apply immediately |
| P1 | Moderate support + clear cause | Apply if change is small |
| P2 | Single occurrence + clear cause | Apply only if trivial |
| P3 | Speculative / low confidence | Skip — wait for more signal |

**Learning rate cap:** Apply at most **4 edits** per session, per owning skill — a session touching 3 skills may apply up to 4 edits to each, not 4 total. This prevents overshooting — too many changes at once makes it impossible to attribute future improvements or regressions to specific edits.

If you have more than 4 worthy edits, select the top 4 by priority. Note the deferred ones for future sessions.

Report the ranked list before implementing.

## Step 6 — Identify Owning Skill(s)

For each selected edit, name the skill that governs the broken behavior.

- A single session may exercise multiple skills — attribute each edit to its owning skill independently
- If the session clearly points to a specific skill, use it
- If multiple skills overlap, pick the most specific one
- If no skill owns it, check your installed skills directories for candidates
- If unclear, ask the user before proceeding

Group edits by owning skill before applying — this makes Step 7 coherent per-skill.

## Step 7 — Update (Apply Patches)

Read the owning skill file before editing it. Apply the minimum change that addresses the root cause:

- **Add a mandatory step** for skipped workflow items
- **Add a guard / check** for reliability issues
- **Add a concrete example** for accuracy issues
- **Add a decision rule** for coverage gaps
- **Delete or replace** rules that actively cause errors

### Edit principles (from SkillOpt):
- Edits must be **generalizable** — do not hardcode session-specific values
- Only patch **gaps** in the skill
- Prefer **reinforcing existing sections** over adding new top-level sections
- Keep edits **concise** — one clear rule per edit, not paragraphs

### Beyond SKILL.md — supporting artifacts

When a skill involves multi-step workflows, also consider:

- **Helper scripts** (`scripts/` subdirectory) — when steps are repeated, error-prone, or need cleanup
- **Reference files** — when the skill relies on external API specifics or repeated lookups

When adding scripts: make them executable, self-documenting, and reference them from the skill.

## Step 7.5 — Quality Audit (Mandatory)

Use `read` on the `writing-great-skills` skill's `SKILL.md` (in your installed skills directory), then audit **every changed section** against all four criteria:

- **No-ops** — does this line change behaviour vs. the model's default? Delete if not.
- **Duplication** — is this meaning already present elsewhere in the skill? Collapse to one source.
- **Sediment** — does this line still bear on what the skill does? Delete if not.
- **Leading word opportunity** — can a repeated phrase collapse into one pretrained token?

Revise any section that fails. **Completion criterion: every changed section passes all four criteria.** Do not proceed to Step 8 until this is done.

## Step 8 — Gate (Validate)

After editing, evaluate the change:

1. **Contract check (postcondition):** if the `skill-contracts` skill is installed, run its checker against the edited skill's directory: `python3 <path-to-skill-contracts>/scripts/check_skill.py <edited-skill-dir>`. A nonzero exit is a failing edit — fix before accepting, not after.
2. Re-read the changed section of the skill file
3. **Regression check:** Would this change break any of the session's *successes*?
4. **Effectiveness check:** Would this change have prevented the observed failure?
5. **Generalization check:** Does this change apply beyond this specific session?

Accept only if the contract check exits 0 **and** all three judgment checks pass. If any fail → revise or reject the edit.

## Step 9 — Persist History (Training Log)

Maintain a per-skill changelog at `CHANGELOG.md` in that skill's own directory — the training log that enables longitudinal comparison across sessions. Formatting and step-numbering are fully mechanical, so a script owns them instead of prose: build the entry (edits applied, deferred edits, regressions, meta notes) and pipe it as JSON to the script co-located with this skill:

```bash
echo '{"skill_name": "<skill-name>", "edits_applied": [...], "deferred": [...], "regressions": [...], "meta_notes": [...]}' \
  | python3 <this-skill-dir>/scripts/append_changelog.py <owning-skill-dir>
```

It creates `CHANGELOG.md` if absent, computes the next Step number from existing entries, and appends the new one — you only ever supply the judgment content, never the date or step count.

### Longitudinal comparison (Slow Update):
When history has 3+ entries for a skill, briefly assess:
- Is the skill **converging** (fewer failures per session) or **diverging** (new failure modes)?
- Are edits **sticking** (still relevant) or **churning** (getting reverted/replaced)?
- Should the learning rate decrease (skill is mature) or increase (skill is clearly undertrained)?

Add a one-line convergence note to the session entry.

## Step 9.5 — Sync Skills (Mandatory)

After persisting the changelog, push all edited skills to remote:

```bash
skillpack sync
```

This ensures edits are not siloed in the local agent directory. Run after every improve-skill session, even if only one skill was changed. A nonzero exit means the edits are still local only — surface the error to the user instead of reporting the session complete.

## Step 10 — Meta-Skill Memory (Optional)

If this is not the first time improving this skill (check CHANGELOG.md), briefly note:

- What changed this time vs. last time
- Whether previous improvements helped or hurt (if observable from this session)
- Any high-level strategy shift (e.g., "this skill keeps getting too verbose, prefer deletion over addition")

This goes into the CHANGELOG.md meta notes section — it serves as cross-session optimizer memory for future improvement cycles.

## Guardrails

- **Fix the root cause, not the symptom.** If "plan.md was not updated" is the symptom, the root cause is "no step requires it" — add the step.
- **Multiple skills may need edits, each capped independently** — see Steps 5-6.
- **Respect protected sections.** If a skill has sections marked as managed by another process, do not edit them.
- **If the user passed a specific skill or instruction**, treat it as the Step 5 answer and skip to Step 6.
