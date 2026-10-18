# Hardening checklist

Names of settings were confirmed to exist in the pnpm settings docs (all live in `pnpm-workspace.yaml`, not `.npmrc`): `minimumReleaseAge`, `minimumReleaseAgeStrict`, `blockExoticSubdeps`, `strictDepBuilds`, `allowBuilds`, `trustPolicy`, `engineStrict`. Defaults and semantics changed between pnpm majors: read the docs for the project's pnpm version before editing, and do not assume a default.

- Lockfile committed; CI installs frozen.
- Dependency lifecycle scripts denied by default; allowlist reviewed per package.
- Release-age cooldown (a few days for production repos) so freshly published, possibly malicious versions are not picked up; exceptions by explicit name with a reason. The rationale (most malicious releases are pulled quickly) is an industry claim, not measured here.
- Block git/tarball URLs in transitive dependencies; consider the trust policy once the tree is clean.
- Audit in CI at high severity; triage, do not paper over with overrides. Add an OSV-based scan or an update bot if the org uses one.
- Publishing: from CI with npm trusted publishing (OIDC): needs a recent npm CLI, `id-token: write` permission, trusted publisher configured on npmjs.com with the exact workflow file, `repository.url` matching the repo. Check the npm docs for current minimum versions. Afterwards restrict token publishing and revoke old tokens.
- Verify what ships: `npm pack --dry-run`, `publint`, `attw`, `files` allowlist excludes tests and `.env`.
- Unused dependencies/exports: `knip` (exists on npm; run it via the project's script when present).
- CI hygiene: third-party Actions pinned to commit SHAs, minimal `permissions`, no secrets for fork PRs, publish job gated by an environment.
- Workspaces: `workspace:*`, shared catalogs, one lockfile, `pnpm -r`/`--filter` scripts, project references or `isolatedDeclarations` for parallel declaration builds.
