---
name: dotnet-error-handling
description: "Error handling across the v1rus .NET layers: a hand-written Result and Result<T> in Domain with a sealed DomainError hierarchy, expected failures returned rather than thrown so the failure is visible in the signature, exceptions reserved for defects and infrastructure faults, infrastructure exceptions mapped to a domain error inside Infrastructure and never escaping it, one IExceptionHandler producing RFC 9457 ProblemDetails with no exception message or stack trace on the wire, the error-case to status-code table, and never treating OperationCanceledException as a failure. Load when writing a use case or a repository, deciding between returning and throwing, mapping a failure to an HTTP status, adding an error case, or wiring the global exception handler."
---

# Error Handling

## `Result` — hand-written, in `Domain`, no dependencies

The type at the foundation of every use-case signature must not be something a third party can break or
abandon, so it is written once and owned:

```csharp
// Domain/Results/Result.cs
public sealed record Result<T>
{
    private Result(T value) { Value = value; Error = null; }
    private Result(DomainError error) { Value = default; Error = error; }

    public T? Value { get; }
    public DomainError? Error { get; }
    public bool IsSuccess => Error is null;

    public static Result<T> Success(T value) => new(value);
    public static Result<T> Failure(DomainError error) => new(error);

    public static implicit operator Result<T>(T value) => Success(value);
    public static implicit operator Result<T>(DomainError error) => Failure(error);
}
```

Plus a non-generic `Result` for a command with no payload.

**A class, not a `record struct`.** A struct always has a `default` instance, and on this shape
`default(Result<T>)` has a null `Error` — so `IsSuccess` reads `true` and the result carries a null
payload. An uninitialised field, an array element or a `default` returned from a generic helper
would then be a silent success. A reference type has no such instance: the only way to get one is
through `Success` or `Failure`.

Why a `Result` rather than an exception for an expected failure: **the failure is visible in the signature**. A missing `try/catch` compiles and reaches
production; a `Result` the caller ignores is a value nobody read, and the analyzer flags it.

## `DomainError` — the vocabulary of failure

`DomainError` lives in `Domain` and is a closed hierarchy of the failures the **product** has an opinion
about — never a transport concept:

```csharp
// Domain/Errors/DomainError.cs
public abstract record DomainError(string Code, string Message)
{
    public sealed record NotFound(string Resource, object Key)
        : DomainError("not_found", $"{Resource} '{Key}' was not found.");

    public sealed record Validation(IReadOnlyDictionary<string, string[]> Errors)
        : DomainError("validation_failed", "One or more fields are invalid.");

    public sealed record Conflict(string Code, string Message) : DomainError(Code, Message);
    public sealed record Forbidden(string Code, string Message) : DomainError(Code, Message);
    public sealed record Unavailable(string Code, string Message) : DomainError(Code, Message);
}
```

- `Code` is a **stable machine-readable string** that clients may branch on; renaming one is a breaking
  API change.
- `Message` is a developer-facing summary, not a localised user string. Text a user reads is resolved by
  the client from the `Code`, or supplied as server-owned free-form text carried as data.
- A `DomainError` carries no `Exception`, no status code and no stack trace. It is data.

## Return or throw — where the line is

| Situation | What to do |
|---|---|
| Expected, recoverable failure the caller can act on — not found, validation, conflict, insufficient balance, an upstream 4xx | return `Result.Failure(<error case>)` |
| Programmer error — invalid argument, broken invariant, unreachable branch | `throw ArgumentException` / `InvalidOperationException` / `UnreachableException`; never model as a `DomainError` |
| Infrastructure fault — the database is down, a socket died, a timeout | let it throw from the driver, catch it **in `Infrastructure`**, log with the exception, and return a `DomainError.Unavailable` (or rethrow if there is genuinely nothing to say) |
| Cancellation | let `OperationCanceledException` propagate. It is **not** a failure: not logged at error, not mapped to 500, not converted into a `Result` |

**Exceptions are not control flow.** A "not found" thrown as a `NotFoundException` and caught three
frames up costs orders of magnitude more than a return, makes every expected path look like an incident
in the telemetry, and hides the outcome from the signature. Wrapping a genuine defect in a `Result` is the
mirror-image mistake: it hides a bug that should crash loudly and be reported.

## Mapping happens in `Infrastructure`, and only there

```csharp
// Infrastructure/Persistence/Orders/OrderRepository.cs
public async Task<Result<Order>> GetAsync(OrderId id, CancellationToken cancellationToken)
{
    try
    {
        var entity = await context.Orders.AsNoTracking()
            .FirstOrDefaultAsync(o => o.Id == id, cancellationToken);

        return entity is null
            ? new DomainError.NotFound(nameof(Order), id.Value)
            : entity;
    }
    catch (DbUpdateConcurrencyException ex)
    {
        logger.LogWarning(ex, "Concurrent update on order {OrderId}", id.Value);
        return new DomainError.Conflict("order_modified", "The order was modified by another request.");
    }
}
```

Non-negotiable: **no `DbUpdateException`, `SqlException`, `HttpRequestException`, `NpgsqlException` or
`JsonException` ever leaves `Infrastructure`.** An `Application` or `Domain` file catching a driver
exception type is an architecture violation — it cannot even reference the package (`dotnet-architecture`).

## Consuming a `Result`

```csharp
var result = await handler.Handle(command, cancellationToken);
return result.IsSuccess
    ? TypedResults.Ok(OrderResponse.From(result.Value!))
    : result.Error!.ToProblem();
```

- Check `IsSuccess` (or pattern-match) — never read `Value` first and null-check it afterwards.
- Never collapse an error to a bool. `if (!result.IsSuccess) return Results.BadRequest();` throws the
  diagnosis away: the client gets the wrong status and the log gets nothing.
- A use case that receives a failed `Result` from a port either maps it to its own error case or passes it
  through — it never swallows it and returns success.

## The HTTP boundary — `ProblemDetails`, once

One mapping table, in `Api`, used by every endpoint:

| Error case | Status |
|---|---|
| `Validation` | 400 (`ValidationProblem` with the field dictionary) |
| unauthenticated (no principal) | 401 — produced by the auth middleware, not by a `DomainError` |
| `Forbidden` | 403 |
| `NotFound` | 404 |
| `Conflict` | 409 |
| `Unavailable` | 503 |
| anything unmapped, and every unhandled exception | 500 |

```csharp
// Api/Errors/DomainErrorExtensions.cs
public static ProblemHttpResult ToProblem(this DomainError error) => error switch
{
    DomainError.NotFound => TypedResults.Problem(statusCode: StatusCodes.Status404NotFound,
        title: error.Message, extensions: new Dictionary<string, object?> { ["code"] = error.Code }),
    ...
};
```

Unhandled exceptions are caught by **one** `IExceptionHandler` (.NET 8+) registered with
`AddExceptionHandler` + `AddProblemDetails`, which logs the exception with its stack trace and returns a
generic `ProblemDetails`:

- **The wire never carries an exception message, a stack trace, a SQL statement or a connection string.**
  The developer detail goes to the log, correlated by a trace id that the response *does* carry
  (`dotnet-observability`).
- The handler returns `false` for an exception it does not own, so the next handler gets it.
- The developer exception page is Development-only, and "Development" must be impossible to switch on in
  a deployed environment by configuration alone.
