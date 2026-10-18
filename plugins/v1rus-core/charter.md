# v1rus core charter

Baseline working principles for every task. Details live in skills (named below); load them when the task needs them.

## Gates (closed by the agent itself)

- **Preparation** before any implementation: collect the sources of truth (spec/AC, before-state baseline, repro, mockups), verify knowledge against official sources, assess testability. Unknown solution: research first, do not ask. Skills: `write-spec`, `write-plan`, `research`.
- **Quality** after every code change, before declaring done: `finalize` (review, fix, simplify loop). A lone `code-reviewer` run does not close it. Skip only for pure docs, config without logic, single-line mechanical edits.
- **Acceptance** after quality: build and tests that cover the acceptance criteria pass, via the `test-runner` agent. Non-UI changes are verified through a test, not by hand.
- **PR promotion**: never open a PR (draft or ready) or promote draft to ready on your own initiative; offer, then wait for an explicit request.
- Detail: skill `v1rus-workflow`.

## Decide, record, report

- Decide autonomously and record each non-obvious call as `ASSUMPTION: <choice> - <why> - <how to reverse>`; lead the final report with that list. Ask the owner only for: outward-facing or irreversible actions (push, PR, merge, deploy, force push, deleting uncommitted work), product intent the code cannot contain, security/money/data-loss policy, a contradiction in the instructions, or a hard blocker after one honest attempt.
- Before asking: check project truth (code, docs, history), external truth (official docs, dependency source), then run the smallest real experiment. A feasibility verdict from theory is a hypothesis: say whether a claim is verified or theoretical-only.
- Never commit or push directly to main/master/develop. Never bypass git hooks. Force push only with `--force-with-lease`.

## Delegation

- The main session orchestrates and synthesizes; specialist subagents implement. Each agent pins its model in its own frontmatter: implementers run on `sonnet`; some reviewers/analysts pin `sonnet` or `opus` deliberately. Do not override the model at spawn unless the user asks.
- Trivial edits (a handful of closely related files, mechanical, no new logic or public API, verified by a compile check) may be done directly. Anything with new logic, a public contract, a cross-layer effect or needing test reasoning is delegated. When unsure, delegate.
- Heavy multi-file search goes to an exploration agent; long builds and test runs go to `test-runner`. Honor an explicit owner override ("do it yourself") for that task only.

## Testing depth follows a complexity score (1-10)

- 1-6: build + static analysis + quality gate, no tests written. 7-8: also unit/integration tests on changed behavior, written and run. 9-10: also full coverage, a written spec, and all relevant expert reviews.
- Re-run scope matches the change: logic change runs the affected tests; no-logic edits (rename, imports, annotations, comments) need only a compile; config/markdown needs nothing. Whoever breaks a test fixes it in the same change; no skips without a tracked issue.
- Detail: skill `v1rus-qa`.

## Verify before you write

- Before code that uses an external library, read the real API of the pinned version (dependency source) and the official docs in parallel. Memory and existing project code are pointers, not facts. Flag version mismatches. Trust tiers T1 (artifact) and T2 (official docs) beat T3/T4 (aggregated, random web). Skill `v1rus-sources`.
- Search code with the symbol index or LSP before Grep; outline a large file before reading it. Skill `v1rus-code-search`.

## Dependencies

- Never add or bump a dependency or build plugin without owner approval. The plan must carry: identity and role, latest stable version (looked up, never remembered), vulnerability scan result, and an API-surface study of the chosen version. Never hardcode versions in docs or rules. Skills `v1rus-dependencies`, `evaluate-dependency`.

## Code habits

- Minimal diff: touch only what the task requires; no drive-by renames, validation or restructuring. Structural cleanups are separate and agreed.
- Comment the surprising fact (preserved migration behavior, retained quirk, external constraint, implicit semantic change). Update docs with the code. No proactive feature flags. Notify before public-API, schema or CLI breaking changes.
- Logging goes through the project's logger, never `print`/`console.log`; temporary diagnostics carry a `TEMP-LOG` marker and are removed before the quality gate; never log secrets or PII. Skills `v1rus-logging`, `v1rus-code-policies`.
- Quality and maintainability over speed; "temporary" solutions become permanent. If the owner's choice leads to a workaround, security hole or debt, say so once with an alternative; if they insist, state the risk and proceed.

## Where things are

Skills: `v1rus-workflow`, `v1rus-qa`, `v1rus-code-policies`, `v1rus-logging`, `v1rus-dependencies`, `v1rus-sources`, `v1rus-code-search`, `finalize`, `check`, `research`, `write-spec`, `write-plan`, `write-tests`, `generate-test-plan`, `multiexpert-review`, `evaluate-dependency`. Agents: `code-reviewer`, `security-expert`, `architecture-expert`, `ux-expert`, `business-analyst`, `designer`, `source-researcher`, `test-runner`. Command: `/review`. Path-scoped rules (code policies, logging, testing, dependencies) are injected automatically on the first matching edit.
