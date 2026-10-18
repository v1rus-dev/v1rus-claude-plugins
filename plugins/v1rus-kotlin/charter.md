# Kotlin layer baseline

- Verify every external library API against the version the project actually pins before writing code that uses it. Memory and existing project code are pointers, not sources. Procedure: skill `kotlin-api-verification`.
- Never add or bump a dependency or Gradle plugin on your own initiative. Adding/bumping is a plan-stage decision: skill `gradle-dependency-gate`.
- Never read `.gradle/`, `.m2/` or `build/` directories by hand; read dependency sources with `ksrc`.
- Style, coroutines, layering and Gradle conventions load automatically as path-scoped rules when a `.kt`, `.kts`, `build.gradle*` or `libs.versions.toml` file is edited. Deeper coroutine review: skill `kotlin-coroutines`.
- Verify by compiling only the affected module (targeted assemble/compile task); leave full suite runs to the test-runner agent.
- Agents on this layer: `kotlin-engineer` (logic layer code), `build-engineer` (Gradle/AGP/KMP build), `performance-expert` (review).
