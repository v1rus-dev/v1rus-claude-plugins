---
name: compose-file-organisation
description: "How Compose code is laid out in files in a v1rus project: every @Composable function and every group of related DSL extensions gets its own file named after it, LazyListScope section groups go into a dedicated *Sections.kt rather than the screen file, content-item composables go into their own sub-package file, every composable file carries at least one @Preview, and the State/Intent/Effect model file is the one deliberate exception that keeps three declarations together. Load when creating a composable, splitting a screen file, reviewing file layout, or wondering where a new composable belongs."
---

# Compose File Organisation

The rule lives in `${CLAUDE_PLUGIN_ROOT}/rules/compose-files.md` and is injected automatically before
any edit under a feature, design-system, presentation or UI package — so when you are writing the code
it is usually already in context. Read it directly when reviewing rather than editing.

In one line: **one composable per file, named after the composable, with at least one `@Preview`** —
and `State` / `Intent` / `Effect` stay together in a single `<Feature>ModelUi.kt`.

Why it is worth the file count: a screen assembled from single-composable files is previewable
piece-by-piece, diffs stay local to the composable that changed, and the `internal` visibility that
keeps features from depending on each other (see `mvi-presentation`, and on a KMP project
`v1rus-kmp:kmp-conventions`) has a file-shaped boundary to attach to.
