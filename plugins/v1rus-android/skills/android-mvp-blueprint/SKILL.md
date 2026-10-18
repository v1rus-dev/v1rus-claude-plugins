---
name: android-mvp-blueprint
description: "The /mvp-init MVP blueprint for native Android / Jetpack Compose: how an empty Android project comes into existence when there is no IDE wizard to run, the Gradle wrapper and toolchain reality, the MVP-sized module graph (app, core:designsystem, core:navigation, core:domain, core:data, one feature) and when each deferred module appears, the baseline dependency set by role with no versions, version-catalog and convention-plugin build configuration, the app skeleton (Application + Koin start-up, MainActivity, theme seed, nav host, Ktor client, DataStore, strings), the first working vertical slice with loading/empty/error/content states, the facts the generated project CLAUDE.md must record, the verification commands, escalation targets and the first-run traps. Load when creating a new native-Android app from scratch, bootstrapping a fresh Gradle module graph, scaffolding an Android project, building its first vertical slice, or generating that project's CLAUDE.md. Do NOT load to add a feature to an existing Android project — that is android-pipeline-profile — and do NOT load for a multiplatform app, which is the KMP blueprint."
---

# MVP blueprint — native Android / Jetpack Compose

The technology half of `/mvp-init` for a single-target Android app: the command owns the process, this
file owns the stack. Once the scaffold exists, feature work switches to
`v1rus-android:android-pipeline-profile` — same vocabulary, different moment. Conventions are
referenced, never restated: `android-conventions`, `android-data-layer`, `android-testing`, and the
`v1rus-compose` set (`mvi-presentation`, `compose-screen-architecture`, `compose-navigation-patterns`,
`di-koin-conventions`, `localisation-and-strings`).

## 1. Stack identity

Choose this stack when the brief says **Android only**, no second platform sharing code, the team is
Kotlin, and the product leans on platform surfaces (widgets, background work, notifications, deep OS
integration) where a shared abstraction would only be in the way. Anti-signals:

| Brief says | Go to |
|---|---|
| iOS **and** Android from one codebase | `v1rus-kmp:kmp-mvp-blueprint` |
| Flutter named, or a design-driven app on many targets fast | `v1rus-flutter:flutter-mvp-blueprint` |
| A project already exists here | `/feature` with `android-pipeline-profile` — this blueprint does not retrofit |
| "Android now, iOS within the year" | KMP. A native Android app is not cheaply converted later; a shared `domain`/`data` is the whole point of paying KMP's cost up front |

## 2. Bootstrap route

**There is no Android project generator on the command line.** Say so plainly instead of pretending:
Android Studio's New Project wizard makes the best skeleton and is **IDE-only**, undrivable from a
terminal; **`gradle init`** has no Android type and emits a JVM skeleton whose build scripts must be
deleted and rewritten, its only durable output being the wrapper that `gradle wrapper` gives directly;
the legacy `android create project` tool no longer exists — ignore any tutorial using it.

So the real work is **hand-written files** in every route; routes differ only in how the wrapper arrives.

| Route | Precondition | Cost |
|---|---|---|
| **A (preferred)** — `gradle wrapper` in the empty directory, then write the Android files | `gradle` on PATH (used once, for the wrapper only) | lowest; nothing to undo |
| **B** — copy `gradlew`, `gradlew.bat` and `gradle/wrapper/` (jar + properties) from another Gradle project on this machine, set `distributionUrl` to the resolved version, then `./gradlew --version` | any other Gradle checkout present | one edit plus a real run to confirm the distribution downloads |
| **C** — write every text file, skip the build, hand the developer the install command | no wrapper obtainable | scaffold is complete but **unverified**; say so in the report |

`gradle-wrapper.jar` is a binary and cannot be hand-written — that is why B exists. **Verify
empirically:** a blueprint cannot know this machine, so run `gradle --version`, `./gradlew --version`,
`java -version`, `adb devices` and read the output before relying on any of them.

**Missing toolchain — never install anything, never use elevated privileges.** Print the exact command
for the developer's own terminal (they can run it in-session by prefixing it with `!`) and continue with
everything that does not depend on it: Gradle via their normal installer (e.g. `sdk install gradle`);
a JDK matching the resolved AGP; the SDK via
`sdkmanager --install "platform-tools" "platforms;android-<compileSdk>" "build-tools;<buildTools>"`
followed by `export ANDROID_HOME=<sdk-path>`.

**Hand-written file set** (the deliverable in all three routes):

