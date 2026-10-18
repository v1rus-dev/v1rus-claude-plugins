---
name: dotnet-http-clients
description: "Calling another service from a v1rus ASP.NET Core app: IHttpClientFactory typed clients registered with AddHttpClient and never a new HttpClient and never a using around one, why a static HttpClient goes stale on DNS changes and a per-call one exhausts sockets, resilience and timeout handlers rather than a hand-rolled retry loop, a DelegatingHandler for auth with single-flight token refresh, per-client JSON options and base address, the response read with ReadFromJsonAsync and a cancellation token passed all the way down, mapping an HttpRequestException to a domain error inside Infrastructure, and never logging a request body or an Authorization header. Load when integrating an upstream HTTP API, registering or configuring an HttpClient, adding a delegating handler, adding retries or a timeout to an outbound call, or reviewing outbound HTTP code."
---

# HTTP Clients

Outbound HTTP lives in **`Infrastructure`**, behind a port declared in `Application`
(`dotnet-architecture`). A use case calls `IPaymentGateway`, not an `HttpClient`.

## Never `new HttpClient`, never `using`

Both halves of the standard mistake:

- `new HttpClient()` per call, disposed with `using` — each one opens its own connection pool, and the
  sockets stay in `TIME_WAIT` after disposal. Under load the process runs out of ports and every outbound
  call starts failing at once, long after the code that caused it ran.
- One `static readonly HttpClient` for the process — fixes sockets, and never notices a **DNS change**,
  because the underlying connection is kept alive indefinitely. A failover or a scale event points the
  old address at nothing and the client keeps dialling it.

`IHttpClientFactory` solves both: it pools and rotates the handler chain on a lifetime, and hands out a
cheap `HttpClient` over it. A client obtained from the factory or injected as a typed client is **never
disposed by you** — the factory owns the handler.

## Typed clients

```csharp
// Infrastructure/DependencyInjection.cs
services.AddHttpClient<IPaymentGateway, PaymentGatewayClient>((provider, client) =>
    {
        var options = provider.GetRequiredService<IOptions<PaymentOptions>>().Value;
        client.BaseAddress = new Uri(options.BaseUrl);          // trailing slash — see below
        client.Timeout = options.Timeout;
        client.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
    })
    .AddHttpMessageHandler<PaymentAuthHandler>()
    .AddStandardResilienceHandler();                            // retries, circuit breaker, timeouts
```

```csharp
internal sealed class PaymentGatewayClient(HttpClient httpClient, ILogger<PaymentGatewayClient> logger)
    : IPaymentGateway
{
    public async Task<Result<PaymentReceipt>> ChargeAsync(ChargeRequest request, CancellationToken cancellationToken)
    {
        using var response = await httpClient.PostAsJsonAsync("v1/charges", request, JsonOptions.Default, cancellationToken);

        if (response.StatusCode is HttpStatusCode.UnprocessableEntity)
        {
            var problem = await response.Content.ReadFromJsonAsync<ProblemDetails>(cancellationToken);
            return new DomainError.Conflict("payment_rejected", problem?.Title ?? "Payment was rejected.");
        }

        if (!response.IsSuccessStatusCode)
        {
            logger.LogWarning("Charge failed with {StatusCode}", (int)response.StatusCode);
            return new DomainError.Unavailable("payment_unavailable", "The payment provider is unavailable.");
        }

        var receipt = await response.Content.ReadFromJsonAsync<PaymentReceiptDto>(JsonOptions.Default, cancellationToken);
        return receipt!.ToDomain();
    }
}
```

What that shape encodes:

- **A typed client per upstream API**, named after the capability, implementing the port. Registration
  configures the client; the class contains only calls.
- **The `CancellationToken` reaches every call** — the send, the content read, the deserialisation. An
  outbound call that ignores it keeps the upstream busy after the caller is gone (`rules/csharp.md`).
- **`BaseAddress` ends with a slash and the relative URI does not start with one.** `new Uri("https://x/v1")`
  plus `"charges"` resolves to `https://x/charges` — the silent path-truncation rule of relative URIs, and
  the reason an integration 404s with a URL that looks right in the code.
- **Read JSON with `ReadFromJsonAsync`**, not `ReadAsStringAsync` plus a deserialise: it streams instead
  of materialising the whole body as a string.
- **The response is a `using`** — the `HttpClient` is not, the `HttpResponseMessage` is.
- **The upstream's failure becomes a `DomainError` here** and never leaves as an `HttpRequestException`
  (`dotnet-error-handling`). A non-success status is not an exception unless you ask for one — do not add
  `EnsureSuccessStatusCode` and then catch it, which is exceptions as control flow.

## Resilience — configured, not hand-written

Add the standard resilience handler (`Microsoft.Extensions.Http.Resilience`, .NET 8+) rather than writing
a retry loop. A hand-rolled loop almost always gets three things wrong: it retries a **non-idempotent**
request, it retries without jitter and synchronises every instance into a thundering herd, and it has no
circuit breaker, so it keeps hammering a dependency that is already down.

- **Only retry what is safe to repeat.** GET, PUT and DELETE are idempotent; a POST is not unless the
  upstream supports an idempotency key — send one.
- A per-attempt timeout and a total timeout are different things, and both are needed.
- `HttpClient.Timeout` is the outermost bound and throws `TaskCanceledException`, which is
  indistinguishable from a caller cancellation unless you check the token. Check it before treating a
  cancellation as a timeout.
- The retry budget and the circuit breaker live in configuration, not in constants (`dotnet-configuration`).

## Auth as a `DelegatingHandler`, refreshed once

Attaching a token is cross-cutting and belongs in a handler, not in every method:

```csharp
internal sealed class PaymentAuthHandler(ITokenProvider tokens) : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request, CancellationToken cancellationToken)
    {
        request.Headers.Authorization =
            new AuthenticationHeaderValue("Bearer", await tokens.GetAsync(cancellationToken));
        return await base.SendAsync(request, cancellationToken);
    }
}
```

- **Refresh is single-flight.** Ten concurrent 401s must trigger **one** refresh, not ten — guard it with
  a `SemaphoreSlim` (or a shared lazily-awaited task) in the token provider, and let the other callers
  await the same refresh. Without it the identity provider rate-limits the service and every request
  fails at once.
- A handler registered with `AddHttpMessageHandler<T>` is resolved from the handler chain's scope, which
  is **not** the request scope: it is reused for the handler's lifetime. Do not capture a `DbContext` or
  anything scoped in it — resolve per call through `IServiceScopeFactory` if it genuinely needs one
  (`dotnet-di`).
- Retry-after-refresh happens **once**: a second 401 after a fresh token is an authorisation failure, not
  a token problem, and retrying it forever is a loop.

## Logging and secrets

The built-in `HttpClient` logging already records the method, URI, status and duration — do not
re-implement it. **Never log a request or response body, an `Authorization` header, a cookie or a
token**, and never attach one to an exception message that could reach a `ProblemDetails`
(`v1rus-logging`). Redact the query string if it can carry identifiers.

## Tests

The unit under test is the typed client's mapping logic; the transport is stubbed with a fake
`HttpMessageHandler` returning canned responses, so deserialisation and the status-to-`DomainError`
mapping are both exercised. Never call a real upstream from a test. Assert the error mapping per status
code — that mapping is what every caller's failure path depends on (`dotnet-testing`).
