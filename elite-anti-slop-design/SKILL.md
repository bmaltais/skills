---
name: elite-anti-slop-design
description: Build, audit or redesign UI with a distinctive, subject-specific identity instead of generic AI output. Invoke as /elite-anti-slop-design [build|audit|redesign|document] <target>.
disable-model-invocation: true
---

# Elite Anti-Slop Design

Product: an interface whose look is *earned* by its subject: swap in a different product and the design would need rewriting. Verified in a real browser, with zero **Floor** fails.

Vocabulary used throughout:
- **Tell**: a generic default that marks output as AI-made.
- **Floor**: a hard fail. Never ships. Listed in [floor.md](floor.md).
- **Reflex**: a choice a model makes for any similar brief. Allowed only with a written reason tied to this brief.
- **Finish**: polish. Desirable, never blocks. Details in [craft.md](craft.md).
- **Signature**: the one place boldness is spent. Everything else stays quiet.

## Mode

The first word of the argument picks the mode; no mode word means **build**. Targeted passes (type, layout, color, motion, distill) are **audit** limited to that axis, with fixes applied.

### Build

1. **Ground.** Name the subject, the audience and the primary job (book, buy, subscribe, operate, read, persuade) in one line each; propose them when the user gave none. The primary action sits where the category puts it, and the page ends on it.
   Done when every fact, metric, photo and quote on the page traces to the user or to a placeholder labelled as one.
2. **Pre-flight.** Read DESIGN.md, PRODUCT.md, tokens, fonts, palette, framework and components, and keep their constraints. With no system present, write a compact DESIGN.md first: 4–6 named colors, type roles and scale, spacing and radius tokens, principles.
   Done when the system in force is either adopted or written down.
3. **Plan.** Write the palette (named, hex or oklch), type families and roles, an ASCII wireframe with alignment, the signature, and the principles. Open on the most characteristic thing in the subject's world. Then run the **Reflex** review: for each choice ask "is this what I would pick for any similar brief?" and revise it, noting why. Consecutive pages and screens must not repeat the same hero → features → CTA rhythm.
   Done when each choice is either subject-specific with its reason written, or revised.
4. **Build** in the project's stack, tokens at the root, decisions stamped in DESIGN.md or a comment.
5. **Critique.** Load the page in a real browser at 375, 768 and 1280 widths and screenshot each. Apply [floor.md](floor.md) in full, then remove one accessory (the Chanel rule).
   Done when every Floor rule has been checked against what the browser shows and no fail remains.
6. **Report.** List what changed for uniqueness and why, every Reflex override with its reason, and any placeholder still standing in for a real asset.

### Audit

Walk every rule in [floor.md](floor.md), then judge hierarchy, type, spacing, contrast and motion against [craft.md](craft.md). Report findings ranked Floor, then Reflex, then Finish, each with file:line and the fix. Apply fixes only when asked.
Done when every rule in floor.md has a verdict.

### Redesign

Keep content and wiring. Rebuild structure and visual direction through Build steps 3–6.

### Document

Extract DESIGN.md and PRODUCT.md from the existing code.
Done when every token and rule in the files exists in the code.

## Companion skills

`better-ui`, `better-colors`, `better-layout` and `better-interface` hold exact polish values, contrast measurement, layout structure and a ranked review. Where one is installed, its values win over [craft.md](craft.md), and Build step 5 may run `better-interface` on the result. This skill adds direction, the Floor and the gates. Run one director at a time.
