---
name: dotnet-mvp-blueprint
description: "The /mvp-init MVP blueprint for C# / ASP.NET Core: how a new backend service comes into existence and what it must contain on day one. Covers when .NET is the right stack and when it is not, the dotnet new bootstrap route and exactly what of the generated template is deleted, the MVP-sized four-project solution with the rule for when each deferred piece appears, the baseline package set by role (no versions), Directory.Build.props and Directory.Packages.props and .editorconfig and appsettings layering, the app skeleton (Program.cs composition root, registration extensions, DbContext, ProblemDetails exception handler, health checks, OpenTelemetry, auth), the first vertical slice as real working code from endpoint through use case to database, the facts the generated project CLAUDE.md must record, the verification commands, and the traps that break a fresh .NET service. Load when scaffolding a new ASP.NET Core service, running dotnet new for a fresh backend MVP, laying out the solution for a new project, or generating a new .NET project's CLAUDE.md. Do NOT load to add a feature to an existing .NET project — that is dotnet-pipeline-profile."
---

# MVP blueprint — C# / ASP.NET Core

The technology half of `/mvp-init` on this stack: the command owns the process, this file owns what a
.NET backend service *is* at hour zero. Project vocabulary, the convention-skill map, test layout and
verification discipline live in **`dotnet-pipeline-profile`** — this blueprint says what to *create*, the
profile says how to work in it afterwards. Everything below is the short form of a skill in this plugin;
invoke the named skill before writing the code.

## 1. Stack identity

.NET when the brief needs an **HTTP backend or worker service** and the team is a .NET team, or the
product already runs on .NET / SQL Server / Azure. Strong positive signals: a relational data model with
real transactions, long-lived business logic, an existing .NET client or shared contracts.

| Anti-signal | Go to |
|---|---|
| The deliverable is a mobile app | `v1rus-flutter:flutter-mvp-blueprint` or `v1rus-kmp:kmp-mvp-blueprint` |
| The deliverable is Android only | `v1rus-android:android-mvp-blueprint` |
| The team is a Kotlin team and the service is small | `v1rus-kotlin` — a JVM backend is the cheaper fit |
| A browser front end is the whole product | not this layer |

This layer is **backend only**: it ships no UI conventions. A service with server-rendered pages is out
of scope for the blueprint — say so rather than improvising one.

## 2. Bootstrap route

`dotnet new` is the generator; the solution is assembled from four project templates rather than from a
single web template that would put everything in one project.

```
dotnet new sln     -n <Product>
dotnet new classlib -n <Product>.Domain         -o src/<Product>.Domain
dotnet new classlib -n <Product>.Application    -o src/<Product>.Application
dotnet new classlib -n <Product>.Infrastructure -o src/<Product>.Infrastructure
dotnet new web      -n <Product>.Api            -o src/<Product>.Api
dotnet new xunit    -n <Product>.UnitTests        -o tests/<Product>.UnitTests
dotnet new xunit    -n <Product>.IntegrationTests -o tests/<Product>.IntegrationTests
dotnet new xunit    -n <Product>.ArchitectureTests -o tests/<Product>.ArchitectureTests
dotnet sln add (every project)
dotnet new gitignore && dotnet new editorconfig && dotnet new globaljson --roll-forward latestFeature
```

- `dotnet new web` (not `webapi`) — the `webapi` template ships the weather-forecast sample and, in some
  versions, controllers; `web` gives a minimal `Program.cs` with less to delete.
- **The product name is settled in the gate before this runs** (trap 1): it becomes the assembly names,
  the root namespaces and the default namespace of every file created afterwards.
- `global.json` pins the SDK **band** so every machine and CI agent builds with the same major — the
  exact version is resolved at plan time, not written from memory.

**Toolchain missing.** If the `dotnet` SDK is not on PATH, do not install it and never use `sudo`. Say so
in one line, hand the developer the exact commands for their own terminal (`dotnet --info`, then the
block above with the resolved product name), and continue with everything that does not need the SDK —
plan, `CLAUDE.md`, the file contents to write once the tree exists.

