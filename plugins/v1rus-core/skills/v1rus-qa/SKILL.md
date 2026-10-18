---
name: v1rus-qa
description: |-
  Testing rules: complexity-to-depth bands (tests only from complexity 7), verification pyramid L0-L2, re-run scope, public-API coverage gate, test priorities P0-P3, source of truth for acceptance.
  Load when deciding whether and how much to test, planning a testing strategy, writing or reviewing tests, or when a test breaks or is about to be skipped.
  Do NOT use for: generating a test-plan document (generate-test-plan), writing retroactive tests (write-tests), or running the suite (test-runner agent).
---

# v1rus QA

The full rulebook (also injected automatically when a test file is first edited): `${CLAUDE_PLUGIN_ROOT}/rules/qa-and-testing.md`

- Task-type routing and baselines: skill `v1rus-workflow`
- Structured test plan: skill `generate-test-plan`; retroactive or regression tests: skill `write-tests`
- Running the build and tests: agent `test-runner`
