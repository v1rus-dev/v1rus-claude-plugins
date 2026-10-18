---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.mts"
  - "**/*.cts"
---

# TypeScript — non-obvious rules

Only what a model gets wrong or omits without a reminder. Generic idiomatic TypeScript — naming,
`const` over `let`, arrow functions, optional chaining, template literals — is not listed here;
the compiler, `typescript-eslint` and Prettier cover it.

## Types that lie

- **`any` is a defect, not a shortcut.** It does not fail at the `any`; it fails three call sites
  later, where the type system has already stopped looking. Use `unknown` and narrow.
- **`as` is an assertion, not a conversion.** `as` tells the compiler to stop checking; it proves
  nothing at runtime. Legitimate uses are narrow (a literal you just built, a value the compiler
  cannot see through). `as unknown as T` is the same lie with an extra step.
- **`!` (non-null assertion) is banned without a reason.** If the value cannot be null, model it so;
  if it can, handle it. A `!` that is wrong produces `undefined is not a function` far from the bug.
- **A type annotation on a value from outside the program is a wish.** `JSON.parse`, `await res.json()`,
  `process.env`, storage reads and message payloads are `any`/`unknown` at runtime regardless of what
  the signature says — parse them (`ts-boundaries-validation`).
- Type predicates (`x is T`) and assertion functions are unchecked assertions with nicer syntax: a
  wrong predicate body is silent. Prefer a schema parse; a hand-written predicate needs a test.

## Modelling

- **Discriminated unions over optional-field bags.** `{ status: 'ok'; data: T } | { status: 'error';
  error: E }` instead of `{ data?: T; error?: E; loading?: boolean }`, which permits states that
  cannot happen and forces defensive checks everywhere.
- **Every `switch` over a union ends with a `never` guard** so adding a variant breaks the build
  instead of falling through silently. `default: throw new Error('unknown')` does not do this.
- **`satisfies`, not `as`, and not a widening annotation**, when a literal must conform to a type but
  keep its narrow inferred shape.
- `readonly` and `as const` are the default for data that is not meant to change; `readonly` is
  shallow, which is a fact to state, not to ignore.
- A type parameter used exactly once is not a generic — it is an `any` with ceremony. Details and the
  rest of the modelling rules: `ts-type-modelling`.

## Boundaries

Every value entering the program from outside — HTTP, env, storage, files, message buses, third-party
callbacks, URL params — is parsed by a schema at the edge, once, and flows inward as a narrow type.
Nothing downstream re-validates and nothing downstream sees the raw shape. `ts-boundaries-validation`.

## Errors

- `catch (e)` binds `unknown` under strict settings. Narrow before using it; `e.message` should not
  compile, because the thrown value may be a string, `undefined`, or a `DOMException`.
- Wrap with context using `cause`: `new AppError('loading user failed', { cause: err })`. Never
  interpolate the original error into a message string — the stack and the type are what you need.
- **Never swallow.** An empty `catch`, or one that returns a default without a log or a typed error,
  is a defect. Do not log-and-rethrow at every level either: attach `cause`, handle once at the
  boundary (`v1rus-logging`).
- `return await` inside `try` is required for the `catch` to see the rejection — a bare `return`
  of a promise resolves the function before the rejection arrives.
- Expected, enumerable, caller-actionable failures at a boundary are returned as a typed result;
  programmer errors and broken invariants throw. `ts-error-handling` draws the line.

## Async

- **No floating promises.** Every promise is awaited, returned, or explicitly handed to something
  that reports its rejection. `array.forEach(async …)` drops every promise it creates.
- `await` inside a loop is either deliberate (ordering, rate limit, dependency between iterations) or
  an accidentally serialized fan-out. Make it obvious which.
- `Promise.all` fails fast but does not cancel the losers; `Promise.race` is not a timeout, it is a
  timeout *report*. Real cancellation is an `AbortSignal`, accepted as a parameter and propagated
  through every layer — never created fresh in the middle and the caller's dropped. `ts-async`.

## Modules

- `import type` / `export type` for anything used only in type position, and the compiler configured
  so a missed one is an error rather than a stray runtime import (`ts-project-config`).
- No deep imports into another package's internals, even when the path resolves. A package's public
  API is its `exports` map; a barrel file inside the package is a liability, not an API.
  `ts-package-structure`.
- An import cycle that typechecks still explodes at runtime as `undefined` during module init.

## Escapes

`// eslint-disable-next-line <rule> -- <reason>` and `@ts-expect-error -- <reason>`, one rule, one
line, always with the reason after `--`. Never `@ts-ignore` (it rots silently where
`@ts-expect-error` fails once it is unnecessary) and never a file-level blanket disable.
`ts-lint-and-format`.
