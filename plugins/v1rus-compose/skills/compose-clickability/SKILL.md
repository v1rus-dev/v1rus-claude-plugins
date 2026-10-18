---
name: compose-clickability
description: Use this skill when adding click handling to any Compose composable — cards, list items, icons, rows, chips, or custom shapes. Covers the mandatory clip-before-clickable rule, ripple containment, touch target sizing, interactionSource lifecycle, indication null patterns, nested click handling, and accessibility roles. Use when the developer adds Modifier.clickable, combinedClickable, pointerInput, or notices ripple bleeding outside a rounded shape.
metadata:
  keywords:
  - jetpack-compose
  - clickable
  - ripple
  - clip
  - touch-target
  - interactionsource
  - compose-multiplatform
  - accessibility
---


> **Scope note.** This skill documents the v1rus Compose **reference architecture** as implemented in
> the flagship project. The patterns are the standard; the concrete type and file names
> (`StoreViewModel`, `AppNavigator`, `AppTheme`, `AppRes`, module paths) are that project's. In
> another v1rus project, read its `CLAUDE.md` first and map the names to its equivalents — do not
> assume a type exists because it is named here.

# Compose Clickability — Everything You Need to Know

## The Cardinal Rule: `clip` Before `clickable`

**Always apply `Modifier.clip(shape)` immediately before `Modifier.clickable` when the composable has a non-rectangular shape.**

Without `clip`, the ripple effect is drawn in the composable's **layout bounds** — a rectangle. The clip is what constrains it to the visible shape boundary.

```kotlin
// WRONG — ripple bleeds outside the rounded corners
Modifier
    .border(1.dp, AppTheme.colors.divider, cardShape)
    .background(AppTheme.colors.background, cardShape)
    .clickable { ... }
    .padding(16.dp)
```

```kotlin
// RIGHT — ripple is clipped to the card shape
Modifier
    .border(1.dp, AppTheme.colors.divider, cardShape)
    .background(AppTheme.colors.background, cardShape)
    .clip(cardShape)          // ← must come before clickable
    .clickable { ... }
    .padding(16.dp)
```

The same rule applies to any shaped surface: `CircleShape`, `RoundedCornerShape`, `CutCornerShape`, or any custom `Shape`.

### Canonical Card Pattern

```kotlin
@Composable
internal fun InquiryListCard(
    item: InquiryListItemModelUi,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val cardShape = AppTheme.shapes.medium
    Row(
        modifier = modifier
            .fillMaxWidth()
            .border(1.dp, AppTheme.colors.divider, cardShape)
            .background(AppTheme.colors.background, cardShape)
            .clip(cardShape)           // ripple stays inside rounded corners
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 12.dp),
    ) { ... }
}
```

---

## Modifier Order Matters

Modifiers are applied top-to-bottom. The order of layout/drawing modifiers is significant:

| Order | Effect |
|-------|--------|
| `background` → `clip` → `clickable` | Background shows, ripple clipped to shape ✓ |
| `clip` → `background` → `clickable` | Background clipped, ripple clipped ✓ (usually the same visual result) |
| `background` → `clickable` → `clip` | Ripple NOT clipped — bleeds outside shape ✗ |
| `clickable` → `clip` | Ripple NOT clipped ✗ |

**Rule:** `clip` must precede `clickable` in the modifier chain. Anything after `clickable` is inside the click handling context.

Padding placed **after** `clickable` makes the touch target smaller (only the content area responds). Padding placed **before** `clickable` expands the touch target:

```kotlin
// Touch target includes the 16dp padding → larger tap area
Modifier.padding(16.dp).clickable { ... }

// Touch target is only the content inside the padding → smaller tap area
Modifier.clickable { ... }.padding(16.dp)
```

---

## `clickable` vs `combinedClickable`

Use `clickable` for single-tap actions. Use `combinedClickable` only when you need long press or double tap:

```kotlin
// Single tap only — prefer clickable
Modifier.clickable { onClick() }

// Long press needed — use combinedClickable
Modifier.combinedClickable(
    onClick = { onClick() },
    onLongClick = { onLongClick() },
)
```

Do NOT use `combinedClickable` just to get `onClick` — it registers extra gesture recognizers for no reason.

---

## Removing the Ripple (`indication = null`)

Suppress the ripple when the component provides its own visual feedback (custom pressed state, explicit animation):

```kotlin
Modifier.clickable(
    interactionSource = remember { MutableInteractionSource() },
    indication = null,
    onClick = { ... },
)
```

**Both** `interactionSource` and `indication` must be provided together when overriding either. Providing one without the other causes a compile error (overload resolution).

---

## Shared / Reusable Components — Always Pass `interactionSource` and `indication` Explicitly

