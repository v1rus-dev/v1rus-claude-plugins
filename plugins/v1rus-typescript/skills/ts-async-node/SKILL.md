---
name: ts-async-node
description: |-
  Use when writing or reviewing async code in Node/TypeScript: promises, concurrency limits, AbortSignal and timeouts, streams, graceful shutdown, event-loop blocking, worker threads.
  Do NOT use for synchronous pure code or for profiling an existing slowness (ts-perf-profile).
---

# Async and Node runtime

Apply `${CLAUDE_PLUGIN_ROOT}/rules/ts-boundaries.md` (async section). Before using a recent built-in (`Promise.try`, `Array.fromAsync`, `AbortSignal.any`, `using`), probe the project's minimum Node line with a one-line `node -e` check, or check the Node docs.
- Design cancellation first: who owns the `AbortController`, where is the signal passed.
- Bound concurrency for any input of unknown size; choose `all` / `allSettled` / `any` deliberately.
- Shutdown path: stop accepting, abort, drain with a deadline, exit.
