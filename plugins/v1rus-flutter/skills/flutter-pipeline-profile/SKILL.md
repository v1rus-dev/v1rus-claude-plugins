---
name: flutter-pipeline-profile
description: "Stack profile that binds the stack-agnostic v1rus feature pipeline to a Flutter/Dart project: the layer vocabulary the architecture plan uses, the stack-specific sections of architecture-plan.md, which convention skill owns which area, the presentation pattern (Bloc for screens, Cubit for components, effects on a separate stream), design-system mapping via ThemeExtension tokens for a design spec, where tests live and on what (test/ mirroring lib/, bloc_test, mocktail, handwritten fakes), which codegen must run, how to analyse and compile-check, which engineer agents implementation escalates to, and the finalizer's stack checklist. Loaded by feature-architect, feature-designer, feature-developer, test-planner, test-writer and feature-finalizer when the pipeline detects a Flutter project. Do NOT load for pipeline mechanics — gates, complexity bands and commit discipline live in feature-pipeline."
---

# Pipeline profile — Flutter / Dart

The pipeline agents (`feature-architect`, `feature-designer`, `feature-developer`, `test-planner`,
`test-writer`, `feature-finalizer`) are stack-agnostic. This profile is the **vocabulary** they use on
a Flutter project: what the layers are called, what the plan must cover, where tests go, which
convention skill owns which rule.

Two boundaries that matter:

- **Pipeline mechanics are not here.** Phase order, gates, complexity bands, artifact names, commit
  discipline and resume live in the `feature-pipeline` skill. This file never repeats them.
- **The project still owns the names.** Real folder layout, type names, analyzer settings and the
  analyze/test/codegen commands come from the target project's `CLAUDE.md`, `pubspec.yaml` and
  `analysis_options.yaml`. Read those first; never guess a command.

## Stack identity

Markers: `pubspec.yaml` with a `flutter` dependency, `analysis_options.yaml`, `lib/main.dart`, `.dart`
sources. One Dart package — the layers are folders under `lib/`, not separate modules, and their
boundaries are enforced by the `import_lint` analyzer plugin rather than by the build graph.

## Layer vocabulary

