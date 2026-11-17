# Craft (Finish)

Finish never blocks. If `better-ui`, `better-colors` or `better-layout` is installed, its exact values win.

## Direction and type
- 1–2 families, clearly distinct when two. One scale, intentional weights.
- Line length under 80 characters. `text-wrap: balance` on headings, `pretty` on body.
- Borders, numbers and labels encode information.

## Surfaces
- Concentric radius: outer = inner + padding.
- Optical alignment over geometric where they disagree.
- Layered transparent `box-shadow` for elevation; borders for structure and state.
- Image outline: 1px, pure black at low opacity in light, pure white in dark.
- Icons: one stroke weight per set, matched to adjacent text; `currentColor`; outline by default, filled for active.
- `antialiased` font smoothing on the root; `tabular-nums` on dynamic figures.

## Motion
- High-frequency interactions get a static cue first (color, icon, label).
- Transition named properties only; `transform` and `opacity` preferred; interruptible.
- Press scales to 0.96, never below 0.95. Stagger about 100ms only for infrequent staged content.
- Demos of product UI: simplify to what the viewer needs, keep real chrome and icons, record the result and watch it.
- Shaders and scroll effects only where the subject (tech, gaming, software) justifies them, with a static fallback.

## System
- Tokens at the root; a literal hex or font-family elsewhere is a defect.
- Consistent radii, spacing and component variants.
- Theming through `color-scheme` and tokens.
- Real photos, brand icons and product UI over stock or illustration; credit where required.

## Forms and interaction
- `autocomplete` set, validation inline and clear, errors specific.
- Important state lives in the URL.
- One primary action per screen; pending and active states look different.
- Locale-aware formatting for dates, numbers and currency; `touch-action` and tap highlight handled.
