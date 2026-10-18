#!/usr/bin/env python3
"""PreToolUse hook: programmatic backstop against touching secrets and exfiltrating them.

Deliberately overlaps whatever `permissions.deny` a project configures. settings.json is the
declarative gate; this hook is the backstop and the only layer that also screens Bash
commands. Do not "dedupe" by dropping either side.

Projects add their own secret files (a service-account json, an auth config) through
`permissions.deny` in the project's `.claude/settings.json` — this hook covers the patterns
that are secrets everywhere.
"""

import json
import re
import sys

BLOCKED_PATHS = [
    r"(^|[/\\])\.env(\.|$)",
    r"(^|[/\\])\.git[/\\]",
    r"(^|[/\\])node_modules[/\\]",
    r"(^|[/\\])\.ssh[/\\]",
    r"(^|[/\\])\.aws[/\\]",
    r"(^|[/\\])\.gnupg[/\\]",
    r"id_rsa$|id_ed25519$|\.pem$|\.p12$|\.jks$|\.keystore$",
    r"(^|[/\\])secrets[/\\]",
    r"credentials\.json$",
    r"local\.properties$",
    r"(^|[/\\])fastlane[/\\].*[Mm]atch",
    r"google-services\.json$|GoogleService-Info\.plist$",
]

BLOCKED_BASH = [
    r"curl\s+.*\|\s*(bash|sh|zsh|python|python3)",
    r"wget\s+.*\|\s*(bash|sh|zsh|python|python3)",
    r"\bcat\b[^|;&]*\.env\b",
    r"\bcp\b[^|;&]*\.env\b[^|;&]*\b(tmp|var|http|ftp)",
    r"\bscp\b",
    r">\s*/dev/tcp/",
    r"\bgit\b[^|;&]*\bpush\b[^|;&]*\bhttps?://[^\s@]+:[^\s@]+@",
]


def blocked(value: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        if re.search(pattern, value, re.IGNORECASE):
            return pattern
    return None


def deny(message: str) -> None:
    print(f"BLOCKED by v1rus-core: {message}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    if tool in ("Read", "Write", "Edit", "MultiEdit", "NotebookEdit"):
        candidates = []
        single = tool_input.get("file_path") or tool_input.get("filePath")
        if single:
            candidates.append(single)
        for edit in tool_input.get("edits", []) or []:
            nested = edit.get("file_path") or edit.get("filePath")
            if nested:
                candidates.append(nested)
        for path in candidates:
            if blocked(path, BLOCKED_PATHS):
                deny(f"access to '{path}' is denied by the v1rus security policy.")

    if tool == "Bash":
        command = tool_input.get("command", "")
        if command and blocked(command, BLOCKED_BASH):
            deny(f"potentially dangerous or exfiltrating command: {command[:120]}")

    sys.exit(0)


if __name__ == "__main__":
    main()
