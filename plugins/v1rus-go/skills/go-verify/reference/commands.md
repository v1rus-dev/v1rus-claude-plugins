# Go verification command set

Resolve each step in this order: project command, repo-pinned `go tool <name>`, PATH binary, else report missing. Flags below were checked against the local toolchain with `go help`.

0. Orient: `go version`, `go env GOTOOLCHAIN GOFLAGS GOWORK`, the `go`/`toolchain`/`tool` lines of `go.mod`, `git status`.
1. Build: `go build ./...` (single package: pass its path).
2. Format check: `gofmt -l .` must print nothing (or the project's formatter, e.g. golangci-lint formatters). Fix with the formatter.
3. Static analysis: `go vet ./...`, then the project lint (`golangci-lint run` or the project's lint target). If no lint config exists, report it; do not add one silently.
4. Tests (only when the task's complexity band calls for tests): `go test -race -shuffle=on ./...` for affected packages first. Add `-count=1` when the test cache hides flakiness. Integration tests only via the project's tag and only when Docker is available.
5. Vulnerabilities: `govulncheck ./...` when `go.mod`/`go.sum` changed or before release; for built artifacts `govulncheck -mode=binary <file>` (not verified locally, tool absent).
6. Modernization drift (on `go` line bump): `go fix -diff ./...` (exits non-zero when the patch is non-empty).
7. Hygiene when relevant: `go generate ./...`, `sqlc generate` (if `sqlc.yaml`), `go mod tidy -diff` (non-zero/diff means tidy is needed), then `git diff --exit-code` on generated files.
8. Report: one line per step (PASS / FAIL / SKIPPED with reason / TOOL MISSING), failing test names with the first error lines, nothing else.

`go test -json` gives machine-readable results when the output must be parsed.
