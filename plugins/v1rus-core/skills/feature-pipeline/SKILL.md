---
name: feature-pipeline
description: Shared orchestration for the multi-agent feature factory. Invoked by the /feature command (manual or Jira-sourced requirements) AFTER requirements.md exists for a task. Sequences the architect → designer? → [confirmation gate + complexity scoring] → test-planner? → developer ⇄ test-runner? → finalizer → code-reviewer ⇄ expert-reviews → reporter phases. Stack-agnostic — the technology vocabulary reaches each spine agent through the stack profile resolved in Phase 0 (KMP/Compose, Flutter, …). Test phases run only at complexity ≥7 (per the the v1rus-qa skill bands); skipped at 1–6. Drives each phase as a subagent, records checkpoints in STATE.md (disk), and commits at three milestones only (plan / feat / docs-report). Runs in one of two modes — `standard` (the full sequence, unchanged and the default) and `lite` (a smaller, faster subset for small well-understood work) — crossed with an orthogonal question profile, `normal` (asks what blocks the acceptance criteria) or `quiet` (decides those itself and logs assumptions instead). Also handles resume.
---

# Feature Pipeline Orchestrator

> **Portability.** This is the corporate pipeline: the phase sequence, gates, commit discipline and
> STATE.md contract are the standard. Everything project-shaped — module paths, build and test task
> names, the real names of the state-holder/navigator/theme types — is read from the target project's
> `CLAUDE.md` at run time, never assumed. Everything **stack**-shaped — layer vocabulary, plan
> sections, convention skills, test location and framework — comes from the **stack profile** the
> technology layer ships (`references/stack-profile.md`), not from the agents. Role→agent binding
> follows `references/agent-resolution.md`: the pipeline agents shipped here are the floor, and the
> stack layers (`v1rus-kotlin`, `v1rus-compose`, `v1rus-kmp`, `v1rus-android`, `v1rus-flutter`) provide the escalation targets —
> `kotlin-engineer`, `compose-developer`, `swift-engineer`, `flutter-engineer`,
> `flutter-ui-developer`, `build-engineer`, `performance-expert`, `test-runner`. With none of them
> installed the pipeline still completes end to end.


You are the **orchestrator** running in the main session. You can use `AskUserQuestion`
and the `Agent` tool — your subagents cannot. You drive a feature from a finished
`requirements.md` all the way to a final commit by delegating each phase to a dedicated
subagent and managing the flow between them.

This skill assumes the entry command (`/feature` or `/feature-jira`) has already:
1. Run the **environment probe** (Phase 0) and written its result into `STATE.md`.
2. Produced `.claude/tasks/<slug>/requirements.md` and committed it.
3. Recorded the `<slug>`, mode, and working branch in `STATE.md`.

`<slug>` is the task folder under `.claude/tasks/`. All paths below are relative to
`.claude/tasks/<slug>/`.

## Operating rules

- **Read `STATE.md` first.** It is the single source of truth for progress. Resume from the
  first unchecked checklist item — never redo a phase whose checkpoint is already marked done.
- **One phase at a time, in order.** Each phase = spawn the named subagent (foreground, so it
  writes to the shared working tree), wait for its result, then update state on disk.
- **Subagents start blind.** They do NOT see this conversation. In each `Agent` prompt include:
  the `<slug>`, absolute task-folder path, exactly which artifact files to read, what file to
  write, the relevant project conventions pointer (CLAUDE.md), and — for every spine agent — the
  **stack + stack-profile skill** recorded in `STATE.md` (see *Stack profile* below). Be explicit.
  **Tell every subagent NOT to commit** — they leave their work in the working tree; the orchestrator
  owns all commits.
- **After every phase:** tick the checkpoint in `STATE.md` and append a checkpoint footer to the
  phase artifact (`<!-- CHECKPOINT: <phase> DONE @ <ISO-date> -->`). This is **disk-only** — it is
  what resume reads, and needs no commit. **Commit only at the three milestones** defined in
  *Commit & branch discipline* below. Never use `--no-verify`. Never push.
- **Communicate phase transitions** to the user in one short line each (e.g.
  "Phase: architecture — delegating to feature-architect (Opus)").
