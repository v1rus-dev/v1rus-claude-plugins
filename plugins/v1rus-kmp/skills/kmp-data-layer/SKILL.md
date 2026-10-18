---
name: kmp-data-layer
description: "v1rus KMP data-layer conventions: API clients and DTOs organised into logical subpackages (never dumped into a dto root), Room DAOs and entities with the database builder as expect/actual per platform, repository implementations in the data module while interfaces and use cases stay in domain, DTOs and entities never leaking through a repository interface, no speculative DataSource layer between repository and API/DAO, the Ktor HttpClientFactory as expect/actual per engine, and bearer auth delegated to v1rus-kotlin:ktor-client-auth with only the per-platform token store kept here. Load when adding an endpoint, DTO, DAO, entity, repository or mapper, or when wiring HTTP auth."
---

# KMP Data Layer

Module and package names are the project's — **read its `CLAUDE.md` and `settings.gradle.kts`
first.** This skill is the layering those modules implement.

## Layout

- **API clients + DTOs** in the data module's `api/` package. DTOs go into **logical subpackages by
  domain area** (auth, user, profile, notification, …) — never dumped into the `dto/` root. Pick the
  existing subpackage before creating a new one.
- **Room DAOs + entities** in the data module's `database/` package. The `RoomDatabase` builder is
  `expect`/`actual` per platform; the DAOs themselves are common. **Schema export stays on and the
  exported JSONs are committed**, every version bump ships a real migration, and
  `fallbackToDestructiveMigration` and its variants are banned in a shipping app — they silently
  delete user data.
- **Repository implementations** in the data module. **Repository interfaces, domain models and use
  cases in the domain module.** The dependency points data → domain, never the reverse.
- **Mappers are explicit functions or classes.** Never put mapping logic inside a data class.
- Data-layer Koin bindings register through the data module's own DI module — see
  `v1rus-compose:di-koin-conventions`.

## Boundaries

- **Never expose a DTO or a Room entity through a repository interface.** Map to a domain model at the
  layer boundary. This is the rule that quietly rots a codebase when broken: once a DTO reaches the
  presentation layer, every serialisation change becomes a UI change.
- **Do not introduce a `DataSource` layer between repository and API/DAO** unless it is carrying real
  weight (two interchangeable backends, an offline-first cache policy with its own logic). A
  pass-through `DataSource` is indirection with no behaviour.
- **Map implementation exceptions at the data → domain boundary.** Ktor's response exceptions,
  `IOException`, SQLite failures, serialization failures — none of them reach domain or presentation;
  convert to a project error type or `Result`. See `v1rus-kotlin:kotlin-coroutines`.
- Suspend functions in the data layer are main-safe, and the dispatcher is **injected, never
  hardcoded** — see `v1rus-kotlin:kotlin-coroutines`.
- Domain models carry **no framework dependencies** (`kotlinx.*` annotations excepted).

## HTTP

The Ktor `HttpClient` is built by an `expect`/`actual` factory — typically OkHttp on Android, Darwin on
iOS, CIO on desktop. Engine-specific configuration belongs in the `actual`, shared configuration
(serialization, logging, timeouts, default request) in the common builder.

**Bearer auth — access + refresh, single-flight, session expiry — is
`v1rus-kotlin:ktor-client-auth`.** The flow is identical on every target, so it is written down once;
invoke that skill before wiring auth, and do not re-derive it here.

What is multiplatform-specific: the `Auth` plugin is installed in the **common** builder, because the
flow is shared — only the engine and the token store are per platform. The store is an
`expect`/`actual` secure store, not a common file: Keystore-backed on Android, Keychain on iOS. Desktop
has no single obvious equivalent, so settle it at plan stage and run the `security-expert` review
rather than defaulting to a file on disk.

## Testing

The data layer is the part of a KMP app that is cheapest to test and most worth testing: API behaviour
through Ktor's `MockEngine`, repositories against handwritten fakes. See the `kmp-testing` skill.
