---
name: kotlin-api-verification
description: |-
  How to verify a JVM/Kotlin/Gradle library's real API and version before writing or editing code that uses it: ksrc for the resolved source jar, official docs for the recommended form, dependency-intelligence tools for versions and changelogs, trust tiers, and the fast-moving libraries that need both channels.
  Use before any Edit/Write that calls an external Kotlin/Java library, when a signature is uncertain, when a compile error mentions a missing or changed API, or when the question is "how is X usually done" for a library.
  Not for: project-internal code (read it), Android/Jetpack specifics (also load android-api-verification when that plugin is present), Compose specifics (compose-api-verification when v1rus-compose is installed), or deciding whether to adopt a new dependency (gradle-dependency-gate).
---

# Kotlin API verification

Memorized signatures are never a source. Existing project code only shows the slice of an API already in use and may be legacy.

1. Read `reference/channels.md` for the channel table, the parallel T1+T2 default and trust tiers.
2. Resolve the pinned version first: version catalog (`libs.versions.toml`), then the module's `build.gradle*`.
3. T1 (`ksrc` on that exact version) and T2 (official docs of the same version or changelog) run in parallel. T1-only is acceptable only for the stable standard library, a symbol already seen on the same pinned version, or a trivial use (data class constructor, enum value, constant); say why in your reasoning.
4. If T1 and T2 disagree, follow T1 (it is what compiles) and report the gap; a large gap is a bump proposal for `gradle-dependency-gate`.
