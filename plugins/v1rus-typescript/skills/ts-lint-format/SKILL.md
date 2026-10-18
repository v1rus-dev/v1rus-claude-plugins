---
name: ts-lint-format
description: |-
  Use when configuring ESLint flat config or typescript-eslint, adding or changing lint rules, deciding between Prettier and Biome, or fixing many lint errors without suppressing them.
  Do NOT use to fix one lint error in place (just fix it) or to reformat code outside the task.
---

# Lint and format setup

1. Read the project's existing eslint/biome/prettier config and scripts; extend, do not replace.
2. Apply `${CLAUDE_PLUGIN_ROOT}/rules/ts-lint-config.md` (presets, project service, typed-lint caveats, TypeScript 7 compatibility check).
3. Check that every rule name exists in the installed plugin version before enabling it (run eslint; an unknown rule fails loudly).
4. Run the project's lint script with `--max-warnings 0`. Fix findings; add no blanket disables.
