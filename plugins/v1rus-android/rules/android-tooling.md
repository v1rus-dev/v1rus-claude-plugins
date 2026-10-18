---
paths:
  - "**/build.gradle*"
  - "**/settings.gradle*"
  - "**/libs.versions.toml"
  - "**/AndroidManifest.xml"
  - "**/local.properties"
---

# Android tooling rules

Applies to a project whose Gradle files reference an Android plugin (application, library, KMP-library) or that has an `AndroidManifest.xml`. Full command matrix: skill `android-cli`.

- The Google `android` CLI is the primary tool for Android docs, project metadata, device/emulator/SDK work. Probe `command -v android` only if a call errors; if missing, use the fallbacks listed in the skill and do not retry for the rest of the session.
- Building is the project's Gradle; `android run` only deploys an already built APK. Do not hardcode AGP/SDK/build-tools facts from memory: look up AGP and Gradle plugin behaviour in the Android docs for the pinned AGP version.
- Never run `android init` or `android skills add` on your own: they register skills in routing and duplicate existing ones. Reading bundled skill files is always fine.
- Never run `android update` automatically: mention a new version once per session and ask first.
- Adding or bumping AGP, Compose compiler/BOM or any androidx artifact goes through the `gradle-dependency-gate` skill.
