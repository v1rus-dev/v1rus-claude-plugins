---
name: kmp-pipeline-profile
description: "Stack profile that binds the stack-agnostic v1rus feature pipeline to a Kotlin Multiplatform / Compose Multiplatform project: the layer vocabulary the architecture plan uses, the stack-specific sections of architecture-plan.md, which convention skill owns which area, the presentation pattern (MVI store, Destination⇄Screen), design-system mapping for a design spec, where tests live and on what (commonTest, kotlin.test, handwritten fakes, MockEngine), how to compile-check, which engineer agents implementation escalates to, and the finalizer's stack checklist. Loaded by feature-architect, feature-designer, feature-developer, test-planner, test-writer and feature-finalizer when the pipeline detects a KMP project. Do NOT load for pipeline mechanics — gates, complexity bands and commit discipline live in feature-pipeline."
---

# Pipeline profile — KMP + Compose Multiplatform

The pipeline agents (`feature-architect`, `feature-designer`, `feature-developer`, `test-planner`,
`test-writer`, `feature-finalizer`) are stack-agnostic. This profile is the **vocabulary** they use
on a KMP project: what the layers are called, what the plan must cover, where tests go, which
convention skill owns which rule.

Two boundaries that matter:

- **Pipeline mechanics are not here.** Phase order, gates, complexity bands, artifact names, commit
  discipline and resume live in the `feature-pipeline` skill. This file never repeats them.
- **The project still owns the names.** Real module paths, type names, indent/line-length settings
  and build-task names come from the target project's `CLAUDE.md` and `settings.gradle.kts`. Read
  those first; **never invent a module that is not declared in `settings.gradle.kts`.** This profile
  gives the shape those modules take, not the list.

## Stack identity

Markers: `settings.gradle.kts` + `gradle/libs.versions.toml`, the Kotlin Multiplatform plugin, a
`commonMain` source set, `.kt` sources. Targets are typically Android + iOS + desktop (`jvm("desktop")`).

## Layer vocabulary

| Layer | Holds |
|---|---|
| feature / presentation module | screens, store view models, State/Intent/Effect, UI models, nav keys local to the feature, feature DI module |
| navigation module | app-wide routes, the `SerializersModule` registration, the navigator |
| design-system module | theme tokens, typography, shapes, shared composables |
| domain module | domain models, repository **interfaces**, use cases |
| data module | DTOs, API clients, Room entities/DAOs, repository **implementations**, mappers, data DI module |
| core / platform modules | shared infrastructure, `expect`/`actual` platform capabilities |

Hard boundaries: feature modules never depend on each other (contracts go through core/domain);
app-wide routes live in the navigation module — only a module-local bottom-sheet route may stay in the
feature; no speculative `DataSource` layer between repository and API/DAO.

## `architecture-plan.md` — stack sections

Use these in place of the generic layer sections:

```
## 3. Data layer changes         (DTOs + @SerialName, API client methods, Room entities/DAOs/migrations,
                                 mappers, repository implementations, data DI module)
## 4. Domain layer changes       (models, repository interfaces, use cases)
## 5. Presentation layer changes (feature module, Destination⇄Screen split, the store view model,
                                 State/Intent/Effect, *Part composables, UI models, feature DI module)
## 6. Navigation & wiring        (nav keys + SerializersModule registration, Koin module lists,
                                 platform-only bindings in the per-platform module)
```

Self-questions the plan must answer for this stack: does anything new belong in `commonMain` rather
than a platform source set; is every `expect` narrow (capability, not platform type); are new Koin
bindings registered in the module that owns them; is a new nav key registered in the right
`SerializersModule`.

## Convention skills by area

