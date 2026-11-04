---
name: speedup
description: Find and implement ONE small, measured performance improvement in the current codebase.
disable-model-invocation: true
---

Speed is a feature. Land exactly one optimisation, proven by a before/after number.

## 1. Find the bottleneck

Profile the real workload (profiler, flame graph, query plan, bundle analyser, `time`, network waterfall) until you can name the single hottest cost and show the evidence. Rank candidates by measured share of total cost; a guess from reading code is a hypothesis, not a bottleneck.

Done when one bottleneck is named with its measured share. No measurable bottleneck: report that and stop; an unmeasured codebase gets a benchmark, not an optimisation.

## 2. Baseline

Write the cheapest repeatable benchmark that exercises that bottleneck. Run it enough times to see the noise band, then record the median and spread.

Done when two consecutive baseline runs agree within the noise band.

## 3. Optimise

Make the smallest change that attacks the bottleneck. Keep behaviour identical: same public API, same output, same errors. Keep it _readable_: if the faster version needs a comment to be understood, the comment states what it buys.

Done when the existing tests pass unchanged and the diff touches one concern.

## 4. Prove

Rerun the benchmark under the same conditions as the baseline. Keep the change only when the improvement clears the noise band. Otherwise revert, and report the dead end with its numbers.

Done when the before/after medians are in hand.

## 5. Document

Put the result in the commit message or PR body:

- **Bottleneck**: what was slow, and the evidence.
- **Change**: what the diff does.
- **Impact**: before → after, with benchmark command and conditions.
- **Risk**: what could behave differently, and why it should not.

Spawn no second optimisation. List other candidates you saw as follow-ups.
