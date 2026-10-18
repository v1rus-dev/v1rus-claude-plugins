# Errors and logging detail

Errors
- Layers: wrap with operation context at layer boundaries, not at every frame; Go has no stack traces by convention, rely on message chains plus structured logs (advisory).
- Choose per condition: sentinel for a single branchable condition, typed error for data, otherwise plain wrap. Typed errors use pointer receivers and an `Error` suffix; sentinels an `Err` prefix.
- Several errors: `errors.Join` or multiple `%w` in `fmt.Errorf`; `errors.Is/As/AsType` traverse them.
- `errors.AsType[E]` (1.26+) is the type-safe alternative to `errors.As`; check with `go doc errors.AsType`.
- Panics: recover only at defined boundaries and convert to errors; `net/http` already recovers per request, add logging not silent swallowing.
- Do not leak driver or internal error types through a public contract: wrap with `%v` or translate.

Logging (`log/slog`)
- Levels: Debug developer detail (off in production); Info lifecycle/business events; Warn recoverable anomaly; Error actionable failure.
- Typed `slog.Attr` with `LogAttrs` in hot paths; stable key names; derive loggers with `With`/`WithGroup`; use `InfoContext` etc. so handlers can read request/trace IDs from the context.
- Vet `slog` flags mismatched key/value arguments; `sloglint` can enforce a style when the repo uses golangci-lint.
- Redaction: `slog.LogValuer` on secret-bearing types, and key-based `ReplaceAttr` scrubbing in the handler setup for `password`, `token`, `authorization` (the `ReplaceAttr` details were not re-verified: check `go doc log/slog.HandlerOptions`).
- Libraries do not configure global logging; they accept a `*slog.Logger` or log nothing. Applications call `slog.SetDefault` at most once in `main`.
- Multiple sinks: `slog.NewMultiHandler` (1.26+).
- Temporary diagnostics follow the user's `// TEMP-LOG` convention and are removed before finishing.
