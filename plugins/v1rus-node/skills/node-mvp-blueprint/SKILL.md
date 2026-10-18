---
name: node-mvp-blueprint
description: "The /mvp-init MVP blueprint for a NestJS / Node backend: when Node is the right backend stack and when to send the brief elsewhere, the nest new bootstrap route and exactly what of the generated template is replaced, the MVP-sized src/ module layout with the rule for when each deferred piece appears, the baseline package set by role (no versions), tsconfig / ESLint / Prisma / Docker Compose / environment configuration, the app skeleton that proves config, DI, logging, persistence, error mapping and shutdown, the first vertical slice as real working code with its migration and endpoint, the facts the generated project CLAUDE.md must record, the verification commands and what runnable means for a service, escalation targets, and the traps that break a fresh Node backend. Load when scaffolding a new NestJS service, bootstrapping a backend for a new product, laying out src/ for a new API, or generating a new Node backend's CLAUDE.md. Do NOT load to add a feature to an existing service — that is node-pipeline-profile."
---

# MVP blueprint — NestJS / Node backend

The technology half of `/mvp-init` on this stack: the command owns the process, this file owns what
a Node backend *is* at hour zero. Layer vocabulary, the convention-skill map, test layout and
verification discipline live in **`node-pipeline-profile`** — this blueprint says what to *create*,
the profile says how to work in it afterwards. Everything below is the short form of a skill in this
plugin; invoke the named skill before writing the code.

## 1. Stack identity

Node/NestJS when the brief says an **HTTP or event-driven backend** for a web or mobile client, the
team is already a TypeScript team, and the work is I/O-bound — CRUD, integrations, orchestration,
webhooks, real-time. Sharing types with a TypeScript frontend is a strong positive signal.

| Anti-signal | Go to |
|---|---|
| Sustained CPU-bound work is the product (media transcoding, ML inference, heavy numerics) | not this layer — a runtime with real threads |
| The team is a JVM team or the service must live in an existing Kotlin codebase | `v1rus-kotlin` |
| Strict hard-real-time or memory-constrained embedded targets | not this layer |
| A frontend, with the backend being someone else's service | `v1rus-react` |
| A single-repo product where the backend and the web client ship together | this blueprint for the service; `v1rus-fullstack` owns the workspace around it |

## 2. Bootstrap route

The Nest CLI is the generator — do not hand-write the scaffold.

```
nest new <service-name> --package-manager <the workspace's>  --strict
```

- `--strict` sets the strict TypeScript flags at creation; the full compiler configuration is then
  aligned with `v1rus-typescript:ts-project-config`, which owns it.
- The package manager matches whatever the repository already uses; in a monorepo the workspace
  tooling is `v1rus-fullstack`'s call, not this blueprint's.
- Commit the lockfile — this is an application.
- The Node version floor is pinned once, in `engines` in `package.json` and in a version file the
  toolchain reads (`.nvmrc` or equivalent), and the CI image and the Dockerfile use that same
  floor. Three places disagreeing is trap 4.

**Toolchain missing.** If Node or the package manager is not on PATH, do not install it and never
use `sudo`. Say so in one line, hand the developer the exact commands for their own terminal, and
continue with everything that does not need the runtime — the plan, the `CLAUDE.md`, the file
contents to write once the tree exists.

| # | After `nest new` | Detail |
|---|---|---|
| 1 | Delete the sample | `app.controller.ts`, `app.service.ts` and their specs; keep `app.module.ts` and `main.ts` and rewrite both |
| 2 | Replace the lint and TS config | the flat ESLint config and `tsconfig` from `v1rus-typescript` |
| 3 | Create the `src/` tree | §3 — a folder only where a file already belongs in it |
| 4 | Add the config module | §6, before anything that needs a setting |
| 5 | Add Prisma + Docker Compose for local Postgres (and Redis if §4 says so) | §5 |
| 6 | Skeleton (§6), then slice (§7) | plumbing before feature code |
| 7 | Verify | §9 |

## 3. Module graph at MVP size

