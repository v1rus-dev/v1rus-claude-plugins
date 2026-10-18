# v1rus-android

The native-Android layer. Depends on `v1rus-compose`, which depends on `v1rus-kotlin`, which depends
on `v1rus-core`: installing this plugin pulls the whole chain.

```
claude plugin install v1rus-android@v1rus
```

## The stack this layer standardises

| Area | Decision |
|---|---|
| Architecture | Gradle modules: `app` / feature / core / domain / data / navigation / design-system. No multiplatform source sets — `commonMain` in such a repository means it is KMP and `v1rus-kmp` applies |
| DI | Koin, one module per layer, registered in the module that owns it |
| Networking | Ktor Client on the OkHttp engine, bearer refresh in one place |
| Storage | Room for structured data, DataStore for settings |
| Serialization | kotlinx.serialization |
| Presentation | `androidx.lifecycle.ViewModel` holding the MVI store from `v1rus-compose:mvi-presentation` |
| UI | Jetpack Compose — the rules come from `v1rus-compose`, not from here |
| Tests | `src/test` by default (JVM, no device), `src/androidTest` opt-in; JUnit plus handwritten fakes, no mocking libraries |

**No version is pinned anywhere here** — only names. The version is resolved at plan stage through the
`v1rus-core:v1rus-dependencies` gate.

## What it contains

| Component | Covers |
|---|---|
| `skills/android-conventions` | The Gradle module graph, manifest and permissions, `Context` and lifecycle discipline |
| `skills/android-data-layer` | Room with a `Context`-bound builder, Ktor over OkHttp with bearer refresh, DataStore, repositories |
| `skills/android-testing` | `src/test` versus `src/androidTest`, JUnit (the generation is read from the project's build files), handwritten fakes instead of mocking libraries, `MockEngine`, in-memory Room, where Robolectric belongs and what it costs, Compose UI tests and when they actually pay off, variant-aware Gradle tasks |
| `skills/android-mvp-blueprint` | The `/mvp-init` blueprint for this stack: bootstrapping an Android project when there is no CLI wizard, the MVP-sized Gradle module graph, the baseline dependency set by role, the app skeleton and its first vertical slice, and the generated project `CLAUDE.md`. |
| `skills/android-pipeline-profile` | The stack profile for the stack-agnostic feature pipeline: layer vocabulary, `architecture-plan.md` sections, the "area → skill" table, the presentation pattern, where tests live, the compile check, escalation targets, the finalizer checklist |
| `rules/android-source.md` | Injected before an Android source file is edited |
| `agents/test-runner` | Discovers the project's own tasks, runs the JVM unit tests and lint, returns PASS/FAIL. Instrumented tests only on explicit request and only with a device attached. Never edits code |
| `hooks/hooks.json` + `hooks/path-rules.py` | Delivery of the path-scoped rules from `rules/`: a plugin cannot ship `.claude/rules/*.md`, so the hook injects the matching rule before `Write`/`Edit` |

## What is deliberately absent

**No engineer agent of its own.** Native Android is Kotlin plus Compose, and both already have an
owner: UI and the `ViewModel` with its store go to `v1rus-compose:compose-developer`; domain, data and
coroutines to `v1rus-kotlin:kotlin-engineer`; build scripts and the version catalog to
`v1rus-kotlin:build-engineer`. `feature-developer` from `v1rus-core` remains the floor. There is no
point looking for an `android-engineer` — there will not be one.

**No Compose skills.** Destination⇄Screen, the MVI store, one composable per file, the screen-state and
accessibility checklist, animations, typed routes, Koin, localisation and the whole performance and
stability set live in `v1rus-compose` and work identically for Jetpack Compose and Compose
Multiplatform. Duplicating them here would create a second copy that drifts from the first.

**No Kotlin or Gradle rules.** Style, coroutines and `gradle-conventions` are `v1rus-kotlin`. Gates,
complexity bands, commit discipline and the pipeline itself are `v1rus-core`.

## What stays with the project

The specifics: real module paths, type names, the product-flavour list and — above all — Gradle task
names. On Android a task name depends on the variant and the variant on the flavours, so neither a
skill nor an agent constructs one on its own: they read the target project's `CLAUDE.md` and its build
files and use what is written there verbatim. The plugin carries the pattern, the project carries the
names.
