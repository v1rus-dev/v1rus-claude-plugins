---
name: localisation-and-strings
description: "The v1rus localisation rule for Compose, Compose Multiplatform and Jetpack Compose alike: every user-visible string comes from a string resource — labels, titles, buttons, contentDescription, empty/error/placeholder copy and fallback defaults — and a hardcoded user-visible literal is a bug caught in review even when translations do not exist yet; free-form server text (names, notes, comments, server error messages) is shown verbatim and never localised, while a closed-set server value (status, type, role) is mapped to a localised label instead of rendering the raw token; plus how to search for an existing key before adding one, where keys are placed, and keeping every locale file in sync in the same change. Load before adding any user-visible text, a contentDescription, a fallback value, or a new string resource."
---

# Localisation and Strings

Applies to any Compose project. The resource file locations are the project's — find them in the
design-system module. Only the generated accessor differs by target: the `R` class (`R.string.<key>`)
on Android, the generated `Res` object over `composeResources/` (`Res.string.<key>`) on Compose
Multiplatform.

## Non-negotiable — resources only

Every string a user can see MUST come from a string resource: labels, titles, button text,
`contentDescription`, empty / error / placeholder copy, **and fallback values** (the default shown when
a name or field is null).

Never bake a user-visible literal into code, not even a "temporary" English default. **A hardcoded
user-visible string is a bug, caught in review, regardless of whether translations exist yet** — that
is precisely why the English default must be a resource: so it localises later without touching code.

If a user-visible fallback is needed where `stringResource` is unavailable (a ViewModel, a mapper), do
not hardcode it there. Keep the value nullable or structured and resolve the resource in the Composable
that renders it.

Only genuinely non-user-visible strings are exempt: API paths, OData/query field names, log and debug
text, serial names, analytics event keys.

## Server-provided strings

| Kind of server value | What to do |
|---|---|
| Free-form / unbounded — user names, notes, comments, descriptions, template names, server-generated error messages | show **verbatim**, do not localise, do not invent resources for it (you cannot know the values and the backend owns the text and its language) |
| Closed / enum-like set — status, type, role, policy scope | **never render the raw token** (`WaitingForApprove`). Map the value to a localised label via a resource, e.g. a `toLabelRes()` extension on the enum |

Rule of thumb: unbounded server text → display as-is; finite known set → map to a resource. **When
unsure whether a field is a closed set, treat it as enum-like and map it** — a raw token leaking into
the UI is worse than an unnecessary mapping.

## Before adding a new key

1. **Search the resource file for the intended value** (`grep -i "retry" strings.xml`) — reuse an
   existing key with the same meaning.
2. **Search for a matching name pattern** to avoid semantically duplicate keys (`projects` versus
   `reports_projects_title`).

## Placement

- Generic action words (`retry`, `cancel`, `back`, `collapse`, `expand`, …) go in the global section at
  the top.
- Feature-specific strings go under a `<!-- Feature name -->` comment block.
- Keep `<string-array>` entries immediately after the `<string>` keys they relate to.
- Never duplicate an array when the values are identical — reuse the existing one (month names, for
  example).

## Locales stay in sync

The default locale file is the source language; each additional locale is a sibling. **Every new
user-visible key MUST be added to every active locale file in the same change** — an English key
without its translation is an incomplete change, caught in review. Keep the files in the same key
order so a diff between them is readable.

In Composables always use `stringResource(...)` / `stringArrayResource(...)`. In non-Composable code
`stringResource` is unavailable: either return a resource reference for the UI to resolve, or, when a
constant genuinely cannot be extracted, document why.
