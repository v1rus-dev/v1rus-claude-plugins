---
name: ts-lint-and-format
description: "The static-analysis gate for a v1rus TypeScript project: ESLint flat config (eslint.config.js as an array, per-entry files/ignores, no cascading extends) with type-aware typescript-eslint enabled through projectService, the rules that only exist with type information (no-floating-promises, no-misused-promises, the no-unsafe-* family, switch-exhaustiveness-check, no-unnecessary-condition, consistent-type-imports) and why a project without them is not linted for anything that matters, the v1rus additions on top of the recommended sets, Prettier owning formatting and ESLint never doing it, and the discipline for escapes — one rule, one line, a reason after `--`, reportUnusedDisableDirectives, `@ts-expect-error` instead of `@ts-ignore`, and CI running with zero tolerated warnings. Load when creating or editing eslint.config, adding or disabling a lint rule, setting up or fixing the lint and format scripts, migrating from .eslintrc, arguing about formatting, or when a disable comment appears in a diff. Not for compiler options (`ts-project-config`) or for the process-level quality gates themselves (`v1rus-qa`)."
---

# Lint and Format

## Flat config, and it is an array

`eslint.config.js` (or `.ts`) exporting an array of config objects is the current format;
`.eslintrc` is legacy and its `extends` cascade does not exist here. The consequences a model
usually gets wrong when writing one:

- **There is no inheritance.** A shared config is an array you spread into yours, in order; later
  entries override earlier ones.
- **`files` and `ignores` are per entry.** An entry with neither applies to everything. A top-level
  entry containing only `ignores` is the replacement for `.eslintignore`, which is gone.
- **Plugins are imported values**, keyed in a `plugins` object — not resolved from strings.
- **`languageOptions`** holds parser, parser options and globals; `linterOptions` holds
  `reportUnusedDisableDirectives`.

## Type-aware linting is the point

```js
// eslint.config.js
export default [
  { ignores: ['dist/**', 'coverage/**'] },
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: { parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname } },
    linterOptions: { reportUnusedDisableDirectives: 'error' },
    rules: { /* the v1rus additions, below */ },
  },
  eslintConfigPrettier,
];
```

Without `projectService` (or an explicit `project`), the rules that catch the bugs this plugin cares
about **do not run at all** — they are silently absent, not failing:

| Rule | What it is the only mechanical check for |
|---|---|
| `@typescript-eslint/no-floating-promises` | A promise nobody holds (`ts-async`) |
| `@typescript-eslint/no-misused-promises` | An async callback in a void-returning slot — the `forEach(async …)` and `onClick={async …}` trap |
| `@typescript-eslint/await-thenable` | `await` on a non-promise, usually a forgotten call |
| `@typescript-eslint/no-unsafe-assignment`, `-argument`, `-return`, `-member-access`, `-call` | Every path by which an `any` from an untyped boundary spreads — this family is what makes `any` a build failure instead of a habit (`ts-boundaries-validation`) |
| `@typescript-eslint/switch-exhaustiveness-check` | A `switch` that stopped covering its union (`ts-type-modelling`) |
| `@typescript-eslint/no-unnecessary-condition` | A null check on something that cannot be null — usually the leftover of a type that got stricter, and a reliable sign the author did not trust the types |
| `@typescript-eslint/consistent-type-imports` | Type-only imports, paired with `verbatimModuleSyntax` (`ts-project-config`) |
| `@typescript-eslint/require-await` | An `async` function with no `await` — a signature promising asynchrony it does not have |

**Type-aware linting is slower. That is not a reason to turn it off.** Scope it (lint the source
tree, not generated output), cache it in CI, and keep the whole repository covered in the CI run.

## The v1rus additions

On top of `strictTypeChecked`:

- `@typescript-eslint/no-explicit-any`: `error`. `any` is a defect; `unknown` at the boundary.
- `@typescript-eslint/no-non-null-assertion`: `error`. `!` needs a reason, and a reason means a
  disable comment that a reviewer reads.
- `@typescript-eslint/no-unused-vars`: `error` with `argsIgnorePattern: '^_'` and
  `varsIgnorePattern: '^_'`, so an intentionally unused parameter is visibly intentional.
- `no-restricted-imports` (or `import-x/no-restricted-paths`): deep imports into package internals
  and cross-layer imports that the architecture forbids (`ts-package-structure`).
- `import-x/no-cycle`: import cycles fail the build, not the on-call engineer.
- `eqeqeq` with `smart` — `== null` is the one useful loose comparison.

Framework rule sets (React hooks, JSX a11y, Node or Nest specifics) come from the layer above and
are added to the same array there; this layer owns the language rules only.

## ESLint does not format

Prettier owns formatting. ESLint owns correctness. Mixing them produces two tools fighting over the
same lines and a review spent on commas.

- `eslint-config-prettier` goes **last** in the array, switching off every stylistic rule that could
  conflict.
- Do not enable ESLint stylistic/formatting rules, and do not run Prettier through ESLint.
- Prettier's configuration is short and not a discussion topic: the formatter decides, the diff is
  never about whitespace, and format-on-save plus a CI `prettier --check` keeps formatting churn out
  of feature diffs.

## Escapes need a reason

```ts
// eslint-disable-next-line @typescript-eslint/no-non-null-assertion -- schema guarantees `id` is set after parse
const id = parsed.id!;

// @ts-expect-error -- upstream types omit the `signal` option; tracked in ACME-1234
client.stream(url, { signal });
```

- **One rule, one line.** `eslint-disable-next-line <rule>` with the rule named. Never a bare
  `/* eslint-disable */` at the top of a file, and never disabling the whole rule set.
- **The reason goes after `--`**, in the same comment, and says *why the rule is wrong here* — not
  what the rule is. "needed" is not a reason.
- **`@ts-expect-error`, never `@ts-ignore`.** `@ts-expect-error` becomes an error once the
  suppression is no longer needed, so it cleans itself up; `@ts-ignore` rots invisibly for years.
- **`reportUnusedDisableDirectives: 'error'`** does the same for ESLint disables.
- A disable that survives review becomes a comment with an issue reference, not a permanent local
  exception.

## The gate

Lint and typecheck are L1 static analysis in `v1rus-qa`, and they gate the same way:

- CI runs `eslint . --max-warnings=0`. A warning nobody fails on is documentation, not a gate — a
  rule is either `error` or removed.
- `tsc --noEmit` runs separately: the bundler does not typecheck (`ts-project-config`).
- Both run on the whole repository in CI, whatever the local editor does.
- Adding a lint plugin or a shared config package is a dependency decision and goes through
  `v1rus-dependencies`; never pin a version from memory.
