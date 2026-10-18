---
name: dotnet-di
description: "Dependency injection in v1rus ASP.NET Core services: the three lifetimes and what each is actually for, the captive dependency that makes a scoped DbContext a de-facto singleton shared by every request, resolving a scope with IServiceScopeFactory inside a singleton or a BackgroundService, ValidateScopes and ValidateOnBuild so the mistake fails at startup instead of under load, one AddXxx extension per area called from Program.cs, constructor injection only with no service locator, keyed services and decorators, and who owns disposal of an injected dependency. Load when registering a service, choosing between singleton scoped and transient, writing a hosted or background service, wiring a new feature module, or when a dependency needs to be resolved somewhere there is no constructor."
---

# Dependency Injection

The built-in container. Anything it cannot do — decoration, assembly scanning — is a package decision
through the `v1rus-dependencies` gate, not a reason to hand-roll a locator.

## One extension per area, called from the composition root

```csharp
// Program.cs — reads as a table of contents
builder.Services
    .AddApiServices(builder.Configuration)
    .AddApplicationServices()
    .AddPersistence(builder.Configuration)
    .AddOrderModule();
```

```csharp
// Infrastructure/DependencyInjection.cs
public static IServiceCollection AddPersistence(this IServiceCollection services, IConfiguration configuration)
{
    services.AddDbContext<AppDbContext>(options => options.UseNpgsql(configuration.GetConnectionString("Default")));
    services.AddScoped<IOrderRepository, OrderRepository>();
    services.AddScoped<IUnitOfWork>(sp => sp.GetRequiredService<AppDbContext>());
    return services;
}
```

An area extension registers **only that area**. `Api` is the only project that calls the `Infrastructure`
extension, and it does so to register — never to use a type from it (`dotnet-architecture`).

**Nothing calls `BuildServiceProvider()` by hand.** It builds a second container: the singletons in it are
different objects from the ones the app uses, and everything registered in it leaks. When a registration
genuinely needs another service, use the factory overload (`sp => ...`) as above.

## Lifetimes

| Lifetime | Use for | The failure when it is wrong |
|---|---|---|
| `Scoped` | **default** for anything touching a request: `DbContext`, repositories, use-case handlers, anything carrying the caller's identity | resolved from a singleton, it becomes a singleton — see below |
| `Singleton` | genuinely stateless or process-wide: `TimeProvider`, `IMemoryCache`, options, a typed `HttpClient`'s handler chain (managed by the factory), a background worker's own state | holding mutable state without synchronisation is a race that only appears under load |
| `Transient` | cheap, stateless, short-lived helpers | a transient `IDisposable` resolved from the root container is **never** disposed until the app exits — a slow leak |

Default to `Scoped` in a web app and justify anything else.

## The captive dependency

**A dependency resolved into a longer-lived object lives as long as that object.** A `DbContext` injected
into a singleton is created once and shared by every concurrent request from then on — which is both a
threading violation (`rules/efcore.md`) and a change tracker that grows for the lifetime of the process.
It works perfectly in development and fails intermittently in production.

The same mistake in its usual disguises: a scoped service injected into middleware's **constructor**
(middleware is constructed once — take it as an `InvokeAsync` parameter instead); a scoped service in an
`IHostedService` or `BackgroundService` constructor; a scoped service injected into a singleton endpoint
filter; `IOptionsSnapshot<T>` (scoped) injected into a singleton (`dotnet-configuration`).

Make the container catch it:

```csharp
builder.Host.UseDefaultServiceProvider(options =>
{
    options.ValidateScopes = true;   // on by default in Development only — turn it on everywhere
    options.ValidateOnBuild = true;  // fail at startup, not at the first request that needs it
});
```

## Resolving a scope where there is no request

A `BackgroundService` runs outside any request, so it has no scope. Inject `IServiceScopeFactory` and
create one **per unit of work** — not one for the lifetime of the service, which is the same captive
dependency with extra steps:

```csharp
public sealed class OutboxPublisher(IServiceScopeFactory scopeFactory, ILogger<OutboxPublisher> logger)
    : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            using var scope = scopeFactory.CreateScope();
            var dispatcher = scope.ServiceProvider.GetRequiredService<IOutboxDispatcher>();
            await dispatcher.DispatchPendingAsync(stoppingToken);
            await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
        }
    }
}
```

Also true here: an unhandled exception in `ExecuteAsync` stops the service silently by default — catch,
log and decide whether to continue or to stop the host deliberately. And a long synchronous stretch before
the first `await` blocks application startup.

## Constructor injection only

Dependencies arrive through the constructor (primary constructors are fine). **No class calls
`IServiceProvider.GetRequiredService<T>()` inside its own body** — that hides the dependency from the
signature, defeats `ValidateOnBuild`, and makes the class untestable without a container.

The permitted exceptions are the boundaries where there is no constructor to inject into: the composition
root and the registration extensions, a scope created in a background service as above, and a minimal-API
handler, which takes its dependencies as **parameters** — that is injection, not a locator.

`IHttpContextAccessor` is not an escape hatch: reading the caller's identity through it inside
`Application` makes the class untestable and null at every non-request call site. Pass the identity in.

## Registration details that bite

- **Register the interface, resolve the interface.** Registering only the concrete type and injecting the
  interface elsewhere throws at the first resolution — `ValidateOnBuild` turns that into a startup failure.
- Registering the same interface twice: the **last** registration wins for a single resolve, and
  `IEnumerable<T>` gets all of them. `TryAdd*` when a default should not overwrite an existing choice.
- **Keyed services** (.NET 8+) are the supported way to have two implementations of one interface chosen by
  name — better than an enum-switching factory, and resolvable with `[FromKeyedServices]`.
- **Disposal is the container's job** for anything it created. Never dispose an injected dependency: it is
  shared, and disposing it breaks every later request (`rules/csharp.md`).
- A decorator (caching, retry, logging around a port) is registered by resolving the inner implementation
  in a factory, or with a decoration package resolved through the dependency gate. It keeps the
  cross-cutting concern out of the implementation without a mediator pipeline.

## Tests

Unit tests construct the class under test with fakes directly — never through a container. Integration
tests get the real graph from `WebApplicationFactory` and replace only what must be replaced, with
`RemoveAll<T>()` before adding the substitute so the original registration does not win
(`dotnet-testing`).
