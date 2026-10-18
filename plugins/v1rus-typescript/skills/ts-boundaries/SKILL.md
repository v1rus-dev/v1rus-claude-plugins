---
name: ts-boundaries
description: |-
  Use when handling external input (HTTP, env, files, JSON, DB rows, queues, CLI args), choosing or using a schema validation library, or designing error handling (Error cause, typed errors, Result versus throw).
  Do NOT use for pure internal logic with already-trusted types, or for async/cancellation design (ts-async-node).
---

# Boundaries and errors

Apply `${CLAUDE_PLUGIN_ROOT}/rules/ts-boundaries.md` (validation and errors sections).
- Use the schema library already in the project. If none exists, a new one is a dependency decision: study it per `ts-supply-chain` before adding (plan-stage gate). Candidates to evaluate by name only: Zod, Valibot, ArkType; libraries should accept Standard Schema.
- Parse once at the edge, infer the type from the schema, map failures to typed errors.
- Decide throw versus result-union per module boundary and document it.
