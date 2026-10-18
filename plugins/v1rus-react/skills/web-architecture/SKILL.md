---
name: web-architecture
description: "The v1rus web frontend architecture and the front door to this layer's path rules: the app/ route tree beside feature folders, what lives in features/ versus components/ versus lib/, the import boundaries a feature must not cross, where the server/client boundary belongs and why it is pushed to the leaves, which module may read a secret, and the route-file and React rule sets shipped in rules/next-app-router.md and rules/react.md. Load when creating a page or a feature folder, deciding which folder a file belongs to, placing a \"use client\" directive, reviewing an import boundary, or reviewing React code where no edit triggers the path-rule injection."
---

# Web Architecture (Next.js App Router)

Two rule files carry the file-local detail and are injected automatically before an edit:

- **`${CLAUDE_PLUGIN_ROOT}/rules/react.md`** — component-level traps: purity and hydration, derived
  state, when an effect is the wrong tool, hooks, keys, context re-renders, controlled inputs,
  cancellation. Injected before any `.tsx` / `.jsx` edit.
- **`${CLAUDE_PLUGIN_ROOT}/rules/next-app-router.md`** — route-file traps: the `"use client"` boundary,
  `NEXT_PUBLIC_` and secrets, layouts versus templates, `error.tsx` / `notFound()` / `redirect()`, route
  handlers as public endpoints, waterfalls, middleware. Injected before editing a `page` / `layout` /
  `route` / `loading` / `error` / `template` file or `middleware.ts`.

**Read them directly when reviewing or planning** — a review performs no edit, so nothing is injected.
TypeScript-language rules are not here: `v1rus-typescript:typescript-conventions` and its siblings own
type discipline, boundary validation, error modelling and async.

## Layout

The route tree and the feature code are separate concerns. `app/` stays thin — routing, composition and
data entry points; the substance lives in `features/`.

```
src/
  app/                        # routing only: page, layout, loading, error, not-found, route handlers
    (marketing)/              # route group — organisation without a URL segment
    (app)/
      orders/
        page.tsx
        loading.tsx
        error.tsx
        [orderId]/page.tsx
    api/<area>/route.ts
    layout.tsx                # root layout: html/body, providers, fonts, skip link
  features/
    orders/
      api/                    # fetchers, query options, server actions for this feature
      components/             # components private to this feature
      model/                  # schemas, types, mappers, pure logic
      hooks/
  components/ui/              # the design system: primitives, no feature knowledge
  lib/                        # framework-agnostic helpers: fetch client, env, formatting, cn
  styles/                     # token layer and global stylesheet
  i18n/ or messages/          # locale message files and the i18n setup
```

A folder appears when a file already belongs in it. Do not create an empty five-folder feature skeleton.

## Import boundaries

```
app/  ──▶ features/  ──▶ components/ui/  ──▶ lib/
      └──────────────▶ lib/
```

- **A feature never imports another feature.** Shared UI goes to `components/ui`, shared logic to `lib`,
  a shared domain type to the feature that owns it with an explicit public entry point (`features/x/index.ts`)
  — or, in a monorepo, to a package (`v1rus-fullstack` owns that decision).
- **`components/ui` and `lib` know nothing about features.** A primitive that imports a feature type is
  not a primitive.
- **`app/` imports features, never the reverse.** A feature that imports from `app/` has its routing
  concern in the wrong place.
- Deep imports across a boundary are banned: cross a boundary through the module's public entry, not
  through `features/orders/components/internal/Row`.
- Enforce what the project can enforce — an ESLint import boundary rule
  (`v1rus-typescript:ts-lint-and-format` owns the flat-config mechanics) beats a review comment,
  because drift then fails CI instead of depending on someone noticing.

## The server/client boundary is an architectural decision

Server components are the default and the boundary is pushed **as far down the tree as possible**. The
question is never "is this page interactive" but "which leaf actually needs a browser API, an event
handler, or React state".

| Needs | Where it goes |
|---|---|
| Data for first paint, secrets, direct backend access | server component |
| An event handler, `useState`, an effect, a browser API, an animation library | client component leaf |
| Interactive shell wrapping server-rendered content | client component taking `children` |

Practical consequences:

- A page composes: server component fetches, renders a client leaf with the data as props.
- A provider (query client, theme, i18n) is a client component mounted **once** in the root layout, with
  `children` passed through — the children stay server components.
- Anything read from `process.env` without the `NEXT_PUBLIC_` prefix is server-only; the module that
  reads it is marked server-only so an accidental client import fails the build rather than the runtime.

## Adding a feature — checklist

1. `src/features/<name>/` with only the folders that already have a file.
2. Schemas and types in `model/` — validated at the boundary
   (`v1rus-typescript:ts-boundaries-validation`), not re-declared per call site.
3. Data access in `api/`: the server fetcher, the query options object, the server actions
   (`web-data-fetching`).
4. Components in `components/`, built from `components/ui` primitives, styled with tokens
   (`web-styling`), satisfying the state and accessibility checklist (`web-ui-conventions`).
5. Routes under `app/` with `loading` and `error` beside the page, and `not-found` for a fetched detail
   (`web-routing`).
6. Message keys added to **every** locale in the same change (`web-localisation`).
7. Tests when the complexity band calls for them (`v1rus-core:v1rus-qa`, `web-testing`).

## Where this layer stops

| Concern | Owner |
|---|---|
| tsconfig, ESM, type modelling, validation, `Error`/`cause`, async, package `exports`, ESLint | `v1rus-typescript` |
| NestJS, Prisma, server runtime, database | `v1rus-node` |
| Monorepo tooling, sharing API types across the seam, cross-seam e2e, env split between apps | `v1rus-fullstack` |
| Process, gates, complexity bands, logging, dependency approval | `v1rus-core` |
