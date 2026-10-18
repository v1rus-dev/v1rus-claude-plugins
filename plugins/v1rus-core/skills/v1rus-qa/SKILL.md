---
name: v1rus-qa
description: "v1rus testing strategy for every code-modifying task: the 1-10 complexity score and the three testing bands (tests are written only from complexity 7 upward), the L0-L2 verification pyramid, the public-API coverage floor, the P0-P3 test priority framework, disposable verification tests, how to scope a test re-run to the change, and the non-negotiable author-fixes-broken-tests rule. Load when planning tests, deciding whether a change needs tests at all, scoping which tests to re-run, or when a change breaks existing tests."
---

# QA & Testing Rules

Project-wide testing decisions, all stacks.

## 0. Mandatory testing strategy

Every code-modifying task gets a testing strategy at planning time, and its depth is driven by the task's **complexity score**. Skipping the strategy *entirely* needs a strong reason ("no code, markdown only"); "simple" / "quick fix" / "obvious" are rejected as reasons to skip — but a **low complexity score is exactly how "simple" is expressed**, and a low score legitimately means less testing.

### Complexity score

- **Scale 1–10.** Assigned by the **planner** (a project pipeline's planning phase, or the main session in plan mode otherwise), then **confirmed or overridden by the user** at the confirmation gate (see the `v1rus-workflow` skill). The planner proposes because it just audited the work; the user has the final word.
- The 1–10 resolution is for estimation feel; behaviour is gated by **three bands** below. A finer number does not create more behaviours — three is the whole repertoire.

### Complexity → testing depth

**Tests are written only from complexity 7.** Below that the work is not worth a test; verification is that it builds, passes static analysis, and clears the quality gate — **no tests are written or run**. Each band is cumulative — it includes everything in the bands below it.

| Score | Band | What runs (cumulative) |
|---|---|---|
| 1–6 | build-only | L0 build + L1 static analysis + `/finalize`. **No tests written.** |
| 7–8 | tested | + L2 unit / integration tests on the changed behaviour — written **and run** |
| 9–10 | critical | + full unit/integration coverage + a written spec as source of truth + all relevant expert reviews (`security-expert` / `performance-expert` / others as relevant) |

The band sets depth; the **public-API floor** (§1) applies **only in the tested bands (≥7)** — below the threshold no tests are written, so the floor is dormant.

### Verification pyramid

Levels are strictly sequential — each requires the previous to pass. **L0 is the implicit entry gate for every band.**

| Level | Name | Description |
|---|---|---|
| L0 | Build | the project — or just the necessary part (the relevant app/module, not always the whole repo) — compiles. Without this, going further is pointless. |
| L1 | Static analysis | lint, type check, code review, dependency audit — always applied |
| L2 | Unit / integration tests | fast — pure logic and cross-component behaviour |

The ladder tops out at L2 (unit / integration).

### Disposable verification tests

Tests don't have to be permanent. To confirm a migration or a one-off / temporary behavior at implementation time, it is valid to **write a test, run it (confirm it actually passes green), then delete it** — verification without committing the test. Distinct from §4: §4 forbids skipping or deleting tests you *broke* (others' coverage); a disposable test is scaffolding you authored and own. Keep a test permanent when the behavior deserves ongoing coverage; use a disposable one when the check is genuinely one-off.

### Test re-run scope — match the check to the change

Re-running the full suite (a multi-minute build) after **every** edit is waste. Scope the verification to what the change can actually affect:

- **Logic / behaviour / signature change** → run the relevant tests (the affected module's suite). This is the only case that needs a real test run.
- **No-logic change** — annotation-only (`@Immutable`/`@Stable`), pure rename/move, import cleanup, constant dedup, dead-code removal, comment/doc/string-resource edits, build-script metadata — a **compile check is sufficient**; do NOT re-run the test suite. Per §1 "No behavior change → no new test", such edits can't change test outcomes.
- **Config / rules / markdown only** → no build or test needed at all.

Corollary for orchestrated pipelines: don't fire a full `test-runner` pass after a trivial cleanup or a one-line gate/annotation swap — a compile (or trusting the implementing agent's own green run) closes it. **Batch fix rounds** so several review findings are fixed, then verified once, rather than test-after-each-finding. Reserve full suite runs for: after the main implementation, after a genuinely large change, and as the final pre-PR gate.

## 1. Public-API coverage gate

