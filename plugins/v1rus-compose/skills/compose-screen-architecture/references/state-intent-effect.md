# StateUi, IntentUi, EffectUi — full reference

## IntentUi

All user actions must go through `IntentUi`.

Examples of user actions:

- back click
- retry click
- logout click
- tab click
- copy click
- open email click
- open phone click
- open Telegram click
- open URL click
- text input changes
- refresh
- item click

`Screen`, `Section`, and `Component` composables must call `onIntent`.

```kotlin
onIntent(ProfileIntentUi.OnTelegramClicked(username))
```

The composable must not execute the action directly.

## EffectUi

`EffectUi` is a one-time command emitted by the `ViewModel` and handled only in `Destination`.

Use `EffectUi` for:

- navigation
- opening links
- opening email
- opening phone
- opening Telegram
- copying to clipboard
- showing toast
- showing snackbar
- opening bottom sheet or selection screen
- external platform/UI actions

Do not put one-time commands into persistent `StateUi`.

### EffectUi example

```kotlin
sealed interface ProfileEffectUi {
    data object NavigateToAuth : ProfileEffectUi
    data class ShowTabSelectionSheet(
        val currentTab: ProfileTabTypeModelUi,
    ) : ProfileEffectUi
    data class OpenEmail(val email: String) : ProfileEffectUi
    data class OpenPhone(val phone: String) : ProfileEffectUi
    data class OpenTelegram(val username: String) : ProfileEffectUi
    data class OpenUrl(val url: String) : ProfileEffectUi
    data class CopyToClipboard(val text: String) : ProfileEffectUi
}
```

## StateUi

`StateUi` describes only what the screen must render.

### Sealed StateUi — for simple screens

For simple screens with mutually exclusive states, sealed state is acceptable.

```kotlin
sealed interface AuthStateUi {
    data object Empty : AuthStateUi
    data object Loading : AuthStateUi
    data class Error(val message: String) : AuthStateUi
}
```

### Data class StateUi — for complex screens

For complex screens with many independent parts, tabs, sections, partial loading, content, or actions, prefer a data class.

```kotlin
data class ProfileStateUi(
    val isLoading: Boolean,
    val selectedTab: ProfileTabTypeModelUi,
    val user: ProfileUserModelUi?,
    val sections: List<ProfileSectionModelUi>,
)
```

Do not expose raw domain models directly if the UI needs formatting or presentation-specific structure.

Use `ModelUi` classes when domain models are not presentation-ready.

## Creating file

Do not create different files for that classes. Always make one `.kt` file with name `*ModelUi.kt`.
For example:

`ProfileModelUi.kt`

```kotlin
@Stable
data class ProfileStateUi(
    val currentTab: ProfileTabTypeModelUi,
    val user: UserProfileModelUi? = null,
    val avatarUrl: String? = null,
    val profileTabState: ProfileTabState,
    val expandedSections: PersistentSet<String> = persistentSetOf(),
) : StateUi

@Stable
sealed interface ProfileTabState {
    data object Loading : ProfileTabState
    data class Content(
        val items: ImmutableList<ProfileContentItemModelUi> = persistentListOf(),
    ) : ProfileTabState
    data class Error(val message: String) : ProfileTabState
}

sealed interface ProfileIntentUi : IntentUi {
    data object OnSignOutClick : ProfileIntentUi
}
```