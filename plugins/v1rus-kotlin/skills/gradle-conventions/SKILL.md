---
name: gradle-conventions
description: "v1rus Gradle build-script conventions: pick the narrowest dependency configuration (implementation by default, api only when a dependency's types appear in this module's public surface, compileOnly/runtimeOnly for plugin-classpath and host-provided cases), how to decide api vs implementation and why the cost of getting it wrong is asymmetric, new coordinates go into the version catalog rather than a module build script, and repeated configuration belongs in convention plugins. Load when editing build.gradle.kts, settings.gradle.kts, libs.versions.toml, a convention plugin, or when adding a dependency to a module."
---

# Gradle Conventions

The full rulebook is `${CLAUDE_PLUGIN_ROOT}/rules/gradle-style.md` — **read it** before editing a
build script. The same file is injected by the `path-rules` hook on any `*.gradle.kts`, `*.gradle`
or `libs.versions.toml` edit.

The load-bearing rule: **`implementation` by default, `api` only when the dependency's types appear
in this module's public surface.** Tightening `api` → `implementation` later is a breaking change for
every consumer that relied on the leak; widening the other way is trivial. When unsure, pick
`implementation` and let a consumer's compile failure tell you to widen.

Two things to check before you edit:

- **Adding a new dependency is a plan-stage decision, not an implementation detail** — the identity,
  latest-stable version, vulnerability scan and API study must already be approved. See the
  `v1rus-dependencies` skill; if the library has not been vetted, use `evaluate-dependency` first.
- **A convention plugin or an upstream module may already provide it transitively.** Check before
  adding a coordinate to a leaf module.

For reading a dependency's real source instead of guessing its API, use `ksrc` (`ksrc --help`) rather
than digging through the Gradle cache — reading `.gradle/` and `.m2/` is forbidden (see the
`v1rus-code-search` skill).
