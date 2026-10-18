---
paths:
  - "package.json"
  - "**/package.json"
  - "pnpm-workspace.yaml"
  - ".npmrc"
  - "**/.npmrc"
---

# package.json and package-manager config

- Adding or bumping a dependency is a plan-stage decision: identity, freshness (`npm view <pkg> version`), vulnerabilities (`npm audit` / `pnpm audit`), API study (read the package's types in `node_modules` or its official docs) come before this file is edited. Prefer platform built-ins (`fetch`, `node:test`, `util.parseArgs`, `node:crypto`, `structuredClone`, `AbortSignal`, `--env-file`) first. Never install a package name suggested from memory without checking registry age, downloads, repository link and publisher (typosquat/slopsquat risk).
- Do not hand-write versions from memory: resolve them from the registry and keep the lockfile in the same change as the manifest.
- Use the project's package manager (lockfile + `packageManager` field). Never mix managers; never run an install/update unprompted.
- `"type": "module"` set explicitly. `private: true` for anything not published. `engines.node` lists the supported lines (never an EOL line); `packageManager` pinned.
- Libraries: `exports` is the only public entry map; condition order is `types` first, then `import`/`require`/`module-sync`, `default` last (key order is priority). `files` allowlist so the tarball holds dist plus metadata only (verify with `npm pack --dry-run`). `sideEffects: false` only when true. Never publish `.ts` as the entry (Node refuses TypeScript under `node_modules`). ESM-only is the default; dual ESM/CJS only for consumers that need it, as a thin wrapper over one implementation, checked with `attw` and `publint` when the project has them.
- `repository.url` exact (trusted publishing matches it).
- Internal imports through `"imports": {"#internal/*": ...}` rather than TS-only `paths`.
- Lifecycle scripts of dependencies: default-deny, allowlist exact packages and review every allowlist change. pnpm: the `allowBuilds`, `strictDepBuilds`, `blockExoticSubdeps`, `minimumReleaseAge`, `trustPolicy` settings live in `pnpm-workspace.yaml`, not `.npmrc` (verify names and defaults for the project's pnpm version in the pnpm settings docs before adding). npm: `ignore-scripts=true` in `.npmrc` plus explicit `npm rebuild <pkg>`.
- Never enable switches that turn off the protections (allow-all builds, disabling release-age cooldown globally); exclusions are by explicit package name with a reason.
- Workspaces: `workspace:*` for internal deps, catalogs for shared versions where the manager supports them, no cross-package relative imports (`../../other/src`).
- Overrides/resolutions are a documented exception list, not a way to hide audit findings.
- CI installs frozen (`pnpm install --frozen-lockfile` / `npm ci`). Do not `npx`/`dlx` unpinned remote packages.
