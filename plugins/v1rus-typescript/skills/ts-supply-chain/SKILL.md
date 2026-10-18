---
name: ts-supply-chain
description: |-
  Use when adding or updating npm dependencies, handling lockfile or audit failures, lifecycle scripts, pnpm/npm configuration, workspace/monorepo setup, publishing and provenance, or package.json exports/files/engines.
  Do NOT use to pick business libraries by feature (use evaluate-dependency) or for application code.
---

# Supply chain and packaging

1. New or bumped dependency: produce the four plan outputs from the global dependency rule using npm tooling: identity, freshness (`npm view <pkg> name version peerDependencies engines`), vulnerabilities (`npm audit` / `pnpm audit`), API study (read the package types/docs). Check peer ranges against the project's `typescript`/`eslint` (a wrong cap blocks installs). No plan block, no edit.
2. Manifest and manager config conventions: `${CLAUDE_PLUGIN_ROOT}/rules/ts-package.md`.
3. Hardening, publishing and CI checklist: `${CLAUDE_PLUGIN_ROOT}/skills/ts-supply-chain/reference/hardening.md`.
4. Never run installs/updates unprompted; never bypass hooks.
