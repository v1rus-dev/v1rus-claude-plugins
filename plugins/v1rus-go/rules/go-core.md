---
paths:
  - "**/*.go"
---

# Go code conventions

Marker: (advisory) = judgment call, not machine-checkable. Everything else is checked by build/vet/lint.

## Style and layout
- Code is `gofmt`/`goimports`-clean; fix with the formatter, never by hand.
- Check the `go` line in `go.mod` before using newer language/stdlib features (`range` over int and per-iteration loop vars need 1.22+, iterators 1.23+, `testing.B.Loop` 1.24+, `sync.WaitGroup.Go` and `testing/synctest` 1.25+, `errors.AsType` and `new(expr)` 1.26+, generic methods 1.27+). The compiler and vet `stdversion` enforce it; do not raise the `go` line as a side effect.
- Use `any`, not `interface{}`; prefer `slices`, `maps`, `cmp`, `strings.Cut*` over hand-written helpers.
- Package names: short, lowercase, singular, no underscores; no `util`/`common`/`helper`. No stutter (`orders.Service`, not `orders.OrdersService`); no `Get` prefix on getters; initialisms keep case (`userID`, `URL`).
- Every exported identifier has a doc comment starting with its name. Document concurrency safety, cleanup duties (`Close`, `Cancel`) and returned error values when not obvious.
- Avoid `init()` with side effects and mutable package-level state; inject dependencies through constructors.
- `os.Exit` and `log.Fatal` only in `main`; `main` stays thin and calls `run(ctx, args) error`.
- Do not shadow predeclared or stdlib names (`error`, `len`, `url`).
- Legacy code: keep its style when touching it (minimal diff); new code follows this file. Repos that already use `pkg/` or testify keep them.

## Interfaces and API (advisory)
- Accept interfaces, return concrete types. Define small interfaces (1-3 methods) in the consumer package, only once a second implementation or consumer exists; not "for mocking" next to the implementation.
- Compile-time check where required: `var _ http.Handler = (*Handler)(nil)`. Always comma-ok on type assertions. Never pointer-to-interface.
- Pointer receivers when mutating, holding a mutex or large; do not mix receiver kinds on one type.
- Make the zero value useful. Return a `nil` slice, not `[]T{}`, unless JSON must emit `[]`. Copy slices/maps at API boundaries when retaining or returning internal state.
- Functional options only when most callers pass none or options can fail; otherwise a config struct. Never put `ctx` in options. No naked `bool` parameters.
- Generics for containers and algorithms over many element types; not for single-implementation behavior (use an interface).
- `time.Duration`/`time.Time` in APIs, never raw ints.

## Errors
- Handle an error once: return it with context OR log it, never both.
- Wrap with `fmt.Errorf("load config %q: %w", path, err)`: lowercase, no trailing punctuation, no "failed to"; add context only when it adds information; `%w` last.
- `%w` when callers may inspect the cause; `%v` at API/storage boundaries where the cause must stay opaque.
- Inspect with `errors.Is` / `errors.As` / `errors.AsType`; never `==` on wrapped errors or matching on `err.Error()`. Never `%w`-wrap a pointer to an error type (vet flags it).
- Sentinel (`ErrFoo`) for one condition callers branch on; typed (`FooError`) when callers need data; otherwise plain `fmt.Errorf`. Export only what callers must match.
- No `panic` for expected failures; panic only for programmer errors and init-time invariants (`regexp.MustCompile` on constants). Never let a panic cross a public API.
- Never discard an error with `_` unless documented why; check `Close` errors on written files.
- Map errors to HTTP/gRPC status once, at the transport edge (advisory).

## Context
- `ctx context.Context` is the first parameter of anything that does I/O or may block; never stored in a struct, never nil. `context.Background()` only in `main`, init and tests.
- `defer cancel()` right after `WithCancel`/`WithTimeout`/`WithDeadline`.
- `ctx.Value` only for request-scoped data with an unexported key type, never for optional parameters or dependencies.
- Outbound calls carry the context (`NewRequestWithContext`, `QueryContext`, gRPC calls). In tests use `t.Context()`.

## Logging and secrets
- `log/slog` with key/value attrs and the `*Context` variants; pass `*slog.Logger` through constructors in libraries. Do not add another logging library to new code.
- Never log secrets, tokens, DSNs, full request/response bodies or whole config structs; give secret-bearing types a `slog.LogValuer` that redacts.
- Randomness for secrets/tokens from `crypto/rand`, not `math/rand`.
- Queries are parameterized; never build SQL, shell commands or HTML with string formatting.
- Do not add dependencies or feature flags without approval; see the `go-deps` skill.