| Layer | Holds |
|---|---|
| `lib/features/<name>/` | `bloc/` (bloc or cubit + state/event/effect), `view/` (screen + parts), `widgets/`, `routes/` (this feature's typed routes) |
| `lib/design_system/` | theme, `ThemeExtension` tokens, reusable widgets, icons |
| `lib/domain/` | entities, repository **interfaces**, the `AppError` union, use cases |
| `lib/data/` | DTOs, Retrofit API clients, Drift tables/DAOs, repository **implementations**, mappers |
| `lib/core/` | `Result`, Dio client + interceptors, storage wrappers, DI container, logging, extensions |
| `lib/l10n/` | `.arb` files |
| `lib/main.dart` | composition root: DI registration, router assembly, `runApp` |

Hard boundaries (checked by `dart analyze` via `import_lint`, not by review): `domain` depends on
nothing — not on `data`, not on `features`, not on Flutter; `data` never imports `features`; a feature
never imports another feature (shared widget → `design_system`, shared logic → `domain`, shared helper
→ `core`); `core` and `design_system` never import `features`/`data`/`domain`.

## `architecture-plan.md` — stack sections

Use these in place of the generic layer sections:

```
## 3. Data layer changes         (DTOs + json_serializable, Retrofit @RestApi endpoint methods,
                                 Drift tables/DAOs + a versioned migration if the schema changes,
                                 repository implementations, mappers DTO→entity, error mapping)
## 4. Domain layer changes       (entities, repository interfaces, AppError cases,
                                 use cases only where there is real logic — not for pass-throughs)
## 5. Presentation layer changes (feature folder, Bloc or Cubit, the sealed state union,
                                 events, the effect stream, screen + parts, feature widgets)
## 6. Wiring                     (get_it registration module + its call from the composition root,
                                 typed go_router routes + router assembly, .arb keys in every locale,
                                 which build_runner generators must re-run)
```

Self-questions the plan must answer for this stack: does the change keep `domain` free of Flutter and
of `data`; does any new use case carry real logic or is it a pass-through that should be dropped; does
a transport exception stay inside `data` and leave only as an `AppError` in a `Result`; does a schema
change come with a migration **and** a migration test; does any new boundary crossing violate an
`import_lint` rule.

## Convention skills by area

| Area | Skill |
|---|---|
| layers, folder layout, `import_lint` boundaries | `flutter-architecture` |
| Bloc/Cubit, sealed state, effect stream | `bloc-conventions` |
| screen states, a11y, theme tokens, tap targets | `flutter-ui-conventions` |
| typed `go_router` routes, redirect-based auth gating, dialogs as routes | `flutter-navigation` |
| Dio + Retrofit, interceptors, single-flight refresh | `flutter-networking` |
| Drift, secure storage, preferences, migrations | `flutter-persistence` |
| `Result`, `AppError`, exhaustive switch consumption | `flutter-error-handling` |
| `get_it` modules, factories vs singletons | `flutter-di` |
| ARB + `gen-l10n`, locale sync | `flutter-localisation` |
| `build_runner` generators, no model generator | `flutter-codegen` |
| Dart style, `context.mounted`, nullability, disposal | `dart-conventions` |
| analyzer setup, CI-blocking analysis | `flutter-analysis` |
| tests | `flutter-testing` |

Name the applicable ones in the plan so the implementing agent invokes them; invoke them yourself
before writing non-trivial widget or data-layer code. If a skill is absent in the current environment,
proceed — never hard-depend on one.

## Presentation pattern

**Bloc for a screen** (event-driven, the Flutter analogue of MVI Intent→State), **Cubit only for
narrow component-local state**. State is a native Dart sealed union with `Equatable` covering
loading / content / empty / error. One-shot side effects go on a **separate effect stream** — never
stored in state. A Bloc never holds a `BuildContext` and never imports a widget. Screens consume the
Bloc: dispatch events, render state, perform effects.

## Design-spec mapping (feature-designer)

Map Figma onto the project's **`design_system`**, not raw Material widgets: colours and typography →
`ThemeExtension` tokens (never `Colors.*`, never a raw `Color(0x…)`), spacing → existing spacing
tokens, components → existing reusable widgets first. Discover the available tokens with `ast-index`
before proposing a raw value.

## Tests

- Location: **`test/` mirrors `lib/`** — `lib/data/repositories/order_repository_impl.dart` →
  `test/data/repositories/order_repository_impl_test.dart`. One test file per production file, named
  `<file>_test.dart`.
- Blocs: **`bloc_test`**, asserting the exact emitted state sequence; effects asserted separately.
- Doubles: **`mocktail`** for collaborators whose calls are asserted; **handwritten fakes** when the
  double carries behaviour — keep reusable ones in `test/fakes/` and reuse them.
- Data layer: mock the Retrofit API *interface* (not the generated implementation); a Drift schema bump
  requires a **migration test**.
- Widgets: widget tests for screen states rather than golden-by-default.
- Detail: `flutter-testing`.

## Verification

- **Codegen first** when the change touched an annotated source (`json_serializable`,
  `retrofit_generator`, `drift`, `go_router_builder`) or an `.arb` file — a stale generated file makes
  every later failure a lie.
- **`dart analyze`** is a gate, not advice: a warning is a failure, and it is what surfaces
  `import_lint` boundary violations. Run `dart run import_lint` too when the plugin is configured.
- Full analyse + test run belongs to the `test-runner` agent of this layer
  (`v1rus-flutter:test-runner`), which discovers the project's own commands.
- Commands come from the project's `CLAUDE.md`; the usual shape is `flutter test [path]` and
  `dart analyze`. Never read `.dart_tool/` or `build/`.

## Implementation escalation targets

Available on this stack, per the pipeline's executor-escalation rule: `flutter-ui-developer` (widgets,
screens, design system, routes, widget tests) and `flutter-engineer` (domain, data, networking,
persistence, DI, and the Bloc's state/event/effect definitions and handlers). The split is: anything
that builds a widget tree → `flutter-ui-developer`; the Bloc itself and everything below it →
`flutter-engineer`. `feature-developer` remains the floor.

## Finalizer stack checklist

On top of the generic cleanup: `get_it` registrations present in the feature's module and called from
the composition root; typed routes registered in the router; `.arb` keys added to **every** locale;
generated files regenerated and never hand-edited; no `BuildContext` reaching a Bloc or repository; no
`context` used after an `await` without a `mounted` check; no `DioException`/Drift exception escaping
`data`; colours and typography from tokens only; `dart analyze` clean including `import_lint`.

## Typical expert reviews to flag

`ux-expert` for a new screen or navigation change; `security-expert` for auth, token storage or
anything touching `flutter_secure_storage`; `performance-expert` for long lists, heavy rebuilds or new
stream plumbing; `architecture-expert` when the change crosses layer boundaries or adds a new
`import_lint` rule.
