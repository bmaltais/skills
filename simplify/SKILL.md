---
name: simplify
description: Automated code review and simplification workflow that reviews git changes through three parallel analyses (code reuse, quality, efficiency) and applies high-confidence fixes. Use whenever users want to clean up code, simplify code, review changes before committing, check for duplicate logic, find N+1 patterns, improve code efficiency, refactor messy code, or reduce technical debt. Trigger on phrases like "simplify my code", "review my changes", "check for duplicates", "optimize this code", "clean up before commit", "any code smells?", "make this more efficient", or "reduce complexity". Always use this skill when the user mentions code review, refactoring, or wants to improve code quality.
categories: [software-development]
agents: [copilot]
metadata:
  source: custom
  scope: global
---

# Simplify

An automated code review and simplification workflow that analyzes your git changes and applies confident improvements.

## Overview

The simplify skill is a 3-phase workflow that:
1. **Identifies Changes** - Detects what code has changed via git diff
2. **Parallel Review** - Three specialized agents analyze changes concurrently
3. **Fix Issues** - Aggregates findings, filters by confidence, and applies fixes

This skill aims to require minimal user input — it works autonomously to detect issues and apply safe improvements in your current branch.

## When to Use

Use this skill when you:
- Want to review code changes before committing
- Need to simplify or clean up messy code
- Suspect duplicate logic or missed abstractions
- Want to catch inefficiency patterns (N+1 queries, missed concurrency)
- Need to reduce technical debt incrementally
- Want an automated second opinion on your changes

## Workflow

### Phase 1: Identify Changes

Start by determining what code has changed:

1. **Check for uncommitted changes** first using `git diff`
   - If there are meaningful uncommitted changes (more than whitespace/comments), use those
   - "Meaningful" means changes to logic, structure, or functionality

2. **Fall back to unpushed commits** if no meaningful local changes
   - Run `git log origin/HEAD..HEAD --oneline` to check for commits not yet pushed to the remote
   - If multiple unpushed commits exist, diff the full range: `git diff origin/HEAD..HEAD`
   - If no unpushed commits exist, fall back to the last commit: `git diff HEAD~1 HEAD`
   - This ensures the skill reviews the full body of in-progress work, not just the tip commit

3. **Extract changed files and context**
   - Get the list of changed files
   - For each file, note the changed line ranges
   - Read the full content of changed files (you need context to review properly)

### Phase 2: Parallel Review

Spawn three review agents **concurrently** (same turn). Each agent has a specialized focus. All three agents receive:
- The git diff output
- Full content of changed files
- Access to the last commit via `git show HEAD`
- Read-only access to the broader codebase for context

The three agents are:

#### 1. Code Reuse Agent

**Focus**: Finding duplicate logic and missed opportunities to use existing utilities.

**What to look for**:
- Duplicate code blocks (similar logic in multiple places)
- Reinventing existing utilities or helper functions
- Copy-pasted code with minor variations
- Opportunities to extract shared logic into reusable functions

**Agent instructions**: See `agents/code_reuse_reviewer.md`

#### 2. Code Quality Agent

**Focus**: Structural issues, leaky abstractions, and code cleanliness.

**What to look for**:
- Redundant state or variables
- Leaky abstractions (implementation details exposed)
- Overly complex conditional logic
- Magic numbers or strings that should be constants
- Inconsistent naming or patterns
- **Terraform: dead locals** — `local.*` names defined in `locals.tf` or `name.tf` that are never referenced in any other `.tf` file; common after a resource is removed
- **Terraform: empty locals files** — files containing only `locals {}` with no assignments; delete them
- **Terraform: stale variable descriptions** — `description` fields that name a different resource type (copy-paste artifact from another module); rewrite to match the actual resource

**Agent instructions**: See `agents/code_quality_reviewer.md`

#### 3. Efficiency Agent

**Focus**: Performance issues and optimization opportunities.

