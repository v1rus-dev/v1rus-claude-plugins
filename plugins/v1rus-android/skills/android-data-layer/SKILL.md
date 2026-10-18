---
name: android-data-layer
description: "v1rus native-Android data-layer conventions: API clients and DTOs in logical subpackages (never a dto dump), repository implementations in data while interfaces and use cases stay in domain, DTOs and Room entities never leaking through a repository interface, no speculative DataSource layer, transport exceptions mapped at the data boundary; Room with a Context-bound databaseBuilder, entities, DAOs, exported schemas, real migrations and MigrationTestHelper tests instead of destructive fallback; the Ktor client on the OkHttp engine as a single factory with ContentNegotiation and kotlinx.serialization, bearer auth delegated to v1rus-kotlin:ktor-client-auth with only token storage kept here; DataStore via the preferencesDataStore delegate and the Keystore reality for secrets; and explicit mappers. Load when adding an endpoint, DTO, DAO, entity, migration, repository, mapper or preference, or when wiring HTTP auth or token storage."
---

# Android Data Layer

Module and package names are the project's — **read its `CLAUDE.md` and `settings.gradle.kts`
first.** This skill is the layering those modules implement. Everything here is single-target: one
engine, one database builder, no `expect`/`actual`.

## Layout

- **API clients + DTOs** in the data module's `api/` package. DTOs go into **logical subpackages by
  domain area** (auth, user, profile, notification, …) — never dumped into a `dto/` root. Pick the
  existing subpackage before creating a new one.
- **Room DAOs + entities** in the data module's `database/` package, likewise grouped by domain area.
- **Repository implementations** in the data module. **Repository interfaces, domain models and use
  cases in the domain module.** The dependency points data → domain, never the reverse.
- **Mappers are explicit functions or classes** (`UserDto.toDomain()`, a `UserMapper`). Never put
  mapping logic inside a data class, a DAO or a Composable.
- Data-layer Koin bindings register through the data module's own DI module — see
  `v1rus-compose:di-koin-conventions`.

## Boundaries

- **Never expose a DTO or a Room entity through a repository interface.** Map to a domain model at the
  boundary. This is the rule that quietly rots a codebase when broken: once a DTO reaches the
  presentation layer, every serialisation change becomes a UI change.
- **Do not introduce a `DataSource` layer between repository and API/DAO** unless it carries real
  weight (two interchangeable backends, an offline-first cache policy with its own logic). A
  pass-through `DataSource` is indirection with no behaviour.
- **Transport exceptions are mapped at the data → domain boundary and never escape it.**
  `IOException`, Ktor's response exceptions, `SQLiteException`, serialization failures — convert to a
  project error type or `Result` in the repository. Nothing in domain or presentation catches an
  HTTP or SQLite type.
- Domain models carry **no framework dependencies** — no Room annotations, no `@Serializable`, no
  `android.*`. An entity and a domain model that look identical today are still two types.
- Suspend functions in the data layer are main-safe, and the dispatcher is **injected, never
  hardcoded** — see `v1rus-kotlin:kotlin-coroutines`.

## Room

- **Check which Room line the project's version catalog wires before writing an import.** Room ships
  as two parallel lines that differ in Maven coordinate *and* package: `androidx.room:room-*` with
  `androidx.room.*` imports, and `androidx.room3:room3-*` with `androidx.room3.*` imports (KSP only —
  no KAPT). Guessing the wrong one does not compile.
- Entities are `@Entity` classes owned by the data module; DAOs are `@Dao` interfaces returning
  domain-agnostic types (`Flow<List<Entity>>` is fine inside data, not across the boundary).
- The `@Database` class is built **once**, with the application `Context`, via
  `Room.databaseBuilder(...)` in the database DI module, and injected as a singleton. Never build a
  database per repository, and never pass an `Activity` context into the builder.
- **Schema export stays on and the exported schema JSONs are committed.** They are the input to both
  auto-migrations and migration tests.
