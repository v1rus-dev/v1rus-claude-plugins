---
name: dotnet-configuration
description: "Configuration in a v1rus ASP.NET Core service: the options pattern with a bound and validated class per area instead of IConfiguration injected everywhere or magic strings at call sites, the difference between IOptions and IOptionsSnapshot and IOptionsMonitor and the captive dependency that comes from injecting the wrong one into a singleton, ValidateDataAnnotations plus ValidateOnStart so a bad setting fails at boot rather than at the first request, the provider precedence order and environment-variable key syntax, and secrets living in user-secrets or the environment or a vault and never in appsettings.json or a connection string in source. Load when adding a setting, binding an options class, reading configuration in code, wiring a connection string or an API key, or setting up per-environment configuration."
---

# Configuration

## An options class per area, never `IConfiguration` in a service

```csharp
// Infrastructure/Payments/PaymentOptions.cs
public sealed class PaymentOptions
{
    public const string SectionName = "Payment";

    [Required, Url]
    public required string BaseUrl { get; init; }

    [Range(typeof(TimeSpan), "00:00:01", "00:01:00")]
    public TimeSpan Timeout { get; init; } = TimeSpan.FromSeconds(10);

    public int RetryBudget { get; init; } = 3;
}
```

```csharp
builder.Services
    .AddOptions<PaymentOptions>()
    .Bind(builder.Configuration.GetSection(PaymentOptions.SectionName))
    .ValidateDataAnnotations()
    .ValidateOnStart();          // fail at boot, not at the first request that needs it
```

- **Injecting `IConfiguration` into a service is the anti-pattern this replaces.** It turns a typo in a
  key into a silent null at runtime, hides what the class actually needs, and makes the class untestable
  without a configuration builder.
- **`ValidateOnStart` is not optional.** Without it a missing or malformed setting surfaces on the first
  request that touches that code path — in production, hours after deployment, as a 500 nobody can
  reproduce. With it the process refuses to start and the deployment fails loudly.
- Defaults belong in the class, so the required set stays small and a new setting does not break an
  existing environment.
- A setting whose validity is not expressible as a data annotation gets `.Validate(o => ..., "message")`.

## Which `IOptions` interface

| Interface | Lifetime | Use for |
|---|---|---|
| `IOptions<T>` | **singleton** | the default: settings read once at startup and never reloaded |
| `IOptionsSnapshot<T>` | **scoped** | a value that must be re-read per request when the file changes |
| `IOptionsMonitor<T>` | singleton, with change notifications | a singleton or background service that must react to a change |

**Injecting `IOptionsSnapshot<T>` into a singleton is a captive dependency**: the snapshot is scoped, so
the singleton pins the first scope's instance and never sees a change — and `ValidateScopes` will throw
for it at startup, which is exactly what it is for (`dotnet-di`). A singleton that needs live values takes
`IOptionsMonitor<T>` and reads `.CurrentValue` **at use time**, never caching `.CurrentValue` in a field —
caching it is the same bug written by hand.

Capturing `options.Value` into a field in a scoped or transient class is fine and preferred: it is a
snapshot of the value at construction, which is what the class wants.

## Sources and precedence

Later providers win. The default host order is: `appsettings.json` → `appsettings.{Environment}.json` →
user secrets (Development only) → environment variables → command line. Consequences worth knowing before
debugging a value that "is not being picked up":

- **Environment variables override the files**, so a stale variable on a machine silently beats the
  committed config.
- The key separator in an environment variable is `__` (double underscore):
  `Payment__BaseUrl`, `ConnectionStrings__Default`. A colon does not work on Linux.
- An array in configuration is bound by index (`Cors__Origins__0`), and an environment variable **cannot
  remove** an element a file defined — it can only overwrite index by index. Prefer a delimited string
  you split yourself when the list is environment-specific.
- `ASPNETCORE_ENVIRONMENT` decides which file is layered on. It is set by the host, never read by
  application code to change behaviour — an `if (env.IsProduction())` in a service is a branch that is
  never tested in the environment that runs it.

## Secrets

- **Nothing secret is in `appsettings.json` or `appsettings.Development.json`** — both are committed. A
  connection string with a password, an API key, a signing key or a token belongs in **user secrets**
  locally and in the **environment or a secret store** when deployed.
- A secret is never a default value in an options class and never a literal in code — including in a test
  fixture, which is also committed.
- Configuration sources for a deployed environment are the platform's (environment variables, a mounted
  file, a vault provider). Which one a project uses is recorded in its `CLAUDE.md`, not guessed.
- If a secret has ever been committed it is compromised and must be rotated, not deleted from the file.
  Say so rather than quietly removing the line.

## Feature flags

A feature flag is a product decision and is never added on the agent's initiative
(`v1rus-code-policies`). When one is genuinely called for, it is an options value like any other, read
at the boundary and passed down — not an `IConfiguration` lookup scattered through the layers.

## Testing

Integration tests supply configuration through the factory (`ConfigureAppConfiguration` with an in-memory
collection), not by writing files. A test that depends on the developer's environment variables is a test
that fails in CI for no visible reason (`dotnet-testing`).
