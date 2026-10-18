# Destination — full reference

`Destination` is the integration layer of the screen.

`Strings.<key>` in the samples below stands for the project's generated string accessor — `R.string.<key>` on Android, `Res.string.<key>` on Compose Multiplatform.

## What Destination may know about

`Destination` is the only layer allowed to hold external dependencies. It may inject and use anything — navigators, URI handlers, clipboard, toast hosts, result stores, platform services, or any other infrastructure. There is no fixed list of allowed dependencies; if a side effect requires it, `Destination` may depend on it.

## Flow rule — all external actions go through EffectUi

`Destination` never triggers external actions on its own initiative. Every external interaction must be authorized by the ViewModel first:

```
User action → onIntent(IntentUi) → ViewModel → emit EffectUi → Destination executes
```

`Destination` listens for `EffectUi` and only then performs the actual side effect — navigation, opening a URI, writing to clipboard, showing a toast, etc. This keeps the ViewModel the single decision-maker for when and why something happens.

## What Destination is responsible for

`Destination` has two fixed jobs and one open-ended job.

**Fixed — always:**
- Inject `ViewModel` and any needed external services via DI.
- Collect `StateUi` and call `Screen(state, onIntent)`.
- Collect `EffectUi` via `CollectEffectsUiEvent` and execute every effect the ViewModel emits.

**Open-ended — whatever `EffectUi` commands:**
The concrete list of actions depends entirely on what the screen needs. The ViewModel decides when and what; `Destination` only executes. Examples: navigating to another screen, opening a URI, writing to clipboard, showing a toast, handling a navigation result, converting an external result back into `IntentUi`. There is no fixed ceiling — if a new external action is needed, add an `EffectUi` variant and handle it here.

## Body order

The body of every `Destination` composable must follow this fixed order. Do not deviate from it.

```
1. Observers
   - DI injections are already in the parameter list (koinInject, koinViewModel)
   - CompositionLocals  (LocalResultStore, LocalUriHandler, LocalClipboard, LocalAppToastHostState, …)
   - State collection   (collectAsState, currentBackStackEntryAsState, …)
   - String / resource  values needed by effect handlers
   - LaunchedEffect(s)  and any other side-effect hooks
   - Result handling    (getResultAndRemove inside LaunchedEffect)

2. Screen call          — FeatureScreen(state, onIntent)

3. CollectEffectsUiEvent — always the very last statement in the function,
                           always placed immediately after the Screen call.
```

**Rule:** Everything that observes, prepares data, or sets up side effects goes **above** the `Screen` call. `CollectEffectsUiEvent` always goes **after** `Screen` and is always the last statement — nothing may follow it.

## Minimal example

```kotlin
@Composable
fun AuthDestination(
    appNavigator: AppNavigator = koinInject(),
    viewModel: AuthViewModel = koinViewModel()
) {
    val state by viewModel.uiState.collectAsState()

    AuthScreen(state, viewModel::onIntent)

    CollectEffectsUiEvent(viewModel.uiEffects) { effect ->
        when (effect) {
            AuthEffectUi.NavigateToRoot -> appNavigator.replaceAll(RootScreenRoute)
        }
    }
}
```

## Full example — all Destination capabilities

```kotlin
@Composable
fun ProfileDestination(
    navigator: AppNavigator = koinInject(),      // DI injections — in parameter list
    viewModel: ProfileViewModel = koinViewModel(),
) {
    // 1. Observers ---------------------------------------------------------

    // CompositionLocals
    val resultStore = LocalResultStore.current
    val uriHandler = LocalUriHandler.current
    val clipboard = LocalClipboard.current
    val toastHostState = LocalAppToastHostState.current

    // State collection
    val state by viewModel.uiState.collectAsState()
    val currentEntry by navigator.currentBackStackEntryAsState()

    // String resources needed by effect handlers
    val copiedToClipboardText = stringResource(Strings.copied_to_clipboard)

    // LaunchedEffect / result handling
    LaunchedEffect(currentEntry) {
        resultStore.getResultAndRemove<ProfileTabTypeModelUi>(PROFILE_TAB_RESULT_KEY)?.let {
            viewModel.onIntent(ProfileIntentUi.OnTabSelected(it))
        }
    }

    // 2. Screen ------------------------------------------------------------
    ProfileScreen(state, viewModel::onIntent)

    // 3. CollectEffectsUiEvent — always last -------------------------------
    CollectEffectsUiEvent(viewModel.uiEffects) { effect ->
        when (effect) {
            ProfileEffectUi.NavigateToAuth -> navigator.replaceCurrent(AuthScreenRoute)
            is ProfileEffectUi.ShowTabSelectionSheet -> {
                navigator.navigate(SelectProfileTabTypeRoute(effect.currentTab, PROFILE_TAB_RESULT_KEY))
            }
            is ProfileEffectUi.OpenEmail -> uriHandler.openUri("mailto:${effect.email}")
            is ProfileEffectUi.OpenPhone -> uriHandler.openUri("tel:${effect.phone}")
            is ProfileEffectUi.OpenTelegram -> {
                val username = effect.username.removePrefix("@")
                uriHandler.openUri("https://t.me/$username")
            }
            is ProfileEffectUi.OpenUrl -> {
                val url = if (effect.url.startsWith("http")) effect.url else "https://${effect.url}"
                uriHandler.openUri(url)
            }
            is ProfileEffectUi.CopyToClipboard -> {
                clipboard.setClipEntry(clipEntryOf(effect.text))
                toastHostState.showToast(copiedToClipboardText, ToastType.Info)
            }
        }
    }
}
```

## Result handling

Navigation results must be handled in `Destination`. External navigation result should be converted into `IntentUi`.

```kotlin
LaunchedEffect(currentEntry) {
    resultStore.getResultAndRemove<ProfileTabTypeModelUi>(PROFILE_TAB_RESULT_KEY)?.let {
        viewModel.onIntent(ProfileIntentUi.OnTabSelected(it))
    }
}
```

Do not handle navigation result logic inside `Screen`.