- Every version bump ships a migration: an `@AutoMigration` (with an `AutoMigrationSpec` when columns
  or tables are renamed or dropped) for mechanical changes, a hand-written `Migration` for anything
  that moves data. **`fallbackToDestructiveMigration` and its variants are banned in a shipping app** —
  they silently delete user data.
- **Every migration gets a test:** create the old version, insert a row, run the migration, assert the
  data survived. `MigrationTestHelper` comes from Room's testing artifact — read the exact coordinate
  from the project's version catalog, it changed across Room majors. In an Android module the only
  constructor available takes an `Instrumentation`, so these tests are instrumented and live in
  `src/androidTest`. (Room's testing artifact does ship an `Instrumentation`-free helper, but only in
  its Kotlin/JVM variant, which an Android module's `src/test` does not resolve.) That puts migration
  tests in the opt-in instrumented lane rather than the default loop — see `android-testing` — so a
  schema change has to budget a device or emulator run, not assume the usual JVM pass covers it.

## HTTP

One `HttpClient`, built by a single factory on the **OkHttp** engine and injected as a singleton — a
client owns a connection pool and threads, so creating one per repository is a resource leak with
extra latency. The factory configures `ContentNegotiation` with kotlinx.serialization (lenient enough
for the backend, `ignoreUnknownKeys` on), timeouts, the default request (base URL, common headers)
and logging. Engine-level settings (interceptors, connection pool, protocols) are configured in the
`OkHttp` engine block of that same factory.

**Bearer auth — the whole access/refresh/session-expiry contract — is
`v1rus-kotlin:ktor-client-auth`.** The flow is identical on native Android and on KMP, so it is
written down once; invoke that skill before wiring auth, and do not re-derive it here.

Android adds exactly one thing to it: **where the token pair lives.** The pair is a secret, so it does
not belong in plain DataStore or `SharedPreferences` — see *Preferences and secrets* below for the
Keystore reality and why `androidx.security:security-crypto` is not the answer.

## Preferences and secrets

- **DataStore** is the key-value store: Preferences DataStore for loose app settings, Proto DataStore
  when the shape deserves a schema. Reads are a `Flow`, writes are suspending and transactional, and
  nothing about it is main-thread safe to block on. Only **one instance per file per process** may
  exist — a second instance for the same file throws.
- The canonical way to get that single instance is the **`preferencesDataStore` property delegate**,
  declared once at the top level of a file as an extension on `Context` —
  `val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")`. The
  `name` names the file. Reach for `PreferenceDataStoreFactory.create(...)` only when the delegate
  genuinely does not fit; hand-rolling the factory is how two instances end up on one file. Bind the
  instance in the DI graph with the application context and expose it behind a typed wrapper, not as a
  raw `DataStore<Preferences>` on the repository interface.
- DataStore is a plain file. **It does not encrypt anything**, and neither does `SharedPreferences`.
- **Jetpack Security Crypto (`androidx.security:security-crypto` — `EncryptedSharedPreferences`,
  `EncryptedFile`) is deprecated**: all of its APIs were deprecated in favour of platform APIs and
  direct Android Keystore use. Do not add it to new code, and do not treat an existing usage as the
  house pattern.
- Keys live in the **Android Keystore**; anything sensitive at rest is encrypted with a Keystore-backed
  key. Prefer not storing the secret at all: authenticate once and keep short-lived, service-specific
  tokens rather than credentials. Where and how a token is persisted is a security decision — settle
  it at plan stage and run the `security-expert` review, do not pick a store while writing the
  repository.
- Large or relational data is Room's job, not DataStore's.

## Testing

The data layer is the cheapest part of an Android app to test and the most worth testing: API
behaviour through Ktor's `MockEngine`, repositories against handwritten fakes, migrations against
`MigrationTestHelper`. Which source set each of those belongs to is `android-testing`.
