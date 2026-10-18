#!/usr/bin/env python3
"""PreToolUse(Bash) hook: enforce the non-negotiables that are shell-command shaped.

Four rules from the v1rus charter, blocked here instead of merely stated:

1. No `sudo` / root escalation — an agent session has no TTY, the call fails anyway, and
   repeated failures can trip pam_faillock and lock the developer out of their account.
2. No git-hook bypass (`--no-verify`, `--no-gpg-sign`, `commit.gpgsign=false`).
3. No plain `--force` push — `--force-with-lease` / `--force-if-includes` only.
4. No commit or push from a protected branch (main / master / develop).

Escape hatch for the rare repo that legitimately commits on its default branch (docs, wiki):
set V1RUS_ALLOW_PROTECTED_BRANCH=1.
"""

import json
import os
import re
import subprocess
import sys

PROTECTED = {"main", "master", "develop", "dev", "development"}

# `sudo` as an actual command word: start of line, or after a shell separator.
SUDO = re.compile(r"(?:^|[;&|(]|&&|\|\|)\s*(?:sudo|doas|pkexec)\b")
BYPASS = re.compile(r"--no-verify\b|--no-gpg-sign\b|commit\.gpgsign\s*=\s*false", re.IGNORECASE)
GIT_PUSH = re.compile(r"\bgit\b(?:\s+-[^\s]+|\s+--[^\s]+(?:=\S+)?)*\s+push\b")
GIT_COMMIT = re.compile(r"\bgit\b(?:\s+-[^\s]+|\s+--[^\s]+(?:=\S+)?)*\s+commit\b")
SAFE_FORCE = re.compile(r"--force-with-lease\b|--force-if-includes\b")
PLAIN_FORCE = re.compile(r"--force\b(?!-with-lease|-if-includes)|(?<![\w-])-f\b")


def deny(message: str) -> None:
    print(f"BLOCKED by v1rus-core: {message}", file=sys.stderr)
    sys.exit(2)


def current_branch() -> str:
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "branch", "--show-current"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = (data.get("tool_input", {}) or {}).get("command", "")
    if not command:
        sys.exit(0)

    if SUDO.search(command):
        deny(
            "root escalation. This session has no TTY for a password prompt, so the call fails "
            "and repeated failures can lock the developer's account. Hand the exact command to "
            "the developer to run in their own terminal, and continue with the rest of the task."
        )

    if BYPASS.search(command):
        deny(
            "git-hook bypass. A failing hook is a root cause to fix, not something to route "
            "around. Investigate the hook failure instead."
        )

    is_push = bool(GIT_PUSH.search(command))
    is_commit = bool(GIT_COMMIT.search(command))

    if is_push and PLAIN_FORCE.search(command) and not SAFE_FORCE.search(command):
        deny("plain `--force` push. Use `--force-with-lease` (or `--force-if-includes`).")

    if (is_push or is_commit) and not os.environ.get("V1RUS_ALLOW_PROTECTED_BRANCH"):
        branch = current_branch()
        if branch in PROTECTED:
            verb = "push" if is_push else "commit"
            deny(
                f"{verb} from the protected branch '{branch}'. Create a feature branch first. "
                "(If this repo genuinely works on its default branch, the developer can set "
                "V1RUS_ALLOW_PROTECTED_BRANCH=1.)"
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
