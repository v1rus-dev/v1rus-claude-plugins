---
name: go-new-service
description: |-
  Scaffold a new Go service, CLI or library, or add a new binary: layout, thin main with run(), typed config, slog, explicit http.Server, graceful shutdown, health endpoints.
  Use when: starting a new Go module/binary or restructuring an entry point.
  Not for: adding a handler to an existing service (use go-http-endpoint); changing a repo's established layout without being asked.
---

Read [reference/skeleton.md](reference/skeleton.md), then the rules `${CLAUDE_PLUGIN_ROOT}/rules/go-core.md` and `${CLAUDE_PLUGIN_ROOT}/rules/go-concurrency.md`. Follow the repo's existing layout if there is one; the skeleton is the default for greenfield. Run `go-bootstrap` first when the project's commands are unknown. New dependencies need the `go-deps` gate; stdlib is the default for routing, config and logging.