| # | After `new` | Detail |
|---|---|---|
| 1 | Delete the sample | the `/` minimal endpoint in `Program.cs`, `Class1.cs` in each classlib, `UnitTest1.cs` in each test project |
| 2 | Add `Directory.Build.props` + `Directory.Packages.props` | §5 — before adding any package, or the versions land in the `.csproj` files |
| 3 | Wire the project references | §3 — the direction is the architecture (`dotnet-architecture`) |
| 4 | Add packages by role | §4, each version resolved through the `v1rus-dependencies` gate |
| 5 | Skeleton (§6), then slice (§7) | inside-out: domain → application → infrastructure → endpoint |
| 6 | Verify | §9 |

## 3. Module graph at MVP size

Four source projects from day one — this is the one place where an MVP does **not** start smaller. The
boundary is a project reference, and retrofitting it into a single project later means untangling every
`using` in the codebase; creating it up front costs four `.csproj` files.

```
src/<Product>.Domain/           Orders/Order.cs, Errors/DomainError.cs, Results/Result.cs
src/<Product>.Application/      Orders/<UseCase>/..., Orders/Ports/IOrderRepository.cs, DependencyInjection.cs
src/<Product>.Infrastructure/   Persistence/AppDbContext.cs, Configurations/, Repositories/, Migrations/,
                                DependencyInjection.cs
src/<Product>.Api/              Program.cs, Endpoints/Orders/OrderEndpoints.cs, Contracts/,
                                Errors/ (exception handler + ProblemDetails mapping)
tests/<Product>.UnitTests/      mirrors Application and Domain
tests/<Product>.IntegrationTests/ ApiFactory.cs + endpoint tests
tests/<Product>.ArchitectureTests/ one fact per dependency rule
```

| Deferred | Created when |
|---|---|
| a second bounded context / a second solution folder | the first feature that shares nothing with the existing one |
| `Application/Behaviours` or DI decorators | the first genuinely cross-cutting concern that an endpoint filter cannot carry |
| a background worker project | the first job that must run outside a request; until then a `BackgroundService` in `Api` |
| caching (`IDistributedCache`, Redis) | a measured read that is hot — never on the first day |
| messaging / an outbox | the first side effect that must survive a failed transaction |
| a second API version | the first breaking change; the `/v1` prefix exists from endpoint one |
| feature flags | a product decision, never the agent's (`v1rus-code-policies`) |

## 4. Baseline dependency set, by role

Names only. **Every version is resolved at plan time through the `v1rus-dependencies` gate** and
CVE-checked there — nothing is added from memory. Add approved packages with `dotnet add package`, which
writes to `Directory.Packages.props` under central package management.

| Role | Package(s) | MVP |
|---|---|---|
| Persistence | `Microsoft.EntityFrameworkCore`, the provider (`Npgsql.EntityFrameworkCore.PostgreSQL` or `Microsoft.EntityFrameworkCore.SqlServer`), `Microsoft.EntityFrameworkCore.Design` (Api, for the tooling) | mandatory with a database |
| Migrations tooling | `dotnet-ef` as a local tool in `.config/dotnet-tools.json` | mandatory with EF Core |
| Validation | `FluentValidation` (+ its DI package) | mandatory — the endpoint filter needs it |
| OpenAPI | the framework's OpenAPI document generation, plus a UI package if the brief wants one | mandatory |
| Outbound HTTP | `Microsoft.Extensions.Http.Resilience` | with the first upstream call |
| Observability | `OpenTelemetry.Extensions.Hosting` + the ASP.NET Core, `HttpClient` and EF Core instrumentations + the OTLP exporter | mandatory |
| Health | `Microsoft.Extensions.Diagnostics.HealthChecks` + the provider-specific check | mandatory |
| Auth | `Microsoft.AspNetCore.Authentication.JwtBearer` | with the first protected endpoint |
| Testing | `xunit`, the runner, `Microsoft.AspNetCore.Mvc.Testing`, `Testcontainers.<provider>`, a fake time provider package, an assertion library if the team uses one | infrastructure mandatory; whether tests are *written* is the complexity band's call (`v1rus-qa`) |
| Architecture tests | reflection over assembly references, or an architecture-testing package | mandatory |
| Mediator | **none by default** — see the plugin README's design notes | — |
| Mapping library | **none by default** — mapping is a hand-written `ToDomain()` / `From()` method, which is greppable, debuggable and fails at compile time | — |

## 5. Build configuration