- **Agents & skills resolve per `${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/references/agent-resolution.md`.** Role→agent bindings are built during
  the Phase 0 environment probe from the available-agent inventory and recorded in `STATE.md` (the
  "Agent bindings" section). The pipeline-specific agents (`feature-*`, `test-*`, `jira-fetcher`) are
  the project floor; the specialist reviewers (`security-expert`, `performance-expert`,
  `architecture-expert`, `ux-expert`, `build-engineer`, `code-reviewer`) are examples of typical
  escalation targets, provided globally. Resolve each role to its discovered escalation or its
  project baseline/inline closure per the rule — never block on a missing global agent.
- **Stop only** for: analyst questions (already done by the command), the Figma gate, the
  pre-development confirmation gate, or a hard blocker a subagent escalates. Otherwise keep going.
- **Language.** Read the user's language from `requirements.md` (the language the user used to
  describe the feature). Default to **Russian** if unclear. All orchestrator-to-user communication
  — phase-transition lines, `AskUserQuestion` text — must be in that language. When spawning each
  subagent, append to the prompt: `Return your final summary in Russian` (or the detected language).
- **Resolve `RECOMMENDED-ROLE:` lines.** Whenever a subagent returns `RECOMMENDED-ROLE:` lines in
  its result, resolve each against `${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/references/agent-resolution.md` (escalate to a discovered
  clearly-better-fit agent, else close with the project baseline/inline) and record the
  binding + reason in `STATE.md`.

## Pipeline modes — `standard` and `lite`

The pipeline runs in one of two modes, resolved by the entry command and recorded in `STATE.md` as
`Mode profile:`. **`standard` is the default and is unchanged** — an invocation without an explicit
lite flag behaves exactly as it always has.

`lite` exists for work whose cost is dominated by the pipeline rather than by the change: a small,
well-understood feature the developer could describe in two sentences. It cuts the planning head and
the review tail — never the verification floor, and never the clarifying questions. **Asking the
user is not a gate lite is allowed to skip:** the bar for what deserves a question is the same in
both modes, and a lite run that cannot state its acceptance criteria asks until it can.

Modes apply to the **feature** pipeline only. `/bugfix` has no lite mode: its red-green discipline —
reproduce, failing regression test, fix, verify green — is the whole point of that pipeline, and
there is nothing in it worth cutting.

### Phase deltas

This table is the **single source** for what a mode changes. The phase bodies further down describe
`standard`; in `lite`, apply the deltas from here.

| Phase | `standard` | `lite` |
|---|---|---|
| Requirements (entry command) | interactive analyst one question at a time, then a `business-analyst` gap-check | requirements written straight from the description; no `business-analyst` gap-check. **The question bar is identical** — lite cuts the gap-check agent, never clarification; see the entry command's *Question economy* block |
| 1. Architecture | `feature-architect` on Opus, full plan across every layer | same agent on **Sonnet**, plan capped at roughly one page: only the layers the feature actually touches, plus the complexity score |
| 2. Design | Figma gate — ask when a Figma MCP is present but no link is in the requirements | runs only when a Figma link is **already** in `requirements.md`; never ask |
| 3. Confirmation gate | mandatory pause | **auto-approved and logged**, unless a risk trigger fires (below) |
| 4. Test plan | complexity >=7 | unchanged — the complexity bands are not a mode setting |
| 5. Development | `feature-developer` or an escalated engineer | unchanged, except the profile's finalizer checklist goes into its prompt: it self-cleans, because Phase 8 will not run |
| 6-7. Tests + test loop | complexity >=7, loop until green | unchanged wherever they run — a lite run that reaches the loop still runs it until green |
| 8. Finalize | `feature-finalizer` pass over the whole feature surface | **skipped** — folded into the developer's prompt |
| 8.5 Code review | `code-reviewer` <-> `feature-developer` until PASS | **one** review plus **one** fix round; still not PASS -> stop and hand the remaining findings to the user |
| 8.6 Expert reviews | dispatch every specialist the escalation section names | **skipped**, except the mandatory `security-expert` when the diff touches the security surface (below) |
| 9. Report | `feature-reporter` | the orchestrator writes a short `REPORT.md` itself: what changed, the file list, how it was verified, the assumptions it logged |
| Commits | three milestones — `plan` / `feat` / `docs: report` | **one** commit at the end: `[<slug>] feat: <feature>`, staging production code, tests, the task artifacts and `STATE.md` together |

