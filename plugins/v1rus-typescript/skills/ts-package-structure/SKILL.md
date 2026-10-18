---
name: ts-package-structure
description: "Module and package boundaries in TypeScript: the `exports` map as the only public API of a package and why condition order and a types-first entry matter, deep imports into another package's internals being forbidden even when the path resolves, path aliases needing a runtime resolver and why package `imports` subpaths beat tsconfig `paths`, the real cost of barrel files (import cycles, watch-mode invalidation, tree-shaking) and the one place a barrel belongs, import cycles that typecheck and still fail at module init, `sideEffects` and what marking it wrong silently deletes, and workspace package boundaries including phantom dependencies and acyclic dependency direction. Load when creating a package or a module folder, writing or changing an `exports` field, adding a path alias, adding or removing an index.ts, importing across packages or layers, or diagnosing a circular-import or unresolved-specifier failure. Not for monorepo tooling, task runners or cross-application contracts, which belong to the layer above, and not for compiler options themselves (`ts-project-config`)."
---

# Modules and Package Structure

## `exports` is the API

A package's `exports` field is not metadata — it is the enforcement point. Once present, nothing
outside the map is importable, and that is the reason to add it.

```jsonc
{
  "type": "module",
  "exports": {
    ".":          { "types": "./dist/index.d.ts", "default": "./dist/index.js" },
    "./testing":  { "types": "./dist/testing.d.ts", "default": "./dist/testing.js" }
  },
  "sideEffects": false
}
```

Three things that break quietly:

- **Condition order is significant** — the resolver takes the first match. `types` goes first in
  each entry, `default` last. A `types` condition placed after `import` is ignored, and consumers
  silently fall back to `any`.
- **`main` / `module` / `types` are legacy fallbacks** for resolvers that do not read `exports`.
  Keep them consistent or drop them; a stale `main` pointing at a deleted build output is a bug that
  only appears for one consumer's toolchain.
- **`sideEffects: false` is a promise.** If any module in the package does work on import
  (registering something, patching a global, installing a polyfill), the bundler is entitled to drop
  it entirely, and the failure is a missing behaviour with no error. Either the claim is true, or
  the side-effectful files are listed explicitly.

Everything reachable through `exports` is a contract; changing it is a breaking change and follows
`v1rus-code-policies`.

## No deep imports

```ts
import { formatMoney } from '@acme/billing/dist/internal/format';  // never
import { formatMoney } from '@acme/billing';                       // the contract
```

A path that happens to resolve is not permission. Deep imports pin a consumer to the producer's file
layout, so an internal rename becomes a cross-package break, and they bypass whatever the entry
point does on the way out. This holds for source-level imports across workspace packages too:
`../../other-package/src/thing` is the same violation with a relative spelling.

Enforce it rather than remembering it: `no-restricted-imports` with a pattern per package, plus the
`exports` map itself (`ts-lint-and-format`). Note that `moduleResolution: "node"` ignores `exports`
entirely — another reason new projects use `bundler` or `nodenext` (`ts-project-config`).

## Aliases

`paths` in tsconfig is compile-time only; the runtime must resolve the alias by its own means or the
process cannot start. Order of preference:

1. **Package `imports` subpaths** (`"#internal/*": "./src/internal/*.js"`) — resolved by the runtime,
   by bundlers, and by TypeScript under `node16`/`nodenext`. One mechanism, honoured everywhere,
   and scoped to the package that declares it.
2. **A bundler alias plus a matching tsconfig `paths`** — acceptable when a bundler is always in the
   loop, and the two must be kept in sync; drift produces "works in dev, fails in build".
3. **tsconfig `paths` alone** — only for a project that emits nothing (typecheck-only tooling).

Keep the number of aliases small and point them at layer or package roots, never at individual
files. An alias per folder makes moving code a repo-wide edit — the opposite of the intent.

## Barrel files

An `index.ts` that re-exports a folder looks tidy and has costs that show up later:

- **Import cycles.** A file importing a sibling through the shared barrel pulls in the whole folder,
  including itself. This is how a cycle appears without any file directly importing another.
- **Watch and build invalidation.** Touching one file invalidates everything that imported the
  barrel, which in a large folder is everything.
- **Weakened tree-shaking.** It survives in a well-configured bundler; it does not survive a
  side-effectful module, a re-export of a CommonJS dependency, or a consumer without
  `sideEffects: false`.
- **A hidden dependency graph.** "Who uses this module" becomes unanswerable when everything imports
  the same index.

The rule:

- A barrel at a **package or module boundary** is fine — that is the public API, and it exists to be
  the single entry.
- **Inside** the package, import the file directly. Never import through your own barrel from within
  the package it belongs to; that is the cycle generator.
- Do not create a barrel that re-exports other barrels.

## Cycles

A cycle typechecks. At runtime one of the two modules is evaluated first and sees the other's
bindings as `undefined` — a class that extends `undefined`, a constant that is missing, a decorator
that receives nothing. The failure appears at import time, far from the code that caused it, and
frequently only in the production bundle where the module order differs.

- Treat a cycle as a design signal: the two modules want a third one holding what they share, or one
  of the two dependencies is upside down.
- `import type` is erased and therefore cannot create a runtime cycle — a legitimate fix when the
  dependency is genuinely only a type.
- Detect cycles in the lint gate (`import-x/no-cycle` or equivalent) so they are caught at the
  commit that introduces them.

## Workspace package boundaries

- **A package may only import what its own `package.json` declares.** Reaching for a package that
  happens to be hoisted into the root `node_modules` is a phantom dependency: it works locally and
  breaks under a different installer, a different hoisting strategy, or when the real dependent
  drops it.
- **Dependency direction is acyclic and deliberate.** Application packages depend on shared
  packages; shared packages never depend on an application. A cycle between workspace packages is a
  build failure waiting for the first cold cache.
- **Shared types live in a package**, imported by name. Not reached through a relative path into
  another application's source tree.
- **One package, one reason to change.** A `utils` or `common` package accumulates everything, is
  depended on by everything, and rebuilds everything. Split by capability instead.

How the workspace is declared, built and versioned — the tool, the task graph, the release flow — is
not this layer's concern; it belongs to the platform layer above.
