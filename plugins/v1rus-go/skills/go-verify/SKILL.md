---
name: go-verify
description: |-
  Run the Go verification command set (build, format check, vet, lint, race tests, vulncheck) and report pass/fail per step.
  Use when: about to declare a Go task done, before the quality/acceptance gate, or after a logic change that needs a scoped test run.
  Not for: docs-only or comment-only changes (build/vet at most); non-Go repos; running a full suite after a no-logic edit.
---

Run the steps in [reference/commands.md](reference/commands.md). Command resolution order per step: the project's own command (CLAUDE.md, Makefile/Taskfile target, CI workflow), then a repo-pinned `go tool <name>`, then a binary on PATH, else report `tool missing: <name>`. Never install tools with elevated privileges and never report a skipped step as passed.

For delegated runs use the `go-test-runner` agent. Scope the check to the change: no-logic edits need build and vet; logic changes need the affected packages with `-race`, whole module before a PR.
