# v1rus-core

Base layer of the v1rus marketplace: always-on charter, the development workflow (gates), shared review/research agents, skills, and the rules engine (`hooks/`, canonical copy, synced to other plugins by `scripts/sync-engine.py`).

## Contents

- `charter.md`: always-on baseline injected at SessionStart (49 lines): gates, autonomy, delegation, testing bands, verify-API rule, dependency gate, code habits, pointers.
- `rules/` (path-scoped, injected once per session on the first matching Write/Edit): `code-policies`, `logging`, `qa-and-testing`, `dependencies`.
- Skills, rulebook doors: `v1rus-workflow`, `v1rus-qa`, `v1rus-code-policies`, `v1rus-logging`, `v1rus-dependencies`, `v1rus-sources`, `v1rus-code-search`.
- Skills, procedures: `finalize`, `check`, `research`, `write-spec`, `write-plan`, `write-tests`, `generate-test-plan`, `multiexpert-review`, `evaluate-dependency`.
- Agents: `code-reviewer`, `security-expert`, `architecture-expert`, `ux-expert`, `business-analyst`, `designer`, `source-researcher`, `test-runner`.
- Command: `/review` (read-only review of a path or the working diff, escalating to expert agents).

Working files (state, reports, plans) go to `swarm-report/` in the target project (gitignore it) and `docs/{plans,specs,testplans}/` for durable documents.

## Split decisions: source -> destination -> why

| Source (`~/.claude`) | Destination | Why |
|---|---|---|
| `rules/workflow.md` | charter (gate summary) + `skills/v1rus-workflow/reference/workflow.md` | Gates are always relevant; the full text is only needed when planning. No editing path to scope it by, so a skill reference, not a rule (a rule without `paths:` is never injected). `[[autonomy]]` links rewritten as standalone text. |
| `rules/task-types.md` | `skills/v1rus-workflow/reference/task-types.md` | Routing matrix and baseline definition are consulted at planning time only. |
| `rules/qa-and-testing.md` | charter (bands) + `rules/qa-and-testing.md` (path-scoped to test files) + door `v1rus-qa` | Complexity bands must be always on; detail is useful exactly when a test file is edited, and is also loadable on demand. |
| `rules/code-policies.md` | charter (habits) + `rules/code-policies.md` (source files) + door `v1rus-code-policies` | Applies while writing code in any language. Added the minimal-diff principle from `CLAUDE.md`. |
| `rules/logging.md` | charter (one line) + `rules/logging.md` (source files) + door `v1rus-logging` | Trimmed from 175 lines: dropped the extension scope table, per-stack logger table (kept as a greenfield hint), and long examples. |
| `rules/dependencies.md` | charter (summary) + `rules/dependencies.md` (build files/manifests) + door `v1rus-dependencies` | Injected on the first build-file edit. Generalized from Gradle/maven-mcp-only to any ecosystem; tool names replaced by capabilities. |
| `rules/external-sources.md` | charter (verify rule) + `skills/v1rus-sources/reference/sources.md` + door `v1rus-sources` | Generalized: personal tool names (ksrc, android docs, Context7) became source classes; Android/Compose/CMP/SwiftUI per-stack routes dropped (belong to stack plugins). Trust tiers and conflict rules kept. |
| `rules/ast-index.md` | `skills/v1rus-code-search/reference/code-search.md` + door `v1rus-code-search` | Personal hook automation (watchers, SessionStart) dropped; the decision matrix and rules kept, phrased for "a symbol index when available". |
| `rules/communication.md`, `autonomy.md`, `task-execution.md`, `context7.md`, `CLAUDE.md` non-negotiables | not migrated (stay personal) | Russian-language style, personal escalation contract, tooling specifics. The essentials referenced by migrated text (decide-record-report, escalation bar, assumption ledger, sudo-free git rules) are condensed into the charter. |
| `rules/kotlin-style, coroutines, gradle-style, mobile-ui, android-cli` | skipped | Owned by the Kotlin/Compose/Android plugins. |
| `skills/finalize` | `skills/finalize` | Rewritten condensed (356 to 94 lines). Dropped: `developer-workflow-experts` dependency, `devops-expert`/`test-coverage-expert`/`build-engineer` as hard agents (optional now), coverage-audit schema file (delegates to `write-tests`), long rationale prose. |
| `skills/check` (source file was a misplaced test-infra reference without frontmatter) | new `skills/check/SKILL.md`; the reference content lives in `write-tests/references/` | `finalize` needs a mechanical build/lint/test gate; the original `check` had no valid skill. |
| `skills/research`, `write-spec`, `write-plan`, `multiexpert-review`, `generate-test-plan` | same names | Copied; `evals/` removed; `rules/external-sources.md` links repointed; personal paths and a plugin-family reference removed; JVM/Android examples generalized; `*-promts.md` typo renamed to `*-prompts.md` (links were broken). |
| `skills/write-tests` | same name | kotlin/swift-engineer routing replaced by "language engineer from an installed stack plugin, else general-purpose on sonnet"; Gradle/Swift commands replaced by project commands; Kotlin/Swift-only prompt templates merged into one. |
| `skills/evaluate-dependency` | same name | The missing `dependency-evaluator` agent replaced by an inline judge subagent; Gradle-only wording widened. |
| `agents/{architecture-expert, business-analyst, code-reviewer, designer, security-expert, source-researcher, ux-expert}` | same names | Descriptions converted to `|-` block scalars; "answer in Russian" replaced by "user's language"; links to rules repointed; build/UI-implementer agent names generalized. Models kept (opus for architecture/business/designer, sonnet for reviewers, source-researcher sonnet). |
| `agents/test-runner` | same name | Rewritten stack-agnostic: commands come from the project's CLAUDE.md or build config. |
| `commands/review.md` | `commands/review.md` | Falls out of `code-reviewer` + expert agents; paths moved to `swarm-report/`. `feature-status` not migrated (pipeline-specific). |

## Lossy or deliberately left

- Security/UX experts still carry Android/iOS examples among general platform notes; stack plugins may add specific ones.
- `finalize` no longer ships the coverage-audit report schema or the long empirical rationale for Phase 0.
- Version numbers inside example text were removed; tool lookups are described by capability.
- `memory: project` is kept on expert agents (supported frontmatter).

## External optional dependencies

`skills/finalize` relies on things this plugin does not ship: the session built-ins `/code-review` and `/simplify`, and the separate `pr-review-toolkit` plugin agents (plus specialist agents such as `performance-expert` from `v1rus-kotlin`). All are optional: when one is absent `finalize` skips or replaces that phase and logs it (fallbacks in the skill's "External optional dependencies" section).

## Install

```
/plugin marketplace add v1rus-dev/v1rus-claude-plugins
/plugin install v1rus-core@v1rus-dev
```

