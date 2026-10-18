---
name: react-state-management
description: "Where state lives in a v1rus web app: the four kinds (server, URL, client, form) and the decision table between them, why server state is owned by a server component or TanStack Query and never copied into useState where it goes stale, the URL as the default home for anything shareable or reloadable (filters, tabs, pagination, an open detail), Zustand for genuinely shared client state with context reserved for dependency injection, colocation and lifting only as far as needed, and resetting state with a key. Load when adding state to a component, choosing between useState / context / a store / the URL, fixing a stale or duplicated value, or reviewing a component that mirrors fetched data. Do NOT load for how the data is fetched or cached — that is web-data-fetching — or for form state mechanics, which is web-forms."
---

# State Management

Most state bugs on the web are placement bugs, not update bugs. Decide the **kind** first.

## The four kinds

| Kind | Examples | Owner |
|---|---|---|
| **Server state** | orders, profile, anything the backend is the source of truth for | a server component, or the query library — never `useState` |
| **URL state** | filters, sort, page, active tab, search text, an open detail id | `searchParams` / route segments |
| **Client state** | a dropdown being open, a hover, a wizard step, an unsent draft, a toast queue | `useState` at the lowest common owner, or a store when genuinely shared |
| **Form state** | field values, touched, errors, submitting | the form library (`web-forms`) |

Ask in that order. Most values a component reaches for `useState` for are one of the first two.

## Server state is never mirrored

```tsx
// wrong — a snapshot that goes stale the moment anything invalidates
const { data } = useOrders();
const [orders, setOrders] = useState(data);

// right — read it; if you need a derived view, derive it during render
const { data: orders } = useOrders();
const visible = useMemo(() => orders.filter(matchesFilter), [orders, filter]);
```

Copying fetched data into local state creates a second source of truth that no refetch, no invalidation
and no optimistic update can reach. The symptoms are always the same: a value that is correct on first
load and wrong after any mutation, and a "refresh" button that fixes it.

The two cases that look like exceptions:

- **An edit form seeded from server data** — that is form state, owned by the form library, initialised
  from the query and **reset by `key` when the entity id changes** (`react.md`). Never patched with an
  effect.
- **An optimistic update** — belongs to the mutation's optimistic cache update, not to a local copy
  (`web-data-fetching`).

## URL first for anything shareable

If reloading the page or sharing the link should reproduce what the user sees, it is URL state. Filters,
sort, pagination, the active tab, a search query and an open detail panel all qualify.

- Read with the framework's `searchParams` (on the server, it is just a prop to the page; on the client,
  the hook), write with a router replace so the back button is not filled with keystrokes.
- Keep keys short and stable (`?status=open&page=2`), omit defaults rather than writing `?page=1`, and
  validate the incoming params with the boundary schema — a URL is user input
  (`v1rus-typescript:ts-boundaries-validation`).
- When filters are applied but the controls are off-screen, the UI must show an active-filter indicator
  (`web-ui-conventions`) — otherwise the user sees a short list and assumes there is no data.
- Do not duplicate a URL value into state "for speed". The URL is the state.

## Client state, placed as low as possible

- Start in the component that uses it. Lift only to the nearest common owner of the components that
  genuinely need it, and no further — lifting a dropdown's open flag to a page re-renders the page.
- Two pieces of state that always change together are one piece of state (a status union, not three
  booleans — `v1rus-typescript:ts-type-modelling`). `isLoading && isError` is a state that should not
  be representable.
- Use `useReducer` when transitions have rules; keep the reducer pure and test it directly — it is the
  cheapest unit test in the app.
- Reset by `key`, not by effect.

## Shared client state: a store, not context

**Default: Zustand** for client state that several distant components read or write — a cart, a
multi-step wizard, a selection, a toast queue, an open-modal registry.

- Context re-renders **every** consumer whenever the value identity changes, so it is a poor state
  manager for anything that changes often; a store lets each component subscribe to the slice it reads.
- Keep the store to client concerns. A store holding fetched entities is server state in disguise and
  goes stale exactly as `useState` does.
- One store per bounded concern with selectors, rather than one global object everything imports.
- The store is created per request/per app instance where server rendering is involved — a module-level
  singleton mutated during SSR leaks one user's state into another's response.

**Context is for dependency injection**: the query client, the theme, the locale, a feature flag set, a
store handle — values that are created once and rarely change. Memoise the value and split state from
dispatch (`react.md`).

## What each choice costs

| Choice | Cost to know |
|---|---|
| Server component | no client bundle, but no interactivity — re-reads require a navigation or revalidation |
| Query library | cache correctness is yours: keys, staleness, invalidation (`web-data-fetching`) |
| URL | serialisable values only, and every write is a navigation |
| Store | global reach, so discipline is manual; easy to become a cache by accident |
| Context | simple, but a wide fast-changing context re-renders the subtree |
| `useState` | invisible to everything else — including tests, deep links and the back button |
