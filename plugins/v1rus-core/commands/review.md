---
description: Run an independent read-only code review on a path/module/glob (or the working diff), with automatic expert escalation
argument-hint: [path | module | glob; empty = working diff]
---

You are the orchestrator of a standalone, read-only code review. You drive the `code-reviewer` agent against a target and, on escalation, the expert reviewers. This command produces findings and never modifies code (use the `finalize` skill to fix). Target (may be empty): **$ARGUMENTS**

Distinct from the built-in `/code-review` (your working diff or a PR): this command reviews arbitrary code you point it at.

## 1. Resolve the target

- Empty: diff mode. Use `git diff HEAD`; if empty, `git diff <default-branch>...HEAD`.
- A build module or workspace member: map it to its source directory.
- A path or glob: use it directly.

Derive a kebab-case `<slug>` (or `working-diff`) and collect the concrete file list (symbol index or Glob; do not bulk-read large files).

## 2. Code review

Spawn `code-reviewer`. In diff mode pass "standalone review, no task/plan" plus the diff inline. In target mode there is no diff: tell it to review the code at the listed paths across its dimensions, mark Task checks as N/A, and still produce the Escalation section. Write its full output to `swarm-report/review-<slug>.md` (the agent is read-only; you write the file).

## 3. Expert escalation

Read the Escalation section of the report. If it requires nothing, skip. Otherwise spawn the recommended specialists in parallel (single message): `security-expert`, `architecture-expert`, `ux-expert`, plus a performance or build-system specialist if one is installed. Pass each the file list and the relevant findings, and instruct every specialist to report findings only and not modify any code. Append each under a `## <specialist>` section of the report.

## 4. Summary

One compact block: overall verdict (PASS/WARN/FAIL), counts by severity, top findings (file:line, one line each), the report path, and a reminder that no code was changed (run `finalize` to act on findings).
