# v1rus-dotnet

The C# / ASP.NET Core backend layer. Depends on `v1rus-core`, so installing it pulls the corporate
baseline with it.

```
/plugin install v1rus-dotnet@v1rus
```

Backend only. This layer ships no UI conventions and no UI agent — a service with server-rendered pages
is out of its scope, and it says so rather than improvising one.

## The stack this plugin standardises

| Concern | Decision |
|---|---|
| Solution | Four projects — `Api` / `Application` / `Domain` / `Infrastructure` — with the dependency direction held by project references **and** an architecture test |
| Build settings | `Directory.Build.props` for every project: `<Nullable>enable</Nullable>`, `TreatWarningsAsErrors`, `EnforceCodeStyleInBuild`; `.editorconfig` as the single style source |
| Packages | `Directory.Packages.props` central package management — one version per package, resolved through the `v1rus-dependencies` gate |
| HTTP surface | **Minimal APIs** as endpoint modules on route groups, named static handlers, typed results; controllers only where they already exist |
| Contracts | Request/response records owned by `Api`; a domain or EF entity never reaches the wire |
| Errors | Hand-written `Result<T>` + a closed `DomainError` hierarchy in `Domain`; expected failures returned, exceptions reserved for defects; one `IExceptionHandler` producing `ProblemDetails` |
| Use cases | A class per use case with one `Handle(command, ct)`, injected directly — **no mediator** |
| Mapping | Hand-written `ToDomain()` / `From()` — **no mapping library** |
| Persistence | EF Core in `Infrastructure`, one `IEntityTypeConfiguration<T>` per entity, reviewed migrations applied as a deployment step, `AsNoTracking` + projections for reads, lazy loading off |
| Outbound HTTP | `IHttpClientFactory` typed clients with a resilience handler and a single-flight refresh handler; never `new HttpClient` |
| Configuration | Options pattern, one class per area, `ValidateDataAnnotations().ValidateOnStart()`; secrets in user-secrets or the environment, never in `appsettings.json` |
| Observability | `ILogger<T>` message templates (never interpolated), `[LoggerMessage]` on hot paths, OpenTelemetry traces + metrics, liveness and readiness split |
| Tests | xUnit; `WebApplicationFactory<Program>` over the real pipeline with a **Testcontainers** database, never the EF in-memory provider |

**No versions are pinned anywhere in this plugin.** Package names only; the version is resolved at plan
time through the `v1rus-dependencies` gate. The one exception is a platform floor where a mechanism does
not exist below it — `TimeProvider`, keyed DI services, `IExceptionHandler` and the standard resilience
handler all require **.NET 8+**, and that is stated as a floor, never as the version to use.

## Contents

| Component | What it covers |
|---|---|
| `skills/dotnet-architecture` | The four projects, the dependency direction, what goes in which, feature-folder layout, the architecture test, adding a slice |
| `skills/aspnetcore-api` | Endpoint modules, named static handlers, contracts, validation, auth policies, middleware order, versioning, health, OpenAPI |
| `skills/dotnet-error-handling` | `Result<T>`, `DomainError`, return-versus-throw, mapping in `Infrastructure`, the `ProblemDetails` table and the exception handler |
| `skills/efcore-persistence` | Where EF lives, the repository contract, the unit of work, reads and writes, migrations, registration |
| `skills/dotnet-di` | Lifetimes, the captive dependency, scopes in background services, `ValidateScopes`/`ValidateOnBuild`, keyed services, disposal ownership |
| `skills/dotnet-http-clients` | Typed clients, why both `new HttpClient` and a static one are wrong, resilience, auth handler with single-flight refresh, error mapping |
| `skills/dotnet-configuration` | Options classes, `IOptions` vs `Snapshot` vs `Monitor`, startup validation, provider precedence, secrets |
| `skills/dotnet-observability` | Message templates, `[LoggerMessage]`, scopes and trace ids, levels at the HTTP boundary, OpenTelemetry, health checks |
| `skills/dotnet-testing` | Test projects, unit doubles, `WebApplicationFactory` + Testcontainers, migration tests, determinism, running |
| `skills/dotnet-analysis` | `Directory.Build.props`, central package management, `.editorconfig`, the severities worth raising, suppressions with a reason |
| `skills/dotnet-pipeline-profile` | The stack profile the feature pipeline loads on a .NET project |
| `skills/dotnet-mvp-blueprint` | The `/mvp-init` blueprint: the `dotnet new` bootstrap, the MVP-sized solution, the baseline package set by role, the skeleton, the first vertical slice, and the generated project `CLAUDE.md` |
| `skills/csharp-conventions` | Front door to `rules/csharp.md` for read-only and review contexts |
| `rules/csharp.md` | Injected before any `.cs` edit: async, cancellation, nullability, collections, culture and time, exceptions, disposal |
| `rules/aspnetcore.md` | Injected before editing `Program.cs`, an endpoint module, a controller, middleware or a filter |
| `rules/efcore.md` | Injected before editing a `DbContext`, a configuration, a migration or a repository |
| `agents/dotnet-engineer` | Writes all four projects, DI, configuration and tests. The only implementer this layer ships. |
| `agents/test-runner` | Runs build → format → tests; reports PASS/FAIL. Never edits code. |

