# pr-reviewer Optimization Log

## Session 2026-06-08 — Step 1

This is the first optimization step for the pr-reviewer skill (no prior CHANGELOG existed).

### Session Context
- Active skill under analysis: pr-reviewer (triggered via `/pr-reviewer pr 250` + follow-up "make sure to provide review as comment(s) in the PR").
- The rollout exercised the full workflow: diff acquisition (web_fetch + redirect handling), context reading (read_file + git show), analysis against focus areas, exact structured output generation (Summary + 🔴 + 🟡 + ✅), verification (go test on changed packages), and the posting flow.
- improve-skill was invoked by the user on the resulting session signals to perform this optimization pass.

### Rollout Signals Extracted
**Failure signals (high priority):**
- Primary recommended posting path failed: `python3 .../post_review.py --pr-url ... --review-file /tmp/... --mode comment --confirm` raised gh error "no pull requests found for branch 'bmaltais/model-shelf#250'" and exited non-zero. Required mid-flow diagnosis (reading the py + sh), then fallback to `source .../github.sh && post_pr_comment` (which succeeded). (support_count: 1, high impact)
- Documentation/implementation mismatch: SKILL.md, scripts/README.md, and comments repeatedly claim the python helper is "Primary posting tool (recommended)", "Uses reliable `--repo` gh syntax so it works from any working directory", "The helpers are now more robust", "Uses `gh pr ... --repo OWNER/REPO N`". The top-level comment code path did not implement it (while get_pr_info, shell post_pr_comment, and inline review path did). (support_count: 1, affects user trust and "always prefer the helpers" rule)
- Extra round-trips and context switches: user explicit posting request + AI had to leave pure Copilot Reviewer persona temporarily to debug the helper and orchestrate the shell function directly instead of the documented "Recommended Posting Flow" just working end-to-end.

**Success signals:**
- Review generation, strict persona adherence, output format, file:line references, focus area prioritization, and test verification all succeeded cleanly on first try with no corrections needed.
- python --dry-run path worked perfectly (parsed 4 findings, produced correct preview).
- The shell helper (github.sh) was already correctly using the robust form + had good comments explaining why.
- Final desired outcome (real top-level comment posted with full review content) was achieved.
- Parser in post_review.py correctly handled the long structured review containing code blocks.

### Edits Applied (P0 only; learning rate respected)
- [op: replace] `post_top_level_comment` implementation in `scripts/post_review.py` (both ~/.grok/... and ~/.pi/agent/... copies for consistency)
  - Changed the gh invocation from `["pr", "comment", f"{owner}/{repo}#{number}", "--body", body]` (fragile) to `["pr", "comment", "--repo", f"{owner}/{repo}", number, "--body", body]` (robust).
  - Added inline comment explaining the choice and linking to the matching shell helper / get_pr_info / SKILL.md.
  - Reasoning: Directly addresses the root cause of the posting failure. The defect was an incomplete application of the "robustness" updates that the skill docs and github.sh already advertised. This makes the *primary recommended tool* (the python helper) actually match its own documentation and the shell library.
  - support_count: 1 (session), but P0 because: clear reproducible root cause, high impact on the "posting" half of the skill (the part users explicitly request with "post this"), generalizable to every future --mode comment / hybrid use, and would have prevented the exact observed failure + extra diagnostic work.
- No other edits. Review generation had zero friction, so no changes there. No edits to SKILL.md itself (the code now makes the existing claims true). Only 1 edit total (<< cap of 4).

### Deferred Edits (waiting for more signal)
- (none — P3 items not present; the posting inconsistency was the only systematic issue with clear root cause)

### Observed Regressions from Previous Edits
- (N/A — this is Step 1; no prior edits existed for this skill)

### Meta Notes
- Strategy this round: "Fix the root cause, not the symptom" + "patch gaps in supporting artifacts (scripts/)". The symptom was "posting didn't work via the python helper"; the root was a single line in post_top_level_comment that hadn't been updated when the robustness claims and shell helper were improved.
- The skill's review *generation* side is mature and reliable (clean first-try success). The posting side had a partial "robustness" retrofit that left the default top-level path (most common) broken.
- Duplicated skill artifacts (SKILL.md + scripts/ live under both ~/.grok/skills/pr-reviewer/ and ~/.pi/agent/skills/pr-reviewer/) were both updated for the helper script so runtime and source stay consistent. The post_review.py hard-codes a .grok path when sourcing github.sh for parse_pr_url fallback, so the .grok copy remains the reference for execution in documented flows.
- Convergence note: First pass. The documented "Updated Workflow Notes" and "The helpers are now more robust" language can now be trusted for the primary python tool as well. Future sessions using `/pr-reviewer ...` followed by posting requests should no longer hit this class of gh invocation failure.
- No signals pointed at improve-skill itself during this optimization run (the process was followed without friction), so no self-edit was performed.

