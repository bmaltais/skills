# Validation Checklist

Use before committing any Markdown file.

## Syntax & Structure

- [ ] ATX headings use 1–6 `#` followed by a space
- [ ] Only one H1 per document
- [ ] No skipped heading levels (H1 → H2 → H3)
- [ ] Blank lines before and after headings
- [ ] Blank lines before and after code blocks

## Code Blocks

- [ ] All fenced code blocks specify a language identifier
- [ ] Matching fence characters (don't mix backticks and tildes)
- [ ] No backticks in info string

## Lists

- [ ] Consistent markers (`-` for unordered)
- [ ] Proper indentation for nested items
- [ ] Blank line before and after list blocks

## Links & Images

- [ ] All links use descriptive text (not "click here" or "link")
- [ ] All images have meaningful alt text
- [ ] No bare URLs — use `[text](url)` syntax
- [ ] No broken links (validate periodically)

## Formatting

- [ ] No trailing whitespace
- [ ] File ends with a single newline
- [ ] Tables have header rows
- [ ] Emphasis uses `*` not `_`

## Accessibility

- [ ] Heading hierarchy is logical and navigable
- [ ] Alt text describes image content for screen readers
- [ ] Link text makes sense out of context
- [ ] Tables are simple (no nested tables)

## Final Check

- [ ] Passes all markdownlint rules
- [ ] Rendered output looks correct in preview
- [ ] Matches existing file style (if editing)
