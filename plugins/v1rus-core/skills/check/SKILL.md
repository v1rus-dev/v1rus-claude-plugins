---
name: check
description: |-
  Mechanical verification of the current change: L0 build, L1 static analysis, and L2 tests when the complexity band calls for them, using the project's own commands. Returns PASS or FAIL with the failing level.
  Triggers: "check", "does it build", "run the checks", "verify the change compiles", and between phases of finalize.
  Do NOT use for: semantic review (code-reviewer, finalize), writing tests (write-tests), or running a whole suite after a no-logic edit (a compile is enough).
---

# Check

Mechanical gate, no judgement. Scope the check to the change (see `${CLAUDE_PLUGIN_ROOT}/rules/qa-and-testing.md` § Re-run scope).

1. Find the commands: project CLAUDE.md, README, CI config, then root marker files. Ask only where a guess would be wrong (Xcode scheme, monorepo module ownership).
2. Pick the scope: logic/behavior/signature change: affected module's tests; no-logic change (annotation, rename, imports, comments, strings): compile only; config/markdown only: nothing.
3. Run in order, stopping at the first failing level: L0 build of the affected module, L1 lint/type check (if the project defines them), L2 tests (only when the complexity band is 7+ or the change touched tests).
4. Delegate long builds or test runs to the `test-runner` agent so the output stays out of the main context.
5. Report: `PASS` with the levels run, or `FAIL` with the level, the exact command, and the trimmed error. Do not fix anything here; the caller owns fixes.

Also scan the diff for leftover `TEMP-LOG` lines (see skill `v1rus-logging`); any hit is a FAIL.
