---
name: node-persistence
description: "Prisma as the data layer of a v1rus NestJS service: schema and naming conventions, the migrate dev / migrate deploy split and why db push and editing an applied migration are forbidden, the repository boundary that keeps Prisma types out of the domain, interactive transactions that cover the whole invariant and never wrap an HTTP call, connection-pool sizing and the exhaustion symptoms, the N+1 that a loop of awaits creates and how to batch it, selecting columns instead of whole rows, Decimal and BigInt not surviving JSON, unique-constraint races answered by catching P2002 rather than checking first, the PrismaService lifecycle and shutdown, and migration testing. Load when writing a repository, changing the Prisma schema, adding a migration, wrapping writes in a transaction, diagnosing a slow or pool-starved endpoint, or reviewing data access."
---

# Persistence with Prisma

Prisma is the default data layer for this stack (see the plugin README design notes). Everything
below assumes it; a project on a different ORM keeps the *boundaries* and swaps the mechanics.

## The repository boundary

**Prisma types stop at `infrastructure`.** No `Prisma.UserGetPayload`, no generated model type, no
`PrismaClientKnownRequestError` in `application` or `domain`. The port lives in `domain/ports`, the
implementation in `infrastructure/persistence`, and a mapper per aggregate converts both directions.

```ts
@Injectable()
export class PrismaOrderRepository implements OrderRepository {
  constructor(private readonly prisma: PrismaService) {}

  async findById(id: OrderId): Promise<Order | null> {
    const row = await this.prisma.order.findUnique({
      where: { id: id.value },
      include: { lines: true },
    });
    return row ? toDomain(row) : null;
  }
}
```

Why it is worth the mapper: a generated model is the *table*, and a domain entity is the *concept*.
When they are the same object, every column rename is a refactor of the business rules, and every
business rule has to be expressed in terms the ORM can round-trip. The mapper is also the only place
where `Decimal` and `BigInt` become domain value objects rather than leaking to the wire.

`PrismaService extends PrismaClient` lives in `core/prisma`, is a singleton, connects in
`onModuleInit` and disconnects in `onModuleDestroy`. **One client per process** — a second
`new PrismaClient()` anywhere opens a second pool.

## Schema conventions

- Singular model names in PascalCase, mapped to the table the database actually wants with `@@map`
  and `@map`. Renaming a model is then a schema-only change.
- Every foreign key has an index — Prisma does not create one for you on the referencing side in
  every case, and the missing index is invisible until the table is large.
- `createdAt`/`updatedAt` on anything auditable; `@default(now())` and `@updatedAt`.
- Money is `Decimal`, never `Float`. Ids are `Uuid`/`String` or `BigInt` — decided once, per the
  serialization consequence below.
- Enums in the schema mirror the domain enum; a free-text status column is a validation hole.
- A `@@unique` constraint is the enforcement of an invariant. An application-level "check then
  insert" is not — see the race below.

## Migrations

| Command | When |
|---|---|
| `prisma migrate dev` | local development only — creates and applies the migration, may reset |
| `prisma migrate deploy` | CI and every deployed environment — applies pending migrations, never resets |
| `prisma db push` | **never** outside a throwaway prototype — it mutates the schema with no migration history, so environments silently diverge |

- **Never edit a migration that has been applied anywhere.** The checksum is recorded; a changed file
  makes `migrate deploy` fail on the next deploy, and if it does not, the environments now differ.
  Fix forward with a new migration.
- A destructive migration (drop column, narrow a type, add a `NOT NULL` without a default) is
  **two deploys**: expand — backfill — contract. One deploy means the old code is still running
  against the new schema during the rollout.
- Review the generated SQL. Prisma writes a plausible migration, not necessarily the one you want:
  an index created without `CONCURRENTLY` locks the table on Postgres, and a rename is emitted as
  drop-plus-create — which is data loss.
- The migration is part of the change, committed with it, and a schema bump gets a migration test
  (`node-testing`).

## Transactions

