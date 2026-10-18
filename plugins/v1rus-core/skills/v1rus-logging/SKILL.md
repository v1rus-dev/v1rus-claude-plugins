---
name: v1rus-logging
description: |-
  Logging policy: use the project's logger (never println/console.log), permanent log levels, temporary diagnostic logs marked TEMP-LOG and removed before finalizing, and what must never be logged (secrets, PII, payment data).
  Load when adding, reviewing or removing logs, debugging with instrumentation, or when a diff contains TEMP-LOG or raw print calls.
  Do NOT use for: shell scripts or CLI programs whose stdout is the product output.
---

# v1rus logging

Rulebook (also injected on the first source-file edit of a session): `${CLAUDE_PLUGIN_ROOT}/rules/logging.md`

Before the quality gate, scan the diff for `TEMP-LOG`; any hit blocks.
