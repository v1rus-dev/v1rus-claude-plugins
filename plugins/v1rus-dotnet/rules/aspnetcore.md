---
paths:
  - "**/*Controller.cs"
  - "**/Program.cs"
  - "**/*Endpoints.cs"
  - "**/Startup.cs"
  - "**/*Middleware.cs"
  - "**/*Filter.cs"
---

# ASP.NET Core — rules for this file

Full detail in the `aspnetcore-api` skill. What must hold in the file you are editing:

- **`Program.cs` is the only composition root.** Registration lives in `AddXxx` extension methods per
  area, called from here; nothing else builds a service provider, and nothing calls
  `BuildServiceProvider()` by hand — that creates a second container whose singletons are duplicates
  (`dotnet-di`).
- **Middleware order is behaviour, not layout.** Exception handling first, then HTTPS redirection,
  routing, CORS, rate limiting, authentication, authorization, and the endpoints last. `UseAuthorization`
  before `UseAuthentication` silently authorises an anonymous principal; CORS after the endpoint never
  runs for the response it was meant to decorate.
- **Take `CancellationToken` in every handler** and pass it on. In a minimal API and in an MVC action the
  framework binds it from `HttpContext.RequestAborted` for free — an endpoint that does not accept one
  keeps querying the database for a client that hung up.
- **Errors leave as `ProblemDetails`**, produced centrally by the exception handler and by the endpoint's
  mapping of a failed `Result` — never an anonymous object, never a bare string, never a 200 with an
  `error` field in the body (`dotnet-error-handling`). A `ProblemDetails` never carries an exception
  message, a stack trace or a connection string.
- **Never return a domain entity or an EF entity from an endpoint.** Return a response record owned by the
  Api project. Returning the entity leaks the schema into the public contract, serialises lazy navigation
  properties, and turns a field rename into a breaking API change.
- **The handler is thin**: bind, delegate to one Application call, map the result to a status code. Business
  logic, EF queries and `HttpClient` calls do not belong in this file.
- **Never capture a scoped service in a singleton** — an endpoint filter, a middleware constructed once at
  startup, or a background service must resolve `IServiceScopeFactory` and create a scope per unit of
  work. A `DbContext` captured in middleware's constructor is shared by every concurrent request
  (`dotnet-di`).
- Middleware **constructor** parameters are singletons; per-request dependencies are parameters of
  `InvokeAsync`.
- **Never block** (`.Result`, `.Wait()`) anywhere in the request path, and never `async void` a handler or
  a filter (`rules/csharp.md`).
- **Nothing touches `HttpContext` after the response has started** or after the handler returned — that
  includes work started with an unawaited task. Background work goes to a hosted service or a queue, never
  to a detached `Task` that outlives the request scope.
- `IHttpContextAccessor` is for infrastructure that genuinely cannot take a parameter. Reading the current
  user in Application code through the accessor makes the class untestable and null at any non-request
  call site — pass the identity in.
- **Authorization is a policy, not an `if`.** Attach `RequireAuthorization("<policy>")` to the endpoint or
  the route group; an endpoint left unauthorised by omission is the standard way a private route becomes
  public. Anonymous access is explicit (`AllowAnonymous`).
- **Validate input at the boundary**, and return 400 with the field errors in `ProblemDetails` before any
  Application call. Route and query values are attacker-controlled: a `take` parameter without an upper
  bound is a denial of service.
- One endpoint file per resource, grouped on a route group that carries the shared prefix, auth policy and
  filters. Handlers are named static methods, not inline lambdas — a lambda cannot be unit-tested, cannot
  be given XML docs, and reads as a wall once there are ten of them.
- Status codes are declared (`Produces`/`ProducesProblem` or typed results) so the generated OpenAPI
  document matches reality.
