---
paths:
  - "**/*.sql"
  - "**/sqlc.yaml"
  - "**/sqlc.yml"
  - "**/sqlc.json"
  - "**/migrations/**"
---

# SQL, sqlc, migrations

- Parameterized queries only (`$1`); no string-built SQL.
- Never edit a migration that was already applied anywhere; add a new one. Migrations are versioned and forward-only, in the repo's existing tool and directory (do not introduce a migration tool without approval).
- Prefer backward-compatible expand/contract steps (add nullable column, backfill, switch code, then drop) so old and new app versions can run together (advisory).
- Destructive statements (`DROP`, `TRUNCATE`, column type narrowing, `DELETE` without `WHERE`) are a data-loss surface: call them out to the user before writing them.
- Long locks: creating indexes on big tables, rewriting columns. Use the engine's concurrent/online variant where it exists and note it.
- sqlc: after editing queries, schema or `sqlc.yaml`, regenerate (`sqlc generate`, `sqlc vet` if configured) and commit the generated output; never edit generated files by hand. If `sqlc` is not installed, say so instead of skipping silently.
- Model NULL deliberately (pointer or null type); zero value is not NULL.
- Details and Go-side patterns: `go-database` skill.
