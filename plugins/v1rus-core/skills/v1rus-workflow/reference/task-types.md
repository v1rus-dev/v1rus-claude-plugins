# Task type routing

Task type, verification source of truth, testing pyramid target, and when to write tests. Whether tests are written at all is set by the complexity band (tests only from 7; see `v1rus-qa`); below it the "Write tests" cells are dormant and verification is build + static analysis + the quality gate. L0 (build of the affected module) is the implicit entry gate for every row; no code change means no L0.

| Task type | Source of truth | Min pyramid | Write tests | Special |
|---|---|---|---|---|
| Feature | Spec / test plan / AC list | L1-L2 | After implementation; before if AC are clear | |
| Bug fix | `swarm-report/<slug>-debug.md` repro steps | L1-L2 | Before the fix: failing test first | Red-green |
| Tech migration | Before-state baseline | L1-L2 | Before migration: establish coverage as part of the baseline | Capture before-state first |
| Library version bump | Before-state baseline | L1-L2 | Existing tests pass; add where gaps found | Capture before-state if tests absent |
| Refactoring | Before-state baseline (tests as proxy) | L1-L2 | Before refactor if coverage gaps | Behavior 1:1 with before-state |
| Infrastructure change (network, storage, auth, DI) | Spec / requirements | L1-L2 | After implementation | |
| UI / design task | Figma / screenshots | L0-L1 | none | Visual match reviewed manually |
| Performance optimization | Benchmark baseline | L0-L2 where measurable | Capture baseline before; measure delta after | Win must be a measurable delta |
| Investigation / research | Research output document | L1 only if code produced | N/A | No pyramid without code |

## Test feasibility gate

Tests are written when both hold: (1) there is a natural test boundary (pure function, API contract); (2) the effort is reasonable relative to the change, without building test infrastructure from scratch. Otherwise document the reason in the plan and proceed without tests for that scope. "Not obvious how to test" and "setup cost is prohibitive" are valid reasons; "didn't feel like it" is not. This governs discretionary scope only: a modified public symbol in the tested bands still follows the public-API gate in `v1rus-qa`; when its test cost is genuinely prohibitive, record a tracked exception (ignore annotation with an issue link), never a silent skip.

### Assess testability at planning time

Lower verification cost before implementing: a hard-to-reach surface gets a sample/sandbox harness where the behavior is prototyped first; changed logic gets extracted to a unit boundary rather than driven through the UI; temporary simplifications that make a verifiable prototype reachable sooner are fine (see disposable tests in `v1rus-qa`) but are removed or hardened before the quality gate. The goal is the cheapest path to a verifiable prototype, not deferring testing.

## Before-state baseline

A durable snapshot of current behavior, created before any change, detailed enough to verify the modified system behaves identically.

1. Passing tests cover the behavior being changed: the suite is the baseline (green before = spec for after).
2. No coverage: capture one. API/backend: response-shape snapshots of affected endpoints saved to `swarm-report/<slug>-baseline.md`. Pure logic: input to output pairs. Shortcut: write tests for the behavior first; that satisfies the baseline and the test step at once.

Sufficiency check: could someone who has never seen the system verify the migration from this baseline alone? Not a baseline: "should be fine", code review or static analysis (they check intent, not behavior), a passing build (proves compilation only).
