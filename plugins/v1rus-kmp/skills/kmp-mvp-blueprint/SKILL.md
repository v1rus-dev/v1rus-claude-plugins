---
name: kmp-mvp-blueprint
description: "The /mvp-init MVP blueprint for a Kotlin Multiplatform / Compose Multiplatform project: which brief answers select the KMP stack, how an empty KMP project is brought into existence and how the Gradle wrapper is obtained, the MVP-sized module graph and when each deferred module appears, the baseline dependency set by role, build configuration, the app skeleton (entry point per target, Koin start order, theme seed, nav display, Ktor client, Room, compose-resources), the first working vertical slice with its loading/empty/error states, the facts the generated project CLAUDE.md must record, the verification commands, the escalation agents and the traps that break a fresh KMP project. Load when creating a new KMP or CMP project, laying out the module graph for a fresh KMP app, scaffolding commonMain/androidMain/iosMain, or building the first vertical slice of a new app. Do NOT load to add a feature to an existing KMP project — that is kmp-pipeline-profile."
---

# MVP blueprint — KMP + Compose Multiplatform

The stack-shaped half of `/mvp-init` for Kotlin Multiplatform: the command owns the process, this
file owns what a KMP project *is* on day one. **`kmp-pipeline-profile` is the sibling for an
existing project** — read it for anything that outlives the scaffold. Conventions are not duplicated
here either: this blueprint names the artifacts to create; `kmp-conventions`, `kmp-data-layer`,
`kmp-testing` and the `v1rus-compose` skills (`mvi-presentation`, `compose-screen-architecture`,
`compose-navigation-patterns`, `di-koin-conventions`, `localisation-and-strings`) say how each one
is written.

## 1. Stack identity

Select KMP when the brief wants iOS **and** Android (± desktop) from one codebase, shared business
logic / networking / persistence, native platform APIs (Keystore, Keychain, biometrics) reached from
shared code, and a Kotlin/Android-first team. Desktop comes along as `jvm("desktop")`.

Two scaffold variants, decided in the brief, not later. **Shared UI (default)** — CMP renders every
target and `iosApp` is a thin SwiftUI host around the Compose view controller. **Shared logic only**
— iOS UI is native SwiftUI over the shared framework; pick it when the brief demands platform-native
iOS feel or an iOS team owns the UI. It widens the framework surface (`kmp-conventions` § iOS
boundary) and removes Compose from `iosMain`.

Anti-signals — send the brief elsewhere: Android only → `v1rus-android:android-mvp-blueprint`;
widest reach with one small team, or a Dart-shaped team → `v1rus-flutter`; iOS only → scaffold
natively with `swift-engineer` / `swiftui-developer`; web or backend → no blueprint, say so per the
fallback rule in `/mvp-init`.

## 2. Bootstrap route

**There is no official headless KMP generator.** The JetBrains wizard at `kmp.jetbrains.com` is a
web page, Android Studio's is IDE-only; neither runs from a terminal. Any generator command you
think you remember must be **verified empirically before it is relied on** — run its `--help`,
confirm a multiplatform template is listed, fall back the moment it is not.

| # | Route | Cost |
|---|---|---|
| 1 | **Clone a v1rus KMP starter** the developer names: `git clone --depth 1 <repo> <dir>`, drop `.git`, rename the app. | Only exists if they have one, and a stale starter carries stale conventions — re-check it against the convention skills. |
| 2 | **Write the file set by hand** (below). Default when no starter is named. | Full control, graph correct at the first commit, no human round-trip. Two binaries cannot be authored as text: the wrapper jar and the Xcode project. |
| 3 | **JetBrains web wizard**, when an officially generated Xcode project is wanted: hand over the URL and the exact selections, they unzip into the target directory. | A human round-trip plus a restructure pass — the wizard emits a flat `composeApp` + `shared` skeleton with none of the graph in §3. |

**Hand-written file set** (route 2):

```text
settings.gradle.kts        modules, pluginManagement, dependencyResolutionManagement
gradle/libs.versions.toml  every coordinate and plugin id — the single place versions live
gradle.properties          jvmargs, AndroidX, Kotlin code style, caching/parallel flags
build.gradle.kts (root) + build-logic/ (own settings + convention plugins, §5)
<module>/build.gradle.kts  one per module in §3
composeApp/src/{commonMain,androidMain,iosMain,desktopMain}/kotlin/… (§6) + AndroidManifest.xml
shared/designsystem/src/commonMain/composeResources/values/strings.xml
.gitignore  .editorconfig  detekt.yml     local.properties stays untracked
```

