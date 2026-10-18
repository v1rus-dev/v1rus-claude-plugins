---
name: nest-http-api
description: "The HTTP surface of a v1rus NestJS service: thin controllers, request DTO classes behind a global ValidationPipe configured with whitelist and forbidNonWhitelisted so unknown properties are stripped rather than passed through, explicit response DTOs instead of returning a Prisma model or domain entity, why implicit type conversion in the pipe is a trap, URI API versioning, pagination and idempotency conventions, the guard/interceptor/pipe/filter execution order, the @Res() escape hatch that disables the response pipeline, OpenAPI decorators that stay in sync, and the security defaults (CORS, helmet, body size limits, rate limiting). Load when adding or changing an HTTP endpoint, writing a DTO, configuring the validation pipe, designing a response shape, versioning an API, or reviewing a controller."
---

# NestJS HTTP API

## A controller is a mapping, not a place to think

```ts
@Controller({ path: 'orders', version: '1' })
export class OrdersController {
  constructor(private readonly placeOrder: PlaceOrder) {}

  @Post()
  @HttpCode(HttpStatus.CREATED)
  async create(@Body() body: CreateOrderRequest): Promise<OrderResponse> {
    const order = await this.placeOrder.execute(toCommand(body));
    return OrderResponse.from(order);
  }
}
```

Route, status code, input DTO, output DTO, one call. Business rules, persistence, orchestration of
two services, transaction boundaries — all of that lives in the application service
(`nest-architecture`). A controller that grew a second `await` on a repository has grown a use case
that has nowhere to live.

## Validation — the pipe must strip, not just check

```ts
app.useGlobalPipes(new ValidationPipe({
  whitelist: true,              // drop properties with no decorator
  forbidNonWhitelisted: true,   // …and reject the request that sent them
  transform: true,              // produce an instance of the DTO class, not a plain object
  forbidUnknownValues: true,
}));
```

- **Without `whitelist`, validation is a lie.** The pipe checks the fields you declared and passes
  every undeclared field through untouched — so `{ email, isAdmin: true }` validates, and a service
  that spreads the DTO into a create call has just accepted a privilege escalation. `whitelist`
  strips; `forbidNonWhitelisted` turns the strip into a 400 so the client learns.
- **`transform: true` is required** for `@Type`-decorated nested objects and arrays to become class
  instances; without it a nested DTO is a plain object and its decorators never run.
- **`enableImplicitConversion` is a trap.** It makes `?limit=abc` become `NaN` instead of failing,
  and coerces `"false"` to `true` for a boolean. Declare the conversion explicitly per field with
  `@Type(() => Number)` plus `@IsInt()`, or use `ParseIntPipe` / `ParseBoolPipe` on the parameter.
- Params and queries are validated too. `@Param('id', ParseUUIDPipe)` is the difference between a
  404 and a driver error on a malformed id.
- A DTO is a **class**, because the decorators are runtime metadata — an `interface` or a `type`
  cannot carry them. The principle behind validating at the boundary at all is
  `v1rus-typescript:ts-boundaries-validation`; this is how it lands on a controller. Where there is
  no class to decorate — queue payloads, external API responses, the env — use `zod`, the default
  that layer names, rather than inventing a second decorator surface.

**Which mechanism validates a request body.** In a standalone service the decorated DTO class is the
default, as above. In a repository that also ships a web app, the shared contract schema is the
request validator — a zod validation pipe on the endpoints the web app consumes — and the DTO class
is **not** written again for those endpoints: one declaration of the shape, validated once, is the
entire point of the contract package. `v1rus-fullstack:api-contract` owns that case and states the
rule; endpoints outside the contract (an internal webhook, an admin route no client of the contract
calls) keep the DTO class.

## Responses — map explicitly

**Never return a persistence model or a domain entity from a handler.** A Prisma model publishes
whatever anyone adds to that table later; the `passwordHash` column added in another sprint ships to
every client of the endpoint on the day it is created, and no test fails.

```ts
export class OrderResponse {
  @ApiProperty() readonly id!: string;
  @ApiProperty() readonly status!: OrderStatus;
  @ApiProperty({ type: [OrderLineResponse] }) readonly lines!: OrderLineResponse[];

  static from(order: Order): OrderResponse { /* explicit field mapping */ }
}
```

`ClassSerializerInterceptor` with `@Expose`/`@Exclude` is an acceptable second route **when the
response class is one you own** and `excludeExtraneousValues` is on. `@Exclude()` sprinkled on a type
you did not define is opt-out security: the next field added is exposed by default.

Conventions to keep stable across the service:

- **Dates** are ISO-8601 UTC strings. A `Date` serialises differently through a custom serializer
  than through `JSON.stringify`, and a client parsing local time is a bug found in another timezone.
- **Money and large ids** are strings on the wire. `Prisma.Decimal` and `BigInt` do not survive
  `JSON.stringify` — `BigInt` throws outright. Convert in the mapper, not in a global hack.
- **Collections** return an envelope: `{ items, nextCursor }` for cursor pagination (the default —
  stable under concurrent inserts) or `{ items, page, pageSize, total }` for offset pagination when
  the client genuinely needs page numbers. Never a bare array: there is nowhere to add the cursor
  later without a breaking change.
- **Errors** have one shape, produced by the exception filter (`nest-error-handling`). A handler
  never builds an error body.

## Versioning

Enable versioning in `main.ts` (`app.enableVersioning({ type: VersioningType.URI })`) from day one,
even with a single version — retrofitting a prefix onto live routes is a client migration. URI
versioning is the default: visible in logs, in a browser and in a curl, and trivially routable at the
gateway. Version at the **controller**, not at the handler, and keep the old version delegating to
the same application service until it is retired.

## Pipeline order

```
middleware → guard → interceptor (pre) → pipe → handler → interceptor (post) → exception filter
```

- **Authorisation is a guard.** A handler whose first three lines check a role has put the rule where
  no other handler can reuse it and no test can target it.
- A guard returns a boolean or throws. It does not write, and it does not mutate the response.
- An interceptor that maps the response must rethrow on error; swallowing turns a 500 into a 200 with
  an empty body.
- **`@Res()` opts the handler out of everything after it** — interceptors and the serializer stop
  applying, and Nest no longer sends the response for you. Use `@Res({ passthrough: true })` when you
  only need to set a header or a cookie, and reserve the full escape hatch for streaming and SSE.

## Security defaults

Set once in `main.ts`, not per controller: CORS with an explicit origin allowlist (never `*` with
credentials), security headers (`helmet`), a JSON body size limit small enough that an oversized
request is rejected by the parser rather than by your heap, a global rate limit for unauthenticated
routes, and compression only if a proxy is not already doing it. A file upload is streamed to its
destination with a size and MIME allowlist, never buffered whole (`node-runtime`).

## OpenAPI

Generate the spec from the DTOs (`@nestjs/swagger`); a hand-maintained spec diverges within a sprint.
The CLI plugin infers most decorators from the TypeScript types, so `@ApiProperty` is needed mainly
for what the type cannot express — enums, examples, nullability, polymorphic unions. Document the
error shape once as a shared response and reference it; publishing the generated spec as a build
artifact is what lets the `v1rus-fullstack` layer derive client types from it rather than from
hand-copied interfaces.
