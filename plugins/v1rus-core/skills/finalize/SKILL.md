---
name: finalize
description: |-
  Quality gate for the current branch: a multi-round review, fix, simplify loop that polishes how the code is written (not what it does). Runs a one-shot built-in /code-review deep scan, then code-reviewer, /simplify, optional pr-review-toolkit agents and conditional expert reviews, with `check` between phases. Exits PASS when no BLOCK findings remain, or ESCALATE after the round budget.
  Triggers: "finalize", "run the code quality pass", "clean up the code", "prepare for review", "polish the code", "tidy up", "harden the implementation".
  Do NOT use for: functional acceptance (test-runner against the acceptance criteria), a read-only review of arbitrary code (the /review command), or pure documentation and single-line mechanical edits.
---

# Finalize

Code-quality pass over the current branch. It focuses on how the code is written (quality, clarity, robustness), not on what it does (acceptance) or whether it builds and passes (`check`). No single reviewer catches the full set of recurring patterns (removed-behavior regressions, cross-file breakage, wrong-altitude band-aids, over-engineered abstractions, silent failures, fragile types, weak coverage), hence the orchestration.

Whoever breaks existing tests fixes them in the same round (see `${CLAUDE_PLUGIN_ROOT}/rules/qa-and-testing.md`). A round cannot end while tests are red.

## External optional dependencies

Not shipped by this plugin; they come from the Claude Code session or other plugins. Check availability first and log what was skipped.

| Dependency | Used in | Fallback when absent |
|---|---|---|
| built-in `/code-review` skill | Phase 0 | skip Phase 0, log it; Phase A still runs |
| built-in `/simplify` skill | Phase B | launch one implementation subagent for a reuse/simplification pass over the diff, or skip and log; run `check` afterwards either way |
| `pr-review-toolkit` agents (separate plugin) | Phase C | skip Phase C, log it |
| performance, build or CI specialist agents (optional, e.g. `performance-expert` from `v1rus-kotlin`) | Phase D | skip those experts, log it |

## Inputs

- `slug`: task slug for artifact names. Branch state: read the current branch, never switch.
- Context artifact (optional): the plan (`docs/plans/<slug>/plan.md`) or, for bug fixes, the debug artifact (`swarm-report/<slug>-debug.md`).
- Diff artifact: materialize the diff to `swarm-report/<slug>-diff.txt` before invoking `code-reviewer`. Do not hardcode `origin/main`: derive the default branch (`git remote show origin`, falling back to `main`/`master`/`develop`) and use `git merge-base`. Use `git diff -M` for rename detection.
- Flags: `--max-rounds N` (default 3), `--skip-deep-scan`, `--deep-scan-effort <auto|low|medium|high|xhigh|max>`, `--skip-experts`, `--skip-security-review "<reason>"` (recorded verbatim in acknowledged risks; discouraged).

## Structure

```
Phase 0 (once)  built-in /code-review deep scan -> dedup vs Phase A -> feeds Round 1
Round N:
  A  code-reviewer                      -> fix BLOCK -> check
  B  /simplify (applies fixes)          -> check
  C  pr-review-toolkit agents, if installed (parallel) -> fix BLOCK -> check
  D  expert reviews, conditional (parallel)            -> fix BLOCK -> check
  Any unfixed BLOCK -> next round (up to max rounds); else PASS
```

PASS: no BLOCK findings; WARN and NIT are listed in the report and never block. ESCALATE: BLOCKs remain after the last round; dump them and let the owner decide (return to implementation, accept the risk, re-scope).

## Phase 0: deep scan

Skip on trivial diffs (single file, under 50 LOC, refactor-only, no new public API) and with `--skip-deep-scan`; log the reason. Invoke the built-in `/code-review` (core skill `code-review`, not a marketplace plugin of the same name that demands a PR number) in report mode: no `--fix`, no `--comment`. If the invoked command demands a PR number it bound the wrong instance: skip Phase 0, log it, and continue. Never pass a PR number to satisfy it.

Effort `auto`, first match wins, floor `medium`: **max** for narrow security patterns, auth/payment/PII/data-migration risk areas or DB migrations; **xhigh** for infra-layer changes (network, storage, auth, DI), new public API across 2+ modules, or over 500 LOC / 15 files; **high** for a new public symbol, cross-module dependency change, or over 150 LOC / 6 files; **medium** otherwise. Record tier and reason in the report.

Ingest only correctness findings whose failure scenario is concrete (crash, wrong output, data loss, dropped guard, broken caller). Discard reuse/simplification/efficiency findings (Phase B owns them) and convention findings (Phase A owns them); dedupe overlaps with Phase A (Phase A wins). Phase 0 does not re-run in later rounds.

