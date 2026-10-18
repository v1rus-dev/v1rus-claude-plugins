# Workflow: gate discipline

Defines what must be true before a task moves forward, independent of any tool. It is not a forced pipeline: pick what the task needs.

**Gates are closed autonomously.** A gate is a quality bar the agent clears, not a checkpoint where it reports. Only outward-facing or irreversible actions involve the owner: push, PR create/promote, merge, deploy, messaging anyone, force push, deleting uncommitted work, and product intent the code cannot contain. Everything else: take the best default, record it as an assumption (`ASSUMPTION: <choice> - <why> - <how to reverse>`), and lead the final report with the list.

**Gates are abstract; closure is per project.** If the project has its own pipeline, its phases close most gates; run it and let it drive. Otherwise close each gate with the building blocks that exist: `finalize`, `check`, `write-tests`, `research`, `multiexpert-review`, the review agents (`code-reviewer`, `security-expert`, `architecture-expert`, `ux-expert`, ...), `test-runner`, `gh`. Never assume a named tool exists: verify against the session's skills and the project. A gate whose ideal tool is absent is still mandatory: use what exists and say which.

## Preparation gate (before any implementation)

Collect, research-first, three outputs, actually gathered, not just named:
- **Sources of truth** (what "done" means): spec/AC, before-state baseline, screenshots/Figma, debug repro. Produce them actively: snapshot the baseline before a migration. What you cannot create and is missing: substitute the best proxy and record what verification degrades without it; ask the owner only when no proxy makes the work verifiable.
- **Knowledge sources** (how to build it): trusted docs and source per tier (see `v1rus-sources`). Memory and project code go stale; on a gap, verify against the official source. Missing understanding means research first (`research` skill), not a question.
- **Testability and decomposition**: assess how hard the change is to verify and simplify up front (sandbox harness, extracting logic to a unit boundary); decompose a task too large for one plan.

Target is zero questions in this phase, ceiling two, batched in one round. A standard or obvious solution: apply it. Skip preparation only for trivial changes. The `write-spec` and `write-plan` skills are the usual vehicles.

## Quality gate: `finalize`

Required after every implementation where code was written, before declaring done. It owns how the code is written: a review, fix, simplify loop that iterates until no findings above Minor remain, or exits ESCALATE for an owner decision. A standalone `code-reviewer` run does not close the gate. Exceptions: pure documentation, config-only changes without logic, single-line mechanical changes.

## Acceptance gate: it works as intended

After the quality gate, before PR promotion. Verifies behavior against the source of truth. Orthogonal to quality: both are mandatory. Closure is automated: the `test-runner` agent runs the build and relevant tests; tests covering the acceptance criteria must pass. For non-UI changes, exercise the changed contract through a test, not by hand. Same exceptions as the quality gate.

## PR promotion gate

Never open a PR (draft or ready) on your own initiative. When work is ready, offer to open a draft and wait. Promoting draft to ready likewise needs explicit confirmation. A feature pipeline typically ends at branch commits and a report.

## Flows

**Non-trivial feature:** preparation gate, implement on a `feature/*` branch, quality gate, acceptance gate, then (on request) PR, ready, merge.

**Bug fix:** capture reproduction steps in `swarm-report/<slug>-debug.md` (source of truth for acceptance); write a failing test first when the testing band calls for tests, then fix (red, green); quality gate; acceptance gate; PR on request. A skipped regression test is a tracked exception, never silent.

**Never** commit or push directly from main/master/develop; never bypass git hooks without an explicit request; force push only with `--force-with-lease`.
