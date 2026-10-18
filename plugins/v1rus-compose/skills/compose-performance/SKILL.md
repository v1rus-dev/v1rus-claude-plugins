---
name: compose-performance
description: |-
  Compose UI performance review: unnecessary recompositions, unstable parameters and stability config, reading state too broadly, heavy work in composition, lazy-list keys and contentType, overdraw and deep layouts, image sizing, derivedStateOf. Use when a screen janks or scrolls badly, when reviewing a list-heavy or animated composable, or when the performance-expert agent needs Compose coverage.
  Not for: general data/threading performance (performance-expert), Android battery/background/memory (android-performance when v1rus-android is installed), or micro-optimising code that has not been measured.
---

# Compose performance

Measure before optimizing; impact on what users feel over purity. Read `${CLAUDE_PLUGIN_ROOT}/rules/compose-ui.md` sections Stability and Phase deferral first.

Check, by typical impact:
1. State read too high or too broadly: defer reads with lambda modifiers (`offset {}`, `drawBehind {}`, `graphicsLayer {}`) and `() -> T` parameters.
2. Heavy computation or allocation inside composition: move to `remember(keys)`, `derivedStateOf`, or the ViewModel.
3. Lazy lists without stable `key`/`contentType`; per-item heavy work inside the item lambda; nested scrolling of unbounded content.
4. Unstable parameters causing non-skippable composables: depends on strong skipping and the project's stability config; confirm with compiler metrics before adding annotations.
5. Large images without size constraints, deep layout nesting, overdraw.

Confirmation tools: Compose compiler metrics/reports, Layout Inspector recomposition counts, system tracing (Perfetto) and macrobenchmarks. When a suspicion cannot be confirmed from code, say so and name the measurement.
