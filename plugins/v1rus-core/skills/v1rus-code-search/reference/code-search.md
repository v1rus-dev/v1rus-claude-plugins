# Code search

Pick the navigation tool by the question, not by habit.

| Task | Tool |
|---|---|
| Find a class/type/function/symbol by name, usages, references | symbol index (`ast-index class|symbol|search|usages|refs`) when available |
| Implementors, hierarchy, callers, call tree | symbol index (`implementations`, `hierarchy`, `callers`, `call-tree`) |
| Module dependencies and dependents, public API of a module | symbol index (`deps`, `dependents`, `api`) |
| Symbols in a file, to decide what to read | symbol index (`outline <file>`) |
| Type resolution, exact definition, precise call hierarchy | LSP (hover, goToDefinition, incomingCalls/outgoingCalls) |
| Regex, string literals, comment text, config values, log messages | Grep |
| Find a file by path pattern | Glob |

## Rules

1. Symbol index first for any "find X" task; LSP when type-aware answers are needed; Grep for regex, literals, comments, configs, or when the index returns nothing.
2. Never Grep for a code symbol by name when an index is available, and never Grep "for completeness" after the index returned results.
3. Never Glob for a source file by class name when the index can answer.
4. Before reading a file longer than about 500 lines, get its outline and then read only the needed slice (`offset`/`limit`).
5. If the index reports "not found/not initialized", bootstrap it (`ast-index rebuild` via Bash, or the stack's init skill) and retry; do not silently fall back to Grep.
6. No index installed in this environment: use LSP, then Grep/Glob, and say so; do not install tooling without approval.

An index is kept fresh by the tool's own watcher or the owner's hooks; do not run manual updates in normal work.
