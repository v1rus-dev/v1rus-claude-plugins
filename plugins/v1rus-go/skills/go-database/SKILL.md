---
name: go-database
description: |-
  Work on Go database access: SQL queries, sqlc config and generation, pgx/pgxpool or database/sql usage, transactions, migrations, NULL handling, DB tests.
  Use when: touching *.sql, sqlc.yaml, migrations, repository/store code, connection pools or transaction boundaries.
  Not for: pure in-memory logic; choosing or introducing a new DB engine/ORM/migration tool (decision for the user, route through go-deps).
---

Read [reference/database.md](reference/database.md) and `${CLAUDE_PLUGIN_ROOT}/rules/go-sql.md`. Use the repo's existing driver, query layer and migration tool. Migrations that can lose data are a data-loss surface: stop and surface the policy question. When the project uses sqlc, regenerate and commit output; if `sqlc` is missing, report it.
