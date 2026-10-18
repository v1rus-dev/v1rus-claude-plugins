---
name: dotnet-observability
description: "Logging, tracing and metrics mechanics in a v1rus ASP.NET Core service: ILogger<T> with message templates and named placeholders instead of an interpolated or concatenated string, why the interpolated version destroys structured search and pays the formatting cost even when the level is off, the LoggerMessage source generator for hot paths, log scopes for per-request correlation, the trace id returned in ProblemDetails so a user report maps to a log line, OpenTelemetry traces and metrics with an ActivitySource and a Meter per area, liveness versus readiness health checks, and log-level semantics at the HTTP boundary including never logging a cancelled request as an error. Load when adding logging to .NET code, instrumenting a request path, wiring OpenTelemetry or health checks, or reviewing diagnostics. Do NOT load for the logging policy itself — what may be logged, temporary diagnostic logs and redaction live in the v1rus-logging skill."
---

# Observability

**The policy is not here.** What may be logged, what a temporary diagnostic log looks like, the level
semantics and the redaction rules are the `v1rus-logging` skill — single source. This skill is the .NET
mechanics of complying with it.

## Message templates, always

```csharp
logger.LogInformation("Order {OrderId} created for customer {CustomerId}", order.Id, order.CustomerId);
```

```csharp
logger.LogInformation($"Order {order.Id} created for customer {order.CustomerId}");   // never
```

The interpolated version compiles, reads the same, and is wrong three times over:

- **The structure is gone.** The log store receives one opaque sentence per order instead of an
  `OrderId` field, so "every log line for this order" stops being a query.
- **The cost is paid unconditionally.** The string is built before `LogInformation` is called, so a level
  that is switched off still formats it — and `ToString()` on a large object still runs.
- **The message template is no longer a constant**, so grouping identical events together is impossible
  and the analyzer's template checks cannot see it.

Rules that follow: placeholders are **named and ordered** to match the arguments (the names are what the
sink indexes; positional mismatch is silent); a template is a constant, never composed at runtime; the
exception goes in the **`exception` parameter**, not interpolated into the message
(`logger.LogError(ex, "...")`).

For a hot path, the `[LoggerMessage]` source generator removes the boxing and the level check entirely:

```csharp
internal static partial class Log
{
    [LoggerMessage(Level = LogLevel.Warning, Message = "Charge rejected for order {OrderId}: {Reason}")]
    public static partial void ChargeRejected(ILogger logger, Guid orderId, string reason);
}
```

## Scopes and correlation

Per-request context is attached **once** with a scope rather than repeated as a parameter in every call:

```csharp
using var scope = logger.BeginScope(new Dictionary<string, object>
{
    ["TenantId"] = tenantId,
    ["CorrelationId"] = correlationId,
});
```

The scope must be disposed on the same logical path that opened it — a scope opened and not disposed
leaks the context into unrelated requests on the same thread.

`Activity.Current?.TraceId` is already the correlation identifier for anything OpenTelemetry sees; do not
invent a second one where a trace id will do. **Return the trace id in `ProblemDetails`** (the default
`AddProblemDetails` customisation) so a user's screenshot of an error maps to the exact log line
(`dotnet-error-handling`).

## Levels at the HTTP boundary

Beyond the general semantics in `v1rus-logging`, the boundary-specific calls that are routinely got
wrong:

- An **expected failure** returned as a `DomainError` — a 404, a validation 400 — is `Information` or
  `Debug`, not `Warning`. Logging every not-found at warning makes the warning level useless.
- An **unhandled exception** is `Error`, logged **once**, in the global exception handler. Logging in the
  catch and rethrowing produces the same incident three times at three levels.
- A **cancelled request** (`OperationCanceledException` with the request token signalled) is not an
  error at all. It is the client hanging up — `Debug` at most (`rules/csharp.md`).
- An upstream 5xx is a `Warning` in the client and an `Error` only if the request fails as a result.

## Tracing and metrics

OpenTelemetry is the default, exported over OTLP; the ASP.NET Core, `HttpClient` and EF Core
instrumentations cover the spans that matter without any application code. Add your own only where the
built-in spans cannot see the work:

```csharp
private static readonly ActivitySource Source = new("<Product>.Orders");
using var activity = Source.StartActivity("ReserveInventory");
activity?.SetTag("order.id", order.Id);
```

- **One static `ActivitySource` and one static `Meter` per area**, named for the area and registered with
  the tracer/meter provider. Creating one per call allocates and the telemetry pipeline will not see it.
- A span name is low-cardinality (`ReserveInventory`), and an identifier goes in a **tag**, never in the
  name. High-cardinality span or metric names are what makes a telemetry bill unpayable and a dashboard
  useless — the same is true of a metric **label** holding a user id.
- Business metrics (`orders.created`, a duration histogram) are counters and histograms on a `Meter`, not
  log lines someone counts later.
- `activity?.` — the activity is null when nothing is sampling, and a null-forgiving dereference here
  crashes only in the environment where tracing is off.

## Health checks

- **Liveness** (`/health/live`) answers "should the orchestrator restart me" and checks nothing external.
  A liveness probe that checks the database restarts every instance when the database blips.
- **Readiness** (`/health/ready`) answers "should traffic come to me" and does probe the dependencies it
  cannot serve without.
- Both are excluded from auth and rate limiting, and neither returns dependency detail to an anonymous
  caller — the detailed response is an internal endpoint or is authenticated.
