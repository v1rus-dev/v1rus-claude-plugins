---
paths:
  - "**/*DbContext.cs"
  - "**/Migrations/**/*.cs"
  - "**/Migrations/*.cs"
  - "**/*Configuration.cs"
  - "**/*Repository.cs"
---

# EF Core — rules for this file

Full detail in the `efcore-persistence` skill. What must hold in the file you are editing:

- **A `DbContext` is not thread-safe and holds one connection.** It is registered scoped and used by one
  logical operation at a time. **Never `Task.WhenAll` over queries on the same context**, never share it
  between concurrent requests, never capture it in a singleton — every one of those surfaces as the
  intermittent "A second operation was started on this context" exception, usually first in production.
- **A read that is not written back is `AsNoTracking()`** — otherwise every row is snapshotted into the
  change tracker, which is both memory and the reason an unrelated `SaveChangesAsync` writes something
  nobody asked it to.
- **Project to what you need.** `Select` into a DTO instead of loading the entity graph; a list endpoint
  that materialises full aggregates pays for columns and joins it never reads.
- **Lazy loading is off.** Load related data with an explicit `Include`, or project it. Lazy loading turns
  one list query into one query per row — the N+1 that is invisible in code review and obvious in the
  query log.
- Two or more collection `Include`s in one query multiply the rows (a cartesian explosion): use
  `AsSplitQuery()` deliberately, and know it is no longer one transaction-consistent snapshot.
- **Never let `IQueryable` escape this layer.** A repository returns materialised entities or DTOs, not a
  query — a leaked `IQueryable` is executed by a caller who does not know a connection is involved, after
  the scope may be disposed, and lets an outer layer compose a query the database cannot translate.
- Anything the provider cannot translate is evaluated **client-side after the rows arrive** — a C# method
  call, a local function, or a culture-sensitive string comparison inside a `Where` either throws or
  quietly downloads the table. Keep predicates expression-translatable.
- **Every async EF call takes the `CancellationToken`**: `ToListAsync(ct)`, `FirstOrDefaultAsync(ct)`,
  `SaveChangesAsync(ct)`.
- `SaveChangesAsync` is called **once per unit of work**, not per entity — one call is one transaction.
- `ExecuteUpdateAsync` / `ExecuteDeleteAsync` go straight to the database and **bypass the change tracker,
  concurrency tokens and any `SaveChanges` interceptor**. That is what they are for, but any entity already
  loaded in this context is now stale.
- Raw SQL is parameterised (`FromSql` with interpolation, or explicit parameters) — string concatenation
  into `FromSqlRaw` is SQL injection, and it is reachable from any endpoint that takes a filter.
- **A migration is reviewed like code, and checked in with the change that caused it.** Read the generated
  `Up`/`Down`: a column rename usually generates drop-plus-add, which silently deletes the data. Never
  edit an applied migration — add a new one. `EnsureCreated` is for throwaway tests only and cannot coexist
  with migrations.
- Mapping lives in an `IEntityTypeConfiguration<T>` per entity, not in a growing `OnModelCreating`. Domain
  types stay free of EF attributes so persistence choices do not become domain decisions
  (`dotnet-architecture`).
- Concurrency-sensitive rows carry a concurrency token, and `DbUpdateConcurrencyException` is handled into
  a 409 rather than a 500.
- **A retrying execution strategy and a manual transaction do not combine on their own** — wrap the whole
  transaction in `ExecuteAsync` on the strategy, or the retry replays half of it.
- Nothing here formats a message for a user and nothing here throws a transport exception outward: a
  storage failure is mapped to a domain error at this boundary (`dotnet-error-handling`).
