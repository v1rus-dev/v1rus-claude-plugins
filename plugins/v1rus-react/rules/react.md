---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/hooks/**/*.ts"
  - "**/use-*.ts"
---

# React — non-obvious rules

Only what a model gets wrong or omits without a reminder. Generic idiomatic React — naming, destructured
props, fragment syntax, `map` over a list — is not listed here; `eslint-plugin-react` and
`eslint-plugin-react-hooks` cover it. TypeScript-level rules (`any`, discriminated unions, `unknown` at
boundaries, floating promises) belong to `v1rus-typescript` and are not repeated here.

## Render must be pure and deterministic

- **No `Date.now()`, `new Date()`, `Math.random()`, `crypto.randomUUID()`, `window`, `localStorage` or
  `navigator` read during render.** On a server-rendered page the server and the client compute different
  markup and React throws away the whole subtree with a hydration error. Derive such values in an event
  handler, in an effect, or pass them in as props from a single source.
- No mutation during render: do not push into a prop array, do not assign to a ref, do not call a setter.
  A ref is read and written in handlers and effects, never while rendering.
- Anything conditionally client-only (a saved theme, a viewport measurement) renders the server-safe
  variant first and upgrades after mount, or is loaded with a client-only dynamic import.

## Derived state

- **Do not copy a prop or query result into `useState`.** `const [items, setItems] = useState(props.items)`
  freezes the first value; every later prop change is silently ignored. Compute it during render instead.
- Do not `useEffect` + `setState` to keep two pieces of state in sync — that is a second render pass and a
  visible flash. Calculate during render; `useMemo` only when the computation is actually expensive.
- When a value must reset because the entity changed, **give the component a `key`** (`<Editor key={id} />`)
  rather than clearing fields in an effect.

## Effects — usually the wrong tool

| You want to | Do not | Do |
|---|---|---|
| transform data for rendering | effect + state | compute during render |
| react to a user action | effect watching state | put the logic in the event handler |
| fetch data on mount | `useEffect` + `fetch` + `setState` | a server component, or the query library (`web-data-fetching`) |
| reset state on prop change | effect clearing state | `key` on the component |
| notify the parent of a change | effect on state | call the callback in the same handler that changed it |

An effect is right for **synchronising with something outside React**: a subscription, a browser API, a
media query, an imperative widget, an analytics beacon. Everything else is a smell.

- **Every effect that starts something returns a cleanup** that stops it: unsubscribe, `clearTimeout`,
  `removeEventListener`, `controller.abort()`. Under Strict Mode effects run twice in development
  precisely to expose a missing cleanup — do not "fix" the double-run by adding a mounted flag.
- Never lie to the dependency array. A disabled `react-hooks/exhaustive-deps` needs a comment explaining
  why the omitted value cannot change; the usual real fix is a ref, a functional setter, or hoisting the
  function out.

## Hooks

- Hooks run unconditionally at the top level — never inside a condition, loop, `try`, or after an early
  `return`. Branch **inside** the hook, not around it.
- A custom hook is named `useX` and may call hooks; a plain helper must not.
- `useState` initialisers and `useRef` arguments are evaluated on **every** render: pass a function
  (`useState(() => expensive())`) when the initial value costs anything.
- A `ref` is not reactive: writing to it does not re-render, and reading it during render is undefined
  behaviour for concurrent rendering.

## Lists and keys

- A `key` is the identity of the row, so it must come from the data: an id, not the array index and not
  `Math.random()`. An index key on a list that can reorder, filter, sort or prepend attaches the wrong
  state (input value, focus, scroll, animation) to the wrong row.
- A key only has to be unique among siblings, and it is never read as a prop — pass the id again if the
  child needs it.

## Context and re-renders

- **A context value object created inline re-renders every consumer on every parent render.** Memoise the
  value (`useMemo`) or, better, split the context in two: one for rarely-changing state and one for the
  stable dispatch/action handle.
- Context is for dependency injection of stable things (theme, locale, a store handle, a client). It is
  not a state manager: high-frequency values in a wide context re-render the whole subtree
  (`react-state-management`).

## Forms and controls

- An input is controlled (`value` + `onChange`) or uncontrolled (`defaultValue`), never switched between
  the two — React warns and the field loses its state. `value={maybeUndefined}` is the usual cause.
- Every input has a real label associated with it; a placeholder is not a label (`web-ui-conventions`).

## Events and the DOM

- An interactive element is a `button`, `a`, `input` or `summary` — never a `div` with `onClick`
  (`web-ui-conventions`).
- Attach global listeners in an effect with a cleanup, never in render. Use the element's own handler in
  preference to a document-level listener.
- `dangerouslySetInnerHTML` requires sanitised input and a one-line comment saying where the trust comes
  from; otherwise it is an XSS hole.

## Async in components

- An async operation started in a component is cancelled when the component unmounts or the input changes
  — pass the `AbortSignal` down (`v1rus-typescript:ts-async`). An un-cancelled request that resolves after
  unmount updates nothing and hides a race: the slower of two in-flight requests can win.
- Never `await` in render, and never mark a component function `async` unless it is a server component.
