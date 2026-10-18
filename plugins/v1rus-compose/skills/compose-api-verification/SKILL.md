---
name: compose-api-verification
description: |-
  Verifying Jetpack Compose and Compose Multiplatform APIs and the currently recommended approach before implementing a non-trivial screen or component: API truth from the resolved sources, reference apps and release notes, changelog and issue trackers, and the version-alignment caveats of Compose Multiplatform artifacts.
  Use before writing or migrating Compose code that uses Material3, navigation, adaptive layouts, Modifier.Node, animation or any API you are not certain exists in the pinned version; when a Compose API looks deprecated; when a CMP and Jetpack version question comes up.
  Not for: plain Kotlin or non-UI libraries (kotlin-api-verification), or trivial use of an API already used elsewhere in the project on the same version.
---

# Compose API verification

Compose changes every release cycle with little back-compat, so "which API exists" is not enough: also check how it is recommended now. Run the relevant roles in parallel (see `kotlin-api-verification` for channel discovery and trust tiers); read `reference/roles.md`.

1. Resolve the pinned versions of each Compose artifact from the version catalog.
2. Run role A (API truth) and role B (recommended approach); add role C when upgrading or when behaviour is surprising.
3. Never use a memorized Compose signature. State in your reasoning which roles you used and which channels were unavailable.
4. If the `v1rus-android` plugin is present, also load `android-api-verification` for the Android docs channel.
