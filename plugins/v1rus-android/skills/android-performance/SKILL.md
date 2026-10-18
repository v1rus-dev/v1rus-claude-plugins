---
name: android-performance
description: |-
  Android-specific performance review: battery and background work (WorkManager constraints, wake locks, polling, location/sensor use), memory leaks through Activity/Context, bitmap and image pressure, Room and main-thread I/O, startup, and profiling tools (Android Studio profiler, Perfetto, LeakCanary, Layout Inspector). Use when reviewing an Android app or module for performance, battery drain, ANR, OOM or leak risk, or when performance-expert needs Android coverage.
  Not for: JVM data/threading performance (performance-expert), Compose recomposition (compose-performance), or code that has not been measured and shows no concrete risk.
---

# Android performance

Main-thread I/O or heavy work is always critical. Measure before optimizing; name the tool that would settle an unconfirmed suspicion.

Check:
1. Battery and background: background work without WorkManager constraints (network, charging, idle); polling where push or reactive streams would do; unnecessary wake locks; location updates at excessive frequency; sensor listeners not unregistered.
2. Memory: Activity/Fragment/Context retained via lambdas, inner classes, singletons; flows collected beyond the lifecycle (see `${CLAUDE_PLUGIN_ROOT}/rules/android-platform.md`); large bitmaps without sizing or recycling; caches referencing framework objects.
3. Storage: Room queries on the main thread, missing `@Transaction` for multi-step writes, choice of LiveData vs Flow consistent with the project.
4. Images: loader library caches configured, requests sized to the target view, placeholders sized.
5. Startup and jank: work done in `Application.onCreate` or first frame that could be deferred.

Tools: Android Studio Profiler, Perfetto system tracing, LeakCanary, Layout Inspector, macrobenchmarks, compiler metrics for Compose. Report each finding as severity, location, problem, concrete fix.
