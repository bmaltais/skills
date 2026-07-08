---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

Implement the work described by the user in the spec or tickets.

Every change ships with a test exercising the new or changed behavior — use /tdd to find the seam even when none was pre-agreed. If something is genuinely untestable, say so explicitly rather than skipping it silently.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, use /code-review to review the work.

Before committing, create a new branch for the work (e.g. `fix/<ticket>-<slug>`) off the target branch; never commit directly to a shared branch like dev/master. Commit there.

Push the branch and open a PR against the target branch, including `Closes #<ticket>` so it links and closes the originating issue on merge.
