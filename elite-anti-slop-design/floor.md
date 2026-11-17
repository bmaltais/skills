# Floor

Every rule applies in Build step 5 and in Audit. A Floor fail blocks shipping.

## Floor

- **Contrast**: 4.5:1 text, 3:1 large text and UI boundaries.
- **Focus**: visible `:focus-visible` on every interactive element; everything keyboard operable.
- **Labels**: every input has a real label; placeholders are hints.
- **Reduced motion**: `prefers-reduced-motion` removes or shortens every animation.
- **Truth**: every metric, testimonial, photo and data point is real or labelled placeholder.
- **Responsive**: usable at 375px with no horizontal scroll and no overlapping content.
- **Content without script**: text and primary actions render before any JS runs.
- **Motion has a cause**: a user action, or one orchestrated moment per view. Enter animations are suppressed on first load where they only delay content.
- **Basics**: images carry dimensions and alt text; semantic HTML; touch targets at least 44×44px (extend the hit area if the visual is smaller).
- **Hero fit**: the hero shows the subject's most characteristic thing.

## Tells

Each tell is a Floor fail; the replacement is in brackets.

- Warm cream with terracotta and a serif; near-black with acid green or vermilion; broadsheet hairline rules. [Palette drawn from the subject's materials.]
- Identical rounded cards with soft gray shadows and gradient washes; cards nested in cards. [One surface level; hierarchy from type and spacing.]
- An eyebrow label above every heading; tracked ALL-CAPS labels; "WORD — fragment" labels; middle-dot meta strings. [Heading alone; labels only where they encode information.]
- One colored or italic word in a headline. [Whole-line emphasis through size or weight.]
- Monospace for all small data. [Mono only for code and aligned figures.]
- "→" on every button. [Arrow only where it signals navigation direction.]
- Inter, Poppins or Montserrat as the display face. [A deliberate pairing of 1–2 families.]
- Purple-to-blue gradient as decoration. [Color that carries meaning.]
- Scroll-reveal fade-and-slide on every section. [One orchestrated entrance.]
- Numbered markers on things that are not a sequence. [Numbers only for real order.]

## Reflex

Overridable with a written reason tied to the brief: big-number hero stat rows, three-column feature grids, a centered hero with two buttons, an emoji or generic icon per feature, pill badges, glassmorphism, a testimonial strip, a closing CTA band that repeats the hero.

## Verification

Browser-checked at 375, 768 and 1280. Where a lint or axe-style checker exists in the project, run it as well; a clean checker does not replace the visual pass.