| What | Where |
|---|---|
| Package versions | `Directory.Packages.props` — the only place (`dotnet-analysis`) |
| Compiler settings for every project | `Directory.Build.props`: `Nullable`, `TreatWarningsAsErrors`, `EnforceCodeStyleInBuild`, `AnalysisLevel`, `LangVersion`, the target framework |
| Test-only relaxations | `tests/Directory.Build.props` importing the parent — never the root file |
| SDK band | `global.json` |
| Style | `.editorconfig`, checked in CI with `dotnet format --verify-no-changes` |
| Non-secret settings | `appsettings.json`; per-environment overrides in `appsettings.{Environment}.json` |
| Secrets in development | `dotnet user-secrets` (initialised on the Api project) — never a committed file |
| Secrets when deployed | environment variables or the platform's secret store, recorded in the project `CLAUDE.md` |
| Connection string | configuration only — never a literal, never committed with a password |
| Local dependencies | a `compose.yaml` bringing up the database so a fresh clone runs |
| Containerisation | a `Dockerfile` for the Api when the brief deploys containers; multi-stage, non-root user |

## 6. App skeleton

Every piece of plumbing is exercised once before feature work starts.

| File | Wires |
|---|---|
| `Api/Program.cs` | the only composition root: `AddApiServices` → `AddApplicationServices` → `AddPersistence` → `AddObservability`, then the pipeline in order (exception handler, HTTPS, routing, CORS, rate limiter, authentication, authorization, endpoints, health) (`aspnetcore-api`) |
| `Application/DependencyInjection.cs`, `Infrastructure/DependencyInjection.cs` | one `AddXxx` extension per area; `ValidateScopes` and `ValidateOnBuild` on everywhere, not only in Development (`dotnet-di`) |
| `Domain/Results/Result.cs`, `Domain/Errors/DomainError.cs` | the `Result`/`Result<T>` type and the closed error hierarchy with stable codes (`dotnet-error-handling`) |
| `Api/Errors/` | one `IExceptionHandler` + `AddProblemDetails` including the trace id, and the `DomainError` → status-code mapping used by every endpoint |
| `Infrastructure/Persistence/AppDbContext.cs` | the context, `ApplyConfigurationsFromAssembly`, registered scoped with the provider and a retrying execution strategy (`efcore-persistence`) |
| `Api/Endpoints/` | the route group at `/api/v1`, the validation endpoint filter, the auth policy constants |
| observability | OpenTelemetry tracing + metrics with the ASP.NET Core / `HttpClient` / EF Core instrumentations and an OTLP exporter; `ILogger` only, never `Console` (`dotnet-observability`) |
| health | `/health/live` checking nothing external and `/health/ready` probing the database, both anonymous and rate-limit exempt |
| options | one options class per area, bound with `ValidateDataAnnotations().ValidateOnStart()` (`dotnet-configuration`) |

Auth is wired only if the brief has it — an unused JWT configuration is dead weight, not plumbing. If it
is wired, at least one endpoint is protected in the first slice so the policy is proven.

## 7. The first vertical slice

One end-to-end feature, **real working code** — no `TODO`, no `NotImplementedException`, no stub
endpoint. It proves DI, configuration, the database, migrations, error mapping, OpenAPI and the test
harness fit together, and it is the template every later feature is copied from.

**Which slice:** the simplest *create-one-and-list-them* resource from the brief's MVP list; with no
obvious candidate, the primary entity of the domain.

| Project | Files |
|---|---|
| `Domain` | `Orders/Order.cs` with its invariants enforced in a factory method, `Orders/OrderId.cs` |
| `Application` | `Orders/CreateOrder/{CreateOrderCommand,CreateOrderHandler,CreateOrderValidator}.cs`, `Orders/GetOrders/{GetOrdersQuery,GetOrdersHandler}.cs`, `Orders/Ports/IOrderRepository.cs` |
| `Infrastructure` | `Persistence/Configurations/OrderConfiguration.cs`, `Persistence/Repositories/OrderRepository.cs`, the initial migration |
| `Api` | `Endpoints/Orders/OrderEndpoints.cs`, `Contracts/{CreateOrderRequest,OrderResponse}.cs` |

The slice covers **both outcomes of each endpoint**: `POST` returns 201 with a `Location` header on
success and 400 `ValidationProblem` on bad input; `GET /{id}` returns 200 or 404 `ProblemDetails` with the
`not_found` code; the list endpoint is paged and enveloped from the first version. The `GET` uses
`AsNoTracking` and projects to the response DTO — so the default is right in the file everyone copies.

