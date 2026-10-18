---
paths:
  - "**/*.{kt,java,swift,m,mm,js,jsx,ts,tsx,py,go,rs,cs,c,cc,cpp,h,hpp,rb,php}"
---

# Logging

Applies to application and library source code. Not to docs, configs, build scripts, shell scripts, generated code, fixtures, or one-off CLI scripts where `print` is the user-facing output (user-facing program output is not logging).

## Logger system

All logging goes through the logger the project already uses: detect it first (dependencies, existing calls, project CLAUDE.md) and match it. Never write `println`, `System.out`, `print()`, `console.log`, `NSLog`, `fmt.Println`, `println!` for diagnostic or operational output in reusable code. Never impose a logger the project does not use. Choosing one is part of the task only when the project has none: propose it during planning, starting from the platform standard (`os.Logger`, stdlib `logging`, `slog`, `tracing`/`log`, slf4j, the platform's own log API).

## Permanent logs

Allowed at every level and worth adding: they are a debugging asset. Good targets: inputs/outputs at system boundaries, errors with full context, key state transitions, non-obvious branch decisions. When adding heavy `debug` logging, verify that production strips or filters it (log level config, R8 rules, system filtering); if not, raise it as a separate decision.

| Level | Use for |
|---|---|
| `error` | Operation failed; always includes the cause |
| `warn` | Degraded behavior, fallback, exhausted retry, recoverable bad input |
| `info` | Significant lifecycle events, one per real-world event, not per loop iteration |
| `debug` | Internal state for investigations; stripped or filtered in release |
| `trace` | Per-iteration detail, raw payloads |

Choose the level by who needs to see it and when. Project conventions win if they differ.

## Temporary diagnostic logs: `// TEMP-LOG`

When read-only hypotheses stop converging (after the second failed one), instrument the code. Mark every temporary line with a `TEMP-LOG` comment on the line above (`// TEMP-LOG`, `# TEMP-LOG`), optionally with the purpose. Once the root cause is fixed, remove every `TEMP-LOG` line before finalizing. To promote a line to permanent, remove the marker, adjust the level, and treat it as a permanent log.

Gate: before the quality gate or a PR, scan the diff (`git diff | grep -n TEMP-LOG`, `grep -rn TEMP-LOG`). Any hit blocks.

## Never log, in any mode

- Secrets: passwords, API keys, tokens, session cookies, signing or private keys.
- PII without need (names, emails, phones, addresses, document ids); if required, a stable hash or last-4 only.
- Payment data: full PAN, CVV, full IBAN.
- Large blobs by default; if needed, truncate with an explicit `...[N bytes truncated]`.
- Anything under the project's privacy or compliance scope without explicit allowance.

`TEMP-LOG` lines are no exception.

## When to instrument

1. New code with non-trivial flow: add permanent logs at boundaries and key transitions as you write.
2. Reproducible bug that read-only attempts do not crack: `TEMP-LOG`.
3. Flaky or intermittent issue: `TEMP-LOG` at suspected race/timing points, often at trace level; expect several iterations.
4. Review finds an unclear runtime path: usually the answer is a permanent `debug` log, not an explanatory comment.
