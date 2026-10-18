---
description: Build a feature end-to-end via the multi-agent pipeline — requirements from a description, a Jira ticket (auto-detected), or nothing at all; --lite cuts gates and agents, --quiet cuts the questions
argument-hint: [short feature description | JIRA-KEY | Jira issue URL] [--lite] [--quiet]
---

You are the **orchestrator** of the feature pipeline, running in the main session. You can use
`AskUserQuestion` and the `Agent` tool; your subagents cannot. The user wants to build a feature.
Input (may be empty): **$ARGUMENTS**

**Language:** Detect the user's language from `$ARGUMENTS` and their follow-up answers. Default
to **Russian** if the input is empty or unclear. All communication with the user — including
`AskUserQuestion` content and phase-transition messages — must be in the detected language.

**Mode profile.** Strip a leading or trailing `--lite` (synonym: `--fast`) from `$ARGUMENTS` before
using it for anything else, and set the mode accordingly:

- flag present → `Mode profile: lite`
- otherwise → `Mode profile: standard`

`standard` is the default and behaves exactly as it always has. `lite` runs the same phase sequence
with a reduced set of gates and agents — the deltas, the four things lite never cuts, and the risk
triggers that still pause it live in the *Pipeline modes* section of the `feature-pipeline` skill.
Read that section before running a lite task; do not invent your own reductions. Record the mode in
`STATE.md`, and mention it in your first message to the user in one short clause.

**Question profile.** Strip `--quiet` (synonym: `--no-questions`) from `$ARGUMENTS` the same way, and
set the profile accordingly:

- flag present → `Question profile: quiet`
- otherwise → `Question profile: normal`

This axis is **orthogonal to the mode**: `--lite` buys speed by cutting gates and agents, `--quiet`
buys uninterrupted work by cutting questions, and the four combinations are all valid. `--lite
--quiet` is the "small task, don't bother me" profile; `--quiet` alone is the full pipeline running
without interrupting you. Record it in `STATE.md` next to `Mode profile:` and name it in the same
short clause of your first message. What `quiet` may never silence is fixed — see Phase 2 and the
*Question profile* section of the `feature-pipeline` skill.

Follow these steps. Do NOT skip the environment probe or the requirements step.

## Phase 0 — Environment probe (always first)

Re-detect capabilities every run (so newly added MCP servers/plugins are picked up automatically):

1. Read `.mcp.json` and `.claude/settings.json` (the `enabledPlugins` block).
2. Determine which MCP capabilities you actually have by checking your available tools / using
   `ToolSearch`:
   - **Atlassian** (Jira/Confluence): look for `mcp__atlassian__*` tools.
   - **Figma**: look for any Figma MCP tools (e.g. `mcp__*figma*`).
   - **mobile-mcp**: look for `mcp__mobile-mcp__*` tools.
3. Note enabled plugins (e.g. `code-simplifier`, `compose-expert`, `security-guidance`).
4. Build role→agent bindings from the available-agent inventory per `${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/references/agent-resolution.md` and
   record them in `STATE.md`'s "Agent bindings" section.
5. **Detect the stack and resolve its pipeline profile** per
   `${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/references/stack-profile.md`: read the repo markers
   (`pubspec.yaml` → Flutter, KMP `settings.gradle.kts` → KMP, `Package.swift`/`*.xcodeproj` only →
   iOS-native), then find the matching `*-pipeline-profile` skill in your available-skills inventory.
   Record `Stack:` and `Pipeline profile:` in `STATE.md`. A polyglot repo → ask the user which surface
   this task touches. No matching profile → record `none — <reason>`; the pipeline still runs with the
   documented fallback.

You will record this into `STATE.md` in the next step.

## Phase 1 — Mode detection & task setup

**Detect the requirements source from `$ARGUMENTS`:**
- **Jira mode** if `$ARGUMENTS` is a Jira issue key matching `^[A-Z][A-Z0-9_]+-[0-9]+$`
  (e.g. `MMS-123`) **or** a Jira issue URL (`*.atlassian.net/browse/...` or contains `/browse/`).
- **Manual mode** otherwise (including an empty argument or a free-text description).

**Jira mode — two-step access gate (do this before any task setup or fetch):**

1. **MCP present?** If the Phase 0 probe shows the Atlassian MCP is **not** available at all, stop
   and ask the user (`AskUserQuestion`): proceed in manual mode treating the text as a description,
   or abort. Do not silently continue.
