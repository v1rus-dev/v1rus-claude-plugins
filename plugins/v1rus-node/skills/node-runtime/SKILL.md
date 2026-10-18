---
name: node-runtime
description: "The Node process a v1rus service actually runs in: what blocks the single event loop (sync crypto, sync fs, large JSON, catastrophic regex) and how to measure the delay rather than guess, moving CPU-bound work to worker threads or a queue, streams with pipeline and real backpressure instead of buffering a whole payload, AbortSignal threaded from the incoming request down to every downstream call and timeout, graceful shutdown that stops accepting, drains in-flight work, closes resources in the right order and stays inside the orchestrator grace period, unhandled rejections and uncaught exceptions as crash-and-restart rather than log-and-continue, and process-level sizing (replicas over cluster, heap limit versus container limit, keep-alive timeouts). Load when writing main.ts, adding a long-running or CPU-heavy operation, handling uploads or large payloads, wiring cancellation, diagnosing latency spikes or restarts, or configuring shutdown."
---

# The Node Runtime

One thread runs all your JavaScript. Every rule here follows from that, plus the fact that the
process will be killed on the next deploy whether or not it is ready.

## Blocking the event loop

A synchronous operation does not slow down the request that called it — it stops **every** in-flight
request, the health probe, and the heartbeat to the queue. The usual offenders:

| Blocking | Instead |
|---|---|
| `crypto.scryptSync`, `pbkdf2Sync`, `bcrypt.hashSync` | the async form; password hashing is always async |
| `fs.readFileSync`, `fs.writeFileSync` on a request path | `fs/promises`, or a stream |
| `JSON.parse` / `JSON.stringify` of a multi-megabyte payload | bound the size at the edge; stream with a streaming parser for genuinely large data |
| `zlib.gzipSync` | the async form, or let the proxy compress |
| `execSync`, `spawnSync` | `execFile` with a timeout — and reconsider the shell-out |
| a regex with nested quantifiers over user input | a bounded pattern, or a parser; this is ReDoS |
| `for (const x of big) await one(x)` | batch the query, or `Promise.all` with a bounded concurrency |

**Measure before believing.** `monitorEventLoopDelay` from `perf_hooks` gives a histogram; a p99 loop
delay in the tens of milliseconds means something synchronous is running, and the next step is a CPU
profile (`--cpu-prof`, or the inspector), not a guess. "It is probably the database" is the wrong
default when the database client is asynchronous and the hashing is not.

CPU-bound work that legitimately has to happen in this process goes to a **worker thread** (a pool,
not a thread per task — spawning one costs milliseconds and a few megabytes). Work that does not
have to be in the response path goes to a **queue job** (`node-background-jobs`), which is usually
the better answer because it also gets retries and backpressure for free.

## Streams and backpressure

```ts
import { pipeline } from 'node:stream/promises';

await pipeline(request, createGunzip(), parser, writeTarget, { signal });
```

- **`pipeline`, never `a.pipe(b)`.** `pipe` does not propagate errors and does not destroy the
  source on failure: the handle leaks and the error surfaces as an unhandled `'error'` event that
  takes the process down.
- Never buffer an upload, a download, an export or a report into memory to return it. Stream it, and
  bound what you accept — a request body limit, a row limit, a maximum result size. "It is only a
  CSV" is true until a client posts a 2 GB one and the pod is OOM-killed.
- Backpressure is the point of streams: `write()` returning `false` means stop and wait for
  `'drain'`. `for await (const chunk of source)` respects this; a loop that calls `write()` and
  ignores the return value buffers the entire source in memory and reproduces the problem streams
  exist to solve.
- Close what you open, including on the error path — `pipeline` does this, hand-rolled plumbing does
  not.

## Cancellation

A client that hung up should stop costing you a database connection and an upstream call.

- Thread an `AbortSignal` from the request down: `AbortSignal` into `fetch`, into the repository
  method, into the job enqueue. The shape and composition of signals (`AbortSignal.any`,
  `AbortSignal.timeout`) belong to `v1rus-typescript:ts-async`; the wiring is here.
- **Every outbound call gets a timeout.** A `fetch` with no signal waits until the socket dies —
  minutes — holding a handler, a connection and, if you were careless, a transaction.
- An abort is an expected outcome. Log it at `debug`, do not count it as an error rate, and do not
  turn it into a 500 for a client that is no longer listening.
- Do not thread a cancellation signal into work that must not be half-done. Cancelling between two
  writes is exactly the state a transaction exists to prevent (`node-persistence`).

## Graceful shutdown

The container gets SIGTERM and then, after the grace period, SIGKILL. What has to happen in between:

1. **Fail readiness immediately** so the load balancer stops sending new requests. Liveness keeps
   passing — you are shutting down on purpose, not stuck (`node-observability`).
2. **Stop accepting new work**: close the HTTP listener to new connections, pause queue workers.
3. **Drain**: let in-flight requests and jobs finish, bounded by a timeout.
4. **Close resources in dependency order**: queue workers and schedulers first, then the database
   pool, then the logger flush. Closing the database while a job is mid-transaction is a corrupt
   outcome that the graceful path was supposed to avoid.
5. **Exit**, and force-exit if the drain timeout expires.

In Nest that is `app.enableShutdownHooks()` in `main.ts` plus `onModuleDestroy` on every provider
holding a resource. **Without `enableShutdownHooks` none of the hooks run** — the most common cause
of "we lose a handful of requests on every deploy".

Two numbers must agree: the drain timeout must be **shorter** than the orchestrator's
`terminationGracePeriodSeconds`, or the graceful path is cut off by SIGKILL and never completes. A
`preStop` sleep of a few seconds before SIGTERM covers the window where the load balancer has not yet
noticed the readiness change.

## Process-level failure

```ts
process.on('unhandledRejection', (reason) => { logger.fatal({ err: reason }, 'unhandled rejection'); shutdown(1); });
process.on('uncaughtException', (err) => { logger.fatal({ err }, 'uncaught exception'); shutdown(1); });
```

- Both mean **unknown state**. Log with full context, attempt the shutdown sequence with a short
  timeout, exit non-zero, let the supervisor restart. A handler that logs and continues keeps serving
  from a process that has already failed in a way you did not model.
- `process.exit()` truncates pending I/O — including the log write that would explain the exit. Let
  the event loop drain, or use the logger's flush before exiting.
- `process.exit()` belongs to the composition root. In a service or repository it is a library
  calling `exit` on its host.
- A `setInterval` that should not keep the process alive is `unref()`'d, and is cleared in
  `onModuleDestroy` regardless.

## Sizing the process

- **Replicas over `cluster`.** In a container, one process per container and N containers gives the
  orchestrator the scheduling, the health checking and the rolling restart. `cluster` inside a
  container hides all three behind a primary process that the platform cannot see into.
- The V8 heap limit and the container memory limit are **different numbers**, and the default heap
  limit is not derived from a cgroup limit in every runtime version. Set `--max-old-space-size`
  below the container limit, or the OOM killer arrives before V8 ever runs a full GC — and an
  OOM-killed container leaves no stack trace.
- Set `server.keepAliveTimeout` above the load balancer's idle timeout, and `headersTimeout` above
  that. The reverse produces intermittent 502s that look random because they only happen on a reused
  connection the server closed first.
- Do not disable TLS verification, ever, including "temporarily to test something" —
  `NODE_TLS_REJECT_UNAUTHORIZED=0` is process-wide and outlives the test.
