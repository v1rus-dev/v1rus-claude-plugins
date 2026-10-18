---
name: kotlin-coroutines
description: |-
  On-demand depth for reviewing or designing Kotlin coroutine and Flow code: scope ownership, dispatcher injection, main-safety, cancellation propagation, Flow operator order, hangs from first()/receive(), and coroutine testing. Use when reviewing concurrency code, debugging a hang/leak/lost cancellation, or designing a repository/use case/state holder with Flow.
  Not for: routine edits of .kt files (the kotlin-coroutines rule injects itself on edit), UI lifecycle collection details (platform plugin rules), or non-Kotlin concurrency.
---

# Kotlin coroutines review

The rule text is `${CLAUDE_PLUGIN_ROOT}/rules/kotlin-coroutines.md`; read it in full before reviewing.

Review checklist, in order of production impact:
1. Every catch of `Exception`/`Throwable` or `runCatching` in suspend code lets `CancellationException` through.
2. No hardcoded dispatcher; suspend functions in data/domain are main-safe and callers do not wrap them.
3. No lifecycle-bound or application scope leaking into repositories/use cases.
4. `first()`/`single()`/`receive()` on sources that may not emit have a timeout or a `firstOrNull()`.
5. `retry` before `catch`; `flowOn` once at the producer; `stateIn` uses `WhileSubscribed` with a lifecycle-aware collector.
6. Tests: shared scheduler across test dispatchers, Main replaced when needed, no sleeps.

Report only real defects with file and line, each with a concrete fix. For performance angles (thread exhaustion, blocking main, `GlobalScope`), delegate to the `performance-expert` agent.
