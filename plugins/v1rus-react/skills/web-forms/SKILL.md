---
name: web-forms
description: "Forms in a v1rus web app: react-hook-form with a zod resolver, the schema declared once and re-validated on the server because client validation is a convenience and never a control, uncontrolled fields by default and what a controlled field costs, accessible errors (label tied to input, aria-invalid, aria-describedby, focus moved to the first error, a live region for the summary), submit state that cannot double-submit, server-side field errors mapped back onto fields, resetting a form when the entity changes, and unsaved-changes handling. Load when building or reviewing a form, wiring validation, handling a submit failure, or making an existing form accessible. Do NOT load for how the mutation itself is sent and invalidated — that is web-data-fetching."
---

# Forms and Validation

**Default: `react-hook-form` with a `zod` resolver.** Fields stay uncontrolled, so typing in one field
does not re-render the form; the schema is one declaration that produces both the runtime check and the
inferred TypeScript type (`v1rus-typescript:ts-type-modelling`).

## One schema, two enforcements

```ts
// features/orders/model/order-form-schema.ts
export const orderFormSchema = z.object({
  title: z.string().trim().min(1).max(120),
  quantity: z.coerce.number().int().positive(),
  comment: z.string().max(500).optional(),
});
export type OrderFormValues = z.infer<typeof orderFormSchema>;
```

- The same schema validates in the form resolver **and** at the server boundary — the server action or
  route handler parses the payload again (`v1rus-typescript:ts-boundaries-validation`).
- **Client validation is a convenience, never a control.** Anyone can post directly to the endpoint, and
  the UI having disabled a button proves nothing. A server that trusts the client's validation is a
  security bug, not a shortcut.
- Validate what the domain requires, not what is easy: trim before length checks, bound the maximum
  length of every free-text field, and prefer a closed union to a free string where the set is closed.
- Messages are keys resolved through the localisation layer, not English literals baked into the schema
  (`web-localisation`). Keep the schema's messages as identifiers and translate at render.

## Field wiring

- **Uncontrolled by default**: register the field and let the library hold the value. Reach for a
  controlled field only for a component that cannot be uncontrolled (a rich editor, a third-party
  select) — and then wrap it once in a controller, not per call site.
- A field is controlled or uncontrolled for its whole life
  (`${CLAUDE_PLUGIN_ROOT}/rules/react.md`); `value={undefined}` on first render is the usual accident.
- Validation mode is a deliberate choice: validate on blur and re-validate on change after the first
  failure. Validating on every keystroke from the start scolds the user mid-word.
- A form is a `form` element with a real `submit` button, so `Enter` submits and the browser's own
  behaviour works. A `div` with a click handler breaks both.

## Accessibility of errors

Every one of these, every time:

- A real `label` tied to the input by `htmlFor`/`id`. A placeholder is not a label
  (`web-ui-conventions`).
- The invalid field carries `aria-invalid` and points at its message with `aria-describedby`; the same
  attribute carries the hint text when there is one.
- The message is **next to the field**, specific and actionable ("Enter a quantity of 1 or more"), not a
  generic "Invalid" and not only a red border — colour is never the only signal.
- **On a failed submit, move focus to the first invalid field** (the library will do it when asked) and
  announce the summary through a live region. Without this a keyboard or screen-reader user is left at
  the submit button with no indication that anything happened.
- A required field is marked in text, not only with an asterisk's colour.
- Grouped controls (radios, a set of checkboxes) sit in a `fieldset` with a `legend`.

## Submitting

- The submit control shows a **pending state and is disabled while in flight**, and stays disabled until
  the mutation and its invalidation settle. Otherwise a double-click sends two writes
  (`web-data-fetching`).
- A failed submit keeps the user's input. Never clear the form on error, and never discard a draft
  because a request failed.
- Map **server-side field errors back onto the fields** (`setError` per field) rather than showing one
  banner that says "validation failed" — the user cannot see which field the server rejected.
- A form-level failure (network, 500) renders the error where the user is looking, with a retry that
  re-submits the same values.
- Success does something visible: navigate, show a confirmation in a live region, or update the list the
  user came from. A form that silently resets looks broken.

## Server actions

- A server action is the default transport for this app's own form submits: it validates with the same
  schema, authorises, mutates, revalidates the affected paths or tags, and returns a typed result
  (`web-data-fetching`).
- Progressive enhancement is free when the form is a real `form` bound to the action — keep it that way
  rather than intercepting submit for no reason.
- Never return the raw exception to the client; return a discriminated result the UI can branch on
  (`v1rus-typescript:ts-error-handling`).

## Lifecycle

- **Seed an edit form from server data, then leave it alone.** Initialise from the fetched entity and
  reset the whole form with a `key` when the entity id changes — never patch fields from an effect when
  a refetch lands, or the user's typing is overwritten mid-edit (`react-state-management`).
- Warn before discarding unsaved changes when the form is dirty and the user navigates away — and make
  the warning escapable.
- Multi-step forms keep the step in the URL so refresh and back behave (`react-state-management`), and
  validate each step's slice of the schema on leaving it.
- File inputs validate type and size on the client for feedback and **again on the server** for real;
  show progress and allow cancel for anything large.
