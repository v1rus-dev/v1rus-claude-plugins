---
name: ktor-client-auth
description: "How a v1rus project wires bearer auth on the Ktor client: an access + refresh token pair as the default, the Auth plugin's bearer provider (loadTokens, refreshTokens, and sendWithoutRequest as a preemptive-attach policy rather than a way to make an endpoint anonymous), markAsRefreshTokenRequest as the thing that breaks the refresh loop, the provider's built-in single-flight refresh, telling a dead session apart from a dropped connection so a lost signal never logs the user out, refresh-token rotation persisted atomically, one session-expiry channel, and clearing tokens on logout. Load when wiring auth on an HttpClient, handling a 401, implementing or debugging token refresh, deciding where a token is stored, or when a user reports being logged out unexpectedly."
---

# Ktor Client Bearer Auth

The flow below is identical on native Android, KMP and a JVM backend client, so it is written down
once here. The layers above add only where the tokens are stored: `v1rus-android:android-data-layer`
for the Keystore reality, `v1rus-kmp:kmp-data-layer` for the per-platform store.

## An access + refresh pair is the default

Assume the backend issues a short-lived access token and a long-lived refresh token. An
**access-token-only design is not the house pattern**: it forces a choice between a long-lived access
token (a much worse credential to leak) and logging the user out whenever it expires.

If the backend exposes no refresh endpoint, that is a **gap to raise with the backend team**, not a
shape to copy. Where a project genuinely has to ship without one, a `401` goes straight to session
expiry and the reason is recorded as an explicit exception in the plan — never left implicit in the
code.

## The `bearer` provider

Install the `Auth` plugin once in the same factory that builds the `HttpClient`.

- **`loadTokens`** supplies the stored pair. Its result is **cached** — it is not consulted per
  request unless `cacheTokens` is turned off. It must not issue a request through the same client.
- **`refreshTokens`** exchanges the refresh token. Its receiver carries the `client` that made the
  failed call, that `response`, and `oldTokens`.
- **`sendWithoutRequest`** is the **preemptive-attach policy** — it decides whether credentials go
  out *before* a `401` challenge. It is **not** a way to mark an endpoint anonymous: returning `false`
  only defers the request to the challenge, and it is still retried with a token afterwards. Its
  default differs between Ktor's prose docs and its source, so read the default off the version the
  project pins instead of relying on either. Keep genuinely public endpoints (login, registration) on
  a **separate unauthenticated client** rather than trying to carve them out here.

## `markAsRefreshTokenRequest()` breaks the loop

The `client` handed to `refreshTokens` is the **same `HttpClient`, with `Auth` still installed**. Call
`markAsRefreshTokenRequest()` on the refresh request's builder:

```kotlin
refreshTokens {
    val new = client.submitForm(url = refreshUrl, formParameters = /* … */) {
        markAsRefreshTokenRequest()
    }.body<TokenResponse>()
    // persist and return the new pair
}
```

Without it the refresh call is itself subject to bearer interception, and a `401` on it triggers
another refresh — the classic infinite loop. This, not `sendWithoutRequest`, is the mechanism.

## The provider already refreshes once

Concurrent `401`s are serialised by the provider: the first caller runs `refreshTokens`, the rest wait
and reuse the result. **Do not hand-roll a second refresh path beside it.** If a bespoke refresh is
genuinely unavoidable, it is single-flight behind a `Mutex` for the same reason.

`nonCancellableRefresh` is worth knowing about: with it on, cancelling the request that triggered a
refresh cannot roll back a refresh that already succeeded.

## A dead session is not a dropped connection

This is the distinction that decides whether losing signal logs the user out, and the provider gives
you two different exits from `refreshTokens`:

| The refresh call… | Do this | What the provider does |
|---|---|---|
| completes and says the grant is dead (`401` / `invalid_grant`) | **return `null`** | clears the cached token; the original `401` surfaces to the caller |
| fails in transport (timeout, no route, TLS) | **let it throw** | keeps the cached pair; the exception surfaces to the caller |

So: **only the first case clears the stored pair and publishes session expiry.** A transport failure
fails the one call and nothing more — the next attempt retries with the pair still intact.
Conflating the two is exactly what logs users out the moment they walk into a lift.

The provider never calls `clearToken()` on the application's behalf in either case; clearing the
*persisted* pair is always your code's job.

## Rotation is persisted atomically

When the backend returns a new refresh token alongside the new access token, **persist the new pair as
one write.** A partial write leaves a live access token beside a dead refresh token — the session then
survives exactly until the access token expires and can never be recovered. If the store cannot write
two values atomically, store the pair as a single serialised value.

Ktor takes no position on rotation; this is a house rule.

## One session-expiry channel

A dead session is published on a **single channel that the app root observes** and turns into one
re-auth. Never re-authenticate from a call site. A second re-auth path is how duplicate login screens
appear, and it is the bug that survives longest because it needs two racing `401`s to reproduce.

## Logout

Clear the persisted pair and the provider's cache — `client.clearAuthTokens()`, or
`client.authProvider<BearerAuthProvider>()?.clearToken()` for one provider. Revoke server-side too
when the backend offers it; a client-side-only logout leaves a usable refresh token in the wild.

Clearing affects the cache, not requests already dispatched: those still carry the old header and will
complete. Cancel the scope that owns them if that matters.

## Never log the credentials

Tokens, `Authorization` headers and full request bodies stay out of the logs, including at `DEBUG` —
see `v1rus-core:v1rus-logging`. Where the pair is stored is a security decision settled at plan
stage with the `security-expert` review, not while writing the repository.