## Phase A: semantic review

Launch `code-reviewer` with the task description verbatim, the plan path if one exists, and the diff. It returns PASS/WARN/FAIL with findings on a 0/25/50/75/100 confidence rubric.

| Severity x confidence | Action |
|---|---|
| critical >= 75 | Fix now, run `check`. If it does not converge it stays BLOCK; never silently downgrade to an accepted risk. |
| major >= 75 | Fix if tractable; refactor beyond the diff escalates and stays BLOCK. |
| minor >= 50 | NIT in the report; never blocks. |

Violations of the project's CLAUDE.md non-negotiables are always BLOCK regardless of confidence. Never skip Phase A: if `code-reviewer` fails to launch, stop and escalate.

## Phase B: simplify

Invoke `/simplify`: a parallel reuse, quality and efficiency pass that applies fixes directly. Trust its output, then `check`. If `check` fails afterwards, revert the simplify changes, log it, and continue to Phase C; this neither adds a BLOCK nor consumes budget.

## Phase C: pr-review-toolkit (optional)

If the `pr-review-toolkit` agents are not installed, skip and log it. Otherwise run in parallel: `pr-test-analyzer`, `silent-failure-hunter`, `type-design-analyzer` (always), and `comment-analyzer` only when the diff adds or changes comments. Same rubric and fix loop as Phase A; fixes that need new test code go to the `write-tests` skill or an implementation agent.

## Phase D: expert reviews (conditional, parallel)

Launch only the experts whose domain the diff matches; none matching means skip.

| Expert | Fires when |
|---|---|
| `architecture-expert` | new module, new public API surface, cross-module dependency change, layering violation |
| `security-expert` | declared risk areas (auth, payment, PII, data-migration) or a pattern below |
| `ux-expert` | UI-surface changes, copy, accessibility, animation |
| `business-analyst` | spec/requirements/scope changes (rare here) |
| a performance reviewer, build-system specialist or CI specialist | hot-path/N+1/concurrency changes; build-script changes; CI/deploy config, if such agents are installed |

Security patterns: narrow (one is enough for a full review): auth/crypto/token/session paths; credential-storage APIs (preferences, keychain, local/session storage, cookies, keystore); new dependency lines in build files; DB migrations; unsafe deserialization. Broad (two needed, or one gives a scoped review of that surface only): network/API/HTTP/RPC/GraphQL paths. Content patterns match only added or modified hunks; path patterns match the new path.

Coverage audit (tested bands only): when the diff adds a public symbol without a test (see the public-API gate in `${CLAUDE_PLUGIN_ROOT}/rules/qa-and-testing.md`), a declared test-plan case is unimplemented, or data-layer code changed without tests, delegate the missing tests via the `write-tests` skill, then `check`. Skip on trivial diffs or when the module has no test infrastructure (record a follow-up instead, never skip silently).

Expert findings use the same gate as Phase A. A security-critical finding at confidence 50 is still included with a `[please verify]` marker and treated as BLOCK.

## Mechanical verification between phases

After any code modification run `check`. On failure: log which phase's fix caused it, make one narrow repair attempt, and if it still fails revert that fix and keep the originating finding as BLOCK (never relabel it as an accepted risk). Round 3 ending with BLOCKs means ESCALATE.

## Report

Save `swarm-report/<slug>-finalize.md` on exit: rounds run, exit (PASS/ESCALATE) with reason, per-round phase results (Phase 0 effort and reason or skip reason, findings per phase with BLOCK/WARN/NIT counts, fixes, `check` result), unresolved BLOCKs table (severity, confidence, category, finding, phase, round, file:line), remaining non-blocking findings, acknowledged risks (only what the owner explicitly accepted), commits added. Also save a terse receipt `swarm-report/<slug>-quality.md` with `Status: PASS|FAIL`, `Date:`, `Escalate: true` (only on ESCALATE) and the detail path.

Chat summary, at most 20 lines: PASS with the count of fixed findings by category, or ESCALATE with up to five top BLOCKs and one question (which first; accept risk, continue implementing, or re-scope). Never paste the report table into chat.

## Scope

In scope: quality of code related to the diff, delegating fixes, `check` after each change. Out of scope: new features, scope changes, functional acceptance, architectural redesign. Keep fixes inside files touched by the change unless a finding requires otherwise. Escalate when BLOCKs remain after the last round, a fix does not converge after one retry, a BLOCK needs refactoring beyond the diff, or an expert demands an architectural change.
