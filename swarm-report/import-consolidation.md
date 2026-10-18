# Import consolidation: old v1rus files vs imported content

Hook engine: new engine wins. Removed `v1rus_rules.py` in every plugin, `scripts/sync-engine.py`, `tests/test_engine.py`, the engine-drift check in `scripts/check-plugins.py`. `v1rus-go/hooks` now uses the standard `hooks.json` + `path-rules.py`.

## Removed

| Item | Reason |
|---|---|
| core `charter.md` (plugin root) | Dead: new `inject-charter.py` reads `hooks/charter.md`; imported charter supersedes it |
| core `rules/{code-policies,dependencies,logging,qa-and-testing}.md` | Imported `v1rus-*` skills (code-policies, dependencies, logging, qa, ...) now carry the full text; rules would double-inject nothing (no `paths:`) |
| core `agents/test-runner.md` | Imported design (feature-pipeline `agent-resolution.md`) says test-run has no closure in the stack-agnostic layer; each stack ships its own `test-runner` |
| kotlin `charter.md` | Dead (only core injects a charter); content is pointers to removed/duplicated skills |
| kotlin `rules/gradle-build.md` | Duplicates imported `rules/gradle-style.md` (same globs, would inject twice) |
| kotlin `rules/kotlin-coroutines.md` | Duplicates imported `rules/coroutines.md` |
| kotlin `skills/gradle-dependency-gate` | Overlaps core `v1rus-dependencies` + kotlin `jvm-dependency-intelligence` |
| kotlin `skills/kotlin-api-verification` | Overlaps `jvm-dependency-intelligence` + core `v1rus-sources` |
| compose `rules/compose-ui.md`, `rules/compose-screen-quality.md` | Covered by imported `compose-ui-conventions`, `compose-screen-architecture`, `mvi-presentation`, `using-efficient-effects`, `deferring-state-reads` and `compose-files.md` rule |
| compose `skills/compose-screen-checklist` | Thin door over the removed rules; duplicates `compose-ui-conventions` |
| compose `skills/compose-performance` | Superseded by `auditing-compose-performance` + the 25 focused perf skills |
| compose `skills/compose-api-verification` | Covered by core `v1rus-sources` (fast-moving declarative UI section) |
| android `rules/android-platform.md` | Overlaps imported `rules/android-source.md` (Context/ViewModel leaks), `collecting-flows-safely`, `localisation-and-strings` |
| typescript `skills/ts-async-node` | Overlaps imported `ts-async` |
| typescript `skills/ts-boundaries` | Overlaps `ts-boundaries-validation` + `ts-error-handling` |
| typescript `skills/ts-lint-format` | Overlaps `ts-lint-and-format` |
| typescript `skills/ts-project-setup` | Overlaps `ts-project-config` |
| typescript `skills/ts-type-design` | Overlaps `ts-type-modelling` |
| typescript `rules/ts-boundaries.md`, `rules/ts-types.md` | Overlap imported `rules/typescript.md` + the skills above |
| typescript `rules/ts-config.md`, `rules/ts-lint-config.md` | Topics owned by `ts-project-config` / `ts-lint-and-format` skills |

## Kept

| Item | Reason |
|---|---|
| core `skills/multiexpert-review/profiles/README.md`, `skills/write-plan/references/review-loop.md` | Referenced by imported SKILL.md files |
| android `rules/android-tooling.md`, `skills/android-api-verification`, `skills/android-cli` (+reference), `skills/android-performance` | No imported counterpart; refs fixed to `v1rus-dependencies` / `v1rus-sources` / `collecting-flows-safely` / `auditing-compose-performance` |
| typescript `skills/ts-checkjs`, `ts-perf-profile`, `ts-security-checklist`, `ts-supply-chain`, `ts-testing` | Unique topics (plain-JS checkJs, profiling, security, supply chain, test runner choice); refs fixed |
| typescript `rules/ts-package.md`, `rules/ts-test.md` | Unique path rules (package.json, test files); `ts-test.md` brace globs expanded because new `path-rules.py` has no brace expansion |
| typescript `agents/ts-{engineer,reviewer,test-runner,toolchain-doctor}.md` | UNRESOLVED: typescript README (imported) says the layer ships no agents on purpose, so these contradict it. Deletion of the directory was blocked by the sandbox; refs inside them were fixed. Decide: delete the four agents, or edit the README sentence |
| go (all skills, agents, rules) | Untouched except `hooks/` and README wording |

## Other decisions

- `scripts/check-plugins.py`: kept ours (not the imported one). It is a superset: version-bump check (`--staged`/`--base`), skill/agent frontmatter, empty descriptions, agent-reference warnings, cycles, pin warnings, plus tests in `tests/test_check_plugins.py`. The imported one lacks these and would drop the tests. Engine-drift check removed, ref regex fixed (stopped matching a trailing `\` in JSON and `…`).
- `.githooks/pre-commit`: replaced with imported one (runs check + `claude plugin validate --strict`), translated to English. `.gitignore`: merged secret patterns from the imported one.
- Marketplace name kept `v1rus-dev` (installs reference `@v1rus-dev`).
- Versions: major bump from HEAD (1.1.1 -> 2.0.0) for core, kotlin, compose, android, typescript, go. New plugins unchanged.
