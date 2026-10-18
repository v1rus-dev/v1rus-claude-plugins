---
name: api-contract
description: "The API contract between a NestJS backend and a Next.js frontend in one repository as a single source of truth: the v1rus default is a shared schema package that the backend validates requests and responses with and the frontend derives its types and its parsing from, with OpenAPI-generated clients and end-to-end typed RPC as the two documented alternatives and when each wins. Covers what lives in the contract package and what must never, request and response and error shapes, versioning a breaking change, and how a contract break is detected at typecheck and by contract tests instead of at runtime. Load when adding or changing an endpoint that the web app consumes, defining or moving a DTO, deciding how the frontend learns the backend's types, seeing a type duplicated on both sides, or reviewing a change that alters a payload. Do NOT load for how a controller or a validation pipe is written (v1rus-node:nest-http-api), how the frontend fetches and caches (v1rus-react:web-data-fetching), or schema validation as a language technique (v1rus-typescript:ts-boundaries-validation)."
---

# The API contract

**A shape that crosses the wire is declared once.** Two declarations of the same payload — a DTO
class in the backend and an interface in the frontend — are not a contract, they are two opinions
that agree until someone edits one. The whole reason both apps live in one repository is that this
is avoidable.

## The v1rus default: a shared schema package

`packages/contracts` holds a runtime **schema** per payload; both sides consume that one artifact.

- The **backend** validates with it: the schema is the request validator at the controller boundary
  and, where the risk justifies it, the response is parsed through it before it is sent.
- The **frontend** types against it: the response type is *inferred from* the schema, and the client
  parses the response with it rather than asserting a type onto `unknown`.
- Neither side declares the shape again. A frontend `interface User` that mirrors a backend DTO is
  the defect this skill exists to prevent.

**At the controller boundary the contract schema wins.** A NestJS service on its own validates a
request body with a decorated DTO class (`v1rus-node:nest-http-api`); here that class would be the
second declaration of a shape the contract already declares, so for every endpoint the web app
consumes the contract schema is the request validator — a validation pipe over the schema — and no
DTO class is written beside it. A standalone service, and an endpoint in this repository that is
outside the contract, keep the DTO class. Two mechanisms on the same endpoint is the case this rule
removes, not a choice left open.

```
packages/contracts/
  src/
    users/
      user.ts          entity schemas + inferred types
      endpoints.ts     route descriptors: method, path, params, body, response, errors
    common/
      pagination.ts    envelope shapes reused across areas
      error.ts         the error body every endpoint can return
    index.ts           the single public entry point
```

A **route descriptor** carries the method, the path template, and the schemas for params, query,
body and response. It matters as much as the payload schemas: a renamed path is then a typecheck
error at both call sites, not a 404 found by a user. The backend derives its route from the
descriptor (or asserts against it in a test); the frontend builds its URL from it and never writes
a path string by hand.

**What the contract package must never contain** — it is loaded into the browser bundle and into
the server process alike:

- No framework: no Nest decorators, no React, no ORM entity types, no Node built-ins.
- No database shape. The persistence model is the backend's business; leaking it into the contract
  makes every schema migration a frontend change. Map at the backend boundary.
- No secrets, no internal-only fields, no `process.env`, no side effects at import.
- No business logic beyond the semantics of the shape itself (a validator, a refinement, a branded
  id). If it needs a service, it does not belong here.

### Why this one

| Property | Shared schema | OpenAPI + generated client | End-to-end typed RPC |
|---|---|---|---|
| Single declaration of a shape | yes | yes, but the source is the backend's code and the frontend's copy is generated | yes |
| Types available without a build step | yes | no — stale generation is a real failure mode | yes |
| Runtime validation on both sides | yes, the same schema | only if the generator emits validators | on the boundary the library owns |
| The contract is reviewable in the diff | yes — it is hand-written | partly — the diff is generated output | no — it is the inferred type of the router |
| Backend still serves non-TypeScript clients | yes — it is ordinary HTTP | yes | poorly — the wire format is an implementation detail |
| Breaking change is caught by | `typecheck` on both apps | regeneration + typecheck, if regeneration ran | `typecheck` on both apps |

The shared schema wins on the two properties that actually cost time: the contract is a hand-written
artifact a reviewer can read, and there is no generation step between changing it and both sides
seeing the change. Its cost is honest — the schemas are maintained by hand, and the backend must
keep its persistence model mapped rather than exposed.

### When another option wins

