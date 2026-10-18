---
name: monorepo-layout
description: "The v1rus TypeScript monorepo shape where a NestJS backend and a Next.js web app share one repository: pnpm workspaces plus Turborepo, apps/* versus packages/*, which package may depend on which and why an app never imports another app, when a shared package is created and when the code stays in the app, the task pipeline and what makes its cache correct, the single lockfile, and one toolchain version across the workspace. Also the front door to rules/workspace.md for package.json, turbo.json, pnpm-workspace.yaml, tsconfig.base.json, .env and docker-compose edits. Load when laying out or restructuring a fullstack repository, adding an app or a shared package, deciding where shared code belongs, wiring or debugging Turborepo tasks and caching, or reviewing a cross-package import. Do NOT load for what goes inside one app — module structure inside the backend is v1rus-node:nest-architecture, inside the web app v1rus-react:web-architecture, and how a single publishable package is organised internally is v1rus-typescript:ts-package-structure."
---

# Monorepo layout

One repository, two deployables, one install. The whole point of the arrangement is that a change to
the contract between them is a **single commit that both sides typecheck against**. Everything below
protects that property; nothing else justifies the extra moving parts.

The file-level rules — what must be right inside `package.json`, `turbo.json`, `pnpm-workspace.yaml`,
`tsconfig.base.json`, `.env*` and `docker-compose*.yml` — are in
`${CLAUDE_PLUGIN_ROOT}/rules/workspace.md`, injected automatically by this plugin's `path-rules`
hook before any edit to those files. Read it directly when reviewing, since a review triggers no
injection. This skill is the shape and the reasoning; that file is the checklist.

## Layout

```
apps/
  api/            NestJS service          — v1rus-node owns its insides
  web/            Next.js app             — v1rus-react owns its insides
packages/
  contracts/      the API contract: schemas, inferred types, route descriptors  (leaf — depends on nothing local)
  config/         shared tsconfig / lint / formatter / test presets             (leaf)
  ui/             shared React components — only once a second consumer exists
e2e/              Playwright suite driving the real api + web together
turbo.json        task pipeline
pnpm-workspace.yaml
tsconfig.base.json
docker-compose.yml   local + CI infrastructure (database, cache), not the apps
```

`apps/*` are **deployables**: they have an entry point, an environment, a runtime. `packages/*` are
**libraries**: no environment reading, no side effects at import, no server start. A package that
reads `process.env` at module scope has become an app with no deployment.

Tooling is chosen per repo, not per developer: **pnpm workspaces** for the install graph, **Turborepo**
for the task graph. A project may run a different equivalent (its own `CLAUDE.md` wins) — the rules
below are about the graph, not the tool.

## Dependency rules

```
apps/api ──▶ packages/contracts ◀── apps/web
   │              (leaf)              │
   └──▶ packages/config ◀─────────────┘
                              e2e ──▶ packages/contracts
```

- **An app never imports another app.** Not a type, not a constant, not "just this one util". Two
  apps that import each other cannot be built, deployed or scaled separately, which is the only
  reason they are separate apps. Anything both need moves into a package — and if it cannot move
  because it is server-only or React-only, it was not shared code, it was a missing contract.
- **A package never imports an app.** The arrow only points from deployable to library.
- **`packages/contracts` depends on nothing in the workspace.** It is the one module both runtimes
  load, so anything it pulls in is pulled into both — including the browser bundle. No Nest, no
  React, no Node built-ins, no ORM types. It is a leaf and stays a leaf.
- **No cycles between packages.** A cycle makes build ordering undefined and the cache wrong.
- **Depth over breadth is not a virtue.** Prefer two packages with a clear direction to one package
  with a `server/` and a `client/` folder — the folder split is not enforced by anything, the
  package boundary is.
- Every cross-package import corresponds to a dependency entry in the importing package's own
  `package.json`, referenced as `workspace:*`. Resolution that works because of hoisting is
  accidental.

