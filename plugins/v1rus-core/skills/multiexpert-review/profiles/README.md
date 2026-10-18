# multiexpert-review profiles

Artifact-specific configuration the engine (`../SKILL.md`) loads at runtime. The engine is
artifact-agnostic — every per-artifact rule lives in a profile here. One file per profile,
`<name>.md`: YAML frontmatter for the structured config the engine reads as `profile.<field>`,
plus a single `## Prompt augmentation` body section.

## Inventory

Canonical list of valid profiles. The engine cross-checks this list against the `*.md` files
actually present in this directory (excluding `README.md`); any disagreement is
`PROFILE_INVENTORY_MISMATCH`.

- `implementation-plan` — implementation plans from `write-plan` (`docs/plans/<slug>/plan.md`).
- `spec` — feature specifications from `write-spec` (`docs/specs/<date>-<slug>.md`).
- `test-plan` — test plans from `generate-test-plan` (`docs/testplans/<slug>-test-plan.md`; review receipt at `swarm-report/<slug>-test-plan.md`).

## Detection precedence (canonical)

Engine Step 1 resolves the profile in this order; first match wins; record the source. Profile is
**locked at cycle 1** — re-reviews (cycle ≥2) reuse the locked profile and MUST NOT re-detect.

The match values for steps 2–4 are NOT hardcoded here — each profile declares them in its own
`detect:` block (`frontmatter_type`, `path_globs`, `structural_signatures`). The engine reads every
profile's `detect:` and matches in this order:

1. **Caller hint** — args begin with `profile: <name>` on the first line(s) before a `---`
   separator. If `<name>` is not in the Inventory → `UNKNOWN_PROFILE_HINT`, stop. Never fall back
   to a default silently.
2. **Artifact frontmatter** — the artifact's `type:` matches some profile's `detect.frontmatter_type`.
3. **Path signature** — the artifact path matches some profile's `detect.path_globs`.
4. **Content signature** — the artifact body matches some profile's `detect.structural_signatures`.
5. **Ask the user** — only when 1–4 all fail.

A signature that matches two profiles is an authoring error — keep `detect` blocks mutually exclusive.

## Profile schema — allowed frontmatter

Everything a profile MAY declare:

- `name` — the profile name; MUST equal the filename stem and an Inventory entry.
- `description` — one-line summary (panel + what the rubric checks).
- `detect` — `{ frontmatter_type: [...], path_globs: [...], structural_signatures: [...] }`; the detection data consulted by Step 2–4 above.
- `artifact_type` — OPTIONAL human label substituted into the engine's prompt skeleton (`{artifact_type}`); defaults to the profile name if omitted.
- `verdicts` — the verdict alphabet, an ordered subset of `[PASS, CONDITIONAL, WARN, FAIL]`.
- `allow_single_reviewer` — bool; governs the engine's single-reviewer guard.
- `reviewer_roster` — `{ primary: [...], optional_if: [{ agent, when }] }`. `when` is a regex matched
  against the artifact text. Empty `primary` + no `optional_if` match → engine falls back to
  tech-match selection.
- `severity_mapping` — OPTIONAL; only for checklist-style profiles (e.g. test-plan items a–e).
- `receipt` — OPTIONAL; `{ path_template, fields_to_update: [...] }`. `<slug>` is substituted.
- `source_routing` — `{ file, plan_mode, conversation }`, each an action or `N/A`.

Body: `## Prompt augmentation` is the section injected into the review prompt as
`{PROFILE_PROMPT_AUGMENTATION}` (it never replaces the engine skeleton). A profile MAY add further
documentation sections (`## Rubric`, `## Verdict policy`, `## Receipt integration`, `## Rationale`)
for reference — only `## Prompt augmentation` reaches the reviewers' prompts.

## Forbidden fields (negative-list)

These are engine constants. A profile declaring ANY of them → `FORBIDDEN_PROFILE_FIELD: <first
offending key>`, stop. Forbidden keys: `verdict_format`, `review_output`, `aggregation`,
`aggregation_rules`, `cycle_cap`, `revise_loop_cap`, `state_machine`, `transitions`,
`review_prompt`, `prompt_skeleton`. (Review output structure, aggregation rules, the 3-cycle cap,
the state machine, and the prompt skeleton are fixed in the engine — a profile extends behavior
ONLY through `reviewer_roster` / `verdicts` / `receipt` / `source_routing` / `## Prompt
augmentation`.)

## Validation — runs on every invocation, before Step 2

1. Resolved profile name is in the Inventory AND its file is present
   (else `UNKNOWN_PROFILE_HINT` or `PROFILE_INVENTORY_MISMATCH`).
2. Frontmatter contains no forbidden field (`FORBIDDEN_PROFILE_FIELD`).
3. `name` == filename stem == Inventory entry; short-name reviewer collisions resolved per the
   engine's family tie-break (`AMBIGUOUS_REVIEWER` on a genuine clash).
