---
name: android-cli
description: |-
  Command reference for Google's `android` CLI: docs search/fetch, project metadata, emulator/AVD and SDK management, device layout and screenshots, APK deploy, bundled skills, plus the raw adb/sdkmanager fallbacks and known quirks. Use when you need Android docs, to inspect a device or UI tree, start an emulator, install an SDK package, or deploy a built APK.
  Not for: building the app (use the project's Gradle), verifying which API to use (android-api-verification), or iOS and other platforms.
---

# android CLI

Rules for when it is primary and what never to run automatically: `${CLAUDE_PLUGIN_ROOT}/rules/android-tooling.md`. Command matrix, fallbacks and quirks: `reference/commands.md`.

Prefer `android` over raw `adb`/`sdkmanager`/`avdmanager`/`emulator`; drop to raw tools only when a flag is missing. Use `android docs search` for guides and `android layout` (text tree) before screenshots because it is far cheaper.
