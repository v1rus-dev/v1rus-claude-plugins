# v1rus-fullstack

The seam between a NestJS backend and a Next.js web app **in one repository**. Depends on
`v1rus-node` and `v1rus-react`, so installing it pulls both halves and, through them,
`v1rus-typescript` and the corporate baseline in `v1rus-core`.

```
/plugin install v1rus-fullstack@v1rus
```

Install this only when both halves live in the same repository. A backend alone is `v1rus-node`;
a frontend alone, consuming an API owned elsewhere, is `v1rus-react`.

## What this layer owns

It is deliberately small. A rule lives on the highest layer where it is still true, and almost
everything about writing a Nest module, a React component or a TypeScript type is true one layer
down. What is left is what is untrue for either side alone — the seam.

| Concern | Decision |
|---|---|
| Workspace | pnpm workspaces + Turborepo; `apps/*` are deployables, `packages/*` are libraries, one lockfile at the root |
| Boundaries | an app never imports another app; a package never imports an app; `packages/contracts` is a leaf |
| **API contract** | **a shared schema package** — the backend validates with it, the frontend infers its types from it and parses responses with it. Declared once, never twice |
| Contract alternatives | OpenAPI + a generated client when there are consumers outside the repo or the backend is not TypeScript; end-to-end typed RPC only when the backend exists for this one frontend. Chosen once, per repository |
| Breaking changes | caught by workspace-wide `typecheck` first, contract tests second, e2e last; additive-then-subtractive sequencing when the halves can deploy independently |
| Session | HttpOnly cookie by default; `localStorage` is banned for the web client; bearer only for non-browser clients |
| Server rendering | the server must forward the credential explicitly, and cannot set a cookie during a render — refresh belongs in middleware |
| Refresh | single-flight, retry once, rotation with reuse detection and a short grace window for concurrent server fetches |
| Environment | each app owns its own `.env`; no root `.env`; a client-exposed prefix means *publish*; two variables for the API URL (browser vs server process) |
| Verification | contract tests in the backend against the real handler; Playwright at repo level against a real backend and a real database; workspace-wide typecheck always |
| Engineers | **none shipped here** — see below |

**No versions are pinned anywhere in this plugin.** Package names only; every version is resolved
at plan time through the `v1rus-dependencies` gate.

## Contents

| Component | What it covers |
|---|---|
| `skills/monorepo-layout` | `apps/*` vs `packages/*`, the dependency graph, when a shared package is created, the task pipeline and what makes its cache correct, one toolchain version. Also the front door to `rules/workspace.md` |
| `skills/api-contract` | The shared schema package, what it must never contain, route descriptors, the three options and when each wins, breaking-change sequencing, the three detection layers |
| `skills/fullstack-auth` | Cookie vs bearer, what the deployment topology does to cookie attributes, reading the session on the server, single-flight refresh, CSRF, a logout that clears both sides |
| `skills/fullstack-configuration` | Which variable belongs to which app, the public/secret line, the two-URL rule, startup validation, task-runner env declarations, the dev/CI/prod matrix |
| `skills/fullstack-verification` | Contract tests, Playwright against the real stack, seeding and resetting, per-app vs whole-repo scope, CI task order |
| `skills/fullstack-pipeline-profile` | Binds the feature pipeline to a fullstack repo: seam vocabulary, contract-first plan sections, which agent implements which half, what "done" means with one half finished |
| `skills/fullstack-mvp-blueprint` | The `/mvp-init` blueprint: root-before-apps bootstrap, the MVP-sized graph, the scaffold that proves the seam, the first vertical slice across both runtimes, the root `CLAUDE.md` |
| `rules/workspace.md` | Injected before editing `package.json`, `turbo.json`, `pnpm-workspace.yaml`, `tsconfig.base.json`, `.env*` or `docker-compose*.yml` |

## Why no engineer agents

This layer ships **no implementation agent**, and that is a decision rather than an omission.

A feature crossing the seam is two pieces of work in two runtimes. An agent owning both would be
strictly worse at each than the specialist that owns one, and it would need a copy of both layers'
conventions to function — the copy that drifts. So implementation escalates to
`v1rus-node:node-engineer` for the contract package and everything in `apps/api`, and to
`v1rus-react:web-developer` for `apps/web` and the e2e suite. Verification escalates to those
layers' `test-runner` agents. `fullstack-pipeline-profile` names the split and fixes the order of
work: contract, then backend, then frontend.

What this layer contributes to a fullstack feature is not labour but **sequencing and boundaries** —
which is exactly what the two specialists cannot supply, because neither can see the other's half.

## Design notes

**Why a shared schema package is the default contract.** The two properties that actually cost time
are that the contract is a hand-written artifact a reviewer can read in the diff, and that there is
no generation step between changing it and both sides seeing the change. A generated client adds a
step that is stale exactly when it matters; typed RPC removes the stable public surface, so the day
a second client appears the API has to be re-specified. The shared schema's cost is honest — the
schemas are maintained by hand, and the backend must map its persistence model rather than expose
it. Both alternatives are documented with the conditions under which they win, because sometimes
they do.

**Why the contract package is a leaf.** It is the one module loaded into both a browser bundle and
a server process, so anything it imports is pulled into both. Keeping it free of framework, ORM and
runtime imports is what lets both apps depend on it — and depending on it is what makes a contract
change mark both apps affected in the task graph, which is how CI notices a break nobody asked it
to look for.

**Why the seam needs an owner at all.** Each half's tests mock the other side, so both suites can
be green while the product is broken. Cookies that the browser attaches automatically are not
attached on a server-to-server fetch. A cookie cannot be set during a render. A client-exposed
environment prefix means publish, not "reachable from frontend code". None of these is visible from
inside one app, which is why they are collected here instead of half-stated in two places.

**Project overrides.** Everything here is the default, not a mandate: a project may specify a
different workspace tool, contract mechanism or topology in its own `CLAUDE.md`, and the project
wins. What the plugin guarantees is that the default is a coherent whole rather than per-developer
taste.
