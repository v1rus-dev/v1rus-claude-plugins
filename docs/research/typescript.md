# JavaScript + TypeScript engineering playbook (input for plugin `v1rus-typescript`)

Researched 2026-10-18. Scope: Node backends, libraries, tooling, framework-agnostic web code, plain-JS projects via JSDoc/checkJs.
Tier legend: T1 = TypeScript handbook/tsconfig ref/release notes, ECMAScript/TC39, Node.js docs, typescript-eslint docs. T2 = other vendor docs (vitest, zod, pnpm, biome, npm, tsdown). T3/T4 = blogs, cross-check only.
Marker: [E] = empirically verified in this session by running it; [D] = read from docs; [U] = could not verify / inference.
Third-party packages are referenced by NAME ONLY; resolve versions at use time (npm view / registry).

---------------------------------------------------------------------------
## 0. State of the world today (verified, dated 2026-10-18)

| Fact | Value | Source |
|---|---|---|
| TypeScript latest stable (`typescript@latest`) | 7.0.2 (published 2026-07-08); native Go port, "Project Corsa" | npm registry [E]; TS blog "Announcing TypeScript 7.0" [D] T1 |
| Last JS-codebase TS | 6.0.x (6.0.2 on 2026-03-23; 6.0.3 installed from `typescript@6`) | TS blog 6.0 [D] T1, npm [E] |
| TS 7 programmatic API | NONE in 7.0 (`require("typescript")` is not the old API); new API expected in 7.1. Nightlies: `typescript@next` (7.1.0-dev present) | TS 7.0 post [D] T1; npm [E] |
| TS 6/7 side-by-side | `@typescript/typescript6` compat package (re-exports 6.0 API, ships `tsc6`); alias pattern `"typescript": "npm:@typescript/typescript6@..."` + `"@typescript/native": "npm:typescript@..."` so `tsc` = 7 | TS 7.0 post [D] T1; package exists on npm [E] |
| typescript-eslint peer range on `typescript` | `>=4.8.4 <6.1.0`: installing it next to `typescript@7` fails with ERESOLVE | npm peerDependencies + real `npm i typescript@7 typescript-eslint` run [E] |
| Node LTS | v24 "Krypton" (Active LTS, latest 24.22.0, 2026-10-14); v22 "Jod" (LTS, maintenance); v20 EOL (2026-03-24); v25 EOL; v26 Current (26.12.0). From v27 the cycle is annual (Current 6 months, then LTS) | nodejs.org previous-releases [D] T1 |
| Node type stripping | enabled by default since 23.6/22.18; marked Stable (Stability 2) since 24.12 / 25.2; `--experimental-transform-types` REMOVED in v26 | nodejs.org/api/typescript [D] T1 |
| `require(esm)` | unflagged in 20.19+/22.12+; no longer experimental in 25.4 | nodejs.org/api/modules [D] T1 |
| Node permission model | Stable, flag `--permission`; a "seat belt", not a sandbox | nodejs.org/api/permissions [D] T1 |
| ES2025 (finished) | Iterator helpers, `Promise.try`, new Set methods, RegExp modifiers, duplicate named groups, ArrayBuffer transfer, JSON modules/import attributes, Float16 | TC39 finished-proposals [D] T1 |
| ES2026 (finished) | `Error.isError`, `Array.fromAsync`, `RegExp.escape`, `Math.sumPrecise`, Uint8Array base64, Iterator sequencing, JSON.parse source text | TC39 [D] T1 |
| Pending ES2027 | Temporal, Explicit Resource Management (`using`), Upsert, more Iterator helpers | TC39 [D] T1 |
| Runtime reality on Node 24.22 | `using`, `Promise.try`, `RegExp.escape`, `AbortSignal.any`, Set methods, `Iterator.from`, `Object.groupBy`, `Promise.withResolvers`, `process.loadEnvFile`, `toSorted`, `URL.canParse`, `Error.isError` all present; `Temporal`, `Math.sumPrecise`, `Uint8Array.fromBase64` ABSENT | local run [E] |
| TS 6.0 new defaults | `strict: true`, `module: esnext`, `target` = latest (es2025), `noUncheckedSideEffectImports: true`, `libReplacement: false`, `rootDir` = tsconfig dir, `types: []` | TS 6.0 post [D] T1 |
| TS 6 deprecations -> TS 7 hard errors | `target: es5`, `downlevelIteration`, `moduleResolution: node/node10`, `classic`, `module: amd/umd/systemjs/none`, `baseUrl`, `esModuleInterop:false`, `allowSyntheticDefaultImports:false`, `alwaysStrict:false`, `outFile`, `module` keyword namespaces, import `asserts` (use `with`) | TS 6.0 + 7.0 posts [D] T1 |
| TS 7 additions | `--checkers`, `--builders` (experimental), `--singleThreaded`, Go-based `--watch`, LSP language server; JS-file checking now follows TS rules (no `@enum`, no `@class`, no postfix `!`, no Closure types, no values-as-types) | TS 7.0 post [D] T1 |
| `module: node20` / `nodenext` | `node20` models require(esm) (stable target); `nodenext` tracks latest Node and implies `target: esnext` | tsconfig ref [D] T1 |
| `#/` subpath imports | supported under `nodenext`/`bundler` since TS 6.0 | TS 6.0 post [D] T1 |

