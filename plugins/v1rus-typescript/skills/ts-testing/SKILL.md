---
name: ts-testing
description: |-
  Use when choosing a test runner, writing or refactoring TypeScript/JavaScript tests, deciding what to mock, adding type tests, setting coverage, or laying out test files.
  Do NOT use to run the suite (use the ts-test-runner agent) or for UI/E2E framework specifics. Respect the global complexity bands: no tests are written below band 7 unless asked.
---

# Testing

Apply `${CLAUDE_PLUGIN_ROOT}/rules/ts-test.md`.
- Use the project's runner and its script (`package.json#scripts`). Never install a runner without the plan-stage dependency gate.
- Write a failing test first for bug fixes; for retroactive tests cover the public contract.
- Verify by running the scoped test command through the `ts-test-runner` agent.
