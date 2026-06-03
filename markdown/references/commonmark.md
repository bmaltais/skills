# CommonMark Syntax Rules

Reference for CommonMark 0.31.2 compliance.

---

## Headings

- ATX style: 1–6 `#` followed by a space.
- Setext (`===`/`---`) allowed by spec but **discouraged** for consistency.
- Blank line before and after headings.

```markdown
# H1 Heading

## H2 Heading

### H3 Heading
```

---

## Thematic Breaks

3+ matching `-`, `_`, or `*` on a line with only spaces/tabs otherwise.

```markdown
---
```

---

## Code Blocks

- Use 3+ backticks or tildes for fences.
- Info string (language) after opening fence.
- Do **not** include backticks in info string.

✓ Correct:

````markdown
```javascript
const x = 1;
```
````

✗ Incorrect:

````markdown
```[javascript]
const x = 1;
```
````

---

## Lists

- Bullets: `-`, `+`, `*` (prefer `-` for consistency)
- Ordered: `1.` or `1)` — use `1.` style
- Indent sublists to content column (typically 2 or 4 spaces)
- Blank line between list items if any item has multiple paragraphs

```markdown
- First item
- Second item
  - Nested item
- Third item
```

---

## Links & Images

- Inline: `[text](url)` or `[text](url "title")`
- Reference: `[text][ref]` with `[ref]: url` definition
- No whitespace before `(` or `[`
- Images: `![alt text](src "title")` — alt text must be non-empty

```markdown
[Markdown Guide](https://www.markdownguide.org/)

![Logo](images/logo.png "Company Logo")
```

---

## Autolinks

- Use `<URL>` or `<email@example.com>` for autolinks
- Bare URLs (`https://example.com`) are **not** auto-linked in CommonMark
- Always use full link syntax for URLs in prose

---

## Emphasis

| Syntax     | Result   |
| ---------- | -------- |
| `*text*`   | *italic* |
| `**text**` | **bold** |

- Prefer `*` over `_` to avoid conflicts with code identifiers
- `_` does not work for intraword emphasis (`foo_bar_baz` stays literal)

---

## Inline HTML

- Allowed by spec but avoid unless necessary
- Use Markdown equivalents when available
- Raw HTML blocks need blank lines before and after

---

## Paragraphs & Line Breaks

- Blank line between paragraphs
- Hard line break: trailing `\` or two spaces (prefer `\` for visibility)
- Keep paragraphs to 3–5 sentences

---

## Tables

```markdown
| Header 1 | Header 2 | Header 3 |
| -------- | -------- | -------- |
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
```

- Always include a header row
- Use alignment colons sparingly (`:---`, `:---:`, `---:`)
- Avoid nested tables
- Keep tables simple — complex data belongs in code blocks or external files