- **OpenAPI generated from the backend, typed client generated for the frontend** — when the API has
  consumers outside this repository (a mobile app, a partner, another team), or the backend is not
  in this repository at all, or the backend is not TypeScript. Then the specification is the
  contract and the generated client is a build artifact. Rules if this is chosen: generation is a
  task in the pipeline, not a command someone remembers; the generated output is committed *or*
  regenerated in CI and the diff checked, never "usually up to date"; and nothing hand-edits
  generated files.
- **End-to-end typed RPC** — when the backend exists solely for this one frontend, both ship
  together, and no other consumer is plausible. It buys the least ceremony and costs the stable
  public surface: the wire format becomes an inferred type, so the day a second client appears the
  API has to be re-specified.

The choice is a **plan-stage decision** recorded in the project's `CLAUDE.md`, and it applies to the
whole repository. Two mechanisms in one API is the worst of all of them.

## Shapes

- **Requests and responses are distinct schemas**, even when they look alike today. A create body
  has no server-assigned id; a response has no write-only fields. Reusing one schema for both is
  how an `id` becomes optional everywhere.
- **One error body for the whole API**, declared in the contract, with a stable machine-readable
  code plus a human message. The frontend switches on the code; it never parses the message. How
  the backend produces it is `v1rus-node:nest-error-handling`; how the UI renders it is
  `v1rus-react:web-data-fetching`.
- **One pagination envelope**, one date encoding (a string format decided once — a `Date` does not
  survive JSON and reappears as a string on the other side), one convention for absent versus null.
  Decide each once in `common/`, not per endpoint.
- **Identifiers are branded types**, not bare strings, so a `UserId` cannot be passed where an
  `OrderId` belongs. Detail: `v1rus-typescript:ts-type-modelling`.

## Changing the contract

A contract change is **one commit that touches the contract package and both apps**. Splitting it
across commits creates a window where the repository does not typecheck, which is the state CI
cannot tell apart from a real break.

| Change | Breaking? | Order of work |
|---|---|---|
| Add an optional response field | no | contract → backend fills it → frontend reads it when ready |
| Add a required request field | yes | contract with it optional → backend accepts both → frontend sends it → contract makes it required → backend drops the fallback |
| Remove or rename a field | yes | contract marks it deprecated → frontend stops reading it → contract removes it → backend stops sending it |
| Change a field's type or meaning | yes | treat as remove + add; never reuse a name with a new meaning |
| Change a path or method | yes | update the descriptor; both sides fail typecheck until they follow |

**Deployment order decides what "breaking" means.** If the backend deploys first, the frontend must
tolerate the new response before it ships — so additive-then-subtractive, in that order, always. If
the two always ship together (one pipeline, one release), a single-step change is legitimate; say
which of the two this project is in its `CLAUDE.md`, because the whole table depends on it.

Never version by copying the schema (`UserV2` next to `User`) unless the API genuinely serves an
older client that cannot be updated. In a repository where both sides ship together, a version
suffix is unmigrated code with a new name.

## Detecting a break before runtime

Three layers, cheapest first:

1. **Typecheck across the workspace.** Both apps depend on the contract package, so removing a field
   fails the frontend's `typecheck` in the same CI run that built the backend. This only works if
   nothing launders the type: no `any`, no `as` onto a response, no re-declared local interface. A
   cast over a contract type defeats every other layer below, which is why it is a review blocker.
2. **Contract tests** (backend): the real handler's output is parsed with the contract's response
   schema. The typechecker sees the declared return type; the contract test sees what the handler
   *actually* returns after the ORM, the serializer and the interceptors have touched it — a `Date`
   instead of a string, an extra relation, a `null` where the schema says absent. This is the layer
   that catches what types cannot.
3. **e2e** against a running stack — the last net, not the first. Detail: `fullstack-verification`.

A change to `packages/contracts` marks both apps as affected in the task graph, so all three run on
that PR without anyone deciding to. That is the payoff for keeping the package a leaf.

## Related

`monorepo-layout` (where the package sits and why it is a leaf), `fullstack-verification` (the
contract test and the e2e layer), `fullstack-pipeline-profile` (contract-first order of work for a
feature spanning both sides), `v1rus-node:nest-http-api` (controllers, pipes, serialization),
`v1rus-react:web-data-fetching` (the client, caching, error rendering),
`v1rus-typescript:ts-boundaries-validation` (parsing at a boundary as a language technique).
