---
description: Build a small feature via the reduced-gate lite pipeline — fewer agents, no confirmation pause, one commit; same command as /feature with --lite
argument-hint: [short feature description | JIRA-KEY | Jira issue URL]
---

Alias for `/feature --lite`. There is no second pipeline: this command runs the **same** orchestration
with `Mode profile: lite`.

Do this:

1. Read `${CLAUDE_PLUGIN_ROOT}/commands/feature.md` and follow it exactly, with one override —
   the mode is **`lite`** regardless of whether `$ARGUMENTS` carries a flag. Treat `$ARGUMENTS`
   as the feature description / Jira key (strip a redundant `--lite` or `--fast` if present).
   A `--quiet` / `--no-questions` flag is **not** stripped away: it is a separate axis, so parse it
   exactly as `feature.md` does and set the question profile from it. `/feature-lite --quiet` is
   therefore the same thing as `/feature --lite --quiet`.
2. Read the *Pipeline modes* section of the `feature-pipeline` skill before the first phase. It is
   the single source for what lite changes, the four things lite never cuts (it compiles; the
   `v1rus-qa` complexity bands still rule; the security surface still gets `security-expert`; the
   non-negotiables still hold), and the risk triggers that still pause the confirmation gate.

**When not to use this command.** Lite is for a small, well-understood change you could describe in
two sentences. If the work is a new subsystem, touches auth / payments / a data migration / a public
contract, or you cannot yet state its acceptance criteria — use `/feature`. If the architect scores
the plan at complexity 7 or higher, stop at the confirmation gate and ask the user to switch to
`standard` rather than continuing in lite.
