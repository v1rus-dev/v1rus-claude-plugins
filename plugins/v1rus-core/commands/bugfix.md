---
description: Fix a bug end-to-end with red-green discipline via the multi-agent pipeline
argument-hint: [bug description | JIRA-KEY | Jira issue URL]
---

You are the **orchestrator** of the bug-fix pipeline, running in the main session. You can use
`AskUserQuestion` and the `Agent` tool; your subagents cannot. The user wants a bug fixed with a
**red-green** workflow: reproduce → failing regression test → fix → verify green. Input (may be
empty): **$ARGUMENTS**

**Language:** Detect the user's language from `$ARGUMENTS` and their answers. Default to **Russian**
if unclear. All communication with the user — `AskUserQuestion` content and phase-transition
messages — must be in the detected language.

All task paths below are under `.claude/tasks/<slug>/`.

## Phase 0 — Environment probe (always first)

Re-detect capabilities every run:
1. Read `.mcp.json` and `.claude/settings.json` (`enabledPlugins`).
2. Check available tools / `ToolSearch` for: **Atlassian** (`mcp__atlassian__*`), **Figma**
   (`mcp__*figma*`), **mobile-mcp** (`mcp__mobile-mcp__*`).
3. Note enabled plugins. Record results into `STATE.md` in the next phase.
4. Build role→agent bindings from the available-agent inventory per `${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/references/agent-resolution.md` and
   record them in `STATE.md`'s "Agent bindings" section.
5. **Detect the stack and resolve its pipeline profile** per
   `${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/references/stack-profile.md` (repo markers →
   the matching `*-pipeline-profile` skill), and record `Stack:` + `Pipeline profile:` in `STATE.md`.
   Every spine agent you spawn (`test-writer`, `feature-developer`, `feature-finalizer`) gets both in
   its prompt with the instruction to invoke the profile skill first. No matching profile → record
   `none — <reason>` and tell the agents to derive conventions from the project's `CLAUDE.md`.

## Phase 1 — Task setup

1. If `$ARGUMENTS` is a Jira key (`^[A-Z][A-Z0-9_]+-[0-9]+$`) or Jira URL, run the **two-step Jira
   access gate** before fetching: (a) if the Atlassian MCP is absent, tell the user and continue
   with the text as the description; (b) if present, verify access to *this* issue with a single
   minimal `mcp__atlassian__jira_get_issue` call (summary field only) — on an auth error run the
   MCP's `authenticate` → `complete_authentication` flow and retry once; on permission/not-found,
   report it and ask the user (different key / manual mode / abort). Only after access is confirmed
   spawn `jira-fetcher` to pull the report into `requirements-raw.md`. For non-Jira input, treat it
   as a free-text bug description.
2. Derive a short kebab-case `<slug>` (e.g. `crash-on-empty-cart` or `mms-123`).
3. If `.claude/tasks/<slug>/STATE.md` exists, this is a **resume**: read it, report the current
   phase, and continue from the first unchecked checklist item. Stop the fresh-start steps.
4. Otherwise create `.claude/tasks/<slug>/` and write `STATE.md` (template below) with the
   Phase 0 probe results, `Mode: bug`, and the branch.
5. Branch: if the current branch is not a `feature/*` or `fix/*` branch, create `fix/<slug>`
   (`git checkout -b fix/<slug>`) and record it in `STATE.md`.

### STATE.md template

```
# Bug-fix State — <slug>

- Bug: <short title>
- Mode: bug
- Branch: fix/<slug>
- Current phase: <phase>
- Complexity: TBD

## Environment (Phase 0 probe)
- Atlassian: yes|no
- Figma: yes|no
- mobile-mcp: yes|no
- Enabled plugins: <list>
- Stack: kmp | flutter | <other> | unknown
- Pipeline profile: <plugin>:<skill> | none — <reason>

## Agent bindings (per ${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/references/agent-resolution.md)
(role → bound agent | baseline-inline — reason; filled during Phase 0 and updated as RECOMMENDED-ROLE lines resolve)

## Checklist
- [ ] debug              (root cause + reproduction in debug.md)
- [ ] confirmation-gate
- [ ] regression-test-red (failing test reproduces the bug)
- [ ] fix-green           (fix makes the test pass, suite stays green)
- [ ] finalize
- [ ] code-review
- [ ] expert-reviews      (mark "skipped — no escalations" when not needed)
- [ ] report

## Test loop log
## Notes
```

