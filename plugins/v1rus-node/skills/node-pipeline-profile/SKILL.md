---
name: node-pipeline-profile
description: "Stack profile that binds the stack-agnostic v1rus feature pipeline to a NestJS / Node backend project: the module and layer vocabulary the architecture plan uses, the stack-specific sections of architecture-plan.md and the self-questions the plan must answer, which convention skill owns which area, the presentation pattern (controller over application service over domain port, DTOs in and explicit response DTOs out), how an API contract stands in for a design spec, where tests live and on what (colocated spec files, e2e with supertest, Testcontainers Postgres), how to type-check, lint, migrate and verify, which engineer agents implementation escalates to, and the finalizer's stack checklist. Loaded by feature-architect, feature-designer, feature-developer, test-planner, test-writer and feature-finalizer when the pipeline detects a Node backend project. Do NOT load for pipeline mechanics — gates, complexity bands and commit discipline live in feature-pipeline."
---

# Pipeline profile — NestJS / Node backend

The pipeline agents (`feature-architect`, `feature-designer`, `feature-developer`, `test-planner`,
`test-writer`, `feature-finalizer`) are stack-agnostic. This profile is the **vocabulary** they use
on a Node backend: what the layers are called, what the plan must cover, where tests go, which
convention skill owns which rule.

Two boundaries that matter:

- **Pipeline mechanics are not here.** Phase order, gates, complexity bands, artifact names, commit
  discipline and resume live in the `feature-pipeline` skill. This file never repeats them.
- **The project still owns the names.** Real module paths, type names, script names and the
  migration and test commands come from the target project's `CLAUDE.md`, `package.json` and
  `nest-cli.json`. Read those first; never guess a command.

## Stack identity

Markers: `package.json` depending on `@nestjs/core`, a `nest-cli.json`, `src/main.ts` with
`NestFactory.create`, `src/app.module.ts`. Usually also `prisma/schema.prisma`. In a monorepo the
backend is one workspace package — the workspace tooling above it belongs to `v1rus-fullstack`, not
to this profile.

## Layer vocabulary

| Location | Holds |
|---|---|
| `src/main.ts` | composition root: global pipe, filter, serializer, versioning, security, `enableShutdownHooks` |
| `src/app.module.ts` | imports config, core infrastructure and every feature module |
| `src/config/` | env schema and typed config namespaces |
| `src/core/` | cross-cutting infrastructure: logger, `PrismaService`, health, global filters/interceptors, queue connection |
| `src/shared/` | pure reusable code: base error types, value-object primitives, helpers |
| `src/modules/<feature>/api/` | controllers, request DTOs, response DTOs, route guards, OpenAPI decorators |
| `src/modules/<feature>/application/` | use-case services, orchestration, transaction boundaries |
| `src/modules/<feature>/domain/` | entities, value objects, port interfaces, domain errors |
| `src/modules/<feature>/infrastructure/` | Prisma repositories, external clients, mappers, job processors |
| `prisma/` | `schema.prisma` and the migration history |
| `test/` | e2e specs and shared fixtures; unit specs are colocated |

Hard boundaries (review-enforced, since the framework enforces only the module boundary): `domain`
imports nothing framework-shaped — no `@nestjs/*`, no Prisma, no `class-validator`; `application`
depends on domain ports, never on `infrastructure`; `api` never touches the ORM; a feature module
never imports another feature module's internals — cross-feature needs go through a port, a shared
module, or an event. Detail: `nest-architecture`.

## `architecture-plan.md` — stack sections

Use these in place of the generic layer sections:

```
## 3. Domain layer changes        (entities and invariants, value objects, port interfaces,
                                  domain error cases and their stable codes)
## 4. Infrastructure changes      (Prisma schema + the migration, repository implementations
                                  and mappers, outbound clients, queue processors)
## 5. Application layer changes   (use-case services, the transaction boundary, domain events)
## 6. API surface changes         (routes and their version, request DTOs + validation rules,
                                  response DTOs, status codes per outcome, OpenAPI)
## 7. Wiring and operations       (module providers/exports and token bindings, new config
                                  variables + their schema entries, new queues, log fields,
                                  readiness checks, and the backward-compatibility story)
```

Self-questions the plan must answer for this stack:

- Does anything in `domain` import Nest, Prisma or `class-validator`? Does the controller reach the
  ORM?
- Is every new endpoint's response an explicit DTO, or does a persistence model leak?
- Does each failure mode have a named domain error, a stable `code` and a mapped status?
- Does the transaction cover the whole invariant — and does it contain any network call?
- Is the new query an N+1 in a loop, and is the pool budget still within the database limit?
- Is the migration additive, or does it need the expand / backfill / contract split across two
  deploys?
- Does any new provider need request scope, and is the bubbling cost stated?
- Does anything slow or retryable belong in a job instead — and if it publishes after a write, does
  it need the outbox?
- Which new environment variables exist, and are they in the schema with no default for secrets?
- Is the change backward compatible for existing clients, and if not, which version carries it?

## Convention skills by area

