# v1rus-node

The Node.js backend layer — NestJS on TypeScript. Depends on `v1rus-typescript`, which depends on
`v1rus-core`, so installing it pulls the language layer and the corporate baseline with it.

```
/plugin install v1rus-node@v1rus
```

## The stack this plugin standardises

| Concern | Decision |
|---|---|
| Framework | **NestJS** — one module per feature, with `api` / `application` / `domain` / `infrastructure` as folders inside it, not as four Nest modules |
| Dependency direction | `api → application → domain ← infrastructure`; `domain` imports nothing framework-shaped, ports live there, infrastructure implements them |
| DI | Constructor injection, **singleton scope by default**; ports injected by `Symbol` token; `Scope.REQUEST` only where its bubbling cost is stated; request data through an `AsyncLocalStorage` context |
| HTTP input | DTO classes + `class-validator` behind a global `ValidationPipe` with `whitelist` and `forbidNonWhitelisted` — unknown properties are **stripped and rejected**, not forwarded. In a repository that also ships a web app the shared contract schema validates the endpoints that app consumes instead (`nest-http-api`, `v1rus-fullstack:api-contract`) |
| HTTP output | Explicit response DTOs. A Prisma model or a domain entity never leaves a handler |
| Versioning | URI versioning enabled from day one, versioned at the controller |
| Errors | Typed `DomainError` subclasses thrown by the domain; one exception filter maps them to RFC 9457 `application/problem+json` with a stable `code` and the correlation id. No stack, no driver text, no internal message on the wire |
| Persistence | **Prisma** behind a repository boundary; `migrate deploy` in every deployed environment, `db push` never; transactions cover the whole invariant and hold no network call |
| Configuration | The environment parsed and validated **once at startup**, failing the boot; typed config namespaces injected; `process.env` appears only in `src/config/` |
| Runtime | No synchronous CPU work on a request path; `stream.pipeline` and real backpressure; `AbortSignal` threaded from the request down; `enableShutdownHooks` with an ordered drain; an unhandled rejection crashes the process |
| Observability | **pino** JSON logs behind the Nest logger, a correlation id in `AsyncLocalStorage` propagated to downstream calls and jobs, redaction configured on the logger, `/health/live` (in-process only) separate from `/health/ready` |
| Background work | **BullMQ**, idempotent handlers, bounded retries with a dead-letter, the transactional outbox for write-then-publish |
| Tests | **Vitest** (Jest where a project already uses it) + `supertest` e2e against the real app + a **Testcontainers** Postgres for anything touching the database |

**No versions are pinned anywhere in this plugin.** Package names only; the version is resolved at
plan time through the `v1rus-core:v1rus-dependencies` gate.

## What this layer does NOT own

The repository's rule is that a rule lives on the highest layer where it is still true, and is never
copied into two layers. So:

| Not here | Where |
|---|---|
| tsconfig strictness and ESM, `any` / `unknown` / discriminated unions / branded types, schema validation at I/O boundaries as a principle, `Error` + `cause` and `Result`-vs-throw as a principle, floating promises and `AbortSignal` shape, package `exports` maps, the flat ESLint config | `v1rus-typescript` |
| pnpm workspaces and turborepo, sharing API types with a frontend, cross-seam e2e, splitting environment between apps | `v1rus-fullstack` |
| Anything React or Next | `v1rus-react` |
| Gates, complexity bands, review agents, the feature pipeline, logging policy, the dependency gate | `v1rus-core` |

This plugin references those by plugin-qualified skill name rather than restating them.

## Contents

