---
paths:
  - "**/Dockerfile"
  - "**/Dockerfile.*"
  - "**/*.Dockerfile"
  - "**/Makefile"
  - "**/Taskfile.yml"
  - "**/Taskfile.yaml"
  - "**/.golangci.yml"
  - "**/.golangci.yaml"
  - "**/.goreleaser.yml"
  - "**/.goreleaser.yaml"
---

# Go build and release files

- The Makefile/Taskfile is the single source of commands for CI and agents (`build test lint vuln fmt tidy generate`); keep target names stable.
- Release binaries: `CGO_ENABLED=0 go build -trimpath -ldflags="-s -w -X main.version=..." ./cmd/<name>`; verify with `go version -m <binary>`. Not for `-race`/`-cover` builds in production images.
- Dockerfile (advisory): multi-stage; copy `go.mod`/`go.sum` and `go mod download` before copying sources (layer cache); pin the builder image to a major.minor matching the `go` line (digest-pin for production); small final image (distroless static or scratch plus CA certificates); run as non-root; exec-form `ENTRYPOINT`; the app must handle SIGTERM.
- `.golangci.yml`: v2 format starts with `version: "2"`. Enable linters deliberately and verify with `golangci-lint config verify` and `golangci-lint linters` when installed. `//nolint` needs a specific linter and a reason. Do not enable noisy style linters unasked.
- PGO: `default.pgo` in the main package directory only after profiling shows CPU-bound hot paths.
- Details: `go-release-build` skill.
