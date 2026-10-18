---
paths:
  - "eslint.config.*"
  - "**/eslint.config.*"
  - ".eslintrc*"
  - "biome.json*"
  - "**/biome.json*"
  - ".prettierrc*"
  - "prettier.config.*"
  - ".prettierignore"
---

# Lint and format configuration

- Never disable a rule globally to make a check pass: fix the code. A suppression comment carries a reason and targets one line; `reportUnusedDisableDirectives` should be `error`. Run lint with `--max-warnings 0`.
- Do not change formatter settings or reformat files outside the task diff. One formatter per file set; run formatters in check mode in CI.
- ESLint is flat config only (`eslint.config.*`). Use `defineConfig` from `eslint/config`; `js.configs.recommended` comes from the separate `@eslint/js` package (it is a dev dependency of its own, not bundled with ESLint; verified).
- typescript-eslint presets: `strictTypeChecked` for new code and libraries, `recommendedTypeChecked` for legacy; `stylisticTypeChecked` optional. The docs mark `strict`, `strict-type-checked` and `all` as unstable across minor versions: review the rule diff on every bump.
- Typed linting: `languageOptions.parserOptions.projectService: true` plus `tsconfigRootDir: import.meta.dirname`. Files outside every tsconfig (for example `eslint.config.js` itself) fail with a project-service parsing error; either include them in a tsconfig or apply `tseslint.configs.disableTypeChecked` to them (verified failure mode). Plain JS that is not in a tsconfig gets the same treatment.
- Rules not in any preset that are worth enabling explicitly: `@typescript-eslint/switch-exhaustiveness-check`, `consistent-type-imports`, `no-import-type-side-effects`, `prefer-readonly`; optional and noisy: `strict-boolean-expressions`, `no-unsafe-type-assertion`, `prefer-readonly-parameter-types`. Check a rule name exists in the installed version before adding it.
- No dedicated `no-enum` rule exists: for non-erasable projects use `no-restricted-syntax` with selector `TSEnumDeclaration`.
- Configure rather than just enable: `no-unused-vars` with `argsIgnorePattern`/`varsIgnorePattern` `^_`; `no-misused-promises` `checksVoidReturn` tuned to the framework.
- Useful core rules: `eqeqeq`, `no-var`, `prefer-const`, `no-eval`, `no-implied-eval`, `no-new-func`, `no-restricted-imports`, `no-console` (except CLI entrypoints).
- TypeScript 7 caveat: typed ESLint needs the TypeScript 6 compiler API; as checked at authoring, typescript-eslint's peer range on `typescript` excludes 7 (`npm view typescript-eslint peerDependencies`). Re-check before changing the `typescript` dependency; see the `ts-project-setup` skill for the side-by-side alias setup.
- Biome as a full replacement loses typescript-eslint's type-aware rules (its type-aware rules are younger and partial; verify against Biome's docs for the installed version). Only adopt it when the team accepts that, and never run it as a second formatter next to Prettier.
