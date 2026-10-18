---
name: flutter-testing
description: "How tests are written and run in a v1rus Flutter project: bloc_test for blocs asserting the exact emitted state sequence with effects asserted separately, mocktail for collaborators and handwritten fakes when the double carries behaviour, widget tests for screen states rather than golden-by-default, a Drift migration test for every schema bump, one test file per production file named _test.dart, and the flutter test / dart analyze commands read from the project rather than guessed. Load when writing or fixing tests for Dart code, testing a Bloc or widget, or when a change breaks existing tests."
---

# Flutter Testing

**Whether tests are written at all is decided by the complexity band, not here** — see the `v1rus-qa`
skill (tests from complexity 7 upward; below that verification is build + static analysis + the quality
gate). This skill covers *how* they are written when warranted.

## Layout and naming

- `test/` mirrors `lib/`: `lib/data/repositories/order_repository_impl.dart` →
  `test/data/repositories/order_repository_impl_test.dart`.
- One test file per production file, `<name>_test.dart`. One `group` per class, one `test` per behaviour.
- Test names state the behaviour, not the method: `emits error state when repository fails`.

## Doubles

- **`mocktail`** for collaborators whose calls you assert (an API client, a repository interface). No
  code generation, no `build_runner` step.
- **Handwritten fakes** when the double carries behaviour — an in-memory `TokenStorage`, an in-memory
  repository backed by a `List`. A fake with behaviour is more readable than five `when(...)` stubs, and it
  is reusable: keep them in `test/fakes/` and reuse rather than re-inventing per test.
- Register fallback values for custom types used in `any()` matchers in `setUpAll`, or matcher failures
  surface as confusing type errors.

## Blocs

`bloc_test` asserts the **exact emitted sequence** — that ordering is the contract:

```dart
blocTest<OrderListBloc, OrderListState>(
  'emits loading then content when orders load',
  setUp: () => when(() => repository.getOrders()).thenAnswer((_) async => Ok(orders)),
  build: () => OrderListBloc(repository),
  act: (bloc) => bloc.add(const OrderListStarted()),
  expect: () => [
    const OrderListLoading(),
    OrderListContent(orders.toUi()),
  ],
);
```

- The sequence assertion **is** the equality test: it passes only because state and everything reachable
  from it carry value equality (`Equatable`, every distinguishing field in `props` — `bloc-conventions`).
  A state comparison that fails for no visible reason is usually a missing `props` entry, and one that
  passes when it should not is usually a state that omits the field being changed.
- Cover the **error path** for every load: `Err(<AppError case>)` in, error state out. A bloc test suite
  with only happy paths tests nothing that breaks in production.
- **Effects are asserted separately** from state — collect from the `effects` stream and assert what was
  emitted (`bloc-conventions`). An effect asserted through state means the effect was wrongly put in state.
- Use `wait` / `skip` deliberately for debounced events rather than sprinkling real delays.
- **Never `Future.delayed` or `sleep` to wait for a bloc.** Use `bloc_test`'s scheduling, `fakeAsync`, or
  await the emitted stream.

## Widgets

- Widget tests cover the **states**, not the pixels: loading shows a progress indicator, error shows the
  retry affordance and the back affordance, empty shows the empty copy, content shows the items.
- Provide a fake Bloc (`mocktail` mock of the Bloc, or a real Bloc with fake repositories) through
  `BlocProvider`. Wrap in the app theme so token lookups do not throw.
- Find by semantics or key, not by literal text where the string is localised — a localisation change must
  not break an unrelated test.
- **Golden tests are opt-in**, not the default: they are valuable for `design_system` components and
  expensive and flaky for full screens across platforms. If used, pin the font and rendering setup so they
  are reproducible in CI.

## Data layer

- API clients: a Retrofit client over a `Dio` whose adapter is stubbed (a mocked `HttpClientAdapter` or
  `DioAdapter`) returning canned payloads — mock the transport, not the generated client, so DTO
  deserialisation is exercised. Assert the mapping DTO→entity and the mapping of each failure to its
  `AppError` — the error mapper deserves its own test, since it is what every screen's error state depends
  on.
- Repositories: doubles for the API interface (`mocktail` on `OrderApi` — the generated implementation is
  not the unit under test here) and the database; assert `Ok`/`Err` and the caching decision.
- **Drift migrations: every `schemaVersion` bump gets a migration test** — build the database at version N,
  migrate, assert data survived. Drift ships schema-verification tooling for this. This is the one place
  where "it compiles" proves nothing (`flutter-persistence`).

## Running

Read the project's `CLAUDE.md` for the exact commands; the usual shape is `flutter test` for the suite,
`flutter test <path>` for one file, `dart analyze` for static analysis (which also runs `import_lint` when
configured — `flutter-architecture`). Never invent a command; if the project documents nothing and the
choice is ambiguous, ask rather than guessing.

Scope the run to the change (`check` skill): a logic change runs the affected tests, a pure rename or a
comment edit needs analysis only. Long runs go to the `test-runner` agent so a full suite does not consume
the orchestrating session's context.

## Non-negotiable

Whoever breaks an existing test fixes it in the same change. A `skip:` without a tracked-issue reference is
forbidden, and a red suite is never merged — `v1rus-qa` § 4.
