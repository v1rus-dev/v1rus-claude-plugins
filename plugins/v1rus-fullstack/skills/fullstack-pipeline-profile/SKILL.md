---
name: fullstack-pipeline-profile
description: "Stack profile that binds the stack-agnostic v1rus feature pipeline to a TypeScript fullstack repository holding a NestJS backend and a Next.js web app: the workspace vocabulary the architecture plan uses, the seam-specific plan sections and the contract-first order of work when one feature touches two runtimes, which convention skill owns which area across three layers, how the profile delegates each half to v1rus-node:node-pipeline-profile and v1rus-react:web-pipeline-profile instead of restating them, where tests live per app and where contract and e2e tests live, workspace-wide verification, the escalation split between node-engineer and web-developer, and what done means when only one half is implemented. Loaded by feature-architect, feature-designer, feature-developer, test-planner, test-writer and feature-finalizer when the pipeline detects a fullstack monorepo. Do NOT load for pipeline mechanics — gates, complexity bands, artifact names and commit discipline live in feature-pipeline — and do NOT load it in a repository holding only a backend or only a frontend, where the single-stack profile is the right one."
---

# Pipeline profile — TypeScript fullstack (NestJS + Next.js)

The pipeline agents (`feature-architect`, `feature-designer`, `feature-developer`, `test-planner`,
`test-writer`, `feature-finalizer`) are stack-agnostic. This profile is the **vocabulary of the
seam**: the workspace layout, what a plan must settle before either half is written, and who
implements which half.

Two boundaries:

- **Pipeline mechanics are not here.** Phase order, gates, complexity bands, artifact names, commit
  discipline and resume live in the `feature-pipeline` skill. This file never repeats them.
- **Each half's vocabulary is not here either.** This profile is a *composition*: for backend
  detail it defers to **`v1rus-node:node-pipeline-profile`**, for frontend detail to
  **`v1rus-react:web-pipeline-profile`**. Load this one first, then the one for the half being
  worked on. Restating either would be the copy that drifts.
- **The project still owns the names.** Real app names, script names and task names come from the
  target repository's own `CLAUDE.md`, its `package.json` files and its task-runner configuration.
  Read those first; never guess a command.

## 1. Stack identity

A single repository containing **both** a NestJS app and a Next.js app: a workspace manifest at the
root (`pnpm-workspace.yaml` or the `workspaces` field), one lockfile, a task-runner configuration
(`turbo.json` or equivalent), `apps/*` with a Nest app and a Next app, and a shared package both
import.

This profile applies **only** when both halves are in the repository. Backend only →
`v1rus-node:node-pipeline-profile`. Frontend only, consuming an API owned elsewhere →
`v1rus-react:web-pipeline-profile`. Both of those are also installed here and remain the right
profile for a task confined to one app; this one is for the seam and for anything that crosses it.

## 2. Workspace vocabulary

| Location | Holds |
|---|---|
| `apps/api/` | the NestJS service — internals per `v1rus-node:node-pipeline-profile` |
| `apps/web/` | the Next.js app — internals per `v1rus-react:web-pipeline-profile` |
| `packages/contracts/` | the API contract: payload schemas, inferred types, route descriptors, the shared error body. A leaf: no framework, no ORM types, no `process.env` |
| `packages/config/` | shared compiler, lint, formatter and test presets |
| `packages/ui/` | shared components, only where a second consumer exists |
| `e2e/` | Playwright suite driving both apps against real infrastructure |
| root | workspace manifest, one lockfile, task pipeline, `tsconfig.base.json`, `docker-compose` |

Hard boundaries: an app never imports another app; a package never imports an app;
`packages/contracts` depends on nothing in the workspace; each app owns its own environment and
there is no root `.env`. Detail: `monorepo-layout` and `${CLAUDE_PLUGIN_ROOT}/rules/workspace.md`.

## 3. `architecture-plan.md` — stack sections

A feature here spans two runtimes, so the plan is ordered **contract first**. Sections 3 and 4 are
not optional preambles to the interesting work: they are what makes the two halves implementable
independently.

