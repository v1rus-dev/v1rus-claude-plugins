# ViewModel — full reference

## Responsibilities

`ViewModel` owns state transitions and business interaction.

`ViewModel` is responsible for:

- exposing `StateUi`
- exposing `EffectUi`
- receiving `IntentUi`
- updating state
- calling use cases
- emitting one-time effects

## What ViewModel must NOT store

- `NavController`
- `AppNavigator`
- composable lambdas
- platform UI objects
- Compose UI state objects that belong only to composition
