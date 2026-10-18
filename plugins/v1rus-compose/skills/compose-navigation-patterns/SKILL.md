---
name: compose-navigation-patterns
description: "v1rus navigation conventions for Compose — Compose Multiplatform and Jetpack Compose alike (Navigation3-style typed routes): a single nav display driven by an app navigator, app-wide routes centralised in the navigation module while feature destination keys stay in the owning feature, every route @Serializable and registered in a SerializersModule or saved-state restoration silently breaks, features never import each other's destinations, replaceCurrent versus replaceAll semantics — and the non-negotiable that dialogs and bottom sheets are navigation destinations, never `if (show) { AlertDialog/ModalBottomSheet }`, with results returned through a result store and consumed once per back-stack entry. Load when adding a screen, route, dialog or bottom sheet, or when a dialog needs to return a value."
---

# Compose Navigation Patterns

Concrete type names (`AppNavigator`, `NavDisplay`, `ResultStore`, the scene strategies) are the
project's — **find them in the project's navigation module before writing code.** This skill is the
set of rules those types exist to enforce.

The rules hold on both androidx Navigation and the JetBrains KMP navigation fork; those differ in
artifact coordinates and version numbering only.

## Routes

- One nav display for the app, driven by a single navigator whose state lives in the shared navigation
  module.
- **App-wide routes live in the navigation module**; a **feature's own destination keys live inside
  that feature**. A bottom-sheet route used exclusively within one feature may stay in that feature.
- Every route is `@Serializable` **and registered in the appropriate `SerializersModule`**. This is the
  rule that breaks silently: an unregistered key does not fail at compile time, it fails as lost state
  after process death.
- **Feature modules never import another feature's screen or destination.** Cross-feature navigation
  goes through a public contract. On a KMP project, also see `v1rus-kmp:kmp-conventions`.
- Know the navigator's stack primitives before choosing one: "replace current" (redirect that leaves
  nothing behind — splash, auth) versus "replace all" (clear the stack). Pushing where a redirect was
  meant leaves a dead screen on the back stack.

## Dialogs and bottom sheets are destinations

**Always** implement a dialog or a bottom sheet as a navigation destination. Never:

```kotlin
// BAD — both of these
if (showConfirm) { AlertDialog(onDismissRequest = { showConfirm = false }, …) }
if (showSheet) { ModalBottomSheet(onDismissRequest = { showSheet = false }) { … } }
```

Inline conditional dialogs do not survive process death, do not participate in back handling, and
duplicate chrome the scene strategy already provides. The destination form gives all three for free.

Steps: define the `@Serializable` route → register it with the dialog / bottom-sheet scene strategy in
DI (global routes in the app module, feature-local ones in the owning feature's module) → write the
content composable as a styled card or sheet body, **without** calling `Dialog { }` / `ModalBottomSheet`
yourself, since the scene strategy owns the chrome.

**Prefer the project's pre-built global dialogs first** (a confirm dialog, an info dialog, a
session-expired notice). Creating a bespoke route for a plain yes/no question is the most common
avoidable duplication here.

## Returning a result

Results travel through the project's result store keyed by a `resultKey` carried on the route — not
through shared ViewModel state, which is fragile across process death.

- The dialog sets the result, then pops.
- The caller reads it with a get-and-remove inside a `LaunchedEffect` keyed on the current back-stack
  entry, so it fires exactly once when the destination closes.
- **Dismissing without pressing a button stores no result — absence of a result means cancellation.**
  Handle that branch; a caller that treats `null` as "nothing happened" silently swallows the action.

## Anti-patterns

- A route declared without `@Serializable`, or not added to the `SerializersModule`.
- A bespoke confirm-dialog route where the shared one fits.
- Popping without setting a result the caller is waiting for.
- Collecting navigation effects inside the pure `*Screen` instead of the `*Destination` (see
  `mvi-presentation`).
