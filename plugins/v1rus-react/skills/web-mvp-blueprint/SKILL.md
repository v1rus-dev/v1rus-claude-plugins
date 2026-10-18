---
name: web-mvp-blueprint
description: "The /mvp-init MVP blueprint for a React / Next.js App Router web app: when this stack is the right choice and when it is not, the create-next-app bootstrap route and exactly what of the template is deleted or replaced, the MVP-sized src/ layout with the rule for when each deferred folder appears, the baseline package set by role (names only, no versions), the tsconfig / ESLint / Tailwind token / i18n / env configuration, the app skeleton (root layout, providers, token layer, fetch client, error and not-found files, message seed), the first vertical slice as real working code with all its screen states, the facts the generated project CLAUDE.md must record, the verification commands, the escalation targets, and the traps that break a fresh Next.js project. Load when scaffolding a new web app, laying out src/ for a new project, or generating a new web project's CLAUDE.md. Do NOT load to add a feature to an existing web project — that is web-pipeline-profile."
---

# MVP blueprint — React / Next.js (App Router)

The technology half of `/mvp-init` on this stack: the command owns the process, this file owns what a
web project *is* at hour zero. Folder vocabulary, the convention-skill map, test layout and verification
discipline live in **`web-pipeline-profile`** — this blueprint says what to *create*, the profile says
how to work in it afterwards. Everything below is the short form of a skill in this plugin; invoke the
named skill before writing the code.

## 1. Stack identity

Next.js with the App Router when the brief describes a **browser-delivered product**: a marketing site, a
dashboard, an admin panel, a customer portal — anything where SEO, first-paint speed or a shareable URL
matters, and where the team writes TypeScript.

| Anti-signal | Go to |
|---|---|
| iOS + Android app from one codebase | `v1rus-flutter:flutter-mvp-blueprint` or `v1rus-kmp:kmp-mvp-blueprint` |
| API, workers, database ownership | `v1rus-node` |
| Web **and** an API in one repo, shared types across the seam | still this blueprint for the web app; `v1rus-fullstack` owns the workspace |
| A purely static document site with no application behaviour | a site generator, not this layer |

## 2. Bootstrap route

`create-next-app` is the generator — never hand-write the framework's config and build wiring. It is
also a demo template, so part of what it produces is deleted immediately.

```
npx create-next-app@latest <app-name> --typescript --app --src-dir --eslint --tailwind \
    --import-alias "@/*" --use-<the project's package manager>
```

- The **package manager is decided in the gate before this runs** and is not changed afterwards: the
  lockfile is committed, and a second lockfile in the tree is trap 1.
- `--app --src-dir --import-alias "@/*"` are the layout this standard assumes; do not drop them.
- Node's version floor comes from the Next major the project resolves — record it in `.nvmrc` / the
  `engines` field so CI and every developer agree.

**Toolchain missing.** If Node or the package manager is not available, do not install it and never use
`sudo`. Say so in one line, hand the developer the exact commands for their own terminal, and continue
with everything that does not need the toolchain — the plan, the `CLAUDE.md`, the file contents to write
once the tree exists.

| # | After `create-next-app` | Detail |
|---|---|---|
| 1 | Delete the demo | the template's page body, its CSS module and hero assets, the framework logo images |
| 2 | Replace the global stylesheet | the token layer (§5) — the template ships raw values |
| 3 | Tighten `tsconfig.json` | `v1rus-typescript:ts-project-config` |
| 4 | Replace the ESLint config | `v1rus-typescript:ts-lint-and-format` + the React-hooks and import-boundary rules |
| 5 | Create the `src/` tree | §3 — a folder only where a file already belongs in it |
| 6 | Add the approved dependencies | §4, through `v1rus-core:v1rus-dependencies` |
| 7 | Skeleton (§6), then the slice (§7) | plumbing before feature code |
| 8 | Verify | §9 |

Kept and edited in place: `next.config.*`, `package.json`, `.gitignore`, the lockfile.

## 3. Module graph at MVP size

One application package. The layers are folders under `src/`, and their boundaries are enforced by an
ESLint import rule rather than by a build graph — that is what makes one package safe here: promoting a
folder to a workspace package later is a move plus a rule update, not an API redesign.

```
src/
  app/                  layout.tsx, page.tsx, error.tsx, not-found.tsx, (app)/<slice>/…
  features/<slice>/     api/, components/, model/
  components/ui/        the primitives the slice actually needs
  lib/                  env.ts, fetch client, cn, formatting
  styles/               tokens.css + globals.css
messages/               <locale>.json
e2e/                    browser specs (created with the first flow)
```

| Deferred | Created when |
|---|---|
| `features/<x>/hooks/` | the feature has logic worth extracting from a component |
| a query provider and TanStack Query | the first data the client re-fetches, polls or mutates — a read-only MVP does not need it |
| a client state store | the first state two distant components share; local state and the URL come first |
| `app/api/` route handlers | something outside this app must call it — a form submit uses a server action |
| auth, middleware, the session check | the brief has accounts |
| a second locale | the brief adds one — the toolchain is wired from day one for a single locale |
| `e2e/` | the first flow worth a browser test |
| analytics, error reporting, a CMS | post-MVP |

