# v1rus-kmp

The Kotlin Multiplatform layer. Depends on `v1rus-compose` → `v1rus-kotlin` → `v1rus-core` —
installing this one pulls in all three.

```
/plugin install v1rus-kmp@v1rus
```

Everything Compose — UI conventions, MVI, navigation, Koin, localisation, the performance and
stability set, the `compose-developer` agent — lives in `v1rus-compose` and applies here unchanged.
This layer carries only what is genuinely multiplatform.

## What it contains

### Conventions

| Skill | Covers |
|---|---|
| `kmp-conventions` | Source sets, `commonMain` constraints, `expect`/`actual` discipline, module graph, shared utilities, the iOS framework boundary, the multiplatform-only Compose rules, CMP version alignment |
| `kmp-data-layer` | API/DTO organisation, the Room builder and Ktor `HttpClient` as `expect`/`actual` per platform, repository/domain split, no leaking DTOs, HTTP auth and session expiry |
| `kmp-testing` | `commonTest`, `kotlin.test`, handwritten fakes (no MockK/Mokkery), `MockEngine`, desktop-target runs |
| `kmp-mvp-blueprint` | The `/mvp-init` blueprint for this stack: how a new KMP project is brought into existence, the MVP-sized module graph, the baseline dependency set by role, the app skeleton and its first vertical slice, and the facts the generated project `CLAUDE.md` must record. Sibling of the pipeline profile — the profile is for working in a project, the blueprint is for creating one. |
| `kmp-pipeline-profile` | The stack vocabulary the feature pipeline uses on a KMP project: layer names, plan sections, which convention skill owns which area, where tests live, how to verify |

### Path-scoped rules

`rules/commonmain.md` fires on any `commonMain` / `commonTest` edit. Delivered by
`hooks/path-rules.py`.

### Agents

| Agent | Role |
|---|---|
| `swift-engineer` | Swift logic for the iOS side: services, models, platform code, Swift concurrency, unit tests. Not SwiftUI. |
| `swiftui-developer` | SwiftUI views, navigation, animation, accessibility. |
| `test-runner` | Discovers the project's build/test tasks, runs them against the desktop/JVM target, reports PASS/FAIL. Never edits code. |

Compose UI on a KMP project is written by `v1rus-compose:compose-developer`; the logic side by
`v1rus-kotlin:kotlin-engineer`.

`references/` holds the deep material the Swift agents read: `swift-concurrency.md`,
`swift-testing.md`, `swiftui-state.md`, `swiftui-patterns.md`, `swiftui-performance.md`,
`swiftui-design-system.md`, addressed as `${CLAUDE_PLUGIN_ROOT}/references/…`.

## What deliberately stays in the project

A project's **concrete** architecture — exact module paths, the real names of its navigator, store,
theme and result store, its Gradle task names, its DTO subpackage list — stays in that project's own
`.claude/rules/` and `CLAUDE.md`. The plugin carries the pattern and the rule; the project carries the
names. That is why every skill here says to read the project's `CLAUDE.md` first.
