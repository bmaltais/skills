---
name: implement
description: "Implement a piece of work end-to-end from a spec or set of tickets: branch, TDD, review, PR."
disable-model-invocation: true
---

1. Create a new branch for the work (e.g. `fix/<ticket>-<slug>`) off the target branch. Never commit directly to a shared branch like dev/master — everything below happens on this branch.
2. Implement each requirement behind a test exercising its new or changed behavior. Use /tdd to find the seam even when none was pre-agreed; if something is genuinely untestable, say so explicitly instead of skipping it.
3. Run typechecking regularly, single test files regularly, and the full test suite once at the end.
4. Use /code-review to review the work.
5. Commit to the branch.
6. Push the branch and open a PR against the target branch, including `Closes #<ticket>` so it links and closes the originating issue on merge.
