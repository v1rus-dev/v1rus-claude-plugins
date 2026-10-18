---
name: dotnet-architecture
description: "The v1rus ASP.NET Core solution shape: four projects (Api, Application, Domain, Infrastructure) with a dependency direction enforced by project references and an architecture test rather than by review, Domain free of EF Core and ASP.NET Core, Application owning use cases and the interfaces Infrastructure implements, Infrastructure holding EF Core and HTTP clients and being referenced only by the composition root, Api holding endpoints and the request and response contracts, plus the folder layout inside each project and the checklist for adding a feature slice. Load when creating a project or a feature, deciding which project a class belongs to, adding a project reference, reviewing a layer boundary, or setting up the solution."
---

# .NET Architecture

Four projects, one dependency direction. The direction is **checked by the compiler and by a test**, not
by review — a project reference that should not exist either does not compile or fails the architecture
test (see § Enforcing the boundaries).

## Solution layout

```
<Solution>.sln
Directory.Build.props          # shared compiler settings for every project
Directory.Packages.props       # central package management: every version, one place
.editorconfig
src/
  <Product>.Domain/            # entities, value objects, domain errors, domain services
  <Product>.Application/       # use cases, the ports Infrastructure implements, DTOs it owns
  <Product>.Infrastructure/    # EF Core (DbContext, configurations, migrations, repositories),
                               # typed HTTP clients, message bus, clock, file storage
  <Product>.Api/               # Program.cs, endpoint modules, request/response contracts,
                               # middleware, filters, auth policies, OpenAPI
tests/
  <Product>.UnitTests/
  <Product>.IntegrationTests/  # WebApplicationFactory + Testcontainers
  <Product>.ArchitectureTests/
```

The product name prefix comes from the project; never invent one. In a solution that already uses
different names, follow what is there (`v1rus-code-policies`).

## Dependency direction

```
Api ──▶ Application ──▶ Domain
 │                         ▲
 └──▶ Infrastructure ──────┘
              │
              └──▶ Application   (implements its ports)
```

Hard rules:

- **`Domain` references nothing.** Not EF Core, not ASP.NET Core, not `Microsoft.Extensions.*`, not a
  serialisation library. A `[Table]` or `[JsonPropertyName]` attribute in `Domain` means a storage or a
  transport decision has become a domain decision, and the next storage change is a domain change.
- **`Application` references `Domain` only.** It declares the ports it needs — `IOrderRepository`,
  `IPaymentGateway`, `IUnitOfWork` — as interfaces it owns, so the direction of the dependency is inverted
  and `Application` stays testable with no database.
- **`Infrastructure` implements those ports** and is referenced by **`Api` only for registration**. No
  Application or Domain code names an Infrastructure type; if a use case needs a new capability, the
  interface is added in `Application` first.
- **`Api` is the composition root and the transport.** It knows all three, and everything it knows about
  them is: how to register them and how to call a use case.
- **No project references `Api`.** A test project may, through `WebApplicationFactory` — that is the one
  case, and it is why `Program` needs to be reachable (`dotnet-testing`).

## What goes in which project

| Project | Contains | Never contains |
|---|---|---|
| `Domain` | entities with behaviour, value objects, the `DomainError` union, invariants, domain events | EF Core, ASP.NET Core, DTOs, JSON attributes, `DbContext`, `HttpClient` |
| `Application` | use-case classes, the port interfaces, application-level DTOs, validators, orchestration and transaction boundaries | `DbContext`, `IQueryable`, `HttpContext`, `HttpClient`, SQL, endpoint types |
| `Infrastructure` | `DbContext`, `IEntityTypeConfiguration<T>`, migrations, repository implementations, typed HTTP clients, `TimeProvider` binding, caching, messaging | endpoints, request/response contracts, business rules |
| `Api` | `Program.cs`, endpoint modules, request/response records, middleware, filters, auth policies, `ProblemDetails` mapping | business rules, EF queries, `HttpClient` calls |
| `*.Tests` | tests | production code |

**A request contract, an application DTO and a domain entity are three different types even when their
fields match today.** Collapsing them couples the wire format to the schema: the first optional field or
renamed column becomes a breaking API change. The duplication is the decoupling, not an oversight.

## Inside a project — folders by feature, not by pattern

```
src/<Product>.Application/Orders/
  CreateOrder/CreateOrderHandler.cs, CreateOrderCommand.cs, CreateOrderValidator.cs
  GetOrders/GetOrdersHandler.cs, GetOrdersQuery.cs
  Ports/IOrderRepository.cs
src/<Product>.Api/Endpoints/Orders/OrderEndpoints.cs, Contracts/CreateOrderRequest.cs
src/<Product>.Infrastructure/Persistence/Orders/OrderRepository.cs, OrderConfiguration.cs
```

A `Services/` folder holding thirty unrelated classes, or an `Interfaces/` folder holding every interface
in the solution, is the layout to avoid: it puts the things that change together furthest apart.

## Use cases — always a class, never a mediator by default

Each use case is a class with **one public entry point** (`Handle(command, ct)`), injected directly into
the endpoint that needs it. No mediator library by default — see the plugin README's design notes for the
trade-off. Cross-cutting concerns that a mediator pipeline would carry are covered here by endpoint
filters (validation, idempotency), middleware (logging, exception mapping) and DI decorators (caching,
retries), all of which keep a readable stack trace.

A use case that only forwards one call to one repository is a pass-through and should not exist — let the
endpoint call the repository port through a thin query handler instead of adding a layer that renames its
argument.

## Enforcing the boundaries

Project references do most of the work: `Domain` cannot see `Application` because there is no reference.
What references cannot catch is a **package** creeping into the wrong project, or `Api` calling
`Infrastructure` directly instead of going through a use case. An architecture test closes that:

```csharp
// tests/<Product>.ArchitectureTests — one fact per rule, named after the rule
[Fact]
public void Domain_has_no_dependency_on_infrastructure_or_framework()
{
    var forbidden = new[] { "Microsoft.EntityFrameworkCore", "Microsoft.AspNetCore", "<Product>.Infrastructure" };
    var referenced = typeof(Order).Assembly.GetReferencedAssemblies().Select(a => a.Name);
    Assert.Empty(referenced.Where(name => forbidden.Any(f => name!.StartsWith(f, StringComparison.Ordinal))));
}
```

Written with reflection over the assemblies as above, or with an architecture-testing package resolved
through the `v1rus-dependencies` gate — either way the rule fails the build rather than a review. Add one
test per rule in this skill's *Dependency direction* section, and add a test whenever a new rule is agreed.

## Adding a feature slice — checklist

1. `Domain`: the entity, its invariants and any new `DomainError` case.
2. `Application`: the use-case class, its command/query and result types, the validator, and any new port
   interface.
3. `Infrastructure`: the port implementation, the `IEntityTypeConfiguration<T>`, and the migration if the
   schema changed (`efcore-persistence`).
4. `Api`: the endpoint module, its request/response records, the auth policy, and the `Result` →
   `ProblemDetails` mapping (`aspnetcore-api`, `dotnet-error-handling`).
5. Registration: the `AddXxx` extension for the area, called from `Program.cs` (`dotnet-di`).
6. Configuration: the options class, bound and validated at startup, if the slice added settings
   (`dotnet-configuration`).
7. Tests, when the complexity band calls for them (`v1rus-qa`): the use case in unit tests, the endpoint
   in integration tests (`dotnet-testing`).
