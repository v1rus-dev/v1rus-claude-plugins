---
name: web-localisation
description: "Localisation in a v1rus web app with next-intl: every user-visible string comes from a message file including empty copy, error copy, placeholders, alt text, accessible names and page titles, keys namespaced per feature and added to every locale in the same change with the drift check failing CI instead of relying on review, ICU plural and select instead of concatenation, Intl for dates numbers and currency with an explicit time zone, shipping only the namespaces a client component needs, locale routing and metadata, RTL and text-expansion safe layout, and free-form server text shown verbatim while closed-set tokens are mapped to labels. Load before adding any user-visible text, an aria-label, a fallback value, a formatted date, or a new message key."
---

# Localisation

**Default: `next-intl`.** It is built for the App Router — messages are available in server components
without shipping the whole catalogue to the browser, locale routing and metadata are first class, and
keys can be typed. `i18next` remains the alternative when the project already shares an i18n stack with
other apps; the project's `CLAUDE.md` decides, and an existing choice wins.

## Non-negotiable — messages only

Every string a user can see comes from a message file: labels, titles, buttons, empty copy, error copy,
placeholders, **`alt` text, `aria-label`s and visually hidden text**, page titles and descriptions, and
**fallback values** (what is shown when a field is null).

A hardcoded user-visible literal is a bug caught in review **regardless of whether a second locale
exists yet** — that is the point: the default must be a message so it localises later without touching
component code.

Exempt: API paths, query and field names, log and analytics keys, test ids, enum values in code.

Where a message is needed outside a component (a schema, a mapper, a store), do not hardcode it there.
Keep the value as a **key or a structured code** and resolve it in the component that renders it
(`web-forms` does exactly this with validation messages).

## Keys

- Namespace per feature and name by meaning, not by the English text: `orders.empty.title`,
  `common.actions.retry`. A key named `theOrderWasNotFound` is unusable the moment the copy changes.
- **Search before adding.** Reuse an existing key with the same meaning rather than introducing a
  synonym; check for a near-identical key name to avoid semantic duplicates.
- Generic actions (`retry`, `cancel`, `back`, `close`) live in a shared namespace and are reused.
- Add the key to the **template locale and every other locale in the same change**.

## Locales stay in sync — mechanically

"Add the key to both files" survives about two sprints as a review rule. Make it a build step: a CI
check that compares every locale's key set against the template and **fails on a missing or orphaned
key**. With typed messages, a missing key in the template is already a type error; the CI check is what
covers the other locales.

Placeholder-shape drift matters as much as missing keys — a translation that dropped a `{count}`
argument breaks at runtime, so the check compares arguments, not only key names.

## Interpolation and plurals

- **Never concatenate.** `t("found") + " " + count + " " + t("orders")` cannot be translated into a
  language with different word order or grammatical number.
- Use ICU `plural` for counts and `select` for gendered or enumerated variants, and give every
  placeholder an explicit type.

```json
{
  "orders": {
    "selected": "{count, plural, =0 {Nothing selected} one {# order selected} other {# orders selected}}"
  }
}
```

- Rich text (a link or bold inside a sentence) goes through the library's rich-text formatting, not by
  splitting the sentence into three keys.

## Formatting

- Dates, times, numbers, currency, units, relative times and list joins go through `Intl` (or the
  library's wrappers) with the active locale — never a hand-rolled format and never `toLocaleString()`
  relying on the runtime default.
- **Always pass an explicit time zone** for anything a user reads as a calendar date. The server and the
  browser are in different zones: formatting the same instant in each produces different text and a
  hydration mismatch, and a date rendered in the server's zone is simply wrong for the user
  (`${CLAUDE_PLUGIN_ROOT}/rules/react.md`).
- Currency carries its currency code from the data, never a hardcoded symbol.

## Server and client

- Read messages in server components wherever possible — nothing ships to the browser.
- A client component receives only the **namespaces it needs**. Sending the whole catalogue to the
  browser is a bundle regression that grows with every feature (`web-performance`).
- Locale is resolved once (route segment or middleware) and flows from there; do not read it from
  `navigator.language` during render.

## Routing and metadata

- The locale lives in the URL (a path segment by default) so a link is shareable and indexable.
- `generateMetadata` uses the localised title and description, and the document sets the right `lang`
  — and `dir` where an RTL locale is in scope (`web-routing`).
- Alternate-language links are emitted for the locales the app actually serves.

## Layout consequences

- **Translations are longer.** German and Russian commonly run 30–50% longer than English: no fixed-width
  buttons, no single-line assumptions, no truncation that hides the meaning (`web-styling`).
- If an RTL locale is in scope, use logical CSS properties (`margin-inline-start`, `text-align: start`)
  from the beginning; retrofitting direction is a rewrite.

## Server-provided text

| Kind of value | What to do |
|---|---|
| Free-form / unbounded — names, comments, notes, server error messages | show **verbatim**, do not localise, do not invent keys — the backend owns the text |
| Closed / enum-like set — status, type, role | **never render the raw token** (`WAITING_FOR_APPROVE`); map it to a localised label |

When unsure whether a field is a closed set, treat it as enum-like and map it — a raw token in the UI is
worse than an unnecessary mapping. An unmapped value must fall back to something human, never to an
empty string (`web-ui-conventions`).