```
settings.gradle.kts       pluginManagement + dependencyResolutionManagement (google, mavenCentral),
                          rootProject.name, includeBuild("build-logic"), every include(":…")
gradle/libs.versions.toml the only declaration site for coordinates, plugin ids and SDK levels
gradle.properties         android.useAndroidX, JVM args, configuration cache, parallel
build-logic/              its own settings.gradle.kts + the convention plugins
build.gradle.kts (root)   plugins { … apply false }
<module>/build.gradle.kts one per module, applying a convention plugin
app/src/main/AndroidManifest.xml  + a library manifest only where a module owns something
app/src/main/res/         values/strings.xml, values/themes.xml, adaptive-icon XML (no binary assets)
app/src/main/kotlin/…/    App.kt (Application) and MainActivity.kt
.gitignore                build/, .gradle/, local.properties, IDE dirs
```

`local.properties` is machine-local: never write it for the developer and never commit it.

## 3. Module graph at MVP size

Six modules. Smaller than a mature graph on purpose — boundaries first, module count later.

| Module | Plugin | Holds at MVP |
|---|---|---|
| `:app` | `com.android.application` | `Application`, `MainActivity`, merged manifest, Koin start-up, the module lists, the nav host |
| `:core:designsystem` | library + Compose | theme, color/typography/shape tokens, shared composables, and for now the UI utilities that later become `:core:ui` |
| `:core:navigation` | library | route keys, the navigator, the `SerializersModule` |
| `:core:domain` | **plain Kotlin JVM** | domain models, repository interfaces, use cases, the `Logger` interface — no `android.*`, and it builds and tests faster as a JVM module |
| `:core:data` | library | `api/` (Ktor client factory, endpoints, DTOs), `database/` (only if Room is in), DataStore wrappers, repository implementations, mappers, the data Koin module |
| `:feature:<slice>` | library + Compose | the one vertical slice |

**One module at MVP that is three at scale:** `:core:data` is `:core:network` + `:core:database` +
`:core:data` collapsed — safe *because the packages inside it are already the split*, so extracting one
later is a file move plus a build script, not a redesign. It stops being safe the moment those internal
boundaries break, which is why `android-data-layer`'s layout rules apply from file one.

**`:core:navigation` exists even with a single route:** the direction is `app → feature`, so a feature
can never see `app`; routes need a neutral home from the second feature on, and adding it later touches
every feature module.

| Deferred | Created when |
|---|---|
| `:core:network`, `:core:database` | a second consumer appears, or `:core:data` build time / ownership becomes a measured cost — never "for symmetry" |
| `:core:ui` | a non-token shared composable is used by two or more features |
| `:core:common` | the same utility is copied a third time |
| `:feature:*` #2…n | one per backlog slice, as `/feature` reaches it |
| `:core:auth` | the brief has auth **and** more than one feature reads the session |
| baseline-profile / benchmark module | after there is a release build worth profiling; product flavors only if the brief asked |

## 4. Baseline dependency set, by role

Names only. **Every coordinate goes through `v1rus-core:v1rus-dependencies` at plan stage** — latest
stable resolved, CVE-checked, API studied — and lands in `gradle/libs.versions.toml`. A version copied
from memory or a snippet is a plan defect.

| Role | Libraries | MVP |
|---|---|---|
| Gradle plugins | Android Gradle plugin, Kotlin Android, **Compose Compiler Gradle plugin** (`org.jetbrains.kotlin.plugin.compose`), kotlinx-serialization | mandatory |
| Codegen | KSP | only with Room |
| UI | Compose BOM, Compose UI, Material 3, ui-tooling-preview (+ ui-tooling on `debugImplementation`), activity-compose | mandatory |
| State holder | lifecycle-viewmodel, lifecycle-viewmodel-compose, lifecycle-runtime-compose (for lifecycle-aware collection) | mandatory |
| Navigation | androidx navigation-compose, typed routes | mandatory |
| DI | Koin core, Koin Android, Koin Compose | mandatory |
| Serialization | kotlinx-serialization-json | mandatory — routes need it even when there is no backend |
| Networking | Ktor client core, OkHttp engine, content-negotiation, kotlinx-json, logging | mandatory when the brief has any backend, mock included |
| Auth | Ktor's auth plugin, wired per `v1rus-kotlin:ktor-client-auth` | only with auth |
| Persistence | DataStore Preferences | mandatory once anything is persisted (session, settings); Room runtime + compiler deferred until there is structured local data |
| Image loading | Coil, Compose artifact | deferred until a screen renders remote images |
| Logging | Timber (or the logger the brief names) behind the project `Logger` interface — `v1rus-core:v1rus-logging` | mandatory |
| Testing | JUnit (the generation the project wires), coroutines-test, Turbine, Ktor `MockEngine` | mandatory; Room testing, AndroidX runner and Compose UI test deferred with the instrumented lane |
| Static analysis | Android Lint — ships with AGP, no coordinate | mandatory; detekt / ktlint deferred, and adding one is a plan-stage decision |

