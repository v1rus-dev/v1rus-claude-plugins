---
name: flutter-di
description: "Dependency injection in v1rus Flutter projects: get_it with one explicit registration module per feature and per core area (the direct analogue of Koin modules), constructor injection everywhere so no class reaches into the locator, blocs registered as factories while clients and databases are singletons, lazy singletons by default, async dependencies awaited before runApp, and a scope reset on logout. Load when registering a dependency, wiring a new feature, deciding singleton versus factory, or when tempted to call the locator from inside a class."
---

# Dependency Injection (get_it)

Explicit registration modules, no code generation. One `build_runner` step fewer than an annotation-based
container, and the whole graph is greppable — which matters more than the boilerplate saved, because a
missing registration is a runtime failure either way.

## One module per area, mirroring the layers

```dart
// core/di/di.dart
final GetIt di = GetIt.instance;

Future<void> configureDependencies() async {
  await registerCore(di);        // logger, Dio, storages, session events
  registerDatabase(di);          // Drift database + DAOs
  registerData(di);              // Retrofit api clients, repository implementations
  registerDomain(di);            // use cases
  registerAuthFeature(di);       // per-feature blocs
  registerOrdersFeature(di);
}
```

```dart
// features/orders/di/orders_module.dart
void registerOrdersFeature(GetIt di) {
  di.registerFactory<OrderListBloc>(() => OrderListBloc(di<OrderRepository>()));
  di.registerFactory<CheckoutBloc>(() => CheckoutBloc(di<PlaceOrder>()));
}
```

A feature module registers **only that feature's** blocs. It never registers a repository — that belongs
to the data module — and it never reads another feature's registrations.

## Lifetimes

| Lifetime | Use for |
|---|---|
| `registerLazySingleton` | **default** for infrastructure: Dio, Retrofit api clients (`OrderApi(di<Dio>())`), database, storages, repositories, use cases. Created on first use, so app start stays fast. |
| `registerFactory` | **every Bloc and Cubit.** A screen must get a fresh instance; a singleton Bloc keeps the previous screen's state and leaks its subscriptions. |
| `registerSingleton` | only when the instance must exist eagerly (something that starts listening at boot) |
| `registerSingletonAsync` | dependencies needing async init (opening secure storage, reading a config) |

If anything is registered async, `await di.allReady()` before `runApp` — otherwise the first screen races
initialisation and fails intermittently, which is the worst kind of bug to reproduce.

## Constructor injection only

Dependencies arrive through the constructor. **No class calls `di<T>()` inside its own body** — that
hides the dependency from the signature, defeats compile-time review of the graph, and makes the class
untestable without the global container.

The permitted exceptions are the boundaries where there is no constructor to inject into:
- the composition root and the DI modules themselves,
- a widget obtaining its Bloc via `BlocProvider(create: (_) => di<XBloc>())`.

Widgets get their Bloc from `BlocProvider`, not from `di` scattered through the tree.

## Logout and scopes

Logout clears user-scoped state. Either reset a `get_it` **scope** that holds user-scoped registrations, or
explicitly clear the caches and storages involved (`flutter-persistence`). Leaving user-scoped singletons
alive is how the next account sees the previous one's data — a review-blocking finding, not a polish item.

## Tests

Tests do not use the global container: they construct the class under test with fakes directly. When a
widget test genuinely needs the locator, register fakes into a fresh scope in `setUp` and tear it down in
`tearDown`, so tests cannot leak registrations into each other (`flutter-testing`).
