---
name: compose-screen-checklist
description: |-
  Review procedure for a finished or planned Compose screen: screen states, back navigation in every state, touch targets and contentDescription, theme tokens, string resources and enum label mapping, lazy-list keys, consistency. Use when a screen or composable is implemented, before calling a UI task done, when reviewing a UI plan or PR, or on the question "what did I miss on this screen".
  Not for: writing composables from scratch (the rules inject on edit), visual fidelity against a mockup (manual comparison with the design), performance profiling (compose-performance), or non-Compose UI.
---

# Compose screen checklist

The checklist text is `${CLAUDE_PLUGIN_ROOT}/rules/compose-screen-quality.md`; the structural rules (Destination/Screen, parameter types, previews) are `${CLAUDE_PLUGIN_ROOT}/rules/compose-ui.md`. Read both.

Procedure:
1. List the screen's states from its state model; confirm each has a composable and none is blank. Check the back affordance is outside the state switch.
2. Walk every interactive element: target size, role/contentDescription from resources.
3. Grep the diff for `Color(0x`, `Color.`, hardcoded strings, raw enum `.name`/`toString()` in text, `Icon(... clickable`, lazy items without `key`.
4. Check the same datum is rendered consistently across the screens that show it.
5. Report only real findings (file:line, what, fix). For a non-trivial screen or a UI plan, ask the ux-expert agent (v1rus-core) for an independent review; for scroll/recomposition concerns use `compose-performance`.
