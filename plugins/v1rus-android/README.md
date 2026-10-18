# v1rus-android

Native Android layer. Depends on `v1rus-compose`. No charter. No agents (none of the in-scope agents are Android-only).

Contents: path rules `android-platform`, `android-tooling`; skills `android-api-verification`, `android-cli`, `android-performance`.

## Source, destination, why

| Source | Destination | Why |
|---|---|---|
| rules/coroutines.md (lifecycle pairing, setMain), rules/kotlin-style.md (viewModelScope), performance-expert (Context leaks) | rules/android-platform.md | Android-only; resource-string/leak bullets are standard Android practice written fresh |
| rules/android-cli.md (applicability, hard rules) | rules/android-tooling.md | short always-while-editing-gradle/manifest rules; paths limited to gradle/manifest/local.properties (the original also matched every `.kt`) |
| rules/android-cli.md (matrix, fallback, quirks) | skills/android-cli (+ reference/commands.md) | command reference is on-demand material; version-specific stamp dropped |
| rules/android-cli.md (routing), rules/external-sources.md (Android composition) | skills/android-api-verification | ksrc + `android docs` in parallel, bundled skills channel |
| agents/performance-expert.md (battery, leaks, bitmaps, Room, profiling tools) | skills/android-performance | Android-only content |

Lossy / unverified: `android` CLI behaviour was copied from the owner's notes, not re-run. The Russian-language text in the original android-cli rule was rewritten in English. The owner-specific global-skill preference (`agp-9-upgrade` vs bundled skill) was generalized to "prefer a dedicated routable skill if present".

## Install

```
/plugin marketplace add v1rus-dev/v1rus-claude-plugins
/plugin install v1rus-android@v1rus-dev
```

Dependencies (v1rus-compose) are resolved automatically from the same marketplace.