After every phase: tick the checkpoint in `STATE.md` and append `<!-- CHECKPOINT: <phase> DONE @
<ISO-date> -->` to the phase artifact — **disk only, this is what resume reads**. Subagents never
commit; the orchestrator owns commits. **Commit only at three milestones** (mirrors
`feature-pipeline`): `[<slug>] debug: <summary>` → `[<slug>] fix: <summary>` →
`[<slug>] docs: bug-fix report`. Never `--no-verify`, never push.

## Phase 2 — Reproduce & locate root cause (you, in the main session)

Establish the **source of truth** for acceptance — the reproduction. Use `ast-index` and, for
broad multi-file searches, the `Explore` agent to find the offending code; do not edit product
code in the main session. Ask the user (`AskUserQuestion`, one question at a time) only for what
you cannot determine yourself: exact steps to trigger, observed vs. expected behavior, environment.

Write `.claude/tasks/<slug>/debug.md`:
- **Reproduction steps** — precise, ordered, deterministic.
- **Observed vs. expected** behavior.
- **Root cause** — the specific code path, with `file:line` references, and *why* it misbehaves.
- **Affected module(s)** and the **proposed fix** (one paragraph).
- **Regression test target** — where the test belongs (the test location the stack profile prescribes
  for the owning module), the project's own command that runs it, and the concrete assertion that would
  fail today and pass after the fix.

**Analyst gap-check (before committing).** Spawn the **`business-analyst`** subagent (via the
`Agent` tool) with `debug.md`. Tell it to ground itself in the code via `ast-index` and return:
whether the *expected* behavior is fully and unambiguously specified, related edge cases / scenarios
the regression test should also cover, scope concerns (is the proposed fix too narrow or too broad),
and the acceptance criteria for "fixed". It is read-only. Fold its points back into `debug.md`
(tighten expected behavior / acceptance / test scope) and raise any blocking question with the user
via `AskUserQuestion`. If `business-analyst` is unavailable, do this analysis yourself — never skip it.

End with the checkpoint footer. Tick `debug`. Commit `[<slug>] debug: root cause + repro`.

## Phase 3 — Confirmation gate (mandatory pause)

Show the user a short summary of `debug.md` (root cause + proposed fix) and assign a complexity
score (1–10; same scale the architect uses, per the `v1rus-qa` skill bands). Use `AskUserQuestion`:
- **Approve** → record `Complexity: N`, proceed.
- **Revise** → adjust `debug.md` (deeper investigation or a different fix approach), return here.

**Regression-test feasibility:** if a no-device unit/integration test can reproduce the bug
(almost always true for logic/data/domain bugs), the failing test is **mandatory** — go to Phase 4.
Only if the bug is genuinely unreachable without a device/emulator (out of scope), record a
**tracked exception** in STATE Notes (with a tracking issue reference), skip Phases 4 and the red
step, and go straight to Phase 5 — never silently skip the test. Tick `confirmation-gate`.

## Phase 4 — Red: failing regression test — `test-writer`

Spawn `test-writer` (with the stack + profile). Tell it: the `<slug>`, the absolute path to `debug.md`,
and that it must write a **single regression test** asserting the *correct* (expected) behavior in the
location named in `debug.md`, using the framework, doubles and naming its stack profile prescribes —
this test is expected to **fail** against the current code.

Then spawn `test-runner` with the exact test scope from `debug.md` (plus the module's regular test
tasks if relevant — `test-runner` discovers them from the project). **Confirm the new test FAILS**
(this proves it reproduces the bug). If it unexpectedly passes, the test does not capture the bug —
send `test-writer` back with the gap. Once red is confirmed, tick `regression-test-red` on disk
(**no commit** — the regression test lands together with the fix in the `fix` milestone, so the
test+fix arrive green in one commit and history never contains a deliberately-red commit).

## Phase 5 — Green: fix — `feature-developer` ⇄ `test-runner` (UNLIMITED until green)

