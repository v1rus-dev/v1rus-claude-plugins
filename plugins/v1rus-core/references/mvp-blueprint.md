# MVP blueprints — how `/mvp-init` learns to create a project

`/mvp-init` turns a project description into a running, convention-correct skeleton. The command
itself is **stack-agnostic**: it owns the brief, the stack choice, the plan, the confirmation gate,
the verification loop and the generated project `CLAUDE.md`. Everything technology-shaped — how an
empty project of this stack comes into existence, what its module graph looks like, which
dependencies an MVP needs, what the app skeleton wires up, how to verify it builds — comes from an
**MVP blueprint** shipped by the technology layer.

Same split as the feature pipeline's stack profiles (`skills/feature-pipeline/references/stack-profile.md`):
one copy of the scaffolding process, one small blueprint per stack, no per-stack clone of the command.

## Where blueprints live

A stack layer ships its blueprint as a skill named `<stack>-mvp-blueprint`:

| Stack | Blueprint skill |
|---|---|
| KMP / Compose Multiplatform | `v1rus-kmp:kmp-mvp-blueprint` |
| Native Android / Jetpack Compose | `v1rus-android:android-mvp-blueprint` |
| Flutter / Dart | `v1rus-flutter:flutter-mvp-blueprint` |
| C# / ASP.NET Core | `v1rus-dotnet:dotnet-mvp-blueprint` |
| Node.js / NestJS | `v1rus-node:node-mvp-blueprint` |
| React / Next.js | `v1rus-react:web-mvp-blueprint` |
| TypeScript monorepo, backend + web | `v1rus-fullstack:fullstack-mvp-blueprint` |

Discovery is by capability, not by a hardcoded list: any skill whose name ends in `-mvp-blueprint`
and whose description says it is an `/mvp-init` blueprint qualifies, so a future layer (native iOS,
web, backend) is picked up without editing this file. Always use the **plugin-qualified** name.

A blueprint is a *sibling* of the stack's `*-pipeline-profile`, not a section of it: the profile
answers "how do I build a feature in an existing project", the blueprint answers "how does the
project come to exist". Keep them in separate skills — the profile's contract is closed at its
eleven items and the two are loaded at different times.

## What a blueprint must contain

A blueprint is complete when it answers all eleven of these — and stops there.

1. **Stack identity.** Which answers in the brief select this stack: target platforms, whether code
   is shared across them, team-language constraints. Also the anti-signals — when to send the user
   to a different layer.
2. **Bootstrap route.** How an empty project of this stack is created, in order of preference:
   the official generator command when one exists, otherwise the hand-written file set (list it).
   Include how the build wrapper / lockfile is obtained, and what to do when the toolchain is
   missing: print the exact command for the developer to run in their own terminal and continue with
   everything that does not need it. Never install a toolchain, never use `sudo`.
3. **Module graph at MVP size.** The layout to create *now* — deliberately smaller than a mature
   project's graph — plus the rule for when each deferred module gets added later. Say what is
   one module at MVP that would be three at scale, and why that is safe.
4. **Baseline dependency set, by role.** Names only, grouped by role (DI, networking, serialization,
   persistence, navigation, image loading, logging, testing). **No versions** — every version is
   resolved at plan time through the `v1rus-dependencies` gate. Mark each entry mandatory-for-MVP
   or deferred, so the plan can drop what the brief does not need.
5. **Build configuration.** Where dependency coordinates are declared, the platform/SDK settings the
   brief's answers map to (application id, minimum platform versions, flavors only if asked),
   static-analysis configuration, and codegen wiring if the stack uses it.
6. **App skeleton.** What the scaffold wires up so the plumbing is proven: entry point per platform,
   DI initialisation and its order, theme / design-system seed, the navigation host with one route,
   the network client with one endpoint, storage initialisation, localisation seed. Name the types
   the way this stack's conventions name them.
7. **The first vertical slice.** The one end-to-end feature the scaffold ships with — a real screen
   through state holder, repository, network to a rendered result, with its loading / empty / error
   states. It is real working code, never a TODO: it is what proves the wiring before any feature
   work starts. Say which slice you build when the brief gives no obvious candidate.
8. **Project `CLAUDE.md` inputs.** The concrete facts this stack must record in the generated
   project's `CLAUDE.md`, because every downstream plugin reads them: module paths, build and test
   task names, the real names of the state-holder / navigator / theme types, codegen commands,
   where tests live, and which v1rus plugins the project should enable.
9. **Verification.** The exact commands that must pass before the scaffold is declared done
   (compile / analyze / test), and what "runnable" means on this stack — the command that starts the
   app on each target, and which of those are checkable headlessly and which need the developer.
10. **Escalation targets.** Which agents implement the scaffold on this stack, per role (build
    configuration, logic layer, UI layer) — `feature-developer` stays the floor when none is
    installed.
11. **Known first-run traps.** The two or three things that predictably break a fresh project on
    this stack and how to avoid them up front.

## What a blueprint must NOT contain

- **Pinned versions of anything.** A version in a document rots faster than anyone updates it. The
  only allowed exception is a minimum platform requirement that gates whether a mechanism exists at
  all, and it is written as a floor ("requires Dart 3.10+"), never as the version to use.
- The phase order, the confirmation gate, the commit discipline, the brief's question set or the
  language rule — those belong to `/mvp-init`, and duplicating them is how two copies start to
  disagree.
- Product decisions: which features the MVP has, what it looks like, what the business rules are.
  Those come from the brief.
- Project-specific names from any real client project.

## Fallback — no blueprint available

`/mvp-init` must degrade visibly, never silently. When no blueprint resolves for the chosen stack,
the command says so to the user in one line, records `Blueprint: none — <reason>` in the brief, and
either proceeds from the stack layer's own convention skills and rules (naming the degradation in
the generated `CLAUDE.md`) or stops if not even those are installed. A wrong-stack blueprint is
never a substitute for a missing one.
