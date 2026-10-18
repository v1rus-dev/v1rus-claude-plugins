# Greenfield Go skeleton

Layout (official module layout guide): start flat, add structure only when forced.
- Library: package(s) at module root. Single command: `main.go` at root.
- Several binaries or a service: `cmd/<binary>/main.go`, private code under `internal/`, non-Go assets in their own directories (`migrations/`, `api/`, `deploy/`). No `pkg/` directory; `internal/` gives compiler-enforced privacy. Reusable code for other projects becomes a separate module.
- Package by domain (`internal/orders`), not by layer (`models/`, `controllers/`). Domain types in a leaf package; wiring in `cmd/` or one composition root.

main:
- `func main()` only builds the root context and calls `run(ctx, args, env) error`; on error prints to stderr and exits non-zero. Root context from `signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)`.
- `run` parses config, builds dependencies, starts servers/workers in an `errgroup`, waits, shuts down in reverse order.

Config:
- One typed struct parsed once from environment (and optional file), validated at startup, fail fast with an actionable message. Stdlib `flag` + `os.LookupEnv` + `time.ParseDuration` first; a config library only if layering is really needed (dependency gate).
- Durations as `time.Duration` (`5s`), secrets only from env/secret manager, config type implements `slog.LogValuer` that redacts.
- Do not add feature flags unasked.

HTTP service essentials: see the `go-http-endpoint` skill reference (explicit `http.Server` with timeouts, graceful `Shutdown`, `/healthz` and `/readyz`, admin listener for pprof).

CLI: stdlib `flag` with subcommands, or cobra if the repo already uses it (use `cmd.Context()`). Exit codes: 0 success, 1 error, 2 usage (convention).

Tooling: Makefile or Taskfile with `build test lint vuln fmt tidy generate` targets; `go.mod` with an explicit `go` line; `.gitignore` for binaries.
