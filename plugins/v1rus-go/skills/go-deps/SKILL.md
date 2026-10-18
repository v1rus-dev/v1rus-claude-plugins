---
name: go-deps
description: |-
  Gate for adding, upgrading, removing or replacing Go dependencies and tools: go.mod require/tool/replace edits, vendoring, toolchain pins.
  Use when: a task needs a new module, a version bump, a go.mod change, a replace directive, or a dev tool.
  Not for: stdlib-only changes; JVM/Maven dependencies (use the core dependency rules).
---

Never add or bump a dependency without user approval. Produce the plan-stage block from [reference/dependency-gate.md](reference/dependency-gate.md) first (identity, freshness, vulnerabilities, API study). Never choose a version from memory. The implementer only writes the approved version and reports back if resolution differs.
