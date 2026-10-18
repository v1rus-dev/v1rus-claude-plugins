---
name: web-ui-conventions
description: "The UI and accessibility checklist a v1rus web screen must satisfy before review: every screen handles loading / empty / error-with-retry / not-found / content with a skeleton rather than a spinner, navigation reachable in every state including error and loading, semantic elements instead of a div with onClick, an accessible name on every icon-only control, visible focus and focus moved deliberately after navigation and in a dialog, labels tied to inputs and errors announced, keyboard operability and no keyboard trap, colour never the only signal and AA contrast, images with dimensions and meaningful alt, motion respecting prefers-reduced-motion, and no raw enum or status token rendered to the user. Load before writing or reviewing any page, screen, dialog, list or form UI."
---

# Web UI Conventions

The high-frequency miss-list an implementer satisfies up front and a reviewer checks. It pre-empts the
predictable UX and accessibility findings that otherwise surface in a late review or from a screen
reader. Not exhaustive — for a non-trivial screen still run a `v1rus-core:ux-expert` review, and prefer
reviewing the design before the code.

## Screen states and navigation

- Every screen handles **loading / empty / error (+retry) / content**; a fetched detail screen also
  handles **not-found**, and a guarded one handles **unauthorised**. No state is left as a blank screen.
- **Navigation must be reachable in every state** — including loading and error. The header, back link
  and skip link live in the **layout**, outside the state branch, never only in the content branch. A
  failed fetch that leaves the user with no way back is a trap, and it is the finding that recurs most
  (`web-routing`).
- **Loading is a skeleton of the real layout**, not a centred spinner on an empty page: it keeps the
  page's shape, so nothing jumps when content arrives. A background refetch keeps the previous content
  visible and shows a subtle pending affordance instead of blanking the screen.
- Empty states carry human copy and, where one exists, the action that fills them ("No orders yet" +
  "Create order") — not an empty container.
- The error state says what failed in human words, offers a **working retry**, and never shows the raw
  message, the status code or a stack.
- **A modal, a drawer or a full-screen error must always offer a way out** — an explicit close control,
  `Escape`, and a backdrop click where appropriate. A dialog the keyboard cannot leave is a trap.
- When filters or a search are applied but the controls are not visible on this surface, show an
  **active-filter indicator** (a count or a chip) so the user understands why the list is short.

## Semantics before ARIA

- **An interactive element is a real element**: `button` for an action, `a`/`Link` for navigation,
  `input`/`select`/`textarea` for entry, `summary`/`details` for disclosure. A `div` with `onClick` is
  not focusable, not keyboard-operable, not announced, and does not work with the browser's own
  behaviours — and adding `role="button"` plus `tabIndex` plus two key handlers is reimplementing a
  `button` badly.
- A `button` that navigates should be a link; a link that performs an action should be a button. Styling
  decides how it looks, not which element it is.
- Page structure uses landmarks — `header`, `nav`, `main` (exactly one), `footer`, `aside` — and a
  heading hierarchy with one `h1` per page and no skipped levels. A screen reader navigates by these.
- Reach for ARIA only when no element expresses it: `aria-expanded` on a disclosure trigger,
  `aria-current="page"` on the active nav item, `aria-live="polite"` on a status region,
  `role="dialog"` with `aria-modal` and a labelled title. **Wrong ARIA is worse than none.**
- `aria-hidden` never goes on anything focusable, and a decorative icon is hidden from the accessibility
  tree (`aria-hidden="true"`) rather than announced as noise.

## Controls

- **Every control has an accessible name.** An icon-only button needs visually hidden text or
  `aria-label` from the localisation layer — never a bare glyph, never `title` alone. "Button" is what a
  screen reader says otherwise.
- Every input has a **real `label`** tied to it by `htmlFor`/`id`. A placeholder is not a label: it
  disappears on typing, fails contrast, and is not announced reliably.
- Touch targets are at least **44×44 CSS pixels** (pointer-coarse), including icon buttons in a dense
  toolbar. Padding counts; a 16px icon with no padding does not.
- Disabled controls are not focusable and cannot explain themselves — prefer an enabled control that
  validates and explains, or pair the disabled state with visible text saying why.