## 4. Baseline dependency set, by role

Names only. **Every version is resolved at plan time through the `v1rus-core:v1rus-dependencies`
gate** and CVE-checked there — nothing is added from memory, and no version from this document.

| Role | Package(s) | MVP |
|---|---|---|
| Framework + runtime | `next`, `react`, `react-dom` | mandatory (from the generator) |
| Language + types | `typescript`, `@types/react`, `@types/node` | mandatory |
| Styling | `tailwindcss` and its build integration, `clsx`, a class-merge helper | mandatory |
| Variants | a class-variance helper | with the second primitive that has variants |
| Validation | `zod` | mandatory — it is the boundary contract |
| Forms | `react-hook-form` + its zod resolver | with the first form |
| Server state | `@tanstack/react-query` | with the first client-owned server state (§3) |
| Client state | `zustand` | with the first genuinely shared client state |
| Localisation | `next-intl` | mandatory — strings are messages from day one |
| Accessible primitives | a headless primitive library (dialog, menu, combobox) | with the first such widget — never hand-roll one |
| Lint + format | `eslint` with the flat config set, `prettier` | mandatory |
| Unit / component tests | `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom` or the browser runner, `msw` | infrastructure mandatory; whether tests are *written* is the complexity band's call (`v1rus-core:v1rus-qa`) |
| Browser tests | `@playwright/test` | with the first flow |
| Accessibility assertions | an axe integration for the test runner | with the first component test |
| Icons | one icon set, imported per icon | with the first icon |

No date library until a real need appears — `Intl` covers formatting (`web-localisation`).

## 5. Configuration

| What | Where |
|---|---|
| Dependency coordinates | `package.json` — the only place; the lockfile is committed |
| Node floor | `.nvmrc` + `engines` |
| Compiler strictness, path alias `@/*` | `tsconfig.json` (`v1rus-typescript:ts-project-config`) |
| Lint | flat ESLint config: the TS set, React + hooks, accessibility (jsx-a11y), and the import-boundary rule from `web-architecture` |
| Design tokens | `src/styles/tokens.css` as CSS variables, mapped into the Tailwind theme; both light and dark defined (`web-styling`) |
| Localisation | the `next-intl` setup module, the locale routing decision, `messages/<locale>.json`, and the CI key-drift check (`web-localisation`) |
| Environment | one typed, validated `src/lib/env.ts` parsed with the schema at startup; server-only values guarded so a client import fails the build; `NEXT_PUBLIC_` used **only** for genuinely public values (trap 2) |
| Backend base URL | an env variable read through `env.ts` — never a hardcoded host |
| Image domains, redirects, headers | `next.config.*`, including the security headers the project needs |
| Test config | Vitest config with the path alias and the setup file; Playwright config with the base URL and trace-on-failure |

## 6. App skeleton

Every piece of plumbing is exercised once before feature work starts.

| File | Wires |
|---|---|
| `src/app/layout.tsx` | `html` with `lang` (and `dir` when RTL is in scope), the font loader, `styles/globals.css`, the providers, the skip link, the header with navigation, `main` |
| `src/app/providers.tsx` | the single client component holding the i18n provider, the theme provider and — when §3 calls for it — the query client created per app instance (`web-data-fetching`) |
| `src/app/error.tsx`, `src/app/not-found.tsx` | the global fallbacks: human copy, a retry, a link home — never a raw message (`web-routing`) |
| `src/styles/tokens.css`, `globals.css` | the token layer for both themes, the base reset, the global `prefers-reduced-motion` rule (`web-styling`) |
| `src/components/ui/` | the two or three primitives the slice needs (button, input, skeleton), forwarding refs and merging `className` |
| `src/lib/env.ts` | the validated environment, server and public halves separated |
| `src/lib/api-client.ts` | one fetch wrapper: base URL, headers, `AbortSignal` pass-through, response validation entry point, transport error → app error mapping (`v1rus-typescript:ts-error-handling`) |
| `messages/<locale>.json` | the slice's keys, the shared actions namespace; nothing user-visible is a literal |

No provider is added "for later": an unused query client or store is dead weight, not plumbing.

## 7. The first vertical slice

One end-to-end feature, **real working code** — no `TODO`, no placeholder page. It proves routing,
fetching, validation, error mapping, tokens, localisation and the state checklist fit together, and it
is the template every later feature is copied from.

**Which slice:** the simplest *fetch-a-list-and-show-it* feature from the brief's MVP list; with no
obvious candidate, the list of the app's primary entity plus its detail route. With no backend yet,
build the identical slice against an in-memory implementation behind the same module boundary — swapping
in the real fetcher later is one file.

