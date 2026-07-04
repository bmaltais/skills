---
name: improve-skill
description: Review the current session and suggest improvements based on issues observed during the session.
argument-hint: "What specific areas or issues should the skill be improved in to make it more effective?"
---

# Improve Skill

Systematically optimize skills using real session signals — treating the skill document as trainable state and the session as a rollout trajectory.

> Inspired by SkillOpt (Microsoft): the skill document is the "weights" of a frozen agent.
> Session outcomes are the loss signal. This skill performs one optimization step.

## Step 1 — Load History (Resume State)

Before analyzing the session, check for existing optimization history:

1. For each skill that was active in the session, check `~/.pi/agent/skills/<skill-name>/CHANGELOG.md`
2. If it exists, load:
   - **Deferred edits** — items waiting for confirming signal
   - **Recent regressions** — edits that hurt previous sessions
   - **Meta notes** — strategy preferences (e.g., "prefer deletion")
   - **Step count** — to continue numbering

This context feeds into the Reflect and Select stages. If no history exists, this is step 1 for that skill.

## Step 2 — Rollout Analysis (Forward Pass)

Scan the full session as a trajectory. Extract **every** observable outcome:

### Failure Signals (high priority)
| Signal | Example |
|--------|---------|
| User correction | "you forgot", "that's wrong", "this keeps happening" |
| Tool failure | failed replacement, build error, test failure that required repair |
| Wrong output | incorrect code, missed requirement, hallucinated API |
| Repeated attempt | same operation tried 2+ times before succeeding |
| Wasted round-trip | clarifying question that revealed an unspoken requirement |

### Success Signals (lower priority, but still valuable)
| Signal | Example |
|--------|---------|
| Clean first-try execution | tool call succeeded, test passed immediately |
| User praise | "perfect", "exactly what I needed" |
| Efficient pattern | solved in fewer steps than expected |
| Novel technique | approach worth encoding for reuse |

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

After merging, you should have a compact set of non-overlapping edits.

## Step 5 — Select (Gradient Clipping / Learning Rate)

Rank merged edits by **impact × frequency × confidence**:

| Priority | Criteria | Action |
|----------|----------|--------|
| P0 | High support count + clear root cause + reproducible | Apply immediately |
| P1 | Moderate support + clear cause | Apply if change is small |
| P2 | Single occurrence + clear cause | Apply only if trivial |
| P3 | Speculative / low confidence | Skip — wait for more signal |

**Learning rate cap:** Apply at most **4 edits** per session. This prevents overshooting — too many changes at once makes it impossible to attribute future improvements or regressions to specific edits.

If you have more than 4 worthy edits, select the top 4 by priority. Note the deferred ones for future sessions.

Report the ranked list before implementing.

## Step 6 — Identify Owning Skill(s)

For each selected edit, name the skill that governs the broken behavior.

- A single session may exercise multiple skills — attribute each edit to its owning skill independently
- If the session clearly points to a specific skill, use it
- If multiple skills overlap, pick the most specific one
- If no skill owns it, check `~/.pi/agent/skills/` for candidates
- If unclear, ask the user before proceeding

Group edits by owning skill before applying — this makes Step 6 coherent per-skill.

## Step 7 — Update (Apply Patches)

Read the owning skill file before editing it. Apply the minimum change that addresses the root cause:

- **Add a mandatory step** for skipped workflow items
- **Add a guard / check** for reliability issues
- **Add a concrete example** for accuracy issues
- **Add a decision rule** for coverage gaps
- **Delete or replace** rules that actively cause errors

### Edit principles (from SkillOpt):
- Edits must be **generalizable** — do not hardcode session-specific values
- Only patch **gaps** in the skill — do not duplicate existing content
- Prefer **reinforcing existing sections** over adding new top-level sections
- Keep edits **concise** — one clear rule per edit, not paragraphs

### Beyond SKILL.md — supporting artifacts

When a skill involves multi-step workflows, also consider:

- **Helper scripts** (`scripts/` subdirectory) — when steps are repeated, error-prone, or need cleanup
- **Reference files** — when the skill relies on external API specifics or repeated lookups

When adding scripts: make them executable, self-documenting, and reference them from the skill.

## Step 8 — Gate (Validate)

After editing, evaluate the change:

1. Re-read the changed section of the skill file
2. **Regression check:** Would this change break any of the session's *successes*?
3. **Effectiveness check:** Would this change have prevented the observed failure?
4. **Generalization check:** Does this change apply beyond this specific session?

If all three pass → accept. If any fail → revise or reject the edit.

## Step 9 — Persist History (Training Log)

Maintain a per-skill changelog at `~/.pi/agent/skills/<skill-name>/CHANGELOG.md`. This is the training log — it enables longitudinal comparison across sessions.

### Format

```markdown
# <skill-name> Optimization Log

## Session <date> — Step <N>

### Edits Applied
- [op: append] Added guard for X — reasoning: observed 3× tool failure
- [op: replace] Changed rule Y — reasoning: user corrected output twice

### Deferred Edits (waiting for more signal)
- [P3] Consider adding Z — only 1 occurrence, low confidence

### Observed Regressions from Previous Edits
- (none) / Edit from step N-1 ("added mandatory check") caused slowdown in unrelated flow

### Meta Notes
- Strategy: skill was getting verbose, preferred deletion over addition this round
```

### What to record each session:
1. **Date and step number** (monotonically increasing)
2. **Edits applied** — op, target, reasoning, support count
3. **Deferred edits** — P3 items parked for future signal
4. **Regression observations** — if a previous edit visibly hurt this session, note it
5. **Meta notes** — optimizer strategy shifts

### How to use history in future sessions:
- **Before Step 3 (Reflect):** Read CHANGELOG.md to load context:
  - Check deferred edits — did this session provide confirming signal? If yes, promote to P0/P1
  - Check for regressions — if a previous edit is causing harm, propose a revert or revision
  - Check meta notes — carry forward strategy preferences
- **During Step 5 (Select):** Avoid re-proposing edits that were already applied or explicitly rejected
- **During Step 8 (Gate):** Compare against known regressions from history

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

This ensures edits are not siloed in the local agent directory. Run after every improve-skill session, even if only one skill was changed.

## Step 10 — Meta-Skill Memory (Optional)

If this is not the first time improving this skill (check CHANGELOG.md), briefly note:

- What changed this time vs. last time
- Whether previous improvements helped or hurt (if observable from this session)
- Any high-level strategy shift (e.g., "this skill keeps getting too verbose, prefer deletion over addition")

This goes into the CHANGELOG.md meta notes section — it serves as cross-session optimizer memory for future improvement cycles.

## Guardrails

- **Fix the root cause, not the symptom.** If "plan.md was not updated" is the symptom, the root cause is "no step requires it" — add the step.
- **Multiple skills may need edits.** A session can invoke several skills — analyze each skill's contribution independently and apply edits to each owning skill. Keep edits per-skill small (learning rate cap applies per skill, not globally).
- **Quality over quantity.** If the session produced no genuine friction — no user corrections, no tool failures, no re-reads, no skipped steps — report that clearly and stop. Do not invent improvements to appear productive.
- **Respect protected sections.** If a skill has sections marked as managed by another process, do not edit them.
- **If the user passed a specific skill or instruction**, treat it as the Step 5 answer and skip to Step 6.
