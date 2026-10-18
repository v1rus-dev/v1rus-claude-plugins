---
name: compose-animations
description: "v1rus rule that every state-driven UI change in Compose is animated — an instant swap is a bug caught in review. Maps each kind of change to its API (AnimatedContent for a when/if that swaps composables, AnimatedVisibility for enter/leave, animateColorAsState / animateFloatAsState / animateDpAsState for values, Modifier.animateContentSize for containers, updateTransition for coordinated properties), gives transitionSpec recipes, and lists the mistakes that recur — missing label, contentKey on data-carrying state, and text fields inside AnimatedContent destroying focus. Load before writing or reviewing any Compose UI that reacts to state."
---

# Compose Animations

**Every UI change driven by state is animated. An instant swap is a bug, caught in review.**

Applies to Compose Multiplatform and Jetpack Compose alike.

## The mapping, applied without being asked

| The change you are writing | What to use |
|---|---|
| `when (state)` / `if/else` swapping different composables | `AnimatedContent` |
| `if (visible) { … }` — element enters or leaves the layout | `AnimatedVisibility` |
| a color | `animateColorAsState` |
| a number / size / offset / alpha | `animateFloatAsState` / `animateDpAsState` |
| a container that grows or shrinks with its content | `Modifier.animateContentSize()` |
| several values that must move on one timeline | `updateTransition` + `animate*` |

## `AnimatedContent` — content switches

Never leave a `when` that renders different UI branches as a bare instant switch.

```kotlin
AnimatedContent(
    targetState = state.displayMode,
    transitionSpec = {
        (fadeIn(tween(DEFAULT_DURATION)) + slideInVertically { it / 6 }) togetherWith
            (fadeOut(tween(DEFAULT_DURATION)) + slideOutVertically { -it / 6 })
    },
    label = "displayModeContent",
) { mode -> /* branch content */ }
```

### `transitionSpec` recipes

| Feel | Spec |
|---|---|
| Soft crossfade | `fadeIn(tween(d)) togetherWith fadeOut(tween(d))` |
| Slide from bottom (tab switch) | `fadeIn() + slideInVertically { it / 6 } togetherWith fadeOut() + slideOutVertically { -it / 6 }` |
| Slide from top (header reveal) | `slideInVertically { -it } + fadeIn() togetherWith slideOutVertically { -it } + fadeOut()` |
| Horizontal page flip | `slideInHorizontally { it } + fadeIn() togetherWith slideOutHorizontally { -it } + fadeOut()` |
| Scale pop | `scaleIn(initialScale = 0.92f) + fadeIn() togetherWith scaleOut(targetScale = 0.92f) + fadeOut()` |

## `AnimatedVisibility` — show / hide

```kotlin
AnimatedVisibility(
    visible = state.isLoading,
    enter = fadeIn() + expandVertically(),
    exit = fadeOut() + shrinkVertically(),
) { LinearProgressIndicator(Modifier.fillMaxWidth()) }
```

## Single-value animation

`animate*AsState` defaults to `spring()`, which is physically natural; override with `tween()` when a
fixed duration is required. Pull the duration from the project's animation-constants object in the
design system — **never hardcode a numeric duration**, and if the project has no such constant, add
one rather than inlining a number.

```kotlin
val progress by animateFloatAsState(
    targetValue = fraction.coerceIn(0f, 1f),
    animationSpec = tween(durationMillis = DEFAULT_DURATION),
    label = "dayProgress",
)
```

Colors come from the app theme's tokens, never from raw `Color(0x…)` — see the
`compose-ui-conventions` skill.

## `updateTransition` — coordinated properties

When several values are driven by the same state, share one timeline instead of writing three
independent `animate*AsState` calls:

```kotlin
val transition = updateTransition(targetState = isSelected, label = "chipSelected")
val scale by transition.animateFloat(label = "scale") { if (it) 1.05f else 1f }
val background by transition.animateColor(label = "bg") { if (it) accent else chipBackground }
```

## Rules that go with it

- **Always pass `label =`.** It names the animation in the Compose animation inspector; without it
  the tooling is useless.
- **`AnimatedContent` over a data-carrying state needs `contentKey`.** With `Content(items)` as the
  target state, every data update replays the whole transition — key on what actually distinguishes
  the branches, e.g. `contentKey = { it::class }`.
- **Never put a `BasicTextField` / `TextField` inside an `AnimatedContent` branch.** Swapping it out
  destroys focus and the IME connection, so the user cannot type. Keep the field always composed and
  animate the *placeholder* over it with `AnimatedVisibility`.

## Mistakes that recur

- Animating a color toward a "neutral / invisible" value in order to hide something → animate alpha
  with `animateFloatAsState`, or use `AnimatedVisibility`.
- An instant `when` between different composables → wrap in `AnimatedContent`.
- `if (visible) { ModalBottomSheet(...) }` → a bottom sheet is a navigation destination; see the
  `compose-navigation-patterns` skill.
- `tween(0)` or no spec on a trivial change → even 150–200 ms is the difference between "cheap" and
  "polished".
