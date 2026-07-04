# herdr Optimization Log

## Session 2026-07-04 — Step 1

### Edits Applied
- [op: insert_after, "wait for output"] Added ⚠️ command-echo false-match warning and sentinel file pattern as the recommended alternative for long-running commands. Reasoning: `herdr wait output` matched the command echo 3× in one session when the marker string was embedded in the command (e.g. `echo 'DEV DONE'`). Each false match required a re-wait and eventually a pivot to sentinel files. Support count: 3.

### Deferred Edits
- (none)

### Observed Regressions from Previous Edits
- N/A — first session

### Meta Notes
- First optimization step. The sentinel file pattern (`touch /tmp/x.done` + `while [ ! -f ]` poll) emerged organically in the session and proved reliable. Encoding it as the preferred pattern for long-running commands is the right generalisation.
- Convergence: N/A (step 1 baseline)
