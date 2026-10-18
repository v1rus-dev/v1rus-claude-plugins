# v1rus-compose

Compose (Jetpack Compose and Compose Multiplatform) layer. Depends on `v1rus-kotlin`. No charter: rules are path-scoped.

Contents: path rules `compose-ui`, `compose-screen-quality`; skills `compose-screen-checklist`, `compose-api-verification`, `compose-performance`; agent `compose-developer` (sonnet).

Rule paths are directory/name heuristics (`**/ui/**`, `**/presentation/**`, `**/designsystem/**`, `*Screen*`, `*Destination*`, `*Composable*`, `*Component*`, `*Theme*`) because the engine matches paths only, not file content. Compose files elsewhere will not auto-load the rules; the skills cover that.

## Source, destination, why

| Source | Destination | Why |
|---|---|---|
| agent-references/compose-rules.md | rules/compose-ui.md | Compose on any target; project symbols (StoreViewModel, `*IntentUi`, koinViewModel, CollectEffectsUiEvent, AppNavigator) generalized; CMP resources/KMP bullets kept short |
| rules/mobile-ui.md | rules/compose-screen-quality.md | the checklist is true for Compose on any target; nothing Android-only in it; `R.string` wording made resource-neutral |
| rules/mobile-ui.md | skills/compose-screen-checklist | review procedure as an on-demand door over the two rules |
| rules/external-sources.md (fast-moving UI section) | skills/compose-api-verification (+ reference/roles.md) | roles A/B/C, CMP vs Jetpack version-alignment caveats; SwiftUI parts left out |
| agents/performance-expert.md (UI section) | skills/compose-performance | Compose perf lives on this layer; performance-expert (kotlin) points to it |
| agents/compose-developer.md | agents/compose-developer.md | project-specific module names, Koin, shared/designsystem, `$HOME` paths, language/return boilerplate removed; discovery step kept |

Lossy: the original agent's illustrative skeleton code and the Destination code sample were dropped; the rules keep the prose. SwiftUI content untouched (out of scope).

## Install

```
/plugin marketplace add <path-or-git-url>
/plugin install v1rus-compose@v1rus-dev
```

Dependencies (v1rus-kotlin) are resolved automatically from the same marketplace.
