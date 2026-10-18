---
name: flutter-localisation
description: "Localisation in v1rus Flutter projects using the official ARB plus flutter gen-l10n toolchain: every user-visible string comes from a resource including fallbacks and placeholders, every new key is added to all locale files in the same change with untranslated-messages-file wired so a missing translation fails CI instead of relying on review, free-form server text shown verbatim while closed-set server values are mapped to localised labels, and how to search for an existing key before adding one. Load before adding any user-visible text, a Semantics label, a fallback value, or a new ARB key."
---

# Localisation (ARB + `gen-l10n`)

Official toolchain, zero extra dependencies: `.arb` files plus Flutter's built-in `gen-l10n`.

## Non-negotiable — resources only

Every string a user can see MUST come from a resource: labels, titles, buttons, `Semantics` labels and
tooltips, empty / error / placeholder copy, **and fallback values** (the default shown when a field is
null).

Never bake a user-visible literal into code, not even a "temporary" English default. **A hardcoded
user-visible string is a bug caught in review, regardless of whether translations exist yet** — that is
exactly why the default must be a resource: so it localises later without touching code.

If a fallback is needed where `AppLocalizations.of(context)` is unavailable (a Bloc, a mapper), do not
hardcode it there. Keep the value nullable or structured and resolve the resource in the widget that
renders it — the same rule as `bloc-conventions` (no `BuildContext` in a Bloc).

Exempt: API paths, query/field names, log and debug text, analytics event keys, `@JsonValue` constants.

## Locales stay in sync — mechanically

`values` drift apart the moment this depends on someone noticing in review. Wire the toolchain to notice
instead:

```yaml
# l10n.yaml
arb-dir: lib/l10n
template-arb-file: app_en.arb
output-localization-file: app_localizations.dart
output-class: AppLocalizations
untranslated-messages-file: l10n_untranslated.json
required-resource-attributes: true
nullable-getter: false
```

- **`untranslated-messages-file`** makes `gen-l10n` write a JSON file of the form
  `"locale": ["message_1", "message_2"]` listing everything not yet translated. The CI step regenerates
  and **fails if that file is non-empty** — that is the enforcement for "every new key lands in every
  locale in the same change". Without the option, the same information is only printed to the console and
  scrolls past.
- **`required-resource-attributes: true`** forces a `@key` description block for each message, so
  translators are not guessing at context.
- **`nullable-getter: false`** removes the `AppLocalizations.of(context)!` bang from every call site.

## Adding a key

1. **Search the ARB for the intended text first** — reuse an existing key with the same meaning rather
   than adding a synonym.
2. **Search for a similar key name** to avoid semantic duplicates (`orders` vs `orders_screen_title`).
3. Add it to the **template** ARB and to **every** other locale in the same change.
4. Name by scope: generic actions (`retry`, `cancel`, `back`) live in a shared section; feature strings are
   prefixed (`orders_empty_title`).
5. Use ARB placeholders with explicit types, and ICU `plural` / `select` for counts and gendered text —
   never string concatenation, which is unlocalisable.

```json
"ordersSelected": "{count, plural, =0{Ничего не выбрано} one{Выбран {count} заказ} other{Выбрано {count} заказов}}",
"@ordersSelected": {
  "description": "Count of selected orders shown in the toolbar",
  "placeholders": { "count": { "type": "int" } }
}
```

## Server-provided strings

| Kind of value | What to do |
|---|---|
| Free-form / unbounded — names, comments, notes, descriptions, server error messages | show **verbatim**, do not localise, do not invent keys (the backend owns the text and its language) |
| Closed / enum-like set — status, type, role | **never render the raw token** (`WaitingForApprove`). Map the enum to a localised label via a resource |

Rule of thumb: unbounded server text → as-is; finite known set → mapped. **When unsure whether a field is
a closed set, treat it as enum-like and map it** — a raw token in the UI is worse than an unnecessary
mapping.

## Error messages

`AppError` carries no text (`flutter-error-handling`). The widget maps the error case to a resource key,
so the same failure reads correctly in every locale. A server-supplied message is displayed verbatim when
present, with a localised fallback when it is not.
