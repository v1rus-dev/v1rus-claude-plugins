---
name: flutter-architecture
description: "The v1rus Flutter layered architecture: a single package with lib/{core,design_system,domain,data,features}, domain always present (entities, repository interfaces, errors) with UseCases only where real logic exists, data owning DTOs and repository implementations, features owning Bloc plus widgets and never importing each other, and the dependency direction enforced mechanically by the import_lint analyzer plugin rather than by review. Load when creating a feature, deciding which layer a class belongs to, adding a folder, reviewing a module boundary, or setting up analysis_options.yaml."
---

# Flutter Architecture

Layered architecture, one Dart package. The layer boundaries are **compiler-adjacent, not advisory** —
they are declared in `analysis_options.yaml` and violations fail `dart analyze` (see § Enforcing the
boundaries).

## Layout

```
lib/
  core/            # framework-agnostic plumbing: Result, AppError, network client,
                   # storage, di, logging, extensions. No feature knowledge.
  design_system/   # theme, tokens (ThemeExtension), shared widgets, icons
  domain/          # entities, repository INTERFACES, domain errors, use cases
  data/            # DTOs, API clients, Drift database, repository IMPLEMENTATIONS, mappers
  features/
    <feature>/
      bloc/        # bloc/cubit, state, event, effect
      view/        # screen + its parts
      widgets/     # widgets private to this feature
      routes/      # this feature's typed routes
  l10n/            # .arb files
  main.dart        # composition root: DI registration, router, runApp
```

Anything under `features/<x>/` that is not `routes/` is **private to that feature**.

## Dependency direction

```
features ──▶ domain ──▶ (nothing)
   │           ▲
   │           │
   └──▶ core   └── data ──▶ core
        ▲
   design_system
```

Hard rules:

- **`domain` depends on nothing** — not on `data`, not on `features`, and **not on Flutter**. A
  `package:flutter/*` import in `domain` is a defect: it means an entity knows about UI.
- **`data` never imports `features`** and never imports another repository implementation.
  Repositories do not know about each other (this is also the official Flutter guidance).
- **A feature never imports another feature.** Cross-feature interaction goes through `domain`
  (a shared use case or repository interface) or through navigation. If two features need the same
  widget, it belongs in `design_system`; the same logic → `domain`; the same helper → `core`.
- **`core` and `design_system` never import `features`, `data` or `domain`.** They are the base of
  the graph. `core` holding a `UserEntity` is a sign the entity belongs in `domain`.

## What goes in which layer

| Layer | Contains | Never contains |
|---|---|---|
| `domain` | entities (plain classes + `Equatable`, no json), repository interfaces, `AppError` hierarchy, use cases | DTOs, json, Flutter, Dio, Retrofit, Drift |
| `data` | DTOs (`json_serializable`), Retrofit API clients, Drift tables/DAOs, repository impls, mappers | widgets, Bloc, navigation |
| `features/<x>` | Bloc/Cubit, state/event/effect, screens, feature widgets, typed routes | repository implementations, DTOs, raw Dio/Retrofit/Drift calls |
| `core` | `Result`, network client + interceptors, storage wrappers, DI container, logger | entities, feature logic, widgets with business meaning |
| `design_system` | theme, `ThemeExtension` tokens, reusable widgets | feature state, data access |

## Domain layer — always present, UseCase only where there is logic

`domain` **always exists**: entities, repository interfaces and the error hierarchy live there from day
one, because they are what keeps `data` swappable and `features` testable.

A **UseCase is mandatory** when the operation:
- combines more than one repository, or
- carries real logic (validation, ordering, derivation, retries with business meaning), or
- is reused by more than one Bloc.

A UseCase is **not** created for a pass-through. For trivial single-repository reads and writes the
Bloc calls the repository interface directly.

```dart
// features/orders — trivial read, no use case
class OrderListBloc extends Bloc<OrderListEvent, OrderListState> {
  OrderListBloc(this._repository) : super(const OrderListLoading());
  final OrderRepository _repository;   // domain interface
}

// features/checkout — real logic across two repositories → use case
class CheckoutBloc extends Bloc<CheckoutEvent, CheckoutState> {
  CheckoutBloc(this._placeOrder) : super(const CheckoutIdle());
  final PlaceOrder _placeOrder;        // domain use case
}
```

A UseCase has **one public entry point** — `call(...)`, invoked as `useCase(args)` — and no state.

## Enforcing the boundaries

Because everything lives in one package, nothing but tooling stops a feature from importing another.
Declare the rules once; after that a violation is a red squiggle and a failed CI step, not a review
comment someone has to remember to write.

```yaml
# analysis_options.yaml
plugins:
  import_lint: <resolve the current version at plan time>

import_lint:
  rules:
    - name: features_are_isolated
      target: "lib/features/*/**"
      from: "lib/features/**"
      except: "lib/features/{self}/**"
      severity: error
    - name: domain_is_pure
      target: "lib/domain/**"
      from: ["lib/data/**", "lib/features/**", "package:flutter/**"]
      severity: error
    - name: data_never_sees_ui
      target: "lib/data/**"
      from: ["lib/features/**", "lib/design_system/**"]
      severity: error
    - name: base_layers_know_nothing
      target: ["lib/core/**", "lib/design_system/**"]
      from: ["lib/features/**", "lib/data/**", "lib/domain/**"]
      severity: error
```

**Prerequisite:** the analyzer-plugin mechanism needs **Dart 3.10+ / Flutter 3.38+**. On an older SDK
the tooling is unavailable — then the rules above are documented in the project's `CLAUDE.md` and
checked at review, and that gap is stated explicitly rather than pretended away. Do not silently drop
the boundary rules because the plugin will not load.

`import_lint` also runs as a CLI (`dart run import_lint`), so it belongs in the CI analyze step even
when the IDE already shows it.

## Adding a feature — checklist

1. `lib/features/<name>/` with `bloc/`, `view/`, `widgets/`, `routes/`.
2. Entities and the repository interface in `domain` (plus a use case only if the rules above call for
   one).
3. DTOs, the Retrofit API interface, Drift tables and the repository implementation in `data`; mappers
   DTO→entity.
4. A `registerXFeature(GetIt)` module and its call from the composition root (`flutter-di` skill).
5. Typed routes in `features/<name>/routes/` (`flutter-navigation` skill).
6. Strings in `l10n` — both locales in the same change (`flutter-localisation` skill).
