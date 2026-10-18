---
name: check
description: "Verification gate — run the project's build, its static analysis, and only the tests the current change can actually affect, then report one PASS or FAIL with the real failing output. This is the 'does it work' gate (L0 build + L1 static analysis + L2 scoped tests), distinct from finalize (how the code is written) and acceptance (what the code does). Load when asked to check, verify, or validate a change, between finalize rounds, after applying fixes, or before offering a PR. Never edits code."
---

# Check

Run the verification levels the change requires and report a single verdict. This skill **executes
and diagnoses — it never edits code.** A failure is reported back to whoever wrote the change; the
author fixes it (see the `v1rus-qa` skill § 4).

`check` owns **whether it works**. `finalize` owns **how it is written**. The acceptance gate owns
**what it does**. Running one does not close another.

## Scope the run to the change — do not reflexively run everything

A full multi-minute suite after every edit is waste. Pick the level from what the change can
affect (the rule is defined once in the `v1rus-qa` skill § "Test re-run scope"):

| Change | What to run |
|---|---|
| Config, rules, markdown only | nothing — no build, no tests |
| Annotation-only, pure rename/move, import cleanup, dead-code removal, comment/string edits | L0 compile of the affected module only |
| Logic, behaviour or signature change | L0 + L1 + L2 for the affected module(s) |
| Large change, cross-module change, or the final pre-PR gate | L0 + L1 + full relevant suite |

When several review findings are being fixed, **batch them** and check once — not once per finding.

## L0 — Build

Compile the affected part, not always the whole repo. Discover the command instead of guessing:
read the project's `CLAUDE.md` first, then the root marker file (`build.gradle*`, `Package.swift`,
`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Makefile`, `*.csproj`).

If the project documents its build and test tasks, use exactly those. If it does not and a wrong
guess is plausible — an Xcode scheme or destination, a Python runner's flags, which module owns the
changed files in a monorepo — **stop and ask** rather than running something arbitrary.

L0 failing means every later level is meaningless: report and stop.

## L1 — Static analysis

Whatever the project actually has configured, in its own invocation: linters (ktlint, detekt,
SwiftLint, ESLint, ruff, clippy, `go vet`), type checks (`tsc --noEmit`, mypy), and the build's own
warnings-as-errors setup. Do not introduce a tool the project has not adopted, and do not "fix" a
pre-existing violation outside the diff — report it separately as untouched debt.

## L2 — Tests

Run the tests covering the changed behaviour. Below complexity 7 no tests were written for the
change, so L2 here means "the existing suite for the affected module still passes", not "new tests
exist".

**Delegate long runs.** If the project provides a `test-runner` agent, dispatch the run to it — a
multi-minute build must not consume the orchestrating session's context. Otherwise run it directly
and keep the output out of context by capturing failures only.

A skipped or `@Ignore`d test without a tracked-issue link is a FAIL, not a pass (`v1rus-qa` § 4).

## Report

One verdict, then only what is actionable:

```
CHECK: PASS | FAIL
Levels run: L0 <task> | L1 <tools> | L2 <tasks>   (and what was deliberately skipped, with the reason)

FAIL details (omit when PASS):
- <module>:<test or file>  — <one-line cause>
  <the real error output, trimmed to the relevant lines>
```

Never report PASS for a level that was not run — say it was skipped and why. "Should be fine",
"looks correct", and "the build probably passes" are not verification.
