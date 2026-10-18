# Roles for Compose verification

## A. API truth: what exists in the project's version
`ksrc` on the resolved Compose artifacts (T1, real source jar; covers Jetpack Compose and Compose Multiplatform core and Material3), then official docs of the same version or a docs-lookup MCP (T2). For Android, the Android docs tooling is a further T2 channel (skill `android-api-verification`, when v1rus-android is installed).

## B. Recommended approach: how it is done now
Official reference apps are worth more than prose docs (code over docs): the Android team's Now in Android and Compose samples, and the JetBrains Compose Multiplatform examples. Then What's New / release notes / roadmap of the toolkit, then the design canon (Compose API Guidelines, Material 3). Community posts are T3/T4: cross-check only, never the sole source.

## C. What changed and known issues
A dependency-intelligence changelog between two versions (for example maven-mcp dependency-changes) is the richest signal for Compose Multiplatform. Issue trackers by correct address: Jetpack Compose bugs live in Google's IssueTracker (not GitHub); Compose Multiplatform bugs in the JetBrains compose-multiplatform GitHub repository.

## Version alignment (Compose Multiplatform)
Core Compose is aligned with Jetpack Compose by major.minor (patch numbers differ and CMP releases later in calendar time). Material3 and the multiplatform navigation artifact have their own numbering and the multiplatform fork can lag the androidx upstream, so verify each artifact's version separately (dependency tool plus the CMP release tables). For general Compose API the Jetpack docs and `ksrc` of the same major.minor are valid; use JetBrains docs for CMP-specific behaviour (resources, `expect`/`actual`, desktop/iOS interop).

## High-staleness
Compose Multiplatform, Material3, navigation (Navigation 3 / navigation-compose), lifecycle-aware state collection, adaptive layouts, Compose compiler/stability settings: always use both A and B.
