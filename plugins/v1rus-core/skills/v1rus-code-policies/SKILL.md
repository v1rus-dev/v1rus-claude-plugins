---
name: v1rus-code-policies
description: |-
  Code policies: mandatory inline comments (preserved migration behavior, retained quirks, non-obvious constraints, implicit semantic changes), doc updates, feature-flag and config rules, breaking changes, architectural-decision handling, legacy code and minimal-diff discipline.
  Load when modifying existing code, migrating behavior, touching legacy code, or unsure whether to refactor or add a flag.
  Do NOT use for: logging (v1rus-logging) or dependency changes (v1rus-dependencies).
---

# v1rus code policies

Rulebook (also injected on the first source-file edit of a session): `${CLAUDE_PLUGIN_ROOT}/rules/code-policies.md`

Key habits: minimal diff, comment the surprising fact, update docs with code, no proactive feature flags, notify before public-API/schema/CLI breaking changes.
