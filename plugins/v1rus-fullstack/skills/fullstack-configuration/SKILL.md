---
name: fullstack-configuration
description: "Environment and configuration split across a NestJS backend and a Next.js frontend in one repository: which variable belongs to which app and why there is no repo-level .env, the hard line that a server secret must never reach the client bundle (the NEXT_PUBLIC_ prefix means publish, and it is inlined at build time), the two-URL rule for an API reachable from both a browser and a server process, validating each app's environment at startup so a missing variable fails fast, declaring variables to the task runner so the build cache is not poisoned, and the dev / CI / prod supply matrix. Load when adding or renaming an environment variable, wiring configuration for a new app or a new environment, a value is needed by both apps, a secret might be leaking into the browser bundle, or a cached build was produced with the wrong configuration. Do NOT load for how the backend's config module is structured (v1rus-node:node-configuration) or how a client component reads a public value (v1rus-react:web-architecture)."
---

# Environment and configuration

Two runtimes, two audiences, one repository. Almost every configuration bug here is one of three
things: a variable with no owner, a secret with a public name, or a cached build made with a value
that is no longer the one in the cache key.

## Ownership: each app owns its own environment

- **`apps/api/.env*`** — database URL, cache URL, signing keys and secrets, third-party API keys,
  the allowed CORS origins, the public base URL of the web app (for links in emails and redirects).
- **`apps/web/.env*`** — the API base URL **as the browser sees it**, the API base URL **as the
  server process sees it** (see below), public feature flags, the analytics id, the public site URL.
- **No `.env` at the repository root.** A variable there has no owner: it gets loaded by whichever
  process happens to start in that directory, and "which app reads this?" becomes unanswerable.
  Repo-wide values that genuinely exist (the environment name, the release identifier) are supplied
  by CI to both apps, and each app still declares that it reads them.
- **A shared value is not a shared variable.** A path, a route or a header name that both sides
  must agree on belongs in `packages/contracts` as code, not in two `.env` files that can drift.
  Only values that differ per environment are environment variables.

`.env.example` is committed per app and lists **every** variable the app reads, with a one-line
description and whether it is a secret. Adding a variable without adding it there turns a startup
failure into someone else's runtime failure a week later.

## The hard line: a server secret never reaches the client

In a frontend framework, a prefix (`NEXT_PUBLIC_`, and the equivalent in any other bundler) marks a
variable for **inlining into the JavaScript served to every visitor**. Two consequences that people
learn the expensive way:

1. **The prefix means "publish this value."** It is not "make this reachable from the frontend
   code" — server-side frontend code reads unprefixed variables perfectly well. A value that must
   not appear in view-source must not carry the prefix. There is no such thing as a secret that is
   "only used in a client component but not really exposed".
2. **The value is baked at build time.** It is frozen into the artifact, so the same build cannot
   be promoted from staging to production with a different value. If a public value must vary per
   environment without a rebuild, it is fetched at runtime from a server endpoint or rendered into
   the page by the server — not read from a public prefix.

Enforcement, in this order:

- Server-only configuration lives in a module that client code cannot import, and that boundary is
  made a build error by the framework's server-only marker rather than a convention
  (`v1rus-react:web-architecture` owns the mechanism).
- The environment schema is split in two: a public object (prefixed variables only) and a server
  object. Client code imports the public one; there is no path from a client component to the
  server one.
- A secret is never read at module scope in a file that anything client-side reaches, even
  conditionally — bundlers include what is reachable, not what runs.
- Review check: a new prefixed variable is a deliberate publication. Ask what happens when it is
  read from the browser console, because it will be.

**The two-URL rule.** The API is reachable at two addresses and they are different variables:

| Caller | Value |
|---|---|
| The browser | the public, externally routable API URL — a public variable by definition |
| The frontend's own server process (server rendering, route handlers) | may be an internal address (a service name, a private hostname) — **not** public |

Collapsing them into one variable forces the internal address into the browser bundle or routes
server traffic out through the public internet. Both are real defects; the second one is also
slower and harder to notice.

## Validate at startup, fail fast

Each app parses its environment **once, at startup, against a schema**, and refuses to start when
it fails. The value of this is entirely in the timing: a missing variable becomes a failed boot
with the variable's name in the message, instead of an `undefined` that becomes a request to
`undefined/users` at three in the morning.

- The parsed, typed object is the only way the rest of the app reads configuration. No
  `process.env` outside that module — that rule is what makes the schema exhaustive rather than
  aspirational.
- Coerce and constrain in the schema: a port is a number, a URL is a URL, an enum is an enum. A
  boolean read from an environment variable is a string; `"false"` is truthy.
- For the frontend, validation runs in the build's configuration step as well, so a missing
  variable fails the build rather than the first request.
- How the backend structures its config module is `v1rus-node:node-configuration`; schema
  validation as a technique is `v1rus-typescript:ts-boundaries-validation`. What this skill
  requires is that both apps do it, separately, over their own variables.

## Tell the task runner

Every variable a task reads is declared in that task's `env` (or `globalEnv`) in the pipeline
configuration. An undeclared variable is not part of the cache key, so a build produced with the
staging value is served from cache as the production build. Nothing fails; the wrong artifact ships.
This is the quietest failure in the whole repository. Mechanics are in
`${CLAUDE_PLUGIN_ROOT}/rules/workspace.md`.

Corollary: adding an environment variable is a four-file change — the app's schema, its
`.env.example`, the task's `env` list, and the environment's secret store. Doing three of the four
is the normal way this breaks.

## The dev / CI / prod matrix

| | Local development | CI | Production |
|---|---|---|---|
| Secrets | `.env.local` per app, never committed, seeded from `.env.example` | the CI provider's secret store, injected per job | the platform's secret manager; never in an image, never in the repository |
| Infrastructure (database, cache) | `docker-compose` — same file CI uses | the same compose stack, ephemeral per run | managed services |
| API base URLs | localhost ports, or one origin behind the dev proxy if that is production's topology | the compose service names | the real hostnames, public and internal |
| Public values | `.env.local` | job configuration | set at **build** time — a promoted artifact carries them |
| Missing variable | app refuses to start, names the variable | the job fails at boot, not at the first test | deploy fails before serving traffic |

Two rules that keep the matrix honest: local development mirrors production's **topology** (same
origin arrangement, same cookie attributes modulo `Secure`), and CI uses the same compose file as
a laptop, or an e2e failure in CI cannot be reproduced locally.

Never print the parsed configuration object at startup, and never log a value that came from a
secret variable — including inside an error message that says what failed to parse. Redaction
policy is `v1rus-core:v1rus-logging`.

## Related

`monorepo-layout` (where the files sit), `fullstack-auth` (cookie attributes per topology),
`fullstack-verification` (what CI supplies to which job),
`v1rus-node:node-configuration` (the backend's config module),
`v1rus-react:web-architecture` (the server/client boundary in the frontend),
`v1rus-core:v1rus-logging` (what must never be logged).