### What `lite` never cuts

These hold in both modes. A lite run that cannot satisfy one of them stops and asks — it does not
lower the bar:

1. **L0 — it compiles.** Even when the complexity band skips tests, the build still runs. Place it
   between Phase 5 (development) and Phase 8.5 (code review): spawn `test-runner` in **build-only**
   mode, or run the compile-check the stack profile prescribes when no `test-runner` is bound.
   Record the outcome in STATE's *Test loop log* as `build-only @ <ISO-date> — PASS|FAIL`; on FAIL,
   send the errors back to `feature-developer` and re-run, exactly like the test loop. An unverified
   diff is not a faster diff.
2. **The complexity bands.** `lite` neither lowers the score nor skips tests the band requires.
   **If the architect scores >=7 in a lite run, stop at the confirmation gate** and ask the user:
   switch to `standard`, or explicitly accept a documented no-test risk. Record the answer in STATE
   Notes. Lite is not a route around the `v1rus-qa` bands.
3. **Security surface.** After code review, look at the changed-file list yourself. If the diff
   touches auth, tokens, crypto, permissions, payments, or a data migration, dispatch
   `security-expert` and act on its critical findings — in both modes, whatever the reviewer's
   escalation section says. This is the one expert review lite does not skip.
4. **The non-negotiables.** Branch discipline, no `--no-verify`, no push, no PR on the pipeline's
   initiative, subagents never commit, the orchestrator owns every commit.

### Risk triggers — when an auto-approved confirmation gate still pauses

Auto-approval is the default in `lite`, and in `quiet` whatever the mode. Pause and use
`AskUserQuestion` when the architecture plan involves any of:

- complexity >=7 (see above);
- auth / tokens / crypto / permissions, payments, or a migration that can lose data;
- a change to a public API, a DB schema, or a CLI contract;
- a new or bumped dependency — it must clear the `v1rus-dependencies` plan-stage gate first;
- requirements that contradict each other, the project's `CLAUDE.md`, or an earlier user instruction;
- a plan substantially larger than the description implied — scope creep the user has not seen yet.

Auto-approval is logged, never silent. Write into `STATE.md`:
`Confirmation: auto-approved (<lite|quiet|lite+quiet>, complexity N) — <one line on why it is safe>`.

### Question profile — `normal` and `quiet`

A second axis, **orthogonal to the mode**, resolved by the entry command from `--quiet`
(synonym `--no-questions`) and recorded in `STATE.md` as `Question profile:`. The mode decides how
many gates and agents run; the profile decides whether the user is interrupted. All four
combinations are valid, and `lite + quiet` is the "small task, don't bother me" profile.

`normal` is the default: the requirements phase asks what blocks the acceptance criteria, and the
`standard` confirmation gate pauses.

In `quiet` the pipeline closes those questions itself:

| | `normal` | `quiet` |
|---|---|---|
| Requirements questions | asked, one at a time | answered by the orchestrator from code / ticket / project patterns, each logged as `ASSUMPTION:` |
| `business-analyst` gap-check (`standard`) | runs; its open questions go to the user | **still runs**; its open questions are resolved by the orchestrator and logged |
| Figma gate (`standard`) | ask when a Figma MCP is present but no link is in the requirements | do not ask — proceed without a design spec and log the assumption |
| Confirmation gate (`standard`) | mandatory pause | **auto-approved and logged**, exactly like `lite`, unless a risk trigger fires |
| Risk triggers | pause | **pause** — unchanged |

`quiet` suppresses *clarification*, never a **hard blocker**. These stop and ask in both profiles:
a self-contradicting task; a *policy* choice on the security / money / data-loss surface; missing
access or credentials; a polyglot repo whose target surface you cannot infer; any risk trigger
below. `quiet` is not a licence to guess on the escalation bar — it is a licence to stop asking
what you can answer.

