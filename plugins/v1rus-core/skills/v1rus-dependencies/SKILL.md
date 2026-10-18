---
name: v1rus-dependencies
description: |-
  Dependency gate: never add or bump a dependency or build plugin without owner approval and a plan containing identity, freshness (latest stable), vulnerability scan, and API-surface study.
  Load when a task needs a new library or plugin, a version bump, or build-file edits that add coordinates.
  Do NOT use for: judging whether a library is worth adopting (evaluate-dependency) or resolving version conflicts and BOM alignment (a build-system specialist).
---

# v1rus dependencies

Rulebook (also injected when a build file is first edited): `${CLAUDE_PLUGIN_ROOT}/rules/dependencies.md`

For an adopt/avoid verdict on a candidate library use skill `evaluate-dependency`; for source trust and API verification see skill `v1rus-sources`.
