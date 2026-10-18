---
name: ts-error-handling
description: "Error handling in TypeScript the way a model does not write it by default: catch binds `unknown` and anything at all can be thrown, so narrow before using it; Error subclasses that carry a machine-readable code and wrap the original through `cause` instead of interpolating it into a message; why `instanceof` is unreliable across bundles and realms and a discriminant field is not; never swallowing and never log-and-rethrow at every level; `return await` inside try; AggregateError and aborts that must not be reported as failures; and the line between returning a typed Result at a boundary and throwing for a broken invariant. Load when writing or reviewing a catch block, designing an error type or error union, deciding whether a function should throw or return a failure, wrapping a third-party error, or adding an error path to an API client or a handler. Not for schema-parse specifics at the boundary (`ts-boundaries-validation`), promise concurrency and cancellation mechanics (`ts-async`), or what may be written to a log (`v1rus-logging`)."
---

# Errors

## `catch` binds `unknown`, and that is correct

With `strict` (specifically `useUnknownInCatchVariables`) the caught value is `unknown`, because
JavaScript can throw anything: a string, `undefined`, a `DOMException`, a rejected promise carrying a
plain object, a third-party "error" that is a bare `{ code: 500 }`.

```ts
try {
  await sync();
} catch (err) {
  // err.message does not compile — and should not.
  if (err instanceof AppError) return handle(err);
  throw new AppError('sync failed', { cause: err });
}
```

Never re-widen it (`catch (err: any)`, `err as Error`). If the code needs a message from an arbitrary
value, it needs one normalizer:

```ts
export function toError(value: unknown): Error {
  return value instanceof Error ? value : new Error(String(value), { cause: value });
}
```

One such helper, at the outermost boundary. Not a cast at every call site.

## Error types

```ts
export class AppError extends Error {
  readonly code: ErrorCode;                     // machine-readable, a literal union

  constructor(message: string, options: { code: ErrorCode; cause?: unknown }) {
    super(message, { cause: options.cause });
    this.name = new.target.name;                // otherwise every subclass reports "Error"
    this.code = options.code;
  }
}
```

- **`name` must be assigned** from `new.target.name` (or a literal in each subclass). Without it a
  subclass stringifies as `Error`, and every log line loses the type.
- **`cause` carries the original.** `new Error(\`failed: ${err}\`)` throws away the stack, the type
  and any structured fields, leaving `[object Object]` in a log. Pass the error, do not print it.
  The log formatter walks the `cause` chain — verify the project's logger actually does, because
  several do not by default (`v1rus-logging`).
- **Discriminate on a `code` field, not on `instanceof` alone.** `instanceof` fails when two copies
  of the same package are installed, across realms (worker, iframe, vm), and after some
  transpilation targets. A literal `code` compared in a `switch` also gives exhaustiveness
  (`ts-type-modelling`). Keep `instanceof` for the local, same-module case where it is honest.
- **The message is for engineers.** No user-facing copy, no localized strings, no personal data or
  tokens in the message or in attached fields. What the user sees is derived from `code` at the UI
  boundary.

## The rules that get broken

- **Never swallow.** An empty `catch {}`, or `catch { return null }` with no log and no typed
  failure, converts a diagnosable error into a blank screen. If an error is genuinely ignorable, say
  so in a one-line comment stating why.
- **Do not catch what you cannot handle.** A `try/catch` that logs and rethrows at every layer
  produces one incident reported five times and a stack that starts in the wrong place. Attach
  context via `cause`, let it propagate, handle once at the boundary that can actually decide.
- **`return await` inside `try`.** `return somePromise()` inside a `try` resolves the function before
  the rejection arrives, so the local `catch` never runs. Inside a `try`, always `return await`.
- **`finally` must not return or throw** — it discards the pending return value or the in-flight
  error. Use it only for cleanup.
- **An abort is not a failure.** When a caller cancels, the rejection (`AbortError`) is expected
  control flow: do not log it as an error, do not report it to the crash reporter, do not render an
  error state. Detect it explicitly and return (`ts-async`).
- **`Promise.all` rejects with the first error and loses the others**; `AggregateError` (from
  `Promise.any`, or constructed by hand) is the shape for "several things failed" — a single
  representative error hides the pattern.
- **An assertion function needs an explicit return-type annotation** (`function assert(c: unknown):
  asserts c { … }`) and cannot be an arrow function assigned to an inferred `const`, or the
  narrowing silently does nothing.

## Result versus throw

Both are correct; using one for everything is not.

| Situation | Shape |
|---|---|
| Expected, enumerable failure at a boundary that the caller must decide about — not found, unauthorized, validation rejected, network unreachable | return a typed result |
| Failure the caller cannot do anything about, at any depth — exhausted retries, corrupt state, unreachable branch | throw |
| Programmer error — invalid argument, broken invariant, impossible variant | throw, always; never model it as a returnable failure |
| Partial failure across several items | return per-item results (`ts-async`, `allSettled`), never one throw for the batch |

The shape, when a result is right, needs no library:

```ts
export type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };
```

Consumed with an exhaustive `switch` on `ok` and a `never` guard. Adopting a Result library instead
is a plan-stage dependency decision (`v1rus-dependencies`), not something to introduce mid-diff.

Two failure modes to avoid:

- **Result infection.** Once a Result crosses many internal layers, every signature carries it and
  people start writing the equivalent of `.unwrap()`, which is `!` with more characters. Keep
  results at boundaries; inside a module, throw.
- **Throwing for expected outcomes.** "User not found" is a normal answer to a lookup, not an
  exception. Modelling it as a throw means every caller either forgets the `catch` or writes one
  that cannot distinguish it from a network failure.

## The outermost boundary

Exactly one place per entry point converts an escaped error into a response, a log entry and a
report: the request handler, the job runner, the UI error boundary, the process-level unhandled
handler. Everything below it adds context and rethrows. Where that boundary is, and what the
framework provides for it, belongs to the platform layer; the discipline — one place, not five —
does not.
