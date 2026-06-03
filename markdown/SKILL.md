---
name: markdown
description: >
  Comprehensive Markdown best practices and formatting rules, aligned with
  markdownguide.org, markdownlint, and CommonMark spec 0.31.2. Use when writing
  or reviewing Markdown files. Trigger on phrases like "format this markdown",
  "markdown best practices", "fix my markdown", "lint markdown", "markdown style".
applyTo: '**/*.md'
categories: [documentation]
agents: [copilot]
version: 1.0.0
metadata:
  source: custom
  scope: global
---

# Markdown Documentation & Formatting

Write Markdown that is correct, consistent, clear, and accessible.

## Core Principles

1. **Consistency** — ATX headings, `-` for lists, `**bold**`/`*italic*`, fenced code blocks with language IDs.
2. **Clarity** — Descriptive headings, logical hierarchy, short paragraphs, active voice.
3. **Correctness** — Passes all markdownlint rules, aligns with CommonMark 0.31.2.
4. **Accessibility** — Descriptive link text, meaningful alt text, no skipped heading levels.

## Routing Table

| Topic                                    | Reference                   |
| ---------------------------------------- | --------------------------- |
| CommonMark syntax rules & compliance     | `references/commonmark.md`  |
| Editor setup & linting configuration     | `references/tooling.md`     |
| Validation checklist                     | `references/checklist.md`   |

## Key Rules (Always Apply)

- Use ATX-style headings (`#`) only — never setext (`===`/`---`).
- Only one H1 per document.
- No skipped heading levels (H1 → H2 → H3, not H1 → H3).
- Fenced code blocks **must** specify a language identifier.
- No trailing whitespace; file ends with a single newline.
- No bare URLs — use `[text](url)` link syntax.
- Use `-` for unordered lists (not `*` or `+`).
- Match existing style when editing a file.
