---
name: v1rus-workflow
description: "v1rus gate discipline for any code-modifying task: the mandatory preparation, quality, acceptance and PR-promotion gates, what closes each one, and the task-type routing matrix (feature, bug fix, tech migration, version bump, refactor, infrastructure, UI, performance, research) with its source-of-truth, test-timing and before-state-baseline requirements. Load before starting an implementation, when deciding whether a task is ready to code, when choosing the verification source of truth, when judging whether the work is done, or before offering a PR."
---

# Recommended Workflow

This file defines a **gate discipline** — *what* must be true before a task moves forward and *why* — independent of any specific tool. It is not a forced pipeline: pick what the task needs and let plan mode drive sequencing.

**Gates are abstract; closure is per-project.** Each gate below states an outcome that must hold. *How* it is closed depends on what the current project actually provides:

- **Project with a feature pipeline:** the pipeline's own phases close most gates internally (its confirmation gate, finalize + code-review loop, expert-reviews) by dispatching the global expert/engineer agents. Run the pipeline and let it drive; this file explains what those phases are *for*.
- **Project without a pipeline:** close each gate manually with the building blocks that exist — `/finalize`, `/code-review`, `/simplify`, `/security-review` skills; the `research` skill for unknowns; the `code-reviewer` / `security-expert` / `performance-expert` / `architecture-expert` / `ux-expert` / `build-engineer` review agents and `test-runner` (via the Agent tool); `gh` for PRs.

Never assume a named skill/command exists — verify against the session's available skills and the project's `.claude/`. A gate whose ideal tool is absent is still mandatory: close it with whatever the project has, and say which tool you used.

## Mandatory gates

**Preparation gate — before any implementation.** Gather, autonomously and research-first, what's needed to build *and* verify — three outputs, actually collected, not just named:
- **Sources of truth** (what "done" means): spec/AC, before-state baseline, screenshots/Figma, debug-repro. Actively *produce* them — snapshot the baseline before a migration (existing passing tests, or API/output snapshots). What you can't make yourself and is missing → ask the user, naming what verification degrades without it. Detail: the `v1rus-qa` skill §6 + § Task type routing below § Before-state baseline. Starting implementation without the sources of truth needed to verify it is not allowed.
- **Knowledge sources** (how to build it): trusted docs/source per tier T1–T4 — see the `v1rus-sources` skill. Agent memory and project code go stale; on a gap or doubt, verify against the official source, don't act from memory. Missing understanding or stuck → research first (the `research` skill — parallel expert investigation of options/feasibility before implementation), not a question to the user.
- **Testability + decomposition**: assess how hard the change is to verify and propose simplifications up front (sample/sandbox app, extracting logic to a unit boundary) so a prototype is exercised fast; decompose a task too large for one plan. Detail: § Task type routing below § Test feasibility gate.

Autonomy: concentrate questions in this prep phase; once sources are gathered, proceed without round-tripping. A standard/obvious solution — apply it, don't ask. Skip prep only for the same trivial cases as the gates below.

In a project with a feature pipeline this gate is its requirements + architecture + **confirmation gate** phases (the pipeline pauses for plan approval and complexity scoring before any code). Outside one: do it in plan mode.

**Quality gate — `/finalize`.** Required after every implementation where code was written — before declaring the task done. `/finalize` owns *how the code is written*: a full **review → fix → simplify** loop that iterates until no findings above Minor severity remain, or exits with ESCALATE requiring a user decision. A standalone run of `code-reviewer` does **not** close this gate — review alone leaves the fix and simplify steps unperformed; «код уже отревьюен» is not grounds to skip it.
- *Pipeline project:* the pipeline runs the `/finalize` skill + `code-reviewer` (loops finalize → code-review until PASS, then dispatches expert reviews on escalation).
- *Otherwise:* run `/finalize` — it orchestrates the full review→fix→simplify loop.
- Exceptions (skip the gate): pure documentation edits, config-only changes with no logic, single-line mechanical changes with an obvious result.

**Acceptance gate — it works as intended.** Runs after the quality gate, before PR promotion. Verifies the implementation against the source of truth (spec, test plan, design, or behavioral baseline). Orthogonal to the quality gate: quality checks *how the code is written*, acceptance checks *what the code does* — neither replaces the other, both mandatory. Same exceptions as the quality gate.
- *Closure:* **automated verification only** — the `test-runner` agent runs the build + the relevant test tasks; the tests covering the acceptance criteria must pass. For non-UI changes, exercise the changed contract through a test rather than by hand.

**PR promotion gate.** **Never open a PR (draft or ready) on your own initiative** — opening one is always an explicit user request, never an automatic step. When the work is ready, *offer* to open a draft PR and wait for the user's go-ahead. Promoting **draft → ready for review** likewise requires explicit user confirmation: it signals the task is complete and makes it visible to reviewers — a shared-state action.
- *Closure:* only after the user asks — `gh pr create --draft` to open, `gh pr ready` to promote. **Note:** a feature pipeline typically ends at branch commits + a report and never opens or pushes a PR — PR creation is always a manual step the user initiates after it.

## Flows

**Non-trivial features:**
1. Plan mode → **preparation gate** (above): gather + collect sources of truth (spec, Figma, AC list, before-state baseline for migrations), confirm knowledge sources, assess testability and decompose. Research-first for unknowns. In a project with a feature pipeline, its entry command drives this (requirements → architecture → confirmation gate); the confirmation gate is where you review the plan and complexity before code.
2. Implement on a `feature/*` branch. Do **not** open a PR automatically — offer to open a draft PR and open it only when the user asks (`gh pr create --draft`).
3. **Quality gate** (`/finalize`) → **acceptance gate** (`test-runner`: build + tests against the AC) → open the PR when the user asks → promote PR to ready (user confirmation required) → drive to merge.

