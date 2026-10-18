---
name: web-testing
description: "How tests are written and run in a v1rus web app: Vitest plus Testing Library for components with queries by role and label rather than test ids or class names, user-event instead of fireEvent, MSW to stub the network at the boundary so the real fetch layer is exercised, what a server component can and cannot be unit tested with and where that logic goes instead, Playwright for browser flows with role locators and web-first assertions and no arbitrary waits, an axe assertion as the cheap accessibility floor, and what not to snapshot. Load when writing or fixing tests for React or Next code, testing a component or a hook, adding an end-to-end flow, or when a change breaks existing tests."
---

# Web Testing

**Whether tests are written at all is decided by the complexity band, not here** — see
`v1rus-core:v1rus-qa` (tests from complexity 7 upward; below that verification is build + static
analysis + the quality gate). This skill covers *how* they are written when warranted.

**Default stack: Vitest + Testing Library + `user-event` + MSW for components and hooks; Playwright for
browser flows.** Read the project's `CLAUDE.md` for the actual script names — never invent a command.

## What is tested where

| Subject | Tool |
|---|---|
| Pure logic, schemas, mappers, reducers, formatting | Vitest, no DOM — the cheapest and most valuable tests |
| A client component's behaviour and accessible output | Vitest + Testing Library |
| A custom hook in isolation | Testing Library's hook renderer |
| A server component, a route handler, middleware, a server action | its **extracted logic** in a unit test; the rendered result in Playwright |
| A user flow across routes, auth, real navigation | Playwright |

**Server components are not renderable by Testing Library** (they are async and run in the server
environment). Do not fight it: put the logic worth testing — the fetcher, the schema, the mapper, the
authorisation decision — in a plain module, unit-test that, and cover the rendered page in Playwright.
A route handler is testable directly by calling it with a `Request` and asserting the `Response`.

## Component tests

- **Test what the user perceives**, not the implementation: rendered text, roles, enabled/disabled,
  what happens after an interaction. Never assert on state variables, hook call counts, or internal
  props.
- **Query priority**: `getByRole` (with the accessible name) → `getByLabelText` → `getByText` →
  `getByTestId` as a last resort. A component that cannot be found by role usually has an accessibility
  bug, so the query priority is a design check as much as a testing one (`web-ui-conventions`).
- Never query by class name, DOM structure or a CSS selector — those break on a styling change that
  changed nothing the user sees.
- **`user-event`, not `fireEvent`.** It dispatches the real sequence (pointer, focus, keydown, input),
  so a control that only works with a synthetic click is caught here.
- Use `findBy*` / `waitFor` for anything async; never a fixed `setTimeout`. `waitFor` asserts, it does
  not sleep.
- Assert the **states that matter**: loading shows a skeleton, empty shows the empty copy, error shows a
  retry **and** the way back, content shows the items. That mirrors the screen-state checklist, so a
  missing state fails a test instead of reaching review.
- Add an `axe` assertion to component tests for anything non-trivial — it catches the mechanical half
  (missing label, bad contrast in markup, invalid ARIA) for almost no effort. It does not catch focus
  order or a keyboard trap; those need a keyboard pass.
- Wrap in the providers the component really needs (theme, i18n, a fresh query client per test) through
  one shared `renderWithProviders` helper — a query client shared between tests leaks cache and makes
  failures order-dependent.

## Network

- **Stub at the network boundary with MSW**, not by mocking the fetch module or the query hook. Mocking
  the hook tests the mock; stubbing the transport exercises the real fetcher, the real schema validation
  and the real error mapping — which is where the bugs are.
- Handlers live in one place and are overridden per test for the error and empty cases. **Cover the
  failure path for every load**: a suite with only happy paths tests nothing that breaks in production.
- Assert the request where it matters (the right body, the right query) — a mutation that silently sends
  the wrong payload passes every render assertion.

## Playwright

- One spec per flow, not per page: sign in → create → see it in the list → edit → sign out.
- **Locate by role and accessible name** (`getByRole("button", { name: ... })`); fall back to a stable
  `data-testid` only where no accessible name exists — and treat that as a hint that the UI needs one.
- **Web-first assertions only** (`await expect(locator).toBeVisible()`); never `waitForTimeout`, never a
  manual sleep. Auto-waiting is the point of the tool.
- Tests are independent and can run in parallel: each seeds and cleans its own data, and authentication
  is reused via a stored session state rather than driving the login form in every spec.
- Keep the surface small — a browser suite is the slowest and flakiest thing in CI. Cover the critical
  paths and the states that only exist in a real browser (real navigation, focus after navigation,
  streaming, a service worker); leave the rest to component tests.
- On failure, keep the trace and the screenshot; a flaky spec is fixed or quarantined with a tracked
  issue, never re-run until green (`v1rus-core:v1rus-qa` § 4).

## Naming and layout

- Test files sit next to the source (`OrderRow.tsx` → `OrderRow.test.tsx`) or under a mirrored `tests/`
  tree — follow what the project already does. Browser specs live in their own directory (`e2e/`).
- One `describe` per unit, one test per behaviour, named for the behaviour:
  `shows the retry action when the request fails`.

## What not to do

- **No snapshot of a whole component tree.** It fails on every cosmetic change, tells you nothing about
  what broke, and gets regenerated without being read. A small, intentional snapshot of a pure
  serialisable value is fine.
- Do not test the framework or the library — that a `Link` navigates or a query hook caches is not your
  test.
- Do not add a test that only exercises a move, a rename or a repackaging with no behaviour change
  (`v1rus-core:v1rus-qa` § 1).

## Running

Read the project's scripts for the exact commands; the usual shape is a unit run, a watch run, a typecheck
and a browser run, plus lint. Scope the run to the change (`v1rus-core:check`): a logic change runs the
affected tests, a rename or a comment edit needs a typecheck only. Long runs go to the
`v1rus-react:test-runner` agent so a full suite does not consume the orchestrating session's context.

## Non-negotiable

Whoever breaks an existing test fixes it in the same change. A `.skip` / `.todo` without a tracked-issue
reference is forbidden, and a red suite is never merged — `v1rus-core:v1rus-qa` § 4.
