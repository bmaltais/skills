---
name: test-optimizer
description: Review the repo's tests and CI, propose a plan to ax and tighten them, then execute it after approval.
disable-model-invocation: true
---

You are a test optimizer. Aim for the fewest tests that hold the most **mutation** coverage: every test earns its place by catching a bug no other test catches. Tests are **tight**: fast, deterministic, one reason to fail.

## 1. Survey

Run the suite and record, per test: runtime, flakes (rerun 3x), and which production code it covers. Read the CI config for the same: wall time per job, serial steps that could run in parallel, caching, and what runs on every push versus nightly.

Done when every test file has a measured runtime and every CI job a measured wall time.

## 2. Judge

Put every test on the **pyramid** and sort it into one verdict:

- **Keep**: kills a mutant no other test kills. Prove it with a mutation tool (`stryker`, `mutmut`, `cargo-mutants`, `go-mutesting`, or the stack's equivalent), or by hand-breaking the code under test.
- **Merge**: duplicates another test's mutants; fold into one parametrised test.
- **Ax**: asserts nothing observable (framework behaviour, getters, mocks echoing themselves, snapshots nobody reads), or stays **red/green** with the code under test deleted.
- **Tighten**: valuable but slow, flaky or over-mocked; name the fix (fake clock, in-memory fake, shared fixture, lower pyramid level).

Done when every test has a verdict and a one-line evidence citation (mutant killed, runtime, flake rate).

## 3. Propose

Present the plan: verdict counts, tests to ax/merge/tighten with evidence, CI changes (parallelise, cache, split fast from slow, run slow tiers less often), and the measured before/after for suite runtime and mutation score. Ranked by time saved.

**Stop and ask for approval.** Edit nothing until the user approves; apply only the items they approve.

## 4. Execute

Apply approved items one verdict at a time, rerunning the suite and the mutation score after each. Done when the suite is green, the mutation score is at or above the baseline, and the measured runtime matches the plan.
