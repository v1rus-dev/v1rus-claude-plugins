# Profiling playbook

Tools verified to be Node/TypeScript built-ins (check the docs of the project's versions for flags): `node --cpu-prof`, `node --heap-prof`, `node --inspect`, `perf_hooks` (`performance.mark/measure`, `monitorEventLoopDelay`); TypeScript `tsc --extendedDiagnostics` and `--generateTrace <dir>`. Confirm each flag with `node --help` / `tsc --help --all` before use.

- Runtime: reproduce with a fixed input, capture a CPU profile, find the hot path, change, re-measure with warmup. Micro-benchmarks need a harness with warmup (use what the project has).
- Event loop: sync fs/crypto/zlib/`execSync`, large `JSON.parse`, regex backtracking; offload to workers/queues or stream.
- Memory: unbounded maps/caches, listeners never removed, retained closures, uncleared timers; compare heap snapshots.
- I/O: reuse connections, stream large bodies, batch DB calls, bound caches, timeouts via `AbortSignal.timeout`.
- Startup: lazy `import()` of heavy rare modules, no import-time side effects.
- Compile time: use `--generateTrace`, avoid deep conditional types, enable `incremental`/project references; the native compiler has parallelism options (see `tsc --help --all`: `--checkers`, `--singleThreaded`, `--builders`).
