---
name: compose-ui-conventions
description: "The Compose UI and accessibility checklist a v1rus screen must satisfy before review, on Compose Multiplatform and Jetpack Compose alike: every screen handles loading / empty / error-with-retry / content (and not-found for a fetched detail), back navigation reachable in ALL states including error and loading, IconButton or an explicit 48dp target for tappable icons, contentDescription from a string resource on every interactive control, colors and typography and shapes exclusively from the app theme (never MaterialTheme directly in feature code, never a raw Color), no raw enum or status token rendered to the user, lazy lists with stable key and contentType, @Immutable UI models, no card-in-card, and active-filter indicators. Load before writing or reviewing any Compose screen or component."
---

# Compose UI Conventions

The high-frequency miss-list an implementer satisfies up front and a reviewer checks. It pre-empts
the predictable UX and accessibility findings that otherwise surface late or on-device. Not
exhaustive — for a non-trivial screen still run a `ux-expert` review, and prefer reviewing the design
before the code.

## Screen states and navigation

- Every screen handles **loading / empty / error (+retry) / content**; a fetched detail screen also
  handles **not-found**. No state is left as a blank screen.
- **Back navigation must be reachable in ALL states** — including loading and error. Hoist the top
  bar / back affordance **outside** the state `when` / `AnimatedContent`, never only in the content
  branch. A network error must never trap the user with no way out.
- Empty states carry human copy ("No results found"), not emptiness.

## Interactive elements and accessibility

- Tappable icons use **`IconButton`** (or an explicit ≥48 dp touch target) — not a bare `Icon` with
  `Modifier.clickable`, which gives a sub-48 dp target and no ripple.
- Every **interactive** icon or control has a `contentDescription` from a string resource. A purely
  decorative icon next to a text label that already names it may use `contentDescription = null` —
  decide deliberately, do not default to `null` on controls.
- Tint icons from theme tokens, never `Color.White` or a raw colour.

## Theming and text

- Colours, typography and shapes come from the **app theme only** — the project's `AppTheme`-style
  object or Material tokens. **Never `MaterialTheme.colorScheme` / `.typography` / `.shapes` directly
  in feature or design-system consumer code**, and never a hardcoded `Color(0x…)`, including
  status / weekend / semantic colours: add a theme token instead. The single exception is inside the
  design-system module where the Material plumbing is wired up.
- Never render a raw enum or status token (`WaitingForApprove`) to the user — map closed-set values to
  **localised labels** via resources. See the `localisation-and-strings` skill.
- All user-visible text comes from string resources, **including fallbacks and placeholders**. Resolve
  them in the Composable when the source is a non-Composable mapper or ViewModel.

## Lists and performance

- Lazy lists use a **stable `key`** and **`contentType`**; hoist heavy or per-item work out of the item
  lambda; `remember` expensive pure derivations (avatar colour, date/string formatting).
- UI-state and list-item models that are read-only data carriers are `@Immutable`, so Compose can skip
  them. The `stabilizing-compose-types` and `understanding-stability-inference` skills cover why.
- Avoid **card-in-card** and double elevation; keep one clickable layer per row.

## Consistency

- The same datum renders consistently across surfaces — a type icon on a list row appears in the
  calendar and detail views too.
- Match the project's existing design-system components and patterns rather than inventing a one-off.
  When a component is missing, add it to the design system, not to the feature.

## Related

`compose-animations` (every state change is animated), `compose-file-organisation` (one composable per
file, previews), `mvi-presentation` (what the screen receives and emits), and the Compose performance
skills — `optimizing-lazy-layouts`, `deferring-state-reads`, `using-strong-skipping-correctly`.
