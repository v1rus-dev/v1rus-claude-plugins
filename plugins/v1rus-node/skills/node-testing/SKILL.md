---
name: node-testing
description: "How tests are written and run for a v1rus NestJS service: Vitest as the runner with the decorator-metadata caveat that esbuild alone cannot satisfy, unit tests constructing a service directly with fakes instead of spinning a Nest testing module, Test.createTestingModule with overrideProvider by token when the wiring itself is under test, e2e with supertest against the real application including the global pipes and exception filter, a Testcontainers Postgres for anything touching the database instead of a mocked Prisma client, migrate-then-truncate isolation between tests, injected clock and id generator so assertions are deterministic, testing the error contract and not just the happy path, migration tests on a schema bump, and what not to test. Load when writing or fixing tests for Node or NestJS code, setting up the test runner or the test database, testing a controller, service, repository or job, or when a change breaks existing tests."
---

# Testing a NestJS Service

**Whether tests are written at all is the complexity band's call**, not this skill's — see
`v1rus-core:v1rus-qa` (tests from complexity 7 upward; below that verification is build + static
analysis + the quality gate). This covers *how* they are written when warranted.

## Runner

**Vitest** is the default (see the plugin README design notes). One caveat that costs an afternoon
if it is not known up front:

> Vitest transforms with esbuild, and **esbuild does not implement `emitDecoratorMetadata`**. Nest's
> DI resolves constructor parameter types from that metadata, so a testing module compiled by
> esbuild alone fails with `Nest can't resolve dependencies` on classes that inject by type. The fix
> is a SWC-based transform plugin for Vitest (`unplugin-swc`) with `decorators` and
> `decoratorMetadata` enabled in the SWC config.

Projects already standardised on **Jest** keep Jest — the difference is not worth a migration, and
the structure below is identical on either. Do not run both.

## Layout and naming

- Unit tests sit next to the code: `order.service.ts` → `order.service.spec.ts`.
- E2E tests live in `test/` and are named `<feature>.e2e-spec.ts`, with their own config so they can
  run separately and with a longer timeout.
- One `describe` per unit under test, one test per behaviour. The name states the behaviour:
  `rejects a second payment for an already-paid order` — not `test placeOrder`.

## Unit tests — construct the class

```ts
const orders = new InMemoryOrderRepository();
const service = new PlaceOrder(orders, fixedClock, nullLogger);
```

No Nest, no container, no decorators involved. It is an order of magnitude faster, a missing
dependency is a compile error rather than a runtime resolution failure, and the test reads as a
description of the class's actual collaborators. This is the default shape for application and
domain code, which is where the logic worth testing lives.

`Test.createTestingModule` is for when **the wiring is the thing under test** — a guard's
integration with a strategy, a dynamic module's options, an interceptor in the pipeline — and for
building the e2e app. Override at the **token**:

```ts
.overrideProvider(ORDER_REPOSITORY).useValue(new InMemoryOrderRepository())
```

Overriding the implementation *class* when the binding is by token compiles, runs, and silently uses
the real provider (`nest-di`).

## Doubles

- **Hand-written fakes** where the double carries behaviour: an in-memory repository backed by a
  `Map`, a fake clock, a fake mailer that records what it was asked to send. More readable than six
  `mockResolvedValue` lines and reusable — keep them in `test/fakes/` and reuse rather than
  reinventing per file.
- **Mocks** where you assert an interaction and nothing else (an outbound client called exactly
  once, with these arguments).
- **Never mock the Prisma client to test a repository.** The repository's job is to produce correct
  SQL and map the result; a mocked client asserts that you called the method you called. Test
  repositories against a real database (below) — a mocked one passes while the query is wrong.
- Inject the clock and the id generator. `new Date()` and `randomUUID()` inside the code under test
  make assertions either non-deterministic or full of `expect.any`.

## E2E with supertest

