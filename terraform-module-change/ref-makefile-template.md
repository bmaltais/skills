# Makefile Template — tests/Makefile

```makefile
.PHONY: test

TEST_DIRS := $(sort $(dir $(wildcard fixtures/*/main.tf)))

## test: Run all terraform test suites under tests/fixtures/
test:
	@echo "==> Running all test suites..."
	@failed=0; \
	for dir in $(TEST_DIRS); do \
	  echo ""; \
	  echo "==> terraform test: $$dir"; \
	  (cd $$dir && terraform init -backend=false -input=false -no-color 2>&1 && terraform test -no-color) || failed=1; \
	done; \
	echo ""; \
	if [ $$failed -eq 0 ]; then \
	  echo "==> All tests passed."; \
	else \
	  echo "==> One or more test suites FAILED."; \
	  exit 1; \
	fi
```

The glob `fixtures/*/main.tf` auto-discovers new suites — no Makefile edits
needed when adding future fixtures.
