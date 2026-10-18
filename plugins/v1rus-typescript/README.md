# v1rus-typescript

Rules, skills and agents for JavaScript and TypeScript (Node backends, libraries, tooling, framework-agnostic web code, plain JS via JSDoc/checkJs). Depends on `v1rus-core` (workflow gates, review agents, rules engine). Framework specifics (React/Next/Nest/Vue) are out of scope.

## Contents
- `rules/` (path-scoped, injected on Write/Edit): `ts-types` and `ts-boundaries` (source files), `ts-config` (tsconfig/jsconfig), `ts-package` (package.json, pnpm-workspace.yaml, .npmrc), `ts-test` (test/spec files), `ts-lint-config` (eslint/biome/prettier config).
- `skills/` (thin doors, long material in `reference/`): `ts-project-setup`, `ts-type-design`, `ts-boundaries`, `ts-async-node`, `ts-lint-format`, `ts-testing`, `ts-supply-chain`, `ts-checkjs`, `ts-security-checklist`, `ts-perf-profile`.
- `agents/`: `ts-engineer` (sonnet, implements), `ts-reviewer` (read-only), `ts-test-runner` (project scripts first, detected package manager, reports NOT RUN instead of skipping), `ts-toolchain-doctor` (diagnoses, does not edit).
- No `charter.md`: every always-on fact (strictness, detect-before-assume, dependency gate) is already carried by core's charter/rules or fires on the first edit of a matching file; an always-on layer would cost context in non-JS sessions.

## Decision log
- Mechanical enforcement (tsconfig flags, typed ESLint rules) is documented as such; judgement items are advisory bullets. Rules say "project config wins".
- Rules were split in two source rules (types vs boundaries/async/security) to stay under ~150 lines each and to keep injection relevant.
- Playbook `ts-config` per-variant table kept; `.github/workflows` rule dropped (marked optional in the playbook; CI/publishing lives in `skills/ts-supply-chain/reference/hardening.md`).
- Packages are named only; no versions anywhere. Facts worth knowing that were verified here (scratch spikes, authoring date 2026-10-18): the TypeScript 7 plus TypeScript 6 alias recipe installs next to typescript-eslint and typed ESLint runs; `@eslint/js` is a separate package; ESLint typed config files outside a tsconfig fail with a project-service error unless `disableTypeChecked` is applied; `tsc` 7 supports `--extendedDiagnostics --generateTrace --checkers --singleThreaded --builders`; Vitest has `--allowOnly` and `--detectAsyncLeaks`; `node:test` `mock.module` needs `--experimental-test-module-mocks`; pnpm setting names exist in the pnpm settings docs. pnpm defaults are NOT stated in rules (not verified).
- Playbook corrections: `@typescript/native` is not a registry package, only an alias key; `mock.module` flag now named; pnpm 11/12 default values were dropped from rules.
- `ts-test-runner` replaces the Gradle-oriented global `test-runner` for JS/TS; Gradle-specific `build-engineer` (from `v1rus-kotlin`, if installed) is not routed JS builds.

## Assumptions (ASSUMPTION: choice, why, how to reverse)
1. TypeScript line: native tsc for checking, TypeScript 6 alias for compiler-API tooling; plain 7 without such tools. Reverse: stay on 6 (edit `ts-project-setup/reference/toolchain.md`, `ts-config.md`).
2. ESM-only libraries, `node20`/`nodenext`, no top-level await in library code. Reverse: dual output via bundler (`ts-package.md`, toolchain reference).
3. `erasableSyntaxOnly` on for new code. Reverse: drop the bullet in `ts-config.md`/`ts-types.md`, lint enums instead.
4. typescript-eslint typed (`strictTypeChecked` new, `recommendedTypeChecked` legacy) plus a non-linting formatter; Biome only if typed rules are given up. Reverse: edit `ts-lint-config.md`.
5. Schema library: use the project's; if none, evaluate Zod/Valibot/ArkType via the dependency gate (no default pick hardcoded, unlike the playbook's Zod default, to honor the dependency policy). Reverse: add a default in `ts-boundaries.md`.
6. Test runner: Vitest default for TS, `node:test` for zero-dep/plain JS, Jest legacy only. Reverse: `ts-test.md`.
7. pnpm default with lifecycle-script allowlist and release-age cooldown; npm alternative with `ignore-scripts`. Reverse: `ts-package.md`, hardening reference.
8. Result type is a hand-rolled discriminated union, no library. Reverse: `ts-boundaries.md`.
9. No barrel files in apps; curated entry in libraries. Reverse: `ts-types.md`.
10. Library build: `tsc` alone, else tsdown (not tsup). Reverse: toolchain reference.
11. `noPropertyAccessFromIndexSignature` and `exactOptionalPropertyTypes` are project judgement calls, not forced. Reverse: `ts-config.md`.
12. `isolatedDeclarations` on for libraries/monorepo packages only. Reverse: `ts-config.md`.
13. kebab-case file names, named exports. Reverse: `ts-types.md`.
14. `using` only when all supported runtimes have it, else `try/finally`. Reverse: `ts-types.md`.

## Unverified
Defaults and semantics of pnpm settings; typescript-eslint plans for TypeScript 7.1; Biome type-aware coverage; npm trusted-publishing minimum versions (point to docs); optional plugin behaviour (eslint-plugin-regexp/security/boundaries, knip, attw, publint beyond existence on npm); Node `--disable-proto` and compile cache (not mentioned in rules).

## Install

```
/plugin marketplace add v1rus-dev/v1rus-claude-plugins
/plugin install v1rus-typescript@v1rus-dev
```

Dependencies (v1rus-core) are resolved automatically from the same marketplace.
