# Model routing

The orchestrator thinks through the gates; execution goes to the cheapest
model that can pass Gate 4. Scores 1–5, higher is better (cost 5 = cheapest).

| Model  | Cost | Intelligence | Taste | Route here for |
|--------|------|--------------|-------|----------------|
| haiku  | 5    | 2            | 2     | Scouting, searches, mechanical edits, well-specified single-file tasks |
| sonnet | 4    | 3            | 3     | Executing a fully scoped plan, multi-file implementation, tests |
| opus   | 2    | 4            | 4     | Orchestration, code review, design decisions, running the gates |
| fable  | 1    | 5            | 5     | Only: adversarial scoping of genuinely hard problems, post-mortems on great outputs to extract more process |

Routing rules:

1. Default sub-agent model is haiku; escalate one tier when a worker fails
   verification twice.
2. The smart model designs steps so a dumb model can execute them with zero
   questions: exact files, exact commands, exact done-checks per step.
3. Workers report evidence (command output), not conclusions. The
   orchestrator re-runs Gate 4 on their claims.
4. Taste-heavy work (UI, naming, UX copy, creative framing) routes up the
   taste column even when intelligence isn't needed.
