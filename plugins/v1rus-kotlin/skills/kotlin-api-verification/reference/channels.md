# Channels and trust tiers for Kotlin/JVM libraries

| Role | Channel | Use for |
|---|---|---|
| API truth (T1) | `ksrc` (run `ksrc --help`) on the resolved version | real signatures, semantics, overloads, deprecations from the source jar |
| API truth / guides (T2) | official library docs, release notes, changelog; a docs-lookup MCP (for example Context7) if connected | recommended usage, migration, breaking changes |
| Versions, vulnerabilities, changelog between versions | a Maven dependency-intelligence tool (for example maven-mcp: latest version, vulnerabilities, dependency-changes) | freshness and what changed between two versions |
| Project style and pinned versions | version catalog, module build scripts, existing usages | conventions; this is not API truth |
| Fallback | web search on the official site | when all of the above are silent |

Discover what is actually reachable in the session (connected MCP servers, built-in search) and query every relevant channel in parallel; one channel is one perspective. If a whole channel class is unavailable, state it as a limitation.

## Trust tiers

- T1: artifact without interpretation: `ksrc`, existing project code on the same pinned version, official release artifact.
- T2: curated vendor docs, releases, changelogs.
- T3: aggregated or AI-generated docs; never the only source for signatures or versions.
- T4: blogs, Q&A sites, tutorials; cross-check only.

Downgrade a source one tier when it names no version, its signature does not reproduce in `ksrc`, it is undated, or it is older than a year for an evolving library. A source for a different version than the project pins is a flag: cross-check before using it. T1/T2 beat T3/T4 unconditionally; two conflicting T2 sources: prefer the fresher vendor changelog, and surface the conflict instead of choosing silently.

## High-staleness libraries (always use both T1 and T2)

Ktor 3.x, kotlinx.serialization, kotlinx.coroutines, kotlinx.datetime, Room (multiplatform `@Upsert`), SQLDelight, Koin, Hilt, KSP, Kotlin Gradle plugin and Gradle itself.

For JVM/Kotlin guides ("how is it done now") `ksrc` only gives sources: add the official docs or release notes as the second channel.
