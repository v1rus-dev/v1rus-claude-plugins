# Path-scoped rules

Files in this directory are injected into context by `hooks/path-rules.py` immediately before an
`Edit` / `Write` / `MultiEdit` touches a file matching the rule's `paths:` globs — the plugin
equivalent of Claude Code's `.claude/rules/*.md` mechanism, which plugins cannot use directly.

Format:

```markdown
---
paths:
  - "**/*.kt"
  - "**/*.kts"
---

# Rule title

…rule body, injected verbatim…
```

Rules:

- A rule body is injected **once per session** (and again after a compaction, which clears the
  marker). Keep bodies proportionate — a 10 KB body is fine once, but anything that would be
  re-read constantly belongs in a skill instead.
- Only use a path rule for guidance that is **worthless unless it arrives before the edit**.
  Everything a model can reasonably be expected to look up belongs in a skill, where it is loaded
  on demand and costs nothing when irrelevant.
- `README.md` and any file without a `paths:` list is ignored by the hook, so notes like this one
  are safe to keep here.

`v1rus-core` itself intentionally ships no path rules: its content is process and policy, which is
not file-type scoped. The Kotlin and KMP layers are where path rules earn their cost.
