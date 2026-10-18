---
name: dart-conventions
description: "Dart and Flutter rules a model omits by default: checking context.mounted after every await, never passing BuildContext into a Bloc or repository, nullability mirroring what the source actually sends, avoiding bare `!` and `as`, value equality for anything emitted as state, disposing every controller and subscription, catching with a stack trace and never swallowing an error, const constructors and widget classes instead of _build methods, and stable keys in dynamic lists. Load when writing or reviewing Dart code, or when deciding how to handle an async gap, a nullable field, or a resource that needs disposal."
---

# Dart Conventions

The full rulebook is `${CLAUDE_PLUGIN_ROOT}/rules/dart.md` — **read it** before writing or reviewing
non-trivial Dart. It is a single source: the same file is injected automatically by this plugin's
`path-rules` hook just before any `.dart` edit, so when you are about to write code it is usually already
in context. Read it directly when reviewing, since a review performs no edit and triggers no injection.

It documents only what a modern model gets wrong without a reminder. Generic idiomatic Dart is left to the
model and to `flutter_lints`.

The four that cause production bugs:

- **`context.mounted` after every `await`** in a widget callback. The analyzer catches many paths, not all.
- **Dispose everything you create** — controllers, focus nodes, stream subscriptions. A missing `dispose`
  leaks past navigation.
- **`catch (e, stackTrace)`**, never `catch (e)` alone, and never an empty catch. The stack trace is the
  part you actually need.
- **Nullability mirrors reality.** A field marked non-null because "the server always sends it" turns one
  missing value into a crash for every user at once.

Related: `bloc-conventions` (state, events, effects), `flutter-ui-conventions` (widgets, theming,
accessibility), `flutter-error-handling` (`Result` and `AppError`), and the `v1rus-logging` skill.
