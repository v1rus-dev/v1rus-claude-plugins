---
name: node-conventions
description: "NestJS and Node runtime rules a model omits by default: exporting only what other modules may use and treating forwardRef as a defect marker, constructor injection with singleton scope and the scope-bubbling cost of Scope.REQUEST, controllers that map rather than think, a ValidationPipe that strips unknown properties instead of passing them through, never returning a persistence model from a handler, process.env read only in the config module, no console logging, enableShutdownHooks in main.ts, no synchronous CPU work on a request path, pipeline over pipe for streams, transactions that cover the whole invariant and hold no network call, and crashing rather than continuing on an unhandled rejection. Load when writing or reviewing NestJS or Node backend code, or when a review needs the rules without performing an edit that would inject them."
---

# Node and NestJS Conventions

Two rulebooks, both single-source:

- **`${CLAUDE_PLUGIN_ROOT}/rules/nestjs.md`** — modules, providers, controllers, guards and
  interceptors, filters, configuration and logging, `main.ts`.
- **`${CLAUDE_PLUGIN_ROOT}/rules/node-runtime.md`** — the event loop, streams and backpressure,
  cancellation, graceful shutdown, process-level failure, data access.

**Read them** before writing or reviewing non-trivial backend code. This plugin's `path-rules` hook
injects each one automatically just before an edit to a file its globs match (`*.module.ts`,
`*.service.ts`, `*.controller.ts`, `*.guard.ts`, `*.interceptor.ts`, `*.filter.ts`, `*.pipe.ts`,
`*.resolver.ts`, `main.ts` for the first; `main.ts`, `*.worker.ts`, `*.job.ts`, `*.processor.ts`,
`*.repository.ts`, `*.datasource.ts` for the second), so while writing code they are usually already
in context. Read them directly when reviewing — a review performs no edit and triggers no injection.

They document only what a modern model gets wrong without a reminder. Generic TypeScript is not
there: type discipline, ESM and `exports` maps, floating promises and `AbortSignal` shape, and the
lint configuration all belong to `v1rus-typescript`.

The five that cause production incidents:

- **`ValidationPipe` without `whitelist: true`** validates the fields you declared and forwards every
  field you did not. `{ email, isAdmin: true }` passes.
- **Returning a Prisma model or an entity from a handler** publishes every column anyone adds to that
  type later, on the day they add it, with no failing test.
- **No `app.enableShutdownHooks()`** means `onModuleDestroy` never runs, so every deploy kills
  in-flight requests and leaves jobs mid-transaction.
- **One `Scope.REQUEST` provider** makes its entire injection chain request-scoped, up to and
  including the controller.
- **Synchronous CPU work on a request path** — `scryptSync`, `readFileSync`, a huge `JSON.parse` —
  stalls every concurrent request, not just its own.

Related: `nest-architecture` (layers and modules), `nest-di` (providers and scopes), `nest-http-api`
(controllers, DTOs, validation), `nest-error-handling` (`DomainError` and the problem response),
`node-persistence` (Prisma, transactions, pool), `node-configuration` (env and secrets),
`node-runtime` (event loop, shutdown), `node-observability` (logging, probes),
`node-background-jobs` (queues), `node-testing` (tests), and `v1rus-core:v1rus-logging` for the
logging policy itself.
