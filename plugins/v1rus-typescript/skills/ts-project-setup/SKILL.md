---
name: ts-project-setup
description: |-
  Use when creating a new TypeScript/JavaScript package, app or library, adding or editing tsconfig, choosing module/moduleResolution, migrating to ESM, adopting TypeScript 6/7, erasableSyntaxOnly, or running .ts under Node type stripping.
  Do NOT use for application logic, framework wiring (Next/Nest/Vite app config) or a single compiler error in existing code.
---

# TypeScript project setup

1. Detect first: package manager (lockfile, `packageManager`), `typescript` major (`npx tsc -v`, lockfile), Node line (`engines`, `.nvmrc`), module system (`type`), workspace layout. Do not assume.
2. Pick the target variant and baseline flags from `${CLAUDE_PLUGIN_ROOT}/rules/ts-config.md`.
3. TypeScript 6/7 side-by-side, library vs app decisions, ESM-only vs dual: `${CLAUDE_PLUGIN_ROOT}/skills/ts-project-setup/reference/toolchain.md`.
4. Package metadata (`exports`, `engines`, `files`): `${CLAUDE_PLUGIN_ROOT}/rules/ts-package.md`.
5. Verify with the project's typecheck script; for a new project run `tsc --noEmit` on a sample file that violates each flag you rely on. Adding dependencies goes through the plan-stage gate (see `ts-supply-chain`).
