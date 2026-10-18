---
name: go-concurrency-review
description: |-
  Checklist for Go code that adds or changes goroutines, channels, mutexes, atomics, errgroup/WaitGroup, worker pools, tickers, or cancellation paths.
  Use when: a diff introduces concurrency or shutdown logic, or a race/leak/deadlock is suspected.
  Not for: single-threaded code; general code review (use go-reviewer).
---

Apply `${CLAUDE_PLUGIN_ROOT}/rules/go-concurrency.md` and the checklist in [reference/checklist.md](reference/checklist.md). Require evidence: `go test -race` on the affected packages and a test that shows each new background worker stops. If race or leak tooling cannot run, say so explicitly.
