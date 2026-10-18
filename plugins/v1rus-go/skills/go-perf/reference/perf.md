# Go performance workflow

1. Baseline: write or find a benchmark (`for b.Loop()`, `b.ReportAllocs()`); `go test -run='^$' -bench=<name> -benchmem -count=10 > before.txt`. Use `benchstat` to compare if installed; otherwise compare medians manually and say so.
2. Profile: `go test -cpuprofile cpu.out -memprofile mem.out -bench=<name>`; analyze with `go tool pprof -http=:0 cpu.out`. In services use `net/http/pprof` on an admin-only listener. Contention: block and mutex profiles; scheduling and latency: `go tool trace`; stuck goroutines: the goroutine profiles.
3. Look at the biggest cost first; prefer algorithmic, I/O, batching and database fixes (indexes, N+1, `CopyFrom`) over micro-optimizations.
4. Typical Go levers once measured: preallocate slices/maps when size is known, `strings.Builder`, `strconv` over `fmt` in hot paths, avoid interface boxing in hot loops, `sync.Pool` only with a measured win, fewer allocations visible in `-benchmem`. Escape analysis: `go build -gcflags='-m'` (flag semantics not re-verified).
5. Change one thing; re-run the benchmark with the same `-count`; report the delta and any trade-off (readability, memory).
6. Do not tune runtime knobs blindly: `GOMAXPROCS` is cgroup-aware on 1.25+; `GOMEMLIMIT` is a container memory decision to confirm with the user.
