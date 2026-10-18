# Go engineering playbook (for plugin `v1rus-go`)

Date of research: 2026-10-18. Scope: backend services, CLIs, libraries.
Source tiers: T1 = official Go docs/spec/blog/release notes/source/`go doc`/real toolchain run; T2 = Google & Uber style guides, golangci-lint / sqlc / pgx / testcontainers official docs; T3/T4 = blogs/community (cross-check only).
Marker legend: [V] = empirically verified on this machine (go1.27.2 toolchain, `go doc`, `go vet help`, spike); [T1]/[T2] = read from the cited source this session; [M] = from knowledge, NOT re-verified this session (treat as hypothesis); [A] = advisory (not machine-enforceable).
No third-party package versions are pinned in this document (names only).

---------------------------------------------------------------------
## 0. Baseline facts about the Go ecosystem today (verified)

- Latest stable: go1.27.2 (go.dev/dl JSON, `stable: true`) [V]. Local toolchain is go1.27.2 [V]. Support policy [M]: the two latest majors (1.27, 1.26) get security fixes.
- Release highlights that change how code should be written (all [T1] release notes unless marked):
  - 1.22: per-iteration `for` loop variables; `range N` over ints; ServeMux method/wildcard patterns. Spike [V]: with `go 1.22+` in go.mod the closure-capture loop prints `012`; `range 3` fails to compile with `go 1.21` ("requires go1.22 or later"). So the `go` line in go.mod controls language semantics per module.
  - 1.23: range-over-func iterators (`iter.Seq`, `iter.Seq2`) [V `go doc iter`].
  - 1.24: generic type aliases; `tool` directive in go.mod (`go get -tool`, `go tool <name>`); `os.Root`; `testing.B.Loop`; `omitzero` JSON tag; `strings.Lines/SplitSeq/FieldsSeq`; `runtime.AddCleanup`; `weak`; vet `tests` analyzer; Swiss-table maps.
  - 1.25: `testing/synctest` GA (`synctest.Test`, `synctest.Wait`); `sync.WaitGroup.Go`; go.mod `ignore` directive; vet `waitgroup` and `hostport`; container-aware GOMAXPROCS (cgroup CPU limit) and periodic update; `go` command no longer auto-adds a `toolchain` line when bumping `go`; experimental json/v2 and Green Tea GC.
  - 1.26: `new(expr)` (e.g. `new(yearsSince(born))`, optional pointer fields); self-referential generic constraints; `go fix` rewritten as host of "modernizers" + `//go:fix inline`; `errors.AsType[E]`; `slog.NewMultiHandler`; `testing` `T/B/F.ArtifactDir` (+`go test -artifacts`); Green Tea GC default; `ReverseProxy.Director` deprecated in favor of `Rewrite`; ServeMux trailing-slash redirect now 307; `signal.NotifyContext` cancel cause names the signal; `reflect` iterators; `io.ReadAll` cheaper; `B.Loop` no longer blocks inlining.
  - 1.27 (current): generic *methods* (methods may declare their own type params; still not on interfaces, cannot satisfy interface methods); wider function type inference; `encoding/json/v2` + `encoding/json/jsontext` shipped, `encoding/json` v1 re-implemented on top of v2 (opt-out `GOEXPERIMENT=nojsonv2`); `go test` runs vet `stdversion` by default; vet `printf` flags `%w` wrapping a `*E` pointer where `E` implements error (breaks `errors.Is/As`); `goroutineleak` pprof profile GA (`/debug/pprof/goroutineleak`); `synctest.Sleep`; `go doc pkg@version` and `go doc -ex`; `go mod tidy` merges require blocks to <=2 for `go 1.27` modules; new `go fix` modernizers (`atomictypes`, `embedlit`, `slicesbackward`, `unsafefuncs`, `waitgroupgo`); `bytes/strings.CutLast`; `net/url.URL.Clone`; `http.Server.MaxHeaderValueCount`; `uuid` package added to stdlib; `asynctimerchan` removed (timer channels always unbuffered/synchronous).
- `go vet` analyzers registered in this toolchain [V `go vet help`]: appends, assign, atomic, bools, buildtag, cgocall, composites, copylocks, defers, directive, errorsas, hostport, httpresponse, ifaceassert, loopclosure, lostcancel, nilfunc, printf, shift, sigchanyzer, slog, stdmethods, stdversion, stringintconv, structtag, testinggoroutine, tests, timeformat, unmarshal, unreachable, unsafeptr, unusedresult, waitgroup.
- `go fix` modernizers present [V `go tool fix help`]: any, atomictypes, buildtag, embedlit, errorsastype, forvar, hostport, inline, mapsloop, minmax, newexpr, omitzero, plusbuild, rangeint, reflecttypefor, slicesbackward, slicescontains, slicessort, stditerators, stringsbuilder, stringscut, stringscutprefix, stringsseq, testingcontext, unsafefuncs. `go fix -diff` prints a patch and exits non-zero if non-empty (usable as a CI "code is modern" gate) [V `go help fix`].
- Observation [V]: `go mod init` under go1.27.2 wrote `go 1.27.2` (full current version), whereas the 1.26 release notes say 1.N writes `go 1.(N-1).0`. Either behavior was reverted/changed in 1.27 or the notes are version-specific; do not rely on either - always set the `go` line explicitly.
- golangci-lint: v2 config format (`version: "2"`) [T2 docs]; latest GitHub release at research time is a v2.x (v2 major) [T2 api]. Six formatters in v2: gci, gofmt, gofumpt, goimports, golines, swaggo [T2]. golangci-lint, govulncheck, staticcheck are NOT installed on this machine [V] -> bootstrap must handle "tool missing".

---------------------------------------------------------------------
## 1. Project / module layout

R1.1 Start flat; add structure only when forced. A library = package(s) at module root; a single command = `main.go` at root. [T1 go.dev/doc/modules/layout]
R1.2 Services/CLIs with multiple binaries: `cmd/<binary>/main.go` (thin: parse flags/env, build deps, call `run(ctx, args, env) error`), private logic under `internal/`. [T1 layout guide, "Server project": logic in `internal/`, binaries in `cmd/`, non-Go assets in their own dirs]
R1.3 Do NOT create `pkg/`. The official layout guide never mentions it; `internal/` gives compiler-enforced privacy, root/sub-directories give public API. `pkg/` is a community convention [T3] with no toolchain meaning; it adds an import path segment. Exception: repo already uses it -> keep (legacy rule). (Resolution of the cmd/internal/pkg debate: `cmd/` + `internal/` yes, `pkg/` no.)
R1.4 Default everything to `internal/`; promote to public only on a real external consumer. Rationale: internal APIs can be refactored freely; public APIs carry semver obligations. [T1]
R1.5 Package by domain/responsibility (`internal/orders`, `internal/billing`), not by layer-type (`models/`, `controllers/`, `utils/`). Tightly coupled types stay in one package; no "one type per file" rule. [T2 Google best-practices]
R1.6 Reusable code needed by other projects -> separate module, not a `pkg/` dir. [T1 layout guide]
R1.7 Non-Go dirs: `migrations/`, `api/` (OpenAPI/proto), `deploy/`, `scripts/`; exclude with go.mod `ignore` directive (1.25+) when they contain Go files you do not want in `./...`. [T1 release notes]
R1.8 `main` is untestable glue: `func main() { if err := run(...); err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) } }`; `os.Exit`/`log.Fatal` only in `main`, at most once. [T2 Uber]
R1.9 `go.mod` hygiene: explicit `go` line = minimum supported language/toolchain (hard minimum since 1.21; it also sets language semantics per module [V spike]); optional `toolchain` line; commit `go.mod` + `go.sum`. [T1 go.dev/doc/toolchain]

## 2. Package design & naming

