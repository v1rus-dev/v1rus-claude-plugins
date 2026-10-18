# Stack profiles — how the pipeline learns the stack

The pipeline's spine agents (`feature-architect`, `feature-designer`, `feature-developer`,
`test-planner`, `test-writer`, `feature-finalizer`) are **stack-agnostic**: they own the phase, the
artifact and the gate, not the technology. Everything technology-shaped — the layer names, the
sections of `architecture-plan.md`, which convention skill owns which rule, where tests live and on
what, how to compile-check — comes from a **stack profile** shipped by the technology layer.

This keeps one copy of the pipeline scaffolding (gates, complexity bands, checkpoint and commit
discipline, return contract) and one small profile per stack, instead of a full clone of every spine
agent per technology.

## Where profiles live

A stack layer ships its profile as a skill named `<stack>-pipeline-profile`:

| Stack | Profile skill |
|---|---|
| KMP / Compose Multiplatform | `v1rus-kmp:kmp-pipeline-profile` |
| Native Android / Jetpack Compose | `v1rus-android:android-pipeline-profile` |
| Flutter / Dart | `v1rus-flutter:flutter-pipeline-profile` |
| C# / ASP.NET Core | `v1rus-dotnet:dotnet-pipeline-profile` |
| Node.js / NestJS | `v1rus-node:node-pipeline-profile` |
| React / Next.js | `v1rus-react:web-pipeline-profile` |
| TypeScript monorepo, backend + web | `v1rus-fullstack:fullstack-pipeline-profile` |

Discovery is by capability, not by a hardcoded list: any skill whose name ends in
`-pipeline-profile` and whose description says it is a feature-pipeline stack profile qualifies, so a
future layer (native iOS, web, backend) is picked up without editing this file. Always use the
**plugin-qualified** name — two layers can be installed at once.

## Detection (orchestrator, Phase 0)

Detect the stack from repo markers, then confirm against the available-skills inventory:

| Marker in the repo root | Stack |
|---|---|
| `pubspec.yaml` with a `flutter` dependency | Flutter |
| `settings.gradle.kts` / `settings.gradle` with a Kotlin Multiplatform plugin, `commonMain` source sets | KMP |
| an `app` module applying `com.android.application`, an `AndroidManifest.xml`, no `commonMain` source set | Android-native |
| `Package.swift` / `*.xcodeproj` only | iOS-native |
| `*.sln` / `*.csproj` with an ASP.NET Core SDK or `Microsoft.NET.Sdk.Web` | .NET backend |
| `package.json` depending on `@nestjs/core`, a `nest-cli.json` | Node / NestJS |
| `package.json` depending on `next` (or `react` with a bundler), an `app/` or `pages/` tree | React / Next web |
| a workspace root (`pnpm-workspace.yaml` / workspaces) holding **both** of the previous two | TypeScript fullstack — use the fullstack profile, not one half |
| several of the above (polyglot repo) | ask the user which surface this task touches |

Record both facts in `STATE.md`:

```
- Stack: flutter | kmp | <other> | unknown
- Pipeline profile: <plugin>:<skill> | none — <reason>
```

If markers and installed layers disagree — a Flutter repo with only `v1rus-kmp` installed — that is
**not** a reason to use the wrong profile. Record `Pipeline profile: none — <stack> detected, no
matching layer installed` and run the fallback below.

## Passing it to a spine agent

Subagents start blind and cannot see the orchestrator's conversation, so every spine-agent prompt
carries the profile explicitly:

> Stack: `flutter`. Before doing anything else, invoke the skill `v1rus-flutter:flutter-pipeline-profile`
> (Skill tool) — it is the stack vocabulary for this project: layer names, the sections your artifact
> must use, which convention skills apply, where tests live, how to verify. Then read the project's
> `CLAUDE.md` for the concrete names.

Reviewers and the reporter do not need it: `code-reviewer` and the `*-expert` agents review against
the project's own conventions, and `feature-reporter` summarises artifacts.

## Fallback — no profile available

The pipeline must still complete end to end with only `v1rus-core` installed (self-sufficiency
invariant, see `agent-resolution.md`). When no profile resolves, the orchestrator tells the spine
agent so, and the agent derives the vocabulary itself:

1. Read the project's `CLAUDE.md` — in a v1rus project it documents the layer layout, the build and
   test commands, and the naming conventions.
2. Read the actual layout (`settings.gradle.kts` / `pubspec.yaml` / `Package.swift`, the top-level
   source folders) and mirror what is already there.
3. **Record the degradation in the artifact** — one line in the plan's assumptions section stating
   that no stack profile was available and the conventions were inferred from the project. Degradation
   is visible, never silent.

## What a profile must contain

A new stack layer's profile is complete when it answers all of these — nothing more:

1. **Stack identity** — the repo markers that identify it.
2. **Layer vocabulary** — what the layers are called, what each holds, the hard boundaries between them.
3. **`architecture-plan.md` stack sections** — the concrete replacements for the generic layer sections,
   plus the self-questions the plan must answer on this stack.
4. **Convention skills by area** — an area → skill table the planner names and the implementer invokes.
5. **Presentation pattern** — the state-holder shape and its rules.
6. **Design-spec mapping** — how a design maps onto the project's design system.
7. **Tests** — location, framework, doubles policy, naming, what is out of scope.
8. **Verification** — codegen/compile-check steps, which `test-runner` owns the full run, what never to read.
9. **Implementation escalation targets** — the engineer agents this stack provides (`feature-developer`
   stays the floor).
10. **Finalizer stack checklist** — the stack-specific cleanup items.
11. **Typical expert reviews** — which specialists this stack's changes usually warrant.

What a profile must **not** contain: phase order, gates, complexity bands, artifact names, commit
discipline, the return contract or the language rule — those are the pipeline's, and duplicating them
is how the two copies start to disagree.
