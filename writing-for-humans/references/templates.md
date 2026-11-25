# Templates for Human Project Documentation

**Status:** Proposed
**Author:** Bernard Maltais
**Created:** 2026-11-24
**Updated:** 2026-11-24
**Summary:** Four original copyable Markdown templates for a project brief, architecture overview, optional detailed design and delivery brief. Includes audience, evidence, approval and readiness distinctions, ownership, review dates, quality scenarios, risks and decision links. Existing decision and operating records remain authoritative.

## Choose one template

Copy only the relevant fenced block into a new document and replace every brace-delimited prompt.
Keep an explicit "Unknown - owner and resolution date" where evidence is missing. Remove instructional
prompts before publication; mark an irrelevant section "Not applicable" with the reason.

| Template | Use when | Reader stops when |
| --- | --- | --- |
| [Project brief](#project-brief-template) | A newcomer needs the purpose, scope and success measures. | The reader can explain why the project exists and what it will deliver. |
| [Architecture overview](#architecture-overview-template) | A reader needs the major parts, relationships and tradeoffs. | The reader can follow a representative journey and name the main limitation. |
| [Detailed design](#detailed-design-template) | An implementer needs an answer absent from the existing owning design. | Interfaces, failures and verification are precise enough to implement and review. |
| [Delivery brief](#delivery-brief-template) | A reader needs current readiness, blockers and decisions. | The reader can identify what changed, what is proven and who must act next. |

The [reading guide](reading-guide.md) owns the reading budgets, evidence map and pilot
process. In this repository, copy detailed design content into the existing owning design where
possible, following its local structure. No separate "technical architecture" document is required
unless it serves a distinct reader question.

For decisions, use the existing [decision-record template](../../../../Documentation/Project/decisions/Decision-Register.md#adr-template)
and [decision process](../../../../Documentation/Project/decisions/Decision-Register.md#how-to-use-this-register). For operating procedures,
link the owning runbook rather than embedding commands in a briefing.

## Project brief template

This is the stable introduction. Current progress belongs in the delivery brief.

```markdown
# {Project name} at a Glance

**Status:** Draft
**Author:** {Name}
**Created:** {YYYY-MM-DD}
**Updated:** {YYYY-MM-DD}
**Owner:** {Accountable person or team}
**Reviewer:** {Named reviewer}
**Evidence checked:** {Date and source revision where relevant}
**Next review:** {Date}
**Summary:** {Problem, intended result and scope in one or two sentences}

## The point in one paragraph

{Who needs this, what problem they face, what the project changes, and why it matters.
Assume the reader has no cloud engineering background.}

## Outcomes and boundaries

| Intended outcome | How success will be measured | Source |
| --- | --- | --- |
| {Result for a person or organization} | {Measure, target and acceptance owner} | {Requirement link} |

**In scope:** {The few capabilities this project is responsible for}

**Outside scope:** {Explicit exclusions and who owns them}

## The proposed approach

{Explain the approach through responsibilities and outcomes rather than a list of products.
State whether it is a proposal, an approved direction or a mix; link approval records.}

## Constraints and important limits

{Funding, security, deadlines, dependencies and the most important compromise.
Explain their practical effect. Link supporting evidence and identify assumptions.}

## Responsibilities and next reading

{Name the sponsor, delivery owner, architecture owner and operational owner.
Link the architecture overview for how it works, and the delivery brief for current status.
Define the few unfamiliar terms needed to understand this brief.}

## Change History

| Date | Author | Change |
| --- | --- | --- |
| {YYYY-MM-DD} | {Name} | {Substantive change} |
```

## Architecture overview template

Use ordinary language even when the subject is technical. The diagram and narrative should tell
the same story. A provider product name can follow the description of its purpose.

```markdown
# How {Project name} Fits Together

**Status:** Draft
**Author:** {Name}
**Created:** {YYYY-MM-DD}
**Updated:** {YYYY-MM-DD}
**Owner:** {Accountable architecture owner}
**Reviewer:** {Named reviewer}
**Evidence checked:** {Date and source revision where relevant}
**Next review:** {Date}
**View:** {Intended design, verified current system, or explicitly labelled comparison}
**Summary:** {Approach, boundary and principal tradeoff in one or two sentences}

## The design in one paragraph

{Explain the organizing idea, why it serves the project's goals and what it gives up.
Link the project brief instead of restating its business case.}

## People and system boundaries

{Link one readable overview diagram with its revision and a text description.
Show the system boundary, its users and external dependencies. Label arrows with their
purpose, distinguish ownership and trust boundaries, and provide a legend.
Label proposed elements explicitly. Keep product icons secondary to understandable names.}

## Major responsibilities

| Part in everyday language | Job it performs | Owner and boundary | Owning design |
| --- | --- | --- | --- |
| {Part} | {Responsibility and what it does not own} | {Team and handoff} | {Section link} |

## A representative journey

{Follow one important request from the person initiating it through the system to its result.
Explain where access is checked, sensitive information crosses a boundary, and evidence is
recorded. State what happens to the user if a critical dependency fails.}

## Quality goals and limitations

| Situation | Required outcome | Evidence or open gap |
| --- | --- | --- |
| {Failure, recovery, load or security scenario} | {Measurable target and source} | {Test, design or explicit unknown} |

{Explain the most important constraint and residual risk in ordinary language. Distinguish
design intent from demonstrated behaviour; approval does not establish operational readiness.}

## Important choices and open questions

{For each material choice, explain its consequence for the reader and link its decision record.
Preserve the record's approval status and conditions. Link pending choices without presenting
them as settled. Link the delivery brief for current owners, deadlines and follow-up.}

## Detail only when needed

{Link each owning design by the question it answers, including operations and recovery guidance.
Define essential terms inline or in a small glossary here.}

## Change History

| Date | Author | Change |
| --- | --- | --- |
| {YYYY-MM-DD} | {Name} | {Substantive change} |
```

## Detailed design template

This is an optional specialist branch, normally one bounded area rather than a system-wide
implementation catalogue. Start with a proposed 1,500-word narrative budget; contract tables and
verification detail can exceed it when needed for correctness. Link generated reference and
configuration rather than copying inventories. This budget is a local starting point for the pilot.

```markdown
# Detailed Design for {Capability}

**Status:** Draft
**Author:** {Name}
**Created:** {YYYY-MM-DD}
**Updated:** {YYYY-MM-DD}
**Owner:** {Implementing team}
**Reviewer:** {Technical reviewer and security or operations reviewer where needed}
**Evidence checked:** {Date and source revision}
**Next review:** {Date}
**View:** {Intended design or verified implementation, with exceptions labelled}
**Summary:** {Capability, boundaries and important constraints}

## Purpose and boundaries

{Explain the capability plainly, then link its architecture overview, requirement IDs and
dependent decisions. Define ownership, exclusions and assumptions. Use "Unknown" for unsettled
design inputs rather than inventing a value.}

## Structure and behaviour

{Describe the components and one normal sequence. Link a scoped diagram if it clarifies the
behaviour. Distinguish logical structure from where things are deployed.}

## Interfaces and responsibilities

| Interface | Producer and consumer | Contract and version | Access and sensitive data | Failure behaviour |
| --- | --- | --- | --- | --- |
| {Name and owning specification link} | {Teams or components} | {Inputs, outputs and compatibility} | {Trust boundary and protection} | {Timeout, retry, duplicate handling or rejection} |

## Quality and security scenarios

| Requirement | Situation and environment | Measurable response | Verification and acceptance owner |
| --- | --- | --- | --- |
| {Source ID and link} | {Load, outage, attack or data-loss scenario} | {Target and limit} | {Test or review evidence; owner} |

{State data handling, access boundaries, audit evidence and retention where relevant.
Explain assumptions and remaining controls owned by another team.}

## Failure and recovery

{Cover dependency loss, partial completion, retry limits, safe failure, alerting ownership and
recovery. Define data-loss and recovery-time targets where applicable. Link executable
procedures; describe any irreversible step and the limits of rollback.}

## Deployment and operation

{Describe environments, release dependencies, configuration and secret ownership, promotion,
monitoring and support handoff. Link code and operating procedures as the authoritative detail.
Identify any manual approval gates.}

## Verification and unresolved risks

{Map each requirement to expected evidence. Label checks planned versus observed; date observed
results and identify their environment and revision. Name the owner and next step for every gap.
Link decisions and risks rather than maintaining a second decision history.}

## Change History

| Date | Author | Change |
| --- | --- | --- |
| {YYYY-MM-DD} | {Name} | {Substantive change} |
```

## Delivery brief template

This is a dated snapshot, not an accumulating activity log. Link detailed records and previous
snapshots only when useful. Dates, costs and completion claims need evidence; an unknown is better
than an invented percentage.

```markdown
# {Project name} Delivery Brief for {YYYY-MM-DD}

**Status:** Draft
**Author:** {Name}
**Created:** {YYYY-MM-DD}
**Updated:** {YYYY-MM-DD}
**Owner:** {Delivery lead}
**Reviewer:** {Named reviewer}
**Reporting period:** {Start to end}
**Evidence checked:** {Date, environment and relevant revision}
**Next review:** {Expiry date; mark Not current after this date until reviewed}
**Summary:** {Overall position, main change and most urgent action}

## Bottom line

{On track, at risk, blocked or unknown, assessed against a named milestone or baseline.
Explain why, what changed since the previous dated brief, and the action needed now.}

## Readiness supported by evidence

| Capability | Approval and conditions | Deployment evidence | Verification evidence | Remaining gap and owner |
| --- | --- | --- | --- | --- |
| {Outcome readers recognize} | {Decision link and exact status} | {Environment, date, revision and evidence, or not deployed or unknown} | {Observed result and evidence, or not tested or unknown} | {Specific gap; owner} |

## Next milestones and dependencies

| Outcome | Baseline date | Current forecast and confidence | Owner and dependency |
| --- | --- | --- | --- |
| {Deliverable or acceptance gate} | {Date or not agreed} | {Date or unknown, with reason and evidence link} | {Person; blocker and tracking link} |

{State material cost changes against a dated estimate and its assumptions, or "No cost update
verified this period." Link the cost model rather than reproduce it.}

## Decisions and help needed

| Question and record | Recommended option and tradeoff | Decision authority | Needed by and consequence of delay |
| --- | --- | --- | --- |
| {Plain-language question and link} | {Recommendation, not an approval} | {Accountable person or body} | {Date and impact} |

## Top risks and immediate actions

{Give each material risk or blocker an impact, mitigation, owner, next action and review date.
Include only what changes the delivery outlook; link the detailed work item.
If there are no open items, say that only after checking the relevant records.}

## Change History

| Date | Author | Change |
| --- | --- | --- |
| {YYYY-MM-DD} | {Name} | {Substantive change} |
```

## Publication check

Before sharing a completed template, verify:

- Every prompt is resolved or explicitly unknown with an owner and resolution date.
- The reader can understand the conclusion before following a technical link.
- Evidence links resolve to the owning section, work item or dated result.
- Recommendations, approvals, deployments and observed tests are clearly distinguished.
- Metadata and review dates are current; word budgets and reader checks follow the guide.
- No credentials, sensitive operational values or unsupported compliance claims were introduced.

## Change History

| Date | Author | Change |
| --- | --- | --- |
| 2026-11-24 | Bernard Maltais | Added four original templates and publication criteria for Task 3082. |
| 2026-11-24 | Bernard Maltais | Bundled templates with the writing-for-humans skill rather than project documentation. |
