---
name: go-write-tests
description: |-
  Write or change Go tests: table-driven tests, fakes, httptest, synctest, golden files, fuzz targets, benchmarks, integration tests with testcontainers.
  Use when: creating or editing *_test.go, adding fuzz/benchmark/integration tests, fixing flaky Go tests, writing a regression test for a bug fix.
  Not for: deciding whether tests are required (the complexity policy decides); test plan documents (use generate-test-plan); running tests (use go-verify or the go-test-runner agent).
---

Read `${CLAUDE_PLUGIN_ROOT}/rules/go-test.md` and [reference/testing.md](reference/testing.md). Match the repo's assertion library and integration-test gating. For a bug fix, write the failing test first, then the fix.
