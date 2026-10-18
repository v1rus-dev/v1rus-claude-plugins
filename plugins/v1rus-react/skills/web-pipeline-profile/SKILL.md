---
name: web-pipeline-profile
description: "Stack profile that binds the stack-agnostic v1rus feature pipeline to a React / Next.js App Router web project: the folder vocabulary the architecture plan uses, the stack-specific sections of architecture-plan.md and the self-questions it must answer, which convention skill owns which area, the presentation pattern (server components by default with the client boundary at the leaves, server state in the query library, URL state), design-spec mapping onto the token layer and components/ui, where tests live and on what (Vitest plus Testing Library, MSW, Playwright), how to typecheck build and verify, which engineer agents implementation escalates to, and the finalizer's stack checklist. Loaded by feature-architect, feature-designer, feature-developer, test-planner, test-writer and feature-finalizer when the pipeline detects a Next.js web project. Do NOT load for pipeline mechanics — gates, complexity bands and commit discipline live in feature-pipeline."
---

# Pipeline profile — React / Next.js (App Router)

The pipeline agents (`feature-architect`, `feature-designer`, `feature-developer`, `test-planner`,
`test-writer`, `feature-finalizer`) are stack-agnostic. This profile is the **vocabulary** they use on a
Next.js web project.

Two boundaries that matter:

- **Pipeline mechanics are not here.** Phase order, gates, complexity bands, artifact names, commit
  discipline and resume live in the `v1rus-core:feature-pipeline` skill. This file never repeats them.
- **The project still owns the names.** The real folder layout, the path alias, the script names, the
  design-token names and the i18n setup come from the target project's `CLAUDE.md`, `package.json` and
  config files. Read those first; never guess a command.

## Stack identity

Markers: `package.json` depending on `next` and `react`, a `next.config.*`, an `app/` directory
containing `page.tsx` / `layout.tsx`, `tsconfig.json`. In a monorepo the markers sit in the web app's
own package, not at the root — `v1rus-fullstack` owns the workspace-level questions.

Anti-marker: a `nest-cli.json` / NestJS dependency in the same package means the target is the backend
(`v1rus-node`), not this layer.

## Folder vocabulary

| Folder | Holds |
|---|---|
| `src/app/` | routing only: `page`, `layout`, `loading`, `error`, `not-found`, `template`, route handlers, route groups |
| `src/features/<name>/` | `api/` (fetchers, query options, server actions), `components/`, `model/` (schemas, types, mappers, pure logic), `hooks/` |
| `src/components/ui/` | the design system: primitives with no feature knowledge |
| `src/lib/` | framework-agnostic helpers: fetch client, env access, formatting, `cn` |
| `src/styles/` | the token layer and the global stylesheet |
| `messages/` or `src/i18n/` | locale message files and the i18n setup |
| `middleware.ts` | routing decisions only |

Hard boundaries: a feature never imports another feature; `components/ui` and `lib` know nothing about
features; `app/` imports features and never the reverse; no deep import across a boundary. Enforce them
with the project's ESLint import rule where one exists — detail in `web-architecture`.

## `architecture-plan.md` — stack sections

Use these in place of the generic layer sections:

```
## 3. Data and contracts        (schemas in features/<x>/model, the fetcher or server action in
                                features/<x>/api, response validation at the boundary, error mapping,
                                query keys and invalidation targets)
## 4. Route changes             (new or changed segments under app/, loading / error / not-found files,
                                metadata, route handlers, middleware impact, redirects)
## 5. UI changes                (server vs client components and exactly where "use client" lands,
                                the component tree, which components/ui primitives are reused or added,
                                every screen state: loading / empty / error / not-found / content)
## 6. Wiring                    (providers touched, message keys per locale, tokens added to the theme,
                                env variables and which side may read them, navigation entry points)
```

Self-questions the plan must answer on this stack: what is the smallest subtree that needs
`"use client"`, and does anything in it pull a heavy dependency into the bundle; does any value crossing
to a client component contain a secret, a token or another user's data; is each piece of new state
server / URL / client / form, and is any server data being copied into component state; does every new
screen state exist, and is navigation reachable in all of them; is every user-visible string a message
key in every locale; what does the mutation invalidate.

## Convention skills by area

