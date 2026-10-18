---
paths:
  - "**/{build.gradle,build.gradle.kts,settings.gradle,settings.gradle.kts,libs.versions.toml,pom.xml}"
  - "**/{package.json,Cargo.toml,go.mod,pyproject.toml,requirements*.txt,Package.swift,Podfile}"
---

# Dependencies

Never add a new dependency without explicit owner approval. Prefer what the project already has. If a new dependency is the only reasonable option, propose it and wait for the go-ahead.

Adding a new dependency or plugin, or bumping an existing one, is a **plan-stage decision**. The plan is not final, and implementation does not start, until the library is studied and the version verified. This covers build plugins on equal footing with libraries (plugin id, version, source repository).

## Four outputs the plan must contain

1. **Identity.** Exact coordinate (`groupId:artifactId`, plugin id, or `name@registry`) plus its role: what it does, why it is needed, why existing dependencies do not cover it.
2. **Freshness.** Latest stable version, resolved with a tool (a Maven dependency-intelligence tool when connected; otherwise `npm view <pkg> version`, `pip index versions`, `cargo search`, `go list -m -versions`, the registry page). Write "latest stable: X.Y.Z". If the latest is a pre-release and stable is older, pick stable and note the gap. Never pin a version because it appeared in a snippet, blog post or memory.
3. **Vulnerabilities.** Run an advisory scan on the chosen coordinate (OSV via the Maven tool, `npm audit`, `pip-audit`, `cargo audit`, `govulncheck`). Any CVE/GHSA hit stops the plan: report severity, advisory id and fixed-in version, propose a safe alternative or wait for the owner. "No advisories" is also a valid output; state it.
4. **API surface study.** Read the actual library at the resolved version (source jar, installed package source, official docs of that version), so the integration uses the current API, not a memorized signature. For a bump across a major version or a fast-moving library, also read the changelog between old and new and surface breaking changes in the plan.

Missing any of the four: the plan is not ready.

## Implementation stage

When the build file is edited, the version is already approved. Confirm the resolved version still matches the plan and write the edit. Do not silently swap versions; if the freshness check needs re-running, report back instead.

If no ecosystem tool exists for the stack, name the scanner you use in the plan. Never skip a check silently because the usual tool is the wrong one.

For deciding whether a library is worth adopting at all, use the `evaluate-dependency` skill.
