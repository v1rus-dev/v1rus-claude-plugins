# Go testing recipes

Time and concurrency: `testing/synctest` (1.25+): `synctest.Test(t, func(t *testing.T) {...})` runs the body in a bubble with a fake clock; `synctest.Wait()` waits until every goroutine in the bubble is durably blocked; time advances only then. Mutexes, real network I/O and syscalls are not durable blocks: use in-memory fakes or `net.Pipe`. Goroutines must exit before the bubble ends. Confirm the API with `go doc testing/synctest`.

Integration tests: testcontainers-go needs Docker; use the module's helper for cleanup (`testcontainers.CleanupContainer`), random host ports, wait strategies. Check the exact API with `go doc` on the resolved version. Gate with `//go:build integration` (or the repo's convention). Share one container per package through `TestMain`; isolate tests with a schema, transaction or template database.

Fuzzing: seeds with `f.Add`, one `f.Fuzz` target, committed failing inputs under `testdata/fuzz/FuzzName/`. Plain `go test` runs seeds; `go test -fuzz=FuzzName -fuzztime=30s` explores (use `Nx` for iteration counts).

Benchmarks: `for b.Loop() { ... }`, `b.ReportAllocs()`; run with `go test -run='^$' -bench=. -benchmem -count=10` and compare runs with `benchstat` (if installed; say so if not).

Golden files: `testdata/<name>.golden`, an `-update` flag, compare with `cmp.Diff`.

Flags worth knowing (see `go help testflag`): `-race`, `-shuffle=on`, `-count=1`, `-run`, `-tags`, `-coverprofile` with `-covermode=atomic` under `-race`, `-artifacts` plus `t.ArtifactDir()` (1.26+) for test outputs.

Fakes: hand-written in-memory fakes in an `<pkg>test` package or beside the test; real `httptest.Server`, real database for storage. Generated mocks only for third-party interfaces that are hard to fake.