In the **tested bands (complexity ≥7)**, a modified public symbol must be exercised by a test — this is the floor within those bands, independent of discretionary depth choices. "Public" = Kotlin without `@internal`/`private`, Swift `public`/`open`, TS `export`; everything else is internal. Below the test threshold (complexity <7) no tests are written, so this gate does not apply.

**Trivial — no test needed:** pure data carriers (`data class`, Swift `struct` with only stored props, TS interfaces, enums, type aliases); builder DSLs with no logic; types re-exporting an already-tested symbol.

**No behavior change → no new test.** A pure file move/rename, repackaging, relocating a symbol, or import-only edit is **not** "modifying" the symbol — existing tests + a green build already cover it. Never add unit tests on top of a no-logic move; that is over-testing, the same noise as over-editing. The gate triggers on changed behavior or signature, not on a symbol merely changing location.

**Test-matching (priority order):** (1) file-name `Foo.kt` ↔ `FooTest.kt` / `FooTests.swift` / `Foo.test.ts`; (2) symbol name appears in any test file in the same module; (3) explicit annotation (`@CoveredBy("...")`). None resolves → gate fails: write a test or annotate trivial before the quality gate (`/finalize`) passes.

## 2. Test priority framework

Classify each case: **P0** release-critical (crash, data-loss, security, payment, auth — failure blocks release); **P1** AC-driven (one test per AC-N from the spec, named after that AC); **P2** happy path (one most-common success flow per surface); **P3** edges (boundaries, empty, locale/timezone, large inputs, races). P4 (cosmetic/exploratory) excluded from formal plans.

## 3. Lightweight test plan (pure-logic surface)

When the surface is API/library/CLI (no end-user UI) and no `ux-expert` review is in scope, cover only: input validation (types, ranges, malformed), state transitions (input → observable change), error paths (which exception/error code, when). This is the default shape for almost everything.

## 4. Author fixes broken tests in the same run — non-negotiable

Whoever breaks existing tests fixes them in the same PR. `@Ignore` / `xit` / `t.Skip` **forbidden** without a tracked-issue link in the annotation (`@Ignore("flaky on iOS 17 — JIRA-1234")`). No "merge red", no "fix later". The test run (`test-runner` / the quality gate) is the gate; a skip without a tracked issue is a violation.

## 5. Test infrastructure — project-defined

The concrete runner, task names, and commands are the **project's** responsibility — read them from the project's own instructions (`<repo>/CLAUDE.md`) or build config, not from a universal table here. If the project doesn't specify, infer from root marker files (`build.gradle*` / `Package.swift` / `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` / `Makefile`) plus the build config — and **block and ask** wherever a guess would be wrong: Xcode scheme/destination, Python runner flags, which module owns the changed files in a monorepo.

## 6. Verification source of truth

A mandatory planning output — defines "done", the contract the **acceptance gate** verifies against (see the `v1rus-workflow` skill).

| Type | Use when | Artifact |
|---|---|---|
| Task / requirements | explicit AC or clear task | plan notes / AC list (`requirements.md` in a pipeline task) |
| Spec | too large to hold in head; traceable ACs | a written spec doc (`docs/specs/<slug>-spec.md`) |
| Test plan | structured executable cases | a test-plan doc (the `generate-test-plan` skill, or a project pipeline's test-planning phase) |
| Design mockups | UI/UX visual ACs | Figma in the spec, or screenshots — used as a **manual** review reference |
| Debug artifact | bug-fix only — repro steps are the contract | `swarm-report/<slug>-debug.md` |
| Behavioral baseline | migration / "shouldn't affect behavior" | captured before changes (see the `v1rus-workflow` skill § Before-state baseline) |

**Behavioral baseline:** for "shouldn't affect behavior" / "migrate without breaking" the before-state IS the truth. Full definition — what qualifies, what does not, the test-coverage shortcut — lives in the `v1rus-workflow` skill § Before-state baseline (single source). In short: capture before any change (existing passing tests, or API/output snapshots), save to `swarm-report/<slug>-baseline.md`, then the acceptance gate verifies after-state matches 1:1. "should be fine" is not a source of truth.

**Absent source:** if none exists and creating one isn't feasible, document in the plan: intended behavior (one paragraph), why no formal source, what proxy is used (e.g. task description). The acceptance gate blocks when no source is found; the justification supplies the proxy — it does not bypass the gate.