One deployable service, one database. Layers are folders inside a feature module, not separate Nest
modules — splitting a feature into four modules buys nothing and costs a `forwardRef` the first time
a controller needs its own service (`nest-architecture`).

```
src/
  main.ts                    composition root
  app.module.ts
  config/                    env schema + typed namespaces
  core/                      logging/, prisma/, health/, filters/, interceptors/, context/
  shared/                    base error types, value-object primitives
  modules/<slice>/           api/, application/, domain/, infrastructure/
prisma/                      schema.prisma, migrations/
test/                        e2e specs, fakes/
docker-compose.yml           Postgres (+ Redis when queues are in scope)
```

| Deferred | Created when |
|---|---|
| `core/queue/` + a worker entrypoint | the first job that must survive a restart or retry |
| a separate worker process | the first job heavy enough to affect API latency |
| `core/cache/` | a measured hot read, never speculatively |
| a second feature module | the second bounded concept — not the second endpoint |
| API versioning beyond `v1` | the first breaking change; versioning itself is **enabled from day one** (trap 3) |
| OpenTelemetry tracing | the first downstream service — a single service traces itself with logs |
| a `shared/` value-object library | the second module that needs the same primitive |
| RBAC beyond a single role check | the brief names the second role |
| multi-tenancy, sharding, read replicas | post-MVP, and each is a schema decision, not a bolt-on |

## 4. Baseline dependency set, by role

Names only. **Every version is resolved at plan time through the `v1rus-dependencies` gate** and
CVE-checked there — nothing is added from memory, and nothing is pinned in this document.

| Role | Package(s) | MVP |
|---|---|---|
| Framework | `@nestjs/core`, `@nestjs/common`, `@nestjs/platform-express` | mandatory |
| Config | `@nestjs/config` | mandatory |
| Env + payload validation | `zod` — the default named in `v1rus-typescript:ts-boundaries-validation` | mandatory |
| HTTP DTO validation | `class-validator`, `class-transformer` | mandatory |
| ORM | `prisma` (dev), `@prisma/client` | mandatory with a database |
| Logging | `pino`, `nestjs-pino` | mandatory |
| Health | `@nestjs/terminus` | mandatory |
| OpenAPI | `@nestjs/swagger` | mandatory for any client-facing API |
| Security | `helmet`, a rate-limit module | mandatory for a public surface |
| Auth | a JWT module + the password-hashing library (`argon2` or `bcrypt`) | with auth in the brief |
| Testing | `vitest` (+ `unplugin-swc` for decorator metadata — trap 2), `supertest`, `testcontainers` | infrastructure mandatory; whether tests are *written* is the complexity band's call (`v1rus-core:v1rus-qa`) |
| Queues | `bullmq`, `@nestjs/bullmq` | deferred to the first job |
| Scheduling | `@nestjs/schedule` | only for in-process timers; recurring work prefers a repeatable queue job (`node-background-jobs`) |
| Outbound HTTP | the platform `fetch` (`undici`) | mandatory when calling another service; a client wrapper lives in `infrastructure` |
| Tracing / metrics | OpenTelemetry SDK + exporter | deferred (§3) |

Jest instead of Vitest where the repository has already standardised on it — never both.

## 5. Build and local configuration

| What | Where |
|---|---|
| Dependency coordinates | `package.json` — the only place |
| Node version floor | `engines` in `package.json` + the toolchain version file + the CI image + the Dockerfile, all agreeing |
| TypeScript configuration | `tsconfig.json` per `v1rus-typescript:ts-project-config` — strict, and `emitDecoratorMetadata` + `experimentalDecorators` on, which Nest DI requires |
| Lint | the flat ESLint config from `v1rus-typescript:ts-lint-and-format`, plus a `no-process-env` rule with an override for `src/config/**` |
| Environment schema | `src/config/env.schema.ts`; every key mirrored in a committed `.env.example` with blank or fake values |
| Local dependencies | `docker-compose.yml` — Postgres, and Redis when queues are in scope. The developer runs one command, not four installers |
| Database schema | `prisma/schema.prisma`; migrations in `prisma/migrations/`, generated by `migrate dev` locally and applied by `migrate deploy` everywhere else |
| Scripts | `build`, `start:dev`, `typecheck`, `lint`, `test`, `test:e2e`, `db:migrate`, `db:generate`, `db:seed` — named once, recorded in `CLAUDE.md`, and never re-invented by an agent |
| Container image | multi-stage Dockerfile: build, then a slim runtime stage running as a **non-root** user, with the Prisma client generated in the build stage and `migrate deploy` run as a separate job, not at container start |

