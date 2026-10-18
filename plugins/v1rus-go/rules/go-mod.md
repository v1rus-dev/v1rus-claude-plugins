---
paths:
  - "go.mod"
  - "go.sum"
  - "go.work"
  - "**/go.mod"
  - "**/go.sum"
  - "**/go.work"
---

# go.mod, go.sum, go.work

- Never edit `go.sum` by hand. Dependency changes go through `go get` / `go mod tidy`.
- A new `require`, `tool` or `replace` is a dependency change: needs approval and the plan-stage gate (identity, freshness, vulnerabilities, API study). See the `go-deps` skill. Never pick a version from memory; resolve it with `go list -m -u <module>` or `go list -m -versions <module>`.
- Do not change the `go` or `toolchain` lines as a side effect of another task. The `go` line is the minimum supported version and also sets language semantics for the module. Set it explicitly; do not rely on what `go mod init` writes.
- A `replace` pointing at a local path is for local development only; never leave one in a committed `go.mod`. `go.work` is not committed unless the repo is a deliberate workspace.
- Dev tools: the `tool` directive (`go get -tool`, run with `go tool <name>`) is available since 1.24. Tools share the module's dependency graph; heavy tools (linters) are better pinned outside it (advisory).
- After editing: `go mod tidy`, then `go build ./...`; `govulncheck ./...` when installed (report "not installed" otherwise). `go mod tidy -diff` shows pending changes without writing.
