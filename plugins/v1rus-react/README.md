# v1rus-react

The web frontend layer: **React with the Next.js App Router, in TypeScript**. Depends on
`v1rus-typescript`, which depends on `v1rus-core`, so installing it pulls the language layer and the
corporate baseline with it.

```
/plugin install v1rus-react@v1rus
```

## The stack this plugin standardises

| Concern | Decision |
|---|---|
| Framework | Next.js **App Router**; server components by default, `"use client"` at the interactive leaf |
| Structure | `src/app/` for routing only, `src/features/<name>/` for substance, `src/components/ui/` for the design system, `src/lib/` for helpers |
| Boundaries | a feature never imports a feature; `components/ui` and `lib` know nothing about features; enforced by an ESLint import rule, not by review |
| Server state | a server component when it is read-only at first paint, **TanStack Query** when the client re-fetches, polls or mutates it — never mirrored into `useState` |
| URL state | filters, sort, page, tab and open-detail live in `searchParams` |
| Client state | local first; **Zustand** for genuinely shared client state; context is dependency injection |
| Forms | **react-hook-form** + a **zod** resolver, one schema re-validated on the server |
| Styling | **Tailwind over a CSS-variable token layer** — feature code names a token, never a raw value |
| Localisation | **next-intl**, message files per locale, locale drift a CI failure |
| Writes | a **server action** for this app's own UI, a **route handler** for anything external |
| Tests | **Vitest + Testing Library + `user-event` + MSW** for components, **Playwright** for browser flows |
| Verification | typecheck → lint → tests → production build; the build is a gate, not an afterthought |

**No versions are pinned anywhere in this plugin.** Package names only; the version is resolved at plan
time through the `v1rus-core:v1rus-dependencies` gate (`npm view` / the registry for npm packages).

## Contents

| Component | What it covers |
|---|---|
| `skills/web-architecture` | Folder layout, import boundaries, the server/client boundary as an architectural decision, adding a feature — and the front door to both rule files |
| `skills/react-component-conventions` | One component per file, composition over configuration, prop API design, splitting, custom hooks |
| `skills/react-state-management` | The four kinds of state and the decision between them, why server state is never mirrored, URL first, store vs context |
| `skills/web-data-fetching` | Server-component fetching, query keys and staleness, invalidation and optimistic updates, hydration, server actions vs route handlers, waterfalls |
| `skills/web-routing` | What a route ships, route groups and dynamic segments, layouts vs templates, modals as routes, metadata, auth gating, deep links |
| `skills/web-ui-conventions` | The screen-state and accessibility checklist — states, semantics, focus, keyboard, announcements, contrast, content, lists |
| `skills/web-styling` | The token contract, class composition, variants, where styles live, theming, responsive, motion |
| `skills/web-forms` | One schema two enforcements, uncontrolled fields, accessible errors, submit state, server-side field errors, form lifecycle |
| `skills/web-performance` | Ship less JavaScript → render sooner → re-render less, images and fonts, lists, and measuring before optimising |
| `skills/web-localisation` | Messages only, key discipline, mechanical locale sync, ICU, `Intl` with an explicit time zone, server vs client namespaces |
| `skills/web-testing` | What is tested where (including what to do about server components), query priority, MSW at the boundary, Playwright discipline |
| `skills/web-pipeline-profile` | The feature-pipeline stack profile: vocabulary, plan sections, skill map, tests, verification, finalizer checklist |
| `skills/web-mvp-blueprint` | The `/mvp-init` blueprint: bootstrap, MVP-sized layout, baseline packages by role, the skeleton, the first vertical slice, the generated project `CLAUDE.md` |
| `rules/react.md` | Injected before any `.tsx` / `.jsx` edit: render purity and hydration, derived state, when an effect is the wrong tool, hooks, keys, context re-renders, cancellation |
| `rules/next-app-router.md` | Injected before editing a route file or `middleware.ts`: the `"use client"` boundary, `NEXT_PUBLIC_` and secrets, layouts vs templates, `error.tsx`, route handlers, waterfalls, middleware |
| `agents/web-developer` | Writes routes, components, styling, forms, client and server-component data access, and their tests. No backend. |
| `agents/test-runner` | Runs typecheck → lint → tests → build (→ browser flows); reports PASS/FAIL. Never edits code. |

### Path-rule globs and the fullstack case

