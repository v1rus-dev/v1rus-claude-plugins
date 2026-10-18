---
name: node-observability
description: "Making a v1rus Node service debuggable in production: pino structured JSON logging behind the Nest logger with one logger for the process, a correlation id generated or accepted at the edge and carried through AsyncLocalStorage into every log line, downstream call and queue job, redaction of tokens and PII configured on the logger rather than remembered at each call site, logging an error exactly once at the boundary, one request log line at the edge instead of a trace per layer, liveness versus readiness probes and why a dependency check belongs only in readiness, terminus health indicators, and where OpenTelemetry tracing and metrics fit. Load when adding logging, wiring request context or correlation ids, configuring redaction, adding health or readiness endpoints, instrumenting an investigation, or reviewing what a service reveals and records."
---

# Observability

The corporate logging policy — permanent versus temporary logs, the `// TEMP-LOG` convention, level
semantics, what must never be logged — is `v1rus-core:v1rus-logging`. This skill is the Node and
Nest mechanics that policy needs.

## One structured logger

**pino** is the default: it serialises to JSON on a worker thread and costs roughly nothing at
`info`. Wire it as Nest's logger (`nestjs-pino` or a `LoggerService` adapter) so framework logs and
application logs share one stream, one format and one destination.

- **JSON always, in every environment that ships logs anywhere.** Pretty-printing is a local
  development transport, never the production format — a log aggregator cannot query a formatted
  string.
- `console.log` is banned. It is unstructured, unleveled, synchronous to a pipe, and invisible to
  redaction.
- **Log objects, not interpolated strings**: `logger.info({ orderId, status }, 'order placed')`, not
  `` logger.info(`order ${orderId} placed`) ``. The first is queryable; the second is a regex
  problem for whoever is on call.
- The `err` key is special to pino's serializer and produces the message, type and stack. Pass the
  error as `{ err }`, not as `error.message`, or the stack is gone at the moment it is needed.

## Correlation id

```ts
// edge middleware
const correlationId = req.headers['x-correlation-id'] ?? randomUUID();
requestContext.run({ correlationId, userId: req.user?.id }, () => next());
```

- Accept an inbound id when a caller supplies one, generate one otherwise, and **echo it in the
  response header** so a client can quote it in a bug report.
- Carry it in `AsyncLocalStorage`, not by threading a parameter through twenty signatures and not by
  making providers request-scoped (`nest-di`). A logger `mixin` reads the store, so every line
  carries the id without any call site remembering to add it.
- **Propagate it outward too**: as a header on every downstream HTTP call, and as a field in every
  queue job payload, so a job's logs join the request that enqueued it
  (`node-background-jobs`). A correlation id that stops at the process boundary answers half the
  question.
- When OpenTelemetry is in play, the trace id is the correlation id — do not maintain two. Put
  `trace_id` and `span_id` on every log line so logs and traces cross-reference.

## Redaction

Configure it **on the logger**, where it cannot be forgotten:

```ts
pino({
  redact: {
    paths: ['req.headers.authorization', 'req.headers.cookie', '*.password', '*.token', '*.ssn', 'req.body.card'],
    censor: '[redacted]',
  },
});
```

- Redaction is the second line of defence. The first is not logging it: **never log a whole request
  body, a whole user object or a whole external response**. Log the two fields you actually need.
- Tokens, authorization headers, cookies, passwords, card data, national ids, precise location and
  full email addresses do not go to logs. Log a user id, not a user.
- Auto-instrumentation libraries log request bodies and headers by default — check what the HTTP
  logger is configured to capture before shipping it.
- The same applies to span attributes, error messages and the exception-filter response
  (`nest-error-handling`).

## Levels and volume

| Level | Means |
|---|---|
| `fatal` | the process is going down |
| `error` | a request or job failed for a reason nobody expected — someone should look |
| `warn` | a handled, expected failure worth counting (a 4xx, a retry, a fallback) |
| `info` | a business-meaningful event, low volume: request completed, job finished, state transition |
| `debug` | diagnostics, off in production by default, enabled by config without a redeploy |

- **One request log line, at the edge**, with method, route (the *route template*, not the URL with
  ids in it), status, duration and correlation id. A log line per layer multiplies volume by four
  and adds nothing that the one line plus the error does not already say.
- **An error is logged once**, where it is handled — the exception filter for a request, the job's
  error handler for a job. `catch → log → rethrow` at every layer produces four stack traces per
  failure.
- Do not log inside a loop over a user-sized collection. One summary line with a count.

## Health and readiness

Two endpoints, different questions, and conflating them is the outage:

| Endpoint | Question | Checks |
|---|---|---|
| `/health/live` | is this process alive and should the orchestrator *not* restart it? | in-process only — the event loop is responsive. **No dependency checks.** |
| `/health/ready` | should this instance receive traffic right now? | the database, the queue connection, any hard dependency, plus the shutting-down flag |

**A dependency check in liveness is a self-inflicted outage**: the database has a hiccup, every
replica fails liveness, the orchestrator restarts all of them at once, and now there is a thundering
herd on a database that was about to recover. Liveness answers "is this process wedged", nothing
more.

Readiness must **fail first during shutdown**, before draining begins, or the load balancer keeps
routing to a process that is closing (`node-runtime`). It should also fail during startup until
migrations and warm-up are done.

`@nestjs/terminus` provides the indicator plumbing; keep each check cheap (`SELECT 1`, a ping),
timeboxed, and cached for a second or two so a probe every second does not become load.

## Metrics and tracing

- **RED at minimum** on the HTTP surface — rate, errors, duration — plus queue depth and job
  outcomes, and the event-loop delay histogram (`node-runtime`). Label by route template and status
  class; labelling by raw URL or by user id is how a metrics backend falls over on cardinality.
- Tracing is OpenTelemetry, initialised **before** anything else in the process so
  auto-instrumentation can patch the libraries — that means a separate file imported first in
  `main.ts`, not a provider.
- Sample: head-based sampling at a low rate for normal traffic, always-on for errors. 100% tracing
  of a busy service costs more than the service.
- Instrumenting an investigation is temporary logging and follows the `// TEMP-LOG` convention in
  `v1rus-core:v1rus-logging` — it is removed before the quality gate, not left behind "in case".
