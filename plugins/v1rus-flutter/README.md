# v1rus-flutter

The Flutter / Dart layer. Depends on `v1rus-core`, so installing it pulls the corporate baseline with it.

```
/plugin install v1rus-flutter@v1rus
```

## The stack this plugin standardises

| Concern | Decision |
|---|---|
| Architecture | Single package, `lib/{core,design_system,domain,data,features}`; boundaries enforced by the `import_lint` analyzer plugin |
| Domain layer | Always present (entities, repository interfaces, `AppError`); **UseCase only where real logic exists**, not as a pass-through |
| State management | **Bloc** for screens (event-driven, the analogue of MVI `Intent → State`), **Cubit** for narrow component state |
| One-shot effects | Separate effect stream, never stored in state — the analogue of `EffectUi` |
| Errors | Hand-written sealed `Result<T>` (`Ok`/`Err`) in `core`, domain `AppError`; transport exceptions never leave `data` |
| Models | **No model generator** — native Dart 3 `sealed`/`final` classes + `equatable`; `json_serializable` on DTOs |
| Network | `dio` as transport (one configured client, auth + single-flight refresh interceptors, one session-expired channel) + `retrofit` for endpoint declarations |
| Persistence | `drift` for structured data, `flutter_secure_storage` for secrets, `shared_preferences` for non-sensitive prefs |
| DI | `get_it` with explicit per-feature modules (no codegen), blocs as factories |
| Navigation | `go_router` + `go_router_builder` typed routes |
| Localisation | Official ARB + `gen-l10n`, with `untranslated-messages-file` making locale drift a CI failure |
| Analysis | `flutter_lints` + the v1rus additions, strict analyzer flags, analyzer output is a gate |
| Tests | `bloc_test` + `mocktail`, handwritten fakes where the double carries behaviour |

**No versions are pinned anywhere in this plugin.** Package names only; the version is resolved at plan time
through the `v1rus-dependencies` gate (`dart pub outdated` and the package's own page for Dart).

## Contents

| Component | What it covers |
|---|---|
| `skills/flutter-architecture` | Layers, dependency direction, what goes where, the `import_lint` rule set, adding a feature |
| `skills/bloc-conventions` | Bloc vs Cubit, sealed state unions, event transformers, the effect stream, what never enters a Bloc |
| `skills/flutter-error-handling` | `Result<T>`, `AppError`, mapping in `data`, exhaustive consumption, `Result` vs throwing |
| `skills/flutter-networking` | Retrofit interfaces over Dio, interceptor order, single-flight refresh, session expiry, cancellation, DTOs |
| `skills/flutter-persistence` | Drift + secure storage + preferences, what goes where, migrations that survive release |
| `skills/flutter-navigation` | Typed routes, feature-owned routes, one auth redirect, dialogs as routes, deep links |
| `skills/flutter-di` | `get_it` modules, lifetimes, constructor injection, logout scope reset |
| `skills/flutter-ui-conventions` | Screen states, back navigation in every state, theme tokens, a11y, lists, `const` |
| `skills/flutter-localisation` | ARB + `gen-l10n`, enforced locale sync, server text vs closed sets |
| `skills/flutter-testing` | `bloc_test`, effects asserted separately, widget tests per state, migration tests |
| `skills/flutter-codegen` | The four generators, why there is no model generator, the Retrofit client shape, never hand-editing generated files |
| `skills/flutter-analysis` | `analysis_options.yaml`, the v1rus lint additions, `// ignore` needs a reason |
| `skills/flutter-mvp-blueprint` | The `/mvp-init` blueprint for this stack: the `flutter create` bootstrap and exactly what of the template is replaced, the MVP-sized `lib/` layout, the baseline package set by role, the app skeleton and its first vertical slice, and the generated project `CLAUDE.md`. |
| `skills/dart-conventions` | Front door to `rules/dart.md` for read-only and review contexts |
| `rules/dart.md` | Injected before any `.dart` edit: async gaps, nullability, disposal, equality, `const` |
| `rules/bloc.md` | Injected before editing a bloc/cubit/state/event/effect file |
| `agents/flutter-engineer` | Writes `domain`, `data`, `core`, DI and the Bloc logic + tests. No widgets. |
| `agents/flutter-ui-developer` | Writes widgets, screens, design system, routes, animations + widget tests. Consumes a Bloc. |
| `agents/test-runner` | Runs codegen → `dart analyze` (+ `import_lint`) → tests; reports PASS/FAIL. Never edits code. |

## Design notes

**Where this diverges from the official Flutter guide, and why.** The official guidance is MVVM with an
optional domain layer: `View → ViewModel → Repository → Service`. This standard maps onto it rather than
contradicting it — a **Bloc is the ViewModel**, and what the guide calls a **Service** is our API client /
DAO inside `data`. Two deliberate differences: `domain` always exists here (so `data` stays swappable and
`features` stay testable across a codebase many people rotate through), and repository **interfaces** live in
`domain` rather than repositories being concrete classes in `data`. The guide's own framing applies —
*"they're guidelines, not steadfast rules"*.

**Why boundaries are tooling, not documentation.** In a single package nothing stops `features/a` from
importing `features/b`. `import_lint` turns each boundary into an analyzer error, so drift fails CI instead
of depending on a reviewer noticing. It needs **Dart 3.10+ / Flutter 3.38+**; below that the rules are
documented and review-checked, and the gap is stated explicitly rather than glossed over.

**Why no `freezed`.** Dart 3 has `sealed`/`final` class modifiers and exhaustive pattern matching natively,
so a union needs no generator; what remained was `==` / `hashCode` / `copyWith`, and `equatable` covers
equality without a build step. Dropping it removes a generator from every model change — the cost is that
value equality is now a **review concern**: a field missing from `props` is a state that compares equal to a
different state, so Bloc skips the `emit` and the screen silently does not rebuild. That is the one failure
mode this choice introduces, and it is called out in `rules/dart.md` and `rules/bloc.md`.

**Why Retrofit on top of Dio.** Dio stays the transport — interceptors, refresh, timeouts, cancellation —
and Retrofit removes the hand-written request-building layer above it: an endpoint becomes a signature, and
a wrong path or a forgotten query parameter fails generation instead of returning a 404 at runtime. It also
kills the "just this once" `dio.get(...)` inside a repository, which is how a network layer stops being one
place.

**Why locale sync is a CI check.** "Add the key to both locales" survives about two sprints as a review
rule. `untranslated-messages-file` makes `gen-l10n` emit the list of missing translations, so the rule
becomes a failing build.

**Project overrides.** Everything here is the default, not a mandate: a project may specify a different
structure or stack in its own `CLAUDE.md`, and the project wins. What the plugin guarantees is that the
default is a coherent whole rather than per-developer taste.
