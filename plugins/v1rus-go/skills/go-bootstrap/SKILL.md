---
name: go-bootstrap
description: |-
  Discover a Go project's real commands and toolchain before working on it: go.mod directives, Makefile/Taskfile/CI commands, lint config, which tools are installed.
  Use when: first Go task in a repo, the verified command set is unknown, go.mod appears or its go line changes, or a command from memory just failed.
  Not for: non-Go repos; routine edits when the commands are already known this session.
---

Follow [reference/bootstrap.md](reference/bootstrap.md). Output is a short command table (build, fmt, vet, lint, test, vuln, generate) with the source of each command, plus a list of tools that are missing. Record it in the project's CLAUDE.md notes or the task's working file; do not invent or install anything.
