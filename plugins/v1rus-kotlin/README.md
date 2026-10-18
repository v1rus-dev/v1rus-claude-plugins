# v1rus-kotlin

Kotlin (JVM, multiplatform source sets) layer. Depends on `v1rus-core`. Compose and Android live in `v1rus-compose` / `v1rus-android`.

Contents: charter (always on, ~10 lines); path rules `kotlin-style`, `kotlin-coroutines`, `gradle-build`; skills `kotlin-api-verification`, `gradle-dependency-gate`, `kotlin-coroutines`; agents `kotlin-engineer` (sonnet), `build-engineer` (sonnet), `performance-expert` (inherits).

## Source, destination, why

| Source | Destination | Why |
|---|---|---|
| rules/kotlin-style.md | rules/kotlin-style.md | Kotlin-true everywhere; project names removed; Clean/MVI layering merged in; KMP `commonMain` bullets kept (Kotlin-level, not iOS-specific); `viewModelScope` bullet kept as a layering statement, Android detail in v1rus-android |
| rules/coroutines.md | rules/kotlin-coroutines.md | generic part; Hilt `@IoDispatcher`, `collectAsStateWithLifecycle`, `repeatOnLifecycle` moved out (Android/Compose) |
| rules/coroutines.md (lifecycle, setMain, viewModelScope) | v1rus-android rules/android-platform.md | Android-only |
| rules/gradle-style.md | rules/gradle-build.md | Gradle is not Android-only; added buildSrc/build-logic paths and convention-plugin bullets from build-engineer |
| rules/external-sources.md (JVM parts), CLAUDE.md API-truth | skills/kotlin-api-verification | ksrc, trust tiers, staleness list; core is stack-agnostic |
| rules/dependencies.md (Gradle/JVM gate) | skills/gradle-dependency-gate | procedure, on demand; tool names generic (maven-mcp as example) |
| agents/kotlin-engineer.md | agents/kotlin-engineer.md | Koin/`shared/*`/StoreViewModel/ast-index/Russian-language/`$HOME` paths removed; UI boundary phrased for optional compose plugin |
| agents/build-engineer.md | agents/build-engineer.md | block-scalar description, same expertise, rules paths via `${CLAUDE_PLUGIN_ROOT}` |
| agents/performance-expert.md | agents/performance-expert.md | JVM domains kept; Compose UI and Android battery/leak sections moved to skills in the upper layers; inherits model (review agent) |

Lossy: the original agents' return-contract/language lines and `memory: project`, `maxTurns`, TaskCreate tools were dropped (user-specific or core concern). The KMP/Android-specific agent-body examples were not preserved.

## Install

```
/plugin marketplace add <path-or-git-url>
/plugin install v1rus-kotlin@v1rus-dev
```

Dependencies (v1rus-core) are resolved automatically from the same marketplace.
