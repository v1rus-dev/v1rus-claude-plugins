---
name: v1rus-workflow
description: |-
  The development workflow: preparation, quality, acceptance and PR-promotion gates, plus per-task-type routing (feature, bug fix, migration, refactor, perf) and before-state baselines.
  Load when planning or starting a non-trivial task, deciding what must be true before declaring done, choosing how to verify a bug fix or migration, or when asked about the gates, baseline, or flow.
  Do NOT use for: tool-specific how-tos (see finalize, check, write-spec, write-plan) or trivial one-line edits.
---

# v1rus workflow

Read the section you need; do not load both unless planning a new task.

- Gates (preparation, quality, acceptance, PR promotion) and the feature/bug-fix flows: `${CLAUDE_PLUGIN_ROOT}/skills/v1rus-workflow/reference/workflow.md`
- Routing by task type, test feasibility, before-state baseline: `${CLAUDE_PLUGIN_ROOT}/skills/v1rus-workflow/reference/task-types.md`
- Testing depth by complexity band: skill `v1rus-qa`
- Executing the gates: skills `finalize`, `check`, `write-tests`; agent `test-runner`
