---
paths:
  - "**/package.json"
  - "**/turbo.json"
  - "**/pnpm-workspace.yaml"
  - "**/tsconfig.base.json"
  - "**/.env*"
  - "**/docker-compose*.yml"
---

# Workspace files — non-obvious rules

Only what breaks quietly in a fullstack monorepo: a build that passes locally and ships the wrong
artifact, a cache that serves a result produced with different inputs, a secret that reaches the
browser. Generic JSON/YAML hygiene is not listed. The shape of the workspace and the reasoning behind
it live in the `monorepo-layout` skill.

## `package.json` — per package

- **A package declares every import it makes.** If a file in `apps/web` imports a module, that module
  is a dependency of `apps/web`'s own `package.json` — not only of the root. pnpm's non-flat
  `node_modules` means an undeclared import resolves on one machine and fails on another, and it
  always fails in a Docker build that copies only one app.
- **Internal packages are referenced as `workspace:*`**, never by a published version range, or the
  install silently pulls a registry package with the same name.
- **Only the root `package.json` carries `packageManager`.** It is what pins the package manager for
  every developer and for CI; a second one in an app makes the two disagree.
- **A dependency added here goes through the `v1rus-dependencies` gate first** — never add a name
  from memory, and never hand-edit a version that the lockfile owns.
- Scripts are the same verbs in every package (`build`, `dev`, `lint`, `typecheck`, `test`), because
  the task runner addresses them by name across the workspace. A package that names its build
  `compile` is invisible to the pipeline.
- `"private": true` on every app and every internal package. Removing it is how an internal package
  gets published by accident.

## Lockfile

One lockfile, at the repo root. A lockfile inside `apps/*` or `packages/*` means someone ran the
package manager from the wrong directory: delete it and re-install from the root. Two lockfiles
produce two different dependency trees from the same commit.

## `pnpm-workspace.yaml`

- The `packages:` globs are the definition of the workspace. A directory not covered by them is not
  part of the install, and its imports resolve from the root by accident.
- Keep one version of the shared toolchain (TypeScript, the linter, the formatter, the test runner)
  for the whole workspace — a catalog entry referenced by every package, rather than a version
  repeated in each `package.json`. Two TypeScript versions in one repo produce type errors that
  appear only in the package with the older one.

## `turbo.json`

- **Every task declares its `outputs`.** A task with no declared outputs is cached as "produced
  nothing": the cache hits, the build directory stays empty, and the failure appears at deploy.
- **Every environment variable a task reads is declared** in that task's `env` (or in `globalEnv`
  when it is repo-wide). An undeclared variable is not part of the cache key, so a cached build made
  with a different value is served as if it were current. This is the single quietest defect in the
  repo: nothing errors.
- `dependsOn: ["^build"]` is what makes a package's dependencies build first. A task that consumes a
  sibling package's output and omits it works until the cache is cold.
- Long-running tasks (`dev`, a watcher) are `"persistent": true` and `"cache": false`; a persistent
  task must never be a `dependsOn` of anything.
- Tests that need a database or a running server are not cacheable unless that state is part of the
  inputs — mark them `"cache": false` rather than pretending.

## `tsconfig.base.json`

- It is the single compiler baseline for the workspace; a package `extends` it and overrides only
  what is genuinely package-specific (`jsx`, `lib`, `outDir`, `types`). Re-declaring a compiler flag
  that the base already sets is how the strictness of one package quietly drifts.
- Loosening a flag here loosens it for every package at once. Loosen in the one package that needs
  it, with a comment saying why — never in the base.
- Path aliases are not a substitute for a workspace dependency: an alias that points into another
  package's `src` bypasses its build and its public entry point. Reference the package.

## `.env` files

- **No `.env` at the repo root.** Each app owns its own, because a variable at the root has no owner
  and ends up loaded by the app it was not meant for.
- A real `.env*` file with values is never committed. `.env.example` is, per app, listing **every**
  variable the app reads with a one-line description and whether it is a secret. Adding a variable
  and not adding it to the example is how the next developer gets a runtime failure instead of a
  startup failure.
- **A secret never gains a client-exposed name.** A `NEXT_PUBLIC_`-prefixed variable (and any
  equivalent client-exposed prefix) is inlined into JavaScript served to every visitor — the prefix
  means "publish this value", not "make this reachable". If a value must not appear in a browser's
  view-source, it must not carry the prefix, and it must not be read from a module that client code
  imports.
- A variable added here is also added to the app's startup validation schema and to the task's `env`
  list in `turbo.json`, in the same change. Details: the `fullstack-configuration` skill.

## `docker-compose*.yml`

- This file exists for **local and CI infrastructure** — database, cache, object storage, a mail
  catcher — not to run the apps themselves during development.
- Pin images by an explicit tag, never `latest`: `latest` makes the database version a function of
  when someone last pulled.
- Credentials in this file are throwaway local values and are never reused for any real environment.
  Ports are explicit so a second project does not silently take the same one.
- Give the data volume a name. An anonymous volume makes "the database reset itself" an unexplainable
  intermittent event.
- CI uses the same compose file as local development, or the two drift and an e2e failure is
  unreproducible on a laptop.