| Area | Skill |
|---|---|
| source sets, `expect`/`actual`, module graph | `kmp-conventions` |
| DTOs, Room, repositories, HTTP client + auth refresh | `kmp-data-layer` |
| store view model, State/Intent/Effect | `v1rus-compose:mvi-presentation` |
| Destination⇄Screen split, screen structure | `v1rus-compose:compose-screen-architecture` |
| one composable per file, `@Preview`, `*Sections.kt` | `v1rus-compose:compose-file-organisation` |
| screen states, a11y, theme tokens, lazy lists | `v1rus-compose:compose-ui-conventions` |
| animated state changes | `v1rus-compose:compose-animations` |
| routes, dialogs and bottom sheets as destinations | `v1rus-compose:compose-navigation-patterns` |
| Koin modules, constructor injection, `getAll` + `bind` | `v1rus-compose:di-koin-conventions` |
| strings and plurals | `v1rus-compose:localisation-and-strings` |
| Kotlin style, coroutines/Flow | `v1rus-kotlin:kotlin-conventions`, `v1rus-kotlin:kotlin-coroutines` |
| Gradle, version catalog, convention plugins | `v1rus-kotlin:gradle-conventions` |
| tests | `kmp-testing` |
| Compose performance (lazy layouts, state-read deferral, stability, …) | the `v1rus-compose` performance skill set |

Name the applicable ones in the plan so the implementing agent invokes them; invoke them yourself
before writing non-trivial presentation or performance-sensitive code. If a skill is absent in the
current environment, proceed — never hard-depend on one.

## Presentation pattern

Stateful screens use the project's store view model typed over `State` / `Intent` / `Effect`. Keep
`init {}` minimal; extract orchestration into named functions; in `onIntent`, a branch needing more
than one call becomes a private function. `*Screen` and `*Part*` composables are `internal`; each
state renders through a dedicated `*Part<State>` composable. Theme tokens only — never
`MaterialTheme.*` directly in feature code.

## Design-spec mapping (feature-designer)

Map Figma onto the project's **design-system module**, not raw Material 3: colors → theme color
tokens, type → the project typography API, spacing → existing spacing conventions, components →
existing shared composables first. Discover the available tokens with `ast-index` before proposing a
raw value.

## Tests

- Location: the **`commonTest`** source set of the module that owns the code — typically the data and
  domain modules. Module paths and test-task names come from the project's `CLAUDE.md`.
- Framework: **`kotlin.test`** assertions only (no JUnit 4/5 in a common source set).
- Doubles: **handwritten fakes**, no mocking libraries. Reuse the project's existing fakes package
  before writing a new fake.
- API tests use Ktor **`MockEngine`**; storage tests use the project's in-memory fake.
- Naming: one test class per production class, `<ProductionClass>Test`.
- Out of scope for the pipeline's test phases: Compose UI tests — say so explicitly in the plan.
- Detail: `kmp-testing`.

## Verification

- Compile check after an implementation pass: a compile-only or targeted assemble task — **task names
  from the project's `CLAUDE.md`**, never guessed.
- Full build + test run belongs to the `test-runner` agent of this layer (`v1rus-kmp:test-runner`),
  which discovers the project's own tasks.
- Never read `.gradle/`, `.m2/` or `build/`.

## Implementation escalation targets

Available on this stack, per the pipeline's executor-escalation rule: `compose-developer` (Compose UI
+ the store view model), `kotlin-engineer` (domain/data/logic), `swift-engineer` and
`swiftui-developer` (iOS-native surface), `build-engineer` (Gradle/build scripts). `feature-developer`
remains the floor.

## Finalizer stack checklist

On top of the generic cleanup: Koin bindings registered in the correct module; every new nav key
present in the right `SerializersModule`; module boundaries intact; `modifier: Modifier = Modifier`
defaults and parameter ordering; Material 3 reached only through the design system; one composable per
file with a `@Preview`; no `android.*`/`java.*` import that slipped into `commonMain`.

## Typical expert reviews to flag

`performance-expert` for lazy lists, recomposition-heavy screens or new Flow plumbing;
`ux-expert` for a new screen or navigation change; `security-expert` for auth, token storage or
crypto; `build-engineer` for build-script or version-catalog changes; `architecture-expert` when the
change crosses module boundaries or introduces a new module.
