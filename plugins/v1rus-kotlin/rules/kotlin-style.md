---
paths:
  - "**/*.kt"
  - "**/*.kts"
---

# Kotlin style and layering

Covers conventions a modern model omits by default. Generic idiomatic Kotlin (null safety, naming, file organization) is not repeated here; follow the official Kotlin coding conventions. An established project convention that differs from a rule below wins.

## Visibility: minimum by default

Pick the narrowest visibility that works: `private` (one file/class) over `internal` (one module) over public (deliberate API surface).

- New code in implementation modules/packages: `internal` by default, `private` when not referenced outside its file/class.
- Top-level functions, extensions, properties, constructors, companion members, sealed hierarchies follow the same priority. A constructor used only via a factory or DI is `internal`/`private`.
- Do not write the `public` keyword (it is the default); reserve explicit modifiers for `internal` and `private`.
- Unsure between `internal` and public: `internal`. Widening later is trivial; narrowing is breaking.
- `.kts` scripts (convention plugins, build scripts): same rule for top-level helpers.

## Collections: operators over `for` loops

Prefer stdlib operators (`filter`, `map`, `mapNotNull`, `flatMap`, `sumOf`, `count`, `groupBy`, `associateBy`, `find`, `firstOrNull`, `any`/`all`/`none`, `fold`, `buildList`/`buildMap`, `onEach`) over imperative loops with `if`/`add`/`continue`.

Keep a `for` loop when: the body early-`return`s from the enclosing function; several unrelated side effects happen per iteration; index/neighbour access is clearer than `zipWithNext`/`windowed`; a profiled hot path needs to avoid intermediate collections (try `asSequence()` first). Past three operators or a `let` tower, reconsider, but do not fall back to `for` mechanically.

## Named arguments for ambiguous calls

Name an argument when it is a primitive whose meaning is not obvious at the call site, when several parameters share a type (name all of that type), or when it is a lone boolean literal (`setVisible(visible = true)`). Positional is fine for a domain-typed argument that documents itself (`show(dialog)`) and for well-known stdlib calls (`maxOf(a, b)`, `Pair(k, v)`). Test: a reader who sees only the call site must infer each argument.

## Empty blocks: delete the call

An empty `apply {}` / `also {}` / `run {}` / `let {}` / `forEach {}` / `onEach {}` / `init {}` carries no behaviour: delete it (or replace with the receiver if the value is used). Keep an empty body required by an interface/abstract override, with a one-line `// no-op: <reason>`. An empty `onClick = {}` default is acceptable only if the API requires non-null; prefer a nullable parameter. An empty `catch` is a separate problem: handle/log it or remove the `try`.

## Value classes

When an `@JvmInline value class` wraps a primitive that has a constraint (non-blank, format, range), add `init { require(...) { "message" } }`. Skip it for opaque values with no real constraint (server-generated ids).

## Nullability and overloads

A nullable parameter or receiver on an extension/top-level function is a design smell: handle the absent case at the call site (`?.`) or provide an overload. Prefer overloads over one function with many nullable/default parameters when the variants behave differently.

## Multiplatform source sets

- No `android.*`, `java.*`, `javax.*`, `dalvik.*` imports in `commonMain`; only stdlib and multiplatform-capable libraries.
- `expect`/`actual` only for platform implementation details; business logic stays in `commonMain`.
- Prefer `kotlinx.*` (`datetime`, `serialization`, `coroutines`) over JVM-only equivalents there.

## Layering (Clean Architecture + MVI)

- A use case has a single responsibility and one public `operator fun invoke()` (or the project's convention).
- Repository interfaces live in the domain layer, implementations in the data layer.
- Domain models have no framework dependencies (exceptions: `kotlinx.coroutines`, `kotlinx.datetime`, `kotlinx.serialization` annotations).
- Mapping is done by explicit mapper functions/classes, never inside data classes. Data-layer types (DTOs, entities) never cross a repository interface: map to domain models at the boundary.
- Lifecycle-bound scopes (`viewModelScope`, `lifecycleScope`) belong to the presentation layer only, not to use cases or repositories.