| Component | What it covers |
|---|---|
| `skills/nest-architecture` | Feature modules, the four inner layers and the dependency rule, `providers` vs `exports`, cross-feature communication, resolving circular modules instead of `forwardRef`, dynamic modules, adding a feature |
| `skills/nest-di` | Constructor injection, ports through tokens, the four provider forms, scopes and the scope-bubbling trap, `AsyncLocalStorage` instead of request scope, lifecycle hooks, `ModuleRef` as a last resort, `overrideProvider` by token |
| `skills/nest-http-api` | Thin controllers, the validation pipe that strips, the implicit-conversion trap, explicit response DTOs, date/`Decimal`/`BigInt` on the wire, pagination envelopes, versioning, pipeline order, the `@Res()` escape hatch, security defaults, OpenAPI |
| `skills/nest-error-handling` | The `DomainError` hierarchy, one filter owning the wire format, the RFC 9457 shape, what must never leak, mapping driver errors at the infrastructure boundary, throw vs `Result`, logging exactly once |
| `skills/node-persistence` | The repository boundary and mappers, schema conventions, `migrate dev` vs `deploy` vs never `db push`, expand/backfill/contract, transactions, N+1 and over-fetching, connection-pool budget, `P2002` instead of check-then-insert, `Decimal`/`BigInt` serialization, `null` vs `undefined` in updates |
| `skills/node-configuration` | Fail-fast env validation, typed config namespaces, why a scattered `process.env` read is a defect, secrets and `.env.example`, `NODE_ENV` pitfalls, config in tests |
| `skills/node-runtime` | What blocks the event loop and how to measure it, worker threads, `pipeline` and backpressure, cancellation and timeouts, the five-step graceful shutdown and the grace-period arithmetic, crash-on-unhandled-rejection, replicas over `cluster`, heap vs container limit, keep-alive timeouts |
| `skills/node-observability` | pino as the Nest logger, correlation id in `AsyncLocalStorage` and propagated outward, redaction on the logger, level semantics and one request line, liveness vs readiness and why a dependency check in liveness is an outage, metrics and OpenTelemetry |
| `skills/node-background-jobs` | What belongs in a job, id-not-object payloads validated on entry, at-least-once and idempotency, retries and the dead-letter, the transactional outbox, concurrency and lock renewal, scheduling with replicas, worker process shape and drain |
| `skills/node-testing` | Vitest and the decorator-metadata caveat, constructing services directly instead of a testing module, overriding by token, supertest against the real app including the error contract, Testcontainers Postgres and migrate-then-truncate, job idempotency tests, what not to test |
| `skills/node-conventions` | Front door to `rules/nestjs.md` and `rules/node-runtime.md` for read-only and review contexts |
| `skills/node-pipeline-profile` | The stack profile that gives the `v1rus-core` feature pipeline its Node vocabulary |
| `skills/node-mvp-blueprint` | The `/mvp-init` blueprint for this stack: the `nest new` bootstrap, the MVP-sized `src/` layout, the baseline package set by role, the app skeleton and its first vertical slice, and the generated project `CLAUDE.md` |
| `rules/nestjs.md` | Injected before editing a module, service, controller, resolver, guard, interceptor, filter, pipe or `main.ts` |
| `rules/node-runtime.md` | Injected before editing `main.ts`, a worker, a job, a processor, a repository or a datasource |
| `agents/node-engineer` | Writes modules, the API surface, application and domain logic, Prisma, config, jobs, runtime wiring + tests. No UI. |
| `agents/test-runner` | Runs generate → migrate → typecheck → lint → unit → e2e; reports PASS/FAIL. Never edits code. |

### A note on the path-rule globs

Path-scoped rules are delivered by the `path-rules.py` hook, which matches a rule's `paths:` globs
against the file about to be edited. In a fullstack monorepo both `v1rus-node` and `v1rus-react` may
be installed, and a glob of `**/*.ts` from either layer would fire on the other's files — a React
hook would receive the NestJS rulebook, and a repository would receive the React one.

So this layer's globs are **file-suffix-scoped**, never language-scoped: `**/*.module.ts`,
`**/*.service.ts`, `**/*.controller.ts`, `**/*.resolver.ts`, `**/*.guard.ts`, `**/*.interceptor.ts`,
`**/*.filter.ts`, `**/*.pipe.ts`, `**/main.ts` for the NestJS rulebook, and `**/main.ts`,
`**/*.worker.ts`, `**/*.job.ts`, `**/*.processor.ts`, `**/*.repository.ts`, `**/*.datasource.ts` for
the runtime one. Language-wide TypeScript rules belong to `v1rus-typescript`, which owns that
surface for both backends and frontends. Keep any rule added here suffix-scoped for the same reason.

