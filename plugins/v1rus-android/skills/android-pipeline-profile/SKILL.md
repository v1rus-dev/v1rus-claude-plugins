---
name: android-pipeline-profile
description: "Stack profile that binds the stack-agnostic v1rus feature pipeline to a native-Android project: the layer vocabulary the architecture plan uses (Gradle modules, no multiplatform source sets), the stack-specific sections of architecture-plan.md, which convention skill owns which area, the presentation pattern (androidx.lifecycle.ViewModel holding the MVI store, Destination⇄Screen), design-system mapping for a design spec, where tests live and on what (src/test by default, src/androidTest opt-in, JUnit, handwritten fakes, MockEngine), how to compile-check with variant-aware Gradle tasks, which engineer agents implementation escalates to, and the finalizer's Android checklist. Loaded by feature-architect, feature-designer, feature-developer, test-planner, test-writer and feature-finalizer when the pipeline detects a native-Android project. Do NOT load for pipeline mechanics — gates, complexity bands and commit discipline live in feature-pipeline. Do NOT load for a Compose Multiplatform repo — that is kmp-pipeline-profile."
---

# Pipeline profile — native Android

The pipeline agents (`feature-architect`, `feature-designer`, `feature-developer`, `test-planner`,
`test-writer`, `feature-finalizer`) are stack-agnostic. This profile is the **vocabulary** they use on
a native-Android project: what the layers are called, what the plan must cover, where tests go, which
convention skill owns which rule.

Two boundaries that matter:

- **Pipeline mechanics are not here.** Phase order, gates, complexity bands, artifact names, commit
  discipline and resume live in the `feature-pipeline` skill. This file never repeats them.
- **The project still owns the names.** Real module paths, type names, product flavors, variant names
  and build/test task names come from the target project's `CLAUDE.md`, `settings.gradle.kts` and its
  module build files. Read those first; **never invent a module that is not declared in
  `settings.gradle.kts`, and never invent a Gradle task.** This profile gives the shape those modules
  take, not the list.

## Stack identity

Markers: `settings.gradle.kts` (or `.gradle`) whose application module applies
**`com.android.application`**, an `AndroidManifest.xml` under `app/src/main/`, `gradle/libs.versions.toml`,
`.kt` sources under `src/main/`, and — decisively — **no `commonMain` source set anywhere**. A repo with
`commonMain` is KMP and uses `v1rus-kmp:kmp-pipeline-profile` instead; if both markers appear, ask which
surface the task touches before planning.

House stack on this profile: Koin for DI, Ktor client on the OkHttp engine, Room, DataStore,
kotlinx.serialization, `androidx.lifecycle.ViewModel` holding the MVI store, Compose UI.

## Layer vocabulary

Layers here are **Gradle modules**, not source sets. Every module is a `settings.gradle.kts` entry with
its own `build.gradle.kts` and its own manifest where it needs one.

| Layer | Holds |
|---|---|
| `app` module | the `Application` class, the single `Activity`, the merged manifest, Koin start-up, the top-level nav host, build types and flavors |
| feature module | screens, the feature's `ViewModel`s and their MVI stores, State/Intent/Effect, UI models, feature-local destinations, the feature Koin module |
| navigation module | app-wide routes, route serialization registration, the navigator |
| design-system module | theme tokens, typography, shapes, shared composables |
| domain module | domain models, repository **interfaces**, use cases — pure Kotlin, no `android.*` |
| data module | DTOs, Ktor API clients, Room entities/DAOs/database, DataStore wrappers, repository **implementations**, mappers, the data Koin module |
| core modules | shared infrastructure — the HTTP client and its auth plumbing, common UI utilities, result/error types |

Hard boundaries: feature modules never depend on each other (contracts go through core/domain); the
domain module carries no Android dependency; app-wide routes live in the navigation module, only a
module-local dialog/bottom-sheet route stays in the feature; no speculative `DataSource` layer between
repository and API/DAO; `app` depends on features, never the reverse.

## `architecture-plan.md` — stack sections

Use these in place of the generic layer sections:

```
## 3. Data layer changes         (DTOs + @SerialName, Ktor API client methods, Room entities/DAOs/
                                 database version + migration, DataStore keys, mappers,
                                 repository implementations, data Koin module)
## 4. Domain layer changes       (models, repository interfaces, use cases)
## 5. Presentation layer changes (feature module, Destination⇄Screen split, the ViewModel and its
                                 MVI store, State/Intent/Effect, *Part composables, UI models,
                                 feature Koin module)
## 6. Manifest, navigation & wiring
                                 (new permissions / activities / providers and their merge impact,
                                 routes + serialization registration, Koin module lists,
                                 module dependencies added to build.gradle.kts, new modules added to
                                 settings.gradle.kts)
```

Self-questions the plan must answer for this stack: which existing module owns this code, and is a new
module actually justified; does anything new drag an `android.*` import into the domain module; does the
change add a manifest entry, permission or exported component; does a Room schema change need a
migration; are new Koin bindings registered in the module that owns them; is a new route registered
where routes are serialized.

## Convention skills by area