## When a shared package is created

Extracting too early is as expensive as extracting too late: an extra package is an extra build
edge, an extra version of the truth in review, and an extra place to look.

| Situation | Where it goes |
|---|---|
| A shape crosses the wire between api and web | `packages/contracts` — always, from the first endpoint |
| A tsconfig / lint / formatter preset both apps use | `packages/config` |
| A pure function both apps need (formatting, a shared calculation) | `packages/contracts` if it belongs to the contract's semantics, otherwise a small `packages/core` — created at the **second** consumer, not the first |
| A React component used by two front-ends | `packages/ui` — created when the second front-end exists, not in anticipation of it |
| Something only the backend needs | stays in `apps/api` |
| Something only the web app needs | stays in `apps/web` |

A package created for a single consumer is a folder with extra ceremony. Move it out when the second
consumer appears; that move is cheap precisely because the boundary rules above were kept.

## Adding a package — checklist

1. Directory under `apps/` or `packages/` covered by the `packages:` globs in `pnpm-workspace.yaml`.
   The one exception already in the layout is `e2e/`, which sits at the workspace root because it
   belongs to neither side of the seam — it is in the globs like any other workspace package.
2. `package.json`: the workspace-scoped name, `"private": true`, the standard script verbs
   (`build`, `lint`, `typecheck`, `test`), and every dependency it actually imports.
3. `tsconfig.json` extending `tsconfig.base.json`, overriding only what is package-specific.
4. A single public entry point. Consumers import the package, never a deep path into its `src`.
5. Declare it in the consumers' `package.json` as `workspace:*` and install from the root.
6. If it has build outputs, declare them in `turbo.json` so the cache is not a lie.

## Task pipeline

The task graph mirrors the dependency graph. What matters is that a task is correct **when it is
skipped**, which is most of the time.

- `build` depends on `^build` — a package's dependencies build first. Omitting this works until the
  cache is cold, then fails in CI only.
- `typecheck` is a first-class task, not a side effect of `build`. It is the gate that catches a
  contract change on both sides at once, and it must run even for an app whose build is cached.
- `lint` and `typecheck` have no dependency on `build` unless the package consumes generated
  artifacts; keeping them independent is what lets CI run them in parallel with the build.
- `test` depends on `^build`; `e2e` depends on both apps' `build` and is not cached (it needs a
  database and a running server — see the `fullstack-verification` skill).
- `dev` is `persistent` and uncached, and is never something another task depends on.
- Filtering by what changed (`--filter=...[<base ref>]`) is how a PR touching one app runs one app's
  tasks. It is also why the contract package matters: a change there marks **both** apps affected,
  automatically, which is exactly the blast radius you want to see in CI.
- Declared `outputs` and declared `env` per task are what make all of the above true rather than
  hopeful. Both are in `rules/workspace.md`.

## One toolchain, one version

TypeScript, the linter, the formatter, the test runner and the package manager exist **once** for
the workspace, referenced by every package rather than versioned per package. Two TypeScript
versions in one repo produce errors that reproduce in one package and not the other, and a review
cannot see it. The runtime version (Node) and the package-manager version are pinned in the repo so
CI and every laptop agree; which versions those are is resolved through the `v1rus-dependencies`
gate, never copied from a template.

The language-level configuration of those tools — what the compiler flags should be, how strict the
lint set is — belongs to `v1rus-typescript:ts-project-config` and
`v1rus-typescript:ts-lint-and-format`. This skill only says there is exactly one of each.

## Related

`api-contract` (what lives in `packages/contracts` and how it stays the single source of truth),
`fullstack-configuration` (which environment variable belongs to which app),
`fullstack-verification` (what runs per app and what runs for the whole repo),
`v1rus-node:nest-architecture` and `v1rus-react:web-architecture` (inside each app),
`v1rus-typescript:ts-package-structure` (inside a single package).
