# Go database access

Defaults for new Postgres code (a preference, not a mandate; follow the repo): `pgx` v5 with `pgxpool`; `database/sql` only when engine portability or a tool requires it. Module paths and versions come from the project's `go.mod` or `go list -m`; study the API with `go doc <pkg>@<version>` before use (names of helpers such as `BeginFunc`, `CollectRows` must be confirmed this way, they were not verified when this document was written).

Queries: sqlc for the bulk of CRUD, hand-written pgx for dynamic or analytical queries; always parameterized. Generated code is committed; CI-style check: `sqlc generate` then `git diff --exit-code`. Option choices (advisory): pointers for nullable columns, no JSON tags on DB structs (map to API types explicitly), overrides for uuid/timestamptz/numeric.

Pool: configure from `ParseConfig` (max/min conns, lifetimes, idle time, health-check period); size max connections against the database limit and replica count. The pool does not connect at creation: ping at startup to fail fast. Close the pool after the HTTP server has shut down. Set statement/lock timeouts per connection or transaction (advisory).

Transactions: services own transaction boundaries (a helper such as `Tx(ctx, func(q) error)`), repositories do not. Always `defer tx.Rollback(ctx)` (safe after commit); context cancellation does not roll back by itself. Keep transactions short with no network calls inside. Retry only on serialization/deadlock failures (SQLSTATE 40001/40P01), bounded, with idempotent bodies.

`database/sql` specifics: set max open/idle conns and conn lifetime; `rows.Close()` and check `rows.Err()`; `QueryRowContext(...).Scan`.

Migrations: versioned, forward-only SQL in the repo's tool and directory; applied by a separate job or command, not implicitly by every instance at boot unless the service is single-instance; never edit applied migrations; expand/contract for zero downtime.

Tests: a real Postgres (testcontainers or a CI service), not SQL mocks; one container per package via `TestMain`, isolation per test by schema, transaction or template database; gate behind a build tag.

Performance: batching (`pgx.Batch`, `CopyFrom`), indexes and N+1 fixes before micro-optimizations.
