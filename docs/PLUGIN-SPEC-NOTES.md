# Plugin spec notes

Facts from the official Claude Code docs, fetched 2026-10-18 with Claude Code 2.1.302. Facts only; anything not verified is listed at the bottom.

Base URL: https://code.claude.com/docs/en/

## Components a plugin can ship today

Source: `plugins-reference` (redirects to the manifest reference) https://code.claude.com/docs/en/plugins/manifest-reference, https://code.claude.com/docs/en/plugins/components

| Component | Default location | Notes |
|---|---|---|
| Skills | `skills/<name>/SKILL.md` | Namespaced `/<plugin>:<dir>`. Frontmatter `paths:` (globs) limits automatic activation to matching files. |
| Commands | `commands/*.md` | Legacy; prefer skills. |
| Agents | `agents/*.md` | Supported frontmatter: name, description, model, effort, maxTurns, autoCompactWindow, tools, disallowedTools, skills, memory, background, omitClaudeMd, isolation, color. Ignored: permissionMode, hooks, mcpServers, initialPrompt. Unparseable frontmatter => agent loads with all fields ignored. |
| Hooks | `hooks/hooks.json` (top-level `"hooks"` key) | Same shape as settings.json hooks. Exec form (`command` + `args`) supported. |
| MCP servers | `.mcp.json` | |
| LSP servers | `.lsp.json` | |
| Settings | `settings.json` | Only `agent` and `subagentStatusLine` take effect. |
| Output styles, workflows, themes, monitors (experimental), `bin/` executables | see layout table in manifest reference | |
| userConfig, channels | in plugin.json | |

## Always-on context and path-scoped rules: NOT supported

