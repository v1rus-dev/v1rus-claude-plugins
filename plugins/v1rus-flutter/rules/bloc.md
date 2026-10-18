---
paths:
  - "**/bloc/**/*.dart"
  - "**/cubit/**/*.dart"
  - "**/*_bloc.dart"
  - "**/*_cubit.dart"
  - "**/*_state.dart"
  - "**/*_event.dart"
  - "**/*_effect.dart"
---

# Bloc — rules for this file

Full detail in the `bloc-conventions` skill. What must hold in the file you are editing:

- **A screen is a `Bloc`** (events in, state out — the analogue of MVI `Intent → State`). A `Cubit` is only
  for narrow component-local state with no event vocabulary. Do not start a screen as a Cubit.
- **State is a native `sealed` union with `Equatable`** (no `freezed`), not a class of nullable flags —
  impossible combinations must be unrepresentable. Cover **loading / content / empty / error**, plus
  **not-found** for a fetched detail.
- **Every distinguishing field is in `props`.** Bloc skips an `emit` equal to the current state, so a
  forgotten field means the screen silently does not rebuild. Effects are the exception — they carry no
  equality, so two identical messages are two events.
- State is a UI model: preformatted values, no entities carrying data-layer concerns, **no `BuildContext`,
  no widgets, no `Color` / `TextStyle`**.
- **One handler per event.** If a handler needs more than a couple of calls, extract a private method.
- Use **event transformers** where concurrency matters: `debounce` for search, `droppable` for submit,
  `restartable` for a superseding query. Missing these causes duplicate calls and out-of-order results.
- **One-shot effects go on a separate effect stream, never into state** — otherwise they replay on rebuild
  and after restoration. Close the controller in `close()`.
- The Bloc **emits** an effect; the widget performs it. No `BuildContext`, `Navigator`,
  `ScaffoldMessenger` or router inside a Bloc.
- Depend on **`domain` interfaces and use cases only** — never a repository implementation, never a DTO,
  never a raw `DioException`.
- Register blocs as **factories**, never singletons (`flutter-di`).
- Cancel subscriptions and in-flight work in `close()`.
- No `print` / `debugPrint` — use the project's logger.
