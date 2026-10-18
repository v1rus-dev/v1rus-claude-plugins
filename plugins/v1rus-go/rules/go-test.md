---
paths:
  - "**/*_test.go"
  - "**/testdata/**"
---

# Go tests

Whether tests are written at all follows the user's complexity policy; this file is how to write them well.

- Table-driven tests with named cases and `t.Run`; name struct fields in literals; no branching logic inside the table, split the test instead.
- Failure messages state input and both values: `Foo(%v) = %v, want %v` (got before want). Helpers call `t.Helper()`; fail in the test function where possible.
- `t.Parallel()` for independent tests; not for tests sharing a database or global state without isolation.
- Use `t.Context()`, `t.TempDir()`, `t.Setenv()`, `t.Cleanup()`. Never `t.Fatal` from a goroutine.
- Default to stdlib `testing` + `go-cmp` (`cmp.Diff`); use testify only if the repo already does.
- Fakes and real dependencies (`httptest.NewServer`, a real Postgres) over generated call-expectation mocks. Do not mock SQL.
- No `time.Sleep` for synchronization; use `testing/synctest` (1.25+) or channels.
- Integration tests (testcontainers, Docker) sit behind a build tag such as `//go:build integration`, or the repo's existing convention, so plain `go test ./...` stays fast (advisory).
- Golden files live in `testdata/` with an `-update` flag and are reviewed in the diff.
- Fuzz targets: `FuzzXxx(f *testing.F)`, seeds via `f.Add`, committed corpus in `testdata/fuzz/`; use for parsers and untrusted input.
- Benchmarks use `for b.Loop()` (1.24+) and `b.ReportAllocs()`.
- `t.Skip` and disabled tests need a tracked-issue reference in the message. Whoever breaks a test fixes it in the same change.
- White-box tests use `package foo`; API-surface tests use `package foo_test`.
- Must pass `go test -race`; `-shuffle=on` exposes order dependence.
