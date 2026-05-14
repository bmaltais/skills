# Simplify Skill - Test Setup

This directory contains test scenarios for the simplify skill.

## Test Cases

### 1. duplicate-error-handling
**Scenario**: API routes with identical error handling logic that should be extracted.

**Setup**: 
- Create a Python FastAPI or Flask app with 3-4 route handlers
- Each handler has identical try/except blocks
- Expected: Skill extracts error handling to shared decorator or function

### 2. n-plus-one-query
**Scenario**: Database queries inside a loop creating N+1 problem.

**Setup**:
- Create a Python script that loads users then queries orders for each user individually
- Expected: Skill detects N+1 pattern and suggests batch query

### 3. magic-numbers-and-quality
**Scenario**: Code with hardcoded magic numbers and complex conditionals.

**Setup**:
- Create HTTP client code with hardcoded status codes and retry logic
- Include complex nested conditionals
- Expected: Skill extracts constants and simplifies logic

## Running Tests

From the skill-creator directory:

```bash
# Run all test cases
python -m scripts.run_evals \
  --skill-path ../simplify \
  --workspace simplify-workspace

# Run single test
python -m scripts.run_evals \
  --skill-path ../simplify \
  --workspace simplify-workspace \
  --eval-id 1
```

## Expected Outcomes

Each test should:
1. Correctly identify the code quality issue
2. Apply high-confidence fixes automatically
3. Show before/after summary
4. Not break functionality

Success criteria:
- All three review agents run in parallel
- Findings are aggregated correctly
- Only high-confidence fixes are applied
- Summary shows what was changed and why