Silence is paid for with the ledger. Every decision that would have been a question is written as
`ASSUMPTION: <choice> — <why> — <how to reverse it>` into `requirements.md` and rolled up into
`REPORT.md`, which **leads with** the assumption list. A `quiet` run that recorded no assumptions
did not do the work — it guessed and left no trace.

### Mode in `STATE.md`, resume, and switching mid-run

- The entry command writes `Mode profile: standard | lite` and `Question profile: normal | quiet`
  into `STATE.md` next to `Mode:`. The two are independent — a resume or a mid-run switch changes
  one without touching the other.
- Phases a mode skips are ticked `skipped — lite`, exactly like the complexity skips, so the
  checklist still reads as a complete record of what ran.
- **Resume keeps the recorded mode.** A resumed task continues in the mode written in `STATE.md`; an
  explicit flag on the resuming invocation overrides it — record the change and its reason in STATE
  Notes.
- **Upgrading mid-run (lite -> standard) is allowed and cheap:** the phases standard adds
  (`feature-finalizer`, the full review loop, expert reviews, `feature-reporter`) simply run over
  work that already exists. Downgrading is not — once a standard run has made its `plan` milestone
  commit it stays standard.

## Stack profile

The spine agents (`feature-architect`, `feature-designer`, `feature-developer`, `test-planner`,
`test-writer`, `feature-finalizer`) carry no technology knowledge. The stack layer supplies it as a
profile skill (`v1rus-kmp:kmp-pipeline-profile`, `v1rus-android:android-pipeline-profile`, `v1rus-flutter:flutter-pipeline-profile`, …),
detected during the Phase 0 probe and recorded in `STATE.md` as `Stack:` + `Pipeline profile:`.

In every spine-agent prompt, name both and tell the agent to invoke the profile skill **first**:

> Stack: `<stack>`. Before anything else, invoke the skill `<plugin>:<profile>` (Skill tool) — it is
> the stack vocabulary for this project. Then read the project's `CLAUDE.md` for the concrete names.

If no profile resolved, say so explicitly (`no stack profile available — derive conventions from the
project's CLAUDE.md and existing layout, and state that in your artifact`) rather than leaving the
agent to guess. Reviewers, experts and `feature-reporter` do not need the profile. Full contract,
including detection markers and what a profile must contain:
`${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/references/stack-profile.md`.

## STATE.md format

The command creates this; you maintain the checklist and logs:

```
# Feature Pipeline State — <slug>

- Feature: <short title>
- Mode: manual | jira
- Mode profile: standard | lite
- Question profile: normal | quiet
- Branch: feature/<slug>
- Current phase: <phase>
- Complexity: TBD

## Environment (Phase 0 probe)
- Atlassian (Jira/Confluence): yes|no
- Figma: yes|no
- mobile-mcp: yes|no
- Enabled plugins: <list>
- Stack: kmp | flutter | <other> | unknown
- Pipeline profile: <plugin>:<skill> | none — <reason>

## Agent bindings (per ${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/references/agent-resolution.md)
(role → bound agent | baseline-inline — reason; filled during Phase 0 and updated as RECOMMENDED-ROLE lines resolve)

## Checklist
- [x] requirements
- [ ] architecture
- [ ] design            (mark "skipped — no Figma" when not applicable)
- [ ] confirmation-gate
- [ ] test-plan         (mark "skipped — complexity <N>" when complexity ≤ 6)
- [ ] development
- [ ] tests-written     (mark "skipped — complexity <N>" when complexity ≤ 6)
- [ ] tests-green       (mark "skipped — complexity <N>" when complexity ≤ 6)
- [ ] finalize          (mark "skipped — lite" in lite mode)
- [ ] code-review
- [ ] expert-reviews    (mark "skipped — no escalations" when not needed, "skipped — lite" in lite mode)
- [ ] report

## Test loop log
(iteration entries appended by the test loop)

## Notes
(blockers, decisions, escalations)
```

## Phase sequence

The bodies below describe **`standard`**. In **`lite`**, run the same sequence with the deltas
from the *Pipeline modes* table above — that table, not these bodies, is the single source for
what a mode changes.

