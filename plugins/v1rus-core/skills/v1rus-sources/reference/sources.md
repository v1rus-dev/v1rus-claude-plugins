# Sources: routing, verification, trust tiers

## Source routing

| Source | Use for | Not for |
|---|---|---|
| Local code and project files | First stop for project questions | |
| Dependency source reader (JVM: source jars; other stacks: installed package source or vendored code) | Real source of the pinned version | Project-internal code |
| Vendor documentation tools (for example Android developer docs tooling) | API truth and guides for that platform | Unrelated libraries |
| Library-docs MCP (Context7-style) | Published library/framework docs, current API and migration | Project code, debugging your own code; one failed library-id resolution means stop, do not chase synonyms |
| Web search/fetch | Everything else | |
| Raw README of a specific repo | Last resort | |

Never fetch rendered GitHub pages (noisy and expensive); use the raw file URL.

## Tool discovery and multi-channel use

The table names classes of source, not a guaranteed toolset. Reachable tools vary per environment (extra MCP servers, docs proxies, platform servers). Never assume a named tool exists and never stop at the first one. Gathering is a three-step discipline:

1. **Discover**: inventory what is actually reachable now (connected MCP servers and deferred tools via `ToolSearch`, plus built-in search/fetch). A subagent can discover and invoke the session's MCP servers itself.
2. **Use all relevant channels in parallel** for the question's class: one channel is one perspective.
3. **Cross-check and tier**: verify a claim across at least two channels where possible, rank by trust tier, and surface disagreements and version mismatches instead of silently picking one.

If a whole channel class is unavailable, state it as an explicit limitation: reduced confidence must be visible.

## Verify library API before code

Mandatory before writing or editing code that uses an external library. Training data goes stale; existing project code shows only the slice of API in use and may be legacy or an anti-pattern. Memorized signatures are never a source.

Three roles of channels complement each other and often run in parallel:
- **API truth** (signatures, semantics, types, alternatives): always when writing code with a library.
- **Guides** (recommended patterns, migration, troubleshooting): for "how to do X", migrations, unfamiliar stacks, non-trivial integration.
- **Project style and versions** (conventions, pinned versions, connected modules): always, as a separate pass over the project; this is not API truth.

Per stack: JVM/Kotlin/Gradle: dependency source reader as API truth plus web docs as guides. Other ecosystems: library-docs MCP, then web search; use the ecosystem's analogue of a source reader if one exists. For fast-moving stacks (declarative UI frameworks, networking/serialization/DI libraries, build plugins) read both API truth and the recommended-approach channel (official sample apps, release notes, changelog between versions, the project's issue tracker at its real address) before implementing a non-trivial screen or component.

**High-staleness warning:** treat any library that changed major shape recently as needing both channels, never one.

## Trust assessment

A formally primary source can still be outdated, for another version, or hallucinated. Assess the tier before believing it.

| Tier | What | Examples |
|---|---|---|
| T1 ground truth | an artifact without interpretation | dependency source at the pinned version, existing project code (for form only), official release artifact |
| T2 official docs | curated vendor docs, releases, changelogs | vendor docs tooling, library-docs MCP for official libraries |
| T3 aggregated/AI | may hallucinate | library-docs MCP for community libraries without vendor docs |
| T4 random web | blogs, Q&A sites, tutorials | web search, arbitrary fetch |

Memory is not a tier. Auto-memory and recalled facts record what was true when written: use them as pointers to where to look, never as facts about APIs, versions or behavior.

Default: T1 and T2 in parallel for any edit with an external library. T1 alone is acceptable only with explicit justification: stable language stdlib; a symbol already seen on the same pinned version; a local helper/data class without behavior; trivial usage (enum value, constant). "Seems obvious" is not justification.

Validate before use:
- Source version equals the project's version? No: flag it, do not use without cross-check (T1 is pinned, T2 is current; a gap means the project lags or the docs cover another major).
- T3/T4 older than a year in an evolving stack: suspicious, lower the weight.
- T3 is never the sole source for signatures or versions; pair it with T1 or T2.
- Red flags (drop one tier): no version stated; signature does not reproduce in the source; text reads as generated (generic phrasing, vague types); undated tutorial.

Conflicts: T1 vs T2: follow T1 (what the project can actually use), note the gap, propose a bump through the dependency gate if it is large. T1/T2 vs T3/T4: T1/T2 win. T2 vs T2: a fresh vendor changelog beats an old docs page; unclear means raise it, do not pick silently.
