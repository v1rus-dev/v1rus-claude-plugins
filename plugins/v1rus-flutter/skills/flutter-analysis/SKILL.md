---
name: flutter-analysis
description: "Static analysis setup for v1rus Flutter projects: flutter_lints as the official base plus a named set of v1rus additions the base omits, the strict analyzer language flags (strict-casts, strict-inference, strict-raw-types), treating analyzer output as CI-blocking rather than advisory, generated files excluded from analysis but not from review of their sources, the import_lint layer rules, and the rule that an ignore comment needs a reason. Load when setting up or editing analysis_options.yaml, when a lint fires and you are considering an ignore, or when adding a lint rule to the standard."
---

# Static Analysis

`dart analyze` is a **gate, not advice**: it runs in CI and a warning fails the build. Everything below
exists so that a defect is caught by tooling instead of a reviewer's attention.

## Base: `flutter_lints` plus v1rus additions

`flutter_lints` is the official base — it stays current with the SDK and does not surprise the team on
upgrade. It is also deliberately minimal, so a named set of additions covers what it omits.

```yaml
# analysis_options.yaml
include: package:flutter_lints/flutter.yaml

analyzer:
  language:
    strict-casts: true          # no implicit dynamic → T
    strict-inference: true      # no silently inferred dynamic
    strict-raw-types: true      # no raw List / Map / Future
  errors:
    # promote the ones that are real defects, not style
    use_build_context_synchronously: error
    unawaited_futures: error
    close_sinks: error
    cancel_subscriptions: error
    avoid_dynamic_calls: error
    invalid_use_of_protected_member: error
  exclude:
    - "**/*.g.dart"
    - "lib/l10n/app_localizations*.dart"

linter:
  rules:
    # correctness the base omits
    avoid_slow_async_io: true
    literal_only_boolean_expressions: true
    no_adjacent_strings_in_list: true
    throw_in_finally: true
    unnecessary_statements: true
    # API and immutability discipline
    always_declare_return_types: true
    prefer_final_locals: true
    prefer_final_in_for_each: true
    avoid_positional_boolean_parameters: true
    use_named_constants: true
    # Flutter specifics
    use_colored_box: true
    use_decorated_box: true
    sized_box_for_whitespace: true
    avoid_unnecessary_containers: true
    prefer_const_constructors: true
    prefer_const_constructors_in_immutables: true
    prefer_const_literals_to_create_immutables: true
    # imports
    always_use_package_imports: true
    depend_on_referenced_packages: true
```

Two notes on the additions:

- **`avoid_positional_boolean_parameters`** and **`use_named_constants`** are the Dart analogue of the
  named-argument rule in v1rus's Kotlin standard: a bare `true` at a call site tells the reader nothing.
- **`always_use_package_imports`** removes the `../../../` relative-import tangle, which also makes the
  `import_lint` layer rules readable and reliable.

Generated files are **excluded from analysis** because their style is not ours to fix — but the annotated
source that produces them is reviewed normally (`flutter-codegen`).

## Layer boundaries

The `import_lint` rules that enforce the architecture live in the same file — see the
`flutter-architecture` skill for the rule set and the Dart 3.10+ / Flutter 3.38+ prerequisite. They run in
the IDE and via `dart run import_lint`, so include both in CI.

## `// ignore` needs a reason

An ignore comment without a justification is a silent suppression:

```dart
// ignore: avoid_dynamic_calls — third-party SDK returns untyped Map, wrapped in DTO below
```

- Prefer `// ignore_for_file:` only for generated or vendored files.
- A rule that gets ignored repeatedly is either wrong for this project — then **disable it in
  `analysis_options.yaml` with a comment explaining why**, so the decision is visible once — or the code is
  wrong. Scattered ignores are the worst of both.

## Adding to the standard

A new lint rule enters the corporate set only with a stated reason: the class of defect it catches, and
whether it is mechanical to satisfy in an existing codebase. Rolling a strict rule onto a legacy project
without a migration path produces hundreds of findings and gets the whole file disabled.

## Formatting

`dart format` with the project's line length, run in CI as a check. Formatting is never a review topic.