## Design notes

**Minimal APIs, not controllers.** Route groups give the shared prefix, auth policy and filters one
obvious home, there is no convention magic to learn, and the endpoint's status codes can be declared in
its return type so the OpenAPI document cannot drift from the implementation. What is given up is real:
MVC's model-binding conventions, action filters, and `[ApiController]`'s automatic 400 on an invalid
model — all replaced here by an explicit validation endpoint filter. The other cost is organisational —
nothing stops a minimal API becoming a thousand-line `Program.cs`, so the endpoint-module shape is not a
style preference, it is the thing that makes the choice survivable. A codebase that already uses
controllers keeps them; mixing both styles for the same resource is worse than either.

**A `Result` for expected failures, exceptions for defects.** The failure is then visible in the
signature: a missing `try/catch` compiles and reaches production, while a `Result` that is never
inspected is a value nobody read. It also keeps the telemetry honest — with exceptions as control flow,
every "not found" is an incident, and the error rate stops meaning anything. The cost is that `Result`
has to be threaded through by hand (C# has no `do`-notation, and the temptation to add a functional
library to hide that is a dependency decision, not a default), and that a `Result` ignored at a call
site is quieter than an exception would be. Infrastructure faults and programmer errors still throw, and
one `IExceptionHandler` turns them into a `ProblemDetails` with no detail on the wire.

**No mediator.** A use case is a class with one `Handle` method, injected into the endpoint that needs
it. What a mediator pipeline buys — cross-cutting behaviours — is covered here by endpoint filters
(validation, idempotency), middleware (logging, exception mapping) and DI decorators (caching, retries),
and what it costs is a reflection-based dispatch that turns "go to definition" into a search and a stack
trace into a wall of library frames. It also removes a dependency whose licensing has moved toward a
commercial model for larger organisations — a fact the `v1rus-dependencies` gate would surface anyway,
but one worth knowing before a solution is built around it. A project that already uses a mediator keeps
it; this is the default for a new one.

**Repositories returning materialised results, not `IQueryable`.** The alternative — exposing the
`DbContext` or an `IQueryable` to the application layer — is genuinely more convenient and is a defensible
choice in a small service. It is rejected here because the query then executes in a caller that does not
know a connection is involved, possibly after its scope is gone, and because it lets an outer layer
compose a predicate the provider cannot translate, which fails at runtime and only under the data that
triggers it. Read-heavy screens are served by a narrow read port returning a projection — not by growing
the aggregate repository one method per screen.

**Why the boundary is a project reference and a test.** In a single project nothing stops `Domain` from
using `DbContext`. Four projects make the common violations impossible to compile, and the architecture
tests cover what references cannot see — a package creeping into the wrong project, or `Api` calling
`Infrastructure` directly. Retrofitting that split into a grown single-project service means untangling
every `using` in the codebase, which is why it is the one thing this layer does **not** defer at MVP size.

**Project overrides.** Everything here is the default, not a mandate: a project may specify a different
structure or stack in its own `CLAUDE.md`, and the project wins. What the plugin guarantees is that the
default is a coherent whole rather than per-developer taste.
