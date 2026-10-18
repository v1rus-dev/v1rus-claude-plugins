---
name: android-testing
description: "How tests are written and run in a native-Android v1rus project: src/test is the default home (JVM unit tests, no device), src/androidTest is instrumented and opt-in because it needs a device or emulator, JUnit is the framework and the project's own build files decide which generation, handwritten fakes instead of a mocking library, Ktor MockEngine for API tests, an in-memory Room database for DAO tests, Robolectric only where a JVM test genuinely needs the framework, Compose UI tests through createComposeRule / createAndroidComposeRule, one test class per production class, and variant-aware Gradle task names read from the project. Load when writing, fixing or running tests in an Android app project, when deciding between src/test and src/androidTest, or when tempted to add a mocking library. Not for Compose Multiplatform — that is kmp-testing."
---

# Android Testing

**Whether tests are written at all is decided by the task's complexity band, not here** — see the
`v1rus-qa` skill (tests from complexity 7 upward; below that, verification is build + static analysis
+ the quality gate). This skill covers *how* they are written once they are warranted.

## Where a test lives

| Source set | Runs on | Use for | Cost |
|---|---|---|---|
| `src/test/` | the JVM on the build machine, no device | **the default** — view models, use cases, repositories, mappers, DTO serialisation, anything that is Kotlin logic | seconds; part of every verification run |
| `src/androidTest/` | a connected device or emulator | what genuinely needs the real framework or a real rendered surface — end-to-end flows, DAO behaviour against real SQLite, Compose interaction that Robolectric cannot fake | minutes plus a device; **opt-in, never part of the normal loop** |

Consequences to hold on to:

- A change is verified by `src/test` unless there is a stated reason it cannot be. "It touches Android"
  is not that reason — a class that needs a `Context` to be unit-testable is usually a class that should
  take its dependency as an interface instead (`android-conventions`).
- Nothing in the default verification loop may require a device. An instrumented test that only a
  developer with a plugged-in phone can run is not coverage, it is a manual step wearing a test's clothes.
- Both source sets mirror the production package under the module that owns the code. Tests never live
  in `app` for code that lives in a feature or core module.

## Framework

- **JUnit is the framework here** — unlike a KMP `commonTest`, an Android source set is a JVM source set,
  so a JVM test framework is correct and not a smell.
- **Which JUnit generation is the project's decision, not this skill's.** Read the module's build files
  and the version catalog and use what is already wired; a project that runs on JUnit 4 stays on JUnit 4.
  Never add a second test framework, a runner, or a Gradle plugin to a module to bring in the generation
  you personally prefer — that is a dependency change and goes through the `v1rus-dependencies` gate.
- **One test class per production class**, named `<ProductionClass>Test`, in the mirrored package.

## No mocking libraries — handwritten fakes

Use handwritten fakes for dependencies. This rule carries over from `kmp-testing` unchanged, and it is
not a KMP compromise that native Android is free of:

- MockK and Mokkery break on Kotlin upgrades; a fake that implements the interface survives them.
- A fake is readable and debuggable — a failing fake shows a stack into real code, a failing mock shows
  a verification DSL.
- It is also the platform's own recommendation: Android's testing guidance prefers fakes over stubs and
  mocking frameworks, and `android/nowinandroid` ships test doubles that implement the production
  interface rather than a mocking library.

Fakes by dependency kind:

| Dependency | Double |
|---|---|
| HTTP / API client | Ktor **`MockEngine`**, returning canned responses per request. Fake the engine, not the repository, when the API client is what is under test. |
| Room DAO / database | an **in-memory Room database** built for the test, or a fake implementing the DAO interface when the query itself is not the subject. Room's own guidance supports both a device run and a host-JVM run — which one applies is set by the project's build, not chosen per test. |
| DataStore / preferences | an in-memory implementation of the project's storage interface, kept in the module's test fakes package and reused rather than re-invented per test. |
| Anything with a `Context` | nothing — restructure so the tested class takes the capability it needs, not the `Context`. |

Reuse the project's existing fakes package before writing a new fake.

## Robolectric — a paid tool, not a default

Robolectric runs Android framework code inside a JVM test, so a `src/test` test can touch resources,
`Context` and a simulated lifecycle without a device. Its price:

- Slower than a plain JVM test and slower to configure; it drags a framework simulation into the fast lane.
- It does not render a real screen and does not implement every API — system-UI behaviour, `WebView`,
  edge-to-edge and picture-in-picture are outside it, and pixel fidelity is not guaranteed.

So: reach for Robolectric when a JVM test genuinely needs the framework and restructuring the code to
avoid it would be worse — legacy code, resource loading, a Compose test you want off the device. Do not
reach for it as the default way to test a view model. Enabling it changes the module's build config
(the unit-test Android-resources option plus the dependency), which is a build change, not a test change.

## Compose UI tests

Available on both sides: `createComposeRule()` for a composable with no activity, or
`createAndroidComposeRule<Activity>()` when the test needs a real activity. `ui-test-junit4` is the test
dependency; `createComposeRule()` additionally needs the test manifest artifact on the debug
configuration. `composeTestRule.setContent { }` then finders and assertions on the semantics tree.
Run them instrumented in `src/androidTest`, or in `src/test` under Robolectric when the project has that
wired.

**When a Compose UI test is worth it** — narrowly:

- A screen's state machine is not reachable from a unit test because the logic lives in the composable.
  Usually the right fix is to move that logic into the MVI store (`v1rus-compose:mvi-presentation`) and
  test it on the JVM.
- A component with real interaction semantics — a custom control, a gesture, a selection/focus rule —
  where the assertion *is* the semantics tree.
- A regression that only reproduces through composition.

Not worth it: asserting that a screen shows the text the state told it to show. That test restates the
composable and breaks on every copy edit.

## Coroutines and Flow

Use the `TestDispatcher` and Turbine rules from `v1rus-kotlin:kotlin-coroutines` — one shared scheduler
across test dispatchers, the main dispatcher swapped for anything touching `viewModelScope`, Turbine for
`Flow` assertions, and never a real `delay()` or `Thread.sleep()` to wait. Not restated here.

## Running

Task names are **variant-aware** on Android: unit tests run through a `test<Variant>UnitTest` task
(`testDebugUnitTest`; with product flavors the flavor is part of the variant name), instrumented tests
through `connected<Variant>AndroidTest`, and `check` / `connectedCheck` are the umbrella tasks. Those are
the Android Gradle plugin's shapes — **the project's own documented task names take precedence**: read
its `CLAUDE.md` and build files and use what is written there verbatim rather than assembling a task name
from this paragraph.

Scope the run to the change (`check` skill): a logic change runs the affected module's unit tests, while
an annotation-only or pure-move change needs a compile, not a suite. Long runs are dispatched to
`v1rus-android:test-runner` so a multi-minute Gradle build does not consume the orchestrating session's
context.

## Out of scope

- **Device farms and cloud test grids** — not part of this standard; if a project uses one, its own
  `CLAUDE.md` documents it.
- **Screenshot / snapshot tests** — do not introduce them. If the project already records and verifies
  screenshots, keep its baselines current; if it does not, adding a screenshot harness is a project
  decision, not a side effect of a feature.
- **Macrobenchmark and startup benchmarking** — performance work, covered by the `v1rus-compose`
  performance set, not by this skill.

## Non-negotiable

Whoever breaks an existing test fixes it in the same change. `@Ignore` without a tracked-issue link in
the annotation is forbidden, and a red suite is never merged — see the `v1rus-qa` skill § 4.
