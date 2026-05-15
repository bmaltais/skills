---
name: ai-brain-wiki
description: Maintain and operate the AI-Brain wiki — run lint, search, ingest, and fix common issues. Covers path facts, tool commands, and known pitfalls discovered during use.
categories: [note-taking]
agents: [pi, hermes, claude, copilot]
version: 1.0.0
tags: [wiki, ai-brain, lint, search, maintenance]
metadata:
  source: custom
  scope: global
---

# AI-Brain Wiki Maintenance

## Key Facts

- Wiki root: ${AI_BRAIN_ROOT:-$HOME/AI-Brain} (NOT ~/OneDrive/AI-Brain)
- Tools: tools/lint.py, tools/search.py, tools/fix-media.py, tools/tl.py
- Wiki pages: wiki/
- Raw sources (immutable): raw/
- Search index: .qmd/ (auto-generated)
- Run all tools with: uv run python tools/<tool>.py

## Search

```bash
# Build/rebuild index (required first time each session or after ingest)
cd ${AI_BRAIN_ROOT:-$HOME/AI-Brain}
uv run python tools/search.py index wiki/

# Search
uv run python tools/search.py search "your query"
```

Index is cached in .qmd/ — only rebuild if stale (after new ingests).

## Lint

```bash
cd ${AI_BRAIN_ROOT:-$HOME/AI-Brain}
uv run python tools/lint.py
```

Run after every ingest. Fix all issues before ending session — they compound.

### Common lint issues and fixes

1. Missing Counter-arguments section in concept page
   - Add "## Counter-arguments and data gaps" (exact casing — all lowercase after first word)
   - Minimum 4-6 bullet points; include strongest external critique even if all sources agree

2. Broken link [[some-slug]]
   - Check if the target file actually exists: search_files for the slug in wiki/
   - If it's a false positive from a code block: the lint.py bug was fixed (strips backtick spans before scanning links) — but re-check if lint.py was reverted
   - If genuinely broken: create the missing page or fix the wikilink

3. Heading casing mismatch
   - Lint checks for EXACT string "## Counter-arguments and data gaps"
   - Pages that wrote "## Counter-arguments and Data Gaps" (capital D/G) will fail
   - Fix: lowercase the heading

4. Orphan pages
   - Every page needs ≥1 inbound link from another wiki page AND entry in index.md
   - Add wikilink from a related page and add row to index.md

## Known lint.py fix (applied 2026-04-11)

lint.py was patched to strip fenced code blocks (``` ```) and inline code spans (` `) before scanning for wikilinks. This prevents false-positive broken link reports when wikilinks appear as examples inside code spans.

If you see a broken link that looks like it lives inside backticks in the source file, check if lint.py has this fix:

```python
# 4. Broken links — strip code blocks and inline code first
content_no_code = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
content_no_code = re.sub(r'`[^`\n]+`', '', content_no_code)
links = re.findall(r'\[\[(.*?)\]\]', content_no_code)
```

If missing, patch tools/lint.py to add it.

## Ingest workflow (summary)

1. Check ingest-manifest.md for dedup
2. Read + classify source
3. Write wiki/sources/<slug>.md
4. Update entities/, concepts/, overview.md as needed
5. Update index.md
6. Append log.md
7. Run: uv run python tools/fix-media.py --apply
8. Run: uv run python tools/search.py index wiki/
9. Every 5th ingest: PYTHONIOENCODING=utf-8 mempalace mine wiki/
10. Run lint: uv run python tools/lint.py — fix all issues
11. Append to ingest-manifest.md
