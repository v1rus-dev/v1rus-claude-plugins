---
paths:
  - "**/*{Test,Tests,Spec,_test,.test,.spec}.*"
  - "**/{test,tests,__tests__,spec}/**"
---

# QA and testing

Project-wide testing decisions, all stacks. The concrete runner, task names and commands belong to the project: read them from the project's CLAUDE.md or build config. If they are not specified, infer from root marker files and the build config, and ask where a guess would be wrong (Xcode scheme/destination, runner flags, which module owns the files in a monorepo).

## Complexity score and testing depth

Every code-changing task gets a testing strategy at planning time. A **complexity score 1-10** is proposed by the planner and confirmed or overridden by the owner. Only three bands matter, each cumulative:

| Score | Band | What runs |
|---|---|---|
| 1-6 | build-only | L0 build + L1 static analysis + the quality gate. No tests written. |
| 7-8 | tested | + L2 unit/integration tests on the changed behavior, written and run |
| 9-10 | critical | + full unit/integration coverage, a written spec as source of truth, all relevant expert reviews (security, performance, ...) |

Verification pyramid, strictly sequential: **L0** the affected module compiles; **L1** static analysis (lint, type check, review, dependency audit); **L2** unit/integration tests. The ladder tops out at L2.

A **disposable verification test** is valid: write it, run it green, delete it, to confirm a one-off migration or temporary behavior. It is scaffolding you own, distinct from skipping tests you broke.

## Re-run scope

Match the check to the change. Logic, behavior or signature change: run the affected module's tests. No-logic change (annotations, rename/move, imports, constants, dead code, comments, strings, build metadata): a compile check is enough. Config, rules or markdown only: no build or test. Batch review-fix rounds and verify once; reserve full-suite runs for after the main implementation, after a large change, and as the final pre-PR gate.

## Public-API coverage gate (tested bands only)

In bands 7+, a modified public symbol must be exercised by a test. "Public" = Kotlin without `private`/`internal`, Swift `public`/`open`, TS `export`, Go exported identifiers; the rest is internal. Not required for pure data carriers, DSL builders without logic, or re-exports of tested symbols. A pure move/rename/import edit is not a modification: add no tests. Matching order: file name (`Foo` to `FooTest`/`foo_test`/`Foo.test`), then the symbol name appearing in a test of the same module, then an explicit coverage annotation. No match: write a test or mark trivial before the quality gate passes.

## Test priority

**P0** release-critical (crash, data loss, security, payment, auth); **P1** one test per acceptance criterion, named after it; **P2** the most common success flow per surface; **P3** edges (boundaries, empty, locale/timezone, large inputs, races). P4 (cosmetic) is excluded from formal plans. For API/library/CLI surfaces the default shape is: input validation, state transitions, error paths.

## Whoever breaks a test fixes it

Same change, no "fix later". `@Ignore` / `xit` / `t.Skip` are forbidden without a tracked-issue link in the annotation. No merging red.

## Verification source of truth

A planning output that defines "done" and is what the acceptance gate verifies against:

| Type | Use when | Artifact |
|---|---|---|
| Task/requirements | explicit AC | plan notes / AC list |
| Spec | too large to hold in head | `docs/specs/<slug>-spec.md` (`write-spec`) |
| Test plan | structured executable cases | `generate-test-plan` |
| Design mockups | UI visual ACs | Figma/screenshots, reviewed manually |
| Debug artifact | bug fix | `swarm-report/<slug>-debug.md` with repro steps |
| Behavioral baseline | migration / "must not change behavior" | captured before changes |

With no source and no feasible way to create one, record in the plan: intended behavior (one paragraph), why no formal source, and the proxy used. The acceptance gate does not pass without a source; the justification supplies a proxy, it does not bypass the gate.

Baseline details and task-type routing: `${CLAUDE_PLUGIN_ROOT}/skills/v1rus-workflow/reference/task-types.md`.