**Gradle wrapper.** Never hand-write `gradle-wrapper.jar`. In order: `gradle` on PATH →
`gradle wrapper --gradle-version <resolved at the gate>`; otherwise copy `gradlew`, `gradlew.bat`,
`gradle/wrapper/gradle-wrapper.jar` and `gradle-wrapper.properties` from another Gradle project on
the machine and edit `distributionUrl`; otherwise hand the developer the exact command. Afterwards
`./gradlew wrapper …` upgrades it in place — record `distributionSha256Sum` so it is verified.

**Xcode project.** `iosApp/iosApp.xcodeproj` is not authored as text — take it from route 1 or 3, or
hand the step to the developer; on Linux and Windows, gate the iOS targets from the first commit
(§11) and defer `iosApp` to the first macOS machine. **Missing toolchain** (JDK, Android SDK, Xcode,
`kdoctor`): never install it, never use `sudo` — print the exact command for the developer to run in
their own terminal and keep scaffolding whatever it does not block.

## 3. Module graph at MVP size

```
composeApp/            entry point per target, Koin start, nav display, app theme wiring
shared/core/           Result/error types, dispatcher provider, logger facade, expect/actual
                       platform capabilities (http engine, secure store, db builder)
shared/designsystem/   theme tokens, typography, shapes, shared composables, composeResources
shared/domain/         domain models, repository interfaces, use cases
shared/data/           DTOs + api/, Room database/, repository implementations, mappers, data DI
feature/<slice>/       the one vertical slice from §7 — presentation only
build-logic/           convention plugins
iosApp/                Xcode project + SwiftUI host (shared-UI variant: thin; logic-only: the app)
```

Deliberately merged, and why it is safe:

| One module now | Three at scale | Split when |
|---|---|---|
| `shared/core` | core + platform + shared UI utilities | a second platform capability class appears, or UI helpers start pulling Compose into a logic module |
| `shared/data` | network + database + repositories | a second backend, or an offline-first cache policy with real logic (per `kmp-data-layer`: no speculative `DataSource`) |
| `shared/domain` | one module per bounded context | contexts stop sharing models |
| routes inside `feature/<slice>` and the nav display in `composeApp` | a `shared/navigation` module | **the second feature module lands** — cross-feature routing is what the module exists for; until then it would be an empty indirection |

Also deferred, with its trigger: `shared/testing` (shared fakes) → a fake needed by two modules'
`commonTest`; one `feature/*` per feature → from the second slice on, never a shared "features"
module; analytics / crash reporting → out of MVP by default. Boundaries hold from day one even at
this size: `feature` → `domain`, `designsystem`, `core`; `data` → `domain`, `core`; `domain`
depends on nothing; `composeApp` is the only module that sees them all.

## 4. Baseline dependency set, by role

Names only. **Every version — library and Gradle plugin alike — is resolved at plan time through the
`v1rus-dependencies` gate** (identity, latest stable, vulnerability scan, current-API study) and
lands in `gradle/libs.versions.toml`. A version copied from memory or a document is a defect.

**Mandatory for the MVP** — *build plugins:* Kotlin Multiplatform, Android Gradle Plugin, Compose
Multiplatform, the Compose compiler (ships with Kotlin), kotlinx-serialization, KSP. *Static
analysis:* detekt at the root, Android Lint on the Android target. *DI:* Koin — core, Compose,
viewmodel. *Presentation:* AndroidX Lifecycle ViewModel multiplatform (the store base).
*Navigation:* the JetBrains KMP navigation-compose artifact (`org.jetbrains.androidx.navigation`).
*Networking:* Ktor client core, content-negotiation and logging plus one engine per target (OkHttp /
Darwin / CIO) — droppable only on `Backend: none`. *kotlinx:* serialization-json, coroutines-core,
datetime. *Logging:* one multiplatform logger (Napier or Kermit) behind `shared/core`'s facade, so
features never import it. *Testing:* kotlin-test, kotlinx-coroutines-test, MockEngine, Turbine.

