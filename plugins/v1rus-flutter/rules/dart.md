---
paths:
  - "**/*.dart"
---

# Dart & Flutter — non-obvious rules

Only what a model gets wrong or omits without a reminder. Generic idiomatic Dart — naming, `final` over
`var`, collection literals, cascade syntax — is not listed here; `flutter_lints` plus the analyzer cover it.

## Async and `BuildContext`

- **After every `await` in a widget callback, check `context.mounted` before using the context.** The
  widget may be gone; using a dead context is a crash, and the analyzer's `use_build_context_synchronously`
  catches many but not all paths (notably contexts captured into local variables or helper functions).
- Do not pass `BuildContext` into a Bloc, a repository, or anything in `core` / `data` / `domain`. If a
  layer needs the context, the design is wrong — return data or an effect instead.
- Never `unawaited` a future by accident: either `await` it, or wrap it in `unawaited(...)` deliberately so
  the intent is visible and errors are still reported.
- `Future.wait` propagates only the first error and loses the rest — when partial failure matters, collect
  results individually.

## Null safety and types

- Nullable fields on a data class mirror what the source **actually** produces. Marking a field non-null
  because "the server always sends it" converts one missing field into a parse crash for every user.
- `!` is a last resort and needs a reason. Prefer pattern matching, `??`, or restructuring so the value
  cannot be null at that point.
- Never `as` without knowing the type is guaranteed; prefer a pattern match (`if (x case final T t)`).
- Avoid `dynamic` in signatures. Deserialisation boundaries take `Map<String, dynamic>` and convert
  immediately; `dynamic` must not travel further.

## Equality and immutability

- Any class compared, put in a `Set`, used as a `Map` key, or emitted as Bloc state needs value equality —
  in practice that means extending `Equatable` and listing **every** distinguishing field in `props`
  (`flutter-codegen`). There is no model generator in this stack: a field omitted from `props` is not a
  style slip, it is a state that compares equal to a different state and a screen that never rebuilds.
- A Bloc emitting a class with identity equality re-renders on every emit; a Bloc emitting one with
  equality and a mutable `List` inside does **not** re-render when the list mutates in place.
- Collections inside state are treated as immutable: build a new list rather than mutating and re-emitting.

## Resources

- Every `AnimationController`, `TextEditingController`, `ScrollController`, `FocusNode`, `StreamController`
  and `StreamSubscription` created must be disposed / cancelled in `dispose()` / `close()`. A missing
  dispose is a leak that outlives navigation.
- A `StreamSubscription` created in a Bloc handler is stored on the Bloc and cancelled in `close()`.

## Errors and logging

- No `print` or `debugPrint` for diagnostics — use the project's logger (`v1rus-logging` skill).
- `catch (e)` without a stack trace loses the only useful part: use `catch (e, stackTrace)` and pass both.
- Never swallow an error silently. An empty `catch` block, or one that returns a default without logging,
  is a defect.
- Do not catch and rethrow with a new stack trace: `rethrow`, or use `Error.throwWithStackTrace`.
- Transport and driver exceptions (`DioException` — including the ones a Retrofit client throws — Drift,
  `PlatformException`) are mapped to `AppError` inside `data` and never escape it
  (`flutter-error-handling`).

## Widget performance

- `const` constructors and `const` literals wherever possible — that is what lets Flutter skip subtrees.
- Extract widgets as **classes**, not `_buildX()` methods returning `Widget`: a method cannot be `const`,
  is never skipped in a rebuild, and does not appear as its own element.
- No computation, I/O or `await` in `build`.
- Dynamic lists use `ListView.builder` with a stable `key` per item, never index identity for a list that
  can be reordered or filtered.

## Style

- Colours, typography, spacing and durations come from theme tokens, never literals in feature code
  (`flutter-ui-conventions`).
- All user-visible strings come from resources, including fallbacks (`flutter-localisation`).
- `library` / `part` splitting only where a generator requires it.