**Bug fixes:**
1. Plan mode (debug + fix in the plan). Capture reproduction steps in `swarm-report/<slug>-debug.md` — this is the source of truth for acceptance.
2. Write a failing test that reproduces the bug first, then implement the fix (red-green) → **quality gate** → **acceptance gate** (the regression test + suite pass via `test-runner`) → PR. The regression test is not optional unless the feasibility gate applies — then a tracked exception, never a silent skip (see § Task type routing below bug-fix row + the `v1rus-qa` skill §4).

---

# Task Type Routing

Routing matrix: task type → verification source of truth + testing pyramid target + when to write tests.

## Test feasibility gate

Tests are written when **both** conditions hold:
1. The coverage approach is clear — there is a natural test boundary for the behavior (pure function, API contract).
2. The effort is within reasonable budget relative to the task — writing the test does not cost more than the change itself for simple cases, and does not require building test infrastructure from scratch.

When either condition is not met — document the reason in the plan and proceed without tests for that scope. "Not obvious how to test" and "setup cost is prohibitive" are valid; "didn't feel like it" is not.

This gate governs **discretionary** scope — which pyramid levels, internal/non-public behavior. It does **not** override the public-API floor: a modified **public** symbol still must satisfy the `v1rus-qa` skill §1 (exercised by a test, or annotated trivial). When test cost is genuinely prohibitive on a public symbol, route it to a **tracked exception** (the the `v1rus-qa` skill §4 `@Ignore`-with-issue pattern) — the gap stays explicit and tracked, never a silent documented skip.

### Testability assessment & simplifications (at planning time)

Don't only decide *whether* to test — assess how hard verification will be and lower that cost **before** implementation (this is part of the preparation gate — see § Mandatory gates above):

- Surface hard to drive (deep in a flow, needs a real backend, slow to reach) → build a **sample / sandbox app** or harness that exercises the changed behavior in isolation; prototype and debug there first, then port to the real app. Re-debugging only in the real app is the slow path.
- Lower verification cost by extracting the changed logic to a **unit / integration boundary** (pure function, API contract) rather than driving it through the UI.
- Temporary simplifications that make a verifiable prototype reachable sooner are valid (see the `v1rus-qa` skill § Disposable verification tests) — but remove or harden them before `/finalize`.

The goal is the cheapest path to a *verifiable* prototype, not to defer testing. Decide the simplifications and what to collect (test baselines, sample data) here, at planning — not mid-implementation.

## Routing matrix

| Task type | Source of truth | Min pyramid | Write tests | Special |
|---|---|---|---|---|
| Feature | Spec / test plan / AC list | L1–L2 | After implementation; before if AC are clear (TDD) | — |
| Bug fix | `swarm-report/<slug>-debug.md` — reproduction steps | L1–L2 | **Before fix** — write a failing test first, then fix | Red-green: test proves bug exists, then proves it's gone |
| Tech migration | Before-state baseline | L1–L2 | Before migration — establish test coverage of migrated behavior as part of baseline | Capture before-state first |
| Library version bump | Before-state baseline | L1–L2 | Verify existing tests pass; add where coverage gaps found | Capture before-state if tests absent |
| Refactoring | Before-state baseline (tests as proxy if they exist) | L1–L2 | Before refactor if coverage gaps exist | Behavior must be 1:1 with before-state |
| Infrastructure change (network / storage / auth / DI) | Spec / requirements | L1–L2 | After implementation | — |
| UI / design task | Figma / screenshots | L0–L1 | — | Visual match reviewed **manually** against the mockup |
| Performance optimization | Benchmark baseline — before/after numbers | L0–L2 where measurable | Capture baseline before; measure delta after | Win must be a measurable delta |
| Investigation / research | Research output document | L1 only if code produced | N/A when no code changes | No pyramid when no code is written |

**L0 (Build) is the implicit entry gate for every row** — the affected part (relevant app/module, not always the whole repo) must compile before any L1+ level runs. The "Min pyramid" column lists levels *above* L0; it never repeals it. No code change → no L0 (e.g. research). **Whether tests are written at all is set by the complexity band: only from complexity 7** (see the `v1rus-qa` skill §0). Below 7 the row's L2 / "Write tests" cell is dormant — verification is build + static analysis + the quality gate. The "Write tests" column describes the *timing* (TDD / red-green / baseline-first) for when the band does call for tests.

## Before-state baseline

A durable snapshot of the system's current behavior, created **before any changes**, detailed enough to verify the modified system behaves identically.

### What qualifies

1. **Passing tests cover the behavior being changed** → the test suite IS the baseline. No additional capture needed — green before = spec for after.
2. **No test coverage** → capture a baseline before starting:
   - API / backend: response shape snapshots for affected endpoints, saved to `swarm-report/<slug>-baseline.md`.
   - Pure logic: input → output pairs for the behavior being changed.
   - When capturing a direct baseline isn't practical, prefer the test-coverage shortcut below (write tests first).

**Shortcut:** establishing test coverage of the migrated behavior before the migration satisfies both the baseline requirement and the `/write-tests` step in one move.

**Sufficiency check:** "Could I hand this baseline to someone who has never seen this system and have them verify the migration succeeded?" If yes — the baseline is sufficient.

### What is not a baseline

- "It should be fine" — not a baseline.
- Code review or static analysis of the change — these check intent, not actual behavior.
- A passing build — proves compilation, not behavior.
