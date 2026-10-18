---
paths:
  - "**/app/**/page.tsx"
  - "**/app/page.tsx"
  - "**/app/**/layout.tsx"
  - "**/app/layout.tsx"
  - "**/app/**/route.ts"
  - "**/app/route.ts"
  - "**/app/**/loading.tsx"
  - "**/app/loading.tsx"
  - "**/app/**/error.tsx"
  - "**/app/error.tsx"
  - "**/app/**/not-found.tsx"
  - "**/app/not-found.tsx"
  - "**/app/**/template.tsx"
  - "**/app/template.tsx"
  - "**/middleware.ts"
---

# Next.js App Router — non-obvious rules

What a model gets wrong in a route file. React-level rules are in the `react.md` rule of this layer;
TypeScript-level rules belong to `v1rus-typescript`.

**Version discipline first.** The App Router changes shape across majors — whether `params` and
`searchParams` are promises, which caching defaults apply to `fetch` and to route handlers, how
`unstable_cache` / `use cache` are spelled. Check the behaviour for the Next version the project actually
resolves before writing a route file; never write from memory and never pin a remembered version
(`v1rus-core:v1rus-sources`, `v1rus-core:v1rus-dependencies`).

## The server/client boundary

- **Every file under `app/` is a server component until a `"use client"` appears.** `"use client"` is not
  a per-file opt-in — it marks a boundary: that module *and everything it imports* is bundled for the
  browser.
- **Never put `"use client"` at the top of a layout or a page** to make one button interactive. It drags
  the whole subtree into the client bundle, deletes the server-rendering benefit, and makes every
  server-only import a build error. Push the directive down to the smallest interactive leaf and keep the
  page a server component that composes it.
- A server component may render a client component and pass it props; a client component cannot import a
  server component, but it can receive one as `children` or as a prop. That slot pattern is how an
  interactive shell (tabs, accordion, dialog) keeps server-rendered content inside it.
- Props crossing the boundary are serialised: no functions, no class instances, no `Date` in a `Map`, no
  symbols. If it does not survive `JSON`-shaped serialisation, restructure rather than reaching for a
  client component.

## Secrets

- **A `NEXT_PUBLIC_` variable is public.** It is inlined into the browser bundle at build time. An API
  key, a service token, a database URL or an admin webhook with that prefix is a leak, and it is a leak in
  every build artifact from then on.
- Server-only secrets are read in server components, route handlers, server actions or middleware only.
  Guard the module that reads them so an accidental client import fails the build (`import "server-only"`).
- **Do not pass a secret to a client component as a prop.** Props of a client component are serialised
  into the HTML payload and are readable in view-source. The same applies to an object fetched on the
  server that happens to carry a token, an internal id or another user's data — narrow it before it
  crosses.

## Pages, layouts, templates

- A layout **does not re-mount on navigation** between its children — that is the point. Never put
  per-page state, per-page data or a `key`-less form in a layout and expect it to reset. Use `template.tsx`
  when a fresh mount per navigation is genuinely required.
- A page renders for one route; shared chrome (header, nav, skip link) belongs in the layout so it is
  present in **every** state of every child, including error and loading (`web-ui-conventions`).
- `metadata` / `generateMetadata` is exported from a page or layout — every user-reachable route gets a
  title and description. `generateMetadata` runs on the server and may fetch; it deduplicates with the
  page's own fetch of the same resource.
- Route-level `loading.tsx`, `error.tsx` and `not-found.tsx` are part of the route's contract, not
  optional polish (`web-routing`).
- **`error.tsx` must be a client component** and receives `{ error, reset }`. It must render a way out —
  a retry calling `reset()` **and** a link back — and it must not render the error's raw message or stack
  to the user; log the detail, show human copy (`v1rus-core:v1rus-logging`).
- `notFound()` and `redirect()` work by throwing. Calling either inside a `try { } catch { }` swallows the
  control flow and turns a redirect into a silent no-op or a caught "error".

## Route handlers

- A route handler is a public HTTP endpoint. It **authenticates and authorises on every request** — the
  UI having hidden the button proves nothing — and validates its input with the schema at the boundary
  (`v1rus-typescript:ts-boundaries-validation`), never trusting the body, the query or a header.
- Return typed, deliberate responses: a status code that matches the outcome, and an error body shape
  consistent across the app. Never return the caught exception's message verbatim.
- Read the caching and runtime semantics for the resolved Next version and state them explicitly in the
  file (the route segment config) rather than relying on a default that changed between majors. A handler
  that reads cookies, headers or the request URL is dynamic by definition.
- Mutations from the UI go through a server action or a route handler with the same validation — not
  through a client-side call that bypasses one of them.

## Data and rendering

- Fetch where the data is used, on the server, and let request-level deduplication collapse repeats;
  do not thread data through props from a layout just to avoid a second call.
- **Sequential `await`s are a waterfall.** Independent fetches go through `Promise.all`; a slow,
  independent section goes behind its own `<Suspense>` with a real skeleton so the rest of the page
  streams (`web-performance`).
- Never fetch in a `useEffect` in a client component when the data could be fetched on the server or by
  the query library (`web-data-fetching`).
- Revalidation is explicit: a mutation that changes a cached page calls the revalidation API for that
  path or tag. "It will be fresh next deploy" is not a caching strategy.

## Middleware

- Middleware runs on every matched request, before the page — keep it to routing decisions
  (auth redirect, locale, rewrite). No database access, no heavy work, no Node-only API unless the
  project has explicitly configured a Node runtime for it.
- Scope it with a `matcher`; an unscoped middleware also runs for static assets and images.
- Middleware is a gate, **not** the authorisation check. The page, the route handler and the server action
  each verify the session themselves — a middleware-only check is bypassed by any direct request.
