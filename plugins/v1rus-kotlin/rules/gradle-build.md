---
paths:
  - "**/*.gradle.kts"
  - "**/*.gradle"
  - "**/libs.versions.toml"
  - "**/buildSrc/**"
  - "**/build-logic/**"
---

# Gradle build script rules

Applies to build scripts, `settings.gradle*`, version catalogs and convention plugins (`build-logic/`, `buildSrc/`).

## Dependency configuration: `implementation` by default

1. `implementation`: first choice; types do not appear in the module's public API.
2. `api`: only when a dependency's types appear in this module's public surface (public signatures, public class hierarchies, annotations on public symbols, generic arguments of public APIs), when consumers would otherwise redeclare the same dependency to use a type this module exposes, or when it provides a public DSL consumers call through this module.
3. `compileOnly` / `runtimeOnly`: plugin-classpath needs, optional annotation processors, libraries provided by the host.

Same priority for test configurations and multiplatform source sets (`commonMain.dependencies { implementation(...) }` first). Unsure: `implementation`; a consumer compile failure is a clean signal to widen, a silent transitive leak is not. Tightening `api` to `implementation` later breaks anyone relying on the leak; widening is trivial. Check the visibility rule first: make sure the symbol is meant to be public at all.

## Catalogs and convention plugins

- New dependency coordinates and versions go into the version catalog (`gradle/libs.versions.toml` or the project's equivalent), not into module scripts.
- Configuration repeated in 3+ modules belongs in a convention plugin (`build-logic/` included build preferred over `buildSrc` when the code changes often), not copied between scripts.
- Before adding a dependency to a leaf module, check whether a convention plugin or an upstream module already provides it.
- Do not apply plugins via `allprojects {}` / `subprojects {}`; use convention plugins. Prefer `tasks.register` over `tasks.create` and lazy `Provider`/`Property` APIs.
- Adding or bumping a dependency or plugin is a planned, approved decision: skill `gradle-dependency-gate`.
