---
name: aspnetcore-api
description: "How an HTTP surface is built in a v1rus ASP.NET Core service: minimal APIs organised as endpoint modules on route groups rather than controllers, named static handlers instead of inline lambdas, request and response records owned by the Api project and never a domain or EF entity on the wire, typed results and declared status codes so OpenAPI matches reality, validation as an endpoint filter returning ProblemDetails, authorization as a named policy attached to the group, the middleware order that silently changes behaviour when it is wrong, and API versioning and pagination defaults. Load when adding or changing an endpoint, writing Program.cs, adding middleware or a filter, designing a request or response contract, or reviewing an HTTP surface. Do NOT load for EF Core query behaviour (efcore-persistence) or for the Result-to-error mapping itself (dotnet-error-handling)."
---

# ASP.NET Core API

The per-file rules are `${CLAUDE_PLUGIN_ROOT}/rules/aspnetcore.md` — injected automatically before an edit
to `Program.cs`, an endpoint, a middleware or a filter, and read directly when reviewing. This skill is
the design layer above them: what the surface looks like and why.

## Minimal APIs, organised as endpoint modules

Minimal APIs are the default; controllers are used only in a codebase that already has them. They are
faster, have no convention magic to learn, and route groups give the shared prefix, auth policy and
filters one obvious home. The cost is that nothing organises them for you — which is what the module
shape below is for. The trade-off in full is in the plugin README's design notes.

```csharp
// Api/Endpoints/Orders/OrderEndpoints.cs
public static class OrderEndpoints
{
    public static IEndpointRouteBuilder MapOrderEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/v1/orders")
            .WithTags("Orders")
            .RequireAuthorization(AuthPolicies.OrdersRead);

        group.MapGet("/", GetOrders).WithName(nameof(GetOrders));
        group.MapGet("/{id:guid}", GetOrder).WithName(nameof(GetOrder));
        group.MapPost("/", CreateOrder)
             .RequireAuthorization(AuthPolicies.OrdersWrite)
             .AddEndpointFilter<ValidationFilter<CreateOrderRequest>>();

        return app;
    }

    private static async Task<Results<Ok<OrderResponse>, ProblemHttpResult>> GetOrder(
        Guid id,
        GetOrderHandler handler,
        CancellationToken cancellationToken)
    {
        var result = await handler.Handle(new GetOrderQuery(id), cancellationToken);
        return result.ToHttpResult(OrderResponse.From);
    }
}
```

Rules this shape encodes:

- **Handlers are named static methods**, one per endpoint. An inline lambda cannot be unit-tested, cannot
  carry docs, and turns the module into a wall at the tenth route.
- **`Results<T1, T2>` as the return type** declares the status codes in the signature, so the generated
  OpenAPI document cannot drift from the implementation. With `IResult` instead, declare them with
  `Produces`/`ProducesProblem`.
- **One module per resource**, registered from `Program.cs` as `app.MapOrderEndpoints()`. A module never
  registers services and never reaches into another module.
- The handler **binds, delegates once, maps the result**. Anything else in it belongs in `Application`.

## `Program.cs`

The only composition root, and short enough to read in one screen: every registration is an `AddXxx`
extension per area (`AddPersistence`, `AddOrderModule`, `AddApiServices`), every pipeline step is on one
line. Order matters more than anything else in the file:

```csharp
app.UseExceptionHandler();        // first — nothing above it is covered
app.UseHttpsRedirection();
app.UseRouting();
app.UseCors(CorsPolicies.Default);
app.UseRateLimiter();
app.UseAuthentication();          // establishes who the caller is
app.UseAuthorization();           // decides what they may do — never before authentication
app.MapOrderEndpoints();
app.MapHealthChecks("/health");
```

`UseAuthorization` before `UseAuthentication` authorises an anonymous principal and fails open. Exception
handling registered late leaves everything above it returning the default error page. Neither produces a
warning.

## Contracts

- **Request and response records live in `Api`** and are the only types on the wire. A domain entity or an
  EF entity on the wire leaks the schema, serialises navigation properties, and makes a column rename a
  breaking change (`dotnet-architecture`).
- Response types are `record`s with `init` properties — a value, not an object with behaviour.
- A collection response is **always paged and always enveloped** (`items`, `total`, `page`) — an endpoint
  that returns a bare array cannot add paging later without breaking clients, and one with no upper bound
  on page size is a denial-of-service parameter.
- Nullability on the contract is the API's promise. `required` on what the client must send; the framework
  will not enforce a non-nullable annotation for you at deserialisation time (`rules/csharp.md`).
- JSON options are configured **once** on the serializer used by the API (camelCase, enums as strings if
  agreed, no reference-loop handling as a workaround for entities that should not be there).

## Validation

Validation runs **at the boundary, before the use case**, as an endpoint filter that returns
`ValidationProblem` with the per-field errors. Attaching the filter per route (or per group where every
route validates) keeps the handler free of guard clauses.

Two distinct jobs: the filter rejects **malformed input**; the use case enforces **business rules** and
returns a failed `Result` for them (`dotnet-error-handling`). "Email is not an email" is the filter;
"this email is already registered" is the use case, because only it can know.

## Authorization

Policies are declared once, named as constants, and attached to the group or the route. An endpoint left
unprotected by omission is the standard way a private route becomes public — so anonymous access is
written out (`AllowAnonymous`), never implied. Resource-level checks ("is this the caller's order?") are
part of the use case, not the policy, because they need the data.

## Versioning, health and OpenAPI

- The version is in the route prefix (`/api/v1/...`) from the first endpoint. Adding a version later to a
  surface that has none means rewriting every client.
- A breaking change gets a new version; an additive field does not.
- `/health` (liveness) and a readiness check that actually probes the dependencies, both excluded from
  auth and from rate limiting, and neither returning detail to an anonymous caller.
- OpenAPI is generated and is part of the review: if the document does not match what the endpoint
  returns, the endpoint's declared results are wrong.

## What never goes in this layer

Business rules, EF queries, `HttpClient` calls, retry policies, and any work that outlives the request.
A detached `Task` started in a handler loses its scope — the `DbContext` it captured is disposed under it.
Background work is a hosted service or a queue (`dotnet-di`).
