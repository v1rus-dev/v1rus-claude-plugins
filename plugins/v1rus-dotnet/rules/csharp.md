---
paths:
  - "**/*.cs"
---

# C# — non-obvious rules

Only what a model gets wrong or omits without a reminder. Generic idiomatic C# — naming, `var`, expression
bodies, collection initialisers, `using` declarations — is not listed here; the .NET analyzers and
`.editorconfig` already enforce it and a rule that repeats them is noise.

## Async

- **`async void` is banned outside an event handler.** An exception thrown inside it cannot be caught by
  the caller and takes the process down. Return `Task` — and for a fire-and-forget background job use a
  hosted service, not an unawaited call.
- **Never block on a task**: no `.Result`, no `.Wait()`, no `.GetAwaiter().GetResult()` in application or
  request code. It burns a thread-pool thread per call and deadlocks under any synchronisation context.
  Sync-over-async in a hot path is how a service dies under load while CPU sits idle.
- **A `CancellationToken` is a parameter, not a decoration.** Every async method that can be cancelled
  takes one as the last parameter and **passes it down** — to EF Core, to `HttpClient`, to `Task.Delay`.
  A token accepted and then ignored is worse than none: it advertises cancellation the caller never gets.
- `ConfigureAwait(false)` belongs in **library** code. An ASP.NET Core app has no synchronisation context,
  so it changes nothing there — do not scatter it through application code as a ritual.
- A `Task` returned from a method is already running: do not wrap an already-async call in `Task.Run`.
  `Task.Run` is for offloading genuinely CPU-bound work, never for making sync I/O "async".
- Awaiting sequentially in a loop over independent work serialises it. Where the work is independent and
  the collaborator is safe to call concurrently, collect the tasks and `await Task.WhenAll`. **A
  `DbContext` is not such a collaborator** (`rules/efcore.md`).
- `ValueTask` is only for a hot path that usually completes synchronously, and it may be awaited **once**
  and never in parallel. When in doubt use `Task`.

## Nullability and types

- The solution builds with `<Nullable>enable</Nullable>`; a nullable warning is a build error
  (`dotnet-analysis`). **Never silence one with `!`.** The null-forgiving operator is a claim you are
  making on behalf of the runtime — if it is genuinely warranted, it carries a comment saying why.
- A nullable annotation mirrors what the source **actually** produces. Marking a deserialised property
  non-nullable because "the payload always has it" converts one missing field into a `NullReferenceException`
  for every caller; it does not make the value arrive.
- Nullable annotations are erased at the boundary: a payload deserialised from JSON, a value read from
  configuration, or a row from a database can be null whatever the annotation says. Validate at the
  boundary, then rely on the type inside.
- Prefer a domain type over a primitive for an identifier or a unit (`record struct OrderId(Guid Value)`).
  A method taking three `Guid` parameters will eventually be called with them in the wrong order.

## Collections and LINQ

- **An `IEnumerable<T>` parameter may be enumerated only once.** Enumerating it twice (a `Count()` then a
  `foreach`) re-executes the source — a second database round trip, a second HTTP call, or a different
  result. Either materialise once (`ToList()`) or declare the parameter as `IReadOnlyCollection<T>` so the
  caller cannot hand over a lazy sequence.
- Never return `IQueryable<T>` from anything but the class that owns the query. A leaked `IQueryable`
  executes in the caller's context, after the scope that owned the connection may be gone
  (`rules/efcore.md`).
- Expose `IReadOnlyList<T>` / `IReadOnlyDictionary<K,V>` from a public surface, not `List<T>` — an
  exposed mutable collection is a second, invisible setter.
- `Any()` rather than `Count() > 0`; `FirstOrDefault` with an explicit null check rather than `First` in
  a path where absence is expected.

## Time, culture and comparison

- **`DateTimeOffset` for a point in time, `DateOnly`/`TimeOnly` for a calendar date or a wall clock.**
  `DateTime` carries a `Kind` that is silently lost across serialisation and storage, and `DateTime.Now`
  bakes the server's local zone into data that will be read in another one. `DateTime.UtcNow` is
  acceptable where the storage type is fixed; the machine-local `Now` is not.
- **Do not read the clock statically.** Inject `TimeProvider` (.NET 8+) — a service that calls
  `DateTimeOffset.UtcNow` directly cannot be tested for anything time-dependent without waiting.
- **String comparison defaults are not what they look like.** `string.Equals(a, b)` and `==` are ordinal,
  but `ToUpper()`/`ToLower()`, `string.Compare`, `StartsWith`/`EndsWith`/`IndexOf(string)` are
  **culture-sensitive by default** and behave differently on a Turkish locale. For identifiers, keys,
  paths, headers and protocol tokens always pass `StringComparison.Ordinal` or `OrdinalIgnoreCase`
  explicitly. Use culture-sensitive comparison only for text a human sorts or reads.
- Same for formatting and parsing: `ToString()` and `Parse` on numbers and dates use the current culture.
  Machine-to-machine payloads use `CultureInfo.InvariantCulture` or a round-trip format (`"O"`).

## Exceptions

- **Exceptions are for defects and for genuinely exceptional conditions, not for control flow.** An
  expected failure — validation, not found, conflict, an upstream 4xx — is a `Result`, not a throw
  (`dotnet-error-handling`). Throwing is orders of magnitude more expensive and makes every expected path
  look like an incident in the logs.
- `throw;` to rethrow, never `throw ex;` — the second resets the stack trace to this line and destroys the
  only useful part of the record.
- Never `catch (Exception)` and continue. Catch the type you can actually handle; a catch-all belongs only
  at the process boundary (the global exception handler, a hosted service's loop) and always logs.
- **Never swallow an `OperationCanceledException` as a failure.** A cancelled request is not an error: do
  not log it at error level, do not map it to a 500, and let it propagate.
- Wrapping an exception loses the original unless it is passed as `innerException`.

## Disposal and lifetime

- Anything `IDisposable`/`IAsyncDisposable` that **you** created is disposed — `using` or `await using`.
  Anything the DI container created is disposed by the container: disposing an injected dependency is a
  bug that breaks every later request.
- `HttpClient` is the exception to both: it is obtained from `IHttpClientFactory` and **never** wrapped in
  a `using` and never constructed with `new` (`dotnet-http-clients`).
- A `CancellationTokenSource` is disposable and is frequently leaked; a linked source especially.
- Static mutable state is shared across all concurrent requests. If it exists it is either immutable, or a
  concurrent collection, or it is a race waiting for load.

## Types and equality

- `record` for a value carried across a boundary (a request/response contract, a DTO, an event); a
  `class` for anything with identity or behaviour. A `record` gives structural equality — which is what you
  want for a value and wrong for an entity whose identity is its id.
- A mutable field inside a `record` breaks the equality contract the record advertises. Keep them `init`.
- Override `GetHashCode` whenever `Equals` is overridden, and never make the hash depend on a mutable field
  of an object that lives in a dictionary or a set.

## Logging and secrets

- Logging goes through `ILogger<T>` with **message templates** and structured parameters, never an
  interpolated string (`dotnet-observability`, and the `v1rus-logging` skill for the policy).
- No `Console.WriteLine`, no `Debug.WriteLine`, no `Trace` for diagnostics in application code.
- A connection string, token, password or personal datum never reaches a log, an exception message, or a
  `ProblemDetails` payload.