- Manifest reference, "Standard layout": "A `CLAUDE.md` at the plugin root isn't loaded as context, and `claude plugin validate` warns when it finds one. To include instructions that load into Claude's context, put them in a skill." (https://code.claude.com/docs/en/plugins/manifest-reference)
- Components page: "Claude Code doesn't load a `CLAUDE.md` at the plugin root" (warning text: `CLAUDE.md at the plugin root is not loaded as project context`).
- No `rules/` component exists in the plugin layout. `.claude/rules/*.md` with `paths:` frontmatter (https://code.claude.com/docs/en/memory#path-specific-rules) is a project/user-level feature; the docs do not say plugins can contribute to it.
- Closest official features: (a) skills — name+description always in context, body loads on use; `paths:` makes a skill auto-activate only for matching files (activation hint, not forced injection); (b) hooks that return `additionalContext`.
- Conclusion: always-on charter and path-scoped rule injection need hooks. See `plugins/v1rus-core/hooks/v1rus_rules.py`.

## Hooks facts used by the engine

Source: https://code.claude.com/docs/en/hooks
- SessionStart stdin: `session_id`, `cwd`, `hook_event_name`, `source` (`startup|resume|clear|compact|fork`). Output `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}` puts text at the start of the conversation. Plain stdout with exit 0 is also added as context.
- PreToolUse stdin: `tool_name`, `tool_input` (Write/Edit use `file_path`), `tool_use_id`. `additionalContext` is supported for PreToolUse and appears next to the tool result. Docs advise phrasing context as facts rather than imperative system instructions.
- Exit 0 = success (stdout parsed as JSON); exit 2 = blocks PreToolUse; other codes = non-blocking error. A timed-out PreToolUse hook does not block unless `onFailure: "block"`.
- Env exported to hook processes: `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_OPTION_<KEY>`. Variables are NOT present in Bash-tool commands. `${CLAUDE_PLUGIN_ROOT}` resolves in hook `command`/`args` and in skill/agent Markdown bodies.
- `${CLAUDE_PLUGIN_ROOT}` changes on every plugin update; `${CLAUDE_PLUGIN_DATA}` (`~/.claude/plugins/data/<id>/`) survives updates.

## Subagent identity in hook input

Source: https://code.claude.com/docs/en/hooks (Common input fields), fetched 2026-10-18.
- `agent_id` ("Unique identifier for the subagent or in-process teammate the hook fires in") and `agent_type` are common input fields. PreToolUse/PostToolUse fire inside subagents with the same configured hooks, and the input carries `agent_id`/`agent_type`. Absent in the main conversation (unless `--agent`, which sets only `agent_type`).
- The docs do not say whether a subagent shares the parent `session_id`; the engine does not rely on it either way.
- Engine choice: once-per-session dedup state is keyed by `session_id` + `agent_id` when present, so every subagent (own context) receives each rule once on its own first matching edit. SessionStart (non-resume) clears the main state and all `<session>__agent_*` states. Empty `session_id` = no dedup (rules inject on every match) instead of a shared persistent state.
- Not verified: that PreToolUse `additionalContext` lands in the subagent's own context (docs imply the agent whose call fired the hook, not stated explicitly).

## Path-scoped rule semantics (mirrored by the engine)

Source: https://code.claude.com/docs/en/memory#path-specific-rules
- `paths` accepts a YAML list or comma-separated string; globs like `**/*.ts`, `src/**/*`, `*.md` (root only); brace expansion `{ts,tsx}`.
- Only Read/Write/Edit (and single-file Bash reads) trigger native path rules. The v1rus engine triggers on Write/Edit/MultiEdit/NotebookEdit only (PreToolUse), by design.

## Manifest, marketplace, dependencies

Sources: manifest-reference, https://code.claude.com/docs/en/plugins/marketplace-reference, https://code.claude.com/docs/en/plugins/dependencies
- plugin.json: only `name` required. `dependencies` is an array of `"name"`, `"name@marketplace"`, or `{name, marketplace?, version?}`; bare names resolve in the same marketplace; no version = tracks the marketplace's current copy. `version` as semver range resolves against git tags `<plugin>--v<version>` (`claude plugin tag`).
- Setting `version` pins the plugin: users stay on that version until it changes (https://code.claude.com/docs/en/plugins/loading#versions-and-updates). Hence the bump-on-change rule in this repo.
- Unknown top-level plugin.json keys are stripped with a validate warning; `--strict` turns warnings into failures. Missing `version`/`description`/`author` also warn.
- marketplace.json: required `name`, `owner{name}`, `plugins[]`; entry requires `name`, `source` (relative path must start with `./`, no `..`); optional `description`, `version`, `category`, `tags`, `strict`, `dependencies`. Marketplace `description` missing => warning. When `plugin.json` and entry both set `version`, plugin.json wins.
- Plugin names starting `claude-`/`anthropic-` etc. are rejected; `v1rus-*` is fine. Marketplace name `v1rus-dev` is not reserved.
- Local marketplace (directory source): files are read in place, edits apply on next session start or `/reload-plugins` with no version change. Hosted (git) installs use a cache copy keyed by version (cache layout observed: `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`), so a plugin cannot assume sibling plugins at a fixed relative path.
- Local dev with dependencies: `claude --plugin-dir ./plugins/v1rus-core --plugin-dir ./plugins/v1rus-kotlin` (local copy satisfies the dependency).

## CLI

`claude plugin validate <path> [--json] [--strict]` validates a plugin, a marketplace, or a directory of skills/agents/commands. Other subcommands: install, update, enable/disable, details, tag, list, prune, marketplace, eval.

## Not verified

- End-to-end behaviour of the hook engine inside a live Claude Code session (hooks were tested by piping JSON on stdin and by `claude plugin validate`, not in an interactive session).
- Whether `additionalContext` from PreToolUse is shown to the model before or after the edit executes (docs say "next to the tool result").
- Exact Write/Edit `tool_input` schema (truncated in fetched docs); `file_path` is assumed from doc examples, `notebook_path` for NotebookEdit from tool conventions.
- Behaviour of several enabled plugins each injecting `additionalContext` for the same PreToolUse event (assumed concatenated).
- Whether `claude plugin install` of a marketplace entry with relative path copies only the plugin directory (assumed; engine does not depend on it).
