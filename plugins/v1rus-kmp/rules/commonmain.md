---
paths:
  - "**/commonMain/**/*.kt"
  - "**/commonTest/**/*.kt"
---

# commonMain constraints

This file is in a **common** source set — it compiles for every target, including iOS and desktop.

- **No `android.*`, `java.*`, `javax.*` or `dalvik.*` imports.** They compile on the Android target and
  break every other one. This is the most common KMP mistake.
- Only the Kotlin stdlib and KMP-compatible libraries. Prefer `kotlinx.*` over a JVM-only equivalent:
  `kotlinx.datetime` over `java.time`, `kotlinx.serialization` over Gson/Moshi.
- `expect` / `actual` is for **platform-specific implementation details only** — business logic belongs
  in `commonMain`. If the same logic appears in two `actual`s, it belonged here.
- Keep an `expect` surface **narrow**: declare the capability (a provider interface), never a platform
  type. An `Activity` or a `UIViewController` must not cross a common API.
- In `commonTest`: `kotlin.test` assertions only, handwritten fakes rather than a mocking library. See
  the `kmp-testing` skill.
