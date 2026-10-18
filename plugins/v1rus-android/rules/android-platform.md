---
paths:
  - "**/src/main/**/*.kt"
  - "**/androidMain/**/*.kt"
  - "**/*ViewModel*.kt"
  - "**/*Activity*.kt"
  - "**/*Fragment*.kt"
  - "**/*Service*.kt"
  - "**/AndroidManifest.xml"
  - "**/res/**/*.xml"
---

# Android platform rules

Android-only conventions; Kotlin, coroutine and Compose rules from the lower layers still apply.

## Scopes and lifecycle
- `viewModelScope` / `lifecycleScope` belong to the Android presentation layer only, never to use cases or repositories. Work that must outlive a screen uses an injected application-scoped `CoroutineScope`.
- Collect flows lifecycle-aware, otherwise a `stateIn(WhileSubscribed(...))` upstream never stops: Compose `collectAsStateWithLifecycle()`; Views `flowWithLifecycle()` or `repeatOnLifecycle(Lifecycle.State.STARTED)`. Plain `collect` in `lifecycleScope.launch` or plain `collectAsState()` keeps collecting in the background.
- Tests of code using `viewModelScope` replace Main first (`Dispatchers.setMain(testDispatcher)` in setup, `resetMain()` in teardown).

## Leaks
- Do not hold an `Activity`, `Fragment`, `View` or UI `Context` in a ViewModel, singleton or long-lived coroutine; use the application context when a context is needed there.
- Lambdas and inner classes passed to long-lived objects capture their outer class: unregister listeners and receivers in the matching lifecycle callback.

## Resources
- User-visible strings live in `res/values` string resources (localizable); do not hardcode text in Kotlin or layouts. Resolve strings in the UI layer when the source is a non-UI mapper.
- Colors and dimensions come from theme/resources, not literals in code.

## Platform docs
- For Android/Jetpack/AGP/SDK API questions use the skill `android-api-verification` (Android docs search plus `ksrc` in parallel) instead of memory.
