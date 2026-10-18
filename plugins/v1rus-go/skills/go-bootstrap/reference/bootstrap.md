# Go bootstrap

1. Toolchain: `go version`; `go env GOTOOLCHAIN GOFLAGS GOWORK GOPRIVATE`. Read `go.mod`: `go` line (minimum version and language semantics), `toolchain` line, `tool` directives, `replace` lines, `ignore` lines. Multiple `go.mod` or a `go.work` means a multi-module repo: find which module owns the changed files.
2. Project commands, in priority order: CLAUDE.md / README, `Makefile` or `Taskfile.yml` targets, CI workflow files (`.github/workflows`, `.gitlab-ci.yml`, etc.). Prefer these over default Go commands; CI is the authority on flags (tags, race, shuffle).
3. Lint: look for `.golangci.yml` / `.golangci.yaml` and its `version:` key (v2 format uses `version: "2"`). Absence is a finding, not something to add silently.
4. Codegen: `sqlc.yaml`, `go:generate` directives (`grep -rn "go:generate"` is fine here: it is a string search), `tools` in `go.mod`.
5. Tool availability: check each of `golangci-lint`, `govulncheck`, `sqlc`, `staticcheck` via `go tool <name>` (if declared as a `tool` directive) then PATH. Report missing ones with the exact name; never install with elevated privileges.
6. Integration prerequisites: build tags in use (`//go:build integration`), Docker availability if testcontainers is imported.
7. Output: table `step | command | source`, plus `missing: ...`, plus risks (old `go` line, local `replace`, uncommitted `go.work`).
