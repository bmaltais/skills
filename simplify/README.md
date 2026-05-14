# Simplify - Automated Code Review & Simplification

A Claude Code skill that automatically reviews your git changes and applies confident code improvements through parallel analysis.

## What It Does

Simplify is a 3-phase workflow that:

1. **Identifies Changes** - Detects uncommitted changes or reviews your last commit
2. **Parallel Review** - Three specialized agents analyze code concurrently:
   - 🔄 **Code Reuse Agent** - Finds duplicate logic and missed utilities
   - ✨ **Code Quality Agent** - Detects structural issues and complexity
   - ⚡ **Efficiency Agent** - Spots N+1 patterns and performance problems
3. **Fix Issues** - Applies high-confidence fixes automatically

## Quick Start

Just ask Claude to review your code:

```
"simplify my code before I commit"
"check for any code smells"
"review my changes for issues"
"optimize this code"
"make this cleaner"
```

The skill works autonomously with minimal user input - it detects changes, reviews them, and applies safe improvements in your current branch.

## What It Catches

### Code Reuse Issues
- ✅ Duplicate error handling logic
- ✅ Reinvented utilities that already exist
- ✅ Copy-pasted code with minor variations
- ✅ Logic that should be extracted to shared functions

### Code Quality Issues
- ✅ Magic numbers and hardcoded strings
- ✅ Redundant state or variables
- ✅ Overly complex conditional logic
- ✅ Leaky abstractions
- ✅ Inconsistent naming patterns

### Efficiency Issues
- ✅ N+1 database/API query patterns
- ✅ Missed concurrency opportunities
- ✅ Inefficient data structures (list vs set)
- ✅ Unnecessary recomputation in loops
- ✅ Potential memory leaks

## How It Works

### 1. Automatic Change Detection

Simplify looks at:
- Uncommitted changes first (`git diff`)
- Falls back to last commit if no local changes (`git diff HEAD~1 HEAD`)

### 2. Parallel Review (Fast!)

Three specialized agents run **concurrently** (not sequentially), each bringing domain expertise:

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Code Reuse     │  │  Code Quality   │  │  Efficiency     │
│  Reviewer       │  │  Reviewer       │  │  Reviewer       │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                    Aggregate Findings
                              │
                    Filter by Confidence
                              │
                       Apply Fixes
```

### 3. Confidence-Based Fixing

Only applies fixes that are:
- ✅ **High confidence** - Clear issues with objective evidence
- ✅ **Low risk** - Simple changes that won't break functionality  
- ✅ **Well-defined** - Specific fix with before/after code

Skips:
- ❌ Low confidence or speculative issues
- ❌ Changes requiring architectural decisions
- ❌ Subjective or stylistic preferences

### 4. Summary Report

After applying fixes, you get a clear summary:

```
## Simplify Review Complete

### Changes Made
- src/api.py: Extracted duplicate error handling to @handle_errors decorator
- src/cache.py: Replaced magic number 429 with HTTP_TOO_MANY_REQUESTS constant
- src/reports.py: Fixed N+1 query - batch load profiles (1000 queries → 1 query)

### Issues Found (Not Fixed)
- src/validator.py: Complex nested conditional (medium confidence - needs human review)

### Statistics
- Files reviewed: 3
- Issues found: 4  
- Fixes applied: 3
- Confidence threshold: High
```

## Configuration

### Scope

By default, simplify reviews:
1. Uncommitted changes (if meaningful)
2. Last commit (if no uncommitted changes)

### Confidence Threshold

Currently hardcoded to **High** - only applies safe, obvious improvements.

Future: Could add `--confidence medium` flag for more aggressive fixes.

### Branch Behavior

- ✅ Works in current branch
- ✅ Never auto-commits
- ✅ You review with `git diff` and commit when ready

## Examples

### Example 1: Duplicate Code

**Before:**
```python
def create_user(data):
    try:
        user = User.create(data)
        return {'success': True, 'user': user}
    except Exception as e:
        logger.error(f'Error creating user: {e}')
        return {'success': False, 'error': str(e)}