**Deferred, with the trigger that adds it** — Room KMP + the bundled SQLite driver, schema export
on: caching or offline in the brief. multiplatform-settings or AndroidX DataStore plus a
Keystore/Keychain token store: auth in scope. Coil multiplatform: remote images.
kotlinx-collections-immutable: Compose stability pressure in a list.

No mocking library, ever — handwritten fakes (`kmp-testing`). Confirm a dependency publishes KMP
artifacts before it reaches common code; an Android-only library compiles on Android and breaks iOS.

## 5. Build configuration

- **Coordinates only in `gradle/libs.versions.toml`** — never in a module script; `implementation`
  by default, `api` only for types in a module's public surface (`gradle-conventions`).
- **`build-logic/` from the start**, three convention plugins: KMP library (targets, source sets,
  `jvmToolchain`, detekt), Compose feature (that plus Compose and the presentation stack), test.
  Six modules re-declaring the plugin stack is the debt this prevents.
- From the brief: application id / bundle id and namespace, display name, `compileSdk` / `minSdk` /
  `targetSdk`, iOS deployment target, desktop distribution name. Minimum platform versions come from
  this layer's current baseline, not a number in a document. **No flavors unless the brief asks.**
- `gradle.properties`: AndroidX, official Kotlin code style, parallel + configuration cache, daemon
  JVM args — with `jvmToolchain` in the convention plugin so the daemon's JDK is not load-bearing.
- **Codegen:** Room through KSP per target, `schemas/` exported and committed; compose resources
  generated from `composeResources/` into `Res` with its package configured explicitly. Take both
  task names from the build you just created, never from memory.

## 6. App skeleton

| Piece | What the scaffold creates |
|---|---|
| Entry points | Android `Application` + one `Activity`; the iOS framework entry returning the root view controller (shared-UI) or exposing the shared surface (logic-only); desktop `main` with `application { Window { … } }` |
| DI | one `initApp()` in `composeApp/commonMain`, called from every entry point: logging first, then `startKoin` with the core, platform, network, data, domain, designsystem and feature module lists. Nothing starts Koin twice; platform-only bindings stay in the per-platform module — `di-koin-conventions` |
| Theme | `AppTheme` in `shared/designsystem` — colour, typography, shape, spacing tokens. Feature code reaches Material 3 only through it |
| Navigation | one nav display in `composeApp` driven by an app navigator, the start route registered in the `SerializersModule`, dialog and bottom-sheet scene strategies wired — `compose-navigation-patterns` |
| Network | the `expect`/`actual` `HttpClientFactory` (OkHttp / Darwin / CIO); shared configuration in the common builder — JSON negotiation, logging, timeouts, base URL from the brief — and one real endpoint, the one §7 consumes |
| Storage | only what the brief needs: the Room builder as `expect`/`actual` with one entity and one DAO, or the secure token store when auth is in scope |
| Localisation, errors | `composeResources/values/strings.xml` carries the slice's keys from the first screen, empty/error/retry copy included; the project error type sits in `shared/core`, and Ktor / SQLite failures are mapped at the data → domain boundary |

## 7. The first vertical slice

Real, compiling, runnable code — never a TODO. Build the brief's **first MVP feature that reads
data** as a list; no obvious candidate → a list of the product's primary entity; no entity at all →
a home screen driven by a repository reading local storage. On `Backend: none yet` keep the whole
slice and back the API with a `MockEngine` fixture behind the same interface, so swapping in the
real base URL touches one file.

```text
shared/domain/  Item.kt, ItemRepository.kt (interface), GetItemsUseCase.kt
shared/data/    api/item/ItemApi.kt, api/item/ItemDto.kt (@Serializable, @SerialName),
                ItemMapper.kt, ItemRepositoryImpl.kt, di/DataModule.kt
feature/items/  ItemsDestination.kt (public), ItemsScreen.kt (internal), ItemsRoute.kt,
                ItemsModelUi.kt (State + Intent + Effect together), ItemsViewModel.kt,
                components/Items{Loading,Empty,Error,Content}Part.kt, di/ItemsModule.kt
shared/data/src/commonTest/  ItemRepositoryImplTest.kt
```