## Design notes

**Why Prisma and not TypeORM.** Prisma generates a typed client from one schema file, so the query
result type is derived from the query rather than declared by hand — a `select` that drops a column
changes the type, and the compiler finds the code that still reads it. Migrations are plain SQL
files with a recorded checksum, which makes "what will this deploy do to the database" a readable
diff rather than a metadata comparison performed at runtime. TypeORM's decorator entities double as
the domain model, which is the coupling this standard specifically breaks: the ORM model is the
*table*, and the domain entity is the *concept*, and the mapper between them is what keeps a column
rename from being a refactor of business rules. The cost is real and stated: Prisma is
schema-first, its escape hatch for exotic SQL is `$queryRaw`, and the generated client must be
regenerated after every schema change — which is why `prisma generate` is step one of verification.

**Why throwing domain errors instead of a `Result` in the request path.** `v1rus-typescript`
owns the principle; here the framework has already voted. Nest's pipeline — guards, interceptors,
exception filters, the transaction wrapper — is built on exceptions, so a `Result` threaded up to
the controller has to be unwrapped and rethrown at the boundary anyway. That buys ceremony and no
guarantee. What the standard takes instead is the part that actually matters: the failure is a
**typed class with a stable machine-readable `code`**, thrown by the domain and mapped in exactly
one place, so the set of failure modes is enumerable and the HTTP contract is a table rather than a
scatter of status codes. `Result` keeps its place where the caller must handle both branches
locally — per-item outcomes in a batch or an import, where one bad row must not abort 999 good
ones.

**Why REST is the default and GraphQL is opt-in.** A REST surface is cacheable at the edge,
trivially observable (a route template is a metric label), and its authorisation boundary is the
endpoint. GraphQL moves query shaping to the client, which is genuinely valuable when many
heterogeneous clients need different field sets — and in exchange it moves N+1 to field
granularity, makes rate limiting a query-cost problem, and makes per-field authorisation something
you must build. That is a real trade, worth making deliberately and not by default. When a project
does run GraphQL, resolvers sit in the `api` layer on exactly the same terms as controllers.

**Why Vitest is the default, with Jest grandfathered.** The TypeScript layer standardises ESM and
`nodenext` resolution; Jest's ESM support still runs through experimental VM modules and a
transform configuration that has to be kept in sync with the compiler's. Vitest reads the project's
own TypeScript configuration and runs the same module graph the application does. It has one sharp
edge, and the plugin says so in three places rather than letting each project rediscover it: Vitest
transforms with esbuild, esbuild does not implement `emitDecoratorMetadata`, and Nest DI resolves
constructor parameters from exactly that metadata — so a Nest testing module fails with
`Nest can't resolve dependencies` until an SWC-based transform is configured. A project already on
Jest keeps Jest; the test structure in `node-testing` is identical on either, and running both is
never right.

**Why BullMQ and an outbox rather than just BullMQ.** A queue gives retries, backoff, concurrency
and observability; what it cannot give is atomicity with a database write, because Redis is not in
the Postgres transaction. Enqueueing inside the transaction publishes work for a state that may
roll back; enqueueing after it loses the work if the process dies in between. Both happen in
production, and neither shows up in a test. The outbox table makes the intent part of the same
commit and leaves delivery to a relay, whose at-least-once semantics are already covered by the
handler idempotency that an at-least-once queue demanded anyway.

**Why layers are folders and not modules.** Nest enforces the module boundary and nothing inside it.
Splitting one feature into four Nest modules to "enforce" the layering buys no enforcement — the
folders are just further apart — and costs a `forwardRef` the first time a controller needs its own
service. The boundary that is worth spending is the **feature** module's `exports`: that one is real,
and keeping it narrow is what stops the service becoming a single namespace.

**Project overrides.** Everything here is the default, not a mandate: a project may specify a
different structure or stack in its own `CLAUDE.md`, and the project wins. What the plugin
guarantees is that the default is a coherent whole rather than per-developer taste.