### 1. Architecture — `feature-architect` (Opus)
Spawn `feature-architect`. Inputs: `requirements.md` (+ `design-spec.md` if it already exists), plus
the stack + profile skill from `STATE.md`. Output: `architecture-plan.md`. The agent loads the stack
profile, audits the codebase with `ast-index`, and produces a full implementation plan aligned with
CLAUDE.md — layer layout, the stack's presentation pattern, data-layer rules, DI and navigation, in
that stack's own vocabulary. Then: checkpoint on disk (no commit yet — folds into the **plan**
milestone).

### 2. Design (optional) — `feature-designer`
Decide whether to run it:
- If the probe shows **Figma: no** → skip. Mark checklist `design — skipped (no Figma MCP)`.
- If **Figma: yes** but no Figma link is in `requirements.md` → **Figma gate**: ask the user
  (`AskUserQuestion`) whether they have a Figma link. If yes, capture it; if no, skip.
- If a Figma link is available → spawn `feature-designer` (with the stack + profile). Output:
  `design-spec.md` (mapping to the project's design system). Checkpoint on disk (folds into the
  **plan** milestone).

If `design-spec.md` is produced after architecture, pass it to the developer in Phase 5.

### 3. Confirmation gate (mandatory pause)
Planning artifacts now exist (`requirements`, `architecture-plan`, optional `design-spec`).
Read `architecture-plan.md` section 9 to extract the architect's complexity score (1–10, per the
the `v1rus-qa` skill bands: 1–6 build-only, 7–8 tested, 9–10 critical).

Use `AskUserQuestion` to let the user review and choose:
- **Approve** (accept complexity N) → record `Complexity: N` in STATE.md and proceed.
- **Approve with complexity override** → user picks a different level; record it.
- **Revise architecture** → re-spawn `feature-architect` with the user's notes, then return to
  this gate.
- **Revise requirements** → capture the delta into `requirements.md`, re-run architecture,
  return to gate.

After approval: record confirmed `Complexity: N` in STATE.md. If complexity ≤ 6, immediately
mark test-plan / tests-written / tests-green as "skipped — complexity N" in the checklist.
Tick `confirmation-gate` (disk-only — no commit yet).

### 4. Test plan — `test-planner` (complexity ≥7 only)
**If complexity ≥ 7:**
Spawn `test-planner`. Inputs: `requirements.md`, `architecture-plan.md`, and the stack + profile.
Output: `test-plan.md` (what/where to test — the test locations the profile prescribes for the modules
under change, cases, edge cases, fakes needed). Checkpoint on disk.

**If complexity ≤ 6:**
Phase already marked skipped.

#### → Milestone 1 — `plan` commit (both complexity branches)
All planning artifacts now exist on disk. Make the **single planning commit** before development:
stage `requirements.md`, `architecture-plan.md`, `design-spec.md` (if any), `test-plan.md` (if any),
and `STATE.md`, then commit `[<slug>] plan: <feature>`. This is the only commit for the whole
planning stage.

### 5. Development — `feature-developer`
Spawn `feature-developer`. Inputs: `architecture-plan.md` (+ `design-spec.md` if present),
`requirements.md`, and the stack + profile. It implements the feature following CLAUDE.md and the
convention skills the profile maps to what it touches. **It does not commit** — it leaves all changes
in the working tree. When it finishes, checkpoint `development` on disk (no commit — folds into the
**feat** milestone in Phase 8).

### 6. Tests written — `test-writer` (complexity ≥7 only)
**If complexity ≥ 7:**
Spawn `test-writer`. Inputs: `test-plan.md` + the implemented code + the stack and profile. Output:
test files in the locations, framework and naming the profile prescribes, reusing the project's
existing fakes. **It does not commit.** Checkpoint on disk (folds into the **feat** milestone).

**If complexity ≤ 6:**
Skip — already marked in checklist. Proceed to finalize.

### 7. Test loop — `test-runner` ⇄ `feature-developer` (complexity ≥7 only, UNLIMITED until green)
**If complexity ≤ 6:** Skip — mark tests-green as "skipped — complexity N". Proceed to finalize.

**If complexity ≥ 7:**
Loop with **no iteration cap** — the pipeline cannot finish until the build and all tests pass:
1. Spawn `test-runner`. It discovers the project's build and test tasks, runs them, writes
   `test-results-<n>.md`, and returns PASS or FAIL+details.