2. **Access to *this* issue?** The MCP being connected does not prove you can read the ticket — the
   session may be unauthenticated, the token expired, or you may lack permission on that
   project/issue. Verify with a **single minimal call** to the specific key before spawning the
   full fetch: load it via `ToolSearch` and call `mcp__atlassian__jira_get_issue` for the issue key
   requesting only a cheap field set (e.g. `summary`). Interpret the result:
   - **Success** → access confirmed; proceed.
   - **Auth error** (401/403 "unauthenticated", or the MCP returns an authenticate prompt) → the
     session isn't authenticated. Run the MCP's authentication flow (`mcp__atlassian__authenticate`
     → `mcp__atlassian__complete_authentication`), tell the user in one line they need to complete
     it, then retry the minimal call **once**.
   - **Permission / not-found** (403 on the resource, or 404) → you reached Jira but cannot see this
     issue (no access, or wrong key). Report which it is and ask the user (`AskUserQuestion`):
     supply a different key, proceed in manual mode with the text you have, or abort. Do **not**
     spawn `jira-fetcher` against an issue you can't read.

   Only after access is confirmed do you continue to task setup and the Jira fetch.

**Empty input.** If nothing is left after stripping the flags, you have no task yet — do not
improvise one, and do not create a slug, a task folder or a branch from a guess. Ask **one**
`AskUserQuestion`: what are we building, with 2–4 concrete options read out of the repo (recent
`TODO`s via `ast-index todo`, an unfinished area, the obvious next step in the current module) plus
free-form input. Only once you have a description do you continue below. In `quiet` this is the one
question that is still asked: an empty prompt is product intent, which no amount of code reading can
supply — `--quiet` licenses you to stop asking what you can answer, not to invent what the user
wants.

Then set up the task:
1. Derive a kebab-case `<slug>`, kept short:
   - Manual mode → from the feature description (e.g. `add-profile-avatar`).
   - Jira mode → from the key (e.g. `mms-123`); the analyst may enrich the title later, but keep
     the task folder name stable on the key.
2. If `.claude/tasks/<slug>/STATE.md` already exists, this is a **resume**: read it, tell
   the user the current phase, and hand off to the `feature-pipeline` skill (Phase 3) to continue.
   The resumed task keeps its recorded `Mode profile` unless this invocation passed an explicit
   flag — an explicit flag overrides it, and you record the change and its reason in STATE Notes.
   Stop here.
3. Otherwise create `.claude/tasks/<slug>/` and write `STATE.md` using the template in the
   `feature-pipeline` skill, filling in the Phase 0 probe results, `Mode: manual` or `Mode: jira`,
   `Mode profile: standard | lite`, `Question profile: normal | quiet`, and the branch.
4. Branch: if the current git branch is not a `feature/*` branch, tell the user you will create
   `feature/<slug>` and do so (`git checkout -b feature/<slug>`). Record the branch in `STATE.md`.

## Phase 2 — Requirements

The goal of both paths is the same artifact: a clean, unambiguous
`.claude/tasks/<slug>/requirements.md` you could hand to an architect with zero open questions.