Slice tests — a unit test per handler outcome and an integration test per status code — are written when
the complexity band calls for them (`v1rus-qa`); the status-code coverage above is required either way.

## 8. Project `CLAUDE.md` inputs

| Fact | Value to record |
|---|---|
| Solution | the `.sln` path, the four project paths and the root namespace |
| Target framework | the `net<major>.0` in `Directory.Build.props` and the `global.json` SDK band |
| Type names | `Result`/`Result<T>` and `DomainError` and where they live; the `DbContext` name; the `AddXxx` registration extension per area; the endpoint-module naming (`Map<Resource>Endpoints`); the auth-policy constants class |
| Database | provider, how the connection string is supplied per environment, whether migrations run as a deployment step or a job |
| Commands | `dotnet build`, `dotnet test`, `dotnet format --verify-no-changes`, `dotnet ef migrations add <Name> --project src/<Product>.Infrastructure --startup-project src/<Product>.Api`, `dotnet ef database update`, `dotnet run --project src/<Product>.Api` |
| Tests | the three test projects, what belongs in each, the container runtime integration tests require |
| Decisions | minimal APIs (not controllers); `Result` for expected failures, exceptions for defects; no mediator; no mapping library; central package management |
| v1rus plugins to enable | `v1rus-core`, `v1rus-dotnet` |

## 9. Verification

In this order — an earlier failure makes every later result a lie:

```
dotnet restore
dotnet build                                   # warnings are errors
dotnet format --verify-no-changes
dotnet ef migrations add Initial ...           # then READ the generated Up/Down
dotnet ef database update                      # against the local/compose database
dotnet test tests/<Product>.UnitTests
dotnet test tests/<Product>.IntegrationTests   # needs a container runtime
```

| Then | Headless? |
|---|---|
| `dotnet run --project src/<Product>.Api` + a request to `/health/ready` and to the slice endpoint | yes, when the database is reachable |
| `docker build` of the Api image | yes, with a container runtime |

"Runnable" here means the service starts, `/health/ready` reports healthy against the real database, and
the slice's endpoints return the documented status codes. The agent verifies what it can and hands over
the exact command for anything it could not run — never claiming a level it skipped. Full runs belong to
`v1rus-dotnet:test-runner`, which discovers the project's own commands.

## 10. Escalation targets

| Scaffold role | Agent |
|---|---|
| `Directory.Build.props`, `Directory.Packages.props`, `.editorconfig`, `global.json`, project references, Dockerfile | `v1rus-dotnet:dotnet-engineer` — there is no separate build agent here (`v1rus-kotlin:build-engineer` is JVM/Gradle and does not apply) |
| `Domain`, `Application`, `Infrastructure`, `Api`, DI, configuration | `v1rus-dotnet:dotnet-engineer` |
| Verification runs | `v1rus-dotnet:test-runner` |
| Floor when none is installed | `feature-developer` |

There is no UI implementer in this layer and none is needed.

## 11. Known first-run traps

1. **The product name decided too late.** It is baked into the assembly names, the root namespaces and
   every generated file's namespace; renaming afterwards touches every file in the solution. Settle it in
   the gate before `dotnet new` runs.
2. **Packages added before central package management exists.** `dotnet add package` writes a `Version`
   into the `.csproj` until `Directory.Packages.props` is in place — after which those versions become
   build errors and have to be stripped by hand. Add the props files first.
3. **`Program` not reachable from the test project.** `WebApplicationFactory<Program>` needs a
   `public partial class Program { }` at the end of `Program.cs` (or `InternalsVisibleTo`). Without it
   the integration test project does not compile, and the error names a type, not the cause
   (`dotnet-testing`).
4. **`dotnet ef` run from the wrong project.** The migration must be generated into `Infrastructure` with
   `Api` as the startup project; run from the wrong directory it either fails to find a `DbContext` or
   silently writes the migration into the wrong assembly. Record the exact command in `CLAUDE.md`.
5. **Migrating from application startup.** It works on one developer machine and races every instance in
   a deployed environment, with no rollback path. Make it a deployment step from day one; a dev-only
   `MigrateAsync` behind an environment check is written as such (`efcore-persistence`).
