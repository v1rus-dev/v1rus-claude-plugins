---
name: ts-boundaries-validation
description: "Runtime validation at every I/O boundary in TypeScript: why a declared type on JSON.parse, a fetch response body, an environment variable, a storage read or a message payload is a lie the compiler cannot catch, where the boundary actually is, parse-don't-validate so the unvalidated shape cannot flow inward, deriving the TypeScript type from the schema instead of writing both, being permissive about unknown fields in responses you do not own and strict about input you accept, parsing environment configuration once at startup, what to do when a parse fails, and why hand-written type predicates and generated OpenAPI/GraphQL types are not runtime checks. Load when writing or reviewing anything that reads data the program did not create — an API client or handler, a config or env module, cache and storage access, a webhook, a queue consumer, URL or query parameters, file or CLI input — or when deciding where a schema validator belongs. Not for framework-specific request pipelines, and not for modelling internal domain types (`ts-type-modelling`)."
---

# Boundaries and Runtime Validation

TypeScript checks the program it can see. Everything that crosses into the program from outside is
unchecked, and an annotation on it is a claim nobody verified.

## The lie

```ts
const user: User = JSON.parse(raw);          // JSON.parse returns any
const user = (await res.json()) as User;     // a cast over any — still any
const port: number = process.env.PORT;       // a string, or undefined
```

None of these is a check. The first field access that disagrees with reality produces `undefined`
somewhere downstream, usually in a different module, frequently as `Cannot read properties of
undefined`. The type told every subsequent reviewer the value was safe.

This is the one place where the compiler cannot help, which is why it is the one place that needs a
runtime schema.

## Where the boundary is

Every one of these is a boundary, and each is routinely missed:

- HTTP responses the program consumes, and HTTP request bodies, params and headers it accepts.
- Environment variables and any configuration file.
- `localStorage`, `sessionStorage`, IndexedDB, cookies, and any on-disk cache — including data
  **this** app wrote in a previous version, whose shape has since changed.
- Message-bus / queue payloads, `postMessage`, worker messages, server-sent events, WebSocket frames.
- URL path and query parameters, route params, CLI arguments.
- Webhooks and third-party callbacks.
- Rows from a raw SQL query or any driver that returns `any`.
- Files the program reads, uploads it receives, clipboard contents.

Everything inside that ring is typed code talking to typed code, and must **not** be re-validated —
see *Where not to validate*.

## Parse, don't validate

A boolean check leaves the caller holding the unnarrowed value and trusting itself to remember:

```ts
if (isUser(raw)) { /* raw is User only because a hand-written predicate said so */ }
```

A parse returns the narrow type, so the unvalidated shape has nowhere to go:

```ts
// data/user-api.ts — the boundary module
const userSchema = z.object({
  id: z.string().min(1),
  email: z.string().email(),
  createdAt: z.coerce.date(),
});

export type User = z.infer<typeof userSchema>;

export async function fetchUser(id: UserId, signal?: AbortSignal): Promise<User> {
  const res = await http.get(`/users/${id}`, { signal });
  return userSchema.parse(res.body);   // throws here, at the edge, with a path to the bad field
}
```

Three properties make this worth doing:

1. **The type is derived from the schema** (`z.infer`), never declared beside it. A hand-written
   type and a hand-written schema drift within two sprints, and the drift is invisible.
2. **The parse happens once**, in the module that owns the boundary. Nothing further in is given the
   raw shape, so nothing further in can be tempted to re-check it.
3. **The failure has a location**: the field, the value, and the call that produced it.

**The v1rus default schema validator is `zod`.** The schema is the declaration, the type falls out
of it with `z.infer` instead of being written twice, and the same schema runs unchanged in a browser
bundle and in a server process — which is what makes one schema shareable across a repository.
Naming a default does not skip the gate: the version is still resolved and CVE-checked at plan time
through `v1rus-dependencies`, and a project with a reason to use a different schema library records
that reason in its `CLAUDE.md`.

**One schema validator in the project, not two.** Two libraries means two dialects of the same
shape, and a rule tightened in one of them silently stays loose in the other. A framework's own
decorator-based validation is not the second library: NestJS DTO classes with `class-validator` are
a mechanism of that framework's HTTP pipeline, not a schema library, and they are allowed to coexist
with the project's schema validator. What both must obey is that **a value crossing into the domain
is validated exactly once** — whichever mechanism owns a boundary owns it alone, and the second
check is either dead code or a disagreement waiting to be found in production.

## Strictness runs in one direction

- **Input you accept — strict.** Reject unknown keys, reject the wrong type, do not coerce silently.
  An accepted-but-ignored field is a client bug you are hiding, and it becomes a security question
  the moment the object reaches a database update.
- **Responses you do not own — permissive.** Validate the fields you use and let the rest pass.
  A schema that rejects unknown keys on a third-party response turns *their* additive, non-breaking
  change into *your* outage.
- **Coerce deliberately.** Transport carries strings; the domain wants `Date`, `number`, a branded
  id (`ts-type-modelling`). Do that conversion in the schema, at the boundary, so the domain never
  holds a string that means a date. Note explicitly in a comment when a coercion is lossy.

## Configuration

One module parses the entire environment at startup, exports a frozen typed object, and is the only
place in the codebase that reads the raw environment:

```ts
// config.ts
const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']),
  PORT: z.coerce.number().int().positive(),
  DATABASE_URL: z.string().url(),
});

export const config = Object.freeze(envSchema.parse(process.env));
```

The point is failing at boot with "PORT is not a number" rather than at 3 a.m. with a type error in
a request handler. Never read the raw environment anywhere else, never default a required secret to
a placeholder, and never log the parsed config object wholesale — it holds credentials
(`v1rus-logging`).

## When a parse fails

A parse failure at a boundary is an **expected** failure, not a bug — the network, the third party,
or the user did something. Handle it accordingly:

- Map it to the project's error vocabulary at the boundary (`ts-error-handling`). A raw validator
  error object should not travel up through the application, and should never reach a user.
- Log it once, with the field path, and **without** the payload — request and response bodies carry
  personal data and tokens (`v1rus-logging`).
- Never `catch` and substitute a default silently. An empty array standing in for a failed parse is
  a blank screen with no diagnosis.
- Do not retry a parse failure. It is deterministic; the shape will not improve.

## Where not to validate

Validating everywhere is the standard overcorrection and it costs more than it saves:

- **Not between internal functions.** The type system already proved that call. A runtime check
  there is dead code that makes the next reader think the type is untrusted.
- **Not in the domain layer.** A schema import in a domain module inverts the dependency direction:
  the domain would then depend on the transport's shape. Parse in the adapter, hand the domain a
  domain type.
- **Not twice on the same value.** Re-parsing in a second layer means the first layer's output type
  is not believed, which is a design problem, not a safety measure.

## What is not a runtime check

- **Type predicates and assertion functions.** `function isUser(x: unknown): x is User` is an
  assertion whose body nobody verifies. When it is wrong it is silently wrong. If a predicate is
  genuinely the right tool, it needs a test; a schema does not.
- **Generated types.** OpenAPI, GraphQL and protobuf codegen produce *types*, from a document that
  may be out of date or aspirational. They remove the typing work, not the trust problem — the
  response still arrives from a server that may have shipped ahead of its spec. Generated types plus
  a schema parse at the boundary; or generate the schema, not just the type.
- **`as unknown as T`.** The longer spelling of the same lie.