| Layer | Files |
|---|---|
| `features/<x>/model/` | the zod schema for the resource and the inferred type |
| `features/<x>/api/` | the server-side fetcher validating the response and mapping failures |
| `features/<x>/components/` | the list, the row, the empty state, the error state — all built from `components/ui` |
| `app/(app)/<x>/page.tsx` | the server component that fetches and composes |
| `app/(app)/<x>/loading.tsx`, `error.tsx` | a skeleton of the real layout; an error with a working retry |
| `app/(app)/<x>/[id]/page.tsx` + `not-found.tsx` | the detail route calling `notFound()` on a missing id |
| `messages/` | title, empty copy, error copy, retry label, the detail's not-found copy |

**All five states render**: skeleton, content, human empty copy, an error with a retry that actually
re-runs the fetch, and not-found on the detail. The header and back link are in the **layout**, outside
the state branch, so navigation works while loading and while failed (`web-ui-conventions`). One
interactive leaf — a filter or a refresh control — carries the only `"use client"` in the slice, so the
boundary pattern exists from the first screen, and its filter value lives in the URL
(`react-state-management`).

Slice tests — a component test per state and one Playwright flow — are written when the complexity band
calls for them (`v1rus-core:v1rus-qa`); the state coverage above is required either way.

## 8. Project `CLAUDE.md` inputs

| Fact | Value to record |
|---|---|
| Package manager | the one chosen, and that its lockfile is the only one in the tree |
| Paths | `src/app`, `src/features/<x>/{api,components,model}`, `src/components/ui`, `src/lib`, `src/styles`, `messages/`, `e2e/`; the `@/*` alias |
| Conventions | server components by default and where `"use client"` is allowed; server state owner (server component or the query library); URL state for filters; the import-boundary rule |
| Names | the token file and the token naming scheme; the `cn` helper; the fetch client; the env module; the providers component; the i18n namespace convention |
| Commands | install; dev; build; start; typecheck; lint; unit tests; browser tests; the i18n key-drift check |
| Tests | where component tests live, where `e2e/` specs live, MSW handler location, the `renderWithProviders` helper |
| Decisions | Tailwind + token layer (or the project's alternative); next-intl; TanStack Query in scope or deferred; which env variables are public |
| v1rus plugins to enable | `v1rus-core`, `v1rus-typescript`, `v1rus-react` (plus `v1rus-node` / `v1rus-fullstack` when the repo has a backend) |

## 9. Verification

In this order — an earlier failure makes every later result a lie:

```
<pm> install
<pm> run typecheck          # tsc --noEmit
<pm> run lint               # a blocking warning is a failure
<pm> run test               # unit + component
<pm> run build              # production build — several errors exist only here
<pm> run test:e2e           # when a flow spec exists
```

| Then | Headless? |
|---|---|
| `<pm> run build` | yes — the real gate for route, boundary and env errors |
| `<pm> start` against the production build, smoke the slice | yes, with a browser test |
| `<pm> run dev` and look at it | **developer** — the visual and keyboard pass is theirs |

"Runnable" means the production build serves the slice's content state, its empty state and its error
state. The agent verifies up to the build and the browser smoke test, then hands over the exact dev
command — never claiming a visual result it did not see. Full runs belong to `v1rus-react:test-runner`.

## 10. Escalation targets

| Scaffold role | Agent |
|---|---|
| `package.json`, tsconfig, ESLint, Tailwind and token setup, env module, test configs | `v1rus-react:web-developer` (TypeScript-level config per `v1rus-typescript`) |
| Layout, providers, primitives, the slice's components and routes | `v1rus-react:web-developer` |
| Verification runs | `v1rus-react:test-runner` |
| Backend package in the same repo | `v1rus-node`'s engineer; the workspace itself is `v1rus-fullstack` |
| Floor when none is installed | `feature-developer` |

## 11. Known first-run traps

1. **Two lockfiles.** Running `npm install` once in a project bootstrapped with another package manager
   leaves a second lockfile, and the framework then resolves the workspace root wrongly and installs a
   different dependency tree in CI than on the developer's machine. Decide the package manager in the
   gate, commit one lockfile, and delete any other on sight.
2. **A secret behind `NEXT_PUBLIC_`.** The prefix inlines the value into the browser bundle at build
   time; it is public in every artifact from then on. Validate the environment in one module, keep the
   server half guarded so a client import fails the build, and review every `NEXT_PUBLIC_` addition as a
   disclosure decision.
3. **`"use client"` at the top of the root layout.** Usually added to mount a provider, it converts the
   entire application to client rendering — the bundle triples, server-only imports break, and the cause
   is invisible in the diff. Providers go in their own small client component that takes `children`.
4. **Demo leftovers.** The template's page, its CSS module and its hero images survive into the first
   review; the generator's default `metadata` ships a framework title in production; and the template's
   global stylesheet carries raw values that quietly become the app's de facto tokens.
5. **Believing the dev server.** Hydration mismatches, env access errors, bundle regressions and several
   route-config mistakes only appear in a production build. Run the build before declaring the scaffold
   done.
