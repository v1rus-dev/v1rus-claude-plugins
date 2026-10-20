#!/usr/bin/env python3
"""Codex -> Claude Code hook input adapter (stdlib only).

Usage (from a Codex hooks.json):  python3 codex-adapter.py <hook-script.py>

The v1rus hooks (git-guard, secrets-guard, path-rules) are written for Claude Code's
PreToolUse input: tool_name Bash/Edit/Write and tool_input.command / tool_input.file_path.
Codex reports file edits as tool_name "apply_patch" with the patch text in
tool_input.command. This adapter normalises that into the Claude shape and then runs the
original, unmodified hook next to it, forwarding stdout, stderr and the exit code.

Status: written from the Codex hooks documentation; NOT run against a real Codex binary.
The documented apply_patch shape is tool_input.command = patch text. The patch-text parse
below is therefore a best effort, and the parser is deliberately defensive: it also accepts
file_path / filePath / path, and patch text under command / patch / patchText / input / diff.
"""
import json
import os
import re
import subprocess
import sys

# apply_patch grammar: "*** Update File: path", "*** Add File: path", "*** Delete File: path",
# plus "*** Move to: path" for renames.
PATCH_PATH = re.compile(r"^\*\*\* (?:Update File|Add File|Delete File|Move to):[ \t]*(.+?)[ \t]*$", re.M)
PATH_KEYS = ("file_path", "filePath", "path")
PATCH_KEYS = ("command", "patch", "patchText", "input", "diff")
EDIT_TOOLS = {"apply_patch", "Edit", "Write", "MultiEdit"}


def extract_paths(tool_input):
    if not isinstance(tool_input, dict):
        return []
    found = []
    for key in PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            found.append(value)
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict):
            for key in PATH_KEYS:
                value = edit.get(key)
                if isinstance(value, str) and value:
                    found.append(value)
    for key in PATCH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and "***" in value:
            found.extend(PATCH_PATH.findall(value))
    seen, ordered = set(), []
    for path in found:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def normalize(data):
    if data.get("tool_name") not in EDIT_TOOLS:
        return data
    paths = extract_paths(data.get("tool_input"))
    if not paths:
        return data
    out = dict(data)
    out["tool_name"] = "Edit"
    out["tool_input"] = {"file_path": paths[0], "edits": [{"file_path": p} for p in paths]}
    return out


def main():
    if len(sys.argv) != 2 or os.path.basename(sys.argv[1]) != sys.argv[1]:
        print("usage: codex-adapter.py <hook-script-basename.py>", file=sys.stderr)
        sys.exit(1)
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, sys.argv[1])
    raw = sys.stdin.read()
    try:
        payload = json.dumps(normalize(json.loads(raw)))
    except (ValueError, TypeError):
        payload = raw  # not JSON: let the target decide (all v1rus hooks exit 0 on bad input)
    env = dict(os.environ)
    env.setdefault("CLAUDE_PLUGIN_ROOT", os.path.dirname(here))
    result = subprocess.run([sys.executable, target], input=payload, text=True, capture_output=True, env=env)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