R2.1 Package names: short, lowercase, singular, no underscores; avoid `util`, `common`, `helper`, `misc`, `base`. [T2 Google; T1 Code Review Comments]
R2.2 Don't stutter: `orders.Service`, not `orders.OrdersService`; `yamlconfig.Parse` not `ParseYAMLConfig`. No `Get` prefix for getters. [T2 Google]
R2.3 Initialisms keep case: `ServeHTTP`, `userID`, `URL`. Receiver names short, consistent, never `this/self/me`. [T1 CRC]
R2.4 Test-double packages: `<pkg>test` (e.g. `orderstest`). [T2 Google]
R2.5 Avoid `init()` and mutable package-level state; if unavoidable `init` must be deterministic, no I/O/env/goroutines. Inject dependencies via constructors. [T2 Uber]
R2.6 No import cycles by construction: domain types in a leaf package; wiring in `cmd/` or an `internal/app` composition root. [A]
R2.7 Comments on every exported identifier, starting with the identifier name; package comment directly above `package` clause, starting `Package x ...` (for main: `Command x ...`). [T1 CRC / go.dev/doc/comment]
R2.8 Don't shadow stdlib package names or predeclared identifiers (`url`, `error`, `string`, `len`). [T2]
R2.9 Run `go fix`-style modernization (1.26+) after bumping `go`: `go fix -diff ./...` then `go fix ./...` - converts `interface{}`->`any`, 3-clause loops -> `range int`, `sort.Slice` -> `slices.Sort`, `HasPrefix+TrimPrefix` -> `CutPrefix`, `errors.As` -> `errors.AsType`, `context.WithCancel` in tests -> `t.Context()`, etc. [V modernizer list]

## 3. Interfaces

R3.1 Accept interfaces, return concrete types (structs). [T1 CRC: "Producers should return concrete types"]
R3.2 Define the interface in the CONSUMER package, as small as the consumer needs (1-3 methods). Never define an interface "for mocking" next to the implementation, and never before a second implementation/consumer exists. [T1 CRC]
R3.3 Exception: the producer package exports an interface when it IS the abstraction (`io.Reader`, `http.Handler`, `slog.Handler`, `driver.Driver`), or a plugin contract with multiple in-package implementations. [A]
R3.4 sqlc option `emit_interface` (generated `Querier`) is acceptable only because the interface is generated and matches exactly; still prefer a consumer-defined narrow interface for the service layer. [T2 sqlc config]
R3.5 Compile-time conformance check where a type must satisfy an interface: `var _ http.Handler = (*Handler)(nil)`. [T2 Uber]
R3.6 Never pointer-to-interface. Do not embed types in exported structs (leaks API); write delegating methods. [T2 Uber]
R3.7 Receivers: pointer receiver when mutating, containing a mutex/uncopyable, or large; don't mix receiver kinds on one type; value receiver only for small immutable types. [T1 CRC] (lint: `recvcheck`.)
R3.8 Type assertions: always comma-ok. [T2 Uber]

## 4. Error handling

R4.1 Handle each error exactly once: either return it (with context) or log/handle it - never log AND return. [T2 Google/Uber]
R4.2 Add context only when it adds information: `fmt.Errorf("load config %q: %w", path, err)`. Error strings lowercase, no trailing punctuation, no "failed to" filler. Place `%w` at the end. [T2 Google; T1 CRC]
R4.3 `%w` when callers may inspect the cause; `%v` at API/RPC/storage boundaries when the cause must stay opaque (do not leak driver/internal error types into your public contract). [T2 Google]
R4.4 Inspect with `errors.Is` (values) and `errors.As` / `errors.AsType[E]` (types; generic, type-safe, 1.26+ [V `go doc errors.AsType`]). Never compare `err == ErrX` for wrapped chains and never match on `err.Error()` strings. [T2 Google; vet `errorsas`]
R4.5 Sentinel vs typed vs opaque: sentinel (`var ErrNotFound = errors.New("not found")`) for a single condition callers branch on; typed (`type ValidationError struct{...}` + `Error()` suffix, pointer receiver) when callers need data; otherwise plain `fmt.Errorf`. Export only what callers must match. Names: `ErrFoo` / `FooError`. [T2 Uber]
R4.6 Multiple errors: `errors.Join` and `fmt.Errorf` with multiple `%w` (cleanup paths, validation aggregation); `AsType`/`Is` traverse trees depth-first. [V `go doc`]
R4.7 Never wrap a pointer-typed error value with `%w` where `E` is the pointer's pointee implementing `error` - vet `printf` flags it from 1.27 and it breaks `Is/As`. [T1 1.27 notes]
R4.8 No panics for control flow or expected failures. Panic only for programmer errors / impossible states and package-init invariants (`regexp.MustCompile` on constants). Internal panics must not cross a public API boundary (recover -> return error). Don't `recover` to keep a process alive except at well-defined boundaries (HTTP server already recovers per-request; add logging middleware, not silent swallow). [T2 Google/Uber]
R4.9 Never discard errors with `_` (except documented cases: `bytes.Buffer.Write`, `defer resp.Body.Close()` after a successful read, `fmt.Fprint` to stderr). `defer f.Close()` on written files must check the error (named return + `errors.Join`). [T1 CRC] (lint `errcheck`.)
R4.10 Early return / indent-error-flow: happy path unindented. [T1 CRC]
R4.11 No in-band errors (`-1`, `""`); return `(T, error)` or `(T, bool)`. [T1 CRC]
R4.12 Errors crossing into HTTP/gRPC are mapped once at the transport edge (`errors.Is(err, orders.ErrNotFound)` -> 404); domain code never imports `net/http` status codes. [A]
R4.13 Wrap with operation context at layer boundaries, not at every frame; stack traces are not a Go convention - rely on message chains + structured logs. [A]

## 5. Context propagation & cancellation

R5.1 `ctx context.Context` is the first parameter of every function that does I/O, blocks, or may be long; never store in a struct (except to satisfy an external interface); never in option structs; never nil; `context.Background()` only in `main`/init/tests; `TODO()` as a tracked placeholder. [T1 go.dev/blog/context; T2 Google/CRC]
R5.2 Always `defer cancel()` right after `WithCancel/WithTimeout/WithDeadline` (vet `lostcancel`). [T1 blog; V vet list]
R5.3 `context.Value` only for request-scoped, cross-API data (trace/request IDs, auth principal), with an unexported key type and typed accessor; never for optional parameters or dependencies. [T1 blog]
R5.4 Use `WithCancelCause` + `context.Cause(ctx)` when the reason for cancellation matters; `WithoutCancel` to detach background work from a request lifetime (keeps values); `AfterFunc` for cleanup callbacks. [V `go doc`]
R5.5 Root the process context with `signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)` - since 1.26 the cancel cause identifies the received signal. [T1 1.26 notes]
R5.6 Every blocking call selects on `ctx.Done()`; every outbound call (`http.NewRequestWithContext`, `db.QueryContext`/pgx methods, gRPC) carries ctx. (lint `noctx`, `contextcheck`.) [T2 golangci-lint]
R5.7 Tests: use `t.Context()` (canceled just before Cleanup funcs run) instead of `context.WithCancel(context.Background())`. [V `go doc testing.T.Context`; `testingcontext` modernizer]
R5.8 Document context behavior only when it deviates from "cancel => return ctx.Err()". [T2 Google]

## 6. Concurrency

