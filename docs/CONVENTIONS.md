# Authoring contract

For every agent or person adding content to a v1rus plugin. Read `CLAUDE.md` (versioning, layering) first.

## Plugin layout

```
plugins/v1rus-<name>/
  .claude-plugin/plugin.json   name, version, description, author, dependencies (array)
  hooks/charter.md             v1rus-core only: always-on baseline, injected at SessionStart by hooks/inject-charter.py
  rules/<topic>.md             path-scoped rules (frontmatter `paths:`), injected on Write/Edit
  skills/<skill>/SKILL.md      thin door + optional supporting files
  agents/<agent>.md
  hooks/hooks.json, hooks/path-rules.py   standard path-rule injector; every plugin ships an identical copy
```

`hooks/path-rules.py` is the same file in every plugin (each layer installs alone, so it cannot be shared by path); change it in all plugins at once. `v1rus-core` additionally ships `inject-charter.py`, `git-guard.py` and `secrets-guard.py`. Plugin-specific hooks go in the plugin's own `hooks/hooks.json`.

## Charter (always-on layer)

Only `v1rus-core` has a charter (`hooks/charter.md`); stack layers deliver their conventions as path-scoped rules and skills. The charter costs context in EVERY session of every project that has the plugin enabled. Rules:
- Only what is true for every task on this layer and must not be forgotten: working principles, hard prohibitions, how to find details (point to skills/rules by name).
- Hard cap 200 lines, target under 80. Short imperative bullets, no tutorials, no examples longer than 3 lines.
- Phrase as facts and conventions, not as "SYSTEM:" commands. Optional frontmatter is stripped.
- Language-/stack-specific content goes to that stack's plugin, never to core.

## Path-scoped rules

File `rules/<topic>.md`, loaded once per session when Claude edits a matching file:

```markdown
---
paths:
  - "**/*.kt"
  - "**/*.kts"
  - "src/**/*Test.kt"
---

# Kotlin coroutines

- Imperative bullets...
```

- `paths` is a YAML list (or comma string); globs are relative to the project root, same semantics as Claude Code `.claude/rules`: `**/*.kt` for any depth, `*.md` only at root. Unlike Claude Code `.claude/rules`, `path-rules.py` does NOT expand `{a,b}` braces: list each glob on its own line.
- A rule without `paths` is NOT injected by `path-rules.py` (checker warns): put always-on text in core's `hooks/charter.md`, or make it a skill.
- One topic per file, under ~150 lines; the body is injected verbatim after frontmatter is stripped.
- Rules are for conventions that apply while writing code. Procedures/workflows -> skills.

## Skills

- Directory name = `name` in frontmatter (checker enforces). Kebab-case, topic-based.
- `description` is the invocation trigger: what topics it covers, the situations to load it, and explicitly when NOT to use it. Write it so the model can decide from the description alone. Block scalar `|-` if it spans lines.
- Body is a thin door: 5-20 lines saying when to read which rule, pointing to files with `${CLAUDE_PLUGIN_ROOT}/rules/<topic>.md` (resolved by Claude Code inside skill bodies; the checker verifies the file exists). Put long material in `rules/` or `skills/<skill>/reference/*.md`, linked relatively.
- Optional `paths:` in skill frontmatter limits auto-activation to matching files.

## Agents

- Frontmatter: `name`, `description`, optional `model`, `tools`, `skills`, `color`. Ignored in plugins (do not use): `permissionMode`, `hooks`, `mcpServers`, `initialPrompt`.
- Multi-line `description` MUST be a block scalar:

```yaml
description: |-
  Reviews Kotlin code for ...
  Use when ...; not for ...
```

  A plain multi-line or colon-containing scalar breaks YAML and the agent loads with all fields ignored.
- Body = system prompt: role, inputs, procedure, output format. Reference rules via `${CLAUDE_PLUGIN_ROOT}/...` paths to read, don't inline them.

## Content rules

- No hardcoded external package/library/tool versions anywhere. Distinction: a **language/runtime version gate** (`Go 1.22+`, `Node 24`, `Kotlin 2.x` as a feature-availability threshold) is allowed and expected, because it states when a feature exists and the project's own `go.mod`/`engines` line is checked first. A **package or tool version pin** (a library coordinate with a version, a `latest is X.Y.Z` claim, a pinned linter/CLI version) is not allowed. Verify gates against the real toolchain before writing them. Say how to resolve (maven tools, `npm view`, docs) instead. Checker warns on version-looking coordinates.
- Product- or project-specific facts (module names, flags, backends, design system) are NOT stored here: instruct the agent to read them from the target project's CLAUDE.md/docs.
- No secrets, internal URLs, customer names.
- Relative markdown links and `${CLAUDE_PLUGIN_ROOT}/...` references must resolve inside the same plugin; never reference another plugin's files by path (cache layout makes that fragile). Cross-plugin knowledge flows via `dependencies` and skill names.
- Layering: place each rule on the highest layer where it is still true (see `CLAUDE.md`).

## Done checklist

1. If `path-rules.py` changed, copy it to every plugin's `hooks/` (checker does not enforce identity)
2. Bump `version` of each touched plugin (patch/minor/major table in `CLAUDE.md`)
3. `claude plugin validate . --strict` and `python3 scripts/check-plugins.py --all`
4. If rules/charter changed: pipe a sample event through the hook (commands in `CLAUDE.md`)
