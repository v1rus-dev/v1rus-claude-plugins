# Agent Resolution & Escalation

How the project's multi-agent pipeline (`/feature`, `/bugfix`, and the `feature-pipeline` skill) binds each unit of work to an agent.

## Dependency direction

- Project agents (`.claude/agents/`, in the repo) = the stable floor — every developer on the project has them.
- Global agents (`~/.claude/agents/`) = per-developer, variable: may be absent, extra, or named differently.
- The pipeline MUST run fully on project agents alone, and treat any fitting global agent as an opportunistic upgrade — never a requirement.

## Invariants

1. **Self-sufficiency** — every role has a project-resident closure (a project agent OR an inline orchestrator routine). No role's baseline is a global agent. With zero global agents present, the pipeline still completes end to end.
2. **Opportunistic, upward-only escalation** — only the orchestrator (it alone has the `Agent` tool and sees the injected "Available agent types" inventory) compares discovered agents against a role's baseline for the specific task at hand, and escalates only when a discovered agent is clearly more specialized for THAT task. Tie or uncertainty → keep the baseline.
3. **Two escalation modes.**
   - **(a) Advisory escalation** — review, audit, research, design authoring, and the `*-expert` reviews. The escalated agent returns *findings only*: it does not edit product code and never commits.
   - **(b) Executor escalation** — **implementation**. The escalated specialist MAY write product code, but still **never commits**: it leaves changes in the working tree for the orchestrator to commit at a milestone, exactly like `feature-developer`. `feature-developer` remains the floor (invariant 1 holds), so the pipeline still completes with zero global agents.
   The remaining spine roles never escalate and stay project: orchestration, STATE.md, commits, requirements authoring, architecture authoring (`feature-architect`), test planning/writing, finalize, report, Jira fetch.
4. **Subagents recommend, the orchestrator decides** — project subagents have no `Agent` tool and never dispatch; they return a `recommended roles` list (see output format) plus a one-line task descriptor per role. The orchestrator binds role→best-available and decides escalate-vs-baseline.
5. **Every binding is recorded in STATE.md** (and surfaced in REPORT.md): which agent — or "inline" — closed each role, whether it was baseline or escalation, and the one-line reason. Both upgrade and degradation are visible; degradation is never silent.

## "Clearly more specialized" — the escalation test

Escalate only if the discovered agent's description names the task's specific domain more narrowly than the baseline does (e.g. "KMP Compose performance", "mobile OAuth/token security", "Gradle convention plugins / build performance"). A general-purpose discovered agent never beats a purpose-built project baseline. When the comparison is unclear, keep the baseline and note it in STATE.md.

## Discovery (orchestrator, Phase 0)

During the Phase 0 environment probe the orchestrator reads its "Available agent types" inventory (names + descriptions) and, for each role in the table below, records a binding in STATE.md: the project baseline, plus the best-fitting discovered agent if one clearly wins per the test above. Discovery is by capability/description, never by a hardcoded name — so a differently-named or extra global agent is picked up too.

## Role → project baseline table

| Role | Project baseline (floor) | Escalate to (if clearly better-fit) |
|---|---|---|
| requirements-gap-check | inline analyst (orchestrator) | business-analyst |
| design-authoring | feature-designer (Figma mapping) or inline | designer |
| architecture-review | inline (plan checked against CLAUDE.md) | architecture-expert |
| code-review | inline orchestrator review | code-reviewer |
| security-review | inline | security-expert |
| performance-review | inline | performance-expert |
| ux-review | inline | ux-expert |
| build-review | inline | build-engineer |
| deep-research | inline | source-researcher / the `research` skill |
| **implementation** (executor escalation) | **feature-developer** (project floor) | a clearly-more-specialized **engineer that writes code** — the stack layer names its own (KMP: `compose-developer` / `kotlin-engineer` / `swift-engineer`; Flutter: `flutter-ui-developer` / `flutter-engineer`; build scripts: `build-engineer`) — writes to the working tree, **never commits** |

