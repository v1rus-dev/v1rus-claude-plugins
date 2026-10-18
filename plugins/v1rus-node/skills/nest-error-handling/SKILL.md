---
name: nest-error-handling
description: "Error handling across a v1rus NestJS service: a typed DomainError hierarchy thrown by the domain and application layers, one global exception filter mapping every error class to a stable RFC 9457 application/problem+json response, why throwing beats returning a Result inside a Nest request pipeline and where Result still wins, never leaking a stack trace or an internal message or a driver error string to the client, the catch-all branch that logs with the correlation id and returns an opaque 500, the validation-error shape, filter ordering and @Catch specificity, mapping Prisma and HTTP-client errors at the infrastructure boundary, and logging an error exactly once. Load when defining a domain error, writing or changing an exception filter, choosing a status code, deciding between throwing and returning, or reviewing what an endpoint reveals on failure."
---

# Error Handling

The language-level rules — `Error` subclassing, `cause` chaining, the `Result`-versus-throw principle
— belong to `v1rus-typescript:ts-error-handling`. This skill is how that lands inside a Nest request
pipeline, where the framework has already decided that failures travel as exceptions.

## Throw typed domain errors; do not build HTTP in the domain

```ts
// domain/errors.ts — no Nest import anywhere in this file
export abstract class DomainError extends Error {
  abstract readonly code: string;            // stable, machine-readable, part of the API contract
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = new.target.name;
  }
}

export class OrderNotFound extends DomainError {
  readonly code = 'ORDER_NOT_FOUND';
  constructor(readonly orderId: string) { super(`Order ${orderId} not found`); }
}

export class OrderAlreadyPaid extends DomainError {
  readonly code = 'ORDER_ALREADY_PAID';
  constructor(readonly orderId: string) { super(`Order ${orderId} is already paid`); }
}
```

- **The domain throws `OrderNotFound`, never `NotFoundException`.** `HttpException` is a transport
  concern; a domain that throws it cannot be reused by a queue consumer, a CLI or a gRPC handler, and
  it has quietly pinned a business rule to a status code.
- `message` is for operators. What the client keys on is `code` — a stable string that never changes
  meaning, even when the wording does.
- Wrap a lower-level failure with `cause`, never by string concatenation: the original stack survives
  and the log shows both frames.

## One filter owns the wire format

```ts
@Catch()
export class DomainExceptionFilter implements ExceptionFilter {
  constructor(private readonly logger: AppLogger, private readonly ctx: RequestContext) {}

  catch(error: unknown, host: ArgumentsHost): void {
    const res = host.switchToHttp().getResponse();
    const problem = toProblem(error, this.ctx.correlationId);

    if (problem.status >= 500) this.logger.error({ err: error, correlationId: this.ctx.correlationId }, 'unhandled');
    else this.logger.warn({ code: problem.code, correlationId: this.ctx.correlationId }, 'request failed');

    res.status(problem.status).type('application/problem+json').send(problem);
  }
}
```

The response shape is RFC 9457 (`application/problem+json`) with two additions the format allows:

```json
{
  "type": "https://errors.example.internal/order-already-paid",
  "title": "Order already paid",
  "status": 409,
  "detail": "Order 6f2… has already been paid",
  "instance": "/v1/orders/6f2…/payments",
  "code": "ORDER_ALREADY_PAID",
  "correlationId": "01HW…"
}
```

- **One mapping table, in one file.** Domain error class → status + title. A `switch` on
  `instanceof` or a static `Map` keyed by the error constructor — not a status code invented at each
  throw site.
- The mapping is part of the API contract: a `409` that becomes a `422` in a refactor breaks clients
  as surely as a renamed field, so it is covered by an e2e test (`node-testing`).
- Typical mapping: not-found → 404, invariant violated / conflicting state → 409, failed
  precondition on valid input → 422, unauthenticated → 401, unauthorised → 403, upstream unavailable
  → 503 with `Retry-After`, everything unrecognised → 500.

## Never leak the inside

The catch-all branch is where services leak. Non-negotiable:

- **No stack trace, no `error.message` of an unknown error, no driver text in the response.** A
  Postgres `duplicate key value violates unique constraint "users_email_key"` tells an attacker your
  schema; a Prisma error message can include the offending values.
- A 5xx body carries `title: "Internal Server Error"`, the status, and the **correlation id** —
  nothing else. The detail goes to the log under that same id, which is what makes support possible
  without making the error a disclosure.
- Validation failures (400) may name the fields, because the client sent them. They must not echo
  back a value that the client did not send, and must not include the raw `class-validator`
  constraint object, which exposes internal property names.
- `@Catch()` is ordered by specificity: register the specific filters before the catch-all, and keep
  exactly one catch-all. Two catch-alls means the wire format has two definitions.

## Map at the boundary, not at the top

Driver and transport errors are translated **inside `infrastructure`**, in the repository or client
that produced them, and leave as a `DomainError`:

```ts
try {
  await this.prisma.user.create({ data });
} catch (e) {
  if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === 'P2002') {
    throw new EmailAlreadyRegistered(data.email, { cause: e });
  }
  throw new RepositoryUnavailable('user.create failed', { cause: e });
}
```

A `PrismaClientKnownRequestError`, an `AxiosError` or an `undici` `TypeError` reaching the exception
filter means a layer boundary was skipped — the filter then has to guess a status from a library it
should not know about.

## Throw or return?

Inside a Nest request, **throw**. The pipeline — filters, interceptors, the transaction wrapper — is
built on exceptions, and a `Result` threaded through it has to be unwrapped and rethrown at the
controller anyway, so it buys a ceremony and not a guarantee.

A `Result` earns its place where the caller must handle both branches locally and a throw would be
control flow:

| Situation | Shape |
|---|---|
| A use case failing a request | `throw` a `DomainError` |
| Validating a batch where each item can fail independently (import, bulk job) | `Result` per item, so one bad row does not abort 999 good ones |
| A "check whether this is possible" query (`canCancel`) | a value, not an exception |
| A programmer error — broken invariant, unreachable branch, missing config | `throw` and let the process surface it; do not model it as a domain error |

## Log exactly once

The error is logged where it is **handled**, which for a request is the exception filter. A
`catch → log → rethrow` at every layer produces four stack traces for one failure and makes the log
useless at the moment it matters. If a layer logs and rethrows, it must add information the top
cannot reconstruct — and then it logs at `debug`, not `error`.

Unhandled rejections and uncaught exceptions are not part of this pipeline: they mean unknown process
state, are logged with full context, and the process exits (`node-runtime`).
