---
name: csharp-conventions
description: "C# rules a model omits by default: async void and sync-over-async, a CancellationToken accepted and then not passed down, IEnumerable enumerated twice, IQueryable leaking out of the class that owns it, DateTimeOffset versus DateTime and never reading the clock statically, culture-sensitive string comparison and formatting where ordinal was meant, exceptions used for expected failures, silencing a nullable warning with !, disposing an injected dependency, records versus classes for equality, and interpolated strings in a log call. Load when writing or reviewing C# of any kind, or when deciding how to handle an async call, a nullable annotation, a comparison, a time value, or a failure. Do NOT load for ASP.NET Core request-pipeline specifics (aspnetcore-api) or EF Core query behaviour (efcore-persistence)."
---

# C# Conventions

The full rulebook is `${CLAUDE_PLUGIN_ROOT}/rules/csharp.md` — **read it** before writing or reviewing
non-trivial C#. It is a single source: the same file is injected automatically by this plugin's
`path-rules` hook just before any `.cs` edit, so when you are about to write code it is usually already
in context. Read it directly when reviewing, since a review performs no edit and triggers no injection.

It documents only what a modern model gets wrong without a reminder. Generic idiomatic C# is left to the
model, to the .NET analyzers and to `.editorconfig` (`dotnet-analysis`).

The five that cause production incidents:

- **`async void` and sync-over-async.** `async void` takes the process down on an unhandled exception;
  `.Result` / `.Wait()` deadlocks and burns a thread-pool thread per call, so the service falls over under
  load with the CPU idle.
- **A `CancellationToken` that is accepted and not passed on.** It advertises cancellation the caller never
  gets, and the work keeps running for a client that hung up.
- **`IEnumerable<T>` enumerated twice.** The source re-executes — a second round trip, or a different
  answer than the first pass got.
- **Culture-sensitive comparison by accident.** `ToUpper()`, `StartsWith(string)` and `IndexOf(string)` are
  culture-sensitive by default; on a Turkish locale an identifier comparison changes answer. Pass
  `StringComparison.Ordinal` explicitly for anything machine-readable.
- **`DateTime.Now` and a statically-read clock.** The server's local zone gets baked into stored data, and
  nothing time-dependent can be tested. Use `DateTimeOffset` and inject `TimeProvider` (.NET 8+).

Related: `dotnet-error-handling` (`Result` versus throwing), `dotnet-di` (lifetimes and disposal
ownership), `dotnet-observability` (message templates), and the `v1rus-logging` skill for what must never
reach a log.
