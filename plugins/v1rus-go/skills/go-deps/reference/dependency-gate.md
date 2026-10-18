# Go dependency gate

Plan-stage block for every new or bumped module or tool:

1. Identity: module path, role in one line, why the stdlib or existing deps do not cover it.
2. Freshness: `go list -m -versions <module>` and `go list -m -u <module>` (inside the project) or the project's own tooling; state "latest stable: X". Prefer stable over pre-release and say so.
3. Vulnerabilities: `govulncheck ./...` after adding (source mode reports reachable calls); if the tool is not installed say so and name the alternative (OSV lookup). Any advisory hit stops the plan until the user decides.
4. API study: read the real API of the resolved version with `go doc <module>/<pkg>@<version>` (supported on recent toolchains; check `go help doc`) or the module source in the module cache; not from memory. For major bumps read the changelog/release notes.

Mechanics: `go get <module>@<version>`, `go mod tidy`, `go build ./...`, `go mod verify` (checks cached module integrity). Dev tools: `go get -tool <module/cmd/x>`, run with `go tool x`. Upgrades: `go list -m -u all`; patch-only with `go get -u=patch ./...`.

Hygiene: commit `go.mod` and `go.sum`; never hand-edit `go.sum`; no local-path `replace` committed; avoid deprecated or unmaintained modules (check the module's deprecation notice via `go list -m -json <module>`); vendoring only for hermetic builds or audit mandates (`go mod vendor`, `-mod=vendor`).

Toolchain: the `go` line is the minimum; CI should pin the toolchain explicitly (the default `GOTOOLCHAIN=auto` may download newer ones).
