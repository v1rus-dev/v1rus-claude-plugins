---
paths:
  - "**/*.{ts,tsx,mts,cts,js,mjs,cjs}"
---

# TypeScript/JavaScript source: type modelling and module hygiene

Layer: framework-agnostic. Read the project's tsconfig and eslint config first; they override these defaults. Do not reformat or modernise code outside the task diff.

## Types
- `unknown` over `any` for anything not known (JSON, catch, untyped libs, parsed input). `any` only in an isolated adapter with a one-line reason.
- No `!` and no `as` to silence the compiler. Narrow, use a guard, or `satisfies`. `as` is for `as const`, a narrowing after a proven check (with comment), and test fixtures.
- Model states as discriminated unions with a literal tag (`kind`/`type`/`status`), not optional-field soups.
- Exhaustive `switch` over a union: `default` assigns the value to `never` (or calls a shared `assertNever`).
- No `enum` / `const enum` / runtime `namespace` / constructor parameter properties in new code: use `as const` objects with a derived union, or string-literal unions. These are not erasable (Node type stripping rejects them) and `const enum` breaks isolated transpilation. In an existing project that already uses enums, follow the project and note it in one line.
- `satisfies` for config and lookup tables (checks shape, keeps narrow literal types).
- Branded types for IDs/units that must not be mixed, minted only by a validating constructor. Not for every string.
- `readonly` by default for properties and arrays that are not mutated. `null` only at I/O boundaries (JSON, DB); map to `undefined` or a domain type inside.
- Generics only when a type parameter relates two positions; constrain them (`T extends ...`).
- Avoid `Function`, `Object`, `{}` as types: use `object`, `Record<string, unknown>` or a call signature.
- Derive types from schemas/values (`typeof x`, `ReturnType`, schema `infer`), never duplicate a type and its schema by hand.
- Explicit return types on exported functions of libraries (also required by `isolatedDeclarations`); inference is fine internally.
- Keep conditional/mapped/template-literal types short; a type that needs a paragraph of explanation is the wrong tool.
- Decorators are not erasable: use only where a framework requires them.

## Modules and style
- ESM syntax. Relative imports carry the extension that the project's `module` setting requires (`./x.js` for tsc-emitted output; `./x.ts` only with `allowImportingTsExtensions` / `rewriteRelativeImportExtensions`).
- `import type` / inline `type` for type-only imports when `verbatimModuleSyntax` is on (it is an error otherwise).
- Prefer the `node:` prefix for Node builtins.
- Named exports; default export only where a tool requires it (config files). No re-export-all barrel files inside applications; a library has one deliberate curated entry.
- No work at import time (module top level is side-effect-free except a documented entrypoint). Use `top-level await` in apps/scripts, not in library entry points (breaks `require(esm)`).
- `const` by default, no parameter mutation; `toSorted/toReversed/toSpliced/with` and `structuredClone` instead of mutating copies, when the minimum runtime supports them.
- File names kebab-case; one primary concept per file; PascalCase types/classes, camelCase values, no `I`/`T` prefixes.
- `using` / `await using` only when every runtime in the support matrix has explicit resource management (check `lib`/`target` and the Node line); otherwise `try/finally`. Never polyfill silently in a library.
- Do not use `Temporal` or other very recent built-ins without checking the minimum Node line actually ships them (run a one-line `node -e` probe).
- Comments explain why, not what. Exported API of a library gets TSDoc (`@param name - text`, `@returns`, `@throws`, `@deprecated` with replacement). Update docs in the same change.
