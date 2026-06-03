# Editor & Linting Setup

## VS Code Settings

```json
// .vscode/settings.json
{
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true,
  "editor.formatOnSave": true,
  "[markdown]": {
    "editor.defaultFormatter": "DavidAnson.vscode-markdownlint",
    "editor.wordWrap": "on"
  }
}
```

## Recommended Extensions

- **DavidAnson.vscode-markdownlint** — Real-time linting against markdownlint rules
- **yzhang.markdown-all-in-one** — Shortcuts, TOC generation, preview

## markdownlint Configuration

Create `.markdownlint.json` or `.markdownlint.yaml` at project root:

```json
{
  "default": true,
  "MD013": false,
  "MD033": { "allowed_elements": ["br", "details", "summary"] },
  "MD041": true
}
```

Key rules:
- **MD013** (line length) — Often disabled for prose-heavy docs
- **MD033** (no inline HTML) — Allow specific elements if needed
- **MD041** (first line heading) — Ensures document starts with H1

## CI Integration

```yaml
# GitHub Actions
- name: Lint Markdown
  uses: DavidAnson/markdownlint-cli2-action@v16
  with:
    globs: '**/*.md'
```

## Writing Workflow

1. Start with a template (README, Guide, API doc)
2. Write content following heading hierarchy
3. Validate with markdownlint as you write (VS Code extension)
4. Review rendered output in preview pane
5. Run CI lint check before merge

## Additional Resources

- [Markdown Guide](https://www.markdownguide.org/)
- [CommonMark Spec](https://spec.commonmark.org/0.31.2/)
- [markdownlint Rules](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md)
