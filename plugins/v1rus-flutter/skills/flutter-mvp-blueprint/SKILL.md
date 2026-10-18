---
name: flutter-mvp-blueprint
description: "The /mvp-init MVP blueprint for Flutter / Dart: how a new Flutter project comes into existence and what it must contain on day one. Covers when Flutter is the right stack and when it is not, the flutter create bootstrap route and exactly what of the generated template is deleted or replaced, the MVP-sized lib/ layer layout with the rule for when each deferred piece appears, the baseline package set by role (no versions), pubspec / analysis_options / l10n.yaml / platform build configuration, the app skeleton (composition root, get_it wiring order, ThemeExtension tokens, go_router host, one Dio, ARB seed), the first vertical slice as real working code with loading / empty / error states, the facts the generated project CLAUDE.md must record, the verification commands, and the traps that break a fresh Flutter project. Load when scaffolding a new Flutter app, running flutter create for a fresh MVP, laying out lib/ for a new project, wiring import_lint boundaries from day one, building the first vertical slice of a new codebase, or generating a new Flutter project's CLAUDE.md. Do NOT load to add a feature to an existing Flutter project — that is flutter-pipeline-profile."
---

# MVP blueprint — Flutter / Dart

The technology half of `/mvp-init` on this stack: the command owns the process, this file owns what a
Flutter project *is* at hour zero. Layer vocabulary, the convention-skill map, test layout and analyse
discipline live in **`flutter-pipeline-profile`** — this blueprint says what to *create*, the profile
says how to work in it afterwards. Everything below is the short form of a skill in this plugin; invoke
the named skill before writing the code.

## 1. Stack identity

Flutter when the brief says **iOS + Android from one codebase**, one team language, UI parity valued
over per-platform native feel; optionally web/desktop from the same source. Custom, design-system-heavy
UI is a positive signal — Flutter renders its own widgets rather than the platform's.

| Anti-signal | Go to |
|---|---|
| Native platform UI required, or heavy native SDK integration dominates | `v1rus-kmp:kmp-mvp-blueprint` |
| Must share code with an existing Kotlin/Swift codebase | `v1rus-kmp:kmp-mvp-blueprint` |
| Android only, no second platform on the roadmap | `v1rus-android:android-mvp-blueprint` |
| Backend or CLI | not this layer |

## 2. Bootstrap route

`flutter create` is the generator — never hand-write the platform runner folders. It is also a sample-app template, so a third of what it produces is deleted immediately.

```
flutter create --org <reverse.dns.org> --project-name <snake_case_name> \
               --platforms=android,ios --template=app --empty .
```

- `--org` + `--project-name` decide the Android `applicationId`, the iOS bundle identifier and the
  package folders — **both settled in the gate before this runs** (trap 1).
- `--platforms` lists only what the brief asks for; add one later with `flutter create --platforms=<p> .`.
- `--empty` suppresses the counter sample and the widget test that references it.
- `flutter pub get` writes `pubspec.lock` — **commit it**, this is an application. Flutter has no build
  wrapper: the SDK floor lives in `environment:` in `pubspec.yaml`.

**Toolchain missing.** If `flutter` is not on PATH, do not install it and never use `sudo`. Say so in one
line, hand the developer the exact commands for their own terminal (`flutter --version`, then the
`flutter create …` line above with the resolved org and name), and continue with everything that does
not need the SDK — plan, `CLAUDE.md`, file contents to write once the tree exists.

| # | After `create` | Detail |
|---|---|---|
| 1 | Delete the sample | `lib/main.dart` body, `test/widget_test.dart`, any `MyApp`/`MyHomePage` remnant |
| 2 | Replace `analysis_options.yaml` | `flutter-analysis` set + the `import_lint` rules from `flutter-architecture` |
| 3 | Create the `lib/` tree | §3 — a folder only where a file already belongs in it |
| 4 | Rewrite `pubspec.yaml` | approved plan dependencies, `flutter: generate: true`, assets |
| 5 | Add `l10n.yaml` + `lib/l10n/app_<locale>.arb` | `flutter-localisation` |
| 6 | Skeleton (§6), then slice (§7) | engineer first, UI second — they share `main.dart` and the DI module |
| 7 | Codegen, then verify | §9 |

