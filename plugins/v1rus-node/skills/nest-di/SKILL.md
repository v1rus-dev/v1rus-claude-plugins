---
name: nest-di
description: "NestJS dependency injection as it actually behaves: constructor injection only, injecting an interface through a Symbol token so the application layer never names its infrastructure, the four custom-provider forms (useClass, useValue, useFactory, useExisting) and when each is right, provider scopes and the scope-bubbling trap where one Scope.REQUEST provider makes its whole injection chain request-scoped, using AsyncLocalStorage request context instead, async initialisation in onModuleInit rather than the constructor, releasing resources in onModuleDestroy, diagnosing and removing circular provider dependencies instead of papering over them with forwardRef, ModuleRef as a last resort, and overrideProvider in tests. Load when registering a provider, injecting a dependency, choosing a scope, hitting a Nest resolution or circular-dependency error, or wiring a test module."
---

# NestJS Dependency Injection

## Constructor injection, always

```ts
@Injectable()
export class PlaceOrder {
  constructor(
    @Inject(ORDER_REPOSITORY) private readonly orders: OrderRepository,
    private readonly clock: Clock,
    private readonly logger: AppLogger,
  ) {}
}
```

Property injection hides the dependency from the signature: the type no longer tells a reader — or a
test — what the class needs, and the field is `undefined` in any construction path that is not Nest's.

## Inject interfaces, not classes

An application service naming `PrismaOrderRepository` in its constructor has just made the domain
depend on the ORM. Bind a port to an implementation with a token:

```ts
// domain/ports/order.repository.ts
export const ORDER_REPOSITORY = Symbol('OrderRepository');
export interface OrderRepository {
  findById(id: OrderId, signal?: AbortSignal): Promise<Order | null>;
  save(order: Order): Promise<void>;
}

// orders.module.ts
providers: [{ provide: ORDER_REPOSITORY, useClass: PrismaOrderRepository }],
```

An interface has no runtime representation, so the token is what Nest resolves — a `Symbol` or an
exported `const string`, declared **next to the interface in `domain`**, never re-declared per module.
A class token (`useClass` with the class as the key) is fine only when the class *is* the contract:
a pure helper with no alternative implementation and nothing to fake.

## The four provider forms

| Form | Use for | Watch out |
|---|---|---|
| `useClass` | binding a port to its implementation | the class must be injectable itself |
| `useValue` | a literal, a config object, a test double | not instantiated by Nest — its own deps are not injected |
| `useFactory` | construction that needs other providers or async setup | declare `inject: [...]`; an `async` factory blocks module init until it resolves |
| `useExisting` | a second token aliasing an already-registered provider | it is an alias, not a second instance |

`useFactory` with `inject` is how an infrastructure client gets its typed config without any layer
reading `process.env` (`node-configuration`).

## Scopes — and the trap

| Scope | Instances |
|---|---|
| `DEFAULT` (singleton) | one per application. **This is the default you keep.** |
| `REQUEST` | one per incoming request, plus a new instance of everything above it in the chain |
| `TRANSIENT` | a new instance per consumer |

**Scope bubbles upward.** If `AuditRepository` is `Scope.REQUEST`, then every service injecting it is
request-scoped, and so is the controller injecting that service — the whole chain is constructed on
every request. On a hot path that is measurable, and it silently changes lifecycle assumptions: a
cache field on a service that "obviously" persists now resets per request.

So: **do not reach for request scope to get request data.** Use an `AsyncLocalStorage`-backed request
context registered as a singleton:

```ts
@Injectable()
export class RequestContext {
  private readonly als = new AsyncLocalStorage<{ correlationId: string; userId?: string }>();
  run<T>(store: { correlationId: string; userId?: string }, fn: () => T): T {
    return this.als.run(store, fn);
  }
  get correlationId(): string | undefined { return this.als.getStore()?.correlationId; }
}
```

A middleware or interceptor opens the scope once per request; everything downstream — including a
logger and an outbound HTTP client — reads it without changing its own lifetime
(`node-observability`). Genuine request scope is for the rare provider that must be constructed from
request data and cannot be handed it as an argument; when you use it, state the cost in the plan.

## Lifecycle

- **Constructors do not do work.** No I/O, no `await` (they cannot), no floating promise to "warm up"
  in the background — that leaves the provider half-built and the failure unattributable. Connect,
  load, subscribe in `onModuleInit`.
- **`onModuleDestroy` releases everything the provider acquired**: connections, intervals, queue
  workers, subscriptions, open streams. It only runs if `app.enableShutdownHooks()` was called in
  `main.ts` — without it, every deploy is a hard kill (`node-runtime`).
- `onApplicationBootstrap` runs after *all* modules are initialised; use it when your startup work
  depends on another module being ready.

## Circular provider dependencies

Same diagnosis as circular modules (`nest-architecture`): the cycle means a third concept wants to
exist. Extract it, or invert one edge with an event. `forwardRef(() => Other)` inside `@Inject` keeps
the cycle and adds a failure mode — during construction one side sees a partially built instance, so
touching it from a constructor throws a `Cannot read properties of undefined` that points at the
wrong file.

When Nest reports `Nest can't resolve dependencies of X (?, Y)`, read the `?`: it is the positional
index of the dependency it could not find. The cause is nearly always one of three things — the
provider is not in `providers`, it is in another module that does not `export` it, or the token in
`@Inject` is not the token used in `provide`.

## `ModuleRef` — last resort

`moduleRef.get(TOKEN)` resolves outside the constructor. It is service location: the dependency is
invisible in the signature and unavailable to a type check. It is justified for genuinely dynamic
resolution (picking a strategy implementation by a runtime key) and for resolving a request-scoped
provider from a singleton (`moduleRef.resolve`). Anywhere else it is a constructor dependency that
lost its way. Prefer a registered map of strategies keyed by an enum over `get` by a computed token.

## Tests

Unit-test a service by constructing it directly: `new PlaceOrder(fakeRepo, fixedClock, nullLogger)`.
It is faster, it needs no Nest, and a missing dependency is a compile error.

Use `Test.createTestingModule` when the wiring itself is under test, or for an e2e app, and override
at the token:

```ts
const moduleRef = await Test.createTestingModule({ imports: [OrdersModule] })
  .overrideProvider(ORDER_REPOSITORY)
  .useValue(new InMemoryOrderRepository())
  .compile();
```

Override the **token**, not the class. Overriding `PrismaOrderRepository` when the binding is by
`ORDER_REPOSITORY` compiles, runs, and quietly uses the real repository. Details: `node-testing`.
