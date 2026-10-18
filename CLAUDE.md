# v1rus-dev marketplace

Personal layered Claude Code plugin marketplace. Plugins: `v1rus-core`, `v1rus-kotlin`, `v1rus-compose`, `v1rus-android`, `v1rus-go`, `v1rus-typescript`. Authoring contract: `docs/CONVENTIONS.md`. Doc facts: `docs/PLUGIN-SPEC-NOTES.md`.

## Rules

- Versioning: any change under `plugins/<name>/` MUST bump that plugin's `version` in `.claude-plugin/plugin.json` in the same commit (installs are pinned by version; without a bump `plugin update` silently does nothing). Enforced by pre-commit.

  | Change | Bump |
  |---|---|
  | Typo, wording, link fix, no behaviour change | patch |
  | New or changed rule/skill/agent/hook, backward compatible | minor |
  | Removed or renamed skill/agent/rule, changed dependency graph, changed hook contract | major |

- Layering: a rule lives on the highest layer where it is still true. Kotlin-only -> kotlin; true for any Kotlin UI -> compose; Android-only -> android; language-agnostic -> core. Dependencies: kotlin->core, compose->kotlin, android->compose, go->core, typescript->core.
- Rules engine: `plugins/v1rus-core/hooks/v1rus_rules.py` is canonical. After editing run `python3 scripts/sync-engine.py` (copies engine + hooks.json to the other plugins); the checker fails on drift.
- No secrets, tokens, internal hostnames or customer data in any file. Nothing copied from third-party/corporate marketplaces.
- Never pin external package versions in docs/rules; say how to look them up.
- Work on feature branches; no direct commits to main.

## Commands

```
git config core.hooksPath .githooks                      # once per clone
claude plugin validate . --strict                        # marketplace + every plugin entry
for p in plugins/*; do claude plugin validate $p --strict; done
python3 scripts/check-plugins.py --all                   # also: --staged | --base <ref>
python3 -m unittest discover -s tests                    # engine tests
```

Test hooks by piping events (set the env the host would set):

```
export CLAUDE_PLUGIN_ROOT=$PWD/plugins/v1rus-kotlin CLAUDE_PLUGIN_DATA=/tmp/v1rus-data
echo '{"session_id":"s","source":"startup"}' | python3 plugins/v1rus-kotlin/hooks/v1rus_rules.py session-start
echo '{"session_id":"s","cwd":"/proj","tool_name":"Edit","tool_input":{"file_path":"/proj/A.kt"}}' | python3 plugins/v1rus-kotlin/hooks/v1rus_rules.py path-rules
```

Empty stdout + exit 0 means "nothing to inject" (also the fail-open result).
Live trial: `claude --plugin-dir plugins/v1rus-core --plugin-dir plugins/v1rus-kotlin`.