Implementation escalation follows the same "clearly more specialized" test (§ below) and is opportunistic: if no discovered engineer clearly out-specializes `feature-developer` for the task, keep `feature-developer`. Record the binding + reason in STATE.md like any other role.

## Spine roles — project-only, never escalate

requirements authoring, architecture authoring (`feature-architect`), test planning/writing (`test-planner`/`test-writer`), finalize (`feature-finalizer`), report (`feature-reporter`), Jira fetch (`jira-fetcher`).

(**Implementation moved out of the spine** — it now escalates via *executor escalation* with `feature-developer` as the floor; see the role table + invariant 3b.)

## Stack dimension — spine agents specialise by profile, not by swapping agents

A spine role staying on its project agent does **not** mean it stays on one technology. The spine agents are stack-agnostic: the technology vocabulary — layer names, the sections of `architecture-plan.md`, which convention skill owns which rule, where tests live and on what, how to compile-check — reaches them as a **stack profile** resolved in Phase 0 (`stack-profile.md`). So the same `feature-architect` plans a KMP feature and a Flutter feature, in each stack's own vocabulary, and there is no per-stack clone of the spine to keep in sync.

Consequences for resolution:

- **Do not** treat a stack layer's engineer agent as an escalation for architecture authoring, test planning or finalize. Those roles specialise through the profile; escalating them would fork the pipeline scaffolding.
- **Do** record `Stack:` and `Pipeline profile:` in STATE.md next to the agent bindings — a missing profile is a visible degradation, exactly like a missing global agent.
- The stack layer's **`test-runner`** and its **engineer agents** are the parts that genuinely differ per technology, and those are resolved as agents in the normal way (see the role table and the `test-run` note below).

A per-stack spine agent is only justified when a stack's phase differs in a way a profile cannot express (a structurally different artifact, not different vocabulary). Then it is added as an escalation target for that one role, on top of the profile, with the core agent staying the floor.

## recommended-roles output format (for subagents)

Subagents that may surface a specialist need end their return with a short block, one line per recommendation:

`RECOMMENDED-ROLE: <role-name> — <one-line task descriptor of what to review and why>`

If none: `RECOMMENDED-ROLE: none`. The orchestrator reads these and resolves each against the table.

## Dispatching advisory/review agents (no-Write rule)

Most review agents (`code-reviewer`, and the read-only `*-expert` reviewers) have **no `Write` tool**. Do NOT instruct them to write their report to a file — they can't, and their final summary often arrives truncated. Instead: in the dispatch prompt, tell the agent to **return its complete, structured report as its final message**, and have the **orchestrator persist** that text to the artifact (`code-review.md`, `expert-reviews.md`). This avoids the truncated-summary → re-prompt round-trips. (Applies to advisory escalation only; executor-escalated engineers do write to the working tree.)

## Open gaps (to resolve)

`test-run` has **no closure in the stack-agnostic layer**: running a build or a test suite requires the stack's own commands, and an inline baseline is not viable because the orchestrator must not run long builds in its own context. It is closed by the stack layer instead — `v1rus-kmp:test-runner` (Gradle build + the desktop/JVM test tasks), `v1rus-android:test-runner` (variant-aware unit-test tasks + lint, instrumented tests opt-in) and `v1rus-flutter:test-runner` (codegen + `dart analyze` + `flutter test`), each discovering the project's commands rather than guessing them. So the role is covered whenever the matching stack layer is installed, which is also the layer that supplies the pipeline profile. With **no** stack layer installed the role is genuinely uncovered: record it as an exception in STATE.md and, at complexity ≥7, stop rather than declaring tests green — never pretend the role is closed.

`code-review` is NOT a gap: its inline baseline — the orchestrator reviewing the diff — is a valid project-resident closure per invariant 1, self-sufficient though weaker than a dedicated reviewer, and it escalates to `code-reviewer` when one is available (see the role table). Listed here only to record that the dedicated reviewer is global-only; the role itself is covered.
