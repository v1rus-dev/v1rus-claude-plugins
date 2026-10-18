---
name: compose-screen-architecture
description: Use this skill when creating, refactoring, or reviewing Compose screens that follow Destination, Screen, StateUi, IntentUi, EffectUi, Section composables, separate UI files, and Preview coverage.
---


> **Scope note.** This skill documents the v1rus Compose **reference architecture** as implemented in
> the flagship project. The patterns are the standard; the concrete type and file names
> (`StoreViewModel`, `AppNavigator`, `AppTheme`, `AppRes`, module paths) are that project's. In
> another v1rus project, read its `CLAUDE.md` first and map the names to its equivalents — do not
> assume a type exists because it is named here.

# Compose Screen Architecture

Use this skill when creating, refactoring, or reviewing a Jetpack Compose or Compose Multiplatform screen.

The screen architecture is based on a strict separation between `Destination`, `Screen`, state rendering, user intents, one-time effects, sections, and previews.

## Core principle

Every Compose screen always starts with a `Destination`.

`Destination` is the entry point for navigation and side effects.

`Screen` is a pure stateless UI function.

### Body order inside Destination

The body of every `Destination` function must follow this fixed order:

1. **Observers** — everything the screen needs before rendering: state collection, CompositionLocals, string resources, `LaunchedEffect`s, result handling, and any other setup.
2. **Screen call** — the single call to `FeatureScreen(state, onIntent)`.
3. **`CollectEffectsUiEvent`** — always the very last statement. Always placed immediately after `Screen`. Never before it, never interleaved with other declarations.

```kotlin
@Composable
fun FeatureDestination(
    navigator: AppNavigator = koinInject(),
    viewModel: FeatureViewModel = koinViewModel(),
) {
    // 1. Observers — state, locals, resources, LaunchedEffects, result handling
    val resultStore = LocalResultStore.current
    val state by viewModel.uiState.collectAsState()
    val currentEntry by navigator.currentBackStackEntryAsState()

    LaunchedEffect(currentEntry) {
        resultStore.getResultAndRemove<FeatureResultModelUi>(RESULT_KEY)?.let {
            viewModel.onIntent(FeatureIntentUi.OnResult(it))
        }
    }

    // 2. Screen
    FeatureScreen(
        state = state,
        onIntent = viewModel::onIntent,
    )

    // 3. CollectEffectsUiEvent — always last
    CollectEffectsUiEvent(viewModel.uiEffects) { effect ->
        when (effect) {
            // handle navigation, uri, clipboard, toast, result handling
        }
    }
}
```

```kotlin
@Composable
internal fun FeatureScreen(
    state: FeatureStateUi,
    onIntent: (FeatureIntentUi) -> Unit,
) {
    // only UI rendering
}
```

Do not use `Route` naming. Use `Destination`.

## Layer responsibilities (summary)

| Layer | Owns | Must NOT know |
|-------|------|---------------|
| `Destination` | ViewModel, DI, AppNavigator, effects, LaunchedEffect, result handling | — |
| `Screen` | StateUi rendering, IntentUi dispatch | ViewModel, DI, navigation, effects |
| `Section` | slice of StateUi, UI models, onIntent | ViewModel, DI, navigation, effects |
| `ViewModel` | StateUi, IntentUi, EffectUi, use cases | NavController, composable lambdas, platform UI objects |

For full responsibilities and examples → read `references/destination.md` and `references/screen-sections-components.md`.

## StateUi / IntentUi / EffectUi (summary)

**StateUi** — sealed for simple mutually exclusive states; data class for complex screens with many independent parts, tabs, partial loading, or content.

**IntentUi** — all user actions (back, retry, logout, tab click, copy, open email/phone/Telegram/URL, text input, refresh, item click). Composables always call `onIntent`, never execute the action directly.

**EffectUi** — one-time commands emitted by the ViewModel and collected only in `Destination` via `CollectEffectsUiEvent`. Use for navigation, opening links, clipboard, toast, showing bottom sheet. Never put one-time commands into `StateUi`.

For sealed interface examples, StateUi patterns, and EffectUi examples → read `references/state-intent-effect.md`.

## Sections and Components (summary)

Use `Section` naming, not `Part`:

```text
AuthEmptySection  AuthLoadingSection  AuthErrorSection
ProfileHeaderSection  ProfileContactsSection  ProfileActionsSection
```

Extract a block into a `Section` when it represents a separate visual area or state, is large enough to make `Screen` harder to read, or deserves its own preview.

`Component` is a smaller reusable element used inside sections. Examples: `ProfileContactItem`, `ProfileInfoCard`, `ProfileAvatar`, `ProfileTabItem`.

For detailed rules, full examples, and what Sections must not know → read `references/screen-sections-components.md`.

## File structure

