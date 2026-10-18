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

# Compose rules: non-obvious

Only what a model omits without a reminder; generic Compose idioms (`remember`, state hoisting, `derivedStateOf`, naming) are assumed. Project conventions override these. Applies to Jetpack Compose and Compose Multiplatform alike. Coroutine/Flow collection inside composables follows the Kotlin coroutines rule.

## Destination and Screen

- The stateful entry point (`*Destination` or the project's equivalent) resolves the ViewModel/state holder, collects state, handles one-shot effects and navigation, and delegates to a stateless `*Screen(state, onIntent/lambdas)`.
- Resolve the ViewModel once at the navigation entry point, never inside the Screen and never inside reusable components. A ViewModel is never a composable parameter (breaks reuse and previews).
- Entry point is public; Screen and per-state parts are `internal`. Render each state in a dedicated composable (loading/error/content parts), not one giant `when` in the Screen body.
- Collect state lifecycle-aware where the platform provides it (`collectAsStateWithLifecycle()` on Android); match the project's established call.

## Forbidden parameter types

Never accept `MutableState<T>` (hoist as `value: T` + `onValueChange: (T) -> Unit`), `State<T>` (pass the value), or a `ViewModel`.

## Custom modifiers: `Modifier.Node`, not `composed {}`

`Modifier.composed {}` is deprecated and slower. Plain extension chain for combinations of existing modifiers; a `@Composable` modifier factory only when it needs animation or a `CompositionLocal`; `Modifier.Node` + `ModifierNodeElement` for draw/layout/input/semantics. Verify the Node API against the pinned Compose version (skill `compose-api-verification`).

## Stability

Whether `@Stable`/`@Immutable` matter depends on compiler configuration. With strong skipping (default in current compilers) annotations are mostly documentation and plain `List`/`Map` skip fine. With strong skipping disabled or an old compiler they matter and collections are unstable (use immutable collections if the project does). Match the project's convention; check a stability config file for cross-module rules.

## Phase deferral

Prefer lambda modifier overloads for frequently changing state: `offset { }`, `drawBehind { }`, `graphicsLayer { }` instead of `offset(x = ...)`, `background(animatedColor)`. Pass `() -> T` instead of `T` to custom composables whose value changes often.

## Long-lived effects

Inside `LaunchedEffect(Unit)`/`DisposableEffect`, captured lambdas are from effect start. Wrap with `rememberUpdatedState` to keep the latest callback without restarting the effect.

## Exhaustive `when`

`when` over a sealed state/intent/effect type has no `else` branch, so adding a subtype is a compile error. Never `else -> {}` to silence the compiler.

## Theme tokens

If the project has a token system, no raw `dp` literals or hex colors in screen code. If it uses the Material theme directly, match that.

## Accessibility beyond contentDescription

- `Modifier.semantics { role = Role.Button }` (or `clickable(role = ...)`) on custom interactive composables.
- `mergeDescendants = true` on compound rows read as one unit.
- `Modifier.minimumInteractiveComponentSize()` when an interactive visual is under 48x48 dp.

## Multiplatform targets

- No `android.*`/`java.*` in `commonMain` UI code; platform UI behind `expect`/`actual` or platform source sets.
- The Compose resources API has changed across versions: read the project's existing resource usage, do not assume.
- Check that every library used in common code has multiplatform artifacts.

## Previews

A preview gets hardcoded sample state, never a ViewModel, repository or real data. Previews are `private` and wrapped in the project's theme. Cover loading/error/empty/populated for screens. Preview Screens and components only, not Destinations or utility functions.
