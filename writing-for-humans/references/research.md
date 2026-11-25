# Research for a Smaller Human Reading Set

**Status:** Research
**Author:** Bernard Maltais
**Created:** 2026-11-24
**Updated:** 2026-11-24
**Summary:** Compares Canada.ca plain language, C4, arc42, Diataxis, architecture decision records and GOV.UK user needs. Recommends three short core documents with optional detailed designs; distinguishes primary-source guidance from proposed local reading budgets and maintenance rules.

## Finding

The useful distinction is not between "high-level architecture" and "technical architecture."
Those labels can describe overlapping material. The distinction is between the questions a reader
needs answered: **Why does this project matter? How does the solution fit together? What needs
attention now?** Specialists then follow links to detailed designs for their own area.

The recommendation is three short core documents: a **project brief**, an **architecture overview**
and a **delivery brief**. Existing detailed designs, operating instructions and decision records
remain available on demand. This is a local synthesis of the sources below, not a standard that
requires three documents. It reduces required reading, not necessarily the total evidence retained.

## Primary sources and their useful boundaries

The following first-party sources were consulted on 2026-11-24. The proposed templates are original
prompts based on these ideas, not copies of the source templates.

| Source | What the source establishes | Application here | Boundary |
| --- | --- | --- | --- |
| [Canada.ca Content Style Guide](https://design.canada.ca/style-guide/), writing principles and plain language | Content should meet audience needs, put important information first, and offer a plain-language summary even for specialized audiences. | Lead with purpose, consequences and the reader's next action; explain specialist terms where they occur. | Guidance for government web content informs this internal kit; using it does not certify accessibility, bilingual publication or compliance. |
| [C4 system context](https://c4model.com/diagrams/system-context) | A context diagram shows the system, its users and connected systems; its audience includes non-technical readers. | Begin the architecture overview with people, boundaries and external relationships. | A context diagram alone does not explain internal responsibilities, operational readiness or deployment. |
| [C4 container diagram](https://c4model.com/diagrams/container) | The next view shows applications and data stores, responsibilities, technology choices and communication, for technical readers. Deployment is a separate concern. | Put internal technical detail behind the overview, with deployment views where needed. | A C4 container means an application or data store, not necessarily a Docker container. An AWS account or network zone should not automatically be labelled a C4 container. |
| [arc42 overview](https://arc42.org/overview/) and [architecture decisions](https://docs.arc42.org/section-9/) | Architecture documentation can be tailored from 12 sections. Significant decisions need rationale; authors should choose the appropriate location and avoid redundant text. | Select context, strategy, responsibilities, quality, risks and decision links rather than require every section in every document. | arc42 is an architecture framework, not a sponsor briefing or project progress-reporting system. |
| [Diataxis](https://diataxis.fr/) | Tutorials, how-to guides, reference and explanation serve different documentation needs. | Separate explanatory reading from operating instructions and exhaustive reference. | Its four documentation forms are not four levels of seniority or four architecture documents. |
| [Michael Nygard on architecture decision records](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) | A short record captures one significant decision, its context, status and consequences. Reversed decisions remain available and point to their replacements. | Retain rationale and approval state in the existing decision register; briefings link to the relevant record. | This is not a task tracker or a mandate to replace the repository's existing decision IDs, roles or lifecycle. |
| [GOV.UK on learning user needs](https://www.gov.uk/service-manual/user-research/start-by-learning-user-needs) | Understand users and their goals, test assumptions with evidence, and keep researching as the service develops. | Test the reading set with actual sponsors, architects and delivery leads. | Applying service-design guidance to documentation readers is an analogy; this research is not a completed reader study. |

## What belongs at each depth

**Project brief.** Explain the problem, intended result, scope, success measures, responsibilities
and important constraints. This is the entry point, not an inventory of cloud products.
The audience-first approach comes from the Canada.ca guide and GOV.UK; this particular document
and its sections are local choices.

**Architecture overview.** Explain the system boundary, major responsibilities, a representative
journey through the solution, quality goals and important tradeoffs. C4 supplies the zooming
principle; arc42 supplies the coverage questions. This view can be technically accurate while
using ordinary language.

**Detailed design.** Explain how one area meets its requirements, including interfaces, failure
handling, security controls, deployment and verification. Reuse an existing design when it already
owns that subject. This is an optional reading branch, not the next document every sponsor must
read. Infrastructure diagrams should use appropriate labels and legends rather than force every
cloud resource into C4's software abstractions.

**Delivery brief.** Explain changes since a named reporting date, evidence of readiness, blockers,
near-term milestones and decisions requiring attention. Keeping this fast-changing view separate
from architecture is a local maintenance choice. None of the sources above prescribes this
particular reporting artifact.

**Decision records and operating instructions.** Keep these as linked evidence. Decision records
explain why a choice was made; operating instructions explain how to perform a task safely.
Neither should become required background reading for understanding the project.

## Plain language without losing substance

Write for an educated reader who does not work in cloud engineering. College-level understanding
does not require college-level sentence complexity. Retain the real tradeoffs, limitations and
uncertainties, but introduce a product through its job before naming it. For example, describe
"a shared network hub that connects separate environments" before introducing Amazon Transit
Gateway. State where an analogy stops being accurate.

The [Canada.ca guide](https://design.canada.ca/style-guide/) supports audience-appropriate language
and summaries for non-specialists. It does not establish the word budgets proposed in the
[reading guide](reading-guide.md). Readability scores can flag dense prose but cannot
prove that a reader understands the architecture or can make the requested decision.

## Keeping summaries trustworthy

[arc42 section 9](https://docs.arc42.org/section-9/) explicitly cautions against redundant decision
text. [Nygard's decision-record guidance](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
preserves rationale and supersession. Together these support linking summaries to the record that
owns a decision, rather than maintaining a second approval history.

The proposed local approach extends this principle to status and implementation evidence:

- Summarize the implication for the reader; link to the authoritative detail.
- Distinguish an intended design, an approved choice, a deployed capability and a tested outcome.
- Date status claims and identify the environment and evidence behind them.
- Refresh a summary when its supporting source changes, or mark it unverified until reviewed.

These are proposed authoring rules, not claims that the sources prescribe one repository layout,
review cadence or source-of-truth hierarchy.

## Alternatives and tradeoffs

| Alternative | Benefit | Cost or limitation |
| --- | --- | --- |
| One master document | One address to remember | Architecture, status, instructions and historical evidence grow together; readers must filter it themselves. |
| A separate document for every named architecture level | Clear specialist divisions when their audiences genuinely differ | Similar titles obscure the reading path and encourage repeated explanations. |
| Full arc42 adoption | Broad and systematic architecture coverage | Requiring every section would exceed this mixed audience's immediate needs. Tailoring remains possible. |
| Three core documents with linked specialist detail | Each reader starts with a small, purpose-specific set | Summaries can drift; ownership, evidence links and reader testing are essential. |

The last option best fits the stated request, subject to a pilot with real readers. Suggested
word budgets, review dates and comprehension checks are defined in the reading guide as local
proposals. No measured improvement in reading time or comprehension is claimed.

## Deliverables and limits

The [reading guide](reading-guide.md) maps questions to existing repository evidence.
The [template pack](templates.md) provides four copyable starting points:
project brief, architecture overview, detailed design and delivery brief.

This work does not rewrite the technical library, reconcile all historical inconsistencies,
assert current deployment status, or approve any architecture decision. The guide and templates
remain proposed until reviewed by their intended readers.

## Change History

| Date | Author | Change |
| --- | --- | --- |
| 2026-11-24 | Bernard Maltais | Initial primary-source research and local recommendation for Task 3082. |
| 2026-11-24 | Bernard Maltais | Packaged the research as a skill reference at the owner's request. |