```text
presentation/profile/
  ProfileDestination.kt
  ProfileScreen.kt
  ProfileViewModel.kt
  ProfileStateUi.kt
  ProfileIntentUi.kt
  ProfileEffectUi.kt

  sections/
    ProfileHeaderSection.kt
    ProfileContactsSection.kt
    ProfileEmploymentSection.kt
    ProfileDocumentsSection.kt
    ProfileActionsSection.kt
    ProfileLoadingSection.kt
    ProfileErrorSection.kt
    ProfileEmptySection.kt

  components/
    ProfileContactItem.kt
    ProfileInfoCard.kt
    ProfileActionButton.kt
```

Split UI into separate files aggressively. Do not create one huge `Screen.kt` with all composables inside it. When creating a new screen, create the file structure first.

## Naming convention

```text
FeatureDestination        FeatureScreen             FeatureViewModel
FeatureStateUi            FeatureIntentUi           FeatureEffectUi
FeatureModelUi            FeatureSomethingModelUi
FeatureSomethingSection   FeatureSomethingComponent
```

Do NOT generate: `FeatureRoute`, `FeatureUiState`, `FeatureAction`, `FeatureEvent`, `FeaturePartSomething`.

## Screen types — Scaffold rules

There are two kinds of `Screen` in this project. **Always identify which type you're creating before writing any layout code.**

`Strings.<key>` below stands for the project's generated string accessor: on Android that is `androidx.compose.ui.res.stringResource` with the generated `R` (`R.string.<key>`), on Compose Multiplatform `org.jetbrains.compose.resources.stringResource` with the generated `Res` (`Res.string.<key>`).

---

### 1. Full-screen (push navigation)

A screen that occupies the full viewport and is reached by `navigator.navigate(...)`. It owns its own `AppHeader` and optional action bar.

**Rules:**
- Wrap the entire screen in `Scaffold`.
- Put `AppHeader(title = ..., navigationIcon = { back-arrow })` in `topBar`.
- Put a primary action (e.g. "Apply", "Save") in `bottomBar` when the design calls for one — use `AppFilledButton` with `fillMaxWidth()` + `navigationBarsPadding()` + padding.
- Set `containerColor = AppTheme.colors.background`.
- Pass `paddingValues` from the `Scaffold` lambda to the content (via `padding(paddingValues)` or `LazyColumn(contentPadding = paddingValues)`).
- Do **not** add `navigationBarsPadding()` inside the content — `bottomBar` already allocates the space.

```kotlin
@Composable
internal fun AbsencesScreen(
    state: AbsencesStateUi,
    onIntent: (AbsencesIntentUi) -> Unit,
    modifier: Modifier = Modifier,
) {
    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = AppTheme.colors.background,
        topBar = {
            AppHeader(
                title = stringResource(Strings.absences_request_title),
                navigationIcon = {
                    Icon(
                        imageVector = ArrowBack,
                        contentDescription = stringResource(Strings.navigate_back),
                        tint = AppTheme.colors.onAccent,
                        modifier = Modifier.size(24.dp).clickable { onIntent(AbsencesIntentUi.Back) },
                    )
                },
            )
        },
        bottomBar = {
            if (state.phase == AbsencesStateUi.Phase.Content) {
                AppFilledButton(
                    onClick = { onIntent(AbsencesIntentUi.OnApply) },
                    enabled = state.isApplyEnabled && !state.isSubmitting,
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(horizontal = 16.dp, vertical = 20.dp),
                ) {
                    if (state.isSubmitting) {
                        CircularProgressIndicator(color = AppTheme.colors.onAccent, modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                    } else {
                        Text(text = stringResource(Strings.absences_apply), style = AppTheme.typography.titleSmall, color = AppTheme.colors.onAccent)
                    }
                }
            }
        },
    ) { paddingValues ->
        when (state.phase) {
            AbsencesStateUi.Phase.Loading -> AbsencesLoadingPart(paddingValues)
            AbsencesStateUi.Phase.Error -> AbsencesErrorPart(paddingValues, onRetry = { onIntent(AbsencesIntentUi.Retry) })
            AbsencesStateUi.Phase.Content -> AbsencesContentPart(state, onIntent, paddingValues)
        }
    }
}
```

**Also:** a screen with a filter/action toolbar but no global bottom action uses a `topBar`-only `Scaffold`:

```kotlin
Scaffold(
    topBar = {
        AppHeader(
            title = stringResource(Strings.reports_filter_title),
            navigationIcon = { Icon(ArrowBack, ...) },
            actions = { Text(stringResource(Strings.clear), ...) },
        )
    },
    bottomBar = {
        AppFilledButton(
            text = stringResource(Strings.apply),
            onClick = { onIntent(ReportsFilterIntentUi.OnApply) },
            modifier = Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 16.dp, vertical = 20.dp),
        )
    },
) { padding ->
    LazyColumn(modifier = Modifier.fillMaxSize().padding(padding), ...) { ... }
}
```

---

### 2. Tab screen (bottom navigation)

