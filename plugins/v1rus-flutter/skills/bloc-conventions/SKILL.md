---
name: bloc-conventions
description: "How state management is written in a v1rus Flutter project: Bloc for screens (event-driven, the direct analogue of MVI Intent to State) and Cubit only for narrow component-local state, state modelled as a native Dart sealed union with Equatable covering loading / content / empty / error, one-shot side effects delivered through a separate effect stream instead of being stored in state, event transformers for debounce and concurrency, and no BuildContext or widget type ever reaching a Bloc. Load when creating or reviewing a Bloc, Cubit, state, event or effect, or when a screen needs to show a snackbar or navigate."
---

# Bloc Conventions

## Bloc for screens, Cubit for components

- **A screen is a `Bloc`.** Events in, state out — the direct analogue of MVI `Intent → State` used in
  v1rus's KMP projects, and the reason a screen's whole interaction surface is greppable as one sealed
  event union. It also gives event transformers (below), which a Cubit cannot express.
- **A `Cubit` is for narrow, component-local state** with no meaningful event vocabulary: an expand
  toggle, a filter chip row, a bottom-sheet's internal step. Direct method calls, no event classes.
- Do **not** start a screen as a Cubit "for now". Migrating a Cubit to a Bloc later rewrites its public
  API and every call site; starting with a Bloc costs one event class.

## State is a sealed union, not a bag of flags

Model state as a **native Dart `sealed` union with `Equatable`** (no `freezed` — see `flutter-codegen`)
so impossible combinations cannot be represented. A class with `isLoading`, `error` and `items` all
nullable permits "loading and error at once" — the union does not.

```dart
sealed class OrderListState extends Equatable {
  const OrderListState();

  @override
  List<Object?> get props => const [];
}

final class OrderListLoading extends OrderListState {
  const OrderListLoading();
}

final class OrderListEmpty extends OrderListState {
  const OrderListEmpty();
}

final class OrderListContent extends OrderListState {
  const OrderListContent(this.items);
  final List<OrderUi> items;

  @override
  List<Object?> get props => [items];
}

final class OrderListError extends OrderListState {
  const OrderListError(this.error);
  final AppError error;

  @override
  List<Object?> get props => [error];
}
```

Every screen state covers **loading / content / empty / error**, and a fetched detail screen also
**not-found** — the UI checklist in `flutter-ui-conventions` is unsatisfiable otherwise.

**Equality is the load-bearing part here.** Bloc drops an `emit` whose state equals the current one, so a
field missing from `props` means the screen does not rebuild — and nothing fails loudly. Every field that
distinguishes two states is in `props`; `AppError` and every UI model reachable from state carry value
equality for the same reason.

Keep the state a *UI* model: preformatted strings, no entities carrying data-layer concerns, no
`BuildContext`, no widgets, no `Color` or `TextStyle` (those come from the theme at render time).

## Events

```dart
sealed class OrderListEvent extends Equatable {
  const OrderListEvent();

  @override
  List<Object?> get props => const [];
}

final class OrderListStarted extends OrderListEvent {
  const OrderListStarted();
}

final class OrderListOrderTapped extends OrderListEvent {
  const OrderListOrderTapped(this.id);
  final String id;

  @override
  List<Object?> get props => [id];
}
```

- One handler per event, registered in the constructor with `on<Event>(_handler)`.
- Events carry `Equatable` too — `bloc_test` expectations and `distinct`-style transformers compare them.
- **If a handler needs more than a couple of calls, extract a private method** — a handler that inlines
  multi-step orchestration stops being readable and untestable in isolation.
- Use **event transformers** where concurrency matters: `debounce` for search input, `droppable` for a
  submit button, `restartable` for a query that supersedes the previous one. Getting this wrong is the
  usual cause of duplicate network calls and out-of-order results.

## One-shot effects — a separate stream, never state

Navigation, snackbars, closing a sheet, haptics: these happen **once**. Putting them in state means
they replay on every rebuild and after state restoration. Keep them on their own stream — the direct
analogue of `EffectUi` in v1rus's KMP projects.

```dart
// core/bloc/effect_bloc.dart
abstract class EffectBloc<E, S, F> extends Bloc<E, S> {
  EffectBloc(super.initialState);
  final _effects = StreamController<F>.broadcast();
  Stream<F> get effects => _effects.stream;
  void emitEffect(F effect) => _effects.add(effect);

  @override
  Future<void> close() {
    _effects.close();
    return super.close();
  }
}
```

```dart
sealed class OrderListEffect {
  const OrderListEffect();
}

final class OrderListShowMessage extends OrderListEffect {
  const OrderListShowMessage(this.text);
  final String text;
}

final class OrderListOpenDetails extends OrderListEffect {
  const OrderListOpenDetails(this.id);
  final String id;
}
```

Effects deliberately do **not** extend `Equatable`: two identical messages emitted in a row are two
separate events the user must see, so an effect must never be deduplicated by value.

On the screen, subscribe once and switch exhaustively:

```dart
StreamBuilder / a small EffectListener widget in core, then:
onEffect: (context, effect) => switch (effect) {
  OrderListShowMessage(:final text) => context.showSnack(text),
  OrderListOpenDetails(:final id) => OrderDetailsRoute(id: id).push(context),
},
```

Rules that go with it:

- **Closing the stream in `close()` is mandatory** — a leaked `StreamController` outlives the screen.
- Effects are fire-and-forget: never await one, never derive state from one.
- The **Bloc emits an effect; the widget performs it.** A Bloc must not touch `BuildContext`, a
  `Navigator`, a `ScaffoldMessenger`, or a router. That is what makes the Bloc testable without a
  widget tree.

## What never enters a Bloc

- `BuildContext`, any widget, any `dart:ui` type.
- A repository **implementation** or a DTO — the Bloc depends on `domain` interfaces and use cases only
  (`flutter-architecture`).
- A raw `DioException` or `DriftRemoteException` — the data layer maps those to `AppError` before they
  reach here (`flutter-error-handling`).
- `print` / `debugPrint` — use the project's logger (`v1rus-logging` skill).

## Lifecycle

- The Bloc is registered as a **factory**, not a singleton, and provided by `BlocProvider` at the screen
  it belongs to (`flutter-di`).
- Cancel or guard in-flight work in `close()`; a stream subscription opened in a handler is stored and
  cancelled there.
- After any `await` inside a widget callback, check `context.mounted` before using the context — the
  analyzer flags most of these, not all.

## Testing

`bloc_test` for blocs, `mocktail` for collaborators, handwritten fakes when the double carries
behaviour. Assert the emitted **state sequence**, and assert effects separately by collecting from the
effect stream. Details in `flutter-testing`.