When writing a **shared or reusable component** (a card, chip, list item, icon button, or any composable used in more than one place), **always** pass `MutableInteractionSource` and `indication = ripple()` explicitly to `clickable`. Never rely on the default overload.

This keeps the component's interaction behaviour transparent and controllable by callers:

```kotlin
// WRONG — shared component with implicit ripple; caller cannot control it
@Composable
fun AppCard(onClick: () -> Unit, modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    val shape = AppTheme.shapes.medium
    Box(
        modifier = modifier
            .clip(shape)
            .clickable { onClick() }   // ripple source hidden, cannot be overridden
    ) { content() }
}

// RIGHT — explicit interactionSource and indication
@Composable
fun AppCard(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    interactionSource: MutableInteractionSource = remember { MutableInteractionSource() },
    content: @Composable () -> Unit,
) {
    val shape = AppTheme.shapes.medium
    Box(
        modifier = modifier
            .clip(shape)
            .clickable(
                interactionSource = interactionSource,
                indication = ripple(),
                onClick = onClick,
            )
    ) { content() }
}
```

Exposing `interactionSource` as a parameter allows the caller to:
- Observe pressed/hovered state to animate a border, scale, or elevation.
- Share the source between the clickable and a separate ripple layer.
- Suppress the ripple selectively by passing `indication = null` at the call site.

**Memory leak rule:** `MutableInteractionSource()` must always be inside `remember { }`. A bare constructor in a composable body is re-created every recomposition and the old instance is leaked.

```kotlin
// WRONG — leaked on every recomposition
interactionSource = MutableInteractionSource()

// RIGHT
interactionSource = remember { MutableInteractionSource() }
```

### Observing Pressed State

When you need custom press feedback (scale, border colour, elevation), read from the same `interactionSource`:

```kotlin
val interactionSource = remember { MutableInteractionSource() }
val isPressed by interactionSource.collectIsPressedAsState()

Box(
    modifier = Modifier
        .clip(cardShape)
        .clickable(
            interactionSource = interactionSource,
            indication = ripple(),
            onClick = onClick,
        )
        .scale(if (isPressed) 0.97f else 1f),
) { ... }
```

---

## Nested Clickables

Compose handles click propagation — a child `clickable` consumes the event and the parent does NOT fire:

```kotlin
// Parent click fires only when tapping outside the child button
Box(modifier = Modifier.clickable { onParentClick() }) {
    Button(onClick = { onChildClick() }) { Text("Child") }
}
```

This works correctly by default. **Avoid creating unnecessary nested clickables** — use a single `clickable` on the topmost container whenever possible and route intent via a lambda parameter.

---

## Accessibility and Semantic Roles

Always declare the role so screen readers announce the element correctly:

```kotlin
// Card or list item
Modifier.clickable(role = Role.Button, onClick = { ... })

// A toggle (checkbox, switch semantics without the widget)
Modifier.toggleable(
    value = isChecked,
    role = Role.Checkbox,
    onValueChange = { onCheckedChange(it) },
)

// Item in a group where only one is selected at a time
Modifier.selectable(
    selected = isSelected,
    role = Role.RadioButton,
    onClick = { onSelect() },
)
```

Common roles: `Role.Button`, `Role.Checkbox`, `Role.RadioButton`, `Role.Switch`, `Role.Tab`, `Role.DropdownList`.

---

## Anti-Patterns

```kotlin
// BAD: no clip before clickable on a shaped composable — ripple bleeds
Modifier
    .background(color, RoundedCornerShape(12.dp))
    .clickable { ... }

// BAD: clip after clickable — ripple not constrained
Modifier
    .clickable { ... }
    .clip(RoundedCornerShape(12.dp))

// BAD: MutableInteractionSource without remember — memory leak
Modifier.clickable(
    interactionSource = MutableInteractionSource(),   // leaked every recomposition
    indication = null,
    onClick = { ... },
)

// BAD: combinedClickable when only onClick is needed
Modifier.combinedClickable(onClick = { ... })   // use clickable instead

// BAD: touch target smaller than 48dp with no padding
Modifier.size(20.dp).clickable { ... }
```

---

## Checklist

- [ ] If the composable has a non-rectangular shape: `clip(shape)` appears **before** `clickable` in the modifier chain.
- [ ] Shared / reusable components pass both `interactionSource = remember { MutableInteractionSource() }` and `indication = ripple()` explicitly to `clickable`.
- [ ] `MutableInteractionSource()` is always inside `remember { }`.
- [ ] `indication = null` is only used with an explicit `interactionSource`.
- [ ] `combinedClickable` is used only when long press or double tap is required.
- [ ] `Modifier.selectable` / `Modifier.toggleable` is used instead of `clickable` for toggle/radio semantics.
- [ ] `role = Role.Button` (or the appropriate role) is declared on non-Button clickable elements.
