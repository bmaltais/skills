# implement Optimization Log

## Session 2026-06-05 — Step 2

### Edits Applied
- (none — no P0/P1 issues observed)

### Deferred Edits (waiting for more signal)
- [P3] Go test stdout capture pattern: use `os.Pipe()` + `io.ReadAll(r)`, not `strings.Builder.ReadFrom`. Single occurrence — wait for repeat before encoding in skill.
- [P2 carried] Compound tool usage reminder — still waiting for repeat signal.

### Observed Regressions from Previous Edits
- (none — Step 1's test-isolation edit was not exercised this session)

### Meta Notes
- Session was clean: implementation first-try, one stdlib knowledge error caught by existing "build after write" guard.
- Convergence: skill is working well. Low friction session. Learning rate should stay low.

## Session 2026-06-05 — Step 1

### Edits Applied
- [op: replace] Extended test isolation rule to cover "modifying existing tests" — reasoning: removing `d.nodes` field caused join_test.go to fail because it loaded real mesh.json from host disk. The rule previously only said "new tests". Support count: 1 (but clear causal chain).

### Deferred Edits (waiting for more signal)
- [P2] Compound tool usage reminder in "Write the code" section — user pointed out read→edit should be read_and_patch. Already in system prompt tool table; adding to implement skill may be duplicative. Wait for repeat.

### Observed Regressions from Previous Edits
- (none — first optimization step)

### Meta Notes
- Added simplify fallback for no-subagent environments earlier in session (separate invocation)
- Skill is fairly mature — prefer surgical edits over broad additions
