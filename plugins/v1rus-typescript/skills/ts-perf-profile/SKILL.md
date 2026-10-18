---
name: ts-perf-profile
description: |-
  Use when there is a measured slowness, memory growth, event-loop delay, slow startup or slow tsc compile time in a JS/TS project.
  Do NOT use for speculative optimisation without a measurement.
---

# Performance investigation

Measure first, report numbers; follow `${CLAUDE_PLUGIN_ROOT}/skills/ts-perf-profile/reference/profiling.md`. Make one change at a time and re-measure. For a deeper review hand the finding to the `performance-expert` agent if it is installed (ships with `v1rus-kotlin`); otherwise do a second inline pass over the profile numbers and the hot path.
