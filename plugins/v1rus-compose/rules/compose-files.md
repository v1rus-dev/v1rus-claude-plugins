---
paths:
  - "**/feature/**/*.kt"
  - "**/features/**/*.kt"
  - "**/designsystem/**/*.kt"
  - "**/design_system/**/*.kt"
  - "**/presentation/**/*.kt"
  - "**/ui/**/*.kt"
---

# Compose File Organisation

Every `@Composable` function and every group of related DSL extension functions lives in its **own
file**. Never add a Composable or DSL helper to an existing file just because it is convenient.

- Each `@Composable` function → its own file, named after the composable (`ProfileUserCard.kt`,
  `ProfileScreenSections.kt`, …).
- `LazyListScope` extension groups (loading / error / success sections) → a dedicated `*Sections.kt`
  file, not inside the screen file that calls them.
- Each content-item composable → its own file inside the relevant sub-package (e.g.
  `profile_content_items/ProfileSkillsItem.kt`).
- Every composable file must include at least one `@Preview`.

The `State` / `Intent` / `Effect` model file is the deliberate exception: those three stay **together**
in one `<Feature>ModelUi.kt` (see the `mvi-presentation` skill). One-composable-per-file applies to
composables, not to the screen's contract.
