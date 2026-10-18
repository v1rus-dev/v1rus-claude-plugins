---
name: react-component-conventions
description: "How a v1rus React component is designed and organised: composition over configuration and the children/slot pattern instead of a boolean-flag prop explosion, prop API design (narrow props, no prop drilling past two levels, event-handler naming, no spreading unknown props onto DOM elements), one component per file with the file named after it, where a component lives once it is used twice, controlled versus uncontrolled, custom hooks as the unit of reuse, and forwarding refs and class names on a design-system primitive. Load when creating a component, splitting one that grew too large, designing its props, extracting a custom hook, or reviewing component structure. Do NOT load for the mechanical traps — keys, effects, hooks order, hydration — those are in this layer's react.md rule, nor for state placement, which is react-state-management."
---

# React Component Conventions

The design-level conventions. The mechanical miss-list (render purity and hydration, derived state,
effects, hooks, keys, context identity, cancellation) lives in `${CLAUDE_PLUGIN_ROOT}/rules/react.md` and
is not repeated here — read it too when writing a non-trivial component.

## One component per file

- A file exports **one** component and is named after it (`OrderRow.tsx` exports `OrderRow`). Small
  private sub-parts used only by that component may live in the same file, below it.
- A component used by exactly one feature lives in that feature's `components/`. The moment a **second**
  feature needs it, it moves to `components/ui` — generalised, with the feature vocabulary stripped out
  (`web-architecture`).
- No barrel file that re-exports an entire folder: it defeats tree shaking and turns one import into a
  whole subtree in the bundle (`web-performance`). Export the public surface of a feature deliberately.

## Composition over configuration

A component that has grown `isCompact`, `showHeader`, `hideFooter`, `variantBordered` has stopped being
one component. The fix is composition, not another boolean.

```tsx
// configuration — every new case adds a prop and a branch
<Card title={t("orders")} action={<Button/>} footer={...} compact bordered />

// composition — the caller assembles, the component owns layout and tokens
<Card>
  <Card.Header>
    <Card.Title>{t("orders")}</Card.Title>
    <Button>{t("refresh")}</Button>
  </Card.Header>
  <Card.Body>{children}</Card.Body>
</Card>
```

- **Slots are props too.** A `ReactNode` prop (`icon`, `action`, `empty`) beats a `renderIcon` callback
  when the caller does not need arguments.
- `children` is the default slot. Prefer it to a `content` prop.
- A *variant* (visual kind: `primary`/`ghost`/`danger`, `sm`/`md`/`lg`) is a closed union prop, not a
  boolean per case, and it maps to tokens rather than to raw values (`web-styling`).
- Composition is also what keeps the server/client boundary low: a client shell that takes `children`
  leaves the content server-rendered (`web-architecture`).

## Prop API

- **Props are the component's public contract** — narrow and behavioural, not the raw server object.
  Passing the whole DTO couples the component to the API shape and re-renders it on unrelated field
  changes. Pass what is rendered.
- Two levels of prop drilling is fine and explicit. Past that, the value belongs in a provider, in the
  URL, or in a store (`react-state-management`) — or the tree needs composition so the value is passed
  as `children` from where it already exists.
- Event props are named `onX` and describe **what happened**, not what to do: `onSelect`, `onDismiss`,
  `onRetry` — not `handleClick` or `doSave`.
- **Do not spread unknown props onto a DOM element.** A design-system primitive extends the real element
  props (`ComponentPropsWithoutRef<"button">`) so the spread is typed; anything else silently forwards
  garbage attributes and swallows misspelled props.
- A design-system primitive **forwards its ref and merges `className`**, or it cannot be used inside a
  popover, a form library or a tooltip without a wrapper element that breaks the layout.
- Optional props get a real default, not `undefined` handled at three call sites. Boolean props default
  to `false` and read positively (`disabled`, not `notEnabled`).

## Controlled and uncontrolled

- A form field is controlled or uncontrolled for its whole life, never switched (`react.md`). Uncontrolled
  with the form library holding the value is the default for forms (`web-forms`).
- A reusable component that can be either exposes both: `value` + `onChange` for controlled use,
  `defaultValue` for uncontrolled — and picks the mode once, on first render.

## When to split a component

Split when one of these is true, not by line count alone:

- it renders more than one **state of the screen** (loading / empty / error / content) — each branch
  becomes its own component so no branch is forgotten (`web-ui-conventions`);
- part of it needs `"use client"` and the rest does not — split so the directive lands on the leaf;
- a part is rendered in a list — the row becomes a component so it can be memoised meaningfully
  (`web-performance`);
- a part is reused, or is the only thing a test wants to exercise.

Do **not** split into `renderHeader()` helper functions returning JSX inside the same component: they
re-run on every render, cannot be memoised, and do not show up as their own node in the tree or the
profiler. Extract a component instead.

## Custom hooks

- A custom hook is the unit of **logic** reuse; a component is the unit of **markup** reuse. A hook that
  returns JSX is a component wearing the wrong name.
- A hook is named for what it gives you (`useOrderFilters`, `useMediaQuery`), takes its inputs as
  arguments rather than reading context implicitly where that can be avoided, and returns a stable shape
  — an object with named fields, not a positional tuple beyond two elements.
- Keep a hook free of rendering decisions: it returns data and callbacks; the component decides markup.
- A hook that only wraps a single `useState` adds indirection, not reuse.

## Typing

- Type the props, do not type the component with a generic wrapper type (`FC`) — it adds nothing and has
  historically carried surprising `children` semantics.
- Prop unions model impossible states away: `{ status: "error"; error: AppError } | { status: "ok"; data: T }`
  beats three optional props (`v1rus-typescript:ts-type-modelling`).
- A component that renders user-supplied HTML sanitises it and says where the trust comes from
  (`react.md`).
