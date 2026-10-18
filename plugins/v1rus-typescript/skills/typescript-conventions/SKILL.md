---
name: typescript-conventions
description: "v1rus TypeScript conventions for .ts/.tsx/.mts/.cts — the rules a model omits by default: any is a defect and unknown is the boundary type, `as` and `!` are unchecked assertions, a type annotation on JSON.parse or a fetch response is a wish rather than a fact, discriminated unions instead of optional-field bags, every union switch ending in a never guard, satisfies instead of a widening annotation, readonly and as const, unknown in catch and wrapping with cause, no floating promises, type-only imports, no deep imports, and disables that carry a reason. Load when writing or reviewing TypeScript, judging whether a diff follows the project's TypeScript conventions, or deciding how to type a value that came from outside the program. Not needed for React/JSX specifics, Node or Nest specifics, or monorepo wiring — those live in the layers above."
---

# TypeScript Conventions

The full rulebook is `${CLAUDE_PLUGIN_ROOT}/rules/typescript.md` — **read it** before writing or
reviewing non-trivial TypeScript. It is a single source: the same file is injected automatically by
this plugin's `path-rules` hook just before any `.ts` / `.tsx` / `.mts` / `.cts` edit, so when you are
about to write code it is usually already in context. Read it directly when reviewing, since a review
performs no edit and triggers no injection.

It documents only what a modern model gets wrong without a reminder. Generic idiomatic TypeScript is
left to the model, to the compiler and to `typescript-eslint`.

The four that cause production bugs:

- **A declared type on external data is a lie.** `JSON.parse`, a fetch response body, environment
  variables and storage reads are unchecked at runtime. Parse at the boundary, once.
- **`any`, `as` and `!` each switch the checker off** at exactly the place where you are least sure.
  `unknown` plus narrowing is the honest form.
- **A `switch` over a union without a `never` guard** silently stops covering the union the day
  someone adds a variant.
- **A floating promise** is a lost error and, in a modern runtime, frequently a lost process.

Depth lives in the sibling skills: `ts-project-config` (tsconfig, ESM, build vs typecheck),
`ts-type-modelling`, `ts-boundaries-validation`, `ts-error-handling`, `ts-async`,
`ts-package-structure`, `ts-lint-and-format`. Process, gates and complexity bands come from
`v1rus-workflow` and `v1rus-qa`; logging from `v1rus-logging`; adding any package from
`v1rus-dependencies`.
