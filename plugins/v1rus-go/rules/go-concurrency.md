---
paths:
  - "**/*.go"
---

# Go concurrency

- Prefer synchronous APIs; let the caller add concurrency.
- Every goroutine has an owner, a stop signal (context) and a way to wait for it (`errgroup`, `sync.WaitGroup`). No fire-and-forget, no goroutines in `init()`. Background workers are a constructor plus `Close`/`Shutdown`.
- Bounded fan-out: `errgroup.WithContext` + `SetLimit(n)` for tasks that return errors; `sync.WaitGroup.Go` (1.25+) otherwise. Unbounded goroutine creation per request/item is a bug.
- Loop variables are per-iteration when the `go` line is 1.22+; remove `i := i` copies only then.
- Mutexes: zero-value, named field, never embedded, never copied (vet `copylocks`). Prefer typed atomics (`atomic.Int64`, `atomic.Pointer[T]`) over the raw functions.
- Channels: sender closes, never the receiver; direction in parameter types; buffer 0 or 1 unless measured. Every blocking send/receive in a long-lived goroutine also selects on `ctx.Done()`.
- Timers and tickers: call `Stop` when done.
- Never call `t.Fatal`/`FailNow` from a goroutine other than the test's.
- New background workers ship with a test that proves they stop; run it with `-race`. Use `testing/synctest` for time-dependent behavior instead of sleeps (needs 1.25+; real network I/O and mutexes are not durable blocks inside a bubble).
- Do not set `GOMAXPROCS` manually or add `automaxprocs` on 1.25+ (cgroup-aware by default).
