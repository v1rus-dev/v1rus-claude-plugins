# Review checklist

- Injection: SQL, shell (`exec`, `shell: true`), HTML (`innerHTML`), paths (traversal, symlinks), URLs (SSRF allowlist), log lines (structured logging, no user strings in templates).
- Prototype pollution: deep merge / `Object.assign` of parsed JSON, dictionaries keyed by user input.
- ReDoS: regexes with nested quantifiers or overlapping alternations applied to user input; unbounded input length. Lint plugins exist (`eslint-plugin-regexp`, `eslint-plugin-security` on npm) but are optional and noisy: advisory.
- Secrets: in source, `.env` committed, logs, error messages, client bundles. Scan tooling is the project's choice.
- Crypto: only `node:crypto`/WebCrypto; AEAD; `timingSafeEqual`; password hashing with a memory-hard KDF; no `Math.random` for secrets.
- Errors: no stacks or schema internals to clients; generic message plus correlation id.
- Deserialisation: no `eval`/`vm` on user data; no revivers instantiating classes by name.
- Node permission model (`--permission`) is a hardening aid for trusted code, not a sandbox for hostile code (per the Node docs).
- Dependencies: new or changed packages checked per `ts-supply-chain`.
