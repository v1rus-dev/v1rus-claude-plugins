---
description: Scaffold a new MVP application from a project description — brief, stack choice, module graph, dependencies, app skeleton with one working vertical slice, and the project CLAUDE.md that makes the rest of the toolchain work
argument-hint: [what the app is — product, platforms, key features]
---

You are the **orchestrator** of the MVP scaffolding run, in the main session. You can use
`AskUserQuestion` and the `Agent` tool; your subagents cannot. The developer wants a new application
brought into existence: a project that builds, runs, follows v1rus conventions, and is ready for
`/feature` on day one. Input (may be empty): **$ARGUMENTS**

**Language:** detect it from `$ARGUMENTS` and the developer's answers; default to **Russian**. All
communication with the developer is in that language. Artifacts (`project-brief.md`,
`scaffold-plan.md`, the generated `CLAUDE.md`, `REPORT.md`) and subagent prompts stay in English.

**The split.** This command owns the process: the brief, the stack choice, the plan, the gate, the
verification loop and the generated project `CLAUDE.md`. Everything technology-shaped comes from the
stack's **MVP blueprint** skill. The contract for what a blueprint provides is
`${CLAUDE_PLUGIN_ROOT}/references/mvp-blueprint.md` — read it if a blueprint looks incomplete, and
never substitute one stack's blueprint for another's.

All task paths below are under `.claude/tasks/mvp-init/`.

## Phase 0 — Probe the target directory and the environment

1. **Where are we.** `pwd`, list the directory including dotfiles, and check for an existing project
   (`pubspec.yaml`, `settings.gradle*`, `package.json`, `*.xcodeproj`, `Package.swift`, `Cargo.toml`)
   and for a git repo.
   - Empty, or only `README` / `LICENSE` / `.git` / `.claude` → proceed.
   - **A real project is already here** → stop. This command creates a new one; it does not
     retrofit an existing codebase. Ask (`AskUserQuestion`): create the project in a named
     subdirectory, or abort and use `/feature` to add to what exists.
2. **Capabilities.** From your available-skill inventory, collect every skill whose name ends in
   `-mvp-blueprint` — that set is the stack menu you can actually deliver. Note which stack layers
   are installed, and whether a Figma MCP is available (`mcp__*figma*`).
3. **Toolchain.** Check what is on PATH for the likely stacks (e.g. `flutter`, `dart`, `java`,
   `gradle`, `xcodebuild`) — do not install anything, just record availability.

## Phase 1 — Project brief

Create `.claude/tasks/mvp-init/` and write `project-brief.md`. Derive everything you can from
`$ARGUMENTS`, take a sensible default for the rest, and ask only for what genuinely changes the
scaffold and cannot be defaulted.

**Question discipline:** one question per round, at most **three** rounds for the whole command.
Priority order for what is worth a question: the stack (only if the platforms do not settle it),
the backend reality, the auth method. Everything you decide without asking goes into an
`## Assumptions` section of the brief — one line each, in the form
`ASSUMPTION: <choice> — <why> — <how to reverse it>` — and is repeated in the final report.

The brief records:

| Field | Default when the description is silent |
|---|---|
| Product one-liner | from `$ARGUMENTS` |
| Target platforms | ask if unclear — it drives the stack |
| MVP feature list (3–7 vertical slices) | derive from the description; name them, do not design them |
| Backend | ask: real API (base URL / OpenAPI spec) \| mock \| none yet — the scaffold differs materially |
| Auth | ask if the description implies accounts; otherwise none |
| Offline requirement | none for an MVP |
| Localisation | one locale, but string resources wired from the start |
| Analytics / crash reporting | deferred |
| Design source | Figma link if given; otherwise the stack's design-system defaults |
| App identifier + display name | derive from the product name, confirm in the gate |
| Minimum platform versions | the stack layer's current baseline |
| Repository | existing repo if one is here, otherwise `git init` in Phase 8 |

Never invent a client name, a real API host or credentials.

## Phase 2 — Stack and blueprint resolution

Map the target platforms and sharing needs onto a stack, using the *stack identity* section of the
candidate blueprints. If several genuinely fit (e.g. "iOS + Android, one codebase" → KMP or
Flutter), that is a legitimate question — ask it once, recommendation first, with the one-line
trade-off for each.

Record in the brief:

```
- Stack: kmp | android | flutter | <other>
- Blueprint: <plugin>:<skill> | none — <reason>
```

