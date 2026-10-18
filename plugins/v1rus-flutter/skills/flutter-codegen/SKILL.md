---
name: flutter-codegen
description: "build_runner discipline for v1rus Flutter projects: the four generators in play (json_serializable, retrofit_generator, drift, go_router_builder), the deliberate absence of a model generator — no freezed, models are native Dart 3 sealed/final classes with Equatable — the retrofit abstract-class shape a model gets wrong, the rule that .g.dart files are never hand-edited and a broken build is fixed at the source, and how to run generation and diagnose conflicts. Load before writing a model, a DTO, an API client, a Drift table or a typed route, or when generated code will not build."
---

# Code Generation

Four generators, one `build_runner`:

| Generator | Generates for |
|---|---|
| `json_serializable` | `fromJson` / `toJson` on DTOs |
| `retrofit_generator` | the implementation of each annotated API client (`flutter-networking`) |
| `drift` | tables, DAOs, migration scaffolding |
| `go_router_builder` | typed route helpers |

Note what is **not** in that list: there is **no model generator**. `freezed` is deliberately not used —
unions, entities and state are written as native Dart 3 classes (below).

## Models are hand-written — no `freezed`

Dart 3 has class modifiers and pattern matching natively, so a union needs no generator; what a generator
still bought was `==` / `hashCode` / `copyWith`, and `Equatable` covers equality without a build step.

```dart
// A UNION (state, event, effect, error) — native `sealed` + `final` subclasses
sealed class OrderState extends Equatable {
  const OrderState();

  @override
  List<Object?> get props => const [];
}

final class OrderLoading extends OrderState {
  const OrderLoading();
}

final class OrderContent extends OrderState {
  const OrderContent(this.items);
  final List<OrderUi> items;

  @override
  List<Object?> get props => [items];
}
```

- **`sealed`** on the base makes `switch` exhaustive — that is what the state and `Result` handling rely
  on. **`final`** on each case so no one extends a state from another layer.
- **Every field that participates in identity goes in `props`.** A field left out means two different
  states compare equal and the screen silently does not rebuild — that is the one failure mode this
  approach introduces, and it is what review looks for.
- `copyWith` is hand-written and **only where it is actually used** — do not add one to every class out of
  habit.
- A class needs equality only if it is compared, keyed, put in a `Set`, or emitted as Bloc state. DTOs
  usually need none (they are mapped and discarded); add `Equatable` to a DTO only when a test compares
  it.

## `retrofit` — the shape a model gets wrong

The API client is an **abstract class** with a generated implementation; the factory redirects to the
generated `_`-prefixed class, and forgetting either the `part` directive or the factory produces an error
that reads as if the annotation were wrong.

```dart
// data/api/orders/order_api.dart
part 'order_api.g.dart';

@RestApi()
abstract class OrderApi {
  factory OrderApi(Dio dio, {String? baseUrl}) = _OrderApi;

  @GET('/orders/{id}')
  Future<OrderDto> getOrder(@Path('id') String id, {@CancelRequest() CancelToken? cancelToken});
}
```

- The return type is a **DTO** with a `fromJson` factory — the default parser is
  `Parser.JsonSerializable`, so a DTO without `@JsonSerializable()` fails generation.
- `baseUrl` is configured on the `Dio` instance, **not** repeated in `@RestApi(...)` per client
  (`flutter-networking`).
- Verify the annotation set against the resolved version's own documentation before writing a client;
  version choice happens at plan time (`v1rus-dependencies`).

## Hard rules

- **Never hand-edit a generated file** (`*.g.dart`, `*.gr.dart`). It is overwritten on
  the next build. If generated code is wrong, the annotation or the source class is wrong — fix that.
- **Never work around a generation failure by writing the generated file yourself.** A red `build_runner`
  is the root cause; treat it as one.
- Generated files are **not** counted as project code for review purposes, but the annotations that
  produce them are.
- Follow the project's existing convention on whether generated files are committed — read
  `.gitignore` rather than deciding unilaterally. Whatever it is, it must be consistent: half-committed
  generated code produces conflicts on every merge.

## Running generation

```
dart run build_runner build --delete-conflicting-outputs   # one-off
dart run build_runner watch --delete-conflicting-outputs   # while developing
```

- `--delete-conflicting-outputs` is the normal flag, not a workaround: it clears stale outputs left by a
  renamed or deleted source file.
- After changing an ARB file, run `gen-l10n` (usually via `flutter gen-l10n` or automatically on build) —
  see `flutter-localisation`.
- If generation is unexpectedly slow or looping, check for a generated file being watched as an input, or a
  `build.yaml` including the whole `lib/` for a generator that needs a subset.
- Read the project's `CLAUDE.md` for the actual commands; do not invent task names.

## Codegen and the boundaries

Generated code lives beside its source, so it inherits that file's layer — a DTO's and an API client's
`.g.dart` are in `data`, a typed route's is in the feature. Keep the annotated source in the layer it
belongs to, and the `import_lint` rules keep applying (`flutter-architecture`).
