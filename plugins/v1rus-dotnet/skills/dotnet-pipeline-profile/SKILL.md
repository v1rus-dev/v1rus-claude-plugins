---
name: dotnet-pipeline-profile
description: "Stack profile that binds the stack-agnostic v1rus feature pipeline to a C# / ASP.NET Core backend project: the project vocabulary the architecture plan uses (Api, Application, Domain, Infrastructure) and the dependency direction, the stack-specific sections of architecture-plan.md, which convention skill owns which area, the request-handling pattern (endpoint module, use-case handler, Result to ProblemDetails), how an API contract stands in for a design spec, where tests live and on what (xUnit, WebApplicationFactory, Testcontainers), how to build and analyse, which engineer agent implementation escalates to, and the finalizer's stack checklist. Loaded by feature-architect, feature-designer, feature-developer, test-planner, test-writer and feature-finalizer when the pipeline detects a .NET backend project. Do NOT load for pipeline mechanics — gates, complexity bands and commit discipline live in feature-pipeline."
---

# Pipeline profile — C# / ASP.NET Core

The pipeline agents (`feature-architect`, `feature-designer`, `feature-developer`, `test-planner`,
`test-writer`, `feature-finalizer`) are stack-agnostic. This profile is the **vocabulary** they use on a
.NET backend project: what the projects are called, what the plan must cover, where tests go, which
convention skill owns which rule.

Two boundaries that matter:

- **Pipeline mechanics are not here.** Phase order, gates, complexity bands, artifact names, commit
  discipline and resume live in the `feature-pipeline` skill. This file never repeats them.
- **The project still owns the names.** The real solution layout, project names, target framework and the
  build/test/migration commands come from the target project's `CLAUDE.md`, its `.sln` and its
  `Directory.Build.props`. Read those first; never guess a command.

## Stack identity

Markers: a `*.sln` or `*.slnx`, `*.csproj` files, `Program.cs` with a `WebApplicationBuilder`,
`appsettings.json`, `Directory.Build.props` / `Directory.Packages.props`. Backend only — there is no UI
surface in this layer, so a design phase is usually skipped and the API contract takes its place.

## Layer vocabulary

| Project | Holds |
|---|---|
| `src/<Product>.Api` | `Program.cs` (the only composition root), endpoint modules per resource, request/response records, middleware, filters, auth policies, the `DomainError` → `ProblemDetails` mapping, OpenAPI |
| `src/<Product>.Application` | use-case classes with one `Handle` entry point, their command/query and result types, validators, the **port interfaces** Infrastructure implements |
| `src/<Product>.Domain` | entities with behaviour, value objects, the `DomainError` hierarchy, `Result`, invariants |
| `src/<Product>.Infrastructure` | `DbContext`, `IEntityTypeConfiguration<T>`, migrations, repository implementations, typed HTTP clients, caching, messaging, clock binding |
| `tests/` | `<Product>.UnitTests`, `<Product>.IntegrationTests`, `<Product>.ArchitectureTests` |

Hard boundaries (enforced by project references plus the architecture tests, not by review): `Domain`
references nothing — no EF Core, no ASP.NET Core; `Application` references `Domain` only and declares the
ports it needs; `Infrastructure` implements those ports and is referenced by `Api` **only for
registration**; no project references `Api` except an integration-test project.

## `architecture-plan.md` — stack sections

Use these in place of the generic layer sections:

```
## 3. Domain changes            (entities and their invariants, value objects,
                                new DomainError cases and their stable codes)
## 4. Application changes       (use-case classes + command/query/result types, validators,
                                new port interfaces, where the transaction boundary sits)
## 5. Infrastructure changes    (EF Core mappings, a migration if the schema changes,
                                repository/port implementations, typed HTTP clients, caching)
## 6. Api changes               (endpoint module + route group, request/response contracts,
                                auth policy, status codes, the Result → ProblemDetails mapping,
                                OpenAPI impact and whether the change is breaking)
## 7. Wiring                    (the AddXxx registration extension + its call from Program.cs,
                                new options classes bound and ValidateOnStart, new health checks,
                                new configuration keys and where their values come from)
```

Self-questions the plan must answer for this stack: does the change keep `Domain` free of EF Core and
ASP.NET Core; is every new dependency injected with the right lifetime and does anything scoped end up
inside a singleton; does every new async path take and forward a `CancellationToken`; does a schema change
come with a reviewed migration **and** a migration test; is the failure expected (a `Result`) or a defect
(an exception); does the endpoint change break an existing client, and if so does it need a new version.

## Convention skills by area

| Area | Skill |
|---|---|
| project layout, dependency direction, where a class belongs | `dotnet-architecture` |
| endpoints, contracts, middleware order, validation, auth policies | `aspnetcore-api` |
| `Result`, `DomainError`, `ProblemDetails`, exception handler | `dotnet-error-handling` |
| EF Core mappings, queries, migrations, repositories | `efcore-persistence` |
| service lifetimes, registration, captive dependencies, background services | `dotnet-di` |
| `IHttpClientFactory` typed clients, resilience, outbound auth | `dotnet-http-clients` |
| options pattern, validation at startup, secrets | `dotnet-configuration` |
| `ILogger` templates, scopes, OpenTelemetry, health checks | `dotnet-observability` |
| C#-level rules: async, nullability, culture, time, disposal | `csharp-conventions` |
| `Directory.Build.props`, central package management, analyzers | `dotnet-analysis` |
| tests | `dotnet-testing` |

