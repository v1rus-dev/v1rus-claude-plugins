---
name: dotnet-testing
description: "How tests are written and run in a v1rus ASP.NET Core project: xUnit with one test project per kind (unit, integration, architecture), unit tests constructing the class under test with fakes and never a container, integration tests over WebApplicationFactory with the real pipeline and a Testcontainers database rather than an in-memory provider, replacing a registration with RemoveAll before AddSingleton, a shared container fixture with per-test data reset, FakeTimeProvider instead of waiting, asserting the status code and the ProblemDetails contract rather than only the happy path, a migration test for a schema change, and the dotnet build and test commands read from the project rather than guessed. Load when writing or fixing tests for C# code, testing an endpoint or a use case or a repository, setting up a test project, or when a change breaks existing tests."
---

# .NET Testing

**Whether tests are written at all is decided by the complexity band, not here** — see the `v1rus-qa`
skill (tests from complexity 7 upward; below that verification is build + static analysis + the quality
gate). This skill covers *how* they are written when warranted.

## Layout and naming

```
tests/
  <Product>.UnitTests/          # Domain and Application, no I/O, milliseconds
  <Product>.IntegrationTests/   # the real pipeline over a real database
  <Product>.ArchitectureTests/  # the dependency-direction rules (dotnet-architecture)
```

- The test project mirrors the source project's folders: `Application/Orders/CreateOrderHandler.cs` →
  `UnitTests/Application/Orders/CreateOrderHandlerTests.cs`.
- One test class per production class, named `<Type>Tests`. `[Fact]` for one case, `[Theory]` with
  `[InlineData]` / `[MemberData]` for a table.
- A test name states the behaviour and the condition, not the method:
  `Returns_not_found_when_the_order_does_not_exist`.
- xUnit creates a **new instance of the test class per test**; shared setup goes in the constructor and
  teardown in `IAsyncLifetime.DisposeAsync`. Anything static is shared across the whole run and is the
  usual cause of a suite that passes alone and fails together.

## Unit tests

- **Construct the class under test directly with fakes.** Never resolve it from a container: the test
  then also tests the registration, and fails for reasons that have nothing to do with the code.
- A hand-written fake when the double **carries behaviour** (an in-memory repository over a `List`, a
  token provider that counts refreshes) — more readable than five stub setups and reusable across the
  suite. A mocking library when the point of the test is **that a call was made** with given arguments.
  Keep reusable fakes in one place and reuse them rather than re-inventing per test.
- **`FakeTimeProvider` instead of waiting.** Any test containing `Task.Delay` or `Thread.Sleep` to let
  something happen is either slow or flaky, usually both — inject `TimeProvider` and advance it
  (`rules/csharp.md`).
- Assert the **failure paths**: every `DomainError` case a use case can return gets a test. A suite of
  happy paths tests nothing that breaks in production.
- Assert on the returned `Result`, not on a log call. Logging is not a contract.

## Integration tests

`WebApplicationFactory<Program>` runs the **real** pipeline — real routing, real middleware order, real
model binding, real authorization — which is exactly what unit tests cannot cover. That requires `Program`
to be reachable from the test project (a `public partial class Program { }` at the end of `Program.cs`, or
`InternalsVisibleTo`).

```csharp
public sealed class ApiFactory : WebApplicationFactory<Program>, IAsyncLifetime
{
    private readonly PostgreSqlContainer _database = new PostgreSqlBuilder().Build();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["ConnectionStrings:Default"] = _database.GetConnectionString(),
        }));

        builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<IPaymentGateway>();          // remove first — otherwise the original wins
            services.AddSingleton<IPaymentGateway, FakePaymentGateway>();
        });
    }

    public async Task InitializeAsync()
    {
        await _database.StartAsync();
        await using var scope = Services.CreateAsyncScope();
        await scope.ServiceProvider.GetRequiredService<AppDbContext>().Database.MigrateAsync();
    }

    // WebApplicationFactory already declares `ValueTask DisposeAsync()`; xUnit v2's IAsyncLifetime
    // declares `Task DisposeAsync()`. Same name, different return type — the interface member must
    // be implemented explicitly or the class does not compile. (xUnit v3 returns ValueTask and the
    // clash disappears; check which one the project is on before copying this.)
    async Task IAsyncLifetime.DisposeAsync()
    {
        await base.DisposeAsync();        // the host
        await _database.DisposeAsync();   // and the container — forgetting this leaks it for the run
    }
}
```

- **A real database in a container, never the EF in-memory provider.** The in-memory provider has no SQL,
  no constraints, no transactions and different LINQ translation — a test that passes on it says nothing
  about whether the query runs. SQLite in-memory is the same trade in a smaller size.
- **`RemoveAll<T>()` before adding a substitute.** Adding alone leaves both registrations; the original
  may win, and the test passes against production code it meant to replace.
- Replace only the true externals — a payment provider, an email sender, the clock. Replacing the
  repository turns an integration test back into a unit test with more setup.
- **One container for the class or the collection, data reset between tests.** Starting a container per
  test makes the suite unusable; sharing state between tests makes them order-dependent. Reset by
  truncating or by wrapping each test in a rolled-back transaction, and say which in the fixture.
- Authenticate by issuing a real token against a test signing key, or by a test authentication handler
  registered in `ConfigureTestServices` — never by disabling authorization, which deletes the thing most
  worth testing.
- Assert the **status code and the body contract**, including the `ProblemDetails` shape and its `code`
  for each failure — that is what clients depend on (`dotnet-error-handling`).

## Data layer

- A repository test runs against the containerised database: assert the mapping, the tracking behaviour
  and the failure-to-`DomainError` mapping.
- **A schema change that data depends on gets a migration test**: migrate to the previous version, seed,
  migrate up, assert the data survived. This is the one place where "it compiles" proves nothing
  (`efcore-persistence`).
- A query whose point is the SQL (a projection, a paging window) is worth asserting on the result set,
  not on the generated SQL string — which changes with every provider upgrade.

## Async and determinism

- `await` every assertion that returns a task, and never `.Result` in a test — it deadlocks the same way
  it does in production and the failure looks like a hang.
- No test depends on the machine's time zone, culture or environment variables. Pin the culture in the
  test when the code under test formats anything.
- A flaky test is a failing test. Quarantining one needs a tracked issue in the skip reason; a bare
  `Skip = "flaky"` is forbidden (`v1rus-qa` § 4).

## Running

Read the project's `CLAUDE.md` for the exact commands; the usual shape is `dotnet build` for the
compile gate, `dotnet test` for the suite, `dotnet test <project>` or `--filter` for a scope, and
`dotnet format --verify-no-changes` for style. Never invent a command; if the project documents nothing
and the choice is ambiguous, say so rather than guessing.

Scope the run to the change (`check` skill): a logic change runs the affected project, a rename or a
comment edit needs the build only. Integration tests need a container runtime available — when there is
none, say so instead of reporting a pass for a level that did not run. Long runs go to the `test-runner`
agent so a full suite does not consume the orchestrating session's context.

## Non-negotiable

Whoever breaks an existing test fixes it in the same change. A `Skip` without a tracked-issue reference is
forbidden, and a red suite is never merged — `v1rus-qa` § 4.