## 5. Build configuration

- **Version catalog is the single declaration site** for coordinates, plugin ids, SDK levels and
  bundles; no literal coordinate in a module script (`v1rus-kotlin:gradle-conventions`).
- **`build-logic` included build from day one**, with an application, a library and a Compose convention
  plugin: four library modules already repeat the same configuration, and retrofitting convention
  plugins costs strictly more than starting with them. Plain scripts only for a single-module throwaway;
  never configure modules from the root script via `subprojects`.
- **Brief → build values:** product name → `rootProject.name` + the `app_name` string; app identifier →
  `applicationId` in `:app` only, with a unique `namespace` per module; `minSdk`/`compileSdk`/`targetSdk`
  → `[versions]`, chosen at plan stage from the current Android baseline and never invented here;
  flavors only if asked.
- **Signing:** debug only — never generate or commit a release keystore; it is the developer's and goes
  in the report as a manual step. **Java toolchain** declared once in the convention plugin, at the
  level the resolved AGP requires, so every module and the Gradle daemon agree.
- **Codegen:** with Room, KSP plus `schemaDirectory`; the exported schema JSONs are committed, since
  they are the input to migrations and their tests.
- **R8 on the release build type from day one** (`isMinifyEnabled`) with the Compose keep rules from
  `v1rus-compose:configuring-r8-for-compose`. Enabling it after twenty screens is how a release gets
  blocked by a week of missing-rule debugging.

## 6. App skeleton

Everything below is wired and proven by the verification run; no placeholder is left unconnected.

| Piece | Shape |
|---|---|
| Entry point | `App : Application` — `onCreate` initialises **logging first, then Koin**: `startKoin { androidContext(this@App); modules(appModules) }`. Nothing else; work here is paid on every cold start |
| Activity | a single `MainActivity : ComponentActivity` — `enableEdgeToEdge()`, then `setContent { AppTheme { AppNavHost() } }`; `android:exported="true"` on it and nothing else |
| DI | module lists in `:app` (`networkModule`, `dataModule`, `domainModule`, `platformModule`, `navigationModule`, `featureModules`); `platformModule` is the only place a binding may need `Context`. Constructor injection everywhere — `di-koin-conventions` |
| Theme | `AppTheme` composable plus the token object in `:core:designsystem`; feature code reaches Material 3 only through it, never `MaterialTheme.*` directly |
| Navigation | `AppNavigator` and the nav host in `:core:navigation`, one `@Serializable` start route **registered in the `SerializersModule`** — an unregistered route fails silently, as lost state after process death |
| Network | one `HttpClient` built by a single factory on the OkHttp engine — content negotiation with kotlinx-json (`ignoreUnknownKeys`), timeouts, `defaultRequest` base URL, logging — bound as a singleton |
| Storage | `preferencesDataStore` delegate declared once at file top level, bound with the application context and exposed behind a typed wrapper, never as a raw `DataStore<Preferences>` |
| Localisation | `values/strings.xml` seeded with **every** string the slice renders, error and empty copy included. A hardcoded user-visible literal is a scaffold defect — `localisation-and-strings` |
| Logging | `Logger` interface in `:core:domain`, its implementation bound in `platformModule` |

## 7. The first vertical slice

**Real working code, never a TODO.** One read-only list screen end to end: `:core:data` API + DTO →
mapper → repository implementation → interface and use case in `:core:domain` → ViewModel holding the
MVI store → Compose screen in `:feature:<slice>`.

- **Which slice** when the brief gives no obvious candidate: the first backlog item that only *reads*
  data. Backend "none yet" or "mock" → the same slice against an in-memory fake behind the domain
  repository interface, so swapping in the real API is one Koin binding.
- **Types** (`mvi-presentation`, `compose-screen-architecture`, `compose-file-organisation`):
  `<Slice>Destination` (public — DI, effects, navigation), `internal <Slice>Screen` (pure `state` +
  `onIntent`), `<Slice>ModelUi.kt` holding `State`/`Intent`/`Effect` together, one `internal
  <Slice><X>Part` per state branch, each with a `@Preview`.