| Area | Skill |
|---|---|
| folder layout, import boundaries, the server/client boundary, the two path rules | `web-architecture` |
| component design, props, composition, custom hooks | `react-component-conventions` |
| where state lives, server vs URL vs client vs form | `react-state-management` |
| server-component fetching, query keys, mutations, invalidation, server actions | `web-data-fetching` |
| route files, layouts, modals as routes, metadata, auth gating | `web-routing` |
| screen states, semantics, focus, keyboard, contrast, announcements | `web-ui-conventions` |
| tokens, Tailwind, variants, theming, responsive, motion | `web-styling` |
| react-hook-form + zod, accessible errors, submit state | `web-forms` |
| bundle, images, streaming, re-renders, measuring | `web-performance` |
| next-intl, keys, ICU, `Intl` formatting, locale sync | `web-localisation` |
| Vitest, Testing Library, MSW, Playwright | `web-testing` |
| types, validation, `Error`/`cause`, async, ESLint, tsconfig | `v1rus-typescript:typescript-conventions` and siblings |

Name the applicable ones in the plan so the implementing agent invokes them; invoke them yourself before
writing non-trivial UI or data code. If a skill is absent in the current environment, proceed — never
hard-depend on one.

## Presentation pattern

**Server components by default**; `"use client"` marks a boundary and is pushed to the smallest
interactive leaf. A page is a server component that fetches and composes; interactive shells take
`children` so their content stays server-rendered. **Server state** is owned by a server component or by
TanStack Query and is never copied into `useState`. **URL state** (filters, sort, page, tab, open
detail) lives in `searchParams`. **Client state** is local, or in a Zustand store when genuinely shared;
context is dependency injection. **Form state** belongs to react-hook-form with a zod resolver.

## Design-spec mapping (feature-designer)

Map the design onto the project's **token layer and `components/ui`**, not onto raw values: colours,
spacing, radii, typography and durations → existing tokens (never a hex, never an arbitrary pixel
value); components → existing primitives first, a new primitive in `components/ui` only when genuinely
missing. Discover what exists with `v1rus-core:v1rus-code-search` before proposing anything new. The
spec must name every screen state, the focus behaviour for dialogs and navigation, and both themes.

## Tests

- **Location:** beside the source (`OrderRow.tsx` → `OrderRow.test.tsx`) or a mirrored tests tree —
  follow the project. Browser specs live in their own directory.
- **Components and hooks:** Vitest + Testing Library + `user-event`; queries by role and label.
- **Network:** MSW at the transport boundary, not a mocked hook or fetch module; the failure path is
  covered for every load.
- **Server components, route handlers, server actions:** unit-test the extracted logic and the handler
  directly; cover the rendered page in Playwright.
- **Flows:** Playwright with role locators and web-first assertions; no arbitrary waits.
- Detail: `web-testing`.

## Verification

In this order — an earlier failure makes every later result a lie:

1. **Typecheck** (`tsc --noEmit` or the project's script) — the first real gate on this stack.
2. **Lint** — ESLint including the React-hooks and import-boundary rules; a warning that the project
   treats as blocking is a failure.
3. **Unit and component tests** at the scope the change warrants (`v1rus-core:check`).
4. **Production build** for anything touching routing, the client boundary, env access or bundle size —
   several classes of error exist only in a production build.
5. **Playwright** only when the change touches a covered flow.

Commands come from the project's `package.json` and `CLAUDE.md`. Full runs belong to
`v1rus-react:test-runner`. Never read `.next/`, `node_modules/` or a coverage directory.

## Implementation escalation targets

| Work | Agent |
|---|---|
| Pages, components, styling, routing, forms, client logic, tests for them | `v1rus-react:web-developer` |
| Verification runs | `v1rus-react:test-runner` |
| Backend / NestJS side of the same task | `v1rus-node`'s engineer, when installed |
| Floor when none is installed | `feature-developer` |

## Finalizer stack checklist

On top of the generic cleanup: no `"use client"` higher in the tree than it needs to be; no secret in a
`NEXT_PUBLIC_` variable or in a client component's props; no server data mirrored into `useState`; no
`useEffect` fetching or deriving state; every list key from the data; every screen state present with
navigation reachable in all of them; every interactive element a real element with an accessible name;
every user-visible string a message key, present in **every** locale; no raw colour or arbitrary spacing
in feature code; no leftover `console.log` (`v1rus-core:v1rus-logging`); typecheck and lint clean.

## Typical expert reviews to flag

`ux-expert` for a new screen, a dialog, or a navigation change; `security-expert` for auth, session
handling, a new route handler or server action, or anything reading env; `performance-expert` for a
large list, a new heavy dependency, or a change to the client boundary; `architecture-expert` when
the change crosses a feature boundary or introduces a new shared module.
