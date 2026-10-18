# Go build and release

Static reproducible build (flags checked with `go help build`; effect checked by building a sample and reading `go version -m`):
`CGO_ENABLED=0 go build -trimpath -ldflags="-s -w -X main.version=$VERSION" -o bin/app ./cmd/app`
- `-trimpath` strips local paths; `-s -w` strip symbol and debug info; `-X pkg.var=value` sets a string variable (must be `var`, not `const`). Version info can also be read at runtime from `runtime/debug.ReadBuildInfo`; `-buildvcs` controls VCS stamping.
- Expose the version through `--version` or an endpoint.

Task runner: Makefile or Taskfile with the canonical targets; CI calls the same targets.

Docker (advisory, not verified by a build here): see `rules/go-build.md`; additionally use BuildKit cache mounts for the Go build and module caches, copy only what the build needs, and set `GOTOOLCHAIN=local` when the base image already has the right Go.

PGO: `default.pgo` in the main package directory is picked up automatically (`-pgo=auto` is the default); gains and build-time cost vary, collect from production-like load, refresh periodically, do it only after profiling shows CPU-bound hot paths. See `go help build` (`-pgo`).

Generated code: `go:generate` directives documented and run through the task runner; generated files carry the standard "Code generated ... DO NOT EDIT." header and are committed; CI checks `git diff --exit-code` after generation.

Releases: goreleaser for CLIs is common (not verified here); run `govulncheck -mode=binary` on the artifact when the tool is installed. Never ship `-race` or `-cover` builds.