| Area | Skill |
|---|---|
| modules, layers, dependency direction, circular modules | `nest-architecture` |
| providers, tokens, scopes, lifecycle, testing overrides | `nest-di` |
| controllers, DTOs, validation pipe, serialization, versioning, pagination | `nest-http-api` |
| domain errors, exception filter, problem responses, throw vs Result | `nest-error-handling` |
| Prisma schema, migrations, repositories, transactions, N+1, pool | `node-persistence` |
| env validation, typed config, secrets | `node-configuration` |
| event loop, streams, cancellation, graceful shutdown, process failure | `node-runtime` |
| pino logging, correlation ids, redaction, health and readiness, metrics | `node-observability` |
| queues, job payloads, idempotency, retries, outbox, scheduling | `node-background-jobs` |
| unit / e2e / Testcontainers tests | `node-testing` |
| the per-file rulebooks | `node-conventions` |
| TypeScript itself — types, ESM, async, package structure, lint | `v1rus-typescript:typescript-conventions` and its siblings |

Name the applicable ones in the plan so the implementing agent invokes them; invoke them yourself
before writing non-trivial API or data-layer code. If a skill is absent in the current environment,
proceed — never hard-depend on one.

## Presentation pattern

There is no UI on this stack; the **API contract is the presentation layer**. The shape is
controller → application service → domain port, with the controller owning only HTTP:

- Input is a **DTO class** with validation decorators, behind a global `ValidationPipe` configured
  with `whitelist` and `forbidNonWhitelisted`.
- Output is an **explicit response DTO**, mapped from the domain object. A Prisma model or an entity
  never leaves a handler.
- Failures are **thrown typed domain errors**, mapped by one exception filter to a stable
  `application/problem+json` body with a machine-readable `code` and the correlation id.
- Business rules live in the application service or the domain entity, never in the controller.

## Design-spec mapping (feature-designer)

A backend feature usually has no visual design, so the designer phase is normally **skipped** — the
orchestrator records why. When it does run, what it produces is an **API contract**, not a screen
spec: resource paths and their version, the request and response DTO shapes, the status code per
outcome with its error `code`, pagination and filter parameters, idempotency and caching semantics,
and any OpenAPI examples. Map it onto what the service already exposes — reuse existing DTO shapes,
the existing pagination envelope and the existing error codes before inventing new ones; discover
them with `ast-index` rather than assuming.

## Tests

- Location: **unit specs are colocated** — `order.service.ts` → `order.service.spec.ts`; **e2e specs
  live in `test/`** as `<feature>.e2e-spec.ts` with their own config; shared fakes in `test/fakes/`.
- Runner: **Vitest** by default, **Jest** where the project already uses it — never both. On Vitest,
  Nest DI needs an SWC-based transform because esbuild does not emit decorator metadata
  (`node-testing`).
- Unit: construct the service directly with fakes (`new PlaceOrder(fakeRepo, fixedClock)`); use
  `Test.createTestingModule` with `overrideProvider` **by token** only when the wiring is under test.
- E2E: `supertest` against an app built with the same global pipes, filter and versioning as
  `main.ts`; assert the error body shape and the status code per outcome, not only the happy path.
- Database: a **Testcontainers Postgres**, one container per suite, `prisma migrate deploy` once,
  truncate between tests. Never a mocked Prisma client for a repository test. A schema change
  requires a migration test.
- Determinism: inject the clock and id generator; never `sleep` to wait for async work.
- Detail: `node-testing`. Whether tests are written at all is the complexity band's call
  (`v1rus-core:v1rus-qa`).

## Verification

In this order — an earlier failure makes every later result a lie:

1. **`prisma generate`** when `schema.prisma` changed; the client is generated code and a stale one
   makes every type error a lie.
2. **Type-check** (`tsc --noEmit` or the project's script) — the compile gate for this stack.
3. **Lint** — the flat ESLint config the `v1rus-typescript` layer owns.
4. **Migrations** applied to the test database with `migrate deploy`, never `migrate dev` in CI and
   never `db push`.
5. **Unit tests**, then **e2e** (slower, needs the container runtime).

The full run belongs to `v1rus-node:test-runner`, which discovers the project's own scripts.
Commands come from the project's `CLAUDE.md` and `package.json`; the usual shape is
`npm run build` / `typecheck` / `lint` / `test` / `test:e2e`. Never read `dist/`, `node_modules/` or
`.prisma/` — read the console output you produced.

## Implementation escalation targets

| Work | Agent |
|---|---|
| Modules, controllers, services, repositories, Prisma schema and migrations, config, jobs, tests | `v1rus-node:node-engineer` |
| Verification runs | `v1rus-node:test-runner` |
| Floor when none is installed | `feature-developer` |

There is no separate UI agent on this layer; a change that also touches a web frontend is two
agents and two plans — `v1rus-react` owns the client, and the seam between them belongs to
`v1rus-fullstack`.

## Finalizer stack checklist

On top of the generic cleanup: no `process.env` outside `src/config/`; no `console.*`; every new
provider registered and every token binding present; `exports` narrowed to what other modules
actually use; no `forwardRef` added without a comment; no Prisma type or driver error escaping
`infrastructure`; no persistence model returned from a controller; every new domain error mapped in
the exception filter with a stable code; the migration committed with the schema change and not
edited after being applied; new environment variables present in the env schema **and** in
`.env.example`; no secret in a log, a span or an error body; every new resource released in
`onModuleDestroy`; OpenAPI decorators matching the DTOs; type-check and lint clean.

## Typical expert reviews to flag

`security-expert` for auth, tokens, permissions, anything touching secrets, a new public endpoint or
a change to what an error response reveals; `performance-expert` for a new query on a large table, a
loop of awaits, a transaction that grew, new queue plumbing or anything on a hot path;
`architecture-expert` when the change crosses module boundaries, adds a `forwardRef`, or introduces a
new cross-feature dependency; `business-analyst` when a status code or an error contract changes in
a way existing clients can see.
