---
paths:
  - "tsconfig*.json"
  - "**/tsconfig*.json"
  - "jsconfig*.json"
  - "**/jsconfig*.json"
---

# tsconfig baseline

Never weaken `strict` or a strictness flag to silence an error: fix the code. Before using or removing an option, check which TypeScript major the project has (`typescript` in the lockfile / `npx tsc -v`); TypeScript 6 deprecated and TypeScript 7 removed several options. Resolve unknown option names against the tsconfig reference for that major, not memory.

## Every variant
- `strict: true` written explicitly, plus: `noUncheckedIndexedAccess`, `noImplicitOverride`, `noImplicitReturns`, `noFallthroughCasesInSwitch`, `forceConsistentCasingInFileNames`, `moduleDetection: "force"`.
- `exactOptionalPropertyTypes` on for new projects; off when integrating libraries with sloppy optional typings. `noPropertyAccessFromIndexSignature` on for backends, off for dictionary-heavy code. Both are judgement calls: follow the project, do not flip them in an unrelated change.
- `verbatimModuleSyntax: true` and `isolatedModules: true` (the former implies the latter; keep both explicit). `skipLibCheck: true`.
- `erasableSyntaxOnly: true` for new code (rejects enum, runtime namespace, parameter properties, `import =`/`export =`); required for running `.ts` under Node type stripping. Drop it only when the team deliberately keeps enums, and then lint them instead.
- `types` is an explicit list (`["node"]`; test globals only in the test tsconfig). TypeScript 6+ defaults `types` to empty, so globals vanish otherwise.
- `include` and `rootDir` explicit (defaults changed in TypeScript 6/7). No `baseUrl`/`paths` unless a bundler resolves them; prefer `package.json#imports` (`#internal/*`).
- Type-check gate is `tsc --noEmit` (`tsc -b` with project references); emitter or bundler is separate. `noEmitOnError` for emitting builds.
- One `module`/`moduleResolution` pair per target; never `bundler` resolution for code that Node runs directly. In monorepos: a root base config with the strict flags, per-package configs that extend it (`${configDir}` in shared bases), `composite` + `tsc -b` for libraries.

## Variants
| Target | module | notes |
|---|---|---|
| Node app emitted by tsc | `node20` (pinned semantics) or `nodenext` (tracks latest) | `target` matches the lowest supported Node, `outDir`, `sourceMap`, `types: ["node"]` |
| Node runs `.ts` directly (type stripping) | `nodenext` | `noEmit`, `erasableSyntaxOnly`, `verbatimModuleSyntax`, `rewriteRelativeImportExtensions` or `allowImportingTsExtensions`, `target: esnext` |
| Bundled app | `preserve` (or `esnext`) + `moduleResolution: bundler` | `noEmit`, `allowImportingTsExtensions`, `lib` includes `dom` only for browser code |
| Published library | `node20` / `nodenext` | `declaration`, `declarationMap`, `sourceMap`; `isolatedDeclarations` on (needs explicit types on exports); library built by a bundler still typechecks with `nodenext` to catch missing extensions |
| Plain JS with checking | `nodenext` | `allowJs`, `checkJs`, `noEmit`, `strict`, `maxNodeModuleJsDepth: 0` |

## Do not emit (removed in TypeScript 7)
`target: es5`, `downlevelIteration`, `moduleResolution: node`/`node10`/`classic`, `module: amd|umd|systemjs|none`, `outFile`, `esModuleInterop: false`, `allowSyntheticDefaultImports: false`, `alwaysStrict: false`, import `asserts` (use `with`). Legacy projects may use `ignoreDeprecations` only as a temporary, tracked step.

## Compiler-API tooling
TypeScript 7 ships no programmatic compiler API; tools that embed the compiler (typed ESLint) need the TypeScript 6 API. Do not bump `typescript` major without checking the installed tools' peer ranges (`npm view <tool> peerDependencies`) and the `ts-project-setup` skill. A project may legitimately run both (native `tsc` for checking, TypeScript 6 for tooling).
