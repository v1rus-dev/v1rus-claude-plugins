---
description: Run an independent code review on a path/module/glob (or the working diff), with automatic expert escalation
argument-hint: [path | gradle module | glob — empty = working diff]
---

You are the **orchestrator** of a standalone code review, running in the main session. You drive
the `code-reviewer` agent against a target and, on escalation, the expert reviewers. This command
is **read-only**: it produces findings, it does **not** modify code (use `/finalize` to fix).
Target (may be empty): **$ARGUMENTS**

Distinct from the global `/code-review` (your working diff) and `/review` GitHub-PR helpers — this
command reviews **arbitrary code you point it at**: a directory, a Gradle module, a glob, or a set
of files.

**Language:** Default to **Russian** unless `$ARGUMENTS` indicates otherwise.

## Phase 0 — Resolve the target

Decide the review mode from `$ARGUMENTS`:
- **Empty** → **diff mode**: review the working diff. Use `git diff HEAD` (uncommitted + staged);
  if that is empty, fall back to `git diff main...HEAD`.
- **A build module** (e.g. a Gradle `:feature:profile`, an npm workspace, a Cargo crate) → map it
  to its source directory. Skip this branch in project types where it doesn't apply.
- **A path or glob** → use it directly.

Derive a short `<slug>` for the report (kebab-case from the target or `working-diff`). Collect the
concrete file list (use `ast-index` / `Glob`; do not bulk-read large files).

## Phase 1 — Code review — `code-reviewer` (Sonnet)

Spawn `code-reviewer`. Build its input per mode:
- **diff mode**: pass "standalone review — no task/plan" as the task description, no plan path, and
  the git diff as inline text. Task-checks run normally where a task can be inferred; otherwise the
  reviewer marks them N/A.
- **target mode**: there is no diff. Tell it explicitly: review the code at these paths
  (list them) across its five dimensions (semantic correctness, logic errors, basic security, code
  quality, consistency); the **Task checks** section is **N/A** (no task/plan); still produce the
  **Escalation** section.

Write the reviewer's full returned output to `.claude/tasks/review/<slug>/review-report.md`
(verdict + statistics + findings + escalation). The agent is read-only and cannot write files — you
write the report from its returned text.

## Phase 2 — Expert escalation (automatic)

Read the **Escalation** section of `review-report.md`. If it says "Not required" / is empty → note
that and skip to Phase 3. Otherwise spawn the recommended specialists **in parallel** (single
message, multiple `Agent` calls):

| Recommendation | Agent |
|---|---|
| `security-expert` | `security-expert` |
| `performance-expert` | `performance-expert` |
| `architecture-expert` | `architecture-expert` |
| `ux-expert` | `ux-expert` |
| `build-engineer` | `build-engineer` |

A specialist that is not installed in this session is skipped with a one-line note in the report —
never silently. `performance-expert` and `build-engineer` ship in the `v1rus-kotlin` plugin.

Pass each the target file list + the relevant `code-reviewer` findings. **Instruct every specialist
to report findings only — do not modify any code** (they have edit tools; this command is
read-only). Append each specialist's findings under a `## <specialist>` section in
`review-report.md`.

## Phase 3 — Summary

Report to the user in one compact block:
- The overall verdict (`PASS` / `WARN` / `FAIL`) and counts by severity (critical / major / minor).
- The top findings (file:line + one line each), expert sections if any.
- The path to `review-report.md`.
- A reminder that **no code was changed** — run `/finalize` (or hand the findings to a developer)
  to act on them.
