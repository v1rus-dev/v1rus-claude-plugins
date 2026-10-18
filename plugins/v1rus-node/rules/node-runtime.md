---
paths:
  - "**/main.ts"
  - "**/*.worker.ts"
  - "**/*.job.ts"
  - "**/*.processor.ts"
  - "**/*.repository.ts"
  - "**/*.datasource.ts"
---

# Node runtime — rules for this file

The process is single-threaded and shared by every concurrent request. Everything below is about
that fact. Async correctness at the language level — floating promises, `AbortSignal` shape, `Error`
`cause` — belongs to `v1rus-typescript:ts-async` and `v1rus-typescript:ts-error-handling`.

## Do not block the event loop

- **No synchronous CPU work on a request path.** `crypto.scryptSync`, `pbkdf2Sync`, `bcrypt.hashSync`,
  `zlib.gzipSync`, `fs.readFileSync`, `execSync` and a `JSON.parse` of a multi-megabyte payload each
  stall *every* in-flight request, not just the one that called them. Use the async variant; hashing
  a password is `scrypt`/`argon2` async, not its `*Sync` twin.
- Genuinely CPU-bound work (image processing, large parsing, report generation) goes to a
  **worker thread** or a queue job, not to the request handler.
- A regex over user input needs a bounded shape. Nested quantifiers over an attacker-controlled
  string is a denial of service with no network traffic behind it.
- Iterating a large collection with `await` inside is both slow and an N+1: batch the query, or bound
  the concurrency deliberately — never fire an unbounded `Promise.all` over a user-sized array.

## Streams and backpressure

- Pipe with `stream.pipeline` (or `pipeline` from `node:stream/promises`), never `a.pipe(b)`:
  `pipe` does not forward errors and does not destroy the source, so a failed write leaks the handle.
- Never buffer a whole upload, download or export into memory to "just return it". Stream it, and
  bound what you accept (body size limit, row limit) — a 2 GB request body is a restart.
- Honour backpressure: `write()` returning `false` means wait for `drain`. An async iterator over a
  stream does this for you; a `for` loop calling `write()` does not.

## Cancellation

- A request that the client abandoned should stop costing money. Thread an `AbortSignal` from the
  request through to the downstream `fetch`, the query and the job enqueue, and treat an abort as a
  normal outcome — not as an error to log at `error` level.
- Every outbound call gets a timeout. A `fetch` with no signal and no timeout hangs until the socket
  dies, holding a handler and a connection with it.

## Graceful shutdown

- SIGTERM means: stop accepting new work, let in-flight work finish, close resources, exit. In Nest
  that is `app.enableShutdownHooks()` plus `onModuleDestroy` on everything holding a resource —
  HTTP server, database pool, queue workers, schedulers, open streams.
- Order matters: stop the queue workers and mark readiness failed **before** closing the database, or
  in-flight jobs die mid-transaction.
- Bound the drain with a timeout and force-exit after it, and keep that timeout **below** the
  orchestrator's grace period — a drain longer than `terminationGracePeriodSeconds` is a SIGKILL and
  the graceful path never ran.

## Process-level failure

- `unhandledRejection` and `uncaughtException` are not recoverable states. Log with full context,
  then exit non-zero and let the supervisor restart — a process that keeps serving after an unknown
  exception serves from corrupt state. Never register a handler that only logs and continues.
- `process.exit()` is for the composition root. In a service or repository it truncates pending I/O,
  including the log write that would have explained the exit.
- A `setInterval` that must not hold the process open is `unref()`'d, and is cleared in
  `onModuleDestroy` either way.

## Data access

- A transaction covers **the whole invariant**, not one of the two writes that must agree. If a
  failure between two statements leaves the system in a state no reader should ever see, they are one
  transaction.
- Nothing slow happens inside a transaction — no HTTP call, no queue publish waiting on a broker, no
  user interaction. A transaction holds a pooled connection and a lock; a 3-second external call
  inside one is how a 10-connection pool deadlocks under 11 concurrent requests.
- **Connection pool size is a budget, not a default.** pool size × replica count must stay under the
  database's own limit, and every long-lived transaction removes a connection from that budget.
- Fetch what you need: a loop of `findUnique` is an N+1 — use one `findMany` with an `in` filter, or
  the ORM's relation loading, and select the columns you actually return.
- Persistence types stay behind the repository. A Prisma model, a row object or a driver-specific
  error does not travel into the application or domain layer (`node-persistence`).
