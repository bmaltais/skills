# A Shorter Reading Path for People

**Status:** Proposed
**Author:** Bernard Maltais
**Created:** 2026-11-24
**Updated:** 2026-11-24
**Summary:** Proposes project, architecture and delivery briefs as the small human reading set, with optional detailed designs. Maps Board reader questions to existing evidence and defines plain-language, freshness and comprehension checks. Includes links to research and four reusable templates; no project rewrite is included.

## Start here

The recommended reading set has **three core documents**, not a new summary for every existing file:

| Reader question | Document | Proposed maximum |
| --- | --- | --- |
| Why are we doing this, and what counts as success? | Project brief | 500 words |
| How does the solution fit together, and why this approach? | Architecture overview | 1,000 words and one overview diagram |
| Where do things stand, and what needs attention? | Delivery brief | 400 words |

These briefs have **not yet been populated for Board**. This deliverable is the research, reading
guide and [copyable template pack](templates.md). The existing evidence is
mapped below so a later pilot can produce the briefs without treating old plans as current facts.

A sponsor starts with the project and delivery briefs: at most 900 words. An architect adds the
overview, then only the detailed design relevant to the question. A delivery lead starts with the
delivery brief and follows a blocker or milestone to its work item. Routine readers can stop there;
they need not read the research or templates.

The budgets are local proposals, not research-backed thresholds. Count the reader-facing prose
and tables, excluding metadata, change history and reference URLs. Essential risks and conditions
remain visible; supporting detail moves behind a labelled link rather than disappearing.

## Where existing Board evidence fits

Choose the row that answers the question; this is a lookup menu, not a required reading sequence.
Existing sources may still use specialist language.

| Question | Existing starting point | What to take from it |
| --- | --- | --- |
| What problem is the project addressing? | [Framework context](../../../../Documentation/Project/10-Framework-Context.md) | Purpose and background, checked against later decisions. |
| What must the solution achieve? | [Requirements baseline](../../../../Documentation/Project/12-Requirements-Baseline.md) | Success measures and constraints, retaining requirement IDs in supporting links. |
| How are the major responsibilities divided? | [Design overview](../../../../Documentation/Design/00-README.md#how-the-pillars-relate) | The system-wide explanation and links to the relevant specialist area. |
| What has actually been approved? | [Decision register](../../../../Documentation/Project/decisions/Decision-Register.md#master-decision-index) | The record's exact status, authority, conditions and outcome. |
| How is deployment intended to work? | [Deployment architecture](../../../../Documentation/Project/41-Deployment-Architecture.md) | Delivery responsibilities and boundaries, not proof of deployment. |
| Where does the proof of concept differ from the design? | [Built versus designed](../../../../Documentation/Project/51-PoC-Built-vs-Designed.md) | Known exceptions, with dates and implementation evidence checked before reuse. |
| What remains to be demonstrated? | [Implementation assessment](../../../../Code/assessment/ASSESSMENT.md) | Findings to verify against current work items and test or deployment evidence. |
| Where is a specific technical answer? | [Design index](../../../../Documentation/Design/00-README.md) or [complete Markdown index](../../../../Documentation/MD-Index.md) | Only the relevant design or reference section. |

This map does not verify today's delivery status. A merged change proves a repository change,
not a deployment or security approval. Conflicting sources become an explicit question for the
owner; the summary must not silently choose a new outcome.

## Plain language for an educated non-specialist

Explain the job before the product, the consequence before the mechanism, and an unfamiliar term
where it first appears. Keep technical identifiers in evidence links when they are not needed
for understanding. Use short paragraphs and descriptive headings. A small glossary covers only
terms the reader will encounter repeatedly.

| Specialist shorthand | Clearer explanation |
| --- | --- |
| Deploy delegated-admin detective services across OUs | Give the security team a central place to monitor threats across the grouped cloud accounts. |
| Independent state reduces blast radius | Keep deployment records separate so a failed change is less likely to affect unrelated services. |
| CCCS Medium inherited controls | Security safeguards supplied by the shared platform; each service still needs evidence that its remaining obligations are met. |

These examples explain concepts, not verified claims about Board. Plain language preserves the
limits: supplying safeguards is not the same as proving compliance.

## Ownership and freshness

The following is a proposed pilot workflow. Each published brief names an owner, reviewer, evidence
date and next review date. The owner checks the linked source whenever its relevant content changes.
The delivery brief also expires at its next review date: an overdue brief is marked **Not current**.
Historical snapshots are dated and linked, not appended indefinitely to the current brief.

The [decision register's process](../../../../Documentation/Project/decisions/Decision-Register.md#how-to-use-this-register) remains
authoritative for decisions. Briefs report implications and link to it. Detailed designs remain
authoritative for their design rules; the briefs introduce those rules without creating independent
copies. Current work items and dated verification evidence support delivery claims.

## Pilot before expanding

1. Choose one document owner and a reviewer from each intended audience. Use the
   [templates](templates.md) to draft the three briefs from the evidence above.
   The existing design layout stays in place; a detailed-design template is used only for a genuine gap.
2. Check every material claim against its source. For each capability, identify whether it is intended,
   approved, deployed or tested; these are separate facts, not interchangeable labels.
3. Give each reviewer only their reading set. Ask them to explain the purpose, scope, major responsibilities,
   most important limitation and next action without opening specialist references. Ask delivery readers
   also to identify the evidence date and the next decision's owner and deadline.
4. Revise any missed answer or unexplained term. The pilot passes when every reviewer can find and explain
   every answer relevant to their role within the proposed word budget, and each claim has a source or
   is explicitly marked unknown. Record the observed results; this kit alone does not establish a pass.
5. Link the accepted briefs from the repository entry point. Retain technical evidence; remove or redirect
   a competing summary only after checking its unique content and references.

The [research](research.md) explains the sources and tradeoffs. The pilot
decides whether these budgets and divisions actually work for this team.

## Change History

| Date | Author | Change |
| --- | --- | --- |
| 2026-11-24 | Bernard Maltais | Proposed the human reading path, evidence map and pilot criteria for Task 3082. |
| 2026-11-24 | Bernard Maltais | Kept the guide and Board evidence map inside the skill, outside the project documentation tree. |
