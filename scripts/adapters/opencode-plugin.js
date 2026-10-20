// v1rus OpenCode plugin: thin bridge to the Claude Code hooks shipped with the v1rus plugins.
// Pure ESM, no dependencies, no build step. Generated layout (see scripts/build-targets.py):
//   <config>/plugins/v1rus.js        this file
//   <config>/v1rus/<plugin>/hooks/   unmodified hook scripts (git-guard, secrets-guard, path-rules, ...)
//   <config>/v1rus/<plugin>/rules/   path-scoped rules read by that plugin's path-rules.py
//
// The hooks speak the Claude Code protocol (JSON on stdin; exit 2 + stderr = deny;
// hookSpecificOutput.additionalContext = context to inject). This file only translates
// OpenCode tool calls into that protocol and the results back.
//
// Two OpenCode plugin APIs exist and one default export serves both:
//   V2 (opencode 2.x): reads `id` + `setup(ctx)`; ignores `server`. Hooks: ctx.tool.hook, ctx.session.hook.
//   V1 (opencode 1.x, object form needs >= 1.18.29): calls `server(input)` and uses the returned hooks.
// Rule injection: neither API can inject context BEFORE a tool call. V2 pushes the rule text into the
// system prompt of every following model call (session "context" hook); V1 appends it to the tool result.
import { spawnSync } from "node:child_process"
import { existsSync, readdirSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const DATA = resolve(dirname(fileURLToPath(import.meta.url)), "..", "v1rus")
const CORE = join(DATA, "v1rus-core", "hooks")
// Same grammar as scripts/adapters/codex_hook_adapter.py
const PATCH_PATH = /^\*\*\* (?:Update File|Add File|Delete File|Move to):[ \t]*(.+?)[ \t]*$/gm

function pluginDirsWithPathRules() {
  if (!existsSync(DATA)) return []
  return readdirSync(DATA, { withFileTypes: true })
    .filter((d) => d.isDirectory() && existsSync(join(DATA, d.name, "hooks", "path-rules.py")))
    .map((d) => join(DATA, d.name))
    .sort()
}

// OpenCode tool call -> Claude Code PreToolUse payload; null = not a tool the hooks care about.
function toClaude(tool, args) {
  args = args ?? {}
  switch (String(tool).toLowerCase()) {
    case "bash":
    case "shell": // V2 name of the bash tool
      return { tool_name: "Bash", tool_input: { command: args.command ?? "" } }
    case "read":
      return { tool_name: "Read", tool_input: { file_path: args.filePath ?? args.path } }
    case "edit":
    case "multiedit":
      return { tool_name: "Edit", tool_input: { file_path: args.filePath ?? args.path } }
    case "write":
      return { tool_name: "Write", tool_input: { file_path: args.filePath ?? args.path } }
    case "apply_patch":
    case "patch": {
      const text = String(args.patchText ?? args.patch ?? args.input ?? args.command ?? "")
      const paths = [...new Set([...text.matchAll(PATCH_PATH)].map((m) => m[1]))]
      if (!paths.length) return null
      return { tool_name: "Edit", tool_input: { file_path: paths[0], edits: paths.map((p) => ({ file_path: p })) } }
    }
    default:
      return null
  }
}


function createCore({ directory, warn }) {
  const projectDir = directory || process.cwd()
  const stateHome = process.env.XDG_STATE_HOME || join(homedir(), ".local", "state")
  const dataDir = join(stateHome, "opencode", "v1rus-data")

  function run(script, pluginDir, payload) {
    const result = spawnSync("python3", [script], {
      input: JSON.stringify({ cwd: projectDir, ...payload }),
      encoding: "utf8",
      timeout: 15000,
      cwd: projectDir,
      env: { ...process.env, CLAUDE_PLUGIN_ROOT: pluginDir, CLAUDE_PLUGIN_DATA: dataDir, CLAUDE_PROJECT_DIR: projectDir },
    })
    if (result.error) {
      // Fail open like Claude Code does for hook crashes; the hook is a guardrail, not a sandbox.
      warn(`v1rus hook ${script} could not run: ${result.error.message}`)
      return { status: 0, stdout: "", stderr: "" }
    }
    return result
  }

  function guard(script, pluginDir, payload) {
    const result = run(script, pluginDir, payload)
    if (result.status === 2) throw new Error((result.stderr || "blocked by a v1rus hook").trim())
  }

  return {
    // Throws to block the tool call. Returns rule texts (path-rules.py) that should reach the model.
    before(tool, args, sessionID) {
      const mapped = toClaude(tool, args)
      if (!mapped) return []
      const payload = { hook_event_name: "PreToolUse", session_id: sessionID, ...mapped }
      const core = join(DATA, "v1rus-core")
      const secrets = join(CORE, "secrets-guard.py")
      if (existsSync(secrets)) guard(secrets, core, payload)
      if (mapped.tool_name === "Bash") {
        const git = join(CORE, "git-guard.py")
        if (existsSync(git)) guard(git, core, payload)
        return []
      }
      if (mapped.tool_name === "Read") return []
      const chunks = []
      for (const dir of pluginDirsWithPathRules()) {
        const result = run(join(dir, "hooks", "path-rules.py"), dir, payload)
        if (result.status === 2) throw new Error((result.stderr || "blocked by a v1rus hook").trim())
        try {
          const text = JSON.parse(result.stdout || "{}")?.hookSpecificOutput?.additionalContext
          if (text) chunks.push(text)
        } catch {}
      }
      return chunks
    },

    // Analogue of Claude Code PreCompact: forget what was injected so rules return after compaction.
    reset(sessionID) {
      for (const dir of pluginDirsWithPathRules()) {
        run(join(dir, "hooks", "path-rules.py"), dir, { hook_event_name: "PreCompact", session_id: sessionID })
      }
    },
  }
}

export default {
  id: "v1rus",

  // OpenCode V2
  async setup(ctx) {
    const core = createCore({ directory: ctx.location?.directory, warn: (m) => console.warn(m) })
    const rules = new Map() // sessionID -> rule texts already delivered once by path-rules.py
    await ctx.tool.hook("execute.before", (event) => {
      const chunks = core.before(event.tool, event.input, event.sessionID)
      if (chunks.length) rules.set(event.sessionID, [...(rules.get(event.sessionID) ?? []), ...chunks])
    })
    await ctx.session.hook("context", (event) => {
      for (const text of rules.get(event.sessionID) ?? []) event.system.push({ type: "text", text })
    })
    await ctx.session.hook("compaction", (event) => {
      rules.delete(event.sessionID)
      core.reset(event.sessionID)
    })
  },

  // OpenCode V1 (docs-based; not run against a V1 binary)
  async server({ directory, worktree, client }) {
    const core = createCore({
      directory: worktree || directory,
      warn: (message) => {
        try {
          client?.app?.log?.({ body: { service: "v1rus", level: "warn", message } })
        } catch {}
      },
    })
    const pending = new Map() // callID -> rule text appended to that tool's result
    return {
      "tool.execute.before": async (input, output) => {
        const chunks = core.before(input.tool, output?.args, input.sessionID)
        if (chunks.length) pending.set(input.callID, chunks.join("\n\n"))
      },
      "tool.execute.after": async (input, output) => {
        const text = pending.get(input.callID)
        if (!text) return
        pending.delete(input.callID)
        output.output = `${output.output ?? ""}\n\n${text}`
      },
      "experimental.session.compacting": async (input) => core.reset(input.sessionID),
      event: async ({ event }) => {
        if (event?.type === "session.compacted") core.reset(event.properties?.sessionID)
      },
    }
  },
}
