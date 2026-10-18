#!/usr/bin/env python3
"""SessionStart hook: inject the v1rus engineering charter into context.

Plugins cannot ship CLAUDE.md — the plugin reference is explicit that a plugin-root
CLAUDE.md is not loaded as project context, and there is no `rules/` component either.
A SessionStart hook returning `additionalContext` is the supported way to make a
corporate baseline unconditionally present, so that is what this does.

The charter text lives next to this script in charter.md; editing that file is the only
thing needed to change the baseline.
"""

import json
import os
import sys

CHARTER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charter.md")


def main() -> None:
    # Consume stdin so the hook never blocks on an unread pipe.
    try:
        sys.stdin.read()
    except Exception:
        pass

    try:
        with open(CHARTER, encoding="utf-8") as handle:
            text = handle.read().strip()
    except OSError as exc:
        # A missing charter must not break the session — report and exit clean.
        print(f"v1rus-core: charter not loaded ({exc})", file=sys.stderr)
        sys.exit(0)

    if not text:
        sys.exit(0)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": text,
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
