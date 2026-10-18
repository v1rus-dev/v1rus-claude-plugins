# Modernization with go fix

1. Confirm the `go` line in `go.mod` is already the intended one; fixers respect it (language features newer than the line are not introduced). Raising the line is a decision for the plan, not a side effect.
2. Preview: `go fix -diff ./...` prints a unified diff and exits non-zero when there are changes. List available fixers with `go tool fix help`; details of one with `go tool fix help <name>`.
3. Apply: `go fix ./...`, in a separate commit/changeset from any behavior work. Review the diff: modernizers are mechanical but can touch many files.
4. Verify: `go build ./...`, `go vet ./...`, and the affected tests with `-race` (behavior must be unchanged).
5. Manual items go fix does not do: removing obsolete helpers (`ptr()` when `new(expr)` is available), replacing deprecated libraries (dependency gate applies), `ioutil` leftovers if not covered by the fixers present on this toolchain.
6. Never fix generated files by hand; regenerate.

Fixers present on a recent toolchain include: any, forvar, rangeint, minmax, slicescontains, slicessort, mapsloop, stringscut, stringscutprefix, stringsbuilder, errorsastype, testingcontext, newexpr, omitzero, atomictypes, waitgroupgo (names differ by toolchain: use `go tool fix help`).