Spawn `feature-developer` in **fix mode** (with the stack + profile). Inputs: `debug.md` (root cause +
proposed fix) and the failing test from Phase 4. Instruct it to fix **only** the root cause — minimal diff, no unrelated
refactors (per CLAUDE.md). Then loop with **no iteration cap**:
1. Spawn `test-runner` (the bug's test task + standard suite). It writes `test-results-<n>.md` and
   returns PASS or FAIL+details. `feature-developer` does **not** commit.
2. **PASS** → tick `fix-green` on disk, exit loop (the commit happens at the `fix` milestone in
   Phase 6).
3. **FAIL** → append the iteration to STATE's "Test loop log", re-spawn `feature-developer` with the
   exact failing tests + error output (fix only those), increment `<n>`, repeat. Iterations are
   **not** committed individually.

**Only escape without green:** if `feature-developer` reports it needs a user decision (ambiguous
expected behavior, contradictory acceptance), stop and ask via `AskUserQuestion`; record the
escalation in STATE Notes. Do not spin on an unchanged, unfixable failure.

## Phase 6 — Finalize — `feature-finalizer`

Spawn `feature-finalizer` (with the stack + profile; it does not commit) to clean leftover
scaffolding/dead code and enforce CLAUDE.md style plus the profile's finalizer checklist, then re-run
the test loop (Phase 5) once to confirm cleanup kept everything green;
loop again if needed. Tick `finalize`.

#### → Milestone 2 — `fix` commit
All fix work is complete and green in the working tree. Make the **single fix commit**: stage the
production code change **and** the regression test, then commit `[<slug>] fix: <bug summary>`. The
code-review and expert-review fixes that follow are **amended** into this commit
(`git commit --amend --no-edit`), never committed separately.

## Phase 7 — Code review — `code-reviewer` (Sonnet)

Spawn `code-reviewer`. Inputs: bug/fix description from `debug.md`, the plan path
`.claude/tasks/<slug>/debug.md`, and the git diff (`git diff <base>...HEAD` as inline text).
Write its full output to `.claude/tasks/<slug>/code-review.md` (append `## Iteration <n>` on
re-reviews — keep history). `code-review.md` is committed later as part of the report milestone.
- **PASS** → tick `code-review` on disk, go to Phase 8.
- **WARN / FAIL** → spawn `feature-developer` with the findings (no commit), re-run
  `feature-finalizer`, **amend the fixes into the `fix` milestone commit**, re-run code review.
  Loop until PASS. **Only stop and ask the user** if `feature-developer` reports it cannot fix a
  finding without a user decision.

## Phase 8 — Expert reviews (automatic escalation)

Read the **Escalation** section of `code-review.md`. If empty → write `expert-reviews.md` recording
"no escalations", tick `expert-reviews` as skipped, commit, proceed. Otherwise spawn the
recommended specialists **in parallel** (`security-expert` / `performance-expert` /
`architecture-expert` / `ux-expert` / `build-engineer`), passing the changed files + reviewer
findings. Write a combined `expert-reviews.md`. If any reports **critical** findings: fix
(`feature-developer`, no commit) → `feature-finalizer` → **amend into the `fix` milestone commit**
→ re-run Phases 7–8. Tick `expert-reviews` on disk when all specialists are clean (no commit —
`expert-reviews.md` is committed in the report milestone).

## Phase 9 — Report — `feature-reporter` → Milestone 3 — `docs: report` commit

Spawn `feature-reporter` (it does not commit). Inputs: all task artifacts (`debug.md`,
`code-review.md`, `expert-reviews.md` when present) + `git log` for the branch. Output: `REPORT.md`
(what the bug was, the root cause, the fix, the regression test, verification notes).

This is the **third and final milestone commit**. Tick `report` in `STATE.md`, then stage all
documentation/process artifacts in one go — `REPORT.md`, `STATE.md`, `debug.md`, `code-review.md`,
`expert-reviews.md`, and any `.claude/` agent memory (`git add .claude/`) — and commit
`[<slug>] docs: bug-fix report`. No separate housekeeping commit. Announce completion with the path
to `REPORT.md`.

## Resume behavior

If `STATE.md` exists with some checkpoints ticked: report the current phase and continue from the
first unchecked item. Reuse artifacts on disk. If resuming mid-test-loop, continue from the last
`test-results-<n>.md`.
