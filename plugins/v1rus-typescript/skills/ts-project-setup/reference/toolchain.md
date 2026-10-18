# Toolchain decisions

## Two-headed TypeScript (verified when authored; re-check before relying)
- The native compiler line (TypeScript 7) is the fast type-checker/emitter. It ships no programmatic API of the old kind; a compiler-API line (TypeScript 6) stays available as a separate compat package (`@typescript/typescript6`, binary `tsc6`).
- typescript-eslint's peer range on `typescript` excluded 7 at authoring time: `npm view typescript-eslint peerDependencies`.
- Verified side-by-side recipe in a scratch project: `devDependencies` of `"typescript": "npm:@typescript/typescript6@<resolved>"` and `"@typescript/native": "npm:typescript@<resolved>"` install cleanly next to typescript-eslint; `tsc` then runs the native compiler and `tsc6` the old one; typed ESLint ran. Resolve `<resolved>` with `npm view <pkg> version`. `@typescript/native` is only an alias key (no such registry package).
- Policy: never bump `typescript` major blindly. If the project uses typed ESLint or any tool embedding the compiler, either stay on 6 or use the alias recipe. Without such tools, plain 7 is fine. Re-check peer ranges and the release notes each time; the compiler API story was still changing.

## ESM vs CJS
- Default: ESM-only, `"type": "module"`, no top-level await in library code (`require(esm)` is unflagged on recent Node lines but fails on top-level await), `engines.node` at or above the first line with unflagged `require(esm)`. Check the Node docs for the exact lines.
- Dual publishing only when CJS-only consumers or old Node must be served; one implementation, thin wrapper, validate with `attw` and `publint` (both exist on npm; run via the project's scripts or `npx` pinned in devDependencies).

## Running TypeScript directly in Node
- Type stripping needs erasable syntax only: `erasableSyntaxOnly`, `verbatimModuleSyntax`, extension-ful imports. Node refuses `.ts` under `node_modules`, so published packages ship JS plus `.d.ts`.

## Library build
- Pure ESM, no transforms: `tsc` alone. Needs bundling or dual output: tsdown (its peer range on typescript included 7 at authoring; the older tsup README says it is no longer maintained). Apps use their bundler's tool with `noEmit` tsconfig.
- Externalise `dependencies`/`peerDependencies`; target the lowest supported Node; no minification of libraries; validate the packed tarball in a temp project.

## isolatedDeclarations
On for libraries and monorepo packages (forces explicit exported types), off for apps. Needs `declaration` or `composite`.
