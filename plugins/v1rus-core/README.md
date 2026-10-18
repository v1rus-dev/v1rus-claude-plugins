# v1rus-core

Corporate engineering baseline for v1rus. Stack-agnostic: every v1rus project installs this
layer, directly or as a dependency of `v1rus-kotlin` / `v1rus-compose` / `v1rus-kmp` /
`v1rus-android` / `v1rus-flutter`.

```
/plugin install v1rus-core@v1rus
```

## What it contains

| Component | What it does |
|---|---|
| `hooks/charter.md` + `inject-charter.py` | The engineering charter, injected at every session start — communication style, non-negotiables, principles, the four mandatory gates, delegation policy. This is the plugin's replacement for a shared `CLAUDE.md`. |
| `hooks/git-guard.py` | Blocks the shell-shaped non-negotiables: `sudo`, git-hook bypass (`--no-verify`), plain `--force` push, and commit/push from `main` / `master` / `develop`. |
| `hooks/secrets-guard.py` | Programmatic backstop over secret files and exfiltration-shaped commands; deliberately overlaps a project's `permissions.deny`. |
| `hooks/path-rules.py` + `rules/` | Delivers path-scoped rules (the `.claude/rules/*.md` mechanism plugins otherwise cannot use). Core ships none; the language layers do. |
| `skills/v1rus-*` | The rulebook, loaded on demand: `v1rus-workflow` (gates + task routing), `v1rus-qa` (testing strategy), `v1rus-code-policies`, `v1rus-sources` (trust tiers), `v1rus-logging`, `v1rus-dependencies`, `v1rus-code-search`. |
| `skills/` (process) | `check` (verification gate), `finalize` (quality loop), `write-spec`, `write-plan`, `write-tests`, `generate-test-plan`, `multiexpert-review`, `research`, `evaluate-dependency`. |
| `agents/` | Stack-agnostic reviewers and authors: `code-reviewer`, `architecture-expert`, `security-expert`, `ux-expert`, `business-analyst`, `designer`, `source-researcher`, `dependency-evaluator`. |
| `commands/review.md` | `/review` — standalone read-only review of a path, module or the working diff, with automatic expert escalation. |
| `skills/feature-pipeline/` | The multi-agent feature factory: phase sequence, confirmation gate with complexity scoring, test loop, three-milestone commit discipline, resume via `STATE.md`. Runs in two modes — `standard` (default, unchanged) and `lite`; the *Pipeline modes* section is the single source for the deltas. `references/agent-resolution.md` defines role→agent binding and escalation. |
| `commands/feature.md`, `commands/bugfix.md` | `/feature` (manual or Jira-sourced requirements) and `/bugfix` (red-green with a mandatory debug artifact) — the pipeline entry points. |
| `commands/feature-lite.md` | `/feature-lite` — alias for `/feature --lite`: the same pipeline with a reduced set of gates for small, well-understood work. It does not lower the verification floor. |
| `commands/mvp-init.md` + `references/mvp-blueprint.md` | `/mvp-init` — scaffold a new application from a product description: brief, stack choice, scaffold plan, mandatory gate, bootstrap, the generated project `CLAUDE.md`, a green build, and an MVP backlog of ready-to-run `/feature` commands. Stack-agnostic; the technology knowledge comes from the stack layer's `*-mvp-blueprint` skill, whose contract lives in `references/mvp-blueprint.md`. |
| `agents/feature-*`, `agents/test-*`, `agents/jira-fetcher` | The pipeline's own agents: architect, designer, developer, finalizer, reporter, test-planner, test-writer, Jira fetcher. They are the **floor** — implementation escalates to `kotlin-engineer` / `compose-developer` / `swift-engineer` when those layers are installed. |

## Design notes

**Why hooks carry the rules.** Claude Code plugins have no `CLAUDE.md` and no `rules/` component —
the plugin reference states that a plugin-root `CLAUDE.md` is not loaded as project context, and
that plugins contribute context through skills, agents and hooks only. So the always-on baseline is
a `SessionStart` hook returning `additionalContext`, and file-type-scoped rules are a `PreToolUse`
hook. Everything else is a skill, loaded by description when it is actually relevant.

**Layering.** `v1rus-core` knows nothing about its consumers. Downstream plugins declare
`"dependencies": ["v1rus-core"]` (an **array**, per the manifest schema — not an object map) and
Claude Code installs and enables it transitively.

**Requirements.** `python3` on `PATH` for the hooks. On Windows without a `python3` shim, either run
Claude Code under WSL or create the alias — the hooks fail open (a hook that cannot start does not
block the session), but the charter and the guards will not be active.

**Pipeline portability.** The pipeline ships the process; the project supplies the names. Every agent
reads the target project's `CLAUDE.md` for module paths, build and test tasks, and type names — nothing
project-shaped is baked in. A project that already has its own `/feature` keeps it: plugin commands are
namespaced (`/v1rus-core:feature`), so both can coexist until the project copy is retired.

**Project overrides.** A project's own `CLAUDE.md` and the developer's explicit instructions win over
the charter. Conflicts are stated once, then resolved in the project's favour.
