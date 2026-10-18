---
name: ts-checkjs
description: |-
  Use when a project is plain JavaScript (ESM or CJS) and needs type safety without migration: adding checkJs or // @ts-check, JSDoc types and generics, or deciding when to migrate files to .ts.
  Do NOT use for TypeScript-only projects.
---

# Plain JS with checkJs

1. Add a `tsconfig.json` per the `ts-project-config` skill (plain-JS variant) and run `tsc` as the gate. Prefer a tsconfig file over CLI flags.
2. JSDoc style, TypeScript 7 JSDoc restrictions, migration criteria: `${CLAUDE_PLUGIN_ROOT}/skills/ts-checkjs/reference/jsdoc.md`.
3. Apply the `typescript-conventions`, `ts-type-modelling` and `ts-boundaries-validation` skills; the `typescript.md` rule matches only TS files, so load them explicitly for `.js/.mjs/.cjs`.
