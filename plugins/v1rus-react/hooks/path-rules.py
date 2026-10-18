#!/usr/bin/env python3
"""PreToolUse hook: deliver path-scoped rules that a plugin otherwise cannot ship.

Claude Code supports `.claude/rules/*.md` with a `paths:` frontmatter glob list, loaded
lazily when a matching file enters context. Plugins have no equivalent component, so this
hook reproduces the behaviour: before an edit, every rule in this plugin's `rules/`
directory whose `paths:` globs match the target file is injected as `additionalContext`.

A rule body is injected at most once per session — after that it is already in context and
re-sending it is waste. `PreCompact` clears the marker, so the rules come back after a
compaction drops them.

Each v1rus plugin layer ships its own copy of this script and its own `rules/` directory
on purpose: `${CLAUDE_PLUGIN_ROOT}` resolves per plugin, so a layer cannot read a sibling's
rules, and keeping the copies independent means each layer installs and works alone.
"""

import fnmatch
import hashlib
import json
import os
import re
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_DIR = os.path.join(PLUGIN_ROOT, "rules")
PLUGIN_NAME = os.path.basename(PLUGIN_ROOT)

FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def state_dir() -> str:
    """Where the per-session 'already injected' markers live.

    CLAUDE_PLUGIN_DATA survives plugin updates and is the documented place for this;
    fall back to a temp dir so the hook still works if it is unset.
    """
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(
        os.environ.get("TMPDIR", "/tmp"), f"{PLUGIN_NAME}-rules"
    )
    return os.path.join(base, "injected")


def parse_paths(text: str) -> list[str]:
    """Extract the `paths:` glob list from a rule's YAML frontmatter.

    Deliberately a small hand-rolled reader instead of PyYAML: hooks must run on a bare
    python3 with no site-packages.
    """
    match = FRONTMATTER.match(text)
    if not match:
        return []
    globs: list[str] = []
    in_paths = False
    for raw in match.group(1).splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if re.match(r"^paths:\s*$", line):
            in_paths = True
            continue
        if in_paths:
            item = re.match(r"^\s*-\s*(.+?)\s*$", line)
            if item:
                globs.append(item.group(1).strip().strip("\"'"))
                continue
            in_paths = False
        inline = re.match(r"^paths:\s*\[(.*)\]\s*$", line)
        if inline:
            globs.extend(p.strip().strip("\"'") for p in inline.group(1).split(",") if p.strip())
    return [g for g in globs if g]


def matches(path: str, globs: list[str]) -> bool:
    candidates = {path, path.lstrip("/")}
    normalised = path.replace(os.sep, "/")
    candidates.add(normalised)
    for glob in globs:
        for candidate in candidates:
            if fnmatch.fnmatch(candidate, glob):
                return True
            # "**/*.kt" should also match a bare relative "src/Foo.kt"
            if glob.startswith("**/") and fnmatch.fnmatch(candidate, glob[3:]):
                return True
    return False


def target_paths(tool_name: str, tool_input: dict) -> list[str]:
    paths = []
    single = tool_input.get("file_path") or tool_input.get("filePath")
    if single:
        paths.append(single)
    for edit in tool_input.get("edits", []) or []:
        nested = edit.get("file_path") or edit.get("filePath")
        if nested:
            paths.append(nested)
    return paths


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if data.get("hook_event_name") == "PreCompact":
        # Forget what was injected so the rules return after context is compacted.
        marker_dir = os.path.join(state_dir(), str(data.get("session_id", "unknown")))
        if os.path.isdir(marker_dir):
            for name in os.listdir(marker_dir):
                try:
                    os.remove(os.path.join(marker_dir, name))
                except OSError:
                    pass
        sys.exit(0)

    if not os.path.isdir(RULES_DIR):
        sys.exit(0)

    paths = target_paths(data.get("tool_name", ""), data.get("tool_input", {}) or {})
    if not paths:
        sys.exit(0)

    marker_dir = os.path.join(state_dir(), str(data.get("session_id", "unknown")))
    os.makedirs(marker_dir, exist_ok=True)

    chunks = []
    for name in sorted(os.listdir(RULES_DIR)):
        if not name.endswith(".md"):
            continue
        rule_path = os.path.join(RULES_DIR, name)
        try:
            with open(rule_path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            continue

        globs = parse_paths(text)
        if not globs or not any(matches(p, globs) for p in paths):
            continue

        marker = os.path.join(marker_dir, hashlib.sha1(name.encode()).hexdigest())
        if os.path.exists(marker):
            continue

        body = FRONTMATTER.sub("", text, count=1).strip()
        if not body:
            continue
        chunks.append(f"<!-- {PLUGIN_NAME}/rules/{name} — applies to the file being edited -->\n{body}")
        try:
            open(marker, "a").close()
        except OSError:
            pass

    if not chunks:
        sys.exit(0)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "\n\n".join(chunks),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