| Area | Skill |
|---|---|
| module graph, manifest, `Context`/lifecycle discipline | `v1rus-android:android-conventions` |
| Room, Ktor-on-OkHttp + bearer refresh, DataStore, repositories | `v1rus-android:android-data-layer` |
| tests | `v1rus-android:android-testing` |
| ViewModel + MVI store, State/Intent/Effect | `v1rus-compose:mvi-presentation` |
| Destination⇄Screen split, screen structure | `v1rus-compose:compose-screen-architecture` |
| one composable per file, `@Preview`, `*Sections.kt` | `v1rus-compose:compose-file-organisation` |
| screen states, a11y, theme tokens, lazy lists | `v1rus-compose:compose-ui-conventions` |
| animated state changes | `v1rus-compose:compose-animations` |
| routes, dialogs and bottom sheets as destinations | `v1rus-compose:compose-navigation-patterns` |
| clip-before-clickable, touch targets, ripple | `v1rus-compose:compose-clickability` |
| Koin modules, constructor injection | `v1rus-compose:di-koin-conventions` |
| strings and plurals | `v1rus-compose:localisation-and-strings` |
| Compose performance (lazy layouts, state-read deferral, stability, R8, baseline profiles, …) | the `v1rus-compose` performance skill set |
| Kotlin style, coroutines/Flow | `v1rus-kotlin:kotlin-conventions`, `v1rus-kotlin:kotlin-coroutines` |
| Gradle, version catalog, convention plugins | `v1rus-kotlin:gradle-conventions` |
| adding or bumping a dependency | `v1rus-core:v1rus-dependencies` |

Name the applicable ones in the plan so the implementing agent invokes them; invoke them yourself before
writing non-trivial presentation or performance-sensitive code. If a skill is absent in the current
environment, proceed — never hard-depend on one.

## Presentation pattern

A stateful screen is driven by an **`androidx.lifecycle.ViewModel` that holds the MVI store** typed over
`State` / `Intent` / `Effect` — the store contract is `v1rus-compose:mvi-presentation`, the ViewModel is
the Android host that gives it `viewModelScope` and survives configuration change. The composable never
owns the store, and nothing in the store touches `Context`, `Activity` or a resource id.

Keep `init {}` minimal; extract orchestration into named functions; in `onIntent`, a branch needing more
than one call becomes a private function. `*Screen` and `*Part*` composables are `internal`; each state
renders through a dedicated `*Part<State>` composable. Theme tokens only — never `MaterialTheme.*`
directly in feature code.

## Design-spec mapping (feature-designer)

Map Figma onto the project's **design-system module**, not raw Material 3: colors → theme color tokens,
type → the project typography API, spacing → existing spacing conventions, components → existing shared
composables first. Discover the available tokens with `ast-index` before proposing a raw value. Note
Android-only surfaces the mockup implies — status/navigation bar treatment, edge-to-edge insets, the
system back gesture — since a design spec that ignores them produces a screen that fails review on device.

## Tests

- Location: **`src/test/`** of the module that owns the code — the default for view models, use cases,
  repositories and mappers. `src/androidTest/` is **opt-in** and is not part of the pipeline's
  verification loop, because it needs a device or emulator.
- Framework: **JUnit** — which generation is whatever the project's build files already wire. Never add
  a test framework or runner to a module as part of a feature.
- Doubles: **handwritten fakes**, no mocking libraries. Reuse the project's existing fakes package before
  writing a new fake.
- API tests use Ktor **`MockEngine`**; DAO tests use an in-memory Room database or a fake DAO; DataStore
  and preferences use an in-memory implementation of the project's storage interface.
- Naming: one test class per production class, `<ProductionClass>Test`, mirrored package.
- Out of scope for the pipeline's test phases — state this explicitly in the plan: instrumented
  (`src/androidTest`) tests, Compose UI tests, screenshot tests, and anything needing a device.
- Detail: `v1rus-android:android-testing`.

## Verification

- Compile check after an implementation pass: a variant-scoped compile or assemble of the affected
  module (the Android Gradle plugin's shapes are `assemble<Variant>` and the per-variant compile tasks) —
  **exact task names from the project's `CLAUDE.md` and build files, never guessed**, since product
  flavors change every variant name.
- Static analysis: the project's lint task for the variant under change (`lint<Variant>` in AGP's shape)
  plus whatever the project wires on top.
- Full build + test run belongs to the `test-runner` agent of this layer (`v1rus-android:test-runner`),
  which discovers the project's own tasks.
- Never read `.gradle/`, `.m2/` or `build/`.

## Implementation escalation targets

**This layer deliberately ships no engineer agent of its own** — do not go looking for an
`android-engineer`. Native-Android code is Kotlin plus Compose, and both already have an owner:

| Work | Escalate to |
|---|---|
| Compose UI, screens, the ViewModel + MVI store | `v1rus-compose:compose-developer` |
| domain, data, repositories, Ktor/Room/DataStore, coroutines | `v1rus-kotlin:kotlin-engineer` |
| `build.gradle.kts`, version catalog, convention plugins, variants | `v1rus-kotlin:build-engineer` |

`feature-developer` remains the floor and handles the ordinary case; escalate when the change is
concentrated in one of those specialisms.

## Finalizer stack checklist

On top of the generic cleanup: no `android.*` import in the domain module; no `Context`, `Activity` or
resource id held by a store, ViewModel or repository; Koin bindings registered in the module that owns
them; every new route registered where routes are serialized; module boundaries intact and every new
module declared in `settings.gradle.kts`; new manifest entries minimal and no component exported without
a reason; Room schema change accompanied by a migration; `modifier: Modifier = Modifier` defaults and
parameter ordering; Material 3 reached only through the design system; one composable per file with a
`@Preview`; no leftover debug logging or `TODO` scaffolding.

## Typical expert reviews to flag

`performance-expert` for lazy lists, recomposition-heavy screens, new Flow plumbing or anything on the
startup path; `ux-expert` for a new screen, navigation change or insets/back-gesture behaviour;
`security-expert` for auth, token storage, DataStore contents, exported components or a new permission;
`build-engineer` for build-script, variant or version-catalog changes; `architecture-expert` when the
change crosses module boundaries or introduces a new module.