The `path-rules` hook injects a rule when the edited file matches its `paths:` globs. Those globs are
deliberately narrow — `**/*.tsx` / `**/*.jsx` plus the two `.ts` shapes a custom hook takes
(`**/hooks/**/*.ts`, `**/use-*.ts`) for the React rule, the `app/**` route files and `middleware.ts`
for the App Router rule — **not** every `.ts` file. A hook file holds the effect and
dependency-array code the rule exists for, and neither shape occurs in a NestJS service: in a
fullstack monorepo `v1rus-node` and `v1rus-react` are installed side by side, and a blanket `.ts`
glob here would inject React rules while someone edits a provider. TypeScript-language rules that are true on both sides are
`v1rus-typescript`'s job, and it ships them once.

## Where this layer stops

| Concern | Owner |
|---|---|
| tsconfig and ESM, `any`/`unknown`/discriminated unions/branded types, schema validation at I/O boundaries, `Error` + `cause` and Result-vs-throw, floating promises and `AbortSignal`, package `exports`, the ESLint flat config | `v1rus-typescript` |
| NestJS, Prisma, the server runtime and everything behind the API | `v1rus-node` |
| Monorepo tooling, sharing API types across the seam, cross-seam e2e, splitting env between apps | `v1rus-fullstack` |
| Process, gates, complexity bands, logging, dependency approval, review agents | `v1rus-core` |

## Design notes

**Why server components are the default and the boundary goes at the leaves.** The single decision that
most affects a Next.js app's bundle, first paint and security surface is where `"use client"` sits. A
directive added to a layout so one button works drags the whole subtree into the browser, and the diff
that caused it is one line. Making "server by default, client at the leaf" the standard turns that into
a reviewable, checkable rule instead of a per-developer habit — and the composition pattern it forces
(a client shell taking `children`) is better structure anyway.

**Why server state is owned by a server component or TanStack Query, never by `useState`.** The most
common class of frontend bug we see is a second source of truth: data fetched once, copied into
component state, and then wrong after every mutation. Server components remove the question for
read-only data; the query library answers it for interactive data with one cache, one invalidation
story and one place where staleness is configured. Picking both, with an explicit rule for which one
applies, is what prevents a codebase where three screens each solve caching differently.

**Why Tailwind with a token layer, not CSS Modules by default.** The failure mode we care about is not
"which syntax" — it is raw values leaking into feature code, where they are invisible to a rebrand,
to dark mode and to an accessibility audit. Tailwind's scale plus CSS variables makes the token the
path of least resistance: `bg-surface` is shorter to write than a hex, and an arbitrary value stands
out in review. CSS Modules stays the right answer for a component library published to other apps and
for complex stateful CSS, and a project that has already chosen it wins.

**Why react-hook-form + zod.** Uncontrolled fields mean typing in one field does not re-render the form,
and one zod schema produces the runtime check, the inferred type and the server-side validation. The
part worth stating is the second half: client validation is a convenience, never a control — the server
action or route handler parses the same schema again, because the endpoint is public no matter which
component calls it.

**Why next-intl and a CI drift check.** The App Router's server/client split makes i18n a bundle
question as well as a translation question: `next-intl` reads messages on the server and lets a client
component receive only the namespaces it needs. The enforcement matters more than the library — "add
the key to both files" survives about two sprints as a review rule, so the key sets are compared in CI
and a missing key or a dropped ICU argument fails the build.

**Why a Zustand default rather than context for shared client state.** Context re-renders every consumer
when its value identity changes, which makes it a poor fit for anything that changes often, and the
usual workaround is splitting a context into three. A store lets each component subscribe to the slice
it reads. Context keeps the job it is good at: injecting stable things — the query client, the theme,
the locale.

**Why the accessibility checklist is a rule set and not a "later pass".** Almost every item on it —
a real `button`, a label tied to an input, a focus ring, focus moved after navigation, an accessible
name on an icon-only control — costs nothing at authoring time and is expensive to retrofit across a
finished screen. Several of them are also directly load-bearing for tests: Testing Library's query
priority means a component that cannot be found by role usually has an accessibility bug.

**Project overrides.** Everything here is the default, not a mandate: a project may specify a different
structure or stack in its own `CLAUDE.md`, and the project wins. What the plugin guarantees is that the
default is a coherent whole rather than per-developer taste.
