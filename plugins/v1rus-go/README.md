# v1rus-go

Go layer of the v1rus marketplace: path-scoped conventions, a verification flow, and engineer/reviewer/test-runner agents for services, CLIs and libraries. Depends on `v1rus-core` (stack-agnostic gates, review agents, workflow). No charter: core's charter covers the always-on baseline, and everything Go-specific loads when a Go file is edited.

## Contents

Rules (injected by the engine on Write/Edit of matching files): `go-core` and `go-concurrency` (`**/*.go`), `go-mod` (`go.mod`, `go.sum`, `go.work`), `go-test` (`*_test.go`, `testdata/`), `go-sql` (`*.sql`, sqlc config, `migrations/`), `go-build` (Dockerfile, Makefile, Taskfile, golangci/goreleaser config).

Skills (thin doors, bodies in `reference/`): `go-bootstrap`, `go-verify`, `go-new-service`, `go-http-endpoint`, `go-database`, `go-concurrency-review`, `go-errors-and-logging`, `go-write-tests`, `go-modernize`, `go-deps`, `go-release-build`, `go-perf`.

Agents: `go-engineer` (sonnet, implements), `go-reviewer` (read-only), `go-test-runner` (runs the verification set, never edits; project commands first, fallback `go build ./... && go vet ./... && go test -race ./...`, reports missing tools explicitly).

## Marking

Rules phrased "(advisory)" are judgment calls with no mechanical check. Facts about Go commands and flags cited here were checked against the local toolchain (`go help`, `go doc`, small spikes): `go fix -diff` (non-zero exit on a non-empty patch), `go mod tidy -diff`, `-trimpath`/`-ldflags -X` with `go version -m`, `go get -tool`, `-shuffle`, `-artifacts`, `errors.AsType`, `sync.WaitGroup.Go`, `testing/synctest`. Not verified (tools absent locally): golangci-lint config and linter set, govulncheck binary mode, sqlc, benchstat, pgx helper names, testcontainers API, Dockerfile practices, goreleaser, `-gcflags=-m`. Skills say so where it matters.

## Deviations from the research playbook

- No hooks beyond the synced engine (the playbook's PostToolUse gofmt and PreToolUse deny ideas are not implemented; they would need a custom hook file, a hook-contract decision for the orchestrator). The rules state the same constraints as text.
- HTTP, logging and database details live in skill references, not path rules, so every `.go` edit injects only `go-core` and `go-concurrency` (about 70 lines) instead of all topics.
- `go-perf-analyst` agent not created (optional in the playbook; `go-perf` skill plus a core performance reviewer cover it).
- Skill bodies point to `rules/` or their own `reference/`; shared command set lives in `go-verify/reference/commands.md`.

## Assumptions

Format: choice, why, how to reverse.

1. No `pkg/` directory; `cmd/` + `internal/` only. Official layout guide never uses `pkg/`. Existing repos keep theirs. Reverse: edit `skills/go-new-service/reference/skeleton.md`.
2. Stdlib `ServeMux` first, no router framework. Method/wildcard patterns since 1.22 cover most needs. Reverse: edit `skills/go-http-endpoint/reference/http.md`.
3. `pgx` + `pgxpool` as the default Postgres driver, `database/sql` when portability requires. Richer native API, supported by sqlc. Reverse: `skills/go-database/reference/database.md`.
4. sqlc for bulk CRUD, hand-written pgx for dynamic queries, no ORM unless the user chooses. Reverse: same file.
5. `log/slog` only for new code. Stdlib, enough handler ecosystem. Reverse: `rules/go-core.md` Logging section.
6. Fakes over generated mocks; stdlib `testing` + `go-cmp` over testify unless the repo already uses it. Reverse: `rules/go-test.md`.
7. `gofumpt` not mandated (gofmt + goimports baseline). Avoids churn in existing repos. Reverse: add to `rules/go-build.md` and `go-verify` commands.
8. Small dev tools via the `tool` directive; heavy linters pinned outside the module graph. Reasoning is advisory. Reverse: `rules/go-mod.md`.
9. Linter selection and the "noisy linters off" stance are judgment. The plugin ships no `.golangci.yml`; it only says enable deliberately. Reverse: add a skeleton to `go-release-build/reference/build.md`.
10. Tests are written only when the user's complexity policy says so; `go-write-tests` and `go-test` describe how, not whether. Reverse: n/a (policy lives in global rules).
11. Migration tool unspecified (goose, golang-migrate, atlas): use the repo's, else decide with research. Reverse: name one in `rules/go-sql.md`.
12. `encoding/json/v2` allowed for new code on toolchains that ship it, v1 stays default in existing code. Reverse: `skills/go-http-endpoint/reference/http.md`.
13. Integration tests gated by a build tag (`integration`) unless the repo has another convention. Reverse: `rules/go-test.md`.
14. `go fix` modernization lives in its own change, never mixed with behavior work (minimal-diff rule). Reverse: `skills/go-modernize/SKILL.md`.
15. CLI framework and exit codes left to the repo (cobra with `cmd.Context()`, or stdlib `flag`; 0/1/2 as convention). Reverse: `skills/go-new-service/reference/skeleton.md`.
Added by this build:
16. Language-feature gates quoted by Go minor (1.22 ... 1.27) in rules; every gate in the rules (loop-var/range-int 1.22, iterators 1.23, `testing.B.Loop` 1.24, `WaitGroup.Go`/`synctest` 1.25, `errors.AsType`/`slog.NewMultiHandler`/`new(expr)` 1.26, generic methods and `encoding/json/v2` 1.27) was verified with a local toolchain via a scratch build and `go vet` (`stdversion`) against lowered `go` lines; the compiler and vet enforce the gate regardless.
17. No charter (core's covers it); no custom hooks.

## Install

```
/plugin marketplace add v1rus-dev/v1rus-claude-plugins
/plugin install v1rus-go@v1rus-dev
```

Dependencies (v1rus-core) are resolved automatically from the same marketplace.
