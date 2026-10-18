# v1rus-typescript

The TypeScript language and toolchain layer shared by every v1rus TypeScript project. Depends on
`v1rus-core` and is itself the base for the platform layers above it — `v1rus-node`, `v1rus-react`
and `v1rus-fullstack`.

```
/plugin install v1rus-typescript@v1rus     # v1rus-core is installed automatically
```

Everything here is true for a Node service and for a browser application alike. Nothing here knows
what a component, a controller or a route is.

## What it contains

| Component | Content |
|---|---|
| [`rules/typescript.md`](rules/typescript.md) | The compact rulebook: types that lie (`any`, `as`, `!`, an annotation on external data), discriminated unions and the `never` guard, `satisfies`, `readonly`, the boundary rule, `unknown` in `catch` and `cause`, floating promises and `AbortSignal`, type-only imports and deep imports, and escapes that carry a reason. Injected automatically before any `.ts` / `.tsx` / `.mts` / `.cts` edit. |
| [`skills/typescript-conventions`](skills/typescript-conventions/SKILL.md) | Front door to the rulebook for read-only and planning contexts that never trigger an edit. |
| [`skills/ts-project-config`](skills/ts-project-config/SKILL.md) | `strict` as the floor and the options it does not include, `moduleResolution` and what each mode demands of import specifiers, ESM, `verbatimModuleSyntax` and `isolatedModules`, why a green bundler build proves nothing and `tsc --noEmit` is the gate, project references, declaration output. |
| [`skills/ts-type-modelling`](skills/ts-type-modelling/SKILL.md) | Illegal states unrepresentable, exhaustive `switch` with `assertNever`, `satisfies` vs annotation vs `as`, branded ids, immutability, unions instead of enums, generics that earn their type parameter, and the traps in `Omit`, `Partial`, overloads and `interface` merging. |
| [`skills/ts-boundaries-validation`](skills/ts-boundaries-validation/SKILL.md) | Why a type on `JSON.parse` or a response body is a lie, the full inventory of boundaries, parse-don't-validate with the type derived from the schema, strict on input and permissive on third-party responses, environment configuration parsed once at startup, what to do when a parse fails, and where **not** to validate. |
| [`skills/ts-error-handling`](skills/ts-error-handling/SKILL.md) | `unknown` in `catch`, `Error` subclasses with `name`, a machine-readable code and `cause`, why `instanceof` is unreliable, never swallow and never log-and-rethrow at every level, `return await` inside `try`, aborts that are not failures, and the line between a returned typed result and a throw. |
| [`skills/ts-async`](skills/ts-async/SKILL.md) | Floating promises and why `void` alone is not a fix, async callbacks in void slots, deliberate vs accidental sequential awaits and bounded concurrency, `all`/`allSettled`/`any`/`race` semantics, `AbortSignal` propagation and composition, async cleanup, and the stale-response and single-flight traps. |
| [`skills/ts-package-structure`](skills/ts-package-structure/SKILL.md) | The `exports` map as the only public API, no deep imports, aliases that the runtime can actually resolve, the real cost of barrel files, cycles that typecheck and fail at module init, `sideEffects`, and workspace package boundaries. |
| [`skills/ts-lint-and-format`](skills/ts-lint-and-format/SKILL.md) | ESLint flat config, type-aware `typescript-eslint` and the rules that do not exist without it, the v1rus additions, Prettier owning formatting, and disables that name one rule and carry a reason. |

## Design notes

**One source per rule.** The rulebook lives once, in `rules/typescript.md`. The `path-rules` hook
injects it verbatim before a matching edit (deterministic, and it arrives before the code is
written); `skills/typescript-conventions` is a thin front door pointing at the same file, for
contexts that never edit — a reviewer, a planner, a question in chat. The text is not forked into
the skill. The seven deep skills are separate bodies: the rulebook states each rule in a line or two
and names the skill that owns the detail.

**Why the hook is duplicated.** `hooks/path-rules.py` is a byte-for-byte copy of the one in
`v1rus-core`. `${CLAUDE_PLUGIN_ROOT}` resolves per plugin, so a layer cannot read a sibling's
`rules/` directory; each layer carrying its own copy is what makes the layers independently
installable.

**No agents and no pipeline profile here — deliberately.** An engineer agent needs a stack
vocabulary (where a module lives, what the build task is called, which framework owns a layer), and
a pipeline profile is that vocabulary written down. This layer has neither, because "TypeScript" is
not a stack you can lay out a project in. The engineer agents and the `*-pipeline-profile` skills
live in `v1rus-node`, `v1rus-react` and `v1rus-fullstack`, which know whether they are looking at a
service or an application. Adding an agent here would force it to guess, which is the failure mode
the layering exists to prevent.

**No test rules here either.** Test frameworks and their conventions belong to the layers above; the
complexity bands that decide whether tests are written at all come from `v1rus-qa` in the core.

**What deliberately is not here.** Anything React, JSX or Next — components, hooks, rendering,
routing, the server/client boundary — belongs to `v1rus-react`. Anything NestJS, Prisma, HTTP-server
or Node-runtime belongs to `v1rus-node`. Monorepo tooling, cross-application contracts and shared
build orchestration belong to `v1rus-fullstack`. A rule that holds for every TypeScript project,
backend and browser alike, belongs here.

**No pinned versions.** Package names only, TypeScript included. Versions are resolved at plan time
through the `v1rus-dependencies` gate. The two version numbers that do appear are minimum
requirements for mechanisms that do not exist below them (`isolatedDeclarations`, `await using`),
and they are stated as such.
