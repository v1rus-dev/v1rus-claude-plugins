---
name: android-conventions
description: "Native-Android structure conventions for v1rus projects: the Gradle module graph of an Android app (one com.android.application, feature modules that never depend on each other, core/domain contracts, one design-system module), AGP's variant-derived source sets and why nothing named commonMain or expect/actual belongs in a native project, where AGP configuration lives, AndroidManifest discipline (manifest merging across modules, android:exported, minimal permissions requested at the point of use), Context discipline (applicationContext for anything long-lived, no Context in domain or presentation state), lifecycle and process death (viewModelScope, SavedStateHandle, configuration changes), res/ qualifiers, and which v1rus-compose skill owns each Compose topic. Load when adding an Android module, editing a manifest or a build script, wiring an Application or ViewModel, or reviewing a native-Android module graph."
---

# Android Conventions

Applies to **native-Android** projects — a single Android target, no multiplatform. The concrete
module names, `minSdk`/`compileSdk`/`targetSdk` values and build-task names live in the project's own
`CLAUDE.md`, `settings.gradle.kts` and build scripts — **read those first and never invent a module
that is not declared in `settings.gradle.kts`.** This skill is the shape those modules take.

## Module graph

- **`app`** — the only `com.android.application` module. It owns the `Application` class, the host
  `Activity`, navigation wiring and the assembled DI graph. No feature logic lives here.
- **`feature/*`** — `com.android.library`, **presentation only**: screens, state holders, feature DI.
- **`core/*`** — domain and data: models, repository interfaces and use cases, repository
  implementations, network, database. The split into individual core modules is the project's.
- **`designsystem`** — theme, tokens and shared composables. Features depend on it, never the reverse.

Hard boundaries:

- **Feature modules must not depend on each other.** Cross-feature interaction goes through a public
  contract in a core/domain module. Importing another feature's screen, state or destination is an
  architecture violation, not a shortcut.
- Core modules never depend on a feature or on `app`. The dependency direction is
  `app → feature → core`, and inside core `data → domain`.

**No multiplatform source sets.** A native-Android module has `src/main`, the test source sets
`src/test` and `src/androidTest` (their split is `android-testing`), and whatever per-flavour,
per-build-type and combined flavour+build-type sets AGP derives from the variants the module declares.
`commonMain`, `androidMain`, `expect`/`actual` are KMP constructs — if they appear in a plan for this project, KMP habit is leaking in. Platform indirection
here is a plain interface with one implementation, not a compiler mechanism.

## Gradle and AGP

- Exactly one module applies `com.android.application`; every other Android module applies
  `com.android.library`. A pure-JVM module (mappers, domain logic with no Android types) should be a
  plain Kotlin JVM module — it builds and tests faster.
- Every Android module declares its own unique `namespace`; `applicationId` exists only in `app`.
- SDK levels, build types, flavours, compiler and packaging options belong in **convention plugins**
  applied by module type, not re-declared per module — the how is `v1rus-kotlin:gradle-conventions`.
- `minSdk` / `compileSdk` / `targetSdk` are **project-owned values**: read them from the build files
  and never bump one as a side effect of an unrelated task. A bump is a plan-stage decision — see
  `v1rus-core:v1rus-dependencies`.
- Do not declare `<uses-sdk>` in a manifest; SDK versions come from the Gradle DSL and the merger
  takes the build value anyway.

## AndroidManifest

Every module has a manifest, and they are merged: build-variant manifest over the `app` manifest over
library manifests in dependency order. The merged result is the thing that ships — inspect it (the
Merged Manifest view, or `build/outputs/logs/manifest-merger-<variant>-report.txt`) before assuming
what is in the APK.

- A feature module declares **only what it owns**. Application-wide attributes (`android:name`, theme,
  label, backup rules) belong in the `app` manifest and nowhere else.
- Resolve a merge conflict deliberately with `tools:node` / `tools:replace` in the `app` manifest, with
  a comment naming the library that forced it. Never loosen a component to make an error go away.
