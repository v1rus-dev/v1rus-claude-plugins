# Previews — full reference

## Rules

Every UI file should have at least one `Preview`.

This applies to:

- `Screen`
- every `Section`
- every non-trivial `Component`

`Destination` does not need a preview because it depends on DI, ViewModel, navigation, effects, and locals.

### Minimum rule

Every new composable UI file must contain at least one preview.

### Preferred rule

- `Screen` should have previews for main states when possible
- loading, empty, error, and content states should be previewed when applicable
- sections should have their own previews with sample data
- components should have their own previews if they are non-trivial

## Section preview example

```kotlin
@Preview
@Composable
private fun ProfileContactsSectionPreview() {
    AppTheme {
        ProfileContactsSection(
            contacts = listOf(
                ProfileContactModelUi.Email("user@example.com"),
                ProfileContactModelUi.Phone("+375291234567"),
            ),
            onIntent = {},
        )
    }
}
```

## Multiple state previews for Screen

For screens with several states, prefer several previews:

```kotlin
@Preview
@Composable
private fun AuthScreenEmptyPreview() {
    AppTheme {
        AuthScreen(
            state = AuthStateUi.Empty,
            onIntent = {},
        )
    }
}

@Preview
@Composable
private fun AuthScreenLoadingPreview() {
    AppTheme {
        AuthScreen(
            state = AuthStateUi.Loading,
            onIntent = {},
        )
    }
}

@Preview
@Composable
private fun AuthScreenErrorPreview() {
    AppTheme {
        AuthScreen(
            state = AuthStateUi.Error("Something went wrong"),
            onIntent = {},
        )
    }
}
```
