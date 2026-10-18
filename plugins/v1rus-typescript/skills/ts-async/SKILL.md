---
name: ts-async
description: "Asynchronous TypeScript beyond async/await basics: floating promises and why `void promise` silences the linter rather than the rejection, async callbacks passed to forEach and other void-returning slots, deliberate versus accidentally serialized awaits in a loop and bounded concurrency for unbounded input, choosing between Promise.all, allSettled, any and race and why race is not a timeout, AbortSignal accepted as a parameter and propagated through every layer with AbortSignal.timeout and AbortSignal.any, cooperative cancellation checks, aborts that must not surface as errors, async cleanup with try/finally and await using, the async promise-executor trap, stale-response race conditions, and single-flight promise caching. Load when writing or reviewing concurrent work, a fetch or client wrapper, a loop containing await, cancellation or timeout handling, a debounced or racing request, resource cleanup in async code, or when a lint reports a floating or misused promise. Not for error type design (`ts-error-handling`) or runtime-specific scheduling and server lifecycle, which belong to the platform layer."
---

# Async

## Floating promises

**Every promise is awaited, returned, or explicitly handed to something that reports its rejection.**
A promise nobody holds is an error nobody sees, and in a modern Node runtime an unhandled rejection
terminates the process by default — so a floating promise is not a style issue, it is an outage with
no stack pointing at the caller.

```ts
saveDraft(doc);                        // floating — the failure vanishes
await saveDraft(doc);                  // awaited
return saveDraft(doc);                 // returned — the caller owns it
void saveDraft(doc).catch(reportError) // deliberately detached, with a handler
```

`void saveDraft(doc)` **alone is not a fix** — it satisfies the lint rule and leaves the rejection
exactly as unhandled as before. `void` is only acceptable when a `.catch` is attached, or the call
is handed to a runner whose job is to report failures.

The rule is enforced by `@typescript-eslint/no-floating-promises`, which requires type-aware linting
(`ts-lint-and-format`). Without type-aware linting, this class of bug is not detectable at all.

## Async functions in void-returning slots

```ts
items.forEach(async (item) => { await save(item); });   // wrong, twice over
```

`forEach` ignores the returned promise: the loop does not wait, the writes overlap in an undefined
order, and any rejection is unhandled. The same trap applies everywhere a callback's return value is
discarded — event listeners, timer callbacks, and anything typed `() => void`.

```ts
for (const item of items) await save(item);             // sequential, deliberate
await Promise.all(items.map((item) => save(item)));     // concurrent, deliberate
```

`@typescript-eslint/no-misused-promises` catches the general case.

## `await` in a loop

Sequential awaiting is a decision, and the reader must be able to tell that it was made:

- **Deliberate** when iterations depend on each other, when order matters, when a rate limit or a
  transaction requires it, or when memory forbids holding all results. Say so in a comment if it is
  not obvious from the code.
- **Accidental** when N independent requests are serialized and the endpoint latency is multiplied
  by N. That is the common case in generated code.

For concurrency over **unbounded** input, do not map the whole array into promises — firing ten
thousand requests at once is a different failure. Bound it: a fixed-size worker loop over a shared
iterator, a chunked loop, or the project's existing concurrency limiter (a new one is a dependency
decision, `v1rus-dependencies`).

## Choosing the combinator

| Combinator | Semantics and the catch |
|---|---|
| `Promise.all` | Rejects on the first failure. The others **keep running**; their rejections become unhandled unless already attached. Right when partial results are useless. |
| `Promise.allSettled` | Never rejects; returns per-item status. Right whenever partial success is meaningful — and then the failures must actually be inspected, not filtered away silently. |
| `Promise.any` | First fulfilment wins; rejects with an `AggregateError` only if all fail. For redundant sources. |
| `Promise.race` | First settlement wins — **and the loser keeps running**. A `race` against a timer reports a timeout; it does not cancel anything. For real cancellation use an `AbortSignal`. |

## `AbortSignal`

Cancellation is a parameter, not a global:

```ts
export async function loadDashboard(
  userId: UserId,
  { signal }: { signal?: AbortSignal } = {},
): Promise<Dashboard> {
  const [profile, orders] = await Promise.all([
    fetchProfile(userId, { signal }),
    fetchOrders(userId, { signal }),
  ]);
  return { profile, orders };
}
```

- **Accept a signal and pass it down through every layer.** A function that creates its own signal
  and ignores the caller's makes the whole call tree uncancellable.
- **Compose instead of choosing**: `AbortSignal.timeout(ms)` for a deadline, `AbortSignal.any([a, b])`
  to combine the caller's signal with a local one.
- **Cancellation is cooperative.** An `await`-free CPU loop, or a sequence of steps after the fetch,
  will not stop by itself: check `signal.aborted` (or `signal.throwIfAborted()`) between steps in
  anything long-running.
- **An abort is not a failure** (`ts-error-handling`): do not log it, report it, or render an error
  state. Check for it explicitly before the generic error path.
- Event listeners registered with `{ signal }` are removed on abort — the cleanest way to unsubscribe
  a whole group at once.

## Cleanup

- Anything acquired in async code is released in `finally`, including on the abort path.
- `await using` with `Symbol.asyncDispose` makes the release scope-bound and is the better shape for
  resources with a clear lifetime. It requires TypeScript 5.2 or newer and a runtime polyfill of the
  disposable symbols — below that the mechanism does not exist.
- Timers are cleared on every exit path; a pending `setTimeout` keeps a handle alive and can fire
  against state that is gone.

## Traps

- **`new Promise(async (resolve, reject) => { … })`** — a throw inside the async executor is
  swallowed and the promise hangs forever. If the body is async, it does not need the constructor.
- **A constructor cannot `await`.** An object requiring async setup gets a static async factory, not
  a constructor that kicks off work and hopes.
- **Stale responses.** Two overlapping requests for the same view resolve out of order and the older
  answer wins. Either abort the previous request before starting the next, or tag each request and
  drop a response whose tag is no longer current. This is the standard search-as-you-type bug and it
  is invisible on a fast connection.
- **Single-flight caching caches the promise, not the result** — otherwise N concurrent callers each
  start their own request before the first resolves. Delete the entry on rejection, or the cache
  memoizes the failure permanently.
- **`await` in a hot path over a synchronous value** still yields to the microtask queue. Rarely
  matters; when it does, it matters in a loop.
