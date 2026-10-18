# v1rus-dev marketplace

Layered Claude Code plugin marketplace: rules, skills, agents and hooks that run in other projects, not application code. Plugins: `v1rus-core`, `v1rus-kotlin`, `v1rus-compose`, `v1rus-kmp`, `v1rus-android`, `v1rus-flutter`, `v1rus-dotnet`, `v1rus-go`, `v1rus-typescript`, `v1rus-node`, `v1rus-react`, `v1rus-fullstack`. Human overview: `README.md`. Authoring contract: `docs/CONVENTIONS.md`. Doc facts: `docs/PLUGIN-SPEC-NOTES.md`.

## Rules

- Versioning: any change under `plugins/<name>/` MUST bump that plugin's `version` in `.claude-plugin/plugin.json` in the same commit (installs are pinned by version; without a bump `plugin update` silently does nothing). Enforced by pre-commit (`scripts/check-plugins.py --staged`).

  | Change | Bump |
  |---|---|
  | Typo, wording, link fix, no behaviour change | patch |
  | New or changed rule/skill/agent/hook, backward compatible | minor |
  | Removed or renamed skill/agent/rule, changed dependency graph, changed hook contract | major |

- Layering: a rule lives on the highest layer where it is still true. Dependency graph (from each `plugin.json` `dependencies`): kotlin, flutter, dotnet, go, typescript -> core; compose -> kotlin; kmp, android -> compose; node, react -> typescript; fullstack -> node + react. Kotlin-only -> kotlin; true for any Kotlin UI -> compose; Android-only -> android; TypeScript on backend and web alike -> typescript; language-agnostic -> core. Never duplicate a rule across layers.
- Hooks: every plugin ships an identical `hooks/path-rules.py` and a `hooks/hooks.json` wiring it (PreToolUse on Write/Edit/MultiEdit, PreCompact reset). `v1rus-core` also ships `inject-charter.py` + `charter.md` (SessionStart), `git-guard.py`, `secrets-guard.py`. When `path-rules.py` changes, copy it to all plugins. `path-rules.py` does not expand `{a,b}` braces in `paths:` globs: one glob per line.
- No secrets, tokens, internal hostnames or customer data in any file.
- Never pin external package versions in docs/rules; say how to look them up.
- Never reference a skill/agent that no longer exists; renaming or removing one is a major bump and requires fixing references in dependent layers in the same commit.
- Work on feature branches; no direct commits to main. Never bypass hooks (`--no-verify`).

## Commands

```
git config core.hooksPath .githooks                      # once per clone
claude plugin validate . --strict                        # marketplace + every plugin entry
for p in plugins/*; do claude plugin validate $p --strict; done
python3 scripts/check-plugins.py --all                   # also: --staged | --base <ref>
python3 -m unittest discover -s tests                    # checker tests
```

Test hooks by piping events (set the env the host would set):

```
export CLAUDE_PLUGIN_ROOT=$PWD/plugins/v1rus-kotlin CLAUDE_PLUGIN_DATA=/tmp/v1rus-data
echo '{"session_id":"s","cwd":"/proj","tool_name":"Edit","tool_input":{"file_path":"/proj/A.kt"}}' | python3 plugins/v1rus-kotlin/hooks/path-rules.py
echo '{}' | python3 plugins/v1rus-core/hooks/inject-charter.py
echo '{"tool_name":"Bash","tool_input":{"command":"sudo ls"}}' | python3 plugins/v1rus-core/hooks/git-guard.py
```

A rule is injected once per session, so a repeated run with the same `session_id` prints nothing; change the id or clear `$CLAUDE_PLUGIN_DATA/injected/<session_id>/`. Empty stdout + exit 0 means "nothing to inject".
Live trial: `claude --plugin-dir plugins/v1rus-core --plugin-dir plugins/v1rus-kotlin`.

## Quiet failures

- Agent frontmatter: a multi-line `description` must be a block scalar (`|-`); otherwise YAML breaks and the agent loads with empty metadata. Check with `claude plugin details <plugin>@v1rus-dev`.
- A skill `description` is the invocation trigger, not an annotation; `name` must equal the directory name.
- Component directories (`skills/`, `agents/`, `commands/`, `hooks/hooks.json`) are defaults: do not list them in `plugin.json`.
- Product-specific facts (module names, type names, build tasks) are read from the target project's CLAUDE.md, not stored in plugins.