Consequence for the plugin (key call #1): the TS toolchain is TWO-HEADED during 2026. TS 7 (`tsc`) is the fast type-checker/emitter; TS 6 remains the library API that typescript-eslint, and anything embedding the compiler, needs until the 7.1 API ships. The plugin must detect which head a project uses (`typescript` version in lockfile) and not "upgrade" TS blindly. Re-check this section before every plugin release.

---------------------------------------------------------------------------
## 1. tsconfig baselines

### 1.1 Rules common to every variant
R1.1 `strict: true` is mandatory (default since 6.0, still write it explicitly: explicit survives tooling/readers using older TS). T1.
R1.2 Add the "beyond strict" flags: `noUncheckedIndexedAccess` (adds `undefined` to index reads, T1 tsconfig ref [D]), `exactOptionalPropertyTypes` (ref marks it Recommended [D]), `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noImplicitReturns`, `noPropertyAccessFromIndexSignature` (opinionated; see C-list), `forceConsistentCasingInFileNames`. Rationale: each removes a whole class of runtime `undefined`/override bugs at no runtime cost. Mechanical: tsconfig.
R1.3 `verbatimModuleSyntax: true` (imports/exports without `type` are preserved verbatim; makes `import type` mandatory for types; implies `isolatedModules` true). Rationale: output == source, required for Node type stripping, bundlers and single-file transpilers behave identically. T1 [D].
R1.4 `isolatedModules: true` (implied by R1.3; set explicitly for clarity). `skipLibCheck: true` (ref recommends; trades a little accuracy for speed; library authors should additionally typecheck their own emitted `.d.ts` via attw/consumer test). T1.
R1.5 `erasableSyntaxOnly: true` for any new code that might run under Node type stripping, tsx-less scripts, or "TS as JS with types" philosophy. It rejects `enum`, runtime `namespace`, parameter properties, `import = / export =`, `<T>x` casts. [E] confirmed: `tsc --erasableSyntaxOnly` raises TS1294 on enum and parameter property; Node 24 rejects enum with `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` [E]. T1.
R1.6 `moduleDetection: "force"` (every file is a module; avoids accidental global scripts). `resolveJsonModule: true` only if needed. `noUncheckedSideEffectImports` leave default true (declare `*.css` etc. modules explicitly).
R1.7 `useUnknownInCatchVariables` comes with `strict`; never turn off. `noEmitOnError` for emitting builds.
R1.8 No `baseUrl`, no `paths` unless a bundler really resolves them. Prefer `package.json#imports` (`#internal/*`, `#/*` on TS>=6) which Node, bundlers and TS all understand. `paths` is TS-only and breaks under plain Node. T1 [D].
R1.9 Do not set `types` implicitly: since 6.0 default is `[]`, so list needed globals explicitly (`"types": ["node"]`; test globals only in the test tsconfig). This also stops ambient-type leakage from `@types/*`.
R1.10 Always `include` explicitly and keep `rootDir` explicit (default changed in 6.0/7.0).
R1.11 `${configDir}` template var (TS 5.5) in shared base configs so `extends` paths resolve relative to the consumer. T1.
R1.12 Pick ONE `module`/`moduleResolution` pair per target (table below); never mix `bundler` resolution into code that Node runs directly.
R1.13 Use `tsc --noEmit` (or `emitDeclarationOnly`) as the type-check gate; the emitter/bundler is separate from the checker.

### 1.2 Variants (module / moduleResolution)

| Target | module | moduleResolution | Other flags |
|---|---|---|---|
| Node app/service, runs JS emitted by tsc | `node20` (pinned semantics) or `nodenext` (tracks latest) | implied by module | `target: es2023`-ish (match LTS, never above Node's support), `outDir`, `sourceMap`, `rewriteRelativeImportExtensions: true` if source imports use `.ts`, `types:["node"]` |
| Node app/script run directly by Node (type stripping) | `nodenext` | implied | `noEmit: true`, `allowImportingTsExtensions` (implied by `rewriteRelativeImportExtensions`), `erasableSyntaxOnly: true`, `verbatimModuleSyntax: true`, `target: esnext`. This is Node's own documented recommendation [D] T1 |
| Bundled app (Vite/esbuild/Rolldown etc.) | `preserve` (or `esnext`) | `bundler` | `noEmit: true`, `allowImportingTsExtensions`, `isolatedModules`, `lib` including `dom` only for browser code |
| Published library | `node20`/`nodenext` (strictest, forces correct extensions and `exports` resolution so consumers' Node works) | implied | `declaration: true`, `declarationMap`, `sourceMap`, `isolatedDeclarations: true` (see 1.3), `stripInternal` optional, `skipLibCheck` true |
| Library built by bundler (tsdown) | `esnext`/`preserve` + `bundler` is acceptable ONLY for typecheck if the tool emits both JS and d.ts and attw/publint pass; otherwise prefer `nodenext` to catch missing extensions | | add `publint` + `attw` CI step |
| Monorepo | root `tsconfig.base.json` (strict flags) extended per package; `composite` + project references (`tsc -b`) for libs | | per-package `types`, `rootDir`, `outDir` |

Never emit `target: es5`, `downlevelIteration`, `amd/umd/systemjs`, `outFile`, `moduleResolution: node10/classic`: removed in TS 7 (T1). Legacy projects: set `ignoreDeprecations: "6.0"` as a TEMPORARY, tracked step.

### 1.3 `isolatedDeclarations`
Requires explicit annotations on exported API so `.d.ts` can be generated per file (5.5). Needs `declaration` or `composite`. Does not change emit; value comes from fast/parallel declaration emit (bundlers, monorepo builds). Official stance: adopt case by case (T1 [D]). Rule: ON for libraries and monorepo internal packages (forces explicit public types, which is good API hygiene regardless); OFF for apps. Mechanical: tsconfig.

### 1.4 `using` / explicit resource management
Works in TS (>=5.2) and Node 24 [E]; TC39 status: finished, publication ES2027 [D]. Rule: use `using`/`await using` for disposable resources (file handles, locks, temp dirs, DB connections) only when ALL runtimes in your support matrix have it (Node >=24, check `target`/`lib` `esnext.disposable`); otherwise try/finally. Never polyfill silently in a library.

---------------------------------------------------------------------------
## 2. Modules: ESM vs CJS, package.json

R2.1 New code is ESM. Set `"type": "module"` explicitly in every package.json (Node recommends always setting `type` [D] T1). `.cjs/.mjs` only for the exceptions.
R2.2 Relative imports include the extension (`./x.js` for tsc-emitted output or `./x.ts` with `rewriteRelativeImportExtensions`). Directory imports and extensionless are bundler-only.
R2.3 `exports` is the only public entry map for libraries; once present everything unlisted is blocked. Condition order: `types` first, then `import`/`require`/`module-sync`, `default` last (key order = priority) [D] T1. Provide `main`/`types` fallbacks only if old tooling matters.
R2.4 ESM-only vs dual publishing. Facts: `require(esm)` works unflagged on Node 20.19+/22.12+/24+ for synchronous graphs; fails with `ERR_REQUIRE_ASYNC_MODULE` on top-level await [D] T1. Dual publishing carries the dual-package hazard (two instances, `instanceof`/state split) [D] T1 (page names the hazard, details from inference [U]). RECOMMENDED DEFAULT: ESM-only, no top-level await in library code, `engines.node` >= the first line that supports require(esm). Dual-publish only when you must serve Node < 20.19 / CJS-only toolchains; then keep CJS a thin wrapper around one implementation, ship via a bundler, and verify with `attw` + `publint`. T1 facts, recommendation = own judgement (log in C).
R2.5 TS `module: node20|nodenext` validates dual-format resolution for you (a `.d.ts` under CJS resolution must be `.d.cts`); `attw` (@arethetypeswrong/cli) catches masquerading-as-CJS/ESM types errors. Both exist on npm [E].
R2.6 Libraries ship compiled JS + `.d.ts`; Node refuses TS files under `node_modules` [D], so never publish `.ts` as the entry. Apps may run `.ts` directly.
R2.7 `files` allowlist (or `.npmignore`) so the tarball contains only dist + metadata; verify with `npm pack --dry-run`. `sideEffects: false` only when truthful (bundler tree-shaking).
R2.8 Subpath imports `"imports": {"#internal/*": "./src/internal/*.js"}` instead of `paths`/baseUrl (Node + TS + bundlers). T1.
R2.9 `engines.node` set to supported lines; `packageManager` pinned (corepack-style field); `private: true` for non-published packages (prevents accidental publish).
R2.10 `package.json` field hygiene: `name`, `version`, `license`, `repository.url` exact (npm trusted publishing requires it to match the GitHub repo [D] T2), `sideEffects`, `types`, `exports`, `files`.

---------------------------------------------------------------------------
## 3. Type modelling

R3.1 `unknown` over `any` everywhere a type is not known (JSON, catch, third-party untyped, parsed input); narrow with schema/guard. `any` only inside a documented, isolated adapter, with a one-line justification. Mechanical: `@typescript-eslint/no-explicit-any` (recommended-type-checked) + the `no-unsafe-*` family (argument/assignment/call/member-access/return, all in recommended-type-checked [E]).
R3.2 Model states as discriminated unions with a literal tag (`kind`/`type`/`status`), not optional-field soups. Make illegal states unrepresentable.
R3.3 Exhaustiveness: `switch` over a union ends with `default: { const _exhaustive: never = x; throw new Error(...) }` or a shared `assertNever`. Mechanical: `@typescript-eslint/switch-exhaustiveness-check` (NOT in recommended/strict presets [E], enable explicitly, with `considerDefaultExhaustiveForUnions` as preferred) plus compiler `noImplicitReturns`/`noFallthroughCasesInSwitch`.
R3.4 No `enum` (esp. not `const enum`): use `as const` objects + derived union (`type X = (typeof X)[keyof typeof X]`) or plain string-literal unions. Rationale: enums generate runtime code (not erasable; TS7 JS-checking also drops `@enum`), numeric enums are unsound-ish, `const enum` breaks isolatedModules/declarations. Mechanical: `erasableSyntaxOnly` (compiler error) ; for non-erasable projects ESLint `no-restricted-syntax` on `TSEnumDeclaration` (there is no dedicated `no-enum` rule in typescript-eslint [E: rule list check]).
R3.5 No non-null assertion `!` and no `as` to silence errors. Prefer narrowing, `satisfies`, runtime guards. `as` only for: `as const`, narrowing after a proven check with comment, test fixtures. Mechanical: `no-non-null-assertion` (strict preset [E]), `consistent-type-assertions` (stylistic), `@typescript-eslint/no-unsafe-type-assertion` (not in presets [E]; opt in, noisy).
R3.6 `satisfies` for config/lookup tables: validates shape while preserving literal/narrow inferred types. Pair with `as const` for tuples/records.
R3.7 Branded (nominal) types for IDs/units that must not be mixed: `type UserId = string & { readonly __brand: 'UserId' }`, minted only by a parse/constructor function that validates. Not for every string; use where mixups were/are plausible.
R3.8 Prefer `interface` for object shapes that are extended/implemented, `type` for unions/mapped/conditional. Be consistent per repo (rule `consistent-type-definitions` is stylistic).
R3.9 `readonly` by default: `readonly` props, `ReadonlyArray<T>`/`readonly T[]`, `Readonly<>`; function params that are not mutated are readonly. Mechanical (partial): `@typescript-eslint/prefer-readonly` (private members; not in presets [E]); parameters need `@typescript-eslint/prefer-readonly-parameter-types` (very noisy; advisory).
R3.10 Explicit return types on exported functions in libraries (needed by isolatedDeclarations anyway); inference is fine for internal code. Do not annotate what inference gets right locally.
R3.11 Generics: only when a type param relates two positions (`no-unnecessary-type-parameters`, strict preset [E]). Constrain (`T extends ...`); avoid "generic to appease the compiler".
R3.12 Avoid `Function`, `Object`, `{}` types (`no-unsafe-function-type`, `no-wrapper-object-types`, `no-empty-object-type` in recommended). Use `Record<string, unknown>`, `object`, specific call signatures.
R3.13 Derive types from values/schemas, not the reverse duplicate: `z.infer<typeof Schema>` or valibot `InferOutput` (zod docs/valibot docs [D] T2); `typeof config`, `ReturnType`, `Parameters`.
R3.14 Optional vs undefined: with `exactOptionalPropertyTypes` be explicit (`x?: T` vs `x: T | undefined`); `null` only at I/O boundaries (JSON/DB), map to `undefined`/domain type inside.
R3.15 Type-predicates / assertion functions (`x is T`, `asserts x is T`) for guards; since 5.5 simple predicates are inferred; still annotate when exporting.
R3.16 Template literal / mapped / conditional types: keep to a few lines; if a type needs a paragraph of comment it is the wrong tool. Type-level programming is a cost center (compile time; `zod` v4 redesign cut instantiations drastically per its own benchmarks [D] T2).
R3.17 Avoid `namespace` (non-erasable), `export =`/`import =`, decorators in new code unless a framework requires (decorators are not erasable; Node rejects them [D]).
R3.18 Do not use `object` spread/`Object.assign` to widen a typed result without a type; avoid `Object.keys` casts, use `Object.entries` + schema.
R3.19 `lib`/`target`: use `es2025`/`esnext` lib entries only for what the minimum runtime really ships (see Node table in section 0; `Temporal` is NOT in Node 24 [E]).

---------------------------------------------------------------------------
## 4. Runtime validation at I/O boundaries

R4.1 TypeScript types are erased: everything crossing a trust boundary (HTTP bodies/queries, env vars, files, DB rows, queue messages, `JSON.parse`, `postMessage`, 3rd-party API responses, CLI args) is `unknown` until a runtime check succeeds. Parse once at the edge into a domain type, then pass trusted types inward ("parse, don't validate").
R4.2 Single source of truth: define the schema, infer the type. Never hand-write the type and schema twice.
R4.3 Library choice (log as assumption): 
 - Zod (v4): ecosystem default; v4 claims large perf and compile-time gains, `zod/mini` tree-shakable API, `z.toJSONSchema`, top-level string formats, unified `error` param, `z.stringbool()` for env booleans [D] T2.
 - Valibot: modular, per-function tree-shaking, very small baseline (vendor claim "<700 bytes", up to 95% smaller vs Zod [D] T2, treat as marketing); best for browser bundles.
 - ArkType and others: TS-syntax-like schemas; [U] not researched in depth.
 - All can interoperate via Standard Schema: a `~standard` property (`version`, `vendor`, `validate`, optional `types`), packaged as `@standard-schema/spec` [D] T2; the spec page does not list adopters, check each library's docs [U].
 DEFAULT: Zod for backends/tooling; Valibot or `zod/mini` where bundle size is measured to matter. In libraries, accept Standard Schema-compatible schemas rather than importing a specific validator.
R4.4 Env: validate `process.env` once at startup into a typed frozen config object; fail fast with all issues listed; never read `process.env` scattered through code. Node has `process.loadEnvFile`/`--env-file` built in [E: function present]; note permission-model caveat that `--env-file` is read before the model initializes [D].
R4.5 Strictness: reject/strip unknown keys deliberately (strict objects for inbound requests to block mass assignment and prototype-key games; strip for lenient third-party data). Coerce deliberately (`z.coerce` hides bugs; prefer explicit parse of query strings).
R4.6 Validation errors map to a typed 4xx/domain error, never leak raw schema issues containing secrets.
R4.7 Do not validate hot-path internal calls; validate at the edge only. Performance budget: schema parse is non-trivial in tight loops; benchmark if needed.
R4.8 JSON: `JSON.parse` returns `any` — wrap: `const v: unknown = JSON.parse(s)`. `JSON.parse` source-text access (ES2026) is not needed in app code.
Mechanical: `no-unsafe-*` rules catch leaks of `any` from `JSON.parse`/`res.json()`; no tool enforces "validated at boundary" — advisory/review.

---------------------------------------------------------------------------
## 5. Error handling

R5.1 Throw `Error` subclasses (or `Error`), never strings/objects. Mechanical: `@typescript-eslint/only-throw-error`, `prefer-promise-reject-errors` (both in recommended-type-checked [E]); core `no-throw-literal` superseded.
R5.2 Always preserve the cause: `new DomainError('msg', { cause: err })` (ES2022, [E] works). Wrap at layer boundaries to add context; do not log-and-rethrow the same error at each layer (log once at the edge).
R5.3 Typed errors: subclass with a stable string `code` and (optionally) a discriminant `name`; consumers branch on `code`/`instanceof`. Remember TS cannot type `throws`; document with TSDoc `@throws`.
R5.4 Narrowing caught values: `catch (e)` is `unknown` (`useUnknownInCatchVariables`); use `e instanceof Error` or `Error.isError(e)` (ES2026, present in Node 24 [E]; use it for cross-realm errors; `instanceof` fails across realms/vm contexts). Never `catch (e: any)`.
R5.5 throw vs Result: Use exceptions for exceptional/unrecoverable and programmer errors; use a Result/`Either`-like return (plain discriminated union `{ ok: true, value } | { ok: false, error }` — no library needed) for EXPECTED, domain-level failures the caller must handle (parse, validation, not-found, permission). Do not mix both styles within one module boundary; document the contract. Libraries (neverthrow etc.) are optional [U adoption not researched]; plugin default is the hand-rolled union (no new dependency, per the dependency policy).
R5.6 Never swallow: empty `catch {}` forbidden (`no-empty` in `eslint:recommended`; allow only with comment). Do not `catch` just to `console.log`.
R5.7 `AggregateError` for multiple failures (`Promise.any`, parallel validation).
R5.8 Process-level: handle `unhandledRejection` / `uncaughtException` only to log + exit non-zero (graceful shutdown), never to continue. Node >=15 crashes on unhandled rejection by default; keep that.
R5.9 `return await` inside `try` blocks (otherwise the catch does not see rejections): `@typescript-eslint/return-await` (strict preset [E]).
R5.10 Errors crossing process boundaries are serialised data, not instances: map to `{code, message, details}`; do not send stacks to clients.

---------------------------------------------------------------------------
## 6. Async

R6.1 No floating promises: every promise is awaited, returned, `.catch`ed, or explicitly `void`-ed with a comment. Mechanical: `@typescript-eslint/no-floating-promises` (in recommended-type-checked [E]).
R6.2 Also `no-misused-promises` (promise in `if`/event handler returning void) and `await-thenable`, both recommended-type-checked [E]; `require-await` also in recommended-type-checked [E].
R6.3 Cancellation: every long/IO operation accepts an `AbortSignal` (`{ signal }` param); combine with `AbortSignal.timeout(ms)` and `AbortSignal.any([...])` (present in Node 24 [E]). Pass the signal into `fetch`, streams, `timers/promises`, `fs/promises`, child processes. Do not invent custom cancel tokens.
R6.4 `Promise.all` = all-or-nothing, fail-fast (note: others keep running; you must cancel them via AbortController). `Promise.allSettled` = need every outcome (batch jobs, partial success). `Promise.any` = first success (+ `AggregateError`). `Promise.race` for timeouts only if the loser is cancelled. Never `Promise.all` over unbounded input: bound concurrency (a small pool/semaphore or chunked batches; async iterators with limited fan-out).
R6.5 Sequential `await` in a loop only when order/dependency demands; `no-await-in-loop` (core) is advisory noisy, enable per project if throughput matters.
R6.6 Don't block the event loop: no sync fs/crypto/zlib/`execSync`/`JSON.parse` of huge payloads on request paths; CPU-bound work goes to `worker_threads` / a child process / a queue. Detect with `perf_hooks.monitorEventLoopDelay`. Regex catastrophic backtracking is also an event-loop block (see section 14). [T1 Node docs: "Don't Block the Event Loop" guide — referenced from knowledge, not re-fetched this session: [U]].
R6.7 Streams: use `stream/promises.pipeline` (propagates errors + cleanup, supports AbortSignal), async iteration over Readable, backpressure respected (`await once(stream,'drain')` or pipeline). Never `readFileSync`/buffer whole large files; use Web Streams only when interop demands it.
R6.8 `Promise.try` (ES2025, [E] present in Node 24) to normalise sync-or-async function calls into a promise; `Promise.withResolvers` [E] for deferred pattern instead of `new Promise` capture hacks; `Array.fromAsync` (ES2026) check runtime before use.
R6.9 Timers: `node:timers/promises` (`setTimeout`, `setInterval` async iterators, abortable) [E: used]. Always `clearTimeout`/unref long-lived timers so they do not hold the process open.
R6.10 Event emitters: `events.once`/`on` with `{ signal }`; always attach an `'error'` listener; set listener leak thresholds knowingly.
R6.11 `async` function that never awaits and is not an interface requirement: drop `async` (`require-await`), but be careful to preserve sync-throw → rejection semantics (use `Promise.try`).
R6.12 Top-level await is fine in ESM apps/scripts; NOT in library entry points (breaks `require(esm)`, R2.4).
R6.13 Graceful shutdown: SIGTERM/SIGINT -> stop accepting, abort in-flight via shared AbortController, drain with deadline, exit.

---------------------------------------------------------------------------
## 7. Project structure and naming

R7.1 Feature/domain folders, not type folders (`orders/{handler,service,repo,schema,test}.ts`, not `controllers/ services/`). Dependency direction inward: IO edge (http, cli, queue) -> application/use-cases -> domain; domain imports nothing from edge. Enforce with `eslint-plugin-boundaries`-type rule or `dependency-cruiser`/`knip` in CI [U: tools exist; not researched here, NAMES ONLY].
R7.2 No barrel files (`index.ts` re-export-all) inside apps: they cause cycles, defeat tree-shaking and slow tsc/test startup. Libraries: exactly one curated public entry (or a few `exports` subpaths), deliberate, with explicit named exports. Mechanical (partial): `import/no-cycle`-style rules; cycle detection via madge/dpdm [U names only]; `knip` for unused exports/files (exists, npm [E]).
R7.3 Named exports only (no default exports) except where a tool requires them (config files). Rationale: rename-safety, grep-ability, consistent import names. Mechanical: `import/no-default-export` [U plugin], or `no-restricted-exports`.
R7.4 File names: `kebab-case.ts` (case-insensitive FS safety, `forceConsistentCasingInFileNames`), one primary concept per file; test `x.test.ts` beside `x.ts` (see 10).
R7.5 Identifier naming: camelCase values/functions, PascalCase types/classes, SCREAMING_SNAKE only for true constants, no `I` prefix on interfaces, no `T` prefix on types, boolean names `is/has/can/should`, generics descriptive when > 1 (`TInput`, `TOutput`). Mechanical: `@typescript-eslint/naming-convention` (exists [E]; configure minimal; advisory elsewhere).
R7.6 Prefer `node:` prefix for builtins (`node:fs/promises`); unambiguous and required for some builtins. Mechanical: `unicorn/prefer-node-protocol` [U plugin] or `no-restricted-imports`.
R7.7 Config as one typed module (R4.4); no magic globals; dependency injection by function parameters/closures (plain functions) over class hierarchies; classes for resources with lifecycle.
R7.8 Small modules, explicit side-effect-free module top level (no work at import time, except a documented entrypoint).
R7.9 Public API surface of libraries tracked (api-extractor or a `.d.ts` snapshot test) [U tooling], breaking changes follow semver.

Immutability (R7.10-12): prefer `const`, no param mutation, `structuredClone` for deep copy [E: standard], `toSorted/toReversed/toSpliced/with` (ES2023 [E present]) instead of mutating `sort/reverse/splice`. `Object.freeze` for module-level constant tables (shallow). Mechanical: core `prefer-const`, `no-param-reassign` (props option), `@typescript-eslint/prefer-readonly` (private fields). Advisory otherwise.

---------------------------------------------------------------------------
## 8. Plain-JS discipline (JSDoc + checkJs)

R8.1 A JS project gets the same rigor without a build step: `tsconfig.json` (or `jsconfig`) with `allowJs: true`, `checkJs: true`, `noEmit: true`, `strict: true`, `module: nodenext`, `maxNodeModuleJsDepth: 0`; run `tsc` as the check gate. [E] confirmed workflow `tsc --checkJs` on a `.js` file with an incorrect `@returns` (invocation needs `types` set properly; use a tsconfig file instead of CLI for the real project).
R8.2 Type with JSDoc: `@param {T} x`, `@returns {T}`, `@type`, `@typedef`, `@template T`, `@satisfies`, and `@import { Foo } from './foo.js'` (TS 5.5, avoids runtime imports in JS) [D] T1. Put non-trivial types in `.d.ts` files or `types.js` typedef modules.
R8.3 TS 7 tightens JS checking: no `@enum`, no `@class` constructor magic, no postfix `!`, no Closure-style function types, no values used as types (use `typeof`), standalone `?` removed [D] T1. Write only mainstream JSDoc-TS: `@typedef`, `@param`, `@returns`, `@template`, `@import`.
R8.4 Per-file opt-in is acceptable for migration: `// @ts-check` header; `// @ts-expect-error` (with reason) over `@ts-ignore`. Mechanical: `@typescript-eslint/ban-ts-comment` (recommended) requires a description for expect-error; flip to errors on `@ts-ignore`.
R8.5 When to migrate to `.ts`: (a) JSDoc generics/overloads get unreadable, (b) you want `enum`-free but richer types like `satisfies`, mapped types inline, (c) team size > ~3 or library publishing declarations, (d) Node type stripping makes `.ts` costless (Node >= 22.18/24, no build for apps). Libraries can stay JS+JSDoc and still ship good `.d.ts` via `tsc --emitDeclarationOnly`. Migration steps: rename file-by-file (`.js` -> `.ts`) with `allowJs` on; keep `erasableSyntaxOnly` so the file remains valid JS-with-types; no behaviour changes in the same commit.
R8.6 Plain JS under ESLint: `tseslint.configs.disableTypeChecked` for non-TS files that are not in the TS program; type-aware rules only on files in a tsconfig [D] T1.
R8.7 Runtime-first JS rules still apply: strict equality, `const`/`let`, no implicit globals, ESM, `node:` imports, `Error` cause. Use `// @ts-check` + `checkJs` as the safety net, not as style.

---------------------------------------------------------------------------
## 9. Lint and format

### 9.1 ESLint + typescript-eslint
Facts: ESLint v10 (engines `^20.19 || ^22.13 || >=24`) [E]; flat config only. typescript-eslint v8 configs: `recommended`, `strict`, `stylistic`, `*-type-checked`, `disable-type-checked`; `all`, `strict`, `strict-type-checked` are flagged unstable by the docs [D] T1 (so selecting them is a moving target, pin and review on bumps).
R9.1 Flat config with `defineConfig` from `eslint/config`; extend `js.configs.recommended` + `tseslint.configs.recommendedTypeChecked` (floor) or `strictTypeChecked` (ceiling) + `stylisticTypeChecked`; `languageOptions.parserOptions.projectService: true` (+ `tsconfigRootDir`) so typed linting follows the tsconfig automatically (docs recommend project service [D] T1).
R9.2 Preset choice (C-list): `strictTypeChecked` for libraries and new services; `recommendedTypeChecked` for legacy codebases. [E] results of the preset content check:
 - in recommendedTypeChecked: no-floating-promises, no-misused-promises, await-thenable, no-explicit-any, all five no-unsafe-*, only-throw-error, prefer-promise-reject-errors, require-await, no-unnecessary-type-assertion, restrict-template-expressions, no-unused-vars, unbound-method, no-unsafe-enum-comparison.
 - added by strictTypeChecked: no-unnecessary-condition, no-non-null-assertion, return-await, no-deprecated, no-confusing-void-expression, use-unknown-in-catch-callback-variable, no-misused-spread, no-extraneous-class, no-unnecessary-type-parameters, related-getter-setter-pairs.
 - NOT in any preset, enable explicitly: `switch-exhaustiveness-check`, `consistent-type-imports` (with `fixStyle: 'inline-type-imports'` or separate; redundant with `verbatimModuleSyntax` compiler error but gives autofix), `no-import-type-side-effects`, `strict-boolean-expressions` (heavy; optional), `no-unsafe-type-assertion` (noisy; optional), `prefer-readonly`.
 - `prefer-nullish-coalescing` lives in stylisticTypeChecked.
R9.3 Rules to configure, not just enable: `no-unused-vars` with `argsIgnorePattern/varsIgnorePattern: '^_'`; `restrict-template-expressions` allow number/boolean as needed; `no-misused-promises` `checksVoidReturn` attributes tuned for frameworks.
R9.4 Disable-comment discipline: `reportUnusedDisableDirectives: 'error'` (ESLint linterOptions) and require descriptions (`eslint-comments` plugin or `ban-ts-comment` for TS directives).
R9.5 TS 7 caveat (key call #2): typescript-eslint and typed linting require the TS 6 JS API; peer `<6.1.0` rejects `typescript@7` [E]. Setup for TS 7 projects: keep `typescript` -> `@typescript/typescript6` alias for tooling, use native `tsc` (7) for type-checking. Revisit once typescript-eslint announces TS 7.1 API support. A community search suggested a support request was closed "not planned" at GA [T3, unverified]; check issue tracker when reconfiguring [U].
R9.6 Core rules worth enabling: `eqeqeq`, `no-var`, `prefer-const`, `no-shadow` (TS variant `@typescript-eslint/no-shadow`), `no-console` (except cli entry), `no-restricted-syntax` (TSEnumDeclaration, `ExportDefaultDeclaration` where wanted), `no-restricted-imports` (ban `moment`-style legacy deps; internal layering), `no-eval`, `no-implied-eval`, `no-new-func`, `no-proto`, `no-prototype-builtins`, `no-throw-literal`->covered, `require-atomic-updates` optional.
R9.7 Security lint: `eslint-plugin-security` (semgrep-ish; noisy, advisory) and `eslint-plugin-regexp` (ReDoS-related rules such as `no-super-linear-backtracking`) [U plugin existence not re-verified this session; names only].

### 9.2 Prettier vs Biome (decision, see C-list)
- Prettier: universal formatter, huge plugin ecosystem, stable style; separate tool from linting. T2.
- Biome: single Rust binary: formatter (Prettier-compatible-ish) + linter + import sorting; v2 line has "types" domain with its own type inference (no `tsc`): `noFloatingPromises`, `noMisusedPromises` are in the `types` domain and are NURSERY (not enabled by `recommended`), scanning the project has a cost [D] T2. Coverage of typescript-eslint's type-aware rule set is partial [U: exact gaps not enumerated].
DEFAULT RECOMMENDATION: ESLint (typescript-eslint, typed) for correctness + a formatter that does NOT lint: Prettier (safe default) or Biome-format-only. Biome as a full replacement only for projects that accept losing the typed rules of section 9.1. Never run two formatters on the same files. Formatter config is the project's; the plugin must NOT reformat code outside the task diff (minimal-diff rule).
R9.8 Formatter in pre-commit/CI check mode (`--check`), not as a fixer in CI. Lint with `--max-warnings 0`.
R9.9 Import order via formatter/linter, not by hand; keep type imports separated (`import type`).

---------------------------------------------------------------------------
## 10. Testing

Facts: Vitest requires Vite >=6.4 and Node >=22.12 (docs), peer `vite ^6.4||^7||^8`; has `typecheck`/`expectTypeOf`, `projects`, v8/istanbul coverage, browser mode [D][E peers] T2. `node:test`: core Stable, snapshots no longer experimental (23.4), coverage (`--experimental-test-coverage`) and watch still Experimental, `mock.fn/method` + timers mocks documented, TS test files discovered by default under type stripping, test tags/randomization/global setup are "early development" [D] T1. `mock.module` presence: function exists on Node 24 but my check printed `undefined` for `typeof require('node:test').mock.module` ... i.e. NOT available without the experimental flag [E, observed; flag name not verified].
R10.1 Default runner: Vitest for any TS project or one that needs mocking of modules, fake timers, snapshot ergonomics, type tests, watch mode, rich coverage. `node:test` for zero-dependency libraries/CLIs and JS projects that want no tooling (and for Node-internals-heavy code), accept experimental coverage. Jest only for legacy codebases (ESM/TS friction). (C-list.)
R10.2 Layout: `x.test.ts` colocated for unit tests; `test/integration/**` and `test/e2e/**` for slower suites; shared builders in `test/support/**`; separate `tsconfig.test.json` (adds test globals via `types`) extending base; tests are type-checked in CI.
R10.3 Test the public contract (inputs -> outputs/effects), not private functions; AAA structure; one behaviour per test; deterministic (no real time, randomness, network).
R10.4 Mocking policy: fake only at boundaries you do not own (network, clock, fs, randomness, third-party SDK) and prefer in-memory fakes/test doubles passed via parameters over module mocking. Avoid mocking your own modules; avoid asserting on call counts unless the call IS the behaviour. Use `AbortSignal`/injected clock for time. Reset mocks automatically (`restoreMocks`/`mockReset` config). For HTTP use a request-level interceptor (undici MockAgent / msw — names only) rather than stubbing `fetch`.
R10.5 Type tests: for libraries with non-trivial public types use `expectTypeOf`/`assertType` (vitest typecheck mode) or `tsd`/`tstyche`-style tools (names only, not researched [U]); compile-time `// @ts-expect-error` assertions inside regular tests also work and cost nothing.
R10.6 Coverage: v8 provider; thresholds are a ratchet not a goal (do not chase 100%); exclude generated/test files; branch coverage on the changed code matters more than the global number. Consistent with the user's testing bands: tests are written from complexity >=7 (global QA rule).
R10.7 Property-based (`fast-check`, name only) for parsers/serializers/pure algorithms; golden-file tests for formatters/codegen.
R10.8 Flaky tests are bugs: no `.skip`/`.only` committed (`vitest --no-only`/lint `no-only-tests` [U plugin]); skips need a tracked issue (global rule).
R10.9 Async tests: always `await`/return; assert rejections via `await expect(p).rejects...`; leaked handles fail via `--detect-async-leaks`-like options [U vitest option names not verified].

---------------------------------------------------------------------------
## 11. Package manager, monorepo, supply chain

Facts [D][E]: pnpm 11 (release notes): `minimumReleaseAge` default 1440 min (1 day), `minimumReleaseAgeStrict` default false (auto-on when you set minimumReleaseAge explicitly, per a 11.1.3 aggregator note [T3]), `blockExoticSubdeps` default true, `strictDepBuilds` default true, `allowBuilds` (map of package pattern -> bool) REPLACES `onlyBuiltDependencies`/`neverBuiltDependencies`/`ignoredBuiltDependencies`/`ignoreDepScripts`; `.npmrc` limited to auth/registry; Node 22+ required. pnpm 12 (current latest on npm; `latest` dist-tag still pointed to 11 per its release post, `pnpm self-update latest-12`): frozen-lockfile flag semantics changed (`--frozen-lockfile false` removed), unknown keys in `pnpm-workspace.yaml` error when pnpm version pinned, `engineStrict` follows normal dependency edges [D] T2. Dependency lifecycle scripts are not run by default (opt-in via `allowBuilds`). `trustPolicy: no-downgrade` blocks installs when a package's trust level (e.g. provenance/trusted-publisher) dropped vs earlier releases; `trustPolicyExclude`/`trustPolicyIgnoreAfter` exist [D] T2.
R11.1 One package manager per repo; default pnpm (strict node_modules, workspace + catalogs, supply-chain controls). npm acceptable for simple/library repos; Yarn/Bun only if inherited. Pin it via `packageManager` field + `engines`. (C-list.)
R11.2 Commit the lockfile; CI installs frozen (`pnpm install --frozen-lockfile` / `npm ci`); never `install` without a lockfile in CI.
R11.3 Lifecycle-script policy: default-deny dependency install scripts; allowlist exactly the packages that need them (`allowBuilds` in `pnpm-workspace.yaml`, pnpm >=11); for npm: `ignore-scripts=true` in `.npmrc` + explicit `npm rebuild <pkg>`; keep `strictDepBuilds` on so new unreviewed builds fail the install. Review every allowlist change.
R11.4 Cooldown: keep `minimumReleaseAge` >= 1 day (default) and consider 7 days (`10080`) for production repos; only exclude packages by explicit name with a reason. Rationale: most malicious npm releases are yanked within days (rationale is [T3 industry claim, [U] not independently measured]; mechanism itself is T2).
R11.5 Block exotic transitive sources (`blockExoticSubdeps: true`: git/tarball URLs in transitive deps); consider `trustPolicy: no-downgrade` once the tree is clean.
R11.6 Audit: `pnpm audit` / `npm audit` in CI at `--audit-level=high` (fail), plus an OSV-based scan or dependabot/renovate for freshness; audit reports are triaged, not blindly "fixed" with overrides. Prefer `overrides`/`resolutions` as a documented, dated exception list.
R11.7 Provenance & publishing: publish via CI with npm Trusted Publishing (OIDC): npm CLI >=11.5.1 and Node >=22.14, GitHub-hosted runners, workflow `permissions: id-token: write`, trusted publisher configured on npmjs.com with exact workflow filename, `repository.url` must match; provenance generated automatically for public packages from public repos; then set package publishing access to "require 2FA, disallow tokens" and revoke old automation tokens; use read-only tokens for private installs; first publish must succeed within 2 days of config [D] T2 (npm docs).
R11.8 Verify what you ship: `npm pack --dry-run`; `publint`; `attw`; check that `files` excludes tests/secrets/`.env`.
R11.9 Workspaces: `pnpm-workspace.yaml` + `workspace:*` protocol for internal deps; catalogs for shared versions (`catalog:`); one root lockfile; per-package `package.json#exports`; root scripts delegate (`pnpm -r`/`--filter`); no cross-package relative imports (`../../other/src`); TS project references (`composite`, `tsc -b`) or `isolatedDeclarations`-driven parallel builds; cache outputs with a task runner only when build time hurts [U: Turborepo/Nx/ moon not researched, names only].
R11.10 Dependency intake gate (matches the user's global dependency rule): new dependency needs identity, freshness (`npm view <pkg> version`), vulnerabilities (`npm audit`/`pnpm audit`), API study (read types/source from `node_modules` or official docs) in the plan BEFORE `package.json` is edited. Prefer platform built-ins first (`fetch`, `node:test`, `util.parseArgs`, `node:crypto`, `structuredClone`, `AbortSignal`, `--env-file`, `node:util styleText`).
R11.11 Typosquat/slopsquat awareness: never install a package name an LLM suggested without checking registry age, downloads, repository link, and publisher.
R11.12 CI hardening: pin third-party GitHub Actions to commit SHAs, minimal `permissions`, no secrets to PR-from-fork workflows, separate publish job gated on environment approval [T3/best practice].
R11.13 `npx`/`dlx` of unpinned remote packages is arbitrary code execution; pin versions or add to devDependencies.
R11.14 Dedupe/hygiene: `knip` (unused deps/exports/files, exists [E]), `pnpm why`, one version per dependency where possible, `peerDependencies` ranges honest for libraries (caps like typescript-eslint's `<6.1.0` demonstrate how a wrong cap blocks users; do not cap without reason).

---------------------------------------------------------------------------
## 12. Library build and bundling

Facts [E][D]: `tsup` README states it is "not actively maintained anymore" and points to `tsdown` (Rolldown + Oxc; tsup-compatible options, migration guide). tsdown peer-depends on typescript `^5||^6||^7` (works with TS 7) and optionally publint/attw integration [E npm peers]. 
R12.1 Choose the least tooling that works:
 - Pure-ESM library, no transforms: `tsc` alone (emit JS + `.d.ts`, `isolatedDeclarations` optional). Zero bundler risk, best debuggability, one-to-one source mapping.
 - Need bundling (single file/UMD-free dist, dual ESM/CJS, JSX, asset handling, tree-shaken entries): tsdown (default). tsup only in already-using repos; plan migration.
 - Apps: the framework/bundler's own tool; the TS config is `noEmit`.
R12.2 Output: ESM `.js`/`.mjs` (+ `.cjs` only if dual), sourcemaps, `.d.ts` (+ `.d.cts` when dual) with matching `exports.types` conditions per format. No minification for libraries.
R12.3 Externalise dependencies (do not bundle `dependencies`/`peerDependencies`); bundle only internal modules.
R12.4 `target` = the lowest supported Node (e.g. `node22` for engines >=22), never transpile modern syntax needlessly.
R12.5 Validate artifacts in CI: `publint` + `attw` (profile `esm-only` or `node16`) + a smoke test importing from the packed tarball in a temp project (ESM and, if dual, CJS).
R12.6 `package.json#exports` is generated or checked against build output; no hand-drifted paths.
R12.7 `declaration` correctness: if `isolatedDeclarations` is on, the bundler can emit declarations without the type checker (fast path); otherwise rely on tsc for `.d.ts`.
R12.8 Executable CLIs: `bin` with shebang `#!/usr/bin/env node`, ESM, no TS at runtime for published packages (Node blocks `.ts` in `node_modules`).

---------------------------------------------------------------------------
## 13. Runtime and performance basics

R13.1 Target an LTS: develop/test on the Active LTS line (24 today), CI matrix = all supported lines in `engines`. Never ship on an EOL line (v20 EOL since 2026-03; v25 EOL). Plan upgrade for v22's end of life.
R13.2 Measure before optimising: `node --cpu-prof`, `--heap-prof`, `perf_hooks` (`performance.mark/measure`, `monitorEventLoopDelay`), `--inspect`, flamegraphs; micro-benchmarks via `tinybench`/`mitata` (names) with warmup. Report numbers, not intuition (global rule: empirical checks).
R13.3 Allocation: avoid per-item closures/objects in hot loops; prefer `for...of`/indexed loops in measured hot paths; typed arrays/Buffers for binary; avoid `delete` on objects (use Map/undefined); `Map`/`Set` for dynamic keys; keep object shapes stable.
R13.4 IO: reuse HTTP agents/connections (`undici`/global `fetch` keep-alive), stream large bodies, batch DB calls, cache with explicit invalidation + size bounds (LRU), timeouts everywhere (`AbortSignal.timeout`).
R13.5 JSON cost: large payloads parse/stringify synchronously on the main thread; stream (NDJSON) or offload.
R13.6 Memory leaks: unbounded Maps/caches, listeners never removed, closures retaining large objects, timers not cleared; use heap snapshots.
R13.7 Startup: lazy `import()` for rarely used heavy modules; avoid import-time side effects; check with `--cpu-prof`; for CLIs consider Node compile cache (`module.enableCompileCache`) [U: not verified this session].
R13.8 Compile time: type perf matters (TS 7 is ~10x faster per vendor [D, vendor claim]); on slow `tsc`, use `--generateTrace`, avoid deep conditional types, enable `incremental`/project references; use `--checkers`/`--singleThreaded` knobs on TS 7.
R13.9 Date/time: `Temporal` not yet in Node 24 [E]; use `Date` with UTC discipline, ISO strings, or a vetted library until runtimes ship it; do not polyfill without need.
R13.10 Config for run: `NODE_ENV=production`, `--enable-source-maps` for emitted JS stacks, `--max-old-space-size` set deliberately in containers.

---------------------------------------------------------------------------
## 14. Security basics

R14.1 Untrusted input is `unknown`; validate (section 4). Never build SQL/shell/HTML/paths by string concat: parameterised queries, `execFile`/`spawn` with arg arrays (never `exec` with interpolation, never `shell: true` with user data), template engines with autoescape, `path.resolve` + prefix check (and `realpath` for symlinks) for file access, `URL`/`URLSearchParams` for URLs, SSRF allowlists for server-side fetches.
R14.2 Prototype pollution: never recursively merge/assign untrusted objects into plain objects (`__proto__`, `constructor`, `prototype` keys); use `Object.create(null)`/`Map` for dictionaries keyed by user input, `Object.hasOwn`, schema `strict`/strip, `structuredClone`; avoid `lodash.merge`-style deep merges on user JSON; consider `node --disable-proto=throw` for services [Node CLI option, existence from knowledge; U not re-verified this session].
R14.3 ReDoS: do not run user-influenced regexes or quadratic patterns on user input; bound input length first; avoid nested quantifiers/overlapping alternations; prefer parsing over regex for structured data; use `RegExp.escape` (ES2026, present Node 24 [E]) when embedding user text; consider a linear-time engine for user-supplied patterns. Lint: `eslint-plugin-regexp` rules [U].
R14.4 Secrets: never in source, `.env` committed, logs, error messages, or client bundles; load via env/secret manager (R4.4); `.env` in `.gitignore`; gitleaks/trufflehog-style scan in CI (names only); rotate on leak. Redact in logs (see user's logging policy).
R14.5 Dangerous APIs banned by lint: `eval`, `new Function`, `setTimeout(string)`, `vm` for untrusted code, `child_process.exec` with interpolation, `innerHTML`/`dangerouslySetInnerHTML` (web), `Math.random()` for secrets (use `node:crypto` `randomBytes`/`randomUUID`), `crypto.createCipher` (deprecated) etc. Mechanical: `no-eval`, `no-implied-eval`, `no-new-func`, `@typescript-eslint/no-implied-eval`.
R14.6 Crypto: use `node:crypto`/WebCrypto; never roll your own; constant-time comparison `timingSafeEqual` for secrets/tokens; argon2/scrypt/bcrypt for passwords; AEAD only; keep policy decisions (algorithms, key mgmt) as escalation items per the user's autonomy bar.
R14.7 HTTP: Node `fetch` timeouts via AbortSignal; limit body sizes; set security headers (framework-specific); validate `Content-Type`; CORS allowlist.
R14.8 Node permission model (`--permission`, `--allow-fs-read`, `--allow-net`, `--allow-child-process`, `--allow-worker`) is a useful hardening seat belt for trusted code and scripts, NOT a sandbox for hostile code: symlinks followed, existing FDs bypass, `--env-file` read before init [D] T1. Use it for build scripts/CLIs; never rely on it to run untrusted plugins.
R14.9 Dependencies are the biggest surface: section 11 policies; avoid dependency for trivial functions; `npm audit` is necessary not sufficient.
R14.10 Error responses: generic client messages, details in logs with correlation id; no stack traces to clients.
R14.11 Logging injection: structure logs as JSON objects, never interpolate user strings into message templates unescaped.
R14.12 Deserialisation: never `eval`/`vm.runIn*`/`serialize-javascript`-style on user data; no `JSON.parse` revivers that instantiate classes by name.

---------------------------------------------------------------------------
## 15. Documentation (TSDoc)

R15.1 Exported API of libraries: TSDoc comment for every export: summary line (what and when), `@param name - description` (TSDoc uses a hyphen), `@returns`, `@throws {ErrorType}` condition, `@example` (runnable-ish), `@deprecated` with replacement and removal version, `@see`; `@remarks` for rationale. Do not repeat the types in prose (types come from TS; in JSDoc-typed JS keep braces types). [TSDoc spec is a Microsoft project; [U] specifics not re-fetched this session beyond knowledge; the tag set above is its standard tag set.]
R15.2 Internal code: comment WHY not WHAT; follow the user's code-policies (mandatory comments for preserved quirks, non-obvious constraints, semantic changes).
R15.3 Keep docs in sync with changes (global rule): update TSDoc, README, and `CHANGELOG` in the same change; examples in README are executed by a test or typechecked (docs-as-test) where feasible.
R15.4 Mechanical (partial): `eslint-plugin-tsdoc` `tsdoc/syntax` (syntax validity) [U plugin], `no-deprecated` (typed, strict preset [E]) forces callers off `@deprecated` APIs; `api-extractor` doc model for public surface [U].
R15.5 README for libraries: install, 10-line quickstart, runtime support matrix (Node versions, ESM-only note), API reference link, security/provenance note. For apps: run/build/test commands, env var table (generated from the env schema).

---------------------------------------------------------------------------
## A. What can be enforced mechanically vs advisory

### A.1 tsconfig (compiler errors; strongest)
`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noImplicitReturns`, `noFallthroughCasesInSwitch`, `verbatimModuleSyntax`, `isolatedModules`, `erasableSyntaxOnly` (kills enum/namespace/parameter properties [E]), `isolatedDeclarations` (explicit public types), `moduleDetection: force`, `noUncheckedSideEffectImports`, `noEmitOnError`, `forceConsistentCasingInFileNames`, `module`/`moduleResolution` pairing (catches missing `.js` extensions, bad `exports` types), `types` explicit list.

### A.2 ESLint (typescript-eslint, typed) — rule names verified to exist [E]
Presets: `recommendedTypeChecked` (floor) / `strictTypeChecked` (ceiling) + `stylisticTypeChecked`.
Explicit adds: `@typescript-eslint/switch-exhaustiveness-check`, `consistent-type-imports`, `no-import-type-side-effects`, `prefer-readonly`, `no-restricted-types`/`no-restricted-imports`, optional `strict-boolean-expressions`, `no-unsafe-type-assertion`, `naming-convention`.
Core: `eqeqeq`, `no-var`, `prefer-const`, `no-eval`, `no-implied-eval`, `no-new-func`, `no-restricted-syntax` (enums, default exports), `no-param-reassign`, `no-empty`.
Config: `reportUnusedDisableDirectives: 'error'`, `--max-warnings 0`.
Plugins (names only, existence not re-verified here): import/boundaries/cycle rules, `eslint-plugin-regexp`, `eslint-plugin-security`, `unicorn`.

### A.3 CI / tooling gates
typecheck (`tsc --noEmit`, TS 7 where adopted), lint (`--max-warnings 0`), format `--check`, tests + coverage threshold ratchet, build, `publint`, `attw`, `knip`, `npm|pnpm audit --audit-level=high`, lockfile frozen install, `npm pack --dry-run` content check, secret scan, SHA-pinned Actions, trusted-publishing release job with provenance.
Package-manager config (pnpm): `minimumReleaseAge`, `allowBuilds`, `strictDepBuilds`, `blockExoticSubdeps`, `trustPolicy`, `engineStrict`; `engines`, `packageManager`.

### A.4 Hooks (local, fast)
PostToolUse on edited TS/JS: run formatter on changed file only (never repo-wide), and `tsc --noEmit` per project at turn end or pre-commit; pre-commit: lint-staged-style typed lint on staged files + typecheck; pre-push: tests. Never bypass hooks (global rule). Hooks only run what the project's own scripts define.

### A.5 Advisory only (needs review/judgement)
Parse-at-boundary discipline; throw vs Result consistency; module boundaries; no barrels; naming; test quality/mocking policy; immutability beyond `readonly`; JSDoc/TSDoc quality; dependency choice; ReDoS review of regex; prototype-pollution-prone merges; secrets handling beyond scanner patterns; perf claims (need measurement); ESM-vs-dual decision.

---------------------------------------------------------------------------
## B. Proposed plugin: `v1rus-typescript`

Design constraints: framework-agnostic; reads the project's own script names; never hardcodes package versions; cooperates with the user's global workflow (builder subagents on sonnet for implementation; reviewers inherit; `/finalize` gate; test depth by complexity; never add dependencies without the plan-stage gate).

### B.1 Skills (trigger-style descriptions)
1. `ts-project-setup` — Use when: creating a new TS/JS package/app/library, adding or editing `tsconfig*.json`, choosing module/moduleResolution, migrating to ESM, adopting TS 6/7, `erasableSyntaxOnly`, Node type stripping. NOT for: editing application logic, framework configs (Next/Nest/Vite app wiring).
   Content: sections 0-2, 8, 12 decision tables; produces baseline tsconfig per variant; detects `typescript` major and installed typescript-eslint peer range before suggesting a bump.
2. `ts-type-design` — Use when: modelling domain types, unions/exhaustiveness, branded types, replacing `enum`/`any`/`!`/`as`, generics, `satisfies`, API signature design, `isolatedDeclarations`. NOT for: runtime validation (use `ts-boundaries`) or lint config.
3. `ts-boundaries` — Use when: handling external input (HTTP, env, files, JSON, DB, queues, CLI), choosing/using a schema library, designing error handling (Error cause, Result vs throw, typed errors). NOT for: pure internal logic.
4. `ts-async-node` — Use when: writing/reviewing async code, streams, AbortSignal/timeouts, concurrency limits, graceful shutdown, event-loop concerns, worker threads. NOT for: synchronous pure code.
5. `ts-lint-format` — Use when: configuring ESLint flat config/typescript-eslint, adding rules, Prettier/Biome decision, fixing lint errors without suppressing them. NOT for: fixing a single lint error in-place (just fix it).
6. `ts-testing` — Use when: choosing runner, writing/refactoring tests, mocks/fakes, type tests, coverage, test layout (respecting the global complexity-band rule: no tests written below band 7 unless asked). NOT for: running the suite (use verification commands) or UI/E2E framework specifics.
7. `ts-supply-chain` — Use when: adding/updating dependencies, lockfile/audit failures, lifecycle scripts, pnpm/npm config, monorepo workspace setup, publishing/provenance, `package.json` `exports`/`files`/`engines`. NOT for: choosing business libraries (use evaluate-dependency flow).
8. `ts-js-checkjs` — Use when: project is plain JS (ESM/CJS) and needs types without migration, adding `// @ts-check`/`checkJs`, JSDoc generics, or deciding when to migrate to `.ts`. NOT for: TS-only projects.
9. `ts-security-review-checklist` — Use when: reviewing/writing code touching user input, regex, merges of untrusted objects, child processes, file paths, crypto, secrets. Feeds `security-expert` agent. NOT for: general code review.
10. `ts-perf-profile` — Use when: a measured slowness/memory/event-loop problem exists, or `tsc` compile time is slow. NOT for: speculative optimisation.

### B.2 Agents
- `ts-engineer` (builder; run on sonnet per global rule): implements/refactors TS/JS code following this playbook; MUST (1) read `package.json`/lockfile/tsconfig/eslint config to learn script names and versions, (2) apply R-rules by section, (3) run the project's typecheck+lint scripts on changed scope, (4) never add dependencies or flags without plan-stage output, (5) minimal diff (no drive-by reformat/modernisation). Tools: Read/Edit/Write/Bash/Grep.
- `ts-reviewer` (read-only; inherits model): reviews diffs against sections 1-15 prioritised: unsound types (`any`, `as`, `!`), unvalidated I/O, floating promises/missing cancellation, error handling (lost cause, swallowed), ESM/exports correctness, supply-chain changes (lockfile/scripts), test quality. Reports only real problems; cites rule id (R-number). Tools: Read/Grep/Glob.
- `ts-toolchain-doctor` (diagnostic; read-mostly): diagnoses TS 6/7 + typescript-eslint peer conflicts, module-resolution errors, `exports` problems (runs `attw`/`publint` if present), slow typecheck; proposes fixes, returns a plan (does not edit).
- Reuse existing global `security-expert`, `performance-expert`, `build-engineer` (note: build-engineer is Gradle-specific; do NOT route JS builds to it), `test-runner` (currently desktop/Gradle-oriented; needs a JS-aware runner or the ts-engineer runs the project scripts itself) [U: verify before wiring].

### B.3 Path-scoped rules (content = compressed R-rules; each file <= ~60 lines)
- `**/*.ts, **/*.tsx, **/*.mts, **/*.cts, **/*.js, **/*.mjs, **/*.cjs` -> `ts-source.md`: R3.*, R4.1, R5.*, R6.1-6.4, R7.3, R7.6, imports with extensions and `import type`, no enum/any/!/as, `unknown`, `node:` prefix, no floating promises, `Error` cause, no `process.env` outside config module.
- `tsconfig*.json, jsconfig.json` -> `ts-config.md`: R1.* and variant table; do not weaken `strict`/flags to silence errors (fix code); check TS major before using options removed in 7; explicit `types`; no `paths`/`baseUrl` without bundler.
- `package.json, pnpm-workspace.yaml, .npmrc, .npmrc*` -> `ts-package.md`: R2.1/2.3/2.9/2.10, R11.*; "no new dependency without plan gate"; do not edit versions by hand — resolve via registry; keep `exports` condition order, `type`, `engines`, `packageManager`; never enable `dangerouslyAllowAllBuilds`-style switches; lockfile changes accompany manifest changes.
- `**/*.test.ts, **/*.spec.ts, **/*.test.js, test/**` -> `ts-test.md`: R10.*; no `.only/.skip` without tracked issue; mock only boundaries; no real network/time; assertions on behaviour; separate tsconfig types for test globals.
- `eslint.config.*, biome.json*, .prettierrc*` -> `ts-lint-config.md`: R9.*; never disable a rule globally to pass; every suppression has a reason; no formatter changes outside task diff.
- `.github/workflows/*` (optional) -> publish/CI rules R11.7, R11.12.

### B.4 Verification command set (project-agnostic; resolve names from `package.json#scripts` first, fall back to direct tools)
Order (stop at first failure; scope to the affected package in monorepos):
1. typecheck — script named like `typecheck|check-types|tsc`; fallback `tsc --noEmit -p <tsconfig>` (use `tsc -b` for project references). TS 7 projects: native `tsc`.
2. lint — script `lint`; fallback `eslint . --max-warnings 0` (or `biome check`). Typed lint requires TS 6 API (see R9.5).
3. format check — script `format:check` / `prettier --check` / `biome format`.
4. test — script `test` (vitest run / node --test / jest); scope by path for changed modules; coverage only at final gate.
5. build — script `build` (tsc/tsdown/bundler) then artifact checks for libraries: `publint`, `attw --pack`, `npm pack --dry-run`.
6. audit — `pnpm audit --audit-level=high` / `npm audit --audit-level=high`; supply-chain config diff review.
Per global QA rules: logic changes -> typecheck+lint+scoped tests; no-logic edits (types-only/rename/import/comments) -> typecheck only; config/markdown -> none unless tsconfig/package change (then typecheck + build).
Discovery: detect package manager from lockfile (`pnpm-lock.yaml`, `package-lock.json`, `yarn.lock`, `bun.lock*`) and `packageManager` field; detect workspace (`pnpm-workspace.yaml`, `workspaces`). Never assume script names; never run installs/updates unprompted; no `sudo`.

### B.5 Out of scope; future separate plugins
- `v1rus-react` (Next/Vite-React): component typing, hooks rules (`eslint-plugin-react-hooks`), server/client component boundaries, RSC data fetching, a11y, testing-library; bundle-size budgets.
- `v1rus-nest` / backend frameworks (Nest, Fastify, Express, Hono): DI/module structure, DTO validation pipes, decorators (non-erasable; conflicts with `erasableSyntaxOnly`), OpenAPI, auth/guards.
- `v1rus-vue`/`svelte`/`angular`: note Vue/MDX/Astro/Svelte/Angular editor support still needs TS 6 language service because TS 7 lacks a stable plugin API [D].
- `v1rus-node-infra`: observability, containers, queues, DB access layers, Prisma/Drizzle-like ORMs.
- `v1rus-web-platform`: browser APIs, service workers, CSP.

---------------------------------------------------------------------------
## C. Decisions with two defensible options (log as ASSUMPTION lines) and unverified items

### C.1 Assumption candidates
1. ASSUMPTION: TypeScript line — new projects start on TS 7 `tsc` for type-checking (native, fast) but keep TS 6 (via `@typescript/typescript6` alias) for typescript-eslint/any compiler-API tooling; projects without such tooling use plain TS 7. Alt: stay on TS 6 until 7.1 API ships (safer, ESLint just works). Reverse: swap aliases. [facts E/D]
2. ASSUMPTION: module setup — ESM-only libraries, `module: node20`/`nodenext`, require(esm)-compatible (no TLA), `engines.node >= 22.12`-ish. Alt: dual ESM+CJS via tsdown for CJS-only consumers/Node < 20.19. [T1 facts; recommendation is judgement]
3. ASSUMPTION: `erasableSyntaxOnly: true` by default for new code (also valid for apps that bundle). Alt: allow enums/parameter properties where the team prefers them (then drop the flag and rely on lint). 
4. ASSUMPTION: ESLint+typescript-eslint typed (`strictTypeChecked` for new/lib, `recommendedTypeChecked` for legacy) + Prettier for formatting. Alt: Biome full-stack (faster, one tool, fewer typed rules; type-aware rules nursery) — adopt when speed outweighs typed-lint depth.
5. ASSUMPTION: Zod default schema lib; Valibot/`zod/mini` for size-sensitive browser code; libraries accept Standard Schema. Alt: ArkType or hand-written guards for tiny surfaces.
6. ASSUMPTION: Vitest default; `node:test` for zero-dep libs/JS; Jest legacy only.
7. ASSUMPTION: pnpm default PM with `allowBuilds` allowlist, 1-day (default) to 7-day `minimumReleaseAge`, frozen lockfile in CI. Alt: npm with `ignore-scripts`. 
8. ASSUMPTION: Result type = hand-rolled discriminated union, no library (per dependency rule). Alt: neverthrow-style libs.
9. ASSUMPTION: no barrel files inside apps; curated entry in libs. Alt: barrels per feature if the team accepts the cycle/tree-shake cost.
10. ASSUMPTION: library build = `tsc` alone when no bundling is needed, else tsdown (not tsup). Alt: keep tsup in existing repos (unmaintained per its README).
11. ASSUMPTION: `noPropertyAccessFromIndexSignature` ON for backends, OFF for code heavy on dictionaries; `exactOptionalPropertyTypes` ON for new projects, OFF when integrating libs with sloppy optional typings (frequent friction). Alt either way.
12. ASSUMPTION: `isolatedDeclarations` ON for libs/monorepo packages only.
13. ASSUMPTION: kebab-case file names; named exports only.
14. ASSUMPTION: `using` allowed only where all supported runtimes have it (Node >= 24); otherwise try/finally.

### C.2 Not verified / needs follow-up
- typescript-eslint support timeline for TS 7 / 7.1 API: only a T3 blog claim and the peer range (`<6.1.0`) verified [E]. Check typescript-eslint issue tracker and TS 7.1 release when reconfiguring.
- TS 7.1 release date and API shape: unreleased as of this date (`typescript@next` = 7.1.0-dev) [E]; blog "~Oct 2026" is T3 estimate.
- Vitest 5 migration breaking changes (page lists a guide, not read). Vitest option names such as async-leak detection not verified.
- `node:test` `mock.module` availability: `typeof mock.module` printed `undefined` on Node 24.22 [E]; flag/status not read (docs page truncated).
- Biome: exact type-aware coverage vs typescript-eslint, Prettier-compat percentage; only domain page read (nursery status of `noFloatingPromises`/`noMisusedPromises` [D]).
- pnpm 12 specifics for supply-chain defaults (release note page did not cover them); pnpm 11 facts via pnpm blog summary through search (T2) and one aggregator note (T3). `trustPolicy` default unknown. `pnpm audit` flags not documented on the pages read.
- ArkType, neverthrow, madge/dpdm/dependency-cruiser, eslint-plugin-regexp/security/unicorn/boundaries/tsdoc, tinybench/mitata/fast-check, api-extractor, tstyche/tsd, gitleaks/trufflehog: named from background knowledge only; NOT verified this session (existence, maintenance, TS 7 compat).
- `node --disable-proto`, `module.enableCompileCache`, Node "Don't Block the Event Loop" guide: from knowledge, not re-fetched.
- TSDoc tag specifics: from knowledge (spec not re-fetched).
- Test-runner / build-engineer global agents are Gradle/desktop oriented; JS-aware replacement/wiring is a plugin-design TODO.
- Empirical spike limits: only Node 24.22 + TS 6.0.3/7.0.2 locally; no ESLint typed-lint run against a real project, no vitest run, no tsdown build, no pnpm run (CLI not installed here). Section 0 and rule-set claims marked [E] are the ones actually run.

### C.3 Sources consulted (tier)
T1: devblogs.microsoft.com/typescript (7.0, 6.0 posts); typescriptlang.org/tsconfig, handbook TS 5.5 notes; nodejs.org (typescript, previous-releases, modules, packages, permissions, test); github.com/tc39/proposals finished-proposals; typescript-eslint.io/users/configs; local runs (node 24.22, tsc 6.0.3/7.0.2, typescript-eslint+eslint 10 rule/preset introspection, npm registry metadata).
T2: pnpm.io (supply-chain-security, settings, blog 11.0 via search, blog 12.0); docs.npmjs.com trusted-publishers; zod.dev/v4; valibot.dev; standardschema.dev; vitest.dev/guide; biomejs.dev (blog, linter domains); tsup/tsdown READMEs via npm.
T3/T4 (cross-check only): third-party blogs on TS 7 migration/typescript-eslint status (digitalapplied, ecorpit, mergify via search summary); newreleases.io note on pnpm 11.1.3.
