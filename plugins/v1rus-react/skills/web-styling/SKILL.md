---
name: web-styling
description: "Styling a v1rus web app through design tokens: Tailwind as the default with a CSS-variable token layer so feature code names a token and never a raw hex, spacing and radius and typography on a scale, dark mode and theming by redefining the variables rather than forking the markup, variants expressed as a closed prop mapped to token classes instead of conditional strings, where a component's styles live and when it graduates to components/ui, safe class composition and why a dynamically built class name disappears in production, and motion with prefers-reduced-motion. Load when styling a component, adding a colour or a spacing value, adding a variant, setting up or extending the theme, or reviewing markup full of raw values."
---

# Styling and Design Tokens

**Default: Tailwind over a CSS-variable token layer.** Utilities live next to the markup they style, the
output is what the app actually uses, and the token layer keeps raw values out of feature code. CSS
Modules remain a legitimate alternative for a component library shipped to other apps, or for complex
stateful CSS that reads badly as a utility string — the project's `CLAUDE.md` decides, and a project
that has already chosen wins.

## Tokens are the contract

```css
/* styles/tokens.css — the only place a raw value appears */
:root {
  --color-surface: oklch(99% 0 0);
  --color-text: oklch(20% 0 0);
  --color-danger: oklch(55% 0.2 25);
  --radius-md: 0.5rem;
  --space-4: 1rem;
}
[data-theme="dark"] {
  --color-surface: oklch(18% 0 0);
  --color-text: oklch(96% 0 0);
}
```

The Tailwind theme maps its scale names onto those variables, so `bg-surface` and `text-danger` resolve
through the token layer.

Rules:

- **No raw colour in feature code.** `bg-[#1f2937]`, `style={{ color: "#f00" }}`, `text-red-500` from the
  default palette — all three bypass the theme, and all three are invisible to a rebrand and to dark
  mode. This includes status, warning and semantic colours: add a token instead.
- Spacing, radii, font sizes, shadows and durations come from the scale. An arbitrary value
  (`p-[13px]`, `mt-[7px]`) is a design decision made in a component; either it belongs on the scale or
  it is a mistake.
- **Every token is defined for every theme.** A colour that only exists in light mode is an unreadable
  component in dark mode — and dark mode is checked before the task is done, not after a bug report.
- Tokens are semantic, not literal: `--color-danger`, not `--color-red`. A literal token renames badly
  the first time the brand changes.
- Raw values are allowed **only** inside the token layer and inside `components/ui` where a primitive's
  internals are defined.

## Composition

- Compose class names with the project's `cn` helper (class merging on top of `clsx`) so a caller's
  `className` can override a default instead of both landing in the DOM and the loser winning by
  stylesheet order.
- **A class name must exist as a complete literal in the source.** `` className={`text-${color}-500`} ``
  works in development and disappears in production because the scanner never saw the string. Map the
  variant to a full class in a lookup object.
- Express variants as a **closed prop** (`variant`, `size`, `tone`) resolved by a variant helper
  (`cva`-style) in the primitive — not as a chain of ternaries in every call site
  (`react-component-conventions`).
- Layout belongs to the parent, not the child: a component does not set its own outer margin. Pass
  layout classes from the container, or let the container's `gap` do the work. A component with a
  built-in `mb-4` is unusable anywhere else.

## Where styles live

| Style | Home |
|---|---|
| Token definitions, resets, base typography | `styles/` |
| Primitive appearance (button, input, card, badge) | `components/ui/<Primitive>.tsx` |
| Feature-specific layout and composition | the feature's component, using tokens and primitives |
| One-off page layout | the page, using the same scale |

The second time a visual pattern appears, it becomes a primitive in `components/ui` and the feature
copies are replaced. Two divergent "cards" is how a design system dies.

## Theming

- Theme switching redefines the variables on a root attribute (`data-theme`) — never forks the markup
  and never duplicates a component per theme.
- Respect the OS preference by default and let an explicit choice override it. Persisting the choice is
  a client concern: write it before first paint (a tiny inline script) or the page flashes the wrong
  theme, and remember that reading `localStorage` during render is a hydration error
  (`${CLAUDE_PLUGIN_ROOT}/rules/react.md`).
- Contrast is verified per theme, not once (`web-ui-conventions`).

## Responsive and layout

- Mobile-first: the unprefixed style is the small screen, breakpoints add. Breakpoints come from the
  scale, not from a magic `min-width` in a component.
- Prefer intrinsic layout — flex, grid, `gap`, `minmax`, container queries where supported — to counting
  pixels. Fewer breakpoints survive a content change.
- Nothing has a fixed height around text: the layout must survive 200% zoom and a longer translation
  (`web-localisation`).
- Reserve space for anything that loads late (images, embeds, ads) so the page does not shift
  (`web-performance`).

## Motion

- Transitions use the duration and easing tokens; animate `transform` and `opacity` rather than layout
  properties.
- **`prefers-reduced-motion` is honoured globally**, in the base stylesheet, so a new animation is
  covered by default instead of each author remembering.
- Motion is never the only carrier of meaning, and nothing loops indefinitely in the user's field of
  view (`web-ui-conventions`).

## Verification

A raw hex or an arbitrary spacing value in feature code is a review finding. Where the project can, make
it mechanical — a lint rule against arbitrary colour values is cheaper than a reviewer noticing
(`v1rus-typescript:ts-lint-and-format`).