```ts
await this.prisma.$transaction(async (tx) => {
  const order = await tx.order.update({ where: { id }, data: { status: 'PAID' } });
  await tx.ledgerEntry.create({ data: toLedgerEntry(order) });
});
```

- **The transaction covers the invariant, not one statement.** If a crash between two writes leaves a
  state no reader should see, they are one transaction. A paid order with no ledger entry is exactly
  that state.
- **Nothing slow inside.** No `fetch`, no queue publish that waits on a broker, no retry loop. A
  transaction holds a pooled connection and row locks; a 3-second external call inside one turns a
  10-connection pool into a deadlock at 11 concurrent requests. Publish *after* commit — or use the
  outbox (`node-background-jobs`) when the publish must be atomic with the write.
- Pass `tx` down explicitly. A repository that grabs `this.prisma` while the caller holds a
  transaction runs **outside** it, and the two writes commit independently — which looks correct in
  every test that does not crash halfway.
- Set `timeout` and `maxWait` deliberately; the defaults are short and a silent
  `Transaction already closed` under load is the symptom.
- Set the isolation level where it matters. Read-committed (the Postgres default) does not prevent
  the read-modify-write race in "read the balance, subtract, write it back" — that needs
  `SERIALIZABLE` with a retry on serialization failure, or an atomic `update ... set x = x - n` with
  a guard condition, which is usually the better answer.

## N+1 and over-fetching

```ts
// N+1 — one query per order, serialised
for (const order of orders) {
  order.customer = await this.prisma.customer.findUnique({ where: { id: order.customerId } });
}

// one query
const customers = await this.prisma.customer.findMany({
  where: { id: { in: orders.map((o) => o.customerId) } },
});
```

- A loop with an `await` inside is an N+1 by construction. Batch with `in`, or let Prisma do it with
  `include`/`select` on the relation.
- `include` on a to-many relation inside a list query is itself a fan-out — check what it actually
  emits before assuming it is one query.
- **`select` the columns you return.** `findMany` with no `select` fetches every column of every row,
  including the large text blob that no endpoint reads.
- Paginate by cursor on a stable, indexed, unique-tie-broken ordering. Deep `skip` scans everything
  it skips, and offset pagination shifts under concurrent inserts.
- Turn on Prisma query logging in development and read it. "It felt fast locally" with 20 rows is not
  evidence about 200 000.

## Connection pool

The pool is a budget: `connection_limit` × replica count must stay under the database's `max_connections`,
with headroom for migrations and for whatever else connects. Every long transaction removes a
connection from that budget for its whole duration. Pool exhaustion shows up as
`Timed out fetching a new connection from the connection pool` — which is almost never a reason to
raise the limit and almost always a slow query or a transaction holding a connection across I/O.
Behind a serverless or per-request-process deployment, put a pooler (PgBouncer, or the platform's)
in front and set the Prisma URL accordingly.

## Races and constraints

Do not "check then insert":

```ts
// racy: two concurrent requests both see no row, both insert
if (await this.prisma.user.findUnique({ where: { email } })) throw new EmailAlreadyRegistered(email);
await this.prisma.user.create({ data: { email } });
```

Let the database arbitrate: keep the `@@unique`, insert, and catch `P2002`, mapping it to the domain
error (`nest-error-handling`). Same for "increment if under limit" — express it as a conditional
`updateMany` and check the affected count, not as read-then-write.

## Serialization traps

`Prisma.Decimal` and `BigInt` do not survive `JSON.stringify` — `BigInt` throws
`Do not know how to serialize a BigInt`. Convert in the mapper (`Decimal` → a string or a money value
object, `BigInt` → a string) rather than installing a global `BigInt.prototype.toJSON` patch, which
hides the problem until a downstream consumer parses a number and loses precision.

`null` versus `undefined` is a semantic difference in Prisma: in an `update`, `undefined` means "do
not touch this column" and `null` means "set it to NULL". A partial-update DTO that spreads
`undefined` for absent fields is therefore correct — and one that defaults them to `null` silently
wipes columns.