R6.1 Prefer synchronous APIs; let callers add concurrency. [T1 CRC]
R6.2 Every goroutine has: a defined stop condition, a way to signal stop (ctx), and a way for the owner to wait (WaitGroup/errgroup). No fire-and-forget; no goroutines in `init()`; background workers = constructor + `Close/Shutdown`. [T2 Uber; T1 CRC]
R6.3 Structured fan-out: `golang.org/x/sync/errgroup` - `errgroup.WithContext` (ctx canceled on first error or on Wait return), `SetLimit(n)` to bound parallelism, `TryGo` for non-blocking. `Go` blocks when limit reached. Group must not be reused across tasks. [T2 pkg.go.dev]
R6.4 Plain fan-out without errors: `sync.WaitGroup.Go(f)` (1.25+) replaces `Add(1)` + `go` + `defer Done()`; `f` must not panic; vet `waitgroup` flags misplaced `Add`. [V `go doc sync.WaitGroup.Go`]
R6.5 Loop variables are per-iteration (go >= 1.22 in go.mod [V]); delete legacy `i := i` copies (`forvar` modernizer) - but only when go.mod's `go` >= 1.22.
R6.6 Channels for ownership transfer / signaling / pipelines; mutex for protecting state; `sync/atomic` typed values (`atomic.Int64`, `atomic.Pointer[T]`) over raw functions (`atomictypes` modernizer). Don't embed mutexes; zero-value mutex, named field. [T2 Uber; T1 notes]
R6.7 Channel buffers 0 or 1 unless justified by measurement; specify direction in params (`<-chan T`); the sender closes; never close from receiver. [T2 Uber/Google]
R6.8 Never call `t.Fatal/FailNow` from a non-test goroutine (vet `testinggoroutine`); use `t.Error` + return. [V vet list]
R6.9 Detect leaks: tests with `-race`; goroutine-leak detection via `goroutineleak` pprof profile (GA in 1.27; `/debug/pprof/goroutineleak`) in services; for unit tests, bounded lifetimes with `synctest.Test` (fails on deadlock; waits for bubble goroutines). [T1 1.27 notes; V synctest doc]
R6.10 Race detector (`go test -race`) in CI for every PR on supported platforms; it only finds races on executed paths so pair with concurrency tests. [T1 go.dev/security/best-practices]
R6.11 Unbounded concurrency is a bug: bound with `SetLimit`, worker pools, or semaphores (`golang.org/x/sync/semaphore`). [A]
R6.12 GOMAXPROCS: since 1.25 cgroup-aware automatically; remove `automaxprocs` shims on go >= 1.25; do not set manually (manual setting disables the auto behavior). [T1 1.25 notes]
R6.13 Timers/tickers: `time.NewTimer/Ticker` with `Stop`; 1.27 timer channels are always synchronous (no stale values after Stop/Reset). [T1]

## 7. Logging (log/slog)

R7.1 Use `log/slog` only (stdlib); no logrus/zap in new code unless a measured need exists. JSON handler in prod, text handler for local/CLI. [T1 go.dev/blog/slog]
R7.2 Structured key/value; stable lower_snake or dot keys; no string-interpolated messages. Use `LogAttrs` + typed `slog.Attr` in hot paths (avoids allocations). Vet `slog` analyzer catches odd key/value arguments; add lint `sloglint` to enforce a style (attrs-only OR kv-only, context-required, no raw keys). [T1 blog; V vet list; T2 lint list]
R7.3 Use `*Context` variants (`InfoContext`) so handlers can extract trace/request IDs from ctx; cancellation does not suppress the record. [T1 blog]
R7.4 Derive loggers with `Logger.With(...)`/`WithGroup` for shared fields; pass `*slog.Logger` via constructors (not a global) in libraries; in apps `slog.SetDefault` once in `main` is acceptable. [T1 blog; T2 Uber on globals]
R7.5 Redaction: implement `slog.LogValuer` on secret-bearing types (return `slog.StringValue("[REDACTED]")` or a safe group); plus `ReplaceAttr` for key-based scrubbing (`password`, `token`, `authorization`). Never log whole request/response bodies, headers, DSNs, or config structs. [T1 blog (LogValuer redaction); ReplaceAttr details [M]]
R7.6 Levels: Debug = developer detail (off in prod); Info = lifecycle/business events; Warn = recoverable anomaly; Error = actionable failure (pages someone). Don't log-and-return. [T2 Google]
R7.7 Multi-sink: `slog.NewMultiHandler` (1.26+) instead of custom fan-out handlers. [T1 1.26 notes]
R7.8 Library code never configures global logging; it accepts a `*slog.Logger` option or logs nothing. [A]
R7.9 Libraries and tests: use a discard handler or `slogtest`/in-memory handler to assert on logs sparingly. [A]

## 8. Configuration

R8.1 12-factor: config from environment (+ optional file), parsed once in `main`/`internal/config` into a typed struct, validated at startup, fail fast with an actionable message. [A; T2 Uber on init errors propagating to main]
R8.2 Stdlib first: `flag` + `os.Getenv`/`os.LookupEnv` + `time.ParseDuration`; adopt a config library only if file+env+flags layering is truly needed (dependency gate applies). [A]
R8.3 No config reads from package-level `init()` or deep in business code; pass the struct (or sub-structs) via constructors. [T2 Uber]
R8.4 Secrets only from env/secret manager, never in repo, never logged (see R7.5); config struct implements `LogValue` that redacts. [A]
R8.5 Use `time.Duration` for intervals (`READ_TIMEOUT=5s`), not ints; if forced to use ints, put the unit in the name (`IntervalMillis`). [T2 Uber]
R8.6 CLIs: cobra or stdlib `flag` + subcommands; `cmd.Context()` must be used with cobra; exit codes: 0 ok, 1 error, 2 usage. [T2 Google (cobra Context); exit codes [M]]
R8.7 Never add feature flags proactively (user policy) - config is not a flag system. [user rule]

## 9. HTTP servers (stdlib-first)

R9.1 Use `net/http` `ServeMux` (1.22+) for routing: patterns `[METHOD ][HOST]/[PATH]`, wildcards `{id}`, `{rest...}`, exact-root `{$}`; `GET` also matches HEAD; most specific wins, conflicts panic at registration (fail-fast at startup); read with `r.PathValue("id")`. [V `go doc net/http.ServeMux`] Add a router lib (chi etc.) only when middleware grouping ergonomics justify it - and then pick one compatible with `http.Handler`.
R9.2 Middleware = `func(http.Handler) http.Handler`; order: recover -> request-ID/trace -> logging -> auth -> body limit -> handler. Keep handlers thin: decode -> call service -> encode; mapping errors in one place (R4.12). [A]
R9.3 ALWAYS build an explicit `*http.Server`, never `http.ListenAndServe` default: set `ReadHeaderTimeout` (mandatory, slowloris), `ReadTimeout`, `WriteTimeout`, `IdleTimeout`, `MaxHeaderBytes`; per-request deadlines via `http.TimeoutHandler` or ctx. Never expose `DefaultServeMux` (anything importing `net/http/pprof` registers on it). [T1 pkg doc names the fields; policy [M/T3]]
R9.4 Graceful shutdown: `ctx, stop := signal.NotifyContext(...)`; run `srv.ListenAndServe()` in a goroutine (errgroup); on `<-ctx.Done()` call `srv.Shutdown(shutdownCtx)` with a bounded timeout; treat `http.ErrServerClosed` as success. `Shutdown` closes listeners, closes idle conns, waits indefinitely for active ones unless ctx expires. `BaseContext` should derive from the root ctx so in-flight handlers see shutdown. Readiness endpoint should flip to not-ready before `Shutdown`. [V `go doc http.Server.Shutdown`]
R9.5 Client side: never use `http.DefaultClient` for production calls (no timeout). Build `http.Client{Timeout: ...}` + tuned `Transport`; reuse clients; always `defer resp.Body.Close()` and drain/limit reads (vet `httpresponse`; lint `bodyclose`). [M/T2 lint]
R9.6 Limit request bodies (`http.MaxBytesReader`), validate content-type, decode JSON with `DisallowUnknownFields` when strictness is wanted; JSON: use `omitzero` for `time.Time`/structs (1.24+); json/v2 (`encoding/json/v2`) is now shipped in 1.27 and v1 runs on it - new code may use v2 but pin behavior with tests; v2 rejects invalid UTF-8 and duplicate names by default. [T1 1.24/1.27 notes]
R9.7 CSRF for cookie-auth browsers: `http.CrossOriginProtection` (stdlib; Sec-Fetch-Site/Origin check; GET/HEAD/OPTIONS exempt). [V `go doc`]
R9.8 Reverse proxies: use `httputil.ReverseProxy.Rewrite`, not deprecated `Director` (hop-by-hop header stripping hole). [T1 1.26 notes]
R9.9 Health: `/healthz` (liveness, no deps) and `/readyz` (deps). pprof/metrics on a separate internal-only listener (`127.0.0.1` or admin port), not the public mux. [M]
R9.10 Test handlers with `httptest.NewRecorder`/`httptest.NewServer`; mux patterns are testable by calling `mux.ServeHTTP`. [T1]
R9.11 HTTP/2 enabled automatically on TLS for `Server`; configure via `Server.Protocols` if needed. [T1 pkg doc]

