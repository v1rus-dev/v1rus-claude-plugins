---
name: go-perf
description: |-
  Profile-first Go performance work: benchmark baseline, pprof/trace analysis, targeted change, before/after comparison.
  Use when: asked to optimize Go code, a benchmark regressed, latency/memory/CPU problems are reported.
  Not for: speculative micro-optimization without a measurement; algorithm or schema design questions with no Go-specific angle.
---

Follow [reference/perf.md](reference/perf.md): baseline first, change second, measure again. A win must be a measurable delta. A performance review agent, when one is available, can judge the findings.