def update_user(id, data):
    try:
        user = User.update(id, data)
        return {'success': True, 'user': user}
    except Exception as e:
        logger.error(f'Error updating user: {e}')
        return {'success': False, 'error': str(e)}
```

**After:**
```python
def handle_user_operation(operation):
    try:
        result = operation()
        return {'success': True, 'user': result}
    except Exception as e:
        logger.error(f'User operation error: {e}')
        return {'success': False, 'error': str(e)}

def create_user(data):
    return handle_user_operation(lambda: User.create(data))

def update_user(id, data):
    return handle_user_operation(lambda: User.update(id, data))
```

### Example 2: N+1 Query

**Before:**
```python
users = User.query.all()
for user in users:
    profile = Profile.query.filter_by(user_id=user.id).first()
    user.profile = profile
```

**After:**
```python
users = User.query.all()
user_ids = [u.id for u in users]
profiles = Profile.query.filter(Profile.user_id.in_(user_ids)).all()
profile_map = {p.user_id: p for p in profiles}
for user in users:
    user.profile = profile_map.get(user.id)
```

### Example 3: Magic Numbers

**Before:**
```python
if response.status_code == 429:
    time.sleep(60)
    retry()
```

**After:**
```python
HTTP_TOO_MANY_REQUESTS = 429
RATE_LIMIT_RETRY_SECONDS = 60

if response.status_code == HTTP_TOO_MANY_REQUESTS:
    time.sleep(RATE_LIMIT_RETRY_SECONDS)
    retry()
```

## Best Practices

### ✅ Do

- **Run before committing** - Make it part of your workflow
- **Review the changes** - Use `git diff` to see what changed
- **Commit frequently** - Smaller diffs = better reviews
- **Trust high-confidence fixes** - They're designed to be safe
- **Run tests after** - Verify nothing broke

### ❌ Don't

- **Don't skip review** - Always check what was changed
- **Don't commit blindly** - Understand the fixes
- **Don't expect perfection** - It catches common issues, not everything
- **Don't use as only review** - Still do human code review for complex changes

## Limitations

This skill is **not**:
- ❌ A replacement for human code review
- ❌ A substitute for linters/formatters (use black, eslint, etc.)
- ❌ A security audit tool
- ❌ A comprehensive test suite

It's best for:
- ✅ Catching common code quality issues
- ✅ Making incremental improvements during development
- ✅ Quick pre-commit cleanup
- ✅ Learning from pattern detection

## Troubleshooting

### "No changes detected"

Make sure you're in a git repository with uncommitted changes or at least one commit.

### "All findings filtered out"

The agents found issues but none met the high-confidence threshold. Check the summary for details - you can manually review flagged issues.

### "Git command failed"

Ensure git is installed and you're in a repository:
```bash
git status
```

## Development

### Running Tests

See `evals/README.md` for test setup and execution.

### Modifying Review Agents

The three review agents are in `agents/`:
- `code_reuse_reviewer.md` - Duplication detection logic
- `code_quality_reviewer.md` - Quality issue patterns
- `efficiency_reviewer.md` - Performance problem detection

Edit these to adjust what gets flagged and how.

### Adjusting Confidence Threshold

In `SKILL.md`, search for "confidence" to find the filtering logic. You can adjust criteria for what counts as high/medium/low confidence.

## Related Skills

- **code-review** - Interactive, educational code review for learning
- **optimize** - Performance-focused with benchmarking
- **refactor** - Large architectural restructuring

Use **simplify** for quick, automated improvements during active development.

## Contributing

Found a bug or have suggestions?
1. Check existing issues in the skill-creator workspace
2. Test your changes against the eval suite
3. Submit improvements with test cases

## License

Part of the news-copilot project skill library.