## 10. Database access

R10.1 Postgres service: `pgx/v5` + `pgxpool` is the default driver/pool; use `database/sql` only when portability across engines or an ORM/tool requires it. sqlc supports `sql_package: pgx/v5` or `database/sql` (default `database/sql`). Rationale: pgx native API gives richer types, `CollectRows`, `CopyFrom`, batch, LISTEN/NOTIFY. [T2 sqlc config + pgx docs; preference is a decision, see C-list]
R10.2 Pool config: `pgxpool.ParseConfig` then set `MaxConns` (default = max(4, NumCPU)), `MinConns`, `MaxConnLifetime` (+jitter), `MaxConnIdleTime`, `HealthCheckPeriod`; the pool does not connect at creation -> `Ping`/acquire at startup to fail fast; `Close()` blocks until connections return - call after server Shutdown. Size `MaxConns` against DB max_connections / replica count. [T2 pgxpool docs]
R10.3 Queries: sqlc (SQL-first codegen, type-safe) for the bulk of CRUD; hand-written pgx for dynamic/analytic queries; always parameterized (`$1`) - never string-built SQL (gosec G201/G202). Check generated code in; CI runs `sqlc generate` + `git diff --exit-code` and `sqlc vet`/`verify`. [T2 sqlc config: version "2", engine, schema, queries, `gen.go` options; `vet` runs rules, `verify` verifies schema changes]
R10.4 sqlc config choices: `emit_pointers_for_null_types: true` (pgx/sqlite) to get `*T` instead of `pgtype`/`sql.Null*`; `emit_json_tags: false` (don't couple DB structs to API; map explicitly); overrides for `uuid`, `timestamptz`, `numeric`. [T2 sqlc config; choice [A]]
R10.5 Transactions: `pgx.BeginTxFunc`/`pgx.BeginFunc` style helper (commit on nil, rollback on error/panic) [BeginFunc not verified on page - [M]]; or `tx, _ := pool.Begin(ctx); defer tx.Rollback(ctx)` (safe after Commit) then `Commit`. pgxpool `BeginTx` ctx covers only BEGIN; there is NO automatic rollback on ctx cancellation - always defer Rollback. Keep transactions short, no network calls inside; pass `sqlc.Queries.WithTx(tx)`; services own transaction boundaries (via a `Tx(ctx, func(q) error)` helper), repositories don't. [T2 pgxpool docs]
R10.6 Retry only on serialization/deadlock errors (SQLSTATE 40001/40P01), with bounded backoff and idempotent bodies. [M]
R10.7 Migrations: versioned, forward-only SQL files in `migrations/` (goose, golang-migrate, or atlas [M - tool comparison not verified]); applied by a separate command/job (not implicitly on every app instance at boot unless single-instance); sqlc reads the same `migrations` dir as schema. Backward-compatible (expand/contract) changes for zero-downtime. Never edit applied migrations. [A]
R10.8 Context on every DB call; set statement/lock timeouts at connection (`RuntimeParams`) or per tx. [A]
R10.9 `database/sql` specifics (when used): `SetMaxOpenConns/SetMaxIdleConns/SetConnMaxLifetime`, always `rows.Close()` + `rows.Err()`, `QueryRowContext(...).Scan`. 1.27 exports `sql.ConvertAssign` and adds `driver.RowsColumnScanner`. [T1 1.27 notes; rest [M]]
R10.10 NULL handling: pointers or `pgtype`/`sql.Null*`; zero value != NULL - model deliberately at the boundary. [A]
R10.11 Tests hit a real Postgres (testcontainers or a CI service), not a SQL mock; see R12.9. [A/T2]

## 11. Package/API design (generics, options, zero values)

R11.1 Make the zero value useful (`sync.Mutex`, `bytes.Buffer`, `errgroup.Group`); constructors only when invariants require them. Return `nil` slice, not `[]string{}`, unless JSON must be `[]`. [T1 CRC; T2 Uber]
R11.2 Generics: use for containers/algorithms over many element types (`slices`, `maps`, typed sets/caches, `iter.Seq` adapters) and to remove duplicate code with identical bodies. Don't use for single-implementation behavior (use interfaces), don't wrap `any` constraints "just in case", don't build generic frameworks/ORMs. Prefer `slices`/`maps`/`cmp` stdlib before writing helpers. 1.27 generic methods exist but cannot satisfy interfaces - rarely needed outside builders/`Rand.N`-style APIs. [T1 notes; guidance [A]]
R11.3 Iterators: return `iter.Seq[V]`/`iter.Seq2[K,V]` for lazily produced sequences (e.g., paged DB/API results, `maps.Keys`); `yield` returning false must stop and never be called again (it panics). Don't use iterators where a slice is simpler/cheaper. [V `go doc iter`]
R11.4 Options: struct for config with many fields; functional options (`type Option func(*T)`) only when most callers pass none, options can fail, or API must grow compatibly; options take values (`WithTimeout(d)`), later wins; never put ctx in options. [T2 Google]
R11.5 Avoid naked `bool` parameters - named types or option structs. Enums via `iota` start at 1 unless zero is a valid default; give them `String()`. [T2 Uber]
R11.6 Copy slices/maps at API boundaries when retaining or returning internal state. [T2 Uber]
R11.7 Use `new(expr)` (1.26+) for optional pointer literals instead of helper `ptr()` funcs - only if module `go` >= 1.26 [V spike: fails at `go 1.22`]. [T1]
R11.8 `time.Time`/`time.Duration` in APIs, never raw ints; UTC at boundaries. [T2 Uber]
R11.9 `os.Root` (1.24+) for file access constrained to a directory (uploads, archive extraction). [T1]
R11.10 Public API changes: semver; use `//go:fix inline` + `Deprecated:` doc to migrate callers (1.26 inliner). [T1]

## 12. Testing

R12.1 Table-driven tests with named cases and subtests (`t.Run(tt.name, ...)`); struct fields named in literals; inputs/outputs `give`/`want` (Uber) or `in`/`want`. Don't put logic/branching in tables - split tests. [T2 Uber/Google]
R12.2 Test failures say what: `Foo(%v) = %v, want %v` (actual before expected). Fail in the Test function, not in assertion helpers; helpers that must fail call `t.Helper()` + `t.Fatalf`. With subtests use `t.Fatal`; without, `t.Error`+continue. [T2 Google; T1 CRC]
R12.3 Assertion libs: stdlib `testing` + `cmp.Diff` (go-cmp) is the default; testify only if the repo already uses it (then enable lint `testifylint`). [T2 Google discourages assertion helpers; choice [A]]
R12.4 `t.Parallel()` for independent tests/subtests (go >= 1.22 loop var safe). Lint: `tparallel`, `paralleltest` (the latter is noisy - optional). Never parallelize tests that share a DB/global without isolation. [T2 lint list; Uber]
R12.5 Use `t.Context()`, `t.TempDir()`, `t.Setenv()`, `t.Cleanup()`; `t.ArtifactDir()` (1.26) for outputs like screenshots/dumps. [V/T1]
R12.6 Fakes over mocks: hand-written in-memory fakes (`orderstest.FakeStore`) or real dependencies (real `httptest.Server`, real DB) beat generated call-expectation mocks, which couple tests to implementation. Use a mock generator only for third-party interfaces that are hard to fake. [T2 Google ("use real transports")]
R12.7 Time & concurrency: `testing/synctest` (`synctest.Test` + `synctest.Wait`; fake clock starting 2000-01-01 UTC; time only advances when all bubble goroutines are *durably blocked*; mutexes, real network I/O, syscalls are NOT durable blocks; use in-memory fakes/`net.Pipe`; tests must not leak goroutines). Replaces `sleep`/injectable-clock hacks for timeouts, tickers, retry/backoff. 1.27 adds `synctest.Sleep`. [V `go doc testing/synctest`; T1 blog]
R12.8 Golden files: `testdata/*.golden` + an `-update` flag; compare with `cmp.Diff`; review diffs in PR. [T3/[M]; convention `testdata/` is T1]
R12.9 Integration tests: testcontainers-go (`testcontainers.Run`, port mapping to random free host port, wait strategies, `testcontainers.CleanupContainer(t, c)`; requires Docker; Ryuk reaps leaks). Gate behind a build tag or `-short`/env (`//go:build integration`) so `go test ./...` stays fast; share one container per package via `TestMain` and isolate with per-test schema/transaction/template DB. [T2 testcontainers docs; gating [A]]
R12.10 Fuzzing: `FuzzXxx(f *testing.F)`, `f.Add` seeds, one `f.Fuzz` target; seed + `testdata/fuzz/FuzzXxx/` corpus run on plain `go test`; run `go test -fuzz=FuzzXxx -fuzztime=30s` (use `Nx` for iterations) on parsers/decoders/untrusted input and round-trip invariants; commit minimized failing inputs. [T1 go.dev/doc/security/fuzz]
R12.11 Benchmarks: use `for b.Loop() { ... }` (1.24+; setup once per `-count`, body not optimized away; 1.26 no longer blocks inlining) not `for i := 0; i < b.N; i++`; `b.ReportAllocs()`; compare with `benchstat` [M]; `-run=^$ -bench=. -benchmem -count=10`. [V `go doc testing.B.Loop`; T1 notes]
R12.12 `-race` always in CI (`go test -race ./...`); `-shuffle=on` to expose order dependence; `-count=1` to bypass cache when needed; coverage: `go test -coverprofile=c.out -covermode=atomic ./...` (atomic with -race) and `go tool cover -func`; coverage is a signal not a target - follow project complexity policy (tests are written from complexity >=7 per the user's global rules). [T1 for flags [M-level detail]; policy user rule]
R12.13 vet runs in `go test` (subset); 1.27 adds `stdversion` to it; the `tests` analyzer (malformed Test/Example/Fuzz names) runs there too. [T1]
R12.14 Skipped tests need a tracked issue reference in the skip message (user rule); no `t.Skip` without it.
R12.15 Test packages: `package foo` for white-box, `package foo_test` for API-surface tests (and to catch import-cycle design smells); keep both when needed. [T1/T2 convention]

## 13. Lint / format / static analysis

R13.1 Formatting is non-negotiable: `gofmt` is the baseline; `goimports` for import grouping (std / third-party / local). `gofumpt` (stricter superset) optional - recommended for new repos, but it's a style bet (C-list). Run formatters via golangci-lint v2 `formatters:` section (gofmt, goimports, gofumpt, gci, golines, swaggo available) so one tool + one config gates both. [T2 golangci docs]
R13.2 golangci-lint v2 config skeleton (`.golangci.yml`) [T2 docs for keys: `version: "2"`, `linters.default` (standard|all|none|fast), `enable`/`disable`, `settings`, `exclusions` (generated, presets, rules, paths), `formatters`, `run`]:
```yaml
version: "2"
run:
  tests: true
  relative-path-mode: gomod
linters:
  default: standard          # errcheck, govet, ineffassign, staticcheck, unused (standard set; confirm via `golangci-lint linters`)
  enable:                    # all names confirmed to exist in the linters list [T2]
    - errorlint              # %w / errors.Is/As discipline
    - bodyclose
    - noctx
    - contextcheck
    - sloglint
    - gosec
    - revive
    - gocritic
    - perfsprint
    - copyloopvar
    - intrange
    - usetesting
    - testifylint            # only if testify is used
    - tparallel
    - nilerr
    - exhaustive
    - errname
    - recvcheck
    - nolintlint
    - forbidigo              # e.g. ban fmt.Print*, log.Fatal outside main
    - depguard               # ban deprecated/duplicate deps (logrus, pkg/errors, ...)
  settings:
    nolintlint: { require-explanation: true, require-specific: true }
  exclusions:
    generated: lax
    rules:
      - path: _test\.go
        linters: [gosec, errcheck]
formatters:
  enable: [gofmt, goimports]   # add gofumpt if adopted
```
(The exact membership of the `standard` default set was NOT displayed by the docs page fetched - verify with `golangci-lint linters` once installed. [unverified])
R13.3 Noisy/opinionated linters to leave OFF by default: `wrapcheck` (forces wrapping at every boundary; conflicts with R4.13), `gochecknoglobals`, `paralleltest`, `godot`, `varnamelen`, `funlen`, `cyclop`, `gocognit`, `lll`, `wsl`/`nlreturn`. Enable per-repo when the team asks. [A; linter names exist [T2]]
R13.4 Never blanket-disable; `//nolint:linter // reason` only (enforce via `nolintlint`). [A]
R13.5 `go vet ./...` always (subset auto-runs in `go test`); extra analyzers via `-vettool`. `staticcheck` is already inside golangci-lint (standard set includes `staticcheck`; v2 merged gosimple/stylecheck into it [M]). [V vet list; M]
R13.6 `govulncheck ./...` for source (reachability-based: "called" = actionable, "imported" = informational); `govulncheck -mode=binary ./bin/app` for artifacts; `-format sarif|json` for CI [first part T1 tutorial; binary/format flags [M]]. Install per project tooling policy (R14.2).
R13.7 `go fix -diff ./...` in CI (non-zero if modernizers have changes) - keeps code idiomatic after Go upgrades. [V `go help fix`]
R13.8 `go mod tidy -diff`-style check (`go mod tidy` then `git diff --exit-code go.mod go.sum`). [M; `-diff` flag for tidy not verified]

## 14. Dependency hygiene

R14.1 Stdlib first; a new dependency needs approval (user rule) and the plan-stage gate (identity, freshness via `go list -m -u`/`go list -m -versions`, vulnerability via `govulncheck`, API study via `go doc pkg@version` (1.27 supports `go doc example.com/pkg@v1.2.3`)). [user rule; V 1.27 notes]
R14.2 Dev tools pinned in go.mod via `tool` directive: `go get -tool <module/cmd/x>`; run `go tool x`; upgrade all with `go get tool`; install with `go install tool`. Replaces `tools.go` blank-import hack. Caveat: tools share the module's dependency graph (version conflicts, vuln noise); for heavy linters (golangci-lint) prefer a separately pinned binary/CI action or a separate `tools/go.mod`. [T1 go.dev/doc/modules/managing-dependencies; caveat [A]]
R14.3 `go mod tidy` before commit; commit `go.sum`; `go mod verify` in CI [M]; never hand-edit `go.sum`.
R14.4 `replace` directives: only for local development or short-lived forks; never merge a local-path `replace` to main; `replace` bypasses `go.sum` verification of the original module, so review. For multi-module dev use `go.work` (not committed unless the repo is a deliberate workspace). [T1 managing-dependencies; go.work policy [A]]
R14.5 Vendoring: not needed by default (module proxy + `go.sum` + checksum DB give integrity). Vendor only for hermetic/offline builds or audit mandates: `go mod vendor`; build with `-mod=vendor`; CI verifies `go mod vendor` is clean. [M]
R14.6 Toolchain: `go` line = minimum supported; `toolchain` line = recommended build version; `GOTOOLCHAIN=auto` default fetches newer toolchains - in CI pin explicitly (`GOTOOLCHAIN=local` + setup-go with the version from go.mod, or `go1.x.y`) for reproducible builds. `go get go@1.x.y` to bump. Since 1.25, bumps no longer add a `toolchain` line automatically. [T1 go.dev/doc/toolchain]
R14.7 Keep Go current (security patches in minors): support window = latest two releases [M]; bump `go` line deliberately and run `go fix`. [T1 security best practices]
R14.8 Upgrades: `go list -m -u all`; `go get -u=patch ./...` for patch-only; read changelogs for majors (use `dependency-changes`-style research for high-churn libs). [M]
R14.9 Avoid deprecated/dead libs (`github.com/pkg/errors`, gorilla/mux-for-new-code, logrus, ioutil). Lint via `depguard`/staticcheck `SA1019`. [A/M]

## 15. Build & release

R15.1 Reproducible static builds: `CGO_ENABLED=0 go build -trimpath -ldflags="-s -w -X main.version=$(VERSION) -X main.commit=$(COMMIT)" -o bin/app ./cmd/app`. `-trimpath` strips local paths; `-s -w` shrink; `-X` injects `var version string`. Also `-buildvcs=auto` embeds VCS info readable via `runtime/debug.ReadBuildInfo`. [M - flags not re-verified; standard go build flags]
R15.2 Version in a `var` set via `-X` or from `debug.ReadBuildInfo`; expose `--version`/`/version`. [A]
R15.3 Task runner: a `Makefile` or `Taskfile.yml` with the canonical targets (`build test lint vuln fmt tidy generate ci`) that CI and the agent both call - single source of commands. [A]
R15.4 Docker: multi-stage; builder `golang:<major.minor>` pinned (digest-pin for prod); copy `go.mod/go.sum` first + `go mod download` (layer cache) with `--mount=type=cache` for GOCACHE/GOMODCACHE; final stage `gcr.io/distroless/static` (nonroot) or `scratch` + CA certs; run as non-root; `ENTRYPOINT` exec-form; handle SIGTERM (R9.4). [M/T3]
R15.5 PGO: commit a representative production CPU profile as `default.pgo` in the main package dir; `-pgo=auto` is default; typical gain 2-14%, costs build time and slightly larger binaries; refresh profile periodically; merge multiple profiles with `go tool pprof -proto a b > merged`. Do it only after profiling shows CPU-bound hot paths. [T1 go.dev/doc/pgo]
R15.6 Release: `goreleaser` for CLIs [M]; sign + SBOM optional; run `govulncheck -mode=binary` on the release artifact. [M]
R15.7 `go:generate` directives documented and run via `make generate`; generated files committed + marked `// Code generated ... DO NOT EDIT.`; CI checks `git diff --exit-code` after generate. [T1/A]
R15.8 `go build -race`/`-cover` binaries only for tests/staging, never prod images. [A]

## 16. Performance

R16.1 Measure first. CPU: `go test -cpuprofile`, `net/http/pprof` on an admin listener, `go tool pprof -http=:0 profile` (1.26: flame graph is default view); memory: `-memprofile`, `-benchmem`; contention: block/mutex profiles; `go tool trace` for scheduling/latency (1.27: `-http` now listens on localhost only); `goroutineleak` profile for stuck goroutines. [T1 notes]
R16.2 Allocations: preallocate (`make([]T, 0, n)`, map hint) when size is known; `strings.Builder`; `strconv` over `fmt` in hot paths; avoid `interface{}` boxing in hot loops; reuse buffers via `sync.Pool` only with measured benefit; `bytes.Buffer.Peek` etc. [T2 Uber perf section (hot paths only)]
R16.3 Escape analysis: `go build -gcflags='-m=2'` shows what escapes/inlines; the compiler stack-allocates more slices in 1.26; size-specialized malloc in 1.27. Don't contort code before a profile says so. [T1 notes; flag [M]]
R16.4 Runtime: Green Tea GC default since 1.26 (10-40% less GC overhead on allocation-heavy; opt-out `GOEXPERIMENT=nogreenteagc` was to be removed in 1.27); Swiss maps since 1.24; cgroup-aware GOMAXPROCS since 1.25; tune `GOMEMLIMIT` for containers (soft memory limit) [M]. [T1 notes]
R16.5 Benchmarks must be comparable: `-count=10` + `benchstat`; use `b.Loop`; avoid microbenchmark-driven PGO profiles. [T1 pgo doc]
R16.6 Prefer algorithmic/DB fixes (indexes, batching, N+1) over micro-optimizations; `pgx` `Batch`/`CopyFrom` for bulk. [A]
R16.7 Use `weak`/`runtime.AddCleanup` (not `SetFinalizer`) for caches/resource cleanup, rarely. [T1 1.24]

## 17. Security basics

R17.1 `govulncheck` in CI + on schedule; subscribe to golang-announce for security releases; stay on latest minor. [T1 security best practices]
R17.2 `go test -race`, `go vet`, fuzzing for untrusted-input parsers. [T1 same page]
R17.3 SQL: parameterized only; no `fmt.Sprintf` in queries. HTML: `html/template` (auto-escape), never `text/template` for HTML. Paths: `os.Root` / `filepath.IsLocal` for user-supplied paths (path traversal; zip-slip). Commands: `exec.Command` with arg list, never `sh -c` + user input. [T1 os.Root; rest [M] / lint `gosec`]
R17.4 Crypto: `crypto/rand` (not `math/rand`) for secrets/tokens (`rand.Text` helper exists [T1 CRC]); stdlib `crypto/*` only, no home-grown crypto; password hashing via `golang.org/x/crypto` argon2/bcrypt (names [M]); TLS defaults of stdlib (min TLS 1.2) - don't weaken; 1.26+ hybrid ML-KEM default on. [T1 notes]
R17.5 Network: server timeouts (R9.3), body limits (R9.6), `net.JoinHostPort` not `Sprintf("%s:%d")` (vet `hostport`), CSRF protection (R9.7), SSRF-safe outbound clients for user-supplied URLs (resolve+validate IP). [V vet list; T1]
R17.6 Secrets/redaction in logs and errors (R7.5); never embed secrets in error strings that cross API boundaries. [A]
R17.7 `unsafe`/cgo: avoid; if needed, isolate and test with `-race` + vet `unsafeptr`/`cgocall`. [V vet list]
R17.8 Supply chain: pin tools, verify `go.sum`/`GONOSUMCHECK` not disabled (`GOFLAGS=-insecure` never), `GOPRIVATE` for private modules. [M]
R17.9 HTTP clients to internal services use mTLS/auth where applicable; policy is the user's call (escalation bar #4). [A]

## 18. Documentation

R18.1 Doc comments (godoc): sentence starting with the identifier; blank-line-separated paragraphs; document concurrency safety, cleanup duties (`Close`, `Stop`, `resp.Body.Close`), context behavior when non-standard, error values returned (sentinels / types, pointer-ness), non-obvious params. [T2 Google best-practices; T1 go.dev/doc/comment]
R18.2 Runnable `Example` functions (`ExampleFoo`, `ExampleFoo_suffix`; checked via `// Output:`) for public APIs; vet `tests` analyzer validates names and that examples reference real identifiers; 1.27 `go doc -ex` lists them. [T1]
R18.3 Deprecations: `// Deprecated: use X instead.` paragraph; staticcheck `SA1019` flags callers. [T1 convention]
R18.4 README: what, install (`go install .../cmd/x@latest`), quick start, config table, make targets. ADRs for decisions in `docs/adr/`. [A]
R18.5 Keep docs in sync when code changes (user rule); mandatory inline comments for preserved quirks per user's code-policies. [user rule]

---------------------------------------------------------------------
## A. Mechanical enforcement vs advisory

Mechanically enforceable (tool -> what it catches):
- Compile/language: `go build ./...` with explicit `go` line (language version gates `range int`, `new(expr)`, generic methods) [V].
- `go vet` (always; run `go vet ./...`): printf/%w (incl. 1.27 pointer-wrap check), lostcancel (R5.2), loopclosure, copylocks (mutex by value), testinggoroutine (R6.8), waitgroup (R6.4), hostport (R17.5), httpresponse, errorsas (R4.4), slog (R7.2), stdversion (uses of too-new stdlib vs go line), tests (naming), timeformat, unusedresult, unreachable, structtag, unmarshal [V list].
- `gofmt`/`goimports` (+ `gofumpt` if adopted) via golangci-lint formatters: R13.1.
- golangci-lint v2 linters (names verified to exist [T2]): `errcheck` (R4.9), `errorlint` (R4.4), `errname` (R4.5), `nilerr`, `bodyclose` (R9.5), `noctx` + `contextcheck` (R5.6), `sloglint` (R7.2), `gosec` (R17), `perfsprint` (R16.2), `copyloopvar` (R6.5), `intrange`, `usetesting` (R12.5), `testifylint`, `tparallel` (R12.4), `exhaustive` (enum switches), `recvcheck` (R3.7), `depguard` + `forbidigo` (R14.9, R1.8 no `os.Exit`/`log.Fatal` outside main, no `fmt.Print*`), `nolintlint` (R13.4), `staticcheck` (SA1019 deprecations), `revive` (naming R2.x, exported comments R2.7), `gocritic`, `prealloc` (R16.2).
- `go fix -diff ./...` exit code: modernization drift (R2.9, R13.7).
- `govulncheck` exit status/JSON: reachable vulns (R13.6).
- CI diff checks: `go mod tidy` clean, `sqlc generate` clean, `go generate` clean, `go fix -diff` clean.
- `go test -race -shuffle=on ./...`: data races, order dependence (R6.10, R12.12); `-fuzz` seeds run in normal `go test`.
- Hooks (Claude Code): PostToolUse on `*.go` edit -> `gofmt -l`/`goimports -w` on the file (cheap, mechanical); on stop/pre-commit -> `go build ./... && go vet ./...`; PreToolUse deny: editing `go.sum` by hand, adding `replace` with a local path, `git push --force` w/o lease (user global). golangci-lint only if installed (else report "tool missing").
Advisory only (needs review judgment): package layout/granularity (R1), interface placement (R3.2/R3.3), error layering and context wording (R4.2/R4.13), when to use generics (R11.2), fakes vs mocks (R12.6), concurrency design/ownership (R6.1/R6.2/R6.11), config layering (R8), transaction boundaries (R10.5), migration safety (R10.7), Docker/release design (R15), performance priorities (R16), API ergonomics/docs quality (R11, R18), SSRF/authz policy (R17).

---------------------------------------------------------------------
## B. Proposed plugin contents: `v1rus-go`

### B.1 Skills (trigger-style)
1. `go-bootstrap` - Invoke when: first task in a Go repo, or the agent lacks the verified command set, or `go.mod` appears/changes `go` line. Does: read `go.mod` (`go` + `toolchain` + `tool` directives), detect `Makefile`/`Taskfile`/CI config, detect golangci config version, record the project's own commands into a `swarm-report/go-commands.md` (or project CLAUDE.md note), report missing tools (golangci-lint, govulncheck) instead of installing them silently. NOT for: non-Go repos; routine edits when commands are already known.
2. `go-new-service` - Invoke when: scaffolding a new service/CLI/library or adding a new binary. Applies R1/R8/R9/R7 skeleton (`cmd/x/main.go` with `run()`, config, slog, graceful shutdown, healthz, errgroup). NOT for: adding a handler to an existing service (use go-http-endpoint).
3. `go-http-endpoint` - Invoke when: adding/changing HTTP routes, middleware, or handlers. Applies R9, R4.12, R5, R17.5-17.6, httptest patterns. NOT for: gRPC, DB-only changes.
4. `go-database` - Invoke when: touching SQL, sqlc config/queries, pgx/pgxpool, migrations or transactions. Applies R10; runs `sqlc generate`/`vet` if present; checks migration compatibility. NOT for: pure in-memory logic.
5. `go-concurrency-review` - Invoke when: code adds goroutines, channels, mutexes, errgroup, worker pools, tickers, or context cancellation paths. Checklist R5/R6; require `-race` run and a synctest/leak test for new background workers. NOT for: single-threaded code.
6. `go-errors-and-logging` - Invoke when: adding error types/wrapping, sentinel errors, or log statements. R4/R7. NOT for: choosing alerting policy.
7. `go-write-tests` - Invoke when: writing/modifying `*_test.go`, fuzz targets, benchmarks, or integration tests. R12, incl. synctest, testcontainers gating, golden files, fuzz. Defers to the user's global complexity policy on whether tests are written at all. NOT for: test plans (generate-test-plan skill).
8. `go-modernize` - Invoke when: bumping the `go` line / toolchain, or code looks pre-1.22 (loop var copies, `interface{}`, `sort.Slice`, `ioutil`). Runs `go fix -diff ./...` first, applies in a separate commit, verifies build+tests. Never changes the go line without a plan-stage note. NOT for: bug fixes (minimal-diff rule).
9. `go-deps` - Invoke when: adding/upgrading/removing a dependency or tool, `go.mod` edits, `replace`, vendoring. Enforces the user's plan-stage gate: identity, freshness (`go list -m -u`/`-versions`), `govulncheck`, API study (`go doc pkg@ver`); never guesses versions. NOT for: stdlib-only changes.
10. `go-release-build` - Invoke when: Dockerfile, Makefile/Taskfile, ldflags, goreleaser, PGO. R15. NOT for: app logic.
11. `go-perf` - Invoke when: asked to optimize or a benchmark regresses. Profile-first workflow R16 (benchmark baseline -> pprof -> change -> `benchstat`). NOT for: speculative micro-optimization.
12. `go-verify` - Invoke when: before declaring a Go task done (feeds the global quality/acceptance gates). Runs the verification command set (B.4), reports concise results. NOT for: running when only docs changed.

### B.2 Agents
- `go-engineer` (builder, run on Sonnet per user policy): implements Go changes; loads the path rules; must run build+vet+scoped tests before returning; may not add deps, flags, or `replace` without approval; keeps diffs minimal; proposes (not applies) refactors.
- `go-reviewer` (read-only; inherits parent model): reviews a diff against R1-R18 prioritising correctness: error handling/wrapping, ctx propagation/leaks, goroutine ownership, tx boundaries, SQL injection, shutdown/timeouts, API stability; reports only real problems (user's code-review rule).
- `go-test-runner` (can reuse global `test-runner`): runs the verification set, parses `go test -json`, returns PASS/FAIL + failing tests; never edits.
- Optional `go-perf-analyst` (read-only + Bash): runs benchmarks/pprof and interprets.

### B.3 Path-scoped rules (short, imperative; each links back to R-numbers)
`**/*.go`:
- gofmt/goimports-clean; `any` not `interface{}`; ctx first, never stored; wrap with `%w` at end, no "failed to"; `errors.Is/As/AsType`; no `panic`/`os.Exit`/`log.Fatal` outside main/init-invariants; no `init()` side effects; interfaces defined in consumer pkg; return structs; goroutines need owner + stop; `slog` with ctx variants, no secrets; parameterized SQL; explicit `http.Server` timeouts; no `http.DefaultClient`/`DefaultServeMux`; `defer cancel()`; `crypto/rand` for secrets; exported symbols have doc comments; do not introduce deps/flags; minimal diff in legacy code.
- Version gates: before using `range int`, `new(expr)`, `WaitGroup.Go`, `AsType`, `B.Loop`, `synctest`, generic methods, check `go.mod` `go` line (compiler enforces; vet `stdversion`).
`go.mod` (and `go.sum`, `go.work`):
- Never edit `go.sum` by hand; changes go through `go get`/`go mod tidy`; no new `require`/`tool`/`replace` without explicit approval + plan-stage gate (user rule); no local-path `replace` committed; do not bump `go`/`toolchain` as a side effect; after edit run `go mod tidy` + `go build ./...` + `govulncheck` (if installed).
`**/*_test.go` (and `testdata/`):
- Table-driven with named subtests; `t.Parallel()` when isolated; `t.Helper()` on helpers; `t.Context/TempDir/Setenv/Cleanup`; no `t.Fatal` in goroutines; failure messages `got/want` with inputs; fakes over mocks; no sleeps - use `synctest`; integration tests behind a tag and via testcontainers; `-race` clean; no `t.Skip` without issue link; goldens in `testdata/` with `-update`; fuzz seeds committed; benchmarks use `b.Loop`.
`**/*.sql`, `sqlc.yaml`, `migrations/**`:
- Parameterized; never edit applied migrations; expand/contract; regenerate sqlc and commit output.
`Dockerfile*`, `Makefile`, `Taskfile*`: R15 (non-root, pinned base, static build, trimpath).

### B.4 Bootstrap / verification command set (stack-agnostic: use the project's own task names first)
Resolution order for each step: (1) the project's documented command (CLAUDE.md, `Makefile`/`Taskfile` target, CI workflow); (2) a repo-pinned tool (`go tool <name>` if in go.mod `tool` directives); (3) a binary on PATH; (4) skip and REPORT "tool missing: X" (never silently pass; never install with sudo).
0. Orient: `go version`; `go env GOTOOLCHAIN GOFLAGS GOWORK`; `head go.mod` (go/toolchain/tool lines); `git status`.
1. Build (L0): `go build ./...` (also `go vet` compiles tests: `go vet ./...`). For a single changed package scope with the package path.
2. Format check: `gofmt -l .` (must print nothing) / formatter via lint tool; fix with the formatter, not by hand.
3. Static analysis (L1): `go vet ./...`; project lint (`golangci-lint run` or the project's `make lint`; if config absent, report and propose the skeleton in R13.2 but do not add silently).
4. Tests (L2, only when the complexity band calls for tests, per user policy): `go test -race -shuffle=on ./...` for the affected packages first, whole module before PR; add `-count=1` when cache masks flakiness; integration via the project's tag (e.g. `-tags integration`) only when Docker is available.
5. Vulnerabilities: `govulncheck ./...` (source) when go.mod/go.sum changed or before release; binary mode on built artifacts.
6. Modernization drift (optional, on `go` bump): `go fix -diff ./...`.
7. Generated code & module hygiene (when relevant): `go generate ./...`, `sqlc generate` (if sqlc.yaml), `go mod tidy`; then `git diff --exit-code -- go.mod go.sum <generated>` to prove clean.
8. Report: pass/fail per step, tool-missing list, and any skipped step with reason.
Scoping rule (user policy): no-logic changes (comments, renames, imports) need only build/vet; logic changes need the affected-package tests with `-race`.

---------------------------------------------------------------------
## C. Decisions where two defensible options exist (log as ASSUMPTION) and unverified items

Decisions made (each: choice - why - how to reverse):
1. No `pkg/` directory - official layout guide never mentions it; `internal/` gives enforced privacy - if an existing repo uses `pkg/`, follow the repo.
2. stdlib `ServeMux` first, no router framework - 1.22 patterns cover method+wildcards; fewer deps - add chi (or similar) only for middleware grouping needs.
3. pgx/v5 + pgxpool as default Postgres driver (over `database/sql`) - richer features, sqlc supports it - use `database/sql` when engine portability/tooling requires.
4. sqlc for CRUD (over ORM, over hand-rolled everywhere) - type safety, SQL-first - hand-written pgx for dynamic queries; ORM only by explicit user choice.
5. `log/slog` only - stdlib, handler ecosystem enough - zap/zerolog if a measured perf need.
6. Fakes over generated mocks; stdlib `testing` + `go-cmp` over testify - Google guidance; if a repo already uses testify/mockery, stay consistent (`testifylint` on).
7. `gofumpt` NOT mandated (gofmt + goimports baseline) - avoids churn in existing repos; recommend for greenfield.
8. Dev tools via go.mod `tool` directive for small tools (stringer, sqlc, govulncheck-style); golangci-lint kept as separately pinned binary/CI action - avoids dependency-graph pollution (this reasoning is [A]; golangci docs page on install not retrievable this session).
9. Linter set in R13.2 and the "off by default" list (wrapcheck, paralleltest, etc.) - judgment on noise vs value.
10. Tests are written only when the user's complexity policy says so (>=7); playbook still describes how - the plugin must defer to that policy rather than mandate tests.
11. Migrations: tool left unspecified (goose / golang-migrate / atlas) - comparison not verified; pick the repo's existing one, else ask/decide with research.
12. json/v2 allowed for new code (shipped in 1.27) but not forced; v1 stays default for existing code - flip when team wants strict defaults.
13. Integration tests gated by build tag `integration` (alternative: `-short` skip or env var) - keeps default `go test ./...` fast; follow repo convention if present.
14. Modernizers (`go fix`) applied in separate commits - preserves minimal-diff rule.
15. Exit codes and CLI framework: cobra vs stdlib `flag` left to repo; Google guide says use `cmd.Context()` with cobra.

Not verified / limits of this research:
- golangci-lint `standard` default linter set contents and exact current v2 settings keys beyond the docs page's structural description; `golangci-lint`, `govulncheck`, `staticcheck`, `sqlc`, `benchstat` are not installed locally, so no config was executed. The sample config in R13.2 is NOT validated by running `golangci-lint config verify`.
- govulncheck binary mode, exit codes, SARIF: stated from knowledge ([M]); the fetched tutorial did not cover them.
- pgx `BeginFunc/BeginTxFunc/CollectRows` helpers: not on the fetched page; confirm with `go doc` / `ksrc`-equivalent after adding the dependency.
- testcontainers-go Postgres module API and per-test isolation strategy: not read.
- Dockerfile practices, ldflags/`-trimpath` details, goreleaser, GOMEMLIMIT, `-gcflags=-m`, benchstat, migration tools: [M], not re-verified this session; verify with a spike (build a sample binary, inspect `go version -m`) before encoding in a hook.
- Go 1.27 `go mod init` writes full current version (observed) vs. 1.26 notes (older minus one): unresolved discrepancy.
- Effective Go and go.dev/doc/comment were not re-fetched; doc-comment rules lean on Google best-practices + Code Review Comments.
- Support-window policy (two latest majors) and the 1.27 `uuid` package scope not independently checked beyond the release notes summary (fetch summarizer output; notes page itself not read verbatim - treat 1.27 details as T1-via-summarizer; spot-check with `go doc` before depending on them. Verified directly by `go doc`: errors.AsType, WaitGroup.Go, synctest, slog.NewMultiHandler, context.WithoutCancel/AfterFunc/WithCancelCause, testing.T.Context, testing.B.Loop, os.Root, http.CrossOriginProtection, ServeMux patterns).
- Tools used: WebFetch (go.dev, pkg.go.dev, golangci-lint.run, GitHub raw/api, docs.sqlc.dev, testcontainers), local `go` toolchain (`go doc`, `go vet help`, `go tool fix help`, spike build). Context7 and other docs MCPs were not queried (none surfaced via ToolSearch for this task); WebSearch was not used. Reduced channel breadth: single-channel for most T2 claims.
