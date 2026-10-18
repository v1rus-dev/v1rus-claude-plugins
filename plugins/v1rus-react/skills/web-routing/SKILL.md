---
name: web-routing
description: "Routing conventions for a v1rus Next.js App Router app: the file conventions a route must ship (page, loading, error, not-found) and what each one owes the user, route groups and dynamic segments, layouts versus templates and what does not re-mount on navigation, parallel and intercepting routes for a linkable modal, typed navigation helpers instead of hand-built path strings, Link and prefetching, metadata and generateMetadata per route, redirects and auth gating in middleware plus the server-side check that actually enforces it, and deep links as a first-class cold entry point. Load when adding a route or a nested layout, wiring navigation between screens, building a modal that must be linkable, handling a not-found detail, or setting route metadata."
---

# Routing (App Router)

Route-file traps — the `"use client"` boundary, `notFound()`/`redirect()` throwing, route handlers,
middleware scope — are in `${CLAUDE_PLUGIN_ROOT}/rules/next-app-router.md`. This skill is the shape of
the route tree and the navigation between routes.

## What a route ships

| File | Obligation |
|---|---|
| `page.tsx` | the content state; a fetched detail also handles **not-found** |
| `loading.tsx` | a **skeleton of the real layout**, not a centred spinner — and only as the coarse fallback; a slow section gets its own `<Suspense>` |
| `error.tsx` | a client component with `{ error, reset }`: human copy, a retry, and a link out. Logs the detail, shows none of it |
| `not-found.tsx` | reachable from `notFound()`; explains what was not found and links somewhere useful |
| `layout.tsx` | the chrome that must exist in **every** state of every child |

The single most common finding on this stack: an error or loading state that renders without the
navigation, so a failed fetch leaves the user with no way back. Put the header, the back link and the
skip link in the **layout**, so they survive every child state (`web-ui-conventions`).

## Tree organisation

- **Route groups** `(marketing)` / `(app)` organise without adding a URL segment — use them to give
  different sections different root chrome, not to hide depth.
- **Dynamic segments** carry identity (`[orderId]`), query parameters carry optional view state
  (`?status=open`). Never encode a filter as a path segment, and never pass a whole object through a
  route — a route is a URL and must survive a cold start where no object exists in memory
  (`react-state-management`).
- Segment params are **user input**: parse and validate them before use
  (`v1rus-typescript:ts-boundaries-validation`). An unvalidated id that goes straight to the backend is
  both a crash and an access-control question.
- Colocation: only the framework's route files live in `app/`. A component that happens to be used by one
  page still belongs to the feature (`web-architecture`).

## Layouts, templates, and what persists

- A layout **does not re-mount** across navigations between its children. State in a layout survives —
  intentionally for a sidebar's scroll position, accidentally for a form you expected to reset.
- Use `template.tsx` only when a fresh mount per navigation is genuinely needed (an enter animation, a
  per-navigation effect).
- A nested layout that fetches runs on every navigation into its subtree. Fetch there only what the whole
  subtree needs.

## Navigation

- **No hand-built path strings at call sites.** `` `/orders/${id}` `` survives a route rename silently
  and shows up as a 404 in production. Keep a typed route helper module (`routes.order(id)`) that is the
  only place a path literal appears, or use the project's typed-routes mechanism when the resolved Next
  version provides one.
- `Link` for anything that navigates — it prefetches, it is a real anchor, it middle-clicks and it is
  reachable by keyboard. `router.push` only for navigation that follows a non-link interaction (a
  successful mutation, a redirect after sign-in).
- A "button" that navigates is a link styled as a button, not a `button` with an `onClick` that pushes
  (`web-ui-conventions`).
- Prefetching is a trade: it is free responsiveness on a small page and wasted bandwidth on a list of
  hundreds of links. Disable it deliberately where a list is long.
- **Focus and scroll on navigation** are the app's responsibility once it is a client-side transition —
  see the focus rules in `web-ui-conventions`.

## Modals that are routes

A modal that is part of a flow — a detail view, a confirm step, anything shareable or deep-linkable —
is a **route**, built with parallel and intercepting routes: the URL changes, the back button closes it,
a direct visit renders the full page instead of a modal over nothing.

A purely local dialog with no navigation meaning (a colour picker, a confirm-delete popup) stays in
component state. Either way, the dialog itself must satisfy the focus-trap and dismissal rules in
`web-ui-conventions` — a modal the keyboard cannot leave is the other common trap on this stack.

## Metadata

- Every user-reachable route exports `metadata` or `generateMetadata`: a title that reads as a page name,
  a description, and the social image where it matters. A tab titled after the framework template is a
  shipped bug.
- `generateMetadata` runs on the server and may fetch; it deduplicates with the page's own fetch of the
  same resource, so it does not cost a second request.
- Titles come from the localisation layer like any other user-visible string (`web-localisation`).
- Set `robots`/`canonical` deliberately on paginated and filtered routes rather than letting every
  query-string permutation be indexable.

## Auth gating

One redirect decision, in middleware: unauthenticated on a guarded route → sign-in; authenticated on the
sign-in route → home. Per-page `if (!session) redirect(...)` scattered through the tree races and misses
routes.

**Middleware is routing, not authorisation.** The page, the server action and the route handler each
verify the session and the permission themselves, because a direct request never passes through the
page's own check. Make sure the redirect cannot loop: the sign-in route must be reachable while
unauthenticated, and the authenticated branch must not send the user back into a guarded route.

## Deep links

Any route can be opened cold: no session, no cache, no in-memory object, possibly a stale or malformed
id. Every page therefore loads everything it needs from its params and handles loading, not-found and
unauthorised itself.
