---
name: kmp-testing
description: "How tests are written and run in a v1rus KMP project: tests live in commonTest for the data and domain modules, kotlin.test assertions only (no JUnit 4/5 added directly), handwritten fakes instead of a mocking library (MockK and Mokkery are incompatible with recent Kotlin), Ktor MockEngine for API tests, in-memory fakes for storage, one test class per production class named <ProductionClass>Test, and the suite is executed against the desktop/JVM target. Load when writing, fixing or running tests in a KMP project, or when tempted to add a mocking library."
---

# KMP Testing

**Whether tests are written at all is decided by the task's complexity band, not here** — see the
`v1rus-qa` skill (tests from complexity 7 upward; below that, verification is build + static analysis
+ the quality gate). This skill covers *how* they are written once they are warranted.

## Placement and framework

- Tests live in **`commonTest`** of the module that owns the code — in practice the data and domain
  modules, since presentation logic is thin by design (see `v1rus-compose:mvi-presentation`).
- Apply the project's test convention plugin to any module that needs tests rather than assembling the
  test dependency stack by hand.
- **`kotlin.test` assertions only.** Do not add JUnit 4 or 5 directly — a KMP `commonTest` source set
  that depends on a JVM-only test framework stops being multiplatform.
- **One test class per production class**, named `<ProductionClass>Test`, in the mirrored package.

## No mocking libraries — handwritten fakes

Use handwritten fakes for dependencies. MockK and Mokkery are **incompatible with recent Kotlin
versions**, and beyond compatibility a fake that implements the interface is readable, debuggable and
survives a Kotlin upgrade.

- API tests → Ktor's **`MockEngine`**, returning canned responses per request. This is the fake for
  HTTP; do not fake the repository when the thing under test is the API client.
- Storage / preferences → an in-memory implementation of the project's storage interface, kept in the
  module's `commonTest` fakes package and reused rather than re-invented per test.
- Coroutines → the `TestDispatcher` rules in the `v1rus-kotlin` plugin's `kotlin-coroutines` skill:
  one shared scheduler across all test dispatchers, `Dispatchers.setMain` for anything touching
  `viewModelScope`, Turbine for `Flow` assertions, and never `delay()` or `Thread.sleep()` to wait.

## Running

The suite runs against the **desktop / JVM target** — the iOS and Android targets are not the
verification path for shared logic. The exact Gradle task names belong to the project: read its
`CLAUDE.md` or build config, and use those tasks verbatim rather than guessing a target name.

Scope the run to the change (`check` skill): a logic change runs the affected module's tests, while an
annotation-only or pure-move change needs a compile, not a suite. Long runs are dispatched to the
project's `test-runner` agent so a multi-minute Gradle build does not consume the orchestrating
session's context.

## Non-negotiable

Whoever breaks an existing test fixes it in the same change. `@Ignore` without a tracked-issue link in
the annotation is forbidden, and a red suite is never merged — see the `v1rus-qa` skill § 4.