- **All four states implemented:** loading, content, empty (human copy from a string resource, not a
  blank screen), error with a retry intent that re-runs the load. The top bar is hoisted **outside** the
  state `when`, so back is reachable in the error and loading states too (`compose-ui-conventions`).
- **One test** in `<feature>/src/test/`: the ViewModel through loading → content and loading → error
  against a handwritten fake repository — the cheapest proof that the test source set, coroutines-test
  and the fakes convention are actually wired (`android-testing`).

## 8. Project `CLAUDE.md` inputs

Hand `/mvp-init` these facts, verbatim from what was created — every downstream plugin reads them:

- Module paths exactly as in `settings.gradle.kts`, each with its one-line role, the dependency
  direction (`app → feature → core`, `data → domain`), and the deferred-module table from §3.
- Build and test task names **as created**, variant spelled out: `:app:assembleDebug`,
  `:app:installDebug`, `testDebugUnitTest`, `lintDebug` — with the note that flavors would change every
  one of them, so they are read, never constructed.
- Real type names: the `Application`, the Activity, the theme object, the navigator and nav host, the
  MVI store base type, the Koin module lists and the file holding them.
- Codegen: whether KSP is on, and the schema directory if Room is in.
- Test layout: `src/test/` is the loop, `src/androidTest/` is opt-in and needs a device; the JUnit
  generation as wired; handwritten fakes, no mocking library.
- The min / compile / target SDK actually set, and where they are declared.
- Plugins for `.claude/settings.json`: `v1rus-android` (it pulls `v1rus-compose`, `v1rus-kotlin`,
  `v1rus-core`).

## 9. Verification

Headless, in order — none needs a device: `./gradlew :app:assembleDebug` (compiles the whole graph) →
`./gradlew lintDebug` (Android Lint on the variant) → `./gradlew testDebugUnitTest` (the slice's test) →
`./gradlew :app:assembleRelease` (proves the R8 configuration before there is anything to debug).

Preconditions: a JDK matching the resolved AGP and an Android SDK reachable via `ANDROID_HOME` or
`local.properties`. Missing either → route C in §2: report the scaffold as unverified, not as done.

**"Runnable" needs hardware.** `./gradlew :app:installDebug` then
`adb shell am start -n <applicationId>/.MainActivity` starts the app — attempt it only when
`adb devices` lists one, otherwise hand both commands to the developer. Rendering, insets and
edge-to-edge are checked by a human on a screen; no headless command substitutes.

## 10. Escalation targets

This layer ships no engineer agent of its own — there is no `android-engineer` to look for.

| Work | Agent |
|---|---|
| `settings.gradle.kts`, the catalog, `build-logic`, module scripts, `gradle.properties` | `v1rus-kotlin:build-engineer` |
| domain, data, Ktor client, Room, DataStore, repositories, mappers, coroutines | `v1rus-kotlin:kotlin-engineer` |
| theme and design system, nav host and routes, the screen, the ViewModel and its store | `v1rus-compose:compose-developer` |
| verification runs | `v1rus-android:test-runner` |
| anything unclaimed | `v1rus-core:feature-developer` — the floor |

Agents touching the same file — `settings.gradle.kts` and the catalog above all — run **sequentially**.

## 11. Known first-run traps

- **The Compose compiler plugin is separate from Compose.** It ships with Kotlin and must be applied as
  `org.jetbrains.kotlin.plugin.compose` in the Compose convention plugin, versioned with Kotlin. Omit it
  and `@Composable` fails to compile with a message that points nowhere near the cause.
- **No Android SDK, or `ANDROID_HOME` unset** → "SDK location not found". Hand over the `sdkmanager`
  command from §2; never install it, never write `local.properties` with a guessed path.
- **JDK mismatch** → "Unsupported class file major version", or an AGP-requires-JDK-N error. Fix it by
  declaring the Java toolchain in the convention plugin, not by installing a JDK for the developer.
- **Missing `gradle-wrapper.jar`** → "Could not find or load main class org.gradle.wrapper.GradleWrapperMain".
  Route B's whole reason to exist; `gradlew` alone is not a wrapper.
- **`android:exported` is mandatory, not advisory** for any component with an intent filter when
  targeting API 31 or higher — the build fails without it. `false` everywhere except the launcher
  Activity; flipping one to `true` to silence the merger is a security regression.
- **Edge-to-edge is enforced by the system** for apps targeting API 35 or higher, so insets are handled
  in the scaffold rather than discovered when content slides under the status bar.

Branch and commit discipline, the confirmation gate and the report belong to `/mvp-init`. Never bypass
git hooks.
