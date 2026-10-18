---
name: web-data-fetching
description: "How a v1rus web app reads and writes server data: the default split between fetching in a server component and owning interactive server state in TanStack Query, never fetching in useEffect, query keys and staleness, invalidation after a mutation and optimistic updates that roll back, hydrating the query cache from the server instead of double-fetching, server actions versus route handlers for writes, avoiding request waterfalls with Promise.all and Suspense, propagating AbortSignal, and mapping a failed request to a screen state the user can act on. Load when adding a fetch, wiring a mutation, choosing between a server component and a query, fixing stale data after a save, or removing a loading waterfall. Do NOT load for where the resulting state lives (react-state-management) or for route-file mechanics (web-routing)."
---

# Data Fetching

## The default split

| Data | Fetch it |
|---|---|
| Needed for first paint, read-only on that screen | **server component** — `await` it in the page or section |
| Re-fetched, polled, paginated, mutated, or needed after a client interaction | **TanStack Query** in a client component |
| Written | **server action** (form or UI-triggered mutation) or a **route handler** (public/external API) |

Rule of thumb: if nothing in the browser will ever ask for it again, do not ship a query for it. If the
user can change it, the query library owns it — that is what gives you one cache, one invalidation
story, and no stale copies.

**Never fetch in `useEffect`.** It runs after paint (so the user sees an empty screen first), it races
on fast input changes, it re-runs under Strict Mode, it has no cache, no deduplication and no retry, and
it is the usual source of "the list shows the previous search's results".

## Server components

- Fetch where the data is used. Request-level deduplication collapses two calls for the same resource in
  one render pass, so a section may fetch its own data instead of receiving it through five prop layers.
- **Independent fetches run in parallel.** Two sequential `await`s are two round trips added together;
  `Promise.all` makes them one. A `map` with an `await` inside is an N+1 — batch it.
- A slow, independent section goes behind its own `<Suspense>` with a real skeleton so the rest of the
  page streams. That is also what makes `loading.tsx` a fallback of last resort rather than the whole
  page's loading strategy (`web-performance`).
- Caching and revalidation behaviour changed across Next majors — read the semantics for the version the
  project resolves and state the choice explicitly in the file rather than inheriting a default
  (`${CLAUDE_PLUGIN_ROOT}/rules/next-app-router.md`).
- The fetch layer lives in `features/<x>/api/`, not inline in the page: one place validates the response
  against the schema (`v1rus-typescript:ts-boundaries-validation`) and maps transport failures to the
  app's error type (`v1rus-typescript:ts-error-handling`). A raw `fetch(...).then(r => r.json())` in a
  page is an `any` crossing the boundary.

## TanStack Query

- **Query keys are structured and derived from the inputs**: `["orders", { status, page }]`. A key that
  omits an input serves the wrong cache entry; a hand-built string key ("orders-open-2") cannot be
  invalidated by prefix. Keep a per-feature key factory so the key exists in exactly one place.
- Set `staleTime` deliberately per query. The default refetches more than most screens need; a value that
  matches how fast the data actually changes removes most redundant traffic.
- `enabled` guards a query on a missing parameter instead of a fetcher that throws on `undefined`.
- Pass the query's `signal` into `fetch` so a superseded or unmounted query is actually cancelled
  (`v1rus-typescript:ts-async`).
- **Hydrate from the server** rather than fetching twice: prefetch on the server, dehydrate, and wrap the
  tree in the hydration boundary. Without it a server-rendered page shows content, then the client
  mounts and shows a spinner over the same data.
- Loading state: the first load renders the skeleton; a background refetch must not blank the screen —
  keep showing the previous data and show a subtle pending affordance
  (`placeholderData` / keep-previous on a paginated list, so pagination does not flash empty).
- The query client is created **once per app instance in a client provider**, never as a module-level
  singleton in a server-rendered app — a shared client leaks one user's cache into another's request.

## Mutations

- A mutation **invalidates what it changed**, by key prefix, in its success handler. "The user will
  refresh" is not invalidation, and neither is manually writing the new object into three components'
  local state.
- Optimistic updates: cancel in-flight queries for the key, snapshot the previous cache, write the
  expected value, and **roll back in `onError`** using the snapshot — then invalidate in `onSettled` so
  the server's version wins. An optimistic update without a rollback shows a change that never happened.
- Disable the submit control while the mutation is pending and keep it disabled until the invalidation
  settles, or a double-click sends two writes (`web-forms`).
- A write that must be authorised is authorised **on the server**, in the action or handler, every time
  (`${CLAUDE_PLUGIN_ROOT}/rules/next-app-router.md`).

## Server actions versus route handlers

| Use | When |
|---|---|
| **Server action** | a mutation triggered by this app's own UI — form submit, a button. Progressive enhancement, no hand-written endpoint, revalidation in the same function |
| **Route handler** | something outside this app calls it: a webhook, a third-party integration, a file download, an endpoint another client consumes |

Both validate their input with the schema and both authorise. A server action is a public POST endpoint
in disguise — being invoked from a component proves nothing about who called it.

## Errors

- A failed fetch becomes a **screen state the user can act on**, not a thrown string: the error branch
  renders human copy and a retry that re-runs the query (`web-ui-conventions`). Never render the raw
  message or a stack to the user; log the detail (`v1rus-core:v1rus-logging`).
- Distinguish expected outcomes from faults: a 404 on a detail route is `notFound()`, a 401 is a
  redirect to sign-in, a validation failure is field-level error state — only the unexpected reaches the
  error boundary (`v1rus-typescript:ts-error-handling`).
- Retry policy is explicit: do not retry a 4xx, do retry a transient network failure, and cap it.