- A dependency can contribute a permission you never declared. Audit the merged manifest's
  `<uses-permission>` list before release.
- **`android:exported` is a decision, not a build fix.** Targeting Android 12 (API 31) or higher, every
  `activity`, `service` and `receiver` with an intent filter must declare it explicitly or the build
  and install fail. `false` is the answer unless the component is genuinely an entry point another app
  must reach; flipping it to `true` to silence the merger is a security regression.
- Declare the **minimum** permission set, and justify each one. Request at the point of use, when the
  user starts the feature that needs it: `ContextCompat.checkSelfPermission`, then
  `shouldShowRequestPermissionRationale` for an in-context rationale, then a launcher registered with
  `registerForActivityResult(ActivityResultContracts.RequestPermission())` (or
  `RequestMultiplePermissions`). Denial — including permanent denial — is a real UI state, not a
  silent no-op; model it like any other screen state.

## Context

The `Context`-leak rule and "no `Context` in domain or presentation state" are the body of
`${CLAUDE_PLUGIN_ROOT}/rules/android-source.md`, injected on every Android source edit. What that rule
does not carry:

- Where `applicationContext` comes from: in Koin, `androidContext(...)` passed at `startKoin` in the
  `Application`. Module and binding conventions are `v1rus-compose:di-koin-conventions`.
- Something in domain that needs text carries a resource id or a domain error the UI maps — see
  `v1rus-compose:localisation-and-strings`.
- The `Application` class is the single process entry point: initialise logging, then DI. Everything
  else is lazy — work in `Application.onCreate` is paid on every cold start.

## Lifecycle and process death

That a `ViewModel` never touches a `View`, an `Activity`, a `Context` or a composable is also in
`${CLAUDE_PLUGIN_ROOT}/rules/android-source.md`. Beyond it:

- State holders are `androidx.lifecycle.ViewModel` running the MVI store from
  `v1rus-compose:mvi-presentation`. Coroutines launched from a state holder use `viewModelScope`.
- A configuration change is not a reload. State lives in the `ViewModel` and survives rotation on its
  own; adding `android:configChanges` to hide a state bug hides the bug, not the cause.
- **`SavedStateHandle` for what must survive system-initiated process death** — navigation arguments
  and transient user input the user would resent losing (query text, selected id, in-progress form,
  list anchor). It is a small bundle, not storage: large or structured data belongs in Room or
  DataStore. It survives process death, not force-stop or reboot.
- Process death is a testable path, not a theory — exercise it for any screen with meaningful
  in-progress state.

## Resources

`res/` qualifiers express variation — `values-<lang>`, `-night`, `-w600dp`, density buckets. Prefer a
qualifier over branching on `Configuration` in Kotlin. Icons are vector drawables; density buckets are
for real bitmaps only. Library resources merge into the app and the app wins on a name collision, so
**prefix or namespace a module's resource names** rather than discovering the override at runtime.
String policy itself is `v1rus-compose:localisation-and-strings`.

## Where the Compose rules live

This layer owns the Android platform. Everything about the UI itself comes from `v1rus-compose` —
do not re-derive it here.

| Topic | Skill |
|---|---|
| Screen structure, state split, previews | `v1rus-compose:compose-screen-architecture` |
| MVI store, `State`/`Intent`/`Effect` | `v1rus-compose:mvi-presentation` |
| Composable, theming and accessibility checklist | `v1rus-compose:compose-ui-conventions` |
| One composable per file, preview coverage | `v1rus-compose:compose-file-organisation` |
| Routes, dialogs and sheets as destinations | `v1rus-compose:compose-navigation-patterns` |
| Koin modules and bindings | `v1rus-compose:di-koin-conventions` |
| Strings and localisation | `v1rus-compose:localisation-and-strings` |
| R8, baseline profiles, stability, recomposition | the `v1rus-compose` performance set |

Data layer: `android-data-layer`. Tests and their source sets: `android-testing`. Kotlin style,
coroutines and Gradle: the `v1rus-kotlin` skills.