```ts
const res = await request(app.getHttpServer())
  .post('/v1/orders')
  .send({ items: [...] })
  .expect(201);
```

- Build the app the way `main.ts` does — **the same global pipes, filters, interceptors and
  versioning**. An e2e suite on a bare app tests routes the production process does not have: the
  validation that strips unknown fields and the filter that shapes errors are exactly what you most
  want covered.
- Cover the contract, not only the happy path: the 400 for a malformed body, the 404, the 409 for a
  violated invariant, and **the error body shape itself** — status, `code`, and the absence of a
  stack (`nest-error-handling`). A status-code change in a refactor is a client-breaking change and
  this is the test that catches it.
- Assert that a request carries its correlation id back in the response header.
- Close the app in `afterAll`, or the suite hangs on open handles.

## Database tests with Testcontainers

```ts
const container = await new PostgreSqlContainer().start();   // once per suite
const databaseUrl = container.getConnectionUri();

// the CLI is a separate process — hand it the URL in its own env, do not mutate this one
execSync('prisma migrate deploy', { env: { ...process.env, DATABASE_URL: databaseUrl } });

const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
  .overrideProvider(databaseConfig.KEY)                      // before the app is built
  .useValue({ url: databaseUrl, poolSize: 5 })
  .build();
```

- **The container's URI reaches the app through configuration, not through `process.env`.** Override
  the namespace provider as above, or load a literal object with `ConfigModule.forRoot({ load: [...] })`
  in the testing module. Assigning `process.env.DATABASE_URL` leaks into every test that runs after
  it in the same worker and makes the suite order-dependent (`node-configuration`).
- **A real Postgres, not SQLite and not a mock.** Constraints, transaction semantics, `ON CONFLICT`,
  `Decimal` behaviour and index-dependent ordering are the things being tested; a different engine
  agrees with none of them.
- **One container per suite file**, started in `beforeAll` — starting one per test turns a 4-second
  suite into four minutes. Run `migrate deploy`, not `migrate dev`, and run it once.
- Isolate between tests by **truncating** the tables (or by wrapping each test in a transaction that
  is rolled back). Re-running migrations per test is the slow way to the same place.
- Containers need a container runtime; in CI that is a service or a mounted socket. When it is
  genuinely unavailable, say so and mark the gap explicitly — a repository suite quietly downgraded
  to mocks tests nothing (`v1rus-core:v1rus-qa` § 4).
- **Every `schemaVersion`-changing migration gets a migration test**: seed the old schema, run the
  migration, assert the data survived and the new constraint holds. This is the one place where "it
  compiles" and "the new tests pass on an empty database" prove nothing.

## Jobs and async

- Test a processor as a **function**: build it, hand it a job object, assert the effect. Do not
  start a real worker and wait.
- Test idempotency explicitly — run the handler twice with the same payload and assert one effect
  (`node-background-jobs`). This is the single most valuable job test and the one most often
  missing.
- **Never `setTimeout` or `sleep` to wait for something.** Use fake timers, await the promise the
  code returns, or poll a condition with a bounded deadline. A sleep-based test is flaky on a loaded
  CI runner and slow everywhere else.

## What not to test

Nest's own wiring, the ORM's query builder, `class-validator`'s decorators, and getters. A test that
would only fail if a framework changed is maintenance with no signal. The public-API coverage floor
and what counts as trivial are `v1rus-core:v1rus-qa` § 1.

## Running

Read the exact commands from the project's `CLAUDE.md` and `package.json` — never invent one. The
usual shape is a unit script, a separate e2e script with its own config, a type-check, and a lint
run; the full run belongs to `v1rus-node:test-runner` so a long suite does not consume the
orchestrating session's context. Scope the run to the change (`v1rus-core:check`): a logic change
runs the affected suites, a rename or a comment edit needs a type-check only.

Whoever breaks an existing test fixes it in the same change; a `.skip` without a tracked issue is
forbidden (`v1rus-core:v1rus-qa` § 4).
