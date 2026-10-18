---
name: ts-project-config
description: "How a v1rus TypeScript project is configured and how it is actually checked: `strict` is the floor and not the ceiling (noUncheckedIndexedAccess, exactOptionalPropertyTypes, noImplicitOverride, noFallthroughCasesInSwitch, noUnusedLocals), moduleResolution bundler versus node16/nodenext and what each demands of import specifiers, ESM as the default with file extensions in relative imports and no __dirname, verbatimModuleSyntax and isolatedModules forcing `import type` / `export type`, why a green bundler build proves nothing and `tsc --noEmit` is the only type gate, project references and incremental builds, and declaration output for a published package. Load when creating or editing tsconfig.json, adding a compiler option, wiring the typecheck or build script, moving a project to ESM, debugging why an import resolves in the editor but not at runtime, or when a type error is being silenced by loosening the config. Not for ESLint or Prettier configuration (`ts-lint-and-format`) or for monorepo tooling and task orchestration, which belong to the layer above."
---

# TypeScript Project Configuration

The compiler is the cheapest reviewer on the team. Most TypeScript codebases run it at a fraction of
its strength and then discover at runtime what it was willing to prove.

## `strict` is the floor

`"strict": true` is assumed, never negotiated, and it is not the whole set. The options below are
**not** in `strict` and each one closes a class of real bug:

| Option | What it catches |
|---|---|
| `noUncheckedIndexedAccess` | `arr[0]` and `record[key]` become `T \| undefined` — the single highest-value non-default. Array and record access is the most common source of a runtime `undefined` in otherwise strict code. |
| `exactOptionalPropertyTypes` | Distinguishes "absent" from "present and `undefined`". Without it, `{ name: undefined }` satisfies `{ name?: string }`, and an explicit `undefined` silently overwrites a default. |
| `noImplicitOverride` | A method that no longer overrides anything (base renamed) stops being flagged silently. |
| `noFallthroughCasesInSwitch` | Accidental fallthrough in a `switch` — pairs with the `never` guard from `ts-type-modelling`. |
| `noUnusedLocals`, `noUnusedParameters` | Dead code and leftover parameters after a refactor. |
| `noPropertyAccessFromIndexSignature` | Forces `obj['key']` for index-signature reads so a real declared property is visually distinct from a guessed one. |
| `noImplicitReturns` | A branch that forgets to return. |

Two rules about them:

- **Turn them on at project creation.** Retrofitting `noUncheckedIndexedAccess` onto a mature
  codebase is a real migration; starting with it costs nothing.
- **Never loosen the config to make an error go away.** Widening a compiler option to silence one
  file trades a local fix for a repo-wide hole. Fix the code, or narrow the escape to one line
  (`@ts-expect-error -- reason`).

`skipLibCheck: true` is normal and stays on — it skips `.d.ts` files you do not own, not your own
code. `allowJs` stays off unless a migration is actively in progress.

## Modules and resolution

`moduleResolution` decides which import specifiers are legal, and getting it wrong produces the
signature failure "the editor is happy, the runtime is not".

- **`bundler`** — for code a bundler consumes. Extensionless relative imports are fine because the
  bundler resolves them. Pair with `module: "preserve"` or `esnext`, `noEmit: true`.
- **`node16` / `nodenext`** — for code a runtime loads directly. Relative ESM imports **must** carry
  the emitted extension: `import { x } from './thing.js'` from a file named `thing.ts`. That looks
  wrong and is correct; TypeScript does not rewrite specifiers on emit, ever.
- **`node` / `node10`** — legacy. Do not use it in new code: it ignores `exports` maps, so it will
  happily resolve a deep path a package deliberately made private (`ts-package-structure`).

ESM is the default for new code (`"type": "module"`). What actually changes:

- `__dirname` and `__filename` do not exist — `import.meta.url`, or `import.meta.dirname` where the
  runtime provides it.
- `require` does not exist; dynamic `import()` returns a promise, so a conditional require becomes
  an async boundary.
- JSON imports need an import attribute; CommonJS dependencies interop through their default export
  and the shape is frequently not what the types claim.

## Type-only imports

Set **`verbatimModuleSyntax: true`**. Without it the compiler guesses which imports to erase, and the
guess is wrong in the two cases that matter: a module imported only for its types stays in the output
and drags a runtime dependency (or a cycle) with it, or an import with a needed side effect is
elided. With it, the rule is mechanical: anything used only in type position is written
`import type { Foo } from './foo'`, and the compiler enforces it.

`isolatedModules: true` for the same reason — it forbids constructs that a single-file transpiler
(esbuild, swc, Babel) cannot handle correctly, notably re-exporting a type without `export type`,
and `const enum`. Any project whose build is not `tsc` needs this on or the build and the typecheck
disagree about what the code means.

## Build is not typecheck

**A green bundler build proves nothing about types.** esbuild, swc, Vite and Babel strip type
annotations without checking them; they will happily emit code the compiler rejects. Therefore:

- `typecheck` is its own script — `tsc --noEmit` (or `tsc -b` with project references) — and it runs
  in CI as a separate, required step. It is level L1 static analysis in `v1rus-qa`; a build that
  passes while the typecheck is not run is not a verified build.
- The editor is also not the gate. It typechecks open files with its own settings; CI typechecks the
  project.
- Watch for the second config: many setups have `tsconfig.json` for the editor and a different one
  for the build. If they diverge, the typecheck is checking something nobody ships.

For incremental work use `incremental: true`; for a multi-package repository use project references
(`composite: true` plus `references`) so `tsc -b` rebuilds only what changed. How the repository's
packages are orchestrated beyond that is the layer above's decision.

## Declaration output

A package that other packages consume emits declarations:

- `declaration: true` and `declarationMap: true` — the map is what makes "go to definition" land in
  the source instead of the `.d.ts`.
- `composite: true` for a referenced project (it implies `declaration`).
- `isolatedDeclarations` makes declaration emit a per-file operation and therefore fast and
  parallelizable, at the price of explicit return-type annotations on everything exported. It is a
  genuine trade; take it for a published library, skip it for an app. It requires TypeScript 5.5 or
  newer — below that the mechanism does not exist.
- What lands in the declaration output is a public contract. Changing it is a breaking change
  (`v1rus-code-policies`).

## Path aliases

`paths` in tsconfig is a **compile-time** mapping. `tsc` does not rewrite the specifier on emit, so
the runtime must be able to resolve the alias by itself — a bundler alias, or the package's own
`imports` field. An alias configured only in tsconfig produces a build that typechecks and a process
that cannot start. See `ts-package-structure` for which aliasing mechanism to prefer.

## Versions

Never pin TypeScript or any tooling version from memory or from a snippet. The version is resolved at
plan time through the `v1rus-dependencies` gate, and a TypeScript major bump is a migration with its
own breaking-change list, not a routine dependency update.
