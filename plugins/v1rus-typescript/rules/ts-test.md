---
paths:
  - "**/*.test.{ts,tsx,mts,cts,js,mjs,cjs}"
  - "**/*.spec.{ts,tsx,mts,cts,js,mjs,cjs}"
  - "test/**"
  - "tests/**"
  - "**/__tests__/**"
---

# Tests (TypeScript/JavaScript)

Depth is set by the global complexity bands: tests are written only from complexity 7 unless the user asks. These rules apply when you do write or edit a test.

- Use the runner the project already has (look at `package.json` scripts and config). New project: Vitest for TypeScript or when module mocking, fake timers, type tests, rich coverage or watch mode matter; `node:test` for zero-dependency libraries/CLIs and plain JS; Jest only in legacy repos.
- Layout: `x.test.ts` beside `x.ts` for unit tests; `test/integration/**`, `test/e2e/**` for slower suites; shared builders in `test/support/**`. Test files are type-checked (a test tsconfig that adds test globals via `types`, extending the base).
- Test the public contract (inputs to outputs/effects), not private functions. One behaviour per test, arrange/act/assert, deterministic: no real time, randomness or network.
- Mock only boundaries you do not own (network, clock, fs, randomness, third-party SDKs). Prefer in-memory fakes passed as parameters over module mocking; do not mock your own modules; assert call counts only when the call is the behaviour. Inject a clock or `AbortSignal` for time. Restore mocks automatically (runner config), do not rely on manual cleanup. For HTTP use a request-level interceptor rather than stubbing `fetch`.
- `node:test`: `mock.module` needs the experimental flag `--experimental-test-module-mocks` (verified in the Node CLI help), and coverage flags are experimental; prefer parameter injection there.
- Async tests always `await` or return; assert rejections with `await expect(p).rejects...` (Vitest) or `assert.rejects` (`node:test`).
- No `.only`; no `.skip`/`xit`/`todo` without a tracked-issue link in the reason. Vitest has `--allowOnly` (default on only outside CI) and `--detectAsyncLeaks`; use them if the project's config does.
- Library types: assert public types with the runner's type-test support (`expectTypeOf` in Vitest typecheck mode) or an inline `// @ts-expect-error` line.
- Coverage is a ratchet, not a goal; do not chase 100%. Branch coverage on changed code beats the global number. Property-based tests suit parsers/serialisers/pure algorithms when the project already has such a tool.
- If you break existing tests, fix them in the same change.
