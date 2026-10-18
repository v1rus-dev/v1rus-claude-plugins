---
name: web-performance
description: "Performance work on a v1rus web app, in the order that actually pays: keeping the client bundle small by placing the \"use client\" boundary at the leaves, avoiding barrel-file and heavy-library imports, dynamic import for what is not needed at first paint, images through next/image with explicit dimensions and fonts that do not shift the layout, streaming with Suspense instead of one page-level spinner, removing fetch waterfalls, and only then memoisation — why memo and useMemo often do nothing, what actually causes a re-render, and splitting a context instead. Load when a page is slow or heavy, before adding memo or useMemo, when a bundle grows, when Lighthouse flags CLS or LCP, or when reviewing a long list. Do NOT load for caching and invalidation semantics — that is web-data-fetching."
---

# Web Performance

Measure, then fix, and fix in this order: **ship less JavaScript → render sooner → re-render less**.
Memoisation is last because it is the cheapest to add and the least likely to matter.

## 1. Ship less JavaScript

- **The `"use client"` boundary is the bundle boundary.** A directive at the top of a layout or page
  pulls that whole subtree — and everything it imports — into the browser. Push it to the interactive
  leaf; this single decision moves more bytes than every other item on this page
  (`${CLAUDE_PLUGIN_ROOT}/rules/next-app-router.md`).
- **Barrel files are a bundle trap.** `import { Button } from "@/components"` can drag the entire folder
  in when anything in the chain has a side effect and tree shaking gives up. Import from the module.
- Check the weight of a dependency before adding it (`v1rus-core:v1rus-dependencies`): a date library,
  an icon set imported wholesale, a charting library or a rich editor can be larger than the rest of the
  app. Prefer the platform (`Intl`, `URLSearchParams`, `structuredClone`) and a subpath import over a
  whole package.
- **Dynamic-import what is not needed at first paint** — a modal's body, a chart, an editor, an
  onboarding tour — with a placeholder that reserves its space. Mark genuinely browser-only widgets as
  such so they are not server-rendered at all.
- Keep polyfills to the browser matrix the project actually supports.

## 2. Render sooner

- **Stream.** Put a slow, independent section behind its own `<Suspense>` with a skeleton, so the fast
  part of the page reaches the user immediately. One page-level `loading.tsx` makes the whole page wait
  for its slowest query.
- **Remove waterfalls.** Sequential `await`s and an `await` inside a `map` are the most common cause of
  a slow page; `Promise.all` and a batched query fix them (`web-data-fetching`).
- **Images**: `next/image` with explicit `width`/`height` or `fill` inside a sized box, `sizes` set to
  what the layout actually uses, `priority` only on the LCP image, and a modern format. An image without
  dimensions is the classic layout-shift bug, and a full-resolution hero is the classic LCP bug.
- **Fonts**: self-host through the framework's font loader with a size-adjusted fallback so swapping does
  not reflow, and subset to the character sets in use. A late-loading web font is both a shift and a
  flash.
- **Reserve space for everything that arrives late** — embeds, banners, async content. Cumulative layout
  shift is a UX bug the user feels as a mis-tap.
- Prefetching is a trade: helpful on a small page, wasteful on a list of hundreds of links
  (`web-routing`).

## 3. Re-render less

Only after the first two, and only with a profile in hand.

**What actually causes a re-render:** the component's own state changed, its context value changed
identity, or its parent re-rendered. Props being "different objects" does **not** cause a re-render on
its own — it only prevents `memo` from skipping one.

- `memo` does nothing unless the component is re-rendered by its parent **and** its props are
  referentially stable. Wrapping a component whose parent passes a fresh inline object or callback each
  render adds a comparison and changes nothing.
- `useMemo` / `useCallback` cost an allocation and a dependency comparison on every render. They earn
  their place when the value is (a) an expensive computation, (b) a dependency of an effect, or (c) a
  prop of a memoised child or a context value. Otherwise they are noise that hides the real problem.
- **Prefer restructuring to memoising**: move state down into the component that owns it, pass expensive
  subtrees as `children` so they are not re-created by the parent's render, and split a context into a
  slow-changing state context and a stable actions context (`react-state-management`).
- A list row that re-renders on every keystroke elsewhere is usually a state-placement bug, not a
  missing `memo`.
- Where the project uses the React compiler, hand-written memoisation is mostly redundant — check what
  the project has configured before adding any.

## Lists

- Paginate by default. Virtualise only when the visible set is genuinely large, and accept the cost:
  find-in-page, anchor links and screen-reader traversal all get harder.
- Hoist per-row work out of the row: format dates, derive labels and build maps once in the parent or
  the data layer, not inside the row's render.
- The loading tail is part of the list, not a dialog over it (`web-ui-conventions`).
- A stable `key` from the data is a correctness rule first and a performance rule second
  (`${CLAUDE_PLUGIN_ROOT}/rules/react.md`).

## Measuring

- **Never optimise from intuition.** Get a number first: the framework's bundle analyzer for weight,
  Lighthouse or field Core Web Vitals for LCP / CLS / INP, the React Profiler (or the DevTools
  "highlight updates" option) for re-renders, and the network panel for waterfalls.
- Measure a **production build**. Development mode double-renders under Strict Mode, skips
  minification, and is not evidence of anything.
- State the before and after numbers when reporting a performance change — a win without a measured
  delta is a claim (`v1rus-core:v1rus-workflow`).
- Regressions are cheapest to catch mechanically: a bundle-size budget in CI beats noticing in a review.
