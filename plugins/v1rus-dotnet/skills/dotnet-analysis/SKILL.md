---
name: dotnet-analysis
description: "Build-level quality settings for a v1rus .NET solution: Directory.Build.props carrying Nullable enable and TreatWarningsAsErrors and EnforceCodeStyleInBuild for every project so a warning is a build failure rather than console noise, Directory.Packages.props central package management so a version exists in exactly one place and cannot drift per project, the analyzer level and the rule categories worth raising to error, .editorconfig as the single style source with dotnet format checked in CI, and the requirement that any pragma or SuppressMessage carries a reason. Load when setting up or editing Directory.Build.props or Directory.Packages.props or .editorconfig, adding a project to the solution, adding or bumping a package reference, when an analyzer warning fires and a suppression is being considered, or when adding a rule to the corporate set."
---

# Build and Static Analysis

A warning is a **build failure**, not advice. Everything below exists so a defect is caught by the
compiler instead of a reviewer's attention.

## `Directory.Build.props` — one place, every project

At the repository root, so a new project inherits the settings instead of being configured by hand and
forgotten:

```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net<major>.0</TargetFramework>   <!-- the solution's floor, resolved at plan time -->
    <LangVersion>latest</LangVersion>
    <ImplicitUsings>enable</ImplicitUsings>

    <Nullable>enable</Nullable>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <WarningsNotAsErrors></WarningsNotAsErrors>

    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <AnalysisLevel>latest-recommended</AnalysisLevel>
    <AnalysisMode>Recommended</AnalysisMode>

    <GenerateDocumentationFile>true</GenerateDocumentationFile>
    <Deterministic>true</Deterministic>
    <ContinuousIntegrationBuild Condition="'$(CI)' == 'true'">true</ContinuousIntegrationBuild>
  </PropertyGroup>
</Project>
```

Why each of the load-bearing ones:

- **`Nullable` without `TreatWarningsAsErrors` does nothing.** Nullable findings are warnings; in a
  solution with any build noise they are invisible within a week. The pair is what makes the annotations
  mean something — and it is why `!` is a decision, not a shortcut (`rules/csharp.md`).
- **`EnforceCodeStyleInBuild`** makes the `.editorconfig` style rules part of the build rather than an
  IDE-only suggestion, so a machine without the IDE settings produces the same result.
- **`GenerateDocumentationFile`** turns on the XML-doc analyzers; if the resulting "missing doc" warnings
  are not wanted, disable those specific rule ids in `.editorconfig` with a comment — do not turn the
  property off, because it also gates useful diagnostics.
- `Deterministic` + `ContinuousIntegrationBuild` make CI output reproducible and the paths in it portable.

Test projects that need to relax a rule do so in a `tests/Directory.Build.props` that imports the parent —
never by editing the root file for everyone.

## `Directory.Packages.props` — central package management

```xml
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
    <CentralPackageTransitivePinningEnabled>true</CentralPackageTransitivePinningEnabled>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Microsoft.EntityFrameworkCore" Version="<resolved at plan time>" />
  </ItemGroup>
</Project>
```

A project file then references the package **without a version**:
`<PackageReference Include="Microsoft.EntityFrameworkCore" />`.

- One version per package for the whole solution. Without this, two projects drift onto two versions of
  the same package, the build picks one, and the mismatch surfaces at runtime as a missing method.
- A version in a `.csproj` alongside central management is an error by design — that is the point.
- **Every version here is resolved and CVE-checked at plan time through the `v1rus-dependencies` gate.**
  Nothing is added from memory, and a bump is a decision with a changelog behind it, not a tidy-up.
- Transitive pinning turns a vulnerable transitive dependency into something you can fix in one place.

## `.editorconfig` — the single style source

Style lives in `.editorconfig` and nowhere else: naming, `var` usage, file-scoped namespaces, `using`
placement and sorting, braces, expression bodies. `dotnet format --verify-no-changes` runs in CI, so
formatting is never a review topic.

The severities worth raising beyond the default, because each catches a real defect class rather than a
preference:

| Category | Why |
|---|---|
| Nullable diagnostics (`CS86xx`) | already errors via `TreatWarningsAsErrors`; never downgrade them per-project |
| `CA2007` (await without `ConfigureAwait`) | **on in library projects, off in the app** — in an ASP.NET Core app it is pure noise (`rules/csharp.md`) |
| `CA1848` / `CA2254` (logging performance, non-constant template) | catch the interpolated log message before review does (`dotnet-observability`) |
| `CA2016` (forward the `CancellationToken`) | the token accepted and not passed on |
| `CA1305` / `CA1307` / `CA1310` (culture) | the culture-sensitive comparison and format defaults |
| `CA2100` (SQL injection review) | raw SQL built from a string |
| `xUnit1031` and the async analyzers | blocking on a task inside a test |
| `VSTHRD` async analyzers (when the threading analyzers are referenced) | `async void`, sync-over-async |

## A suppression needs a reason

```csharp
#pragma warning disable CA1852 // sealed by the test project's InternalsVisibleTo — see ApiFactory
```

- A `#pragma` or `[SuppressMessage]` without a justification is a silent suppression and is a review
  finding.
- Scope it to the narrowest span that needs it, and re-enable it (`#pragma warning restore`).
- `<NoWarn>` in a project file is the widest possible suppression and needs the same justification, in a
  comment, in the project file.
- **A rule that gets suppressed repeatedly is either wrong for this solution** — then turn it off once in
  `.editorconfig` with a comment explaining why, so the decision is visible in one place — **or the code
  is wrong.** Scattered pragmas are the worst of both.

## Adding to the standard

A new analyzer rule enters the corporate set with a stated reason: the defect class it catches, and
whether it is mechanical to satisfy in an existing codebase. Rolling a strict rule onto a legacy solution
with no migration path produces hundreds of errors and ends with the whole category disabled.

## Generated code

Source-generated and scaffolded files are excluded from style analysis, never hand-edited, and never
committed with manual fixes — the generator input is what gets reviewed. EF Core migrations are the
exception: they are generated and then **read and corrected** before they are committed
(`efcore-persistence`).
