---
name: v1rus-code-search
description: "How to navigate a v1rus codebase without burning context: use ast-index for any symbol, class, usage, implementation, hierarchy, call-graph or module-dependency lookup; use LSP when type resolution is needed; use Grep only for string literals, regex, comments and config values; outline a large file before reading it. Load before searching for a class, function, symbol or usage, when tempted to grep for a code identifier or glob for a source file by class name, or when a search returns nothing."
---

# Code Search

Three tools cover all code navigation. Picking the wrong one is the most common way an agent burns
context: a `Grep` for a class name reads dozens of irrelevant matches where a structured lookup
returns one line.

## Decision matrix

| Task | Tool |
|------|------|
| Find class / interface / struct | `ast-index class "Name"` |
| Find any symbol by name | `ast-index symbol "Name"` |
| Universal search (symbol + file + refs) | `ast-index search "query"` |
| Find all usages of a symbol | `ast-index usages "Name"` |
| Find all references (defs + imports + usages) | `ast-index refs "Name"` |
| Find subclasses / implementors | `ast-index implementations "Interface"` |
| Class / type hierarchy | `ast-index hierarchy "ClassName"` |
| Who calls a function | `ast-index callers "functionName"` |
| Call tree | `ast-index call-tree "fn" --depth 3` |
| Module dependencies / reverse dependents | `ast-index deps "module"` / `ast-index dependents "module"` |
| Symbols in a file | `ast-index outline path/to/File.kt` |
| Public API of a module | `ast-index api "module-path"` |
| Potentially unused symbols | `ast-index unused-symbols` |
| TODO / FIXME / HACK | `ast-index todo` |
| Regex / string-literal search | **Grep** |
| Comment content search | **Grep** |
| Type resolution, inferred types | **LSP hover** |
| Go to definition (type-aware) | **LSP goToDefinition** |
| Precise call hierarchy | **LSP incomingCalls / outgoingCalls** |

Run `ast-index --help` or `ast-index <command> --help` for exact syntax — do not guess flags.

## Priority rules

1. **`ast-index` first** for any "find X" task — structured results, single-digit milliseconds.
2. **LSP** when semantic type resolution is genuinely needed (hover, exact definition, generics).
3. **Grep** only for regex patterns, string literals, comments, config values, log messages.
4. **Never** run a Grep "for completeness" after `ast-index` already returned results.

## Hard rules

- **Never use Grep to find a class, function, interface, variable or any code symbol by name.**
  That is always `ast-index` territory.
- **Never use Glob to find a source file by class or module name.** Use `ast-index search` or
  `ast-index class`.
- If `ast-index` reports "Index not found" — **bootstrap it, do not fall back to Grep**: run
  `ast-index rebuild` via Bash (this works from any agent, including read-only search agents that
  have no Skill tool), then retry the query. Skipping the search entirely is also not an option.
- If the `ast-index` CLI is not installed at all, say so explicitly before degrading to Grep, so the
  reduced confidence is visible rather than silent.

## Large-file reads

Before `Read` on a file longer than roughly 500 lines, run `ast-index outline <file>` and then read
only the needed slice via `offset` / `limit`. The outline is the symbol map that lets you target an
exact range — bulk-reading a large file is not an acceptable substitute.

## Forbidden directories

Never read, search, list or grep inside dependency and build caches — `.gradle/`, `.m2/`,
`node_modules/`, `Pods/`, `.venv/`, `target/`, `build/`, `DerivedData/` — anywhere on the system.
They hold caches, jars and compiled artifacts, no source. For dependency information read the
build file (`build.gradle(.kts)`, `libs.versions.toml`, `pom.xml`, `package.json`, `Package.swift`)
instead; to read a JVM dependency's actual source use `ksrc` (see the `v1rus-kotlin` plugin).
