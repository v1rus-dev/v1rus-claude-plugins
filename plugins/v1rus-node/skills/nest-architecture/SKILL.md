---
name: nest-architecture
description: "The v1rus NestJS module and layer architecture: one module per feature with an enforced inner layering of api (controllers, DTOs) over application (use-case services) over domain (entities, ports, domain errors) over infrastructure (Prisma repositories, HTTP clients, queue adapters), the dependency rule that domain imports nothing framework-shaped, providers private unless exported, shared and core modules, cross-feature communication through ports and events rather than through another feature's service, and dynamic modules with register/registerAsync. Load when creating a NestJS module or feature, deciding which layer a class belongs to, wiring modules together, resolving a circular module dependency, or reviewing a module boundary."
---

# NestJS Architecture

A NestJS application is a graph of modules. Nest enforces the module boundary and nothing inside it,
so the inner layering is a convention that review and the folder layout carry — which is exactly why
it is written down and checked, rather than assumed.

## Layout

```
src/
  main.ts                     # composition root: bootstrap, globals, shutdown hooks
  app.module.ts               # imports config, core infrastructure, and every feature module
  config/                     # env schema, typed config namespaces (node-configuration)
  core/                       # cross-cutting infrastructure, no feature knowledge:
                              #   logging/, prisma/, http/, queue/, health/, filters/, interceptors/
  shared/                     # reusable pure code: value objects, result/error base types, utils
  modules/
    <feature>/
      <feature>.module.ts
      api/                    # controllers, request DTOs, response DTOs, route guards
      application/            # use-case services, orchestration, transaction boundaries
      domain/                 # entities, value objects, ports (interfaces), domain errors
      infrastructure/         # repository implementations, external clients, mappers, job handlers
```

`api` / `application` / `domain` / `infrastructure` are folders, not modules. Splitting a feature
into four Nest modules buys nothing and costs a `forwardRef` the first time a controller needs its
own service.

## The dependency rule

```
api ──▶ application ──▶ domain ◀── infrastructure
                            ▲
                       (ports live here;
                        infrastructure implements them)
```

- **`domain` imports nothing from the other three, and nothing framework-shaped.** No `@nestjs/*`
  decorator on a domain entity, no Prisma type, no `class-validator` decorator, no `Request`. A
  domain file that imports Prisma means the ORM has become the model.
- **`application` depends on domain ports, never on `infrastructure`.** The service asks for
  `OrderRepository` (an interface in `domain/ports`) and Nest injects the Prisma implementation by
  token. That is what makes the service testable without a database and the database replaceable
  without touching the service.
- **`infrastructure` implements ports and maps.** A Prisma row becomes a domain entity here; a
  domain entity becomes a Prisma `create` input here. Both directions in one mapper file per
  aggregate, never inline in a query.
- **`api` never talks to `infrastructure` or to the ORM.** A controller calling `prisma.user.findMany`
  is the single most common shortcut on this stack and it removes the only layer that can hold a
  business rule.

## What goes in which layer

| Layer | Contains | Never contains |
|---|---|---|
| `api` | controllers, request/response DTOs, `class-validator` decorators, route-level guards, OpenAPI decorators | business rules, ORM calls, transactions |
| `application` | use-case services, orchestration across repositories, transaction boundaries, domain-event dispatch | HTTP types (`Request`, `Response`), SQL, ORM types, DTO validation decorators |
| `domain` | entities, value objects, invariants, port interfaces, the domain error union | Nest decorators, Prisma, `class-validator`, `process.env`, I/O of any kind |
| `infrastructure` | Prisma repositories, HTTP clients for other services, queue producers/consumers, cache adapters, mappers | business rules, cross-feature orchestration |
| `core` | logger, `PrismaService`, health checks, global filters/interceptors, queue connection | anything a single feature owns |
| `shared` | pure helpers, base error types, value-object primitives | anything with a Nest decorator or I/O |

## Module wiring

```ts
@Module({
  imports: [PrismaModule, HttpModule],
  controllers: [OrdersController],
  providers: [
    PlaceOrder,                                        // application service
    { provide: ORDER_REPOSITORY, useClass: PrismaOrderRepository },
  ],
  exports: [ORDER_REPOSITORY],                         // only what another module legitimately needs
})
export class OrdersModule {}
```

- **`providers` is ownership, `exports` is public API.** Anything not exported is private to the
  module, and that is the one boundary the framework actually enforces — spend it.
- **A feature module never imports another feature module to reach its internals.** Legitimate
  cross-feature needs resolve as: a port the other feature implements, a shared module both depend
  on, or a domain event. Two features reaching into each other is how a monolith becomes a knot.
- `@Global()` is for one or two genuinely ambient things (the logger, the Prisma client) declared in
  `core`. A `@Global()` feature module makes every import implicit and every dependency invisible.

## Circular module dependencies

`forwardRef` makes the error go away and keeps the cycle. The cycle is the problem: it means the two
modules share a concept neither owns. Resolve it, in this order of preference:

1. **Extract the shared thing** into a third module both import — usually a port interface plus its
   DTOs, sometimes a small domain service.
2. **Invert one direction with an event.** `Orders` does not call `Notifications`; it emits
   `OrderPlaced` and `Notifications` subscribes. The compile-time edge disappears.
3. **Merge**, if the two modules turn out to be one aggregate that was split by accident.

`forwardRef` remains only where an intentional recursive structure exists, and carries a comment
saying why the three options above do not apply. Note that a provider-level cycle (`forwardRef` in
`@Inject`) has the same diagnosis; see `nest-di`.

## Dynamic modules

A module that needs configuration exposes `register` (static) or `registerAsync` (factory,
`inject: [AppConfig]`) and returns a `DynamicModule`. It **does not read `process.env` itself** —
configuration arrives as an argument, which is what makes the module reusable and testable
(`node-configuration`).

## Adding a feature — checklist

1. `src/modules/<feature>/` with `api/`, `application/`, `domain/`, `infrastructure/`.
2. Domain first: the entity and its invariants, the port interfaces, the feature's domain errors.
3. Infrastructure: the Prisma repository implementing the port, plus the mapper
   (`node-persistence`).
4. Application: one service per use case, owning the transaction boundary.
5. Api: the controller, the request DTO with validation decorators, the explicit response DTO
   (`nest-http-api`).
6. Module: providers, the port→implementation binding by token, a minimal `exports`.
7. Register the module in `app.module.ts`; register config it needs through `registerAsync`.
8. Tests at the depth the complexity band calls for (`v1rus-core:v1rus-qa`, `node-testing`).

## GraphQL

REST is the default surface (see this plugin's README design notes). When a project does run
GraphQL, resolvers occupy the `api` layer on exactly the same terms as controllers: thin, typed
input and output, no ORM access, the same application services underneath. A resolver that queries
Prisma directly reintroduces N+1 at field granularity, which is the failure mode GraphQL is famous
for; a dataloader per request does not fix a missing application layer.
