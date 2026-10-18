---
name: fullstack-auth
description: "Authentication and session across the seam between a NestJS backend and a Next.js frontend: where the token actually lives (HttpOnly cookie by default, bearer only for non-browser clients and why), what the deployment topology does to cookie attributes, reading the session during server rendering and forwarding it on server-to-server fetches, refreshing without a race and without trying to set a cookie during a render, refresh-token rotation and reuse detection, CSRF for cookie auth, and a logout that clears the server session, both cookies and every client-side cache. Load when wiring login or logout end to end, deciding cookie versus bearer, a server component or middleware needs the current user, a token refresh races or loops, a user still sees the previous user's data after logout, or the frontend and backend sit on different origins. Do NOT load for how tokens are minted, verified or stored server-side (v1rus-node:nest-architecture and node-persistence), or for the login form and its UI states (v1rus-react:web-forms and web-routing)."
---

# Auth across the seam

This skill owns exactly one question: **where the credential lives and how it crosses between the
two apps.** Minting, verifying and storing it server-side is the backend's (`v1rus-node`); the
login screen and its states are the web app's (`v1rus-react`). Those two get this wrong when nobody
owns the middle, which is what this file is.

## Where the token lives

**Default: an HttpOnly cookie set by the backend.** The browser never holds the credential in
JavaScript-reachable storage.

| Storage | Verdict |
|---|---|
| `HttpOnly; Secure; SameSite=Lax` cookie | **default** for the browser client |
| `localStorage` / `sessionStorage` | **banned** for the web app — any XSS, including one in a third-party script, exfiltrates the token wholesale, and no CSP makes that safe enough |
| In-memory bearer + refresh cookie | acceptable when the access token must also be sent to a third-party API the cookie cannot reach; it is more moving parts, so justify it |
| `Authorization: Bearer` | for **non-browser** clients: mobile, CLI, service-to-service. The backend accepts both; the browser path uses the cookie |

Cookie attributes, all of them, every time: `HttpOnly`, `Secure` (outside local development),
`SameSite`, an explicit `Path`, and an explicit expiry. A cookie set without an attribute you
intended is a cookie you cannot reliably delete later — see logout.

**Access and refresh are two cookies.** A short-lived access cookie scoped to `Path=/`, and a
refresh cookie scoped **only to the refresh endpoint's path**, so it is not attached to every
request and a leak of one request's headers does not hand over the long-lived credential.

## Topology decides the attributes

Settle this before writing any of it — it is a deployment decision that changes the code.

| Deployment | Cookie |
|---|---|
| One origin (the web app proxies `/api/*` to the backend) | **preferred.** First-party cookie, `SameSite=Lax`, no CORS, no third-party-cookie problem |
| Sibling subdomains of one registrable domain (`app.` and `api.`) | workable: `Domain=<parent>`, `SameSite=Lax`; CORS with credentials and an explicit origin allowlist — never a wildcard with credentials |
| Different registrable domains | the cookie is third-party: `SameSite=None; Secure`, and browsers increasingly block it outright. Do not design a browser session on this; put the two behind one origin or accept an in-memory-token design and say so |

Local development mirrors production's topology, or the cookie behaves differently on a laptop than
in production and the difference surfaces at release.

## Reading the session on the server

Server rendering is where cookie auth quietly breaks, because two intuitions are wrong at once.

- **A server-side fetch does not carry the browser's cookies automatically.** During server
  rendering the request to the backend originates from the server, not from the browser. The server
  read the incoming request's cookies; it must **explicitly forward** them (or a derived
  credential) on the outgoing call. Centralise this in one server-side API client that takes the
  incoming request context — never a bare `fetch` to the backend scattered through server code, or
  half the calls will be unauthenticated and render a signed-out page to a signed-in user.
- **A render cannot set a cookie.** Only middleware, a route handler or a server action can write
  `Set-Cookie`. So a server component that discovers an expired session cannot refresh it: it
  redirects, or renders the signed-out state. Refresh belongs in middleware or a dedicated route
  handler, before the render.

Consequences worth stating in the plan: which routes are protected in middleware (cheap, runs before
render, can redirect and can set cookies) versus which check inside the page (needed when the
decision depends on data). Middleware is a gate, not the authorisation — the backend still
authorises every request, because a client-side or edge check is an optimisation, not a boundary.

## Refresh without a race

A refresh has exactly one correct concurrency story: **one refresh in flight at a time, everyone
else waits for it.**

- **Client side:** a single shared in-flight refresh promise. On a 401, a request enqueues on that
  promise, does not start its own refresh, and retries once when it resolves. Without this, ten
  parallel requests trigger ten refreshes; with rotation enabled, nine of them present a
  just-rotated token and the whole session is revoked as suspected reuse.
- **Retry exactly once.** A refresh that itself returns 401 means the session is over: clear
  everything, route to signed-out. A retry loop here is how a page hammers the backend forever.
- **Server side:** refresh in middleware (or a route handler) before the render, not during it, for
  the reason above. Concurrent server requests from the same user are a real case — rotation must
  tolerate a small reuse window (a short grace period on the previous token) or a page with several
  parallel server fetches revokes its own session.
- **Rotation with reuse detection** is the default: each refresh issues a new refresh token and
  invalidates the old one; presenting an already-used token invalidates the whole family and forces
  re-authentication. The grace window above is the one deliberate exception, and it is short.
- The refresh endpoint is the only place either app touches the refresh token. No component, no
  loader, no page calls it directly.

## CSRF

Cookie auth means the browser attaches the credential to cross-site requests, so it needs an
answer — bearer auth does not, which is the one real thing bearer buys.

- `SameSite=Lax` is the baseline: it blocks the cross-site form-post shape.
- **State-changing requests additionally verify the request's origin** against an allowlist on the
  backend, or carry a double-submit token. Pick one, apply it to every mutating route through one
  mechanism, never per-controller.
- `SameSite=None` (the cross-domain topology) removes the baseline entirely — then a token is not
  optional.

## Logout clears both sides

Logout is where "it looked like it worked" is most expensive: the next person on that laptop sees
the previous user's data rendered from a cache.

1. **Backend:** revoke the server-side session / refresh-token family. A logout that only deletes
   cookies leaves a valid credential alive for anyone who copied it.
2. **Cookies:** clear each one with the **exact same** `Path` and `Domain` it was set with. A
   `Set-Cookie` with a different path does not delete it; it creates a second, empty cookie beside
   the live one, and the user stays signed in with no way to see why.
3. **Client caches:** purge the data-layer cache (the query client's store) *and* the framework's
   router/route cache, then navigate. Clearing one and not the other is the classic "signed out but
   the dashboard still shows their name" bug.
4. **Server-rendered pages** for authenticated users must not be cached in a shared cache: the
   response is per-user. Mark them accordingly, or a CDN serves one user's page to the next.
5. **Every open tab.** Logout in one tab leaves the others believing they are signed in until their
   next request fails; broadcast it (a storage event or a broadcast channel) so they all reset.

A session that expires server-side must funnel through the same teardown: one `signOut()` routine
called by the logout button, by the refresh failure path and by an unrecoverable 401 — not three
implementations that clear slightly different things.

## Related

`fullstack-configuration` (which of these values is a secret and which app holds it),
`api-contract` (the auth endpoints and the error body), `fullstack-verification` (logging in once
for e2e via the API and reusing the storage state), `v1rus-node:nest-http-api` and
`v1rus-node:node-configuration` (how the backend issues and reads it),
`v1rus-react:web-routing` (protected routes and redirects in the frontend).
