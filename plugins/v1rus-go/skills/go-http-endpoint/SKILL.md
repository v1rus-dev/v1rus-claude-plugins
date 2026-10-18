---
name: go-http-endpoint
description: |-
  Add or change Go HTTP routes, handlers, middleware, server setup, shutdown or outbound HTTP clients (net/http, ServeMux).
  Use when: touching handlers, routing patterns, middleware order, http.Server config, request/response encoding, error-to-status mapping, http.Client usage.
  Not for: gRPC; database-only changes (use go-database); scaffolding a whole new service (use go-new-service).
---

Read [reference/http.md](reference/http.md) and `${CLAUDE_PLUGIN_ROOT}/rules/go-core.md`. Match the router and middleware already in the repo; stdlib `ServeMux` is the default for new code. Test handlers with `httptest`. Security-sensitive changes (auth, CORS/CSRF, SSRF) are a policy decision: implement mechanics, flag the policy to the user and suggest the `security-expert` review.