## 6. App skeleton

Every piece of plumbing is exercised once before feature work starts.

| File | Wires |
|---|---|
| `src/main.ts` | `NestFactory.create` → global `ValidationPipe` (`whitelist`, `forbidNonWhitelisted`, `transform`) → global exception filter → serializer → `enableVersioning` (URI) → helmet + CORS + body limit → Swagger → **`app.enableShutdownHooks()`** → `listen(config.http.port)` |
| `src/config/` | the env schema with fail-fast validation and typed namespaces; the only place `process.env` is read (`node-configuration`) |
| `src/core/logging/` | pino as the Nest logger, JSON output, redaction paths, level from config |
| `src/core/context/` | the `AsyncLocalStorage` request context and the edge middleware that opens it with a correlation id, echoed in the response header (`node-observability`) |
| `src/core/prisma/` | `PrismaService extends PrismaClient`, connecting in `onModuleInit` and disconnecting in `onModuleDestroy` — one client per process |
| `src/core/filters/` | the single exception filter mapping `DomainError` subclasses to `application/problem+json`, with an opaque 500 carrying only the correlation id (`nest-error-handling`) |
| `src/core/health/` | `/health/live` (in-process only) and `/health/ready` (database, and the queue when present), with readiness failing during shutdown |
| `src/shared/errors.ts` | the `DomainError` base with its stable `code` |
| `prisma/schema.prisma` | the slice's model, plus the first migration |
| `.env.example` | every key the schema declares |

## 7. The first vertical slice

One end-to-end feature, **real working code** — no `TODO`, no `NotImplementedException`, no stub
returning a literal. It proves config, DI, logging, the request context, Prisma, the error contract
and shutdown fit together, and it is the template every later feature is copied from.

**Which slice:** the simplest *create-and-list a primary entity* pair from the brief's MVP list;
with no obvious candidate, the primary entity of the product's domain. With no database decision yet
— which should not happen, but does — build the identical slice against an in-memory implementation
of the same domain port, so swapping in the Prisma one later is one line in one module.

| Layer | Files |
|---|---|
| `domain` | `<entity>.ts` with its invariants, `ports/<entity>.repository.ts` with the token, `errors.ts` with at least one not-found and one conflict case |
| `infrastructure` | `prisma-<entity>.repository.ts` implementing the port, `<entity>.mapper.ts` both directions, `P2002` mapped to the conflict error |
| `application` | `create-<entity>.ts` and `list-<entity>.ts` use-case services, the transaction boundary where the invariant needs one |
| `api` | `<entity>.controller.ts` (`POST` + `GET` list), `create-<entity>.request.ts` with validation decorators, `<entity>.response.ts` as an explicit DTO, cursor pagination envelope |
| `prisma` | the model and its migration |
| tests | e2e: 201 + body shape, 400 on a rejected field, 404, 409 on the duplicate; unit on the use case |

Non-negotiable in the slice, because it is what everything is copied from: unknown request
properties are rejected, the response is an explicit DTO (no Prisma model), a duplicate returns the
mapped 409 problem body and not a driver message, and every log line carries the correlation id.

Slice tests are written when the complexity band calls for them (`v1rus-core:v1rus-qa`); the
behaviour above is required either way.

## 8. Project `CLAUDE.md` inputs

