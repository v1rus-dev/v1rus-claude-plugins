---
name: flutter-persistence
description: "What is stored where in a v1rus Flutter project: Drift for structured relational data with typed DAOs, reactive watch queries and versioned migrations; flutter_secure_storage for anything secret (access and refresh tokens, PINs, keys); shared_preferences for non-sensitive user preferences and flags only; plus the non-negotiable that a token never goes into preferences, migrations are never edited after release, and storage is always behind a core interface so a Bloc never touches a DAO. Load when adding a table, a migration, a cached entity, a stored preference, or when deciding where a value belongs."
---

# Persistence

Three stores, three jobs. Choosing the wrong one is the most common source of both security findings and
migration pain.

| Store | Use for | Never for |
|---|---|---|
| **Drift** (SQLite) | structured, queryable, relational data; offline cache; anything with more than a handful of rows or needing reactive queries | secrets; one-off flags |
| **flutter_secure_storage** | access/refresh tokens, PIN/biometric secrets, API keys, anything whose leak is an incident | large data; anything you query |
| **shared_preferences** | non-sensitive user preferences and flags: theme mode, locale, onboarding-seen, last-used filter | **tokens, credentials, PII**; structured data |

**Non-negotiable: a token never goes into `shared_preferences`.** It is plain text on disk —
`SharedPreferences` XML on Android, `NSUserDefaults` plist on iOS — readable on a rooted/jailbroken
device and in a backup. Secure storage is the only correct place. This is a review-blocking finding, not
a preference.

## Everything sits behind a `core` interface

```dart
// core/storage/token_storage.dart
abstract interface class TokenStorage {
  Future<String?> readAccessToken();
  Future<void> writeTokens({required String access, required String refresh});
  Future<void> clear();
}
```

Blocs, use cases and repositories depend on the interface. Nothing outside `core/storage/` and
`data/database/` imports `flutter_secure_storage`, `shared_preferences` or Drift types. This is what makes
storage swappable and tests fast: an in-memory implementation replaces it entirely
(`flutter-testing`).

## Drift

- **Tables and DAOs** in `data/database/`; the database class is registered as a singleton.
- **`watch` over `get` for anything the UI displays.** A reactive query is the point of choosing Drift:
  the repository exposes a `Stream`, the Bloc emits on each change, and no manual invalidation is needed.
- **Repositories map rows to entities.** A Drift row class never reaches `domain` or `features`.
- Keep heavy work off the UI isolate for large reads/writes — Drift supports running on a background
  isolate; use it before optimising anything else.

### Migrations — the part that bites

- `schemaVersion` is bumped on **every** shape change, and a `MigrationStrategy` step is written for it.
- **A migration that has shipped is never edited.** Editing it means devices that already ran it are
  permanently inconsistent with devices that have not. Add a new version instead.
- Write a migration test: create the database at version N, run the migration, assert the data survived.
  Drift ships schema-verification tooling for exactly this; a migration is the one piece of persistence
  code where "it compiles" proves nothing.
- Destructive fallback (drop and recreate) is acceptable **only** for a pure cache whose loss is
  invisible to the user, and it must be commented as a deliberate decision.

## `shared_preferences`

- Keys are constants in one place, namespaced (`prefs.theme_mode`), never inline string literals at call
  sites.
- Reading returns a typed default rather than a nullable value the caller re-decides each time.
- Preferences are not a cache. If it has structure or needs querying, it belongs in Drift.

## Cache policy is explicit

For every cached entity, state in the plan: what is cached, its **TTL or invalidation trigger**, and what
happens offline (stale data shown with an indicator / empty state / error). "It caches" without an
invalidation rule becomes a bug report about data that never refreshes.

Clearing on logout is part of the feature, not a follow-up: tokens **and** user-scoped cached data are
wiped, so the next account does not see the previous one's content.

## API verification

Drift, secure storage and preferences all changed APIs across majors (`shared_preferences` now has an
async/cache-based API alongside the legacy one). Check the resolved version's own documentation before
writing the code, never a remembered signature; version choice happens at plan time via
`v1rus-dependencies`.
