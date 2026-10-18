---
name: jvm-dependency-intelligence
description: "How to establish ground truth about a JVM/Kotlin dependency instead of guessing: read the real source of the resolved version with ksrc rather than digging through the Gradle cache, resolve the latest stable version and check CVE/GHSA advisories through a Maven dependency-intelligence tool, and diff what actually changed between two versions before an upgrade. Load when you need a library's real API signature, when a version or changelog matters, before bumping a dependency in libs.versions.toml, or when a memorized signature might be stale."
---

# JVM Dependency Intelligence

Training data goes stale and the project's existing code shows only the slice of an API it happens to
use — often a legacy slice. Before writing code against a JVM/Kotlin library, or changing its version,
establish ground truth from the artifact itself.

## Reading the real API — `ksrc`

`ksrc` fetches and reads the actual source jar of the version the build resolves. It is **T1 ground
truth** (see the `v1rus-sources` skill): what the code in front of you can actually call.

- Run `ksrc --help` for the current syntax rather than guessing flags.
- Use it for: exact signatures, whether a symbol exists in *this* version, what a class actually does,
  and confirming a remembered API shape.
- Do **not** substitute a hand-search of `.gradle/` or `.m2/` — reading those directories is forbidden
  (see `v1rus-code-search`), and the jars there are compiled anyway.
- `ksrc` gives you source, not guidance. For "how is this meant to be used", pair it with the vendor's
  docs — the two channels answer different questions and are used together, not alternately.

## Versions, advisories and changelogs

When a Maven dependency-intelligence capability is available (a `maven-mcp`-style tool), use it for:

| Question | What to request |
|---|---|
| What is the latest stable version? | latest-version for the coordinate — never pin from a blog snippet or memory |
| Does the project have outdated deps? | a project-wide dependency scan across build files and submodules |
| Are there known CVEs / GHSAs? | a vulnerability check for the coordinate and version |
| What breaks if we upgrade? | a version-to-version change report between the current and target versions |
| Is this library maintained at all? | health signals — release cadence, last commit, archived flag, license |

If no such tool is connected, say so explicitly and fall back to the vendor's release notes and
repository — reduced confidence must be visible, not silent.

## When to use which

- Writing code against a library already in the build → `ksrc` (T1) **and** the vendor docs for the
  same version, in parallel.
- Bumping a version → latest-stable lookup + vulnerability check + a change report between the two
  versions, surfaced *in the plan* before the build file is edited (`v1rus-dependencies` skill).
- Considering a brand-new library → the `evaluate-dependency` skill, which drives this plus a verdict.
- Crossing a major version, or touching a fast-moving library (Ktor, Room, Compose, AGP, Hilt, Koin,
  kotlinx.*) → the change report is mandatory, not optional.

A signature you did not verify against T1 or the vendor's docs for the project's pinned version is a
hypothesis. Never treat it as fact, and never treat agent memory or an existing call site as a
substitute.
