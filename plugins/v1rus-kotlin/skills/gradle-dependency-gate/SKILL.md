---
name: gradle-dependency-gate
description: |-
  Plan-stage gate for adding a NEW dependency or Gradle plugin, or BUMPING an existing one, in a Gradle/Maven project: identity, freshness, vulnerabilities, API study, plus changelog for major bumps. Use before editing libs.versions.toml, build.gradle*, pom.xml, or when a task needs a library that is not yet in the project.
  Not for: writing code with a library that is already a dependency (kotlin-api-verification), version-conflict or BOM-alignment problems (build-engineer), or a broader adopt/avoid judgement of an unfamiliar library (use the dependency-evaluation skill if present, else research its health manually).
---

# Dependency gate

A dependency change is a plan-stage decision, not an implementation detail. Implementation must not start, and the catalog must not be edited, until the plan contains all of the following for each coordinate. Without explicit user approval nothing is added.

1. Identity: exact `group:artifact` (or plugin id) and its role in one line: what it does, why it is needed, why existing dependencies do not cover it.
2. Freshness: the latest stable version from a dependency-intelligence tool (for example maven-mcp latest-version, or the registry's own lookup). If the latest is a pre-release and a stable exists, pick stable and note the gap. Never pin a version because a snippet, blog post or memory said so.
3. Vulnerabilities: scan the chosen coordinate (maven-mcp vulnerability check / OSV). Any advisory stops the plan: report severity, advisory id and fixed-in version, propose an alternative or wait. "No advisories" is also a valid result: state it.
4. API study: read the real library with `ksrc` on the resolved version (plus official docs; for Android also the Android docs). The plan shows the integration uses the current API. For a major-version bump or an evolving library, also fetch the changelog between old and new version and list breaking changes.

For ecosystems other than Maven name the scanner explicitly (`npm audit`, `pip-audit`, `cargo audit`); the four outputs are mandatory regardless of stack.

At implementation time only confirm the resolved version still matches the plan and make the edit; if freshness needs re-checking, report back instead of silently swapping versions. See `${CLAUDE_PLUGIN_ROOT}/rules/gradle-build.md` for catalog and configuration conventions.
