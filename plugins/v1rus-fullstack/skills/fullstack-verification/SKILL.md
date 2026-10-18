---
name: fullstack-verification
description: "Verifying the seam between a NestJS backend and a Next.js frontend: contract tests that assert the real handler's output parses against the shared response schema, Playwright e2e driving the real web app against a real backend and a real database, seeding and resetting state deterministically, authenticating e2e once through the API instead of the login form, what runs per app versus what runs only for the whole repository, and the CI task order with affected-package filtering. Load when setting up or fixing e2e, deciding where a cross-app behaviour should be tested, an e2e suite is flaky or order-dependent, a change passed both apps' tests and still broke in production, or wiring the repository's CI pipeline. Do NOT load for unit and integration tests inside one app (v1rus-node:node-testing, v1rus-react:web-testing) or for how much testing a change deserves at all (v1rus-core:v1rus-qa owns the complexity bands)."
---

# Verification across the seam

Both apps can be green and the product still broken — that is the defect class this file is about.
Each app's own tests mock the other side, so they verify that each app is consistent with its
*belief* about the contract. Only three things check the belief itself: workspace-wide typecheck,
contract tests, and e2e.

**How much of this a given change deserves is not decided here.** The complexity bands in
`v1rus-core:v1rus-qa` decide whether tests are written at all; this skill says what the tests are
and where they live when they are.

## The layers, cheapest first

| Layer | Runs | Catches | Owner |
|---|---|---|---|
| `typecheck`, whole workspace | every change | a contract shape that one side no longer satisfies | `api-contract` |
| Unit / integration, per app | per app, mocked at the boundary | that app's own logic | `v1rus-node:node-testing`, `v1rus-react:web-testing` |
| **Contract tests** | in the backend, against the real handler | what the handler *actually* returns after the ORM, serializers and interceptors | here |
| **e2e** | repository level, real stack | routing, auth, cookies, hydration, the things only a browser does | here |

Push a check down whenever it fits: an assertion that holds in a contract test does not need an
e2e, and an e2e that only exercises one app's logic belongs in that app's suite. e2e is the most
expensive and the most fragile layer — spend it on flows that genuinely cross the seam.

## Contract tests

A contract test calls the backend's real endpoint — through the HTTP layer, with the real
serialization path, against a real (test) database — and **parses the response with the schema from
`packages/contracts`**. It asserts nothing about business values; it asserts the shape is the one
both sides were compiled against.

It exists because the typechecker sees the *declared* return type and the network sees the actual
bytes, and the gap between them is where these bugs live:

- a `Date` object that the declared type calls a string and JSON serialises differently than the
  contract says,
- a relation the ORM eagerly included, adding a field the contract does not know,
- `null` where the schema says the key is absent, or absent where it says nullable,
- a numeric id serialised as a number on one route and a string on another,
- a field an interceptor stripped after the handler returned it.

Rules: one per endpoint that the web app consumes, including the error body (provoke the failure,
parse the error response with the error schema). Request payloads get the mirror check — the
frontend's request builder output parses against the request schema. Keep them in the backend's
test suite so they run with its database, and make the contract package the only source of the
schemas they use; a contract test that re-declares the shape tests nothing.

## e2e

**Real backend, real database, real browser.** An e2e against a mocked API is a slower unit test of
the frontend and gives false confidence about exactly the seam it is supposed to cover. It lives in
its own workspace package (`e2e/`), depends on `packages/contracts`, and depends on neither app's
source.

- **Authenticate through the API, once.** A setup step logs in with an HTTP request, saves the
  resulting storage state (cookies included), and every test reuses it. Driving the login form in
  every test multiplies the slowest, most brittle flow by the size of the suite. Keep exactly one
  test that drives the real login form, because that flow also needs covering — once.
- **Cover what only a browser can show:** navigation and redirects, the protected-route gate,
  session expiry and refresh mid-session, logout clearing everything (`fullstack-auth`), server
  rendering producing the same result as the client, a form round-tripping through a real
  validation error from the backend.
- **Do not re-test business rules** that a backend integration test already covers. The question
  an e2e answers is "do the two halves fit", not "is the calculation right".
- **Wait for the application's own signals** — a visible element, a settled request — never a fixed
  sleep. Time-based waiting is how a suite becomes flaky on a slower CI machine and then gets
  disabled.
- A skipped or quarantined e2e needs a tracked issue in the annotation, per `v1rus-core:v1rus-qa`.
  A silently skipped test is worse than a missing one: it reports green.

## Seeding and resetting

Determinism here is the whole ballgame; almost every "flaky e2e" is shared state.

- **A dedicated test database**, never the development one. It comes from the same
  `docker-compose` stack CI uses, so a laptop reproduces a CI failure.
- **Migrations run, then a seed script runs.** The seed is owned by the backend package (it knows
  the schema), is deterministic — fixed ids, fixed timestamps, no randomness, no "today" — and is
  the same script locally and in CI.
- **Reset between runs, not between assertions.** Truncate and re-seed before the suite; for
  parallel workers, give each worker its own database or schema rather than trying to make tests
  share one safely.
- **A test creates the data it needs, through the API,** and does not depend on another test having
  run. If two tests must run in order, they are one test.
- Fixed clock and fixed locale/timezone for the whole suite, or a date-formatting assertion passes
  in one region and fails in another.

## What runs where

| Scope | Tasks |
|---|---|
| Per app | `lint`, `typecheck`, `test`, `build` — via the task graph, so a PR touching one app runs one app |
| Per package | the same verbs; `packages/contracts` has no tests of its own beyond schema behaviour worth asserting |
| Whole repository only | `e2e`, and any check that needs both apps running at once |

A change to `packages/contracts` marks both apps affected in the task graph, so it pulls both apps'
tasks and the e2e suite into that PR without anyone deciding to — the reason the contract package
is a leaf both apps depend on.

## CI order

```
install (frozen lockfile)
  ├─ lint            (affected)         ┐ parallel
  └─ typecheck       (whole workspace)  ┘
build                (affected, ^build first)
unit + integration   (affected; contract tests run here, with the test database)
e2e                  (only when both apps are affected or on the main branch)
  start infrastructure (docker-compose) → migrate → seed → start api → start web → run Playwright
artifacts            (Playwright traces and reports on failure, always)
```

- **Frozen lockfile** on install: CI must fail on a lockfile that does not match the manifests
  rather than silently resolving something else.
- **`typecheck` runs over the whole workspace, not just the affected set.** It is cheap and it is
  the gate that sees a contract break on the side nobody touched.
- **e2e is not cached.** It depends on a database and a running server, which are not in the cache
  key. Marking it cacheable produces a green run that executed nothing.
- **Fail the job on the first gate that fails** — running e2e after a failed typecheck produces a
  wall of misleading errors.
- Always upload the failure artifacts. An e2e failure with no trace costs more to reproduce than
  it cost to run.

## Related

`api-contract` (the schemas the contract tests use, and the typecheck layer),
`fullstack-auth` (the storage-state login and the logout assertions),
`fullstack-configuration` (what CI supplies to which job),
`monorepo-layout` (the task graph and affected filtering),
`v1rus-core:v1rus-qa` (whether a change needs tests at all).
