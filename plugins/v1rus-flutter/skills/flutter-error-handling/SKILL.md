---
name: flutter-error-handling
description: "Error handling across the v1rus Flutter layers: a hand-written sealed Result<T> with Ok and Err living in core with no external dependencies, a hand-written sealed AppError union in domain, repositories returning Result carrying a domain AppError, DioException and Drift and platform exceptions mapped inside the data layer and never escaping it, exhaustive switch consumption in the Bloc, and the rules for what is a recoverable AppError versus a programmer error that should throw. Load when writing a repository, mapping a network or database failure, deciding between throwing and returning, or adding an error state to a screen."
---

# Error Handling

## `Result<T>` — hand-written, in `core`, no dependencies

This is the shape the official Flutter architecture guidance prescribes, and it is deliberately
hand-written: the type at the foundation of every repository signature must not be something a third
party can break or abandon.

```dart
// core/result/result.dart
sealed class Result<T> {
  const Result();
}

final class Ok<T> extends Result<T> {
  const Ok(this.value);
  final T value;
}

final class Err<T> extends Result<T> {
  const Err(this.error);
  final AppError error;
}
```

Why a `Result` rather than exceptions: **the failure is visible in the signature**. A forgotten
`try/catch` compiles and crashes in production; a forgotten `Err` branch is a non-exhaustive `switch`
and fails to compile.

## `AppError` — the domain vocabulary of failure

`AppError` lives in `domain` (it is part of the contract a repository interface promises) and is a
hand-written sealed union with `Equatable` — no generator, same reasoning as `Result` (`flutter-codegen`).
It describes failures **in terms the app cares about**, not in terms of the transport.

```dart
// domain/errors/app_error.dart
sealed class AppError extends Equatable {
  const AppError();

  @override
  List<Object?> get props => const [];
}

final class NetworkError extends AppError {        // no connectivity, timeout
  const NetworkError();
}

final class UnauthorizedError extends AppError {   // 401 after refresh failed
  const UnauthorizedError();
}

final class NotFoundError extends AppError {       // 404
  const NotFoundError();
}

final class ValidationError extends AppError {
  const ValidationError(this.fields);
  final Map<String, String> fields;

  @override
  List<Object?> get props => [fields];
}

final class ServerError extends AppError {
  const ServerError({this.status, this.message});
  final int? status;
  final String? message;

  @override
  List<Object?> get props => [status, message];
}
```

Plus `ForbiddenError`, `StorageError` and `UnknownError({Object? cause})` in the same shape. `AppError`
carries value equality because it is reachable from Bloc state, and a state whose error differs must not
compare equal (`bloc-conventions`).

`AppError` carries **no localised text**. A message shown to a user is resolved in the widget from a
string resource keyed by the error case (`flutter-localisation`); a server-provided free-form message is
carried as data and displayed verbatim.

## Mapping happens in `data`, and only there

```dart
// data/repositories/order_repository_impl.dart
@override
Future<Result<Order>> getOrder(String id) async {
  try {
    final dto = await _api.getOrder(id);
    return Ok(dto.toEntity());
  } on DioException catch (e, s) {
    _logger.warn('getOrder failed', error: e, stackTrace: s);
    return Err(e.toAppError());
  } on FormatException catch (e, s) {
    _logger.error('getOrder response malformed', error: e, stackTrace: s);
    return Err(const ServerError());
  }
}
```

Non-negotiable: **no `DioException`, Drift exception, `PlatformException`, `SocketException` or
`FormatException` ever leaves the data layer.** A `domain` or `features` file that catches a `Dio`
type is an architecture violation — `import_lint` blocks the import, and the review catches the rest.

Put the transport→domain mapping in one place (`data/network/dio_error_mapper.dart` as a
`DioException.toAppError()` extension) rather than repeating a `switch` in every repository.

## Consuming a `Result`

```dart
Future<void> _onStarted(OrderListStarted event, Emitter<OrderListState> emit) async {
  emit(const OrderListLoading());
  switch (await _repository.getOrders()) {
    case Ok(:final value):
      emit(value.isEmpty ? const OrderListEmpty() : OrderListContent(value.toUi()));
    case Err(:final error):
      emit(OrderListError(error));
  }
}
```

Rules:

- **Switch exhaustively; never `is Ok` plus a cast.** The exhaustiveness check is the whole benefit.
- Never `(result as Ok).value`. A cast reintroduces the runtime failure the type removed.
- Do not collapse an error to a bool. `if (result is Err) return;` throws the diagnosis away — the user
  gets a blank screen and the log gets nothing.

## Result versus throwing — where the line is

| Situation | What to do |
|---|---|
| Expected, recoverable failure the user can be told about — network, 4xx, storage, validation | return `Err(<AppError case>)` |
| Programmer error — invalid argument, broken invariant, unreachable branch | `throw ArgumentError` / `StateError`; do not model as `AppError` |
| Cancellation of work whose screen is gone | let it complete or be dropped; never surface as an error state |
| A failure that must be visible but not blocking (background sync) | `Err` returned to the caller, surfaced as an effect (a message), not as an error state that replaces content |

A `Result` is for the failures the product has an opinion about. Wrapping a genuine bug in `Ok`/`Err`
hides it — those should crash loudly in debug and be reported in release.

## Uncaught errors

Register global handlers in the composition root so nothing is lost: `FlutterError.onError` for
framework errors and `PlatformDispatcher.instance.onError` for uncaught async errors, both routed to the
project's logger and crash reporter. **Never** log an error's raw request body, headers or tokens — see
the `v1rus-logging` skill.
