---
name: writing-great-tests
description: Use when writing, reviewing, or repairing tests — adding coverage to an untested file, writing a reproducing test for a bug, or fixing tests that are flaky, brittle, or slow.
---

A test that has never been **red** proves nothing. Everything here serves getting each test to fail for the right reason once, before it is allowed to pass.

## The test you hand back

Test code, held to the standard of the code it guards.

- **Purpose** — it tells whoever breaks this code later what broke and why, from the failure output alone.
- **Composition** — one behaviour per test; a name stating that behaviour; a fixture built inside the test; one exercise of the system under test; assertions on the outcome.
- **Derivation** — from the behaviour contract: the issue, the docstring, the bug report, the observed current output. Where no contract exists, ask for it.
- **Quality criteria** — each test has been observed red; passes alone and in randomized order; reads top to bottom without jumping to a helper to learn what it does.

## Preconditions

Read the runner command out of the project (`package.json` scripts, `pyproject.toml`, `Makefile`, CI config) and run the suite once. You know it is green, or you know exactly which tests were already failing. Match the surrounding tests' framework, layout, and naming — a second style in one suite costs more than any convention it improves on.

## Red first

Three ways in, one outcome:

- **New behaviour** — write the test, run it, confirm it fails for the expected reason. An import error or a typo is not red; fix it and run again.
- **A bug** — reproduce before repairing. The test fails on current code, with the reported symptom in the failure message.
- **Legacy code with no tests** — characterize: assert the actual current output, then earn the red by mutation — flip one operator or constant in the source, confirm the test fails, revert.

Postcondition, per test: a failing run you have actually seen. A test that cannot be made to fail is asserting nothing — repair it or drop it.

## Green

Write the smallest change that passes, then run the whole suite.

## What to assert

Assert the **outcome** — the return value, the resulting state, the observable effect. A test that asserts a collaborator was called is coupled to today's implementation and dies at the next refactor; assert the call only when the collaboration itself is the contract ("charges the card exactly once").

Substitute only what is slow or nondeterministic — clock, network, filesystem, randomness — and inject it rather than patching it in place. Everything else runs for real.

One concept per test. Several assertions describing one outcome are fine; two unrelated behaviours in one test are two tests.

Cover the sad paths, where failures actually live: empty / one / many, zero / negative / maximum, malformed input, and the error type and message raised.

Leave an unfinished test failing loudly (`pytest.fail("TODO: ...")`), so it reports itself rather than passing quietly.

## Verify

Run these, and report the output:

1. Full suite — green.
2. The new tests alone — green (`pytest path::test_name`, `vitest -t "name"`).
3. Shuffled order — `pytest -p randomly` (pytest-randomly) or `vitest --sequence.shuffle`. Same result as step 1; a difference means shared state between tests.
4. Mutation — break one line the new test claims to cover, confirm red, revert.

Coverage tools locate untested branches; the bar is step 4, not the percentage.
