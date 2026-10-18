---
name: go-release-build
description: |-
  Work on Go build and release plumbing: Dockerfile, Makefile/Taskfile, ldflags and version injection, trimpath, goreleaser, CI build steps, PGO.
  Use when: editing those files or setting up reproducible/static builds and container images.
  Not for: application logic; deployment/infrastructure outside the repo.
---

Read `${CLAUDE_PLUGIN_ROOT}/rules/go-build.md` and [reference/build.md](reference/build.md). Match the repo's existing build tooling. Verify a build change by actually building and inspecting the artifact.