```
## 3. Contract changes      (which payload schemas are added or changed in packages/contracts,
                            the route descriptors, the error codes, request vs response shapes,
                            and whether the change is breaking — with the additive-then-subtractive
                            sequence spelled out when it is)
## 4. Seam decisions        (auth: does this route need a session, is it read on the server or the
                            client; configuration: which new env var belongs to which app and
                            whether any of it is public; caching and revalidation across the seam)
## 5. Backend half          (per v1rus-node:node-pipeline-profile's own sections — module,
                            controller, service, persistence, migrations)
## 6. Frontend half         (per v1rus-react:web-pipeline-profile's own sections — route, server
                            versus client boundary, data fetching, state, UI states)
## 7. Verification plan     (which contract tests, whether an e2e is warranted, seed data needed)
```

Self-questions the plan must answer on this stack:

- Is every shape crossing the wire declared **once**, in `packages/contracts`? Any type declared on
  both sides, or any `as` onto a response, is a finding in the plan, not a detail for review.
- Is the contract change breaking, and if so does the plan sequence it so the repository typechecks
  after **every** commit, not only after the last one?
- Do the two halves ship together, or can one deploy first? That answer decides whether a
  single-step contract change is legal (`api-contract`).
- Does anything new read the session? If so, is it read in middleware, in a server component, or in
  the browser — and does the server-side path forward the credential explicitly?
- Does a new environment variable exist, and is it in the right app, the right schema, the right
  `.env.example` and the task's `env` list?
- Does anything in the frontend now need a value that is only safe on the server?

## 4. Convention skills by area

| Area | Skill |
|---|---|
| workspace layout, package boundaries, task pipeline | `monorepo-layout` |
| the shared contract, breaking changes, DTO ownership | `api-contract` |
| session across the seam, cookies, refresh, logout | `fullstack-auth` |
| environment split, public versus secret, startup validation | `fullstack-configuration` |
| contract tests, e2e, seeding, CI order | `fullstack-verification` |
| everything inside the backend | `v1rus-node:*` — start from `node-pipeline-profile` |
| everything inside the frontend | `v1rus-react:*` — start from `web-pipeline-profile` |
| language-level typing, validation, async, errors | `v1rus-typescript:*` |

Name the applicable ones in the plan so the implementing agent invokes them. If a skill is absent
in the current environment, proceed — never hard-depend on one.

## 5. Presentation pattern

Owned by the halves, not by the seam: the backend's module/controller/service shape is
`v1rus-node:nest-architecture`, the frontend's server/client component split and state holders are
`v1rus-react:web-architecture` and `v1rus-react:react-state-management`.

What the seam fixes: **the frontend never re-declares a backend shape**, and a response is *parsed*
with the contract schema rather than asserted into a type. The boundary between "data the server
rendered" and "data the client fetched" is a frontend decision, but both use the same contract.

## 6. Design-spec mapping (feature-designer)

Unchanged from the frontend layer — map the design onto the web app's design system per
`v1rus-react:web-ui-conventions` and `v1rus-react:web-styling`. The seam contributes exactly one
thing: a design implies data, and the data it implies must exist in the contract. If the mockup
shows a field the API does not return, that is a contract change in section 3 of the plan, not a
frontend workaround.

## 7. Tests

| What | Where | With |
|---|---|---|
| Backend unit / integration | `apps/api` | per `v1rus-node:node-testing` |
| Frontend unit / component | `apps/web` | per `v1rus-react:web-testing` |
| **Contract tests** | `apps/api`, against the real handler and a test database | the response and error schemas from `packages/contracts` |
| **e2e** | `e2e/` | Playwright against both apps, real database, storage-state login |

Out of scope for the seam: re-testing a business rule through the browser that a backend
integration test already covers. Detail and the seeding/reset discipline: `fullstack-verification`.
Whether tests are written at all is the complexity band's call (`v1rus-core:v1rus-qa`).

## 8. Verification

In this order — an earlier failure makes every later result a lie:

1. **Install with a frozen lockfile**, from the repository root.
2. **`typecheck` over the whole workspace**, not just the changed app. This is the gate that sees a
   contract break on the side nobody edited; running it only on the touched app defeats the entire
   arrangement.
3. **`lint`** on the affected set.
4. **`build`**, with dependencies built first.
5. **Tests** on the affected set, contract tests included.
6. **e2e** when both halves changed or the seam did.

