---
name: android-api-verification
description: |-
  Verifying Android, Jetpack, Compose-on-Android, AGP and SDK APIs and recommended practice: Android docs search/fetch in parallel with ksrc, bundled Android CLI skills for migrations and narrow areas, and fallbacks. Use before writing or migrating code that uses Android framework or androidx APIs, when upgrading AGP or Android libraries, or for "how is X done on Android now" and migration questions (edge-to-edge, Navigation 3, AGP major upgrade, XML to Compose).
  Not for: non-Android libraries (`v1rus-sources`), Compose-only API questions with no Android angle (`v1rus-sources`, fast-moving declarative UI section), or CLI command syntax (android-cli).
---

# Android API verification

Always run API truth and guides in parallel, not either/or:

1. API truth: `ksrc` on the resolved androidx artifact (the jar) AND `android docs search "<query>"` then `android docs fetch <url>` (the currently recommended form). A disagreement means legacy code or an outdated pinned version: report it.
2. Guides and migrations: `android docs` plus the bundled skills on disk. `android skills find <keyword>`, then Read the matching `SKILL.md` under `~/.android/cli/skills/` (no install needed). Use them for migrations, upgrades and narrow areas (Wear, XR, camera, Navigation 3, edge-to-edge, adaptive layouts, R8, Perfetto, XML to Compose, AGP major upgrades). Downgrade a bundled skill whose last-updated date is over a year old in an evolving area. Prefer a dedicated routable skill from another plugin when one covers the same migration.
3. If `android` is missing: web search on developer.android.com, then fetch the page.
4. Also apply the `v1rus-sources` skill (trust tiers, pinned versions, and for Compose UI the guides-and-changelog pass).

High-staleness here: AGP 8+/9 and above, KSP, Firebase Android BoM changes, Navigation 3, Room, Hilt, Compose Material3.
