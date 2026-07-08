---
name: implement
description: "Implement a piece of work end-to-end from a spec or set of tickets: branch, TDD, review, PR."
disable-model-invocation: true
---

1. Before any research or edits, identify the target branch — check for a long-lived integration branch such as `dev` before assuming the repository's default branch — then create a new branch off it (e.g. `fix/<ticket>-<slug>`). Never commit directly to a shared branch like dev/master — everything below happens on this new branch.
2. Implement each requirement behind a test exercising its new or changed behavior. Use /tdd to find the seam even when none was pre-agreed; if something is genuinely untestable, say so explicitly instead of skipping it.
3. Run typechecking regularly, single test files regularly, and the full test suite once at the end.
4. Before committing, run /code-review and address its findings.
5. Commit to the branch.
6. Push the branch and open a PR against the target branch, including `Closes #<ticket>` so it links and closes the originating issue on merge.