No blueprint for the chosen stack → say so to the developer in one line, record the degradation, and
proceed from that layer's convention skills and rules if it is installed. If nothing for that stack
is installed, stop and say which plugin to add.

## Phase 3 — Scaffold plan — `feature-architect` (Sonnet)

Spawn `feature-architect`. Tell it: the absolute task-folder path, to read `project-brief.md`, and —
before anything else — to invoke the blueprint skill (`Skill` tool), which is the stack vocabulary
for this project. Output: `scaffold-plan.md` containing

1. the module / package graph to create now, and what is deliberately deferred;
2. the complete file list to be written, grouped by module;
3. the **dependency table**: every coordinate from the blueprint's baseline set that the brief
   actually needs, each row carrying identity, role, resolved latest stable version and the CVE
   check — the `v1rus-dependencies` plan-stage gate applies in full, and a version is never copied
   from memory or from a blueprint;
4. build configuration values derived from the brief (identifier, minimum platform versions,
   static analysis, codegen);
5. the app skeleton wiring — entry points, DI order, theme seed, navigation host, network client,
   storage, localisation;
6. the first vertical slice, named, with its states;
7. the verification commands that will have to pass.

It plans; it does not create files, and it does not commit.

## Phase 4 — Confirmation gate (mandatory — this gate never auto-approves)

Show the developer, compactly: the stack, the module graph, the dependency list with the resolved
versions, the first vertical slice, and what will be created on disk. Then `AskUserQuestion`:
approve / adjust the plan / change the stack / abort.

Unlike the feature pipeline's lite mode, this gate always pauses: a project skeleton is the most
expensive thing in the whole workflow to undo, and every later feature inherits its decisions.

## Phase 5 — Bootstrap

Follow the blueprint's bootstrap route.

- **Toolchain missing** for a generator step: do not install it and do not use `sudo`. Hand the
  developer the exact command to run in their own terminal (they can run it in-session by prefixing
  it with `!`), and continue with every part that does not depend on it.
- **Delegate the file creation** to the agents the blueprint names as escalation targets — build
  configuration to the build agent, the logic layer to the stack's engineer, the UI layer to the
  stack's UI agent — with `feature-developer` as the floor when none is installed. Run agents that
  touch the same files **sequentially**, not in parallel.
- Every subagent prompt names the blueprint skill and instructs it to invoke it first, points at
  `scaffold-plan.md`, and states that it must **not** commit — the orchestrator owns commits.

## Phase 6 — The project's `CLAUDE.md` and Claude Code wiring

Write the new project's own `CLAUDE.md` from the blueprint's *project `CLAUDE.md` inputs*: module
paths, the build and test task names, the real names of the state-holder / navigator / theme types,
codegen commands, where tests live, and the v1rus plugins the project should enable. Also write
`.claude/settings.json` with `enabledPlugins` for the resolved stack layer.

**Do not skip this phase.** Every downstream plugin — the feature pipeline's stack profile, the
review agents, the path-scoped rules — reads the concrete names from the project's `CLAUDE.md`. A
scaffold without it leaves the whole toolchain guessing.

## Phase 7 — Verify

Run the blueprint's verification commands through the stack's `test-runner` when one is bound,
otherwise through the build agent. On failure, send the exact errors back to the implementing agent
and re-run — same shape as the feature pipeline's test loop, no iteration cap. Do not declare the
scaffold done on a tree that has not compiled and passed static analysis.

Record the final result in the brief as `Verification: <command> — PASS`.

## Phase 8 — Backlog, report, commit

1. **`mvp-backlog.md`** — one line per MVP feature from the brief, written as a command the
   developer can run as-is: `/feature --lite "<feature>"` for the small, well-understood ones and
   `/feature "<feature>"` for anything touching auth, payments, sync or a public contract.
2. **`REPORT.md`** — what was created (module graph + file count), the assumption list from the
   brief, what the developer must still do by hand (toolchain installs, signing, API keys, the real
   backend URL), and the next command to run.
3. **Commit.** Branch discipline applies exactly as everywhere else: never commit on
   `main` / `master` / `develop`, never push, never open a PR, never bypass git hooks.
   - No repo yet → `git init`, then `git checkout -b chore/mvp-init` **before** the first commit
     (a fresh repo starts on the protected default branch).
   - Existing repo → branch off it the same way.
   - One commit: `[mvp-init] chore: scaffold <app name>` — the whole scaffold plus the task
     artifacts.
   Finish by handing the developer the one-line command to fast-forward their default branch onto
   the scaffold branch, and let them decide when to run it.
