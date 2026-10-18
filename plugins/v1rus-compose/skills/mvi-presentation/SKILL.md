---
name: mvi-presentation
description: "The v1rus MVI presentation shape for Compose screens: a store-style ViewModel typed over State / Intent / Effect, UI sends intents through one onIntent entry point, one-shot side effects come back as effects collected in the Destination composable, State/Intent/Effect for a screen live together in a single ModelUi file, and the Destination-versus-Screen split (Destination owns navigation and DI, internal Screen is pure state plus onIntent, each state rendered by a dedicated Part composable taking only its slice). Load when creating or refactoring a screen, a ViewModel, or its state/intent/effect model."
---

# MVI Presentation

The presentation layer of a v1rus Compose feature. Concrete base-class and helper names are the
project's (`StoreViewModel`, `CollectEffectsUiEvent`, and similar) — **find them in the project before
writing code**; this skill is the shape they implement.

## The store

A stateful screen is driven by a ViewModel typed over three contracts —
`ViewModel<State, Intent, Effect>`:

- **State** — everything the screen renders. Immutable, `@Immutable`, one object.
- **Intent** — everything the user (or the screen lifecycle) can ask for. The UI sends these through a
  single `onIntent(...)` entry point; there is no second channel.
- **Effect** — one-shot side effects that are *not* state: navigate, show a snackbar, close a sheet.
  Collected in the `*Destination` composable, never inside the pure screen.

Discipline inside the store:

- Keep `init { }` minimal — move orchestration into named functions so the initialisation order is
  readable and testable.
- In `onIntent`, if a `when` branch needs more than one call, extract a private function and call only
  that. A `when` that inlines multi-step logic stops being a dispatcher.
- A plain MVI store without a ViewModel is acceptable for narrowly scoped behaviour that has no
  lifecycle of its own.

## The model file

**`State`, `Intent` and `Effect` for one screen are never split across files.** All three live
together in a single `<FeatureName>ModelUi.kt`. Reading the screen's contract must be one file open,
not three.

## Destination ⇄ Screen split

| Layer | Owns | Visibility |
|---|---|---|
| `*Destination` | navigation dependencies, route params, obtaining the ViewModel from DI, collecting state, observing effects, performing navigation | public (it is the navigation entry point) |
| `*Screen` | pure rendering from `state` + `onIntent`. No navigation, no DI, no effect collection | `internal` |
| `*Part<State>` | rendering one state branch, in a sibling `components/` package; takes only the slice of state it needs | `internal` |

`*Screen` does `when (state)` and delegates to the matching `*Part*`; it does not inline branch UI.
Marking `*Screen` and every `*Part*` `internal` is what keeps a feature module's surface to its
destinations, which is what makes the "features must not depend on each other" rule enforceable (on a
KMP project, also see `v1rus-kmp:kmp-conventions`).

Because the pure `*Screen` takes only data and callbacks, it is previewable and testable without DI —
that is the point of the split, not a side effect.

## Related

`compose-screen-architecture` for the full worked reference architecture including previews,
`compose-file-organisation` for how these composables are laid out in files,
`compose-navigation-patterns` for effects that navigate, dialogs and bottom sheets, and
`v1rus-kotlin:kotlin-coroutines` for `stateIn` / lifecycle-aware collection.