**Existing interview artifact.** Before asking anything, check for
`swarm-report/interview-<slug>.md` (the `interview` skill's output) and, in Jira mode, for a slug
derived from the key. If one exists, read it and treat its acceptance criteria, assumptions and
out-of-scope notes as already-gathered requirements — re-ask only what it leaves genuinely open.
Asking the user again what the artifact already records is a defect.

**Question economy — both modes, not a lite reduction.** The bar is *what counts as a question*,
not how many you are allowed:

> Ask only what blocks stating the acceptance criteria **and** what neither the code, the ticket,
> nor the project's existing patterns can answer.

Ground yourself first — `ast-index` and the existing screens/modules — then ask. A question the
index already answered is a defect of this phase. Everything with a defensible default is decided
by you and written into `requirements.md` as `ASSUMPTION: <choice> — <why> — <how to reverse it>`;
the user corrects one line while reading the artifact instead of answering one question at a time.
A question you would follow with "as expected" should not have been asked.

Within that bar there is **no cap on the number of questions**, and this phase is the declared
exception to the charter's question budget: keep asking until you can write `requirements.md` with
no open questions. Do not stop early to stay under a budget — an unasked blocking question becomes
a wrong implementation. Always `AskUserQuestion`, **one question at a time**, each answer processed
before the next is formed, recommended option first with a one-line reason.

**In `quiet` you decide instead of asking.** Run the same grounding and — in `standard` — the same
`business-analyst` gap-check, then answer its open questions **yourself** from the code, the ticket
and the project's existing patterns, recording each answer in `requirements.md` as
`ASSUMPTION: <choice> — <why> — <how to reverse it>`. The analyst still runs: `quiet` changes what
happens to its findings, not whether the analysis happens. Put the assumption list at the top of
`requirements.md` — it is the user's review surface, and they correct a line instead of answering a
queue.

`quiet` never silences a **hard blocker**. These stop and ask in both profiles:

- the task contradicts itself, the project's `CLAUDE.md`, or an earlier instruction from the user;
- a *policy* choice on the security / money / data-loss surface — you decide the mechanics, never
  the policy;
- missing access or credentials: Jira unreachable, no permission on the issue, a service you cannot
  reach (the Phase 1 Jira access gate stands in both profiles);
- a polyglot repo where you cannot tell which surface the task touches;
- any risk trigger at the confirmation gate — the list lives in the `feature-pipeline` skill.

Everything else is decided, logged, and left behind. A `quiet` run that ends with zero assumptions
recorded did not do this right: silence without a ledger is guesswork.

**In `lite` the artifact is the same, the route to it is shorter:** write `requirements.md` straight
from the description (Jira mode still spawns `jira-fetcher` — it is the only way to read the ticket)
and skip the `business-analyst` gap-check below. The question bar above is **unchanged** — lite cuts
gates and agents, never clarification. A lite task usually needs fewer questions because it is
smaller, not because you are allowed fewer.

### Path A — Manual mode (interactive analyst)

Act as a business analyst. Gather complete, unambiguous requirements under the question bar
above. Cover:
- The user-facing goal and the concrete acceptance criteria.
- Which existing screen/feature/module it touches (use `ast-index` to ground yourself in what
  already exists before asking — don't ask what the code can tell you).
- Inputs/outputs, server endpoints involved, edge cases, error states, empty/loading states.
- Whether there is a Figma design link (capture it if yes).

Stop asking once you can write requirements with no open questions.

### Path B — Jira mode (fetch, then clarify gaps)

1. Spawn the **`jira-fetcher`** subagent (via the `Agent` tool). Tell it: the Jira key/URL, and to
   write a structured `.claude/tasks/<slug>/requirements-raw.md` containing the issue summary,
   description, acceptance criteria, attachments/links, and the full text of any linked Confluence
   pages, plus any Figma links it finds. It returns a concise summary; the detail stays in the file.
   Do **not** commit — the file stays in the working tree and folds into the pipeline's `plan`
   milestone commit.
2. Read `requirements-raw.md`. Act as a business analyst: identify gaps, ambiguities, and missing
   acceptance criteria. Ask the user **one question at a time** with `AskUserQuestion`, processing
   each answer before forming the next. Use `ast-index` to ground questions in the existing
   codebase rather than asking what the code already answers. Capture any Figma link.

### Both paths — analyst gap-check, then finalize

1. **Draft.** Write a first-pass `.claude/tasks/<slug>/requirements.md` from what you have so far
   (Path A: your interactive answers; Path B: `requirements-raw.md` + answers).
2. **Analyst gap-check** (`standard` only — skipped in `lite`). Spawn the **`business-analyst`** subagent (via the `Agent` tool) with the
   draft `requirements.md` (and `requirements-raw.md` if it exists). Tell it to ground itself in the
   existing code via `ast-index` and return a structured list of: missing or weak acceptance
   criteria, ambiguities, implicit assumptions, scope boundaries (in / out), and the **open
   questions that block implementation**. It is read-only — it returns its analysis, it does not edit
   files. If `business-analyst` is not available in this environment, do the gap analysis yourself —
   never skip this step.
3. **Resolve gaps** (`standard` only). Ask the user the analyst's open questions with `AskUserQuestion`, one at a time,
   skipping any the draft already answers; process each answer before forming the next.
4. **Finalize.** Rewrite `requirements.md` incorporating the answers and the analyst's
   acceptance-criteria suggestions (goal, acceptance criteria, affected modules, API/data needs, UI
   states, edge cases, Figma link if any, out-of-scope notes). End the file with
   `<!-- CHECKPOINT: requirements DONE @ <ISO-date> -->`.
5. Tick `requirements` in `STATE.md` (disk only — **do not commit**). The requirements artifact is
   committed later by the pipeline as part of the single `plan` milestone commit (see the
   `feature-pipeline` commit discipline: three milestones — plan / feat / docs-report).

## Phase 3 — Hand off to the pipeline

Invoke the **`feature-pipeline`** skill to run the remaining phases (architecture → designer? →
test-plan → confirmation gate → development → tests → finalize → report). Pass it the `<slug>` and
the `Mode profile` from `STATE.md`. Keep the user informed with one short line per phase transition.