A screen shown as a **tab inside the root bottom navigation** (`HomeScreen`, `TimesheetScreen`, `ReportsScreen`, `BookingScreen`). The `AppHeader` and bottom navigation bar are **already provided by `RootScreen`** — the tab screen must NOT add its own `AppHeader`.

**Rules:**
- Do NOT wrap in `Scaffold` with a `topBar`. The global `AppHeader` is rendered by `RootScreen`.
- Do NOT add `navigationBarsPadding()` — the root Scaffold handles it.
- Use `Scaffold(contentWindowInsets = WindowInsets())` **only** when the screen needs a `floatingActionButton` (FAB). Otherwise use `Column` / `LazyColumn` directly.
- The tab screen receives `modifier: Modifier = Modifier` and applies it to the root layout so the root can pass `fillMaxSize()` with inner padding.

```kotlin
// TimesheetScreen — tab screen with FAB
@Composable
internal fun TimesheetScreen(
    state: TimesheetStateUi,
    onIntent: (TimesheetIntentUi) -> Unit,
    modifier: Modifier = Modifier,
) {
    Scaffold(
        modifier = modifier,
        contentWindowInsets = WindowInsets(),   // required — suppresses insets double-counting
        floatingActionButton = {
            AppFab(onClick = { onIntent(TimesheetIntentUi.OnAddTaskClicked) })
        },
    ) { paddingValues ->
        Column(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            TimesheetControlBar(...)
            TimesheetContentPart(...)
        }
    }
}

// ReportsScreen — tab screen without FAB, plain Column
@Composable
internal fun ReportsScreen(
    state: ReportsStateUi,
    onIntent: (ReportsIntentUi) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxSize()) {
        PeriodNavigationControlBar(...)
        AnimatedContent(state.dataState) { dataState ->
            when (dataState) {
                is ReportsDataState.Content -> ReportsContentPart(...)
                ReportsDataState.Loading -> ReportsLoadingPart()
                ReportsDataState.Error -> ReportsErrorPart(...)
                ReportsDataState.Empty -> ReportsEmptyPart(...)
            }
        }
    }
}
```

**Decision table:**

| Criterion | Full-screen | Tab screen |
|-----------|-------------|------------|
| Navigation | `navigator.navigate(route)` | registered in `RootScreen` tab list |
| Has back arrow | Yes — in `AppHeader` `navigationIcon` | No |
| `AppHeader` | Own `AppHeader` in `Scaffold.topBar` | Provided by `RootScreen` — do NOT add |
| Bottom action | `Scaffold.bottomBar` with `navigationBarsPadding()` | FAB-only via `Scaffold(contentWindowInsets = WindowInsets())` |
| `containerColor` | `AppTheme.colors.background` | Not needed |

---

## Previews (summary)

Every UI file must have at least one `@Preview`. Applies to `Screen`, every `Section`, and every non-trivial `Component`. `Destination` does not need a preview — it depends on DI, ViewModel, navigation, effects, and locals.

The annotation itself differs by target — `androidx.compose.ui.tooling.preview.Preview` on Android, `org.jetbrains.compose.ui.tooling.preview.Preview` on Compose Multiplatform.

**The Content (Success) preview is mandatory and must be created first.** It is the most valuable preview — it shows real data, real layout, and catches the majority of visual bugs. Never ship a screen that has only Loading or Error previews but lacks a Content preview.

Priority order for `Screen` previews:
1. **Content** — filled with realistic data (names, dates, numbers). Always required.
2. **Loading** — skeleton or spinner state.
3. **Error** — error message with retry.
4. **Empty** — zero-item or unauthenticated state, if applicable.

For full preview rules and examples → read `references/previews.md`.

## Code generation rules

When creating a new Compose screen:

1. Create `FeatureDestination`.
2. Create `FeatureScreen`.
3. Create `FeatureStateUi`.
4. Create `FeatureIntentUi`.
5. Create `FeatureEffectUi` if one-time commands are needed.
6. Create `FeatureViewModel`.
7. Extract large UI blocks into `Section` composables.
8. Extract smaller reusable elements into `components`.
9. Split sections and components into separate files.
10. Add at least one preview for every UI file.
11. Add several screen previews for main states when possible.
12. Keep navigation and side effects only in `Destination`.
13. Keep `Screen`, `Section`, and `Component` composables stateless.
14. Send all user actions through `IntentUi`.
15. Emit one-time commands as `EffectUi`.
16. Follow the existing project conventions if they conflict with this skill.

## Koin DI — registering a UseCase is mandatory

**CRITICAL**: every new UseCase MUST be registered in the project's domain module Koin file via `factoryOf(::MyNewUseCase)`. Without it the app crashes on start with a Koin missing-binding error.

```kotlin
// the project's domain module — di/DomainModule.kt
val domainModule = module {
    // ...
    factoryOf(::MyNewUseCase)   // ← add it here
}
```

The same applies to a ViewModel — `viewModelOf(::MyNewViewModel)` in the owning feature module's Koin file (usually `di/FeatureModule.kt`).