2. If **PASS** → tick `tests-green` on disk (no commit — folds into the **feat** milestone), exit loop.
3. If **FAIL** → append the iteration to STATE's "Test loop log", then spawn `feature-developer`
   again with the exact failing tests + error output and instruction to fix only those (no commit).
   Increment `<n>`, repeat. Iterations are **not** committed individually.

**Only escape from the loop without green:** if `feature-developer` reports it cannot fix a
failure because it needs a user decision (ambiguous requirement, missing spec, contradictory
acceptance criteria), stop the loop and ask the user via `AskUserQuestion`. Record the
escalation in STATE Notes. Do not spin the loop on an unchanged, unfixable failure.

### 8. Finalize — `feature-finalizer`
Spawn `feature-finalizer` (with the stack + profile). It refactors/cleans leftover scaffolding, dead
code, stray comments, and inconsistencies left by earlier agents; enforces CLAUDE.md style and the
profile's finalizer checklist; then runs `ast-index update`.
**It does not commit.** **If complexity ≥ 7:** re-run the test loop (Phase 7) once to confirm
cleanup didn't break tests; loop again if needed. If complexity ≤ 6: skip the post-finalize test
re-run.

**Finalizer cadence (don't over-run it).** This main post-development pass is where the heavy
cleanup belongs — it has the whole new feature surface to tidy. The later review/expert fix rounds
(Phases 8.5–8.6) re-run the finalizer **only when that fix round was a *large* change** (new
components/structure, many files, or a broad refactor). For a **small/targeted fix** (a handful of
lines, a few findings, annotation/string/const swaps, a single-file change) **skip the finalizer** —
those deltas don't accumulate scaffolding, and the code-review re-pass already catches any leftover
cleanliness issue. Running the full finalizer after every minor fix is wasted cycles.

#### → Milestone 2 — `feat` commit
All implementation work (development + tests + finalize) is now complete and green in the working
tree. Make the **single implementation commit**: stage the production code and test files and
commit `[<slug>] feat: <feature>` (use `fix:` for a bug-shaped change). The code-review and
expert-review fixes that follow are **amended into this commit** — they do not create new commits.

### 8.5. Code Review — `code-reviewer` (Sonnet)
Spawn `code-reviewer`. Inputs:
- Task description from `requirements.md`
- Plan from `architecture-plan.md`
- Git diff: run `git diff main...HEAD` and pass as inline text

**Write the reviewer's full output to `code-review.md`** (verdict + statistics + all findings +
task checks + escalation section) before acting on it. On a re-review after fixes, append a new
`## Iteration <n> @ <ISO-date>` section to the same file — keep the history, don't overwrite.

`code-review.md` itself is committed later as part of the **report** milestone (Phase 9) — it is
not committed here.

**Verdict PASS** → tick `code-review` on disk. Proceed to Phase 8.6.

**Verdict WARN** → automatically spawn `feature-developer` with all major findings (no user
question; it does not commit). After fixes, re-run `feature-finalizer` **only if the fix was large**
(per the finalizer-cadence note in Phase 8; skip it for small/targeted fixes), **amend the fixes into the
`feat` milestone commit** (`git commit --amend --no-edit`), re-run code review. Loop until PASS.
**Only stop and ask the user** if `feature-developer` reports it cannot fix a major finding
without a user decision (ambiguous requirement, missing spec, contradictory criteria) — in that
case surface only that specific question via `AskUserQuestion`, then resume the fix loop.

**Verdict FAIL** → spawn `feature-developer` with the critical issues (it does not commit). After
fixes, re-run `feature-finalizer` **only if the fix was large** (Phase 8 cadence note; skip for small
fixes), **amend into the `feat` milestone commit**, re-run code review. Loop until PASS or WARN.
**Only stop and ask the user** if `feature-developer` reports it cannot fix a critical finding
without a user decision — same rule as WARN.

### 8.6. Expert Reviews (automatic escalation dispatch)
After code review PASS, read the **Escalation** section of `code-review.md`.
If no specialists are recommended → write `expert-reviews.md` recording "no escalations —
skipped", tick `expert-reviews` as "skipped — no escalations" on disk (no commit), and proceed to
Phase 9.