- A control that triggers async work shows its pending state and cannot be double-submitted
  (`web-forms`).

## Keyboard and focus

- **Everything usable with a mouse is usable with the keyboard**, in a logical tab order that follows the
  visual order. No positive `tabIndex`.
- **Never remove the focus outline.** Restyle it (`:focus-visible`) so it matches the design and stays
  visible against every background it can appear on.
- **A dialog traps focus while open**, is labelled by its title, returns focus to the element that opened
  it on close, and closes on `Escape`. Content behind it is inert.
- **After a client-side navigation, focus does not move on its own** — the user is left at the bottom of
  the previous page and a screen reader announces nothing. Move focus to the new page's `h1` or main
  landmark, and reset scroll. This is a real bug that no visual test catches.
- A skip link to `main` is the first focusable element on the page.
- Custom widgets (menu, combobox, tabs, tree) follow the expected key bindings, or use an accessible
  primitive library instead of hand-rolling one.

## Feedback and announcements

- A result that appears without a navigation — a toast, an inline save confirmation, a validation
  summary, a search result count — is announced through a **live region** that exists in the DOM before
  the message arrives (`aria-live="polite"`, `role="alert"` for errors).
- A toast is never the only place a failure is reported, and never the only way to recover from one.
- Progress that takes longer than a moment says so in text, not only in animation.

## Visual

- **Colour is never the only signal.** A status, a validation error or a selected row also carries an
  icon, text, or a shape difference — otherwise it does not exist for a colour-blind user or in
  high-contrast mode.
- Contrast meets **WCAG AA**: 4.5:1 for body text, 3:1 for large text and for the boundary of an
  interactive element and its focus indicator. Check the disabled, hover and dark-mode variants too.
- Text scales: the layout survives 200% zoom and a larger root font size without clipping or horizontal
  scroll. Fixed pixel heights around text are the usual cause.
- Nothing is hidden behind hover alone — a row action revealed only on hover is invisible to touch and
  keyboard users.
- **Images have explicit dimensions** (or an aspect-ratio box) so the page does not shift when they load,
  and meaningful `alt` text — empty `alt=""` for decorative images, deliberately (`web-performance`).
- Animation respects `prefers-reduced-motion`; nothing essential is conveyed only by motion, and nothing
  auto-plays or loops indefinitely in the user's way.

## Content

- **All user-visible text comes from the localisation layer**, including empty copy, error copy,
  placeholders, `alt` text and accessible names (`web-localisation`).
- **Never render a raw enum or server token** (`WAITING_FOR_APPROVE`) to the user — map a closed set to a
  localised label. Free-form server text (names, comments, server messages) is shown verbatim.
- Dates, numbers, currency and relative times are formatted through `Intl` with the active locale and
  time zone — never hand-concatenated, never assumed to be the server's locale.
- Truncation keeps the full value reachable (title attribute, tooltip, or expansion); a truncated id the
  user cannot read or copy is a dead end.

## Lists and tables

- A list renders its rows with a stable `key` from the data (`${CLAUDE_PLUGIN_ROOT}/rules/react.md`).
- Long lists paginate or virtualise, and the loading tail is part of the list rather than a dialog over
  it (`web-performance`).
- A data table uses a real `table` with `th` and `scope`, a caption or accessible name, and sortable
  headers exposing `aria-sort`. A grid of `div`s is not a table to a screen reader.
- One clickable layer per row: a row-level link plus nested buttons inside it is ambiguous for both mouse
  and keyboard — put the actions outside the link's target or make the row non-clickable.

## Consistency

- The same datum renders the same way across surfaces — the status badge on the list row looks and reads
  the same on the detail page.
- Use the existing design-system primitives before inventing a one-off. When a primitive is missing, add
  it to `components/ui`, not to the feature (`web-styling`, `react-component-conventions`).

## Verification

Keyboard-only pass and a zoom/contrast check are part of "done", not a later accessibility sprint. An
automated axe assertion in the component test catches the mechanical half (`web-testing`); the focus
order, the trap and the announcement have to be tried.