Full runs belong to the test-runner agent of the half being verified
(`v1rus-node:test-runner`, `v1rus-react:test-runner`); workspace-wide tasks run from the root
through the task runner. Commands come from the project's `CLAUDE.md`. Never read `node_modules/`,
`.turbo/`, `.next/` or `dist/`.

## 9. Implementation escalation targets

**This layer ships no engineer agent.** A fullstack feature is two pieces of work in two runtimes,
and an agent that owns both would be worse at each than the specialist that owns one.

| Half | Agent |
|---|---|
| `packages/contracts`, and the backend: modules, controllers, services, persistence, migrations, config | `v1rus-node:node-engineer` |
| `apps/web`: routes, server and client components, data fetching, state, UI | `v1rus-react:web-developer` |
| Workspace files (`turbo.json`, workspace manifest, `tsconfig.base.json`, `docker-compose`) | whichever half the change serves; `v1rus-node:node-engineer` by default, since the backend half owns the contract package and the infrastructure stack |
| `e2e/` | `v1rus-react:web-developer` — it drives a browser |
| Floor when neither is installed | `feature-developer` |

**Order of work is fixed: contract, then backend, then frontend.**

1. The contract package changes first, in one commit, and the workspace typechecks (the frontend
   will show errors where it must now adapt — that is the change being visible, not a break).
2. `v1rus-node:node-engineer` implements the backend half against the contract, with its contract
   tests. The half is verifiable on its own: the endpoint returns a response that parses.
3. `v1rus-react:web-developer` implements the frontend half against the same contract. It does not
   wait for the backend to be deployed — it waits for the contract, which already exists.

Steps 2 and 3 can run in parallel **only** when step 1 is committed and both agents are told the
contract is frozen for this task. If either needs the contract changed mid-flight, it stops and the
contract changes once, centrally — two agents editing `packages/contracts` concurrently is how the
single source of truth becomes two.

`packages/contracts`, the workspace files and each app's `.env.example` are touched by both halves
in principle; in practice the contract belongs to step 1 and the rest to the half that needs it.
Never both in parallel.

**"Done" with one half finished.** A completed backend half is a *milestone*, not a completed
feature: the acceptance criteria are user-visible, and a user cannot see an endpoint. Report it as
what it is — "backend half implemented and contract-tested; frontend half outstanding" — and leave
the task open. The two states that are legitimately shippable alone are (a) a contract-only commit,
which is inert by design, and (b) a backend half behind a contract nothing consumes yet, when the
plan deliberately split delivery. Both must say so in the plan up front. What is never acceptable
is a frontend half wired to an endpoint that does not exist yet, or a report that calls the feature
complete because every test that exists passes — the missing half has no tests, so a green run
proves nothing about it.

## 10. Finalizer stack checklist

On top of the generic cleanup:

- No shape declared twice — no frontend interface mirroring a contract type, no `as` or `any` over
  a response.
- The contract package is still a leaf: no framework, ORM, Node built-in or `process.env` import
  crept in.
- No app imports another app; every new cross-package import is declared in that package's
  `package.json` as `workspace:*`.
- Every new environment variable is in its app's schema, its `.env.example` and the task's `env`
  list; no secret gained a client-exposed prefix.
- New tasks declare `outputs` and `env`; nothing long-running became a dependency of another task.
- Session handling: server-side calls forward the credential, no attempt to set a cookie during a
  render, refresh is single-flight, logout clears server session, both cookies and the client
  caches.
- Where the complexity band calls for tests at all (`v1rus-core:v1rus-qa`, §7), contract tests
  exist for every endpoint the frontend consumes, including the error body.
- Workspace-wide typecheck and lint are clean, from the root, not per app.

## 11. Typical expert reviews to flag

`security-expert` for anything touching auth, cookies, CORS, the public/secret split or a new
`NEXT_PUBLIC_`-style variable — mandatory on this stack, because the seam is where a secret leaks;
`architecture-expert` when a new package appears, a boundary changes, or the contract mechanism
itself is revisited; `performance-expert` for a new server-rendered data path, an N+1 behind a new
endpoint, or a payload that grew; `ux-expert` for a new screen or navigation change, per the
frontend layer.
