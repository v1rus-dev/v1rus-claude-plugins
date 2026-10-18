---
paths:
  - "**/ui/**/*.kt"
  - "**/presentation/**/*.kt"
  - "**/designsystem/**/*.kt"
  - "**/*Screen*.kt"
  - "**/*Destination*.kt"
  - "**/*Composable*.kt"
  - "**/*Component*.kt"
  - "**/*Theme*.kt"
---

# Compose screen quality checklist

High-frequency miss-list for an implementer to satisfy up front and a reviewer to check. Not exhaustive: for a non-trivial screen also run a ux-expert review, preferably on the plan/design as well as the code. Deeper procedure: skill `compose-screen-checklist`.

## Screen states and navigation
- Every screen handles loading / empty / error (with retry) / content; a fetched detail screen also handles not-found. No blank state.
- Back navigation is reachable in ALL states, including loading and error: hoist the top bar/back affordance outside the state `when`/`AnimatedContent`. A network error never traps the user.
- Empty states carry human copy ("No results found"), not emptiness.

## Interactive elements and accessibility
- Tappable icons use `IconButton` (or an explicit >=48dp touch target), not bare `Icon` + `Modifier.clickable` (small target, no ripple).
- Every interactive icon/control has a `contentDescription` from a string resource. A decorative icon beside a text label that already names it may use `null`; decide deliberately, never default to null on controls.
- Tint icons from theme tokens, never `Color.White` or raw colors.

## Theming and text
- Colors, typography, shapes from the app theme only (design-system or Material tokens); no `Color(0x...)` in feature code, including status/weekend/semantic colors (add a theme token).
- Never render a raw enum/status token to the user: map closed-set values to localized labels via resources.
- All user-visible text via string resources, including fallbacks and placeholders (resolve in the composable when the source is a non-composable mapper/ViewModel); free-form server text is shown as is.
- When filters/sorting are active but not visible on the current surface, show an active-state indicator (badge/count).

## Lists and performance
- Lazy lists use a stable `key` and a `contentType`; hoist heavy per-item work out of the item lambda; `remember` expensive pure derivations (avatar color, date/string formatting).
- Read-only UI-state and list-item models are `@Immutable` where the project's stability setup calls for it.
- No card-in-card or double elevation; one clickable layer per row.

## Consistency
- The same datum renders the same way across surfaces (a type icon on a list row also appears in the detail view).
- Reuse established design-system components and patterns instead of one-offs.
