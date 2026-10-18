---
name: node-configuration
description: "Configuration and secrets in a v1rus Node service: the environment parsed and validated exactly once at startup against a schema, the process failing to boot on a missing or malformed variable rather than throwing on first use, typed config namespace objects injected through DI so no layer reads process.env, why a scattered process.env read is untyped and unvalidated and invisible to the fail-fast check, secrets never defaulted and never logged and never committed, .env for local development only with the real source being the platform secret store, derived and computed settings resolved once, NODE_ENV pitfalls, and configuration for tests. Load when adding an environment variable, wiring the config module, injecting configuration into a provider, handling a secret or credential, or reviewing where configuration is read."
---

# Configuration and Secrets

Two rules produce everything below: **the environment is read once, at startup, validated**, and
**nothing downstream knows that `process.env` exists**.

## Validate at boot, fail to start

```ts
// config/env.schema.ts — the one place process.env appears
const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']),
  PORT: z.coerce.number().int().positive().default(3000),
  DATABASE_URL: z.string().url(),
  REDIS_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),                 // no default — ever
  LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug']).default('info'),
  SHUTDOWN_TIMEOUT_MS: z.coerce.number().int().positive().default(10_000),
  DATABASE_POOL_SIZE: z.coerce.number().int().positive().default(10),
});

export type Env = z.infer<typeof EnvSchema>;

export function loadEnv(source: NodeJS.ProcessEnv = process.env): Env {
  const parsed = EnvSchema.safeParse(source);
  if (!parsed.success) {
    // names only — never the values, they are secrets
    throw new Error(`Invalid environment: ${Object.keys(parsed.error.flatten().fieldErrors).join(', ')}`);
  }
  return parsed.data;
}
```

- **A missing variable is a boot failure, not a runtime surprise.** Discovering at 3am that
  `STRIPE_KEY` was undefined — because the first charge attempt of the day hit it — is the failure
  mode this removes. The deploy fails instead, in front of whoever deployed.
- The error message lists **variable names, never values**. A validation error that echoes the value
  prints the secret into the log it was meant to stay out of.
- Coerce and default *in the schema*, so the rest of the code sees `number`, not `string | undefined`.
  Env values are always strings: `PORT` without coercion is `"3000"`, and `"false"` is truthy.
- **Secrets have no defaults.** A defaulted `JWT_SECRET` means a misconfigured production boots
  successfully with a signing key that is in the repository.
- The schema library is `zod`, the default named in `v1rus-typescript:ts-boundaries-validation`;
  the shape above is what it looks like here. Do not introduce a second one for config.

## Typed config, injected

```ts
// config/env.ts — parsed once, at import; every namespace reads this object
export const env = loadEnv();

// config/database.config.ts
// registerAs takes a zero-argument factory — it is called by the config module with no arguments
export const databaseConfig = registerAs('database', () => ({
  url: env.DATABASE_URL,
  poolSize: env.DATABASE_POOL_SIZE,
} as const));
```

Group by consumer — `database`, `http`, `auth`, `queue`, `observability` — and inject the namespace
object, not the whole config:

```ts
constructor(@Inject(databaseConfig.KEY) private readonly config: ConfigType<typeof databaseConfig>) {}
```

- A provider that receives exactly the settings it uses is testable with a literal object, and its
  dependencies are visible in the constructor (`nest-di`).
- A module that needs configuration takes it through `registerAsync`, not by reaching for the config
  service inside itself (`nest-architecture`).
- Configuration is **immutable after boot**. Nothing mutates the config object; a value that must
  change at runtime is a feature flag or a database row, and adding a feature flag is a product
  decision, not an implementation detail (`v1rus-core:v1rus-code-policies`).
- Derived values are computed once, at load — a parsed allowlist, an assembled base URL, a
  precomputed key object — not re-derived per request.

## `process.env` past startup is a defect

```ts
// forbidden anywhere but config/
const timeout = Number(process.env.HTTP_TIMEOUT ?? 5000);
```

Three concrete costs, not a style preference: the value is untyped and unvalidated; it is invisible
to the boot check, so a typo in the variable name silently yields the default forever; and it cannot
be varied in a test without mutating global state, which makes the test order-dependent. Make it a
lint rule — `no-process-env` with an override for `src/config/**` — so it is caught at the edit, not
at review.

The one legitimate exception is the bootstrap itself, before the DI container exists, and even there
it goes through `loadEnv()`.

## Secrets

- The real source is the platform's secret store (the orchestrator's secrets, the cloud secret
  manager, the CI variable store). `.env` is a **local development convenience**, is in
  `.gitignore`, and is never read in a deployed environment.
- `.env.example` is committed with every key present and every value blank or obviously fake. It is
  the checklist a new environment is provisioned from, and the diff that tells a reviewer a new
  secret was introduced.
- A secret never reaches a log, a span attribute, an error message or an exception body. The logger
  redacts by path (`node-observability`), but redaction is the second line — not putting it there is
  the first.
- Rotation is a config change, not a deploy of new code: read the secret at boot from the store, and
  keep the restart cheap.
- A committed secret is compromised the moment it is pushed. Rotate it; removing the commit does
  not.

## `NODE_ENV`

`NODE_ENV` selects framework behaviour (`production` disables verbose framework errors and enables
library fast paths) — and that is all it should do. Branching business behaviour on it produces code
paths that are never exercised before production. If staging must behave differently from
production, that is an explicit setting with its own name, and `NODE_ENV` stays `production` in
both. In tests it is `test`, and the config is loaded from an explicit object rather than from a
`.env.test` file that drifts.

## Configuration in tests

A unit test constructs the provider with a literal config object — no env, no `ConfigModule`. An
e2e test loads a fixed config, overriding only what the test container supplies (the Testcontainers
database URL, a free port). Never `process.env.X = ...` inside a test: it leaks into every test that
runs after it in the same worker (`node-testing`).
