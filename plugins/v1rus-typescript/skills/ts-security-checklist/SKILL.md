---
name: ts-security-checklist
description: |-
  Use when writing or reviewing TypeScript/JavaScript that touches user input, regular expressions, merging of untrusted objects, child processes, file paths, crypto or secrets; feeds the security-expert review.
  Do NOT use for general code review or non-security style issues.
---

# Security checklist (JS/TS)

Apply the security section of `${CLAUDE_PLUGIN_ROOT}/rules/ts-boundaries.md`, then walk `${CLAUDE_PLUGIN_ROOT}/skills/ts-security-checklist/reference/checklist.md`. Report findings with file and line; policy choices (algorithms, key management, auth model) are escalated to the user, not decided. For a deep review hand the diff to the `security-expert` agent.
