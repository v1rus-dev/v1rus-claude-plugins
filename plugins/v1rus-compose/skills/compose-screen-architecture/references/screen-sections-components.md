# Screen, Sections, and Components — full reference

## Screen responsibilities

`Screen` is a pure renderer. It has exactly two inputs and zero external interactions.

**Two inputs:**
- `state: FeatureStateUi` — what to render
- `onIntent: (FeatureIntentUi) -> Unit` — where to send user actions

**Hard rule — no external world access:**
`Screen` must never touch anything outside its two inputs. This means no DI (`koinInject`, `koinViewModel`), no navigation (`AppNavigator`, `NavController`), no platform services (`LocalUriHandler`, `LocalClipboard`, `LocalAppToastHostState`, `LocalResultStore`), no effect collection, and no side effects of any kind. If a composable inside `Screen` needs to trigger something external, it calls `onIntent` — the ViewModel decides what happens next.

### Screen example

```kotlin
@Composable
internal fun AuthScreen(
    state: AuthStateUi,
    onIntent: (AuthIntentUi) -> Unit
) {
    Box(modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        LoginBackground()
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Image(
                imageVector = V1rusLogo,
                modifier = Modifier.padding(horizontal = 16.dp).localSharedElement("v1rus_logo_image"),
                contentDescription = null
            )
            Spacer(modifier = Modifier.height(12.dp))
            when (state) {
                AuthStateUi.Empty -> AuthEmptySection(onIntent)
                AuthStateUi.Loading -> AuthLoadingSection()
                is AuthStateUi.Error -> AuthErrorSection(state.message, onIntent)
            }
        }
    }
}
```

## Sections

Use `Section` naming instead of `Part`.

Do not use:

```kotlin
AuthPartEmpty()
AuthPartLoading()
AuthPartError()
```

Use:

```kotlin
AuthEmptySection()
AuthLoadingSection()
AuthErrorSection()
```

A `Section` is a meaningful part of a screen.

Extract a block into a `Section` when:

- it represents a separate visual area
- it represents a separate state
- it is large enough to make `Screen` harder to read
- it has its own responsibility
- it deserves its own preview
- it can be reasoned about independently

### Section tree example

```text
ProfileScreen
  ProfileHeaderSection
  ProfileContactsSection
  ProfileEmploymentSection
  ProfileDocumentsSection
  ProfileActionsSection
  ProfileLoadingSection
  ProfileErrorSection
  ProfileEmptySection
```

### Section rules

`Section` composables must also be stateless.

They may receive:

- part of `StateUi`
- UI models
- `onIntent`
- `modifier`

They must not know about:

- `ViewModel`
- DI
- navigation
- effect flows
- platform side effects

### Section example

```kotlin
@Composable
internal fun ProfileContactsSection(
    contacts: List<ProfileContactModelUi>,
    onIntent: (ProfileIntentUi) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier) {
        contacts.forEach { contact ->
            ProfileContactItem(
                contact = contact,
                onClick = {
                    onIntent(ProfileIntentUi.OnContactClick(contact))
                },
            )
        }
    }
}
```

## Components

Use `components` for smaller reusable UI elements inside sections.

A `Component` is smaller than a `Section`.

Examples:

```text
ProfileContactItem
ProfileInfoCard
ProfileActionButton
ProfileAvatar
ProfileTabItem
```

Components should also be stateless and previewable.

## IntentUi dispatch rule

`Screen`, `Section`, and `Component` composables must call `onIntent`.

```kotlin
onIntent(ProfileIntentUi.OnTelegramClicked(username))
```

The composable must not execute the action directly.
