---
name: di-koin-conventions
description: "Koin dependency-injection conventions for v1rus Compose projects, Compose Multiplatform and Jetpack Compose alike: a single app initializer called from every platform entry point that wires logging then Koin with the network, data, domain, platform, feature and core modules; new core infrastructure and new features register in their own module lists; platform-only bindings (Android Context, iOS view controller, desktop paths) live in the per-platform module and never in a common one; constructor injection is the default; and when several implementations must resolve through getAll, each registers under its own primary type with bind rather than multiple unqualified definitions of the same interface. Load when adding a Koin module, registering a dependency, wiring a new feature, or bridging a platform capability."
---

# DI (Koin) Conventions

The concrete initializer and module-list file names are the project's — **read the project's
`CLAUDE.md` and its app module before adding a binding.** This skill is the structure they follow.

## Initialisation

One app initializer, called from every platform entry point — the Android `Application`, and on a
multiplatform project the iOS framework entry and desktop `main` as well. It sets up logging first,
then starts Koin with the full module list: network, data, domain, the platform module, auth
configuration, feature modules, core modules.

Nothing initialises Koin a second time, and no module list is assembled at a call site.

## Where a binding goes

| What you are adding | Where it registers |
|---|---|
| New core infrastructure | the core-modules list in the app module |
| New feature | the feature-modules list in the app module |
| Data-layer binding (API client, DAO, repository) | the data module's own Koin module |
| Platform-only binding — Android `Context`, iOS view controller, desktop file paths | that platform's own DI module, **never** a shared one |
| Feature-local dialog / bottom-sheet destination | the owning feature's Koin module |

A binding that needs a platform type is the signal that it belongs in a platform module — not the
signal to widen a common API.

## Rules

- **Constructor injection is the default.** Service-locator lookups (`get()` inside a class body,
  `koinInject()` outside a composable) are the exception, not the pattern.
- **Multiple implementations of one interface:** register each under its **own primary type** plus
  `bind<Interface>()`, then resolve with `getAll<Interface>()`. Registering several unqualified
  definitions with the same interface as the primary type silently overwrites — the last one wins and
  the others vanish with no error.
- Bridging a platform capability on a KMP project has rules of its own — see
  `v1rus-kmp:kmp-conventions`.
- Compose destinations registered through DI (dialog and bottom-sheet scene strategies) follow the
  `compose-navigation-patterns` skill.
- A dispatcher is injected as a constructor parameter, not resolved from Koin inside the class — see
  `v1rus-kotlin:kotlin-coroutines`.
