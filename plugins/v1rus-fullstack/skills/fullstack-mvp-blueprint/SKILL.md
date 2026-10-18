---
name: fullstack-mvp-blueprint
description: "The /mvp-init MVP blueprint for a TypeScript fullstack repository holding a NestJS backend and a Next.js web app: when one repository for both is the right answer and when it is not, the bootstrap route (workspace root first, then each app's own generator, and what of each generated template is removed), the MVP-sized apps/packages graph with the rule for when each deferred package appears, the baseline dependency set by role with no versions, root and per-app build configuration, the scaffold that proves the seam (contract package, one endpoint, one page rendering it, docker-compose infrastructure, env split), the first vertical slice as real working code across both runtimes, the facts the generated root CLAUDE.md must record, the verification command order, and the traps that break a fresh fullstack monorepo. Load when scaffolding a new NestJS plus Next.js repository from scratch, laying out a new workspace, or generating a new fullstack project's CLAUDE.md. Do NOT load to add a feature to an existing repository — that is fullstack-pipeline-profile — and do NOT load for a backend-only or frontend-only project, where v1rus-node:node-mvp-blueprint or v1rus-react:web-mvp-blueprint applies."
---

# MVP blueprint — TypeScript fullstack (NestJS + Next.js)

The technology half of `/mvp-init` for a repository holding **both** halves: the command owns the
process, this file owns what the repository *is* at hour zero. Everything inside one app is the
single-stack blueprint's — **`v1rus-node:node-mvp-blueprint`** for the backend,
**`v1rus-react:web-mvp-blueprint`** for the frontend. This file owns the root, the packages, the
seam, and the order the three are created in. How to work in the result afterwards is
`fullstack-pipeline-profile`.

## 1. Stack identity

This layer when the brief says: **a web product with its own backend**, one team, TypeScript on
both sides, both halves shipping on the same cadence. The single repository is worth its overhead
for exactly one reason — the contract between the halves becomes a compile-time artifact instead of
a document — so it is the right answer when that contract will change often, which for a new
product it will.

| Anti-signal | Go to |
|---|---|
| Backend only — an API, a worker, a service with no web UI in this repo | `v1rus-node:node-mvp-blueprint` |
| Frontend only, against an API owned by another team or another repository | `v1rus-react:web-mvp-blueprint` |
| The backend is not TypeScript | frontend-only repository + a generated client from the API's specification (`api-contract`) |
| A mobile app is the primary client | the mobile layer; a web admin panel may still live with the backend here |
| Several independent products sharing nothing but a login | separate repositories — a monorepo with no shared contract is only overhead |

## 2. Bootstrap route

**Root first, then the apps.** Creating an app first and a workspace around it afterwards means
undoing an install: each generator writes its own lockfile and often its own git repository.

```
1. mkdir <repo> && git init
2. root package.json: "private": true, the package-manager pin, the standard script verbs
3. pnpm-workspace.yaml: packages: ["apps/*", "packages/*", "e2e"]
4. tsconfig.base.json, .gitignore, .editorconfig, docker-compose.yml
5. generate apps/api  (the Nest CLI, per v1rus-node:node-mvp-blueprint)
6. generate apps/web  (the Next generator, per v1rus-react:web-mvp-blueprint)
7. hand-write packages/contracts and packages/config — no generator, they are a few files
8. install once, from the root
9. turbo.json, then the scaffold (§6) and the slice (§7)
```

After each generator runs, **remove what it assumed about being alone**:

| Remove from a generated app | Why |
|---|---|
| its lockfile | one lockfile, at the root (`rules/workspace.md`) |
| its `.git` directory | the repository already exists |
| its standalone compiler config values that the base now owns | `tsconfig.json` extends `tsconfig.base.json` and overrides only what is app-specific |
| its own lint and formatter config, if `packages/config` supplies one | two configurations in one repository disagree eventually |
| the sample/demo route, controller, page and their tests | they fail the first lint or test run against code nobody intends to keep |

Kept and edited in place: the app's `package.json` (add `"private": true`, align the script verbs),
its framework configuration, its platform files.

**Toolchain missing.** If the package manager or the required runtime is not available, do not
install it and never use `sudo`. Say so in one line, hand the developer the exact commands for
their own terminal, and continue with everything that does not need the toolchain — the plan, the
root `CLAUDE.md`, and the file contents to write once the tree exists.

## 3. Module graph at MVP size

```
apps/
  api/            NestJS service
  web/            Next.js app
packages/
  contracts/      payload schemas, inferred types, route descriptors, the shared error body
  config/         tsconfig / lint / formatter / test presets
e2e/              Playwright suite (created with the first slice, not later)
docker-compose.yml   database (+ cache only if the brief needs one)
turbo.json  pnpm-workspace.yaml  tsconfig.base.json
```

Two apps and two packages. `packages/contracts` exists **from the first endpoint** — it is the
reason for the repository shape, and retrofitting it means unpicking duplicated types out of both
apps.

