---
name: flutter-ui-conventions
description: "The Flutter widget and accessibility checklist a v1rus screen must satisfy before review: every screen handles loading / empty / error-with-retry / content (plus not-found for a fetched detail), back navigation reachable in every state including error and loading, colours and typography exclusively from ThemeExtension tokens rather than Colors.* or hardcoded Color values, tap targets at least 48dp with a Semantics label on every interactive control, ListView.builder with keys for dynamic lists, const constructors, no logic or async work in build, no raw enum rendered to the user, and disposal of every controller. Load before writing or reviewing any widget or screen."
---

# Flutter UI Conventions

The high-frequency miss-list. An implementer satisfies it up front; a reviewer checks it. Not
exhaustive — for a non-trivial screen still run a `ux-expert` review, and prefer reviewing the design
before the code.

## Screen states and navigation

- Every screen handles **loading / empty / error (+retry) / content**; a fetched detail screen also
  handles **not-found**. No state renders as a blank screen. The state union makes this checkable
  (`bloc-conventions`).
- **Back navigation must be reachable in every state** — including loading and error. Put the
  `AppBar` / back affordance **outside** the state `switch`, never only in the content branch. A network
  error that leaves the user with no way back is a trap, and it is the single most common finding here.
- Empty states carry human copy from resources ("Ничего не найдено"), not emptiness.
- A deep link can open any screen cold: it must load from its route parameters and handle unauthorized
  itself (`flutter-navigation`).

## Theming — tokens only

- Colours, typography, spacing, radii and durations come from the app theme via **`ThemeExtension`**
  tokens in `design_system`. **Never `Colors.red`, never `Color(0xFF…)`, never a hardcoded `TextStyle`,
  never a magic `EdgeInsets` number** in feature code — including status, weekend and semantic colours:
  add a token instead.
- The only place raw values are allowed is inside `design_system` where the theme is defined.
- Both light and dark themes are defined and checked. A token that only looks right in one of them is
  incomplete.
- Reading a token is `Theme.of(context).extension<AppTokens>()!` behind a small extension
  (`context.tokens`), so call sites stay short.

## Interactive elements and accessibility

- Every tappable thing has a **≥48×48 dp** target — `IconButton`, or explicit `constraints` /
  `minimumSize`. A bare `GestureDetector` around a 16 dp icon fails on real fingers.
- Every interactive control has an accessible name: a visible label, or a `Semantics(label:)` /
  `tooltip` from a string resource. Decorative-only images use `ExcludeSemantics` deliberately.
- Respect the platform text scale: no fixed-height container that clips at 200% text scale. Test one
  screen at large text before calling a UI task done.
- Contrast, focus order and hit areas are part of "done", not a later accessibility pass.

## Widgets

- **No logic in `build`.** No network calls, no `await`, no computation that could be `late final` or
  hoisted. `build` runs often and unpredictably; work placed there runs that often too.
- **`const` constructors and `const` widget literals wherever possible** — this is what lets Flutter skip
  rebuilding subtrees.
- Extract widgets into **classes, not methods returning `Widget`**. A `_buildHeader()` method cannot be
  `const`, cannot be skipped in a rebuild, and does not show up as its own element in the tree.
- Keep the widget tree shallow where it costs nothing; avoid a `Container` that only adds padding.
- **After every `await` in a callback, check `context.mounted`** before touching the context. The
  analyzer catches many of these, not all — an unmounted context is a crash.
- **Dispose everything you create**: `AnimationController`, `TextEditingController`, `ScrollController`,
  `FocusNode`, `StreamSubscription`. A missing `dispose` is a leak that survives navigation.

## Lists

- Dynamic lists use `ListView.builder` / `SliverList` with a **stable `key`** per item — never index-based
  identity for a reorderable or filterable list.
- Hoist per-item work out of `itemBuilder`; precompute in the state, not during scroll.
- Long lists get `itemExtent` / `prototypeItem` when items are uniform — it removes layout cost per frame.
- Paginate rather than loading everything; show the loading tail as part of the list, not as a dialog.

## Text

- All user-visible text comes from resources, **including fallbacks and placeholders**
  (`flutter-localisation`).
- **Never render a raw enum or server token** (`WaitingForApprove`) to the user — map closed sets to
  localised labels.
- Free-form server text (names, comments, server messages) is shown verbatim and not localised.

## Consistency

- The same datum renders the same way across surfaces.
- Use existing `design_system` components before inventing a one-off. When a component is missing, add it
  to `design_system` — not to the feature.
- Avoid card-in-card and double elevation; one clickable layer per row.

## API verification

Flutter's widget and Material APIs move fast, and Material 3 defaults changed across releases. Before
writing a non-trivial widget, check the current API and the recommended approach for the Flutter version
the project uses — the trust-tier and multi-channel rules are in the `v1rus-sources` skill.