Kept and edited in place, never recreated: `android/`, `ios/`, `.metadata`, `pubspec.yaml`, `.gitignore` (one edit — the generated-file policy, §5).

## 3. Module graph at MVP size

One Dart package; layers are folders under `lib/`, boundaries enforced by `import_lint` rather than by a build graph. That is what makes one package safe here — promoting a folder to its own package later is a move plus a rule update, not an API redesign — and why a project that defers the boundary rules has folder names, not layers.

```
lib/
  core/            result/, network/, logging/, di/          (storage/ only when §4 says so)
  design_system/   theme/ (AppTokens ThemeExtension), widgets/
  domain/          entities/, repositories/ (interfaces), errors/
  data/            api/<area>/ (+dto/), mappers/, repositories/ (impls)
  features/<slice>/  bloc/, view/, routes/, di/
  l10n/            app_<locale>.arb
  main.dart        composition root
test/              mirrors lib/
```

| Deferred | Created when |
|---|---|
| `domain/usecases/` | the first operation spanning two repositories, carrying real logic, or used by two blocs — never a pass-through |
| `data/database/` (Drift) | the first data that must survive a restart or be queried offline |
| `core/storage/` secure / prefs wrappers | the first secret (arrives with auth) / the first user preference |
| `features/<x>/widgets/` | the screen grows its own private widgets |
| shell route with bottom navigation | the second top-level destination |
| further ARB locales | the brief adds one — the toolchain is wired from day one for a single locale |
| flavors / multiple build configs | the second environment; until then the base URL is a `--dart-define` |
| `get_it` scopes | logout exists |
| analytics, crash reporting, deep-link config | post-MVP |

## 4. Baseline dependency set, by role

