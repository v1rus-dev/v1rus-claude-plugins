---
name: flutter-networking
description: "Networking conventions for v1rus Flutter projects: Dio as the transport (one configured instance built in core with base options and timeouts) and Retrofit as the endpoint declaration layer (@RestApi abstract classes in data, generated implementations, no hand-written Dio calls in a repository); interceptors for auth token injection, single-flight token refresh with request queueing, and logging that never prints tokens or bodies; DTOs owned by data and mapped to entities at the boundary; a single session-expired channel that the app root observes to trigger re-auth rather than ad-hoc handling per call site; and cancellation tokens tied to screen lifetime. Load when adding an endpoint, writing a Retrofit API client, configuring Dio, implementing auth refresh, handling 401, or debugging a network layer."
---

# Networking (Dio + Retrofit)

Two layers with one job each, and the split is the point:

| Layer | Owns | Lives in |
|---|---|---|
| **Dio** | transport: base options, timeouts, interceptors, auth refresh, logging, cancellation | `core/network/` |
| **Retrofit** | endpoint declarations: paths, methods, parameters, return DTOs | `data/api/` |

## One Dio, built in `core`

A single configured `Dio` is created in `core/network/` and registered as a singleton. Feature code
never constructs a `Dio`, and never calls `Dio()` inline for "just this one request".

Configure once: `baseUrl`, `connectTimeout`, `receiveTimeout`, `sendTimeout`, default headers, and the
JSON content type. A request with no timeout is a hang the user experiences as a frozen screen.

## Endpoints are Retrofit interfaces, not hand-written Dio calls

API clients live in `data/api/`, are `@RestApi()` abstract classes over the injected `Dio`, and return
**DTOs** — never entities, never `Map<String, dynamic>` to the caller.

```dart
// data/api/orders/order_api.dart
part 'order_api.g.dart';

@RestApi()
abstract class OrderApi {
  factory OrderApi(Dio dio, {String? baseUrl}) = _OrderApi;

  @GET('/orders')
  Future<List<OrderDto>> getOrders({
    @Query('page') int page = 1,
    @CancelRequest() CancelToken? cancelToken,
  });

  @POST('/orders')
  Future<OrderDto> createOrder(@Body() CreateOrderDto body);
}
```

Rules that come with it:

- **`baseUrl` stays on the `Dio` instance.** Do not repeat it in `@RestApi(baseUrl: …)` — two sources of
  truth for the host is how a staging build ends up talking to production. A path prefix shared by one
  client's endpoints is fine as a literal prefix in each `@GET`/`@POST`.
- **No `dio.get(...)` inside a repository.** If an endpoint exists, it belongs on an API interface; a
  repository calls the interface. The exception is genuinely non-endpoint transport work (a token refresh
  call issued from the interceptor itself, a raw file download) — those are in `core/network/`.
- **Return the DTO, not `HttpResponse<T>`.** Reach for `HttpResponse<T>` only when the method genuinely
  needs a header or the status code (pagination headers, `ETag`); it leaks transport shape otherwise.
- **The `Authorization` header is never a method parameter.** It is attached by the auth interceptor
  (below). A `@Header('Authorization')` on a method means the token is being threaded through `domain`,
  which is a boundary violation.
- Static per-endpoint headers use `@Headers({...})`; a per-request flag the interceptors read uses
  `@Extra({...})` / `@Extras()` (see the auth interceptor below).
- Retrofit throws `DioException` on a non-2xx, so error handling is unchanged: the repository maps it
  (`flutter-error-handling`).
- One client per domain area (`OrderApi`, `AuthApi`), each in its own subfolder of `data/api/` — never one
  `ApiClient` accumulating every endpoint in the app.

## Interceptor order matters

```
[ auth (attach token) ] → [ refresh (401 → refresh → retry) ] → [ logging (last) ]
```

- **Auth interceptor** attaches the access token to requests that need it. Endpoints that must *not*
  carry a token (login, refresh itself) are marked explicitly — with `@Extra({'no_auth': true})` on the
  Retrofit method, which the interceptor reads from `options.extra`, or with a separate Dio instance —
  otherwise refresh recurses into itself.
- **Refresh interceptor** handles `401`. Two rules decide whether this works under load:
  1. **Single-flight.** Concurrent 401s must trigger **one** refresh; the rest wait on the same future
     and then retry. Without this, five parallel requests fire five refreshes and the backend
     invalidates the token as fast as you obtain it.
  2. **One retry, then give up.** Retry the original request once with the new token. If refresh itself
     fails, do not retry — emit session-expired (below) and return `UnauthorizedError()`.
- **Logging interceptor is last** so it sees the final request. It must never log the `Authorization`
  header, cookies, refresh tokens, or full request/response bodies by default — see `v1rus-logging`.
  Redact, truncate, and keep verbose bodies to debug builds only.

## Session expiry — one channel, not N call sites

When refresh ultimately fails, publish it **once** on a single channel in `core` (a broadcast
`Stream<void>` or a small `SessionEvents` service). The app root listens and drives re-authentication:
clear tokens, navigate to login, show one dialog.

Every feature handling 401 itself is how apps end up showing three stacked "session expired" dialogs and
racing navigation. Feature code maps `UnauthorizedError` to a state; it does not navigate to login
on its own.

## Cancellation

Pass a `CancelToken` for work tied to a screen and cancel it in the Bloc's `close()`. On a Retrofit method
the token is a parameter annotated `@CancelRequest()`; the repository accepts it and forwards it. A
cancelled request is **not** an error state: detect `CancelToken` cancellation in the mapper and drop it
rather than emitting `AppError`.

## DTOs and mapping

- DTOs are `@JsonSerializable()` classes (`json_serializable` only — no `freezed`, see
  `flutter-codegen`), in `data/api/dto/`, grouped into **subpackages by domain area** — never dumped into
  one flat `dto/` folder. Each exposes a `fromJson` factory, which Retrofit's default parser requires.
- Prefer an **enum with a fallback** over a raw `String` for closed value sets
  (`@JsonValue` + `unknown` default), so an unexpected server value degrades instead of throwing.
- Mapping DTO→entity is an explicit extension or mapper function in `data/mappers/`. Never put mapping
  inside the DTO's own class, and never let a DTO cross into `domain` or `features`.
- Nullability in a DTO mirrors what the server **actually** sends. Making everything non-null because
  "it should always be there" turns a missing field into a parse crash for every user at once.

## Errors

The whole failure surface is mapped to `AppError` inside `data` — see `flutter-error-handling`. A
`DioException` must never reach a Bloc.

## Verifying before writing code

Dio's interceptor API, Retrofit's annotation set and Flutter's HTTP stack all change between majors.
Before writing or editing networking code, check the current API against the package's own docs for the
version the project resolves — never from memory. Version resolution itself happens at plan time
(`v1rus-dependencies`);
for Dart use `dart pub outdated` and the package page rather than pinning a remembered number.