Otherwise, resolve each recommended role to its bound agent per `${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/references/agent-resolution.md` (the
discovered specialist if one clearly fits, otherwise the project baseline/inline closes the role),
then spawn all resolved specialists **in parallel** (single message, multiple Agent calls). The
table below is the canonical role→inputs guidance; the **Agent** column names the typical
escalation target, not a hardcoded requirement:

| Recommendation | Agent | Inputs |
|---|---|---|
| `security-expert` | `security-expert` | changed files + code-reviewer findings |
| `performance-expert` | `performance-expert` | changed files + code-reviewer findings |
| `architecture-expert` | `architecture-expert` | changed files + `architecture-plan.md` |
| `ux-expert` | `ux-expert` | changed Composable files + `requirements.md` |
| `build-engineer` | `build-engineer` | changed Gradle/build files |

**Write a combined `expert-reviews.md`** with one `## <specialist>` section per spawned agent
holding its findings and severities. Collect all specialist results. If any specialist reports
**critical findings**:
1. Spawn `feature-developer` with all critical findings from all specialists combined (no commit).
2. Re-run `feature-finalizer` **only if the combined fix was large** (Phase 8 cadence note; skip for small/targeted fixes).
3. **Amend the fixes into the `feat` milestone commit**, then re-run the full code-review loop
   (Phase 8.5 → 8.6) and append the new specialist results to `expert-reviews.md`.

Tick `expert-reviews` on disk after all specialists PASS (no critical findings remain).
`expert-reviews.md` is committed as part of the **report** milestone (Phase 9).

### 9. Report — `feature-reporter` → Milestone 3 — `docs: report` commit
Spawn `feature-reporter`. Inputs: all task artifacts (including `code-review.md` and
`expert-reviews.md` when present) + `git log` for the branch. Output:
`REPORT.md` (user-visible summary + technical summary + verification notes).

This is the **third and final milestone commit**. Tick `report` in `STATE.md`, then stage the
documentation/process artifacts in one go — `REPORT.md`, `STATE.md`, `code-review.md`,
`expert-reviews.md`, and any agent-memory files under `.claude/` written during the run
(`git add .claude/`) — and commit `[<slug>] docs: feature report`. There is **no** separate
housekeeping commit; this single commit captures all remaining `.claude/` state. Never
`--no-verify`.

Announce completion to the user (in the detected language) with a short summary and the path
to `REPORT.md`.

## Resume behavior

On invocation, if `STATE.md` already exists with some checkpoints ticked: report the current
phase, then continue from the first unchecked item. Planning artifacts on disk are reused as-is.
If resuming mid-test-loop, continue the loop from the last `test-results-<n>.md`.

## Commit & branch discipline

**In `lite` mode this section collapses to a single commit** — see the *Pipeline modes* table.
Everything below describes `standard`.

**Three milestone commits per feature — nothing else.** Phases checkpoint to disk (`STATE.md` +
artifact footers); only these three points produce a commit:

1. **`plan`** (end of Phase 4) — `[<slug>] plan: <feature>`. All planning artifacts together:
   `requirements.md`, `architecture-plan.md`, `design-spec.md`?, `test-plan.md`?, `STATE.md`.
2. **`feat`** (end of Phase 8) — `[<slug>] feat: <feature>`. All production code + tests, green and
   finalized. Code-review and expert-review fixes (Phases 8.5–8.6) are **amended** into this commit
   (`git commit --amend --no-edit`), never committed separately.
3. **`docs: report`** (Phase 9) — `[<slug>] docs: feature report`. `REPORT.md` + all review
   artifacts (`code-review.md`, `expert-reviews.md`) + final `STATE.md` + any `.claude/` agent
   memory. The single closing commit — no separate housekeeping commit.

Rules:
- **Subagents never commit.** They leave work in the working tree; the orchestrator owns every
  commit. Tell each subagent so in its prompt.
- Work on the branch recorded in `STATE.md` (the command sets/creates `feature/<slug>` if the
  current branch is not a `feature/*` branch).
- Never `git push`, never force, never `--no-verify`.
- A complexity ≤6 feature still produces exactly these three commits (the test-plan/test artifacts
  are simply absent from the `plan`/`feat` commits).
