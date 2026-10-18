#!/usr/bin/env python3
"""v1rus rules engine: always-on charter + path-scoped rules for a Claude Code plugin.

Claude Code plugins cannot ship CLAUDE.md or .claude/rules (see docs/PLUGIN-SPEC-NOTES.md),
so each v1rus-* plugin carries this file and calls it from its own hooks/hooks.json
with its own ${CLAUDE_PLUGIN_ROOT}. The canonical copy lives in plugins/v1rus-core/hooks/;
`python3 scripts/sync-engine.py` copies it into every other plugin (check-plugins.py
fails when a copy drifts).

Modes (first argv):
  session-start  stdin: SessionStart event. Injects <root>/charter.md as additionalContext.
  path-rules     stdin: PreToolUse event.   On Write/Edit of a file matching `paths:` globs in
                 <root>/rules/*.md frontmatter, injects that rule once per session per agent
                 (state keyed by session_id + `agent_id` for subagents; empty session_id = no dedup).

Contract: stdlib only, never blocks, fails open (any error -> exit 0, no output).
"""
import json
import os
import re
import sys
import tempfile
import time

EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
STATE_TTL_SECONDS = 7 * 24 * 3600
MAX_BRACE_EXPANSION = 1000


def read_event():
    try:
        data = json.loads(sys.stdin.read() or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def plugin_root():
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root:
        return root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def plugin_name(root):
    try:
        with open(os.path.join(root, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            return json.load(f).get("name") or os.path.basename(root)
    except Exception:
        return os.path.basename(root)


def split_frontmatter(text):
    """Return (frontmatter_text, body). No frontmatter -> ('', text)."""
    if text.startswith("---\n") or text.startswith("---\r\n"):
        m = re.match(r"---\r?\n(.*?)\r?\n---[ \t]*\r?\n?(.*)\Z", text, re.S)
        if m:
            return m.group(1), m.group(2)
    return "", text


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse_paths(frontmatter):
    """Extract `paths:` as a list of globs. Accepts YAML list, inline list, or comma string."""
    lines = frontmatter.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"paths\s*:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1).strip()
        if rest.startswith("[") and rest.endswith("]"):
            return [_unquote(x) for x in rest[1:-1].split(",") if x.strip()]
        if rest:
            return [_unquote(x) for x in rest.split(",") if x.strip()]
        out = []
        for nxt in lines[i + 1:]:
            lm = re.match(r"\s*-\s*(.+?)\s*$", nxt)
            if lm:
                out.append(_unquote(lm.group(1)))
            elif nxt.strip() == "" or nxt.lstrip().startswith("#"):
                continue
            else:
                break
        return out
    return []


def expand_braces(pattern):
    """Expand every {a,b} group (nesting supported). A group without a comma is a literal
    brace pair: it is kept as text and the remaining groups are still expanded.
    Returns [pattern] unexpanded if over budget."""
    done, todo = [], [pattern]
    while todo:
        p = todo.pop()
        pos = 0
        while True:
            m = re.compile(r"\{([^{}]*)\}").search(p, pos)
            if not m:
                done.append(p)
                break
            if "," in m.group(1):
                for alt in m.group(1).split(","):
                    todo.append(p[:m.start()] + alt + p[m.end():])
                break
            pos = m.end()  # literal braces: skip, keep scanning for further groups
        if len(done) + len(todo) > MAX_BRACE_EXPANSION:
            return [pattern]
    return sorted(set(done))


def glob_to_regex(pattern):
    """Glob -> regex over '/'-separated relative paths. `**` crosses dirs, `*` and `?` do not."""
    i, n, out = 0, len(pattern), []
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern[i:i + 2] == "**":
                i += 2
                if pattern[i:i + 1] == "/":
                    i += 1
                    out.append("(?:.*/)?")
                else:
                    out.append(".*")
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "[":
            j = pattern.find("]", i + 2)
            if j == -1:
                out.append(re.escape(c))
            else:
                body = pattern[i + 1:j]
                if body.startswith("!"):
                    body = "^" + body[1:]
                out.append("[" + body.replace("\\", "\\\\") + "]")
                i = j
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def matches(globs, rel_path):
    for g in globs:
        g = g.lstrip("/")
        if g.startswith("./"):
            g = g[2:]
        for expanded in expand_braces(g):
            try:
                if glob_to_regex(expanded).match(rel_path):
                    return True
            except re.error:
                continue
    return False


def relative_path(file_path, event):
    base = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    if not os.path.isabs(file_path):
        file_path = os.path.join(base, file_path)
    file_path = os.path.normpath(file_path)
    base = os.path.normpath(base)
    rel = os.path.relpath(file_path, base).replace(os.sep, "/")
    if rel == ".." or rel.startswith("../"):
        return None  # outside the project root: relative globs must not match
    return rel


def state_key(session_id, agent_id=None):
    """Dedup key. Subagent tool calls carry `agent_id` (hooks docs) and run with their own
    context, so each agent dedups on its own. Empty session_id -> None (no dedup)."""
    if not session_id:
        return None
    key = str(session_id)
    if agent_id:
        key += "__agent_" + str(agent_id)
    return re.sub(r"[^A-Za-z0-9_-]", "_", key)


def state_dir(root):
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    base = os.path.join(data, "state") if data else os.path.join(tempfile.gettempdir(), "v1rus-rules-" + str(os.getuid() if hasattr(os, "getuid") else 0), plugin_name(root))
    os.makedirs(base, exist_ok=True)
    return base


def state_path(root, session_id, agent_id=None):
    key = state_key(session_id, agent_id)
    if key is None:
        return None
    return os.path.join(state_dir(root), key + ".json")


def prune_state(d):
    now = time.time()
    for name in os.listdir(d):
        p = os.path.join(d, name)
        try:
            if name.endswith(".json") and now - os.path.getmtime(p) > STATE_TTL_SECONDS:
                os.remove(p)
        except OSError:
            pass


def load_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except Exception:
        return set()


def save_state(path, seen):
    tmp = "%s.%d.%s.tmp" % (path, os.getpid(), os.urandom(4).hex())  # unique: parallel edits don't race
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(sorted(seen), f)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def emit(event_name, text):
    sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": text}}))


def session_start(event):
    root = plugin_root()
    # Rule dedup state: keep on resume (context survives); reset on startup/clear/compact (context lost).
    try:
        d = state_dir(root)
        key = state_key(event.get("session_id", ""))
        if key and event.get("source") != "resume":
            for name in os.listdir(d):  # main-agent state plus all subagent states of this session
                if name == key + ".json" or name.startswith(key + "__agent_"):
                    os.remove(os.path.join(d, name))
        prune_state(d)
    except Exception:
        pass
    charter = os.path.join(root, "charter.md")
    if not os.path.isfile(charter):
        return
    with open(charter, encoding="utf-8") as f:
        _, body = split_frontmatter(f.read())
    body = body.strip()
    if body:
        emit("SessionStart", "[%s charter]\n%s" % (plugin_name(root), body))


def path_rules(event):
    if event.get("tool_name") not in EDIT_TOOLS:
        return
    tin = event.get("tool_input") or {}
    file_path = tin.get("file_path") or tin.get("notebook_path")
    if not file_path:
        return
    root = plugin_root()
    rules_dir = os.path.join(root, "rules")
    if not os.path.isdir(rules_dir):
        return
    rel = relative_path(file_path, event)
    if rel is None:
        return
    sp = state_path(root, event.get("session_id", ""), event.get("agent_id"))
    # Empty session_id: no dedup (inject on every match) rather than a shared persistent state.
    seen = load_state(sp) if sp else set()
    chunks = []
    for name in sorted(os.listdir(rules_dir)):
        if not name.endswith(".md") or name in seen:
            continue
        try:
            with open(os.path.join(rules_dir, name), encoding="utf-8") as f:
                fm, body = split_frontmatter(f.read())
        except Exception:
            continue  # unreadable / non-UTF8 rule must not abort the others
        globs = parse_paths(fm)
        if globs and body.strip() and matches(globs, rel):
            seen.add(name)
            chunks.append("[%s rule: %s]\n%s" % (plugin_name(root), name, body.strip()))
    if chunks:
        if sp:
            try:
                save_state(sp, seen)
            except Exception:
                pass  # state is best-effort; still emit
        emit("PreToolUse", "\n\n".join(chunks))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    event = read_event()
    if mode == "session-start":
        session_start(event)
    elif mode == "path-rules":
        path_rules(event)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: a broken rules engine must never block a session or a tool call
    sys.exit(0)
