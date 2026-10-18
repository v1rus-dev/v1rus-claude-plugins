---
paths:
  - "**/*.module.ts"
  - "**/*.service.ts"
  - "**/*.controller.ts"
  - "**/*.resolver.ts"
  - "**/*.guard.ts"
  - "**/*.interceptor.ts"
  - "**/*.filter.ts"
  - "**/*.pipe.ts"
  - "**/main.ts"
---

# NestJS — rules for this file

Only what a model gets wrong or omits without a reminder. Generic TypeScript is not here — the
`v1rus-typescript` layer owns type discipline, ESM, `exports` maps and the lint config, and ESLint
enforces the rest.

## Modules

- A module declares what it **owns** in `providers` and what other modules may use in `exports`.
  A provider that is not exported is private — that is the only boundary Nest gives you, so use it.
  Exporting everything turns the module graph into one namespace.
- **A feature module never imports another feature module to reach its internals.** Cross-feature
  reuse goes through a shared module, a domain port, or an event — not through `exports` of a service
  that was meant to be internal.
- **`forwardRef` is a defect marker, not a tool.** Two modules referring to each other means a third
  thing wants to exist: extract the shared contract into its own module, or invert one direction with
  an event. Write `forwardRef` only with a comment saying why extraction is impossible here.
- Configuration that a module needs comes in through a `register`/`registerAsync` static factory on
  that module, not by reading `process.env` inside it.

## Providers and injection

- **Constructor injection only.** `private readonly x: X` in the constructor. Property injection
  (`@Inject()` on a field) hides the dependency from the type signature and from every test.
- Inject an **interface through a token**, not a concrete class, wherever the implementation is meant
  to be swappable (a repository, a clock, an outbound HTTP client). A `Symbol` or a `const` token plus
  an `InjectionToken`-typed provider keeps the domain free of the infrastructure class.
- **Default scope is singleton and that is the default you keep.** A `Scope.REQUEST` provider makes
  every provider that injects it request-scoped too, transitively up to the controller — the whole
  chain is then re-instantiated per request. If you need request data, inject a request-context
  service backed by `AsyncLocalStorage` instead of making the graph request-scoped.
- Async initialisation goes in `onModuleInit`, never in the constructor. A constructor that awaits
  cannot; a constructor that starts a floating promise leaves the provider half-built.
- Anything holding a resource (a connection, an interval, a subscription, a queue worker) implements
  `onModuleDestroy` and releases it there.

## Controllers

- A controller **maps HTTP to a call and back**. Route, DTO, status code, response shape. No business
  rules, no persistence, no orchestration of two services — that belongs in the application service.
- **The input type is a DTO class with validation decorators**, never `any`, never a bare `Record`,
  never the persistence model. The global `ValidationPipe` must run with `whitelist: true` and
  `forbidNonWhitelisted: true`; without `whitelist` the pipe validates the declared fields and passes
  every undeclared one straight through to your service.
- **The output type is an explicit response DTO.** Returning a Prisma model, a TypeORM entity or a
  domain object publishes whatever anyone adds to that type later — including the password hash added
  in a different sprint. Map explicitly, or serialise through a class with `@Expose` and
  `ClassSerializerInterceptor`; never rely on `@Exclude` alone on a type you did not define.
- `@Res()` opts the handler out of the Nest response pipeline — interceptors and the serializer stop
  running for it. Use `@Res({ passthrough: true })` when you only need to set a header or a cookie.
- Errors leave a controller as a thrown typed error, not as a manually built error body. One
  exception filter owns the wire format (`nest-error-handling`).

## Guards, interceptors, pipes, filters

- Order is fixed: middleware → guard → interceptor (before) → pipe → handler → interceptor (after) →
  exception filter. Authorisation belongs in a guard, not in the first three lines of the handler.
- A guard returns a boolean or throws; it does not mutate the response and does not perform writes.
- An interceptor that wraps the response must not swallow errors: rethrow, or map deliberately.
- An exception filter never passes an internal message or a stack to the client. Log the detail with
  the correlation id, return the stable shape (`nest-error-handling`).

## Configuration and logging

- **`process.env` is read in exactly one place** — the config module, at startup, validated. A
  `process.env.X` anywhere else is a defect: it is untyped, unvalidated, and invisible to the
  fail-fast check (`node-configuration`).
- No `console.log` / `console.error`. The injected logger only, structured, with the request
  correlation id (`node-observability`, `v1rus-core:v1rus-logging`).
- Never log a token, an authorization header, a password, a full request body or a PII field.

## main.ts

- The bootstrap enables, in this order: the global validation pipe, the global exception filter, the
  global serializer, versioning, CORS and security headers, and **`app.enableShutdownHooks()`**.
  Without shutdown hooks `onModuleDestroy` never runs on SIGTERM and every deploy kills in-flight
  requests (`node-runtime`).
- `main.ts` wires; it holds no business logic and no `if (env === 'production')` branches beyond
  what the config object already answers.
