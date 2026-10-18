---
name: v1rus-code-search
description: |-
  Code navigation rules: symbol index first for finding symbols, usages, implementors and callers; LSP for type-aware answers; Grep only for regex, literals, comments and configs; outline before reading large files.
  Load when starting an investigation across a codebase or unsure which search tool to use.
  Do NOT use for: reading external library docs (v1rus-sources).
---

# v1rus code search

Reference: `${CLAUDE_PLUGIN_ROOT}/skills/v1rus-code-search/reference/code-search.md`

Short form: never Grep for a symbol by name when an index exists; outline a large file before reading it.
