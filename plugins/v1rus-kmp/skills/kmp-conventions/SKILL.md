---
name: kmp-conventions
description: "Kotlin Multiplatform structure conventions for v1rus projects: what belongs in commonMain versus a platform source set, the expect/actual discipline (narrow interfaces for platform capabilities, business logic never duplicated per platform), preferring kotlinx.* over JVM-only libraries, module-graph rules (feature modules must not depend on each other, contracts in core/domain, presentation-only feature modules), convention plugins over re-declared plugin stacks, the iOS framework boundary, the multiplatform-only Compose rules (UI logic in commonMain, the shifting compose-resources API, verifying a dependency publishes KMP artifacts, platform-specific UI), and how to verify version alignment for Compose Multiplatform artifacts. Load when adding a KMP module, writing expect/actual, deciding where code belongs across source sets, writing shared Compose UI in commonMain, or reviewing a KMP module graph."
---

# KMP Conventions

Applies to Kotlin Multiplatform projects targeting Android, iOS and desktop (JVM). The concrete
module names live in the project's own `CLAUDE.md` and `settings.gradle.kts` — **read those first and
never invent a module that is not declared there.** This skill is the shape those modules take.

## Source sets

`commonMain` is the default home for everything. A platform source set exists only for what genuinely
cannot be expressed commonly.

- **No `android.*`, `java.*`, `javax.*`, `dalvik.*` imports in `commonMain`.** This is the single most
  common KMP mistake, and it compiles on the Android target while breaking iOS.
- Prefer `kotlinx.*` over a JVM-only equivalent: `kotlinx.datetime` over `java.time`,
  `kotlinx.serialization` over Gson/Moshi, `kotlinx.coroutines` over JVM concurrency primitives.
- Desktop is usually the `jvm("desktop")` target — check the project rather than assuming the source
  set name.

## `expect` / `actual`

`expect`/`actual` exists for **platform-specific implementation details, never for business logic.**
If the same logic appears in two `actual`s, it belonged in `commonMain`.

- Keep the `expect` surface **narrow**: declare the capability, not the platform type. An interface
  like `ActivityProvider` / `ViewControllerProvider` is right; passing an `Activity` or a
  `UIViewController` through a common API is not.
- Platform factories (`HttpClientFactory`, the Room database builder, secure storage, file paths) are
  the legitimate cases: one `expect` declaration, one `actual` per target.
- A platform-only binding (Android `Context`, iOS view controller, desktop paths) belongs in that
  platform's DI module, not in a common module — see the `v1rus-compose:di-koin-conventions` skill.

## Module graph

- **Feature modules must not depend on each other.** Cross-feature interaction goes through a public
  contract in a shared core/domain module. Importing another feature's internal screen or destination
  is an architecture violation, not a shortcut.
- Feature modules are **presentation only**. Repository interfaces, domain models and use cases live
  in the domain module; implementations, API clients and persistence live in the data module.
- Design-system code (theme, tokens, shared composables, resources) lives in one design-system module
  that features depend on — never the other way round.
- Prefer the project's **convention plugins** (`build-logic/`, `buildSrc/`) over re-declaring the
  KMP/Compose plugin stack in a module build script. See the `v1rus-kotlin` plugin's
  `gradle-conventions` skill.

## Shared utilities — no duplication

Extension and utility functions for **standard-library or KMP types** (`LocalTime`, `LocalDate`,
`String`, `Int`, `List`) live in a **shared module**, never in the feature or component that first
needed them.

- UI-layer helpers (time/date formatting, duration display, string helpers used in Composables) go in
  the shared UI-components module; domain/data helpers go in the corresponding core module.
- **Search before writing one** (`ast-index search`, or grep across the shared modules) — a duplicate
  formatter is the most common instance of this.
- Never add an extension on a type you do not own inside a feature module or a narrow UI module.
- If the target module lacks the dependency on the shared utilities module, **add the dependency** —
  do not copy the function.

## iOS boundary

The Kotlin framework is consumed by the Xcode project under a fixed framework name and entry point —
find both in the project rather than guessing. Anything crossing that boundary must be
Objective-C-representable, so avoid exposing Kotlin-only shapes (sealed hierarchies with generics,
default arguments, `Flow`) directly to Swift; expose a narrow, explicit surface instead.

iOS targets are often gated so the build works on Linux and Windows (a `hasIosTargets()`-style check
or a Gradle property). Do not "fix" a skipped iOS module on a non-macOS machine — it is deliberate.

## Compose Multiplatform UI

Everything target-neutral about Compose lives in `v1rus-compose` and applies here unchanged. These are
the rules that exist only because the UI is shared from `commonMain`.

- **UI logic belongs in `commonMain`.** `expect`/`actual` carries the platform implementation behind it
  — never a second copy of the same screen.
- Resources go through the `org.jetbrains.compose.resources` API, and **that API has changed several
  times across CMP versions.** Read the project's existing resource usage; do not assume a shape.
- **Verify a dependency publishes KMP artifacts** before using it in common UI code — an Android-only
  library compiles on the Android target and breaks iOS.
- Platform-specific UI — iOS touch handling, SwiftUI / UIKit interop, desktop window behaviour — is
  verified against current docs before it is written. These API shapes move.

## Version alignment

Compose Multiplatform tracks Jetpack Compose by `major.minor` for the core artifacts, but **Material3
and the KMP navigation artifact are versioned independently and the KMP fork can lag androidx
upstream**. Verify each artifact's version separately rather than assuming one number covers them
all, and read the general Compose API from docs matching the same `major.minor`. Details and the
per-stack routing are in the `v1rus-sources` skill.