**What to look for**:
- N+1 query patterns (database or API calls in loops)
- Missed concurrency opportunities (sequential when could be parallel)
- Inefficient data structures or algorithms
- Unnecessary recomputation (memoization opportunities)
- Potential memory leaks or excessive allocations

**Agent instructions**: See `agents/efficiency_reviewer.md`

**Important**: All three agents run in parallel. Launch them together and collect results as they complete.

### Phase 3: Fix Issues

Once all three review agents have completed:

1. **Aggregate findings**: Collect all issues identified by the three agents

2. **Filter by confidence**: Only proceed with fixes that have:
   - **High confidence** (agent explicitly marked as "high confidence" or provided clear evidence)
   - **Low risk** (simple, localized changes)
   - **Clear fix** (agent provided concrete solution, not just identified a problem)

3. **Skip false positives**: Ignore findings where:
   - The agent couldn't provide specific evidence
   - The fix requires significant architectural changes
   - The issue is subjective or stylistic (not objective improvement)
   - The agent marked it as "low confidence" or "needs human review"

4. **Apply fixes**: Make the code changes directly to the files in the current branch
   - Use multi_replace_string_in_file for efficiency
   - Do not create commits automatically
   - Work incrementally — apply one type of fix at a time if there are many changes

5. **Show summary**: After applying fixes, present a summary:
   ```
   ## Simplify Review Complete
   
   ### Changes Made
   - [File path]: [Brief description of fix]
   - [File path]: [Brief description of fix]
   
   ### Issues Found (Not Fixed)
   - [Issue description]: [Why not fixed - low confidence/requires manual review/etc]
   
   ### Statistics
   - Files reviewed: X
   - Issues found: Y
   - Fixes applied: Z
   - Confidence threshold: High
   ```

The user can then review the changes with `git diff`, commit if satisfied, or ask for adjustments.

## Error Handling

**No changes detected**: If both `git diff` and `git diff HEAD~1 HEAD` show no changes, inform the user and ask if they want to review a specific file or directory instead.

**Git not available**: If git commands fail, this skill cannot run. Inform the user that simplify requires a git repository.

**All findings filtered out**: If all three agents return only low-confidence findings, show the findings but explain why no fixes were applied. Ask the user if they want to manually review any of the flagged issues.

**Conflicting fixes**: If two agents suggest conflicting changes to the same code, present both options to the user and ask which approach they prefer.

## Tips for Best Results

1. **Commit frequently**: The skill works best when reviewing small, focused changes rather than massive diffs

2. **Run before committing**: Make simplify part of your pre-commit workflow

3. **Trust the process**: The confidence filtering is designed to avoid breaking changes — if a fix passes the threshold, it's very likely safe

4. **Iterate**: If the summary shows issues that weren't fixed, you can ask about specific ones or manually address them

5. **Combine with testing**: After fixes are applied, run your test suite to verify nothing broke

## Limitations

This skill is **not a replacement for**:
- Comprehensive code review by humans
- Static analysis tools (linters, type checkers)
- Security audit tools
- Performance profiling under realistic load

It's best suited for catching common patterns and making incremental improvements during active development.

## Example Usage

**User**: "simplify my code before I commit"

**Claude**: 
1. Runs `git diff` → finds changes in `src/api.py` and `src/utils.py`
2. Spawns 3 review agents in parallel
3. Code Reuse Agent finds: duplicate error handling in both files
4. Quality Agent finds: magic number `429` in api.py (should be constant)
5. Efficiency Agent finds: no issues (marks as "none found")
6. Applies 2 fixes (high confidence)
7. Shows summary with statistics

**User**: "check my last commit for problems"

**Claude**:
1. Runs `git diff` → no uncommitted changes
2. Falls back to `git diff HEAD~1 HEAD`
3. Reviews the last commit through 3 agents
4. Applies safe improvements
5. Shows summary

## Related Skills

- **code-review**: Human-focused code review with detailed explanations (for learning)
- **optimize**: Performance-focused optimization with benchmarking
- **refactor**: Large-scale restructuring with architectural planning

Use **simplify** for quick, automated improvements. Use the related skills for deeper, more involved work.