| Deferred | Created when |
|---|---|
| `packages/ui` | a second front-end exists — not for "we might have an admin panel" |
| `packages/core` (shared pure logic) | the second consumer of the same function, and only if it is not contract semantics |
| a worker / jobs app | the first task that must outlive a request (`v1rus-node:node-background-jobs`) |
| a second frontend (admin) | the brief actually names it as MVP scope |
| cache service in compose | the first thing genuinely worth caching |
| remote build cache | the local one stops paying off — usually when CI time hurts |
| Dockerfiles per app | the first real deployment; local development does not need the apps containerised |
| API versioning, a public specification document | the first consumer outside this repository |

Everything inside `apps/api` and `apps/web` is sized by their own blueprints; do not invent a
module layout for either here.

## 4. Baseline dependency set, by role

Names only. **Every version is resolved at plan time through the `v1rus-dependencies` gate** and
CVE-checked there — nothing is added from memory, and nothing is copied from a starter template.

| Role | Where | MVP |
|---|---|---|
| Package manager (workspaces) | pinned at the root | mandatory |
| Task runner with caching | root, dev | mandatory |
| TypeScript | root, one version for the workspace | mandatory |
| Linter + formatter | root / `packages/config`, dev | mandatory |
| Schema validation (the contract) | `packages/contracts` — a runtime validator with static type inference | mandatory; it is the contract mechanism |
| Backend framework and its runtime stack | `apps/api` — per `v1rus-node:node-mvp-blueprint` | mandatory |
| Frontend framework and its stack | `apps/web` — per `v1rus-react:web-mvp-blueprint` | mandatory |
| Browser e2e runner | `e2e`, dev | mandatory with the first slice |
| Unit test runner | per app, dev | infrastructure mandatory; whether tests are *written* is the complexity band's call (`v1rus-core:v1rus-qa`) |
| Database + migrations | `apps/api` per its blueprint; the service itself in `docker-compose` | mandatory once anything is stored |
| Auth | `apps/api` per its blueprint, with the seam rules from `fullstack-auth` | when the brief has users |
| Data fetching / caching client | `apps/web` per its blueprint | mandatory |
| Logging | per app, behind the app's own interface — `console.log` is banned (`v1rus-core:v1rus-logging`) | mandatory |

The shared toolchain is declared **once** for the workspace and referenced by every package, not
repeated per `package.json` (`monorepo-layout`).

## 5. Build configuration

| What | Where |
|---|---|
| Workspace membership | `pnpm-workspace.yaml` — `apps/*`, `packages/*`, `e2e` |
| Package manager and runtime pin | root `package.json`: `packageManager` and `engines` |
| Lockfile | one, at the root; CI installs with it frozen |
| Compiler baseline | `tsconfig.base.json`; each package extends it and overrides only what is its own |
| Task pipeline | `turbo.json`: `build` (`dependsOn: ["^build"]`, `outputs` declared), `typecheck`, `lint`, `test`, `e2e` (uncached), `dev` (persistent, uncached) — every task declaring the env it reads |
| Lint / format presets | `packages/config`, consumed by both apps |
| Local infrastructure | `docker-compose.yml`: database with a pinned image tag, explicit port, named volume — the same file CI uses |
| Environment | per app: `.env.example` committed, real `.env*` never; no root `.env` (`fullstack-configuration`) |
| API URL for the browser vs for the frontend's server process | two separate variables, from day one — collapsing them is a later migration |
| CI | one workflow: frozen install → lint + typecheck → build → test → e2e, with affected-package filtering |
| Origin topology | decide now: the web app proxies `/api/*` to the backend (preferred — first-party cookies, no CORS) or the two run on separate origins with CORS and an explicit allowlist |

## 6. App skeleton — the seam wired once

Every piece of the seam is exercised before feature work starts. Each app's internal skeleton is
its own blueprint's job; what follows is what connects them.

| Piece | Wires |
|---|---|
| `packages/contracts/src/index.ts` | the single public entry point; `common/error.ts` (the one error body, with machine-readable codes) and `common/pagination.ts` present from the start |
| The backend's validation boundary | the contract schema used as the request validator on the one endpoint, so the mechanism exists rather than being planned |
| The frontend's API client | one client that builds its URL from the contract's route descriptor, parses the response with the contract schema, and maps the error body — no hand-written path strings, no `as` onto a response |
| The frontend's **server-side** API client | the variant that forwards the incoming request's cookies on server-rendered calls (`fullstack-auth`) — present even before auth exists, because adding it later means auditing every call site |
| Environment modules | one per app, parsing its variables against a schema at startup and refusing to boot when it fails; the frontend's split into a public object and a server object (`fullstack-configuration`) |
| `docker-compose.yml` + migrations + a seed script | the database comes up, migrates and seeds with one command, locally and in CI |
| `e2e/` | the Playwright project, with the storage-state login helper stubbed for the moment auth arrives |
| CI workflow | the full order in §9, green on the scaffold |

## 7. The first vertical slice

One end-to-end feature crossing the whole seam, **real working code** — no `TODO`, no placeholder,
no mocked API. It proves the contract package, validation, the client, error mapping, rendering and
the e2e harness fit together, and it is the template every later feature is copied from.

**Which slice:** the simplest *list the primary entity* feature from the brief. With no obvious
candidate, a list of the app's main entity read from the database.