Name the applicable ones in the plan so the implementing agent invokes them; invoke them yourself before
writing non-trivial endpoint or persistence code. If a skill is absent in the current environment,
proceed — never hard-depend on one.

## Request-handling pattern

**Minimal APIs organised as endpoint modules**: one static class per resource exposing
`Map<Resource>Endpoints(this IEndpointRouteBuilder)`, a route group carrying the prefix, tags, auth policy
and filters, and **named static handlers** — never inline lambdas. A handler binds, calls exactly one
Application use case, and maps the `Result` to a typed result or a `ProblemDetails`. Controllers are used
only in a codebase that already has them.

A **use case** is a class with one public `Handle(command, ct)`, injected directly into the endpoint —
there is no mediator by default; cross-cutting concerns are endpoint filters, middleware and DI
decorators. A pass-through use case that forwards one call to one port should not be created.

Expected failures are a `Result` with a `DomainError`; exceptions are for defects and infrastructure
faults and are mapped once by the global `IExceptionHandler`.

## API-contract mapping (in place of a design spec)

There is no UI here, so `feature-designer` normally does not run. The equivalent artifact is the **API
contract**: route, method, request and response records, status codes per outcome, the `code` value of
every `DomainError` the endpoint can return, the auth policy, and paging defaults. Map it onto the
project's existing conventions — the existing route prefix and version, the existing envelope for a
collection, the existing `ProblemDetails` extensions — before proposing a new shape. Discover them with
`ast-index` rather than inventing a second style.

## Tests

- Location: **`tests/<Product>.UnitTests`** mirroring the source folders (`<Type>Tests.cs`),
  **`tests/<Product>.IntegrationTests`** for anything crossing the pipeline or the database,
  **`tests/<Product>.ArchitectureTests`** for the dependency-direction rules.
- Framework: **xUnit**. Unit tests construct the class with fakes and never use a container.
- Integration: **`WebApplicationFactory<Program>`** over the real pipeline with a **Testcontainers**
  database — never the EF in-memory provider. Replace an external with `RemoveAll<T>()` first.
- Assert the failure paths: each `DomainError` case, and the `ProblemDetails` status and `code`.
- A schema change requires a **migration test**; `TimeProvider` is faked, never waited on.
- Detail: `dotnet-testing`.

## Verification

- **`dotnet build`** is the entry gate and, with `TreatWarningsAsErrors`, is also the static-analysis
  gate — a warning is a failure (`dotnet-analysis`).
- `dotnet format --verify-no-changes` for style; `dotnet test` for the suite, scoped to the change.
- A schema change: `dotnet ef migrations add <Name>` in the Infrastructure project, then **read the
  generated `Up`/`Down`** before committing. Never migrate a deployed database from application startup.
- Integration tests need a container runtime; when none is available, say the level was skipped rather
  than reporting a pass.
- The full build + test run belongs to the `test-runner` agent of this layer
  (`v1rus-dotnet:test-runner`), which discovers the project's own commands.
- Commands come from the project's `CLAUDE.md`. Never read `bin/` or `obj/`.

## Implementation escalation targets

Available on this stack, per the pipeline's executor-escalation rule: `v1rus-dotnet:dotnet-engineer`
(all four projects — domain, use cases, EF Core, endpoints, DI, configuration, and their tests). There is
no UI agent in this layer and none is needed; `feature-developer` remains the floor.

## Finalizer stack checklist

On top of the generic cleanup: every new service registered in the right `AddXxx` extension and called
from `Program.cs`, with a lifetime that survives `ValidateScopes`; no scoped dependency captured in a
singleton, middleware constructor or background service; every async path takes and forwards a
`CancellationToken`; no `.Result` / `.Wait()` / `async void`; no EF entity or domain entity on the wire;
every endpoint carries an explicit auth policy or an explicit `AllowAnonymous`; errors leave as
`ProblemDetails` with no exception detail; new settings bound to an options class with `ValidateOnStart`
and no secret in `appsettings.json`; a new package added to `Directory.Packages.props` only, with the
version resolved through the dependency gate; the migration read and checked in; `dotnet build` clean with
warnings as errors.

## Typical expert reviews to flag

`security-expert` for auth, tokens, a new public endpoint, anything touching secrets, raw SQL or file
upload; `performance-expert` for a new query on a large table, an N+1 risk, a new outbound call in a hot
path or new background work; `architecture-expert` when the change crosses project boundaries, adds a
project reference or introduces a new port. There is no UI surface, so `ux-expert` does not apply —
the API contract review is part of `architecture-expert`'s scope here.
