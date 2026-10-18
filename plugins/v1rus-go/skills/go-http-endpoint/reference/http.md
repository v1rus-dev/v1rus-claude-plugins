# Go HTTP

Routing (`net/http.ServeMux`, 1.22+): patterns `[METHOD ][HOST]/[PATH]`, wildcards `{id}`, `{rest...}`, exact root `{$}`; read values with `r.PathValue("id")`; conflicting patterns panic at registration (fails fast at startup). Verify details with `go doc net/http.ServeMux`.

Handlers: thin: decode, call service, encode. Business errors map to status codes in one place at the edge (`errors.Is` / `errors.As`); domain packages never import status codes. Limit bodies with `http.MaxBytesReader`; strict JSON with `Decoder.DisallowUnknownFields` where wanted. Use `omitzero` JSON tag for zero structs/`time.Time` (1.24+). `encoding/json/v2` is available on the newest toolchains; keep v1 in existing code and pin behavior with tests if adopting v2 (advisory).

Middleware: `func(http.Handler) http.Handler`. Suggested order: panic recovery, request ID/trace, logging, auth, body limit (advisory).

Server: always an explicit `*http.Server`, never bare `http.ListenAndServe`. Set `ReadHeaderTimeout` (always), `ReadTimeout`, `WriteTimeout`, `IdleTimeout`, `MaxHeaderBytes`; derive `BaseContext` from the root context. Never expose `http.DefaultServeMux` (importing `net/http/pprof` registers on it); serve pprof/metrics on a separate loopback/admin listener.

Graceful shutdown: run `ListenAndServe` in a goroutine (errgroup); on root-context cancellation call `srv.Shutdown(ctx)` with a bounded timeout (it waits for active requests until that context expires); treat `http.ErrServerClosed` as success; flip readiness to not-ready before shutdown; close DB pools after the server stops.

Health: `/healthz` (liveness, no dependencies) and `/readyz` (dependencies) (advisory convention).

Clients: never `http.DefaultClient` for production calls (no timeout); build `http.Client{Timeout: ...}` with a tuned `Transport`, reuse it; `http.NewRequestWithContext`; always close the body; limit what you read. Reverse proxies use `httputil.ReverseProxy.Rewrite`, not the deprecated `Director`.

CSRF for cookie-authenticated browser endpoints: `http.CrossOriginProtection` (stdlib; verify with `go doc net/http.CrossOriginProtection`). Outbound requests to user-supplied URLs need SSRF protection (resolve and validate the IP): policy decision, flag it.

Tests: `httptest.NewRecorder` calling `mux.ServeHTTP`, or `httptest.NewServer` for client code.
