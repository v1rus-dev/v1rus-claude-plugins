---
paths:
  - "**/*.{kt,kts,java,swift,m,mm,js,jsx,ts,tsx,py,go,rs,cs,c,cc,cpp,h,hpp,rb,php}"
---

# Code policies

## Comments and docs

When code changes, update directly related docs (KDoc/docstrings, inline comments, `.md` files). Never leave docs describing something the code no longer does.

Add a short inline comment (one or two lines, surprising fact first, then the reason) when the code contains:
- **Preserved behavior from a migration**: what the old code did and why the new code matches it (old API used the system timezone, callers rely on a missing null-check).
- **Intentionally retained bug or quirk**: what the bug is and why it stays (compat, spec compliance, fixing breaks something else).
- **Non-obvious constraint**: looks wrong but is correct because of an external contract, hardware quirk, server format, third-party library or platform limit.
- **Implicit semantic change**: logic looks equivalent but differs in edge cases (overflow, timezone, locale, rounding, encoding); say what differs and why it is acceptable.

No task or PR references in comments.

## Logging

Logging policy (logger choice, levels, temporary diagnostic logs, redaction) lives in the `v1rus-logging` skill.

## Feature flags and configuration

- Never add a feature flag proactively: that is a product decision. If the task clearly implies one, ask first.
- Configuration: follow the project's existing pattern; if none, use a dedicated config layer, no hardcoded values.

## Breaking changes

Make the change directly; backward compatibility and migration are the owner's responsibility unless asked. For public API, DB schema or CLI interface changes, notify the owner before proceeding.

## Architectural decisions

When several approaches are possible: (1) match the existing project pattern if clear; (2) no clear pattern: present options with trade-offs, recommend one, proceed; (3) no signal at all: apply best practices. Never silently pick when alternatives exist.

## Legacy code and minimal diff

- Do not change code outside the task's scope unless it is a direct blocker.
- A legacy pattern that works and does not conflict stays; note it in one line. New code nearby follows the current project standard, not the legacy style.
- Refactor legacy code only when it actively blocks the task or mixing styles creates inconsistency, and explain why.
- Targeted fixes touch only what the task requires: no renames, no added validation, no restructuring or modernizing "for clarity". Structural improvements go into a separate refactor with the owner's consent.