| Layer | What exists |
|---|---|
| `packages/contracts` | the entity schema, the list response schema, the route descriptor, the error body |
| `apps/api` | one module: controller validating with the contract schema, service, persistence with a migration and a seed, response shaped by the contract, its error path mapped to the shared error body |
| `apps/web` | one route rendering the list through the API client, with **loading, empty and error-with-retry states** all implemented, not sketched |
| Tests | a contract test parsing the real handler's response with the contract's schema; one e2e opening the page and asserting the seeded content appears. Written when the complexity band calls for them (`v1rus-core:v1rus-qa`); the states above are required either way |

If the brief has authentication in MVP scope, the slice is a **protected** list, so the cookie, the
server-side credential forwarding and the protected-route redirect are all exercised once, by real
code, instead of being designed later against a codebase that assumed neither.

## 8. Project `CLAUDE.md` inputs

The root `CLAUDE.md` is what every downstream plugin reads. It records:

| Fact | Value to record |
|---|---|
| Workspace | the package manager, the task runner, the app and package names and paths, and that there is one lockfile at the root |
| Contract mechanism | shared schema package (the default) or the alternative chosen, the package name, and the rule that a wire shape is declared only there |
| Shipping model | whether both halves always deploy together — it decides whether a single-step contract change is legal (`api-contract`) |
| Origin topology | one origin behind a proxy, sibling subdomains, or separate domains — plus the resulting cookie attributes |
| Commands | install, `dev` for each app, `build`, `typecheck`, `lint`, `test`, `e2e`, the compose up/down, migrate and seed commands, and the affected-filter invocation |
| Environment | which variables each app owns, which are public, where `.env.example` lives, and that a variable is added in four places (schema, example, task `env`, secret store) |
| Tests | per-app suites, where contract tests live, where the e2e suite lives, how it authenticates |
| Type names | the contract package's entry point, the shared error body and its code enum, the API client names (browser and server) |
| v1rus plugins to enable | `v1rus-core`, `v1rus-typescript`, `v1rus-node`, `v1rus-react`, `v1rus-fullstack` |

## 9. Verification

In this order — an earlier failure makes every later result a lie:

```
install, frozen lockfile, from the root
typecheck        whole workspace
lint             whole workspace
build            dependencies first
docker compose up   database, then migrate, then seed
test             both apps, contract tests included
e2e              both apps running, Playwright against them
```

| Then | Headless? |
|---|---|
| Both apps' production builds | yes |
| Both apps started and the slice's page fetched | yes — the real check that the seam is wired |
| A browser session driven by a developer | **developer** — hand over the exact dev command |

"Runnable" here means: `docker compose up`, both dev servers running, and the slice's page showing
the seeded list in a browser. The agent verifies through the e2e run and hands over the dev command
— it never claims the app runs on something it did not start. Full runs belong to the test-runner
agent of the half being verified.

## 10. Escalation targets

| Scaffold role | Agent |
|---|---|
| Workspace root, task pipeline, compiler baseline, `docker-compose`, CI workflow | `v1rus-node:node-engineer` — the backend half owns the infrastructure stack; there is no separate build agent on this stack |
| `packages/contracts`, `packages/config` | `v1rus-node:node-engineer` |
| `apps/api` in full | `v1rus-node:node-engineer` |
| `apps/web` in full, and `e2e/` | `v1rus-react:web-developer` |
| Verification runs | `v1rus-node:test-runner`, `v1rus-react:test-runner` |
| Floor when none is installed | `feature-developer` |

**This layer ships no engineer agent of its own** — a scaffold spanning two runtimes is better
built by the two specialists than by a generalist who is second-best at both. Order: root and
packages, then the backend, then the frontend. The contract package must exist and typecheck before
either app is wired to it, and the two app agents never edit it concurrently.

## 11. Known first-run traps

1. **An app generated before the workspace.** Each generator writes its own lockfile and git
   repository and assumes it owns its configuration. Create the root first; when an app is
   generated anyway, delete its lockfile and `.git`, and re-install once from the root — two
   lockfiles produce two dependency trees from the same commit, and the difference only shows up
   on someone else's machine.
2. **Undeclared task inputs.** A task with no declared `outputs` caches as "produced nothing" and a
   later run serves an empty build directory; a task that reads an environment variable it did not
   declare serves a build made with a different value. Neither errors — the wrong artifact simply
   ships. Declare both on every task, on the first day, while there are four of them.
3. **A secret with a public prefix.** A `NEXT_PUBLIC_`-style variable is inlined into JavaScript
   served to every visitor and frozen at build time. The prefix means publish. Set up the
   two-object environment split (public / server) in the scaffold, before anyone needs a shortcut.
4. **One variable for the API URL.** The browser and the frontend's own server process reach the
   backend at different addresses. Collapsing them into one variable works on a laptop, then forces
   either an internal hostname into the browser bundle or server traffic out through the public
   internet. Two variables from the first commit.
5. **A type declared on both sides "just to get started".** The duplicate compiles, agrees, and
   stops agreeing three weeks later without a single error. The contract package exists from the
   first endpoint for exactly this reason.