- `State` is one `@Immutable` object covering **Loading / Empty / Error / Content**; `ItemsScreen`
  does `when (state)` and delegates to the matching `*Part` — no branch UI inlined.
- **Error carries a retry intent**, and the top bar is hoisted outside the state `when`, so back
  navigation is reachable while loading and after a failure.
- Effects (navigate, snackbar) are collected in `ItemsDestination`, never in `ItemsScreen`. The
  content list uses a stable `key` and `contentType`; every item model is `@Immutable`.
- Every string — title, empty copy, error copy, retry, each `contentDescription` — is a resource key.
- One test in `commonTest`: the repository over `MockEngine`, one success and one failure path. It
  proves the test wiring runs, independently of the complexity band that governs feature work later.

## 8. Project `CLAUDE.md` inputs

The facts every downstream v1rus plugin reads. Record the **real** values from the tree you just
created, not the placeholders above.

- Module paths exactly as declared in `settings.gradle.kts`, plus the dependency direction rule.
- Gradle task names: desktop compile, Android assemble, test, detekt, desktop run, the iOS framework
  link task, the KSP/Room and compose-resources codegen tasks.
- The type names the conventions refer to abstractly: the store view-model base, the app navigator
  and nav display, the result store, `AppTheme`, the generated `Res` object, `HttpClientFactory`,
  the database class and its builder, the error type, the logger facade.
- Where tests live (`commonTest` of `shared/data` and `shared/domain`), run on the desktop target.
- The iOS framework name and entry point, and the property or host check gating the iOS targets.
- Scaffold variant, application id, minimum platform versions, backend base-URL source, locales.
- Enable `v1rus-kmp` in `.claude/settings.json` — it pulls `v1rus-compose` → `v1rus-kotlin` →
  `v1rus-core`.

## 9. Verification

Run in this order; stop at the first failure and send the exact error back to the implementing agent.

| Check | Command | Headless |
|---|---|---|
| Wrapper resolves | `./gradlew --version` | yes |
| Common code is genuinely common | the desktop target's compile task, e.g. `:composeApp:compileKotlinDesktop` | yes |
| Static analysis | `./gradlew detekt` | yes |
| Scaffold test | the desktop test task of `shared/data` | yes |
| Android app assembles | `:composeApp:assembleDebug` | yes, with an Android SDK |
| iOS framework links | the debug framework link task for the simulator target | macOS + Xcode only |

"Runnable" per target: desktop `:composeApp:run`, Android `:composeApp:installDebug` + launch, iOS
from Xcode. Only the desktop run needs no device; Android and iOS go to the developer unless a
mobile-automation MCP is bound. On a non-macOS host the iOS rows are recorded as *not verified
here*, never as passed.

## 10. Escalation targets

Build configuration — wrapper, settings, version catalog, convention plugins, module scripts →
`v1rus-kotlin:build-engineer`. Logic — domain, data, Ktor, Room, mappers, Koin bindings,
`expect`/`actual` → `v1rus-kotlin:kotlin-engineer`. UI — theme, design system, nav display,
screens, the store view model → `v1rus-compose:compose-developer`. iOS entry point, Swift glue and
a native SwiftUI shell → `v1rus-kmp:swift-engineer` and `v1rus-kmp:swiftui-developer`. Build and
test runs → `v1rus-kmp:test-runner`. `feature-developer` is the floor when a layer is not
installed; agents touching the same files run sequentially.

## 11. Known first-run traps

1. **`android.*` / `java.*` in `commonMain`** compiles on the Android target and breaks iOS and
   desktop, often weeks later. That is why the desktop compile is the *first* verification step.
2. **Compose stack version alignment.** CMP core, Material 3 and the KMP navigation fork are
   versioned independently and the fork can lag androidx upstream; the Compose compiler is tied to
   the Kotlin version. A mismatch surfaces as an opaque compiler or runtime error — resolve each
   artifact separately at the gate (`kmp-conventions` § Version alignment).
3. **Ktor engine per source set.** The common client builder compiles with no engine and then fails
   at runtime with "no engine found". Declare one in every platform source set; `MockEngine` in
   `commonTest`.
4. **iOS targets on a non-macOS host.** Gate them behind a host check or Gradle property in the
   first commit — retrofitting the gate means touching every module script. A skipped iOS module on
   Linux is deliberate, not a bug to fix.
