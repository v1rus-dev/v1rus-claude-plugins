---
paths:
  - "**/*.{ts,tsx,mts,cts,js,mjs,cjs}"
---

# TypeScript/JavaScript source: I/O boundaries, errors, async, security

## Validate at the edge
- Types are erased. Everything crossing a trust boundary (HTTP, env, files, DB rows, queue messages, `JSON.parse`, third-party responses, CLI args) is `unknown` until a runtime check passes. Parse once at the edge into a domain type; pass trusted types inward. No re-validation in hot internal paths.
- One source of truth: define the schema, infer the type. Use the schema library the project already has. No schema library yet: adding one is a dependency decision (see the `ts-supply-chain` skill and the plan-stage gate); a hand-written guard is fine for tiny surfaces. Libraries should accept Standard Schema-compatible schemas instead of importing a specific validator.
- Read `process.env` once, in one config module, into a typed frozen object; fail fast listing all issues. No scattered `process.env` reads.
- Reject or strip unknown keys deliberately (strict for inbound requests). No silent coercion of query strings. Validation errors map to a typed 4xx/domain error without echoing secrets.
- `const v: unknown = JSON.parse(s)`; never let `any` from `JSON.parse` / `res.json()` flow on.

## Errors
- Throw `Error` subclasses only. Preserve the cause: `new DomainError('msg', { cause: err })`. Wrap at layer boundaries; log once at the edge, do not log-and-rethrow at every layer.
- Typed errors carry a stable string `code`; consumers branch on `code` or `instanceof`. Document with TSDoc `@throws`.
- `catch (e)` is `unknown`: narrow with `instanceof Error` (or `Error.isError` where the runtime has it, for cross-realm errors). Never `catch (e: any)`.
- Expected domain failures the caller must handle (parse, not-found, permission): a plain discriminated-union result `{ ok: true, value } | { ok: false, error }` (no library). Exceptions for programmer and unrecoverable errors. Do not mix the two styles across one module boundary.
- No empty `catch {}` and no catch-just-to-log. `return await` inside `try` so the `catch` sees the rejection. `AggregateError` for multiple failures.
- Process-level `unhandledRejection` / `uncaughtException` handlers only log and exit non-zero.
- Errors crossing process boundaries are serialised data (`{code, message, details}`), never stacks to clients.

## Async
- No floating promises: await, return, `.catch`, or explicit `void` with a comment. No promise in `if` or in a void-returning callback.
- Cancellation: long or I/O operations accept `{ signal }: { signal?: AbortSignal }`; combine with `AbortSignal.timeout(ms)` / `AbortSignal.any([...])`; pass the signal into `fetch`, streams, `node:timers/promises`, `node:fs/promises`. No custom cancel tokens.
- `Promise.all` is fail-fast and does not cancel the rest (use a shared `AbortController`); `allSettled` when every outcome is needed; `any` for first success; `race` for timeouts only if the loser is cancelled. Never `Promise.all` over unbounded input: bound concurrency.
- Sequential `await` in a loop only when order or dependency requires it.
- Do not block the event loop on request paths: no sync fs/crypto/zlib/`execSync`, no parsing of huge JSON; CPU-bound work goes to `worker_threads`, a child process or a queue.
- Streams: `pipeline` from `node:stream/promises` (error propagation, abort), async iteration, respect backpressure; never read a large file whole.
- Timers: `node:timers/promises` where abortable; clear or `unref` long-lived timers. Event emitters always get an `'error'` listener.
- Graceful shutdown: on SIGTERM/SIGINT stop accepting, abort in-flight work through a shared controller, drain with a deadline, exit.

## Security (see the `ts-security-checklist` skill for review)
- No SQL/shell/HTML/path built by string concatenation: parameterised queries; `execFile`/`spawn` with an argument array (never `exec` with interpolation, never `shell: true` with user data); `path.resolve` plus a prefix check (and `realpath` for symlinks); `URL`/`URLSearchParams`; allowlists for server-side fetches.
- No recursive merge of untrusted objects into plain objects (`__proto__`, `constructor`, `prototype`); use `Map` or `Object.create(null)` for user-keyed dictionaries, `Object.hasOwn`.
- No user-influenced regex and no quadratic patterns on user input; bound input length first; escape embedded user text.
- Secrets never in source, logs, errors or client bundles. `node:crypto`/WebCrypto only, `timingSafeEqual` for secret comparison, `randomBytes`/`randomUUID` (never `Math.random`) for tokens. Algorithm/key-management choices are a policy decision: escalate, do not pick silently.
- No `eval`, `new Function`, string `setTimeout`, `vm` for untrusted code.