Names only. **Every version is resolved at plan time through the `v1rus-dependencies` gate**
(`dart pub outdated` plus the package's own page) and CVE-checked there — nothing is added from memory.
Add approved coordinates with `dart pub add` / `dart pub add --dev`.

| Role | Package(s) | MVP |
|---|---|---|
| State management | `flutter_bloc` | mandatory |
| Value equality | `equatable` | mandatory |
| DI | `get_it` | mandatory |
| Navigation | `go_router`, `go_router_builder` (dev) | mandatory |
| Localisation | `flutter_localizations` (SDK), `intl` | mandatory |
| Codegen host | `build_runner` (dev) | mandatory with any generator |
| Lints | `flutter_lints` (dev) | mandatory |
| Layer boundaries | `import_lint` (dev, analyzer plugin) | mandatory when the SDK floor is met (trap 3) |
| Testing | `flutter_test` (SDK), `bloc_test` (dev), `mocktail` (dev) | infrastructure mandatory; whether tests are *written* is the complexity band's call (`v1rus-qa`) |
| Networking | `dio`, `retrofit`, `retrofit_generator` (dev) | with a real or HTTP-mock backend; dropped when the brief says "no backend yet" |
| Serialization | `json_annotation`, `json_serializable` (dev) | with networking |
| Logging | one logging package behind a `core/logging` interface | mandatory — `print` is banned (`v1rus-logging`) |
| Persistence | `drift`, `drift_dev` (dev), the SQLite native bundle | deferred to the first stored entity |
| Secure storage | `flutter_secure_storage` | with auth |
| Preferences | `shared_preferences` | deferred to the first preference |
| Image loading | a cached-network-image package | deferred to the first remote image |

No model generator: unions, entities and state are native Dart `sealed`/`final` classes with `Equatable` (`flutter-codegen`).

## 5. Build configuration

| What | Where |
|---|---|
| Dependency coordinates | `pubspec.yaml` — the only place |
| Dart/Flutter SDK floor | `environment:` in `pubspec.yaml`; raised only by a package that demands it |
| gen-l10n switch | `flutter: generate: true` in `pubspec.yaml` |
| Application id / bundle id | set by `--org` at create; afterwards `android/app/build.gradle.kts` + the Xcode project |
| Display name | `android:label` in `AndroidManifest.xml`, `CFBundleDisplayName` in `Info.plist` |
| Min platform versions | `minSdk` in `android/app/build.gradle.kts`, the iOS deployment target in the Podfile and project — layer baseline unless the brief says otherwise |
| Static analysis | `analysis_options.yaml`: `flutter-analysis` set + `import_lint` rules from `flutter-architecture` |
| Localisation | `l10n.yaml` with `untranslated-messages-file` and `required-resource-attributes` |
| Codegen scoping | `build.yaml` only when a generator needs a narrower input set |
| Backend base URL | `--dart-define`, read once in `core/network` — never a hardcoded host |
| Flavors | omitted unless the brief names a second environment |
| Generated-file policy | `.gitignore`: commit `*.g.dart` or ignore them — decided **once**, recorded in `CLAUDE.md`; half-committed generated code conflicts on every merge |

## 6. App skeleton

Every piece of plumbing is exercised once before feature work starts.

| File | Wires |
|---|---|
| `main.dart` | composition root only: `WidgetsFlutterBinding.ensureInitialized()` → `configureDependencies()` → `await di.allReady()` → `runApp(const App())` |
| `core/di/di.dart` | `final GetIt di = GetIt.instance;` and `configureDependencies()` calling, in order, `registerCore` (logger, then Dio, then storages) → `registerData` → `registerDomain` → each `register<Feature>Feature`. Blocs are factories, infrastructure lazy singletons (`flutter-di`) |
| `app.dart` | `MaterialApp.router` with `routerConfig`, `theme` + `darkTheme`, `AppLocalizations.localizationsDelegates` / `supportedLocales` |
| `design_system/theme/` | `AppTokens extends ThemeExtension<AppTokens>` (colours, spacing, radii, durations) for **both** light and dark + the `context.tokens` extension; feature code never sees a raw `Color` (`flutter-ui-conventions`) |
| `core/navigation/app_router.dart` | one `GoRouter` from the generated typed-route tree with the slice's route registered; a single `redirect` only when the brief has auth |
| `core/network/` | one `Dio` — base URL, timeouts, JSON content type, logging interceptor last; auth + single-flight refresh interceptors and the session-expired channel only with auth (`flutter-networking`) |
| `core/result/`, `domain/errors/`, `data/mappers/` | `sealed Result<T>`/`Ok`/`Err`, the `AppError` union, and the transport-exception → `AppError` mapper. A `DioException` never leaves `data` (`flutter-error-handling`) |
| `lib/l10n/app_<locale>.arb` | the slice's keys; nothing user-visible is a literal |

Storage is initialised only if §4 put it in scope — an unused database is dead weight, not plumbing.

## 7. The first vertical slice

One end-to-end feature, **real working code** — no `TODO`, no `UnimplementedError`, no placeholder screen. It proves DI, routing, theme, localisation, networking, error mapping and the Bloc contract fit together, and is the template every later feature is copied from.

**Which slice:** the simplest *fetch-a-list-and-show-it* feature from the brief's MVP list; with no
obvious candidate, the home list of the app's primary entity. With no backend yet, build the identical
slice against an in-memory repository implementation — the `domain` interface is unchanged, so swapping
in the Retrofit-backed one later is a single line in one DI module.

| Layer | Files |
|---|---|
| `domain` | `entities/<item>.dart`, `repositories/<item>_repository.dart` returning `Future<Result<List<Item>>>` |
| `data` | `api/<area>/<area>_api.dart` (`@RestApi` abstract class, `part` + factory redirect), `api/<area>/dto/<item>_dto.dart` (`@JsonSerializable`), `mappers/<item>_mapper.dart`, `repositories/<item>_repository_impl.dart` mapping failures to `AppError` |
| `features/<area>` | `bloc/` (bloc + sealed event union + sealed state union + effect stream), `view/<x>_screen.dart` + one part widget per state, `routes/<x>_routes.dart`, `di/<x>_module.dart` |
| `l10n` | title, empty copy, error copy, retry label |

The state union is `Loading` / `Content` / `Empty` / `Error(AppError)` and **all four render**: a progress
indicator, the list, human empty copy from the ARB, and an error message with a working retry that
dispatches the reload event. The `AppBar` is hoisted **outside** the state `switch`, so back navigation
works while loading and while failed. One effect (`ShowMessage`) travels on the effect stream so the
pattern exists from the first screen. The bloc holds no `BuildContext`.

Slice tests — `bloc_test` on loading→content and loading→error, a widget test per state — are written when the complexity band calls for them (`v1rus-qa`); the state coverage above is required either way.

## 8. Project `CLAUDE.md` inputs

| Fact | Value to record |
|---|---|
| Package | the `pubspec.yaml` name and the `package:<name>/` import prefix (all imports are package imports) |
| Layer paths | `lib/core`, `lib/design_system`, `lib/domain`, `lib/data`, `lib/features/<x>`, `lib/l10n`; composition root `lib/main.dart` |
| Type names | state holder `<Feature>Bloc` (Cubit for component-local state) with a separate effect stream; `Result`/`Ok`/`Err` in `core/result`; `AppError` in `domain/errors`; theme tokens `AppTokens` read via `context.tokens`; the router instance and its file; the `get_it` instance name (`di`) and the `register<Feature>Feature(GetIt)` convention |
| Commands | `flutter pub get`; `dart run build_runner build --delete-conflicting-outputs`; `flutter gen-l10n`; `dart analyze`; `dart run import_lint`; `flutter test`; `flutter run -d <device>` |
| Tests | `test/` mirrors `lib/`, `<file>_test.dart`, `bloc_test` + `mocktail`, fakes in `test/fakes/` |
| Decisions | generated-file commit policy; whether `import_lint` is active or the SDK floor is unmet (state the gap, trap 3); how the base URL is supplied |
| v1rus plugins to enable | `v1rus-core`, `v1rus-flutter` |

## 9. Verification

In this order — an earlier failure makes every later result a lie:

```
flutter pub get
dart run build_runner build --delete-conflicting-outputs
flutter gen-l10n
dart analyze                # a warning is a failure
dart run import_lint        # when the SDK floor is met
flutter test
```

| Then | Headless? |
|---|---|
| `flutter build apk --debug` | yes, when the Android SDK and a JDK are present |
| `flutter build ios --no-codesign` | only on macOS with Xcode |
| `flutter run -d <device>` | **developer** — needs a device or simulator |

"Runnable" here means `flutter run` shows the slice's content state against the configured backend. The
agent verifies up to the platform build, then hands over the exact `flutter run` line — never claiming
the app runs on a target it did not start. Full runs belong to `v1rus-flutter:test-runner`, which
discovers the project's own commands.

## 10. Escalation targets

| Scaffold role | Agent |
|---|---|
| `pubspec.yaml`, `analysis_options.yaml`, `l10n.yaml`, platform build config, codegen wiring | `v1rus-flutter:flutter-engineer` — there is no separate build agent here (`v1rus-kotlin:build-engineer` is JVM/Gradle and does not apply) |
| `core`, `domain`, `data`, DI modules, the Bloc and its state/event/effect | `v1rus-flutter:flutter-engineer` |
| `design_system`, screens, widgets, typed routes, widget tests | `v1rus-flutter:flutter-ui-developer` |
| Verification runs | `v1rus-flutter:test-runner` |
| Floor when none is installed | `feature-developer` |

`main.dart`, `core/di/di.dart` and the router are touched by both implementers — engineer first, UI second, never in parallel.

## 11. Known first-run traps

1. **The identifier decided too late.** `--org` and `--project-name` are baked into the package folders,
   the Gradle namespace and the Xcode project; renaming afterwards is a multi-file edit across both
   platforms, avoided by settling both in the gate before `flutter create` runs.
2. **Analyzing before generating.** With no `.g.dart` files `dart analyze` reports dozens of undefined
   `_XApi` / `fromJson` errors that read like real breakage — as does a `@RestApi` class missing its
   `part` directive or factory redirect. Run `build_runner` and `gen-l10n` before believing analyzer
   output, and never hand-write a generated file to silence it.
3. **`import_lint` silently not loading.** The analyzer-plugin mechanism requires **Dart 3.10+ /
   Flutter 3.38+**; below that floor it does not load and boundary violations pass unnoticed. Keep the
   rules in `analysis_options.yaml`, state the gap in the project `CLAUDE.md`, and check boundaries at
   review until the SDK is raised.
4. **Template leftovers.** A surviving counter `main.dart` or `test/widget_test.dart` fails the first
   analyze or test run against code nobody intends to keep; a missing `flutter: generate: true` makes
   `gen-l10n` produce nothing and leaves `AppLocalizations` unresolved wherever it is imported.
