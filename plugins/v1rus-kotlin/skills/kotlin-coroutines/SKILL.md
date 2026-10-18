---
name: kotlin-coroutines
description: "Kotlin coroutine and Flow rules a model gets wrong without a reminder: scope ownership per layer (a repository owns no scope), CoroutineDispatcher injected via constructor instead of a hardcoded Dispatchers.IO, suspend functions are main-safe so callers never wrap them in withContext, stateIn + WhileSubscribed paired with lifecycle-aware collection, flowOn/retry/catch ordering, indefinite suspension on first()/receive(), CancellationException must be rethrown (and bare runCatching is banned in suspend code), withContext(NonCancellable) only in finally, error mapping at layer boundaries, and the TestDispatcher/Turbine testing rules. Load when writing or reviewing suspend functions, Flows, ViewModels, repositories, or coroutine tests."
---

# Kotlin Coroutines & Flow

The full rulebook is `${CLAUDE_PLUGIN_ROOT}/rules/coroutines.md` — **read it** before writing or
reviewing coroutine or `Flow` code. Same single source as the `path-rules` hook injects on a `.kt`
edit, so it may already be in context.

Generic structured-concurrency basics are deliberately absent; the file covers only the recurring
mistakes. The three that cause production bugs:

- **`CancellationException` must propagate.** Any `catch (e: Exception)` in suspend code rethrows it
  first, and bare `runCatching { }` is banned in suspend code because it swallows cancellation.
- **`retry { }` goes before `catch { }`.** With `catch` first the error is consumed and `retry` never
  runs.
- **`first()` on a `SharedFlow(replay = 0)` or a `Channel` can hang forever.** Wrap in
  `withTimeout`, or use `firstOrNull()` when absence is a valid outcome.