| Fact | Value to record |
|---|---|
| Layout | `src/config`, `src/core`, `src/shared`, `src/modules/<feature>/{api,application,domain,infrastructure}`, `prisma/`, `test/`; composition root `src/main.ts` |
| Type names | `DomainError` base and where the error→status map lives; the config namespace names; `PrismaService`; `RequestContext`; the repository token naming convention |
| Commands | install; `db:generate`; `db:migrate` (dev) and `migrate deploy` (deployed); `db:seed`; `typecheck`; `lint`; `test`; `test:e2e`; `start:dev`; the Docker Compose command for local dependencies |
| Runner | Vitest or Jest, and the decorator-metadata transform in use |
| Tests | unit specs colocated as `*.spec.ts`; e2e in `test/` as `*.e2e-spec.ts`; fakes in `test/fakes/`; Testcontainers Postgres for database tests |
| API | base path and versioning scheme, the error response shape and where the code list lives, the pagination envelope, where the OpenAPI spec is published |
| Decisions | ORM; queue (or none); auth scheme; Node version floor; whether a separate worker process exists |
| v1rus plugins to enable | `v1rus-core`, `v1rus-typescript`, `v1rus-node` (plus `v1rus-fullstack` in a shared repo with a frontend) |

## 9. Verification

In this order — an earlier failure makes every later result a lie:

```
<install>
docker compose up -d                 # Postgres (+ Redis) for local work
<db:generate>                        # prisma generate — the client is generated code
<db:migrate>                         # migrate dev locally / migrate deploy in CI
<typecheck>                          # the compile gate for this stack
<lint>
<test>                               # unit
<test:e2e>                           # supertest + Testcontainers; needs a container runtime
```

| Then | Headless? |
|---|---|
| `docker build` of the production image | yes |
| Start the service and curl `/health/ready` and the slice endpoint | yes |
| Verify against the real deployed dependencies | **developer** — needs environment credentials |

"Runnable" here means the service boots against the Compose database, `/health/ready` returns
healthy, and the slice's `POST` then `GET` round-trips through Prisma. The agent verifies that much
and hands over anything needing real credentials — never claiming a deployment it did not perform.
Full runs belong to `v1rus-node:test-runner`, which discovers the project's own scripts.

## 10. Escalation targets

| Scaffold role | Agent |
|---|---|
| `package.json`, `tsconfig`, ESLint, Dockerfile, Compose, CI scripts | `v1rus-node:node-engineer` — there is no separate build agent on this layer |
| `config`, `core`, modules, Prisma schema and migrations, the slice | `v1rus-node:node-engineer` |
| Verification runs | `v1rus-node:test-runner` |
| Floor when none is installed | `feature-developer` |

A web client in the same repository is `v1rus-react`'s, and the workspace wiring between them is
`v1rus-fullstack`'s — never scaffolded from this blueprint.

## 11. Known first-run traps

1. **No `enableShutdownHooks()`.** It is not on by default. Without it `onModuleDestroy` never runs:
   the Prisma pool is not closed, queue workers are killed mid-job, and every deploy drops in-flight
   requests. It costs one line at hour zero and an incident later.
2. **Decorator metadata missing under the test runner.** Vitest transforms with esbuild, which does
   not implement `emitDecoratorMetadata`, so `Test.createTestingModule` fails with
   `Nest can't resolve dependencies` on classes that inject by type — an error that reads like a
   wiring bug and is a transform bug. Configure the SWC-based transform when the test setup is
   created, not when the first test fails (`node-testing`).
3. **Versioning retrofitted.** Adding a `/v1` prefix after clients exist is a client migration.
   Enable `enableVersioning` and put the first controller on `v1` on day one, even with one version.
4. **The Node version floor disagreeing with itself.** `engines`, the toolchain version file, the CI
   image and the Dockerfile are four places that must name the same floor; when they drift, a
   feature works locally and fails in CI with a syntax error that names no version.
5. **A generated Prisma client that is stale or missing.** `prisma generate` runs after every schema
   change and in the Docker build stage; without it `tsc` reports dozens of missing-type errors that
   read like real breakage, and hand-editing the generated client to silence them is never the fix.