### Verification Performed (Gate)
- Re-read the edited function in both file locations after search_replace.
- Confirmed the gh argv now exactly matches the successful manual call that posted the real comment (https://github.com/bmaltais/model-shelf/pull/250#issuecomment-4649144170).
- Regression check: dry-run, parsing, inline/hybrid, and all non-posting behavior untouched. Existing shell helper path unchanged.
- Effectiveness check: the exact failing command sequence would now succeed at the gh layer.
- Generalization check: applies to any PR, any environment (no checkout required), default --mode comment and hybrid.
- Scripts remain executable; the added comment is self-documenting.
- No CHANGELOG existed before; this entry creates the training log as specified.

Next improvement round (Step 2) should re-load this CHANGELOG before analysis.

## Session 2026-06-08 — Step 2

### Session Context
- Active skill under analysis: pr-reviewer (triggered via plain `/pr-reviewer pr 251` with no `--post` flag or "post" language).
- The rollout exercised the full review generation path (diff fetch via web_fetch + gh, context via read_file/git, strict Copilot Reviewer persona + exact **Summary** + 🔴 + 🟡 + ✅ + file:line output, verification via `go test`), but **stopped after emitting the structured review**.
- User issued direct correction: "you forgot to put the feedback as comment(s) in the PR. Make sure to not do that again."
- Follow-up explicit instruction: "update the skill so it is clear I want this by default".
- User then invoked `/improve-skill` to perform the formal optimization pass.
- This is the *second* occurrence of the user having to prompt for posting behavior on a plain pr-reviewer invocation (see Step 1 session which contained a similar "make sure to provide review as comment(s)" signal).

### Rollout Signals Extracted
**Failure signals (high priority):**
- Direct user correction + explicit request to change default behavior (support_count: 2 across sessions, high impact). Plain `/pr-reviewer pr 251` (a form documented in "Examples of Triggers") resulted in the agent emitting only the review block and taking no posting action.
- Instructions in the skill at invocation time conditioned posting on explicit request: Workflow step 5 ("If the user asked to post (e.g. ... --post ..., or follows up ... 'post this')"), "The posting action is opt-in by the user.", "Ask for explicit confirmation before any write.", frontmatter and examples that treated `--post` as the way to get comments, and the strict "Produce **only** the structured review in the exact format specified" + "nothing before **Summary**, nothing after...".
- Recurrence of the same class of signal after Step 1: the previous optimizer saw a related user desire for comments but scoped the fix narrowly to a helper implementation bug and explicitly chose *not* to edit SKILL.md for the default behavior. This left the documented default mismatched with user expectation, causing the signal to reappear in the very next session using the skill.
- Extra round-trips: the user had to issue a correction + a separate "update the skill" request instead of the plain command doing what they wanted.

**Success signals:**
- Review *generation*, persona adherence, output format fidelity, file:line references, focus area analysis, and verification steps (running relevant `go test` packages) all succeeded cleanly on first try with no corrections needed on the content itself.
- Upon receiving the direct "update the skill" instruction, the agent correctly performed coordinated, multi-section edits to SKILL.md (frontmatter, command/flag handling, workflow, posting constraints + recommended flow + execution rules + notes + examples) plus the supporting scripts/README.md.
- The subsequent posting of the actual review for PR 251 was performed successfully via the (now-default) helper flow.
- The user correctly used `/improve-skill` as the meta-tool to formalize and persist the improvement.

### Edits Applied (P0; learning rate respected)
- [op: replace / sync] Applied the full "make posting the default" bundle to the *canonical* `~/.pi/agent/skills/pr-reviewer/SKILL.md` (frontmatter description, Command/flag handling, Workflow step 5, Posting Feedback core constraints + Recommended Posting Flow (now labeled "default behavior") + Execution Rules + Updated Workflow Notes + Examples of Triggers). The `~/.grok/skills/pr-reviewer/SKILL.md` copy had already received the equivalent changes earlier in the session in direct response to the user's "update the skill" request.
- [op: replace] Updated the canonical `~/.pi/agent/skills/pr-reviewer/scripts/README.md` "Usage inside the skill" section (and the .grok mirror) to describe the new default flow (plain invocation = output review + dry-run then auto --confirm; document `--no-post`).
- Reasoning: The root cause was in the skill's own instructions (not the helper code, which Step 1 had already hardened). The user's explicit "I want this by default" + recurrence from Step 1 gives this high support_count and confidence. The change is generalizable to every future plain `/pr-reviewer` invocation. It directly implements the requested behavior while preserving the opt-out (`--no-post`), the strict review output format for the Copilot persona, the dry-run visibility requirement, and the "always prefer helpers" rule. Only one logical improvement (default flip + supporting text) + mechanical sync of duplicates (well under the cap of 4).
- No other edits. The review generation side remains untouched and was already mature.

### Deferred Edits (waiting for more signal)
- (none in this round). A potential future refinement (P2/P3) could be a small clarifying sentence under "Output Format" or "Workflow" / "Never break character" explaining how the agent can/should emit the exact structured review block as the primary visible Copilot Reviewer output *while also* executing the default posting side-effect via tool calls (dry-run + confirm) in the same activation. Current edits already make the intent and flow clear in the posting section; more signal would be needed before adding text that risks conflicting with the "produce only..." rule.

### Observed Regressions from Previous Edits
- The Step 1 decision to scope the fix only to the post_review.py helper implementation (and explicitly *not* touch SKILL.md's "posting is opt-in" language or workflow defaults) is now visible as a regression in behavior for user expectation. The same class of user correction re-appeared. This Step 2 resolves it by updating the instructions.

### Meta Notes
- Strategy this round: When a user gives an explicit "make X the default" after a prior optimization pass left the documented default unchanged, treat it as strong confirming signal for a previously deferred or narrowly-scoped edit. Prioritize updating the *skill instructions and documented behavior* (not just implementation) when the mismatch is about core defaults, especially for high-value features like posting (half the skill's purpose).
- Repeated user signals on the same expectation (posting on plain invocation) across Step 1 and this session: support_count = 2. Future passes should raise the priority of "user mental model vs. documented default" even on first occurrence if it concerns the primary user-facing contract of the skill.
- improve-skill was invoked cleanly by the user at the end of the trajectory with no friction in the process itself. No signals pointed to needed changes in improve-skill.
- Duplicated artifacts (under both ~/.grok/skills/pr-reviewer/ and ~/.pi/agent/skills/pr-reviewer/) were kept in sync for SKILL.md and scripts/README.md, consistent with the practice established in Step 1 for the helper.
- Convergence note: The behavioral default for the most common invocation form (`/pr-reviewer <pr>`) now matches the user's repeatedly expressed desire. The "Updated Workflow Notes" and posting flow language can be trusted. The review generation side was already reliable; the posting side's *when to post* contract is now aligned.

### Verification Performed (Gate)
- Re-read the edited sections in both the .grok and .pi copies of SKILL.md (and both copies of scripts/README.md) after the search_replace operations in this pass.
- Regression check: Review generation, strict output format, --no-post opt-out path, "produce only the structured review", persona rules, and all non-posting behavior are untouched. The dry-run preview requirement is preserved and now explicitly part of the default flow.
- Effectiveness check: A plain `/pr-reviewer pr 251` under the new instructions would cause the agent to (a) emit the structured review as before, and (b) treat posting as the default and run the save + post_review.py --dry-run + --confirm sequence (while still showing the dry-run output for visibility). This would have prevented the observed "you forgot" correction.
- Generalization check: Applies to any PR, any plain invocation (with or without number vs. full URL), and any future user who expects the slash command to leave comments by default. The --no-post escape hatch is clearly documented.
- The changes are concise, reinforce the existing "Helpers (always prefer these)" and "Recommended Posting Flow" sections rather than adding new top-level ones, and are directly traceable to the observed signals + history.
- Both copies of the artifacts are now consistent; the canonical .pi versions are updated.

This completes Step 2 for pr-reviewer. The training log now reflects that the default-posting contract has been explicitly set and validated against repeated user signals.
