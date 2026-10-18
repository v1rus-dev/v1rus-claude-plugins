---
name: implementation-plan
description: Profile for implementation plans (docs/plans/<slug>/plan.md) produced by write-plan. Tech-matched panel, no mandatory reviewer; red-team anti-gaming rubric plus project-flow checks (complexity band, L0–L2 pyramid, dependency gate).
artifact_type: implementation plan
detect:
  frontmatter_type: [plan]
  path_globs:
    - "docs/plans/**/plan.md"
  structural_signatures:
    - "^## Technical Approach"
verdicts: [PASS, CONDITIONAL, FAIL]
allow_single_reviewer: true
reviewer_roster:
  primary: []
  optional_if:
    - agent: security-expert
      when: "auth|token|oauth|jwt|session|password|secret|credential|crypt|encrypt|pii|gdpr|permission|keystore"
    - agent: performance-expert   # lives in v1rus-kotlin; optional: skipped when not installed (note it in the report)
      when: "performance|latency|throughput|cache|N\\+1|pagination|batch|memory|leak|coroutine|dispatcher|recomposition|jank|index|query plan"
    - agent: architecture-expert
      when: "new module|module boundary|dependency direction|layer|public api|abstraction|decoupl|circular|breaking change|interface contract"
    - agent: build-engineer   # a build-system specialist; skipped when not installed
      when: "build script|lockfile|version catalog|build-logic|convention plugin|new dependency|bump|plugin id"
    - agent: ux-expert
      when: "screen|navigation|user-facing|accessibility|onboarding|error state|empty state|loading state"
receipt:
  path_template: "docs/plans/<slug>/plan.md"
  fields_to_update: [review_verdict, review_blockers]
source_routing:
  file: edit-in-place
  plan_mode: "N/A"
  conversation: surface-one-by-one
---

# Profile: implementation-plan

Reviews an **implementation plan** (the HOW of an already-decided change) before it is approved for
autonomous execution. Empty `primary` + tech-matched `optional_if` means the panel is sized to what
the plan actually touches — no padding, no fixed mandatory reviewer. With nothing matched the engine
falls back to tech-match selection; `allow_single_reviewer: true` lets a `--quick` plan pass with one
reviewer (verdict carries the single-perspective marker).

## Prompt augmentation

You are reviewing an **implementation plan** — the technical approach + ordered tasks an agent will
execute **without further approval**. Your job is to find what is *wrong* or *missing*, as a
strict-but-fair red team: do not look for reasons to approve, and do not invent blockers to look
thorough. Every finding must name the weakness, where it is (`section` / `T-N` / `file:line`), and
why it matters. A plan only earns PASS when an implementer could build from it with no guessing.

Reject — as **critical** (blocks implementation) or **major** — any of these anti-gaming patterns:

- **Hand-waving verbs** — "handle errors appropriately", "wire it up", "update the relevant files",
  "as needed" with no concrete target. Demand the actual file, contract, or behaviour.
- **Unfalsifiable acceptance** — a task whose `check` needs human judgement ("looks right", "works
  well"). Demand a test name, grep, or build/lint target.
- **Missing failure modes** — happy-path only. Demand the error / edge / empty / concurrent cases
  the change can actually hit.
- **Invisible scope** — a one-line task hiding a subsystem or days of work. Demand it be split or
  sized honestly.
- **Untraced requirements** — a spec `AC-N` with no task that satisfies it, or a task that satisfies
  nothing. Demand the mapping be complete.
- **Missing or hollow verification** — no `## Verification & Sources` section, or one that names a
  source of truth without confirming it is **collected and sufficient** ("baseline TBD", "spec
  somewhere"), or a migration / behaviour-preserving task with no before-state baseline captured
  **before** implementation. Demand the concrete source, its status, and a sufficiency claim.

Then apply these project-flow checks (this repo's rules — `qa-and-testing.md`, `task-types.md`,
`dependencies.md`):

- **Complexity score** — the plan must carry a complexity score (1–10) with its band. Flag a score
  that looks **gamed low** to dodge tests (e.g. multi-module behavioural change scored ≤6). At
  complexity **≥7** the verification section must include **L2 unit/integration tests on the changed
  behaviour**, and every modified **public** symbol must be covered (or annotated trivial) — a
  ≥7 plan with no test coverage of changed public behaviour is a blocker.
- **Testing strategy** — pyramid is **L0–L2 only** (build / static / unit-integration). A plan that
  proposes device / UI / E2E / manual-runtime verification, or treats it as required, is wrong —
  that tier is out of scope; flag it.
- **Dependency gate** — if the plan adds or bumps any dependency / plugin, its `## Dependencies`
  block must carry all four outputs (identity + role, latest-stable freshness, vulnerability scan,
  current-API study). A dependency introduced without them is a **blocker**. A reported CVE/GHSA
  with no mitigation is a blocker.
- **Conventions** — the approach must follow existing project patterns (module layout, DI, state
  management, data layer) rather than introducing a parallel one without justification in
  `## Decisions Made`.

Anything that violates a `## Non-negotiables` rule in any applicable `CLAUDE.md` is automatically a
critical blocker (confidence 100) — not subject to trade-off discussion.
