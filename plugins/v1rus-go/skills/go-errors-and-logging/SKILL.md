---
name: go-errors-and-logging
description: |-
  Design Go error types, wrapping, sentinel errors, error-to-status mapping, and slog log statements incl. redaction and levels.
  Use when: adding custom errors or %w wrapping, changing error flow across layers, adding or reviewing log calls, handling panics.
  Not for: choosing alerting/observability policy; non-Go logging.
---

Read the Errors and Logging sections of `${CLAUDE_PLUGIN_ROOT}/rules/go-core.md` and [reference/errors-logging.md](reference/errors-logging.md). Follow the project's logging policy from its CLAUDE.md if one exists; the global logging rules of the user still apply.
