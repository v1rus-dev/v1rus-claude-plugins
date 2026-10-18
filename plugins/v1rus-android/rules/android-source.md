---
paths:
  - "**/src/main/kotlin/**/*.kt"
  - "**/src/main/java/**/*.kt"
---

# Android source constraints

This file is in an Android module's production source set — it runs on a device, inside a process the
system can kill and a main thread that must stay free.

- **Never hold an `Activity`, `Fragment` or `View` context in anything that outlives the screen** — a
  singleton, repository, cache or companion object holding one leaks the whole Activity. Use
  `applicationContext` for anything long-lived.
- **A `ViewModel` never touches a `Context`, an `Activity`, a `View` or a composable.** It survives
  configuration changes, so holding any of them leaks them. Domain and presentation state carry no
  `Context` either.

Depth lives in the `android-conventions` and `android-data-layer` skills. Dispatchers and main-safety
are owned by `v1rus-kotlin:kotlin-coroutines`, user-visible strings by
`v1rus-compose:localisation-and-strings` — not repeated here.
