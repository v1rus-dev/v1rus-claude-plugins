---
paths:
  - "**/*.kt"
---

# Kotlin coroutines and Flow: non-obvious rules

Only rules a model omits or gets wrong without a reminder. Basic structured concurrency, `async`/`await`, `flow {}` builders, immutable `StateFlow` exposure and no empty `catch` are assumed known.

## Scope ownership by layer

| Layer | Scope | Why |
|---|---|---|
| UI-layer state holder (ViewModel or equivalent) | its own lifecycle scope | cancelled with the screen/holder |
| Use case / repository | none: inherits the caller's | caller controls cancellation |
| Work that must outlive a screen | injected application-scoped `CoroutineScope` | completes even if the user navigates away |

Never inject an application-wide scope into a repository to launch ad-hoc work.

## Dispatchers

- Inject `CoroutineDispatcher` through the constructor; do not hardcode `Dispatchers.IO` inside `withContext`, it makes the class untestable.
- Every `suspend fun` in data/domain is main-safe: it picks its dispatcher with an internal `withContext`. Callers do not wrap it in `withContext`.

```kotlin
class DefaultOrderRepository(
    private val api: OrderApi,
    private val dispatcher: CoroutineDispatcher,
) : OrderRepository {
    override suspend fun getOrders(): List<Order> =
        withContext(dispatcher) { api.getOrders().map { it.toOrder() } }
}
```

## StateFlow / SharedFlow sharing

`stateIn(scope, SharingStarted.WhileSubscribed(5_000), initial)` is the right default for screen-scoped state, and it only stops the upstream if the collector is lifecycle-aware (platform rules cover how). `Eagerly` wastes resources unless the state is always needed; `Lazily` never stops once started.

## Operator gotchas

- `flowOn` affects only upstream operators; apply it once, at the producer side.
- `retry { }` goes BEFORE `catch { }`; otherwise `catch` consumes the error and `retry` never sees it.

## Avoiding indefinite suspension

`first()`, `single()`, `Channel.receive()` wait forever if the source never emits.

| Source | Risk | Mitigation |
|---|---|---|
| `StateFlow` | none | none |
| `SharedFlow(replay > 0)` | low | `withTimeout` for rare events |
| `SharedFlow(replay = 0)` | high | always `withTimeout` |
| `Channel` | high | `tryReceive()` or `withTimeout` |
| cold `flow {}` | depends on producer | `withTimeout` if it may not emit |

Use `firstOrNull()` when absence is a valid outcome.

## Cancellation

- Every `catch` of `Exception`/`Throwable` in suspend code re-throws `CancellationException` first.
- Bare `runCatching` swallows `CancellationException`; use explicit `try/catch`, or re-throw inside `onFailure`.
- `withContext(NonCancellable)` only inside `finally` for cleanup that must finish during cancellation; anywhere else it disables cooperative cancellation.

```kotlin
try { api.fetchData() }
catch (e: CancellationException) { throw e }
catch (e: Exception) { handleError(e) }
```

## Error mapping

Do not leak transport/storage exceptions (HTTP, SQL, engine-specific) past the data layer. Map them at the data to domain boundary into a project error type or `Result<T>`.

## Testing

1. All test dispatchers in one test share one scheduler (pass the same `TestCoroutineScheduler`), otherwise `advanceUntilIdle()` does not propagate.
2. Replace `Dispatchers.Main` (`setMain` before, `resetMain` after) before testing anything that uses a lifecycle scope backed by Main.
3. `UnconfinedTestDispatcher` runs eagerly (simple assertions); `StandardTestDispatcher` queues, advance with `advanceUntilIdle()`/`runCurrent()` when ordering matters.
4. Assert Flows with a Flow-testing helper if the project already has one (Turbine-style `test { awaitItem() }`); never wait with `delay()` or `Thread.sleep()`.
