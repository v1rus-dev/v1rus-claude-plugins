# Concurrency checklist

For every goroutine in the change answer: who starts it, what stops it, who waits for it, what happens to its error, what happens on panic.

- Ownership: owner type has `Close`/`Shutdown`; callers cannot leak the goroutine by forgetting a cancel.
- Cancellation: derived from the caller's context; blocking operations select on `ctx.Done()`; `defer cancel()` present.
- Bounds: fan-out limited (`errgroup.SetLimit`, worker count, semaphore); channel buffers justified.
- Shared state: guarded by one mutex or atomic; no lock held across I/O or channel operations; no copy of a struct containing a lock; lock ordering consistent.
- Channels: closed by the sender only; no send on closed channel path; no goroutine blocked forever on a channel nobody reads.
- Timers: stopped; no `time.After` in hot loops.
- Shutdown order: stop accepting work, drain, then close dependencies (pools, files).
- Tests: `-race` clean; deterministic (no sleeps; `testing/synctest` for time); worker stop proven; goroutine-leak evidence for services (the `goroutineleak` pprof profile exists on the newest toolchains: check with `go doc runtime/pprof`).
- Race detector only sees executed paths: ask for a test that exercises the concurrent path.
