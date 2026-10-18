# v1rus-kotlin

The Kotlin / JVM / Gradle layer shared by every v1rus Kotlin project. Depends on `v1rus-core` and
is itself the base for `v1rus-compose`, and through it for `v1rus-kmp` and `v1rus-android`.

```
/plugin install v1rus-kotlin@v1rus     # v1rus-core is installed automatically
```

## What it contains

| Component | Content |
|---|---|
| `rules/kotlin-style.md` | Visibility discipline, collection operators vs `for`, named arguments, empty blocks, value-class validation, parameter nullability, `commonMain` constraints, Clean Architecture + MVI layering. Injected automatically before any `.kt` / `.kts` edit. |
| `rules/coroutines.md` | Scope ownership per layer, dispatcher injection, main-safety, `stateIn` pairing, operator ordering, cancellation propagation, error mapping, coroutine testing. Injected before any `.kt` edit. |
| `rules/gradle-style.md` | `implementation` vs `api`, version catalogs, convention plugins. Injected before any `*.gradle.kts` / `libs.versions.toml` edit. |
| `skills/` | Front doors to the three rulebooks (`kotlin-conventions`, `kotlin-coroutines`, `gradle-conventions`) for read-only and planning contexts that never trigger an edit, plus two standalone skills: `jvm-dependency-intelligence` (`ksrc` and Maven tooling) and `ktor-client-auth` (the access/refresh bearer contract — same on Android, KMP and backend, so it lives here once). |
| `agents/kotlin-engineer.md` | Writes the logic side: business logic, data layer, networking, persistence, domain models, repositories, use cases, mappers, DI wiring, coroutines/Flow and their unit tests. Does not write UI. |
| `agents/build-engineer.md` | Gradle configuration, build performance, module structure, AGP, KMP source sets, version catalogs, convention plugins. |
| `agents/performance-expert.md` | JVM / Android / KMP performance review: N+1, memory, threading, jank, network, battery. |

## Design notes

**One source per rule.** Each rulebook lives once, in `rules/`. The `path-rules` hook injects it
verbatim before a matching edit (deterministic, arrives before the code is written); the matching
skill is a thin front door that points at the same file, for contexts that never edit — a reviewer, a
planner, a question in chat. Do not fork the text into the skill.

**Why the hook is duplicated.** `hooks/path-rules.py` is a copy of the one in `v1rus-core`.
`${CLAUDE_PLUGIN_ROOT}` resolves per plugin, so a layer cannot read a sibling's `rules/` directory;
each layer carrying its own copy is what makes the layers independently installable.

**What deliberately is not here.** Anything Compose — UI, MVI presentation, Koin wiring,
recomposition and stability — belongs to `v1rus-compose`. `commonMain`, `expect`/`actual` and iOS
belong to `v1rus-kmp`; the Android module graph, manifest and `Context` discipline belong to
`v1rus-android`. A rule that holds for every Kotlin project, backend included, belongs here.
