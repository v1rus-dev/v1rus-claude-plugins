---
name: kotlin-conventions
description: "v1rus Kotlin conventions for .kt and .kts code — the rules a model omits by default: narrowest-visibility discipline (private → internal → public, never explicit `public`), collection extension operators over imperative for-loops and when a for-loop is still right, named arguments for ambiguous and boolean parameters, deleting empty blocks, value-class validation with init/require, nullable-parameter design smell and overloads, commonMain constraints, and Clean Architecture + MVI layering rules. Load when writing or reviewing Kotlin, deciding a declaration's visibility, or judging whether Kotlin code follows project conventions."
---

# Kotlin Conventions

The full rulebook is `${CLAUDE_PLUGIN_ROOT}/rules/kotlin-style.md` — **read it** before writing or
reviewing non-trivial Kotlin. It is deliberately a single source: the same file is injected
automatically by this plugin's `path-rules` hook just before any `.kt` / `.kts` edit, so when you
are about to edit Kotlin you may already have it in context.

It documents only what a modern model gets wrong or omits without a reminder. Generic idiomatic
Kotlin — null safety, naming, file organisation — is not in there on purpose; trust the model and
the official [Kotlin coding conventions](https://kotlinlang.org/docs/coding-conventions.html).

The four rules most often violated, so you can catch them without the full read:

- **Visibility is the narrowest that still works.** `private` first, then `internal`, `public` only
  as a deliberate API decision — and never written out, since it is the default.
- **Named arguments** are required for same-typed parameter groups, non-obvious primitives, and
  every lone boolean literal.
- **`@JvmInline value class` wrappers that enforce a constraint carry `init { require(...) }`** —
  the wrapper without the check is the usual omission.
- **`commonMain` takes no `android.*` / `java.*` / `javax.*` imports** and prefers `kotlinx.*` over
  JVM-only equivalents.

Related: `${CLAUDE_PLUGIN_ROOT}/rules/coroutines.md` (the `kotlin-coroutines` skill) for anything
`suspend` or `Flow`, and the `gradle-conventions` skill for build scripts.
