---
name: efcore-persistence
description: "Persistence with EF Core in a v1rus ASP.NET Core service: DbContext and configurations and migrations living in Infrastructure with Domain entities kept free of EF attributes, one IEntityTypeConfiguration per entity, repositories returning materialised entities or DTOs and never an IQueryable, AsNoTracking for reads and projections instead of whole aggregates, explicit Include with lazy loading off, the cartesian explosion and AsSplitQuery, one SaveChangesAsync per unit of work, migrations reviewed for data-destroying renames and applied deliberately rather than at startup, concurrency tokens mapped to 409, and the retrying execution strategy that breaks a manual transaction. Load when adding or changing an entity mapping, writing a query or a repository, creating or reviewing a migration, or diagnosing an N plus one or a change-tracking surprise."
---

# EF Core Persistence

The per-file rules are `${CLAUDE_PLUGIN_ROOT}/rules/efcore.md` — injected automatically before an edit to
a `DbContext`, a configuration, a migration or a repository, and read directly when reviewing. This skill
is the design layer above them.

## Where it lives

Everything EF Core is in **`Infrastructure`**: the `DbContext`, the configurations, the migrations, the
repository implementations. `Domain` entities are plain classes with behaviour and **no EF attributes**
(`dotnet-architecture`) — the moment a `[Column]` appears in `Domain`, a storage decision has become a
domain decision.

```
Infrastructure/Persistence/
  AppDbContext.cs
  Configurations/OrderConfiguration.cs, OrderLineConfiguration.cs
  Repositories/OrderRepository.cs
  Migrations/
```

Mapping is one `IEntityTypeConfiguration<T>` per entity, applied with
`modelBuilder.ApplyConfigurationsFromAssembly(typeof(AppDbContext).Assembly)`. A growing `OnModelCreating`
is the alternative to avoid: it becomes the file everyone edits and nobody reads.

Persistence-only concerns that the domain must not carry — a private backing field for a collection, a
shadow property, an owned-type mapping for a value object, the concurrency token — are expressed in the
configuration, which is exactly what it is for.

## The repository contract

A repository takes and returns **domain types**, and it materialises. It does not return `IQueryable`,
does not take an `Expression<Func<T, bool>>` from the caller, and does not expose the `DbContext`:

```csharp
public interface IOrderRepository            // declared in Application/Orders/Ports
{
    Task<Result<Order>> GetAsync(OrderId id, CancellationToken cancellationToken);
    Task<IReadOnlyList<Order>> ListForCustomerAsync(CustomerId id, Paging paging, CancellationToken cancellationToken);
    void Add(Order order);                    // no await — the write happens at SaveChanges
}
```

A leaked `IQueryable` is executed by a caller who does not know a connection is involved, possibly after
the scope is disposed, and lets an outer layer compose a predicate the provider cannot translate. A
predicate parameter is the same leak in a narrower shape.

**Read-heavy queries do not have to go through a repository.** A query handler in `Application` that needs
a projection for one screen can take a narrow read port implemented in `Infrastructure`
(`IOrderReadStore`) and return a DTO — better than growing the aggregate repository a method per screen.
What does not change: the query is written in `Infrastructure`.

## Transactions and the unit of work

`SaveChangesAsync` is called **once per request**, by the use case, at the end — one call is one
transaction. A repository that saves inside each method turns one logical operation into several
transactions, and a partial failure leaves the data half-written.

```csharp
public async Task<Result<OrderId>> Handle(CreateOrderCommand command, CancellationToken cancellationToken)
{
    var order = Order.Create(command.CustomerId, command.Lines);
    orders.Add(order);
    await unitOfWork.SaveChangesAsync(cancellationToken);   // the only commit
    return order.Id;
}
```

An explicit `BeginTransactionAsync` is needed only when more than one `SaveChanges` or a raw command must
commit together — and with a retrying execution strategy configured (`EnableRetryOnFailure`), a manual
transaction **must** be wrapped in `strategy.ExecuteAsync(...)`, or a retry replays half of it.

## Reading

- **`AsNoTracking()` on every read that is not written back.** Tracking a list endpoint's rows costs
  memory and makes a later `SaveChanges` write things nobody asked it to.
- **Project instead of loading.** `Select` into the DTO the caller needs; a list endpoint materialising
  full aggregates pays for every column and join it never reads. A projection is also implicitly
  no-tracking.
- **Lazy loading stays off** (do not install the proxies package). Load related data with an explicit
  `Include`, or project it. With lazy loading on, one list query becomes one query per row — invisible in
  review, obvious in the query log.
- Two collection `Include`s in one query multiply rows. Use `AsSplitQuery()` deliberately, knowing it
  gives up the single-snapshot consistency of one query.
- Paging is `OrderBy` + `Skip`/`Take` — `Skip` without a deterministic `OrderBy` returns overlapping pages
  as the table changes, and the database is not obliged to be stable without it.
- Anything the provider cannot translate is evaluated **after the rows arrive**: a C# helper method, a
  local function, or `string.Equals(a, b, StringComparison.OrdinalIgnoreCase)` inside a `Where` either
  throws or quietly downloads the table. Collation belongs in the mapping, not in the predicate.

## Writing

- Load, mutate, save: the change tracker writes what changed. Do not read an entity, construct a new one
  with the same id and `Update` it — that writes every column and clobbers concurrent changes.
- `ExecuteUpdateAsync` / `ExecuteDeleteAsync` are the right tool for a bulk operation and **bypass the
  change tracker, concurrency tokens and `SaveChanges` interceptors**. Any entity already loaded in the
  context is stale afterwards.
- Concurrency-sensitive rows carry a token (`IsRowVersion()`, or a `xmin` concurrency token on
  PostgreSQL). `DbUpdateConcurrencyException` becomes a 409 `Conflict`, never a 500
  (`dotnet-error-handling`).
- Raw SQL is parameterised. `FromSqlRaw` with a concatenated string is SQL injection reachable from any
  endpoint that takes a filter; `FromSql` with an interpolated string parameterises it for you.

## Migrations

- A migration is **generated, then read**, and checked in with the change that caused it. The generator
  cannot see intent: a property rename usually emits drop-plus-add, which deletes the column's data. Fix
  the migration to a rename, or write the data move explicitly.
- **Never edit an applied migration** — add a new one. Editing one that has run leaves every environment
  in a different state from the model snapshot.
- **Never migrate at application startup** in a deployed environment: every instance races the same
  schema change, and a rollback has no path. Migration is a deployment step (`dotnet ef database update`,
  a generated idempotent script, or a one-shot job). A dev-only `MigrateAsync` behind an environment check
  is acceptable and must be written as such.
- `EnsureCreated` and migrations cannot coexist — `EnsureCreated` is for a throwaway test database only.
- A schema change that data depends on gets a **migration test**: create the database at the previous
  migration, seed, migrate, assert the data survived. This is the one place where "it compiles" proves
  nothing (`dotnet-testing`).
- Schema changes are additive first when the deployment is rolling: add the column, deploy the code that
  writes it, backfill, then remove the old one in a later release. A single migration that renames and a
  single deploy that switches means the old instances are broken for the length of the rollout.

## Registration

`AddDbContext<AppDbContext>` registers it **scoped** — which is what it must be (`dotnet-di`). Do not
register it as a singleton to "save allocations", and do not resolve it inside a singleton. `AddDbContextPool`
is a performance option, not a lifetime change, and it requires that the context has no injected
per-request state.

Connection strings come from configuration, never from a literal, and never from `appsettings.json` in a
deployed environment (`dotnet-configuration`).
